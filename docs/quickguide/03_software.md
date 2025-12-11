# QuickGuide 3: Software Setup

> **Purpose**: Software stack installation and deployment for VirtualPyTest  
> **Audience**: Developers, DevOps, System Administrators

---

## Overview

### Stack Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            VIRTUALPYTEST STACK                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐        │
│   │    Frontend     │    │ Backend Server  │    │  Backend Host   │        │
│   │   (React/TS)    │◄──►│   (Flask/Py)    │◄──►│   (Flask/Py)    │        │
│   │                 │    │                 │    │                 │        │
│   │ • Vite          │    │ • REST API      │    │ • Device Control│        │
│   │ • Material-UI   │    │ • WebSocket     │    │ • VNC Server    │        │
│   │ • TypeScript    │    │ • Grafana       │    │ • FFmpeg        │        │
│   │                 │    │                 │    │ • NoVNC         │        │
│   │ Port: 3000      │    │ Port: 5109      │    │ Port: 6109+     │        │
│   └─────────────────┘    └────────┬────────┘    └─────────────────┘        │
│                                   │                                         │
│                          ┌────────▼────────┐                                │
│                          │  Shared Library │                                │
│                          │  (Python)       │                                │
│                          │                 │                                │
│                          │ • Config        │                                │
│                          │ • Models        │                                │
│                          │ • Utils         │                                │
│                          └─────────────────┘                                │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                           EXTERNAL SERVICES                                 │
│                                                                             │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                    │
│   │  Supabase   │    │ Cloudflare  │    │ OpenRouter  │                    │
│   │ (PostgreSQL)│    │     R2      │    │  (AI/LLM)   │                    │
│   │             │    │  (Storage)  │    │             │                    │
│   │ Database    │    │ Screenshots │    │ GPT-4o      │                    │
│   │ Auth        │    │ Videos      │    │ Claude      │                    │
│   │ Real-time   │    │ Logs        │    │ Gemini      │                    │
│   └─────────────┘    └─────────────┘    └─────────────┘                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Deployment Options

| Option | Use Case | Command | External DB |
|--------|----------|---------|-------------|
| **Standalone** | Local dev, POC | `./setup/docker/standalone_server_host/launch.sh` | No (local PostgreSQL) |
| **Hetzner** | Cloud production | `./setup/docker/hetzner_custom/launch.sh` | Yes (Supabase) |
| **Proxmox** | VM-based, scalable | See DEPLOYMENT_GUIDE.md | Yes (Supabase) |
| **Local (no Docker)** | Development | `./setup/local/install_all.sh` | Optional |

---

## Part A: Prerequisites

### System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **OS** | Ubuntu 20.04 / Debian 11 | Ubuntu 22.04 / 24.04 |
| **CPU** | 2 cores | 4+ cores |
| **RAM** | 4GB | 8GB+ |
| **Storage** | 20GB | 50GB+ SSD |
| **Docker** | 20.10+ | 24.0+ |
| **Docker Compose** | 2.0+ | 2.20+ |

### OS-Level Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Core dependencies
sudo apt install -y \
    build-essential \
    git \
    curl \
    wget \
    software-properties-common

# Video processing
sudo apt install -y \
    ffmpeg \
    imagemagick

# OCR (for screen text extraction)
sudo apt install -y \
    tesseract-ocr \
    tesseract-ocr-eng

# VNC (for Backend Host)
sudo apt install -y \
    tigervnc-standalone-server \
    xvfb \
    fluxbox \
    novnc \
    websockify

# File monitoring
sudo apt install -y \
    inotify-tools \
    lsof \
    net-tools
```

### Docker Installation

```bash
# Quick install
curl -fsSL https://get.docker.com | sh

# Add user to docker group
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt install -y docker-compose-plugin

# Verify
docker --version
docker compose version

# Or use VirtualPyTest script
./setup/docker/install_docker.sh
```

---

## Part B: Standalone Deployment

### Quick Start (Docker)

```bash
# 1. Clone repository
git clone https://github.com/angelstreet/virtualpytest.git
cd virtualpytest

# 2. Install Docker (if needed)
./setup/docker/install_docker.sh

# 3. Launch everything
./setup/docker/standalone_server_host/launch.sh
```

**Access Points:**
| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend Server | http://localhost:5109 |
| Backend Host | http://localhost:6109 |
| Grafana | http://localhost:3001 |
| NoVNC | http://localhost:6080 |

### Manual Installation (Local)

```bash
# 1. Clone repository
git clone https://github.com/angelstreet/virtualpytest.git
cd virtualpytest

# 2. Install everything (creates venv, installs deps, sets up DB)
./setup/local/install_all.sh

