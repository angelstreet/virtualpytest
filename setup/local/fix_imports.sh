#!/bin/bash

# VirtualPyTest - Fix Import Statements
# This script fixes src.utils imports to use the new microservices structure

set -e

echo "🔧 Fixing import statements in backend-server routes..."

# Get to project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

ROUTES_DIR="backend-server/src/routes"

if [ ! -d "$ROUTES_DIR" ]; then
    echo "❌ Routes directory not found: $ROUTES_DIR"
    exit 1
fi

echo "📁 Fixing imports in: $ROUTES_DIR"

# Fix src.utils imports to utils
find "$ROUTES_DIR" -name "*.py" -exec sed -i.bak 's/from src\.utils\./from utils./g' {} \;

# Fix src.lib imports to use shared/lib structure 
find "$ROUTES_DIR" -name "*.py" -exec sed -i.bak 's/from src\.lib\./from /g' {} \;

# Fix src.web imports (these should be handled differently or removed)
find "$ROUTES_DIR" -name "*.py" -exec sed -i.bak 's/from src\.web\.utils\.routeUtils/from utils.route_utils/g' {} \;
find "$ROUTES_DIR" -name "*.py" -exec sed -i.bak 's/from src\.web\.cache\./from utils./g' {} \;

# Fix src.controllers imports to controllers
find "$ROUTES_DIR" -name "*.py" -exec sed -i.bak 's/from src\.controllers\./from controllers./g' {} \;

# Clean up backup files
find "$ROUTES_DIR" -name "*.py.bak" -delete

echo "✅ Import statements fixed!"
echo ""
echo "📋 Fixed the following import patterns:"
echo "   src.utils.* → utils.*"
echo "   src.lib.* → *" 
echo "   src.controllers.* → controllers.*"
echo "   src.web.utils.routeUtils → utils.route_utils"
echo "   src.web.cache.* → utils.*"
echo ""
echo "⚠️ Note: Some imports may need manual review if they reference"
echo "   modules that don't exist in the new structure."
echo ""
echo "🔄 You can now restart the backend-server service" 