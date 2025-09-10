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
    && rm -rf /var/lib/apt/lists/*

# Install Grafana
RUN wget -q -O /usr/share/keyrings/grafana.key https://apt.grafana.com/gpg.key \
    && echo "deb [signed-by=/usr/share/keyrings/grafana.key] https://apt.grafana.com stable main" | tee -a /etc/apt/sources.list.d/grafana.list \
    && apt-get update \
    && apt-get install -y grafana \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy shared library
COPY shared/ shared/
# Add shared to PYTHONPATH instead of installing as package
ENV PYTHONPATH="/app/shared:/app/shared/lib:/app/backend_core/src"

# Copy backend_core (required dependency)
COPY backend_core/ backend_core/

# Copy backend_server requirements and install
COPY backend_server/requirements.txt backend_server/
RUN pip install --no-cache-dir -r backend_server/requirements.txt

# Copy backend_server source
COPY backend_server/src/ backend_server/src/

# Copy backend_server configuration
COPY backend_server/config/ backend_server/config/

# Copy nginx configuration for Render
COPY backend_server/config/nginx/render.conf /etc/nginx/sites-available/default

# Copy separate Grafana configuration to expected location
COPY grafana/config/ backend_server/config/grafana/
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
    && chown -R vptuser:vptuser /app \
    && chown -R vptuser:vptuser /var/lib/grafana \
    && chown -R vptuser:vptuser /var/log/grafana \
    && chown -R vptuser:vptuser /etc/grafana \
    && chown -R vptuser:vptuser /usr/share/grafana/data/plugins \
    && chown -R vptuser:vptuser /var/lib/grafana/plugins \
    && chmod -R 755 /usr/share/grafana/data/plugins \
    && chmod -R 755 /var/lib/grafana/plugins \
    && chmod -R 775 /var/lib/grafana \
    && chmod -R 775 /app/backend_server/config/grafana \
    && chmod -R 755 /var/log/grafana

# Copy supervisor configuration (with nginx)
COPY backend_server/config/supervisor/supervisord.conf /etc/supervisor/conf.d/virtualpytest.conf

# Expose nginx port (Render routes to this)
EXPOSE 80

# Health check for nginx (which proxies to Flask)
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:80/health || exit 1

# Run supervisor as root (needed for Grafana)
USER root

# Run supervisor to manage nginx, Flask and Grafana
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/supervisord.conf", "-n"] 