#!/bin/bash

# VirtualPyTest - Test Database Setup
# This script tests if the database setup is working correctly

set -e

echo "🧪 Testing VirtualPyTest database setup..."

# Test VirtualPyTest database connection
echo "🔍 Testing VirtualPyTest database connection..."
if PGPASSWORD=virtualpytest_pass psql -h localhost -U virtualpytest_user -d virtualpytest -c "SELECT 'VirtualPyTest DB connection successful!' as status;" 2>/dev/null; then
    echo "✅ VirtualPyTest database connection successful"
else
    echo "❌ VirtualPyTest database connection failed"
    exit 1
fi

# Test Grafana database connection
echo "🔍 Testing Grafana database connection..."
if PGPASSWORD=grafana_pass psql -h localhost -U grafana_user -d grafana_metrics -c "SELECT 'Grafana DB connection successful!' as status;" 2>/dev/null; then
    echo "✅ Grafana database connection successful"
else
    echo "❌ Grafana database connection failed"
    exit 1
fi

# Test key tables exist
echo "🔍 Testing key tables exist..."
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
)

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
echo "📊 Total tables: $TABLE_COUNT"

# Test database configuration file
echo "🔍 Testing database configuration file..."
if [ -f "config/database/local.env" ]; then
    echo "✅ Database configuration file exists"
    echo "📁 Config file: config/database/local.env"
else
    echo "❌ Database configuration file missing"
    exit 1
fi

echo ""
echo "🎉 All database tests passed!"
echo ""
echo "📋 Summary:"
echo "   🚀 VirtualPyTest DB: ✅ Connected ($TABLE_COUNT tables)"
echo "   📊 Grafana DB: ✅ Connected"
echo "   📁 Config: ✅ Available"
echo ""
echo "🔧 Connection strings:"
echo "   App: postgresql://virtualpytest_user:virtualpytest_pass@localhost:5432/virtualpytest"
echo "   Grafana: postgresql://grafana_user:grafana_pass@localhost:5432/grafana_metrics"
echo ""
