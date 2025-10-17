# Reference Images Update: device_model → userinterface

## ✅ What Was Updated

As part of the screenshot migration to userinterface-based paths, **reference images** have also been updated to use the same structure.

---

## 📁 Path Changes

### **Before (device_model-based)**
```
R2 Storage:
reference-images/
├── android_mobile/
│   ├── logo.jpg
│   ├── button_play.jpg
│   └── menu_settings.jpg
├── android_tv/
├── stb/
└── host_vnc/
```

### **After (userinterface-based)**
```
R2 Storage:
reference-images/
├── horizon_android_mobile/
│   ├── logo.jpg
│   ├── button_play.jpg
│   └── menu_settings.jpg
├── horizon_android_tv/
├── horizon_tv/
├── perseus_360_web/
└── iad_gui/
```

---

## 🔧 Code Changes Made

### **1. Cloudflare Utils** (`shared/src/lib/utils/cloudflare_utils.py`)

```python
# Before:
def upload_reference_image(local_path: str, model: str, image_name: str)
remote_path = f"reference-images/{model}/{image_name}"

# After:
def upload_reference_image(local_path: str, userinterface_name: str, image_name: str)
remote_path = f"reference-images/{userinterface_name}/{image_name}"
```

### **2. Image Helpers** (`backend_host/src/controllers/verification/image_helpers.py`)

```python
# Before:
def save_image_reference(self, image_path: str, reference_name: str, device_model: str, team_id: str, area: Dict[str, Any] = None)
upload_reference_image(image_path, device_model, r2_filename)

# After:
def save_image_reference(self, image_path: str, reference_name: str, userinterface_name: str, team_id: str, area: Dict[str, Any] = None)
upload_reference_image(image_path, userinterface_name, r2_filename)
```

### **3. Image Controller** (`backend_host/src/controllers/verification/image.py`)

```python
# Before:
device_model = data.get('device_model')
if not device_model:
    return {'success': False, 'message': 'device_model is required for saving reference'}
save_result = self.helpers.save_image_reference(image_saved_path, reference_name, device_model, team_id, area)

# After:
userinterface_name = data.get('userinterface_name')
if not userinterface_name:
    return {'success': False, 'message': 'userinterface_name is required for saving reference'}
save_result = self.helpers.save_image_reference(image_saved_path, reference_name, userinterface_name, team_id, area)
```

---

## 🎯 Impact

### **For Navigation Screenshots**
- ✅ Already updated in the main migration
- ✅ Frontend sends `userinterface_name`
- ✅ Backend saves to `navigation/{userinterface_name}/`

### **For Reference Images**
- ✅ Backend code updated to use `userinterface_name`
- ⚠️ **Frontend needs to send `userinterface_name` instead of `device_model`**
- ✅ Backend saves to `reference-images/{userinterface_name}/`

---

## 📝 Frontend Update Required

The frontend code that saves reference images needs to be updated to send `userinterface_name` instead of `device_model`:

```typescript
// Before:
body: JSON.stringify({
  device_model: currentDeviceModel,  // e.g., 'android_mobile'
  reference_name: 'logo',
  ...
})

// After:
body: JSON.stringify({
  userinterface_name: userinterfaceName,  // e.g., 'horizon_android_mobile'
  reference_name: 'logo',
  ...
})
```

**Location**: Find where reference images are saved in the frontend (likely in a verification or reference management component).

---

## 🔄 Migration for Existing Reference Images

If you have existing reference images, you'll need to migrate them similar to the navigation screenshots:

### **Option 1: Let Them Accumulate**
- Old reference images stay in `reference-images/{device_model}/`
- New reference images go to `reference-images/{userinterface_name}/`
- Eventually delete old paths after all references are recreated

### **Option 2: Migrate Existing References**
- Query database for all verification references
- Copy files in R2 from `device_model` to `userinterface_name` paths
- Update database URLs
- Similar process to the screenshot migration

---

## ✅ Benefits

1. **Consistency**: Reference images and navigation screenshots use the same structure
2. **Clarity**: `perseus_360_web` is clearer than `host_vnc`
3. **Reusability**: Same UI on different devices can share references
4. **Organization**: Better structure for multi-interface testing

---

## 🎉 Summary

- ✅ Backend code updated to use `userinterface_name`
- ✅ Same pattern as navigation screenshots
- ✅ Clean, consistent API
- ⚠️ Frontend update needed to send `userinterface_name`

**Status**: Backend ready, frontend update pending

---

**Created**: October 17, 2025
**Part of**: Screenshot Migration to UserInterface-based Paths