# 3. Launch all services
./scripts/launch_virtualpytest.sh
```

### Service Architecture (Standalone)

```
┌─────────────────────────────────────────────────────────────┐
│                    DOCKER COMPOSE                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   frontend   │  │backend_server│  │ backend_host │      │
│  │    :3000     │  │    :5109     │  │    :6109     │      │
│  │              │  │    :3001     │  │    :6080     │      │
│  │   (nginx)    │  │  (gunicorn)  │  │  (gunicorn)  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│         │                 │                 │               │
│         └─────────────────┼─────────────────┘               │
│                           │                                 │
│                    Docker Network                           │
│                  (virtualpytest-net)                        │
│                           │                                 │
│              ┌────────────┴────────────┐                    │
│              │                         │                    │
│       ┌──────▼──────┐          ┌───────▼──────┐            │
│       │  postgres   │          │ postgres_gf  │            │
│       │    :5432    │          │    :5433     │            │
│       │ (app data)  │          │  (grafana)   │            │
│       └─────────────┘          └──────────────┘            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Configuration Files

| File | Purpose | Required |
|------|---------|----------|
| `.env` | Main configuration (project root) | Yes |
| `backend_host/.env` | Host-specific settings | Optional |
| `frontend/.env` | Frontend settings | Optional |
| `config.env` | Deployment config (Hetzner) | Hetzner only |

**Example `.env`:**
```bash
# Database (Standalone uses local, Hetzner uses Supabase)
DATABASE_URL=postgresql://user:pass@localhost:5432/virtualpytest

# Supabase (for Hetzner/Production)
SUPABASE_DB_URI=postgresql://postgres:xxx@db.xxx.supabase.co:5432/postgres
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=xxx
SUPABASE_SERVICE_ROLE_KEY=xxx

# Storage (Cloudflare R2)
CLOUDFLARE_R2_ENDPOINT=https://xxx.r2.cloudflarestorage.com
CLOUDFLARE_R2_ACCESS_KEY_ID=xxx
CLOUDFLARE_R2_SECRET_ACCESS_KEY=xxx

# AI (OpenRouter)
OPENROUTER_API_KEY=xxx

# Security
API_KEY=your-secure-api-key

# Grafana
GRAFANA_ADMIN_PASSWORD=admin123
```

---

## Part C: Production Deployment

### Hetzner/Cloud Setup

```bash
# 1. Clone on server
git clone https://github.com/angelstreet/virtualpytest.git
cd virtualpytest

# 2. Install Docker
./setup/docker/install_docker.sh

# 3. Configure deployment
cd setup/docker/hetzner_custom
cp config.env.example config.env
nano config.env
```

**config.env:**
```bash
# Server identity
SERVER_NAME=production1

# Hosts configuration
HOST_MAX=4                    # Number of backend hosts
HOST_START_PORT=6109          # First host port

# Domain
DOMAIN=api.yourdomain.com

# Optional features
ENABLE_GRAFANA=true
ENABLE_LANGFUSE=false
USE_VPN=false
```

```bash
# 4. Create main .env
cp setup/docker/hetzner_custom/env.example .env
nano .env  # Add Supabase credentials

# 5. Run setup (generates nginx, docker-compose, host configs)
./setup.sh

# 6. Setup SSL
sudo certbot --nginx -d api.yourdomain.com

# 7. Launch
./launch.sh
```

### Multi-Host Configuration

**Generated files after `setup.sh`:**
```
setup/docker/hetzner_custom/
├── docker-compose.yml        # Generated for N hosts
├── docker-compose.dev.yml    # Dev mode with mounted source
├── host-nginx.conf           # Nginx config for N hosts
└── ...

backend_host_1/.env           # Host 1 config
backend_host_2/.env           # Host 2 config
backend_host_3/.env           # Host 3 config
backend_host_4/.env           # Host 4 config
```

**Host .env example (auto-generated):**
```bash
SERVER_URL=http://backend_server:5109
HOST_NAME=production1-host1
HOST_PORT=6109
HOST_URL=https://api.yourdomain.com/host1
HOST_VNC_STREAM_PATH=https://api.yourdomain.com/host1/vnc/vnc_lite.html
API_KEY=your-secure-api-key
```

### Scaling Hosts

```bash
# Edit config
nano config.env
# Change: HOST_MAX=4 → HOST_MAX=8

# Regenerate configs
./setup.sh

# Restart with new hosts
docker-compose -f docker-compose.yml down
./launch.sh
```

### Development Mode

```bash
# Use dev mode for live code editing
./launch-dev.sh

# Edit code locally → changes reflect immediately
# Just restart container to pick up changes
docker-compose -f docker-compose.yml restart backend_host_1
```

