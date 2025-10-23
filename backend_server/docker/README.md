# 🐳 Backend Server - Docker Guide

Complete guide for running backend_server in Docker. Simple and organized.

---

## 🚀 Quick Start (3 Steps)

### 1. Setup Environment (One-time)

```bash
# Copy template and add your values
cp docker/.env.example .env
nano .env  # Add your database URL, Supabase keys, etc.
```

### 2. Build

```bash
cd backend_server/docker
./scripts/build.sh
```

⏱️ Takes 5-8 minutes first time

### 3. Run

```bash
./scripts/run.sh
```

**Done!** 🎉 Services running at:
- **Flask API**: http://localhost:5109
- **Health Check**: http://localhost:5109/health
- **Grafana**: http://localhost:3000 (admin/admin123)

---

## 🏗️ Architecture

### What's Inside the Container

```
┌─────────────────────────────────────┐
│   Docker Container                   │
│                                      │
│   ┌──────────────────────────────┐  │
│   │ Supervisor (Process Manager) │  │
│   │  ├── nginx (port 80)         │  │  ← Reverse proxy
│   │  ├── Flask (port 5109)       │  │  ← Your Python API
│   │  └── Grafana (port 3000)     │  │  ← Monitoring
│   └──────────────────────────────┘  │
│                                      │
│   OS: Debian-slim (lightweight)     │
│   Python: 3.11                      │
│   Your code: /app/backend_server    │
└─────────────────────────────────────┘
```

### Service Flow

```
Internet → Docker Container
              ↓
         nginx (port 80)
              ↓
    ┌─────────┴──────────┐
    ↓                    ↓
Flask API          Grafana
(port 5109)       (port 3000)
```

---

## 📋 Common Commands

```bash
cd backend_server/docker

# Start services
./scripts/run.sh
# OR
docker-compose up -d

# Test services
./scripts/test.sh
# OR
curl http://localhost:5109/health

# View logs
docker-compose logs -f

# Stop services  
./scripts/stop.sh
# OR
docker-compose stop

# Clean up everything
./scripts/clean.sh
# OR
docker-compose down -v

# Restart after code changes
docker-compose restart
```

---

## 🔧 Configuration Files

| File | Purpose |
|------|---------|
| `Dockerfile` (in parent) | Recipe to build the Docker image |
| `docker-compose.yml` | Defines how to run the container |
| `.env.example` | Template for environment variables |
| `scripts/*.sh` | Convenience scripts (optional) |

### Required Environment Variables

Your `.env` file needs:

```bash
# Server
SERVER_PORT=5109
SERVER_URL=http://localhost:5109

# Database (Supabase)
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
DATABASE_URL=postgresql://postgres:password@host:5432/postgres

# Grafana
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=admin123
GRAFANA_SECRET_KEY=your-secret-key
```

See `.env.example` for complete list.

---

## 🐛 Troubleshooting

### Port already in use

```bash
# Check what's using the port
lsof -i :5109
lsof -i :3000

# Kill it
kill -9 $(lsof -t -i:5109)
```

### Container won't start

```bash
# Check logs
docker-compose logs backend_server

# Rebuild from scratch
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

### Health check failing

```bash
# Test endpoint
curl http://localhost:5109/health

# Check processes inside container
docker-compose exec backend_server supervisorctl status

# Should show:
# nginx    RUNNING
# flask    RUNNING
# grafana  RUNNING
```

### ".env file not found"

```bash
# Make sure .env is in project root (not docker folder)
ls -la ../../.env

# Copy template if missing
cp docker/.env.example ../../.env
nano ../../.env
```

### Database connection error

```bash
# Check .env has correct DATABASE_URL
cat ../../.env | grep DATABASE_URL

# Test connection
docker-compose exec backend_server python3 -c "
from shared.src.lib.config.supabase_config import get_supabase_client
print('Testing connection...')
client = get_supabase_client()
print('✅ Database connection OK')
"
```

---

## 🎓 Understanding Docker (Simple)

**Docker = A box that packages your app + everything it needs**

### Why use Docker?

✅ **Same everywhere** - Works on your laptop, servers, cloud  
✅ **All dependencies included** - No "works on my machine" problems  
✅ **Easy to start/stop** - One command  
✅ **Isolated** - Won't mess up your computer  

### What the files do

- **`Dockerfile`** - Recipe that says "install Python, nginx, Grafana, copy code"
- **`docker-compose.yml`** - Says "run the container, open ports 5109 and 3000"
- **`scripts/`** - Just shortcuts so you don't type long commands

**That's it!** Docker isn't magic, it's just packaging.

---

## 🚀 Deployment Options

### Local Development (What you're doing now)

```bash
cd backend_server/docker
docker-compose up -d
```

Uses volume mounts so code changes reflect immediately (after restart).

### Production (Render, AWS, etc.)

For production deployment:

1. **Render**: Set environment to "Docker", dockerfile path to `backend_server/Dockerfile`
2. **AWS ECS**: Use the Docker image  
3. **Google Cloud Run**: Deploy the container
4. **Any Docker host**: Use `docker-compose.prod.yml`

**Port configuration:**
- Local: 5109 (Flask), 3000 (Grafana)
- Render: Can use any port via SERVER_PORT env var

---

## 📊 Grafana Monitoring

Grafana is included for system monitoring.

**Access**: http://localhost:3000  
**Login**: admin / admin123 (change via `GRAFANA_ADMIN_PASSWORD`)

**Features:**
- System overview dashboard
- Real-time metrics
- Database connectivity monitoring
- Custom dashboards

---

## 🎯 The Absolute Minimum

Don't want scripts? Just use:

```bash
cd backend_server/docker
docker-compose up -d
```

That's it! Docker handles everything.

---

## 📞 Need Help?

1. Check logs: `docker-compose logs -f`
2. Check this troubleshooting section above
3. Verify .env file exists with correct values
4. Check Docker and Docker Compose are installed: `docker --version`

---

**Remember:** All scripts in `scripts/` are optional. You can use basic `docker-compose` commands directly if you prefer!
