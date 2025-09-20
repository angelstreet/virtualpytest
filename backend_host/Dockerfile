FROM python:3.11-slim

# Install system dependencies for hardware control and NoVNC
RUN apt-get update && apt-get install -y \
    xvfb \
    x11-utils \
    scrot \
    python3-tk \
    python3-dev \
    libopencv-dev \
    ffmpeg \
    curl \
    wget \
    gcc \
    g++ \
    make \
    build-essential \
    linux-libc-dev \
    novnc \
    websockify \
    x11vnc \
    fluxbox \
    xterm \
    android-tools-adb \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy shared library and backend_host
COPY shared/ shared/
COPY backend_host/ backend_host/

# Add shared and backend_host to PYTHONPATH instead of installing as packages
ENV PYTHONPATH="/app/shared:/app/shared/lib:/app/backend_host/src"

# Copy backend_host requirements and install
COPY backend_host/requirements.txt backend_host/
RUN pip install --no-cache-dir -r backend_host/requirements.txt

# Copy backend_host source
COPY backend_host/src/ backend_host/src/

# Copy the env.example as default .env if no .env exists
RUN if [ ! -f /app/backend_host/src/.env ]; then \
        if [ -f /app/backend_host/src/env.example ]; then \
            cp /app/backend_host/src/env.example /app/backend_host/src/.env; \
        else \
            echo "# Docker default environment" > /app/backend_host/src/.env && \
            echo "HOST_NAME=docker-host" >> /app/backend_host/src/.env && \
            echo "HOST_PORT=6109" >> /app/backend_host/src/.env && \
            echo "HOST_URL=http://localhost:6109" >> /app/backend_host/src/.env && \
            echo "SERVER_URL=http://localhost:5109" >> /app/backend_host/src/.env && \
            echo "DEBUG=false" >> /app/backend_host/src/.env; \
        fi; \
    fi

# Copy utils directory (if it exists in project root)
# Note: This copy is optional and will be skipped if src/utils/ doesn't exist

# Set working directory to backend_host
WORKDIR /app/backend_host

# Copy service orchestration scripts
COPY backend_host/scripts/generate_services_config.sh /app/backend_host/scripts/
COPY backend_host/scripts/start_services.sh /app/backend_host/scripts/
COPY backend_host/scripts/run_ffmpeg_and_rename_docker.sh /app/backend_host/scripts/

# Make scripts executable (before switching to non-root user)
RUN chmod +x /app/backend_host/scripts/generate_services_config.sh && \
    chmod +x /app/backend_host/scripts/start_services.sh && \
    chmod +x /app/backend_host/scripts/run_ffmpeg_and_rename_docker.sh

# Create /var/www directory structure and set permissions
RUN mkdir -p /var/www/html && chmod 755 /var/www/html

# Create non-root user for security
RUN useradd -m -u 1000 vptuser && chown -R vptuser:vptuser /app /var/www

# Expose ports
EXPOSE 6109 6080

# Set display environment
ENV DISPLAY=:99

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:6109/host/health || exit 1

# Switch to non-root user
USER vptuser

# Run the clean service orchestrator
CMD ["/app/backend_host/scripts/start_services.sh"] 