---

## Part D: Services Deep Dive

### Frontend (React)

| Attribute | Value |
|-----------|-------|
| **Framework** | React 18 + TypeScript |
| **Build Tool** | Vite |
| **UI Library** | Material-UI |
| **Port** | 3000 |
| **Deployment** | Nginx (Docker) / Vercel (Cloud) |

**Key Directories:**
```
frontend/
├── src/
│   ├── components/     # React components
│   ├── hooks/          # Custom hooks
│   ├── pages/          # Page components
│   ├── services/       # API clients
│   └── types/          # TypeScript types
├── public/             # Static assets
└── vite.config.ts      # Vite configuration
```

**Environment Variables:**
```bash
VITE_SERVER_URL=http://localhost:5109
VITE_DEV_MODE=true
```

### Backend Server (Flask)

| Attribute | Value |
|-----------|-------|
| **Framework** | Flask + Gunicorn |
| **Language** | Python 3.10+ |
| **Port** | 5109 |
| **Features** | REST API, WebSocket, Grafana |

**Key Directories:**
```
backend_server/
├── src/
│   ├── routes/         # API endpoints
│   ├── services/       # Business logic
│   ├── models/         # Data models
│   └── app.py          # Flask app
├── docker/             # Docker configs
└── requirements.txt    # Python deps
```

