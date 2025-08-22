# Freeze Detection Feature for Zapping Analysis

## Overview
Add freeze detection capability to the existing zapping detection system with minimal code changes. The system will intelligently learn device zapping patterns and optimize detection methods accordingly.

## Problem Statement
Current zapping detection only handles blackscreen transitions. Some devices use freeze-frame zapping where the image freezes instead of going black during channel changes. This causes zapping detection to fail on freeze-only devices.

## Solution Approach
- **Minimal Changes**: Add freeze detection as fallback to existing blackscreen detection
- **Smart Learning**: Learn each device's zapping pattern (blackscreen vs freeze)
- **Adaptive Detection**: Use learned pattern to optimize detection method selection
- **Backward Compatible**: No API changes, same result format, no UI modifications

## Implementation Plan

### Phase 1: Add Device Learning to ZapController

#### 1.1 Device Pattern Memory
```python
# In ZapController.__init__()
self.device_zapping_patterns = {}  # NEW: Learn per device

def _get_device_pattern(self, device_id: str) -> Dict[str, Any]:
    """Get learned zapping pattern for device."""
    if device_id not in self.device_zapping_patterns:
        self.device_zapping_patterns[device_id] = {
            'primary_method': 'blackscreen',  # Start with blackscreen
            'success_count': {'blackscreen': 0, 'freeze': 0},
            'total_attempts': 0,
            'confidence': 0.0
        }
    return self.device_zapping_patterns[device_id]

def _update_device_pattern(self, device_id: str, successful_method: str):
    """Update learned pattern based on successful detection."""
    pattern = self._get_device_pattern(device_id)
    pattern['success_count'][successful_method] += 1
    pattern['total_attempts'] += 1
    
    # Switch to freeze as primary if it's more successful
    freeze_rate = pattern['success_count']['freeze'] / pattern['total_attempts']
    if freeze_rate > 0.6:
        pattern['primary_method'] = 'freeze'
        pattern['confidence'] = freeze_rate
```

#### 1.2 Smart Detection Method Selection
```python
# Modify existing _analyze_zapping() method
def _analyze_zapping(self, context, iteration: int, action_command: str, action_end_time: float = None):
    device_id = context.selected_device.device_id
    device_pattern = self._get_device_pattern(device_id)
    primary_method = device_pattern['primary_method']
    
    print(f"🧠 [ZapController] Smart detection: {primary_method} first")
    
    # Try primary method first
    if primary_method == 'freeze':
        result = self._try_freeze_detection(context, iteration, action_command, action_end_time)
        if not result.get('zapping_detected', False):
            result = self._try_blackscreen_detection(context, iteration, action_command, action_end_time)
    else:
        result = self._try_blackscreen_detection(context, iteration, action_command, action_end_time)
        if not result.get('zapping_detected', False):
            result = self._try_freeze_detection(context, iteration, action_command, action_end_time)
    
    # Update learning
    if result.get('zapping_detected', False):
        method = result.get('detection_method', primary_method)
        self._update_device_pattern(device_id, method)
    
    return result
```

### Phase 2: Split Detection Methods

#### 2.1 Extract Existing Blackscreen Logic
```python
def _try_blackscreen_detection(self, context, iteration: int, action_command: str, action_end_time: float):
    """Try blackscreen detection - extract existing logic."""
    try:
        print(f"⬛ [ZapController] Trying blackscreen detection...")
        
        # Move existing _analyze_zapping logic here
        # ... existing blackscreen detection code ...
        
        if result.get('success', False):
            result['detection_method'] = 'blackscreen'
            result['transition_type'] = 'blackscreen'
        
        return result
    except Exception as e:
        return {"success": False, "zapping_detected": False, "detection_method": "blackscreen"}
```

