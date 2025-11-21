# VirtualPyTest - Proxmox VM Deployment

Deploy VirtualPyTest as a single VM on Proxmox with Docker inside.

## Overview

### Simple Deployment: Use Existing VM

**If you already have a VM on Proxmox**, just use your Hetzner setup unchanged:

```bash
ssh ubuntu@your-vm-ip
cd virtualpytest/setup/docker/hetzner_custom
./setup.sh
./launch.sh
```

No Proxmox-specific scripts needed! ✅

### Scalable Deployment: Multi-VM with Physical Devices

For production environments with physical devices (STBs, phones) and scaling beyond 8 hosts, see:

**📖 [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - Complete scalable architecture guide

```
Proxmox Host
├── VM 101: Server + Grafana (2GB RAM, 2 cores, 20GB)
├── VM 102: Hosts 1-4 + USB + HDMI (4GB RAM, 2 cores, 40GB)
├── VM 103: Hosts 5-8 + USB + HDMI (4GB RAM, 2 cores, 40GB)
└── VM 10N: Scale infinitely...
```

Includes:
- Physical device passthrough (USB for ADB, HDMI capture cards)
- Horizontal scaling (add VMs as needed)
- High availability setup
- Complete deployment automation

## Why VM + Docker?

- ✅ **Zero migration effort** - Hetzner setup.sh works unchanged
- ✅ **Full isolation** - Own kernel, no LXC/Docker conflicts
- ✅ **Snapshots** - Rollback before/after updates
- ✅ **USB passthrough** - Easy device testing (phones, STBs)
- ✅ **Portable** - Export VM, run on any hypervisor
- ✅ **Backup** - Proxmox Backup Server integration

## Requirements

**Proxmox Host:**
- Proxmox VE 7.0+ (tested on 8.0+)
- 8GB+ RAM (4GB for VM + 4GB for Proxmox)
- 60GB+ free storage
- Internet access for downloading Ubuntu image

**Network:**
- Bridge interface (default: vmbr0)
- DHCP server OR static IP configuration
- Domain with SSL cert (for HTTPS access)

## Quick Start

### 1. Run Setup Script (on Proxmox host)

```bash
cd /root
git clone https://github.com/youruser/virtualpytest.git
cd virtualpytest/setup/docker/proxmox

# Edit configuration
cp config.env.example config.env
nano config.env

# Create VM
./setup.sh
```

This will:
- Download Ubuntu 22.04 Cloud Image (~350MB)
- Create VM (ID 100) with 4GB RAM, 2 cores, 40GB disk
- Configure cloud-init (SSH, network)
- Start VM

### 2. Configure Inside VM

```bash
# SSH into VM (get IP from Proxmox console or DHCP)
ssh ubuntu@<VM_IP>

# Clone your repo inside VM
git clone https://github.com/youruser/virtualpytest.git
cd virtualpytest

# Create main .env file
cp setup/docker/hetzner_custom/env.example .env
nano .env
# Add: SUPABASE_DB_URI, API_KEY, etc.

# Run Hetzner setup (works unchanged!)
cd setup/docker/hetzner_custom
cp config.env.example config.env
nano config.env
# Set: DOMAIN=your.domain.com, HOST_MAX=8, etc.

./setup.sh
./launch.sh
```

### 3. Configure Nginx on Proxmox Host

The VM runs Docker containers on internal ports. You need Nginx on Proxmox host for SSL termination:

```bash
# On Proxmox host
cd virtualpytest/setup/docker/proxmox
./setup_nginx.sh
```

## Architecture

### Network Flow

```
Internet
  ↓ HTTPS (443)
Proxmox Host Nginx (SSL termination)
  ↓ HTTP (proxied to VM IP)
VM: Ubuntu with Docker
  ↓
  ├── backend_server:8001
  ├── backend_host_1:5001
  ├── backend_host_2:5002
  ├── ...
  └── backend_host_8:5008
```

### Storage Layout

```
VM Disk (40GB):
├── OS: ~2GB (Ubuntu minimal)
├── Docker images: ~5GB
├── Logs: ~2GB
├── Captures/screenshots: ~5GB
└── Free: ~26GB

VM RAM (4GB):
├── OS: ~200MB
├── Docker: ~150MB
├── backend_server: ~300MB
├── backend_host × 8: ~2800MB (350MB each)
└── Buffer: ~650MB
```

### Tmpfs for Video Captures

Video streams use RAM (tmpfs), not disk:
```
/var/www/html/stream/capture1/hot → 200MB tmpfs
/var/www/html/stream/capture2/hot → 200MB tmpfs
...
Total: 1.6GB in RAM (included in 4GB allocation)
```

## Configuration

### config.env

```bash
# VM Configuration
VM_ID=100                    # Proxmox VM ID (100-999)
VM_NAME="virtualpytest"      # VM name
VM_MEMORY=4096               # RAM in MB (4GB = CX23)
VM_CORES=2                   # CPU cores
VM_DISK_SIZE=40G             # Disk size

# Network
VM_BRIDGE="vmbr0"            # Proxmox bridge
VM_IP_CONFIG="ip=dhcp"       # Or "ip=192.168.1.100/24,gw=192.168.1.1"

# Cloud-init
VM_USER="ubuntu"             # Default user
VM_PASSWORD=""               # Set password or use SSH key
VM_SSH_KEY=""                # Path to public key (recommended)

# Domain
DOMAIN="your.domain.com"     # Your SSL domain

# Storage
STORAGE="local-lvm"          # Proxmox storage (local-lvm, local, etc.)
```

## USB Device Passthrough

Pass USB devices (phones, STBs, IR blasters) to VM:

```bash
# On Proxmox host, find USB device
lsusb
# Example output: Bus 001 Device 005: ID 04e8:6860 Samsung Electronics

# Pass to VM (permanent)
qm set 100 --usb0 host=04e8:6860

# Or pass entire USB port
qm set 100 --usb0 host=1-2

# Restart VM
qm reboot 100

# Inside VM, verify
lsusb
# Device should appear
```

## GPU Passthrough (Optional)

For browser hardware acceleration:

```bash
# On Proxmox host
# 1. Enable IOMMU in BIOS
# 2. Edit /etc/default/grub
GRUB_CMDLINE_LINUX_DEFAULT="quiet intel_iommu=on"  # Intel
# OR
GRUB_CMDLINE_LINUX_DEFAULT="quiet amd_iommu=on"    # AMD

update-grub
reboot

# 3. Pass GPU to VM
qm set 100 --hostpci0 01:00,pcie=1,x-vga=1

# Inside VM, install drivers
sudo apt install -y xserver-xorg-video-intel  # Intel
# OR
sudo apt install -y xserver-xorg-video-amdgpu  # AMD
```

## VM Management

### Start/Stop VM

```bash
# On Proxmox host
cd virtualpytest/setup/docker/proxmox
./launch.sh start    # Start VM
./launch.sh stop     # Stop VM gracefully
./launch.sh restart  # Restart VM
./launch.sh status   # Show VM status
./launch.sh console  # Open console
./launch.sh ssh      # SSH into VM
```

### Snapshots

```bash
# Create snapshot before updates
qm snapshot 100 before-update --description "Before Python upgrade"

# List snapshots
qm listsnapshot 100

# Rollback
qm rollback 100 before-update

# Delete snapshot
qm delsnapshot 100 before-update
```

### Backup

```bash
# Manual backup
vzdump 100 --mode snapshot --compress zstd --storage backup

# Scheduled backups (Proxmox UI)
Datacenter → Backup → Add
```

### Clone VM

```bash
# Create dev/staging copy
qm clone 100 101 --name virtualpytest-dev --full

# Start clone
qm start 101
```

## Resource Scaling

### Add More RAM

```bash
# Stop VM
qm stop 100

# Increase to 8GB
qm set 100 --memory 8192

# Start VM
qm start 100

# Inside VM, update config to run more hosts
cd virtualpytest/setup/docker/hetzner_custom
nano config.env
# Set: HOST_MAX=16
./setup.sh
./launch.sh
```

### Expand Disk

```bash
# Online resize (VM running)
qm resize 100 scsi0 +20G  # Add 20GB

# Inside VM
sudo growpart /dev/sda 1
sudo resize2fs /dev/sda1
df -h  # Verify
```

## Troubleshooting

### VM Won't Start

```bash
# Check VM config
qm config 100

# Check logs
qm terminal 100  # Open console

# Reset cloud-init
qm set 100 --delete ciuser
qm set 100 --ciuser ubuntu --cipassword <password>
qm reboot 100
```

### Can't SSH to VM

```bash
# Get VM IP from console
qm terminal 100
# Inside console:
ip addr show

# Or from Proxmox
qm guest exec 100 -- ip addr show

# Test connectivity
ping <VM_IP>

# Check SSH
ssh -v ubuntu@<VM_IP>
```

### Docker Not Working

```bash
# Inside VM
sudo systemctl status docker
sudo docker ps

# If not installed
sudo apt update
sudo apt install -y docker.io docker-compose
sudo usermod -aG docker ubuntu

# Logout and login
exit
ssh ubuntu@<VM_IP>
docker ps  # Should work without sudo
```

### Out of Memory

```bash
# Inside VM, check usage
free -h
docker stats

# Stop some containers
cd virtualpytest/setup/docker/hetzner_custom
docker-compose stop backend_host_5 backend_host_6 backend_host_7 backend_host_8

# Or increase VM RAM (see Resource Scaling)
```

## Migration from Hetzner

### 1. Backup Hetzner Data

```bash
# On Hetzner server
cd /path/to/virtualpytest
tar czf ~/virtualpytest-backup.tar.gz \
  .env \
  setup/docker/hetzner_custom/config.env \
  backend_host_*/.env

# Download to local machine
scp root@hetzner:<file> ~/Downloads/
```

### 2. Setup Proxmox VM

```bash
# On Proxmox host
cd virtualpytest/setup/docker/proxmox
./setup.sh
```

### 3. Restore Configuration

```bash
# Copy backup to VM
scp ~/Downloads/virtualpytest-backup.tar.gz ubuntu@<VM_IP>:~/

# Inside VM
tar xzf virtualpytest-backup.tar.gz
# Configs are restored

# Start services
cd virtualpytest/setup/docker/hetzner_custom
./launch.sh
```

### 4. Update DNS

Point your domain to new Proxmox public IP:
```
A record: your.domain.com → <Proxmox_Public_IP>
```

### 5. SSL Certificate

```bash
# On Proxmox host
sudo certbot --nginx -d your.domain.com
```

## Performance Tuning

### Enable Ballooning

Allow VM to return unused RAM to host:

```bash
qm set 100 --balloon 2048  # Can shrink to 2GB if idle
```

### CPU Type

```bash
# Use host CPU for better performance
qm set 100 --cpu host

# Or specific type
qm set 100 --cpu x86-64-v2-AES
```

### I/O Threads

```bash
# Enable for better disk performance
qm set 100 --scsihw virtio-scsi-single --iothread 1
```

## Monitoring

### Inside VM

```bash
# Resource usage
htop
docker stats

# Disk usage
df -h
ncdu /var/lib/docker

# Logs
docker-compose logs -f
```

### From Proxmox Host

```bash
# VM stats
qm status 100
qm monitor 100

# Resource usage
pvesh get /nodes/$(hostname)/qemu/100/status/current
```

### Grafana (Optional)

Enable Grafana in your Hetzner config:

```bash
# Inside VM
cd virtualpytest/setup/docker/hetzner_custom
nano config.env
# Set: ENABLE_GRAFANA=true

./setup.sh
./launch.sh

# Access: https://your.domain.com/grafana
```

## Comparison: Proxmox vs Hetzner

| Feature | Hetzner CX23 | Proxmox VM |
|---------|--------------|------------|
| **Cost** | €5.83/month | Hardware cost only |
| **Setup** | Cloud-init instant | 10 min VM creation |
| **Control** | Limited (cloud provider) | Full (your hardware) |
| **Snapshots** | Paid add-on | Free, unlimited |
| **Backup** | €3.20/month | Free (Proxmox Backup Server) |
| **USB Devices** | ❌ Not possible | ✅ Passthrough |
| **GPU** | ❌ Not possible | ✅ Passthrough |
| **Scale** | Upgrade instance | Edit VM config |
| **Migration** | Manual | Live migration (cluster) |

## Support

For issues:
1. Check VM console: `qm terminal 100`
2. Check Docker logs inside VM
3. Check Proxmox logs: `/var/log/syslog`
4. Verify network: VM → Proxmox → Internet

## Security

### Firewall

```bash
# On Proxmox host
# Datacenter → Firewall → Enable

# Allow SSH, HTTP, HTTPS
pve-firewall localnet 192.168.1.0/24

# Restrict VM access
qm set 100 --firewall 1
```

### Updates

```bash
# Proxmox host
apt update && apt upgrade -y

# Inside VM
sudo apt update && sudo apt upgrade -y
sudo reboot

# Docker images (inside VM)
cd virtualpytest/setup/docker/hetzner_custom
docker-compose pull
docker-compose up -d
```

## Next Steps

1. **Setup Proxmox VM**: Run `./setup.sh`
2. **Configure inside VM**: Install Docker, clone repo
3. **Run Hetzner setup**: Your existing setup.sh works unchanged
4. **Setup Nginx**: Configure SSL on Proxmox host
5. **Test**: Access https://your.domain.com/host1/vnc/vnc_lite.html

