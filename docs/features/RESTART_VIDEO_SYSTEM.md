# Restart Video System Documentation

## Overview

The Restart Video System provides fast 10-second video generation with AI-powered analysis and overlay capabilities. The system **reuses existing infrastructure** including continuous screenshot capture, audio processing, and image-based AI analysis routes - **no new routes or legacy code**.

## Architecture

### Backend Components

#### Video Generation (`backend_core/src/controllers/base_controller.py`)
- **Fast Generation**: 10-second MP4 videos generated in 2-3 seconds
- **Local Audio Processing**: Uses existing `AudioAIHelpers` directly (same as ZapController)
- **Screenshot Collection**: Leverages existing continuous capture system
- **R2 Storage**: Analysis data stored for frontend polling

#### Analysis Pipeline (Using Existing Infrastructure)
1. **Audio Analysis**: Local processing via `AudioAIHelpers.get_recent_audio_segments()` + `analyze_audio_segments_ai()`
2. **Screenshot Collection**: Uses existing `/captures/capture_*.jpg` files from continuous capture
3. **Frontend Analysis**: Uses existing image-based routes for subtitle/description analysis

### Frontend Components

#### Core Hook (`frontend/src/hooks/pages/useRestart.ts`)
- **Fast Video Display**: Returns video URL immediately
- **R2 Data Polling**: Loads audio analysis from backend-stored R2 data
- **Existing Route Usage**: Uses `/server/verification/video/detectSubtitlesAI` and `/server/verification/video/analyzeImageAI` with screenshot URLs
- **Progressive Analysis**: Audio from backend, visuals from frontend using existing routes

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

## API Endpoints (Existing Routes Only)

### Video Generation
```
POST /server/av/generateRestartVideo
Body: {
  host: Host,
  device_id: string,
  duration_seconds: 10,
  include_audio_analysis: true  // Enables backend audio processing
}
Response: {
  success: true,
  video_url: string,
  processing_time_seconds: number
}
```

### Frontend Analysis (Using Existing Image-Based Routes)
```
POST /server/verification/video/detectSubtitlesAI
Body: {
  host: Host,
  device_id: string,
  image_source_url: string,  // Screenshot URL from continuous capture
  extract_text: true
}

POST /server/verification/video/analyzeImageAI  
Body: {
  host: Host,
  device_id: string,
  image_source_url: string,  // Screenshot URL from continuous capture
  prompt: "Describe what you see in this frame in 1-2 sentences"
}
```

### R2 Data Access
```
GET https://dev.virtualpytest.com/r2/restart_analysis/{device_id}/{video_filename}.json
Response: {
  audio_analysis: { combined_transcript, detected_language, ... },
  screenshot_urls: ["/host/stream/capture1/captures/capture_0001.jpg", ...],
  analysis_complete: true
}
```

## Data Structures

### Analysis Results (Updated Structure)
```typescript
interface AnalysisResults {
  audio: {
    success: boolean;
    combined_transcript: string;
    detected_language: string;
    speech_detected: boolean;
    confidence: number;
    execution_time_ms: number;
  } | null;
  subtitles: {
    success: boolean;
    subtitles_detected: boolean;
    extracted_text: string;
    detected_language?: string;
    execution_time_ms: number;
  } | null;
  videoDescription: {
    frame_descriptions: string[];  // Per-second descriptions
    video_summary: string;         // Generated summary
    frames_analyzed: number;
    execution_time_ms: number;
  } | null;
}
```

### Progress Tracking
```typescript
interface AnalysisProgress {
  audio: 'idle' | 'loading' | 'completed' | 'error';
  subtitles: 'idle' | 'loading' | 'completed' | 'error';
  videoDescription: 'idle' | 'loading' | 'completed' | 'error';
}
```

## Configuration

### Video Settings
- **Duration**: Fixed 10 seconds
- **Format**: MP4 (H.264)
- **Source**: HLS segments from live stream
- **Quality**: Inherits from HLS stream quality

### Analysis Settings
- **Audio Processing**: Local `AudioAIHelpers` with 3 recent segments
- **Screenshot Analysis**: Uses existing continuous capture screenshots (every 2nd screenshot, up to 10)
- **Subtitle Detection**: Middle screenshot from available screenshots
- **AI Models**: Existing Whisper for audio, OpenRouter vision models for images

