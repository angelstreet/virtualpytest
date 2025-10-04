# Hot/Cold File Architecture - RAM + SD Card System

**Goal:** Eliminate caching complexity and SD card wear by using RAM for hot storage and SD card for cold archives.

**Core Principle:** 
- **HOT (RAM):** Small (≤100 files), ephemeral, ultra-fast writes/reads
- **COLD (SD):** Hourly archives, persistent, minimal writes

**Benefits:**
- 🔥 **99% reduction in SD card writes** (extends lifespan years)
- ⚡ **10x faster operations** (<1ms vs 5ms)
- 💪 **Zero cache complexity** (no caching needed)
- 📦 **Simple architecture** (hot=RAM, cold=SD)

---

## 📁 NEW FOLDER STRUCTURE (RAM + SD)

**HOT (RAM tmpfs mount):**
```
/var/www/html/stream/capture1/hot/    # 100MB tmpfs - ephemeral
├── captures/
│   └── capture_*.jpg                 # Last 100 files (~50s of data)
├── thumbnails/
│   └── capture_*_thumbnail.jpg       # Last 100 files (~20s of data)
└── segments/
    ├── segment_*.ts                  # Last 10 segments (~10s HLS window)
    └── output.m3u8                   # Live manifest
```

**COLD (SD card persistent archive):**
```
/var/www/html/stream/capture1/
├── captures/              # Full-res images (1h retention)
│   ├── 0/                 # Hour 0 (00:00-00:59)
│   ├── 1/                 # Hour 1
│   ├── ...
│   └── 23/                # Hour 23
│
├── thumbnails/            # Thumbnails (24h retention)
│   ├── 0/
│   ├── ...
│   └── 23/
│
├── metadata/              # JSON analysis (24h retention)
│   ├── 0/
│   ├── ...
│   └── 23/
│
└── segments/              # HLS segments (24h retention)
    ├── 0/
    │   └── archive.m3u8   # Hour 0 manifest
    ├── ...
    └── 23/
```

**Key Principles:**
- **FFmpeg writes ONLY to RAM** (`/hot/` directory)
- **Archival service moves to SD** (when limits exceeded)
- **Backend reads RAM for live, SD for history**
- **99% write reduction on SD card**

---

## 📊 FILE LIMITS & PERFORMANCE

| Location | Storage | Max Files | Operation Time | Cache? | Retention |
|----------|---------|-----------|----------------|--------|-----------|
| `hot/segments/` | **RAM** | 10 | **<0.1ms** | ❌ NO | Live HLS |
| `hot/captures/` | **RAM** | 100 | **<1ms** | ❌ NO | ~50s |
| `hot/thumbnails/` | **RAM** | 100 | **<1ms** | ❌ NO | ~20s |
| `captures/X/` | SD | ~7,200 | 20ms | ❌ NO | 1h |
| `thumbnails/X/` | SD | ~18,000 | 50ms | ❌ NO | 24h |
| `metadata/X/` | SD | ~7,200 | 20ms | ❌ NO | 24h |
| `segments/X/` | SD | 3,600 | 20ms | ❌ NO | 24h |

**Result: NO CACHE NEEDED!** RAM hot storage is ultra-fast, SD archives are fast enough.

### **🔥 Retention Policy (Optimized for Space):**
- **Captures (full-res)**: **1 hour max** - Large files (~500KB), only for recent incident verification
- **Thumbnails**: 24 hours - Small files (~50KB), needed for heatmap/gallery
- **Metadata**: 24 hours - Tiny files (~2KB), needed for incident analysis  
- **Segments**: 24 hours - Video files, needed for playback

**Space Savings:** Full-res captures are 85% of total space. 1h retention = huge savings! 💰

### **💾 SD Card Write Reduction:**
- **Before (direct writes):** ~600,000 writes/day per device
  - 2 captures/sec = 172,800 writes/day
  - 5 thumbnails/sec = 432,000 writes/day
  - Segments every 1s = constant writes
- **After (RAM hot storage):** ~6,000 writes/day per device
  - Only archival moves to SD (once per file)
  - **99% write reduction = years of SD card lifespan!** 🎉

---

