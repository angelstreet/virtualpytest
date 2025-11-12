# VirtualPyTest Hetzner Custom Deployment

**1 Backend Server + 2 Backend Hosts Configuration**

## Architecture

```
┌─────────────────────────────────────────────────┐
│         Backend Server (Centralized)            │
│  - Flask API (Port 5109)                        │
│  - Grafana Monitoring (Port 3001)               │
│  - Connects to Supabase Database                │
└─────────────────────────────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
┌───────▼────────┐            ┌───────▼────────┐
│ Backend Host 1 │            │ Backend Host 2 │
│  Port: 6109    │            │  Port: 6110    │
│  Device: TV #1 │            │  Device: TV #2 │
└────────────────┘            └────────────────┘
```

## What's Included

- ✅ **1 Backend Server** - Centralized API and monitoring
- ✅ **2 Backend Hosts** - Distributed device controllers
- ✅ **Supabase Database** - External cloud database
- ✅ **Shared Network** - All services communicate via Docker network

## Ports

- **5109** - Backend Server API
- **3000** - Grafana Monitoring Dashboard
- **6109** - Backend Host 1 Device Controller
- **6110** - Backend Host 2 Device Controller

## Prerequisites

1. **Docker & Docker Compose** installed
2. **Supabase account** with database configured
3. **Hardware access** for device controllers (HDMI capture cards, etc.)
4. **Environment variables** configured in `.env` file

## Quick Start

### 1. Configure Environment

**Backend Server:**
```bash
# Copy server environment template to project root
cp setup/docker/hetzner_custom/env.server.example .env

# Edit with your Supabase and configuration
nano .env
```

**Backend Hosts:**
```bash
# Copy host environment template to backend_host/src/
cp setup/docker/hetzner_custom/env.host.example backend_host/src/.env

# Edit with your hardware configuration
nano backend_host/src/.env
```

### 2. Launch Services

```bash
# Start all services (1 server + 2 hosts)
docker-compose -f setup/docker/hetzner_custom/docker-compose.yml up -d

# View logs
docker-compose -f setup/docker/hetzner_custom/docker-compose.yml logs -f

# Stop services
docker-compose -f setup/docker/hetzner_custom/docker-compose.yml down
```

### 3. Verify Services

```bash
# Check Backend Server
curl http://localhost:5109/health

# Check Backend Host 1
curl http://localhost:6109/health

# Check Backend Host 2
curl http://localhost:6110/health

# Access Grafana
open http://localhost:3000
```

## Configuration Details

### Backend Server

The backend server runs centralized:
- **API endpoints** for frontend and hosts
- **Grafana monitoring** for all services
- **Database connection** to Supabase
- **CORS configuration** for frontend access

### Backend Host 1

First device controller:
- **Port**: 6109 (external and internal)
- **Hostname**: backend-host-1
- **Connects to**: Backend Server via Docker network
- **Hardware access**: `/dev` mounted for device control

### Backend Host 2

Second device controller:
- **Port**: 6110 (external), 6109 (internal)
- **Hostname**: backend-host-2
- **Connects to**: Backend Server via Docker network
- **Hardware access**: `/dev` mounted for device control

## Environment Variables

### Required for Backend Server

```bash
SUPABASE_DB_URI=postgresql://...
NEXT_PUBLIC_SUPABASE_URL=https://...
NEXT_PUBLIC_SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...
GRAFANA_ADMIN_PASSWORD=...
```

### Required for Backend Hosts

```bash
# Host 1
HOST1_NAME=hetzner-host-1
HOST1_DEVICE1_NAME=Samsung_TV_Location_1
HOST1_DEVICE1_VIDEO=/dev/video0

# Host 2
HOST2_NAME=hetzner-host-2
HOST2_DEVICE1_NAME=LG_TV_Location_2
HOST2_DEVICE1_VIDEO=/dev/video0
```

See `.env.example` for complete configuration.

## Scaling

### Add More Hosts

To add additional hosts, edit `docker-compose.yml`:

```yaml
backend_host_3:
  build:
    context: ../../../
    dockerfile: backend_host/Dockerfile
  container_name: virtualpytest-backend-host-3
  ports:
    - "6111:6109"  # Next available port
  environment:
    - HOST_NAME=hetzner-host-3
    - HOST_URL=http://localhost:6111
    # ... additional config
```

### Multiple Servers (Load Balancing)

For multiple backend servers, use a load balancer (nginx, HAProxy) in front of multiple server instances.

## Troubleshooting

### Services won't start

```bash
# Check Docker status
docker ps -a

# View logs for specific service
docker-compose -f setup/docker/hetzner_custom/docker-compose.yml logs backend_server
docker-compose -f setup/docker/hetzner_custom/docker-compose.yml logs backend_host_1
```

### Database connection issues

```bash
# Test Supabase connection
psql "$SUPABASE_DB_URI"

# Check environment variables loaded
docker-compose -f setup/docker/hetzner_custom/docker-compose.yml config
```

### Hardware access issues

```bash
# Check device permissions
ls -la /dev/video*
ls -la /dev/snd/

# Ensure privileged mode is enabled in docker-compose.yml
```

### Network issues between services

```bash
# Check network
docker network inspect virtualpytest-hetzner-network

# Test connectivity from host to server
docker-compose -f setup/docker/hetzner_custom/docker-compose.yml exec backend_host_1 \
  curl http://backend_server:5109/health
```

## Production Deployment

### Security Checklist

- [ ] Change default Grafana admin password
- [ ] Use strong GRAFANA_SECRET_KEY
- [ ] Configure proper CORS_ORIGINS
- [ ] Secure Supabase credentials
- [ ] Use HTTPS in production
- [ ] Configure firewall rules
- [ ] Enable container auto-restart
- [ ] Set up log rotation

### Monitoring

Access Grafana at `http://your-server:3000`:
- **Username**: admin
- **Password**: `$GRAFANA_ADMIN_PASSWORD` from .env

### Backup

```bash
# Backup Grafana data
docker run --rm --volumes-from virtualpytest-backend-server \
  -v $(pwd)/backup:/backup \
  ubuntu tar czf /backup/grafana-backup.tar.gz /var/lib/grafana

# Restore Grafana data
docker run --rm --volumes-from virtualpytest-backend-server \
  -v $(pwd)/backup:/backup \
  ubuntu tar xzf /backup/grafana-backup.tar.gz -C /
```

## Additional Resources

- **Main Documentation**: See `/docs/` folder
- **Standalone Setup**: See `/setup/docker/standalone_server_host/`
- **Individual Services**: See `/backend_server/docker/` and `/backend_host/docker/`
- **Database Schema**: See `/setup/db/schema/`

## Support

For issues or questions:
1. Check logs: `docker-compose logs -f`
2. Verify environment: `docker-compose config`
3. Test connectivity: `curl http://localhost:5109/health`

