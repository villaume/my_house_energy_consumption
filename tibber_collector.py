"""
Tibber Energy Consumption Data Collector

A clean, production-ready implementation to fetch energy consumption
data from Tibber's GraphQL API. Designed to run efficiently on Raspberry Pi.

Features:
- Hourly resolution (highest available via GraphQL API)
- Proper pagination handling
- Incremental data fetching
- Secure credential management
- CSV storage with deduplication

Note: The GraphQL API supports HOURLY, DAILY, WEEKLY, MONTHLY, and ANNUAL resolutions.
For higher resolution data (15-minute intervals), you would need to use Tibber's
real-time WebSocket API or the REST Data API.
"""

import httpx
import polars as pl
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import os
from typing import Optional, Dict, Any, List
import time
import dotenv

dotenv.load_dotenv()

class TibberCollector:
    """Collects energy consumption data from Tibber API"""
    
    def __init__(
        self, 
        access_token: Optional[str] = None,
        home_id: Optional[str] = None,
        data_file: str = "tibber_consumption_data.csv"
    ):
        """
        Initialize the Tibber collector
        
        Args:
            access_token: Tibber API access token (or set TIBBER_TOKEN env var)
            home_id: Tibber home ID (or set TIBBER_HOME_ID env var)
            data_file: Path to CSV file for storing data
        """
        self.access_token = access_token or os.getenv('TIBBER_TOKEN')
        self.home_id = home_id or os.getenv('TIBBER_HOME_ID')
        self.data_file = Path(data_file)
        self.api_url = 'https://api.tibber.com/v1-beta/gql'
        
        if not self.access_token:
            raise ValueError(
                "No access token provided. Set TIBBER_TOKEN environment variable "
                "or pass access_token parameter"
            )
        
        # Set headers before trying to fetch home ID
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.access_token}'
        }
        
        if not self.home_id:
            # Try to fetch home ID automatically
            self.home_id = self._get_home_id()
    
    def _get_home_id(self) -> str:
        """Automatically fetch the first available home ID"""
        query = """
        {
          viewer {
            homes {
              id
              appNickname
              address {
                address1
              }
            }
          }
        }
        """
        
        response = self._make_request({'query': query})
        homes = response.get('data', {}).get('viewer', {}).get('homes', [])
        
        if not homes:
            raise ValueError("No homes found in your Tibber account")
        
        home = homes[0]
        print(f"✅ Using home: {home.get('appNickname', 'N/A')} (ID: {home['id']})")
        return home['id']
    
    def _make_request(self, payload: Dict[str, Any], retries: int = 3) -> Dict[str, Any]:
        """
        Make a GraphQL request with retry logic
        
        Args:
            payload: GraphQL query payload
            retries: Number of retries on failure
            
        Returns:
            Response JSON
        """
        for attempt in range(retries):
            try:
                response = httpx.post(
                    self.api_url,
                    json=payload,
                    headers=self.headers,
                    timeout=60.0  # Increased timeout for slower connections
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if 'errors' in data:
                        print(f"⚠️  GraphQL errors: {data['errors']}")
                    return data
                elif response.status_code == 429:
                    # Rate limited - wait and retry
                    wait_time = 2 ** attempt
                    print(f"⚠️  Rate limited. Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                elif response.status_code == 504:
                    # Gateway timeout - wait and retry
                    wait_time = 2 ** attempt
                    print(f"⚠️  Gateway timeout. Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                else:
                    print(f"❌ Request failed: {response.status_code} - {response.text[:200]}")
                    
            except Exception as e:
                print(f"⚠️  Request error (attempt {attempt + 1}/{retries}): {e}")
                if attempt < retries - 1:
                    time.sleep(1)
        
        raise Exception(f"Failed to make request after {retries} attempts")
    
    def _get_last_timestamp(self) -> Optional[datetime]:
        """Get the timestamp of the most recent data point in storage"""
        if not self.data_file.exists():
            return None
        
        try:
            df = pl.read_csv(self.data_file, separator='\t')
            if len(df) == 0:
                return None
            
            # Parse the 'from' timestamp and get the maximum
            # Use map_elements to handle timezone-aware datetimes
            df_with_dates = df.with_columns(
                pl.col('from').map_elements(
                    lambda x: datetime.fromisoformat(x.replace('Z', '+00:00')),
                    return_dtype=pl.Datetime("us", "UTC")
                ).alias('from_dt')
            )
            
            last_timestamp = df_with_dates['from_dt'].max()
            return last_timestamp
        except Exception as e:
            print(f"⚠️  Could not read last timestamp: {e}")
            return None
    
    def fetch_consumption_data(
        self,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        resolution: str = "HOURLY",
        max_records: Optional[int] = None
    ) -> pl.DataFrame:
        """
        Fetch consumption data with pagination
        
        Args:
            since: Start datetime (defaults to last stored timestamp or 90 days ago)
            until: End datetime (defaults to now)
            resolution: Data resolution (HOURLY, DAILY, WEEKLY, MONTHLY, ANNUAL)
            max_records: Maximum number of records to fetch (None = all)
            
        Returns:
            Polars DataFrame with consumption data
        """
        # Determine date range (use timezone-aware datetimes)
        if until is None:
            until = datetime.now(timezone.utc)
        elif until.tzinfo is None:
            # Make timezone-aware if not already
            until = until.replace(tzinfo=timezone.utc)
        
        if since is None:
            last_timestamp = self._get_last_timestamp()
            if last_timestamp:
                # Fetch from last timestamp + 1 hour (for hourly data)
                since = last_timestamp + timedelta(hours=1)
                print(f"📅 Fetching data since last collection: {since.isoformat()}")
            else:
                # Default to 90 days ago (Tibber's typical limit)
                since = until - timedelta(days=90)
                print(f"📅 No existing data. Fetching last 90 days since: {since.isoformat()}")
        elif since.tzinfo is None:
            # Make timezone-aware if not already
            since = since.replace(tzinfo=timezone.utc)
        
        print(f"📅 Date range: {since.isoformat()} to {until.isoformat()}")
        print(f"📊 Resolution: {resolution}")
        
        # Fetch all pages
        all_edges = []
        cursor = None
        page_count = 0
        
        # Tibber typically allows up to ~10,000 quarter-hourly records
        # That's about 104 days of data
        page_size = 1000  # Fetch 1000 records per page
        
        while True:
            if max_records and len(all_edges) >= max_records:
                print(f"✅ Reached max records limit ({max_records})")
                break
            
            page_count += 1
            print(f"📄 Fetching page {page_count}...")
            
            # Build query with pagination
            query = self._build_consumption_query(
                resolution=resolution,
                first=page_size,
                after=cursor
            )
            
            response = self._make_request({'query': query})
            
            # Extract data
            try:
                consumption = response['data']['viewer']['home']['consumption']
                edges = consumption['edges']
                page_info = consumption['pageInfo']
            except KeyError as e:
                print(f"❌ Unexpected response structure: {e}")
                break
            
            print(f"   Got {len(edges)} records")
            
            if len(edges) == 0:
                print("✅ No more data available")
                break
            
            # Check date range
            if edges:
                first_date_str = edges[0]['node']['from']
                last_date_str = edges[-1]['node']['from']
                
                # Parse dates - handle both 'Z' and timezone offsets
                first_date = datetime.fromisoformat(first_date_str.replace('Z', '+00:00'))
                last_date = datetime.fromisoformat(last_date_str.replace('Z', '+00:00'))
                
                print(f"   Date range: {first_date} to {last_date}")
                
                # Tibber API returns data in reverse chronological order (newest first)
                # Stop if the oldest date in this page is before our 'since' date
                oldest_in_page = min(first_date, last_date)
                if since and oldest_in_page < since:
                    print(f"✅ Reached target start date ({since})")
                    # Filter edges to only include dates >= since
                    edges = [
                        e for e in edges 
                        if datetime.fromisoformat(e['node']['from'].replace('Z', '+00:00')) >= since
                    ]
                    all_edges.extend(edges)
                    break
            
            all_edges.extend(edges)
            
            # Check if there are more pages
            if not page_info.get('hasNextPage', False):
                print("✅ No more pages available")
                break
            
            cursor = page_info['endCursor']
            
            # Small delay to be respectful to the API
            time.sleep(0.3)
        
        print(f"\n📊 Total records collected: {len(all_edges)}")
        
        if not all_edges:
            print("ℹ️  No new data to collect")
            return pl.DataFrame()
        
        # Convert to DataFrame
        df = pl.DataFrame([edge['node'] for edge in all_edges])
        
        # Filter by date range if specified  
        if since or until:
            # Parse datetime strings with timezone information
            df = df.with_columns(
                pl.col('from').map_elements(
                    lambda x: datetime.fromisoformat(x.replace('Z', '+00:00')),
                    return_dtype=pl.Datetime("us", "UTC")
                ).alias('from_dt')
            )
            
            if since:
                df = df.filter(pl.col('from_dt') >= since)
            if until:
                df = df.filter(pl.col('from_dt') <= until)
            
            df = df.drop('from_dt')
        
        print(f"✅ Final dataset: {len(df)} records")
        return df
    
    def _build_consumption_query(
        self,
        resolution: str = "HOURLY",
        first: int = 1000,
        after: Optional[str] = None
    ) -> str:
        """Build a GraphQL query for consumption data"""
        after_clause = f', after: "{after}"' if after else ''
        
        query = f"""
        {{
          viewer {{
            home(id: "{self.home_id}") {{
              consumption(resolution: {resolution}, first: {first}{after_clause}) {{
                pageInfo {{
                  hasNextPage
                  endCursor
                }}
                edges {{
                  node {{
                    from
                    to
                    consumption
                    consumptionUnit
                    cost
                    unitPrice
                    unitPriceVAT
                    currency
                  }}
                }}
              }}
            }}
          }}
        }}
        """
        return query
    
    def save_data(self, df: pl.DataFrame, append: bool = True) -> None:
        """
        Save data to CSV file
        
        Args:
            df: DataFrame to save
            append: If True, append to existing file (with deduplication)
        """
        if len(df) == 0:
            print("ℹ️  No data to save")
            return
        
        if append and self.data_file.exists():
            # Load existing data
            existing_df = pl.read_csv(self.data_file, separator='\t')
            
            # Combine and deduplicate
            combined_df = pl.concat([existing_df, df])
            combined_df = combined_df.unique(subset=['from', 'to'], keep='last')
            
            # Sort by timestamp
            combined_df = combined_df.sort('from')
            
            print(f"💾 Saving {len(combined_df)} total records (removed duplicates)")
            combined_df.write_csv(self.data_file, separator='\t')
        else:
            print(f"💾 Saving {len(df)} records")
            df.write_csv(self.data_file, separator='\t')
        
        print(f"✅ Data saved to {self.data_file}")
    
    def collect(
        self,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        resolution: str = "HOURLY"
    ) -> pl.DataFrame:
        """
        Main collection method: fetch and save data
        
        Args:
            since: Start datetime (auto-detects if None)
            until: End datetime (defaults to now)
            resolution: Data resolution (HOURLY, DAILY, WEEKLY, MONTHLY, ANNUAL)
            
        Returns:
            DataFrame with collected data
        """
        print("🚀 Starting Tibber data collection")
        print(f"🏠 Home ID: {self.home_id}")
        
        df = self.fetch_consumption_data(
            since=since,
            until=until,
            resolution=resolution
        )
        
        self.save_data(df, append=True)
        
        return df


def main():
    """Main entry point for CLI usage"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Collect Tibber energy consumption data"
    )
    parser.add_argument(
        '--token',
        help='Tibber API access token (or set TIBBER_TOKEN env var)'
    )
    parser.add_argument(
        '--home-id',
        help='Tibber home ID (auto-detected if not provided)'
    )
    parser.add_argument(
        '--data-file',
        default='tibber_consumption_data.csv',
        help='Output CSV file path'
    )
    parser.add_argument(
        '--resolution',
        choices=['HOURLY', 'DAILY', 'WEEKLY', 'MONTHLY', 'ANNUAL'],
        default='HOURLY',
        help='Data resolution (HOURLY is the highest available)'
    )
    parser.add_argument(
        '--since',
        help='Start date (ISO format: 2024-01-01T00:00:00)'
    )
    parser.add_argument(
        '--until',
        help='End date (ISO format: 2024-12-31T23:59:59)'
    )
    
    args = parser.parse_args()
    
    # Parse dates
    since = datetime.fromisoformat(args.since) if args.since else None
    until = datetime.fromisoformat(args.until) if args.until else None
    
    # Create collector and run
    collector = TibberCollector(
        access_token=args.token,
        home_id=args.home_id,
        data_file=args.data_file
    )
    
    collector.collect(
        since=since,
        until=until,
        resolution=args.resolution
    )


if __name__ == "__main__":
    main()
