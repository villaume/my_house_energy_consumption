# Security Guide

## API Key Authentication

The API now supports optional API key authentication to protect your energy data.

## How It Works

- **Without API_KEY set**: API is open to anyone (backwards compatible)
- **With API_KEY set**: All `/api/*` endpoints require authentication
- **Public endpoints**: `/` and `/health` are always accessible

## Setup

### 1. Generate a Secure API Key

```bash
# Generate a random 32-character hex key
openssl rand -hex 32
```

Example output: `a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2`

### 2. Set the API Key

#### For Docker Compose

Edit `docker-compose.yml`:

```yaml
environment:
  - DATABASE_PATH=/data/tibber_data.duckdb
  - API_KEY=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2
```

Restart:
```bash
docker-compose down
docker-compose up -d
```

#### For Local Development

```bash
# Start with API key
cd api
API_KEY=your-secret-key DATABASE_PATH=../tibber_data.duckdb uvicorn main:app --host 0.0.0.0 --port 8000
```

Or use the helper script (edit to add API_KEY):
```bash
./start_api.sh
```

#### For Systemd Service

Edit your systemd service file:

```ini
[Service]
Environment="API_KEY=your-secret-key"
Environment="DATABASE_PATH=/path/to/tibber_data.duckdb"
```

Reload:
```bash
sudo systemctl daemon-reload
sudo systemctl restart tibber-api
```

### 3. Using the API with Authentication

#### cURL

```bash
# Without key (will fail if authentication is enabled)
curl http://localhost:8000/api/stats

# With key
curl -H "X-API-Key: your-secret-key" http://localhost:8000/api/stats
```

#### Python

```python
import requests

headers = {"X-API-Key": "your-secret-key"}
response = requests.get("http://localhost:8000/api/stats", headers=headers)
print(response.json())
```

#### JavaScript

```javascript
fetch('http://localhost:8000/api/stats', {
  headers: {
    'X-API-Key': 'your-secret-key'
  }
})
  .then(response => response.json())
  .then(data => console.log(data));
```

#### Home Assistant REST Sensor

```yaml
sensor:
  - platform: rest
    resource: http://localhost:8000/api/latest
    headers:
      X-API-Key: your-secret-key
    name: "Current Energy Consumption"
    value_template: "{{ value_json.consumption }}"
    unit_of_measurement: "kWh"
```

## Testing Authentication

### Test Without Key (should fail)
```bash
curl http://localhost:8000/api/stats
# Response: {"detail":"Invalid or missing API key. Include X-API-Key header."}
```

### Test With Wrong Key (should fail)
```bash
curl -H "X-API-Key: wrong-key" http://localhost:8000/api/stats
# Response: {"detail":"Invalid or missing API key. Include X-API-Key header."}
```

### Test With Correct Key (should succeed)
```bash
curl -H "X-API-Key: your-secret-key" http://localhost:8000/api/stats
# Response: {"total_records": 10244, ...}
```

### Test Public Endpoints (should always work)
```bash
curl http://localhost:8000/
curl http://localhost:8000/health
```

## OpenAPI Documentation

When authentication is enabled, you can still access the interactive docs at:

**http://localhost:8000/docs**

Use the "Authorize" button (🔒) to enter your API key for testing.

## Security Best Practices

### 1. Keep Your API Key Secret
- **Never commit** API keys to git
- Use environment variables, not hardcoded values
- Rotate keys periodically

### 2. Use HTTPS in Production
```bash
# With a reverse proxy (nginx, caddy, traefik)
# Your API key will be encrypted in transit
```

### 3. Network Security

**Local Network Only (Most Secure)**
```yaml
# docker-compose.yml
ports:
  - "127.0.0.1:8000:8000"  # Only accessible from localhost
```

**Home Network Only**
- Don't expose port 8000 to the internet
- Access remotely via VPN or Nabu Casa

**If Exposing to Internet**
- Use HTTPS (required!)
- Use a strong API key (32+ characters)
- Consider rate limiting
- Monitor access logs

### 4. Multiple API Keys (Advanced)

If you need different keys for different users/services, modify `api/main.py`:

```python
VALID_API_KEYS = set([
    os.getenv('API_KEY_ADMIN'),
    os.getenv('API_KEY_HOME_ASSISTANT'),
    os.getenv('API_KEY_GRAFANA'),
])

def verify_api_key(api_key: Optional[str] = Depends(api_key_header)) -> None:
    if not VALID_API_KEYS:
        return  # No keys set, allow all

    if api_key not in VALID_API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid API key")
```

## Disabling Authentication

To run without authentication (not recommended for internet-facing deployments):

**Don't set the `API_KEY` environment variable**

```yaml
# docker-compose.yml
environment:
  - DATABASE_PATH=/data/tibber_data.duckdb
  # No API_KEY = no authentication
```

## Troubleshooting

### "Invalid or missing API key" error

1. Check that your API key matches exactly (no spaces)
2. Verify the header name is `X-API-Key` (case-sensitive)
3. Check if API_KEY environment variable is actually set

### Can't access API at all

1. Check the API is running: `curl http://localhost:8000/health`
2. If health check fails, check logs: `docker-compose logs tibber-api`
3. Verify port 8000 is not blocked by firewall

### API key working locally but not from Home Assistant

1. Check network connectivity: `ping <api-host>`
2. Verify the API key in HA configuration
3. Check HA logs for detailed error messages

## Example: Complete Docker Setup with Security

```yaml
version: '3.8'

services:
  tibber-api:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: tibber-energy-api
    restart: unless-stopped
    ports:
      - "127.0.0.1:8000:8000"  # Only accessible from localhost
    volumes:
      - ./tibber_data.duckdb:/data/tibber_data.duckdb:ro  # Read-only
    environment:
      - DATABASE_PATH=/data/tibber_data.duckdb
      - API_KEY=${API_KEY}  # Load from .env file
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

Create a `.env` file (add to .gitignore!):
```bash
API_KEY=your-secret-key-here
```

## Questions?

- Check logs: `docker-compose logs -f tibber-api`
- Test authentication: See "Testing Authentication" section above
- API documentation: http://localhost:8000/docs
