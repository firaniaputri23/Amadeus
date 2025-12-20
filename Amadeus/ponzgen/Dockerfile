#MULTI STAGE DOCKER BUILD
# Stage 1: Build the npm package
FROM node:20-alpine AS npm-builder
WORKDIR /build
COPY microservice/mcp_lib/sendgrid_mcp/package*.json ./
COPY microservice/mcp_lib/sendgrid_mcp/ ./
RUN npm run build:docker
# Directory Structure Validation
RUN test -f /build/build/index.js || \
    (echo "Build failed: index.js not found in expected location" && exit 1)

# Stage 2: Main application

FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

# Set working directory
WORKDIR /app

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/root/.cargo/bin:/root/.local/bin:$PATH" \
    SUPABASE_URL="https://ktolhizmsfzrmmhfqvmu.supabase.co" \
    SUPABASE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imt0b2xoaXptc2Z6cm1taGZxdm11Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDIwMjQzMTQsImV4cCI6MjA1NzYwMDMxNH0.pYXSvvyjmXdfoQswk7zMp4G-zJEITYSC5PMnv775TjQ" \
    JWT_SECRET="vc7jKA/JQVnrHr5+k5lDL0R7D37ymUrWGkci58qsgcmKMHIp6xh899PnBh51W2ZpHF1grp2aKHRsFeJ/JY+qFw==" \
    MCP_RUNNER_DIR="/app/microservice/mcp_2/runner_files" \
    MCP_USE_VENV="false" \
    MCP_CHECK_INTERVAL_MINUTES="10"

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    ca-certificates \
    gnupg \
    unzip \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
# Create necessary directories with appropriate permissions
RUN mkdir -p /app/microservice/mcp_2/runner_files/logs /app/microservice/mcp_2/runner_files/envs && \
    chmod -R 777 /app/microservice/mcp_2/runner_files && \
    chmod -R 777 /app/microservice/mcp_2
    
# Install Node.js (includes npx)
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get update && apt-get install -y nodejs && \
    npm install -g npm

# Install uv (Python package manager)
RUN curl -Ls https://astral.sh/uv/install.sh | bash

# Add uv to PATH
ENV PATH="/root/.cargo/bin:$PATH"

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies using pip (or switch to uv if needed)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Copy the built npm package to the exact location
COPY --from=npm-builder /build /app/microservice/mcp_lib/sendgrid_mcp

# Return to main app directory
WORKDIR /app

EXPOSE 8080

# Start app
CMD ["python3", "app.py"]