# Quick Reference Card

## 🔐 Enable Authentication

```bash
# 1. Generate key
openssl rand -hex 32

# 2. Edit docker-compose.yml
environment:
  - API_KEY=your-key-here

# 3. Restart
docker-compose restart tibber-api
```

## 📡 API Usage

### Without Authentication
```bash
curl http://localhost:8000/api/stats
```

### With Authentication
```bash
curl -H "X-API-Key: your-key" http://localhost:8000/api/stats
```

## 🏠 Home Assistant Integration

### REST Sensor (No Auth)
```yaml
sensor:
  - platform: rest
    resource: http://localhost:8000/api/latest
    name: "Energy Consumption"
    value_template: "{{ value_json.consumption }}"
    unit_of_measurement: "kWh"
```

### REST Sensor (With Auth)
```yaml
sensor:
  - platform: rest
    resource: http://localhost:8000/api/latest
    headers:
      X-API-Key: your-secret-key
    name: "Energy Consumption"
    value_template: "{{ value_json.consumption }}"
    unit_of_measurement: "kWh"
```

## 🚀 Common Commands

### Start API Locally
```bash
./start_api.sh
# OR
cd api && DATABASE_PATH=../tibber_data.duckdb uvicorn main:app --reload
```

### Start with Authentication
```bash
cd api
API_KEY=your-key DATABASE_PATH=../tibber_data.duckdb uvicorn main:app
```

### Run Collector
```bash
uv run python tibber_collector.py --db-path tibber_data.duckdb
```

### Docker Commands
```bash
# Start everything
docker-compose up -d

# View logs
docker-compose logs -f

# Restart API only
docker-compose restart tibber-api

# Stop everything
docker-compose down
```

## 📊 API Endpoints

| Endpoint | Description | Auth Required |
|----------|-------------|---------------|
| `GET /` | API info | ❌ No |
| `GET /health` | Health check | ❌ No |
| `GET /api/stats` | Overall statistics | ✅ Yes |
| `GET /api/latest` | Latest reading | ✅ Yes |
| `GET /api/hourly` | Hourly data | ✅ Yes |
| `GET /api/daily` | Daily data | ✅ Yes |
| `GET /api/daily/{date}` | Specific date | ✅ Yes |
| `GET /api/monthly` | Monthly data | ✅ Yes |
| `GET /api/monthly/{year}/{month}` | Specific month | ✅ Yes |

## 🔍 Testing

### Test Public Endpoints
```bash
curl http://localhost:8000/
curl http://localhost:8000/health
```

### Test Protected Endpoints
```bash
# Should fail
curl http://localhost:8000/api/stats

# Should succeed
curl -H "X-API-Key: your-key" http://localhost:8000/api/stats
```

## 🐛 Troubleshooting

### API not responding
```bash
# Check if running
curl http://localhost:8000/health

# Check logs
docker-compose logs tibber-api
```

### Authentication failing
```bash
# Verify API key is set
docker-compose config | grep API_KEY

# Test with correct key
curl -H "X-API-Key: $(grep API_KEY docker-compose.yml | cut -d: -f2 | xargs)" \
  http://localhost:8000/api/stats
```

### Database locked
```bash
# Only one collector should run at a time
# Stop any running collectors
pkill -f tibber_collector

# Run collector
uv run python tibber_collector.py
```

## 📁 Important Files

| File | Purpose |
|------|---------|
| `api/main.py` | API application |
| `tibber_collector.py` | Data collector |
| `tibber_data.duckdb` | Database (gitignored) |
| `docker-compose.yml` | Docker configuration |
| `.env` | Environment variables |
| `SECURITY.md` | Security documentation |
| `API_README.md` | Full API documentation |

## 🔗 URLs

- **API Docs**: http://localhost:8000/docs
- **OpenAPI Schema**: http://localhost:8000/openapi.json
- **Health Check**: http://localhost:8000/health

## ⚙️ Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `API_KEY` | No | None | Enable authentication |
| `DATABASE_PATH` | No | `../tibber_data.duckdb` | Database location |
| `TIBBER_TOKEN` | Yes (collector) | None | Tibber API token |
| `TIBBER_HOME_ID` | No | Auto-detect | Tibber home ID |

## 📚 Documentation

- **SECURITY.md** - Authentication setup
- **API_README.md** - Complete API guide
- **SETUP_SUMMARY.md** - Setup overview
- **QUICK_REFERENCE.md** - This file!
