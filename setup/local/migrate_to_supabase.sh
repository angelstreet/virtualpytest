#!/bin/bash

# VirtualPyTest - Migrate Main Database to Supabase Cloud
# This script helps migrate from local PostgreSQL to Supabase cloud
# Usage: ./migrate_to_supabase.sh

set -e

echo "🌩️ VirtualPyTest - Supabase Cloud Migration Helper"
echo "=================================================="
echo ""
echo "This script will help you migrate your main database to Supabase cloud."
echo "⚠️  IMPORTANT: This only migrates the main application database."
echo "    Grafana metrics will remain on local PostgreSQL for performance."
echo ""

# Get to project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Change to project root
cd "$PROJECT_ROOT"

# Check if we're in the right directory
if [ ! -f "README.md" ] || [ ! -d "shared" ]; then
    echo "❌ Could not find virtualpytest project root directory"
    echo "Current directory: $(pwd)"
    exit 1
fi

echo "📁 Project root: $PROJECT_ROOT"
echo ""

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found. Please run ./setup/local/install_all.sh first."
    exit 1
fi

# Backup current .env
echo "💾 Creating backup of current configuration..."
cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
echo "✅ Backup created: .env.backup.$(date +%Y%m%d_%H%M%S)"
echo ""

# Collect Supabase information
echo "🔑 Please provide your Supabase project details:"
echo "   (You can find these in your Supabase dashboard → Settings → API)"
echo ""

read -p "📍 Supabase Project URL (https://your-project-id.supabase.co): " SUPABASE_URL
if [ -z "$SUPABASE_URL" ]; then
    echo "❌ Supabase URL is required"
    exit 1
fi

read -p "🔑 Supabase Anonymous Key: " SUPABASE_ANON_KEY
if [ -z "$SUPABASE_ANON_KEY" ]; then
    echo "❌ Supabase Anonymous Key is required"
    exit 1
fi

read -p "🔐 Supabase Service Role Key: " SUPABASE_SERVICE_ROLE_KEY
if [ -z "$SUPABASE_SERVICE_ROLE_KEY" ]; then
    echo "❌ Supabase Service Role Key is required"
    exit 1
fi

read -p "🔒 Supabase Database Password: " SUPABASE_DB_PASSWORD
if [ -z "$SUPABASE_DB_PASSWORD" ]; then
    echo "❌ Supabase Database Password is required"
    exit 1
fi

# Extract project ID from URL
PROJECT_ID=$(echo "$SUPABASE_URL" | sed 's|https://||' | sed 's|\.supabase\.co||')
if [ -z "$PROJECT_ID" ]; then
    echo "❌ Could not extract project ID from URL"
    exit 1
fi

echo ""
echo "📋 Configuration Summary:"
echo "   Project URL: $SUPABASE_URL"
echo "   Project ID: $PROJECT_ID"
echo "   Database Host: db.$PROJECT_ID.supabase.co"
echo ""

read -p "🤔 Does this look correct? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Migration cancelled"
    exit 1
fi

echo ""
echo "🔄 Updating .env configuration..."

# Create temporary file with new configuration
cat > .env.temp << EOF
# Local Development Environment Configuration
# Updated for Supabase Cloud Migration: $(date)

# =============================================================================
# DATABASE CONFIGURATION - SUPABASE CLOUD
# =============================================================================

# Supabase Configuration (ENABLED for cloud database)
DATABASE_URL=postgresql://postgres:$SUPABASE_DB_PASSWORD@db.$PROJECT_ID.supabase.co:5432/postgres
NEXT_PUBLIC_SUPABASE_URL=$SUPABASE_URL
NEXT_PUBLIC_SUPABASE_ANON_KEY=$SUPABASE_ANON_KEY
SUPABASE_SERVICE_ROLE_KEY=$SUPABASE_SERVICE_ROLE_KEY

# Database connection details (for Supabase)
DB_HOST=db.$PROJECT_ID.supabase.co
DB_PORT=5432
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=$SUPABASE_DB_PASSWORD

