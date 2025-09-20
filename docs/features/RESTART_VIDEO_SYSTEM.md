# Restart Video System Documentation

## Overview

The Restart Video System provides fast 10-second video generation with comprehensive AI-powered analysis including audio transcription, subtitle detection, frame-by-frame video descriptions, and **dynamic audio dubbing**. The system uses a **two-phase approach**: fast video generation followed by asynchronous AI analysis to ensure immediate video playback while maintaining comprehensive analysis capabilities. Additionally, users can generate dubbed versions in multiple languages with background audio preservation.

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

**Phase 3: Dynamic Audio Dubbing** (`generateDubbedRestartVideo`)
- **Audio Separation**: Uses Demucs to separate vocals from background audio (modern AI model)
- **Voice Translation**: Translates existing transcript to target language
- **Speech Generation**: Creates dubbed voice using gTTS (Google Text-to-Speech)
- **Audio Mixing**: Combines background audio with dubbed voice while preserving timing
- **Video Reconstruction**: Replaces original audio track with dubbed version

**Phase 4: Audio Timing Adjustment** (`adjustVideoAudioTiming`)
- **Timing Control**: Adjust audio timing by ±110ms, ±200ms, ±300ms using FFmpeg
- **Smart Detection**: Automatically applies to dubbed or original video based on current language
- **Caching System**: Timing-adjusted videos cached for instant switching
- **FFmpeg Processing**: Uses `adelay` filter for delays, `atrim` filter for advances

#### Core Implementation (`backend_host/src/controllers/base_controller.py`)
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
- **Comprehensive Frontend Caching**: Intelligent caching for translations, dubbing, and timing adjustments
- **Instant Content Switching**: Cached content switches instantly without backend calls
- **Cache-Aware UI**: Different toast messages for cached vs newly processed content

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
- **Automatic Dubbing**: When non-English language selected, automatically chains translation → dubbing
- **Frame-by-Frame Analysis**: Individual frame descriptions plus conclusion summary
- **Subtitle Text Display**: Shows original detected text with translation support
- **Audio Timing Control**: Simple dropdown (0ms, ±110ms, ±200ms, ±300ms) with OK button for instant adjustment

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

### 4. Dubbing Workflow
```
First Time:
Select Language (French) → Toast: "🌐 Starting translation..." → 
Toast: "🎤 Starting dubbing..." → Toast: "🎬 Dubbing complete! (cached for future use)" → 
Dubbed video available with preserved background audio

Subsequent Times:
Select Language (French) → Toast: "✅ Switched to French (cached)" → 
Instant language switch with dubbed video
```

### 5. Audio Timing Adjustment
```
First Time:
Settings Panel → Audio Timing Section → Select offset (+110ms) → Click OK → 
Toast: "✅ Audio timing: +110ms (processed & cached)" → Video player updates with adjusted audio

Subsequent Times:
Settings Panel → Audio Timing Section → Select offset (+110ms) → Click OK → 
Toast: "✅ Audio timing: +110ms (cached)" → Instant timing switch

Reset to Original:
Settings Panel → Audio Timing Section → Select 0ms → Click OK → 
Toast: "✅ Audio timing reset to 0ms" → Instant switch to original timing
```

### 6. Overlay Controls
```
Settings Panel:
├── Video Summary
│   ├── ☐ Show Per-Second Summary (top overlay)
│   ├── Language: [English ▼]
│   └── [Final summary text display]
├── Subtitles  
│   ├── ☐ Show Subtitle Overlay (bottom overlay)
│   └── Language: [Spanish ▼]
├── Audio Transcript
│   └── [Full transcript text]
└── Audio Timing
    ├── Offset: [+110ms ▼]
    └── [OK Button]
```

