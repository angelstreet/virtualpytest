# RESTORE PLAN: Copy Main Branch Analysis Reporting Exactly

## 🎯 **OBJECTIVE**
Restore the exact same analysis reporting functionality that existed in the main branch by copying the existing implementations.

---

## 📋 **CURRENT STATE ANALYSIS**

### ✅ **MOTION DETECTION - FIXED**
- **Status**: Working with 3 thumbnails + modal
- **Implementation**: Custom `motion_analysis_images` array with R2 upload
- **Display**: 120x80px thumbnails in chronological order

### ❌ **SUBTITLE DETECTION - NEEDS RESTORE**
- **Main Branch Had**: Single `analyzed_screenshot` thumbnail + modal
- **Current State**: No thumbnails, no modal
- **Location**: Lines 610-633 in `report_step_formatter.py`

### ❌ **AUDIO SPEECH DETECTION - NEEDS RESTORE** 
- **Main Branch Had**: Audio URLs display + transcript details
- **Current State**: Basic text display only
- **Location**: Lines 636-672 in `report_step_formatter.py`

### ❌ **AUDIO MENU ANALYSIS - NEEDS RESTORE**
- **Main Branch Had**: Single `analyzed_screenshot` thumbnail + modal
- **Current State**: No thumbnails, no modal  
- **Location**: Lines 708-732 in `report_step_formatter.py`

### ❌ **ZAPPING DETECTION - NEEDS RESTORE**
- **Main Branch Had**: 4-image sequence thumbnails + modal
- **Current State**: No thumbnails, no modal
- **Location**: Lines 769-824 in `report_step_formatter.py`

---

## 🔧 **RESTORATION TASKS**

### **TASK 1: SUBTITLE ANALYSIS RESTORE**

#### **Step 1.1: Add `analyzed_screenshot` to subtitle result**
```python
# In zap_executor.py _map_verification_result() - subtitle section
# Add analyzed_screenshot field to result.subtitle_details
result.subtitle_details['analyzed_screenshot'] = image_path_from_verification
# Add to context.screenshot_paths for R2 upload
```

#### **Step 1.2: Copy main branch display code**
```python
# In report_step_formatter.py lines 610-633
# Copy EXACTLY the existing subtitle screenshot display code:
analyzed_screenshot = subtitle_analysis.get('analyzed_screenshot')
if analyzed_screenshot:
    # ... exact copy of lines 612-633
```

#### **Step 1.3: Add R2 URL mapping**
```python
# In report_formatting.py update_step_results_with_r2_urls()
# Ensure 'analyzed_screenshot' field gets R2 URL mapping (already exists)
```

---

### **TASK 2: AUDIO SPEECH ANALYSIS RESTORE**

#### **Step 2.1: Add audio URLs to audio result**
```python
# In zap_executor.py _map_verification_result() - audio section  
# Add audio_urls field to result.audio_details
result.audio_details['audio_urls'] = audio_urls_from_verification
# Add audio files to context.screenshot_paths for R2 upload
```

#### **Step 2.2: Copy main branch display code**
```python
# In report_step_formatter.py lines 661-668
# Copy EXACTLY the existing audio URLs display code:
audio_urls = audio_analysis.get('audio_urls', [])
if audio_urls:
    # ... exact copy of lines 663-668
```

---

### **TASK 3: AUDIO MENU ANALYSIS RESTORE**

#### **Step 3.1: Add `analyzed_screenshot` to audio menu result**
```python
# In zap_executor.py _map_verification_result() - audio_menu section (if exists)
# Or in _analyze_audio_menu() method
# Add analyzed_screenshot field and R2 upload
```

#### **Step 3.2: Copy main branch display code**
```python
# In report_step_formatter.py lines 708-732
# Copy EXACTLY the existing audio menu screenshot display code:
analyzed_screenshot = audio_menu_analysis.get('analyzed_screenshot')
if analyzed_screenshot:
    # ... exact copy of lines 711-732
```

---

### **TASK 4: ZAPPING ANALYSIS RESTORE**

