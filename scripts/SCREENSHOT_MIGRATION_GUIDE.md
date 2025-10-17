# Screenshot Migration Guide: device_model → userinterface

## 📋 Overview

This migration changes screenshot storage paths from `device_model`-based to `userinterface`-based organization.

### **Why This Migration?**

- **Problem**: Screenshots were stored per device_model (android_mobile, android_tv, stb, host_vnc)
- **Issue**: Multiple device_models can share the same UI (e.g., host_vnc used for both perseus_360_web and iad_gui)
- **Solution**: Store screenshots per userinterface for better organization and reusability

### **Current State (Before Migration)**

```
R2 Storage:
navigation/
├── android_mobile/     (12 screenshots) → horizon_android_mobile UI
├── android_tv/         (15 screenshots) → horizon_android_tv UI
├── stb/                (12 screenshots) → horizon_tv UI
└── host_vnc/           (14 screenshots) → mixed between perseus_360_web and iad_gui
```

### **Target State (After Migration)**

```
R2 Storage:
navigation/
├── horizon_android_mobile/  (12 screenshots)
├── horizon_android_tv/      (15 screenshots)
├── horizon_tv/              (12 screenshots)
├── perseus_360_web/         (8 screenshots)
└── iad_gui/                 (6 screenshots)
```

---

## 🗂️ Your UserInterfaces

Based on your database:

| UserInterface Name | Device Models | Screenshots |
|--------------------|---------------|-------------|
| `horizon_android_mobile` | android_mobile | 12 |
| `horizon_android_tv` | android_tv, fire_tv | 15 |
| `horizon_tv` | stb | 12 |
| `perseus_360_web` | web | 8 |
| `iad_gui` | web | 6 |

**Total: 53 screenshots to migrate**

---

## 🚀 Migration Steps

### **Step 1: Backup (Recommended)**

```bash
# The migration script keeps original files, but it's good to have a backup
# Backup your database userinterfaces and navigation_nodes tables
pg_dump -h your_host -U your_user -d your_db -t userinterfaces -t navigation_nodes > backup_before_migration.sql
```

### **Step 2: Activate Environment**

```bash
cd /Users/cpeengineering/virtualpytest
source venv/bin/activate  # or your venv activation method
```

### **Step 3: Set Environment Variables**

Ensure your environment has:
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `TEAM_ID`
- `CLOUDFLARE_R2_ENDPOINT`
- `CLOUDFLARE_R2_ACCESS_KEY_ID`
- `CLOUDFLARE_R2_SECRET_ACCESS_KEY`
- `CLOUDFLARE_R2_PUBLIC_URL`

```bash
# If using .env file
source activate.sh  # or whatever loads your environment
```

### **Step 4: Run Migration Script**

```bash
python scripts/migrate_screenshots_to_userinterface.py
```

The script will:
1. 📊 Query database to build migration mapping
2. 📦 Copy files in R2 (server-side copy, very fast)
3. 🗄️ Update database URLs to point to new paths
4. ✅ Keep original files as backup

**Interactive Confirmation**: The script will show you the migration plan and ask for confirmation before proceeding.

---

## 📝 What Changes Were Made

### **1. Migration Script**
- **File**: `scripts/migrate_screenshots_to_userinterface.py`
- **Purpose**: Copy R2 files and update database URLs

### **2. Frontend Changes**
- **File**: `frontend/src/hooks/navigation/useNode.ts`
- **Changes**:
  - Now sends `userinterface_name` instead of `device_model`
  - Gets userinterface from NavigationContext
  - Updated dependency arrays

### **3. Backend Changes**
- **File**: `backend_host/src/routes/host_av_routes.py`
- **Changes**:
  - Accepts `userinterface_name` parameter instead of `device_model`
  - Validates userinterface_name is provided

### **4. Shared Utilities**
- **File**: `shared/src/lib/utils/cloudflare_utils.py`
- **Changes**:
  - Added `copy_file()` method for R2 server-side copy
  - Updated `upload_navigation_screenshot()` to use `userinterface_name`

---

## ✅ Verification Steps

After running the migration:

### **1. Check Migration Output**

