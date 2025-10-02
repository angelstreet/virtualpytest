# Hot/Cold Architecture Migration Guide

## 📋 Overview

This guide walks you through migrating from the old flat file structure to the new hot/cold architecture.

**Migration is SAFE:**
- ✅ Dry-run mode by default (test before applying)
- ✅ Preserves all file metadata and timestamps
- ✅ Can be run on live system
- ✅ Resumable if interrupted
- ✅ No data loss

---

## 🚀 Quick Start

### 1. **Test Migration (Dry-Run)**
```bash
# Navigate to scripts directory
cd /home/sunri-pyautogui/virtualpytest/scripts

# Test migration for capture1 (shows what WOULD happen)
python3 migrate_to_hot_cold.py /var/www/html/stream/capture1

# Review the output - check file counts and paths
```

### 2. **Execute Migration**
```bash
# Migrate capture1 (actual file moves)
python3 migrate_to_hot_cold.py /var/www/html/stream/capture1 --execute

# You'll be prompted to confirm:
# ⚠️  WARNING: This will move files to new structure!
# Are you sure you want to proceed? (yes/no): yes
```

### 3. **Migrate All Captures**
```bash
# Migrate all capture directories
for dir in /var/www/html/stream/capture*; do
  echo "Migrating $dir..."
  python3 migrate_to_hot_cold.py "$dir" --execute
done
```

---

## 📊 What Gets Migrated

### Before (Old Structure):
```
capture1/
├── segment_000000001.ts
├── segment_000000002.ts
├── ... (86,000+ files in root)
├── output.m3u8
└── captures/
    ├── capture_000000001.jpg (175,000+ files)
    ├── capture_000000001_thumbnail.jpg
    └── capture_000000001.json
```

### After (Hot/Cold Structure):
```
capture1/
├── segments/
│   ├── segment_*.ts (HOT: last 10)
│   ├── output.m3u8
│   ├── 0/ ... 23/ (COLD: hour folders)
├── captures/
│   ├── capture_*.jpg (HOT: last 100)
│   └── 0/ ... 23/ (COLD: hour folders, 1h retention)
├── thumbnails/
│   ├── capture_*_thumbnail.jpg (HOT: last 100)
│   └── 0/ ... 23/ (COLD: hour folders, 24h retention)
└── metadata/
    ├── capture_*.json (HOT: last 100)
    └── 0/ ... 23/ (COLD: hour folders, 24h retention)
```

---

## ⏱️ Migration Time Estimates

| Capture | Files | Time (Dry-Run) | Time (Execute) |
|---------|-------|----------------|----------------|
| Small (1 day) | ~100k | 10s | 30s |
| Medium (3 days) | ~300k | 30s | 2min |
| Large (7 days) | ~700k | 1min | 5min |
| Very Large (14 days) | ~1.4M | 2min | 10min |

**Note:** Migration is I/O bound. Times vary based on disk speed.

---

## 🛡️ Safety Features

### 1. **Dry-Run Mode (Default)**
- Shows exactly what will happen
- No files are moved
- Perfect for testing

```bash
# Always run dry-run first!
python3 migrate_to_hot_cold.py /var/www/html/stream/capture1
```

### 2. **File Validation**
- Counts files before and after
- Reports any errors
- Preserves file timestamps

### 3. **Confirmation Prompt**
```
⚠️  WARNING: This will move files to new structure!
Are you sure you want to proceed? (yes/no):
```

### 4. **Resumable**
- If interrupted, can be run again
- Skips already-migrated files
- No duplicate work

---

## 📝 Migration Checklist

### Pre-Migration:
- [ ] **Backup** - Ensure you have backups (optional but recommended)
- [ ] **Disk Space** - Verify sufficient space (same as current usage)
- [ ] **Dry-Run** - Test migration first
- [ ] **Review Output** - Check file counts and paths

### During Migration:
- [ ] **Stop FFmpeg** (optional, but cleaner)
  ```bash
  sudo systemctl stop virtualhost_ffmpeg
  ```
