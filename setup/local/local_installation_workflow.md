# VirtualPyTest Local Installation Workflow

**A complete guide to understanding and installing VirtualPyTest locally**

## 🎯 **What You're Getting**

VirtualPyTest is a comprehensive test automation platform for connected devices (TVs, set-top boxes, mobile devices). After installation, you'll have:

- **🌐 Web Interface** - Modern React dashboard to create tests and view results
- **🤖 Backend Services** - API server and device controller for test execution  
- **🗄️ Complete Database** - PostgreSQL with full schema for storing tests, results, and navigation data
- **📊 Monitoring Dashboard** - Grafana for real-time performance monitoring
- **🔧 Shared Libraries** - Python utilities for device control and test automation

## 🏗️ **Architecture Overview**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │  Backend Server │    │  Backend Host   │
│   (React App)   │◄──►│   (API/Web)     │◄──►│ (Device Control)│
│   Port 3000     │    │   Port 5109     │    │  Hardware I/O   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 ▼
                    ┌─────────────────────────────┐
                    │      PostgreSQL DB          │
                    │  ┌─────────────────────────┐ │
                    │  │ VirtualPyTest Schema    │ │
                    │  │ • Tests & Results       │ │
                    │  │ • Navigation Trees      │ │
                    │  │ • Device Configs        │ │
                    │  │ • Performance Metrics   │ │
                    │  └─────────────────────────┘ │
                    │  ┌─────────────────────────┐ │
                    │  │ Grafana Metrics DB      │ │
                    │  └─────────────────────────┘ │
                    └─────────────────────────────┘
                                 ▲
                    ┌─────────────────────────────┐
                    │       Grafana Dashboard     │
                    │     (Monitoring & Analytics)│
                    │         Port 3001           │
                    └─────────────────────────────┘
