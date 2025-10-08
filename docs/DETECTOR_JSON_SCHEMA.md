# Detector JSON Output Schema

## **Current Schema** (detector.py v1)

```json
{
  "timestamp": "2025-10-08T15:23:45.123456",
  "filename": "capture_001234.jpg",
  "blackscreen": false,
  "blackscreen_percentage": 23.3,
  "freeze": false,
  "freeze_diffs": [0.5, 1.2, 0.8],
  "last_3_filenames": ["/path/capture_001232.jpg", "..."],
  "last_3_thumbnails": ["/path/capture_001232_thumbnail.jpg", "..."],
  "macroblocks": false,
  "quality_score": 98.5,
  "audio": true,
  "volume_percentage": 45,
  "mean_volume_db": -23.5,
  "performance_ms": {
    "image_load": 0.5,
    "blackscreen": 0.09,
    "freeze": 5.0,
    "macroblocks": 3.2,
    "audio": 0.1,
    "audio_cached": true,
    "subtitles": 0.0,
    "total": 8.9
  },
  "subtitle_analysis": {
    "has_subtitles": true,
    "extracted_text": "It's time to ride",
    "detected_language": "en",
    "confidence": 0.9
  }
}
```

---

## **New Schema** (detector.py v2 - ENHANCED)

### **✅ Backward Compatible** - All existing fields preserved

```json
{
  "timestamp": "2025-10-08T15:23:45.123456",
  "filename": "capture_001234.jpg",
  
  // ===== BLACKSCREEN (Enhanced) =====
  "blackscreen": false,
  "blackscreen_percentage": 23.3,
  "blackscreen_threshold": 10,           // NEW - threshold used
  "blackscreen_region": "5-70%",         // NEW - region analyzed
  
  // ===== ZAP DETECTION (NEW) =====
  "zap": false,                          // NEW - confirmed zapping
  "has_bottom_content": false,           // NEW - banner/channel info detected
  "bottom_edge_density": 0.0,            // NEW - edge density in bottom 30%
  
  // ===== FREEZE (Unchanged) =====
  "freeze": false,
  "freeze_diffs": [0.5, 1.2, 0.8],
  "last_3_filenames": ["/path/capture_001232.jpg", "..."],
  "last_3_thumbnails": ["/path/capture_001232_thumbnail.jpg", "..."],
  
  // ===== MACROBLOCKS (Unchanged) =====
  "macroblocks": false,
  "quality_score": 98.5,
  
  // ===== AUDIO (Unchanged) =====
  "audio": true,
  "volume_percentage": 45,
  "mean_volume_db": -23.5,
  
  // ===== SUBTITLES (Enhanced) =====
  "subtitle_analysis": {
    "has_subtitles": true,
    "extracted_text": "It's time to ride",
    "detected_language": "en",
    "confidence": 1.0,
    
    // NEW FIELDS
    "box": {                             // NEW - OCR region coordinates
      "x": 330,
      "y": 523,
      "width": 623,
      "height": 124
    },
    "ocr_method": "edge_based_box_detection",  // NEW - detection method
    "downscaled_to_height": 80,          // NEW - optimization applied
    "psm_mode": 6,                       // NEW - tesseract mode used
    "subtitle_edge_density": 2.2,        // NEW - edge density in subtitle area
    "skipped": false,                    // NEW - was OCR skipped?
    "skip_reason": null                  // NEW - why skipped (e.g., "zap", "no_edges")
  },
  
  // ===== PERFORMANCE (Enhanced) =====
  "performance_ms": {
    "image_load": 0.5,
    "edge_detection": 1.5,               // NEW - core edge detection
    "blackscreen": 0.09,
    "zap": 0.1,                          // NEW - bottom content check
    "subtitle_area_check": 0.04,         // NEW - subtitle area detection
    "subtitle_ocr": 152.0,               // NEW - actual OCR time
    "freeze": 5.0,
    "macroblocks": 3.2,
    "audio": 0.1,
    "audio_cached": true,
    "subtitles": 0.0,                    // DEPRECATED - use subtitle_ocr
    "total": 162.5
  }
}
```

