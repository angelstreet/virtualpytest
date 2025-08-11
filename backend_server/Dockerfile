FROM python:3.11-slim

# Install system dependencies including Grafana and nginx
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    gnupg2 \
    software-properties-common \
    supervisor \
    postgresql-client \
    libpq-dev \
    libpq5 \
    nginx \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libglib2.0-0 \
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

# Copy Grafana configuration
COPY backend_server/config/ backend_server/config/

# Copy utils directory (if it exists in project root)
# Note: This copy is optional and will be skipped if src/utils/ doesn't exist

# Set working directory to backend_server
WORKDIR /app/backend_server

# Create directories for Grafana with proper plugin support
RUN mkdir -p /var/lib/grafana /var/log/grafana /etc/grafana \
    && mkdir -p /app/backend_server/config/grafana/provisioning/{datasources,dashboards} \
    && mkdir -p /app/backend_server/config/grafana/dashboards \
    && mkdir -p /var/log/supervisor \
    && mkdir -p /usr/share/grafana/data/plugins \
    && mkdir -p /var/lib/grafana/plugins

# Create non-root user for security and fix Grafana permissions
RUN useradd -m -u 1000 vptuser \
    && chown -R vptuser:vptuser /app \
    && chown -R grafana:grafana /var/lib/grafana \
    && chown -R grafana:grafana /var/log/grafana \
    && chown -R grafana:grafana /etc/grafana \
    && chown -R grafana:grafana /usr/share/grafana/data/plugins \
    && chown -R grafana:grafana /var/lib/grafana/plugins \
    && chmod -R 755 /usr/share/grafana/data/plugins \
    && chmod -R 755 /var/lib/grafana/plugins \
    && chmod -R 775 /var/lib/grafana \
    && chmod -R 755 /var/log/grafana

# Copy nginx configuration
COPY backend_server/config/nginx/virtualpytest.conf /etc/nginx/sites-available/virtualpytest
RUN ln -s /etc/nginx/sites-available/virtualpytest /etc/nginx/sites-enabled/virtualpytest \
    && rm -f /etc/nginx/sites-enabled/default

# Copy supervisor configuration
COPY backend_server/config/supervisor/supervisord.conf /etc/supervisor/conf.d/virtualpytest.conf

# Expose ports (Flask + Grafana)
EXPOSE 5109 3001

# Health check for nginx proxy
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:5109/health || exit 1

# Run supervisor as root (needed for nginx)
USER root

# Run supervisor to manage nginx, Flask and Grafana
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/supervisord.conf", "-n"] 