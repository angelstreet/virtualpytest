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

# Optional VPN Configuration (leave empty to disable)
# Get free WireGuard config: protonvpn.com → Downloads → WireGuard
ENABLE_VPN=false
VPN_CONFIG_PATH=""
VPN_INTERFACE=wg0
EOF
    echo "✅ Created config.env with defaults"
    echo "   Edit config.env to change HOST_MAX or enable VPN"
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

# ============================================
# 0. INSTALL DEPENDENCIES
# ============================================
echo "📦 Installing dependencies..."

# Install WireGuard (lightweight, ~1MB)
if ! command -v wg &> /dev/null; then
    echo "   Installing WireGuard..."
    if sudo apt update && sudo apt install -y wireguard 2>/dev/null; then
        echo "   ✅ WireGuard installed"
    else
        echo "   ⚠️  WireGuard installation failed (non-critical)"
    fi
else
    echo "   ✅ WireGuard already installed"
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
# 0.5. VPN SETUP (Optional)
# ============================================
echo "🌐 VPN Configuration:"

if [ "$USE_VPN" = "true" ]; then
    echo "   VPN enabled in config.env"
    
    # Check if wg0.conf exists
    if [ ! -f "/etc/wireguard/wg0.conf" ]; then
        echo "   ❌ VPN config not found: /etc/wireguard/wg0.conf"
        echo ""
        echo "   Setup VPN:"
        echo "      1. Get free config: protonvpn.com → Downloads → WireGuard"
        echo "      2. Download .conf file (pick country: US, NL, etc.)"
        echo "      3. Upload: scp ~/Downloads/your.conf root@SERVER_IP:~/vpn.conf"
        echo "      4. Install: sudo cp ~/vpn.conf /etc/wireguard/wg0.conf"
        echo "      5. Secure:  sudo chmod 600 /etc/wireguard/wg0.conf"
        echo ""
        read -p "Continue without VPN? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        # Check if wg0 is already up
        if ip link show wg0 &> /dev/null && [ "$(ip link show wg0 | grep 'state UP')" ]; then
            echo "   ✅ VPN already active (wg0)"
        else
            echo "   Starting WireGuard VPN..."
            if sudo wg-quick up wg0 2>/dev/null; then
                echo "   ✅ VPN started successfully"
                
                # Enable on boot
                if ! systemctl is-enabled wg-quick@wg0 &> /dev/null; then
                    sudo systemctl enable wg-quick@wg0 2>/dev/null
                    echo "   ✅ VPN enabled on boot"
                fi
            else
                echo "   ⚠️  VPN already running or failed to start"
            fi
        fi
        
        # Show current IP
        echo "   Current IP: $(curl -s --max-time 5 ifconfig.me || echo 'Unable to detect')"
    fi
else
    echo "   VPN disabled (set USE_VPN=true in config.env to enable)"
    if [ -f "/etc/wireguard/wg0.conf" ]; then
        echo "   VPN config detected but not enabled"
    fi
fi

echo ""

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
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

EOF