```

## 🚀 **Installation Workflow**

### **Step 1: System Requirements** ⚙️
**What happens:** Installs OS-level dependencies that VirtualPyTest needs
```bash
./setup/local/install_requirements.sh
```

**Installs:**
- Build tools (gcc, make, git)
- Video processing (FFmpeg, ImageMagick)
- OCR capabilities (Tesseract)
- VNC server (for remote device control)
- Network tools

**Why needed:** These are system-level packages that can't be installed via Python/Node package managers.

---

### **Step 2: Complete Installation** 🎯
**What happens:** Installs all VirtualPyTest components in the correct order
```bash
./setup/local/install_all.sh
```

**Installation Order & What Each Does:**

#### **2.1 Database Setup** 🗄️
- **Installs PostgreSQL** (if not present)
- **Creates 2 databases:**
  - `virtualpytest` - Main application data
  - `grafana_metrics` - Monitoring data
- **Runs migration files** to create 20+ tables:
  - Device models and configurations
  - Navigation trees and test paths
  - Test cases and execution results
  - Performance metrics and alerts
- **Creates database users** with proper permissions
- **Generates config file** with connection strings

#### **2.2 Shared Library** 📚
- **Python virtual environment** creation
- **Core utilities** for device communication
- **Common functions** used by all services
- **Device controller libraries** (Appium, Selenium, etc.)

#### **2.3 Backend Server** 🖥️
- **API server dependencies** (Flask/FastAPI)
- **Database connection libraries**
- **Authentication and routing**
- **File upload/download handling**

#### **2.4 Backend Host** 🤖
- **Device control libraries**
- **Hardware interface drivers**
- **Video capture and analysis**
- **Remote control protocols**

#### **2.5 Frontend** 🌐
- **Node.js and npm** installation
- **React application** build
- **Modern web dashboard** for test management
- **Real-time result visualization**

#### **2.6 Grafana Monitoring** 📊 *(Optional, default enabled)*
- **Grafana server** installation
- **Pre-configured dashboards** for VirtualPyTest
- **Database connections** to both PostgreSQL databases
- **Performance monitoring** setup

---

### **Step 3: Launch Everything** 🚀
**What happens:** Starts all services with unified logging
```bash
./setup/local/launch_all.sh --with-grafana
```

**Services Started:**
- **Frontend** → http://localhost:3000
- **Backend Server** → http://localhost:5109
- **Backend Host** → Device control ready
- **Grafana** → http://localhost:3000
- **PostgreSQL** → Database ready

## 🔧 **Configuration Files Created**

After installation, you'll have these configuration files to customize:

```
📁 Project Root
├── config/database/local.env          # Database connection strings
├── backend_server/src/.env            # API server settings
├── backend_host/src/.env              # Device control settings  
├── frontend/.env                      # Web interface settings
└── shared/.env                        # Shared library settings
```

## 🗄️ **Database Schema Details**

The installation creates a complete database with these key components:

### **Core Tables**
- **`teams`** - Multi-tenant organization
- **`device_models`** - TV/device specifications
- **`device`** - Physical device instances
- **`environment_profiles`** - Test environment configs

### **Navigation & Testing**
- **`userinterfaces`** - Apps/screens being tested
- **`navigation_trees`** - Visual navigation maps
- **`navigation_nodes`** - Individual screens/states
- **`navigation_edges`** - Transitions between screens
- **`test_cases`** - Test definitions and steps

### **Execution & Results**
- **`script_results`** - Test execution outcomes
- **`execution_results`** - Detailed step results
- **`zap_results`** - Media analysis data
- **`alerts`** - System monitoring incidents

### **Analytics & Monitoring**
- **`node_metrics`** - Screen performance data
- **`edge_metrics`** - Transition success rates
- **`heatmaps`** - Performance visualizations

## 💡 **Why This Architecture?**

### **Local Database Benefits**
- **No cloud dependency** - Works offline
- **Full control** - Your data stays local
- **Development speed** - No network latency
- **Cost effective** - No cloud database fees
- **Schema consistency** - Same structure as production

### **Microservices Design**
- **Scalability** - Each service can be scaled independently
- **Maintainability** - Clear separation of concerns
- **Flexibility** - Can run services on different machines
- **Development** - Teams can work on different services

### **Monitoring Integration**
- **Real-time insights** - See performance as tests run
- **Historical data** - Track improvements over time
- **Alert system** - Get notified of issues
- **Custom dashboards** - Visualize what matters to you

## 🎯 **What Happens After Installation**

### **Immediate Capabilities**
1. **Create test cases** via web interface
2. **Define navigation paths** between screens
3. **Execute tests** on connected devices
4. **View real-time results** and metrics
5. **Monitor system performance** via Grafana

### **File Structure Created**
```
📁 virtualpytest/
├── venv/                    # Python virtual environment
├── config/database/         # Database configuration
├── backend_server/          # API server (ready to run)
├── backend_host/           # Device controller (ready to run)
├── frontend/dist/          # Built web application
├── shared/                 # Common libraries
└── grafana/               # Monitoring dashboards
```

### **Network Ports Used**
- **3000** - Frontend web interface
- **5109** - Backend API server
- **3001** - Grafana monitoring dashboard
- **5432** - PostgreSQL database

## 🚨 **Common Questions**

### **"Do I need all components?"**
- **Minimum:** Database + Shared + Backend Server + Frontend
- **Recommended:** All components for full functionality
- **Optional:** Grafana (use `--no-grafana` to skip)

### **"Can I install components separately?"**
Yes! Each component has its own install script:
```bash
./setup/local/install_db.sh          # Database only
./setup/local/install_shared.sh      # Shared library only
./setup/local/install_server.sh      # Backend server only
# ... etc
```

### **"What if something fails?"**
- **Check logs** - Each script shows detailed output
- **Run test script** - `./setup/local/test_db_setup.sh`
- **Individual components** - Install one at a time to isolate issues
- **Clean start** - `./setup/local/clean_build_artifacts.sh`

### **"How much disk space needed?"**
- **Database:** ~100MB (empty schema)
- **Python environment:** ~500MB
- **Node.js dependencies:** ~200MB
- **Grafana:** ~100MB
- **Total:** ~1GB for complete installation

## 🎉 **Success Indicators**

After successful installation, you should see:

✅ **Database:** 20+ tables created, connections working  
✅ **Services:** All components start without errors  
✅ **Web Interface:** Accessible at http://localhost:3000  
✅ **API:** Backend responds at http://localhost:5109  
✅ **Monitoring:** Grafana dashboard at http://localhost:3000  
✅ **Configuration:** All .env files created with examples  

## 🚀 **Next Steps**

1. **Configure .env files** with your specific settings
2. **Connect test devices** (TVs, mobile devices, etc.)
3. **Create your first test case** via the web interface
4. **Set up navigation trees** for your applications
5. **Run your first automated test**

---

**Ready to start?** Run the installation workflow:
```bash
cd /path/to/virtualpytest
./setup/local/install_requirements.sh
./setup/local/install_all.sh
./setup/local/launch_all.sh --with-grafana
```

Then open http://localhost:3000 and start testing! 🚀
