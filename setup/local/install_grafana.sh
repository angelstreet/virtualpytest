#!/bin/bash

# VirtualPyTest - Install Grafana for Local Development
# This script installs and configures Grafana for local monitoring

set -e

echo "📊 Installing Grafana for VirtualPyTest local development..."

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

# Check if running on Linux
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    echo "❌ This script only supports Linux"
    echo "Detected OS: $OSTYPE"
    exit 1
fi

echo "🖥️ Detected OS: Linux"


# Function to install Grafana on Linux
install_grafana() {
    echo "🐧 Installing Grafana on Linux..."
    
    # Check if running as root or with sudo
    if [[ $EUID -eq 0 ]]; then
        SUDO=""
    else
        SUDO="sudo"
        echo "🔐 This installation requires sudo privileges"
    fi
    
    # Detect Linux distribution
    if command -v apt-get &> /dev/null; then
        # Debian/Ubuntu
        echo "📦 Installing Grafana on Debian/Ubuntu..."
        
        # Install prerequisites
        $SUDO apt-get update
        $SUDO apt-get install -y software-properties-common wget
        
        # Add Grafana repository
        wget -q -O - https://packages.grafana.com/gpg.key | $SUDO apt-key add -
        echo "deb https://packages.grafana.com/oss/deb stable main" | $SUDO tee -a /etc/apt/sources.list.d/grafana.list
        
        # Install Grafana
        $SUDO apt-get update
        $SUDO apt-get install -y grafana
        
    elif command -v yum &> /dev/null; then
        # RHEL/CentOS/Fedora
        echo "📦 Installing Grafana on RHEL/CentOS/Fedora..."
        
        # Add Grafana repository
        cat <<EOF | $SUDO tee /etc/yum.repos.d/grafana.repo
[grafana]
name=grafana
baseurl=https://packages.grafana.com/oss/rpm
repo_gpgcheck=1
enabled=1
gpgcheck=1
gpgkey=https://packages.grafana.com/gpg.key
sslverify=1
sslcacert=/etc/pki/tls/certs/ca-bundle.crt
EOF
        
        # Install Grafana
        $SUDO yum install -y grafana
        
    else
        echo "❌ Unsupported Linux distribution"
        echo "Please install Grafana manually: https://grafana.com/docs/grafana/latest/installation/"
        exit 1
    fi
    
    # Get Grafana paths
    GRAFANA_HOME="/var/lib/grafana"
    GRAFANA_LOGS="/var/log/grafana"
    GRAFANA_CONF="/etc/grafana/grafana.ini"
    GRAFANA_BIN="/usr/sbin/grafana-server"
}

# Function to setup PostgreSQL for Grafana metrics
setup_postgresql() {
    echo "🐘 Setting up PostgreSQL for Grafana metrics..."
    
    # Check if PostgreSQL is installed
    if ! command -v psql &> /dev/null; then
        echo "❌ PostgreSQL is not installed"
        echo "Please install PostgreSQL first:"
        echo "  sudo apt-get install postgresql postgresql-contrib  # Ubuntu/Debian"
        echo "  sudo yum install postgresql-server postgresql-contrib  # RHEL/CentOS"
        exit 1
    fi
    
    # Check if PostgreSQL is running
    if ! pg_isready &> /dev/null; then
        echo "🚀 Starting PostgreSQL..."
        sudo systemctl start postgresql
        sudo systemctl enable postgresql
        
        # Wait for PostgreSQL to start
        sleep 3
        
        if ! pg_isready &> /dev/null; then
            echo "❌ Failed to start PostgreSQL"
            exit 1
        fi
    fi
    
    echo "✅ PostgreSQL is running"
    
    # Create Grafana database and user
    echo "📊 Creating Grafana metrics database..."
    
    # Create database and user (handle existing gracefully)
    # On Linux, use sudo to run as postgres user
    sudo -u postgres psql -c "CREATE DATABASE grafana_metrics;" 2>/dev/null || echo "Database grafana_metrics already exists"
    sudo -u postgres psql -c "CREATE USER grafana_user WITH PASSWORD 'grafana_pass';" 2>/dev/null || echo "User grafana_user already exists"
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE grafana_metrics TO grafana_user;" 2>/dev/null || true
    sudo -u postgres psql -c "ALTER USER grafana_user CREATEDB;" 2>/dev/null || true
    
    # Test the connection
    if PGPASSWORD=grafana_pass psql -h localhost -U grafana_user -d grafana_metrics -c "SELECT version();" &> /dev/null; then
        echo "✅ Grafana database setup successful"
    else
        echo "❌ Failed to connect to Grafana database"
        exit 1
    fi
}

