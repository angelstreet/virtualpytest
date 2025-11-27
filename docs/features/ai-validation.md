# 🤖 AI-Powered Validation

**Smart verification without brittle selectors.**

AI-driven OCR, image recognition, and content detection that validates what users actually see, not what the DOM says.

---

## The Problem

Traditional test automation breaks easily:
- ❌ CSS selectors change → tests fail
- ❌ Element IDs renamed → tests fail
- ❌ UI updated → tests fail
- ❌ Content loads slowly → false negatives
- ❌ Dynamic content → unreliable assertions

---

## The VirtualPyTest Solution

✅ **Visual verification** - Validate what's actually on screen  
✅ **OCR text detection** - Find text anywhere, no selectors needed  
✅ **Smart image matching** - Fuzzy matching handles minor variations  
✅ **Content-aware** - Understands context, not just pixels  
✅ **Self-healing** - Adapts to minor UI changes  

---

## Core Capabilities

### 🔍 Text Recognition (OCR)

**Detect text anywhere on screen - no DOM access needed.**

```python
# Verify subtitle text appears
controller.verify_text(
    text="Hello World",
    region=(0, 800, 1920, 1080),  # Bottom third of screen
    confidence=0.8
)
```

**Use cases:**
- Subtitle validation on video players
- Menu text verification on STBs
- Error message detection
- App name confirmation
- Any text-based validation

**Technology:**
- Tesseract OCR engine
- OpenCV preprocessing
- Multi-language support
- Configurable confidence thresholds

---

### 🖼️ Image Detection

**Find UI elements visually, no IDs required.**

```python
# Find the "Play" button by image
controller.verify_image(
    reference="play_button.png",
    threshold=0.9,  # 90% similarity
    timeout=10
)
```

**Features:**
- Template matching
- Multi-scale detection
- Rotation tolerance
- Fuzzy matching for variations

**Use cases:**
- Logo detection
- Button verification
- Icon matching
- UI element validation

---

### 📊 Content Analysis

**Understand what's on screen, not just detect it.**

#### Black Screen Detection

```python
# Detect if video playback has failed
detector.detect_black_screen(
    stream="/dev/video0",
    threshold=10,        # Max brightness
    min_duration=3,      # Black for 3+ seconds
    alert=True
)
```

#### Freeze Detection

```python
# Detect if video has frozen
detector.detect_freeze(
    stream="/dev/video0",
    similarity=0.98,     # 98% identical frames
    min_duration=5,      # Frozen for 5+ seconds
    alert=True
)
```

#### Color Analysis

```python
# Verify expected content by color distribution
detector.analyze_colors(
    expected_palette=["blue", "white", "red"],
    tolerance=0.1
)
```

---

## Advanced AI Features

### 🧠 Smart Comparison

**Compare images intelligently, not pixel-by-pixel.**

```python
# Fuzzy image comparison
result = ai_analyzer.compare_images(
    expected="expected_screen.png",
    actual=controller.capture_screenshot(),
    ignore_regions=[
        (10, 10, 100, 50),    # Clock area (changes)
        (1800, 10, 1900, 50)  # Battery indicator
    ],
    threshold=0.92
)
```

**Handles:**
- Minor color variations
- Timestamp differences
- Dynamic content (ads, recommendations)
- Lighting changes
- Resolution differences

---

### 📝 Natural Language Verification

**Describe what you expect in plain English.**

```python
# AI understands intent
controller.verify_screen_contains(
    description="Netflix home screen with user profile visible",
    confidence=0.85
)
```

**Powered by:**
- OpenRouter API integration
- GPT-4 Vision
- Claude Sonnet Vision
- Custom prompt engineering

---

### 🎯 Smart Element Detection

**AI finds elements without training.**

```python
# Find and click the login button
element = ai_analyzer.find_element(
    description="blue rectangular login button",
    screenshot=controller.capture_screenshot()
)

controller.click_at(element.x, element.y)
```

---

## Real-World Examples

### Subtitle Validation

```python
# Verify subtitles appear and are correct
from shared.src.services.subtitle_detector import SubtitleDetector

detector = SubtitleDetector(device="android_tv_1")

# Detect subtitle text in video stream
result = detector.detect_text(
    region="bottom_third",  # Subtitle area
    expected_texts=["Hello", "world"],
    language="eng",
    timeout=10
)

if result.found:
    print(f"✅ Subtitles detected: {result.text}")
else:
    print(f"❌ Subtitles missing or unreadable")
```

