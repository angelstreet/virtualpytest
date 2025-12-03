# VirtualPyTest Documentation

**Complete documentation for VirtualPyTest.**

Your one-stop resource for everything VirtualPyTest - from quick start to advanced topics.

---

## 🚀 Getting Started

**New to VirtualPyTest?** Start here!

### [Quick Start](./get-started/quickstart.md)
Get up and running in 5 minutes with Docker.

### [Installation Options](./get-started/README.md)
- Docker deployment (recommended)
- Local development setup
- Cloud deployment
- Database configuration

---

## 📖 Main Sections

### [Features](./features/README.md)
**Discover what VirtualPyTest can do.**

- [Unified Device Controller](./features/unified-controller.md) - One script, all devices
- [Visual Capture & Monitoring](./features/visual-capture.md) - See everything, miss nothing
- [AI-Powered Validation](./features/ai-validation.md) - Smart verification
- [Real-time Analytics](./features/analytics.md) - Grafana dashboards
- [Test Automation](./features/test-automation.md) - Low-code automation
- [Integrations](./features/integrations.md) - Connect external tools

---

### [User Guide](./user-guide/README.md)
**Learn how to use VirtualPyTest effectively.**

- Running tests and campaigns
- Device configuration
- Navigation trees
- Monitoring and alerts
- Best practices
- Troubleshooting

---

### [Technical Documentation](./technical/README.md)
**Understand the architecture and internals.**

- System architecture
- Component design
- AI systems
- MCP integration
- Development guides
- Deployment

---

### [Security Reports](./security/README.md)
**Security analysis and vulnerability scanning.**

- Code security (Bandit)
- Dependency vulnerabilities (Safety & npm audit)
- Backend host, server, and frontend coverage
- Interactive HTML dashboard
- Automated scanning tools

---

### [API Reference](./api/README.md)
**Complete API documentation.**

- REST API endpoints
- OpenAPI specifications
- Authentication
- Python SDK
- Webhooks
- Integration examples

---

### [Examples & Demos](./examples/README.md)
**Learn by example.**

- Automation prompts
- Code examples
- Demo scenarios
- Best practices
- CI/CD integration

---

### [FAQ](./faq/README.md)
**Quick answers to common questions.**

- How does one script work for all devices?
- What devices are supported?
- How does AI validation work?
- How is VirtualPyTest different from commercial tools?
- Getting started and prerequisites

---

### [Integrations](./integrations/README.md)
**Connect to external tools.**

- JIRA integration
- Grafana dashboards
- CI/CD pipelines
- Cloud storage
- Custom integrations

---

## 🎯 Quick Links by Role

### For QA Engineers
1. [Quick Start](./get-started/quickstart.md)
2. [Test Automation Features](./features/test-automation.md)
3. [User Guide](./user-guide/README.md)
4. [Examples](./examples/README.md)

### For Developers
1. [Technical Documentation](./technical/README.md)
2. [API Reference](./api/README.md)
3. [Architecture](./technical/architecture/architecture.md)
4. [Examples](./examples/README.md)

### For DevOps
1. [Installation Options](./get-started/README.md)
2. [Deployment Guide](./technical/architecture/deployment.md)
3. [Security Reports](./security/README.md)
4. [Monitoring](./features/analytics.md)
5. [Integrations](./integrations/README.md)

### For Managers
1. [Features Overview](./features/README.md)
2. [Quick Start](./get-started/quickstart.md)
3. [Analytics](./features/analytics.md)
4. [User Guide](./user-guide/README.md)

---

## 🔍 Search by Topic

