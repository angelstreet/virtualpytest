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
    
    # Detect OS and install accordingly
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux (including Raspberry Pi)
        if command -v apt-get &> /dev/null; then
            sudo apt-get update
            sudo apt-get install -y postgresql postgresql-contrib
        elif command -v yum &> /dev/null; then
            sudo yum install -y postgresql postgresql-server postgresql-contrib
            sudo postgresql-setup initdb
        elif command -v pacman &> /dev/null; then
            sudo pacman -S postgresql
            sudo -u postgres initdb -D /var/lib/postgres/data
        fi
        
        # Start and enable PostgreSQL
        sudo systemctl start postgresql
        sudo systemctl enable postgresql
        
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            brew install postgresql
            brew services start postgresql
        else
            echo "❌ Homebrew not found. Please install PostgreSQL manually."
            exit 1
        fi
    else
        echo "❌ Unsupported OS. Please install PostgreSQL manually."
        exit 1
    fi
    
    echo "✅ PostgreSQL installed successfully"
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

# Skip backend_core installation - using direct imports instead
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
echo "   • Access Grafana at: http://localhost:3001 (when server is running)"
echo "" 