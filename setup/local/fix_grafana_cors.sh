#!/bin/bash

# VirtualPyTest - Fix Grafana CORS for Local Development
# This script fixes cross-origin issues with locally installed Grafana

set -e

echo "🔧 Fixing Grafana CORS configuration for local development..."

# Get to project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Change to project root
cd "$PROJECT_ROOT"

# Check if Grafana is installed
if ! command -v grafana-server &> /dev/null; then
    echo "❌ Grafana is not installed"
    echo "Please run: ./setup/local/install_grafana.sh"
    exit 1
fi

# Check if Grafana configuration exists
GRAFANA_CONF="/etc/grafana/grafana.ini"
if [ ! -f "$GRAFANA_CONF" ]; then
    echo "❌ Grafana configuration not found at $GRAFANA_CONF"
    echo "Please run: ./setup/local/install_grafana.sh"
    exit 1
fi

echo "📋 Current Grafana configuration:"
echo "   Config file: $GRAFANA_CONF"

# Stop Grafana service if running
if systemctl is-active --quiet grafana-server; then
    echo "🛑 Stopping Grafana service..."
    sudo systemctl stop grafana-server
    sleep 2
fi

# Backup current configuration
echo "💾 Creating backup of current configuration..."
sudo cp "$GRAFANA_CONF" "$GRAFANA_CONF.backup.$(date +%Y%m%d_%H%M%S)"

# Configure security settings for local development with cross-origin support
echo "🔒 Configuring security settings for local development..."

# Disable secure cookies for HTTP (local development)
sudo sed -i 's/cookie_secure = true/cookie_secure = false/' "$GRAFANA_CONF"

# Set SameSite to None for cross-origin embedding (required for iframe embedding)
sudo sed -i 's/cookie_samesite = lax/cookie_samesite = none/' "$GRAFANA_CONF"

# Ensure embedding is allowed (should already be true, but make sure)
sudo sed -i 's/;allow_embedding = false/allow_embedding = true/' "$GRAFANA_CONF"
sudo sed -i 's/allow_embedding = false/allow_embedding = true/' "$GRAFANA_CONF"

# Add CSRF trusted origins for local development
# This allows requests from Vite dev server and common local IPs
sudo sed -i 's/;csrf_trusted_origins = example.com/csrf_trusted_origins = localhost:5073 127.0.0.1:5073 192.168.1.34:5073 0.0.0.0:5073/' "$GRAFANA_CONF"

# If the line doesn't exist, add it
if ! grep -q "csrf_trusted_origins" "$GRAFANA_CONF"; then
    sudo sed -i '/\[security\]/a csrf_trusted_origins = localhost:5073 127.0.0.1:5073 192.168.1.34:5073 0.0.0.0:5073' "$GRAFANA_CONF"
fi

# Ensure proper local configuration
echo "⚙️ Ensuring proper local configuration..."

# Update configuration for local use (change port to 3001 to avoid conflicts)
sudo sed -i 's/http_port = 3000/http_port = 3001/' "$GRAFANA_CONF"
sudo sed -i 's/domain = dev.virtualpytest.com/domain = localhost/' "$GRAFANA_CONF"
sudo sed -i 's|root_url = https://dev.virtualpytest.com/grafana/|root_url = http://localhost:3000/|' "$GRAFANA_CONF"
sudo sed -i 's/serve_from_sub_path = true/serve_from_sub_path = false/' "$GRAFANA_CONF"

# Set proper permissions
sudo chown -R grafana:grafana /var/lib/grafana
sudo chown -R grafana:grafana /var/log/grafana
sudo chown -R grafana:grafana /etc/grafana/

echo "✅ Grafana CORS configuration updated successfully!"

# Show what was changed
echo ""
echo "📋 Configuration changes made:"
echo "   ✅ cookie_secure = false (allows HTTP cookies)"
echo "   ✅ cookie_samesite = none (allows cross-origin cookies)"
echo "   ✅ allow_embedding = true (allows iframe embedding)"
echo "   ✅ csrf_trusted_origins = localhost:5073 127.0.0.1:5073 192.168.1.34:5073 0.0.0.0:5073"
echo "   ✅ http_port = 3001 (local port)"
echo "   ✅ domain = localhost"
echo "   ✅ root_url = http://localhost:3000/"

# Start Grafana service
echo ""
echo "🚀 Starting Grafana service..."
sudo systemctl start grafana-server

# Wait for Grafana to start
echo "⏳ Waiting for Grafana to start..."
sleep 5

# Check if Grafana is running
if systemctl is-active --quiet grafana-server; then
    echo "✅ Grafana service is running"
else
    echo "⚠️ Grafana service may not be running properly"
    echo "🔍 Checking Grafana status..."
    sudo systemctl status grafana-server --no-pager || true
fi

echo ""
echo "🎉 Grafana CORS fix completed!"
echo ""
echo "🌐 Access Grafana at:"
echo "   URL: http://localhost:3000"
echo "   Login: admin / admin123"
echo ""
echo "💡 Your Vite dev server (http://localhost:5073) should now be able to:"
echo "   ✅ Embed Grafana dashboards in iframes"
echo "   ✅ Make cross-origin requests to Grafana"
echo "   ✅ Access Grafana APIs with credentials"
echo ""
echo "🔧 If you still have issues, try:"
echo "   1. Clear your browser cache and cookies"
echo "   2. Restart your Vite dev server"
echo "   3. Check browser console for specific CORS errors"
