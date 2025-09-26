#!/bin/bash

# VirtualPyTest - Install backend_server
# This script installs backend_server dependencies including PostgreSQL for Grafana

set -e

echo "🖥️ Installing VirtualPyTest backend_server..."

# Get to project root directory (from setup/local to project root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Change to project root
cd "$PROJECT_ROOT"

# Check if we're in the right directory
if [ ! -f "README.md" ] || [ ! -d "backend_server" ]; then
    echo "❌ Could not find virtualpytest project root directory"
    echo "Current directory: $(pwd)"
    exit 1
fi

# Function to check if PostgreSQL is installed
check_postgresql() {
    if command -v psql &> /dev/null; then
        return 0
    else
        return 1
    fi
}

# Function to install PostgreSQL
install_postgresql() {
    echo "🐘 Installing PostgreSQL..."
    
    # Install on Linux
    if command -v apt-get &> /dev/null; then
        sudo apt-get update
        sudo apt-get install -y postgresql postgresql-contrib
    elif command -v yum &> /dev/null; then
        sudo yum install -y postgresql postgresql-server postgresql-contrib
        sudo postgresql-setup initdb
    elif command -v pacman &> /dev/null; then
        sudo pacman -S postgresql
        sudo -u postgres initdb -D /var/lib/postgres/data
    else
        echo "❌ Unsupported Linux distribution. Please install PostgreSQL manually."
        exit 1
    fi
    
    # Start and enable PostgreSQL
    sudo systemctl start postgresql
    sudo systemctl enable postgresql
    
    echo "✅ PostgreSQL installed successfully"
}

# Function to install VNC and noVNC tools
install_vnc() {
    echo "🖥️ Installing VNC and noVNC tools..."
    
    # Install on Linux
    if command -v apt-get &> /dev/null; then
        sudo apt-get update
        sudo apt-get install -y tigervnc-standalone-server xvfb xfce4 xfce4-goodies novnc websockify
    elif command -v yum &> /dev/null; then
        sudo yum install -y tigervnc-server xorg-x11-server-Xvfb xfce4-session novnc python3-websockify
    elif command -v pacman &> /dev/null; then
        sudo pacman -S tigervnc xorg-server-xvfb xfce4 xfce4-goodies novnc python-websockify
    else
        echo "❌ Unsupported Linux distribution. Please install VNC tools manually."
        exit 1
    fi
    
    # Setup noVNC if not already present
    if [ -d "/usr/share/novnc" ]; then
        echo "✅ noVNC web interface installed"
    else
        echo "⚠️ noVNC may need manual setup if package installation failed"
    fi
    
    echo "✅ VNC and noVNC tools installed successfully"
}

# Function to setup Grafana metrics database
setup_grafana_database() {
    echo "📊 Setting up Grafana metrics database..."
    
    # Create database and user for Grafana metrics
    sudo -u postgres psql << 'EOF'
-- Create database for Grafana metrics
CREATE DATABASE grafana_metrics;

-- Create user for Grafana
CREATE USER grafana_user WITH PASSWORD 'grafana_pass';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE grafana_metrics TO grafana_user;
ALTER USER grafana_user CREATEDB;

-- Exit
\q
EOF

    # Test the connection
    if PGPASSWORD=grafana_pass psql -h localhost -U grafana_user -d grafana_metrics -c "SELECT version();" &> /dev/null; then
        echo "✅ Grafana database setup successful"
    else
        echo "❌ Failed to connect to Grafana database"
        exit 1
    fi
}

# Function to setup Grafana datasource configuration
setup_grafana_config() {
    echo "⚙️ Setting up Grafana configuration..."
    
    # Create provisioning directories
    mkdir -p backend_server/config/grafana/provisioning/datasources
    mkdir -p backend_server/config/grafana/provisioning/dashboards
    
    # Create the local datasource configuration
    cat > backend_server/config/grafana/provisioning/datasources/local.yml << 'EOF'
# Local Grafana datasource configuration for VirtualPyTest
apiVersion: 1

datasources:
  # Supabase PostgreSQL - READ ONLY for fetching application data
  - name: VirtualPyTest Supabase (Read-Only)
    type: postgres
    access: proxy
    url: ${SUPABASE_DB_URI}
    jsonData:
      sslmode: require
      postgresVersion: 1300  # PostgreSQL 13+
      timescaledb: false
      maxOpenConns: 3  # Reduced connections for read-only
      maxIdleConns: 1
      connMaxLifetime: 14400  # 4 hours
    # NOT default datasource - metrics DB will be default
    isDefault: false
    # Read-only access - prevent table creation
    editable: false
    
  # Local PostgreSQL - DEFAULT for storing metrics and Grafana data
  - name: VirtualPyTest Metrics (Local)
    type: postgres
    access: proxy
    url: postgres://grafana_user:grafana_pass@localhost:5432/grafana_metrics
    jsonData:
      sslmode: disable  # Local connection, no SSL needed
      postgresVersion: 1300
      timescaledb: false
      maxOpenConns: 10
      maxIdleConns: 5
      connMaxLifetime: 14400
    # Set as default datasource for metrics storage
    isDefault: true
    # Allow editing for metrics and dashboard creation
    editable: true
EOF

    echo "✅ Grafana datasource configuration created"
}

# Check and install PostgreSQL if needed
if ! check_postgresql; then
    echo "🔍 PostgreSQL not found, installing..."
    install_postgresql
else
    echo "✅ PostgreSQL already installed"
fi

