# User Guide

**Learn how to use VirtualPyTest effectively.**

This guide covers everything you need to know to get the most out of VirtualPyTest, from basic operations to advanced features.

---

## 🎯 Quick Navigation

### Getting Started
- **[Getting Started](./getting-started.md)** - Your first steps with VirtualPyTest
- **[System Requirements](./system-requirements.md)** - What you need to run VirtualPyTest
- **[Raspberry Pi Quick Start](./raspberry-pi-quickstart.md)** - Deploy on Raspberry Pi

### Core Features
- **[Running Tests](./running-tests.md)** - Execute tests and campaigns
- **[Monitoring](./monitoring.md)** - 24/7 device monitoring and alerts
- **[Requirements](./requirements.md)** - Manage requirements and traceability

### Cloud Services
- **[Grafana Cloud](./grafana_cloud.md)** - Set up cloud analytics
- **[Supabase Cloud](./supabase_cloud.md)** - Configure cloud database

### Best Practices
- **[Test Case Naming](./guides/testcase-naming.md)** - Naming conventions
- **[Test Case Templates](./guides/testcase-template.md)** - Reusable templates
- **[Navigation Graphs](./guides/testcase-graph.md)** - Build navigation trees

### Help
- **[Troubleshooting](./troubleshooting.md)** - Common issues and solutions

---

## 📚 Documentation by Topic

### Test Management

#### Creating Tests
Learn how to create effective test cases:
- Define test steps
- Add verifications
- Capture screenshots
- Handle errors

#### Running Tests
Execute tests on your devices:
- Single test execution
- Campaign execution
- Parallel execution
- Scheduled execution

#### Test Results
Understand and analyze results:
- View test reports
- Screenshot galleries
- Video playback
- Failure analysis

---

### Device Management

#### Device Configuration
Set up and configure your devices:
- Add new devices
- Configure controllers (ADB, IR, Appium)
- Set up video capture
- Power management

#### Device Monitoring
Keep track of device health:
- Real-time status
- Connection monitoring
- Performance metrics
- Alert configuration

---

### Navigation Trees

#### Building Navigation Maps
Create reusable navigation structures:
- Define nodes (screens)
- Set navigation paths
- Add verifications
- Connect nodes

#### Using Navigation
Navigate efficiently in tests:
- Navigate to any node
- Automatic pathfinding
- Breadcrumb navigation
- Custom navigation logic

---

### Monitoring & Alerts

#### Setting Up Monitoring
Configure continuous monitoring:
- Video quality monitoring
- Black screen detection
- Freeze detection
- Subtitle validation

#### Alert Configuration
Get notified when issues occur:
- Configure alert rules
- Set up notification channels (Slack, Email)
- Define severity levels
- Alert escalation

---

### Campaigns

#### Campaign Creation
Organize tests into campaigns:
- Select test cases
- Choose devices
- Set execution order
- Configure retries

#### Campaign Scheduling
Automate test execution:
- Cron-based scheduling
- Recurring campaigns
- One-time executions
- Campaign dependencies

---

### Integrations

#### JIRA Integration
Connect to JIRA for issue tracking:
- Sync test cases
- Create defects automatically
- Link requirements
- Update test status

#### Grafana Dashboards
View analytics and metrics:
- Access dashboards
- Create custom panels
- Set up alerts
- Export data

---

## 🎓 Learning Path

### For QA Engineers

1. **Start Here**: [Getting Started](./getting-started.md)
2. **Learn Navigation**: [Navigation Graphs](./guides/testcase-graph.md)
3. **Create Tests**: [Test Case Templates](./guides/testcase-template.md)
4. **Run Tests**: [Running Tests](./running-tests.md)
5. **Analyze Results**: Check test reports in web interface

### For DevOps Engineers

1. **Deploy**: [Installation Guide](../get-started/README.md)
2. **Configure**: [System Requirements](./system-requirements.md)
3. **Monitor**: [Monitoring](./monitoring.md)
4. **Integrate**: [Integrations](../features/integrations.md)

### For Test Managers

1. **Overview**: [Features](../features/README.md)
2. **Plan**: [Requirements](./requirements.md)
3. **Execute**: [Running Tests](./running-tests.md)
4. **Report**: [Grafana Dashboards](./grafana_cloud.md)

---

## 💡 Tips & Tricks

### Productivity Tips

- Use **navigation trees** to avoid repeating navigation code
- Create **reusable fixtures** for common setup/teardown
- Use **campaigns** for regression testing
- Enable **automatic retries** for flaky tests
- Leverage **parallel execution** for faster results

### Best Practices

- Name test cases consistently ([naming guide](./guides/testcase-naming.md))
- Verify after every navigation
- Take screenshots at key points
- Use meaningful verification messages
- Keep tests independent and isolated

---

## 🆘 Need Help?

### Common Issues

Check [Troubleshooting](./troubleshooting.md) for solutions to:
- Connection problems
- Test failures
- Performance issues
- Configuration errors

### Get Support

- 🐛 [Report a Bug](https://github.com/angelstreet/virtualpytest/issues)
- 💬 [Ask a Question](https://github.com/angelstreet/virtualpytest/discussions)
- 📖 [Technical Docs](../technical/README.md)
- 🎯 [Feature Requests](https://github.com/angelstreet/virtualpytest/issues/new)

---

## 📖 Related Documentation

- **[Features](../features/README.md)** - What VirtualPyTest can do
- **[Get Started](../get-started/README.md)** - Installation and setup
- **[Technical Docs](../technical/README.md)** - Architecture and internals
- **[API Reference](../api/README.md)** - API documentation
- **[Examples](../examples/README.md)** - Code examples and demos

---

**Ready to start testing?**  
➡️ [Getting Started Guide](./getting-started.md)