# Local PostgreSQL (DISABLED - migrated to Supabase)
# POSTGRES_HOST=localhost
# POSTGRES_PORT=5432
# POSTGRES_DB=virtualpytest
# POSTGRES_USER=vpt_user
# POSTGRES_PASSWORD=vpt_local_pass

EOF

# Append the rest of the .env file (non-database settings)
echo "# =============================================================================" >> .env.temp
echo "# SERVER CONFIGURATION" >> .env.temp
echo "# =============================================================================" >> .env.temp
echo "" >> .env.temp

# Extract non-database configuration from existing .env
grep -E "^(SERVER_|HOST_|CORS_|ENVIRONMENT|DEBUG|FLASK_)" .env >> .env.temp || true

echo "" >> .env.temp
echo "# =============================================================================" >> .env.temp
echo "# GRAFANA CONFIGURATION - KEEP LOCAL FOR PERFORMANCE" >> .env.temp
echo "# =============================================================================" >> .env.temp
echo "" >> .env.temp

# Extract Grafana configuration from existing .env
grep -E "^(GRAFANA_|GF_)" .env >> .env.temp || true

# Add any other configuration that's not database or server related
echo "" >> .env.temp
echo "# =============================================================================" >> .env.temp
echo "# OTHER CONFIGURATION" >> .env.temp
echo "# =============================================================================" >> .env.temp
echo "" >> .env.temp

# Extract other configuration
grep -v -E "^(DATABASE_|POSTGRES_|SUPABASE_|DB_|SERVER_|HOST_|CORS_|ENVIRONMENT|DEBUG|FLASK_|GRAFANA_|GF_|#|^$)" .env >> .env.temp || true

# Replace the .env file
mv .env.temp .env

echo "✅ Configuration updated successfully"
echo ""

# Test connection to Supabase
echo "🔍 Testing connection to Supabase..."
if command -v curl >/dev/null 2>&1; then
    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
        -H "apikey: $SUPABASE_ANON_KEY" \
        -H "Authorization: Bearer $SUPABASE_ANON_KEY" \
        "$SUPABASE_URL/rest/v1/")
    
    if [ "$HTTP_STATUS" = "200" ]; then
        echo "✅ Connection to Supabase successful"
    else
        echo "⚠️  Connection test returned HTTP $HTTP_STATUS"
        echo "   This might be normal if you haven't set up the schema yet"
    fi
else
    echo "⚠️  curl not available, skipping connection test"
fi

echo ""
echo "📊 Next Steps:"
echo ""
echo "1. 🗄️  Set up your database schema in Supabase:"
echo "   → Go to your Supabase dashboard → SQL Editor"
echo "   → Execute the schema files in order:"
echo "     • setup/db/schema/001_core_tables.sql"
echo "     • setup/db/schema/002_ui_navigation_tables.sql"
echo "     • setup/db/schema/003_test_execution_tables.sql"
echo "     • setup/db/schema/004_actions_verifications.sql"
echo "     • setup/db/schema/005_monitoring_analytics.sql"
echo ""
echo "2. 🚀 Restart VirtualPyTest services:"
echo "   ./scripts/launch_virtualpytest.sh"
echo ""
echo "3. 🧪 Test the migration:"
echo "   → Open http://localhost:3000"
echo "   → Try creating a test device"
echo "   → Check if it appears in Supabase Table Editor"
echo ""
echo "4. 📖 For detailed instructions, see:"
echo "   docs_new/user/supabase_cloud.md"
echo ""

# Check if local PostgreSQL is still running
if systemctl is-active --quiet postgresql 2>/dev/null; then
    echo "ℹ️  Local PostgreSQL is still running (this is normal)."
    echo "   It's being used for Grafana metrics storage."
    echo ""
fi

echo "🔄 Rollback Instructions (if needed):"
echo "   # Restore previous configuration"
echo "   cp .env.backup.* .env"
echo "   ./scripts/launch_virtualpytest.sh"
echo ""

echo "=================================================================="
echo "🌩️ Supabase Migration Helper Complete!"
echo "=================================================================="
echo ""
echo "Your main database configuration has been updated to use Supabase."
echo "Don't forget to set up the database schema in your Supabase dashboard!"
echo ""