#### 2.2 Add New Freeze Detection Method
```python
def _try_freeze_detection(self, context, iteration: int, action_command: str, action_end_time: float):
    """Try freeze detection method."""
    try:
        print(f"🧊 [ZapController] Trying freeze detection...")
        
        device_id = context.selected_device.device_id
        video_controller = get_controller(device_id, 'verification_video')
        av_controller = get_controller(device_id, 'av')
        
        # Use same areas as blackscreen detection
        device_model = context.selected_device.device_model
        if device_model in ['android_mobile', 'ios_mobile']:
            analysis_rectangle = {'x': 475, 'y': 50, 'width': 325, 'height': 165}
            banner_region = {'x': 470, 'y': 230, 'width': 280, 'height': 70}
        else:
            analysis_rectangle = {'x': 300, 'y': 130, 'width': 1300, 'height': 570}
            banner_region = {'x': 245, 'y': 830, 'width': 1170, 'height': 120}
        
        # Call NEW freeze zapping detection
        freeze_result = video_controller.detect_freeze_zapping(
            folder_path=av_controller.video_capture_path,
            key_release_timestamp=context.last_action_start_time,
            analysis_rectangle=analysis_rectangle,
            banner_region=banner_region,
            max_images=10
        )
        
        if freeze_result.get('freeze_zapping_detected', False):
            return {
                "success": True,
                "zapping_detected": True,
                "detection_method": "freeze",
                "transition_type": "freeze",
                "blackscreen_duration": freeze_result.get('freeze_duration', 0.0),  # Same field name
                "zapping_duration": freeze_result.get('zapping_duration', 0.0),
                # ... copy other fields from freeze_result ...
            }
        
        return {"success": False, "zapping_detected": False, "detection_method": "freeze"}
        
    except Exception as e:
        return {"success": False, "zapping_detected": False, "detection_method": "freeze"}
```

### Phase 3: Add Freeze Detection to VideoVerificationController

#### 3.1 New detect_freeze_zapping() Method
```python
# In video.py - VideoVerificationController
def detect_freeze_zapping(self, folder_path: str, key_release_timestamp: float, 
                         analysis_rectangle: Dict[str, int] = None, 
                         banner_region: Dict[str, int] = None, 
                         max_images: int = 10) -> Dict[str, Any]:
    """Detect freeze-based zapping sequence."""
    try:
        print(f"VideoVerify[{self.device_name}]: Starting freeze zapping detection")
        
        # Call content helpers for freeze detection
        freeze_result = self.content_helpers.detect_freeze_zapping_sequence(
            folder_path, key_release_timestamp, analysis_rectangle, max_images, banner_region
        )
        
        if not freeze_result.get('success', False):
            return {
                'success': False,
                'freeze_zapping_detected': False,
                'freeze_duration': 0.0,
                'error': freeze_result.get('error', 'Unknown error')
            }
        
        # Extract channel info if available (same as blackscreen)
        channel_info = freeze_result.get('channel_info', {})
        
        success = freeze_result.get('freeze_zapping_detected', False)
        freeze_duration = freeze_result.get('freeze_duration', 0.0)
        
        return {
            'success': success,
            'freeze_zapping_detected': success,
            'freeze_duration': freeze_duration,
            'zapping_duration': freeze_result.get('zapping_duration', 0.0),
            'first_image': freeze_result.get('first_image'),
            'freeze_start_image': freeze_result.get('freeze_start_image'),
            'freeze_end_image': freeze_result.get('freeze_end_image'),
            'first_content_after_freeze': freeze_result.get('first_content_after_freeze'),
            'channel_info': channel_info,
            'analyzed_images': freeze_result.get('analyzed_images', 0),
            'analysis_type': 'freeze_zapping_detection'
        }
        
    except Exception as e:
        return {
            'success': False,
            'freeze_zapping_detected': False,
            'freeze_duration': 0.0,
            'error': str(e)
        }
```

### Phase 4: Add Freeze Detection to VideoContentHelpers