## API Endpoints (Four-Phase Architecture)

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
```

### Phase 3: Dynamic Audio Dubbing
```
POST /server/restart/generateDubbedVideo
Body: {
  host: Host,
  device_id: string,
  video_id: string,
  target_language: string,  // 'es', 'fr', 'de', 'it', 'pt'
  existing_transcript: string
}
Response: {
  success: true,
  dubbed_video_url: string,
  gtts_audio_url: string,    // MP3 for gTTS comparison
  edge_audio_url: string,    // MP3 for Edge-TTS comparison
  target_language: string,
  video_id: string
}

### Phase 4: Audio Timing Adjustment
```
POST /server/restart/adjustAudioTiming
Body: {
  host: Host,
  device_id: string,
  video_url: string,        // URL of video to adjust (original or dubbed)
  timing_offset_ms: number, // ±110, ±200, ±300 milliseconds
  language: string          // "original" or language code ("es", "fr", etc.)
}
Response: {
  success: true,
  adjusted_video_url: string,
  timing_offset_ms: number,
  language: string,
  video_id: string,
  original_video_url: string
}
```

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

interface DubbingState {
  dubbedVideos: Record<string, string>;  // language -> video_url
  dubbedAudioUrls: Record<string, { gtts: string; edge: string }>;  // language -> audio comparison URLs
  isDubbing: boolean;
  dubbingCache: Record<string, boolean>;  // language -> is_cached
  generateDubbedVersion: (language: string, transcript: string, videoId: string) => Promise<void>;
}

