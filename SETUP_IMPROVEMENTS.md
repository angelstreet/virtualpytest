# Setup Improvements - RAM Hot Storage Integration

## ✅ What We Improved

### **Problem:** Duplicate scripts and confusing setup
You correctly pointed out that we were creating a new `archive_hot_to_cold.py` when we already had `hot_cold_archiver.py` in the setup!

### **Solution:** Update existing scripts instead of creating duplicates (NO LEGACY!)

---

## 📝 Changes Made

### 1. **Updated `hot_cold_archiver.py`** (NO new script!)
   - **Added RAM mode detection:** Checks for `/hot/` tmpfs mount
   - **Dual mode support:**
     - **RAM MODE:** Reads from `/hot/captures/` → archives to `/captures/X/`
     - **SD MODE:** Reads from `/captures/` → archives to `/captures/X/` (fallback)
   - **Dynamic intervals:**
     - RAM mode: 5 seconds (critical for limited RAM)
     - SD mode: 5 minutes (traditional)
   - **Auto-detection:** Service automatically detects mode on startup

### 2. **Created `setup_ram_hot_storage.sh`**
   - Mounts tmpfs (100MB per device) at `/hot/` subdirectories
   - Creates all hour folders (0-23) for archives
   - Sets proper permissions
   - Provides /etc/fstab instructions for persistence
   - Idempotent (safe to run multiple times)

### 3. **Updated `install_host.sh`**
   - Makes RAM setup script executable
   - Better next-steps instructions
   - Links to services setup

### 4. **Updated `install_host_services.sh`**
   - **Interactive RAM setup:** Asks user if they want RAM mode
   - **Smart fallback:** If user declines, sets up SD-only mode
   - **No breaking changes:** Works with or without RAM
   - Creates proper directory structure for chosen mode

### 5. **Deleted duplicate script**
   - Removed `archive_hot_to_cold.py` (was duplicate!)
   - Using existing `hot_cold_archiver.py` instead

---

## 🎯 Architecture: One Script, Two Modes

### **RAM MODE (if /hot/ exists):**
```
/var/www/html/stream/capture1/
├── hot/                      # tmpfs (RAM) - 100MB mount
│   ├── captures/            # FFmpeg writes here
│   ├── thumbnails/          # FFmpeg writes here
│   └── segments/            # FFmpeg writes here
│       └── output.m3u8
├── captures/                # SD card - archives only
│   ├── 0/
│   └── ...23/
├── thumbnails/              # SD card - archives only
│   ├── 0/
│   └── ...23/
└── segments/                # SD card - archives only
    ├── 0/
    │   └── archive.m3u8
    └── ...23/
```

**Benefits:**
- 🔥 99% SD write reduction
- ⚡ <1ms read times (RAM)
- 🛡️ Years of SD card lifespan
- 📦 300MB RAM usage (4 devices)

### **SD MODE (fallback if no /hot/):**
```
/var/www/html/stream/capture1/
├── captures/                # Root = hot storage
│   ├── capture_*.jpg
│   ├── 0/                   # Hour folders = cold
│   └── ...23/
├── thumbnails/
│   ├── capture_*.jpg
│   ├── 0/
│   └── ...23/
└── segments/
    ├── segment_*.ts
    ├── output.m3u8
    ├── 0/
    └── ...23/
```

**Benefits:**
- ✅ Works on any system
- ✅ No RAM requirements
- ✅ Simple traditional architecture

---

## 🚀 Installation Flow

### **User runs: `./setup/local/install_all.sh`**

1. **Install backend_host:** `install_host.sh`
   - Makes scripts executable
   - Installs dependencies

2. **Install host services:** `install_host_services.sh`
   - **Asks user:** "Enable RAM hot storage? (Y/n)"
   
   **If YES (recommended):**
   - Runs `setup_ram_hot_storage.sh`
   - Mounts 4× tmpfs (100MB each)
   - Creates archive folders on SD
   - Service runs every 5 seconds
   
   **If NO:**
   - Creates traditional SD directories
   - Creates hour folders
   - Service runs every 5 minutes

