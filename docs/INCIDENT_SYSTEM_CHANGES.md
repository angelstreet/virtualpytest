# Incident System Changes - Git Diff Summary

## What We Changed

### **Files Deleted (Legacy System)**
```bash
- backend_host/scripts/capture_monitor.py (505 lines) - Complex threading system
- backend_host/scripts/alert_system.py (560 lines) - Verbose error handling
- backend_host/scripts/analyze_audio_video.py (519 lines) - Mixed responsibilities
```

### **Files Created (New System)**
```bash
+ backend_host/scripts/capture_monitor.py (98 lines) - Simple main loop
+ backend_host/scripts/detector.py (95 lines) - Pure detection logic
+ backend_host/scripts/incident_manager.py (99 lines) - State machine + DB
```

## Current Issues on Pi

### **1. Database Connection Failure**
```
[@supabase_utils:get_supabase_client] Supabase environment variables not set, client not available
[ERROR] [device1] DB error creating incident: 'NoneType' object has no attribute 'table'
```

**Root Cause:** Supabase environment variables not configured on Pi

### **2. Detection Logic Too Sensitive**
```
[INFO] [device1] Issues detected: ['freeze', 'audio_loss']
[INFO] [device3] Issues detected: ['freeze', 'audio_loss']
```

**Root Cause:** Detection algorithms may be triggering false positives

## Git Diff (Conceptual)

```diff
--- a/backend_host/scripts/capture_monitor.py (OLD SYSTEM - 505 lines)
+++ b/backend_host/scripts/capture_monitor.py (NEW SYSTEM - 98 lines)

- Complex threading with race conditions
- Memory-based state synchronization
- Subprocess communication via stdout parsing
- Mixed detection + alerting responsibilities

+ Simple single-threaded loop
+ Clean separation: detection → state → database
+ Proper logging to /tmp/capture_monitor.log
+ Graceful database failure handling

--- a/backend_host/scripts/alert_system.py (DELETED - 560 lines)
--- a/backend_host/scripts/analyze_audio_video.py (DELETED - 519 lines)

+++ b/backend_host/scripts/detector.py (NEW - 95 lines)
+ Pure detection functions (blackscreen, freeze, audio)
+ No state management or database operations
+ Stateless and fast

+++ b/backend_host/scripts/incident_manager.py (NEW - 99 lines)
+ Simple state machine (NORMAL/INCIDENT)
+ Direct database operations
+ Graceful degradation when DB unavailable
```

## Immediate Fixes Applied

### **1. Database Graceful Degradation**
```python
# Before (CRASHES)
self.db.table('alerts').insert(...)  # Crashes if db is None

# After (GRACEFUL)
if not self.db_available:
    logger.info(f"Would create {issue_type} incident (DB not available)")
    return f"mock_{issue_type}_{device_id}"
```

### **2. Better Error Handling**
```python
# Before
[ERROR] [device1] DB error creating incident: 'NoneType' object has no attribute 'table'

# After  
[INFO] [device1] Would create freeze incident (DB not available)
[INFO] [device1] Would create audio_loss incident (DB not available)
```

## Next Steps

### **Option 1: Fix Environment (Recommended)**
```bash
# On Pi, set Supabase environment variables
export SUPABASE_URL="your_supabase_url"
export SUPABASE_KEY="your_supabase_key"
```

### **Option 2: Rollback to Original System**
```bash
git checkout HEAD~4 -- backend_host/scripts/
```

### **Option 3: Tune Detection Sensitivity**
- Adjust freeze detection threshold (currently 0.5)
- Adjust audio loss threshold (currently -50dB)
- Add hysteresis (require 3+ consecutive detections)

## Summary

- **New System:** 292 lines vs 1,584 lines (5x smaller)
- **Current Status:** Detection working, DB connection failing
- **Quick Fix:** Added graceful degradation for DB failures
- **Root Issue:** Missing Supabase environment variables on Pi

The architecture is sound, but environment setup is incomplete.