interface TimingCache {
  timingCache: Record<string, Record<number, string>>;  // language -> { offset_ms -> video_url }
}
```

## Configuration

### Video Settings
- **Duration**: Fixed 10 seconds
- **Format**: MP4 (H.264)
- **Source**: HLS segments from live stream
- **Quality**: Inherits from HLS stream quality

### Analysis Settings
- **Audio Processing**: Local `AudioAIHelpers` with merged segments
- **Screenshot Analysis**: FPS-based alignment (5 FPS for HDMI, 2 FPS for VNC)
- **Screenshot Offset**: 3-frame offset to account for segment timing differences
- **Subtitle Detection**: Frame-aligned screenshots with proper timing
- **AI Models**: Existing Whisper for audio, OpenRouter vision models for images
- **Batch Processing**: 6 images per batch (optimized from 10 for reliability)
- **Batch Fallback**: Automatic retry with smaller batches on AI model limits

### Dubbing Settings
- **Audio Separation**: Demucs htdemucs model (vocals + no_vocals) - state-of-the-art AI separation
- **Text-to-Speech**: Dual engine support - gTTS (Google) and Edge-TTS (Microsoft) for quality comparison
- **Supported Languages**: Spanish (es), French (fr), German (de), Italian (it), Portuguese (pt)
- **Audio Processing**: pydub for mixing, FFmpeg for video reconstruction
- **Translation Cache**: `{video_id: {language: translation_result}}` for instant re-dubbing
- **Background Preservation**: 100% background audio volume with +5dB voice boost
- **Audio Comparison**: Both TTS engines generate MP3 files for quality testing
- **File Naming**: `restart_original_*` for source files, `restart_{lang}_*` for dubbed versions

### Translation Settings
- **Cache Structure**: `{language: translation_result}` - frontend session cache
- **Batch Processing**: Single API call with structure preservation
- **Performance**: ~2-5 seconds first time, instant for cached languages
- **Frame Alignment**: Maintains frame numbers during translation
- **Instant Switching**: Cached translations switch immediately without backend calls
- **Cache Persistence**: Translations persist throughout session for instant access

### Batch Processing Settings
- **Batch Size**: 6 images per batch (optimized from 10 for AI model reliability)
- **AI Model Limits**: Prevents "Empty content from AI" errors with large batches
- **Failure Handling**: Shows error toasts with duration timing
- **AI Fallback**: Automatic model switching (Kimi → Qwen) on rate limits
- **Toast Notifications**: Success and failure states show processing duration

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
- **Batch Processing**: 6 images per batch (optimized for AI model limits)
- **Subtitle Detection**: 3-5 seconds (AI analysis with batch processing)
- **Video Description**: 8-12 seconds (AI analysis with batch processing + summary)
- **Failure Handling**: Shows error toast with duration on batch failures
- **Total Analysis**: 10-15 seconds (runs in background)

**Phase 3 (Dubbing - On Demand):**
- **First Time Processing**:
  - **Audio Separation**: 5-8 seconds (Demucs processing - cached after first use)
  - **Translation**: 0.5-1 seconds (cached after first use, with AI fallback on rate limits)
  - **Dual TTS Generation**: 3-5 seconds (both gTTS and Edge-TTS)
  - **Audio Mixing**: 1-2 seconds (pydub processing with 100% background volume)
  - **Video Reconstruction**: 1-2 seconds (FFmpeg processing)
  - **Audio Comparison Files**: MP3 generation for quality testing
  - **Total Dubbing**: 10-18 seconds (triggered by language selection)
- **Cached Access**: <100ms (instant switch to previously dubbed language)
- **Translation Switching**: <100ms (instant switch between cached translations)

**Phase 4 (Audio Timing - On Demand):**
- **Cached Component Method** (Primary):
  - **Vocal Timing**: 0.5-1 second (FFmpeg audio filter on vocals only)
  - **Audio Mixing**: 0.5-1 second (pydub background + timed vocals)
  - **Video Assembly**: 0.5-1 second (FFmpeg silent video + mixed audio)
  - **Total**: 1.5-3 seconds (reuses cached silent video + background)
- **Fallback Method** (When cached components unavailable):
  - **FFmpeg Processing**: 1-3 seconds (full video audio filter)
- **Caching Check**: <0.1 seconds (instant if already cached)
- **Total Timing Adjustment**: 1.5-3 seconds (first time), <0.1 seconds (cached)

### Resource Optimization
- **Screenshot Reduction**: 73% fewer screenshots (12 vs 45 for 10s video)
- **Audio Merging**: Single 10-12s audio file vs multiple 1s segments
- **Memory Efficiency**: Fixed filename overwriting eliminates cleanup needs
- **Network Optimization**: Backend handles all AI analysis, no frontend R2 polling
- **Batch Optimization**: 6 images per batch prevents AI model overload
- **Dubbing Efficiency**: Reuses extracted audio, caches translations and background separation
- **Model Caching**: Demucs model downloaded once and cached for subsequent uses
- **AI Fallback**: Automatic model switching on rate limits (Kimi → Qwen)
- **Frontend Caching**: 90%+ reduction in backend calls for repeat operations
- **Instant Switching**: Cached content (translations, dubbing, timing) switches in <100ms
- **Session Persistence**: All caches persist throughout user session for optimal UX

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
- **Frame-Aligned Translation**: Preserves frame-to-content mapping during translation
- **Single API Call**: Batch translation for performance (20x faster than individual calls)
- **Frontend Translation Caching**: Instant language switching after first translation
- **Session Persistence**: Cached translations persist throughout session
- **Smart Cache Lookup**: Always checks cache before backend calls
- **Instant English Switch**: Original English content always available instantly
- **No Fallbacks**: Shows "Translation not found" for missing translations
- **Dual Content Support**: Translates both subtitles and descriptions simultaneously

## Frontend Caching System

### Cache Architecture
The frontend implements a comprehensive four-tier caching system that eliminates redundant backend calls and provides instant content switching:

#### 1. Translation Cache
```typescript
translationResults: Record<string, TranslationResults> = {
  "es": { transcript: "...", summary: "...", frameDescriptions: [...], frameSubtitles: [...] },
  "fr": { transcript: "...", summary: "...", frameDescriptions: [...], frameSubtitles: [...] }
}
```
- **Purpose**: Stores translated content for instant language switching
- **Behavior**: First translation takes 2-5s, subsequent switches are instant (<100ms)
- **Toast Messages**: 
  - First time: `"✅ Translation to Spanish complete! (3.2s, cached for future use)"`
  - Cached: `"✅ Switched to Spanish (cached)"`
  - English: `"✅ Switched to English (original)"` (always instant)

#### 2. Dubbing Cache
```typescript
dubbingCache: Record<string, boolean> = {
  "es": true,  // Spanish dubbing completed and cached
  "fr": true   // French dubbing completed and cached
}

