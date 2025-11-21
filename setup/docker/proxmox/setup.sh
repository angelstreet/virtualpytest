#!/bin/bash
# VirtualPyTest Proxmox VM Setup
# Creates Ubuntu VM with Docker for VirtualPyTest deployment

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 VirtualPyTest Proxmox VM Setup"
echo "===================================="
echo ""

# ============================================
# LOAD CONFIGURATION
# ============================================

if [ ! -f "config.env" ]; then
    if [ -f "config.env.example" ]; then
        echo "📋 Creating config.env from example..."
        cp config.env.example config.env
        echo "✅ config.env created"
        echo "   ⚠️  EDIT config.env before continuing!"
        echo "   Required: VM_PASSWORD or VM_SSH_KEY, DOMAIN"
        echo ""
        exit 1
    else
        echo "❌ Error: config.env.example not found"
        exit 1
    fi
fi

source config.env

# ============================================
# VALIDATE CONFIGURATION
# ============================================

echo "📋 Configuration:"
echo "   VM ID: $VM_ID"
echo "   VM Name: $VM_NAME"
echo "   Memory: ${VM_MEMORY}MB ($(($VM_MEMORY / 1024))GB)"
echo "   Cores: $VM_CORES"
echo "   Disk: $VM_DISK_SIZE"
echo "   Storage: $STORAGE"
echo "   Network: $VM_BRIDGE ($VM_IP_CONFIG)"
echo "   Domain: $DOMAIN"
echo ""

# Check if VM already exists
if qm status $VM_ID &>/dev/null; then
    echo "⚠️  VM $VM_ID already exists!"
    echo ""
    qm config $VM_ID | head -5
    echo ""
    read -p "Delete existing VM and recreate? (y/N) " -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🗑️  Stopping and removing VM $VM_ID..."
        qm stop $VM_ID 2>/dev/null || true
        sleep 2
        qm destroy $VM_ID
        echo "✅ VM removed"
    else
        echo "Setup cancelled. Use a different VM_ID in config.env"
        exit 1
    fi
fi

# Check if storage exists
if ! pvesm status | grep -q "^$STORAGE"; then
    echo "❌ Error: Storage '$STORAGE' not found"
    echo ""
    echo "Available storage:"
    pvesm status
    echo ""
    echo "Edit config.env and set STORAGE to one of the above"
    exit 1
fi

# Validate credentials
if [ -z "$VM_PASSWORD" ] && [ -z "$VM_SSH_KEY" ]; then
    echo "❌ Error: Must set VM_PASSWORD or VM_SSH_KEY in config.env"
    echo ""
    echo "For SSH key (recommended):"
    echo "   VM_SSH_KEY=\"\$HOME/.ssh/id_rsa.pub\""
    echo ""
    echo "For password:"
    echo "   VM_PASSWORD=\"YourStrongPassword123\""
    exit 1
fi

# ============================================
# DOWNLOAD UBUNTU CLOUD IMAGE
# ============================================

IMAGE_FILE="/tmp/ubuntu-cloud-$VM_ID.img"

if [ -f "$IMAGE_FILE" ]; then
    echo "✅ Cloud image already downloaded: $IMAGE_FILE"
else
    echo "📦 Downloading Ubuntu $UBUNTU_VERSION Cloud Image..."
    echo "   URL: $UBUNTU_IMAGE_URL"
    echo "   Size: ~350MB"
    echo ""
    
    if wget -q --show-progress "$UBUNTU_IMAGE_URL" -O "$IMAGE_FILE"; then
        echo "✅ Download complete"
    else
        echo "❌ Download failed"
        rm -f "$IMAGE_FILE"
        exit 1
    fi
fi

echo ""

# ============================================
# CREATE VM
# ============================================

echo "🔧 Creating VM $VM_ID ($VM_NAME)..."

qm create $VM_ID \
    --name "$VM_NAME" \
    --memory $VM_MEMORY \
    --cores $VM_CORES \
    --net0 virtio,bridge=$VM_BRIDGE \
    --agent enabled=$VM_AGENT \
    --ostype l26 \
    --onboot $VM_ONBOOT

