# VirtualPyTest Backend Server - Docker Configuration

## 🎯 **Overview**

This document explains the Docker configuration for the VirtualPyTest backend server, designed for deployment on **Render** with **nginx reverse proxy**. The container runs nginx, Flask API and Grafana using supervisor for process management.

## 🏗️ **Architecture**

### **Deployment Flow:**
```
Internet → Render Load Balancer → Docker Container
                                     │
                                     ├─ nginx (port 80) ← Entry point
                                     ├─ Flask API (port 5110) ← Internal service
                                     └─ Grafana (port 3000) ← Internal service
```

### **Service Communication:**
```
External Requests:
- https://virtualpytest.onrender.com/server/* → nginx → Flask API
- https://virtualpytest.onrender.com/grafana/* → nginx → Flask → Grafana (proxy)

Internal Services:
- nginx: localhost:80 (exposed to Render)
- Flask: localhost:5110 (internal only)
- Grafana: localhost:3000 (internal only)
```

## 📦 **Container Components**

### **Services Managed by Supervisor:**
1. **nginx** - Reverse proxy and routing
2. **Flask API** - Main backend service  
3. **Grafana** - Monitoring and dashboards

### **Key Features:**
- ✅ **nginx reverse proxy** - Handles /server/ URL routing
- ✅ **Flask API** - Port 5110 internal service
- ✅ **Grafana integration** - Accessible via /grafana/ routes
- ✅ **Proper URL routing** - Strips /server/ prefix for Flask

## 🔧 **Configuration Files**

### **1. Dockerfile**
```dockerfile
# Key changes:
- Removed nginx installation
- Removed nginx configuration copying
- Changed EXPOSE to 10000 (single port)
- Updated health check to Flask directly
- Uses supervisord-no-nginx.conf
```

### **2. Supervisor Configuration** (`supervisord-no-nginx.conf`)
```ini
[program:flask]
command=python src/app.py
environment=SERVER_PORT="10000"  # ← Changed from 5110 to 10000

[program:grafana]
command=/usr/share/grafana/bin/grafana-server
environment=GF_SERVER_HTTP_PORT="3000"  # ← Internal port only
```

### **3. Flask Application** (`src/app.py`)
```python
# Added Grafana proxy routes:
@app.route('/grafana/')
@app.route('/grafana/<path:path>')
def grafana_proxy(path=''):
    # Proxies requests to localhost:3000
```

## 🚀 **Deployment Process**

### **Render Configuration** (`render.yaml`)
```yaml
services:
  - type: web
    name: virtualpytest-backend-server
    env: docker
    dockerfilePath: ./backend_server/Dockerfile
    dockerContext: .
    plan: free
    region: oregon
    branch: dev
    envVars:
      - key: SERVER_PORT
        value: 10000  # ← Must match Dockerfile EXPOSE
```

### **Build Process:**
1. **Base Image**: `python:3.11-slim`
2. **Install Dependencies**: System packages + Grafana
3. **Copy Code**: shared, backend_host, backend_server
4. **Setup Permissions**: User accounts and file permissions
5. **Configure Supervisor**: Process management without nginx
6. **Expose Port**: 10000 for Flask API

## 🔍 **Service Details**

### **Flask API Service**
- **Port**: 10000 (exposed to Render)
- **User**: vptuser
- **Working Directory**: `/app/backend_server`
- **Environment**: Production with full PYTHONPATH
- **Health Check**: `curl -f http://localhost:10000/health`

### **Grafana Service**
- **Port**: 3000 (internal only)
- **User**: grafana
- **Config**: `/app/backend_server/config/grafana/grafana.ini`
- **Data**: `/app/backend_server/config/grafana/data`
- **Access**: Via Flask proxy at `/grafana/*`

## 🌐 **URL Routing**

### **External URLs:**
- **API Endpoints**: `https://virtualpytest.onrender.com/server/system/getAllHosts`
- **Health Check**: `https://virtualpytest.onrender.com/health`
- **Grafana**: `https://virtualpytest.onrender.com/grafana/`

