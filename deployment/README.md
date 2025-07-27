# VirtualPyTest Deployment Configuration

This directory contains deployment configurations migrated from the old `config/` folder and adapted for the new microservices architecture.

## 📁 **Configuration Migration Map**

### Old → New Structure

```
config/
├── host_gninx.conf          → docker/nginx/backend_host.conf
├── server_gninx.conf        → docker/nginx/backend_server.conf  
├── service/*.service        → deployment/systemd/ (updated)
├── remote/appium_remote.json → shared/lib/config/devices/
├── vnc_lite_*.html          → frontend/public/
└── test_cases/              → Keep in config/ (test data)
```

## 🔧 **Systemd Services**

Updated service files for microservices architecture:

### backend_host (Raspberry Pi)
```bash
# Install service
sudo cp deployment/systemd/backend_host.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable backend_host
sudo systemctl start backend_host

# Check status
sudo systemctl status backend_host
sudo journalctl -u backend_host -f
```

### backend_server (Local Server)
```bash
# Install service  
sudo cp deployment/systemd/backend_server.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable backend_server
sudo systemctl start backend_server

# Check status
sudo systemctl status backend_server
sudo journalctl -u backend_server -f
```

## 🌐 **Nginx Configuration**

### For Docker Deployment
Nginx configs are automatically used in Docker containers via:
- `docker/nginx/backend_host.conf` - Host service reverse proxy
- `docker/nginx/backend_server.conf` - Server service reverse proxy

### For Manual Nginx Setup
```bash
# Copy configurations
sudo cp docker/nginx/backend_host.conf /etc/nginx/sites-available/
sudo cp docker/nginx/backend_server.conf /etc/nginx/sites-available/

# Enable sites
sudo ln -s /etc/nginx/sites-available/backend_host.conf /etc/nginx/sites-enabled/
sudo ln -s /etc/nginx/sites-available/backend_server.conf /etc/nginx/sites-enabled/

# Test and reload
sudo nginx -t
sudo systemctl reload nginx
```

## 🎛️ **Device Configuration**

Device configurations are now in shared library:
- `shared/lib/config/devices/appium_remote.json` - Appium device setup
- Accessible by all services that import shared library

## 📺 **VNC Interface**

VNC HTML files moved to frontend:
- `frontend/public/vnc_lite_host.html` - Host VNC interface
- `frontend/public/vnc_lite_server.html` - Server VNC interface

Access via: `http://your-frontend-url/vnc_lite_host.html`

## 🚀 **Deployment Options**

### Option 1: Full Cloud + RPi
```
Frontend (Vercel) → backend_server (Render) → backend_host (RPi systemd)
```

### Option 2: Docker Everything
```bash
cd docker
./scripts/deploy.sh production
```

### Option 3: Hybrid (Cloud + Local)
```
Frontend (Vercel) → backend_server (Local systemd) → backend_host (RPi systemd)
```

## 🔧 **Environment Variables**

Update service files with your actual URLs:

```bash
# backend_host.service
Environment=SERVER_URL=https://your-backend_server.onrender.com

# backend_server.service  
Environment=CORS_ORIGINS=https://your-frontend.vercel.app
```

## 📋 **Migration Checklist**

- [x] Move nginx configs to Docker nginx directory
- [x] Update systemd services for microservices
- [x] Move device configs to shared library
- [x] Move VNC files to frontend public
- [ ] Update environment variables in service files
- [ ] Test services individually
- [ ] Deploy and verify communication between services

## 🆘 **Troubleshooting**

### Service Logs
```bash
# backend_host
sudo journalctl -u backend_host -f

# backend_server
sudo journalctl -u backend_server -f
```

### Port Conflicts
```bash
# Check what's using ports
sudo netstat -tlnp | grep :6109  # backend_host
sudo netstat -tlnp | grep :5109  # backend_server
```

### Service Dependencies
Ensure services start in order:
1. backend_server (API)
2. backend_host (connects to server)
3. Frontend (connects to API) 