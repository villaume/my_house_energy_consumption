#!/bin/sh
set -e

# Read configuration from Home Assistant
CONFIG_PATH="/data/options.json"

if [ -f "$CONFIG_PATH" ]; then
    # Extract API key from config
    API_KEY=$(cat $CONFIG_PATH | grep -o '"api_key"[[:space:]]*:[[:space:]]*"[^"]*"' | sed 's/.*"\([^"]*\)"/\1/')
    LOG_LEVEL=$(cat $CONFIG_PATH | grep -o '"log_level"[[:space:]]*:[[:space:]]*"[^"]*"' | sed 's/.*"\([^"]*\)"/\1/')

    if [ -n "$API_KEY" ] && [ "$API_KEY" != "" ]; then
        export API_KEY="$API_KEY"
        echo "[INFO] API key authentication enabled"
    else
        echo "[WARN] No API key configured - API is open"
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