## 🔧 PHASE 1: FFMPEG CHANGES

### **File:** `backend_host/scripts/run_ffmpeg_and_rename_local.sh`

### **Changes Required:**

#### **1. Create Directory Structure on Startup**
```bash
setup_capture_directories() {
  local capture_dir=$1
  
  # Create root directories (hot storage)
  mkdir -p "$capture_dir/segments"
  mkdir -p "$capture_dir/captures"
  mkdir -p "$capture_dir/thumbnails"
  mkdir -p "$capture_dir/metadata"
  
  # Create 24 hour folders for EACH type (unified architecture)
  for hour in {0..23}; do
    mkdir -p "$capture_dir/segments/$hour"
    mkdir -p "$capture_dir/captures/$hour"
    mkdir -p "$capture_dir/thumbnails/$hour"
    mkdir -p "$capture_dir/metadata/$hour"
  done
  
  echo "✓ Created unified hot/cold structure for $capture_dir"
  echo "  - segments/    : 10 hot + 24 hour folders"
  echo "  - captures/    : 100 hot + 24 hour folders"
  echo "  - thumbnails/  : 100 hot + 24 hour folders"
  echo "  - metadata/    : 100 hot + 24 hour folders"
}
```

#### **2. Update FFmpeg Output Paths**
```bash
# BEFORE:
-hls_segment_filename $capture_dir/segment_%09d.ts \
$capture_dir/output.m3u8 \
$capture_dir/captures/capture_%09d.jpg \
$capture_dir/captures/capture_%09d_thumbnail.jpg

# AFTER:
-hls_segment_filename $capture_dir/segments/segment_%09d.ts \
$capture_dir/segments/output.m3u8 \
$capture_dir/captures/capture_%09d.jpg \
$capture_dir/thumbnails/capture_%09d_thumbnail.jpg
```

**Note:** FFmpeg writes to HOT storage (root of captures/thumbnails), archival process moves to hour folders.

---

## 🗄️ PHASE 2: ARCHIVAL SERVICE (NEW)

### **File:** `backend_host/scripts/archive_hot_to_cold.py` (NEW)

### **Purpose:** 
- Move files from hot storage (root) to cold storage (hour folders)
- Keep only last 100 files in hot storage
- Run every 60 seconds

### **Implementation:**

