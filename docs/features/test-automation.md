# 🧪 Test Automation

**Low-code automation for powerful testing.**

Python-based test automation with intuitive navigation trees and visual test builder. Designed for QA teams without requiring deep coding expertise.

---

## The Problem

Traditional test automation requires:
- ❌ Programming expertise
- ❌ Complex framework setup
- ❌ Brittle scripts that break easily
- ❌ Steep learning curve for QA teams

---

## The VirtualPyTest Solution

✅ **Low-code approach** - Focus on what to test, not how  
✅ **Navigation trees** - Visual representation of app structure  
✅ **Reusable components** - Build once, use everywhere  
✅ **Python-based** - Powerful yet accessible  
✅ **Web interface** - Create and run tests from browser  

---

## Core Concepts

### 📍 Navigation Nodes

**Define where things are in your app.**

```python
# Navigation tree structure
navigation_tree = {
    "home": {
        "path": ["HOME"],
        "children": ["settings", "netflix", "youtube"]
    },
    "settings": {
        "path": ["HOME", "DOWN", "DOWN", "SELECT"],
        "verification": "text:Settings"
    },
    "netflix": {
        "path": ["HOME", "RIGHT", "RIGHT", "SELECT"],
        "verification": "image:netflix_logo.png"
    }
}
```

**Benefits:**
- Centralized app navigation logic
- Easy updates when UI changes
- Reusable across tests
- Visual graph representation

---

### 🧩 Test Cases

**Combine actions into reusable test scenarios.**

```python
# Simple test case
test_case = {
    "name": "Launch Netflix",
    "steps": [
        {"action": "navigate_to", "target": "home"},
        {"action": "navigate_to", "target": "netflix"},
        {"action": "verify_text", "text": "Netflix"},
        {"action": "screenshot", "name": "netflix_home"}
    ]
}
```

**Features:**
- Step-by-step execution
- Automatic verification
- Screenshot capture
- Error handling
- Retry logic

---

### 📋 Test Campaigns

**Run multiple tests in batches.**

```python
campaign = {
    "name": "Nightly Regression",
    "devices": ["android_tv_1", "android_tv_2"],
    "test_cases": [
        "launch_netflix",
        "launch_youtube",
        "settings_navigation",
        "channel_zapping"
    ],
    "schedule": "0 2 * * *"  # Run at 2 AM daily
}
```

---

## Web Interface

### 🖥️ Visual Test Builder

**Create tests without writing code.**

1. **Drag and drop actions** from palette
2. **Configure parameters** in sidebar
3. **Preview navigation** in real-time
4. **Save and execute** immediately

**Available actions:**
- Navigate to node
- Press key
- Enter text
- Verify text/image
- Wait for condition
- Take screenshot
- Custom Python code

---

### 🎯 Test Execution Interface

**Run tests from the browser.**

**Features:**
- Select device or multiple devices
- Choose test case or campaign
- Watch live execution
- View real-time logs
- See screenshots as they're captured
- Stop/pause execution

---

## Python Test Scripts

### Simple Navigation Test

```python
from shared.src.controller_factory import ControllerFactory

# Get device controller
controller = ControllerFactory.get_controller(device="android_tv_1")

# Navigate using tree
controller.navigate_to("netflix")

# Verify we arrived
assert controller.verify_text("Netflix")

# Take evidence
screenshot = controller.capture_screenshot()

print("✅ Test passed!")
```

---

### Advanced Test Example

```python
from shared.src.services.test_executor import TestExecutor

def test_netflix_playback():
    """Test Netflix app launches and plays content."""
    
    executor = TestExecutor(device="android_tv_1")
    
    # Navigate to Netflix
    executor.navigate("netflix")
    executor.verify_screen("netflix_home")
    
    # Search for content
    executor.press_key("SEARCH")
    executor.enter_text("Stranger Things")
    executor.press_key("SELECT")
    
    # Verify search results
    executor.wait_for_text("Stranger Things", timeout=10)
    executor.screenshot("search_results")
    
    # Play content
    executor.press_key("SELECT")  # Select first result
    executor.press_key("SELECT")  # Press Play
    
    # Verify playback started
    executor.wait_for_playback(timeout=15)
    assert not executor.detect_black_screen()
    assert not executor.detect_freeze()
    
    executor.screenshot("playback_started")
    
    return executor.get_results()
```

---

## Navigation Tree Management

### Create Navigation Trees

**Via Web Interface:**
1. Go to **Interface** section
2. Select your model
3. Click **Add Node**
4. Define path and verification
5. Connect nodes visually

**Via JSON:**
```json
{
  "nodes": [
    {
      "id": "home",
      "label": "Home Screen",
      "path": ["HOME"],
      "verification": {
        "type": "text",
        "value": "Home"
      }
    },
    {
      "id": "settings",
      "label": "Settings",
      "path": ["HOME", "DOWN", "DOWN", "SELECT"],
      "parent": "home",
      "verification": {
        "type": "image",
        "value": "settings_icon.png"
      }
    }
  ]
}
```

---

### Navigation Strategies

**Shortest Path:**
```python
# Automatically finds shortest route
controller.navigate_to("deep_nested_menu")
# Calculates optimal path through navigation tree
```

**Breadcrumb Navigation:**
```python
# Track navigation history
controller.navigate_to("settings")
controller.navigate_to("audio_settings")
controller.go_back()  # Returns to settings
controller.go_home()  # Returns to home
```

---

## Campaign Management

### Create Campaigns

