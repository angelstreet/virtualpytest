# Local Setup Scripts

Quick reference for VirtualPyTest local installation and launch scripts.

## 🎯 **Quick Start**

```bash
# 1. Clone and navigate to project
git clone https://github.com/angelstreet/virtualpytest
cd virtualpytest

# 2. Install everything (automatically installs system requirements + creates .env files)
./setup/local/install_all.sh

# 3. Launch everything
./scripts/launch_virtualpytest.sh
```

## 📋 **Main Commands**

```bash
# Installation
./setup/local/install_all.sh              # Install everything (recommended)
./setup/local/install_all.sh --no-grafana # Install without monitoring

# Launch Services  
./scripts/launch_virtualpytest.sh         # Start all services
./setup/local/launch_server.sh            # Backend server only
./setup/local/launch_host.sh              # Backend host only
./setup/local/launch_frontend.sh          # Frontend only

# Individual Components
./setup/local/install_db.sh               # Database only
./setup/local/install_shared.sh           # Shared library only
./setup/local/install_server.sh           # Backend server only
./setup/local/install_host.sh             # Backend host only
./setup/local/install_frontend.sh         # Frontend only
./setup/local/install_grafana.sh          # Grafana monitoring only

# Hardware Setup (Raspberry Pi)
./setup/local/install_host_services.sh    # Stream/monitor systemd services

# Utilities
./setup/local/stop_all_local.sh           # Stop all services
./setup/local/clean_build_artifacts.sh    # Clean build files
```

---

## 📖 **Detailed Information**

### 📦 **Installation Scripts**

| Script | Purpose | What It Installs |
|--------|---------|------------------|
| `install_requirements.sh` | **System requirements** | OS-level dependencies (auto-called by install_all.sh) |
| `install_all.sh` | **Main installer** | All components + database + Grafana (default) |
| `install_db.sh` | **Database setup** | PostgreSQL + VirtualPyTest schema + Grafana DB |
| `install_shared.sh` | Shared library | Python dependencies for shared utilities |
| `install_server.sh` | Backend Server | API server dependencies |
| `install_host.sh` | Backend Host | Device controller + Python deps |
| `install_frontend.sh` | Frontend | Node.js + React web interface |
| `install_grafana.sh` | Grafana | Monitoring dashboard configuration |
| `install_host_services.sh` | Host Services | Stream/monitor systemd services |

### 🚀 **Launch Scripts**

| Script | Purpose | What It Starts |
|--------|---------|----------------|
| `launch_all.sh` | **Main launcher** | All services with unified logs |
| `launch_server.sh` | Backend Server only | API server (port 5109) |
| `launch_host.sh` | Backend Host only | Device controller + auto-services |
| `launch_frontend.sh` | Frontend only | Web interface (port 3000) |

### 🛠️ **Utility Scripts**

| Script | Purpose |
|--------|---------|
| `stop_all_local.sh` | Stop all running services |
| `clean_build_artifacts.sh` | Clean build files and caches |

## 💡 **Notes**

- **Automatic Setup**: `install_all.sh` now automatically installs system requirements and creates .env files
- **Database Included**: Complete PostgreSQL setup with VirtualPyTest and Grafana databases
- **Environment Files**: .env files are automatically created from templates during installation
- **Grafana Default**: Monitoring included by default (use `--no-grafana` to skip)
- **Auto-detection**: `launch_host.sh` automatically starts stream/monitor services if video devices are configured
- **Migration Files**: Database setup reuses the migration files from `setup/db/schema/`
- **Logs**: All launch scripts show real-time colored logs

## 📋 **Additional Files**

| File | Purpose |
|------|---------|
| `REQUIREMENTS.md` | Detailed system requirements documentation |
| `README_GRAFANA.md` | Grafana-specific setup and troubleshooting |
