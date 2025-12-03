# 🚀 Quick Start - Docker Installation

Get VirtualPyTest up and running in **5 minutes** with Docker.

## What You'll Get

✅ Complete testing platform (Frontend + Backend + Database)  
✅ Web interface at `http://localhost:3000`  
✅ Device control and monitoring  
✅ AI-powered test automation  

---

## Prerequisites

- **Docker** & **Docker Compose** installed ([Get Docker](https://docs.docker.com/get-docker/))
- **Git** installed
- **8GB RAM** minimum
- **20GB disk space**

---

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/angelstreet/virtualpytest.git
cd virtualpytest
```

### 2. Run Quick Start Script

```bash
./setup/quickstart.sh
```

That's it! The script will:
- ✅ Install Docker & Docker Compose (if needed)
- ✅ Set up all configurations
- ✅ Launch the full stack
- ✅ Open the dashboard automatically

### 3. Access Your Platform

Open your browser to:

**🌐 http://localhost:3000**

Default services:
- **Frontend**: http://localhost:3000
- **Backend Server**: http://localhost:5109
- **Backend Host**: http://localhost:6109
- **Virtual Desktop (NoVNC)**: http://localhost:6080

---

## First Steps

### 1. **Explore the Dashboard**
   - View system status
   - Check connected devices
   - Browse available features

### 2. **Connect a Device** (Optional)
   - Navigate to Settings → Models
   - Add your Android TV, mobile, or STB
   - Configure connection (ADB/IR/Appium)

### 3. **Run Your First Test**
   - Go to Test → Run Tests
   - Select a device
   - Execute a simple navigation test

---

## What's Next?

- 📖 **[Features Overview](../features/README.md)** - See what VirtualPyTest can do
- 📚 **[User Guide](../user-guide/README.md)** - Learn how to use the platform
- 🔧 **[Technical Docs](../technical/README.md)** - Understand the architecture
- 🔌 **[Integrations](../integrations/README.md)** - Connect to JIRA, Grafana, etc.

---

## Troubleshooting

### Docker not found
```bash
# Install Docker first
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
```

### Port conflicts
If port 3000 is already in use, edit `docker-compose.yml` and change the port mapping.

### Can't access the dashboard
- Check Docker is running: `docker ps`
- Verify services: `docker-compose logs`
- Restart: `docker-compose restart`

---

## Need Help?

- 🐛 [Report Issues](https://github.com/angelstreet/virtualpytest/issues)
- 💬 [Ask Questions](https://github.com/angelstreet/virtualpytest/discussions)
- 📖 [Full Documentation](../README.md)

---

**⚡ Pro Tip**: For advanced setup options (local development, cloud deployment), see the [other setup guides](./README.md).


