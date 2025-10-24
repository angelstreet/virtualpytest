FROM python:3.11-slim

# Install system dependencies for hardware control, VNC, and NoVNC
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    supervisor \
    xvfb \
    x11-utils \
    x11vnc \
    novnc \
    websockify \
    fluxbox \
    xterm \
    scrot \
    python3-tk \
    python3-dev \
    libopencv-dev \
    ffmpeg \
    gcc \
    g++ \
    make \
    build-essential \
    linux-libc-dev \
    android-tools-adb \
    libpq-dev \
    libpq5 \
    libgl1-mesa-dri \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy shared library
COPY shared/ shared/
# Add shared to PYTHONPATH
ENV PYTHONPATH="/app/shared:/app/shared/src/lib:/app/backend_host/src"

# Copy backend_host requirements and install with exact versions (no cache)
COPY backend_host/requirements.txt backend_host/
RUN pip install --no-cache-dir --force-reinstall -r backend_host/requirements.txt

# Copy backend_host source
COPY backend_host/src/ backend_host/src/

# Copy backend_host scripts
COPY backend_host/scripts/ backend_host/scripts/

# Copy backend_host configuration
COPY backend_host/config/ backend_host/config/

# Set working directory to backend_host
WORKDIR /app/backend_host

# Create non-root user for security
RUN useradd -m -u 1000 vptuser

# Create directories and set proper permissions
RUN mkdir -p /var/www/html \
    && mkdir -p /var/log/supervisor \
    && mkdir -p /var/run \
    && chown -R vptuser:vptuser /app \
    && chown -R vptuser:vptuser /var/www \
    && chmod -R 755 /var/www \
    && chmod +x /app/backend_host/scripts/*.sh || true

# Copy supervisor configuration from docker folder
COPY backend_host/docker/supervisord.conf /etc/supervisor/conf.d/virtualpytest.conf

# Expose ports for Flask and NoVNC
EXPOSE 6109 6080

# Set display environment
ENV DISPLAY=:99

# Health check for Flask API
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:6109/host/health || exit 1

# SECURITY NOTE: supervisord runs as root to manage all services
# However, all processes drop privileges to 'vptuser' via supervisord config
USER root

# Run supervisor to manage Xvfb, x11vnc, NoVNC, and Flask
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/supervisord.conf", "-n"]

