# ☁️ Cloud + Local Hybrid Setup

This guide shows you how to deploy VirtualPyTest in a production-ready hybrid setup:

- **Frontend**: Deployed on Vercel (global CDN)
- **Backend Server**: Deployed on Render (scalable API)
- **Backend Host**: Running locally (hardware access required)
- **Database**: Supabase (managed PostgreSQL)

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│    Frontend     │    │ Backend Server  │    │  Backend Host   │
│   (Vercel)      │◄──►│   (Render)      │◄──►│    (Local)      │
│                 │    │                 │    │                 │
│ • Global CDN    │    │ • Auto-scaling  │    │ • Hardware I/O  │
│ • Fast deploys  │    │ • SSL included  │    │ • Device control│
│ • Branch preview│    │ • Zero downtime │    │ • Local network │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 ▼
                    ┌─────────────────┐
                    │    Supabase     │
                    │   (PostgreSQL)  │
                    │                 │
                    │ • Managed DB    │
                    │ • Auto backups  │
                    │ • Global edge   │
                    └─────────────────┘
```

## 📋 Prerequisites

- **Vercel account** (free tier available)
- **Render account** (free tier available)  
- **Supabase project** ([setup guide](./supabase-setup.md))
- **Local machine** for Backend Host (hardware access)
- **GitHub repository** with your VirtualPyTest code

## 🚀 Step 1: Deploy Backend Server to Render

### 1.1 Create Render Service

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository
4. Configure the service:

   - **Name**: `virtualpytest-backend-server`
   - **Region**: Choose closest to your users
   - **Branch**: `main` (or your production branch)
   - **Root Directory**: `backend_server`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python src/app.py`

### 1.2 Configure Environment Variables

In Render dashboard, add these environment variables:

```bash
# Server Configuration
SERVER_PORT=5109
DEBUG=false
ENVIRONMENT=production
RENDER=true

# Database Configuration  
SUPABASE_URL=your_supabase_project_url
SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key

# Python Path
PYTHONPATH=/opt/render/project/src:/opt/render/project

# Optional: GitHub integration
GITHUB_TOKEN=your_github_token_if_needed
```

### 1.3 Deploy

Click **"Create Web Service"**. Render will:
- ✅ Build your application
- ✅ Deploy to a global URL (e.g., `https://virtualpytest-backend-server.onrender.com`)
- ✅ Provide SSL certificate automatically
- ✅ Set up auto-deploys from your Git branch

## 🌐 Step 2: Deploy Frontend to Vercel

### 2.1 Prepare Frontend for Deployment

First, update your frontend environment configuration. Create `frontend/.env.production`:

```bash
# API Endpoints (use your actual backend server URL)
VITE_SERVER_URL=https://virtualpytest-backend-server.onrender.com
VITE_DEV_MODE=false
```

### 2.2 Create Vercel Project