```python
#!/usr/bin/env python3
"""
Hot-to-Cold Archival Service
Moves files from hot storage (root) to hour folders when > 100 files
Runs every 60 seconds
"""
import os
import sys
import time
import shutil
import logging
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('/tmp/archive_hot_to_cold.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

HOT_STORAGE_LIMIT = 100  # Keep last 100 files in hot storage
ARCHIVE_INTERVAL = 60  # Check every 60 seconds

def get_file_hour(filepath: str) -> int:
    """Get hour (0-23) from file mtime"""
    mtime = os.path.getmtime(filepath)
    return datetime.fromtimestamp(mtime).hour

def archive_folder(hot_dir: str, cold_base: str, pattern: str):
    """
    Move old files from hot storage to hour folders
    
    Args:
        hot_dir: Hot storage directory (e.g., /captures/)
        cold_base: Cold storage base (same as hot_dir, hour folders inside)
        pattern: File pattern (e.g., "capture_*.jpg")
    """
    try:
        # Get all files matching pattern in hot storage (not in subdirs)
        hot_files = sorted(
            [f for f in Path(hot_dir).glob(pattern) if f.is_file()],
            key=lambda f: f.stat().st_mtime
        )
        
        if len(hot_files) <= HOT_STORAGE_LIMIT:
            logger.debug(f"{hot_dir}: {len(hot_files)} files (within limit)")
            return
        
        # Move oldest files to hour folders
        files_to_archive = hot_files[:-HOT_STORAGE_LIMIT]
        
        logger.info(f"{hot_dir}: Archiving {len(files_to_archive)} files (total: {len(hot_files)})")
        
        for filepath in files_to_archive:
            try:
                # Determine destination hour folder
                file_hour = get_file_hour(str(filepath))
                hour_folder = os.path.join(cold_base, str(file_hour))
                
                # Move file
                dest_path = os.path.join(hour_folder, filepath.name)
                shutil.move(str(filepath), dest_path)
                
                logger.debug(f"Moved {filepath.name} → hour {file_hour}")
                
            except Exception as e:
                logger.error(f"Error moving {filepath}: {e}")
                
    except Exception as e:
        logger.error(f"Error archiving {hot_dir}: {e}")

def archive_segments(capture_dir: str):
    """
    Archive segments using UNIFIED architecture
    Keep last 10 in root (HLS window), move older to hour folders
    SAME PATTERN as captures/thumbnails/metadata
    """
    try:
        segments_dir = os.path.join(capture_dir, 'segments')
        
        # Get all segments in ROOT (not subdirs), sorted by number
        segments = sorted(
            [f for f in Path(segments_dir).glob('segment_*.ts') if f.is_file()],
            key=lambda f: int(f.stem.split('_')[1])
        )
        
        # Keep last 10 in live folder (HLS window)
        if len(segments) <= 10:
            return
        
        segments_to_archive = segments[:-10]
        
        logger.info(f"Segments: Archiving {len(segments_to_archive)} old segments")
        
        for seg_path in segments_to_archive:
            try:
                # Get hour from mtime
                seg_hour = get_file_hour(str(seg_path))
                # UNIFIED: hour folder is subdirectory of segments/, not separate archive/
                hour_folder = os.path.join(segments_dir, str(seg_hour))
                
                # Move segment
                dest_path = os.path.join(hour_folder, seg_path.name)
                shutil.move(str(seg_path), dest_path)
                
                logger.debug(f"Archived {seg_path.name} → segments/{seg_hour}/")
                
            except Exception as e:
                logger.error(f"Error archiving segment {seg_path}: {e}")
                
    except Exception as e:
        logger.error(f"Error archiving segments: {e}")

def archive_cycle():
    """One archive cycle for all capture directories"""
    # Use centralized utilities - respects hot/cold storage architecture
    from shared.src.lib.utils.storage_path_utils import get_capture_base_directories
    
    capture_dirs = get_capture_base_directories()
    
    for capture_dir in capture_dirs:
        if not os.path.exists(capture_dir):
            continue
        
        device_name = os.path.basename(capture_dir)
        logger.debug(f"Processing {device_name}...")
        
        # Archive captures (full-res images)
        captures_dir = os.path.join(capture_dir, 'captures')
        if os.path.exists(captures_dir):
            archive_folder(captures_dir, captures_dir, 'capture_*.jpg')
        
        # Archive thumbnails
        thumbnails_dir = os.path.join(capture_dir, 'thumbnails')
        if os.path.exists(thumbnails_dir):
            archive_folder(thumbnails_dir, thumbnails_dir, 'capture_*_thumbnail.jpg')
        
        # Archive metadata (JSON)
        metadata_dir = os.path.join(capture_dir, 'metadata')
        if os.path.exists(metadata_dir):
            archive_folder(metadata_dir, metadata_dir, 'capture_*.json')
        
        # Archive segments (special handling)
        archive_segments(capture_dir)

def main():
    """Main service loop"""
    logger.info("=" * 80)
    logger.info("Hot-to-Cold Archival Service")
    logger.info(f"Hot storage limit: {HOT_STORAGE_LIMIT} files")
    logger.info(f"Check interval: {ARCHIVE_INTERVAL}s")
    logger.info("=" * 80)
    
    while True:
        try:
            start_time = time.time()
            archive_cycle()
            elapsed = time.time() - start_time
            logger.debug(f"Archive cycle completed ({elapsed:.2f}s)")
            
            time.sleep(ARCHIVE_INTERVAL)
            
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            break
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            time.sleep(10)

if __name__ == '__main__':
    main()
```

### **Systemd Service:** `backend_host/config/services/archive_hot_to_cold.service`
```ini
[Unit]
Description=Hot-to-Cold Archival Service
After=network.target

[Service]
Type=simple
User=sunri-pm
WorkingDirectory=/home/sunri-pm/virtualpytest/backend_host
ExecStart=/home/sunri-pm/virtualpytest/venv/bin/python3 /home/sunri-pm/virtualpytest/backend_host/scripts/archive_hot_to_cold.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

---

## 🧹 PHASE 3: CLEANUP CHANGES

### **File:** `backend_host/scripts/clean_captures.sh`

### **Changes Required:**

```bash
#!/bin/bash
# SIMPLIFIED CLEANUP - Delete old hour folders

