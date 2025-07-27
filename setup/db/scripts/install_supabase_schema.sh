#!/bin/bash

# VirtualPyTest - Install Database Schema on Supabase
# This script creates all required tables and indexes in a Supabase database

set -e

echo "🗄️ VirtualPyTest Database Schema Installation"
echo "=============================================="

# Get to project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
SCHEMA_DIR="$PROJECT_ROOT/setup/db/schema"

# Change to project root
cd "$PROJECT_ROOT"

# Load environment variables from .env file in setup directory
ENV_FILE="$PROJECT_ROOT/setup/.env"
if [ -f "$ENV_FILE" ]; then
    echo "📄 Loading environment variables from .env file..."
    # Export variables from .env file
    export $(grep -v '^#' "$ENV_FILE" | grep -v '^$' | xargs)
    echo "✅ Environment variables loaded"
else
    echo "⚠️ .env file not found at: $ENV_FILE"
    echo "💡 Creating example .env file..."
    cat > "$ENV_FILE" << 'EOF'
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here

# You can find these values in your Supabase project settings:
# 1. Go to https://app.supabase.com/project/YOUR_PROJECT/settings/api
# 2. Copy the URL and service_role key
EOF
    echo "📝 Created example .env file in setup/ directory"
    echo "   Please edit $ENV_FILE with your Supabase credentials"
    exit 1
fi

# Check if required environment variables are set
if [ -z "$SUPABASE_URL" ] || [ -z "$SUPABASE_SERVICE_ROLE_KEY" ]; then
    echo "❌ Required environment variables not set in .env file:"
    echo "   SUPABASE_URL - Your Supabase project URL"
    echo "   SUPABASE_SERVICE_ROLE_KEY - Your Supabase service role key"
    echo ""
    echo "💡 You can find these in your Supabase project settings:"
    echo "   1. Go to https://app.supabase.com/project/YOUR_PROJECT/settings/api"
    echo "   2. Copy the URL and service_role key"
    echo ""
    echo "💡 Update your .env file with:"
    echo "   SUPABASE_URL='https://your-project.supabase.co'"
    echo "   SUPABASE_SERVICE_ROLE_KEY='your-service-role-key'"
    exit 1
fi

# Install psql if not available
if ! command -v psql &> /dev/null; then
    echo "📦 Installing PostgreSQL client..."
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo apt-get update && sudo apt-get install -y postgresql-client
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        brew install postgresql
    else
        echo "❌ Please install PostgreSQL client (psql) manually"
        exit 1
    fi
fi

# Parse Supabase URL to get connection details
SUPABASE_HOST=$(echo $SUPABASE_URL | sed 's|https://||' | sed 's|http://||')
DB_URL="postgresql://postgres:$SUPABASE_SERVICE_ROLE_KEY@db.$SUPABASE_HOST:5432/postgres"

echo "🔍 Testing database connection..."
if ! psql "$DB_URL" -c "SELECT 1;" &> /dev/null; then
    echo "❌ Failed to connect to Supabase database"
    echo "   Please check your SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY"
    exit 1
fi

echo "✅ Database connection successful"
echo ""

# Function to execute SQL file
execute_sql_file() {
    local file=$1
    local description=$2
    
    echo "📄 Executing: $description"
    echo "   File: $file"
    
    if [ ! -f "$file" ]; then
        echo "❌ Schema file not found: $file"
        exit 1
    fi
    
    if psql "$DB_URL" -f "$file"; then
        echo "✅ $description completed successfully"
    else
        echo "❌ Failed to execute: $description"
        exit 1
    fi
    echo ""
}

# Execute schema files in order
echo "🚀 Installing VirtualPyTest database schema..."
echo ""

execute_sql_file "$SCHEMA_DIR/001_core_tables.sql" "Core Tables (devices, models, controllers, environments, campaigns)"
execute_sql_file "$SCHEMA_DIR/002_ui_navigation_tables.sql" "UI & Navigation Tables (userinterfaces, navigation_trees, history)"
execute_sql_file "$SCHEMA_DIR/003_test_execution_tables.sql" "Test Execution Tables (test_cases, executions, results)"
execute_sql_file "$SCHEMA_DIR/004_actions_verifications.sql" "Actions & Verifications Tables (actions, verifications, references)"
execute_sql_file "$SCHEMA_DIR/005_monitoring_analytics.sql" "Monitoring & Analytics Tables (alerts, heatmaps, metrics)"

# Verify installation
echo "🔍 Verifying installation..."
TABLE_COUNT=$(psql "$DB_URL" -t -c "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE';")
echo "📊 Created $TABLE_COUNT tables"

if [ "$TABLE_COUNT" -ge 20 ]; then
    echo "✅ All tables created successfully!"
else
    echo "⚠️ Expected 20+ tables, but found $TABLE_COUNT"
    echo "   Some tables may not have been created properly"
fi

echo ""
echo "🎉 VirtualPyTest database schema installation complete!"
echo ""
echo "📋 Next steps:"
echo "   1. Update your application .env files with database credentials"
echo "   2. Test the connection from your application"
echo "   3. Optionally run: ./setup/db/scripts/seed_example_data.sh"
echo ""
echo "🔗 Useful links:"
echo "   • Supabase Dashboard: https://app.supabase.com/project/$(echo $SUPABASE_URL | sed 's|https://||' | sed 's|\.supabase\.co||' | sed 's|.*//||')"
echo "   • Database Tables: https://app.supabase.com/project/$(echo $SUPABASE_URL | sed 's|https://||' | sed 's|\.supabase\.co||' | sed 's|.*//||')/editor" 