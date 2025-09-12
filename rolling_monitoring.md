# Two-Process Monitoring System

## Overview

The autonomous monitoring system uses a **dual-process architecture** to achieve consistent 1 FPS display while performing AI analysis that takes ~4 seconds per frame.

## Architecture

### Core Concept
- **Process Separation**: Queue feeding and display consumption are completely independent
- **AI Processing Time**: ~4-5 seconds per frame
- **Display Rate**: Consistent 1 FPS (1000ms intervals)
- **Key Insight**: Fast frame detection feeds queue, slow AI analysis runs in background

## Two-Process Implementation

### Process 1: Queue Feeder (Background)
```
Continuous Loop (200ms polling):
├── Detect new frame → Queue immediately
├── Start AI analysis in background (non-blocking)
└── Repeat without waiting for AI completion

Result: Queue always fed by fast frame detection (~200ms)
```

### Process 2: Display Consumer (1 FPS Timer)
```
1000ms Timer:
├── Take next frame from queue
├── Display frame immediately
└── Never wait for AI completion

Result: Consistent 1 FPS regardless of AI processing time
```

## Technical Details

### Process 3: Background AI Analysis (Asynchronous)
Each frame undergoes 3 parallel AI analyses:
1. **Subtitle Detection** (`/detectSubtitlesAI`) - ~1.6-2.2s
2. **Language Menu Analysis** (`/analyzeLanguageMenu`) - ~1.6-2.1s  
3. **Image Description** (`/analyzeImageAI`) - ~1.3-2.8s

**Total Time**: ~4-5 seconds (parallel execution + JSON loading)

### Queue Management
- **Display Queue**: Holds frames ready for display (max 10 frames)
- **Frame Detection**: 200ms polling rate (5 FPS detection)
- **Display Rate**: 1000ms intervals (1 FPS consumption)
- **AI Updates**: Results applied asynchronously when ready

### Performance Metrics
- **First Display**: 1 second (initial loading buffer)
- **Sustained Rate**: 1 FPS (guaranteed by queue separation)
- **Queue Efficiency**: Never empty (5 FPS feeding vs 1 FPS consumption)

## Code Structure

### Key Components
- `useMonitoring.ts` - Main hook with dual-process architecture
- `analyzeFrameAsync()` - Background AI analysis (non-blocking)
- `queueFeederLoop()` - Continuous frame detection and queuing
- `displayInterval` - 1000ms display consumer

### Process Flow
```javascript
// Process 1: Queue Feeder
queueFeederLoop() → fetchLatestMonitoringData() → queue immediately → analyzeFrameAsync()

// Process 2: Display Consumer  
displayInterval → consume from queue → display frame

// Process 3: AI Analysis
analyzeFrameAsync() → update frames when ready
```

## Benefits

1. **Consistent Performance**: True 1 FPS guaranteed by process separation
2. **Autonomous**: No manual intervention required
3. **Non-blocking**: AI analysis never blocks display pipeline
4. **Scalable**: Queue absorbs any AI processing variance
5. **Elegant**: Simple, clean architecture without fallbacks

## Frame Data Structure

Each frame contains:
```typescript
interface QueuedFrame {
  timestamp: string;           // ISO 8601 from MCM metadata
  imageUrl: string;           // Capture image URL
  jsonUrl: string;            // MCM analysis JSON URL
  sequence: string;           // Frame sequence number
  // AI analysis added asynchronously:
  analysis?: MonitoringAnalysis | null;
  subtitleAnalysis?: SubtitleAnalysis | null;
  languageMenuAnalysis?: LanguageMenuAnalysis | null;
  aiDescription?: string | null;
}
```

## Display Components

### MonitoringPlayer
- Displays current frame image
- Shows AI description overlay (when available)
- Fully autonomous operation

### MonitoringOverlay  
- Shows subtitle analysis results (when available)
- Shows language menu detection results (when available)
- Displays timestamp from MCM metadata

## Performance Optimization

The dual-process architecture ensures:
- **No blocking**: Display never waits for AI completion
- **Continuous feeding**: Queue always populated by fast detection
- **Memory efficient**: Max 10 frames in queue, 100 in history
- **Predictable timing**: Consistent 1 FPS regardless of AI variance

## Monitoring Logs

Key log patterns to watch:
```
🔄 Starting queue feeder process...
📦 New frame 1: capture_48919.jpg
🎬 Displaying frame: capture_48919.jpg
✅ Background AI analysis completed in 4718ms (JSON: 12ms, AI: 4706ms)
```

This architecture provides smooth, autonomous monitoring with AI-enhanced analysis at guaranteed 1 FPS performance.
