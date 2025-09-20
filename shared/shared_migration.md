# Shared Library Migration Plan

Migration to restructure `shared/lib/` to `shared/src/lib/` for consistency with backend_host and backend_server structure.

## 🎯 **Goal**

Create consistent structure across all services:
- `shared/src/lib/`
- `backend_host/src/lib/`  
- `backend_server/src/lib/`

This way imports only change based on parent folder name (shared vs backend_host vs backend_server).

## 📁 **Current vs Target Structure**

### **Current**
```
shared/
├── __init__.py
├── lib/
│   ├── __init__.py
│   ├── config/
│   ├── models/
│   ├── utils/
│   ├── ai/
│   ├── mcp/
│   └── supabase/
└── README.md
```

### **Target**
```
shared/
├── __init__.py
├── src/
│   └── lib/
│       ├── __init__.py
│       ├── config/
│       ├── models/
│       ├── utils/
│       ├── ai/
│       └── mcp/
└── README.md
```

## 🚀 **Migration Steps**

### **Step 1: Create New Structure**
```bash
# Create new directory structure
mkdir -p shared/src/lib

# Move all lib contents to new location
mv shared/lib/* shared/src/lib/

# Remove old lib directory
rmdir shared/lib
```

### **Step 2: Update All Imports**
```bash
# Update all imports from shared.lib to shared.src.lib
find . -name "*.py" -exec sed -i '' 's/from shared\.lib\./from shared.src.lib./g' {} \;
find . -name "*.py" -exec sed -i '' 's/import shared\.lib\./import shared.src.lib./g' {} \;
```

### **Step 3: Update Docker Files**
```bash
# Update PYTHONPATH in Docker files
find . -name "Dockerfile*" -exec sed -i '' 's|/app/shared/lib|/app/shared/src/lib|g' {} \;
```

### **Step 4: Update Configuration Files**
```bash
# Update any config files that reference shared/lib paths
find . -name "*.conf" -o -name "*.yml" -o -name "*.yaml" | xargs sed -i '' 's|shared/lib|shared/src/lib|g'
```

## ✅ **Benefits**

1. **Consistent Structure**: All services follow same `*/src/lib/` pattern
2. **Simple Import Changes**: Only parent folder name changes in imports
3. **Clear Organization**: Standard src/ directory structure
4. **Future-Proof**: Easy to add other src/ components if needed

## 📋 **Import Pattern Examples**

### **Before**
```python
from shared.lib.utils.app_utils import load_environment_variables
from shared.lib.models.device import Device
from shared.lib.config.settings import shared_config
```

### **After**
```python
from shared.src.lib.utils.app_utils import load_environment_variables
from shared.src.lib.models.device import Device
from shared.src.lib.config.settings import shared_config
```

## 🔧 **Verification**

After migration, verify:
1. All imports work correctly
2. Docker builds succeed
3. Services start without import errors
4. Tests pass

## 📋 **Final Project Structure**

After migration, the project will have consistent structure across all services:

```
virtualpytest/
├── shared/
│   ├── __init__.py
│   ├── src/
│   │   └── lib/
│   │       ├── __init__.py
│   │       ├── config/          # Configuration management
│   │       ├── models/          # Data models
│   │       ├── utils/           # Truly shared utilities
│   │       ├── ai/              # AI interfaces
│   │       └── mcp/             # MCP server
│   └── README.md
├── backend_host/
│   ├── src/
│   │   ├── lib/
│   │   │   └── utils/           # Host-specific utilities
│   │   ├── controllers/         # Device controllers
│   │   ├── services/            # Host services
│   │   └── routes/              # Host API routes
│   └── ...
├── backend_server/
│   ├── src/
│   │   ├── lib/
│   │   │   ├── utils/           # Server-specific utilities
│   │   │   └── supabase/        # Database operations
│   │   └── routes/              # Server API routes
│   └── ...
└── frontend/
    └── ...
```

## 🎯 **Import Patterns**

### **Shared Components** (used by both services)
```python
# Configuration and models
from shared.src.lib.config.settings import shared_config
from shared.src.lib.models.device import Device

# Truly shared utilities
from shared.src.lib.utils.app_utils import load_environment_variables
from shared.src.lib.utils.build_url_utils import buildServerUrl
```

### **Host-Specific Components** (internal to backend_host)
```python
# Internal imports within backend_host
from src.lib.utils.host_utils import get_host_manager
from src.lib.utils.adb_utils import ADBUtils
from src.lib.utils.navigation_cache import get_cached_unified_graph
```

### **Server-Specific Components** (internal to backend_server)
```python
# Internal imports within backend_server
from src.lib.utils.route_utils import proxy_to_host
from src.lib.utils.heatmap_utils import HeatmapJob
from src.lib.supabase.devices_db import get_device
```

### **Cross-Service Imports** (server accessing host)
```python
# Server accessing host utilities (rare cases)
from backend_host.src.lib.utils.host_utils import get_host_manager
```

## ✅ **Migration Complete**

The shared library migration achieves:

1. **Consistent Architecture**: All services follow `*/src/lib/` pattern
2. **Clear Separation**: Host, server, and shared components are properly separated
3. **Autonomous Services**: Each service has its own utilities while sharing common components
4. **Simple Imports**: Predictable import patterns based on component location
5. **No Legacy Code**: Clean migration with immediate deletion of old structure

**Total Time Estimate**: 15 minutes

**Next Steps**: This migration can be combined with the full shared library component migration to move host-specific and server-specific utilities to their respective services.
