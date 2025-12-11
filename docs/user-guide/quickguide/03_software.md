# Quick Guide: Software Stack

## Overview
This guide covers the VirtualPytest software stack including server, frontend, backend host, and supporting services.

## Software Architecture

### Component Overview

```
┌───────────────────────────────────────────────────┐
│                 VirtualPytest Stack                 │
├───────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────┐    ┌─────────┐  │
│  │  Frontend   │    │ Backend     │    │  Host   │  │
│  │ (React/TS)  │◄───►│ Server      │◄───►│ (Python)│  │
│  └─────────────┘    │ (FastAPI)   │    └─────────┘  │
│                    └─────────────┘                  │
│                         │                           │
│                         ▼                           │
│              ┌─────────────────┐                   │
│              │  PostgreSQL     │                   │
│              │  Database       │                   │
│              └─────────────────┘                   │
│                         │                           │
│                         ▼                           │
│              ┌─────────────────┐                   │
│              │   Grafana       │                   │
│              │  Monitoring     │                   │
│              └─────────────────┘                   │
└───────────────────────────────────────────────────┘
```

## Software Components

### 1. Frontend

**Technology Stack:**
- React 18+
- TypeScript
- Vite
- Tailwind CSS
- ShadCN UI Components

**Key Features:**
- Web-based interface for test management
- Real-time device control and monitoring
- Test case builder and editor
- Dashboard and analytics
- Multi-device management

**Installation:**
```bash
# Navigate to frontend directory
cd /Users/cpeengineering/virtualpytest/frontend

# Install dependencies
npm install

# Build for production
npm run build

# Run development server
npm run dev
```

**Configuration:**
```bash
# Environment variables
cp .env.example .env

# Edit configuration
nano .env
```

### 2. Backend Server

**Technology Stack:**
- Python 3.10+
- FastAPI
- SQLAlchemy
- PostgreSQL
- Pydantic

**Key Features:**
- REST API for test management
- Campaign execution and scheduling
- Device management and coordination
- AI-powered test analysis
- Authentication and authorization

**Installation:**
```bash
# Navigate to backend server directory
cd /Users/cpeengineering/virtualpytest/backend_server

# Install Python dependencies
pip install -r requirements.txt

# Run server
python src/app.py
```

**Configuration:**
```bash
# Environment variables
cp .env.example .env

# Edit configuration
nano .env
```

### 3. Backend Host

**Technology Stack:**
- Python 3.10+
- FastAPI
- OpenCV
- PyAutoGUI
- FFmpeg
- VNC/NoVNC

**Key Features:**
- Device control and automation
- Video capture and processing
- Remote control via VNC
- Test execution engine
- Hardware interaction

**Installation:**
```bash
# Navigate to backend host directory
cd /Users/cpeengineering/virtualpytest/backend_host

# Install Python dependencies
pip install -r requirements.txt

# Run host service
python src/app.py
```

**Configuration:**
```bash
# Environment variables
cp .env.example .env

# Edit configuration
nano .env
```

## Supporting Services

### 1. PostgreSQL Database

**Installation:**
```bash
# Install PostgreSQL
sudo apt install postgresql postgresql-contrib

# Start service
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database
sudo -u postgres createdb virtualpytest
sudo -u postgres createuser virtualpytest_user
```

**Configuration:**
```bash
# Edit PostgreSQL configuration
sudo nano /etc/postgresql/14/main/postgresql.conf

# Edit pg_hba.conf
sudo nano /etc/postgresql/14/main/pg_hba.conf
```

### 2. Grafana

**Installation:**
```bash
# Install Grafana
sudo apt install grafana

# Start service
sudo systemctl start grafana-server
sudo systemctl enable grafana-server

# Access at http://localhost:3001
```

**Configuration:**
```bash
# Edit Grafana configuration
sudo nano /etc/grafana/grafana.ini

# Add PostgreSQL data source
```

### 3. Redis (Optional)

**Installation:**
```bash
# Install Redis
sudo apt install redis-server

# Start service
sudo systemctl start redis
sudo systemctl enable redis
```

## Software Installation Workflow

