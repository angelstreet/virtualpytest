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

# Detect OS
OS=""
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
else
    echo "❌ Unsupported operating system: $OSTYPE"
    echo "This script supports Linux and macOS only"
    exit 1
fi

echo "🖥️ Detected OS: $OS"

# Function to install Grafana on macOS
install_grafana_macos() {
    echo "🍺 Installing Grafana on macOS..."
    
    # Check if Homebrew is installed
    if ! command -v brew &> /dev/null; then
        echo "❌ Homebrew is required but not installed"
        echo "Please install Homebrew first: https://brew.sh/"
        exit 1
    fi
    
    # Install Grafana
    if brew list grafana &> /dev/null; then
        echo "✅ Grafana is already installed"
    else
        echo "📦 Installing Grafana via Homebrew..."
        brew install grafana
    fi
    
    # Get Grafana paths
    GRAFANA_HOME="/usr/local/var/lib/grafana"
    GRAFANA_LOGS="/usr/local/var/log/grafana"
    GRAFANA_CONF="/usr/local/etc/grafana/grafana.ini"
    GRAFANA_BIN="/usr/local/bin/grafana-server"
    
    # Create directories if they don't exist
    mkdir -p "$GRAFANA_HOME"
    mkdir -p "$GRAFANA_LOGS"
    mkdir -p "$(dirname "$GRAFANA_CONF")"
}

# Function to install Grafana on Linux
install_grafana_linux() {
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
        if [[ "$OS" == "macos" ]]; then
            echo "  brew install postgresql"
        else
            echo "  sudo apt-get install postgresql postgresql-contrib  # Ubuntu/Debian"
            echo "  sudo yum install postgresql-server postgresql-contrib  # RHEL/CentOS"
        fi
        exit 1
    fi
    
    # Check if PostgreSQL is running
    if ! pg_isready &> /dev/null; then
        echo "🚀 Starting PostgreSQL..."
        if [[ "$OS" == "macos" ]]; then
            brew services start postgresql
        else
            sudo systemctl start postgresql
            sudo systemctl enable postgresql
        fi
        
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
    if [[ "$OS" == "macos" ]]; then
        # On macOS, usually no password required for local connections
        psql postgres -c "CREATE DATABASE grafana_metrics;" 2>/dev/null || echo "Database grafana_metrics already exists"
        psql postgres -c "CREATE USER grafana_user WITH PASSWORD 'grafana_pass';" 2>/dev/null || echo "User grafana_user already exists"
        psql postgres -c "GRANT ALL PRIVILEGES ON DATABASE grafana_metrics TO grafana_user;" 2>/dev/null || true
        psql postgres -c "ALTER USER grafana_user CREATEDB;" 2>/dev/null || true
    else
        # On Linux, use sudo to run as postgres user
        sudo -u postgres psql -c "CREATE DATABASE grafana_metrics;" 2>/dev/null || echo "Database grafana_metrics already exists"
        sudo -u postgres psql -c "CREATE USER grafana_user WITH PASSWORD 'grafana_pass';" 2>/dev/null || echo "User grafana_user already exists"
        sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE grafana_metrics TO grafana_user;" 2>/dev/null || true
        sudo -u postgres psql -c "ALTER USER grafana_user CREATEDB;" 2>/dev/null || true
    fi
    
    # Test the connection
    if PGPASSWORD=grafana_pass psql -h localhost -U grafana_user -d grafana_metrics -c "SELECT version();" &> /dev/null; then
        echo "✅ Grafana database setup successful"
    else
        echo "❌ Failed to connect to Grafana database"
        exit 1
    fi
}

# Function to create local Grafana configuration
create_grafana_config() {
    echo "⚙️ Creating local Grafana configuration..."
    
    # Create local Grafana config directory
    mkdir -p "$PROJECT_ROOT/grafana/config"
    mkdir -p "$PROJECT_ROOT/grafana/data"
    mkdir -p "$PROJECT_ROOT/grafana/logs"
    mkdir -p "$PROJECT_ROOT/grafana/provisioning/datasources"
    mkdir -p "$PROJECT_ROOT/grafana/provisioning/dashboards"
    
    # Create local Grafana configuration file
    cat > "$PROJECT_ROOT/grafana/config/grafana-local.ini" << 'EOF'
##################### Grafana Local Configuration #####################

[paths]
# Local data directory
data = ./grafana/data
logs = ./grafana/logs
plugins = ./grafana/plugins
provisioning = ./grafana/provisioning

[server]
# Local server configuration
protocol = http
http_addr = 127.0.0.1
http_port = 3001
domain = localhost
root_url = http://localhost:3001/

[database]
# Use local SQLite for Grafana metadata
type = sqlite3
path = grafana.db

[security]
# Local development security settings
admin_user = admin
admin_password = admin123
secret_key = virtualpytest_local_secret_key
allow_embedding = true
cookie_secure = false

[auth.anonymous]
# Enable anonymous access for local development
enabled = true
org_name = Main Org.
org_role = Viewer

[users]
# Allow sign up for local development
allow_sign_up = true
auto_assign_org = true
auto_assign_org_role = Editor
default_theme = dark

[analytics]
# Disable analytics for local development
reporting_enabled = false
check_for_updates = false

[log]
mode = console file
level = info

[log.console]
level = info
format = console

[log.file]
level = info
format = text
log_rotate = true
max_lines = 1000000
max_size_shift = 28
daily_rotate = true
max_days = 7
EOF

    echo "✅ Local Grafana configuration created"
}