CLEAN_LOG="/tmp/clean.log"
> "$CLEAN_LOG"

# Get capture directories
CAPTURE_DIRS=(
  "/var/www/html/stream/capture1"
  "/var/www/html/stream/capture2"
  "/var/www/html/stream/capture3"
  "/var/www/html/stream/capture4"
)

# Current hour (0-23)
CURRENT_HOUR=$(date +%-H)

# Calculate 24 hours ago hour
CUTOFF_HOUR=$(( (CURRENT_HOUR + 1) % 24 ))

for CAPTURE_DIR in "${CAPTURE_DIRS[@]}"; do
  if [ ! -d "$CAPTURE_DIR" ]; then
    continue
  fi
  
  echo "$(date): Cleaning $CAPTURE_DIR" >> "$CLEAN_LOG"
  
  # Delete hour folder that's 24+ hours old
  # Example: If current hour is 14, delete hour 15 (which is 23 hours old)
  OLD_HOUR_FOLDER="$CUTOFF_HOUR"
  
  # Clean captures
  if [ -d "$CAPTURE_DIR/captures/$OLD_HOUR_FOLDER" ]; then
    echo "$(date): Deleting captures/$OLD_HOUR_FOLDER (24h old)" >> "$CLEAN_LOG"
    rm -rf "$CAPTURE_DIR/captures/$OLD_HOUR_FOLDER"
    mkdir -p "$CAPTURE_DIR/captures/$OLD_HOUR_FOLDER"
  fi
  
  # Clean thumbnails
  if [ -d "$CAPTURE_DIR/thumbnails/$OLD_HOUR_FOLDER" ]; then
    echo "$(date): Deleting thumbnails/$OLD_HOUR_FOLDER (24h old)" >> "$CLEAN_LOG"
    rm -rf "$CAPTURE_DIR/thumbnails/$OLD_HOUR_FOLDER"
    mkdir -p "$CAPTURE_DIR/thumbnails/$OLD_HOUR_FOLDER"
  fi
  
  # Clean metadata
  if [ -d "$CAPTURE_DIR/metadata/$OLD_HOUR_FOLDER" ]; then
    echo "$(date): Deleting metadata/$OLD_HOUR_FOLDER (24h old)" >> "$CLEAN_LOG"
    rm -rf "$CAPTURE_DIR/metadata/$OLD_HOUR_FOLDER"
    mkdir -p "$CAPTURE_DIR/metadata/$OLD_HOUR_FOLDER"
  fi
  
  # Clean segments (UNIFIED architecture)
  if [ -d "$CAPTURE_DIR/segments/$OLD_HOUR_FOLDER" ]; then
    echo "$(date): Deleting segments/$OLD_HOUR_FOLDER (24h old)" >> "$CLEAN_LOG"
    rm -rf "$CAPTURE_DIR/segments/$OLD_HOUR_FOLDER"
    mkdir -p "$CAPTURE_DIR/segments/$OLD_HOUR_FOLDER"
  fi
  
  echo "$(date): ✓ Cleaned $CAPTURE_DIR" >> "$CLEAN_LOG"
done
```

**Result:** Cleanup is now INSTANT (delete folder vs find+filter millions of files)!

---

## 🔌 PHASE 4: BACKEND API CHANGES

### **A. Screenshot API** (`base_controller.py`)

```python
def take_screenshot(self, filename: str = None) -> Optional[str]:
    """Take screenshot from hot storage (always fast, max 100 files)"""
    try:
        import time
        import os
        from pathlib import Path
        
        # Hot storage path
        captures_dir = f"{self.video_capture_path}/captures"
        
        # Get latest JPG from hot storage (max 100 files)
        jpg_files = sorted(
            Path(captures_dir).glob('capture_*.jpg'),
            key=lambda f: f.stat().st_mtime,
            reverse=True
        )
        
        if not jpg_files:
            print(f"[{self.capture_source}]: No images in hot storage")
            return None
        
        latest_jpg = str(jpg_files[0])
        age = time.time() - os.path.getmtime(latest_jpg)
        
        if age > 3:
            print(f"[{self.capture_source}]: Latest image too old: {age:.2f}s")
            return None
        
        print(f"[{self.capture_source}]: Using hot storage (age: {age:.2f}s)")
        return latest_jpg
        
    except Exception as e:
        print(f'[{self.capture_source}]: ERROR: {e}')
        return None
