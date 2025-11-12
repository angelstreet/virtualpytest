# VirtualPyTest Standalone - Complete Local System

**Everything included for local development and testing**

---

## 🚀 Quick Start from Scratch

### 1. Clone Repository

```bash
# Clone VirtualPyTest from GitHub
git clone https://github.com/angelstreet/virtualpytest.git
cd virtualpytest
```

### 2. Install Docker

```bash
# Run Docker installation script
./setup/docker/install_docker.sh
```

### 3. Configure (Optional)

```bash
# Optional: Copy environment template (contains server + host config)
cp setup/docker/standalone_server_host/env.example .env

# Edit if needed (default values work fine)
nano .env
```

**Note:** Standalone uses local PostgreSQL, so Supabase config is not needed.

### 4. Launch

```bash
# Launch everything!
./setup/docker/standalone_server_host/launch.sh
```

**That's it!** Your complete local development environment is running. 🎉

Access points:
- **Web Interface**: http://localhost:3000
- **Backend API**: http://localhost:5109
- **Grafana**: http://localhost:3001

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│              Frontend (React)                   │
│              Port: 3000                         │
└───────────────────┬─────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────┐
│         Backend Server (API + Grafana)          │
│         Ports: 5109, 3001                       │
└───────────────────┬─────────────────────────────┘
                    │
        ┌───────────┼───────────┐
        │           │           │
┌───────▼──────┐    │    ┌──────▼────────┐
│ Backend Host │    │    │   PostgreSQL  │
│ Port: 6109   │    │    │   Port: 5432  │
└──────────────┘    │    └───────────────┘
                    │
            ┌───────▼────────┐
            │ Grafana Metrics│
            │   PostgreSQL   │
            │   Port: 5433   │
            └────────────────┘
```

## What's Included

- ✅ **Frontend** - React web interface (Port 3000)
- ✅ **Backend Server** - Flask API + Grafana monitoring (Ports 5109, 3001)
- ✅ **Backend Host** - Device controller (Port 6109)
- ✅ **PostgreSQL** - Main application database (Port 5432)
- ✅ **Grafana Metrics DB** - Monitoring data storage (Port 5433)

## Ports

- **3000** - Frontend Web Interface
- **5109** - Backend Server API
- **3001** - Grafana Monitoring Dashboard
- **6109** - Backend Host Device Controller
- **5432** - PostgreSQL Main Database
- **5433** - Grafana Metrics Database

## Prerequisites

1. **Linux, macOS, or Windows with WSL2**
2. **Docker & Docker Compose** (installed via `install_docker.sh`)
3. **Git** for cloning repository
4. **Hardware access** (optional - for device control testing)

**No external dependencies required!** Everything runs locally.

## Detailed Setup Guide

### 1. Clone and Setup

```bash
# Clone from GitHub
git clone https://github.com/angelstreet/virtualpytest.git
cd virtualpytest

# Make scripts executable
chmod +x setup/docker/install_docker.sh
chmod +x setup/docker/standalone_server_host/launch.sh
```

### 2. Install Docker

```bash
# Install Docker and Docker Compose
./setup/docker/install_docker.sh

# Verify installation
docker --version
docker compose version
```

## Environment Configuration

**Single .env file for all services (optional):**

```bash
# Optional: Copy environment template
cp setup/docker/standalone_server_host/env.example .env

# Edit if needed (default values work fine)
nano .env
```

**Note:** 
- Standalone uses local PostgreSQL instead of Supabase, so external database configuration is not required
- All services (server + host + frontend) load from the same `.env` file in project root
- Default values work out of the box for local development

## Quick Start

### Launch Services (Easy Way)

```bash
# Use the automated launch script
./setup/docker/standalone_server_host/launch.sh
```

### Launch Services (Manual Way)

```bash
# Easy way - Use launch script
./setup/docker/standalone_server_host/launch.sh

# Manual way - Direct docker-compose
docker-compose -f setup/docker/standalone_server_host/docker-compose.yml up -d

# View logs
docker-compose -f setup/docker/standalone_server_host/docker-compose.yml logs -f
```

### Access the Application

```bash
# Open web interface
open http://localhost:3000

# Check API health
curl http://localhost:5109/health

# Check device controller
curl http://localhost:6109/health

# Access Grafana monitoring
open http://localhost:3001
```

### Stop Services

```bash
# Stop all services (keep data)
docker-compose -f setup/docker/standalone_server_host/docker-compose.yml down

# Stop and remove all data
docker-compose -f setup/docker/standalone_server_host/docker-compose.yml down -v
```

## Default Credentials

### PostgreSQL Database

- **Host**: localhost
- **Port**: 5432
- **Database**: virtualpytest
- **User**: virtualpytest_user
- **Password**: virtualpytest_pass

### Grafana

- **URL**: http://localhost:3001
- **Username**: admin
- **Password**: admin123

## Configuration Details

### Frontend

React web interface built with Vite:
- **Framework**: React + TypeScript
- **Port**: 3000 (nginx serves static files)
- **API Connection**: http://localhost:5109
- **Hot Reload**: Volume-mounted for development

### Backend Server

Centralized API server:
- **Framework**: Flask
- **Port**: 5109 (nginx proxy)
- **Grafana**: 3001 (direct access)
- **Database**: PostgreSQL (local)
- **Monitoring**: Built-in Grafana dashboards

### Backend Host

Device controller:
- **Port**: 6109
- **Server Connection**: http://backend_server:5109 (Docker network)
- **Database**: PostgreSQL (local)
- **Hardware Access**: `/dev` mounted (privileged mode)

### PostgreSQL Databases

Two separate databases:

**1. Main Application Database (Port 5432)**
- Application data (testcases, incidents, devices, etc.)
- Auto-initialized with schema from `/setup/db/schema/`
- Optimized for application workload

**2. Grafana Metrics Database (Port 5433)**
- Monitoring and metrics data
- Separate to avoid impacting main database
- Optimized for time-series data

## Data Persistence

All data is stored in Docker volumes:

```bash
# View volumes
docker volume ls | grep virtualpytest