### UI Settings
- **Progress Bar**: 100px width, 6px height, top-right
- **Settings Panel**: 350px width, full height, right slide
- **Overlays**: Top (summary) and bottom (subtitles) positioning

## Performance Characteristics

### Timing Benchmarks
- **Video Generation**: 2-3 seconds (MP4 creation only)
- **Audio Analysis**: 1-2 seconds (local processing, no HTTP)
- **R2 Data Polling**: 1-2 seconds (backend stores data)
- **Subtitle Detection**: 2-3 seconds (existing route with screenshot)
- **Video Description**: 5-8 seconds (existing route with multiple screenshots)
- **Total Time**: Video shows immediately, analysis completes in 5-8 seconds

### Resource Usage
- **Storage**: Videos stored in R2, analysis data stored in R2
- **Memory**: No temporary files - uses existing screenshots
- **Network**: R2 polling + existing image-based analysis routes
- **CPU**: Local audio processing (backend), image analysis (existing routes)

## Integration Points

### Host Stream Modal
```typescript
<RestartPlayer 
  host={host} 
  device={device} 
  includeAudioAnalysis={true} 
/>
```

### Existing Infrastructure Reuse
- **Screenshot System**: Uses existing continuous capture (`/captures/capture_*.jpg`)
- **Audio Processing**: Uses existing `AudioAIHelpers` (same as ZapController)
- **AI Routes**: Uses existing `/server/verification/video/detectSubtitlesAI` and `/server/verification/video/analyzeImageAI`
- **R2 Storage**: Uses existing R2 infrastructure for data storage

### Translation System
- Integrates with existing translation utilities
- Supports multiple target languages
- Maintains translation state per overlay type

## Implementation Approach

### Key Design Principles
1. **No New Routes**: Uses only existing `/server/av/generateRestartVideo`, `/server/verification/video/detectSubtitlesAI`, and `/server/verification/video/analyzeImageAI`
2. **No Legacy Code**: Clean implementation without backward compatibility or fallback mechanisms
3. **Reuse Existing Infrastructure**: Leverages continuous screenshot capture, AudioAIHelpers, and R2 storage
4. **Local Processing**: Audio analysis happens locally in backend (no HTTP overhead)
5. **Progressive Loading**: Video shows immediately, analysis loads progressively

### Data Flow
```
1. Frontend → /server/av/generateRestartVideo (include_audio_analysis: true)
2. Backend → take_video() generates MP4 + starts background analysis
3. Backend → AudioAIHelpers processes audio locally → stores in R2
4. Backend → Collects screenshot URLs → stores in R2
5. Frontend → Polls R2 for analysis data
6. Frontend → Uses screenshot URLs with existing image routes for visual analysis
```

### Why This Approach Works
- **Fast**: Video available in 2-3 seconds, no waiting for analysis
- **Efficient**: No temporary files, no new routes, minimal network overhead
- **Reliable**: Uses proven existing systems (AudioAIHelpers, continuous capture, image analysis)
- **Maintainable**: Single source of truth, no duplicate code paths

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
1. **Video not appearing**: Check HLS segment availability and `/server/av/generateRestartVideo` response
2. **Audio analysis not loading**: Check R2 data polling and `restart_analysis/{device_id}/{video}.json` file
3. **Screenshot analysis failing**: Verify continuous capture is running and screenshots exist in `/captures/`
4. **Overlays not showing**: Check that analysis completed and data structure matches expected format

### Debug Information
- Console logs prefixed with `[@hook:useRestart]` and `[@component:RestartPlayer]`
- R2 polling logs show data loading progress
- Network tab shows R2 requests and existing image analysis routes
- Backend logs show `[RestartVideo]` prefixed messages for audio processing

## Migration Notes

### Removed Components
- `SubtitleOverlay.tsx` → Replaced by `RestartSubtitleOverlay.tsx`
- `SubtitleSettings.tsx` → Replaced by `RestartSettingsPanel.tsx`
- `VideoDescriptionPanel.tsx` → Replaced by `RestartSettingsPanel.tsx`

### Implementation Changes
- **Data Structure**: Updated to use `analysisResults` object with proper TypeScript interfaces
- **Route Usage**: Uses existing image-based routes instead of creating new video-based routes
- **Audio Processing**: Moved from HTTP routes to local `AudioAIHelpers` processing
- **Screenshot Integration**: Leverages existing continuous capture instead of extracting frames
- **No Legacy Code**: Clean implementation without backward compatibility layers
