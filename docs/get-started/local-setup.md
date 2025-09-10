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
./setup/local/install_all.sh

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
- **Backend Host**: http://localhost:6109
- **NoVNC (Virtual Desktop)**: http://localhost:6080

## ⚙️ Environment Configuration

Before first use, configure your environment files:

### 1. Project-Level Configuration
Create `.env` in project root:
```bash
# Copy from template
cp .env.example .env

# Edit with your values - used by backend_server, backend_core, shared:
NEXT_PUBLIC_SUPABASE_URL=https://your-project-id.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key_here
CLOUDFLARE_R2_ENDPOINT=https://your-account-id.r2.cloudflarestorage.com
CLOUDFLARE_R2_ACCESS_KEY_ID=your_r2_access_key_id
CLOUDFLARE_R2_SECRET_ACCESS_KEY=your_r2_secret_access_key
CLOUDFLARE_R2_PUBLIC_URL=https://pub-your-bucket-id.r2.dev
OPENROUTER_API_KEY=your_openrouter_api_key_here
SERVER_URL=http://localhost:5109
SERVER_PORT=5109
FLASK_SECRET_KEY=your_flask_secret_key_here
ENVIRONMENT=development
DEBUG=true
```

### 2. Backend Host Configuration
Create `backend_host/src/.env`:
```bash
# Copy from template
cp backend_host/src/env.example backend_host/src/.env

# Edit with your values - based on actual env.example:
HOST_URL=http://localhost:6109
HOST_PORT=6109
HOST_NAME=my-host-1

# Device Configuration (uncomment and configure for video capture)
# DEVICE1_NAME=device_name
# DEVICE1_MODEL=android_mobile
# DEVICE1_IP=192.168.1.x
# DEVICE1_PORT=8100
# DEVICE1_VIDEO=/dev/video0
# DEVICE1_VIDEO_STREAM_PATH=/host/stream/capture1
# DEVICE1_VIDEO_CAPTURE_PATH=/var/www/html/stream/capture1
```

**Service Configuration:**
- **Minimal Config**: Default .env (VNC services only)
- **Full Config**: Uncomment DEVICE* variables for video capture + monitoring

### 3. Frontend Configuration
Create `frontend/.env`:
```bash
# Copy from template
cp frontend/.env.example frontend/.env

# Edit with your values:
VITE_SERVER_URL=http://localhost:5109
VITE_DEV_MODE=true
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
docker-compose -f setup/docker/docker-compose.dev.yml up
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
./setup/local/install_all.sh

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
./setup/local/install_all.sh
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