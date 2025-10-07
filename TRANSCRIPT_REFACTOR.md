# Transcript Accumulator Refactor - State File Removal

## Problem

The old `transcript_state.json` file had a fatal flaw:
- State file lived at device root, **not** inside hour folders
- Cleanup script deletes hour folders every 24h
- State keys like `"13/chunk_10min_0.mp3"` remained forever
- After 24h, same key exists but references **different file**
- Result: **Transcripts stopped working after 24 hours** (skipped new files)

## Solution

**MP3 files are source of truth. Manifest reflects reality.**

### Changes

1. **Removed state file logic** - No more `transcript_state.json`
2. **mtime-based comparison** - Compare MP3 vs transcript modification times
3. **Orphaned transcript reconciliation** - Mark transcripts as unavailable when MP3 deleted
4. **Manifest tracks MP3 availability** - `has_mp3: false` when MP3 is gone

### New Logic

```python
# 1. Check if transcription needed
def should_transcribe(mp3_path, transcript_path):
    if not exists(transcript_path):
        return True  # No transcript
    if mp3_mtime > transcript_mtime:
        return True  # MP3 newer (24h rotation)
    return False  # Up-to-date

# 2. Reconcile orphaned transcripts
for transcript in all_transcripts:
    if corresponding_mp3 not in mp3_set:
        update_manifest(has_mp3=False)
```

### Manifest Structure

```json
{
  "chunks": [
    {
      "hour": 13,
      "chunk_index": 0,
      "has_transcript": true,
      "has_mp3": true,              ← NEW
      "language": "en",
      "confidence": 0.95
    },
    {
      "hour": 14,
      "chunk_index": 2,
      "has_transcript": true,
      "has_mp3": false,             ← MP3 deleted
      "unavailable_since": "2025-10-08T14:00:00"
    }
  ]
}
```

## Benefits

✅ **No state file bloat** - No indefinite growth
✅ **24h rotation works** - mtime comparison handles overwritten files
✅ **Self-healing** - Orphaned transcripts marked automatically
✅ **Simple** - File system is the source of truth
✅ **Manifest accuracy** - Always reflects reality

## Files Changed

- `backend_host/scripts/transcript_accumulator.py`
  - Removed: State file loading/saving (lines 352-364, 418-440)
  - Added: `should_transcribe()` - mtime comparison
  - Added: `reconcile_orphaned_transcripts()` - mark unavailable
  - Updated: `process_mp3_chunks()` - simple logic

- `backend_host/scripts/hot_cold_archiver.py`
  - Updated: `update_manifest()` - added `has_mp3` parameter
  - Updated: `update_transcript_manifest()` - pass `has_mp3` flag

## Migration

No migration needed! The service will:
1. Find existing MP3s and transcripts
2. Compare mtimes and transcribe if needed
3. Mark orphaned transcripts automatically
4. Old `transcript_state.json` files are ignored (can be deleted manually)

## Testing

```bash
# Restart service
sudo systemctl restart transcript_accumulator

# Watch logs
sudo journalctl -u transcript_accumulator -f

# Check manifest
cat /var/www/html/stream/capture4/transcript/transcript_manifest.json | jq

# Verify no state file created
ls /var/www/html/stream/capture4/transcript_state.json  # Should not exist
```

## Result

**Simple, clean, correct.** 🎯

