# Transcript Translation Integration Guide

## Overview
This document explains how to integrate transcript segment translations into the existing translation system **WITHOUT duplicating code**.

## Architecture

### ✅ Frontend (COMPLETED)

#### 1. TypeScript Types Updated
- `TimedSegment` interface now has `translations?: Record<string, string>` field
- `TranslationResults` interface now has `transcriptSegments?: string[]` field
- `EnhancedHLSPlayerProps` now has optional `transcriptTranslations` prop

#### 2. Translation Flow
```
User changes language
  ↓
useRestart.translateToLanguage(language) ← EXISTING FUNCTION
  ↓
Calls /server/translate/restart-batch ← EXISTING ENDPOINT
  ↓
Backend translates ALL content in ONE batch ← NEEDS BACKEND UPDATE
  ↓
Returns translations including transcript_segments ← NEEDS BACKEND UPDATE
  ↓
Frontend caches in translationResults.transcriptSegments ← EXISTING STATE
  ↓
useTranscriptPlayer reads from cache or JSON ← UPDATED
  ↓
Display translated segment ✅
```

#### 3. Translation Priority (in `useTranscriptPlayer`)
1. **First**: Check segment's own `translations` field (from JSON cache)
2. **Second**: Check `externalTranslations` from parent (e.g., from useRestart)
3. **Fallback**: Display original text

### ⚠️ Backend (TODO)

#### Required Changes

##### 1. Extend Existing Batch Translation Endpoint

**File**: `backend_server/src/routes/translation.py` (or wherever `/server/translate/restart-batch` is defined)

**Current Payload**:
```python
{
  "host_name": "host1",
  "content_blocks": {
    "video_summary": {"text": "...", "source_language": "en"},
    "audio_transcript": {"text": "...", "source_language": "en"},
    "frame_descriptions": {"texts": [...], "source_language": "en"},
    "frame_subtitles": {"texts": [...], "source_language": "en"}
  },
  "target_language": "es"
}
```

**ADD**: `transcript_segments` block:
```python
{
  "host_name": "host1",
  "content_blocks": {
    # ... existing blocks ...
    
    # NEW: Transcript segments for archive mode
    "transcript_segments": {
      "texts": ["Hello world", "How are you", "The weather is nice"],
      "source_language": "en",
      "hour": 1,  # Optional: for caching in transcript JSON
      "chunk_index": 0  # Optional: for caching in transcript JSON
    }
  },
  "target_language": "es"
}
```

**Response** (extend existing):
```python
{
  "success": true,
  "translations": {
    "video_summary": "...",
    "audio_transcript": "...",
    "frame_descriptions": [...],
    "frame_subtitles": [...],
    
    # NEW: Translated segments
    "transcript_segments": ["Hola mundo", "Cómo estás", "El clima es agradable"]
  }
}
```

##### 2. Backend Implementation Example

```python
@app.route('/server/translate/restart-batch', methods=['POST'])
def translate_restart_batch():
    data = request.json
    content_blocks = data.get('content_blocks', {})
    target_language = data.get('target_language')
    
    result = {'success': True, 'translations': {}}
    
    # ... existing translation logic for video_summary, audio_transcript, etc. ...
    
    # NEW: Handle transcript segments
    if 'transcript_segments' in content_blocks:
        segment_texts = content_blocks['transcript_segments']['texts']
        source_lang = content_blocks['transcript_segments'].get('source_language', 'en')
        
        translated_segments = []
        for text in segment_texts:
            if text.strip():  # Skip empty segments
                translated = google_translate(
                    text,
                    target_lang=target_language,
                    source_lang=source_lang
                )
                translated_segments.append(translated)
            else:
                translated_segments.append('')  # Keep empty as empty
        
        result['translations']['transcript_segments'] = translated_segments
        
        # OPTIONAL: Cache translations in transcript JSON
        # (This is for persistent caching across page reloads)
        hour = content_blocks['transcript_segments'].get('hour')
        chunk_index = content_blocks['transcript_segments'].get('chunk_index')
        
        if hour is not None and chunk_index is not None:
            cache_segment_translations_in_json(
                data.get('host_name'),
                hour,
                chunk_index,
                target_language,
                translated_segments
            )
    
    return jsonify(result)


def cache_segment_translations_in_json(host_name, hour, chunk_index, target_lang, translations):
    """
    Optional: Cache translations in transcript JSON for persistent storage
    """
    # Load transcript JSON
    transcript_path = f"/path/to/{host_name}/transcript/{hour}/chunk_10min_{chunk_index}.json"
    
    with open(transcript_path, 'r') as f:
        transcript_data = json.load(f)
    
    # Update segment translations
    if 'segments' in transcript_data:
        for i, translation in enumerate(translations):
            if i < len(transcript_data['segments']):
                if 'translations' not in transcript_data['segments'][i]:
                    transcript_data['segments'][i]['translations'] = {}
                transcript_data['segments'][i]['translations'][target_lang] = translation
    
    # Save atomically
    with open(transcript_path + '.tmp', 'w') as f:
        json.dump(transcript_data, f, indent=2, ensure_ascii=False)
    os.replace(transcript_path + '.tmp', transcript_path)
    
    print(f"✅ Cached {len(translations)} segment translations for {target_lang}")
```

## How Frontend Will Use This

### When User Changes Language:

1. **Existing `useRestart.translateToLanguage('es')` is called**
2. Frontend includes transcript segments in payload (if available from loaded transcript)
3. Backend translates everything in one batch (including segments)
4. Frontend stores `translationResults['es'].transcriptSegments = [...]`
5. When transcript is displayed, `useTranscriptPlayer` checks:
   - First: JSON cache (`segment.translations.es`)
   - Second: Parent cache (`externalTranslations['es'][segmentIndex]`)
   - Fallback: Original text

### Cache Strategy:

**In-Memory (Fast)**:
- Translations stored in `useRestart.translationResults`
- Lost on page reload
- Good for quick language switching

**Persistent (Optional Backend Enhancement)**:
- Translations saved in transcript JSON files
- Survives page reload
- Good for frequently accessed content

## Testing

### 1. Test Without Backend Changes
- Frontend will work with external translations from `useRestart`
- Translations NOT persisted to JSON
- Works for restart video analysis flow

### 2. Test With Backend Changes
- Full integration with persistent caching
- Translations survive page reload
- Works for archive/24h mode

## Benefits

✅ **No code duplication** - Reuses existing `/server/translate/restart-batch` endpoint  
✅ **Minimal changes** - Just extend existing endpoint with one more content block  
✅ **Backward compatible** - `transcript_segments` is optional  
✅ **Consistent** - Same translation API for all content  
✅ **Cacheable** - Can store in JSON or in-memory  

## Summary

**Frontend**: ✅ Complete - Ready to receive translated segments  
**Backend**: ⚠️ TODO - Add `transcript_segments` handling to existing batch endpoint  

**Estimated Backend Work**: 30-60 minutes (just extending existing function)