# Function to setup local Grafana configuration
setup_grafana_config() {
    echo "⚙️ Setting up local Grafana configuration..."
    
    # Create Grafana directories (Linux system directories)
    sudo mkdir -p /var/lib/grafana
    sudo mkdir -p /var/log/grafana
    sudo mkdir -p /etc/grafana
    
    # Copy the pre-configured database with all dashboards
    echo "📊 Copying Grafana database with dashboards..."
    echo "🔍 Looking for: $PROJECT_ROOT/grafana/data/grafana.db"
    if [ -f "$PROJECT_ROOT/grafana/data/grafana.db" ]; then
        sudo cp "$PROJECT_ROOT/grafana/data/grafana.db" /var/lib/grafana/
    else
        echo "❌ File not found at: $PROJECT_ROOT/grafana/data/grafana.db"
        echo "📁 Current PROJECT_ROOT: $PROJECT_ROOT"
        echo "📁 Contents of grafana/data/:"
        ls -la "$PROJECT_ROOT/grafana/data/" || echo "Directory doesn't exist"
        exit 1
    fi
    
    # Copy the configuration file
    echo "⚙️ Copying Grafana configuration..."
    sudo cp "$PROJECT_ROOT/grafana/config/grafana.ini" /etc/grafana/
    
    # Set up provisioning directories and copy local datasource configuration
    echo "📋 Setting up Grafana provisioning for local databases..."
    sudo mkdir -p /etc/grafana/provisioning/datasources
    sudo mkdir -p /etc/grafana/provisioning/dashboards
    sudo mkdir -p /etc/grafana/dashboards/virtualpytest
    
    # Create provisioning configuration files directly
    echo "📋 Creating local datasource configuration..."
    sudo tee /etc/grafana/provisioning/datasources/local.yml > /dev/null << 'EOF'
# Local Grafana datasource configuration for VirtualPyTest
# This file automatically configures Grafana to use local PostgreSQL databases
apiVersion: 1

datasources:
  # VirtualPyTest Application Database - DEFAULT datasource
  - name: VirtualPyTest Local
    type: postgres
    access: proxy
    url: postgres://virtualpytest_user:virtualpytest_pass@localhost:5432/virtualpytest
    jsonData:
      sslmode: disable  # Local connection, no SSL needed
      postgresVersion: 1300
      timescaledb: false
      maxOpenConns: 10
      maxIdleConns: 5
      connMaxLifetime: 14400
    # Set as DEFAULT datasource
    isDefault: true
    # Allow editing for development
    editable: true
    
  # VirtualPyTest Metrics Database - for storing custom metrics
  - name: VirtualPyTest Metrics
    type: postgres
    access: proxy
    url: postgres://grafana_user:grafana_pass@localhost:5432/grafana_metrics
    jsonData:
      sslmode: disable  # Local connection, no SSL needed
      postgresVersion: 1300
      timescaledb: false
      maxOpenConns: 5
      maxIdleConns: 2
      connMaxLifetime: 14400
    # Not default, but available for metrics storage
    isDefault: false
    # Allow editing for development
    editable: true
EOF

    echo "📋 Creating dashboard provisioning configuration..."
    sudo tee /etc/grafana/provisioning/dashboards/dashboards.yml > /dev/null << 'EOF'
# Local Grafana dashboard provisioning configuration
apiVersion: 1

providers:
  # VirtualPyTest dashboards
  - name: 'VirtualPyTest'
    orgId: 1
    folder: 'VirtualPyTest'
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /etc/grafana/dashboards/virtualpytest
EOF
    
    # Update configuration for local use (keep port 3000 as default)
    sudo sed -i 's/;http_port = 3000/http_port = 3000/' /etc/grafana/grafana.ini
    sudo sed -i 's/domain = dev.virtualpytest.com/domain = localhost/' /etc/grafana/grafana.ini
    sudo sed -i 's|root_url = http://localhost/grafana/|root_url = http://localhost:3000/|' /etc/grafana/grafana.ini
    sudo sed -i 's/serve_from_sub_path = true/serve_from_sub_path = false/' /etc/grafana/grafana.ini
    
    # Configure security settings for local development with cross-origin support
    echo "🔒 Configuring security settings for local development..."
    
    # Disable secure cookies for HTTP (local development)
    sudo sed -i 's/cookie_secure = true/cookie_secure = false/' /etc/grafana/grafana.ini
    
    # Set SameSite to None for cross-origin embedding (required for iframe embedding)
    sudo sed -i 's/cookie_samesite = lax/cookie_samesite = none/' /etc/grafana/grafana.ini
    
    # Ensure embedding is allowed (should already be true, but make sure)
    sudo sed -i 's/;allow_embedding = false/allow_embedding = true/' /etc/grafana/grafana.ini
    sudo sed -i 's/allow_embedding = false/allow_embedding = true/' /etc/grafana/grafana.ini
    
    # Add CSRF trusted origins for local development
    # This allows requests from Vite dev server and common local IPs
    sudo sed -i 's/;csrf_trusted_origins = example.com/csrf_trusted_origins = localhost:5073 127.0.0.1:5073 192.168.1.34:5073 0.0.0.0:5073/' /etc/grafana/grafana.ini
    
    # If the line doesn't exist, add it
    if ! grep -q "csrf_trusted_origins" /etc/grafana/grafana.ini; then
        sudo sed -i '/\[security\]/a csrf_trusted_origins = localhost:5073 127.0.0.1:5073 192.168.1.34:5073 0.0.0.0:5073' /etc/grafana/grafana.ini
    fi
    
    # Set proper permissions
    sudo chown -R grafana:grafana /var/lib/grafana
    sudo chown -R grafana:grafana /var/log/grafana
    sudo chown -R grafana:grafana /etc/grafana/
    
    echo "✅ Grafana configuration setup completed successfully"
}



