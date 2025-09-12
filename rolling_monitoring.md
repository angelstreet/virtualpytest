# Rolling Buffer Monitoring System

## Overview

The autonomous monitoring system uses a **rolling buffer architecture** to achieve smooth 1 FPS display while performing AI analysis that takes ~3 seconds per frame.

## Architecture

### Core Concept
- **Buffer Depth**: 3 frames ahead of display
- **AI Processing Time**: ~3 seconds per frame
- **Display Rate**: 1 FPS (1000ms intervals)
- **Key Insight**: 3-frame buffer absorbs 3-second AI latency

## Implementation Flow

### Phase 1: Initial Buffer (9 seconds)
```
Time 0-9s: Load Frame 1,2,3 + AI analysis in parallel
├── Frame 1: Subtitle + Language Menu + Description analysis
├── Frame 2: Subtitle + Language Menu + Description analysis  
└── Frame 3: Subtitle + Language Menu + Description analysis
Result: 3 frames ready for display after ~9 seconds
```

### Phase 2: Rolling Display (1 FPS sustained)
```
Time 9s:  Display Frame 1 → Start Frame 4 AI (completes at 12s)
Time 10s: Display Frame 2 → Start Frame 5 AI (completes at 13s)  
Time 11s: Display Frame 3 → Start Frame 6 AI (completes at 14s)
Time 12s: Display Frame 4 → Start Frame 7 AI (completes at 15s)
...continues indefinitely...
```

## Technical Details

### AI Analysis Components
Each frame undergoes 3 parallel AI analyses:
1. **Subtitle Detection** (`/detectSubtitlesAI`) - ~1.6-2.2s
2. **Language Menu Analysis** (`/analyzeLanguageMenu`) - ~1.6-2.1s  
3. **Image Description** (`/analyzeImageAI`) - ~1.3-2.8s

**Total Time**: ~2-3 seconds (parallel execution)

### Buffer Management
- **Display Queue**: Holds completed frames ready for display
- **Processing**: Each display triggers next frame AI analysis
- **Rolling**: Always maintains 3 frames ahead of current display

### Performance Metrics
- **First Display**: 9 seconds (initial buffer fill)
- **Sustained Rate**: 1 FPS (1000ms intervals)
- **Buffer Efficiency**: 100% (never starves due to 3-frame lead)

## Code Structure

### Key Components
- `useMonitoring.ts` - Main hook with rolling buffer logic
- `analyzeFrame()` - Parallel AI analysis function with timing
- `initializeBuffer()` - Initial 3-frame parallel loading
- `displayInterval` - 1000ms display loop with next frame trigger

### Timing Measurements
```javascript
console.log(`✅ Frame analysis completed in ${totalTime}ms (JSON: ${jsonTime}ms, AI: ${aiTime}ms)`)
console.log(`📊 Display queue length: ${prev.length}`)
console.log(`🎬 Displaying frame: ${nextFrame.imageUrl}`)
```

## Benefits

1. **Smooth Playback**: True 1 FPS without stuttering
2. **Autonomous**: No manual button presses required
3. **Efficient**: Parallel processing maximizes throughput
4. **Scalable**: Buffer depth can be adjusted for different AI latencies
5. **Robust**: Handles AI failures gracefully (continues with available data)

## Frame Data Structure

Each frame contains:
```typescript
interface FrameRef {
  timestamp: string;           // ISO 8601 from MCM metadata
  imageUrl: string;           // Capture image URL
  jsonUrl: string;            // MCM analysis JSON URL
  subtitleAnalysis?: SubtitleAnalysis | null;
  languageMenuAnalysis?: LanguageMenuAnalysis | null;
  aiDescription?: string | null;
}
```

## Display Components

### MonitoringPlayer
- Displays current frame image
- Shows AI description overlay (top-centered, 2 lines max)
- Removed manual detection buttons (fully autonomous)

### MonitoringOverlay  
- Shows subtitle analysis results
- Shows language menu detection results
- Displays timestamp from MCM metadata (HH:MM:SS format)

## Performance Optimization

The rolling buffer ensures:
- **No blocking**: Display never waits for AI completion
- **Continuous processing**: Always 3 frames being analyzed
- **Memory efficient**: Maintains only necessary frames in memory
- **Predictable timing**: Consistent 1 FPS regardless of AI variance

## Monitoring Logs

Key log patterns to watch:
```
🚀 Initializing 3-frame buffer...
📦 Processing frame 1: capture_48919.jpg
✅ Frame analysis completed in 2847ms (JSON: 45ms, AI: 2802ms)
✅ Buffer initialized with 3 frames in 9000ms
🎬 Displaying frame: capture_48919.jpg
➕ Added frame to queue: capture_48941.jpg
```

This architecture provides smooth, autonomous monitoring with AI-enhanced analysis at true 1 FPS performance.
