# VirtualPyTest

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![Status](https://img.shields.io/badge/status-active-success.svg)]()
[![Documentation](https://img.shields.io/badge/docs-latest-brightgreen)](docs_new/user/)
[![Sandbox](https://img.shields.io/badge/Try_Live-VirtualPyTest.com-orange)](https://www.virtualpytest.com/)

<div align="center">
  <h3><b>Open-source, multi-device automation and monitoring made easy.</b></h3>
  <p>One script = all devices. No expensive licenses. No vendor lock-in.</p>

  <p>
    <a href="docs_new/user/getting-started.md"><b>Getting Started</b></a> •
    <a href="docs_new/user/"><b>Documentation</b></a> •
    <a href="docs_new/examples/"><b>Tutorials</b></a> •
    <a href="#community--support"><b>Community</b></a>
  </p>
</div>

---

## **Overview**

VirtualPyTest is a unified automation platform that helps you automate, monitor, and remotely control all your devices—TVs, set-top boxes (STBs), mobile phones, and more.

Designed to **replace $15k+ commercial tools**, VirtualPyTest provides a free, flexible solution that works everywhere. Whether you are a QA team needing to automate regression tests, or an operations team monitoring device health 24/7, VirtualPyTest scales to meet your needs.

<div align="center">
  <a href="https://www.virtualpytest.com/">
    <img src="/frontend/screenshot/dashboard.png" alt="VirtualPyTest Dashboard" width="100%">
  </a>
  <p><i><a href="https://www.virtualpytest.com/">Try the Live Sandbox</a></i></p>
</div>

---

## **Key Features**

### **🎮 Unified Device Controller**
Write one script that works across **Android TV, mobile, STB, and iOS**. Abstract away the hardware differences and focus on the user journey.

### **📹 Intelligent Visual Capture** 
Automatic HDMI capture and screenshot timeline generation for every test step. Never miss a visual bug again with frame-by-frame replay.

### **🤖 AI-Powered Validation**
Smart image and text detection validates test results automatically. Our AI verification engine detects UI elements, text on screen, and visual anomalies without brittle selectors.

### **📊 Real-time Analytics Dashboard**
Integrated **Grafana** dashboards provide real-time metrics on test pass rates, device health, and performance trends.

### **🧪 Low-Code Script Execution**
Python-based automation with intuitive navigation trees. Designed for QA teams to build complex scenarios without needing deep coding expertise.

---

## **🚀 Quick Start**

Get up and running in minutes using Docker.

### **One-Click Installation**

```bash
git clone https://github.com/angelstreet/virtualpytest.git
cd virtualpytest && ./quickstart.sh
```

This script will automatically:
1. Install Docker & Docker Compose (if missing)
2. Launch the full stack (Frontend + Backend + Database)
3. Open the dashboard at `http://localhost:3000`

### **Manual Setup**
For developers who want to contribute or run locally without Docker, see our [Developer Guide](docs_new/technical/setup.md).

---

## **Tutorials & Examples**

Learn how to automate common scenarios:

1. **[Basic Navigation](docs_new/examples/navigation.md)** - How to navigate menus on any device.
2. **[Channel Zapping](docs_new/examples/zapping.md)** - Automate channel changes and validate video stability.
3. **[App Validation](docs_new/examples/validation.md)** - Launch apps and verify they load correctly.
4. **[Visual Regression](docs_new/examples/visual.md)** - Detect UI changes using AI comparison.

*See all examples in the [Examples Directory](docs_new/examples/).*

---

## **Why Choose VirtualPyTest?**

| Feature | VirtualPyTest | Commercial Tools |
| :--- | :---: | :---: |
| **Cost** | **Free (Open Source)** | $15k+ / year |
| **Platform Support** | Linux, Raspberry Pi, Docker, Cloud | often Windows only |
| **Customization** | Full Source Code Access | Vendor Locked |
| **Monitoring** | Built-in Grafana | Paid Add-on |
| **AI Validation** | Included | Extra Cost |

---

## **See It In Action**

Execute tests directly from your terminal or the web UI:

```bash
# Navigate to any screen
python test_scripts/goto.py --node live

# Run channel zapping test  
python test_scripts/fullzap.py --max_iteration 10

# Complete device validation
python test_scripts/validation.py horizon_android_mobile
```

---

## **Roadmap**

We are constantly improving VirtualPyTest. Here is what's coming next:

- [ ] **Cloud Device Farm**: Connect to remote devices over the internet effortlessly.
- [ ] **Visual Test Builder**: Drag-and-drop test creation UI.
- [ ] **Advanced AI**: Self-healing test scripts that adapt to UI changes.

Check out our [full roadmap](docs_new/roadmap.md) for more details.

---

## **Community & Support**

We welcome you to join our growing community!

- **🐛 Issue Tracker**: Report bugs or request features on [GitHub Issues](https://github.com/your-repo/virtualpytest/issues).
- **💬 Discussions**: Ask questions and share ideas in [GitHub Discussions](https://github.com/your-repo/virtualpytest/discussions).
- **🤝 Contributing**: Want to help? Read our [Contribution Guide](CONTRIBUTING.md).

---

## **License**

VirtualPyTest is available under the [MIT License](LICENSE).

**Ready to revolutionize your device testing?**
[Get Started Now](docs_new/user/getting-started.md) 🚀