echo "✅ VM created"

# ============================================
# IMPORT DISK
# ============================================

echo "💾 Importing disk image..."

qm importdisk $VM_ID "$IMAGE_FILE" "$STORAGE" --format qcow2

# Find the imported disk name
DISK_NAME=$(qm config $VM_ID | grep "^unused" | head -1 | cut -d: -f1)

if [ -z "$DISK_NAME" ]; then
    echo "❌ Failed to import disk"
    qm destroy $VM_ID
    exit 1
fi

echo "✅ Disk imported as $DISK_NAME"

# ============================================
# CONFIGURE VM
# ============================================

echo "⚙️  Configuring VM..."

# Attach disk
qm set $VM_ID --scsihw virtio-scsi-pci
qm set $VM_ID --scsi0 ${STORAGE}:vm-${VM_ID}-disk-0

# Add cloud-init drive
qm set $VM_ID --ide2 ${STORAGE}:cloudinit

# Set boot order
qm set $VM_ID --boot order=scsi0

# Serial console
qm set $VM_ID --serial0 socket --vga serial0

# CPU type
if [ -n "$VM_CPU_TYPE" ]; then
    qm set $VM_ID --cpu $VM_CPU_TYPE
fi

# Memory ballooning
if [ "$VM_BALLOON" -gt 0 ]; then
    qm set $VM_ID --balloon $VM_BALLOON
fi

echo "✅ VM configured"

# ============================================
# RESIZE DISK
# ============================================

echo "📏 Resizing disk to $VM_DISK_SIZE..."

qm resize $VM_ID scsi0 $VM_DISK_SIZE

echo "✅ Disk resized"

# ============================================
# CONFIGURE CLOUD-INIT
# ============================================

echo "🔑 Configuring cloud-init..."

# User
qm set $VM_ID --ciuser "$VM_USER"

# Password or SSH key
if [ -n "$VM_SSH_KEY" ]; then
    if [ -f "$VM_SSH_KEY" ]; then
        qm set $VM_ID --sshkeys "$VM_SSH_KEY"
        echo "✅ SSH key configured: $VM_SSH_KEY"
    else
        echo "⚠️  SSH key not found: $VM_SSH_KEY"
        if [ -n "$VM_PASSWORD" ]; then
            qm set $VM_ID --cipassword "$VM_PASSWORD"
            echo "✅ Password configured (fallback)"
        else
            echo "❌ Error: No valid authentication method"
            qm destroy $VM_ID
            exit 1
        fi
    fi
elif [ -n "$VM_PASSWORD" ]; then
    qm set $VM_ID --cipassword "$VM_PASSWORD"
    echo "✅ Password configured"
fi

# Network
qm set $VM_ID --ipconfig0 "$VM_IP_CONFIG"

# DNS
if [ -n "$VM_NAMESERVER" ]; then
    qm set $VM_ID --nameserver "$VM_NAMESERVER"
fi

echo "✅ Cloud-init configured"

# ============================================
# USB DEVICE PASSTHROUGH
# ============================================

if [ -n "$USB_DEVICE_1" ]; then
    echo "🔌 Configuring USB passthrough..."
    qm set $VM_ID --usb0 "$USB_DEVICE_1"
    echo "✅ USB device 1: $USB_DEVICE_1"
fi

if [ -n "$USB_DEVICE_2" ]; then
    qm set $VM_ID --usb1 "$USB_DEVICE_2"
    echo "✅ USB device 2: $USB_DEVICE_2"
fi

# ============================================
# GPU PASSTHROUGH
# ============================================

if [ -n "$GPU_PASSTHROUGH" ]; then
    echo "🎮 Configuring GPU passthrough..."
    qm set $VM_ID --hostpci0 "$GPU_PASSTHROUGH,pcie=1"
    echo "✅ GPU: $GPU_PASSTHROUGH"
    echo "   ⚠️  Ensure IOMMU is enabled in BIOS!"
fi

