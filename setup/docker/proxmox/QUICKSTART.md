# VirtualPyTest - Proxmox Quick Start

Deploy VirtualPyTest on Proxmox in 10 minutes.

## Prerequisites

- Proxmox VE 7.0+ installed
- 8GB+ RAM (4GB for VM, 4GB for Proxmox)
- 60GB+ free storage
- Domain name pointed to Proxmox public IP
- SSH access to Proxmox host

## Quick Setup

### 1. Clone Repository on Proxmox Host

```bash
ssh root@your-proxmox-host

cd /root
git clone https://github.com/youruser/virtualpytest.git
cd virtualpytest/setup/docker/proxmox
```

### 2. Configure

```bash
# Copy example config
cp config.env.example config.env

# Edit configuration
nano config.env
```

**Required settings:**
```bash
VM_ID=100
VM_NAME="virtualpytest"
VM_MEMORY=4096  # 4GB RAM
VM_CORES=2
VM_DISK_SIZE=40G

# Set password OR SSH key (SSH key recommended)
VM_PASSWORD="YourStrongPassword123"
# OR
VM_SSH_KEY="$HOME/.ssh/id_rsa.pub"

# Your domain
DOMAIN="virtualpytest.example.com"

# Storage (check with: pvesm status)
STORAGE="local-lvm"
```

### 3. Create VM

```bash
./setup.sh
```

This will:
- Download Ubuntu 22.04 Cloud Image (~350MB)
- Create VM with 4GB RAM, 2 cores, 40GB disk
- Configure cloud-init
- Start VM
- Show VM IP address

**Output:**
```
✅ VM Setup Complete!
VM IP: 192.168.1.100
SSH: ssh ubuntu@192.168.1.100
```

### 4. Setup Inside VM

```bash
# SSH into VM
ssh ubuntu@192.168.1.100

# Install Docker
sudo apt update
sudo apt install -y docker.io docker-compose git curl
sudo usermod -aG docker ubuntu

# Logout and login again for docker group
exit
ssh ubuntu@192.168.1.100

# Verify Docker works
docker ps

# Clone repository
git clone https://github.com/youruser/virtualpytest.git
cd virtualpytest
```

### 5. Configure VirtualPyTest

```bash
# Inside VM, create main .env file
cp setup/docker/hetzner_custom/env.example .env
nano .env
```

**Add your credentials:**
```bash
SUPABASE_DB_URI=postgresql://user:pass@host/db
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
API_KEY=your-secret-api-key-for-authentication
```

### 6. Run Hetzner Setup (works unchanged in VM!)

```bash
cd setup/docker/hetzner_custom

# Copy config
cp config.env.example config.env
nano config.env
```

**Configure for VM environment:**
```bash
DEPLOYMENT_NAME="proxmox1"
HOST_MAX=8
HOST_START_PORT=5001
SERVER_PORT=8001
DOMAIN="virtualpytest.example.com"
ENABLE_GRAFANA=false  # Optional
USE_VPN=false         # Not needed in VM
```

**Run setup:**
```bash
./setup.sh
./launch.sh
```

**Verify containers:**
```bash
docker-compose ps

# Should show:
# backend_server (port 8001)
# backend_host_1 (port 5001)
# backend_host_2 (port 5002)
# ... up to backend_host_8 (port 5008)
```

### 7. Configure Nginx on Proxmox Host

Exit VM and return to Proxmox host:

```bash
exit  # Leave VM

# On Proxmox host
cd /root/virtualpytest/setup/docker/proxmox
./setup_nginx.sh
```

This will:
- Generate Nginx config
- Proxy traffic from Proxmox → VM
- Setup SSL with certbot

### 8. Test Access

```bash
# Test health endpoint
curl https://virtualpytest.example.com/health

# Open browser
https://virtualpytest.example.com/host1/vnc/vnc_lite.html
```

## Management Commands

### VM Management (on Proxmox host)

```bash
cd /root/virtualpytest/setup/docker/proxmox

./launch.sh start      # Start VM
./launch.sh stop       # Stop VM
./launch.sh restart    # Restart VM
./launch.sh status     # Show status and IP
./launch.sh console    # Open console
./launch.sh ssh        # SSH into VM
```

### Docker Management (inside VM)

```bash
ssh ubuntu@<VM_IP>
cd virtualpytest/setup/docker/hetzner_custom

docker-compose ps              # Show containers
docker-compose logs -f         # Show logs
docker-compose restart         # Restart all
docker-compose stop host_5     # Stop one host
```

### Snapshots (on Proxmox host)

```bash
# Before updates
./launch.sh snapshot before-update

# After breaking something
./launch.sh rollback before-update
```

## Troubleshooting

### Can't SSH to VM

```bash
# Get IP from console
./launch.sh console
# Inside console: ip addr show

# Or check Proxmox UI
# Datacenter → node → VM 100 → Summary
```

### Docker Not Working

```bash
# Inside VM
sudo systemctl status docker
sudo usermod -aG docker ubuntu
exit  # Logout and login again
```

### Containers Won't Start

```bash
# Inside VM
cd virtualpytest/setup/docker/hetzner_custom

# Check logs
docker-compose logs backend_server

# Restart
docker-compose restart

# Rebuild
docker-compose down
docker-compose up -d --build
```

### VM IP Changed (DHCP)

```bash
# On Proxmox host
./launch.sh status  # Get new IP

# Update Nginx
./setup_nginx.sh
```

Or set static IP in config.env:
```bash
VM_IP_CONFIG="ip=192.168.1.100/24,gw=192.168.1.1"
```

### Out of Memory

```bash
# Stop VM
./launch.sh stop

# Increase RAM
./launch.sh resize
# Choose option 1 (Memory)

# Or edit directly
qm set 100 --memory 8192  # 8GB

# Start VM
./launch.sh start
```

## Architecture

```
Internet
  ↓ HTTPS (443)
Proxmox Host
  ├── Nginx (SSL termination)
  │   ├── Proxies to VM IP
  │   └── Certbot (Let's Encrypt)
  └── VM (Ubuntu 22.04)
      ├── Docker Engine
      ├── backend_server:8001
      ├── backend_host_1:5001
      ├── backend_host_2:5002
      └── ... (up to host_8:5008)
```

## Resources

- **Full Documentation**: [README.md](README.md)
- **Configuration Reference**: [config.env.example](config.env.example)
- **Hetzner Setup**: [../hetzner_custom/setup.sh](../hetzner_custom/setup.sh)

## Next Steps

1. ✅ VM created and running
2. ✅ Docker containers deployed
3. ✅ Nginx configured
4. 📱 Setup frontend (optional)
5. 🔄 Configure backups
6. 📊 Enable Grafana monitoring

## Support

Issues? Check:
1. VM console: `./launch.sh console`
2. VM logs: `./launch.sh logs`
3. Docker logs inside VM: `docker-compose logs`
4. Nginx logs: `/var/log/nginx/error.log`

