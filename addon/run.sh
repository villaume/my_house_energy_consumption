#!/usr/bin/env bash
set -e

# Set environment variables
export DATABASE_PATH="/share/tibber_data.sqlite"

# Get configuration from options
CONFIG_PATH="/data/options.json"
if [ -f "$CONFIG_PATH" ]; then
    API_KEY=$(jq -r '.api_key // empty' $CONFIG_PATH)
    LOG_LEVEL=$(jq -r '.log_level // "info"' $CONFIG_PATH)
else
    API_KEY=""
    LOG_LEVEL="info"
fi

if [ -n "$API_KEY" ]; then
    echo "[INFO] API key authentication enabled"
    export API_KEY="$API_KEY"
else
    echo "[WARN] API key not set - API will be open to all requests"
fi

# Log configuration
echo "[INFO] Starting Tibber Energy API..."
echo "[INFO] Database path: ${DATABASE_PATH}"
echo "[INFO] Log level: ${LOG_LEVEL}"

# Check if database exists
if [ ! -f "$DATABASE_PATH" ]; then
    echo "[WARN] Database not found at ${DATABASE_PATH}"
    echo "[WARN] Please copy tibber_data.sqlite to /share/"
fi

# Start the API
cd /app
exec python3 -m uvicorn main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --log-level ${LOG_LEVEL}