#### **Step 4.1: Add zapping sequence images to zapping result**
```python
# In zap_executor.py _map_verification_result() - zapping section
# Extract and add these fields to result.zapping_details:
# - first_image
# - blackscreen_start_image  
# - blackscreen_end_image
# - first_content_after_blackscreen
# Add all to context.screenshot_paths for R2 upload
```

#### **Step 4.2: Copy main branch display code**
```python
# In report_step_formatter.py lines 769-824
# Copy EXACTLY the existing zapping sequence display code:
before_blackscreen = zapping_analysis.get('first_image')
blackscreen_start = zapping_analysis.get('blackscreen_start_image')
# ... exact copy of lines 770-824
```

---

## 📁 **FILES TO MODIFY**

### **1. `shared/src/lib/executors/zap_executor.py`**
- **Method**: `_map_verification_result()`
- **Action**: Add missing fields to each analysis result
- **Add R2 Upload**: Ensure all image paths added to `context.screenshot_paths`

### **2. `shared/src/lib/utils/report_step_formatter.py`**
- **Method**: `format_analysis_results()`
- **Action**: Copy exact main branch display code for each analysis type
- **Lines**: 610-633 (subtitle), 661-668 (audio), 708-732 (audio menu), 769-824 (zapping)

### **3. `shared/src/lib/utils/report_formatting.py`**
- **Method**: `update_step_results_with_r2_urls()`
- **Action**: Verify all analysis fields get R2 URL mapping (likely already exists)

---

## 🎯 **IMPLEMENTATION STRATEGY**

### **Phase 1: Copy Display Code (No Backend Changes)**
1. **Copy exact HTML generation code** from main branch for each analysis type
2. **Test with dummy data** to ensure display works
3. **Verify modal functionality** works with existing JS

### **Phase 2: Add Backend Data (Minimal Changes)**
1. **Add missing fields** to each analysis result in `_map_verification_result()`
2. **Add R2 upload paths** to `context.screenshot_paths`
3. **Test end-to-end** with real analysis data

### **Phase 3: Verification & Cleanup**
1. **Compare with main branch** - ensure identical functionality
2. **Remove debug logs** added during motion detection fix
3. **Test all analysis types** work exactly like main branch

---

## ✅ **SUCCESS CRITERIA**

Each analysis type should have **IDENTICAL** functionality to main branch:

### **Subtitle Analysis:**
- ✅ Single thumbnail (60x40px) with filename label
- ✅ Modal with single image labeled "Analyzed for Subtitles"
- ✅ R2 URL for image display

### **Audio Speech Analysis:**
- ✅ Audio segment links (Segment 1, Segment 2, etc.)
- ✅ Clickable links to R2-hosted audio files
- ✅ Transcript preview in details

### **Audio Menu Analysis:**
- ✅ Single thumbnail (60x40px) with filename label  
- ✅ Modal with single image labeled "Analyzed for Audio Menu"
- ✅ R2 URL for image display

### **Zapping Analysis:**
- ✅ 4 thumbnails (55x37px) showing sequence progression
- ✅ Modal with 4 images: "Before Transition", "First Transition", "Last Transition", "First Content After"
- ✅ R2 URLs for all sequence images
- ✅ Proper labels with capture names and sequence descriptions

---

## 🚫 **WHAT NOT TO DO**

1. **Don't reinvent** - Copy existing code exactly
2. **Don't modify motion detection** - It's already working correctly  
3. **Don't change modal JS** - Existing `openVerificationImageModal()` works
4. **Don't change R2 upload logic** - Existing URL mapping works
5. **Don't add new features** - Just restore what existed

---

## 📝 **VALIDATION CHECKLIST**

- [ ] Subtitle analysis shows single thumbnail + modal
- [ ] Audio speech shows clickable audio segment links
- [ ] Audio menu shows single thumbnail + modal  
- [ ] Zapping shows 4-image sequence + modal
- [ ] All images load from R2 URLs (no broken links)
- [ ] All modals open correctly with proper titles
- [ ] Display matches main branch exactly (sizes, labels, layout)
- [ ] No console errors in browser
- [ ] All analysis types work together without conflicts

**GOAL**: Achieve 100% feature parity with main branch analysis reporting by copying existing implementations exactly.
