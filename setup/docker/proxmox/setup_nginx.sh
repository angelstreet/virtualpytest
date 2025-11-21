#!/bin/bash
# Configure Nginx on Proxmox host for SSL termination and proxying to VM

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🌐 VirtualPyTest Nginx Configuration"
echo "====================================="
echo ""

# Load config
if [ ! -f "config.env" ]; then
    echo "❌ Error: config.env not found"
    echo "   Run ./setup.sh first"
    exit 1
fi

source config.env

# ============================================
# GET VM IP
# ============================================

echo "🔍 Detecting VM IP address..."

check_vm_exists() {
    if ! qm status $VM_ID &>/dev/null; then
        echo "❌ Error: VM $VM_ID does not exist"
        echo "   Run ./setup.sh first"
        exit 1
    fi
}

get_vm_status() {
    qm status $VM_ID | grep -oP 'status: \K\w+'
}

get_vm_ip() {
    qm guest exec $VM_ID -- ip -4 addr show 2>/dev/null | grep -oP 'inet \K[\d.]+' | grep -v '127.0.0.1' | head -1 || echo ""
}

check_vm_exists

VM_STATUS=$(get_vm_status)

if [ "$VM_STATUS" != "running" ]; then
    echo "❌ Error: VM is not running"
    echo "   Start it with: ./launch.sh start"
    exit 1
fi

VM_IP=$(get_vm_ip)

if [ -z "$VM_IP" ]; then
    echo "❌ Error: Unable to detect VM IP"
    echo ""
    echo "Options:"
    echo "   1. Wait for VM to fully boot and try again"
    echo "   2. Get IP manually: ./launch.sh console → run 'ip addr show'"
    echo "   3. Set IP manually: export VM_IP=192.168.1.x && ./setup_nginx.sh"
    exit 1
fi

echo "✅ VM IP detected: $VM_IP"
echo ""

# ============================================
# CONFIGURATION
# ============================================

echo "📋 Configuration:"
echo "   Domain: $DOMAIN"
echo "   VM IP: $VM_IP"
echo "   Backend Server Port: 8001 (inside VM)"
echo "   Host Ports: 5001-5008 (inside VM)"
echo ""

# ============================================
# CHECK NGINX
# ============================================

if ! command -v nginx &> /dev/null; then
    echo "📦 Nginx not installed, installing..."
    apt update
    apt install -y nginx certbot python3-certbot-nginx
    echo "✅ Nginx installed"
else
    echo "✅ Nginx already installed"
fi

# ============================================
# GENERATE NGINX CONFIG
# ============================================

echo "🔧 Generating Nginx configuration..."

NGINX_CONF="/etc/nginx/sites-available/virtualpytest"

cat > "$NGINX_CONF" <<EOF
# VirtualPyTest - Auto-generated Proxmox Host Configuration
# Proxies to VM at $VM_IP

# HTTP - Redirect to HTTPS
server {
    listen 80;
    server_name $DOMAIN;
    
    # Allow certbot for SSL certificate
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }
    
    # Redirect all other traffic to HTTPS
    location / {
        return 301 https://\$server_name\$request_uri;
    }
}

