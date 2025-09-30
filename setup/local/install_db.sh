#!/bin/bash

# VirtualPyTest - Install Local Database
# This script creates a complete VirtualPyTest database using the migration files
# It sets up both the application database and Grafana metrics database
# Usage: ./install_db.sh [--force-clean]

set -e

# Parse command line arguments
FORCE_CLEAN=false
if [[ "$1" == "--force-clean" ]]; then
    FORCE_CLEAN=true
    echo "🗄️ Installing VirtualPyTest database (FORCE CLEAN)..."
    echo "🗑️ This will drop existing databases and recreate them..."
else
    echo "🗄️ Installing VirtualPyTest local database..."
fi

# Get to project root directory (from setup/local to project root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Change to project root
cd "$PROJECT_ROOT"

# Check if we're in the right directory
if [ ! -f "README.md" ] || [ ! -d "setup/db/schema" ]; then
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

# Function to setup VirtualPyTest application database
setup_virtualpytest_database() {
    echo "🚀 Setting up VirtualPyTest application database..."
    
    # Drop existing database if force clean
    if [ "$FORCE_CLEAN" = true ]; then
        echo "🗑️ Dropping existing VirtualPyTest database..."
        sudo -u postgres env LC_ALL=C.UTF-8 LANG=C.UTF-8 psql -c "DROP DATABASE IF EXISTS virtualpytest;" 2>/dev/null || true
        sudo -u postgres env LC_ALL=C.UTF-8 LANG=C.UTF-8 psql -c "DROP USER IF EXISTS virtualpytest_user;" 2>/dev/null || true
    fi
    
    # Create database and user for VirtualPyTest application
    sudo -u postgres env LC_ALL=C.UTF-8 LANG=C.UTF-8 psql -c "CREATE DATABASE virtualpytest;"
    sudo -u postgres env LC_ALL=C.UTF-8 LANG=C.UTF-8 psql -c "CREATE USER virtualpytest_user WITH PASSWORD 'virtualpytest_pass';"
    sudo -u postgres env LC_ALL=C.UTF-8 LANG=C.UTF-8 psql -c "GRANT ALL PRIVILEGES ON DATABASE virtualpytest TO virtualpytest_user;"
    sudo -u postgres env LC_ALL=C.UTF-8 LANG=C.UTF-8 psql -c "ALTER USER virtualpytest_user CREATEDB;"
    sudo -u postgres env LC_ALL=C.UTF-8 LANG=C.UTF-8 psql -c "ALTER USER virtualpytest_user SUPERUSER;"

    # Test the connection
    if PGPASSWORD=virtualpytest_pass psql -h localhost -U virtualpytest_user -d virtualpytest -c "SELECT version();" &> /dev/null; then
        echo "✅ VirtualPyTest database created successfully"
    else
        echo "❌ Failed to connect to VirtualPyTest database"
        exit 1
    fi
}

# Function to setup Grafana metrics database
setup_grafana_database() {
    echo "📊 Setting up Grafana metrics database..."
    
    # Drop existing database if force clean
    if [ "$FORCE_CLEAN" = true ]; then
        echo "🗑️ Dropping existing Grafana database..."
        sudo -u postgres env LC_ALL=C.UTF-8 LANG=C.UTF-8 psql -c "DROP DATABASE IF EXISTS grafana_metrics;" 2>/dev/null || true
        sudo -u postgres env LC_ALL=C.UTF-8 LANG=C.UTF-8 psql -c "DROP USER IF EXISTS grafana_user;" 2>/dev/null || true
    fi
    
    # Create database and user for Grafana metrics
    sudo -u postgres env LC_ALL=C.UTF-8 LANG=C.UTF-8 psql -c "CREATE DATABASE grafana_metrics;"
    sudo -u postgres env LC_ALL=C.UTF-8 LANG=C.UTF-8 psql -c "CREATE USER grafana_user WITH PASSWORD 'grafana_pass';"
    sudo -u postgres env LC_ALL=C.UTF-8 LANG=C.UTF-8 psql -c "GRANT ALL PRIVILEGES ON DATABASE grafana_metrics TO grafana_user;"
    sudo -u postgres env LC_ALL=C.UTF-8 LANG=C.UTF-8 psql -c "ALTER USER grafana_user CREATEDB;"

    # Test the connection
    if PGPASSWORD=grafana_pass psql -h localhost -U grafana_user -d grafana_metrics -c "SELECT version();" &> /dev/null; then
        echo "✅ Grafana database setup successful"
    else
        echo "❌ Failed to connect to Grafana database"
        exit 1
    fi
}

# Function to run migration files
run_migrations() {
    echo "📋 Running VirtualPyTest database migrations..."
    
    # Array of migration files in order
    MIGRATIONS=(
        "001_core_tables.sql"
        "002_ui_navigation_tables.sql"
        "003_test_execution_tables.sql"
        "004_actions_verifications.sql"
        "005_monitoring_analytics.sql"
        "006_parent_node_sync_triggers.sql"
        "007_system_monitoring_tables.sql"
        "008_ai_plan_generation.sql"
        "009_device_flags.sql"
        "010_ai_prompt_disambiguation.sql"
    )
    
    # Run each migration file
    for migration in "${MIGRATIONS[@]}"; do
        migration_file="setup/db/schema/$migration"
        
        if [ ! -f "$migration_file" ]; then
            echo "❌ Migration file not found: $migration_file"
            exit 1
        fi
        
        echo "🔄 Running migration: $migration"
        
        # Run the migration
        if PGPASSWORD=virtualpytest_pass psql -h localhost -U virtualpytest_user -d virtualpytest -f "$migration_file" &> /dev/null; then
            echo "✅ Migration completed: $migration"
        else
            echo "❌ Migration failed: $migration"
            echo "Checking for detailed error..."
            PGPASSWORD=virtualpytest_pass psql -h localhost -U virtualpytest_user -d virtualpytest -f "$migration_file"
            exit 1
        fi
    done
    
    echo "✅ All migrations completed successfully"
}