### **Internal Routing:**
```
Request: /server/system/getAllHosts
→ Render routes to Flask:10000
→ Flask handles directly

Request: /grafana/dashboard/xyz
→ Render routes to Flask:10000
→ Flask proxies to Grafana:3000
→ Returns Grafana response
```

## 🔧 **Environment Variables**

### **Required in Render Dashboard:**
```bash
SERVER_PORT=10000                    # Flask port
NEXT_PUBLIC_SUPABASE_URL=https://... # Database URL
NEXT_PUBLIC_SUPABASE_ANON_KEY=...    # Database key
DEBUG=false                          # Production mode
RENDER=true                          # Platform flag
```

### **Container Environment:**
```bash
PYTHONPATH="/app/shared:/app/shared/lib:/app/backend_host/src"
FLASK_ENV="production"
PYTHONUNBUFFERED="1"
GF_PATHS_CONFIG="/app/backend_server/config/grafana/grafana.ini"
GF_PATHS_DATA="/app/backend_server/config/grafana/data"
GF_SERVER_HTTP_PORT="3000"
```

## 🐛 **Debugging**

### **Check Service Status:**
```bash
# In Render console
supervisorctl status

# Expected output:
# flask    RUNNING   pid 123, uptime 0:05:00
# grafana  RUNNING   pid 456, uptime 0:05:00
```

### **View Logs:**
```bash
# Flask logs
tail -f /var/log/supervisor/flask.log

# Grafana logs  
tail -f /var/log/supervisor/grafana.log

# Supervisor logs
tail -f /var/log/supervisor/supervisord.log
```

### **Test Services:**
```bash
# Test Flask directly
curl http://localhost:10000/health

# Test Grafana directly
curl http://localhost:3000/api/health

# Test Grafana proxy
curl http://localhost:10000/grafana/api/health
```

## 📊 **Performance Benefits**

### **Compared to nginx Setup:**
- ✅ **Faster startup** - No nginx configuration parsing
- ✅ **Lower memory** - One less process (nginx)
- ✅ **Simpler debugging** - Direct Flask logs
- ✅ **Better health checks** - Direct to application
- ✅ **Fewer failure points** - Less complex routing

### **Resource Usage:**
- **Flask Process**: ~50-100MB RAM
- **Grafana Process**: ~100-200MB RAM
- **Supervisor**: ~5-10MB RAM
- **Total**: ~155-310MB RAM (vs ~200-400MB with nginx)

## 🚨 **Important Notes**

### **Port Configuration:**
- **CRITICAL**: `SERVER_PORT` in supervisor must match `EXPOSE` in Dockerfile
- **CRITICAL**: Render routes to the exposed port (10000)
- **Internal**: Grafana runs on 3000 but not exposed

### **Grafana Access:**
- **External**: Only via Flask proxy (`/grafana/*`)
- **Internal**: Direct access on port 3000
- **Security**: Grafana not directly exposed to internet

### **Health Checks:**
- **Render**: Checks Flask on port 10000
- **Flask**: Must respond to `/health` endpoint
- **Grafana**: Monitored by supervisor, not Render

## 🔄 **Migration from nginx Setup**

### **What Changed:**
1. **Removed nginx** from Dockerfile
2. **Changed Flask port** from 5109 to 10000
3. **Added Grafana proxy** in Flask application
4. **Simplified supervisor** configuration
5. **Updated health checks** to Flask directly

### **What Stayed:**
1. **Supervisor** for process management
2. **Grafana** installation and configuration
3. **User permissions** and security setup
4. **Directory structure** and file organization

## 🎯 **Best Practices**

### **Development:**
- Test locally with same port configuration
- Use Docker Compose for local development
- Match production environment variables

### **Production:**
- Monitor both Flask and Grafana processes
- Set up proper logging and alerting
- Use health checks for auto-restart

### **Security:**
- Grafana not directly exposed
- Proper user permissions in container
- Environment variables for sensitive data

This configuration provides a **clean, efficient, and maintainable** Docker setup optimized for Render deployment without the complexity of nginx reverse proxy.
