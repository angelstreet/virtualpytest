# useRestart Hook - Complete Documentation

## Overview

The `useRestart` hook is an expert-level React hook that provides fast video generation with comprehensive AI analysis capabilities for the VirtualPyTest platform. It uses a two-phase architecture: immediate 10-second video generation followed by asynchronous AI analysis including audio transcription, subtitle detection, and frame-by-frame descriptions.

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Installation & Usage](#installation--usage)
- [API Reference](#api-reference)
- [Examples](#examples)
- [Performance Considerations](#performance-considerations)
- [Error Handling](#error-handling)
- [Backend Integration](#backend-integration)
- [Troubleshooting](#troubleshooting)

## Features

### 🎥 Video Generation
- **Fast MP4 Creation**: Converts HLS segments to compressed MP4 videos
- **Smart Caching**: Professional caching system prevents duplicate requests
- **Automatic Cleanup**: Memory management with TTL-based expiration
- **Progress Tracking**: Real-time generation status and timing

### 🤖 AI Analysis Pipeline
- **Audio Transcription**: Backend Whisper AI processing for speech-to-text
- **Subtitle Detection**: Frontend OCR analysis of video frames
- **Frame Description**: AI-powered description of video content
- **Multi-language Support**: Automatic language detection

### 🚀 Performance Features
- **Professional Caching**: 30-second TTL with automatic cleanup
- **Optimized Re-renders**: `useCallback`/`useMemo` for performance
- **Abort Controllers**: Timeout protection (15s/20s)
- **Memory Leak Prevention**: Automatic resource cleanup

### 🛡️ Error Handling
- **Comprehensive Boundaries**: Graceful degradation on failures
- **Network Recovery**: Automatic retry with exponential backoff
- **Timeout Protection**: Prevents hanging requests
- **Individual Analysis Isolation**: One analysis failure doesn't affect others

## Architecture

```mermaid
graph TD
    A[useRestart Hook] --> B[Video Generation]
    A --> C[Analysis Pipeline]
    A --> D[Cache Management]
    
    B --> E[Backend API Call]
    B --> F[Response Processing]
    B --> G[State Updates]
    
    C --> H[Audio Analysis - Backend]
    C --> I[Subtitle Analysis - Frontend]
    C --> J[Frame Analysis - Frontend]
    
    D --> K[TTL Cache]
    D --> L[Duplicate Prevention]
    D --> M[Memory Cleanup]
    
    E --> N[/server/av/generateRestartVideo]
    H --> O[Whisper AI]
    I --> P[OCR Processing]
    J --> Q[AI Description]
```

## Installation & Usage

### Basic Import

```typescript
import { useRestart } from '../hooks/pages/useRestart';
```

### Basic Video Generation

```typescript
function RestartPlayer({ host, device }) {
  const { 
    videoUrl, 
    isGenerating, 
    isReady, 
    error 
  } = useRestart({
    host,
    device,
    includeAudioAnalysis: false
  });

  if (isGenerating) return <div>Generating video...</div>;
  if (error) return <div>Error: {error}</div>;
  if (!videoUrl) return <div>No video available</div>;

  return (
    <video src={videoUrl} controls autoPlay />
  );
}
```

### Full Analysis Pipeline

```typescript
function AdvancedRestartPlayer({ host, device }) {
  const { 
    videoUrl,
    isGenerating,
    analysisResults,
    analysisProgress,
    isAnalysisComplete
  } = useRestart({
    host,
    device,
    includeAudioAnalysis: true
  });

  return (
    <div>
      <video src={videoUrl} controls />
      
      {/* Audio Analysis Results */}
      {analysisResults.audio && (
        <div>
          <h3>Audio Transcript</h3>
          <p>{analysisResults.audio.combined_transcript}</p>
          <p>Language: {analysisResults.audio.detected_language}</p>
          <p>Confidence: {analysisResults.audio.confidence}</p>
        </div>
      )}
      
      {/* Subtitle Analysis Results */}
      {analysisResults.subtitles && (
        <div>
          <h3>Detected Subtitles</h3>
          <p>{analysisResults.subtitles.extracted_text}</p>
        </div>
      )}
      
      {/* Video Description Results */}
      {analysisResults.videoDescription && (
        <div>
          <h3>Video Description</h3>
          <p>{analysisResults.videoDescription.video_summary}</p>
          <ul>
            {analysisResults.videoDescription.frame_descriptions.map((desc, i) => (
              <li key={i}>{desc}</li>
            ))}
          </ul>
        </div>
      )}
      
      {/* Analysis Progress */}
      <div>
        <p>Audio: {analysisProgress.audio}</p>
        <p>Subtitles: {analysisProgress.subtitles}</p>
        <p>Description: {analysisProgress.videoDescription}</p>
        <p>Complete: {isAnalysisComplete ? 'Yes' : 'No'}</p>
      </div>
    </div>
  );
}
```

### Manual Analysis Triggers

```typescript
function ManualAnalysisExample({ host, device }) {
  const { 
    analyzeSubtitles, 
    analyzeVideoDescription,
    regenerateVideo
  } = useRestart({ host, device });

  const handleAnalyzeImage = async (imageUrl: string) => {
    try {
      // Analyze subtitles in specific image
      const subtitleResult = await analyzeSubtitles(imageUrl);
      console.log('Subtitle result:', subtitleResult);
      
      // Generate AI description of image
      const descriptionResult = await analyzeVideoDescription(imageUrl);
      console.log('Description result:', descriptionResult);
    } catch (error) {
      console.error('Analysis failed:', error);
    }
  };

  const handleRegenerateVideo = async () => {
    try {
      await regenerateVideo();
      console.log('Video regenerated successfully');
    } catch (error) {
      console.error('Regeneration failed:', error);
    }
  };

  return (
    <div>
      <button onClick={() => handleAnalyzeImage('https://example.com/image.jpg')}>
        Analyze Image
      </button>
      <button onClick={handleRegenerateVideo}>
        Regenerate Video
      </button>
    </div>
  );
}
```

## API Reference

### Hook Parameters

```typescript
interface UseRestartParams {
  host: Host;                    // Host configuration object
  device: Device;                // Device configuration object
  includeAudioAnalysis?: boolean; // Enable AI audio analysis (default: false)
}
```

### Return Interface

```typescript
interface UseRestartReturn {
  // ===== CORE VIDEO STATE =====
  videoUrl: string | null;           // Generated video URL
  isGenerating: boolean;             // Generation in progress
  isReady: boolean;                  // Video ready for playback
  error: string | null;              // Error message if failed
  processingTime: number | null;     // Generation time in seconds
  
  // ===== ANALYSIS STATE =====
  analysisResults: AnalysisResults;  // All analysis results
  analysisProgress: AnalysisProgress; // Current analysis progress
  isAnalysisComplete: boolean;       // All analyses finished
  
  // ===== MANUAL TRIGGERS =====
  analyzeAudio: (videoUrl: string) => Promise<any>;
  analyzeSubtitles: (imageUrl: string) => Promise<any>;
  analyzeVideoDescription: (imageUrl: string) => Promise<any>;
  
  // ===== UTILITIES =====
  regenerateVideo: () => Promise<void>; // Force regeneration
}
```

### Analysis Results Structure

```typescript
interface AnalysisResults {
  audio: {
    success: boolean;
    combined_transcript: string;    // Full transcript
    detected_language: string;      // Language code
    speech_detected: boolean;       // Speech found
    confidence: number;             // 0-1 confidence score
    execution_time_ms: number;      // Processing time
  } | null;
  
  subtitles: {
    success: boolean;
    subtitles_detected: boolean;    // Subtitles found
    extracted_text: string;         // Subtitle text
    detected_language?: string;     // Language code
    execution_time_ms: number;      // Processing time
  } | null;
  
  videoDescription: {
    frame_descriptions: string[];   // Per-frame descriptions
    video_summary: string;          // Overall summary
    frames_analyzed: number;        // Number of frames
    execution_time_ms: number;      // Processing time
  } | null;
}
```

## Performance Considerations

### Caching Strategy

```typescript
// Cache Configuration
const CACHE_TTL = 30000; // 30 seconds
const CLEANUP_DELAY = 5000; // 5 seconds after completion

// Cache Key Format
const cacheKey = `${host.host_name}-${device.device_id}`;
```

### Timeout Configuration

```typescript
// Analysis Timeouts
const SUBTITLE_TIMEOUT = 15000;    // 15 seconds
const DESCRIPTION_TIMEOUT = 20000; // 20 seconds

// Abort Controller Usage
const controller = new AbortController();
setTimeout(() => controller.abort(), timeout);
```

### Memory Management

```typescript
// Automatic cleanup after completion
setTimeout(() => {
  videoCache.delete(host, device);
}, 5000);

// Cache expiration
private isExpired(entry: CacheEntry): boolean {
  return Date.now() - entry.timestamp > this.CACHE_TTL;
}
```

## Error Handling

### Error Types

1. **Network Errors**: Connection failures, timeouts
2. **Generation Errors**: Backend processing failures
3. **Analysis Errors**: AI processing failures
4. **Cache Errors**: Cache corruption or expiration

### Error Recovery Strategies

```typescript
// Network Error Recovery
try {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }
} catch (error) {
  if (error.name === 'AbortError') {
    console.log('Request timed out');
  } else {
    console.error('Network error:', error);
  }
}

// Analysis Error Isolation
try {
  await analyzeSubtitles(imageUrl);
} catch (error) {
  // Subtitle analysis failed, but other analyses can continue
  setAnalysisProgress(prev => ({ ...prev, subtitles: 'error' }));
}
```

### Graceful Degradation

```typescript
// Partial results on failure
const isAnalysisComplete = useMemo(() => {
  if (!includeAudioAnalysis) return true;
  
  // Consider complete even if some analyses failed
  return analysisProgress.audio !== 'idle' && 
         analysisProgress.audio !== 'loading' &&
         analysisProgress.subtitles !== 'idle' && 
         analysisProgress.subtitles !== 'loading' &&
         analysisProgress.videoDescription !== 'idle' && 
         analysisProgress.videoDescription !== 'loading';
}, [analysisProgress, includeAudioAnalysis]);
```

## Backend Integration

### Endpoint Configuration

```typescript
// Primary endpoint
const endpoint = '/server/av/generateRestartVideo';

// Request payload
const payload = {
  host: host,
  device_id: device.device_id || 'device1',
  duration_seconds: 10,
  include_audio_analysis: includeAudioAnalysis || false
};
```

### Response Format

```json
{
  "success": true,
  "video_url": "https://host/stream/capture1/restart_video.mp4",
  "processing_time_seconds": 2.5,
  "analysis_data": {
    "audio_analysis": {
      "success": true,
      "combined_transcript": "Hello world, this is a test...",
      "detected_language": "English",
      "speech_detected": true,
      "confidence": 0.95,
      "segments_analyzed": 3
    },
    "screenshot_urls": [
      "https://host/stream/capture1/captures/frame_001.jpg",
      "https://host/stream/capture1/captures/frame_002.jpg"
    ],
    "analysis_complete": true
  }
}
```

### Backend Processing Flow

1. **Video Generation**: Convert HLS segments to MP4
2. **Audio Extraction**: Extract audio from video segments
3. **AI Transcription**: Process audio with Whisper AI
4. **Screenshot Collection**: Gather recent frame captures
5. **URL Building**: Generate proper host URLs for screenshots
6. **Response Assembly**: Combine all data into structured response

## Troubleshooting

### Common Issues

#### 1. Video Generation Fails

**Symptoms**: `error` state contains generation failure message

**Causes**:
- No HLS segments available
- Backend processing error
- Network connectivity issues

**Solutions**:
```typescript
// Check if streaming is active
const { isGenerating, error } = useRestart({ host, device });

if (error?.includes('No video segments found')) {
  // Start video capture first
  console.log('No segments available - start streaming');
}
```

#### 2. Analysis Never Completes

**Symptoms**: `analysisProgress` stuck in 'loading' state

**Causes**:
- Network timeout
- Backend analysis failure
- Invalid screenshot URLs

**Solutions**:
```typescript
// Monitor analysis progress
useEffect(() => {
  if (analysisProgress.audio === 'loading') {
    // Set timeout for stuck analysis
    const timeout = setTimeout(() => {
      console.warn('Audio analysis timeout - may be stuck');
    }, 30000);
    
    return () => clearTimeout(timeout);
  }
}, [analysisProgress.audio]);
```

#### 3. Cache Issues

**Symptoms**: Stale data or duplicate requests

**Causes**:
- Cache corruption
- TTL expiration issues
- Memory leaks

**Solutions**:
```typescript
// Force cache clear
const { regenerateVideo } = useRestart({ host, device });

// Clear cache manually
await regenerateVideo();
```

#### 4. Memory Leaks

**Symptoms**: Increasing memory usage over time

**Causes**:
- Uncleaned timeouts
- Unaborted requests
- Cache accumulation

**Solutions**:
```typescript
// Proper cleanup in useEffect
useEffect(() => {
  const controller = new AbortController();
  
  // Your async operations
  
  return () => {
    controller.abort(); // Clean up requests
  };
}, []);
```

### Debug Mode

Enable detailed logging for troubleshooting:

```typescript
// Add to component
useEffect(() => {
  console.log('useRestart Debug Info:', {
    videoUrl,
    isGenerating,
    isReady,
    error,
    analysisResults,
    analysisProgress,
    isAnalysisComplete
  });
}, [videoUrl, isGenerating, isReady, error, analysisResults, analysisProgress, isAnalysisComplete]);
```

### Performance Monitoring

Track hook performance:

```typescript
// Monitor generation time
useEffect(() => {
  if (processingTime) {
    console.log(`Video generation took ${processingTime}s`);
    
    // Alert on slow generation
    if (processingTime > 10) {
      console.warn('Slow video generation detected');
    }
  }
}, [processingTime]);
```

## Best Practices

### 1. Component Integration

```typescript
// ✅ Good: Proper error boundaries
function RestartPlayerWrapper({ host, device }) {
  return (
    <ErrorBoundary fallback={<div>Video generation failed</div>}>
      <RestartPlayer host={host} device={device} />
    </ErrorBoundary>
  );
}

// ❌ Bad: No error handling
function RestartPlayer({ host, device }) {
  const { videoUrl } = useRestart({ host, device });
  return <video src={videoUrl} />; // Will crash on null videoUrl
}
```

### 2. Performance Optimization

```typescript
// ✅ Good: Memoized host/device objects
const memoizedHost = useMemo(() => host, [host.host_name, host.host_url]);
const memoizedDevice = useMemo(() => device, [device.device_id]);

const restartData = useRestart({
  host: memoizedHost,
  device: memoizedDevice,
  includeAudioAnalysis: true
});

// ❌ Bad: New objects on every render
const restartData = useRestart({
  host: { ...host }, // Creates new object every render
  device: { ...device },
  includeAudioAnalysis: true
});
```

### 3. Analysis Result Handling

```typescript
// ✅ Good: Check for null values
if (analysisResults.audio?.success) {
  const transcript = analysisResults.audio.combined_transcript;
  // Use transcript safely
}

// ❌ Bad: Assume results exist
const transcript = analysisResults.audio.combined_transcript; // May crash
```

### 4. Manual Analysis Usage

```typescript
// ✅ Good: Proper error handling
const handleAnalyze = async (imageUrl: string) => {
  try {
    setLoading(true);
    const result = await analyzeSubtitles(imageUrl);
    if (result) {
      setSubtitleData(result);
    }
  } catch (error) {
    setError(error.message);
  } finally {
    setLoading(false);
  }
};

// ❌ Bad: No error handling
const handleAnalyze = async (imageUrl: string) => {
  const result = await analyzeSubtitles(imageUrl); // May throw
  setSubtitleData(result); // May be null
};
```

## Migration Guide

### From Legacy useRestart

If migrating from an older version:

```typescript
// Old API
const { videoUrl, isLoading, error } = useRestartLegacy(host, device);

// New API
const { 
  videoUrl, 
  isGenerating, // renamed from isLoading
  isReady,      // new state
  error,
  processingTime, // new field
  analysisResults, // new analysis system
  regenerateVideo  // new utility
} = useRestart({ host, device, includeAudioAnalysis: true });
```

### Breaking Changes

1. **Parameters**: Now uses object parameter instead of individual params
2. **State Names**: `isLoading` → `isGenerating`, added `isReady`
3. **Analysis**: Complete rewrite of analysis system
4. **Caching**: New professional caching system
5. **Error Handling**: Enhanced error boundaries and recovery

---

## Support

For issues or questions about the useRestart hook:

1. Check the [troubleshooting section](#troubleshooting)
2. Review the [examples](#examples) for proper usage
3. Enable debug logging for detailed information
4. Check backend logs for server-side issues

**Version**: 2.0.0  
**Last Updated**: September 2025  
**Maintainer**: VirtualPyTest Team
