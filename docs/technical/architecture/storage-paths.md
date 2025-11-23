# Centralized Storage Path Architecture

## Problem Solved
**NO MORE CODE DUPLICATION** - All storage path logic is now in ONE place!

### Before (Problems):
- ❌ `archive_utils.py` in backend_host/scripts/ (local only)
- ❌ Duplicate `is_ram_mode()` functions everywhere
- ❌ Hard-coded paths like `/captures/` scattered across codebase
- ❌ Health checks looking in wrong directories

### After (Solution):
- ✅ **Single source of truth:** `shared/src/lib/utils/storage_path_utils.py`
- ✅ **Auto-detects RAM/SD mode** everywhere
- ✅ **Centralized path resolution** via `get_capture_storage_path()`
- ✅ **Backward compatible** via wrapper in `backend_host/scripts/archive_utils.py`

---

## Architecture

```
shared/src/lib/utils/storage_path_utils.py (SINGLE SOURCE OF TRUTH)
├── is_ram_mode(capture_base_dir)           # Detect RAM hot storage
├── get_capture_storage_path(base_dir, subfolder)  # Get correct path
├── get_capture_base_directories()          # Get all active captures
└── get_device_info_from_capture_folder()   # Device .env mapping

backend_host/scripts/hot_cold_archiver.py (MANIFEST GENERATION)
├── generate_hour_manifest()                # Create/update hour-based manifests
├── update_all_manifests()                  # Update all 24 hour manifests
└── archive_hot_files()                     # Move files to hour folders
```

---

## Usage Examples

### Python (Backend) - Clean API

```python
# Import from centralized location
from shared.src.lib.utils.storage_path_utils import get_capture_storage_path

# ✅ RECOMMENDED: Just pass device name (simple, clean, no hardcoding!)
captures_path = get_capture_storage_path('capture1', 'captures')
# Returns: /var/www/html/stream/capture1/hot/captures  (RAM mode)
# Returns: /var/www/html/stream/capture1/captures       (SD mode)

# Get thumbnails path
thumbnails_path = get_capture_storage_path('capture2', 'thumbnails')

# Get segments path
segments_path = get_capture_storage_path('capture3', 'segments')

# ✅ ONE FUNCTION CALL - Auto-detects:
#    - Base stream path
#    - RAM vs SD mode  
#    - Correct subfolder location
```

### Backward Compatible

```python
# Still works if you pass full path (backward compatible)
captures_path = get_capture_storage_path('/var/www/html/stream/capture1', 'captures')
# Same result as above
```

### Backward Compatibility

```python
# Old code still works!
from backend_host.scripts.archive_utils import is_ram_mode

# This now imports from shared automatically
```

---

## What Was Changed

### 1. Created Central Module
- **File:** `shared/src/lib/utils/storage_path_utils.py`
- **Purpose:** Single source of truth for all storage paths
- **Functions:** 
  - `is_ram_mode()` - Detect tmpfs mounts
  - `get_capture_storage_path()` - Resolve paths automatically

### 2. Updated Health Checks
- **File:** `backend_host/src/lib/utils/system_info_utils.py`
- **Before:** Hard-coded `/captures/` directory
- **After:** Uses `get_capture_storage_path()` to check correct location
- **Result:** Health checks now find files in RAM hot storage!

### 3. Backward Compatibility Wrapper
- **File:** `backend_host/scripts/archive_utils.py`
- **Purpose:** Imports from shared, no code duplication
- **Benefit:** Existing imports still work

---

## Hot/Cold Architecture

### RAM Mode (Hot Storage)
```
/var/www/html/stream/capture1/
├── hot/                    # ← tmpfs (100MB RAM)
│   ├── captures/          # ← FFmpeg writes here
│   ├── thumbnails/
│   ├── segments/
│   └── metadata/
├── captures/              # ← Archived hourly (SD card)
│   ├── 0/
│   ├── 1/
│   └── ...
├── thumbnails/            # ← 24h retention
└── segments/              # ← 24h retention
```

### SD Mode (Traditional)
```
/var/www/html/stream/capture1/
├── captures/              # ← FFmpeg writes directly
│   ├── capture_001.jpg
│   └── ...
├── thumbnails/
└── segments/
```

---

## Frontend Considerations

### Current State
Frontend uses centralized URL building (`buildUrlUtils.ts`):
```typescript
buildCaptureUrl(host, filename, deviceId)
// → https://host/stream/capture1/captures/capture_001.jpg
```

### Nginx Handling
Nginx should serve from hot storage transparently:

```nginx
# Try hot storage first, fallback to cold
location ~ ^/stream/([^/]+)/(captures|thumbnails|segments|metadata)/ {
    try_files /stream/$1/hot/$2/$uri /stream/$1/$2/$uri =404;
}
```

**TODO:** Verify nginx configuration includes hot storage fallback

---

## Migration Checklist

- [x] Create centralized `storage_path_utils.py`
- [x] Add `is_ram_mode()` detection
- [x] Add `get_capture_storage_path()` resolver
- [x] Update `system_info_utils.py` health checks
- [x] Create backward-compatible wrapper
- [x] Remove duplicate code from `archive_utils.py`
- [ ] Verify nginx hot storage configuration
- [ ] Test health checks with RAM mode enabled
- [ ] Update documentation

---

## Benefits

1. **No Duplication** - One function, used everywhere
2. **Auto-Detection** - Automatically uses RAM or SD
3. **Easy Testing** - Change one place, affects everything
4. **Clean Imports** - Clear dependency hierarchy
5. **Future-Proof** - Add new storage modes easily

---

## Testing

```bash
# Test RAM mode detection
python3 -c "
from shared.src.lib.utils.storage_path_utils import is_ram_mode, get_capture_storage_path
print(f'RAM mode: {is_ram_mode(\"/var/www/html/stream/capture1\")}')
print(f'Path: {get_capture_storage_path(\"/var/www/html/stream/capture1\", \"captures\")}')
"
```

---

## Next Steps

1. **Verify nginx configuration** - Ensure it tries /hot/ first
2. **Test health checks** - Confirm they find files in RAM
3. **Monitor logs** - Check for "0 files" issues
4. **Document nginx** - Add hot storage to nginx docs

