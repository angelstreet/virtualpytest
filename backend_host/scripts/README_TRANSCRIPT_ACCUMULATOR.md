# Transcript Accumulator - Processing Model

## 📊 Sequential Processing (Same as capture_monitor.py)

Both `transcript_accumulator.py` and `capture_monitor.py` use **SEQUENTIAL** processing:

```python
while True:
    for capture_dir in capture_dirs:  # Sequential loop
        capture_folder = get_capture_folder(capture_dir)
        process_capture(capture_dir)  # Process one device at a time
    time.sleep(60)  # Check every 60s
```

### Why Sequential?

1. **CPU Resource Management** - Whisper is CPU-intensive, running multiple in parallel would overload RPi
2. **Memory Efficiency** - Each Whisper instance loads ~150MB model, sequential = single model load
3. **I/O Throttling** - FFmpeg operations are already I/O bound, parallelism wouldn't help
4. **Consistency** - Same pattern as `capture_monitor.py` for easier debugging

## 🔄 Processing Order Example

```
[18:10:37] Starting Transcript Accumulator...
[18:10:37] Monitoring 3 capture directories:
[18:10:37]   → Monitoring: /var/www/html/stream/capture1/captures -> capture1
[18:10:37]   → Monitoring: /var/www/html/stream/capture2/captures -> capture2
[18:10:37]   → Monitoring: /var/www/html/stream/capture3/captures -> capture3

[18:10:38] [capture1] Checking for new transcript samples...
[18:10:38] [capture1] Processing 6489 new samples (10 segments per sample)...
[18:10:38] [capture1] [AudioTranscriptionUtils] Merging 10 TS segments...
[18:10:38] [capture1] [AudioTranscriptionUtils] ✓ Merged 10 TS files (874012 bytes)
[18:10:38] [capture1] [AudioTranscriptionUtils] Loading Whisper model 'tiny'...
[18:10:44] [capture1] 📝 seg#10 (10 merged) - English: 'Hello world'
[18:10:47] [capture1] 📝 seg#20 (10 merged) - English: 'Test message'
...
[18:11:00] [capture1] ✓ Transcript buffer updated: 6489 samples

[18:11:00] [capture2] Checking for new transcript samples...
[18:11:00] [capture2] Processing 4523 new samples (10 segments per sample)...
[18:11:00] [capture2] [AudioTranscriptionUtils] Merging 10 TS segments...
...

[18:12:00] [capture3] Checking for new transcript samples...
...
```

## ⏱️ Timing Comparison

### **capture_monitor.py**
- **Cycle time**: ~1-3 seconds per device
- **Analysis**: Simple image detection (freeze, blackscreen, audio)
- **CPU usage**: Low (image comparison)
- **Total loop**: ~3-9 seconds for 3 devices

### **transcript_accumulator.py**
- **Cycle time**: ~5-20 seconds per device (depending on speech)
- **Analysis**: Audio merging + Whisper transcription
- **CPU usage**: Medium-High (Whisper inference)
- **Total loop**: ~15-60 seconds for 3 devices
- **Optimization**: Audio level pre-check skips Whisper on silence

## 🎯 Device Identification in Logs

Every log now shows which device is being processed:

```
[capture1] [AudioTranscriptionUtils] Merging 10 TS segments...
[capture1] [AudioTranscriptionUtils] ✓ Merged 10 TS files (874012 bytes)
[capture1] [AudioTranscriptionUtils] Audio level: -25.4dB (sound)
[capture1] [AudioTranscriptionUtils] Audio: 10.0s, Segments: 1, Transcript length: 11 chars
[capture1] 📝 seg#10 (10 merged) - English: 'Hello world'
```

## 💡 Parallel Processing - Not Recommended

While technically possible with `multiprocessing`, it's **NOT recommended** for Raspberry Pi:

### ❌ Why Not Parallel?
```python
# This would OVERLOAD the Raspberry Pi:
with ProcessPoolExecutor(max_workers=3) as executor:
    futures = [executor.submit(process_device, d) for d in capture_dirs]
```

**Problems**:
- 3x Whisper models loaded = ~450MB RAM (RPi only has 1-4GB)
- 3x CPU usage = thermal throttling on RPi
- 3x FFmpeg processes = I/O bottleneck
- Diminishing returns (processing not parallel anyway)

### ✅ Current Sequential = Optimal
- Single Whisper model = ~150MB RAM
- Controlled CPU usage
- Predictable performance
- Same proven pattern as `capture_monitor.py`

## 📈 Performance Characteristics

| **Scenario** | **Time per Device** | **CPU Usage** | **RAM Usage** |
|--------------|-------------------|---------------|---------------|
| **Silent segments** | ~0.5s (skipped) | 5% | ~150MB |
| **Speech segments** | ~2-3s (Whisper) | 60-80% | ~150MB |
| **3 devices sequential** | ~1.5-9s total | Peaks at 80% | ~150MB |
| **3 devices parallel (❌)** | ~2-3s total | >200% (throttles) | ~450MB |

## 🚀 Conclusion

**Sequential processing is the right choice** for Raspberry Pi:
- ✅ Controlled resource usage
- ✅ Predictable performance
- ✅ Same pattern as capture_monitor
- ✅ Clear device identification in logs
- ✅ Optimal for 24/7 operation

The 60-second check interval is sufficient for 24-hour transcript accumulation!

