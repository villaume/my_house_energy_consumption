# Tibber Energy API Add-on

REST API for querying Tibber energy consumption data stored in DuckDB.

## Installation

1. Copy the entire `addon` directory to your Home Assistant:
   ```bash
   scp -r addon username@homeassistant:/addons/tibber_energy_api/
   ```

2. In Home Assistant:
   - Go to **Settings** → **Add-ons** → **Add-on Store**
   - Click **⋮** (three dots menu) → **Check for updates**
   - Find **Tibber Energy API** in the local add-ons
   - Click **Install**

## Configuration

### Options

- **api_key** (optional): Set an API key to enable authentication
- **log_level** (optional): Set logging level (debug, info, warning, error)

### Example Configuration

```yaml
api_key: "your-secret-api-key-here"
log_level: info
```

## Usage

### 1. Prepare the Database

Before starting the add-on, you need to have a DuckDB database file. You have two options:

**Option A: Copy existing database**
```bash
# Copy from your development machine
scp tibber_data.duckdb username@homeassistant:/usr/share/hassio/share/tibber_data.duckdb
```

**Option B: Run collector on Home Assistant**
1. Copy `tibber_collector.py` to Home Assistant
2. Install Python dependencies
3. Run the collector to create the database

### 2. Start the Add-on

1. Go to **Settings** → **Add-ons** → **Tibber Energy API**
2. Configure the API key (optional but recommended)
3. Click **Start**
4. Enable **Start on boot** and **Watchdog**

### 3. Check Logs

Click on the **Log** tab to see if the API started successfully.

You should see:
```
Starting Tibber Energy API...
Database path: /share/tibber_data.duckdb
```

## Accessing the API

The API will be available at:
- **From Home Assistant**: `http://homeassistant.local:8000`
- **From your network**: `http://your-ha-ip:8000`
- **API Documentation**: `http://your-ha-ip:8000/docs`

## Home Assistant Integration

Add REST sensors to your `configuration.yaml`:

```yaml
sensor:
  - platform: rest
    resource: http://homeassistant.local:8000/api/latest
    headers:
      X-API-Key: your-secret-api-key  # Remove if no API key
    name: "Energy Consumption"
    value_template: "{{ value_json.consumption }}"
    unit_of_measurement: "kWh"
    scan_interval: 3600
```

See `home_assistant_example.yaml` for more examples.

## API Endpoints

- `GET /` - API information
- `GET /health` - Health check (always public)
- `GET /api/stats` - Overall statistics
- `GET /api/latest` - Most recent reading
- `GET /api/hourly` - Hourly data
- `GET /api/daily` - Daily aggregations
- `GET /api/monthly` - Monthly aggregations

All `/api/*` endpoints require authentication if `api_key` is set.

## Database Location

The database is stored at `/share/tibber_data.duckdb` which maps to:
- `/usr/share/hassio/share/tibber_data.duckdb` on the host

This location is persistent across restarts and accessible from other add-ons.

## Updating Data

To update the data, you'll need to run `tibber_collector.py` periodically. Options:

1. **Manual**: SSH and run the collector script
2. **Automation**: Create a Home Assistant automation to trigger collection
3. **Separate Add-on**: Create a companion collector add-on (advanced)

## Troubleshooting

### Add-on won't start

1. Check the logs for errors
2. Verify the database file exists at `/share/tibber_data.duckdb`
3. Check permissions on the database file

### Database not found

Copy your database file to the correct location:
```bash
scp tibber_data.duckdb user@homeassistant:/usr/share/hassio/share/
```

### API returns 401 errors

- Verify your API key is correct
- Check the add-on configuration
- Try accessing without the X-API-Key header (if no key is set)

### Can't access from Home Assistant

Use `http://homeassistant.local:8000` or `http://localhost:8000` instead of an IP address.

## Support

For issues and questions:
- Check the add-on logs
- See full documentation in the main repository
- Open an issue on GitHub
