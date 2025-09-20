# Import Path Migration Plan

## 🔍 **Analysis: What Worked Before**

From commit `25f726a0b9192933a3fa9fe855923a70218e7271`, the working structure was:

```
src/
├── lib/                    # Business logic
│   ├── navigation/
│   ├── actions/
│   └── ...
├── utils/                  # Utility functions  
├── models/                 # Data models
└── web/                    # Flask routes
    ├── routes/
    └── src/                # React frontend
```

**Key Imports that worked:**
- `from src.utils.script_utils import ...`
- `from src.lib.navigation.navigation_pathfinding import ...`
- Direct imports within the same structure

## 🎯 **Current Problem**

After migration, we have:
```
backend_server/src/routes/server_actions_routes.py
# Trying to import:
from lib.supabase.actions_db import ...
```

But our structure is now:
```
shared/lib/supabase/actions_db.py
```

The `backend_server/src/app.py` sets up:
```python
sys.path.insert(0, '../../shared/lib')
sys.path.insert(0, '../../backend_host/src')
```

## ✅ **Solution Strategy**

### **Option A: Make imports match the path setup (RECOMMENDED)**

Since `app.py` adds `shared/lib` to `sys.path`, imports should be:

```python
# Instead of:
from lib.supabase.actions_db import ...

# Should be:
from supabase.actions_db import ...
```

This matches the path structure after `shared/lib` is added to sys.path.

### **Option B: Use explicit relative imports**

```python
# Import with full path from project root
from shared.lib.supabase.actions_db import ...
```

## 📋 **Implementation Plan**

### **Phase 1: Fix Route Imports (backend_server)**

1. **Identify all problematic imports** in `backend_server/src/routes/`
2. **Change import pattern** from `lib.X` to `X` (since `shared/lib` is in path)
3. **Test each route file** imports work

### **Phase 2: Fix Shared Library Internal Imports**

Files in `shared/lib/` currently have imports like:
```python
from lib.utils.supabase_utils import ...
```

Should be:
```python
from utils.supabase_utils import ...
```

### **Phase 3: Test backend_server Startup**

After fixing imports:
```bash
cd backend_server && python3 src/app.py
```

## 🔧 **Specific Changes Needed**

### **Files to Update:**

**backend_server/src/routes/:**
- `server_actions_routes.py`: `from lib.supabase.actions_db` → `from supabase.actions_db`
- All other route files with similar patterns

**shared/lib/ internal imports:**
- `supabase/actions_db.py`: `from lib.utils.supabase_utils` → `from utils.supabase_utils`
- All files in supabase/ with `lib.` imports
- All files in utils/ with `lib.` imports

## 🚀 **Execution Order**

1. **Fix backend_server route imports** (external imports into shared)
2. **Fix shared library internal imports** (within shared)
3. **Test backend_server startup**
4. **Fix backend_host the same way**
5. **Test full system**

## 🎯 **Success Criteria**

- [ ] `cd backend_server && python3 src/app.py` starts without import errors
- [ ] All routes can be imported successfully
- [ ] Basic API endpoints respond
- [ ] Same process works for backend_host

---

**Key Insight**: Don't change folder names or structure - just fix imports to match the sys.path setup that's already working in `app.py`. 