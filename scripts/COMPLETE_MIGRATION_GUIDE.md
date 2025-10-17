# Complete Migration Guide: device_model → userinterface

## 📋 Overview

This guide covers the complete migration from `device_model`-based organization to `userinterface`-based organization for:
1. **Navigation Screenshots** (53 files)
2. **Reference Images** (image & text, 23 files)

---

## 🗂️ What Needs to Migrate

### **1. Navigation Screenshots**
- **Database**: `navigation_nodes.data.screenshot` (URLs only)
- **R2 Storage**: `navigation/{device_model}/` → `navigation/{userinterface_name}/`
- **Count**: 53 screenshots

### **2. Verification References**
- **Database**: `verifications_references` table needs schema change!
  - Add `userinterface_id` column
  - Migrate data from `device_model` to `userinterface_id`
- **R2 Storage**:
  - `reference-images/{device_model}/` → `reference-images/{userinterface_name}/`
  - `text-references/{device_model}/` → `text-references/{userinterface_name}/`
- **Count**: 23 references (both image and text)

---

## 🎯 Migration Scripts

### **Script 1: Navigation Screenshots**
```bash
python scripts/migrate_screenshots_to_userinterface.py
```

**What it does:**
- ✅ Copies 53 screenshots in R2 to new paths
- ✅ Updates `navigation_nodes.data.screenshot` URLs
- ✅ Keeps old files as backup

### **Script 2: Verification References**
```bash
python scripts/migrate_references_to_userinterface.py
```

**What it does:**
- ✅ Adds `userinterface_id` column to `verifications_references` table
- ✅ Populates `userinterface_id` based on `device_model` → `userinterface` mapping
- ✅ Copies 23 reference files in R2 to new paths
- ✅ Updates `r2_path` and `r2_url` in database
- ✅ Keeps `device_model` column and old files as backup

---

## 📊 Your Data

### **UserInterfaces**
| Name | Models | Screenshots | References |
|------|--------|-------------|------------|
| `horizon_android_mobile` | android_mobile | 12 | 4 |
| `horizon_android_tv` | android_tv, fire_tv | 15 | 12 |
| `horizon_tv` | stb | 12 | 7 |
| `perseus_360_web` | web | 8 | 0 |
| `iad_gui` | web | 6 | 0 |

### **Total Migration**
- **Screenshots**: 53 files
- **References**: 23 files (image + text)
- **Total**: 76 files to migrate

---

## 🚀 Step-by-Step Execution

### **Prerequisites**
```bash
cd /home/sunri-pi1/virtualpytest
source venv/bin/activate
# .env file is automatically loaded by scripts
```

### **Step 1: Migrate Navigation Screenshots**
```bash
python scripts/migrate_screenshots_to_userinterface.py
```

**Expected output:**
```
✅ Loaded environment from: /home/sunri-pi1/virtualpytest/.env
✅ All required environment variables are set

📊 [Migration] Found 53 screenshots to migrate

📁 Current paths (by device_model):
   - android_mobile: 12 files
   - android_tv: 15 files
   - host_vnc: 14 files
   - stb: 12 files

📁 New paths (by userinterface):
   - horizon_android_mobile: 12 files
   - horizon_android_tv: 15 files
   - horizon_tv: 12 files
   - iad_gui: 6 files
   - perseus_360_web: 8 files

Press ENTER to continue...
✅ MIGRATION COMPLETE
```

### **Step 2: Migrate Verification References**
```bash
python scripts/migrate_references_to_userinterface.py
```

**Expected output:**
```
✅ Loaded environment from: /home/sunri-pi1/virtualpytest/.env
✅ All required environment variables are set

📊 [Migration] Building device_model → userinterface mapping...
   android_mobile → horizon_android_mobile
   android_tv → horizon_android_tv
   fire_tv → horizon_android_tv
   stb → horizon_tv
   web → perseus_360_web
   web → iad_gui

📝 [Step 1] Adding userinterface_id column...
   ✅ Added userinterface_id column

📝 [Step 2] Populating userinterface_id values...
   ✅ 23 succeeded, 0 failed

📦 [Step 3] Copying files in R2...
   ✅ 23 files copied, 0 failed

🗄️  [Step 4] Updating database R2 paths...
   ✅ 23 updated, 0 failed

✅ MIGRATION COMPLETE
```

---

## ✅ Verification Checklist

After running both migrations:

### **Navigation Screenshots**
- [ ] Screenshots display correctly in navigation editor
- [ ] New screenshots can be taken and saved
- [ ] Screenshot URLs show `navigation/{userinterface_name}/`
- [ ] No 404 errors in browser console

### **Verification References**
- [ ] Image references load in verification panel
- [ ] Text references work correctly
- [ ] New references can be created and saved
- [ ] Reference URLs show `reference-images/{userinterface_name}/`
- [ ] Database has `userinterface_id` populated

### **Database Check**
```sql
-- Check navigation screenshots
SELECT label, data->>'screenshot' as screenshot_url 
FROM navigation_nodes 
WHERE data->>'screenshot' LIKE '%navigation/%' 
LIMIT 5;

-- Should show: .../navigation/horizon_android_mobile/...

-- Check verification references
SELECT name, device_model, userinterface_id, r2_path 
FROM verifications_references 
LIMIT 5;

-- Should show userinterface_id populated and new r2_path
```

