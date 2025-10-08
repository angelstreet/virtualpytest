# Audio Detection Flow - Ultra-Fast System

## Overview
The audio detection system uses a **two-tier approach** with ffprobe (ultra-fast ~1ms) and ffmpeg (precise ~200ms) to balance speed and accuracy.

**Key Strategy:**
- **ffprobe every 1 second** (~1ms) - checks if audio stream exists (no cache)
- **ffmpeg every 30 seconds** (~200ms) - measures precise volume (cached for 30s)

## Detection Schedule (5fps device example)

```
Time    Frame   Action                          Method              Time      Volume Data
────────────────────────────────────────────────────────────────────────────────────────
0s      0       Check audio                     ffmpeg volumedetect 200ms     -25.3 dB (measured)
0.2s    1       (skip - not audio frame)        frame cache         0ms       -25.3 dB (cached)
0.4s    2       (skip - not audio frame)        frame cache         0ms       -25.3 dB (cached)
0.6s    3       (skip - not audio frame)        frame cache         0ms       -25.3 dB (cached)
0.8s    4       (skip - not audio frame)        frame cache         0ms       -25.3 dB (cached)
1s      5       Check audio (1s interval)       ffprobe             1ms       -25.3 dB (from JSON < 30s)
1.2s    6       (skip - not audio frame)        frame cache         0ms       -25.3 dB (cached)
...
2s      10      Check audio (1s interval)       ffprobe             1ms       -25.3 dB (from JSON < 30s)
...
3s      15      Check audio (1s interval)       ffprobe             1ms       -25.3 dB (from JSON < 30s)
...
5s      25      Check audio (1s interval)       ffprobe             1ms       -25.3 dB (from JSON < 30s)
...
10s     50      Check audio (1s interval)       ffprobe             1ms       -25.3 dB (from JSON < 30s)
...
30s     150     Check audio (30s full check)    ffmpeg volumedetect 198ms     -26.1 dB (measured)
30.2s   151     (skip - not audio frame)        frame cache         0ms       -26.1 dB (cached)
...
31s     155     Check audio (1s interval)       ffprobe             1ms       -26.1 dB (from JSON < 30s)
...
```

## How It Works

### 1. Frame-Level Decision (Every Frame)
```python
# Most frames skip audio check entirely (use frame-level cache)
if frame_number % fps != 0:  # Not an audio check frame (1s interval)
    return cached_result  # 0ms - instant from _audio_result_cache
```

### 2. Audio Check Frames (Every 1 second)
When it's time to check audio, call `analyze_audio()`:

#### Step 2.1: Decide Between ffmpeg and ffprobe
```python
time_since_last_ffmpeg = now - last_ffmpeg_check

if time_since_last_ffmpeg >= 30.0:
    # FULL CHECK (every 30s)
    run ffmpeg volumedetect  # ~200ms
    measure precise volume   # -25.3 dB
    save to JSON cache       # Cache for 30s
    return results
    
else:
    # FAST CHECK (every 1s)
    run ffprobe             # ~1ms
    verify audio stream exists
    
    # Get volume data from JSON cache (< 30s old)
    if json_cache_age < 30.0:
        use cached volume   # From last ffmpeg check
    else:
        use defaults        # 50%, -20dB until next ffmpeg
    
    return results
```

**No caching of audio detection** - ffprobe is so fast (~1ms) that caching provides no benefit.
**Only volume data is cached** - expensive ffmpeg measurements are reused for 30s.

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
- **< 30 seconds old**: Use cached volume data (from last ffmpeg check)
- **> 30 seconds old**: Run ffmpeg to re-measure volume

### Why This Works
1. ffprobe runs every 1s (~1ms) - so fast that caching is unnecessary
2. Volume data cached for 30s (from ffmpeg measurement)
3. All metadata JSONs in a 30s window get same volume values
4. Stream presence verified every 1s (ultra-fast with ffprobe)

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

### ffprobe Fast Check (every 1s)
```
⏱️  Performance: audio=1ms(ffprobe)
```
**JSON Output:**
```json
{
  "audio": true,
  "volume_percentage": 47,
  "mean_volume_db": -25.3,
  "audio_check_method": "ffprobe_with_cached_volume",
  "audio_check_time_ms": 1.23
}
```

### Cached Frame (between 1s intervals)
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
  "audio_check_time_ms": 1.23
}
```

## Check Methods

| Method | When Used | Time | Volume Source |
|--------|-----------|------|---------------|
| `ffmpeg_volumedetect` | Every 30s | ~200ms | Measured from audio decode |
| `ffprobe` | When no audio stream | ~1ms | N/A (no audio) |
| `ffprobe_with_cached_volume` | Every 1s (stream exists) | ~1ms | JSON cache (< 30s old) |
| `ffprobe_estimated` | First check, no history | ~1ms | Estimated (50%, -20dB) |
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

