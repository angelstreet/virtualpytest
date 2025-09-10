#!/bin/bash
set -e

# VirtualPyTest Docker Build Script

echo "🏗️ Building VirtualPyTest Docker Images"

# Build order: shared -> backend_core -> backend_host/backend_server -> frontend
BUILD_ORDER=(
    "shared"
    "backend_core" 
    "backend_host"
    "backend_server"
    "frontend"
)

# Function to build individual service
build_service() {
    local service=$1
    echo "📦 Building $service..."
    
    case $service in
        "shared")
            docker build -f ../shared/Dockerfile -t virtualpytest/shared:latest ..
            ;;
        "backend_core")
            docker build -f ../backend_core/Dockerfile -t virtualpytest/backend_core:latest ..
            ;;
        "backend_host")
            docker build -f ../backend_host/Dockerfile -t virtualpytest/backend_host:latest ..
            ;;
        "backend_server")
            docker build -f ../backend_server/Dockerfile -t virtualpytest/backend_server:latest ..
            ;;
        "frontend")
            docker build -f ../frontend/Dockerfile -t virtualpytest/frontend:latest ../frontend
            ;;
        *)
            echo "❌ Unknown service: $service"
            exit 1
            ;;
    esac
    
    echo "✅ $service build complete"
}

# Parse arguments
SERVICES_TO_BUILD=()
PARALLEL=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --service)
            SERVICES_TO_BUILD+=("$2")
            shift 2
            ;;
        --parallel)
            PARALLEL=true
            shift
            ;;
        --all)
            SERVICES_TO_BUILD=("${BUILD_ORDER[@]}")
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --service <name>  Build specific service"
            echo "  --all            Build all services"
            echo "  --parallel       Build in parallel (where possible)"
            echo "  --help           Show this help"
            echo ""
            echo "Available services: ${BUILD_ORDER[*]}"
            exit 0
            ;;
        *)
            echo "❌ Unknown option: $1"
            exit 1
            ;;
    esac
done

# Default to all if no services specified
if [[ ${#SERVICES_TO_BUILD[@]} -eq 0 ]]; then
    SERVICES_TO_BUILD=("${BUILD_ORDER[@]}")
fi

# Build services
if [[ "$PARALLEL" == true ]]; then
    echo "🚀 Building services in parallel..."
    for service in "${SERVICES_TO_BUILD[@]}"; do
        build_service "$service" &
    done
    wait
else
    echo "🔄 Building services sequentially..."
    for service in "${SERVICES_TO_BUILD[@]}"; do
        build_service "$service"
    done
fi

echo "🎉 All builds complete!"
echo ""
echo "📋 Built images:"
docker images | grep virtualpytest 