**API Endpoints:**
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/server/system/*` | GET | System info |
| `/server/devices/*` | CRUD | Device management |
| `/server/testcases/*` | CRUD | Test cases |
| `/server/hosts/*` | GET | Host management |

### Backend Host (Flask + VNC)

| Attribute | Value |
|-----------|-------|
| **Framework** | Flask + Gunicorn |
| **Language** | Python 3.10+ |
| **Port** | 6109 (API), 6080 (NoVNC), 5900 (VNC) |
| **Features** | Device control, video capture, VNC |

**Key Directories:**
```
backend_host/
├── src/
│   ├── routes/         # API endpoints
│   ├── controllers/    # Device controllers
│   ├── services/       # Hardware services
│   └── app.py          # Flask app
├── docker/
│   ├── Dockerfile      # Multi-stage build
│   ├── nginx.conf      # Internal nginx
│   └── supervisord.conf # Process manager
└── requirements.txt
```

**Container Services (supervisord):**
```
┌─────────────────────────────────────────┐
│           BACKEND HOST CONTAINER        │
├─────────────────────────────────────────┤
│                                         │
│   supervisord (PID 1)                   │
│       │                                 │
│       ├── nginx (port 80)               │
│       │    └── proxies to services      │
│       │                                 │
│       ├── gunicorn (port 6109)          │
│       │    └── Flask API                │
│       │                                 │
│       ├── Xvfb (:1)                     │
│       │    └── Virtual display          │
│       │                                 │
│       ├── x11vnc (port 5900)            │
│       │    └── VNC server               │
│       │                                 │
│       ├── novnc (port 6080)             │
│       │    └── Web VNC                  │
│       │                                 │
│       └── ffmpeg (optional)             │
│            └── Video capture            │
│                                         │
└─────────────────────────────────────────┘
```

### Grafana (Monitoring)

| Attribute | Value |
|-----------|-------|
| **Version** | 10.x |
| **Port** | 3001 (direct) / 5109/grafana (proxied) |
| **Datasource** | PostgreSQL |
| **Deployment** | Embedded in Backend Server |

**Default Credentials:**
- Username: `admin`
- Password: `admin123` (change in production!)

**Pre-configured Dashboards:**
- System Overview
- Test Execution Metrics
- Device Health
- Host Performance

---

## Part E: External Services

### Supabase (Database)

**Setup:**
1. Create account at [supabase.com](https://supabase.com)
2. Create new project
3. Get connection string from Settings → Database
4. Apply schema migrations

**Schema Migration:**
```bash
# Connect to Supabase
psql $SUPABASE_DB_URI

# Apply migrations
\i setup/db/schema/001_initial.sql
\i setup/db/schema/002_devices.sql
# ... etc
```

**Environment Variables:**
```bash
SUPABASE_DB_URI=postgresql://postgres:[password]@db.[project].supabase.co:5432/postgres
NEXT_PUBLIC_SUPABASE_URL=https://[project].supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=[anon-key]
SUPABASE_SERVICE_ROLE_KEY=[service-role-key]
```

### Cloudflare R2 (Storage)

**Setup:**
1. Create Cloudflare account
2. Enable R2 in dashboard
3. Create bucket (e.g., `virtualpytest-storage`)
4. Create API token with R2 permissions

**Environment Variables:**
```bash
CLOUDFLARE_R2_ENDPOINT=https://[account-id].r2.cloudflarestorage.com
CLOUDFLARE_R2_ACCESS_KEY_ID=[access-key]
CLOUDFLARE_R2_SECRET_ACCESS_KEY=[secret-key]
CLOUDFLARE_R2_BUCKET=virtualpytest-storage
CLOUDFLARE_R2_PUBLIC_URL=https://[custom-domain-or-r2-url]
```

### OpenRouter (AI/LLM)

**Setup:**
1. Create account at [openrouter.ai](https://openrouter.ai)
2. Add credits
3. Generate API key

**Environment Variables:**
```bash
OPENROUTER_API_KEY=sk-or-v1-xxxxx
```

**Supported Models:**
- GPT-4o (vision)
- Claude 3.5 Sonnet
- Gemini Pro Vision

---

## Appendix

### A. Environment Variables Reference

| Variable | Service | Required | Description |
|----------|---------|----------|-------------|
| `DATABASE_URL` | All | Yes* | PostgreSQL connection |
| `SUPABASE_DB_URI` | All | Yes* | Supabase connection |
| `API_KEY` | Server/Host | Yes | Inter-service auth |
| `CLOUDFLARE_R2_*` | Server | Optional | Screenshot storage |
| `OPENROUTER_API_KEY` | Server | Optional | AI features |
| `GRAFANA_ADMIN_PASSWORD` | Server | Yes | Grafana login |
| `HOST_NAME` | Host | Yes | Host identifier |
| `HOST_PORT` | Host | Yes | Host API port |
| `SERVER_URL` | Host | Yes | Backend server URL |

*Either `DATABASE_URL` (standalone) or `SUPABASE_DB_URI` (production)

### B. Docker Commands Cheat Sheet

```bash
# View running containers
docker ps

# View logs
docker-compose -f <compose-file> logs -f
docker-compose -f <compose-file> logs -f backend_host_1

# Restart single service
docker-compose -f <compose-file> restart backend_host_1

# Rebuild and restart
docker-compose -f <compose-file> up -d --build backend_host_1

# Shell into container
docker exec -it virtualpytest-backend-host-1 bash

# View container resources
docker stats

# Clean up
docker-compose -f <compose-file> down        # Stop containers
docker-compose -f <compose-file> down -v     # Stop + remove volumes
docker system prune -a                        # Remove all unused
```

### C. Troubleshooting

**Services won't start:**
```bash
# Check Docker status
systemctl status docker
docker info

# Check logs
docker-compose -f docker-compose.yml logs

# Verify .env file exists
ls -la .env
```

**Database connection issues:**
```bash
# Test connection
psql $DATABASE_URL -c "SELECT 1"

# Check from container
docker exec -it virtualpytest-backend-server \
    python -c "from shared.config import config; print(config.database_url)"
```

**Host not connecting to server:**
```bash
# Check host logs
docker logs virtualpytest-backend-host-1

# Verify SERVER_URL
docker exec virtualpytest-backend-host-1 env | grep SERVER

# Test connectivity
docker exec virtualpytest-backend-host-1 \
    curl http://backend_server:5109/health
```

**VNC not working:**
```bash
# Check Xvfb
docker exec virtualpytest-backend-host-1 ps aux | grep Xvfb

# Check x11vnc
docker exec virtualpytest-backend-host-1 ps aux | grep x11vnc

# Check NoVNC
docker exec virtualpytest-backend-host-1 \
    curl -I http://localhost:6080
```

**Port conflicts:**
```bash
# Find process using port
lsof -i :5109
netstat -tlnp | grep 5109

# Kill process
kill -9 <PID>
```

### D. File Structure Overview

```
virtualpytest/
├── frontend/                 # React frontend
│   ├── src/
│   └── Dockerfile
├── backend_server/           # Flask API server
│   ├── src/
│   └── Dockerfile
├── backend_host/             # Device controller
│   ├── src/
│   └── Dockerfile
├── shared/                   # Shared Python library
├── setup/
│   ├── docker/
│   │   ├── standalone_server_host/   # Local deployment
│   │   ├── hetzner_custom/           # Production deployment
│   │   └── proxmox/                  # VM deployment
│   ├── local/                        # Non-Docker setup
│   └── db/schema/                    # Database migrations
├── docs/                     # Documentation
├── test_scripts/             # Test automation scripts
└── .env                      # Configuration (git-ignored)
```

---

**Previous:** [QuickGuide 2: Network Setup](./quickguide-network.md)  
**Next:** [QuickGuide 4: Security Setup](./quickguide-security.md)