# 🐳 backend_host Docker Setup

Complete Docker configuration for VirtualPyTest `backend_host` - the hardware control and device management service.

---

## 📋 Overview

This Docker setup provides a **fully containerized backend_host** with:

- ✅ **Flask API** (port 6109) - Hardware control endpoints
- ✅ **NoVNC** (port 6080) - Web-based VNC access to virtual display
- ✅ **x11vnc** (port 5900) - VNC server for remote desktop
- ✅ **Xvfb** (display :1) - Virtual X11 display
- ✅ **Supervisor** - Process management for all services
- ✅ **ADB support** - Android device control
- ✅ **Hardware abstraction** - Camera, USB, power control

---

## 🗂️ Structure

```
backend_host/
└── docker/
    ├── Dockerfile              # Image definition
    ├── docker-compose.yml      # Service orchestration  
    ├── supervisord.conf        # Process manager config
    ├── scripts/                # Helper scripts
    │   ├── build.sh           # Build Docker image
    │   ├── run.sh             # Start with docker-compose
    │   ├── stop.sh            # Stop containers
    │   ├── restart.sh         # Restart containers
    │   ├── logs.sh            # View logs
    │   ├── test.sh            # Health checks
    │   ├── clean.sh           # Cleanup resources
    │   └── help.sh            # Show this help
    └── README.md               # This file
```

---

## 🚀 Quick Start

### **1. Prerequisites**

- Docker 20.10+
- Docker Compose 1.29+
- `.env` file in project root (see Environment Variables)

### **2. Build Image**

```bash
cd backend_host/docker
./scripts/build.sh
```

### **3. Start Services**

```bash
./scripts/run.sh
```

### **4. Verify Health**

```bash
./scripts/test.sh
```

### **5. Access Services**

- **Flask API**: http://localhost:6109/host/health
- **NoVNC**: http://localhost:6080
- **VNC Direct**: `vnc://localhost:5900`

---

## 🔧 Environment Variables

Create `.env` in **project root** (not in `docker/` folder):

```bash
# Required
HOST_NAME=docker-host
HOST_PORT=6109
HOST_URL=http://localhost:6109
SERVER_URL=http://localhost:5109

# Supabase (required)
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
DATABASE_URL=postgresql://postgres:password@host:5432/postgres

# Optional
DEBUG=false
FLASK_SECRET_KEY=your-secret-key

# Hardware (if using)
# ADB_HOST=localhost
# TAPO_USERNAME=your-username
# TAPO_PASSWORD=your-password
```

---

## 🛠️ Available Commands

### **Build & Run**
```bash
./scripts/build.sh       # Build Docker image
./scripts/run.sh         # Start with docker-compose
./scripts/stop.sh        # Stop containers
./scripts/restart.sh     # Restart containers
```

### **Management**
```bash
./scripts/logs.sh        # View logs (tail -f)
./scripts/test.sh        # Run health checks
./scripts/clean.sh       # Remove all Docker resources
./scripts/help.sh        # Show help message
```

---

## 🧪 Testing

### **Health Check**
```bash
curl http://localhost:6109/host/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "host_name": "docker-host",
  "services": {
    "flask": "running",
    "xvfb": "running",
    "x11vnc": "running",
    "novnc": "running"
  }
}
```

### **NoVNC Access**
1. Open browser: http://localhost:6080
2. Click "Connect"
3. You should see the virtual desktop

### **View Supervisor Status**
```bash
docker exec -it virtualpytest-backend-host supervisorctl status
```

---

## 📦 What's Inside

### **Supervisor Services**

The container runs 4 services managed by Supervisor:

1. **Xvfb** (priority 1)
   - Virtual X11 display on :1
   - Resolution: 1920x1080x24
   - Enables GUI applications without physical display

2. **x11vnc** (priority 2)
   - VNC server on port 5900
   - Shares the Xvfb display
   - No password (for development)

3. **NoVNC** (priority 3)
   - WebSocket proxy on port 6080
   - HTML5 VNC client
   - Access virtual desktop from browser

4. **Flask** (priority 4)
   - Hardware control API on port 6109
   - Routes: `/host/*`
   - WebSocket support

### **Logging**

All logs go to **stdout/stderr** for easy viewing:
```bash
./scripts/logs.sh
```

