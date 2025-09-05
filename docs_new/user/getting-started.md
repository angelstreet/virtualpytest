# Getting Started with VirtualPyTest

**Quick setup guide for QA teams and non-technical users.**

---

## 🎯 **What You'll Learn**

- Install VirtualPyTest locally in 5 minutes
- Run your first automated test
- Access monitoring dashboards
- Navigate the web interface

---

## 📋 **Prerequisites**

- **Computer**: Linux, macOS, or Windows with Docker
- **Docker**: [Install Docker Desktop](https://www.docker.com/products/docker-desktop/)
- **Device**: Android TV, mobile, or STB to test (optional for demo)

---

## ⚡ **Quick Installation**

### Step 1: Download VirtualPyTest
```bash
# Download the project
git clone https://github.com/your-repo/virtualpytest
cd virtualpytest
```

### Step 2: Start Services
```bash
# Start all services with one command
docker compose up
```

*Wait 2-3 minutes for all services to start...*

### Step 3: Open Web Interface
```bash
# Open in your browser
http://localhost:3000
```

*[Image placeholder: Web interface dashboard showing main navigation]*

**That's it!** VirtualPyTest is now running on your computer.

---

## 🎮 **Your First Test**

### 1. **Access the Dashboard**
- Open `http://localhost:3000` in your browser
- You'll see the main dashboard with device status

*[Image placeholder: Dashboard showing connected devices and system status]*

### 2. **Run a Demo Test**
```bash
# Navigate to the test scripts directory
cd test_scripts

# Run a simple navigation test
python goto.py --node home
```

*[Image placeholder: Terminal showing test execution with success message]*

### 3. **View Results**
- **Screenshots**: Automatic screenshots saved in `/captures`
- **Logs**: Real-time execution logs in terminal
- **Dashboard**: Test results appear in web interface

---

## 📊 **Monitoring Dashboard**

### Access Grafana
```bash
# Open monitoring dashboard
http://localhost:3000/grafana
```

**Login**: admin / admin123

*[Image placeholder: Grafana dashboard showing test metrics and device health]*

### Key Metrics
- **Test Success Rate**: Percentage of passing tests
- **Device Status**: Connected devices and health
- **Execution Times**: Performance trends over time
- **Error Rates**: Failed test analysis

---

## 🔧 **Web Interface Tour**

### Main Sections
- **📊 Dashboard**: System overview and quick actions
- **🧪 Tests**: Create and manage test cases
- **📋 Campaigns**: Batch test execution
- **🌳 Navigation**: Visual device interface mapping
- **🔧 Devices**: Hardware configuration
- **📈 Monitoring**: Real-time system metrics

*[Image placeholder: Web interface showing main navigation menu]*

---

## 🎯 **Common Use Cases**

### For QA Teams
1. **Device Testing**: Validate app behavior across multiple devices
2. **Regression Testing**: Run test suites automatically
3. **Visual Validation**: Verify UI elements and content
4. **Performance Monitoring**: Track device response times

### For Operations Teams
1. **24/7 Monitoring**: Watch streaming devices continuously
2. **Health Checks**: Automated device status verification
3. **Alert Management**: Get notified of device issues
4. **Reporting**: Generate test execution reports

---

## 🚀 **Next Steps**

1. **📖 [Features Guide](features.md)** - Learn what VirtualPyTest can do
2. **🧪 [Running Tests](running-tests.md)** - Execute your own test scripts
3. **📊 [Monitoring Guide](monitoring.md)** - Master the dashboards
4. **❓ [Troubleshooting](troubleshooting.md)** - Fix common issues

---

## 💡 **Tips for Success**

- **Start Simple**: Begin with basic navigation tests
- **Use Screenshots**: Visual evidence helps debug issues
- **Monitor Regularly**: Check dashboards for device health
- **Save Campaigns**: Reuse successful test combinations

---

## 🆘 **Need Help?**

- **Common Issues**: See [Troubleshooting Guide](troubleshooting.md)
- **Feature Questions**: Check [Features Documentation](features.md)
- **Community Support**: GitHub Discussions and Issues

---

**Ready to automate your device testing? Let's explore the features!** 🎉
