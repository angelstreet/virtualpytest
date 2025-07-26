#!/bin/bash

# Fix imports script - Convert src.utils imports to proper paths
# This script fixes import statements after src_LEGACY removal

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

echo "🔧 Fixing import statements throughout the project..."

# Find all Python files with src.utils imports
echo "📁 Searching for files with src.utils imports..."

# Fix imports in all Python files
find . -name "*.py" -type f \
    -not -path "./src_LEGACY/*" \
    -not -path "./venv/*" \
    -not -path "./.git/*" \
    -not -path "./build/*" \
    -not -path "./*.egg-info/*" \
    -exec grep -l "from src\.utils\." {} \; | while read file; do
    
    echo "🔄 Fixing imports in: $file"
    
    # Create backup
    cp "$file" "$file.bak"
    
    # Fix various src.utils imports
    sed -i.tmp \
        -e 's/from src\.utils\./from utils\./g' \
        -e 's/from src\.lib\./from /g' \
        -e 's/from src\.web\.utils\.routeUtils/from utils.route_utils/g' \
        -e 's/from src\.web\.cache\./from utils\./g' \
        -e 's/from src\.controllers\./from controllers\./g' \
        "$file"
    
    # Remove the .tmp file created by sed
    rm -f "$file.tmp"
done

echo "🧹 Cleaning up backup files..."
find . -name "*.bak" -type f \
    -not -path "./src_LEGACY/*" \
    -not -path "./venv/*" \
    -not -path "./.git/*" \
    -delete

echo "✅ Import fixing completed!"
echo ""
echo "📋 Summary of changes made:"
echo "   • from src.utils.* → from utils.*"
echo "   • from src.lib.* → from *"
echo "   • from src.web.utils.routeUtils → from utils.route_utils"
echo "   • from src.web.cache.* → from utils.*"
echo "   • from src.controllers.* → from controllers.*"
echo ""
echo "🔄 Please restart your services for changes to take effect" 