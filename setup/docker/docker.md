# VirtualPyTest Docker Setup

**3 focused Docker deployments for different use cases**

## 🐳 **Available Docker Setups**

### **1. Standalone - Complete Local System**
**File:** `docker-compose.standalone.yml`  
**Use case:** Local development, testing, demos

### **2. Backend Server - API Only**
**File:** `docker-compose.backend-server.yml`  
**Use case:** Deploy API server to cloud, separate from hardware

### **3. Backend Host - Device Controller Only**
**File:** `docker-compose.backend-host.yml`  
**Use case:** Deploy to Raspberry Pi, hardware locations

---

## 🎯 **Setup 1: Standalone (Complete Local)**

### **What You Get:**
- ✅ Backend Server (API + Grafana monitoring)
- ✅ Backend Host (Device controller)
- ✅ Frontend (React web interface)
- ✅ PostgreSQL (Local database with VirtualPyTest schema)
- ✅ Grafana Metrics DB (Monitoring data storage)

### **Ports:**
- **3000** - Frontend web interface
- **5109** - Backend Server API
- **6109** - Backend Host device controller
- **5432** - PostgreSQL main database
- **5433** - Grafana metrics database
- **3001** - Grafana dashboard

### **Usage:**
```bash
# Easy way - Use launch script
./setup/docker/launch_standalone.sh

# Manual way - Direct docker-compose commands
docker-compose -f setup/docker/docker-compose.standalone.yml up -d
docker-compose -f setup/docker/docker-compose.standalone.yml logs -f
docker-compose -f setup/docker/docker-compose.standalone.yml down
```

### **Access Points:**
- **Web Interface:** http://localhost:3000
- **API Server:** http://localhost:5109
- **Device Controller:** http://localhost:6109
- **Grafana Monitoring:** http://localhost:3001

### **Configuration:**
No external configuration needed - everything runs locally with default settings.

---

## 🎯 **Setup 2: Backend Server (API Only)**

### **What You Get:**
- ✅ Backend Server (API + Grafana monitoring)
- ✅ Shared library (included in container)

### **External Dependencies:**
- **Supabase Database** - For application data
- **Frontend** - Deployed separately (Vercel, Netlify, etc.)

### **Ports:**
- **5109** - Backend Server API
- **3001** - Grafana dashboard

### **Usage:**
```bash
# Easy way - Use launch script
./setup/docker/launch_backend_server.sh

# Manual way - Direct docker-compose commands
docker-compose -f setup/docker/docker-compose.backend-server.yml up -d
docker-compose -f setup/docker/docker-compose.backend-server.yml logs -f
docker-compose -f setup/docker/docker-compose.backend-server.yml down
```

### **Required Configuration:**

Create `.env` file in project root with:

```bash
# Supabase Database Configuration
SUPABASE_DB_URI=postgresql://postgres:[password]@db.[project].supabase.co:5432/postgres
NEXT_PUBLIC_SUPABASE_URL=https://[project].supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# Supabase Database Connection Details (for Grafana)
SUPABASE_DB_HOST=db.[project].supabase.co
SUPABASE_DB_NAME=postgres
SUPABASE_DB_USER=postgres
SUPABASE_DB_PASSWORD=your-database-password

# Grafana Configuration
GRAFANA_ADMIN_PASSWORD=your-secure-password
GRAFANA_SECRET_KEY=your-secret-key
GRAFANA_DOMAIN=your-domain.com  # or localhost for local testing

# CORS Origins (add your frontend domains)
CORS_ORIGINS=https://your-frontend.vercel.app,https://your-domain.com
```

### **External Services Setup:**

#### **Supabase Database:**
1. Create Supabase project at https://app.supabase.com
2. Run migration files from `setup/db/schema/` in Supabase SQL Editor
3. Get connection details from Supabase dashboard

#### **Frontend Connection:**
Configure your frontend to connect to the API:
```javascript
// Frontend environment variables
VITE_SERVER_URL=https://your-backend-server.com:5109
VITE_API_URL=https://your-backend-server.com:5109/api
```

#### **Grafana Access:**
- **Dashboard:** http://your-server:3001
- **Integrated:** http://your-server:5109/grafana
- **Login:** admin / [GRAFANA_ADMIN_PASSWORD]

