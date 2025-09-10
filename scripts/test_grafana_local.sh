#!/bin/bash
# Test Grafana setup locally with persistent storage

set -e

echo "🚀 Testing Grafana setup locally..."

# Create local directories for Grafana data
echo "📁 Creating local Grafana directories..."
mkdir -p grafana/data
mkdir -p grafana/logs

# Set proper permissions (may require sudo on some systems)
echo "🔒 Setting permissions..."
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux - might need sudo
    if command -v sudo &> /dev/null; then
        sudo chown -R 472:472 grafana/data grafana/logs
    else
        chown -R 472:472 grafana/data grafana/logs
    fi
elif [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS - permissions might be different
    chmod -R 755 grafana/data grafana/logs
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found. Grafana won't be able to connect to Supabase as a datasource."
    echo "   Create a .env file with your Supabase credentials if you want to query your database."
fi

# Navigate to docker directory
cd docker

# Stop any existing containers
echo "🛑 Stopping existing containers..."
docker-compose -f docker-compose.yml down --volumes  # Use --volumes to clean up if needed, but warn user

# Build and start the backend_server with Grafana
echo "🔨 Building and starting services..."
docker-compose -f docker-compose.yml up --build -d backend_server  # Only start backend_server for testing

# Wait for services to start
echo "⏳ Waiting for services to start..."
sleep 10

# Check service health
echo "🏥 Checking service health..."
docker-compose -f docker-compose.yml ps backend_server

# Show logs
echo "📋 Showing initial logs..."
docker-compose -f docker-compose.yml logs --tail=50 backend_server

echo ""
echo "✅ Grafana test setup complete!"
echo ""
echo "🌐 Access points:"
echo "   - Flask API: http://localhost:5109"
echo "   - Grafana (via proxy): http://localhost:5109/grafana"
echo "   - Grafana (direct): http://localhost:3001"
echo ""
echo "📝 Default Grafana credentials:"
echo "   - Username: admin"
echo "   - Password: admin123"
echo ""
echo "📊 To view logs:"
echo "   docker-compose -f setup/docker/docker-compose.yml logs -f backend_server"
echo ""
echo "🛑 To stop:"
echo "   docker-compose -f setup/docker/docker-compose.yml down"
