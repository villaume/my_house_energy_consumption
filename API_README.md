# Tibber Energy Consumption API

A FastAPI-based REST API for querying Tibber energy consumption data stored in DuckDB.

## Features

- **Hourly, Daily, and Monthly** aggregated consumption data
- **RESTful API** with automatic OpenAPI documentation
- **DuckDB backend** for efficient analytics queries
- **Docker support** for easy deployment
- **Automatic data aggregation** when new data is collected
- **Deduplication** of hourly records
- **Optional API Key authentication** for security (see SECURITY.md)

## Quick Start

### 1. Migrate Existing CSV Data (Optional)

If you have existing CSV data, first migrate it to DuckDB:

```bash
# This will create a new DuckDB database and import your CSV data
python migrate_csv_to_duckdb.py
```

### 2. Collect Initial Data

```bash
# Make sure your .env file has TIBBER_TOKEN set
uv run tibber_collector.py --db-path tibber_data.duckdb
```

### 3. Run the API Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run the API
cd api
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Visit http://localhost:8000/docs for interactive API documentation.

### 4. Run with Docker Compose

```bash
# Build and start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## API Endpoints

### Health & Info

- `GET /` - API information
- `GET /health` - Health check

### Consumption Data

- `GET /api/hourly?start_date=2024-01-01&end_date=2024-12-31&limit=100`
  - Get hourly consumption data
  - Parameters: `start_date`, `end_date`, `limit` (default: 100)

- `GET /api/daily?start_date=2024-01-01&end_date=2024-12-31&limit=365`
  - Get daily aggregated data
  - Parameters: `start_date`, `end_date`, `limit` (default: 365)

- `GET /api/daily/{date}`
  - Get consumption for specific date
  - Example: `/api/daily/2024-10-15`

- `GET /api/monthly?year=2024&limit=24`
  - Get monthly aggregated data
  - Parameters: `year`, `limit` (default: 24)

- `GET /api/monthly/{year}/{month}`
  - Get consumption for specific month
  - Example: `/api/monthly/2024/10`

- `GET /api/latest`
  - Get the most recent hourly consumption record

- `GET /api/stats`
  - Get overall statistics (total records, date range, total consumption, etc.)

## Example Responses

### GET /api/latest

```json
{
  "from_time": "2024-10-15T17:00:00+02:00",
  "to_time": "2024-10-15T18:00:00+02:00",
  "consumption": 2.657,
  "consumption_unit": "kWh",
  "cost": 4.886223,
  "unit_price": 1.839,
  "unit_price_vat": 0.415545,
  "currency": "SEK"
}
```

### GET /api/daily/2024-10-15

```json
{
  "date": "2024-10-15",
  "total_consumption": 15.234,
  "total_cost": 42.56,
  "avg_unit_price": 2.15,
  "currency": "SEK"
}
```

### GET /api/stats

```json
{
  "total_records": 10243,
  "date_range_start": "2024-08-15T00:00:00+02:00",
  "date_range_end": "2024-10-15T18:00:00+02:00",
  "total_consumption_kwh": 2345.67,
  "total_cost": 6543.21,
  "currency": "SEK"
}
```

## Database Schema

### hourly_consumption
- `from_time` - Start timestamp (with timezone)
- `to_time` - End timestamp (with timezone)
- `consumption` - Energy consumption (kWh)
- `consumption_unit` - Unit (typically "kWh")
- `cost` - Total cost
- `unit_price` - Price per kWh
- `unit_price_vat` - VAT amount
- `currency` - Currency code (e.g., "SEK")

### daily_consumption (auto-generated)
- `date` - Date
- `total_consumption` - Sum of hourly consumption
- `total_cost` - Sum of hourly costs
- `avg_unit_price` - Average price per kWh
- `currency` - Currency code

### monthly_consumption (auto-generated)
- `year` - Year
- `month` - Month (1-12)
- `total_consumption` - Sum of hourly consumption
- `total_cost` - Sum of hourly costs
- `avg_unit_price` - Average price per kWh
- `currency` - Currency code

## Deployment on Home Assistant

### Option 1: Docker Compose (Recommended)

1. Copy files to your Home Assistant host:
```bash
scp -r . homeassistant:/path/to/tibber-api/
```

2. SSH into your Home Assistant host and start the services:
```bash
cd /path/to/tibber-api/
docker-compose up -d
```

### Option 2: Systemd Service

Create `/etc/systemd/system/tibber-api.service`:

```ini
[Unit]
Description=Tibber Energy API
After=network.target

