# Examples & Demos

**Learn by example.**

Code examples, automation prompts, and demos to help you get started quickly.

---

## 🎯 What's Here

This section contains:
- **Automation Prompts** - AI-generated test automation examples
- **Code Examples** - Python scripts and snippets
- **Demo Scenarios** - Real-world use cases
- **Best Practices** - Proven patterns and approaches

---

## 🤖 AI Automation Prompts

These examples show how to use AI to generate test automation scripts.

### TV / Set-Top Box Automation

**[TV Automation Prompt](./automate-prompt-tv.md)**

Learn how to prompt AI to create automation for:
- Navigation testing
- Channel zapping
- EPG validation
- Settings configuration
- App launching

**Example prompt:**
> "Create a test that navigates to Settings → Audio → Select Stereo mode on an Android TV"

---

### Mobile Automation

**[Mobile Automation Prompt](./automate-prompt-mobile.md)**

Generate automation for mobile devices:
- App installation and launch
- Touch gestures and swipes
- Form filling
- Camera and sensors
- Notifications

**Example prompt:**
> "Test the login flow in the Netflix app: enter credentials, tap login, verify home screen appears"

---

### Web Automation

**[Web Automation Prompt](./automate-prompt-web.md)**

Create web browser automation:
- Page navigation
- Form submission
- Element interaction
- Responsive testing
- Cross-browser validation

**Example prompt:**
> "Navigate to Google, search for 'VirtualPyTest', verify search results appear"

---

### General Automation Guide

**[General Automation Prompt](./automate-prompt.md)**

Universal automation patterns that work across all device types.

---

## 🎬 Demo Scenarios

### SauceDemo Optimal Prompt

**[SauceDemo Example](./sauce-demo-optimal-prompt.md)**

Complete example using the popular SauceDemo test site:
- Login flow
- Product browsing
- Shopping cart
- Checkout process

**Perfect for:**
- Learning test automation
- Practicing with a known site
- Training new team members

---

## 💡 Code Examples

### Basic Test Execution

```python
from shared.src.controller_factory import ControllerFactory

# Get controller for your device
controller = ControllerFactory.get_controller(device="android_tv_1")

# Navigate to home
controller.go_home()

# Navigate to Netflix
controller.navigate_to("netflix")

# Verify Netflix loaded
assert controller.verify_text("Netflix")

print("✅ Test passed!")
```

---

### Channel Zapping Test

```python
from shared.src.controller_factory import ControllerFactory
import time

controller = ControllerFactory.get_controller(device="stb_ir")

# Go to live TV
controller.navigate_to("live")

# Zap through 10 channels
for i in range(10):
    controller.press_key("CHANNEL_UP")
    time.sleep(2)
    
    # Verify video is playing
    assert not controller.detect_black_screen()
    assert not controller.detect_freeze()
    
    controller.capture_screenshot(f"channel_{i}.png")
    print(f"✅ Channel {i} OK")
```

---

### AI-Powered Validation

```python
from shared.src.services.ai_analyzer import AIAnalyzer

controller = ControllerFactory.get_controller(device="android_tv_1")
ai = AIAnalyzer()

# Navigate to Netflix
controller.navigate_to("netflix")

# Capture screen
screenshot = controller.capture_screenshot()

# Use AI to verify
result = ai.analyze_screen(
    screenshot=screenshot,
    expected_elements=[
        "Netflix logo",
        "user profile icon",
        "content thumbnails",
        "navigation menu"
    ]
)

for element, found in result.items():
    status = "✅" if found else "❌"
    print(f"{status} {element}")
```

---

### Campaign Execution

```python
from shared.src.services.campaign_manager import CampaignManager

manager = CampaignManager()

# Create campaign
campaign = manager.create_campaign(
    name="Streaming Apps Validation",
    test_cases=[
        "tc_001_netflix",
        "tc_002_youtube",
        "tc_003_prime_video"
    ],
    devices=["android_tv_1", "android_tv_2"],
    execution_mode="parallel"
)

# Execute
results = manager.execute(campaign)

# Report
print(f"Passed: {results.passed_count}/{results.total_count}")
print(f"Duration: {results.duration}s")
```

---

### Visual Regression Test