dubbedVideos: Record<string, string> = {
  "es": "restart_es_dubbed_video.mp4",
  "fr": "restart_fr_dubbed_video.mp4"
}
```
- **Purpose**: Tracks completed dubbing operations for instant video switching
- **Behavior**: First dubbing takes 10-18s, subsequent access is instant
- **Toast Messages**:
  - First time: `"🎉 Dubbing for Spanish completed! (cached for future use)"`
  - Cached: `"✅ Dubbed video for Spanish (cached)"`

#### 3. Component Cache
```typescript
componentCache: Record<string, {
  silent_video: string;
  background_audio: string;
  original_vocals: string;
  dubbed_vocals: Record<string, string>;
}> = {
  "restart_original_video.mp4": {
    silent_video: "/path/to/restart_video_no_audio.mp4",
    background_audio: "/path/to/restart_original_background.wav", 
    original_vocals: "/path/to/restart_original_vocals.wav",
    dubbed_vocals: {
      "es": "/path/to/restart_es_dubbed_voice_edge.wav",
      "fr": "/path/to/restart_fr_dubbed_voice_edge.wav"
    }
  }
}
```
- **Purpose**: Tracks separated video components to optimize backend processing
- **Backend Integration**: Passes component paths to backend, eliminating redundant separation
- **Auto-Population**: Updated when backend creates new components during first timing/dubbing
- **Cross-Operation Reuse**: Same components used for timing adjustments and dubbing

#### 4. Audio Timing Cache
```typescript
timingCache: Record<string, Record<number, string>> = {
  "en": { 
    0: "restart_original_video.mp4", 
    -200: "restart_original_video_syncm200.mp4",
    100: "restart_original_video_syncp100.mp4"
  },
  "es": { 
    0: "restart_es_dubbed_video.mp4", 
    -200: "restart_es_dubbed_video_syncm200.mp4" 
  }
}
```
- **Purpose**: Stores timing-adjusted videos per language for instant switching
- **Behavior**: First timing adjustment takes 1-3s, subsequent switches are instant
- **Special Handling**: 0ms timing handled entirely in frontend (no backend call)
- **Toast Messages**:
  - First time: `"✅ Audio timing: -200ms (processed & cached)"`
  - Cached: `"✅ Audio timing: -200ms (cached)"`
  - Reset: `"✅ Audio timing reset to 0ms"` (always instant)

### Cache Behavior Patterns

#### Cache-First Lookup
All operations follow this pattern:
1. **Check Cache**: Look for existing content in appropriate cache
2. **Instant Return**: If cached, switch immediately with "cached" toast
3. **Backend Call**: If not cached, process via backend and cache result
4. **Cache Update**: Store result for future instant access

#### Session Persistence
- **Lifetime**: All caches persist throughout user session
- **Memory Efficient**: Only stores URLs and text data, not large files
- **Language Aware**: Separate caches per language for optimal organization

#### Performance Impact
- **Backend Load Reduction**: 90%+ fewer backend calls for repeat operations
- **User Experience**: Sub-100ms switching for all cached content
- **Network Efficiency**: Eliminates redundant processing and data transfer

### Cache Integration Examples

#### Language Switching Flow
```typescript
// First time Spanish selection
translateToLanguage("es") → Backend processing (3s) → Cache storage → Success toast

// Subsequent Spanish selections  
translateToLanguage("es") → Cache hit → Instant switch → Cached toast

// English selection (always instant)
translateToLanguage("en") → No cache needed → Instant switch → Original toast
```

#### Timing Adjustment Flow
```typescript
// First time -200ms adjustment
applyAudioTiming(-200) → Backend processing (2s) → Cache storage → Success toast

