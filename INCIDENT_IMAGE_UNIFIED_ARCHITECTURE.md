# Unified Incident Image Architecture

## Problem Solved
Blackscreen, macroblocks, and audio_loss incidents were missing thumbnails in database because START frame images were being referenced 3+ seconds after the event started, by which time they'd been archived/deleted from hot storage.

## Unified Strategy (ALL Incident Types)

### Flow for Freeze, Blackscreen, Macroblocks, Audio Loss

```
1. Event STARTS
   ↓
2. Copy thumbnail to COLD storage immediately
   (safe from archiver for 1+ hour)
   ↓
3. Wait for INCIDENT_REPORT_DELAY (3s, 5min, or any duration)
   ↓
4. Event still active after delay?
   ├─ YES → Upload from COLD to R2 → Insert to DB with URLs
   └─ NO  → Delete from COLD (cleanup, no R2 upload)
```

### Key Benefits
✅ Works with ANY INCIDENT_REPORT_DELAY duration (3s to hours)  
✅ Doesn't upload to R2 for brief glitches (< delay threshold)  
✅ Same strategy for all incident types (consistent)  
✅ Cold storage safe for 1+ hour (plenty of time)  
✅ Minimal code duplication

## Implementation

### 1. Storage Utility Function
**File:** `shared/src/lib/utils/storage_path_utils.py`

```python
def copy_to_cold_storage(hot_or_cold_path):
    """Copy file from hot to cold storage. If already in cold, return as-is."""
    if '/hot/' not in hot_or_cold_path:
        return hot_or_cold_path  # Already in cold
    
    cold_path = hot_or_cold_path.replace('/hot/', '/')
    os.makedirs(os.path.dirname(cold_path), exist_ok=True)
    
    if os.path.exists(hot_or_cold_path):
        shutil.copy2(hot_or_cold_path, cold_path)
        return cold_path
    
    return None
```

### 2. Event START - Copy to Cold
**File:** `backend_host/scripts/capture_monitor.py`

When blackscreen/macroblocks/audio_loss START:
- Copy thumbnail to cold storage immediately
- Store cold path in `device_state['{event_type}_start_thumbnail_cold']`
- No R2 upload yet (wait for delay)
- Note: Audio loss uses visual thumbnails to show screen state when audio was lost

### 3. After Delay - Upload to R2
**File:** `backend_host/scripts/incident_manager.py`

When incident persists for INCIDENT_REPORT_DELAY:
- Get cold path from device_state
- Upload from cold to R2
- Insert to DB with R2 URLs

### 4. Cleanup on Early Resolution
**File:** `backend_host/scripts/incident_manager.py`

If incident clears before INCIDENT_REPORT_DELAY:
- Delete cold copy (won't be uploaded to R2)
- Clean up device_state

## Special Cases

### Freeze Incidents
Freeze already had paths in `last_3_thumbnails` but they could be in hot storage:
- Copy all 3 thumbnails to cold before R2 upload
- Same timing strategy as other incidents

### Audio Loss Incidents
Audio loss has no visual artifact but uses screen thumbnails:
- Shows what was on screen when audio was lost/restored
- Unified handling with other visual incidents
- Previously had separate R2 upload logic in transcript_accumulator (now removed)

## Testing Scenarios

### Scenario 1: Brief Glitch (< 3s)
- Blackscreen starts → Copy to cold
- Blackscreen clears at 2s → Delete cold copy, no DB insert, no R2 upload
- Result: ✅ No false alarm

### Scenario 2: Real Incident (> 3s with 3s delay)
- Blackscreen starts → Copy to cold
- Wait 3 seconds → Still active
- Upload cold → R2 → DB insert with URL
- Result: ✅ Incident in DB with thumbnail

### Scenario 3: Real Incident (> 5min with 5min delay)
- Blackscreen starts → Copy to cold
- Wait 5 minutes → Still active
- Upload cold → R2 → DB insert with URL
- Cold copy still exists (archiver protects for 1+ hour)
- Result: ✅ Incident in DB with thumbnail

### Scenario 4: Hot Storage with 30s Archival
- Blackscreen starts → Copy to cold (safe!)
- Hot copy deleted at 30s → Cold copy preserved
- Upload at 5min from cold → R2 → DB insert
- Result: ✅ Works perfectly even with fast archival

## Files Modified

1. **`shared/src/lib/utils/storage_path_utils.py`**
   - Added `copy_to_cold_storage()` utility function (13 lines)

2. **`backend_host/scripts/capture_monitor.py`**
   - Event START: Copy thumbnails to cold for blackscreen/macroblocks/audio
   - Event END: Copy closure thumbnails to cold for all incident types
   - Unified handling for all visual incidents

3. **`backend_host/scripts/incident_manager.py`**
   - Upload from cold path (not current filename)
   - Added cold copy cleanup for early resolutions
   - Freeze: Copy to cold before R2 upload
   - Audio loss: Same treatment as blackscreen/macroblocks

4. **`backend_host/scripts/transcript_accumulator.py`**
   - Removed duplicate R2 upload logic for audio_loss (40 lines removed)
   - Now uses unified image handling from capture_monitor

## Configuration

Current settings:
- `INCIDENT_REPORT_DELAY = 3` seconds (in `IncidentManager.__init__`)

Can be changed to any value (30s, 5min, 10min) without code changes.

## Migration from Old Code

### Before (Broken)
```python
# At DB insert time (3+ sec later)
filename = detection_result.get('filename')  # CURRENT filename
thumbnail_path = construct_path(filename)    # START frame may be gone!
upload_to_r2(thumbnail_path)  # FAILS if archived
```

### After (Fixed)
```python
# At event START
cold_path = copy_to_cold_storage(start_thumbnail_path)
device_state['start_thumbnail_cold'] = cold_path

# At DB insert time (3+ sec later)
cold_path = device_state['start_thumbnail_cold']  # Still exists!
upload_to_r2(cold_path)  # SUCCESS
```

## Performance Impact

- **CPU:** Minimal (one `cp` command per incident start)
- **Memory:** None (disk-to-disk copy)
- **Disk:** Temporary ~50KB per incident (cleaned up if < 3s)
- **Network:** No change (R2 upload only for real incidents)

## Monitoring

Logs to watch:
```
✓ Copied {event_type} START to cold storage
✓ Uploaded {event_type} start thumbnail from cold
✓ Cleaned up {event_type} cold thumbnail (cleared before 3s)
⚠️ Cold thumbnail not found for {event_type}
```

