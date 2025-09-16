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

# Function to setup local Grafana configuration
setup_grafana_config() {
    echo "⚙️ Setting up local Grafana configuration..."
    
    # Create Grafana directories
    if [[ "$OS" == "linux" ]]; then
        # On Linux, use system directories
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
        
        # Update configuration for local use (change port to 3001 to avoid conflicts)
        sudo sed -i 's/http_port = 3000/http_port = 3001/' /etc/grafana/grafana.ini
        sudo sed -i 's/domain = dev.virtualpytest.com/domain = localhost/' /etc/grafana/grafana.ini
        sudo sed -i 's|root_url = https://dev.virtualpytest.com/grafana/|root_url = http://localhost:3001/|' /etc/grafana/grafana.ini
        sudo sed -i 's/serve_from_sub_path = true/serve_from_sub_path = false/' /etc/grafana/grafana.ini
        
        # Set proper permissions
        sudo chown -R grafana:grafana /var/lib/grafana
        sudo chown -R grafana:grafana /var/log/grafana
        sudo chown grafana:grafana /etc/grafana/grafana.ini
        
    else
        # On macOS, use local directories
        mkdir -p "$GRAFANA_HOME"
        mkdir -p "$GRAFANA_LOGS"
        mkdir -p "$(dirname "$GRAFANA_CONF")"
        
        # Copy the pre-configured database with all dashboards (if it exists)
        if [ -f "$PROJECT_ROOT/grafana/data/grafana.db" ]; then
            echo "📊 Copying Grafana database with dashboards..."
            cp "$PROJECT_ROOT/grafana/data/grafana.db" "$GRAFANA_HOME/"
        else
            echo "⚠️ Pre-configured Grafana database not found, Grafana will create a fresh one"
            echo "📊 Creating empty Grafana database directory..."
            # Grafana will create its own database on first startup
        fi
        
        # Copy and modify configuration for local use
        echo "⚙️ Copying Grafana configuration..."
        cp "$PROJECT_ROOT/grafana/config/grafana.ini" "$GRAFANA_CONF"
        
        # Update configuration for local use (change port to 3001 to avoid conflicts)
        sed -i '' 's/http_port = 3000/http_port = 3001/' "$GRAFANA_CONF"
        sed -i '' 's/domain = dev.virtualpytest.com/domain = localhost/' "$GRAFANA_CONF"
        sed -i '' 's|root_url = https://dev.virtualpytest.com/grafana/|root_url = http://localhost:3001/|' "$GRAFANA_CONF"
        sed -i '' 's/serve_from_sub_path = true/serve_from_sub_path = false/' "$GRAFANA_CONF"
    fi
    
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

# Check if Grafana is configured
if [[ "$OSTYPE" == "darwin"* ]]; then
    GRAFANA_CONF="/usr/local/etc/grafana/grafana.ini"
else
    GRAFANA_CONF="/etc/grafana/grafana.ini"
fi

if [ ! -f "$GRAFANA_CONF" ]; then
    echo "❌ Grafana configuration not found at $GRAFANA_CONF"
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

# Start Grafana server using system configuration
if [[ "$OSTYPE" == "darwin"* ]]; then
    # On macOS, start with Homebrew paths
    grafana-server \
        --config="$GRAFANA_CONF" \
        --homepath="/usr/local/share/grafana" \
        web
else
    # On Linux, start with system paths
    grafana-server \
        --config="$GRAFANA_CONF" \
        --homepath="/usr/share/grafana" \
        web
fi
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
    
    # Setup Grafana configuration and database
    setup_grafana_config
    create_launch_script
    
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

# Make the script executable
chmod +x "$PROJECT_ROOT/setup/local/install_grafana.sh"

echo "✅ Grafana installation script created"
