FROM python:3.11-slim

# Install system dependencies for hardware control, VNC, and NoVNC
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    supervisor \
    nginx \
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
    chromium \
    chromium-driver \
    nano \
    vim \
    dnsutils \
    iputils-ping \
    traceroute \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy shared library
COPY shared/ shared/
# Add shared to PYTHONPATH
ENV PYTHONPATH="/app/shared:/app/shared/src/lib:/app/backend_host/src"

# Copy backend_host requirements and install with exact versions
COPY backend_host/requirements.txt backend_host/
RUN pip install --no-cache-dir -r backend_host/requirements.txt

# Install Playwright WebKit browser and all its system dependencies
RUN playwright install-deps webkit
RUN playwright install webkit

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
    && mkdir -p /var/www/html/stream \
    && mkdir -p /var/log/supervisor \
    && mkdir -p /var/run \
    && mkdir -p /home/vptuser/.android \
    && mkdir -p /app/backend_host/src \
    && touch /app/backend_host/src/.env \
    && chown -R vptuser:vptuser /app \
    && chown -R vptuser:vptuser /var/www \
    && chown -R vptuser:vptuser /home/vptuser \
    && chmod -R 755 /var/www \
    && chmod 644 /app/backend_host/src/.env \
    && chmod +x /app/backend_host/scripts/*.sh || true

# Copy supervisor configuration from docker folder
COPY backend_host/docker/supervisord.conf /etc/supervisor/conf.d/virtualpytest.conf
COPY backend_host/docker/nginx.conf /etc/nginx/sites-available/default

# Copy Docker helper scripts (use absolute path to avoid WORKDIR confusion)
COPY backend_host/docker/scripts/ /app/backend_host/docker/scripts/
RUN chmod +x /app/backend_host/docker/scripts/*.sh

# Expose port 80 for nginx
EXPOSE 80

# Set display and ADB environment
ENV DISPLAY=:1
ENV HOST_VIDEO_SOURCE=:1
ENV ANDROID_HOME=/home/vptuser/.android
ENV ADB_VENDOR_KEYS=/home/vptuser/.android

# Health check for Flask API
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:80/host/system/health || exit 1

# SECURITY NOTE: supervisord runs as root to manage all services
# However, all processes drop privileges to 'vptuser' via supervisord config
USER root

# Use entrypoint script to generate .env and start supervisord
CMD ["/app/backend_host/docker/scripts/entrypoint.sh"]