# Function to create datasource configurations
create_datasource_config() {
    echo "🔌 Creating datasource configurations..."
    
    # Create local datasource configuration
    cat > "$PROJECT_ROOT/grafana/provisioning/datasources/local.yml" << 'EOF'
# Local Grafana datasource configuration for VirtualPyTest
apiVersion: 1

datasources:
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
    
  # Supabase PostgreSQL - READ ONLY for fetching application data (if configured)
  - name: VirtualPyTest Supabase (Read-Only)
    type: postgres
    access: proxy
    url: ${SUPABASE_DB_URI:-postgres://user:pass@localhost:5432/postgres}
    jsonData:
      sslmode: require
      postgresVersion: 1300
      timescaledb: false
      maxOpenConns: 3
      maxIdleConns: 1
      connMaxLifetime: 14400
    # NOT default datasource
    isDefault: false
    # Read-only access
    editable: false
EOF

    echo "✅ Datasource configuration created"
}

# Function to create dashboard provisioning
create_dashboard_config() {
    echo "📊 Creating dashboard provisioning configuration..."
    
    # Create dashboard provisioning configuration
    cat > "$PROJECT_ROOT/grafana/provisioning/dashboards/dashboards.yml" << 'EOF'
apiVersion: 1

providers:
  # VirtualPyTest dashboards from backend_server config
  - name: 'VirtualPyTest Dashboards'
    orgId: 1
    folder: 'VirtualPyTest'
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: ./backend_server/config/grafana/dashboards
      
  # Local development dashboards
  - name: 'Local Development'
    orgId: 1
    folder: 'Local'
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: ./grafana/dashboards
EOF

    # Create local dashboards directory
    mkdir -p "$PROJECT_ROOT/grafana/dashboards"
    
    # Create a simple local development dashboard
    cat > "$PROJECT_ROOT/grafana/dashboards/local-development.json" << 'EOF'
{
  "dashboard": {
    "id": null,
    "title": "Local Development Overview",
    "tags": ["local", "development"],
    "timezone": "browser",
    "panels": [
      {
        "id": 1,
        "title": "Welcome to Local Grafana",
        "type": "text",
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
        "options": {
          "mode": "markdown",
          "content": "# Welcome to VirtualPyTest Local Grafana\n\nThis is your local Grafana instance for development and testing.\n\n## Quick Links\n- [Datasources](http://localhost:3000/datasources)\n- [Dashboard Settings](http://localhost:3000/dashboard/settings)\n- [Explore](http://localhost:3000/explore)\n\n## Next Steps\n1. Configure your datasources\n2. Import VirtualPyTest dashboards\n3. Create custom panels for your metrics\n\n**Note**: This is running in local development mode with anonymous access enabled."
        }
      }
    ],
    "time": {"from": "now-6h", "to": "now"},
    "refresh": "30s",
    "schemaVersion": 30,
    "version": 1
  }
}
EOF

    echo "✅ Dashboard configuration created"
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

# Check if configuration exists
if [ ! -f "grafana/config/grafana-local.ini" ]; then
    echo "❌ Grafana configuration not found"
    echo "Please run: ./setup/local/install_grafana.sh"
    exit 1
fi

# Check if PostgreSQL is running (for metrics storage)
if ! pg_isready &> /dev/null; then
    echo "🐘 Starting PostgreSQL..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        brew services start postgresql
    else
        sudo systemctl start postgresql
    fi
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
echo "📊 Grafana will be available at: http://localhost:3001"
echo "🔑 Login: admin / admin123"
echo "💡 Press Ctrl+C to stop"

# Start Grafana server
grafana-server \
    --config="$PROJECT_ROOT/grafana/config/grafana-local.ini" \
    --homepath="$PROJECT_ROOT/grafana" \
    web
EOF

    # Make launch script executable
    chmod +x "$PROJECT_ROOT/setup/local/launch_grafana.sh"
    
    echo "✅ Launch script created at setup/local/launch_grafana.sh"
}

# Main installation process
main() {
    echo "🎯 Starting Grafana installation for VirtualPyTest..."
    
    # Install Grafana based on OS
    if [[ "$OS" == "macos" ]]; then
        install_grafana_macos
    else
        install_grafana_linux
    fi
    
    # Setup PostgreSQL for metrics
    setup_postgresql
    
    # Create local configurations
    create_grafana_config
    create_datasource_config
    create_dashboard_config
    create_launch_script
    
    echo ""
    echo "🎉 Grafana installation completed successfully!"
    echo ""
    echo "📋 What was installed:"
    echo "   ✅ Grafana server"
    echo "   ✅ PostgreSQL database for metrics (grafana_metrics)"
    echo "   ✅ Local Grafana configuration"
    echo "   ✅ Datasource configurations"
    echo "   ✅ Dashboard provisioning"
    echo "   ✅ Launch script"
    echo ""
    echo "🚀 To start Grafana:"
    echo "   ./setup/local/launch_grafana.sh"
    echo ""
echo "🌐 Access Grafana at:"
echo "   URL: http://localhost:3001"
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
}

# Run main installation
main
EOF

# Make the script executable
chmod +x "$PROJECT_ROOT/setup/local/install_grafana.sh"

echo "✅ Grafana installation script created"