---

## **Frontend Impact Analysis**

### **1. useMonitoring.ts** ✅ No Breaking Changes
**Location**: `frontend/src/hooks/monitoring/useMonitoring.ts`

**Current Usage** (lines 77-93):
```typescript
const parsed: MonitoringAnalysis = {
  timestamp: data.timestamp || '',
  filename: data.filename || '',
  blackscreen: data.blackscreen ?? false,
  blackscreen_percentage: data.blackscreen_percentage ?? 0,
  freeze: data.freeze ?? false,
  freeze_diffs: data.freeze_diffs || [],
  last_3_filenames: data.last_3_filenames || [],
  last_3_thumbnails: data.last_3_thumbnails || [],
  audio: data.audio ?? false,
  volume_percentage: data.volume_percentage ?? 0,
  mean_volume_db: data.mean_volume_db ?? -100,
  macroblocks: data.macroblocks ?? false,
  quality_score: data.quality_score ?? 0,
  has_incidents: data.has_incidents ?? false,
};
```

**Impact**: ✅ **NONE** - All used fields are preserved
**New fields available**:
- `data.zap` - for zapping detection
- `data.blackscreen_threshold` - for debugging
- `data.subtitle_analysis.box` - for visual overlay
- `data.subtitle_analysis.skip_reason` - for debugging

---

### **2. useHeatmap.ts** ✅ No Breaking Changes
**Location**: `frontend/src/hooks/useHeatmap.ts`

**Current Usage** (lines 28-42):
```typescript
analysis_json: {
  audio?: boolean;
  blackscreen?: boolean;
  freeze?: boolean;
  volume_percentage?: number;
  mean_volume_db?: number;
  freeze_diffs?: number[];
  last_3_thumbnails?: string[];
  r2_images?: {...}
}
```

**Impact**: ✅ **NONE** - All used fields are preserved
**New fields available**:
- `analysis_json.zap` - for zapping incidents
- `analysis_json.subtitle_analysis` - for subtitle overlay

---

### **3. Video AI Helpers** ⚠️ Subtitle Analysis Structure
**Location**: `backend_host/src/controllers/verification/video_ai_helpers.py`

**Current Structure** (lines 618-624):
```python
subtitle_result = {
    'subtitles_detected': bool(...),
    'combined_extracted_text': str(...),
    'detected_language': str(...),
    'confidence': float(...),
    'detection_message': str(...)
}
```

**New Structure** (detector.py):
```python
subtitle_result = {
    'has_subtitles': bool(...),        # DIFFERENT KEY
    'extracted_text': str(...),        # DIFFERENT KEY
    'detected_language': str(...),     # SAME
    'confidence': float(...),          # SAME
    'box': {...},                      # NEW
    'ocr_method': str(...),            # NEW
    ...
}
```

**Impact**: ⚠️ **REQUIRES MAPPING**
- Frontend expects `has_subtitles` (from detector.py)
- AI helpers use `subtitles_detected` (different key)
- Both structures are used in different contexts

**Solution**: Keep both structures separate (AI vs OCR-based subtitles)

---

## **Migration Plan**

### **Phase 1**: Implement optimized workflow ✅
- Move functions from `test_detector.py` → `video_content_helpers.py`
- Add edge detection, zap detection, box-based OCR
- Preserve all existing functions (no deletions)

### **Phase 2**: Update detector.py output ✅
- Add new fields to JSON (backward compatible)
- Keep all existing fields
- Enhanced `subtitle_analysis` structure

### **Phase 3**: Frontend enhancements (Optional) 🔜
- Display zap detection in monitoring UI
- Show subtitle boxes visually
- Add performance metrics display

### **Phase 4**: Documentation ✅
- Create `detector.md` with full workflow
- Document all JSON fields
- Provide migration guide

---

## **Backward Compatibility Guarantee**

✅ **All existing flat fields preserved**
✅ **Frontend parsing code unchanged**
✅ **New fields are additive only**
✅ **Optional fields use null-safe defaults**
✅ **Performance metrics remain in same structure**

**No frontend changes required for basic functionality**