#### 4.1 New detect_freeze_zapping_sequence() Method
```python
# In video_content_helpers.py
def detect_freeze_zapping_sequence(self, folder_path: str, key_release_timestamp: float, 
                                  analysis_rectangle: Dict[str, int] = None, max_images: int = 10, 
                                  banner_region: Dict[str, int] = None) -> Dict[str, Any]:
    """Detect freeze-based zapping sequence."""
    try:
        print(f"VideoContent[{self.device_name}]: Starting freeze zapping detection")
        
        # Step 1: Get images after timestamp (reuse existing logic)
        image_data = self._get_images_after_timestamp(folder_path, key_release_timestamp, max_images)
        
        if not image_data:
            return {
                'success': False,
                'error': 'No images found after key release timestamp',
                'freeze_zapping_detected': False,
                'freeze_duration': 0.0
            }
        
        # Step 2: Detect freeze sequence using existing freeze detection
        freeze_results = self._detect_freeze_batch(image_data, analysis_rectangle)
        
        # Step 3: Find freeze sequence pattern
        sequence = self._find_freeze_sequence(freeze_results)
        
        if sequence.get('freeze_detected', False):
            # Calculate durations
            freeze_duration = sequence.get('freeze_duration', 0.0)
            zapping_duration = sequence.get('zapping_duration', 0.0)
            
            return {
                'success': True,
                'freeze_zapping_detected': True,
                'freeze_duration': freeze_duration,
                'zapping_duration': zapping_duration,
                'freeze_start_image': sequence.get('freeze_start_image'),
                'freeze_end_image': sequence.get('freeze_end_image'),
                'first_content_after_freeze': sequence.get('first_content_after_freeze'),
                'analyzed_images': len(image_data),
                'analysis_type': 'freeze_zapping_detection'
            }
        
        return {
            'success': False,
            'freeze_zapping_detected': False,
            'freeze_duration': 0.0,
            'error': 'No freeze sequence detected'
        }
        
    except Exception as e:
        return {
            'success': False,
            'freeze_zapping_detected': False,
            'freeze_duration': 0.0,
            'error': str(e)
        }
```

#### 4.2 Helper Methods for Freeze Detection
```python
def _detect_freeze_batch(self, image_data: List[Dict], analysis_rectangle: Dict = None) -> Dict[str, Any]:
    """Detect freeze frames in batch - reuse existing freeze detection."""
    
    # Convert to image paths
    image_paths = [item['path'] for item in image_data]
    
    # Crop to analysis rectangle if provided
    if analysis_rectangle:
        cropped_paths = self._crop_images_to_rectangle(image_paths, analysis_rectangle)
        image_paths = cropped_paths
    
    # Use existing freeze detection
    freeze_result = self.detect_freeze_in_images(image_paths, freeze_threshold=1.0)
    
    return {
        'success': freeze_result.get('success', False),
        'freeze_detected': freeze_result.get('freeze_detected', False),
        'comparisons': freeze_result.get('comparisons', []),
        'analyzed_images': len(image_paths)
    }

def _find_freeze_sequence(self, freeze_results: Dict[str, Any]) -> Dict[str, Any]:
    """Find freeze sequence pattern - mirror of blackscreen logic."""
    
    comparisons = freeze_results.get('comparisons', [])
    
    if not comparisons:
        return {'freeze_detected': False}
    
    # Find first frozen frame and first non-frozen frame
    freeze_start_idx = None
    freeze_end_idx = None
    
    for i, comp in enumerate(comparisons):
        if comp.get('is_frozen', False) and freeze_start_idx is None:
            freeze_start_idx = i
        elif not comp.get('is_frozen', False) and freeze_start_idx is not None:
            freeze_end_idx = i
            break
    
    if freeze_start_idx is not None:
        # Calculate duration (same logic as blackscreen)
        start_frame = comparisons[freeze_start_idx]['frame1']
        end_frame = comparisons[freeze_end_idx]['frame2'] if freeze_end_idx else comparisons[-1]['frame2']
        
        # Extract timestamps and calculate duration
        # ... duration calculation logic similar to blackscreen ...
        
        return {
            'freeze_detected': True,
            'freeze_start_image': start_frame,
            'freeze_end_image': end_frame,
            'first_content_after_freeze': end_frame,
            'freeze_duration': calculated_duration,
            'zapping_duration': calculated_duration
        }
    
    return {'freeze_detected': False}
```