---

## 🎯 Code Changes Summary

### **✅ Already Done**

#### **Navigation Screenshots:**
- ✅ Frontend (`useNode.ts`) - sends `userinterface_name`
- ✅ Backend (`host_av_routes.py`) - accepts `userinterface_name`
- ✅ Cloudflare utils - uses `navigation/{userinterface_name}/`

#### **Reference Images:**
- ✅ Backend (`image_helpers.py`, `image.py`) - accepts `userinterface_name`
- ✅ Cloudflare utils - uses `reference-images/{userinterface_name}/`

### **⚠️ Frontend Updates Needed**

#### **Reference Images:**
Find where reference images are saved in frontend and update to send `userinterface_name`:

```typescript
// Before:
body: JSON.stringify({
  device_model: deviceModel,
  reference_name: 'logo',
  ...
})

// After:
body: JSON.stringify({
  userinterface_name: userinterfaceName,
  reference_name: 'logo',
  ...
})
```

---

## 🔄 Database Schema Changes

### **verifications_references Table**

**Before:**
```sql
CREATE TABLE verifications_references (
    id UUID PRIMARY KEY,
    name TEXT,
    device_model TEXT,  -- ⚠️ OLD
    reference_type TEXT,
    r2_path TEXT,
    r2_url TEXT,
    team_id UUID,
    ...
);
```

**After (migration script adds):**
```sql
CREATE TABLE verifications_references (
    id UUID PRIMARY KEY,
    name TEXT,
    device_model TEXT,  -- ⚠️ Kept for backward compatibility during migration
    userinterface_id UUID REFERENCES userinterfaces(id),  -- ✅ NEW
    reference_type TEXT,
    r2_path TEXT,  -- Updated to use userinterface_name in path
    r2_url TEXT,   -- Updated to use userinterface_name in URL
    team_id UUID,
    ...
);
```

### **Optional: Remove device_model Column**

After verifying everything works (1+ week), you can optionally remove the old column:

```sql
ALTER TABLE verifications_references DROP COLUMN device_model;
```

---

## 🧹 Cleanup (After 1+ Week)

Once you've verified everything works:

### **1. Delete Old R2 Paths**

Manually delete old folders in R2:
- `navigation/android_mobile/`
- `navigation/android_tv/`
- `navigation/stb/`
- `navigation/host_vnc/`
- `reference-images/android_mobile/`
- `reference-images/android_tv/`
- `reference-images/stb/`
- `text-references/android_mobile/`
- `text-references/android_tv/`
- `text-references/stb/`

### **2. Remove device_model Column** (Optional)

```sql
ALTER TABLE verifications_references DROP COLUMN device_model;
```

---

## 📝 Troubleshooting

### **Issue**: "userinterface_name is required"

**Solution**: Frontend not sending `userinterface_name`. Update frontend code to get userinterface from NavigationContext and send it.

### **Issue**: References not loading after migration

**Solution**: 
1. Check if `userinterface_id` is populated in database
2. Verify R2 files were copied successfully
3. Check `r2_path` in database matches actual R2 storage

### **Issue**: "No userinterface found for device_model"

**Solution**: Ensure the device_model is mapped to a userinterface in the `userinterfaces.models` array:

```sql
SELECT name, models FROM userinterfaces;

-- If a device_model is missing, add it:
UPDATE userinterfaces 
SET models = array_append(models, 'new_device_model')
WHERE name = 'your_userinterface_name';
```

---

## 🎉 Benefits

### **Immediate**
1. ✅ Consistent organization (screenshots + references use same structure)
2. ✅ Proper support for web interfaces (`perseus_360_web`, `iad_gui`)
3. ✅ Clear, descriptive paths

### **Long-term**
1. 🚀 Multiple devices can share same UI resources
2. 📈 Scalable for new userinterfaces
3. 🧹 Cleaner codebase and better separation of concerns
4. 🔧 Database properly reflects the UI concept

---

## 📚 Documentation Files

1. ✅ `migrate_screenshots_to_userinterface.py` - Navigation screenshot migration
2. ✅ `migrate_references_to_userinterface.py` - Reference migration
3. ✅ `SCREENSHOT_MIGRATION_GUIDE.md` - Detailed screenshot guide
4. ✅ `REFERENCE_IMAGES_UPDATE.md` - Reference code changes
5. ✅ `COMPLETE_MIGRATION_GUIDE.md` - This file (complete overview)

---

## 🎯 Execution Order

1. Run navigation screenshots migration
2. Verify screenshots work
3. Run references migration
4. Verify references work
5. Update frontend for new references
6. Monitor for 1+ week
7. Optional cleanup (delete old paths, remove old column)

---

**Status**: Ready to execute
**Total Files**: 76 files to migrate
**Estimated Time**: 10-15 minutes
**Risk**: Low (backups preserved, easy rollback)

---

**Created**: October 17, 2025
**Version**: 2.0 (includes reference migration)