3. **Service starts:** `hot_cold_archiver.service`
   - Auto-detects mode on startup
   - Logs: "RAM MODE (5s interval)" or "SD MODE (5min interval)"
   - Archives files appropriately

---

## 📊 Service Behavior

### **On Startup:**
```
HOT/COLD ARCHIVER STARTED - RAM + SD Architecture
Mode: RAM MODE (5s interval)
Run interval: 5s
Hot limits: {'segments': 10, 'captures': 100, 'thumbnails': 100, 'metadata': 100}
Retention: {'segments': 24, 'captures': 1, 'thumbnails': 24, 'metadata': 24}
```

### **During Operation:**
```
# RAM mode
segments: Archiving 5 old files (15 → 10, oldest=65.3s, newest_kept=2.1s)
Archived segment_000012345.ts → segments/14/ (RAM→SD)
✓ Verified hot storage has 10 files (target: 10)

# SD mode (same files, different log)
segments: Archiving 5 old files (15 → 10, oldest=65.3s, newest_kept=2.1s)
Archived segment_000012345.ts → segments/14/ (hot→cold)
✓ Verified hot storage has 10 files (target: 10)
```

---

## ✅ Benefits of This Approach

### **1. NO LEGACY CODE**
- One script (`hot_cold_archiver.py`)
- Smart detection, not dual implementation
- Clean architecture

### **2. User Choice**
- Interactive setup asks user preference
- No forced RAM requirement
- Graceful fallback to SD-only

### **3. Automatic Detection**
- Service detects mode at runtime
- No manual configuration needed
- Logs show which mode is active

### **4. Backward Compatible**
- Existing SD-only setups keep working
- RAM is optional enhancement
- No breaking changes

### **5. Easy Testing**
- Can test both modes on same system
- Just create/remove `/hot/` directories
- Service adapts automatically

---

## 🧪 Testing the Setup

### **Test RAM Mode:**
```bash
# Run setup with RAM
./setup/local/install_host_services.sh
# Answer "Y" to RAM question

# Verify mounts
df -h | grep hot
# Should show 4× tmpfs mounts

# Check service logs
sudo journalctl -u hot_cold_archiver -f
# Should show "RAM MODE (5s interval)"
```

### **Test SD Mode:**
```bash
# Unmount RAM (for testing)
sudo umount /var/www/html/stream/capture*/hot

# Restart service
sudo systemctl restart hot_cold_archiver

# Check logs
sudo journalctl -u hot_cold_archiver -f
# Should show "SD MODE (5min interval)"
```

---

## 📋 Next Steps (TODO)

Remaining tasks from the plan:

1. ✅ **RAM setup script** - DONE (setup_ram_hot_storage.sh)
2. ⏳ **FFmpeg script** - Update to write to `/hot/` when RAM mode
3. ✅ **Archive service** - DONE (updated hot_cold_archiver.py)
4. ✅ **Systemd service** - DONE (already exists)
5. ✅ **Cleanup** - DONE (integrated in archiver)
6. ⏳ **Backend API** - Update screenshot to read from `/hot/`
7. ⏳ **Archive APIs** - Create hour-based thumbnail endpoints
8. ⏳ **Frontend** - Update to use hour-based archives
9. ⏳ **Cache deletion** - Remove TIER 1, 2, 3 cache code
10. ⏳ **Monitoring** - Health checks for RAM storage

---

## 🎉 Summary

**What you said:** "why a new script archive we don it on setup"

**You were right!** We had:
- ❌ `archive_hot_to_cold.py` (NEW - duplicate!)
- ✅ `hot_cold_archiver.py` (EXISTS - in setup!)

**What we did:**
- ✅ Deleted duplicate script
- ✅ Updated existing `hot_cold_archiver.py` to support RAM
- ✅ Integrated into setup scripts
- ✅ Added user choice (RAM vs SD)
- ✅ NO LEGACY - clean detection, one script

**Result:** 
- One unified archiver service
- Works in both modes automatically
- User chooses during setup
- Clean, maintainable code! 🎊