# Function to create launch script
create_launch_script() {
    echo "🚀 Creating Grafana launch script..."
    
    cat > "$PROJECT_ROOT/setup/local/launch_grafana.sh" << 'EOF'
#!/bin/bash

# VirtualPyTest - Launch Grafana Locally
# This script starts Grafana for local development

set -e

echo "📊 Starting Grafana for VirtualPyTest local development..."

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

# Check if Grafana is configured (Linux only)
GRAFANA_CONF="/etc/grafana/grafana.ini"

if [ ! -f "$GRAFANA_CONF" ]; then
    echo "❌ Grafana configuration not found at $GRAFANA_CONF"
    echo "Please run: ./setup/local/install_grafana.sh"
    exit 1
fi

# Check if PostgreSQL is running (for metrics storage)
if ! pg_isready &> /dev/null; then
    echo "🐘 Starting PostgreSQL..."
    sudo systemctl start postgresql
    sleep 3
fi

# Kill any existing Grafana processes on port 3001
if lsof -ti:3001 > /dev/null 2>&1; then
    echo "🛑 Stopping existing Grafana process..."
    lsof -ti:3001 | xargs kill -9 2>/dev/null || true
    sleep 2
fi

# Set environment variables for datasource configuration
export SUPABASE_DB_URI="${SUPABASE_DB_URI:-postgres://user:pass@localhost:5432/postgres}"

echo "🚀 Starting Grafana server..."
echo "📊 Grafana will be available at: http://localhost:3000"
echo "🔑 Login: admin / admin123"
echo "💡 Press Ctrl+C to stop"

# Start Grafana server using system configuration (Linux)
grafana-server \
    --config="$GRAFANA_CONF" \
    --homepath="/usr/share/grafana" \
    web
EOF

    # Make launch script executable
    chmod +x "$PROJECT_ROOT/setup/local/launch_grafana.sh"
    
    echo "✅ Launch script created at setup/local/launch_grafana.sh"
}

# Main installation process
main() {
    echo "🎯 Starting Grafana installation for VirtualPyTest..."
    
    # Install Grafana on Linux
    install_grafana
    
    # Setup PostgreSQL for metrics
    setup_postgresql
    
    # Setup Grafana configuration and database
    setup_grafana_config
    create_launch_script
    
    # Enable and start Grafana service
    echo ""
    echo "🚀 Enabling and starting Grafana service..."
    sudo systemctl enable grafana-server
    sudo systemctl start grafana-server
    
    # Wait for Grafana to start
    echo "⏳ Waiting for Grafana to start..."
    sleep 10
    
    # Check if Grafana is running
    if systemctl is-active --quiet grafana-server; then
        echo "✅ Grafana service is running"
    else
        echo "⚠️ Grafana service may not be running properly"
        echo "🔍 Checking Grafana status..."
        sudo systemctl status grafana-server --no-pager || true
        echo "📋 Recent Grafana logs:"
        sudo journalctl -u grafana-server --no-pager -n 10 || true
    fi
    
    echo ""
    echo "🎉 Grafana installation completed successfully!"
    echo ""
    echo "📋 What was installed:"
    echo "   ✅ Grafana server"
    echo "   ✅ PostgreSQL database for metrics (grafana_metrics)"
    echo "   ✅ Grafana configuration (copied from project)"
    echo "   ✅ Grafana database with all dashboards (copied from project)"
    echo "   ✅ Launch script"
    echo ""
    echo "🚀 To start Grafana:"
    echo "   ./setup/local/launch_grafana.sh"
    echo ""
echo "🌐 Access Grafana at:"
echo "   URL: http://localhost:3000"
echo "   Login: admin / admin123"
    echo ""
    echo "📊 Configuration files:"
    echo "   Config: grafana/config/grafana.ini"
    echo "   Data: grafana/data/"
    echo "   Logs: grafana/logs/"
    echo ""
    echo "💡 Next steps:"
    echo "   1. Start Grafana: ./setup/local/launch_grafana.sh"
    echo "   2. Configure SUPABASE_DB_URI environment variable (optional)"
    echo "   3. Import existing dashboards from backend_server/config/grafana/dashboards/"
    echo "   4. Create custom dashboards for your local metrics"
    echo ""
    echo "🔧 If you have CORS issues with Vite frontend:"
    echo "   Run: ./setup/local/fix_grafana_cors.sh"
}

# Run main installation
main

# Make the script executable
chmod +x "$PROJECT_ROOT/setup/local/install_grafana.sh"

echo "✅ Grafana installation script created"