### Phase 5: Enhanced Statistics and Display

#### 5.1 Update ZapStatistics
```python
# In ZapStatistics class
def __init__(self):
    # ... existing fields ...
    self.freeze_zapping_detected_count = 0  # NEW
    self.detection_methods_used = []  # NEW: track which method was used

def add_zapping_result(self, zapping_details: Dict[str, Any]):
    # ... existing logic ...
    
    # Track detection method
    detection_method = zapping_details.get('detection_method', 'blackscreen')
    self.detection_methods_used.append(detection_method)
    
    if detection_method == 'freeze':
        self.freeze_zapping_detected_count += 1

def print_summary(self, action_command: str):
    # ... existing output ...
    
    # Show detection method breakdown
    blackscreen_count = self.detection_methods_used.count('blackscreen')
    freeze_count = self.detection_methods_used.count('freeze')
    
    if blackscreen_count > 0:
        print(f"   ⬛ Blackscreen zapping: {blackscreen_count}/{self.total_iterations}")
    if freeze_count > 0:
        print(f"   🧊 Freeze zapping: {freeze_count}/{self.total_iterations}")
```

#### 5.2 Update Display Messages
```python
# In _try_freeze_detection() and _try_blackscreen_detection()
if zapping_detected:
    transition_type = result.get('transition_type', 'blackscreen')
    duration = result.get('blackscreen_duration', 0.0)  # Same field name for compatibility
    
    if transition_type == 'freeze':
        print(f"✅ [ZapController] Freeze zapping detected - Duration: {duration}s")
    else:
        print(f"✅ [ZapController] Blackscreen zapping detected - Duration: {duration}s")
```

## Code Changes Summary

### Files to Modify:
1. **`shared/lib/utils/zap_controller.py`** (~100 lines added)
   - Add device learning logic
   - Split detection methods
   - Update statistics tracking

2. **`backend_core/src/controllers/verification/video.py`** (~50 lines added)
   - Add `detect_freeze_zapping()` method

3. **`backend_core/src/controllers/verification/video_content_helpers.py`** (~80 lines added)
   - Add `detect_freeze_zapping_sequence()` method
   - Add `_detect_freeze_batch()` method
   - Add `_find_freeze_sequence()` method

### Total Code Addition: ~230 lines

## Benefits

### ✅ **Smart Efficiency**
- Learn device patterns after 3-5 zaps
- Skip unnecessary detection methods
- 50% faster detection for learned devices

### ✅ **Minimal Changes**
- No API changes
- Same result format (uses `blackscreen_duration` field for both types)
- No UI modifications needed
- Backward compatible

### ✅ **Better Detection**
- Handle both blackscreen and freeze zapping
- Automatic fallback detection
- Clear indication of detection method used

### ✅ **User Experience**
- Transparent learning process
- Better success rates across all devices
- Clear logging shows which method worked

## Testing Plan

### Test Scenarios:
1. **Blackscreen-only devices**: Verify blackscreen detection still works
2. **Freeze-only devices**: Verify freeze detection works and becomes primary
3. **Mixed devices**: Verify learning adapts to most successful method
4. **Fallback scenarios**: Verify fallback works when primary method fails

### Success Criteria:
- Blackscreen detection: Maintain >95% accuracy
- Freeze detection: Achieve >90% accuracy  
- Learning: Switch to optimal method within 5 attempts
- Performance: <20% overhead for dual detection

## Implementation Timeline

### Week 1: Core Implementation
- Add device learning to ZapController
- Split detection methods
- Add freeze detection to VideoVerificationController

### Week 2: Integration & Testing  
- Add freeze detection to VideoContentHelpers
- Update statistics and display
- Test with real freeze zapping scenarios
- Validate backward compatibility

This minimal approach adds freeze detection capability while maintaining all existing functionality and optimizing performance through smart learning.
