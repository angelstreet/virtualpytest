# Local Setup Scripts

Quick reference for VirtualPyTest local installation and launch scripts.

## 📦 **Installation Scripts**

| Script | Purpose | What It Installs |
|--------|---------|------------------|
| `install_requirements.sh` | **System requirements** | OS-level dependencies (run first!) |
| `install_all.sh` | **Main installer** | All components + database + Grafana (default) |
| `install_db.sh` | **Database setup** | PostgreSQL + VirtualPyTest schema + Grafana DB |
| `install_shared.sh` | Shared library | Python dependencies for shared utilities |
| `install_server.sh` | Backend Server | API server dependencies |
| `install_host.sh` | Backend Host | Device controller + Python deps |
| `install_frontend.sh` | Frontend | Node.js + React web interface |
| `install_grafana.sh` | Grafana | Monitoring dashboard configuration |
| `install_host_services.sh` | Host Services | Stream/monitor systemd services |

## 🚀 **Launch Scripts**

| Script | Purpose | What It Starts |
|--------|---------|----------------|
| `launch_all.sh` | **Main launcher** | All services with unified logs |
| `launch_server.sh` | Backend Server only | API server (port 5109) |
| `launch_host.sh` | Backend Host only | Device controller + auto-services |
| `launch_frontend.sh` | Frontend only | Web interface (port 3000) |

## 🛠️ **Utility Scripts**

| Script | Purpose |
|--------|---------|
| `stop_all_local.sh` | Stop all running services |
| `clean_build_artifacts.sh` | Clean build files and caches |

## 🎯 **Quick Start**

```bash
# 1. Install system requirements first (run once)
./install_requirements.sh

# 2. Install everything (includes Grafana by default)
./install_all.sh

# 3. Launch everything (Grafana is built into backend_server)
./launch_all.sh
```

## 📋 **Individual Components**

**Install specific components:**
```bash
./install_db.sh          # Database setup first
./install_shared.sh      # Shared library
./install_server.sh      # Backend API
./install_host.sh        # Device controller
./install_frontend.sh    # Web interface
./install_grafana.sh     # Monitoring
```

**Launch specific components:**
```bash
./launch_server.sh       # API only
./launch_host.sh         # Host only (auto-detects services)
./launch_frontend.sh     # Web only
```

## 🔧 **Advanced Setup**

**For hardware testing with video capture:**
```bash
./install_host_services.sh   # Creates systemd services for:
                             # - FFmpeg video capture
                             # - Capture monitoring
                             # - File cleanup
```

## 💡 **Notes**

- **System Requirements**: Run `install_requirements.sh` first to install OS-level dependencies
- **Database First**: `install_all.sh` now includes complete database setup with VirtualPyTest schema
- **Local Database**: Creates PostgreSQL with both application and Grafana databases
- **Grafana Default**: `install_all.sh` includes Grafana by default (use `--no-grafana` to skip)
- **Auto-detection**: `launch_host.sh` automatically starts stream/monitor services if video devices are configured in `.env`
- **Migration Files**: Database setup reuses the migration files from `setup/db/schema/`
- **Logs**: All launch scripts show real-time colored logs

## 📋 **Additional Files**

| File | Purpose |
|------|---------|
| `REQUIREMENTS.md` | Detailed system requirements documentation |
| `README_GRAFANA.md` | Grafana-specific setup and troubleshooting |