# HTTPS - SSL Termination and Proxy to VM
server {
    listen 443 ssl http2;
    server_name $DOMAIN;

    # SSL Configuration (will be managed by certbot)
    # ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    # ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;
    # include /etc/letsencrypt/options-ssl-nginx.conf;
    # ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    # Increase buffer sizes
    client_max_body_size 100M;
    proxy_buffer_size 128k;
    proxy_buffers 4 256k;
    proxy_busy_buffers_size 256k;

    # Server API
    location /server/ {
        proxy_pass http://$VM_IP:8001/server/;
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
        proxy_pass http://$VM_IP:8001/health;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
    }

EOF

# Generate host locations (host1 through host8)
for i in {1..8}; do
    PORT=$((5000 + i))
    cat >> "$NGINX_CONF" <<EOF
    # Host ${i} - HLS Video Streams
    location ~ ^/host${i}/stream/([^/]+)/(captures|thumbnails|segments|metadata|audio|transcript)/(.+)\$ {
        proxy_pass http://$VM_IP:$PORT/host/stream/\$1/\$2/\$3;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        add_header Access-Control-Allow-Origin "*" always;
        add_header Cache-Control "no-cache, no-store, must-revalidate" always;
        proxy_buffering off;
    }

    # Host ${i} - General stream location
    location /host${i}/stream/ {
        proxy_pass http://$VM_IP:$PORT/host/stream/;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        add_header Access-Control-Allow-Origin "*" always;
        proxy_buffering off;
    }

    # Host ${i} - Captures
    location /host${i}/captures/ {
        proxy_pass http://$VM_IP:$PORT/host/captures/;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        add_header Access-Control-Allow-Origin "*" always;
        proxy_buffering off;
    }

    # Host ${i} - WebSocket
    location /host${i}/websockify {
        proxy_pass http://$VM_IP:$PORT/websockify;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }

    # Host ${i} - All other routes
    location /host${i}/ {
        proxy_pass http://$VM_IP:$PORT/host/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }

EOF
done

cat >> "$NGINX_CONF" <<EOF
    # Root - proxy to backend server
    location / {
        proxy_pass http://$VM_IP:8001/;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

echo "✅ Configuration generated: $NGINX_CONF"

# ============================================
# ENABLE SITE
# ============================================

echo "🔗 Enabling site..."

# Create symlink
ln -sf "$NGINX_CONF" /etc/nginx/sites-enabled/virtualpytest

# Remove default if exists
if [ -f /etc/nginx/sites-enabled/default ]; then
    echo "   Removing default site..."
    rm -f /etc/nginx/sites-enabled/default
fi

echo "✅ Site enabled"

# ============================================
# TEST CONFIGURATION
# ============================================

echo "🧪 Testing Nginx configuration..."

if nginx -t; then
    echo "✅ Configuration valid"
else
    echo "❌ Configuration test failed"
    echo "   Check errors above"
    exit 1
fi

# ============================================
# RELOAD NGINX
# ============================================

echo "🔄 Reloading Nginx..."

systemctl reload nginx

echo "✅ Nginx reloaded"

# ============================================
# SSL CERTIFICATE
# ============================================

echo ""
echo "🔐 SSL Certificate Setup"
echo "========================"
echo ""

if [ -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]; then
    echo "✅ SSL certificate already exists for $DOMAIN"
else
    echo "📋 No SSL certificate found for $DOMAIN"
    echo ""
    echo "To obtain a free SSL certificate from Let's Encrypt:"
    echo ""
    echo "   sudo certbot --nginx -d $DOMAIN"
    echo ""
    read -p "Run certbot now? (y/N) " -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        certbot --nginx -d $DOMAIN
        echo "✅ SSL certificate obtained"
    else
        echo "⚠️  Skipping SSL setup"
        echo "   Run manually later: sudo certbot --nginx -d $DOMAIN"
    fi
fi

# ============================================
# SUMMARY
# ============================================

echo ""
echo "===================================="
echo "✅ Nginx Configuration Complete!"
echo "===================================="
echo ""
echo "📋 Configuration:"
echo "   Domain: $DOMAIN"
echo "   VM IP: $VM_IP"
echo "   Config: $NGINX_CONF"
echo ""
echo "🌐 Access Points:"
echo "   Server API: https://$DOMAIN/server/"
echo "   Host 1 VNC: https://$DOMAIN/host1/vnc/vnc_lite.html"
echo "   Host 2 VNC: https://$DOMAIN/host2/vnc/vnc_lite.html"
echo "   ... (up to host8)"
echo ""
echo "📝 Next Steps:"
echo ""
echo "1. Ensure Docker services are running inside VM:"
echo "   ./launch.sh ssh"
echo "   cd virtualpytest/setup/docker/hetzner_custom"
echo "   docker-compose ps  # Should show running containers"
echo ""
echo "2. Test access:"
echo "   curl https://$DOMAIN/health"
echo "   Open: https://$DOMAIN/host1/vnc/vnc_lite.html"
echo ""
echo "3. If VM IP changes (DHCP):"
echo "   Re-run: ./setup_nginx.sh"
echo "   Or set static IP in VM"
echo ""

