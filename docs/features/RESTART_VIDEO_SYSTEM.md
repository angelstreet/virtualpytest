# Restart Video System Documentation

## Overview

The Restart Video System provides fast 10-second video generation with comprehensive AI-powered analysis including audio transcription, subtitle detection, and frame-by-frame video descriptions. The system uses a **two-phase approach**: fast video generation followed by asynchronous AI analysis to ensure immediate video playback while maintaining comprehensive analysis capabilities.

## Architecture

### Backend Components

#### Two-Phase Architecture

**Phase 1: Fast Video Generation** (`generateRestartVideoFast`)
- **Immediate MP4 Creation**: 10-second videos generated in 2-3 seconds
- **Timeline Synchronization**: Uses `HLS_SEGMENT_DURATION` global variable for consistent segment timing
- **Optimized Screenshot Collection**: 1 FPS analysis (12 screenshots for 10s video) vs previous 3 FPS (45 screenshots)
- **Audio Analysis**: Local processing via merged audio segments for better Whisper accuracy
- **Fast Response**: Returns video URL + basic analysis immediately

**Phase 2: Asynchronous AI Analysis** (`analyzeRestartVideoAsync`)
- **Subtitle Detection**: AI-powered text extraction from synchronized screenshots
- **Video Descriptions**: Frame-by-frame analysis with overall video summary
- **Complete Analysis**: Comprehensive AI processing without blocking video playback

#### Core Implementation (`backend_core/src/controllers/base_controller.py`)
- **Global Configuration**: Uses `AVControllerInterface.HLS_SEGMENT_DURATION = 1` consistently
- **Segment Synchronization**: Video segments and screenshots use same timeline
- **Audio Segment Merging**: Combines 10-12 second audio for improved Whisper detection
- **Dynamic Screenshot Count**: `max(5, int(duration_seconds * 1 FPS * 1.2 buffer))`

### Frontend Components

#### Core Hook (`frontend/src/hooks/pages/useRestart.ts`)
- **Two-Phase Orchestration**: Calls fast generation then async analysis
- **Immediate Video Display**: Shows video player as soon as MP4 is ready
- **Backend Analysis Integration**: Receives complete AI analysis from backend
- **No Direct R2 Access**: Frontend no longer polls R2 directly, uses backend APIs
- **State Management**: Tracks video generation, analysis progress, and completion

#### Main Player (`frontend/src/components/rec/RestartPlayer.tsx`)
- **Video Display**: Standard HTML5 video player
- **Progress Bar**: Animated progress indicator during analysis
- **Settings Button**: Appears when analysis completes
- **Overlay Management**: Controls summary and subtitle overlays

#### Enhanced Settings Panel (`frontend/src/components/rec/RestartSettingsPanel.tsx`)
- **Compact Design**: Reduced font sizes, tighter margins, bordered sections
- **Expandable Content**: All analysis results collapse/expand by default
- **Integrated Checkboxes**: Checkboxes next to section titles (Video Summary, Subtitles, Audio Transcript)
- **Language & Confidence Display**: Shows detected language and confidence (e.g., "English, 95% confidence")
- **Dynamic Translation**: Real-time translation when target language differs from detected language
- **Frame-by-Frame Analysis**: Individual frame descriptions plus conclusion summary
- **Subtitle Text Display**: Shows original detected text with translation support

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

## API Endpoints (Two-Phase Architecture)

### Phase 1: Fast Video Generation
```
POST /server/av/generateRestartVideo
Body: {
  host: Host,
  device_id: string,
  duration_seconds: 10
}
Response: {
  success: true,
  video_url: string,
  analysis_data: {
    audio_analysis: {
      combined_transcript: string,
      detected_language: string,
      confidence: number
    },
    screenshot_urls: string[],
    video_analysis: { pending: true },
    subtitle_analysis: { pending: true },
    video_id: string  // For async analysis
  },
  processing_time_seconds: number
}
```

### Phase 2: Asynchronous AI Analysis
```
POST /server/av/analyzeRestartVideo
Body: {
  host: Host,
  device_id: string,
  video_id: string,
  screenshot_urls: string[]  // From fast generation phase
}
Response: {
  success: true,
  analysis_data: {
    video_id: string,
    subtitle_analysis: {
      success: boolean,
      subtitles_detected: boolean,
      extracted_text: string,
      detected_language: string,
      confidence: number
    },
    video_analysis: {
      success: boolean,
      frame_descriptions: string[],  // "Frame 1: ...", "Frame 2: ..."
      video_summary: string,
      frames_analyzed: number
    }
  },
  processing_time_seconds: number
}
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

### Timing Benchmarks (Two-Phase)
**Phase 1 (Fast Generation):**
- **Video Generation**: 2-3 seconds (MP4 creation)
- **Audio Analysis**: 1-2 seconds (merged segments, local processing)
- **Screenshot Collection**: <1 second (optimized to 12 screenshots vs 45)
- **Response Time**: Video player shows immediately

**Phase 2 (Async Analysis):**
- **Subtitle Detection**: 3-5 seconds (AI analysis on 5 screenshots)
- **Video Description**: 8-12 seconds (AI analysis on 10 screenshots + summary)
- **Total Analysis**: 10-15 seconds (runs in background)

### Resource Optimization
- **Screenshot Reduction**: 73% fewer screenshots (12 vs 45 for 10s video)
- **Audio Merging**: Single 10-12s audio file vs multiple 1s segments
- **Memory Efficiency**: No temporary files, uses existing continuous capture
- **Network Optimization**: Backend handles all AI analysis, no frontend R2 polling

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
1. **Two-Phase Architecture**: Fast video generation + asynchronous AI analysis
2. **No Legacy Code**: Clean implementation without backward compatibility or fallback mechanisms
3. **Global Configuration**: Uses `HLS_SEGMENT_DURATION` consistently across all components
4. **Optimized Performance**: 1 FPS screenshot analysis, merged audio segments
5. **Backend-Driven Analysis**: All AI processing handled by backend, frontend receives complete results
6. **Timeline Synchronization**: Video segments and screenshots use same time period

### Data Flow (Two-Phase)
```
Phase 1 - Fast Generation:
1. Frontend → /server/av/generateRestartVideo
2. Backend → generateRestartVideoFast() creates MP4 in 2-3s
3. Backend → Collects synchronized screenshots (1 FPS)
4. Backend → Processes merged audio segments locally
5. Frontend ← Receives video URL + basic analysis immediately

Phase 2 - Async Analysis:
6. Frontend → /server/av/analyzeRestartVideo (video_id + screenshot_urls)
7. Backend → analyzeRestartVideoAsync() performs AI analysis
8. Backend → Subtitle detection on 5 screenshots
9. Backend → Video description on 10 screenshots + summary
10. Frontend ← Receives complete AI analysis results
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
