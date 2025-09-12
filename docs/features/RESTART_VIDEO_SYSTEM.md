# Restart Video System Documentation

## Overview

The Restart Video System provides fast 10-second video generation with AI-powered analysis and overlay capabilities. Users can generate restart videos instantly and access advanced features through a unified settings panel.

## Architecture

### Backend Components

#### Video Generation (`backend_core/src/controllers/base_controller.py`)
- **Fast Generation**: 10-second MP4 videos generated in 2-3 seconds
- **Background Analysis**: 3 parallel AI analyses run after video generation
- **HLS Source**: Uses existing HLS segments for video creation
- **R2 Storage**: Analysis results stored for future reporting

#### Analysis Pipeline
1. **Audio Analysis**: Extracts audio from HLS segments, transcribes with Whisper
2. **Subtitle Detection**: Analyzes middle frame (frame 5/10) for subtitle presence  
3. **Video Description**: Extracts 10 frames (1 per second), generates AI descriptions

### Frontend Components

#### Core Hook (`frontend/src/hooks/pages/useRestart.ts`)
- **Fast Video Display**: Returns video URL immediately
- **Progressive Loading**: Tracks analysis progress (audio, subtitles, description)
- **Background Requests**: 3 parallel analysis API calls
- **State Management**: Manages video, analysis results, and progress states

#### Main Player (`frontend/src/components/rec/RestartPlayer.tsx`)
- **Video Display**: Standard HTML5 video player
- **Progress Bar**: Animated progress indicator during analysis
- **Settings Button**: Appears when analysis completes
- **Overlay Management**: Controls summary and subtitle overlays

#### Settings Panel (`frontend/src/components/rec/RestartSettingsPanel.tsx`)
- **Right Slide Panel**: 350px width, slides from right
- **Video Summary Section**: Toggle per-second overlay + final summary display
- **Subtitles Section**: Toggle subtitle overlay with language selection
- **Audio Transcript**: Full transcript text display

#### Overlay Components

**RestartSummaryOverlay** (`frontend/src/components/rec/RestartSummaryOverlay.tsx`)
- **Position**: Top center of video
- **Content**: Per-second frame descriptions
- **Sync**: Updates based on video currentTime
- **Styling**: Semi-transparent black background

**RestartSubtitleOverlay** (`frontend/src/components/rec/RestartSubtitleOverlay.tsx`)
- **Position**: Bottom center of video (covers original subtitles)
- **Content**: Detected subtitles with translation support
- **Styling**: Strong black background to hide original subtitles

## User Experience Flow

### 1. Video Generation
```
User clicks "Restart" → Video appears in 2-3 seconds → Progress bar shows analysis
```

### 2. Analysis Progress
```
Progress bar: [████░░░░░░] 33% → [████████░░] 66% → [██████████] 100%
```

### 3. Settings Access
```
Analysis complete → Settings button (⚙️) appears → Click → Panel slides from right
```

### 4. Overlay Controls
```
Settings Panel:
├── Video Summary
│   ├── ☐ Show Per-Second Summary (top overlay)
│   ├── Language: [English ▼]
│   └── [Final summary text display]
├── Subtitles  
│   ├── ☐ Show Subtitle Overlay (bottom overlay)
│   └── Language: [Spanish ▼]
└── Audio Transcript
    └── [Full transcript text]
```

## API Endpoints

### Video Generation
```
POST /server/av/generateRestartVideo
Body: {
  host: Host,
  device_id: string,
  duration_seconds: 10,
  include_audio_analysis: false
}
Response: {
  success: true,
  video_url: string,
  processing_time_seconds: number
}
```

### Background Analysis (3 parallel calls)
```
POST /server/verification/audio/analyzeAudio
POST /server/verification/video/detectSubtitlesAI  
POST /server/verification/video/analyzeVideoDescription
```

## Data Structures

### Analysis Results
```typescript
interface AnalysisResults {
  audioAnalysis: {
    transcript: string;
    detected_language: string;
    successful_segments: number;
  };
  subtitleAnalysis: {
    subtitles_detected: boolean;
    extracted_text: string;
    confidence: number;
  };
  videoDescription: {
    frame_descriptions: string[];  // Per-second descriptions
    video_summary: string;         // Final 10-line summary
    frames_analyzed: number;
  };
}
```

### Progress Tracking
```typescript
interface AnalysisProgress {
  audio: 'pending' | 'loading' | 'completed' | 'error';
  subtitles: 'pending' | 'loading' | 'completed' | 'error';
  description: 'pending' | 'loading' | 'completed' | 'error';
}
```

## Configuration

### Video Settings
- **Duration**: Fixed 10 seconds
- **Format**: MP4 (H.264)
- **Source**: HLS segments from live stream
- **Quality**: Inherits from HLS stream quality

### Analysis Settings
- **Audio Segments**: 3 segments (~6 seconds total)
- **Frame Analysis**: 10 frames (1 per second)
- **Subtitle Frame**: Middle frame (frame 5/10)
- **AI Model**: Whisper (tiny) for audio, OpenRouter vision models for frames

### UI Settings
- **Progress Bar**: 100px width, 6px height, top-right
- **Settings Panel**: 350px width, full height, right slide
- **Overlays**: Top (summary) and bottom (subtitles) positioning

## Performance Characteristics

### Timing Benchmarks
- **Video Generation**: 2-3 seconds (MP4 creation only)
- **Audio Analysis**: 3-5 seconds (parallel)
- **Subtitle Detection**: 2-3 seconds (parallel)
- **Video Description**: 8-12 seconds (parallel)
- **Total Time**: Video shows immediately, analysis completes in 8-12 seconds

### Resource Usage
- **Storage**: Videos stored in R2, analysis results cached
- **Memory**: Temporary frame extraction (~50MB during analysis)
- **Network**: 3 parallel API calls during background analysis

## Integration Points

### Host Stream Modal
```typescript
<RestartPlayer 
  host={host} 
  device={device} 
  includeAudioAnalysis={true} 
/>
```

### Monitoring System
- Reuses AI analysis infrastructure from `useMonitoring`
- Same vision AI models and processing pipeline
- Consistent analysis result formats

### Translation System
- Integrates with existing translation utilities
- Supports multiple target languages
- Maintains translation state per overlay type

## Future Enhancements

### Report Generation
- Analysis data stored in R2 bucket `restart-reports/`
- JSON format ready for report generation system
- Timeline navigation similar to heatmap reports

### Advanced Features
- Custom video durations (5s, 15s, 30s)
- Subtitle styling options (font, color, position)
- Export capabilities (video + analysis)
- Batch restart video generation

## Troubleshooting

### Common Issues
1. **Video not appearing**: Check HLS segment availability
2. **Analysis not starting**: Verify `includeAudioAnalysis=true`
3. **Overlays not syncing**: Check video `currentTime` event listeners
4. **Settings panel not opening**: Ensure analysis is complete

### Debug Information
- Console logs prefixed with `[@hook:useRestart]` and `[@component:RestartPlayer]`
- Analysis progress tracked in browser developer tools
- Network tab shows parallel analysis requests

## Migration Notes

### Removed Components
- `SubtitleOverlay.tsx` → Replaced by `RestartSubtitleOverlay.tsx`
- `SubtitleSettings.tsx` → Replaced by `RestartSettingsPanel.tsx`
- `VideoDescriptionPanel.tsx` → Replaced by `RestartSettingsPanel.tsx`

### Breaking Changes
- Settings interface completely redesigned
- Overlay positioning and styling updated
- Analysis data structure modified for per-second summaries