### Device Control
- [Unified Controller](./features/unified-controller.md)
- [User Guide - Device Management](./user-guide/README.md#device-management)
- [Controller Creation Guide](./technical/architecture/CONTROLLER_CREATION_GUIDE.md)

### Visual Testing
- [Visual Capture](./features/visual-capture.md)
- [AI Validation](./features/ai-validation.md)
- [User Guide - Monitoring](./user-guide/monitoring.md)

### Test Automation
- [Test Automation Features](./features/test-automation.md)
- [Examples](./examples/README.md)
- [User Guide - Running Tests](./user-guide/running-tests.md)

### Analytics & Monitoring
- [Analytics Features](./features/analytics.md)
- [Grafana Integration](./technical/architecture/GRAFANA_INTEGRATION.md)
- [User Guide - Monitoring](./user-guide/monitoring.md)

### Integrations
- [Integration Features](./features/integrations.md)
- [JIRA Integration](./integrations/JIRA_INTEGRATION.md)
- [API Reference](./api/README.md)

---

## 📱 Supported Platforms

VirtualPyTest works with:

- **Android** - TV, mobile, tablets
- **iOS** - iPhone, iPad, Apple TV
- **Set-Top Boxes** - IR and network controlled
- **Smart TVs** - Samsung, LG, etc.
- **Web** - Browser automation
- **Desktop** - Windows, macOS, Linux

---

## 💰 Why VirtualPyTest?

| Feature | VirtualPyTest | Commercial Tools |
| :--- | :---: | :---: |
| Cost | **Free** | $15k+/year |
| Platform Support | All | Limited |
| Customization | Full | Vendor Locked |
| Monitoring | Built-in | Extra Cost |
| AI Validation | Included | Extra Cost |

---

## 🆘 Need Help?

### Documentation
- Browse sections above
- Check [FAQ](./faq/README.md) for quick answers
- Check [User Guide](./user-guide/README.md)
- See [Examples](./examples/README.md)
- Read [Technical Docs](./technical/README.md)

### Community
- 💬 [Ask Questions](https://github.com/angelstreet/virtualpytest/discussions)
- 🐛 [Report Bugs](https://github.com/angelstreet/virtualpytest/issues)
- 🎯 [Request Features](https://github.com/angelstreet/virtualpytest/issues/new)

### Troubleshooting
- [Troubleshooting Guide](./user-guide/troubleshooting.md)
- [Common Issues](./user-guide/README.md#need-help)
- [GitHub Issues](https://github.com/angelstreet/virtualpytest/issues)

---

## 🗺️ Documentation Structure

```
docs/
├── README.md (this file)
├── get-started/           # Installation & setup
│   ├── quickstart.md
│   ├── local-setup.md
│   └── cloud-setup.md
├── features/              # Feature showcase
│   ├── unified-controller.md
│   ├── visual-capture.md
│   ├── ai-validation.md
│   └── ...
├── user-guide/            # How to use
│   ├── running-tests.md
│   ├── monitoring.md
│   └── guides/
├── faq/                   # Frequently asked questions
│   └── README.md
├── technical/             # Architecture & internals
│   ├── architecture/
│   ├── ai/
│   ├── mcp/
│   └── dev/
├── api/                   # API documentation
│   ├── README.md
│   └── openapi/
├── examples/              # Code examples
│   ├── automate-prompt-*.md
│   └── sauce-demo-*.md
├── integrations/          # Third-party tools
│   └── JIRA_INTEGRATION.md
└── security/              # Security reports
    ├── README.md
    ├── index.html
    └── *.json
```

---

## 🔄 Recently Updated

- ❓ [FAQ](./faq/README.md) - Common questions answered
- ✨ [Quick Start Guide](./get-started/quickstart.md) - Simplified installation
- 📖 [Features Section](./features/README.md) - Complete feature showcase
- 🤖 [AI Validation](./features/ai-validation.md) - AI capabilities documented
- 🔌 [Integrations](./integrations/README.md) - Integration guides
- 📚 [User Guide](./user-guide/README.md) - Comprehensive usage guide

---

## 🤝 Contributing to Documentation

Found an error? Want to improve the docs?

1. 📝 Edit on GitHub
2. Submit a pull request
3. Help make the docs better!

---

**Ready to get started?**  
➡️ [Quick Start Guide](./get-started/quickstart.md)  
➡️ [Features Overview](./features/README.md)  
➡️ [User Guide](./user-guide/README.md)