---

## 🎯 **Setup 3: Backend Host (Device Controller Only)**

### **What You Get:**
- ✅ Backend Host (Device controller)
- ✅ Shared library (included in container)

### **External Dependencies:**
- **Backend Server** - Running separately (cloud or local)
- **Supabase Database** - For application data (optional direct access)

### **Ports:**
- **6109** - Backend Host device controller

### **Usage:**
```bash
# Easy way - Use launch script
./setup/docker/launch_backend_host.sh

# Manual way - Direct docker-compose commands
docker-compose -f setup/docker/docker-compose.backend-host.yml up -d
docker-compose -f setup/docker/docker-compose.backend-host.yml logs -f
docker-compose -f setup/docker/docker-compose.backend-host.yml down
```

### **Required Configuration:**

Create `.env` file in project root with:

```bash
# Backend Server Connection
SERVER_URL=https://your-backend-server.com:5109
# or for local: SERVER_URL=http://localhost:5109

# Host Identification
HOST_NAME=raspberry-pi-1  # Unique name for this host
HOST_URL=http://localhost:6109

# Device Configuration (configure for your hardware)
DEVICE1_NAME=Samsung_TV_Living_Room
DEVICE1_MODEL=Samsung_QN65Q80A
DEVICE1_VIDEO=/dev/video0  # HDMI capture device
DEVICE1_AUDIO=plughw:1,0   # Audio capture device
DEVICE1_REMOTE=ir_blaster   # Remote control method

# Optional: Direct Supabase access (if host needs direct DB access)
SUPABASE_DB_URI=postgresql://postgres:[password]@db.[project].supabase.co:5432/postgres
NEXT_PUBLIC_SUPABASE_URL=https://[project].supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

### **Hardware Requirements:**
- **HDMI Capture Card** - For video capture (`/dev/video*`)
- **Audio Capture** - For audio analysis (`plughw:*`)
- **IR Blaster/Network Control** - For device control
- **Privileged Access** - Container runs with `privileged: true`

### **External Services Setup:**

#### **Backend Server Connection:**
Ensure your backend server is accessible from the host location:
- **Cloud deployment:** Use HTTPS URL
- **Local network:** Use local IP address
- **VPN/Tunnel:** Configure secure connection

---

## 🚀 **Launch Scripts**

VirtualPyTest provides 3 focused launch scripts that make it easy to start the right setup:

### **1. `launch_standalone.sh` - Complete Local System**
```bash
./setup/docker/launch_standalone.sh
```
**What it does:**
- ✅ Checks Docker installation and prerequisites
- ✅ Starts complete VirtualPyTest system (all 5 containers)
- ✅ Shows all access points and URLs
- ✅ Provides helpful commands for logs and management
- ✅ Perfect for local development and testing

### **2. `launch_backend_server.sh` - API Server Only**
```bash
./setup/docker/launch_backend_server.sh
```
**What it does:**
- ✅ Checks Docker installation and prerequisites
- ✅ Validates .env configuration for Supabase
- ✅ Starts API server with Grafana monitoring
- ✅ Shows configuration requirements and external dependencies
- ✅ Perfect for cloud API deployment

### **3. `launch_backend_host.sh` - Device Controller Only**
```bash
./setup/docker/launch_backend_host.sh
```
**What it does:**
- ✅ Checks Docker installation and prerequisites
- ✅ Validates .env configuration for backend server connection
- ✅ Checks hardware access permissions
- ✅ Starts device controller with hardware access
- ✅ Perfect for Raspberry Pi and hardware deployments

### **Benefits of Launch Scripts:**
- **Validation:** Check prerequisites before starting
- **Configuration:** Warn about missing .env settings
- **Guidance:** Show what's running and how to access it
- **Troubleshooting:** Provide helpful commands and next steps
- **Simplicity:** One command instead of long docker-compose commands

---

## 🔧 **Common Configuration**

### **Environment Variables:**

All setups support these common variables in `.env`:

```bash
# Debug Mode
DEBUG=false  # Set to true for development

# Logging
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR

# Network Configuration
HOST_PORT=6109
SERVER_PORT=5109

