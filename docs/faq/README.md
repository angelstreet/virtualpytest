# Frequently Asked Questions

Quick answers to the most common questions about VirtualPyTest.

---

## Core Concepts

### How does one script work for all devices?

VirtualPyTest separates **test logic** from **navigation logic** using a navigation tree model.

**The key insight:**
- **Nodes** = Screens/destinations (e.g., "home", "settings", "live_tv")
- **Edges** = Actions to navigate between screens (e.g., press OK, swipe left)

Your test script only cares about *what* to test:
```python
navigate_to("settings")
verify_screen("settings")
# Run your test logic here
```

The navigation tree handles *how* to get there for each platform. Same script, different navigation trees for Android, iOS, STB, or web.

**Benefits:**
- Write once, run on any device
- Change navigation without touching test logic
- AI can auto-generate navigation trees

---

### What is a navigation tree?

A navigation tree is a graph where:
- **Nodes** represent screens or UI states your device can be in
- **Edges** represent the actions needed to move between screens

```
home ──[press OK]──► settings ──[press DOWN, OK]──► wifi_settings
  ▲                      │
  └──────[press BACK]────┘
```

Each edge stores:
- Forward actions (how to go from A to B)
- Reverse actions (how to go from B to A)

The pathfinding system finds the optimal route between any two screens automatically.

---

### What devices are supported?

VirtualPyTest supports virtually any device that can be remotely controlled:

| Category | Examples |
|----------|----------|
| **Mobile** | Android phones/tablets, iOS (iPhone, iPad) |
| **TV/Streaming** | Android TV, Apple TV, Fire TV, Smart TVs (Samsung, LG) |
| **Set-Top Boxes** | Any STB with IR or network control |
| **Web** | Any browser (Chrome, Firefox, Safari, Edge) |
| **Desktop** | Windows, macOS, Linux applications |
| **HDMI Devices** | Any device with HDMI output + remote control capability |

**Control methods supported:**
- ADB (Android)
- Appium (iOS/Android)
- IR blasters (STB, TV)
- Network APIs (Smart TVs)
- Browser automation (Web)

---

## Features

### How does AI validation work?

Instead of fragile DOM selectors or pixel-perfect matching, VirtualPyTest uses **vision AI** to verify screens:

1. **Screenshot Capture** - Takes a screenshot of the current screen
2. **AI Analysis** - Vision model analyzes what's visible
3. **Semantic Verification** - Checks if expected content is present

**Example:**
```python
# Instead of: find_element(id="settings_title").text == "Settings"
# You do:
verify_screen("settings")  # AI confirms this looks like a settings screen
```

**Why this matters:**
- Works across all platforms identically
- Survives UI redesigns (no brittle selectors)
- Can detect visual bugs humans would notice

---

### How does visual capture work?

VirtualPyTest captures video/screenshots from your devices in real-time:

**For HDMI devices (STB, TV):**
- USB capture cards grab HDMI output
- Real video of what users actually see
- No dependency on device accessibility APIs

**For mobile/web:**
- ADB screencap (Android)
- Appium screenshots (iOS)
- Browser screenshots (Web)

**What you get:**
- Frame-by-frame replay of every test
- Automatic screenshot timeline
- Visual evidence for bug reports

---

## Getting Started

### What are the prerequisites?

**Minimum requirements:**
- Docker & Docker Compose (recommended)
- Python 3.9+ (for local development)

**For device control:**
| Device Type | Requirements |
|-------------|--------------|
| Android | ADB access (USB or WiFi) |
| iOS | Mac with Xcode, Appium |
| STB/TV | IR blaster or network API |
| HDMI capture | USB capture card |
| Web | Chrome/Firefox installed |

**Quick start:**
```bash
git clone https://github.com/angelstreet/virtualpytest.git
cd virtualpytest && ./setup/quickstart.sh
```

---

### How is VirtualPyTest different from Appium/Selenium?

| Aspect | VirtualPyTest | Appium/Selenium |
|--------|---------------|-----------------|
| **Approach** | Visual-first, platform-agnostic | DOM/selector-based, platform-specific |
| **Script portability** | Same script for all devices | Different scripts per platform |
| **Validation** | AI vision (semantic) | Element selectors (brittle) |
| **STB/TV support** | Built-in (IR, HDMI capture) | Not supported |
| **Cost** | Free (MIT License) | Free (but commercial tools cost $50k+) |
| **Monitoring** | Built-in Grafana dashboards | Requires separate tools |

**VirtualPyTest complements** Appium/Selenium - it uses them under the hood for mobile/web while adding the unified layer on top.

---

## Practical Usage

### How do I add a new device?

1. **Create a controller** - Implement the device interface for your platform
2. **Build a navigation tree** - Define screens and actions (AI can help)
3. **Configure connection** - Add device credentials/connection details

**For common platforms**, controllers already exist:
- Android (ADB)
- iOS (Appium)
- Web (Playwright/Selenium)
- IR-controlled devices

See [Controller Creation Guide](../technical/architecture/CONTROLLER_CREATION_GUIDE.md) for details.

---

### Can I run tests in CI/CD pipelines?

Yes. VirtualPyTest provides:

**REST API:**
```bash
# Trigger a test via API
curl -X POST http://localhost:5000/api/scripts/execute \
  -H "Content-Type: application/json" \
  -d '{"script": "validation", "device_id": "device1"}'
```

**Docker-based execution:**
```yaml
# In your CI pipeline
services:
  virtualpytest:
    image: virtualpytest/backend:latest
```

**Webhooks** for test completion notifications to Slack, JIRA, etc.

---

### Is it really free?

**Yes, 100% free and open source** under the MIT License.

- No paid tiers
- No feature restrictions
- No usage limits
- Full source code access

**Why free?**
VirtualPyTest was built to democratize device testing. Commercial tools cost $50k+/year and lock you into vendor ecosystems. We believe testing infrastructure should be accessible to everyone.

**How to support the project:**
- ⭐ Star the repo
- 🐛 Report bugs
- 🤝 Contribute code
- 📣 Spread the word

---

## Need More Help?

- 📖 [Full Documentation](../README.md)
- 💬 [GitHub Discussions](https://github.com/angelstreet/virtualpytest/discussions)
- 🐛 [Report Issues](https://github.com/angelstreet/virtualpytest/issues)

