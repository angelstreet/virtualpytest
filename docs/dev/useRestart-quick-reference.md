# useRestart Hook - Quick Reference

## Import

```typescript
import { useRestart } from '../hooks/pages/useRestart';
```

## Basic Usage

```typescript
const { videoUrl, isGenerating, isReady, error } = useRestart({
  host,
  device,
  includeAudioAnalysis: false
});
```

## Full Analysis

```typescript
const { 
  videoUrl,
  analysisResults,
  analysisProgress,
  isAnalysisComplete
} = useRestart({
  host,
  device,
  includeAudioAnalysis: true
});
```

## Return Values

| Property | Type | Description |
|----------|------|-------------|
| `videoUrl` | `string \| null` | Generated video URL |
| `isGenerating` | `boolean` | Generation in progress |
| `isReady` | `boolean` | Video ready for playback |
| `error` | `string \| null` | Error message if failed |
| `processingTime` | `number \| null` | Generation time (seconds) |
| `analysisResults` | `AnalysisResults` | All analysis results |
| `analysisProgress` | `AnalysisProgress` | Current progress states |
| `isAnalysisComplete` | `boolean` | All analyses finished |
| `analyzeSubtitles` | `Function` | Manual subtitle analysis |
| `analyzeVideoDescription` | `Function` | Manual frame analysis |
| `regenerateVideo` | `Function` | Force video regeneration |

## Analysis Results

### Audio Analysis
```typescript
analysisResults.audio: {
  success: boolean;
  combined_transcript: string;
  detected_language: string;
  speech_detected: boolean;
  confidence: number;
  execution_time_ms: number;
} | null
```

### Subtitle Analysis
```typescript
analysisResults.subtitles: {
  success: boolean;
  subtitles_detected: boolean;
  extracted_text: string;
  detected_language?: string;
  execution_time_ms: number;
} | null
```

### Video Description
```typescript
analysisResults.videoDescription: {
  frame_descriptions: string[];
  video_summary: string;
  frames_analyzed: number;
  execution_time_ms: number;
} | null
```

## Progress States

- `'idle'` - Not started
- `'loading'` - In progress  
- `'completed'` - Finished successfully
- `'error'` - Failed

## Manual Analysis

```typescript
// Analyze image for subtitles
const result = await analyzeSubtitles('https://host/image.jpg');

// Generate AI description
const description = await analyzeVideoDescription('https://host/image.jpg');

// Force regeneration (clears cache)
await regenerateVideo();
```

## Error Handling

```typescript
if (error) {
  console.error('Video generation failed:', error);
}

// Check individual analysis failures
if (analysisProgress.audio === 'error') {
  console.warn('Audio analysis failed');
}
```

## Performance Tips

1. **Memoize props** to prevent unnecessary re-renders
2. **Use error boundaries** for graceful failure handling  
3. **Monitor processing time** for performance issues
4. **Cache is automatic** - no manual management needed

## Common Patterns

### Loading State
```typescript
if (isGenerating) {
  return <Spinner />;
}
```

### Error State  
```typescript
if (error) {
  return <ErrorMessage error={error} />;
}
```

### Video Display
```typescript
if (videoUrl && isReady) {
  return <video src={videoUrl} controls autoPlay />;
}
```

### Analysis Display
```typescript
{analysisResults.audio && (
  <div>
    <h3>Transcript</h3>
    <p>{analysisResults.audio.combined_transcript}</p>
  </div>
)}
```

## Timeouts

- **Video Generation**: No timeout (handled by backend)
- **Subtitle Analysis**: 15 seconds
- **Description Analysis**: 20 seconds
- **Cache TTL**: 30 seconds

## Backend Endpoints (Two-Phase)

### Phase 1: Fast Generation
- **URL**: `/server/av/generateRestartVideo`
- **Method**: `POST`
- **Payload**: `{ host, device_id, duration_seconds: 10 }`
- **Response**: Video URL + basic analysis + video_id

### Phase 2: Async Analysis  
- **URL**: `/server/av/analyzeRestartVideo`
- **Method**: `POST`
- **Payload**: `{ host, device_id, video_id, screenshot_urls }`
- **Response**: Complete AI analysis (subtitles + descriptions)

---

**Version**: 2.0.0 | **Updated**: September 2025