1. Go to [Vercel Dashboard](https://vercel.com/dashboard)
2. Click **"New Project"**
3. Import your GitHub repository
4. Configure the project:

   - **Framework Preset**: `Vite`
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
   - **Install Command**: `npm install`

### 2.3 Configure Environment Variables

In Vercel project settings, add environment variables:

```bash
# API Endpoints
VITE_SERVER_URL=https://virtualpytest-backend-server.onrender.com
VITE_DEV_MODE=false
```

### 2.4 Deploy

Click **"Deploy"**. Vercel will:
- ✅ Build your React application
- ✅ Deploy to global CDN
- ✅ Provide custom domain (e.g., `https://virtualpytest.vercel.app`)
- ✅ Set up automatic deployments from Git
- ✅ Create preview deployments for pull requests

## 🏠 Step 3: Set Up Backend Host

The Backend Host can run locally (for hardware access) or on cloud runners (for testing).

### 3.1 Option A: Local Installation (Hardware Access)

```bash
# Clone repository (if not already done)
git clone <your-repo-url>
cd virtualpytest

# Install only the host component
./setup/local/install_host.sh
```

### 3.2 Option B: Docker Deployment (Local or Cloud)

#### **Local Docker Deployment**
```bash
# Quick setup with Docker
./setup/docker/install_docker.sh
./setup/docker/launch_all.sh
```

#### **Cloud Runner Docker Deployment**

**For Render (Docker Environment):**

1. **Create Docker Web Service** on Render dashboard
2. **Configure Service Settings**:
   - **Environment**: Select **"Docker"** 
   - **Root Directory**: Leave **EMPTY**
   - **Dockerfile Path**: `backend_host/Dockerfile`
   - **Port**: 6109

3. **Configuration**:
   - Configure your `backend_host/src/.env` file before building
   - For minimal config: Use default .env (VNC only)
   - For full config: Add DEVICE* variables to .env file

**Example .env for cloud deployment:**
```bash
# Host Configuration
HOST_NAME=render-host-1
HOST_PORT=6109
HOST_URL=https://your-host-service.onrender.com
SERVER_URL=https://your-backend-server.onrender.com
DEBUG=false

# Optional: Video devices (for full config)
# DEVICE1_VIDEO=/dev/video0
# DEVICE1_VIDEO_CAPTURE_PATH=/var/www/html/stream/capture1
```

**For AWS/GCP/Azure:**
```bash
# Build and deploy container
docker build -f backend_host/Dockerfile -t virtualpytest/backend_host .
docker run -d -p 6109:6109 -p 6080:6080 virtualpytest/backend_host
```

### 3.3 Configure Backend Host

Create `backend_host/src/.env`:

#### **Minimal Configuration (VNC Only)**
```bash
# Host Configuration
HOST_NAME=my-host
HOST_PORT=6109
DEBUG=false

# Database Configuration
NEXT_PUBLIC_SUPABASE_URL=your_supabase_project_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
```

#### **Full Configuration (VNC + Video + Monitor)**
```bash
# Host Configuration
HOST_NAME=my-host
HOST_PORT=6109
DEBUG=false

# Database Configuration
NEXT_PUBLIC_SUPABASE_URL=your_supabase_project_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key

# Device 1 - Video capture configuration
DEVICE1_VIDEO=/dev/video0
DEVICE1_AUDIO=plughw:2,0
DEVICE1_VIDEO_CAPTURE_PATH=/var/www/html/stream/capture1
DEVICE1_FPS=10

# Device 2 - Additional video device (optional)
DEVICE2_VIDEO=/dev/video2
DEVICE2_AUDIO=plughw:3,0
DEVICE2_VIDEO_CAPTURE_PATH=/var/www/html/stream/capture2
DEVICE2_FPS=10

# Optional: Cloud Storage & AI
CLOUDFLARE_R2_ENDPOINT=your_r2_endpoint
CLOUDFLARE_R2_ACCESS_KEY_ID=your_access_key
CLOUDFLARE_R2_SECRET_ACCESS_KEY=your_secret_key
OPENROUTER_API_KEY=your_openrouter_key
```

**Note**: Backend Host automatically detects which services to start based on your configuration:
- **No DEVICE variables**: Only VNC services (minimal)
- **With DEVICE variables**: VNC + Video capture + Monitor services

### 3.4 Launch Backend Host

#### **Local Launch**
```bash
# Launch only the host service
./setup/local/launch_host.sh

# Or run directly
cd backend_host
source ../venv/bin/activate
python src/app.py
```

#### **Docker Launch**
```bash
# Quick Docker launch (all services)
./setup/docker/launch_all.sh

# Or just backend_host
cd docker
docker compose up backend_host
```

### 3.5 Access Backend Host Services

Once running, you can access:

- **API Endpoints**: `http://localhost:6109/host/*`
- **NoVNC Web Desktop**: `http://localhost:6080` (virtual desktop access)
- **Health Check**: `http://localhost:6109/host/health`

### 3.6 Expose Host to Internet (Optional)

If you need to access the Backend Host from outside your local network:

#### Option A: ngrok (Recommended for testing)
```bash
# Install ngrok
npm install -g ngrok

# Expose local host (API + NoVNC)
ngrok http 6109
ngrok http 6080  # In separate terminal for NoVNC
```

Update your frontend environment with the ngrok URL:
```bash
VITE_SERVER_URL=https://your-ngrok-url.ngrok.io
```

#### Option B: Port Forwarding
Configure your router to forward ports 6109 and 6080 to your local machine:
```bash
VITE_SERVER_URL=http://your-public-ip:6109
# NoVNC available at: http://your-public-ip:6080
```

#### Option C: Cloud Deployment (Render)
Deploy Backend Host directly to Render using Docker (see Step 3.2 above)

## 🔧 Step 4: Configure Cross-Service Communication

### 4.1 Update CORS Settings

In your **Backend Server** (Render), ensure CORS allows your Vercel domain:

```python
# In backend_server/src/app.py
from flask_cors import CORS

CORS(app, origins=[
    "https://virtualpytest.vercel.app",  # Your Vercel domain
    "http://localhost:3000",             # Local development
    "http://localhost:6409"              # Local host
])
```

### 4.2 Update API Endpoints

Ensure your **Frontend** uses the correct API endpoints:

```typescript
// In frontend/src/services/apiClient.ts
const SERVER_URL = import.meta.env.VITE_SERVER_URL || 'http://localhost:5109';
```

## 🔄 Step 5: Set Up Continuous Deployment

### 5.1 Automatic Deployments

Both Vercel and Render automatically deploy when you push to your connected Git branch:

- **Push to main** → Production deployment
- **Push to dev** → Staging deployment (configure separate services)
- **Pull requests** → Preview deployments (Vercel)

### 5.2 Environment-Specific Configurations

Create branch-specific environment variables:

#### Production Branch (`main`)
```bash
VITE_SERVER_URL=https://your-production-server.com
VITE_DEV_MODE=false
```

#### Staging Branch (`dev`)  
```bash
VITE_SERVER_URL=https://your-staging-server.com
VITE_DEV_MODE=true
```

## 📊 Step 6: Monitoring and Maintenance

### 6.1 Service Health Checks

Monitor your deployments:

- **Render**: Built-in health checks and logs
- **Vercel**: Analytics and function logs
- **Supabase**: Database metrics and logs

### 6.2 Scaling Considerations

- **Render**: Automatically scales based on traffic
- **Vercel**: Edge functions scale automatically  
- **Backend Host**: Consider multiple local instances for redundancy

## 🔍 Troubleshooting

### Common Issues

#### CORS Errors
- Verify CORS origins in backend server
- Check environment variable URLs
- Ensure HTTPS/HTTP protocol matching

#### Database Connection Issues
- Verify Supabase URLs and keys
- Check IP allowlists in Supabase
- Test connection from each service

#### Local Host Connectivity
- Ensure Backend Host is running locally
- Check firewall settings
- Verify port forwarding if needed

### Health Check URLs

Test your deployments:

```bash
# Backend Server (Render)
curl https://virtualpytest-backend-server.onrender.com/health

# Frontend (Vercel)  
curl https://virtualpytest.vercel.app

# Backend Host (Local)
curl http://localhost:6109/host/health

# NoVNC Web Desktop (Local)
curl http://localhost:6080
```

## 🎯 Production Checklist

Before going live:

- [ ] All environment variables configured
- [ ] CORS properly set up
- [ ] Database schemas applied
- [ ] SSL certificates active (automatic)
- [ ] Health checks passing
- [ ] Monitoring set up
- [ ] Backup strategy in place
- [ ] Local host service running reliably

## 🔗 Next Steps

1. **Custom Domain**: Set up custom domains in Vercel/Render
2. **Monitoring**: Add application monitoring (Sentry, LogRocket)
3. **CI/CD**: Set up testing pipelines
4. **Scaling**: Configure auto-scaling rules
5. **Security**: Review security settings and access controls

## 🔗 Related Guides

- [Supabase Database Setup](./supabase-setup.md)
- [Local Development Setup](./local-setup.md)
- [Architecture Overview](../ARCHITECTURE_REDESIGN.md) 