[Service]
Type=simple
User=homeassistant
WorkingDirectory=/path/to/tibber-api/api
Environment="DATABASE_PATH=/path/to/tibber_data.duckdb"
ExecStart=/usr/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable tibber-api
sudo systemctl start tibber-api
```

### Option 3: Home Assistant Add-on

Create a custom add-on (requires add-on development setup).

## Scheduled Data Collection

### With Docker Compose

The `tibber-collector` service runs automatically every hour.

### With Cron

Add to crontab:
```bash
0 * * * * cd /path/to/project && /usr/bin/python tibber_collector.py --db-path tibber_data.duckdb
```

### With Systemd Timer

Create `/etc/systemd/system/tibber-collector.timer`:

```ini
[Unit]
Description=Tibber Data Collector Timer

[Timer]
OnCalendar=hourly
Persistent=true

[Install]
WantedBy=timers.target
```

Create `/etc/systemd/system/tibber-collector.service`:

```ini
[Unit]
Description=Tibber Data Collector

[Service]
Type=oneshot
WorkingDirectory=/path/to/project
ExecStart=/usr/bin/python tibber_collector.py --db-path tibber_data.duckdb
```

Enable:
```bash
sudo systemctl enable tibber-collector.timer
sudo systemctl start tibber-collector.timer
```

## Environment Variables

- `TIBBER_TOKEN` - Your Tibber API token (required for collector)
- `TIBBER_HOME_ID` - Your Tibber home ID (auto-detected if not set)
- `DATABASE_PATH` - Path to DuckDB database file
- `API_KEY` - Optional API key for authentication (see SECURITY.md)

## Security

The API supports optional API key authentication. See **SECURITY.md** for detailed setup instructions.

**Quick setup:**
```bash
# Generate a key
openssl rand -hex 32

# Set in docker-compose.yml
environment:
  - API_KEY=your-generated-key

# Use in requests
curl -H "X-API-Key: your-generated-key" http://localhost:8000/api/stats
```

## Development

### Run Tests

```bash
# Install dev dependencies
pip install pytest httpx

# Run tests (TODO: create tests)
pytest
```

### Access Database Directly

```bash
# Install DuckDB CLI
# macOS: brew install duckdb
# Linux: Download from duckdb.org

# Connect to database
duckdb tibber_data.duckdb

# Query data
SELECT * FROM daily_consumption ORDER BY date DESC LIMIT 10;
```

## Troubleshooting

### Database locked error
- DuckDB doesn't support concurrent writes well
- Make sure only one collector instance is running
- The API opens connections in read-only mode

### No data in aggregation tables
- Run the collector at least once to populate data
- Aggregations are updated automatically when new data is collected

### API returns 500 error
- Check that the database file exists and is readable
- Verify DATABASE_PATH environment variable is correct
- Check API logs: `docker-compose logs tibber-api`

## Cost Estimation

Running on a Raspberry Pi or similar:
- **Storage**: ~10MB for 1 year of hourly data
- **Memory**: ~100MB for API + DuckDB
- **CPU**: Minimal (queries are very fast)
- **Network**: ~1 API call per hour to Tibber

**Total cost**: Essentially free if you already have the hardware!

## Future Enhancements

- [ ] Add authentication/API keys
- [ ] Real-time updates via WebSocket
- [ ] Export to CSV/JSON
- [ ] Grafana dashboard integration
- [ ] Alerts for high consumption
- [ ] Price forecasting
- [ ] Comparison with historical averages

## License

MIT
