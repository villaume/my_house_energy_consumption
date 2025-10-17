# Use Python Alpine base instead of Home Assistant base
FROM python:3.11-alpine

# Install system dependencies
RUN apk add --no-cache \
    curl

# Upgrade pip
RUN pip install --upgrade pip

# Install Python dependencies (only what the API actually needs)
# SQLite is included with Python, no need to install separately
RUN pip install --no-cache-dir \
    fastapi \
    pydantic \
    uvicorn[standard] \
    python-dotenv

# Set working directory
WORKDIR /app

# Copy API files
COPY api/ /app/

# Copy and setup entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Set environment variables
ENV DATABASE_PATH=/share/tibber_data.sqlite

# Expose port
EXPOSE 8000

# Use entrypoint script
CMD ["/entrypoint.sh"]