# Volumes created:
# - virtualpytest-postgres-data          (Main database)
# - virtualpytest-grafana-metrics-data   (Metrics database)
# - virtualpytest-grafana-data           (Grafana dashboards)
# - virtualpytest-grafana-logs           (Grafana logs)
```

## Development Workflow

### Live Code Changes

Source code is volume-mounted for live development:

```yaml
volumes:
  - ../../shared:/app/shared:ro
  - ../../backend_host:/app/backend_host:ro
  - ../src:/app/backend_server/src:ro
```

Changes to Python code reflect immediately without rebuild.

### Database Management

```bash
# Connect to database
psql postgresql://virtualpytest_user:virtualpytest_pass@localhost:5432/virtualpytest

# Run migrations
psql postgresql://virtualpytest_user:virtualpytest_pass@localhost:5432/virtualpytest -f setup/db/schema/your_migration.sql

# Backup database
docker-compose -f setup/docker/standalone_server_host/docker-compose.yml exec postgres \
  pg_dump -U virtualpytest_user virtualpytest > backup.sql

# Restore database
docker-compose -f setup/docker/standalone_server_host/docker-compose.yml exec -T postgres \
  psql -U virtualpytest_user virtualpytest < backup.sql
```

## Troubleshooting

### Services won't start

```bash
# Check Docker status
docker ps -a

# View logs for specific service
docker-compose -f setup/docker/standalone_server_host/docker-compose.yml logs postgres
docker-compose -f setup/docker/standalone_server_host/docker-compose.yml logs backend_server
docker-compose -f setup/docker/standalone_server_host/docker-compose.yml logs frontend
```

### Port conflicts

```bash
# Check what's using ports
lsof -i :3000
lsof -i :5109
lsof -i :5432

# Stop conflicting services or change ports in docker-compose.yml
```

### Database connection issues

```bash
# Check database is ready
docker-compose -f setup/docker/standalone_server_host/docker-compose.yml exec postgres \
  pg_isready -U virtualpytest_user -d virtualpytest

# Check database logs
docker-compose -f setup/docker/standalone_server_host/docker-compose.yml logs postgres
```

### Frontend not loading

```bash
# Check frontend logs
docker-compose -f setup/docker/standalone_server_host/docker-compose.yml logs frontend

# Check nginx configuration
docker-compose -f setup/docker/standalone_server_host/docker-compose.yml exec frontend \
  cat /etc/nginx/conf.d/default.conf
```

### Hardware access issues

```bash
# Check device permissions
ls -la /dev/video*
ls -la /dev/snd/

# Ensure Docker has hardware access
docker run --privileged --rm -it ubuntu ls /dev/
```

## Performance Tuning

### PostgreSQL Configuration

Database is pre-configured with optimized settings:

```yaml
command: >
  postgres
  -c shared_preload_libraries=pg_stat_statements
  -c pg_stat_statements.track=all
  -c max_connections=200
  -c shared_buffers=256MB
  -c effective_cache_size=1GB
```

Adjust in `docker-compose.yml` for your system.

### Docker Resources

Allocate more resources if needed:

```bash
# Check Docker resources
docker stats

# Increase in Docker Desktop: Settings > Resources
```

## Testing Scenarios

### API Testing

```bash
# Test backend server
curl http://localhost:5109/health
curl http://localhost:5109/api/devices
curl http://localhost:5109/api/testcases

# Test backend host
curl http://localhost:6109/health
curl http://localhost:6109/devices
```

### Load Testing

```bash
# Use Apache Bench
ab -n 1000 -c 10 http://localhost:5109/health

# Use wrk
wrk -t12 -c400 -d30s http://localhost:5109/health
```

## Cleanup

### Stop services (keep data)

```bash
docker-compose -f setup/docker/standalone_server_host/docker-compose.yml down
```

### Remove everything (including data)

```bash
# Stop and remove containers, networks, volumes
docker-compose -f setup/docker/standalone_server_host/docker-compose.yml down -v

# Remove images (optional)
docker rmi $(docker images 'virtualpytest*' -q)
```

## Use Cases

### Perfect For:

- ✅ Local development
- ✅ Testing new features
- ✅ Demo and presentations
- ✅ CI/CD testing environments
- ✅ Learning the system
- ✅ Offline development

### Not Recommended For:

- ❌ Production deployments
- ❌ Multi-user environments
- ❌ Distributed testing
- ❌ Cloud deployments

For production, see:
- `/setup/docker/hetzner_custom/` - Cloud deployment with Supabase
- `/backend_server/docker/` - Server-only deployment
- `/backend_host/docker/` - Host-only deployment

## Additional Resources

- **Main Documentation**: See `/docs/` folder
- **Cloud Deployment**: See `/setup/docker/hetzner_custom/`
- **Individual Services**: See `/backend_server/docker/` and `/backend_host/docker/`
- **Database Schema**: See `/setup/db/schema/`

## Support

For issues or questions:
1. Check logs: `docker-compose logs -f`
2. Verify services: `docker-compose ps`
3. Test connectivity: `curl http://localhost:5109/health`
4. Check documentation: `/docs/`