// Subsequent -200ms adjustments
applyAudioTiming(-200) → Cache hit → Instant switch → Cached toast

// 0ms reset (always instant)
applyAudioTiming(0) → Frontend URL manipulation → Instant switch → Reset toast
```

## Implementation Approach

### Key Design Principles
1. **Two-Phase Architecture**: Fast video generation + asynchronous AI analysis
2. **No Legacy Code**: Clean implementation without backward compatibility or fallback mechanisms
3. **Global Configuration**: Uses `HLS_SEGMENT_DURATION` consistently across all components
4. **Optimized Performance**: 1 FPS screenshot analysis, merged audio segments
5. **Backend-Driven Analysis**: All AI processing handled by backend, frontend receives complete results
6. **Timeline Synchronization**: Video segments and screenshots use same time period
7. **Comprehensive Frontend Caching**: Intelligent caching system for instant content switching
8. **Cache-First Architecture**: Always check cache before making backend calls

### Data Flow (Three-Phase)
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

Phase 3 - Dubbing (On Language Selection):
11. Frontend → Language selection triggers translation + dubbing
12. Frontend → /server/restart/generateDubbedVideo (existing_transcript + target_language)
13. Backend → Demucs separates vocals from background audio
14. Backend → Translates transcript to target language (cached)
15. Backend → gTTS generates dubbed voice
16. Backend → Mixes dubbed voice with background audio
17. Backend → Creates new MP4 with dubbed audio track
18. Frontend ← Receives dubbed video URL
```

### Why This Approach Works
- **Fast**: Video available in 2-3 seconds, no waiting for analysis
- **Efficient**: No temporary files, minimal network overhead, reuses existing infrastructure
- **Reliable**: Uses proven existing systems (AudioAIHelpers, continuous capture, image analysis)
- **Maintainable**: Single source of truth, no duplicate code paths
- **Scalable**: Dubbing is on-demand, translation caching prevents duplicate work
- **Quality**: Background audio preservation maintains original video atmosphere

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

### Dubbing Enhancements
- Voice cloning for consistent speaker identity (ElevenLabs integration)
- Emotion preservation in dubbed speech
- Multi-speaker detection and separate dubbing
- Real-time dubbing during live streams
- Custom voice selection per language
- Lip-sync adjustment for video content

## Troubleshooting

### Common Issues
1. **Video not appearing**: Check HLS segment availability and `/server/av/generateRestartVideo` response
2. **Audio analysis not loading**: Check segment files are passed correctly from video generation
3. **Screenshot analysis failing**: Verify FPS detection and 3-frame offset alignment
4. **Batch analysis failing**: AI model limits hit with large batches - reduced to 6 images per batch
5. **Translation misalignment**: Check frame-to-content mapping preservation
6. **AI rate limiting**: Automatic fallback from Kimi to Qwen on 429 errors
7. **Overlays not showing**: Check that analysis completed and data structure matches expected format
8. **Dubbing not starting**: Verify transcript exists and dependencies installed (demucs, pydub, gTTS, edge-tts)
9. **Audio separation failing**: Check Demucs model download and audio file format
10. **TTS generation failing**: Verify internet connection for gTTS/Edge-TTS and language code support
11. **Video file not found**: Ensure `restart_original_video.mp4` exists (new naming convention)
12. **Dubbed audio out of sync**: Check video duration detection and audio mixing timing

### Debug Information
- Console logs prefixed with `[@hook:useRestart]` and `[@component:RestartPlayer]`
- Screenshot alignment logs: `Screenshot alignment - FPS:5, PerSegment:5, Start:1346091, Offset:3, Adjusted:1346088`
- Translation cache logs: `Using cached translation for french` or `Cached batch translation for french`
- Segment files logs: `Segment files available: 12` or `No segment files provided, falling back to globbing`
- Backend logs show `[RestartVideo]` prefixed messages for audio processing
- Batch processing logs: `BATCH_1_START: frames=1-6 images=6` or `BATCH_1_FAILED: Empty content from AI`
- AI fallback logs: `Kimi rate limited, trying Qwen...` or `SUCCESS with Qwen: Received 161 characters`
- Dubbing logs: `Starting dubbing to fr`, `Using cached background/vocals separation`, `gTTS speech generated`, `Edge-TTS speech generated`
- Toast notifications: Success shows duration `✅ Analysis complete in 15s!`, failures show `❌ Analysis failed after 12s`
- Error logs: `Video file not found: restart_original_video.mp4` (indicates naming alignment needed)

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

