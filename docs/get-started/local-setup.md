# 🏠 Local Development Setup

This guide walks you through setting up VirtualPyTest for local development. All components (Frontend, Backend Server, Backend Host) will run on your local machine.

## 📋 Prerequisites

Before starting, ensure you have:

- **Node.js** 18+ and npm installed
- **Python** 3.8+ installed  
- **Git** installed
- **Supabase project** set up ([follow this guide](./supabase-setup.md))

## 🚀 Quick Install

The fastest way to get everything running locally:

```bash
# Clone the repository
git clone <your-repo-url>
cd virtualpytest

# Install all components at once
./setup/local/install_local.sh

# Launch all services
./setup/local/launch_all.sh
```

That's it! The script will:
- ✅ Install Python dependencies in a virtual environment
- ✅ Install Node.js dependencies for frontend
- ✅ Set up all required configurations
- ✅ Launch all three services with unified logging

## 🌐 Access Your Services

After running the launch script, you can access:

- **Frontend**: http://localhost:3000
- **Backend Server**: http://localhost:5109  
- **Backend Host**: http://localhost:6409

## ⚙️ Environment Configuration

Before first use, configure your environment files:

### 1. Shared Configuration
Create `shared/.env`:
```bash
# Database Configuration
SUPABASE_URL=your_supabase_project_url
SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key

# Environment
ENVIRONMENT=development
DEBUG=true
```

### 2. Backend Server Configuration  
Create `backend_server/src/.env`:
```bash
# Server Configuration
SERVER_PORT=5109
DEBUG=true
ENVIRONMENT=development

# Database (inherits from shared)
# Add server-specific overrides here if needed

# External APIs
GITHUB_TOKEN=your_github_token_if_needed
```

### 3. Backend Host Configuration
Create `backend_host/src/.env`:
```bash
# Host Configuration  
HOST_PORT=6409
DEBUG=true
ENVIRONMENT=development

# Hardware Interface Settings
ADB_PATH=/usr/local/bin/adb
APPIUM_SERVER_URL=http://localhost:4723

# Device Control
DEFAULT_DEVICE_TIMEOUT=30
VIDEO_CAPTURE_ENABLED=true
```

### 4. Frontend Configuration
Create `frontend/.env`:
```bash
# API Endpoints
VITE_BACKEND_SERVER_URL=http://localhost:5109
VITE_BACKEND_HOST_URL=http://localhost:6409

# Environment
VITE_ENVIRONMENT=development
VITE_DEBUG=true
```

## 🔧 Manual Component Installation

If you prefer to install components individually:

### Install Shared Library
```bash
./setup/local/install_shared.sh
```

### Install Backend Server
```bash  
./setup/local/install_server.sh
```

### Install Backend Host
```bash
./setup/local/install_host.sh
```

### Install Frontend
```bash
./setup/local/install_frontend.sh
```

## 🚀 Manual Service Launch

Launch services individually:

### Launch All Services (Recommended)
```bash
./setup/local/launch_all.sh
```

### Launch Individual Services
```bash
# Backend Server only
./setup/local/launch_server.sh

# Backend Host only  
./setup/local/launch_host.sh

# Frontend only
./setup/local/launch_frontend.sh
```

## 🖥️ Hardware Setup (Raspberry Pi)

For full hardware integration on Raspberry Pi:

```bash
# Install host services (GPIO, camera, etc.)
./setup/local/install_host_services.sh
```

This sets up:
- GPIO control libraries
- Camera interface
- HDMI capture
- Device communication protocols

## 🐳 Docker Alternative

If you prefer Docker for local development:

```bash
# Build and launch all services
./setup/docker/launch_all.sh

# Or use docker-compose directly
docker-compose -f docker/docker-compose.dev.yml up
```

## 📊 Real-time Logging

The launch script provides unified logging with color-coded prefixes:

- 🔵 **[SERVER]** - Backend server logs
- 🟢 **[HOST]** - Backend host logs  
- 🟡 **[FRONTEND]** - Frontend logs

Press `Ctrl+C` to stop all services gracefully.

## 🔍 Troubleshooting

### Port Conflicts
If you get port conflicts, the launch script automatically kills processes on required ports:
- Port 3000 (Frontend)
- Port 5109 (Backend Server)
- Port 6409 (Backend Host)

### Missing Dependencies
```bash
# Reinstall everything
./setup/local/install_local.sh

# Or install specific components
./setup/local/install_shared.sh
./setup/local/install_server.sh
./setup/local/install_host.sh
./setup/local/install_frontend.sh
```

### Python Virtual Environment Issues
```bash
# Recreate virtual environment
rm -rf venv
./setup/local/install_local.sh
```

### Database Connection Issues
- Verify your Supabase configuration in `shared/.env`
- Check that your Supabase project is active
- Ensure all SQL schemas are applied ([Supabase setup guide](./supabase-setup.md))

## 🎯 Next Steps

1. **Verify Setup**: Open http://localhost:3000 and check all services are running
2. **Configure Devices**: Set up your test devices in the device management section
3. **Create Tests**: Start building your first automated test workflows
4. **Explore Features**: Try device control, monitoring, and verification features

## 🔗 Related Guides

- [Supabase Database Setup](./supabase-setup.md)
- [Cloud Deployment Setup](./cloud-setup.md)
- [Architecture Overview](../ARCHITECTURE_REDESIGN.md) 