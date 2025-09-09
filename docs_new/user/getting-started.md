# Getting Started with VirtualPyTest

**Simple installation guide for QA teams and engineers.**

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
| **Backend Host** | Device controller | 6109 | Actually controls your devices (TV, mobile, etc.) |
| **Grafana** | Monitoring | 3001 | Charts and metrics (optional but recommended) |
| **Test Scripts** | Ready examples | - | Pre-built tests you can run immediately |

---

## 📋 **Prerequisites**

- **Ubuntu 18.04+** or similar Linux distribution
- **Internet connection** for downloading dependencies
- **8GB RAM** recommended (4GB minimum)

*Note: macOS and Windows work too, but Ubuntu is easiest for beginners.*

---

## ⚡ **Installation (3 Simple Steps)**

### Step 1: Get VirtualPyTest
```bash
# Download the project
git clone https://github.com/angelstreet/virtualpytest
cd virtualpytest
```

### Step 2: Install Everything
```bash
# This installs all components (takes 5-10 minutes)
./setup/local/install_all.sh --with-grafana
```

*The script will:*
- ✅ Create Python virtual environment
- ✅ Install all Python dependencies  
- ✅ Install Node.js dependencies for web interface
- ✅ Set up Grafana monitoring
- ✅ Configure all services

### Step 3: Start All Services
```bash
# Start everything with one simple command
./scripts/launch_virtualpytest.sh
```

*You'll see colored logs like:*
- 🔵 **[SERVER]** - Backend server starting...
- 🟢 **[HOST]** - Backend host ready...
- 🟡 **[FRONTEND]** - Web interface loading...

**Keep this terminal open** - it shows live logs from all services.

---

## ⚙️ **Configure Environment (Important!)**

Before starting services, you need to configure environment files. VirtualPyTest uses 3 different `.env` files:

### Step 3.1: Project-Level Configuration

```bash
# Copy the main environment template
cp .env.example .env

# Edit with your values (optional for basic local testing)
nano .env
```

**For basic local testing**, you can use the defaults. **For full functionality**, configure:

```bash
# Database (Supabase) - REQUIRED for data storage
NEXT_PUBLIC_SUPABASE_URL=https://your-project-id.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key_here
DATABASE_URL=postgresql://postgres:password@db.project-id.supabase.co:5432/postgres

# Cloud Storage (Cloudflare R2) - OPTIONAL for screenshots
CLOUDFLARE_R2_ENDPOINT=https://your-account-id.r2.cloudflarestorage.com
CLOUDFLARE_R2_ACCESS_KEY_ID=your_r2_access_key_id
CLOUDFLARE_R2_SECRET_ACCESS_KEY=your_r2_secret_access_key

# AI Services - OPTIONAL for smart analysis
OPENROUTER_API_KEY=your_openrouter_api_key_here
```

### Step 3.2: Backend Host Configuration

```bash
# Copy backend host template
cp backend_host/src/env.example backend_host/src/.env

# Edit with your device settings
nano backend_host/src/.env
```

**For basic testing** (desktop only):
```bash
HOST_NAME=my-local-host
HOST_PORT=6109
HOST_URL=http://localhost:6109
```

**For device testing** (Android TV, mobile, etc.):
```bash
# Uncomment and configure device settings
DEVICE1_NAME=my_android_tv
DEVICE1_MODEL=android_tv
DEVICE1_IP=192.168.1.100
DEVICE1_PORT=8100
```

### Step 3.3: Frontend Configuration

```bash
# Copy frontend template
cp frontend/env.example frontend/.env

# Edit API endpoint (usually no changes needed for local)
nano frontend/.env
```

**Default settings work for local development:**
```bash
VITE_SERVER_URL=http://localhost:5109
VITE_ENVIRONMENT=development
```

---

## ✅ **Verify Installation**

### Step 4: Check All Services Are Running

Open a **new terminal** (keep the first one with logs running) and test each service:

```bash
# Test Frontend (should show HTML)
curl http://localhost:3000

# Test Backend Server (should show {"status": "healthy"})
curl http://localhost:5109/api/health

# Test Backend Host (should show {"status": "ok"})
curl http://localhost:6109/host/health

# Test Grafana (should show login page)
curl http://localhost:3001
```

### Step 5: Open Web Interfaces

Open these URLs in your browser:

- **🌐 Main Dashboard**: http://localhost:3000
- **📊 Monitoring**: http://localhost:3001 (login: admin / admin123)

*If any URL doesn't work, check the terminal with logs for error messages.*

---

## 🎮 **Your First Test**

### Step 6: Run a Simple Test

In a **new terminal**, run your first automation test:

```bash
# Navigate to test scripts
cd test_scripts

# Activate the Python environment
source ../venv/bin/activate

# Run a simple navigation test
python goto.py --node home
```

**Expected output:**
```
🎯 [GOTO_HOME] EXECUTION SUMMARY
📱 Device: virtual_device (desktop)
🖥️  Host: localhost
📋 Interface: default
🗺️  Target: home
📍 Path length: 1 steps
⏱️  Total Time: 2.3s
📸 Screenshots: 2 captured
🎯 Result: SUCCESS
```

### Step 7: View Your Test Results

- **Screenshots**: Check the `captures/` folder for automatic screenshots
- **Web Dashboard**: Refresh http://localhost:3000 to see test results
- **Monitoring**: Check http://localhost:3001 for test metrics

---

## 🔧 **Web Interface Overview**

### Main Dashboard (http://localhost:3000)

The web interface has these main sections:

- **📊 Dashboard**: System status and recent test results
- **🧪 Tests**: Create and manage individual test cases
- **📋 Campaigns**: Run multiple tests in batches
- **🔧 Devices**: Configure your hardware (TVs, phones, etc.)
- **📈 Monitoring**: Real-time system health

### Monitoring Dashboard (http://localhost:3001)

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
./setup/local/install_all.sh --with-grafana
./scripts/launch_virtualpytest.sh
```

### Grafana Database Issues
```bash
# Check if PostgreSQL is running
pg_isready

# Start PostgreSQL if needed
# On Ubuntu/Linux:
sudo systemctl start postgresql
# On macOS:
brew services start postgresql

# Test Grafana database connection
PGPASSWORD=grafana_pass psql -h localhost -U grafana_user -d grafana_metrics -c "SELECT version();"
```

### Web Interface Not Loading
```bash
# Check if frontend is running
curl http://localhost:3000

# If not working, check logs in the terminal running launch_virtualpytest.sh
# Look for [FRONTEND] errors in colored output
```

### Test Scripts Fail
```bash
# Make sure you're in the right directory and virtual environment
cd test_scripts
source ../venv/bin/activate
python goto.py --node home
```

---

## 💡 **Pro Tips**

- **Keep Logs Open**: Always run `./scripts/launch_virtualpytest.sh` in a visible terminal to see real-time logs
- **Use Screenshots**: Every test automatically captures screenshots - check the `captures/` folder
- **Monitor Health**: Check http://localhost:3001 regularly for system health
- **Start Simple**: Begin with `goto.py` tests before trying complex campaigns

---

## 🆘 **Need Help?**

- **🐛 Issues**: Check [Troubleshooting Guide](troubleshooting.md)
- **❓ Questions**: See [Features Documentation](features.md)  
- **💬 Community**: GitHub Discussions and Issues

---

**🎉 Congratulations! VirtualPyTest is now running on your system.**

*Ready to automate your device testing? Start with simple tests and work your way up to complex campaigns!*