# Generate individual hardcoded location blocks for each host (1-8 max)
for i in $(seq 1 $HOST_MAX); do
    PORT=$((HOST_START_PORT + i - 1))
    cat >> "$NGINX_FILE" <<EOF
    # Host ${i} - HLS Video Streams (specific resource types, MUST be first)
    location ~ ^/host${i}/stream/([^/]+)/(captures|thumbnails|segments|metadata|audio|transcript)/(.+)\$ {
        rewrite ^/host${i}/stream/(.*)$ /host/stream/\$1 break;
        proxy_pass http://127.0.0.1:${PORT};
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        add_header Access-Control-Allow-Origin "*" always;
        add_header Access-Control-Allow-Methods "GET, POST, OPTIONS" always;
        add_header Access-Control-Allow-Headers "DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range" always;
        add_header Access-Control-Expose-Headers "Content-Length,Content-Range" always;
        add_header Cache-Control "no-cache, no-store, must-revalidate" always;
        proxy_buffering off;
    }

    # Host ${i} - General stream location
    location /host${i}/stream/ {
        rewrite ^/host${i}/stream/(.*)$ /host/stream/\$1 break;
        proxy_pass http://127.0.0.1:${PORT};
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        add_header Access-Control-Allow-Origin "*" always;
        add_header Access-Control-Allow-Methods "GET, POST, OPTIONS" always;
        add_header Access-Control-Allow-Headers "DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range" always;
        add_header Access-Control-Expose-Headers "Content-Length,Content-Range" always;
        proxy_buffering off;
    }

    # Host ${i} - Captures location
    location /host${i}/captures/ {
        rewrite ^/host${i}/captures/(.*)$ /host/captures/\$1 break;
        proxy_pass http://127.0.0.1:${PORT};
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        add_header Access-Control-Allow-Origin "*" always;
        add_header Access-Control-Allow-Methods "GET, OPTIONS" always;
        add_header Access-Control-Allow-Headers "DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range" always;
        add_header Access-Control-Expose-Headers "Content-Length,Content-Range" always;
        proxy_buffering off;
    }

    # Host ${i} - Normalize legacy /host path (e.g. /host${i}/host/stream → /host/stream)
    location /host${i}/host/ {
        rewrite ^/host${i}/host/(.*)$ /host/\$1 break;
        proxy_pass http://127.0.0.1:${PORT};
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_buffering off;
    }

    # Host ${i} WebSocket (specific match)
    location /host${i}/websockify {
        rewrite ^/host${i}/websockify\$ /websockify break;
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

    # Host ${i} All other routes
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
# OPTIMIZED: Single backend_host image shared across all hosts
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
      - GF_SERVER_HTTP_PORT=3000
      - GF_SERVER_PROTOCOL=http
      - GF_SERVER_DOMAIN=${DOMAIN}
      - GF_SERVER_ROOT_URL=https://${DOMAIN}/grafana
      - GF_SERVER_SERVE_FROM_SUB_PATH=true
    restart: unless-stopped
    networks:
      - hetzner_network

  # Build backend_host image ONCE (shared by all hosts)
  backend_host_base:
    build:
      context: ../../../
      dockerfile: backend_host/Dockerfile
    image: virtualpytest-backend-host:latest
    # This service never runs - it's only used to build the image
    profiles: ["build-only"]

EOF

# Generate host services (all use the same pre-built image)
for i in $(seq 1 $HOST_MAX); do
    PORT=$((HOST_START_PORT + i - 1))
    cat >> "$COMPOSE_FILE" <<EOF
  backend_host_${i}:
    image: virtualpytest-backend-host:latest
    container_name: virtualpytest-backend-host-${i}
    hostname: backend-host-${i}
    ports:
      - "${PORT}:80"
    volumes:
      - /dev:/dev
      - ../../../.env:/app/.env:ro
      - ../../../backend_host_${i}/.env:/app/backend_host/src/.env:ro
      - ../../../test_scripts:/app/test_scripts:ro
      - ../../../test_campaign:/app/test_campaign:ro
      - ../../../backend_discard:/app/backend_discard:ro
    tmpfs:
      - /var/www/html/stream/capture${i}/hot:size=200M,mode=777
    environment:
      - XDG_CONFIG_HOME=/tmp/.chromium
      - XDG_CACHE_HOME=/tmp/.chromium
      - XDG_RUNTIME_DIR=/tmp/.chromium
    depends_on:
      backend_server:
        condition: service_started
    command: sh -c "sleep 10 && /app/backend_host/docker/scripts/entrypoint.sh"
    privileged: true
    security_opt:
      - seccomp=unconfined
      - apparmor=unconfined
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
HOST_URL=https://${DOMAIN}/host${i}
HOST_API_URL=http://backend_host_${i}:80
HOST_VIDEO_CAPTURE_PATH=/var/www/html/stream/capture${i}
HOST_VIDEO_STREAM_PATH=/host/stream/capture${i}
HOST_VNC_STREAM_PATH=https://${DOMAIN}/host${i}/vnc/vnc_lite.html?path=/host${i}/websockify
HOST_VIDEO_SOURCE=:1
HOST_VIDEO_AUDIO=null
HOST_VIDEO_FPS=2
DEBUG=false
PYTHONUNBUFFERED=1

# R2 Storage - Copy from main .env if exists
# NOTE: These will be overwritten if present in main .env (OS env vars take priority)
CLOUDFLARE_R2_ENDPOINT=
CLOUDFLARE_R2_ACCESS_KEY_ID=
CLOUDFLARE_R2_SECRET_ACCESS_KEY=
CLOUDFLARE_R2_PUBLIC_URL=
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

# Show VPN status if enabled
if [ "$USE_VPN" = "true" ] && ip link show wg0 &> /dev/null; then
    echo "🌐 VPN Status:"
    echo "   Interface: wg0 (active)"
    echo "   Public IP: $(curl -s --max-time 5 ifconfig.me || echo 'Unable to detect')"
    echo ""
fi

echo "🚀 Start services:"
echo "   ./launch.sh"
echo ""
echo "🌐 Access points:"
for i in $(seq 1 $HOST_MAX); do
    echo "   https://${DOMAIN}/host${i}/vnc/vnc_lite.html"
done
echo ""