### Dubbing Implementation
- **New Dependencies**: Added demucs, pydub, gTTS, edge-tts to requirements.txt (removed tensorflow/spleeter)
- **New Components**: `AudioDubbingHelpers` class for dual TTS audio separation and mixing
- **Extended Helpers**: `VideoRestartHelpers.generate_dubbed_restart_video()` method with caching
- **Frontend Integration**: Extended `useRestart` hook and `RestartSettingsPanel` for dubbing with audio comparison
- **Automatic Workflow**: Dubbing triggered automatically after translation completes
- **Modern AI**: Uses Demucs for superior audio separation quality vs legacy Spleeter
- **Dual TTS**: Generates both gTTS and Edge-TTS versions for quality comparison
- **Audio Comparison**: Hyperlinks in UI (dub_gTTS, dub_edge) for direct audio testing
- **File Management**: Fixed naming convention with automatic overwriting
- **Clean Architecture**: No fallback code, reuses existing audio extraction and translation systems
- **Background Caching**: Demucs separation cached after first use for all languages

### Audio Timing Implementation
- **Backend Method**: `VideoRestartHelpers.adjust_video_audio_timing()` with component reuse optimization
- **Component Reuse Architecture**: Reuses same base components across all languages
- **Primary Method**: 
  - **Step 1**: Apply timing to appropriate vocals only (positive: silence prepend, negative: `atrim` from start)
  - **Step 2**: Mix background + timed vocals (pydub overlay)
  - **Step 3**: Combine silent video + mixed audio (FFmpeg assembly)
- **Fallback Method**: Traditional FFmpeg filters on full video when cached components unavailable
- **Frontend-Driven Component Caching**: 
  - **Frontend Tracks Components**: Frontend maintains `componentCache` with paths to separated video components
  - **API Integration**: Frontend passes component paths to backend in timing/dubbing requests
  - **Auto-Creation**: Backend creates components only when frontend doesn't provide paths
  - **Universal Component Reuse**: Same base components (silent video + background) used for all languages
  - **Language-Specific Vocals**: Uses original vocals for English, dubbed vocals for other languages
  - **No Backend File Cache**: Backend never checks file existence - relies on frontend component tracking
  - **Clean Architecture**: Frontend handles caching, backend handles processing
- **Timing Methods**:
  - **Positive Timing (+ms)**: Prepends silence using FFmpeg `anullsrc` + `concat` (clean, no echo)
  - **Negative Timing (-ms)**: Trims from start using FFmpeg `atrim` (clean, precise)
  - **No adelay Filter**: Eliminates phase/echo issues from stereo channel misalignment
- **Performance**: 1.5-3 seconds first generation, <0.1 seconds for cached versions
- **No Double Audio**: Clean separation + proper timing methods ensure single vocal track
- **Cross-Language Support**: Same components work for original English and all dubbed languages
- **Frontend Integration**: Simple dropdown UI in `RestartSettingsPanel` with OK button and loading states
- **Smart Detection**: Automatically applies to dubbed or original video based on current language selection
- **API Endpoint**: `/server/restart/adjustAudioTiming` for timing adjustment requests
- **File Naming**: Respects original filename + sync suffix (e.g., `restart_original_video_syncp100.mp4`, `restart_es_dubbed_video_syncm200.mp4`)
- **Error Handling**: Graceful fallback with toast notifications for success/failure states
- **React Protection**: StrictMode deduplication using complex key-based pattern (video URL + offset + language)