The script will show:
```
✅ MIGRATION COMPLETE
R2 Files:     53/53 copied
Database:     53/53 updated
```

### **2. Test Screenshot Display**

1. Open your navigation editor
2. Navigate to any node with a screenshot
3. Verify the screenshot loads correctly
4. The URL should now show: `https://.../navigation/{userinterface_name}/{filename}.jpg`

### **3. Test Screenshot Creation**

1. Select a node in your navigation editor
2. Click "Save Screenshot"
3. Verify it saves to the new userinterface-based path

### **4. Verify Database**

```sql
-- Check that URLs have been updated
SELECT 
  label,
  data->>'screenshot' as screenshot_url
FROM navigation_nodes 
WHERE data->>'screenshot' LIKE '%navigation/%'
LIMIT 10;

-- Should show paths like: .../navigation/horizon_android_mobile/...
```

### **5. Verify R2 Storage**

Check your R2 bucket:
- Old paths should still exist (backup)
- New userinterface-based paths should exist
- Both should have the same files

---

## 🔄 Rollback (If Needed)

If something goes wrong, you can rollback:

### **1. Restore Database** (if you made backup)
```bash
psql -h your_host -U your_user -d your_db < backup_before_migration.sql
```

### **2. Revert Code Changes**
```bash
git checkout frontend/src/hooks/navigation/useNode.ts
git checkout backend_host/src/routes/host_av_routes.py
git checkout shared/src/lib/utils/cloudflare_utils.py
```

### **3. Old Files Still Exist**
The migration script doesn't delete old files, so screenshots will still work with the old code.

---

## 🧹 Cleanup (After Successful Migration)

After verifying everything works for a few days:

### **Delete Old R2 Paths**

You can manually delete the old device_model-based paths:
- `navigation/android_mobile/`
- `navigation/android_tv/`
- `navigation/stb/`
- `navigation/host_vnc/`

**Warning**: Only do this after confirming the migration was successful!

---

## 🐛 Troubleshooting

### **Issue**: "User interface not available" error when taking screenshots

**Solution**: Ensure the navigation tree has a userinterface_id set:
```sql
UPDATE navigation_trees 
SET userinterface_id = (SELECT id FROM userinterfaces WHERE name = 'your_ui_name')
WHERE id = 'your_tree_id';
```

### **Issue**: Screenshots not loading after migration

**Solution**: 
1. Check browser console for 404 errors
2. Verify the URL path in database matches R2 storage
3. Check if R2 copy succeeded for that specific file

### **Issue**: Migration script fails with R2 error

**Solution**: 
1. Verify R2 credentials are correct
2. Check network connectivity
3. Ensure source files exist in R2

---

## 📞 Support

If you encounter issues:

1. Check the migration script output for specific errors
2. Verify all environment variables are set correctly
3. Check R2 bucket permissions
4. Review database logs for any errors

---

## 📊 Migration Statistics

**Files Migrated**: 53 screenshots
**UserInterfaces**: 5
**Device Models Consolidated**: 4 → 5 (split host_vnc into perseus_360_web and iad_gui)

**Before**:
- android_mobile: 12 files
- android_tv: 15 files
- stb: 12 files
- host_vnc: 14 files

**After**:
- horizon_android_mobile: 12 files
- horizon_android_tv: 15 files
- horizon_tv: 12 files
- perseus_360_web: 8 files
- iad_gui: 6 files

---

## ✨ Benefits

1. **Better Organization**: Screenshots organized by actual UI, not device
2. **Reusability**: Same UI on different devices shares screenshots
3. **Clarity**: `perseus_360_web` is clearer than `host_vnc`
4. **Scalability**: Easy to add new UIs without device model conflicts
5. **Web Support**: Proper support for web-based UIs

---

## 🎉 Next Steps

After successful migration:

1. ✅ Verify all screenshots display correctly
2. ✅ Test creating new screenshots
3. ✅ Monitor for a few days
4. 🧹 Clean up old R2 paths (optional)
5. 📝 Update team documentation

---

**Migration Script**: `/Users/cpeengineering/virtualpytest/scripts/migrate_screenshots_to_userinterface.py`
**Date**: October 17, 2025

