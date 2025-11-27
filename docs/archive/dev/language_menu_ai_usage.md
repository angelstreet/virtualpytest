# AI Language/Subtitle Menu Analysis

## Overview

This feature provides AI-powered analysis of language and subtitle menu options from images. It detects available languages, currently selected options, and provides index mapping for navigation.

## Backend Implementation

### New Method: `analyze_language_menu_ai()`

Located in: `backend_host/src/controllers/verification/video.py`

```python
result = video_controller.analyze_language_menu_ai(image_path)
```

**Response Format:**
```json
{
  "success": true,
  "menu_detected": true,
  "audio_languages": ["English", "French", "Spanish"],
  "subtitle_languages": ["English", "French", "Spanish", "Off"],
  "selected_audio": 0,
  "selected_subtitle": 3,
  "image_path": "frame.jpg",
  "analysis_type": "ai_language_menu_analysis"
}
```

### API Endpoints

- **Host:** `POST /host/verification/video/analyzeLanguageMenu`
- **Server:** `POST /server/verification/video/analyzeLanguageMenu`

**Request Body:**
```json
{
  "host": "host_info",
  "device_id": "device1",
  "image_source_url": "http://host:port/frame.jpg"
}
```

## Frontend Implementation

### Type Definition

Located in: `frontend/src/types/pages/Monitoring_Types.ts`

```typescript
export interface LanguageMenuAnalysis {
  menu_detected: boolean;
  audio_languages: string[];      // Ordered list: 0=English, 1=French, etc.
  subtitle_languages: string[];   // Ordered list: 0=English, 1=French, 2=Spanish, 3=Off
  selected_audio: number;         // Index of selected audio (-1 if none)
  selected_subtitle: number;      // Index of selected subtitle (-1 if none)
}
```

### Hook Usage

Located in: `frontend/src/hooks/monitoring/useMonitoringLanguageMenu.ts`

```typescript
import { useMonitoringLanguageMenu } from '../hooks/monitoring';

// In your component
const {
  analyzeLanguageMenu,
  isAnalyzingLanguageMenu,
  hasLanguageMenuResults,
  currentLanguageMenuAnalysis,
} = useMonitoringLanguageMenu({
  frames,
  currentIndex,
  setFrames,
  setIsPlaying,
  setUserSelectedFrame,
  host,
  device,
});

// Call analysis
await analyzeLanguageMenu();

// Access results
if (currentLanguageMenuAnalysis?.menu_detected) {
  console.log('Audio options:', currentLanguageMenuAnalysis.audio_languages);
  console.log('Selected audio:', currentLanguageMenuAnalysis.selected_audio);
  console.log('Subtitle options:', currentLanguageMenuAnalysis.subtitle_languages);
  console.log('Selected subtitle:', currentLanguageMenuAnalysis.selected_subtitle);
}
```

## Usage Examples

### Example 1: Basic Detection
```typescript
// Call analysis on current frame
await analyzeLanguageMenu();

// Check results
if (currentLanguageMenuAnalysis?.menu_detected) {
  // Menu detected
  const audioOptions = currentLanguageMenuAnalysis.audio_languages;
  const subtitleOptions = currentLanguageMenuAnalysis.subtitle_languages;
  
  console.log('Available audio languages:', audioOptions);
  // Output: ["English", "French", "Spanish"]
  
  console.log('Available subtitle options:', subtitleOptions);
  // Output: ["English", "French", "Spanish", "Off"]
}
```

### Example 2: Navigation Mapping
```typescript
if (currentLanguageMenuAnalysis?.menu_detected) {
  // To select French audio (index 1)
  console.log('To select French audio, navigate to index:', 1);
  
  // To turn off subtitles (index 3 for "Off")
  console.log('To turn off subtitles, navigate to index:', 3);
  
  // Currently selected options
  const currentAudio = currentLanguageMenuAnalysis.audio_languages[currentLanguageMenuAnalysis.selected_audio];
  const currentSubtitle = currentLanguageMenuAnalysis.subtitle_languages[currentLanguageMenuAnalysis.selected_subtitle];
  
  console.log('Currently selected:', { currentAudio, currentSubtitle });
}
```

### Example 3: Component Integration
```typescript
const LanguageMenuAnalyzer = () => {
  const { analyzeLanguageMenu, isAnalyzingLanguageMenu, currentLanguageMenuAnalysis } = useMonitoringLanguageMenu({
    frames, currentIndex, setFrames, setIsPlaying, setUserSelectedFrame, host, device
  });

  return (
    <div>
      <button onClick={analyzeLanguageMenu} disabled={isAnalyzingLanguageMenu}>
        {isAnalyzingLanguageMenu ? 'Analyzing...' : 'Analyze Language Menu'}
      </button>
      
      {currentLanguageMenuAnalysis?.menu_detected && (
        <div>
          <h3>Language Menu Detected</h3>
          
          <div>
            <h4>Audio Languages:</h4>
            <ul>
              {currentLanguageMenuAnalysis.audio_languages.map((lang, index) => (
                <li key={index} style={{ fontWeight: index === currentLanguageMenuAnalysis.selected_audio ? 'bold' : 'normal' }}>
                  {index}: {lang} {index === currentLanguageMenuAnalysis.selected_audio && '(Selected)'}
                </li>
              ))}
            </ul>
          </div>
          
          <div>
            <h4>Subtitle Options:</h4>
            <ul>
              {currentLanguageMenuAnalysis.subtitle_languages.map((lang, index) => (
                <li key={index} style={{ fontWeight: index === currentLanguageMenuAnalysis.selected_subtitle ? 'bold' : 'normal' }}>
                  {index}: {lang} {index === currentLanguageMenuAnalysis.selected_subtitle && '(Selected)'}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
};
```

## Response Format Details

### Successful Detection
```json
{
  "success": true,
  "menu_detected": true,
  "audio_languages": ["English", "French", "Spanish"],
  "subtitle_languages": ["English", "French", "Spanish", "Off"],
  "selected_audio": 0,      // English is selected (index 0)
  "selected_subtitle": 3,   // Subtitles are off (index 3)
  "image_path": "frame.jpg",
  "analysis_type": "ai_language_menu_analysis",
  "execution_time_ms": 1250
}
```

### No Menu Detected
```json
{
  "success": true,
  "menu_detected": false,
  "audio_languages": [],
  "subtitle_languages": [],
  "selected_audio": -1,
  "selected_subtitle": -1,
  "image_path": "frame.jpg",
  "analysis_type": "ai_language_menu_analysis",
  "execution_time_ms": 800
}
```

### Error Response
```json
{
  "success": false,
  "error": "AI service not available",
  "execution_time_ms": 50
}
```

## Integration Notes

1. **Minimal Code Changes**: Uses existing AI infrastructure and follows established patterns
2. **Simple Data Structure**: Returns ordered arrays with index mapping
3. **Generic Detection**: Works with any streaming service or application
4. **Separate Function**: Independent of subtitle detection functionality
5. **No Visual Indicators**: Returns raw data for flexible UI implementation

## Requirements

- OpenRouter API key must be set in environment variables
- Same AI model (`qwen/qwen-2.5-vl-7b-instruct`) as existing features
- No additional dependencies required