### 1. System Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install basic dependencies
sudo apt install -y git curl wget build-essential python3 python3-pip python3-venv

# Install Node.js (for frontend)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Install FFmpeg
sudo apt install -y ffmpeg

# Install VNC server
sudo apt install -y tigervnc-standalone-server
```

### 2. Clone Repository

```bash
# Clone VirtualPytest repository
git clone https://github.com/virtualpytest/virtualpytest.git
cd virtualpytest

# Checkout desired branch
git checkout dev
```

### 3. Install Components

```bash
# Install frontend dependencies
cd frontend
npm install

# Install backend server dependencies
cd ../backend_server
pip install -r requirements.txt

# Install backend host dependencies
cd ../backend_host
pip install -r requirements.txt
```

### 4. Configuration

```bash
# Copy environment files
cp .env.example .env
cd frontend && cp .env.example .env && cd ..
cd backend_server && cp .env.example .env && cd ..
cd backend_host && cp .env.example .env && cd ..

# Edit configurations
nano .env
nano frontend/.env
nano backend_server/.env
nano backend_host/.env
```

## Service Management

### Systemd Services

```bash
# Create systemd service for backend server
sudo nano /etc/systemd/system/virtualpytest-server.service
```

Example service file:
```ini
[Unit]
Description=VirtualPytest Backend Server
After=network.target postgresql.service

[Service]
User=virtualpytest
WorkingDirectory=/Users/cpeengineering/virtualpytest/backend_server
ExecStart=/usr/bin/python3 /Users/cpeengineering/virtualpytest/backend_server/src/app.py
Restart=always
Environment="PATH=/usr/bin:/usr/local/bin"
EnvironmentFile=/Users/cpeengineering/virtualpytest/backend_server/.env

[Install]
WantedBy=multi-user.target
```

```bash
# Create systemd service for backend host
sudo nano /etc/systemd/system/virtualpytest-host.service
```

Example service file:
```ini
[Unit]
Description=VirtualPytest Backend Host
After=network.target

[Service]
User=virtualpytest
WorkingDirectory=/Users/cpeengineering/virtualpytest/backend_host
ExecStart=/usr/bin/python3 /Users/cpeengineering/virtualpytest/backend_host/src/app.py
Restart=always
Environment="PATH=/usr/bin:/usr/local/bin"
EnvironmentFile=/Users/cpeengineering/virtualpytest/backend_host/.env

[Install]
WantedBy=multi-user.target
```

### Service Commands

```bash
# Enable services
sudo systemctl enable virtualpytest-server
sudo systemctl enable virtualpytest-host

# Start services
sudo systemctl start virtualpytest-server
sudo systemctl start virtualpytest-host

# Check status
sudo systemctl status virtualpytest-server
sudo systemctl status virtualpytest-host

# View logs
journalctl -u virtualpytest-server -f
journalctl -u virtualpytest-host -f
```

## Software Updates

### Update Workflow

```bash
# Pull latest changes
cd /Users/cpeengineering/virtualpytest
git pull origin dev

# Update frontend dependencies
cd frontend
npm update

# Update Python dependencies
cd ../backend_server
pip install -r requirements.txt --upgrade

cd ../backend_host
pip install -r requirements.txt --upgrade

# Restart services
sudo systemctl restart virtualpytest-server
sudo systemctl restart virtualpytest-host
```

## Troubleshooting

### Common Issues

1. **Port Conflicts**: Check with `netstat -tuln`
2. **Dependency Issues**: Use virtual environments
3. **Permission Problems**: Check file permissions and user groups
4. **Database Connection**: Verify PostgreSQL is running and accessible

### Diagnostic Commands

```bash
# Check running processes
ps aux | grep virtualpytest

# Check open ports
ss -tuln

# Check service status
sudo systemctl status virtualpytest-server
sudo systemctl status virtualpytest-host

# Check logs
journalctl -u virtualpytest-server -n 50
journalctl -u virtualpytest-host -n 50

# Test API endpoints
curl http://localhost:8000/api/health
curl http://localhost:5000/api/health
```

## Next Steps

After software installation:
1. Configure authentication
2. Set up initial users and permissions
3. Configure devices and connections
4. Run initial tests to verify installation
