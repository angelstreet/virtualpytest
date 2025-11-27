# VirtualPyTest Features

**Open-source device automation and monitoring made easy.**

VirtualPyTest is designed to replace expensive commercial testing tools with a flexible, powerful, free solution.

---

## 🎮 Core Features

### [Unified Device Controller](./unified-controller.md)
Write one test script that works across **all your devices** - Android TV, mobile, STB, iOS, and more. Abstract away hardware differences and focus on the user journey.

**Perfect for**: Multi-platform app testing, device compatibility validation

---

### [Visual Capture & Monitoring](./visual-capture.md)
**Automatic HDMI capture** and screenshot generation for every test step. Watch live streams, replay test executions frame-by-frame, and never miss a visual bug.

**Perfect for**: Video quality monitoring, UI regression testing, visual debugging

---

### [AI-Powered Validation](./ai-validation.md)
Smart **OCR and image detection** validates test results automatically. Our AI engine detects UI elements, text on screen, and visual anomalies without brittle selectors.

**Perfect for**: Subtitle validation, content detection, black screen monitoring

---

### [Real-time Analytics](./analytics.md)
Integrated **Grafana dashboards** provide real-time metrics on test pass rates, device health, performance trends, and system monitoring.

**Perfect for**: 24/7 monitoring, quality metrics, performance tracking

---

### [Test Automation](./test-automation.md)
Python-based automation with intuitive **navigation trees**. Build complex test scenarios with low-code approach designed for QA teams.

**Perfect for**: Regression testing, navigation validation, campaign execution

---

### [Integrations](./integrations.md)
Connect to **JIRA**, **Grafana**, and more. Export test results, sync requirements, and integrate with your existing workflow.

**Perfect for**: Team collaboration, issue tracking, CI/CD pipelines

---

## 💰 Why Choose VirtualPyTest?

| Feature | VirtualPyTest | Commercial Tools |
| :--- | :---: | :---: |
| **Cost** | **Free (Open Source)** | $15k+ / year |
| **Platform Support** | Linux, Raspberry Pi, Docker, Cloud | Often Windows only |
| **Customization** | Full Source Code Access | Vendor Locked |
| **Monitoring** | Built-in Grafana | Paid Add-on |
| **AI Validation** | Included | Extra Cost |
| **Device Support** | Android, iOS, TV, STB, Web | Limited |

---

## 🎯 Use Cases

### QA Teams
- Automated regression testing
- Multi-device compatibility validation
- Visual regression detection
- Test campaign management

### DevOps
- CI/CD integration
- Automated deployment validation
- Performance monitoring
- Alert management

### Operations
- 24/7 device monitoring
- Streaming quality assurance
- Incident detection and alerting
- Device health tracking

---

## 🚀 See It In Action

```python
# Navigate to any screen across all devices
python test_scripts/goto.py --node live

# Run channel zapping test
python test_scripts/fullzap.py --max_iteration 10

# Complete device validation
python test_scripts/validation.py horizon_android_mobile
```

Or use the **Web Interface** for point-and-click test execution!

---

## Ready to Start?

➡️ **[Quick Start Guide](../get-started/quickstart.md)** - Get running in 5 minutes  
➡️ **[User Guide](../user-guide/README.md)** - Learn how to use VirtualPyTest  
➡️ **[Technical Docs](../technical/README.md)** - Understand the architecture  

---

## Have Questions?

- 🐛 [Report Issues](https://github.com/angelstreet/virtualpytest/issues)
- 💬 [Ask Questions](https://github.com/angelstreet/virtualpytest/discussions)
- 📖 [Full Documentation](../README.md)

