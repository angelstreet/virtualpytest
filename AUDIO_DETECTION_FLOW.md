# Audio Detection Flow - Optimized System

## Overview
The audio detection system uses a **two-tier approach** with ffprobe (fast) and ffmpeg (precise) to balance speed and accuracy.

## Detection Schedule (5fps device example)

```
Time    Frame   Action                          Method              Time      Volume Data
────────────────────────────────────────────────────────────────────────────────────────
0s      0       Check audio                     ffmpeg volumedetect 200ms     -25.3 dB (measured)
0.2s    1       (skip - not audio frame)        in-memory cache     0ms       -25.3 dB (cached)
0.4s    2       (skip - not audio frame)        in-memory cache     0ms       -25.3 dB (cached)
...
5s      25      Check audio (5s interval)       ffprobe             12ms      -25.3 dB (from JSON < 30s)
5.2s    26      (skip - not audio frame)        in-memory cache     0ms       -25.3 dB (cached)
...
10s     50      Check audio (5s interval)       ffprobe             10ms      -25.3 dB (from JSON < 30s)
...
15s     75      Check audio (5s interval)       ffprobe             8ms       -25.3 dB (from JSON < 30s)
...
20s     100     Check audio (5s interval)       ffprobe             11ms      -25.3 dB (from JSON < 30s)
...
25s     125     Check audio (5s interval)       ffprobe             9ms       -25.3 dB (from JSON < 30s)
...
30s     150     Check audio (30s full check)    ffmpeg volumedetect 198ms     -26.1 dB (measured)
30.2s   151     (skip - not audio frame)        in-memory cache     0ms       -26.1 dB (cached)
...
35s     175     Check audio (5s interval)       ffprobe             10ms      -26.1 dB (from JSON < 30s)
...
```

## How It Works

### 1. Frame-Level Decision (Every Frame)
```python
# Most frames skip audio check entirely (use in-memory cache)
if frame_number % (fps * 5) != 0:  # Not an audio check frame
    return cached_result  # 0ms - instant
```

### 2. Audio Check Frames (Every 5 seconds)
When it's time to check audio, call `analyze_audio()`:

#### Step 2.1: In-Memory Cache Check
```python
if segment_file in cache and mtime matches:
    return cached_result  # 0ms - same segment
```

#### Step 2.2: JSON Cache Check (< 5 seconds)
```python
if json_cache_age < 5.0:
    return json_cached_result  # 0ms - within same 5s window
    # This shares data between frames in the same 5s interval
```

#### Step 2.3: Decide Between ffmpeg and ffprobe
```python
time_since_last_ffmpeg = now - last_ffmpeg_check

if time_since_last_ffmpeg >= 30.0:
    # FULL CHECK (every 30s)
    run ffmpeg volumedetect  # ~200ms
    measure precise volume   # -25.3 dB
    save to JSON cache
    
else:
    # FAST CHECK (every 5s between full checks)
    run ffprobe             # ~10ms
    verify audio stream exists
    
    # Get volume data from:
    # 1. In-memory cache (same segment), OR
    # 2. JSON cache (< 30s old), OR  
    # 3. Estimated defaults (50%, -20dB)
    
    save to JSON cache      # Updates timestamp, keeps data fresh
```

## JSON Cache Management

### Cache File: `.audio_volume_cache.json`
```json
{
  "timestamp": 1234567890.123,
  "has_audio": true,
  "volume_percentage": 47,
  "mean_volume_db": -25.3,
  "check_method": "ffmpeg_volumedetect",
  "check_time_ms": 198.45
}
```

### Cache Lifetime Strategy
- **< 5 seconds old**: Quick return (shares data within same check window)
- **5-30 seconds old**: Run ffprobe to verify stream, reuse volume data
- **> 30 seconds old**: Run ffmpeg to re-measure volume

### Why This Works
1. JSON cache updated every 5s by ffprobe (extends timestamp)
2. Volume data stays constant for 30s (from last ffmpeg measurement)
3. All metadata JSONs in a 30s window get same volume values
4. Stream presence verified every 5s (fast with ffprobe)

## Logs You'll See

### ffmpeg Full Check (every 30s)
```
⏱️  Performance: audio=198ms(ffmpeg_volumedetect)
```
**JSON Output:**
```json
{
  "audio": true,
  "volume_percentage": 47,
  "mean_volume_db": -25.3,
  "audio_check_method": "ffmpeg_volumedetect",
  "audio_check_time_ms": 198.45
}
```

### ffprobe Fast Check (every 5s)
```
⏱️  Performance: audio=10ms(ffprobe)
```
**JSON Output:**
```json
{
  "audio": true,
  "volume_percentage": 47,
  "mean_volume_db": -25.3,
  "audio_check_method": "ffprobe_with_cached_volume",
  "audio_check_time_ms": 10.23
}
```

### Cached Frame (between 5s intervals)
```
⏱️  Performance: audio=0ms(cache)
```
**JSON Output:**
```json
{
  "audio": true,
  "volume_percentage": 47,
  "mean_volume_db": -25.3,
  "audio_check_method": "ffprobe_with_cached_volume",
  "audio_check_time_ms": 10.23
}
```

## Check Methods

| Method | When Used | Time | Volume Source |
|--------|-----------|------|---------------|
| `ffmpeg_volumedetect` | Every 30s | ~200ms | Measured from audio decode |
| `ffprobe` | When no audio stream | ~10ms | N/A (no audio) |
| `ffprobe_with_cached_volume` | Every 5s (stream exists) | ~10ms | JSON cache (< 30s old) |
| `ffprobe_estimated` | First check, no history | ~10ms | Estimated (50%, -20dB) |
| `cached_json_cache` | Within 5s window | ~0ms | JSON cache (< 5s old) |
| `ffmpeg_fallback` | Error recovery | ~200ms | Measured from audio decode |

## Performance Benefits

### Before (original ffmpeg every check)
- Every 5s: ffmpeg ~200ms
- CPU: High (decoding audio every 5s)
- Accuracy: High (always measured)

### After (hybrid ffprobe/ffmpeg)
- Every 5s: ffprobe ~10ms (20x faster)
- Every 30s: ffmpeg ~200ms (precise measurement)
- CPU: Low (no decoding between 30s intervals)
- Accuracy: High (measured every 30s, verified every 5s)

### Savings
- **90% reduction** in audio check time (10ms vs 200ms)
- **83% reduction** in CPU usage (1 ffmpeg per 30s instead of 6)
- Same accuracy: volume measurements every 30s, stream verification every 5s

