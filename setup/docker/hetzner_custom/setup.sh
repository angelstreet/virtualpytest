#!/bin/bash
# VirtualPyTest Hetzner - Complete Setup
# Generates all configs for N hosts dynamically

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 VirtualPyTest Hetzner - Dynamic Setup"
echo "========================================="
echo ""

# Check if config exists
if [ ! -f "config.env" ]; then
    echo "❌ Error: config.env not found"
    echo "Creating default config.env..."
    cat > config.env <<'EOF'
# VirtualPyTest Hetzner - Configuration
HOST_MAX=2
HOST_START_PORT=6109
DOMAIN=api.virtualpytest.com
SERVER_PORT=5109
EOF
    echo "✅ Created config.env with defaults"
    echo "   Edit config.env to change HOST_MAX"
    echo ""
fi

# Load config
source config.env

echo "📋 Configuration:"
echo "   Hosts: $HOST_MAX"
echo "   Ports: ${HOST_START_PORT}-$((HOST_START_PORT + HOST_MAX - 1))"
echo "   Domain: $DOMAIN"
echo ""

# Check if main .env exists
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    echo "⚠️  Warning: Main .env file not found at:"
    echo "   $PROJECT_ROOT/.env"
    echo ""
    echo "📝 This file is needed for Docker services to start."
    echo "   You can create it later before running ./launch.sh"
    echo ""
    read -p "Continue anyway? (y/N) " -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Setup cancelled. Create .env file:"
        echo "  cp setup/docker/hetzner_custom/env.example .env"
        echo "  nano .env  # Add your Supabase credentials"
        exit 1
    fi
fi

# ============================================
# 0. CLEANUP EXISTING CONTAINERS
# ============================================
echo "🧹 Checking for existing containers..."

# Check if docker-compose.yml exists
if [ -f "docker-compose.yml" ]; then
    # Try to find .env file
    if [ -f "$PROJECT_ROOT/.env" ]; then
        RUNNING=$(docker-compose --env-file "$PROJECT_ROOT/.env" -f docker-compose.yml ps -q 2>/dev/null | wc -l)
        if [ "$RUNNING" -gt 0 ]; then
            echo "   Found running containers, stopping..."
            docker-compose --env-file "$PROJECT_ROOT/.env" -f docker-compose.yml down
            echo "   ✅ Containers stopped and removed"
        else
            echo "   No running containers found"
        fi
    else
        echo "   ⚠️  Warning: .env file not found at $PROJECT_ROOT/.env"
        echo "   Trying to stop containers without env file..."
        docker-compose -f docker-compose.yml down 2>/dev/null || true
    fi
else
    echo "   No docker-compose.yml found (first run)"
fi

# Also check for any orphaned virtualpytest containers
ORPHANED=$(docker ps -a --filter "name=virtualpytest" -q 2>/dev/null | wc -l)
if [ "$ORPHANED" -gt 0 ]; then
    echo "   Found ${ORPHANED} orphaned containers, removing..."
    docker rm -f $(docker ps -a --filter "name=virtualpytest" -q) 2>/dev/null || true
    echo "   ✅ Orphaned containers removed"
fi

echo ""

# Check RAM
TOTAL_RAM=$(free -m | awk '/^Mem:/{print $2}')
AVAILABLE_RAM=$(free -m | awk '/^Mem:/{print $7}')
NEEDED_RAM=$((HOST_MAX * 350))
RECOMMENDED_HOSTS=$((AVAILABLE_RAM / 350))

echo "💾 Memory Check:"
echo "   Total RAM: ${TOTAL_RAM}MB"
echo "   Available: ${AVAILABLE_RAM}MB"
echo "   Needed for ${HOST_MAX} hosts: ~${NEEDED_RAM}MB"
echo ""

if [ "$HOST_MAX" -gt "$RECOMMENDED_HOSTS" ]; then
    echo "⚠️  WARNING: Recommended max: $RECOMMENDED_HOSTS hosts"
    read -p "Continue with $HOST_MAX hosts? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Edit config.env to set HOST_MAX=$RECOMMENDED_HOSTS"
        exit 1
    fi
fi

# ============================================
# 1. GENERATE NGINX CONFIG
# ============================================
echo "🔧 [1/4] Generating nginx config..."
NGINX_FILE="host-nginx.conf"

cat > "$NGINX_FILE" <<EOF
# HTTP - Redirect all to HTTPS
server {
    listen 80;
    server_name ${DOMAIN};
    return 301 https://\$server_name\$request_uri;
}