Or view specific service:
```bash
docker-compose logs flask
docker-compose logs novnc
```

---

## 🔐 Security Notes

- **Development setup**: NoVNC has no password, x11vnc has no password
- **Production**: Add authentication to VNC and use HTTPS for NoVNC
- **Supervisor runs as root** to manage services
- **All processes drop to `vptuser`** for security

---

## 🐛 Troubleshooting

### **Container won't start**
```bash
./scripts/logs.sh
# Look for errors in supervisor logs
```

### **Can't access Flask API**
```bash
curl http://localhost:6109/host/health
# Check if port 6109 is already in use
lsof -i :6109
```

### **NoVNC shows black screen**
```bash
docker exec -it virtualpytest-backend-host supervisorctl status
# Check if xvfb and x11vnc are running
```

### **Permission denied errors**
```bash
# Check volume permissions
docker exec -it virtualpytest-backend-host ls -la /var/www/html
```

### **Rebuild from scratch**
```bash
./scripts/clean.sh
./scripts/build.sh
./scripts/run.sh
```

---

## 🚢 Deployment to Render

### **1. Update `render.yaml`** (if it exists)

```yaml
services:
  - type: web
    name: backend-host
    env: docker
    dockerfilePath: ./backend_host/docker/Dockerfile
    dockerContext: .
    envVars:
      - key: HOST_NAME
        value: render-host
      - key: HOST_PORT
        value: 6109
      - key: HOST_URL
        sync: false
      - key: SERVER_URL
        sync: false
      - key: NEXT_PUBLIC_SUPABASE_URL
        sync: false
      - key: NEXT_PUBLIC_SUPABASE_ANON_KEY
        sync: false
      - key: DATABASE_URL
        sync: false
```

### **2. Push to Render**

```bash
git add .
git commit -m "feat: Add backend_host Docker setup"
git push
```

Render will automatically:
1. Detect `Dockerfile`
2. Build the image
3. Start the container
4. Run health checks

### **3. View Logs in Render**

All supervisor logs go to **stdout/stderr**, visible in Render dashboard.

---

## 📊 Resource Usage

- **Image size**: ~1.5GB (includes VNC, GUI libraries)
- **Memory**: ~500MB idle, ~1GB under load
- **CPU**: Low idle, scales with hardware operations

---

## 🔄 Development Workflow

### **Local Development with Hot Reload**

The `docker-compose.yml` mounts source directories as volumes:
```yaml
volumes:
  - ../../shared:/app/shared
  - ../src:/app/backend_host/src
  - ../scripts:/app/backend_host/scripts
```

**Workflow:**
1. Edit code locally
2. Restart Flask to pick up changes:
   ```bash
   docker exec virtualpytest-backend-host supervisorctl restart flask
   ```
3. Or restart all services:
   ```bash
   ./scripts/restart.sh
   ```

---

## 🧩 Integration with backend_server

The `backend_host` communicates with `backend_server`:

```bash
# Start both services
cd backend_server/docker && ./scripts/run.sh
cd backend_host/docker && ./scripts/run.sh

# They share the same network
docker network inspect virtualpytest_virtualpytest
```

**Communication:**
- `backend_host` → `backend_server`: HTTP requests to `SERVER_URL`
- `backend_server` → `backend_host`: HTTP requests to `HOST_URL`

---

## 📝 Notes

- **Xvfb display** is `:1` (set via `DISPLAY=:1`)
- **All logs** go to stdout for Render compatibility
- **Supervisor** manages process lifecycle and restarts
- **Non-root user** (`vptuser`) runs all services except supervisor
- **Health check** pings Flask API every 30s

---

## 🎯 Next Steps

- [ ] Test locally: `./scripts/test.sh`
- [ ] Add hardware device mappings in `docker-compose.yml`
- [ ] Configure ADB for Android devices
- [ ] Set up Tapo power control
- [ ] Deploy to Render
- [ ] Monitor logs and health checks

---

## 📚 Related Documentation

- [backend_server Docker Setup](../../backend_server/docker/README.md)
- [Project Root README](../../README.md)
- [Deployment Guide](../../docs/DEPLOYMENT_SYSTEM.md)

---

**Questions?** Check `./scripts/help.sh` or review supervisor logs with `./scripts/logs.sh`

