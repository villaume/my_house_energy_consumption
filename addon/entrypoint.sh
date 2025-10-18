#!/bin/sh
set -e

# Read configuration from Home Assistant
CONFIG_PATH="/data/options.json"

if [ -f "$CONFIG_PATH" ]; then
    # Extract configuration values
    API_KEY=$(cat $CONFIG_PATH | grep -o '"api_key"[[:space:]]*:[[:space:]]*"[^"]*"' | sed 's/.*"\([^"]*\)"/\1/')
    LOG_LEVEL=$(cat $CONFIG_PATH | grep -o '"log_level"[[:space:]]*:[[:space:]]*"[^"]*"' | sed 's/.*"\([^"]*\)"/\1/')
    TIBBER_TOKEN=$(cat $CONFIG_PATH | grep -o '"tibber_token"[[:space:]]*:[[:space:]]*"[^"]*"' | sed 's/.*"\([^"]*\)"/\1/')
    TIBBER_HOME_ID=$(cat $CONFIG_PATH | grep -o '"tibber_home_id"[[:space:]]*:[[:space:]]*"[^"]*"' | sed 's/.*"\([^"]*\)"/\1/')

    # Export API key for FastAPI
    if [ -n "$API_KEY" ] && [ "$API_KEY" != "" ]; then
        export API_KEY="$API_KEY"
        echo "[INFO] API key authentication enabled"
    else
        echo "[WARN] No API key configured - API is open"
    fi

    # Export Tibber credentials
    if [ -n "$TIBBER_TOKEN" ] && [ "$TIBBER_TOKEN" != "" ]; then
        export TIBBER_TOKEN="$TIBBER_TOKEN"
        echo "[INFO] Tibber token configured"
    else
        echo "[WARN] No Tibber token configured"
    fi

    if [ -n "$TIBBER_HOME_ID" ] && [ "$TIBBER_HOME_ID" != "" ]; then
        export TIBBER_HOME_ID="$TIBBER_HOME_ID"
        echo "[INFO] Tibber home ID configured"
    fi

    if [ -z "$LOG_LEVEL" ]; then
        LOG_LEVEL="info"
    fi
else
    echo "[WARN] No config file found at $CONFIG_PATH"
    LOG_LEVEL="info"
fi

# Set database path
export DATABASE_PATH="/share/tibber_data.sqlite"

echo "[INFO] Starting Tibber Energy API..."
echo "[INFO] Database: $DATABASE_PATH"
echo "[INFO] Log level: $LOG_LEVEL"

# Start uvicorn
cd /app
exec python3 -m uvicorn main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --log-level ${LOG_LEVEL}
