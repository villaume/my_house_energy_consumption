"""
Tibber Energy Consumption Data Collector (SQLite version)

Collects energy consumption data from Tibber's GraphQL API and stores it in SQLite.
"""

import httpx
import sqlite3
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import os
from typing import Optional, Dict, Any, List
import time
import sys

# Try to load dotenv if available
try:
    import dotenv
    dotenv.load_dotenv()
except ImportError:
    pass

class TibberCollector:
    """Collects energy consumption data from Tibber API"""

    def __init__(
        self,
        access_token: Optional[str] = None,
        home_id: Optional[str] = None,
        db_path: str = "tibber_data.sqlite"
    ):
        """
        Initialize the Tibber collector

        Args:
            access_token: Tibber API access token (or set TIBBER_TOKEN env var)
            home_id: Tibber home ID (or set TIBBER_HOME_ID env var)
            db_path: Path to SQLite database file
        """
        self.access_token = access_token or os.getenv('TIBBER_TOKEN')
        self.home_id = home_id or os.getenv('TIBBER_HOME_ID')
        self.db_path = Path(db_path)
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

        # Initialize database
        self._init_database()

    def _init_database(self) -> None:
        """Initialize SQLite database and create tables if they don't exist"""
        con = sqlite3.connect(str(self.db_path))
        cur = con.cursor()

        # Create hourly consumption table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS hourly_consumption (
                from_time TEXT NOT NULL,
                to_time TEXT NOT NULL,
                consumption REAL,
                consumption_unit TEXT,
                cost REAL,
                unit_price REAL,
                unit_price_vat REAL,
                currency TEXT,
                PRIMARY KEY (from_time, to_time)
            )
        """)

        # Create daily aggregation table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS daily_consumption (
                date TEXT PRIMARY KEY,
                total_consumption REAL,
                total_cost REAL,
                avg_unit_price REAL,
                currency TEXT
            )
        """)

        # Create monthly aggregation table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS monthly_consumption (
                year INTEGER,
                month INTEGER,
                total_consumption REAL,
                total_cost REAL,
                avg_unit_price REAL,
                currency TEXT,
                PRIMARY KEY (year, month)
            )
        """)

        con.commit()
        con.close()
        print(f"✅ Database initialized at {self.db_path}")

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
        """Make a GraphQL request with retry logic"""
        for attempt in range(retries):
            try:
                response = httpx.post(
                    self.api_url,
                    json=payload,
                    headers=self.headers,
                    timeout=60.0
                )

                if response.status_code == 200:
                    data = response.json()
                    if 'errors' in data:
                        print(f"⚠️  GraphQL errors: {data['errors']}")
                    return data
                elif response.status_code == 429:
                    wait_time = 2 ** attempt
                    print(f"⚠️  Rate limited. Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                elif response.status_code == 504:
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
        try:
            con = sqlite3.connect(str(self.db_path))
            cur = con.cursor()
            cur.execute("""
                SELECT MAX(from_time) as last_time
                FROM hourly_consumption
            """)
            result = cur.fetchone()
            con.close()

            if result and result[0]:
                return datetime.fromisoformat(result[0])
            return None
        except Exception as e:
            print(f"⚠️  Could not read last timestamp: {e}")
            return None

    def fetch_consumption_data(
        self,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        resolution: str = "HOURLY"
    ) -> List[Dict[str, Any]]:
        """Fetch consumption data with pagination"""

        # Determine date range
        if until is None:
            until = datetime.now(timezone.utc)
        elif until.tzinfo is None:
            until = until.replace(tzinfo=timezone.utc)

        if since is None:
            last_timestamp = self._get_last_timestamp()
            if last_timestamp:
                since = last_timestamp + timedelta(hours=1)
                print(f"📅 Fetching data since last collection: {since.isoformat()}")
            else:
                since = until - timedelta(days=90)
                print(f"📅 No existing data. Fetching last 90 days since: {since.isoformat()}")
        elif since.tzinfo is None:
            since = since.replace(tzinfo=timezone.utc)

        print(f"📅 Date range: {since.isoformat()} to {until.isoformat()}")
        print(f"📊 Resolution: {resolution}")

        # Fetch all pages
        all_records = []
        cursor = None
        page_count = 0
        page_size = 1000

        while True:
            page_count += 1
            print(f"📄 Fetching page {page_count}...")

            # Build query
            if cursor is None:
                query = self._build_consumption_query(resolution=resolution, last=page_size)
            else:
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

                first_date = datetime.fromisoformat(first_date_str.replace('Z', '+00:00'))
                last_date = datetime.fromisoformat(last_date_str.replace('Z', '+00:00'))

                print(f"   Date range: {first_date} to {last_date}")

                oldest_in_page = min(first_date, last_date)
                if since and oldest_in_page < since:
                    print(f"✅ Reached target start date ({since})")
                    edges = [
                        e for e in edges
                        if datetime.fromisoformat(e['node']['from'].replace('Z', '+00:00')) >= since
                    ]
                    all_records.extend([edge['node'] for edge in edges])
                    break

            all_records.extend([edge['node'] for edge in edges])

            if not page_info.get('hasNextPage', False):
                print("✅ No more pages available")
                break

            cursor = page_info['endCursor']
            time.sleep(0.3)

        print(f"\n📊 Total records collected: {len(all_records)}")

        # Filter by date range
        if since or until:
            filtered = []
            for record in all_records:
                record_time = datetime.fromisoformat(record['from'].replace('Z', '+00:00'))
                if since and record_time < since:
                    continue
                if until and record_time > until:
                    continue
                filtered.append(record)
            all_records = filtered

        print(f"✅ Final dataset: {len(all_records)} records")
        return all_records

    def _build_consumption_query(
        self,
        resolution: str = "HOURLY",
        first: int = 1000,
        after: Optional[str] = None,
        last: Optional[int] = None
    ) -> str:
        """Build a GraphQL query for consumption data"""
        after_clause = f', after: "{after}"' if after else ''

        if last is not None:
            size_clause = f'last: {last}'
        else:
            size_clause = f'first: {first}'

        query = f"""
        {{
          viewer {{
            home(id: "{self.home_id}") {{
              consumption(resolution: {resolution}, {size_clause}{after_clause}) {{
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

    def save_data(self, records: List[Dict[str, Any]]) -> None:
        """Save data to SQLite database"""
        if len(records) == 0:
            print("ℹ️  No data to save")
            return

        con = sqlite3.connect(str(self.db_path))
        cur = con.cursor()

        # Insert or replace data
        for record in records:
            cur.execute("""
                INSERT OR REPLACE INTO hourly_consumption
                (from_time, to_time, consumption, consumption_unit, cost, unit_price, unit_price_vat, currency)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record['from'],
                record['to'],
                record.get('consumption'),
                record.get('consumptionUnit'),
                record.get('cost'),
                record.get('unitPrice'),
                record.get('unitPriceVAT'),
                record.get('currency')
            ))

        con.commit()

        cur.execute("SELECT COUNT(*) FROM hourly_consumption")
        record_count = cur.fetchone()[0]
        print(f"💾 Saved {len(records)} new records")
        print(f"📊 Total records in database: {record_count}")

        con.close()

        # Update aggregations
        self._update_aggregations()

        print(f"✅ Data saved to {self.db_path}")

    def _update_aggregations(self) -> None:
        """Update daily and monthly aggregation tables"""
        con = sqlite3.connect(str(self.db_path))
        cur = con.cursor()

        # Update daily aggregations
        cur.execute("""
            INSERT OR REPLACE INTO daily_consumption
            SELECT
                DATE(from_time) as date,
                SUM(consumption) as total_consumption,
                SUM(cost) as total_cost,
                AVG(unit_price) as avg_unit_price,
                MAX(currency) as currency
            FROM hourly_consumption
            WHERE consumption IS NOT NULL
            GROUP BY DATE(from_time)
        """)

        # Update monthly aggregations
        cur.execute("""
            INSERT OR REPLACE INTO monthly_consumption
            SELECT
                CAST(strftime('%Y', from_time) AS INTEGER) as year,
                CAST(strftime('%m', from_time) AS INTEGER) as month,
                SUM(consumption) as total_consumption,
                SUM(cost) as total_cost,
                AVG(unit_price) as avg_unit_price,
                MAX(currency) as currency
            FROM hourly_consumption
            WHERE consumption IS NOT NULL
            GROUP BY strftime('%Y', from_time), strftime('%m', from_time)
        """)

        con.commit()
        con.close()
        print("📊 Updated daily and monthly aggregations")

    def collect(
        self,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        resolution: str = "HOURLY"
    ) -> List[Dict[str, Any]]:
        """Main collection method: fetch and save data"""
        print("🚀 Starting Tibber data collection")
        print(f"🏠 Home ID: {self.home_id}")

        records = self.fetch_consumption_data(
            since=since,
            until=until,
            resolution=resolution
        )

        self.save_data(records)

        return records


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
        '--db-path',
        default='tibber_data.sqlite',
        help='SQLite database file path'
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
        db_path=args.db_path
    )

    collector.collect(
        since=since,
        until=until,
        resolution=args.resolution
    )


if __name__ == "__main__":
    main()
