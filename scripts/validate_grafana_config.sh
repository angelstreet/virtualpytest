#!/bin/bash

# Grafana Configuration Validation Script
echo "🔍 Validating Grafana configuration..."

# Check if separate Grafana folder exists
if [ -d "grafana/config" ]; then
    echo "✅ Separate grafana/config directory exists"
else
    echo "❌ Missing grafana/config directory"
    exit 1
fi

# Check if grafana.ini exists
if [ -f "grafana/config/grafana.ini" ]; then
    echo "✅ grafana.ini found in separate folder"
else
    echo "❌ Missing grafana/config/grafana.ini"
    exit 1
fi

# Check if grafana data directory exists
if [ -d "grafana/data" ]; then
    echo "✅ Separate grafana/data directory exists"
else
    echo "❌ Missing grafana/data directory"
    exit 1
fi

# Check Dockerfile for correct COPY commands
if grep -q "COPY grafana/config/ backend_server/config/grafana/" backend_server/Dockerfile; then
    echo "✅ Dockerfile copies grafana config correctly"
else
    echo "❌ Dockerfile missing grafana config copy command"
    exit 1
fi

if grep -q "COPY grafana/data/ backend_server/config/grafana/data/" backend_server/Dockerfile; then
    echo "✅ Dockerfile copies grafana data correctly"
else
    echo "❌ Dockerfile missing grafana data copy command"
    exit 1
fi

# Check supervisor configuration
if grep -q '/app/backend_server/config/grafana/grafana.ini' backend_server/config/supervisor/supervisord.conf; then
    echo "✅ Supervisor configuration points to correct grafana.ini path"
else
    echo "❌ Supervisor configuration has incorrect grafana.ini path"
    exit 1
fi

echo ""
echo "🎉 All Grafana configuration checks passed!"
echo ""
echo "📋 Summary:"
echo "   • Grafana config: grafana/config/grafana.ini (separate folder)"
echo "   • Grafana data: grafana/data/ (separate folder)"
echo "   • Docker copies to: /app/backend_server/config/grafana/"
echo "   • Supervisor uses: /app/backend_server/config/grafana/grafana.ini"
echo ""
echo "🚀 Ready to build and run!"
