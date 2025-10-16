#!/usr/bin/with-contenv bashio

# Get configuration
API_KEY=$(bashio::config 'api_key')
LOG_LEVEL=$(bashio::config 'log_level')

# Set environment variables
export DATABASE_PATH="/share/tibber_data.duckdb"

if [ -n "$API_KEY" ]; then
    bashio::log.info "API key authentication enabled"
    export API_KEY="$API_KEY"
else
    bashio::log.warning "API key not set - API will be open to all requests"
fi

# Log configuration
bashio::log.info "Starting Tibber Energy API..."
bashio::log.info "Database path: ${DATABASE_PATH}"
bashio::log.info "Log level: ${LOG_LEVEL}"

# Check if database exists
if [ ! -f "$DATABASE_PATH" ]; then
    bashio::log.warning "Database not found at ${DATABASE_PATH}"
    bashio::log.warning "Please run tibber_collector.py to create the database"
    bashio::log.info "You can copy an existing database to /share/tibber_data.duckdb"
fi

# Start the API
cd /app
exec python3 -m uvicorn main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --log-level ${LOG_LEVEL}