```

**Performance:** 100 files max → <5ms (no cache needed!)

---

### **B. Thumbnail Heatmap API** (NEW endpoint)

```python
@host_monitoring_bp.route('/api/host/thumbnails/<device_name>/<int:hour>', methods=['GET'])
def get_thumbnails_for_hour(device_name: str, hour: int):
    """
    Get thumbnails for specific hour
    Used by heatmap to display 24h of thumbnails
    
    Args:
        device_name: e.g., 'capture1'
        hour: 0-23
    """
    try:
        # Get thumbnails from hour folder
        thumbnails_dir = f'/var/www/html/stream/{device_name}/thumbnails/{hour}'
        
        if not os.path.exists(thumbnails_dir):
            return jsonify({'error': 'Hour folder not found'}), 404
        
        # Get all thumbnails
        thumbnails = sorted(
            Path(thumbnails_dir).glob('capture_*_thumbnail.jpg'),
            key=lambda f: int(f.stem.split('_')[1])  # Sort by number
        )
        
        # Build URLs
        thumbnail_urls = [
            f'/host/stream/{device_name}/thumbnails/{hour}/{thumb.name}'
            for thumb in thumbnails
        ]
        
        return jsonify({
            'hour': hour,
            'count': len(thumbnail_urls),
            'thumbnails': thumbnail_urls
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

---

### **C. Archive Manifest API** (UPDATED)

```python
def update_archive_manifest_incremental(capture_dir):
    """
    SIMPLIFIED: Create manifest for current hour's segments
    UNIFIED architecture: segments/XX/archive.m3u8
    """
    try:
        current_hour = datetime.now().hour
        # UNIFIED: hour folder is inside segments/
        hour_dir = os.path.join(capture_dir, 'segments', str(current_hour))
        
        if not os.path.exists(hour_dir):
            return
        
        # Get segments from current hour folder
        segments = sorted(
            Path(hour_dir).glob('segment_*.ts'),
            key=lambda f: int(f.stem.split('_')[1])
        )
        
        if not segments:
            return
        
        # Generate manifest for this hour
        manifest_path = os.path.join(hour_dir, 'archive.m3u8')
        
        with open(manifest_path, 'w') as f:
            f.write('#EXTM3U\n')
            f.write('#EXT-X-VERSION:3\n')
            f.write('#EXT-X-TARGETDURATION:4\n')
            f.write(f'#EXT-X-MEDIA-SEQUENCE:{int(segments[0].stem.split("_")[1])}\n')
            
            for seg in segments:
                f.write('#EXTINF:1.000000,\n')
                f.write(f'{seg.name}\n')
            
            f.write('#EXT-X-ENDLIST\n')
        
        logger.info(f"Generated manifest: segments/{current_hour}/archive.m3u8 ({len(segments)} segments)")
        
    except Exception as e:
        logger.error(f"Error generating archive manifest: {e}")
```

**Performance:** Max 3,600 segments per hour → 20ms (no cache needed!)

---

## 🎨 PHASE 5: FRONTEND CHANGES

### **A. Screenshot Display** (No change needed!)
```typescript
// Existing endpoint works - just faster now!
const response = await fetch('/api/host/screenshot/capture1');
```

### **B. Heatmap - 24h Thumbnails**

```typescript
interface ThumbnailHeatmap {
  async loadHeatmap(deviceName: string) {
    const hours = Array.from({length: 24}, (_, i) => i);
    
    // Load thumbnails for each hour
    const hourlyData = await Promise.all(
      hours.map(hour => 
        fetch(`/api/host/thumbnails/${deviceName}/${hour}`)
          .then(r => r.json())
      )
    );
    
    // Combine into 24h view
    return hourlyData.flatMap(data => data.thumbnails);
  }
}
```

### **C. Archive Video Player**

```typescript
interface ArchivePlayer {
  async playHour(deviceName: string, hour: number) {
    // Load HLS manifest for specific hour (UNIFIED path)
    const manifestUrl = `/host/stream/${deviceName}/segments/${hour}/archive.m3u8`;
    
    // Use existing HLS player
    player.loadSource(manifestUrl);
  }
}
```

---

## 📈 PERFORMANCE COMPARISON

### **Before (Mixed Folders + Complex Cache):**

| Operation | Method | Files Scanned | Time | Cache? |
|-----------|--------|---------------|------|--------|
| Screenshot | Scan + filter | 867,000 | 50-200ms | ✅ TIER 1 |
| Count images | Scan + filter | 867,000 | 500ms-2s | ✅ TIER 2 |
| Heatmap | Scan + filter | 432,000 | 1-2s | ✅ TIER 2 |
| Archive manifest | Scan + sort | 86,400 | 1-2s | ✅ TIER 2 |
| Cleanup | Find old files | 1M+ | 5-10s | ❌ |

**Total:** 3 cache tiers, ~2,000 lines of code

---

### **After (Hot/Cold + No Cache):**

| Operation | Method | Files Scanned | Time | Cache? |
|-----------|--------|---------------|------|--------|
| Screenshot | Scan hot storage | 100 | <5ms | ❌ NO |
| Count images | Count hot storage | 100 | <5ms | ❌ NO |
| Heatmap | Load hour folder | 18,000 | 50ms | ❌ NO |
| Archive manifest | Read hour folder | 3,600 | 20ms | ❌ NO |
| Cleanup | Delete hour folder | 0 (instant) | <1ms | ❌ NO |

**Total:** Zero cache, ~200 lines of code

---

## 🚀 MIGRATION PLAN

### **Phase 1: Create Structure (No Breaking Changes)**
1. Update `run_ffmpeg_and_rename_local.sh` to create new folders
2. FFmpeg continues writing to same paths
3. Deploy and test

### **Phase 2: Add Archival Service**
1. Deploy `archive_hot_to_cold.py`
2. Files start moving to hour folders automatically
3. Old and new systems coexist

### **Phase 3: Update Backend APIs**
1. Update screenshot API to read from hot storage
2. Add new thumbnail/archive endpoints
3. Old paths still work (backwards compatible)

### **Phase 4: Update Frontend**
1. Update heatmap to use hour-based API
2. Update archive player
3. Test thoroughly

### **Phase 5: Cleanup**
1. Remove old cache code (TIER 1, 2, 3)
2. Simplify cleanup script
3. Delete old mixed-folder files

### **Phase 6: Monitoring**
1. Monitor hot storage size (should stay ~100)
2. Monitor archival service logs
3. Verify 24h retention working

---

## ✅ VALIDATION CHECKLIST

- [ ] FFmpeg creates new folder structure on startup
- [ ] FFmpeg writes to correct paths (captures/, thumbnails/, segments/)
- [ ] Archival service moves files when >100 in hot storage
- [ ] Hour folders contain correct files
- [ ] Screenshot API returns latest image <5ms
- [ ] Heatmap displays 24h of thumbnails
- [ ] Archive manifests load correctly
- [ ] Cleanup deletes 24h old hour folders
- [ ] No timeouts or performance issues
- [ ] Removed all cache code (TIER 1, 2, 3)

---

## 🎯 EXPECTED RESULTS

**Performance:**
- Screenshot API: 50-200ms → <5ms (10-40x faster)
- Count operations: 500ms-2s → <5ms (100-400x faster)
- Cleanup: 5-10s → <1ms (1000x faster)

**Complexity:**
- Code: 2,000 lines → 200 lines (10x simpler)
- Services: 3 cache services → 0 cache services
- Maintenance: High → Low

**Scalability:**
- File limits: Unbounded → Bounded (100 hot, 18k/hour cold)
- Predictable: No → Yes

**Result: Simple, fast, maintainable architecture with ZERO caching complexity!** 🎉