# Install VNC and noVNC tools
echo "🔍 Installing VNC and noVNC tools..."
install_vnc

# Setup Grafana database
echo "🔍 Checking Grafana database setup..."
if ! PGPASSWORD=grafana_pass psql -h localhost -U grafana_user -d grafana_metrics -c "SELECT 1;" &> /dev/null; then
    echo "📊 Setting up Grafana database..."
    setup_grafana_database
else
    echo "✅ Grafana database already configured"
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "🐍 Creating Python virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Skip shared library installation - using direct imports instead
echo "📚 Shared library will be used via direct imports..."

# Skip backend_host installation - using direct imports instead
echo "⚙️ Backend_core will be used via direct imports..."

# Install backend_server dependencies
echo "📦 Installing backend_server dependencies..."
cd backend_server
pip install -r requirements.txt

# Setup Grafana configuration
cd ..
setup_grafana_config

# Create .env file in src/ directory if it doesn't exist
cd backend_server/src
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo "📝 Creating .env file from .env.example..."
        cp .env.example .env
        echo "✅ Created .env file - please configure it with your settings"
    else
        echo "⚠️ No .env.example found - please create .env manually"
    fi
else
    echo "✅ .env file already exists"
fi

cd ../..

# Configure firewall ports for backend_server
echo "🔥 Configuring firewall for backend_server..."

# Source port checking functions
source "$PROJECT_ROOT/setup/local/check_and_open_port.sh"

# Get SERVER_PORT (default 5109)
SERVER_PORT="5109"

echo "🔧 Configuring firewall for backend_server ports:"
echo "   - Backend Server API: $SERVER_PORT"
echo "   - PostgreSQL: 5432"
echo "   - Grafana: 3000"

# Configure UFW for backend_server ports
check_and_open_port "$SERVER_PORT" "backend_server API" "tcp"
check_and_open_port "5432" "PostgreSQL database" "tcp"
check_and_open_port "3000" "Grafana dashboard" "tcp"

# Install Heatmap Processor Service
echo "🔧 Installing Heatmap Processor Service..."
HEATMAP_SERVICE_FILE="backend_server/config/services/heatmap_processor.service"

if [ -f "$HEATMAP_SERVICE_FILE" ]; then
    # Stop existing service if running
    sudo systemctl stop heatmap_processor 2>/dev/null || true
    
    # Copy service file to systemd directory
    sudo cp "$HEATMAP_SERVICE_FILE" /etc/systemd/system/
    
    # Reload systemd daemon
    sudo systemctl daemon-reload
    
    # Enable service for auto-start
    sudo systemctl enable heatmap_processor
    
    echo "✅ Heatmap Processor service installed and enabled"
    echo "   • Service will start automatically on boot"
    echo "   • Generates 24h circular heatmap buffer every minute"
    echo "   • To start now: sudo systemctl start heatmap_processor"
    echo "   • To check status: sudo systemctl status heatmap_processor"
    echo "   • To view logs: sudo journalctl -u heatmap_processor -f"
else
    echo "⚠️ Heatmap service file not found: $HEATMAP_SERVICE_FILE"
fi

# Create VPT Server Host systemd service (but don't enable/start it)
echo "🔧 Creating VPT Server Host systemd service..."
cat > /tmp/vpt_server_host.service << EOF
[Unit]
Description=VirtualPyTest Server Host Service - Launch VirtualPyTest System
After=network.target
Wants=network.target

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$(pwd)/scripts
ExecStartPre=/usr/bin/git pull
ExecStart=/bin/bash $(pwd)/scripts/launch_virtualpytest.sh
TimeoutStopSec=10
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Environment
Environment=HOST_NAME=$USER-server
Environment=PATH=/usr/local/bin:/usr/bin:/bin

[Install]
WantedBy=multi-user.target
EOF

# Install the service file (but don't enable or start it)
sudo cp /tmp/vpt_server_host.service /etc/systemd/system/
sudo systemctl daemon-reload
echo "✅ VPT Server Host service created (not enabled)"

echo ""
echo "✅ backend_server installation completed!"
echo ""
echo "📋 Next steps:"
echo "1. Configure your Supabase URI in backend_server/src/.env"
echo "2. Run: ./setup/local/launch_server.sh"
echo ""
echo "🔧 Grafana Configuration:"
echo "   • Local PostgreSQL database created for metrics storage"
echo "   • Supabase connection configured as read-only"
echo "   • Access Grafana at: http://localhost:3000 (when server is running)"
echo ""
echo "🖥️ VNC Configuration:"
echo "   • TigerVNC server installed for remote desktop access"
echo "   • noVNC web interface installed for browser-based VNC"
echo "   • XFCE4 desktop environment installed"
echo "   • Additional setup may be needed for VNC services"
echo ""
echo "🔧 Heatmap Processor Service:"
echo "   • Service installed and enabled: heatmap_processor.service"
echo "   • Generates 24h circular heatmap buffer every minute"
echo "   • To start now: sudo systemctl start heatmap_processor"
echo "   • To check status: sudo systemctl status heatmap_processor"
echo "   • To view logs: sudo journalctl -u heatmap_processor -f"
echo ""
echo "🔧 VPT Server Host Service (Optional):"
echo "   • Service created: vpt_server_host.service"
echo "   • To enable auto-start: sudo systemctl enable vpt_server_host"
echo "   • To start now: sudo systemctl start vpt_server_host"
echo "   • To check status: sudo systemctl status vpt_server_host"
echo "" 