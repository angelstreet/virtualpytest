# Backend Core Migration Plan - Clean 2-Step Process

Simple migration of `backend_host` folders into `backend_host/src/` with import updates. No legacy code, no fallbacks, just move and rename imports.

**Architecture**: Server proxies to host, host manages devices autonomously. All controllers and services belong in backend_host.

**Time**: 30 minutes total

## Step 1: Move Folders (10 minutes)

1. **Create target directories**:
   ```bash
   mkdir -p backend_host/src/controllers
   mkdir -p backend_host/src/services
   ```

2. **Move all backend_host content**:
   ```bash
   # Move directories
   mv backend_host/src/controllers/* backend_host/src/controllers/
   mv backend_host/src/services/* backend_host/src/services/
   
   # Move root files
   mv backend_host/src/__init__.py backend_host/src/core_init.py
   mv backend_host/src/base_controller.py backend_host/src/
   mv backend_host/src/controller_config_factory.py backend_host/src/
   mv backend_host/src/controller_manager.py backend_host/src/
   ```

3. **Delete old directory**:
   ```bash
   rm -rf backend_host/
   ```

## Step 2: Update All Imports (20 minutes)

1. **Batch replace all backend_host imports**:
   ```bash
   # Replace in Python files
   grep -rl --include=\*.py "backend_host" . | xargs sed -i '' 's/backend_host/backend_host/g'
   
   # Replace in Markdown files  
   grep -rl --include=\*.md "backend_host" . | xargs sed -i '' 's/backend_host/backend_host/g'
   
   # Replace in Docker files
   grep -rl --include=\*Dockerfile "backend_host" . | xargs sed -i '' 's/backend_host/backend_host/g'
   
   # Replace in config files
   grep -rl --include=\*.conf --include=\*.yml --include=\*.yaml "backend_host" . | xargs sed -i '' 's/backend_host/backend_host/g'
   ```

2. **Fix backend_host internal imports**:
   ```bash
   # Fix internal imports in backend_host/src files
   sed -i '' 's/from backend_host/from src/g' backend_host/src/*.py
   sed -i '' 's/from backend_host/from src/g' backend_host/src/controllers/**/*.py
   sed -i '' 's/from backend_host/from src/g' backend_host/src/services/**/*.py
   ```

**Done**. No testing, no validation, no documentation updates - just the move and import rename.

**Post-Migration Notes**:
- No fallbacks: If the new structure doesn't work, fix root causes (e.g., adjust paths) without reverting to old code.
- If doubts arise (e.g., heavy shared usage), stop and reassess splitting.
- Run this migration in a test environment first.

Last updated: September 20, 2025