# ============================================
# START VM
# ============================================

echo ""
echo "🚀 Starting VM..."

qm start $VM_ID

echo "✅ VM started"

# ============================================
# WAIT FOR VM TO BOOT
# ============================================

echo ""
echo "⏳ Waiting for VM to boot (30 seconds)..."
sleep 5

for i in {1..25}; do
    echo -n "."
    sleep 1
done

echo ""
echo ""

# ============================================
# GET VM IP ADDRESS
# ============================================

echo "🌐 Getting VM IP address..."
sleep 5

VM_IP=$(qm guest exec $VM_ID -- ip -4 addr show | grep -oP 'inet \K[\d.]+' | grep -v '127.0.0.1' | head -1 2>/dev/null || echo "")

if [ -z "$VM_IP" ]; then
    echo "⚠️  Unable to detect VM IP automatically"
    echo ""
    echo "Options to find IP:"
    echo "   1. Check Proxmox console: qm terminal $VM_ID"
    echo "   2. Check DHCP server logs"
    echo "   3. Login via console and run: ip addr show"
else
    echo "✅ VM IP: $VM_IP"
fi

# ============================================
# CLEANUP
# ============================================

echo ""
echo "🧹 Cleaning up..."
rm -f "$IMAGE_FILE"
echo "✅ Temporary files removed"

# ============================================
# SUMMARY
# ============================================

echo ""
echo "===================================="
echo "✅ VM Setup Complete!"
echo "===================================="
echo ""
echo "📋 VM Details:"
echo "   ID: $VM_ID"
echo "   Name: $VM_NAME"
echo "   RAM: ${VM_MEMORY}MB"
echo "   Cores: $VM_CORES"
echo "   Disk: $VM_DISK_SIZE"
if [ -n "$VM_IP" ]; then
    echo "   IP: $VM_IP"
fi
echo ""
echo "🔐 Login:"
echo "   User: $VM_USER"
if [ -n "$VM_SSH_KEY" ]; then
    echo "   Auth: SSH key"
else
    echo "   Auth: Password"
fi
echo ""

if [ -n "$VM_IP" ]; then
    echo "🌐 SSH Connection:"
    echo "   ssh $VM_USER@$VM_IP"
    echo ""
fi

echo "📝 Next Steps:"
echo ""
echo "1. SSH into VM:"
if [ -n "$VM_IP" ]; then
    echo "   ssh $VM_USER@$VM_IP"
else
    echo "   First get VM IP: qm terminal $VM_ID"
    echo "   Then: ssh $VM_USER@<VM_IP>"
fi
echo ""
echo "2. Install Docker:"
echo "   sudo apt update"
echo "   sudo apt install -y docker.io docker-compose git"
echo "   sudo usermod -aG docker $VM_USER"
echo "   exit  # Logout and login again"
echo ""
echo "3. Clone repository:"
echo "   git clone https://github.com/youruser/virtualpytest.git"
echo "   cd virtualpytest"
echo ""
echo "4. Setup environment:"
echo "   cp setup/docker/hetzner_custom/env.example .env"
echo "   nano .env  # Add SUPABASE_DB_URI, API_KEY, etc."
echo ""
echo "5. Run Hetzner setup (works unchanged in VM!):"
echo "   cd setup/docker/hetzner_custom"
echo "   cp config.env.example config.env"
echo "   nano config.env  # Set DOMAIN=$DOMAIN, HOST_MAX=8"
echo "   ./setup.sh"
echo "   ./launch.sh"
echo ""
echo "6. Configure Nginx on Proxmox host:"
echo "   Back on Proxmox host, run:"
echo "   cd /root/virtualpytest/setup/docker/proxmox"
echo "   ./setup_nginx.sh"
echo ""
echo "🎉 Your Hetzner Docker setup will work unchanged inside this VM!"
echo ""
echo "📚 More commands:"
echo "   ./launch.sh status   # Check VM status"
echo "   ./launch.sh stop     # Stop VM"
echo "   ./launch.sh console  # Open console"
echo ""