---

### Content Verification

```python
# Verify Netflix app loaded correctly
from shared.src.services.ai_analyzer import AIAnalyzer

analyzer = AIAnalyzer()

screenshot = controller.capture_screenshot()

# AI checks multiple aspects
checks = analyzer.verify_app_loaded(
    screenshot=screenshot,
    expected_app="Netflix",
    checks=[
        "logo_visible",
        "navigation_menu_present",
        "content_thumbnails_loaded",
        "no_error_messages"
    ]
)

for check, passed in checks.items():
    status = "✅" if passed else "❌"
    print(f"{status} {check}")
```

---

### Visual Regression

```python
# Detect UI changes between releases
from shared.src.services.visual_regression import VisualRegression

regression = VisualRegression()

# Compare against baseline
result = regression.compare(
    baseline="baseline_v1.2_home_screen.png",
    current=controller.capture_screenshot(),
    ignore_dynamic_content=True,
    generate_diff=True  # Creates visual diff image
)

if result.changed:
    print(f"⚠️ UI changed by {result.difference_percent}%")
    print(f"View diff: {result.diff_image_path}")
else:
    print("✅ UI unchanged")
```

---

## Configuration

### OCR Settings

```yaml
ocr:
  engine: "tesseract"
  languages: ["eng", "fra", "spa"]
  preprocessing:
    - "grayscale"
    - "threshold"
    - "denoise"
  confidence_threshold: 0.7
```

### AI Model Configuration

```yaml
ai:
  provider: "openrouter"
  model: "anthropic/claude-3.5-sonnet"
  vision_model: "anthropic/claude-3.5-sonnet"
  max_tokens: 4000
  temperature: 0.1  # Low temperature for consistent results
```

### Detection Thresholds

```yaml
detection:
  black_screen_threshold: 10      # Brightness level
  freeze_similarity: 0.98         # Frame similarity
  text_confidence: 0.8            # OCR confidence
  image_match_threshold: 0.9      # Template matching
```

---

## Performance Optimization

### Caching

```python
# Cache OCR results for faster re-validation
controller.verify_text(
    text="Settings",
    cache=True,           # Cache result for 30s
    cache_duration=30
)
```

### Region-Specific Detection

```python
# Only analyze relevant screen regions
controller.verify_text(
    text="Volume",
    region=(0, 0, 400, 200),  # Top-left corner only
    # Much faster than full-screen OCR
)
```

### Parallel Processing

```python
# Check multiple conditions simultaneously
results = await asyncio.gather(
    controller.verify_text_async("Play"),
    controller.verify_text_async("Pause"),
    controller.verify_image_async("logo.png")
)
```

---

## Benefits

### 🚀 Faster Test Creation
No need to find selectors or element IDs. Describe what you see and validate it.

### 💪 More Resilient Tests
Tests don't break when developers change class names or restructure the DOM.

### 🎯 Real User Validation
Verify what users actually see, not what the code says should be there.

### 🔍 Better Debugging
Visual diffs and OCR results show exactly what went wrong.

---

## Integration with Test Framework

### Pytest Integration

```python
import pytest
from shared.src.services.ai_validator import AIValidator

@pytest.fixture
def validator():
    return AIValidator()

def test_netflix_home_screen(controller, validator):
    controller.navigate_to("netflix")
    
    screenshot = controller.capture_screenshot()
    
    # AI validates the screen
    assert validator.verify_text(screenshot, "Netflix")
    assert validator.verify_element(screenshot, "user profile icon")
    assert validator.no_errors_visible(screenshot)
```

---

## Monitoring Integration

### Continuous Validation

```python
# Monitor content 24/7
monitor = ContentMonitor(device="living_room_tv")

monitor.add_check(
    name="subtitles_present",
    interval=60,  # Check every minute
    validator=lambda: detector.detect_subtitle_text()
)

monitor.add_check(
    name="no_black_screen",
    interval=10,  # Check every 10 seconds
    validator=lambda: not detector.detect_black_screen()
)

monitor.start()
```

---

## Next Steps

- 📖 [Visual Capture](./visual-capture.md) - Capture what AI validates
- 📖 [Analytics](./analytics.md) - Track validation metrics
- 📚 [User Guide - Validation](../user-guide/running-tests.md#validation)
- 🔧 [Technical Docs - AI Architecture](../technical/ai/README.md)

---

**Ready to validate with AI?**  
➡️ [Get Started](../get-started/quickstart.md)

