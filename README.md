# VirtualPyTest - Microservices Architecture

Modern test automation framework with microservices architecture for scalable device testing and validation.

## 🏗️ Architecture Overview

VirtualPyTest is now organized as microservices for better scalability, maintainability, and deployment flexibility:

```
virtualpytest/
├── shared/              # Shared libraries and utilities
├── backend-core/        # Core business logic and device controllers
├── backend-server/      # API server and client interface
├── backend-host/        # Hardware interface service
├── frontend/           # React TypeScript UI application
└── docker/             # Container orchestration
```

## 🚀 Quick Start

### Prerequisites

**Quick Setup (Linux/Raspberry Pi):**
```bash
# Install Docker and Docker Compose
./setup/install_docker.sh

# OR install for local development
./setup/install_local.sh
```

**Python Virtual Environment (Recommended for local development):**
```bash
# Install Python venv (if not already available)
sudo apt install python3-venv

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Then run local setup
./setup/install_local.sh
```

### Docker Deployment (Recommended)

```bash
# Clone repository
git clone https://github.com/angelstreet/virtualpytest
cd virtualpytest

# Install Docker (first time only)
./setup/install_docker.sh

# Launch all services
./setup/launch_all.sh

# Access the application
# Frontend: http://localhost:3000
# API: http://localhost:5109
# Host Interface: http://localhost:6109
```

### Local Development

```bash
# Install all dependencies (first time only)
./setup/install_local.sh

# Launch individual services:
./setup/launch_server.sh    # Backend-Server only
./setup/launch_host.sh      # Backend-Host only  
./setup/launch_frontend.sh  # Frontend only
./setup/launch_all.sh       # All services (Docker)
```

## 📦 Services

### 🔧 Backend-Host (Hardware Interface)
- **Port**: 6109
- **Purpose**: Direct hardware control and device management
- **Deployment**: Raspberry Pi, local hardware
- **Features**: Device controllers, system monitoring, hardware abstraction

### 🖥️ Backend-Server (API Server)
- **Port**: 5109  
- **Purpose**: Business logic and client API
- **Deployment**: Render, cloud services
- **Features**: REST API, test orchestration, user management

### 🎨 Frontend (React UI)
- **Port**: 3000 (dev) / 80 (prod)
- **Purpose**: User interface
- **Deployment**: Vercel, static hosting
- **Features**: Test management, device control, monitoring dashboards

### 📚 Shared Library
- **Purpose**: Common utilities and models
- **Usage**: Imported by all backend services
- **Features**: Configuration, data models, utilities

## 🌐 Deployment Options

### Option 1: Full Cloud + Local Hardware
```
Vercel (Frontend) → Render (Backend-Server) → RPi (Backend-Host)
```

### Option 2: Docker on Single Host
```bash
docker-compose -f docker/docker-compose.yml up
```

### Option 3: Development Setup
```bash
# Terminal 1: Backend-Server
cd backend-server && python src/app.py

# Terminal 2: Backend-Host  
cd backend-host && python src/app.py

# Terminal 3: Frontend
cd frontend && npm run dev
```

## 🔧 Configuration

### Environment Variables

#### Backend-Server (.env.server)
```bash
SERVER_URL=http://localhost:5109
SERVER_PORT=5109
DEBUG=false
CORS_ORIGINS=http://localhost:3000
```

#### Backend-Host (.env.host)
```bash
HOST_URL=http://localhost:6109
HOST_PORT=6109
HOST_NAME=my-host-1
SERVER_URL=http://localhost:5109
```

#### Frontend (.env)
```bash
VITE_API_URL=http://localhost:5109
VITE_DEV_MODE=true
```

## 🐳 Docker Commands

```bash
# Build all images
./docker/scripts/build.sh --all

# Deploy development environment
./docker/scripts/deploy.sh development

# Deploy production environment  
./docker/scripts/deploy.sh production

# View logs
docker-compose -f docker/docker-compose.yml logs -f

# Scale backend-server
docker-compose up --scale backend-server=3
```

## 🛠️ Development

### Project Structure

```
virtualpytest/
├── shared/lib/
│   ├── config/         # Shared configuration
│   ├── models/         # Data models
│   └── utils/          # Common utilities
├── backend-core/src/
│   ├── controllers/    # Device controllers
│   └── services/       # Business services
├── backend-server/src/
│   ├── routes/         # API endpoints
│   └── middleware/     # Flask middleware
├── backend-host/src/
│   ├── routes/         # Hardware interface endpoints
│   └── services/       # Host services
└── frontend/src/
    ├── components/     # React components
    ├── pages/          # Page components
    └── services/       # API clients
```

### Adding New Features

1. **Shared utilities**: Add to `shared/lib/`
2. **Device controllers**: Add to `backend-core/src/controllers/`
3. **API endpoints**: Add to `backend-server/src/routes/`
4. **Hardware interfaces**: Add to `backend-host/src/routes/`
5. **UI components**: Add to `frontend/src/components/`

## 📊 Monitoring

### Health Checks
- Backend-Server: `http://localhost:5109/api/health`
- Backend-Host: `http://localhost:6109/host/health`
- Frontend: `http://localhost:3000` (or port 80 in production)

### Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend-server
```

## 🚀 Production Deployment

### Vercel (Frontend)
1. Connect repository to Vercel
2. Set environment variables:
   - `VITE_API_URL=https://your-backend-server.onrender.com`
3. Auto-deploy on git push

### Render (Backend-Server)
1. Connect repository to Render
2. Set build command: `cd backend-server && pip install -r requirements.txt`
3. Set start command: `cd backend-server && python src/app.py`
4. Configure environment variables

### Raspberry Pi (Backend-Host)
```bash
# Clone and setup
git clone <repository-url>
cd virtualpytest

# Install and run
cd backend-host
pip install -r requirements.txt
python src/app.py
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

- **Documentation**: See `docs/` directory
- **Issues**: Create GitHub issue
- **Development**: See individual service READMEs