```python
from shared.src.services.campaign_manager import CampaignManager

manager = CampaignManager()

campaign = manager.create_campaign(
    name="Streaming Apps Validation",
    test_cases=[
        "tc_001_netflix",
        "tc_002_youtube",
        "tc_003_hulu"
    ],
    devices=[
        "android_tv_living_room",
        "android_tv_bedroom"
    ],
    execution_mode="parallel",  # or "sequential"
    retry_failed=True,
    max_retries=2
)

# Schedule for later
manager.schedule(campaign, cron="0 2 * * *")

# Or run immediately
results = manager.execute(campaign)
```

---

### Campaign Results

**Comprehensive reporting:**
- Overall pass/fail rate
- Per-device results
- Per-test-case results
- Execution duration
- Screenshots and logs
- Failure analysis

---

## Verification Methods

### Text Verification

```python
# Simple text check
controller.verify_text("Expected Text")

# With region
controller.verify_text(
    "Subtitles",
    region=(0, 800, 1920, 1080)  # Bottom of screen
)

# With timeout
controller.verify_text(
    "Loading complete",
    timeout=30,
    poll_interval=1
)
```

---

### Image Verification

```python
# Exact match
controller.verify_image("play_button.png")

# Fuzzy match
controller.verify_image(
    "netflix_logo.png",
    threshold=0.85  # 85% similarity
)

# Multiple templates
controller.verify_any_image([
    "play_icon_v1.png",
    "play_icon_v2.png"
])
```

---

### Screen State Verification

```python
# Verify screen is not black
assert not controller.detect_black_screen()

# Verify video is playing (not frozen)
assert not controller.detect_freeze()

# Verify specific color present
assert controller.detect_color("blue", threshold=0.1)

# AI-powered verification
controller.verify_screen_state(
    description="Netflix home screen with recommendations"
)
```

---

## Reusable Test Components

### Test Fixtures

```python
import pytest
from shared.src.controller_factory import ControllerFactory

@pytest.fixture
def tv_controller():
    """Reusable TV controller fixture."""
    controller = ControllerFactory.get_controller("android_tv_1")
    yield controller
    controller.go_home()  # Cleanup
    controller.disconnect()

def test_app_launch(tv_controller):
    tv_controller.navigate_to("netflix")
    assert tv_controller.verify_text("Netflix")
```

---

### Page Objects

```python
class NetflixHomePage:
    """Page object for Netflix home screen."""
    
    def __init__(self, controller):
        self.controller = controller
        
    def navigate_here(self):
        self.controller.navigate_to("netflix")
        
    def search(self, query):
        self.controller.press_key("SEARCH")
        self.controller.enter_text(query)
        self.controller.press_key("SELECT")
        
    def verify_loaded(self):
        return self.controller.verify_text("Netflix")

# Use in tests
def test_search():
    netflix = NetflixHomePage(controller)
    netflix.navigate_here()
    netflix.search("Stranger Things")
    # ... assertions ...
```

---

## Test Data Management

### External Test Data

```python
import yaml

# Load test data from file
with open("test_data/streaming_apps.yml") as f:
    test_data = yaml.safe_load(f)

# Use in tests
for app in test_data["apps"]:
    controller.navigate_to(app["node"])
    controller.verify_text(app["expected_text"])
```

**test_data/streaming_apps.yml:**
```yaml
apps:
  - name: "Netflix"
    node: "netflix"
    expected_text: "Netflix"
  - name: "YouTube"
    node: "youtube"
    expected_text: "YouTube"
```

---

## Parallel Execution

### Run Tests Concurrently

```python
from concurrent.futures import ThreadPoolExecutor

devices = ["android_tv_1", "android_tv_2", "android_tv_3"]

def run_test_on_device(device):
    controller = ControllerFactory.get_controller(device)
    # ... test logic ...
    return results

# Execute on all devices simultaneously
with ThreadPoolExecutor(max_workers=3) as executor:
    results = executor.map(run_test_on_device, devices)
```

---

## CI/CD Integration

### Jenkins

```groovy
stage('VirtualPyTest Tests') {
    steps {
        sh '''
            cd virtualpytest
            source venv/bin/activate
            python test_scripts/validation.py --device android_tv_1
        '''
    }
    post {
        always {
            publishHTML([
                reportDir: 'test_results',
                reportFiles: 'report.html',
                reportName: 'VirtualPyTest Report'
            ])
        }
    }
}
```

---

### GitHub Actions

```yaml
name: VirtualPyTest Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run Tests
        run: |
          python test_scripts/fullzap.py --max_iteration 10
      - name: Upload Results
        uses: actions/upload-artifact@v2
        with:
          name: test-results
          path: test_results/
```

---

## Benefits

### 🚀 Faster Test Creation
Visual tools and reusable components reduce test creation time by 80%.

### 💪 Lower Maintenance
Navigation trees mean updating one place updates all tests.

### 🎯 Better Coverage
Easy test creation leads to more comprehensive test coverage.

### 👥 Accessible to QA
Low-code approach means non-programmers can create effective tests.

---

## Next Steps

- 📖 [Unified Controller](./unified-controller.md) - Control devices
- 📖 [AI Validation](./ai-validation.md) - Smart verification
- 📚 [User Guide - Test Builder](../user-guide/guides/testcase-template.md)
- 🔧 [Technical Docs - Test Architecture](../technical/architecture/README.md)

---

**Ready to automate your testing?**  
➡️ [Get Started](../get-started/quickstart.md)

