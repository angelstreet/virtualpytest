# Getting Started with VirtualPyTest

**Simple installation guide for QA teams and engineers.**

## 📋 **Requirements**

Before installing VirtualPyTest, you'll need to set up external services for database, storage, queuing, and AI functionality.

**👉 [Complete Requirements Setup Guide](requirements.md)**

This includes:
- **Supabase** - Database and authentication
- **Cloudflare R2** - Cloud storage for videos/screenshots  
- **Upstash Redis** - Queue management
- **OpenRouter** - AI analysis services

*Setting up these services takes ~15 minutes and is required for full functionality.*

### 🌩️ **Cloud Database Option**

By default, VirtualPyTest uses a local PostgreSQL database for the main application. If you prefer cloud-hosted database benefits, you can migrate to Supabase:

**👉 [Supabase Cloud Database Migration Guide](supabase_cloud.md)**

*This migration is optional and can be done after initial installation. Note: Grafana metrics will remain local for optimal performance.*

---

## 🚀 **TL;DR - Quick Start**

```bash
# 1. Clone project
git clone https://github.com/angelstreet/virtualpytest
cd virtualpytest

# 2. Install everything (auto-installs requirements + creates .env files)
./setup/local/install_all.sh

# 3. IMPORTANT: Edit .env files for your setup (see locations below)
# Main config: .env
# Host config: backend_host/src/.env  
# Frontend config: frontend/.env

# 4. Launch all services
./scripts/launch_virtualpytest.sh

# 5. Open browser: http://localhost:3000
```

**That's it!**

⚠️ **IMPORTANT**: You must edit the 3 .env files before launching to configure your setup

---

## 🎯 **What You'll Get**

- **Web Interface** - Control devices from your browser
- **Monitoring Dashboard** - See test results and device health
- **Automation Scripts** - Ready-to-run test examples
- **Video Capture** - Screenshots and recordings of all tests

---

## 🏗️ **What Gets Installed**

VirtualPyTest has 5 main components that work together:

| Component | Purpose | Port | What It Does |
|-----------|---------|------|--------------|
| **Frontend** | Web dashboard | 3000 | Your main interface - control everything here |
| **Backend Server** | API coordinator | 5109 | Manages tests, campaigns, and data |
| **Backend Host** | Device controller | 6109 | Controls devices + auto-starts stream/monitor services |
| **Grafana** | Monitoring | 3001 | Charts and metrics (optional but recommended) |
| **Test Scripts** | Ready examples | - | Pre-built tests you can run immediately |

---

## 📋 **Prerequisites**

- **Ubuntu 18.04+** or similar Linux distribution
- **Internet connection** for downloading dependencies
- **8GB RAM** recommended (4GB minimum)

*Note: macOS and Windows work too, but Ubuntu is easiest for beginners.*

---

## 🔧 **Web Interface Overview**

### Main Dashboard (http://localhost:3000)

The web interface has these main sections:

- **📊 Dashboard**: System status and recent test results
- **🧪 Tests**: Create and manage individual test cases
- **📋 Campaigns**: Run multiple tests in batches
- **🔧 Devices**: Configure your hardware (TVs, phones, etc.)
- **📈 Monitoring**: Real-time system health

### Monitoring Dashboard (http://localhost:3000)

Grafana provides detailed analytics:

- **Test Success Rates**: Track passing/failing tests over time
- **Device Health**: Monitor connected devices
- **Performance Metrics**: Execution times and system resources
- **Alerts**: Get notified of issues

---

## 🚀 **What's Next?**

### Immediate Next Steps

1. **Connect Real Devices**: 
   - Connect Android TV, mobile, or STB via USB/network
   - Configure device settings in web interface

2. **Try More Tests**:
   ```bash
   # Run channel zapping test
   python test_scripts/fullzap.py --max_iteration 5
   
   # Run device validation
   python test_scripts/validation.py
   ```

3. **Create Test Campaigns**:
   ```bash
   # Run multiple tests in sequence
   python test_campaign/campaign_fullzap.py
   ```

### Learn More

- **📖 [Features Guide](features.md)** - See all VirtualPyTest capabilities
- **🧪 [Running Tests](running-tests.md)** - Create your own test scripts  
- **📊 [Monitoring Guide](monitoring.md)** - Master Grafana dashboards
- **🌩️ [Cloud Database Migration](supabase_cloud.md)** - Move main database to Supabase cloud

---

## 🔧 **Quick Troubleshooting**

### Services Won't Start
```bash
# Check if ports are already in use
sudo netstat -tlnp | grep -E ':(3000|3001|5109|6109)'

# Kill conflicting processes
sudo pkill -f "node.*3000"
sudo pkill -f "python.*5109"
sudo pkill -f "python.*6109"
sudo pkill -f "grafana-server"

# Restart installation and launch
./setup/local/install_all.sh
./scripts/launch_virtualpytest.sh
```
---

## 🆘 **Need Help?**

- **🐛 Issues**: Check [Troubleshooting Guide](troubleshooting.md)
- **❓ Questions**: See [Features Documentation](features.md)  
- **💬 Community**: GitHub Discussions and Issues

---

**🎉 Congratulations! VirtualPyTest is now running on your system.**

*Ready to automate your device testing? Start with simple tests and work your way up to complex campaigns!*