# HTTPS - SSL Termination and Proxy to Docker Containers
server {
    listen 443 ssl http2;
    server_name ${DOMAIN};

    # SSL Configuration (managed by certbot)
    ssl_certificate /etc/letsencrypt/live/${DOMAIN}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${DOMAIN}/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    # Increase buffer sizes
    client_max_body_size 100M;
    proxy_buffer_size 128k;
    proxy_buffers 4 256k;
    proxy_busy_buffers_size 256k;

    # Server API
    location /server/ {
        proxy_pass http://127.0.0.1:${SERVER_PORT}/server/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
    }

    # Health check
    location /health {
        proxy_pass http://127.0.0.1:${SERVER_PORT}/health;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
    }

    # Grafana
    location /grafana/ {
        proxy_pass http://127.0.0.1:3000/;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # Auto-redirect VNC lite pages to include correct WebSocket path
    location ~ ^/host([1-8])/vnc/vnc_lite\\.html\$ {
        if (\$arg_path = "") {
            return 302 /host\$1/vnc/vnc_lite.html?path=host\$1/websockify;
        }
    }

    # Root-level WebSocket for VNC
    location /websockify {
        # Default to first host
        set \$backend_port "${HOST_START_PORT}";
EOF

# Add referer-based routing (only if blocks, no unconditional sets)
for i in $(seq 1 $HOST_MAX); do
    PORT=$((HOST_START_PORT + i - 1))
    cat >> "$NGINX_FILE" <<EOF
        if (\$http_referer ~* "/host${i}/") {
            set \$backend_port "${PORT}";
        }
EOF
done

cat >> "$NGINX_FILE" <<'EOF'
        
        proxy_pass http://127.0.0.1:$backend_port/websockify;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }

EOF

# Generate host location blocks
for i in $(seq 1 $HOST_MAX); do
    PORT=$((HOST_START_PORT + i - 1))
    cat >> "$NGINX_FILE" <<EOF
    # Host ${i} WebSocket
    location /host${i}/websockify {
        rewrite ^/host${i}/websockify$ /websockify break;
        proxy_pass http://127.0.0.1:${PORT};
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }

    # Host ${i} routes
    location /host${i}/ {
        rewrite ^/host${i}/(.*)$ /host/\$1 break;
        proxy_pass http://127.0.0.1:${PORT};
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }

EOF
done

cat >> "$NGINX_FILE" <<EOF
    # Root - proxy to backend server
    location / {
        proxy_pass http://127.0.0.1:${SERVER_PORT}/;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}

EOF

echo "   ✅ Created: $NGINX_FILE"

# ============================================
# 2. GENERATE DOCKER-COMPOSE.YML
# ============================================
echo "🔧 [2/4] Generating docker-compose.yml..."
COMPOSE_FILE="docker-compose.yml"

cat > "$COMPOSE_FILE" <<EOF
# Auto-generated for ${HOST_MAX} hosts
services:
  backend_server:
    build:
      context: ../../../
      dockerfile: backend_server/Dockerfile
    container_name: virtualpytest-backend-server
    ports:
      - "${SERVER_PORT}:${SERVER_PORT}"
      - "3000:3000"
    volumes:
      - ../../../.env:/app/.env:ro
      - grafana-data:/var/lib/grafana
      - grafana-logs:/var/log/grafana
    environment:
      - SERVER_PORT=${SERVER_PORT}
      - SERVER_URL=\${SERVER_URL:-http://localhost:${SERVER_PORT}}
      - DEBUG=\${DEBUG:-false}
      - CORS_ORIGINS=\${CORS_ORIGINS:-http://localhost:3000}
      - SUPABASE_DB_URI=\${SUPABASE_DB_URI}
      - NEXT_PUBLIC_SUPABASE_URL=\${NEXT_PUBLIC_SUPABASE_URL}
      - NEXT_PUBLIC_SUPABASE_ANON_KEY=\${NEXT_PUBLIC_SUPABASE_ANON_KEY}
      - GRAFANA_ADMIN_USER=admin
      - GRAFANA_ADMIN_PASSWORD=\${GRAFANA_ADMIN_PASSWORD:-admin123}
      - GRAFANA_SECRET_KEY=\${GRAFANA_SECRET_KEY}
      - GRAFANA_DOMAIN=\${GRAFANA_DOMAIN:-localhost}
      - GF_SERVER_HTTP_PORT=3000
      - GF_SERVER_PROTOCOL=http
      - GF_SERVER_DOMAIN=\${GRAFANA_DOMAIN:-localhost}
      - GF_SERVER_ROOT_URL=\${SERVER_URL:-http://localhost:${SERVER_PORT}}/grafana
      - GF_SERVER_SERVE_FROM_SUB_PATH=true
    restart: unless-stopped
    networks:
      - hetzner_network

EOF

# Generate host services
for i in $(seq 1 $HOST_MAX); do
    PORT=$((HOST_START_PORT + i - 1))
    cat >> "$COMPOSE_FILE" <<EOF
  backend_host_${i}:
    build:
      context: ../../../
      dockerfile: backend_host/Dockerfile
    container_name: virtualpytest-backend-host-${i}
    hostname: backend-host-${i}
    ports:
      - "${PORT}:80"
    volumes:
      - /dev:/dev
      - ../../../.env:/app/.env:ro
      - ../../../backend_host_${i}/.env:/app/backend_host/src/.env:ro
    depends_on:
      backend_server:
        condition: service_started
    command: sh -c "sleep 10 && /app/backend_host/docker/scripts/entrypoint.sh"
    privileged: true
    restart: unless-stopped
    networks:
      - hetzner_network

EOF
done

cat >> "$COMPOSE_FILE" <<EOF
volumes:
  grafana-data:
    name: virtualpytest-hetzner-grafana-data
  grafana-logs:
    name: virtualpytest-hetzner-grafana-logs

networks:
  hetzner_network:
    name: virtualpytest-hetzner-network
    driver: bridge
EOF

echo "   ✅ Created: $COMPOSE_FILE"

# ============================================
# 3. GENERATE HOST .ENV FILES
# ============================================
echo "🔧 [3/4] Generating host .env files..."

for i in $(seq 1 $HOST_MAX); do
    PORT=$((HOST_START_PORT + i - 1))
    DIR="$PROJECT_ROOT/backend_host_${i}"
    mkdir -p "$DIR"
    
    cat > "$DIR/.env" <<EOF
# Backend Host ${i} Configuration (Auto-generated)
SERVER_URL=http://backend_server:${SERVER_PORT}
HOST_NAME=hetzner-host-${i}
HOST_PORT=${HOST_START_PORT}
HOST_URL=http://backend_host_${i}:80
HOST_API_URL=http://backend_host_${i}:80
HOST_VIDEO_CAPTURE_PATH=/var/www/html/stream/capture${i}
HOST_VNC_STREAM_PATH=https://${DOMAIN}/host${i}/vnc/vnc_lite.html
DEBUG=false
PYTHONUNBUFFERED=1
EOF
    
    echo "   ✅ Created: backend_host_${i}/.env"
done

echo ""
echo "========================================="
echo "✅ Setup Complete!"
echo ""
echo "📝 Generated:"
echo "   • host-nginx.conf (${HOST_MAX} hosts)"
echo "   • docker-compose.yml (1 server + ${HOST_MAX} hosts)"
echo "   • backend_host_1/.env through backend_host_${HOST_MAX}/.env"
echo ""

# ============================================
# 4. DEPLOY NGINX CONFIG
# ============================================
echo "🌐 [4/4] Deploying nginx configuration..."
echo ""

if [ ! -d "/etc/nginx/sites-available" ]; then
    echo "⚠️  Warning: /etc/nginx/sites-available not found"
    echo "   Skipping nginx deployment (not running on server?)"
    echo ""
    echo "📋 Manual nginx deployment:"
    echo "   sudo cp host-nginx.conf /etc/nginx/sites-available/virtualpytest"
    echo "   sudo ln -sf /etc/nginx/sites-available/virtualpytest /etc/nginx/sites-enabled/"
    echo "   sudo nginx -t && sudo systemctl reload nginx"
else
    # Deploy nginx config
    echo "   Copying nginx config..."
    sudo cp host-nginx.conf /etc/nginx/sites-available/virtualpytest
    
    # Create symlink if not exists
    if [ ! -L "/etc/nginx/sites-enabled/virtualpytest" ]; then
        echo "   Creating symlink..."
        sudo ln -sf /etc/nginx/sites-available/virtualpytest /etc/nginx/sites-enabled/virtualpytest
    fi
    
    # Remove default if exists
    if [ -f "/etc/nginx/sites-enabled/default" ]; then
        echo "   Removing default site..."
        sudo rm -f /etc/nginx/sites-enabled/default
    fi
    
    # Test nginx config
    echo "   Testing nginx configuration..."
    if sudo nginx -t; then
        echo "   Reloading nginx..."
        sudo systemctl reload nginx
        echo "   ✅ Nginx deployed successfully!"
    else
        echo "   ❌ Nginx config test failed!"
        echo "   Please check the configuration manually"
        exit 1
    fi
fi

echo ""
echo "========================================="
echo "🎉 Complete! Ready to launch."
echo ""
echo "🚀 Start services:"
echo "   ./launch.sh"
echo ""
echo "🌐 Access points:"
for i in $(seq 1 $HOST_MAX); do
    echo "   https://${DOMAIN}/host${i}/vnc/vnc_lite.html"
done
echo ""
