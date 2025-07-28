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
# API Endpoints (use your Render URL)
VITE_BACKEND_SERVER_URL=https://virtualpytest-backend-server.onrender.com
VITE_BACKEND_HOST_URL=http://localhost:6409

# Environment
VITE_ENVIRONMENT=production
VITE_DEBUG=false
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
VITE_BACKEND_SERVER_URL=https://virtualpytest-backend-server.onrender.com
VITE_BACKEND_HOST_URL=http://localhost:6409

# Environment
VITE_ENVIRONMENT=production  
VITE_DEBUG=false
```

### 2.4 Deploy

Click **"Deploy"**. Vercel will:
- ✅ Build your React application
- ✅ Deploy to global CDN
- ✅ Provide custom domain (e.g., `https://virtualpytest.vercel.app`)
- ✅ Set up automatic deployments from Git
- ✅ Create preview deployments for pull requests

## 🏠 Step 3: Set Up Local Backend Host

The Backend Host must run locally to access hardware (cameras, devices, etc.).

### 3.1 Install Backend Host Locally

```bash
# Clone repository (if not already done)
git clone <your-repo-url>
cd virtualpytest

# Install only the host component
./setup/local/install_host.sh
```

### 3.2 Configure Backend Host

Create `backend_host/src/.env`:

```bash
# Host Configuration
HOST_PORT=6409
DEBUG=false
ENVIRONMENT=production

# Database Configuration
SUPABASE_URL=your_supabase_project_url
SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key

# Hardware Interface Settings
ADB_PATH=/usr/local/bin/adb
APPIUM_SERVER_URL=http://localhost:4723

# Device Control
DEFAULT_DEVICE_TIMEOUT=30
VIDEO_CAPTURE_ENABLED=true

# CORS - Allow your Vercel frontend
CORS_ORIGINS=https://virtualpytest.vercel.app,http://localhost:3000
```

### 3.3 Launch Backend Host

```bash
# Launch only the host service
./setup/local/launch_host.sh

# Or run directly
cd backend_host
source ../venv/bin/activate
python src/app.py
```

### 3.4 Expose Host to Internet (Optional)

If you need to access the Backend Host from outside your local network:

#### Option A: ngrok (Recommended for testing)
```bash
# Install ngrok
npm install -g ngrok

# Expose local host
ngrok http 6409
```

Update your frontend environment with the ngrok URL:
```bash
VITE_BACKEND_HOST_URL=https://your-ngrok-url.ngrok.io
```

#### Option B: Port Forwarding
Configure your router to forward port 6409 to your local machine, then update:
```bash
VITE_BACKEND_HOST_URL=http://your-public-ip:6409
```

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
const BACKEND_SERVER_URL = import.meta.env.VITE_BACKEND_SERVER_URL || 'http://localhost:5109';
const BACKEND_HOST_URL = import.meta.env.VITE_BACKEND_HOST_URL || 'http://localhost:6409';
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
VITE_ENVIRONMENT=production
DEBUG=false
```

#### Staging Branch (`dev`)  
```bash
VITE_ENVIRONMENT=staging
DEBUG=true
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
curl http://localhost:6409/health
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