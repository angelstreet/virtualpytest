#!/bin/bash

# VirtualPyTest - Clean Build Artifacts
# This script removes Python build artifacts and egg-info directories

set -e

echo "🧹 Cleaning VirtualPyTest build artifacts..."

# Get to project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

echo "📁 Current directory: $(pwd)"

# Remove build artifacts from shared
if [ -d "shared/build" ]; then
    echo "🗑️ Removing shared/build/"
    rm -rf shared/build/
fi

if [ -d "shared/virtualpytest_shared.egg-info" ]; then
    echo "🗑️ Removing shared/virtualpytest_shared.egg-info/"
    rm -rf shared/virtualpytest_shared.egg-info/
fi

# Remove build artifacts from backend_core
if [ -d "backend_core/build" ]; then
    echo "🗑️ Removing backend_core/build/"
    rm -rf backend_core/build/
fi

if [ -d "backend_core/virtualpytest_backend_core.egg-info" ]; then
    echo "🗑️ Removing backend_core/virtualpytest_backend_core.egg-info/"
    rm -rf backend_core/virtualpytest_backend_core.egg-info/
fi

# Remove from git tracking if they exist
echo "📝 Removing from git tracking..."
git rm -rf --cached shared/build/ 2>/dev/null || echo "   shared/build/ not in git"
git rm -rf --cached shared/virtualpytest_shared.egg-info/ 2>/dev/null || echo "   shared/virtualpytest_shared.egg-info/ not in git"
git rm -rf --cached backend_core/build/ 2>/dev/null || echo "   backend_core/build/ not in git"
git rm -rf --cached backend_core/virtualpytest_backend_core.egg-info/ 2>/dev/null || echo "   backend_core/virtualpytest_backend_core.egg-info/ not in git"

# Update .gitignore if not already there
echo "📋 Updating .gitignore..."
if ! grep -q "# Build artifacts" .gitignore; then
    echo "" >> .gitignore
    echo "# Build artifacts" >> .gitignore
    echo "shared/build/" >> .gitignore
    echo "shared/virtualpytest_shared.egg-info/" >> .gitignore
    echo "backend_core/build/" >> .gitignore
    echo "backend_core/virtualpytest_backend_core.egg-info/" >> .gitignore
    echo "*.egg-info/" >> .gitignore
    echo "__pycache__/" >> .gitignore
    echo "*.pyc" >> .gitignore
    echo "*.pyo" >> .gitignore
    echo "*.pyd" >> .gitignore
    echo ".Python" >> .gitignore
    echo "build/" >> .gitignore
    echo "develop-eggs/" >> .gitignore
    echo "dist/" >> .gitignore
    echo "downloads/" >> .gitignore
    echo "eggs/" >> .gitignore
    echo ".eggs/" >> .gitignore
    echo "lib/" >> .gitignore
    echo "lib64/" >> .gitignore
    echo "parts/" >> .gitignore
    echo "sdist/" >> .gitignore
    echo "var/" >> .gitignore
    echo "wheels/" >> .gitignore
    echo "*.egg-info/" >> .gitignore
    echo ".installed.cfg" >> .gitignore
    echo "*.egg" >> .gitignore
    echo "✅ Added Python build patterns to .gitignore"
else
    echo "✅ .gitignore already contains build patterns"
fi

echo ""
echo "✅ Build artifacts cleaned!"
echo ""
echo "📋 Next steps:"
echo "   1. git add .gitignore"
echo "   2. git commit -m 'Add build artifacts to gitignore and remove from tracking'"
echo "   3. git pull (should work now)"
echo ""
echo "🔄 Future builds will not commit these files" 