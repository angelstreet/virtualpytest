# VirtualPyTest - Microservices Architecture

Modern test automation framework with microservices architecture for scalable device testing and validation.

## 🏗️ Architecture Overview

VirtualPyTest is now organized as microservices for better scalability, maintainability, and deployment flexibility:

```
virtualpytest/
├── shared/              # Shared libraries and utilities
├── backend_core/        # Core business logic and device controllers
├── backend_server/      # API server and client interface
├── backend_host/        # Hardware interface service
├── frontend/           # React TypeScript UI application
└── docker/             # Container orchestration
```

## 🚀 Getting Started

Choose your setup path based on your needs:

### 📚 **[Complete Setup Guides](./docs/get-started/README.md)**

**New to VirtualPyTest?** Start here for comprehensive step-by-step guides:

- 🏠 **[Local Development Setup](./docs/get-started/local-setup.md)** - Perfect for development and testing
- ☁️ **[Cloud + Local Hybrid Setup](./docs/get-started/cloud-setup.md)** - Production-ready deployment
- 🗄️ **[Database Setup (Supabase)](./docs/get-started/supabase-setup.md)** - Required for both setups

### ⚡ Quick Start (Experienced Users)

**Environment Setup:**
```bash
# Copy environment templates
cp env.example .env                    # Project-level (backend_server, shared, backend_core)
cp frontend/env.example frontend/.env  # Frontend (API endpoints)
cp backend_host/src/env.example backend_host/src/.env  # Host (device config)

# Edit with your values
nano .env
nano frontend/.env
nano backend_host/src/.env
```

**Local Development:**
```bash
# Clone and install everything
git clone <your-repo-url>
cd virtualpytest
./setup/local/install_local.sh

# Launch all services
./setup/local/launch_all.sh
```

**Docker Deployment:**
```bash
# Install Docker and launch
./setup/docker/install_docker.sh
./setup/docker/launch_all.sh
```

### 🌐 Access Your Services

After setup, access your services at:
- **Frontend**: http://localhost:3000
- **Backend Server**: http://localhost:5109  
- **Backend Host**: http://localhost:6409

### 📋 Prerequisites

- **Node.js** 18+ and npm
- **Python** 3.8+
- **Git**
- **Supabase account** (for database)

> 💡 **Need detailed instructions?** Follow the [complete setup guides](./docs/get-started/README.md) for step-by-step instructions with troubleshooting and configuration details.

## 📦 Services

### 🔧 backend_host (Hardware Interface)
- **Port**: 6109
- **Purpose**: Direct hardware control and device management
- **Deployment**: Raspberry Pi, local hardware
- **Features**: Device controllers, system monitoring, hardware abstraction

### 🖥️ backend_server (API Server)
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
- **Environment**: Copy `shared/env.example` to `shared/.env` and configure
- **Features**: Configuration, data models, utilities

## 🌐 Deployment Options

### Option 1: Full Cloud + Local Hardware
```
Vercel (Frontend) → Render (backend_server) → RPi (backend_host)
```

### Option 2: Docker on Single Host
```bash
docker-compose -f docker/docker-compose.yml up
```

### Option 3: Development Setup
```bash
# Terminal 1: backend_server
cd backend_server && python src/app.py

# Terminal 2: backend_host  
cd backend_host && python src/app.py

# Terminal 3: Frontend
cd frontend && npm run dev
```

## 🔧 Configuration

### Environment Variables

#### backend_server (uses project-level .env)
```bash
SERVER_URL=http://localhost:5109
SERVER_PORT=5109
DEBUG=false
CORS_ORIGINS=http://localhost:3000
```

#### backend_host (src/.env)
```bash
HOST_URL=http://localhost:6109
HOST_PORT=6109
HOST_NAME=my-host-1
SERVER_URL=http://localhost:5109
```

#### Frontend (.env)
```bash
VITE_SERVER_URL=http://localhost:5109
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
docker compose -f docker/docker-compose.yml logs -f

# Scale backend_server
docker-compose up --scale backend_server=3
```

## 🛠️ Development

### Project Structure

```
virtualpytest/
├── shared/lib/
│   ├── config/         # Shared configuration
│   ├── models/         # Data models
│   └── utils/          # Common utilities
├── backend_core/src/
│   ├── controllers/    # Device controllers
│   └── services/       # Business services
├── backend_server/src/
│   ├── routes/         # API endpoints
│   └── middleware/     # Flask middleware
├── backend_host/src/
│   ├── routes/         # Hardware interface endpoints
│   └── services/       # Host services
└── frontend/src/
    ├── components/     # React components
    ├── pages/          # Page components
    └── services/       # API clients
```

### Adding New Features

1. **Shared utilities**: Add to `shared/lib/`
2. **Device controllers**: Add to `backend_core/src/controllers/`
3. **API endpoints**: Add to `backend_server/src/routes/`
4. **Hardware interfaces**: Add to `backend_host/src/routes/`
5. **UI components**: Add to `frontend/src/components/`

## 📊 Monitoring

### Health Checks
- backend_server: `http://localhost:5109/api/health`
- backend_host: `http://localhost:6109/host/health`
- Frontend: `http://localhost:3000` (or port 80 in production)

### Logs
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f backend_server
```

## 🚀 Production Deployment

### Vercel (Frontend)
1. Connect repository to Vercel
2. Set environment variables:
   - `VITE_SERVER_URL=https://your-backend_server.onrender.com`
3. Auto-deploy on git push

### Render (backend_server)
1. Connect repository to Render
2. Set build command: `cd backend_server && pip install -r requirements.txt`
3. Set start command: `cd backend_server && python src/app.py`
4. Configure environment variables

### Raspberry Pi (backend_host)
```bash
# Clone and setup
git clone <repository-url>
cd virtualpytest

# Install and run
cd backend_host
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