```python
from shared.src.services.visual_regression import VisualRegression

controller = ControllerFactory.get_controller(device="android_tv_1")
vr = VisualRegression()

# Navigate to screen
controller.navigate_to("home")

# Capture current state
current = controller.capture_screenshot()

# Compare with baseline
result = vr.compare(
    baseline="baselines/home_screen_v1.0.png",
    current=current,
    threshold=0.95
)

if result.changed:
    print(f"⚠️ UI changed by {result.difference_percent}%")
    print(f"Diff image: {result.diff_path}")
else:
    print("✅ UI unchanged")
```

---

## 🎓 Tutorials by Use Case

### For QA Engineers

**Test Automation Basics:**
1. Review [General Automation Prompt](./automate-prompt.md)
2. Try [SauceDemo Example](./sauce-demo-optimal-prompt.md)
3. Adapt to your application
4. Create test campaigns

**Visual Testing:**
1. Set up baseline screenshots
2. Use visual regression example
3. Configure diff threshold
4. Automate in CI/CD

---

### For Mobile Testers

**Mobile App Testing:**
1. Study [Mobile Automation Prompt](./automate-prompt-mobile.md)
2. Configure Appium controller
3. Create page objects
4. Build test suite

---

### For TV/STB Testers

**Streaming Device Testing:**
1. Review [TV Automation Prompt](./automate-prompt-tv.md)
2. Set up IR or ADB controller
3. Build navigation tree
4. Create zapping tests

---

## 📚 Learning Resources

### Recommended Order

**Beginners:**
1. Start with [SauceDemo](./sauce-demo-optimal-prompt.md) - Known working example
2. Read [General Automation](./automate-prompt.md) - Core concepts
3. Choose platform ([TV](./automate-prompt-tv.md), [Mobile](./automate-prompt-mobile.md), or [Web](./automate-prompt-web.md))
4. Build your first test

**Intermediate:**
1. Study code examples above
2. Create reusable page objects
3. Build test campaigns
4. Implement CI/CD integration

**Advanced:**
1. Use AI-powered validation
2. Implement visual regression
3. Create custom controllers
4. Extend the framework

---

## 🔗 Integration Examples

### Jenkins Pipeline

```groovy
pipeline {
    agent any
    stages {
        stage('Run VirtualPyTest') {
            steps {
                sh '''
                    cd virtualpytest
                    source venv/bin/activate
                    python test_scripts/validation.py android_tv_1
                '''
            }
        }
    }
    post {
        always {
            publishHTML([
                reportDir: 'test_results',
                reportFiles: 'index.html',
                reportName: 'VirtualPyTest Report'
            ])
        }
    }
}
```

---

### GitHub Actions

```yaml
name: Nightly Tests

on:
  schedule:
    - cron: '0 2 * * *'  # 2 AM daily

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Run Tests
        run: |
          python test_scripts/fullzap.py --max_iteration 20
          
      - name: Upload Results
        uses: actions/upload-artifact@v2
        with:
          name: test-results
          path: test_results/
```

---

## 💡 Tips & Best Practices

### Writing Effective Prompts

When using AI to generate tests:
- ✅ Be specific about device type
- ✅ Describe the exact user journey
- ✅ Specify verification points
- ✅ Include error handling needs

### Code Organization

```
tests/
├── page_objects/       # Reusable page objects
│   ├── netflix_home.py
│   └── settings.py
├── test_cases/         # Individual tests
│   ├── test_netflix.py
│   └── test_youtube.py
├── campaigns/          # Test campaigns
│   └── nightly_regression.py
└── fixtures/           # Test fixtures
    └── conftest.py
```

---

## 🆘 Need Help?

- 💬 [Ask Questions](https://github.com/angelstreet/virtualpytest/discussions)
- 📖 [User Guide](../user-guide/README.md)
- 🔧 [Technical Docs](../technical/README.md)
- 🐛 [Report Issues](https://github.com/angelstreet/virtualpytest/issues)

---

## 📖 Related Documentation

- **[Features](../features/README.md)** - What VirtualPyTest can do
- **[User Guide](../user-guide/README.md)** - How to use the platform
- **[API Reference](../api/README.md)** - API documentation
- **[Get Started](../get-started/README.md)** - Installation

---

**Ready to start automating?**  
➡️ [Try the SauceDemo Example](./sauce-demo-optimal-prompt.md)

