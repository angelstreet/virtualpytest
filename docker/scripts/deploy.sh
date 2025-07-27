#!/bin/bash
set -e

# VirtualPyTest Deployment Script

ENVIRONMENT=${1:-development}
COMPOSE_FILE=""

echo "🚀 Deploying VirtualPyTest to $ENVIRONMENT environment"

# Set compose file based on environment
case $ENVIRONMENT in
    "development"|"dev")
        COMPOSE_FILE="docker-compose.dev.yml"
        echo "📝 Using development configuration"
        ;;
    "production"|"prod")
        COMPOSE_FILE="docker-compose.prod.yml"
        echo "📝 Using production configuration"
        ;;
    "local")
        COMPOSE_FILE="docker-compose.yml"
        echo "📝 Using local configuration"
        ;;
    *)
        echo "❌ Unknown environment: $ENVIRONMENT"
        echo "Available environments: development, production, local"
        exit 1
        ;;
esac

# Navigate to docker directory
cd "$(dirname "$0")/.."

# Function to check if service is healthy
check_health() {
    local service=$1
    local max_attempts=30
    local attempt=1
    
    echo "🏥 Checking health of $service..."
    
    while [[ $attempt -le $max_attempts ]]; do
        if docker compose -f "$COMPOSE_FILE" ps "$service" | grep -q "healthy\|Up"; then
            echo "✅ $service is healthy"
            return 0
        fi
        
        echo "⏳ Attempt $attempt/$max_attempts: $service not ready yet..."
        sleep 5
        ((attempt++))
    done
    
    echo "❌ $service failed to become healthy"
    return 1
}

# Stop existing containers
echo "🛑 Stopping existing containers..."
docker compose -f "$COMPOSE_FILE" down --remove-orphans

# Pull latest images (if not building locally)
if [[ "$2" != "--no-pull" ]]; then
    echo "📥 Pulling latest images..."
    docker compose -f "$COMPOSE_FILE" pull
fi

# Start services
echo "🏃 Starting services..."
docker compose -f "$COMPOSE_FILE" up -d

# Check service health
if [[ "$ENVIRONMENT" == "production" ]] || [[ "$ENVIRONMENT" == "prod" ]]; then
    echo "🔍 Performing health checks..."
    
    # Check backend services first
    check_health "backend_server"
    check_health "backend_host"
    check_health "frontend"
    
    echo "✅ All services are healthy!"
fi

# Show running containers
echo ""
echo "📊 Running containers:"
docker compose -f "$COMPOSE_FILE" ps

# Show useful URLs
echo ""
echo "🌐 Service URLs:"
case $ENVIRONMENT in
    "development"|"dev")
        echo "  Frontend (Dev):     http://localhost:3000"
        echo "  Backend Server:     http://localhost:5109"
        echo "  Backend Host:       http://localhost:6109"
        ;;
    "production"|"prod")
        echo "  Frontend:           http://localhost:80"
        echo "  Backend Server:     http://localhost:5109"
        echo "  Backend Host:       http://localhost:6109"
        ;;
    "local")
        echo "  Frontend:           http://localhost:3000"
        echo "  Backend Server:     http://localhost:5109"
        echo "  Backend Host:       http://localhost:6109"
        ;;
esac

echo ""
echo "🎉 Deployment to $ENVIRONMENT complete!"
echo ""
echo "📋 Useful commands:"
echo "  View logs:          docker compose -f $COMPOSE_FILE logs -f"
echo "  Stop services:      docker compose -f $COMPOSE_FILE down"
echo "  Restart service:    docker compose -f $COMPOSE_FILE restart <service>" 