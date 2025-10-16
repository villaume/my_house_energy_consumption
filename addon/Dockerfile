ARG BUILD_FROM
FROM $BUILD_FROM

# Install system dependencies
RUN apk add --no-cache \
    python3 \
    py3-pip \
    curl \
    g++ \
    gcc \
    python3-dev \
    musl-dev

# Upgrade pip
RUN pip3 install --break-system-packages --upgrade pip

# Install Python dependencies (only what the API actually needs)
RUN pip3 install --break-system-packages --no-cache-dir \
    fastapi \
    pydantic \
    uvicorn[standard] \
    python-dotenv

# Install duckdb with build tools available
RUN pip3 install --break-system-packages --no-cache-dir duckdb==0.9.2

# Set working directory
WORKDIR /app

# Copy API files
COPY api/ /app/

# Copy run script
COPY run.sh /
RUN chmod a+x /run.sh

# Expose port
EXPOSE 8000

CMD [ "/run.sh" ]