# Security
CORS_ORIGINS=http://localhost:3000,https://your-frontend.com
```

### **Volume Persistence:**

Each setup creates named volumes for data persistence:
- **Standalone:** `virtualpytest-postgres-data`, `virtualpytest-grafana-data`
- **Backend Server:** `virtualpytest-backend-server-grafana-data`
- **Backend Host:** No persistent volumes (stateless)

### **Networking:**

Each setup creates its own Docker network:
- **Standalone:** `virtualpytest-standalone-network`
- **Backend Server:** `virtualpytest-backend-server-network`
- **Backend Host:** `virtualpytest-backend-host-network`

---

## 🚀 **Deployment Scenarios**

### **Scenario 1: Local Development**
```bash
# Use standalone for complete local development
docker-compose -f setup/docker/docker-compose.standalone.yml up
```
**Result:** Everything running locally, no external dependencies

### **Scenario 2: Cloud + Local Hardware**
```bash
# Deploy API to cloud
docker-compose -f setup/docker/docker-compose.backend-server.yml up

# Deploy controller to Raspberry Pi
docker-compose -f setup/docker/docker-compose.backend-host.yml up
```
**Result:** Scalable architecture with cloud API and distributed hardware

### **Scenario 3: Microservices Architecture**
```bash
# Multiple backend servers for load balancing
docker-compose -f setup/docker/docker-compose.backend-server.yml up

# Multiple hosts for different locations/devices
docker-compose -f setup/docker/docker-compose.backend-host.yml up
```
**Result:** Fully distributed system with independent scaling

---

## 🛠️ **Troubleshooting**

### **Common Issues:**

#### **Port Conflicts:**
```bash
# Check what's using ports
lsof -i :5109
lsof -i :6109
lsof -i :3000

# Stop conflicting services or change ports in compose file
```

#### **Database Connection Issues:**
```bash
# Test Supabase connection
psql "postgresql://postgres:[password]@db.[project].supabase.co:5432/postgres"

# Check environment variables
docker-compose -f setup/docker/docker-compose.backend-server.yml config
```

#### **Hardware Access Issues (Backend Host):**
```bash
# Check device permissions
ls -la /dev/video*
ls -la /dev/snd/

# Ensure Docker has hardware access
docker run --privileged --rm -it ubuntu ls /dev/
```

### **Logs and Debugging:**
```bash
# View logs for specific service
docker-compose -f setup/docker/docker-compose.standalone.yml logs backend_server

# Follow logs in real-time
docker-compose -f setup/docker/docker-compose.standalone.yml logs -f

# Debug container
docker-compose -f setup/docker/docker-compose.standalone.yml exec backend_server bash
```

---

## 📋 **Quick Reference**

### **File Structure:**
```
setup/docker/
├── docker-compose.standalone.yml     # Complete local system
├── docker-compose.backend-server.yml # API server only
├── docker-compose.backend-host.yml   # Device controller only
├── launch_standalone.sh              # Launch complete system
├── launch_backend_server.sh          # Launch API server only
├── launch_backend_host.sh            # Launch device controller only
├── install_docker.sh                 # Install Docker & Docker Compose
└── docker.md                         # This documentation
```

### **Launch Scripts (Recommended):**
```bash
# Complete local system
./setup/docker/launch_standalone.sh

# API server only (requires Supabase)
./setup/docker/launch_backend_server.sh

# Device controller only (requires backend server)
./setup/docker/launch_backend_host.sh
```

### **Manual Docker Compose Commands:**
```bash
# Standalone (everything local)
docker-compose -f setup/docker/docker-compose.standalone.yml up -d

# Backend Server (API + Grafana)
docker-compose -f setup/docker/docker-compose.backend-server.yml up -d

# Backend Host (device controller)
docker-compose -f setup/docker/docker-compose.backend-host.yml up -d

# Stop any setup
docker-compose -f setup/docker/docker-compose.[setup].yml down

# View logs
docker-compose -f setup/docker/docker-compose.[setup].yml logs -f
```

### **Access URLs:**
- **Frontend:** http://localhost:3000 (standalone only)
- **API:** http://localhost:5109
- **Device Controller:** http://localhost:6109
- **Grafana:** http://localhost:3001

Choose the setup that matches your deployment needs! 🚀