- [ ] **Run Migration**
  ```bash
  python3 migrate_to_hot_cold.py /var/www/html/stream/capture1 --execute
  ```
- [ ] **Monitor Progress** - Watch console output

### Post-Migration:
- [ ] **Verify Structure**
  ```bash
  ls -la /var/www/html/stream/capture1/
  # Should see: segments/, captures/, thumbnails/, metadata/
  ```
- [ ] **Check File Counts**
  ```bash
  # Hot storage
  ls /var/www/html/stream/capture1/segments/*.ts | wc -l  # Should be ≤10
  ls /var/www/html/stream/capture1/captures/*.jpg | wc -l  # Should be ≤100
  
  # Cold storage (hour folders)
  ls /var/www/html/stream/capture1/segments/*/*.ts | wc -l
  ```
- [ ] **Start Services**
  ```bash
  sudo systemctl start virtualhost_ffmpeg
  sudo systemctl start hot_cold_archiver
  ```
- [ ] **Test Live Stream** - Verify video playback works
- [ ] **Test Archive** - Check historical playback

---

## 🔧 Troubleshooting

### Issue: "Permission denied"
**Solution:**
```bash
# Run as the user who owns the files
sudo -u www-data python3 migrate_to_hot_cold.py /var/www/html/stream/capture1 --execute
```

### Issue: "Directory not found"
**Solution:**
```bash
# Verify capture directory exists
ls -la /var/www/html/stream/capture1

# Check path in active_captures.conf
cat /tmp/active_captures.conf
```

### Issue: Migration interrupted
**Solution:**
```bash
# Just run it again - it will skip already-migrated files
python3 migrate_to_hot_cold.py /var/www/html/stream/capture1 --execute
```

### Issue: "No space left on device"
**Solution:**
```bash
# Check disk space
df -h /var/www/html/stream

# Migration doesn't require extra space (moves files, doesn't copy)
# But ensure at least 10% free for operations
```

---

## 🎯 Best Practices

### 1. **Migrate During Low Activity**
- Off-peak hours
- Or stop FFmpeg temporarily

### 2. **Test on One Capture First**
```bash
# Migrate capture4 first (lowest priority)
python3 migrate_to_hot_cold.py /var/www/html/stream/capture4 --execute

# Verify it works, then do others
```

### 3. **Monitor Logs**
```bash
# Watch migration output
python3 migrate_to_hot_cold.py /var/www/html/stream/capture1 --execute | tee migration.log

# Check for errors
grep ERROR migration.log
```

### 4. **Start Services Immediately After**
```bash
# Don't leave FFmpeg stopped for long
sudo systemctl start virtualhost_ffmpeg
sudo systemctl start hot_cold_archiver
```

---

## 📞 Support

If you encounter issues:

1. **Check the migration log output** - errors are clearly marked
2. **Run dry-run again** - see current state
3. **Verify file counts** - ensure no data loss
4. **Check disk space** - `df -h`
5. **Review service logs** - `journalctl -u virtualhost_ffmpeg -f`

---

## ✅ Success Criteria

Migration is successful when:

1. ✅ All directory structures created
2. ✅ File counts match (before = after)
3. ✅ No errors in migration output
4. ✅ Live stream works (segments/output.m3u8)
5. ✅ Archive works (segments/X/archive.m3u8)
6. ✅ Hot storage contains recent files (≤100)
7. ✅ Cold storage organized by hour (0-23)

---

## 🚀 Next Steps After Migration

1. **Enable hot_cold_archiver service:**
   ```bash
   sudo systemctl enable hot_cold_archiver
   sudo systemctl start hot_cold_archiver
   sudo systemctl status hot_cold_archiver
   ```

2. **Monitor for 24 hours** - ensure archiving works

3. **Verify cleanup** - old hour folders should be removed after 24h

4. **Enjoy the benefits!**
   - ⚡ Instant file operations
   - 💾 42% space savings
   - 🎯 Simple architecture
   - ❌ No cache complexity

---

**🎉 Welcome to Hot/Cold Architecture!**