# Function to verify database setup
verify_database() {
    echo "🔍 Verifying database setup..."
    
    # Check if key tables exist
    EXPECTED_TABLES=(
        "teams"
        "device_models"
        "device"
        "userinterfaces"
        "navigation_trees"
        "navigation_nodes"
        "navigation_edges"
        "test_cases"
        "script_results"
        "alerts"
        "system_metrics"
        "system_device_metrics"
        "system_incident"
        "ai_plan_generation"
        "device_flags"
        "ai_prompt_disambiguation"
    )
    
    echo "📋 Checking for expected tables..."
    for table in "${EXPECTED_TABLES[@]}"; do
        if PGPASSWORD=virtualpytest_pass psql -h localhost -U virtualpytest_user -d virtualpytest -c "\d $table" &> /dev/null; then
            echo "✅ Table exists: $table"
        else
            echo "❌ Table missing: $table"
            exit 1
        fi
    done
    
    # Count total tables
    TABLE_COUNT=$(PGPASSWORD=virtualpytest_pass psql -h localhost -U virtualpytest_user -d virtualpytest -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" | xargs)
    echo "📊 Total tables created: $TABLE_COUNT"
    
    if [ "$TABLE_COUNT" -ge 26 ]; then
        echo "✅ Database verification successful"
    else
        echo "❌ Expected at least 26 tables, found $TABLE_COUNT"
        exit 1
    fi
}

# Function to create database configuration
create_database_config() {
    echo "⚙️ Creating database configuration..."
    
    # Create database config directory
    mkdir -p config/database
    
    # Create local database configuration file
    cat > config/database/local.env << 'EOF'
# VirtualPyTest Local Database Configuration
# This file contains database connection settings for local development

# VirtualPyTest Application Database
VIRTUALPYTEST_DB_HOST=localhost
VIRTUALPYTEST_DB_PORT=5432
VIRTUALPYTEST_DB_NAME=virtualpytest
VIRTUALPYTEST_DB_USER=virtualpytest_user
VIRTUALPYTEST_DB_PASSWORD=virtualpytest_pass
VIRTUALPYTEST_DB_URI=postgresql://virtualpytest_user:virtualpytest_pass@localhost:5432/virtualpytest

# Grafana Metrics Database
GRAFANA_DB_HOST=localhost
GRAFANA_DB_PORT=5432
GRAFANA_DB_NAME=grafana_metrics
GRAFANA_DB_USER=grafana_user
GRAFANA_DB_PASSWORD=grafana_pass
GRAFANA_DB_URI=postgresql://grafana_user:grafana_pass@localhost:5432/grafana_metrics
EOF

    echo "✅ Database configuration created at: config/database/local.env"
}

# Main installation flow
echo "🔍 Checking PostgreSQL installation..."
if ! check_postgresql; then
    echo "🔍 PostgreSQL not found, installing..."
    install_postgresql
else
    echo "✅ PostgreSQL already installed"
fi

# Setup databases - always setup if force clean, otherwise check if they exist
if [ "$FORCE_CLEAN" = true ]; then
    echo "🚀 Setting up VirtualPyTest database (FORCE CLEAN)..."
    setup_virtualpytest_database
    echo "📊 Setting up Grafana database (FORCE CLEAN)..."
    setup_grafana_database
else
    # Setup VirtualPyTest application database
    echo "🔍 Checking VirtualPyTest database setup..."
    if ! PGPASSWORD=virtualpytest_pass psql -h localhost -U virtualpytest_user -d virtualpytest -c "SELECT 1;" &> /dev/null; then
        echo "🚀 Setting up VirtualPyTest database..."
        setup_virtualpytest_database
    else
        echo "✅ VirtualPyTest database already configured"
    fi

    # Setup Grafana database
    echo "🔍 Checking Grafana database setup..."
    if ! PGPASSWORD=grafana_pass psql -h localhost -U grafana_user -d grafana_metrics -c "SELECT 1;" &> /dev/null; then
        echo "📊 Setting up Grafana database..."
        setup_grafana_database
    else
        echo "✅ Grafana database already configured"
    fi
fi

# Run migrations - always run if force clean, otherwise check if they're needed
echo "🔍 Checking if migrations need to be run..."
if [ "$FORCE_CLEAN" = true ]; then
    echo "📋 Running database migrations (FORCE CLEAN)..."
    run_migrations
else
    if ! PGPASSWORD=virtualpytest_pass psql -h localhost -U virtualpytest_user -d virtualpytest -c "SELECT 1 FROM teams LIMIT 1;" &> /dev/null; then
        echo "📋 Running database migrations..."
        run_migrations
    else
        echo "✅ Database migrations already applied"
    fi
fi

# Verify database setup
verify_database

# Create database configuration
create_database_config

echo ""
echo "✅ VirtualPyTest database installation completed!"
echo ""
echo "📋 Database Summary:"
echo "   🚀 Application DB: virtualpytest (user: virtualpytest_user)"
echo "   📊 Grafana DB:     grafana_metrics (user: grafana_user)"
echo "   📁 Config:         config/database/local.env"
echo ""
echo "🔧 Connection Details:"
echo "   Application: postgresql://virtualpytest_user:virtualpytest_pass@localhost:5432/virtualpytest"
echo "   Grafana:     postgresql://grafana_user:grafana_pass@localhost:5432/grafana_metrics"
echo ""
echo "📝 Next Steps:"
echo "1. Update your .env files to use the local database"
echo "2. Run: ./setup/local/install_all.sh to complete the setup"
echo ""
