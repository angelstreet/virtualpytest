FROM python:3.11-slim

# Install system dependencies including nginx and Grafana
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    gnupg2 \
    nginx \
    supervisor \
    postgresql-client \
    libpq-dev \
    libpq5 \
    libgl1-mesa-dri \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    xvfb \
    nano \
    vim \
    && rm -rf /var/lib/apt/lists/*

# Install Grafana
RUN wget -q -O /usr/share/keyrings/grafana.key https://apt.grafana.com/gpg.key \
    && echo "deb [signed-by=/usr/share/keyrings/grafana.key] https://apt.grafana.com stable main" | tee -a /etc/apt/sources.list.d/grafana.list \
    && apt-get update \
    && apt-get install -y grafana \
    && rm -rf /var/lib/apt/lists/*

# Install Grafana plugins
RUN grafana-cli plugins install marcusolsson-gantt-panel \
    && grafana-cli plugins install volkovlabs-echarts-panel

WORKDIR /app

# Copy shared library
COPY shared/ shared/
# Add shared to PYTHONPATH
ENV PYTHONPATH="/app/shared:/app/shared/src/lib:/app/backend_server/src"

# Copy backend_server requirements and install with exact versions (no cache)
COPY backend_server/requirements.txt backend_server/
RUN pip install --no-cache-dir --force-reinstall -r backend_server/requirements.txt

# Copy backend_server source
COPY backend_server/src/ backend_server/src/

# Copy backend_server scripts
COPY backend_server/scripts/ backend_server/scripts/

# Copy backend_server configuration
COPY backend_server/config/ backend_server/config/

# Copy nginx configuration for Render
COPY backend_server/config/nginx/render.conf /etc/nginx/sites-available/default

# Copy separate Grafana configuration to expected location
COPY grafana/config/ backend_server/config/grafana/
COPY grafana/dashboards/ backend_server/config/grafana/dashboards/
COPY grafana/data/ backend_server/config/grafana/data/

# Set working directory to backend_server
WORKDIR /app/backend_server

# Create non-root user for security
RUN useradd -m -u 1000 vptuser

# Create directories for Grafana and set proper permissions
RUN mkdir -p /var/lib/grafana /var/log/grafana /etc/grafana \
    && mkdir -p /app/backend_server/config/grafana/provisioning/{datasources,dashboards} \
    && mkdir -p /app/backend_server/config/grafana/dashboards \
    && mkdir -p /app/backend_server/config/grafana/data/{png,csv,sessions,plugins} \
    && mkdir -p /var/log/supervisor \
    && mkdir -p /usr/share/grafana/data/plugins \
    && mkdir -p /var/lib/grafana/plugins \
    && mkdir -p /var/log/nginx \
    && mkdir -p /var/lib/nginx \
    && chown -R vptuser:vptuser /app \
    && chown -R vptuser:vptuser /var/lib/grafana \
    && chown -R vptuser:vptuser /var/log/grafana \
    && chown -R vptuser:vptuser /etc/grafana \
    && chown -R vptuser:vptuser /usr/share/grafana/data/plugins \
    && chown -R vptuser:vptuser /var/lib/grafana/plugins \
    && chown -R www-data:www-data /var/log/nginx \
    && chown -R www-data:www-data /var/lib/nginx \
    && chmod -R 755 /usr/share/grafana/data/plugins \
    && chmod -R 755 /var/lib/grafana/plugins \
    && chmod -R 775 /var/lib/grafana \
    && chmod -R 775 /app/backend_server/config/grafana \
    && chmod -R 755 /var/log/grafana \
    && chmod -R 755 /var/log/nginx \
    && chmod -R 755 /var/lib/nginx \
    && chmod 1777 /tmp

# Copy supervisor configuration (with nginx) from docker folder
COPY backend_server/docker/supervisord.conf /etc/supervisor/conf.d/virtualpytest.conf

# Copy and set permissions for Grafana datasource setup script
COPY backend_server/docker/scripts/setup_grafana_datasource.sh /app/backend_server/docker/scripts/
RUN chmod +x /app/backend_server/docker/scripts/setup_grafana_datasource.sh

# Expose ports for Flask and Grafana
EXPOSE 5109 3000

# Health check for Flask API
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:5109/health || exit 1

# SECURITY NOTE: supervisord runs as root to manage nginx (which needs root)
# However, Flask and Grafana processes drop privileges to 'vptuser' via supervisord config
USER root

# Run supervisor to manage nginx, Flask and Grafana
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/supervisord.conf", "-n"] 