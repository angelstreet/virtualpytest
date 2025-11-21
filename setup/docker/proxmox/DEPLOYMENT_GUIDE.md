# VirtualPyTest - Production Datacenter Deployment Guide

Complete guide for deploying VirtualPyTest in production with modular 2-rack architecture: Compute Rack + Device Rack.

**Architecture:** Fully decentralized, horizontally scalable, 80 devices per rack pair.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Two-Rack Design](#two-rack-design)
- [VM Requirements](#vm-requirements)
- [Hardware Bill of Materials](#hardware-bill-of-materials)
- [Physical Device Integration](#physical-device-integration)
- [Network Architecture](#network-architecture)
- [Initial Setup](#initial-setup)
- [Device Passthrough Configuration](#device-passthrough-configuration)
- [Deployment](#deployment)
- [Scaling Operations](#scaling-operations)
- [Management](#management)
- [High Availability](#high-availability)
- [Troubleshooting](#troubleshooting)

**For demo/testing setup, see:** [DEMO_SETUP.md](DEMO_SETUP.md)

---

## Architecture Overview

### Two-Rack Modular Design

**Separation of Concerns:** Compute vs Devices for infinite scalability.

```
Datacenter Floor
┌──────────────────┐  ┌──────────────────┐
│   RACK A         │  │   RACK B         │
│   COMPUTE ONLY   │  │   DEVICES ONLY   │
│                  │  │                  │
│ • 5 Servers      │  │ • 0 Servers      │
│ • Capture Cards  │──┼──> • STBs        │
│ • USB Hubs       │──┼──> • Mobiles     │
│ • IR Controllers │──┼──> • Shelves     │
│ • Network        │  │                  │
│                  │  │                  │
│ 42U = 80 devices │  │ 42U = 80 devices │
└──────────────────┘  └──────────────────┘
        ↑                     ↑
        └───── 10GbE ─────────┘
             5m cables
```

### Why This Architecture?

**Advantages:**
- ✅ **Modular Scaling** - 1 rack pair = 80 devices, add pairs to scale (80→160→240→320+)
- ✅ **Fully Decentralized** - Each Host VM has own backend_server (no single point of failure)
- ✅ **Clean Separation** - Compute rack (expensive) vs Device rack (cheap)
- ✅ **Flexibility** - Change device mix (STB/mobile) without touching compute
- ✅ **Cost Effective** - $838/device infrastructure cost
- ✅ **Linear Scaling** - Double capacity = add 2 racks = add $67k

### Scaling Path

| Phase | Total Devices | Compute Racks | Device Racks | Total Racks | Cost |
|-------|---------------|---------------|--------------|-------------|------|
| **Phase 1** | 80 | 1 | 1 | 2 | $67k |
| **Phase 2** | 160 | 2 | 2 | 4 | $134k |
| **Phase 3** | 240 | 3 | 3 | 6 | $201k |
| **Phase 4** | 320 | 4 | 4 | 8 | $268k |
| **Phase N** | 80×N | N | N | 2×N | $67k×N |

**Start small (80), scale infinitely by adding rack pairs!**

---

## Two-Rack Design (80 Devices per Pair)

### Rack A: Compute Infrastructure (42U - Full Utilization)

```
┌─────────────────────────────────────────────────────────────┐
│ RACK A - COMPUTE ONLY (No Physical Devices)                 │
├─────────────────────────────────────────────────────────────┤
│ U42-41 (2U): Core Network Switch                            │
│              - 48-port 10GbE managed switch                  │
│              - Uplink to datacenter                          │
│              - Inter-rack connectivity                       │
├─────────────────────────────────────────────────────────────┤
│ U40-37 (4U): Proxmox Server #1 (Frontend + 16 devices)      │
│              CPU: AMD EPYC 7313P (16 cores)                  │
│              RAM: 128GB DDR4 ECC                             │
│              Storage: 2×2TB NVMe RAID1                       │
│              PCIe: 4× HDMI Quad Cards (16 inputs)            │
│                    1× USB Controller + 1× IR Controller      │
│              VMs: 1 Frontend + 4 Host VMs (devices 1-16)     │
│              Power: 450W                                     │
├─────────────────────────────────────────────────────────────┤
│ U36-33 (4U): Proxmox Server #2 (16 devices: 17-32)          │
│              Same config, VMs: 4 Host VMs                    │
│              Power: 400W                                     │
├─────────────────────────────────────────────────────────────┤
│ U32-29 (4U): Proxmox Server #3 (16 devices: 33-48)          │
│              Same config, VMs: 4 Host VMs                    │
│              Power: 400W                                     │
├─────────────────────────────────────────────────────────────┤
│ U28-25 (4U): Proxmox Server #4 (16 devices: 49-64)          │
│              Same config, VMs: 4 Host VMs                    │
│              Power: 400W                                     │
├─────────────────────────────────────────────────────────────┤
│ U24-21 (4U): Proxmox Server #5 (16 devices: 65-80)          │
│              Same config, VMs: 4 Host VMs                    │
│              Power: 400W                                     │
├─────────────────────────────────────────────────────────────┤
│ U20-19 (2U): PDU #1 (32A, 24 outlets, metered)              │
│              - Server power distribution                     │
│              - Real-time power monitoring                    │
├─────────────────────────────────────────────────────────────┤
│ U18-17 (2U): Powered USB Hub Array                          │
│              - 10× Anker 10-port hubs (60W each)            │
│              - 100 USB ports total (80 used for mobiles)     │
│              - Power: 600W                                   │
├─────────────────────────────────────────────────────────────┤
│ U16-15 (2U): IR Blaster Controller Array                    │
│              - 5× Global Caché iTach (16 ports each)         │
│              - 80 IR outputs total                           │
│              - Network controlled                            │
├─────────────────────────────────────────────────────────────┤
│ U14-11 (4U): Cable Breakout Panels                          │
│              - 80× HDMI female → to Device Rack              │
│              - 80× USB pass-through → to Device Rack         │
│              - 80× IR pass-through → to Device Rack          │
│              - Labeled: DEV-001 to DEV-080                   │
├─────────────────────────────────────────────────────────────┤
│ U10-03 (8U): Cable Management                               │
│              - Vertical cable managers                       │
│              - Cable routing channels                        │
│              - Proper airflow maintained                     │
├─────────────────────────────────────────────────────────────┤
│ U02-01 (2U): Rack Ventilation                               │
│              - 4× 200 CFM exhaust fans                       │
│              - Temperature sensors (4 zones)                 │
│              - Automatic speed control                       │
└─────────────────────────────────────────────────────────────┘

Total: 42U (100% utilized)
Power: 2,650W (servers + hubs + IR + network + fans)
```

### Rack B: Device Shelves (42U - Full Utilization)

```
┌─────────────────────────────────────────────────────────────┐
│ RACK B - DEVICES ONLY (No Servers or Compute)               │
├─────────────────────────────────────────────────────────────┤
│ U42 (1U): PDU #2 (32A, 24 outlets)                          │
│           - Device power only                                │
│           - STB power supplies + mobile charging             │
├─────────────────────────────────────────────────────────────┤
│ U41-40 (2U): Cable Entry Point                              │
│              - 80× HDMI cables from Rack A (5m)             │
│              - 80× USB cables from Rack A (5m, for mobiles) │
│              - 80× IR cables from Rack A (5m, for STBs)     │
│              - Bundled in groups of 16                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ ═══════════════ FLEXIBLE CONFIGURATION ═════════════════    │
│                                                              │
│ Configuration Example: 60 STBs + 20 Mobiles = 80 devices    │
│                                                              │
│ U39-38 (2U): Mobile Shelf #1 (6 mobiles: 1-6)               │
│              - USB power from Rack A hubs                    │
│              - HDMI to Rack A capture cards                  │
│              - Adjustable mounts, labeled MOB-001 to 006     │
├─────────────────────────────────────────────────────────────┤
│ U37-36 (2U): Mobile Shelf #2 (6 mobiles: 7-12)              │
├─────────────────────────────────────────────────────────────┤
│ U35-34 (2U): Mobile Shelf #3 (6 mobiles: 13-18)             │
├─────────────────────────────────────────────────────────────┤
│ U33-32 (2U): Mobile Shelf #4 (2 mobiles: 19-20)             │
│              - Partial shelf, 4 slots empty                  │
├─────────────────────────────────────────────────────────────┤
│ U31-30 (2U): STB Shelf #1 (4 STBs: 1-4)                     │
│              - Integrated STB power supplies                 │
│              - HDMI output to Rack A                         │
│              - IR receiver facing IR blaster output          │
│              - Labeled: STB-001 to STB-004                   │
├─────────────────────────────────────────────────────────────┤
│ U29-28 (2U): STB Shelf #2 (4 STBs: 5-8)                     │
├─────────────────────────────────────────────────────────────┤
│ U27-26 (2U): STB Shelf #3 (4 STBs: 9-12)                    │
├─────────────────────────────────────────────────────────────┤
│ ... (continue pattern for remaining STB shelves)             │
├─────────────────────────────────────────────────────────────┤
│ U07-06 (2U): STB Shelf #13 (4 STBs: 53-56)                  │
├─────────────────────────────────────────────────────────────┤
│ U05-04 (2U): STB Shelf #14 (4 STBs: 57-60)                  │
├─────────────────────────────────────────────────────────────┤
│ U03-02 (2U): Environmental Monitoring                       │
│              - Temperature/humidity sensors                  │
│              - Smoke detector                                │
│              - Network-connected alerts                      │
├─────────────────────────────────────────────────────────────┤
│ U01 (1U): Cable Management Tray                             │
└─────────────────────────────────────────────────────────────┘

Total: 42U (100% utilized for 80 devices)
Power: 1,800W (60 STBs × 30W + 20 mobiles × 10W)
Weight: ~400kg (lighter than Rack A, no servers)

Device Rack is Reconfigurable:
- All STBs: 80 STBs (20 shelves × 4)
- All Mobiles: 80 mobiles (14 shelves × 6)
- Mix: Any combination totaling 80 devices
- Rearrange without touching Rack A!
```

### Frontend VM Specifications

```yaml
VM ID: 101
Name: virtualpytest-frontend
Purpose: Presentation layer, monitoring dashboard, reverse proxy

Components:
  - frontend (React UI - optional)
  - grafana (monitoring dashboard)
  - nginx (reverse proxy to Host VMs)
  - NO backend_server (fully decentralized)

Resources:
  RAM: 2GB (2048 MB)
  CPU: 2 cores
  Disk: 20GB SSD
  Network: 1 NIC (vmbr0)
  Devices: None (no USB/HDMI)

RAM Breakdown:
  - OS (Ubuntu minimal): ~200 MB
  - Docker daemon: ~150 MB
  - Frontend (nginx + static): ~100 MB
  - Grafana: ~200 MB
  - Nginx proxy: ~50 MB
  - Buffer: ~1300 MB

Performance:
  - Serves UI to users
  - Aggregates metrics from all Host VMs
  - Routes requests to backend_servers on Host VMs
```

### Host VM Specifications (Per Group) - Self-Contained

```yaml
VM ID: 102, 103, 104... (one per 4 hosts)
Name: virtualpytest-host-N
Purpose: Complete testing unit - backend_server + 4 backend_host containers

Components:
  - backend_server (FastAPI - orchestrates THIS VM's 4 hosts only)
  - backend_host_1 to backend_host_4 (Docker containers with devices)
  - X11 display server
  - VNC server
  - Chrome/Browser automation

Resources:
  RAM: 6GB (6144 MB) ⚠️ UPDATED from 4GB
  CPU: 2 cores
  Disk: 40GB SSD
  Network: 1 NIC (vmbr0)
  
Devices:
  - 4 × USB ports (for ADB/device control)
  - 1 × PCIe HDMI Capture Card (4 inputs)

RAM Breakdown:
  - OS (Ubuntu minimal): ~200 MB
  - Docker daemon: ~150 MB
  - backend_server: ~300 MB ⚠️ NEW (orchestration)
  - backend_host × 4: ~2800 MB (350 MB each)
  - X11 + VNC × 4: ~400 MB
  - Video tmpfs × 4: ~800 MB (200 MB each)
  - Buffer: ~1550 MB

Disk Breakdown:
  - OS: ~2 GB
  - Docker images: ~4 GB (includes backend_server)
  - Logs: ~2 GB
  - Screenshots: ~5 GB
  - Free: ~27 GB

Autonomy:
  - Fully independent (no reliance on other VMs)
  - Own database (SQLite or PostgreSQL in container)
  - Registers hosts 1-4 OR 5-8 OR 9-12 etc.
  - Reports metrics to VM 101 Grafana
```

### Scaling Table

| Hosts | Frontend VM | Host VMs | Total VMs | Total RAM | Total Cores | Total Disk |
|-------|-------------|----------|-----------|-----------|-------------|------------|
| 4     | 1 (2GB)     | 1 (6GB)  | 2         | 8 GB      | 4           | 60 GB      |
| 8     | 1 (2GB)     | 2 (6GB)  | 3         | 14 GB     | 6           | 100 GB     |
| 16    | 1 (2GB)     | 4 (6GB)  | 5         | 26 GB     | 10          | 180 GB     |
| 32    | 1 (2GB)     | 8 (6GB)  | 9         | 50 GB     | 18          | 340 GB     |
| 64    | 1 (2GB)     | 16 (6GB) | 17        | 98 GB     | 34          | 660 GB     |

**Each Host VM includes backend_server + 4 hosts (self-contained)**

**Proxmox Host Requirements (for 32 hosts):**
- **RAM**: 96GB (50GB for VMs + 30GB for Proxmox + 16GB buffer)
- **CPU**: 24+ cores (18 for VMs + 6 for Proxmox)
- **Storage**: 500GB+ (340GB VMs + Proxmox + snapshots)
- **PCIe Slots**: 8 slots (for HDMI capture cards)
- **USB Ports**: 32+ (built-in + PCIe USB controllers)

---

## Physical Device Integration

### Datacenter Hardware Topology

```
Server Rack (1U-4U)
┌─────────────────────────────────────────────────┐
│ 1U: Network Switch (1Gbps+)                     │
├─────────────────────────────────────────────────┤
│ 2U: Proxmox Server (Hosts 1-16)                 │
│   ├── Motherboard: X11 or EPYC (PCIe slots)    │
│   ├── RAM: 64GB DDR4                            │
│   ├── Storage: 1TB NVMe SSD                     │
│   │                                              │
│   ├── PCIe Slot 1: USB 3.0 Card (8 ports)      │
│   │   └── USB Ports 1-8 → Devices 1-8          │
│   │                                              │
│   ├── PCIe Slot 2: USB 3.0 Card (8 ports)      │
│   │   └── USB Ports 9-16 → Devices 9-16        │
│   │                                              │
│   ├── PCIe Slot 3: HDMI Capture Card 1          │
│   │   ├── Input 1 → STB 1 HDMI                 │
│   │   ├── Input 2 → STB 2 HDMI                 │
│   │   ├── Input 3 → STB 3 HDMI                 │
│   │   └── Input 4 → STB 4 HDMI                 │
│   │                                              │
│   ├── PCIe Slot 4: HDMI Capture Card 2          │
│   │   └── Inputs 1-4 → STBs 5-8 HDMI           │
│   │                                              │
│   ├── PCIe Slot 5: HDMI Capture Card 3          │
│   │   └── Inputs 1-4 → STBs 9-12 HDMI          │
│   │                                              │
│   └── PCIe Slot 6: HDMI Capture Card 4          │
│       └── Inputs 1-4 → STBs 13-16 HDMI          │
├─────────────────────────────────────────────────┤
│ 3U: Device Shelf (STBs/Phones mounted)          │
│   ├── [STB-1]  USB→Port1  HDMI→Card1-In1       │
│   ├── [STB-2]  USB→Port2  HDMI→Card1-In2       │
│   ├── [STB-3]  USB→Port3  HDMI→Card1-In3       │
│   ├── [STB-4]  USB→Port4  HDMI→Card1-In4       │
│   ├── [STB-5]  USB→Port5  HDMI→Card2-In1       │
│   └── ... (up to 16 devices)                    │
└─────────────────────────────────────────────────┘
```

### Hardware Recommendations

**USB Controllers:**
- StarTech PEXUSB3S44V (4-port PCIe card) × 4 = 16 USB ports
- Or: Built-in USB 3.0 + PCIe expansion
- **Important**: USB 3.0+ for Android ADB (USB 2.0 causes timeouts)

**HDMI Capture Cards:**
- **Recommended**: Magewell Pro Capture Quad HDMI (4 inputs per card)
  - Price: ~$1,300 per card
  - PCIe 3.0 x4
  - 4K @ 30fps per input
  - Low latency (~60ms)
  - Linux V4L2 support (shows as /dev/video0-3)
  
- **Budget**: AVerMedia Live Gamer 4K (1 input per card)
  - Price: ~$200 per card
  - Need 4 cards for 4 hosts
  - 4K @ 60fps
  
- **Alternative**: Elgato 4K60 Pro (1 input, ~$250)

**Proxmox Server:**
- **Entry**: Supermicro X11 (16 hosts)
  - CPU: Intel Xeon E-2288G (8 cores)
  - RAM: 64GB DDR4 ECC
  - PCIe: 6 slots
  - Cost: ~$2,000

- **Scale**: AMD EPYC Server (64 hosts)
  - CPU: AMD EPYC 7402P (24 cores)
  - RAM: 256GB DDR4 ECC
  - PCIe: 12+ slots
  - Cost: ~$5,000

### Device Passthrough Methods

#### Method 1: USB Port Passthrough (Recommended)

Pass entire USB port to VM (stable, survives device replug):

```bash
# On Proxmox host

# 1. Find USB port topology
lsusb -t

# Output example:
# /:  Bus 01.Port 1: Dev 1, Class=root_hub
#     |__ Port 2: Dev 5, If 0, Class=Vendor Specific
#     |__ Port 3: Dev 6, If 0, Class=Mass Storage

# 2. Pass USB ports to VM 102 (hosts 1-4)
qm set 102 \
  --usb0 host=1-2 \      # STB 1 (Port 2)
  --usb1 host=1-3 \      # STB 2 (Port 3)
  --usb2 host=1-4 \      # STB 3 (Port 4)
  --usb3 host=1-5        # STB 4 (Port 5)

# 3. Pass USB ports to VM 103 (hosts 5-8)
qm set 103 \
  --usb0 host=1-6 \
  --usb1 host=1-7 \
  --usb2 host=1-8 \
  --usb3 host=1-9

# Restart VMs
qm reboot 102
qm reboot 103
```

**Pros:**
- ✅ Device can be unplugged/replugged
- ✅ Port physically labeled = easy management
- ✅ Most stable for production

**Cons:**
- ❌ Port locked to specific VM

#### Method 2: USB Device by ID

Pass specific USB device by vendor:product ID:

```bash
# Find device IDs
lsusb

# Output:
# Bus 001 Device 005: ID 18d1:4ee2 Google Inc. Nexus 4
# Bus 001 Device 006: ID 04e8:6860 Samsung Electronics

# Pass to VM
qm set 102 \
  --usb0 host=18d1:4ee2 \   # Google device
  --usb1 host=04e8:6860     # Samsung device
```

**Pros:**
- ✅ Device follows VM (even if USB port changes)

**Cons:**
- ❌ Requires replug detection if device reboots
- ❌ Less stable for Android devices

#### Method 3: PCIe HDMI Capture Card Passthrough

Pass entire capture card (4 HDMI inputs) to one VM:

```bash
# On Proxmox host

# 1. Enable IOMMU in BIOS (required!)
# Intel: Enable VT-d
# AMD: Enable IOMMU

# 2. Configure GRUB
nano /etc/default/grub

# Add to GRUB_CMDLINE_LINUX_DEFAULT:
# Intel:
intel_iommu=on iommu=pt

# AMD:
amd_iommu=on iommu=pt

# Update and reboot
update-grub
reboot

# 3. Find PCIe devices
lspci -nn | grep -i capture

# Output:
# 01:00.0 Multimedia controller [0480]: ... Magewell [1234:5678]
# 02:00.0 Multimedia controller [0480]: ... Magewell [1234:5678]

# 4. Check IOMMU group (must be isolated)
find /sys/kernel/iommu_groups/ -type l | grep 01:00.0

# 5. Pass capture card to VM 102 (hosts 1-4)
qm set 102 --hostpci0 01:00.0,pcie=1

# 6. Pass capture card to VM 103 (hosts 5-8)
qm set 103 --hostpci0 02:00.0,pcie=1

# 7. Restart VMs
qm reboot 102
qm reboot 103
```

**Inside VM, verify:**
```bash
ssh ubuntu@192.168.1.102

# Check capture card
lspci | grep -i capture
# Should show: Multimedia controller: Magewell...

# Check video devices (4 HDMI inputs = 4 devices)
ls -l /dev/video*
# Output:
# /dev/video0  → HDMI Input 1 (STB 1)
# /dev/video1  → HDMI Input 2 (STB 2)
# /dev/video2  → HDMI Input 3 (STB 3)
# /dev/video3  → HDMI Input 4 (STB 4)
```

**Pros:**
- ✅ Full native performance (no overhead)
- ✅ Low latency (~60ms)
- ✅ All 4 HDMI inputs available to VM

**Cons:**
- ❌ Entire card locked to one VM
- ❌ Can't share between VMs
- ❌ Requires IOMMU support + isolated IOMMU group

### Device Assignment Table

| VM | Role | Components | USB Ports | HDMI Capture | Devices | RAM | IP |
|----|------|------------|-----------|--------------|---------|-----|----|
| VM 101 | Frontend | frontend + grafana + nginx | None | None | None | 2GB | 192.168.1.101 |
| VM 102 | Hosts 1-4 | backend_server + host_1-4 | Ports 1-4 | Card 1 (/dev/video0-3) | STBs 1-4 | 6GB | 192.168.1.102 |
| VM 103 | Hosts 5-8 | backend_server + host_5-8 | Ports 5-8 | Card 2 (/dev/video0-3) | STBs 5-8 | 6GB | 192.168.1.103 |
| VM 104 | Hosts 9-12 | backend_server + host_9-12 | Ports 9-12 | Card 3 (/dev/video0-3) | STBs 9-12 | 6GB | 192.168.1.104 |
| VM 105 | Hosts 13-16 | backend_server + host_13-16 | Ports 13-16 | Card 4 (/dev/video0-3) | STBs 13-16 | 6GB | 192.168.1.105 |

**Each Host VM is fully autonomous with its own backend_server**

---

## Network Architecture

### Internal Network (VM to VM)

```
Proxmox Bridge (vmbr0) - 192.168.1.0/24
├── 192.168.1.1         - Proxmox host (gateway)
├── 192.168.1.101       - Frontend VM (UI, Grafana, Nginx)
├── 192.168.1.102       - Host VM 1 (backend_server + hosts 1-4)
├── 192.168.1.103       - Host VM 2 (backend_server + hosts 5-8)
├── 192.168.1.104       - Host VM 3 (backend_server + hosts 9-12)
└── 192.168.1.105       - Host VM 4 (backend_server + hosts 13-16)
```

**Decentralized Communication:**
- Each Host VM is autonomous (no cross-VM dependencies)
- Frontend VM → Host VMs: API calls for test execution
- Host VMs → Frontend VM: Metrics push to Grafana
- Host VMs → Supabase: Direct database writes (no central server)
- NO single point of failure

### External Access (Nginx Reverse Proxy on VM 101)

```
Internet → HTTPS (443) → Proxmox Host Nginx
  ↓
  ├── /grafana/    → 192.168.1.101:3000 (Frontend VM - Grafana)
  ├── /            → 192.168.1.101:80   (Frontend VM - React UI)
  │
  ├── /server1/    → 192.168.1.102:8001 (Host VM 1 - backend_server)
  ├── /host1/      → 192.168.1.102:5001 (Host VM 1 - backend_host_1)
  ├── /host2/      → 192.168.1.102:5002 (Host VM 1 - backend_host_2)
  ├── /host3/      → 192.168.1.102:5003 (Host VM 1 - backend_host_3)
  ├── /host4/      → 192.168.1.102:5004 (Host VM 1 - backend_host_4)
  │
  ├── /server2/    → 192.168.1.103:8001 (Host VM 2 - backend_server)
  ├── /host5/      → 192.168.1.103:5001 (Host VM 2 - backend_host_5)
  ├── /host6/      → 192.168.1.103:5002 (Host VM 2 - backend_host_6)
  ├── /host7/      → 192.168.1.103:5003 (Host VM 2 - backend_host_7)
  ├── /host8/      → 192.168.1.103:5004 (Host VM 2 - backend_host_8)
  └── ...
```

**Decentralized Access:**
- Each Host VM exposes its own backend_server (port 8001)
- Frontend aggregates data from multiple backend_servers
- Direct access to any host via `/hostN/vnc/vnc_lite.html`
- Can access individual backend_server APIs for debugging

**URL Examples:**
- `https://virtualpytest.example.com/host1/vnc/vnc_lite.html` → STB 1 VNC
- `https://virtualpytest.example.com/host5/stream/capture5/segments/` → STB 5 video stream
- `https://virtualpytest.example.com/grafana` → Monitoring dashboard

---

## Initial Setup

### Step 1: Prepare Proxmox Host

```bash
# SSH into Proxmox host
ssh root@proxmox-host

# Update system
apt update && apt upgrade -y

# Enable IOMMU for PCIe passthrough
nano /etc/default/grub

# Add to GRUB_CMDLINE_LINUX_DEFAULT (Intel):
intel_iommu=on iommu=pt pcie_acs_override=downstream,multifunction

# Or for AMD:
amd_iommu=on iommu=pt pcie_acs_override=downstream,multifunction

# Update GRUB
update-grub

# Load VFIO modules
echo "vfio" >> /etc/modules
echo "vfio_iommu_type1" >> /etc/modules
echo "vfio_pci" >> /etc/modules
echo "vfio_virqfd" >> /etc/modules

# Reboot
reboot

# After reboot, verify IOMMU
dmesg | grep -e DMAR -e IOMMU

# Should show: DMAR: IOMMU enabled
```

### Step 2: Clone Repository

```bash
# On Proxmox host
cd /root
git clone https://github.com/youruser/virtualpytest.git
cd virtualpytest/setup/docker/proxmox
```

### Step 3: Create Frontend VM (VM 101)

```bash
# Download Ubuntu Cloud Image (one time)
wget https://cloud-images.ubuntu.com/jammy/current/jammy-server-cloudimg-amd64.img -O /tmp/ubuntu-cloud.img

# Create Frontend VM
qm create 101 \
  --name virtualpytest-frontend \
  --memory 2048 \
  --cores 2 \
  --net0 virtio,bridge=vmbr0 \
  --agent enabled=1 \
  --ostype l26

# Import disk
qm importdisk 101 /tmp/ubuntu-cloud.img local-lvm --format qcow2

# Configure VM
qm set 101 --scsihw virtio-scsi-pci
qm set 101 --scsi0 local-lvm:vm-101-disk-0
qm set 101 --ide2 local-lvm:cloudinit
qm set 101 --boot order=scsi0
qm set 101 --serial0 socket --vga serial0

# Resize disk to 20GB
qm resize 101 scsi0 20G

# Configure cloud-init (static IP)
qm set 101 --ciuser ubuntu
qm set 101 --cipassword "YourPassword123"  # Or use SSH key
qm set 101 --ipconfig0 ip=192.168.1.101/24,gw=192.168.1.1
qm set 101 --nameserver 8.8.8.8

# Start VM
qm start 101

# Wait 30 seconds, then SSH
sleep 30
ssh ubuntu@192.168.1.101
```

### Step 4: Setup Frontend VM

```bash
# Inside Frontend VM (192.168.1.101)

# Install Docker
sudo apt update
sudo apt install -y docker.io docker-compose git curl nginx
sudo usermod -aG docker ubuntu
exit && ssh ubuntu@192.168.1.101

# Clone repository
git clone https://github.com/youruser/virtualpytest.git
cd virtualpytest

# Create .env (minimal - no Supabase needed here)
cat > .env <<EOF
# Frontend VM - Presentation Layer Only
# Supabase credentials NOT needed here (Host VMs connect directly)
EOF
```

**Create docker-compose.frontend.yml:**
```bash
cd ~/virtualpytest
nano docker-compose.frontend.yml
```

```yaml
# Frontend VM - Presentation Layer Only (NO backend_server)
services:
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: virtualpytest-frontend
    ports:
      - "80:80"
    environment:
      # Frontend talks to multiple backend_servers (one per Host VM)
      - VITE_API_URL_1=http://192.168.1.102:8001
      - VITE_API_URL_2=http://192.168.1.103:8001
      - VITE_API_URL_3=http://192.168.1.104:8001
    restart: unless-stopped
    networks:
      - virtualpytest

  grafana:
    image: grafana/grafana:latest
    container_name: virtualpytest-grafana
    ports:
      - "3000:3000"
    volumes:
      - grafana-data:/var/lib/grafana
      - ./grafana/config/grafana.ini:/etc/grafana/grafana.ini:ro
      - ./grafana/dashboards:/var/lib/grafana/dashboards:ro
    environment:
      - GF_SERVER_ROOT_URL=https://virtualpytest.example.com/grafana
      - GF_SERVER_SERVE_FROM_SUB_PATH=true
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD:-admin123}
      # Grafana scrapes metrics from all Host VMs
      - GF_DATASOURCE_URL_1=http://192.168.1.102:8001/metrics
      - GF_DATASOURCE_URL_2=http://192.168.1.103:8001/metrics
      - GF_DATASOURCE_URL_3=http://192.168.1.104:8001/metrics
    restart: unless-stopped
    networks:
      - virtualpytest

volumes:
  grafana-data:

networks:
  virtualpytest:
    driver: bridge
```

**Start frontend containers:**
```bash
docker-compose -f docker-compose.frontend.yml up -d

# Verify
docker ps
# Should show: frontend, grafana (NO backend_server)

# Test frontend
curl http://192.168.1.101/
# Should return HTML
```

### Step 5: Create Host VM Template (VM 102)

```bash
# On Proxmox host (back from Server VM)
exit

# Create Host VM 102
qm create 102 \
  --name virtualpytest-host-1 \
  --memory 4096 \
  --cores 2 \
  --net0 virtio,bridge=vmbr0 \
  --agent enabled=1 \
  --ostype l26

# Import disk (reuse same image)
qm importdisk 102 /tmp/ubuntu-cloud.img local-lvm --format qcow2

# Configure VM
qm set 102 --scsihw virtio-scsi-pci
qm set 102 --scsi0 local-lvm:vm-102-disk-0
qm set 102 --ide2 local-lvm:cloudinit
qm set 102 --boot order=scsi0
qm set 102 --serial0 socket --vga serial0

# Resize disk to 40GB
qm resize 102 scsi0 40G

# Configure cloud-init
qm set 102 --ciuser ubuntu
qm set 102 --cipassword "YourPassword123"
qm set 102 --ipconfig0 ip=192.168.1.102/24,gw=192.168.1.1
qm set 102 --nameserver 8.8.8.8

# DON'T START YET - First configure device passthrough
```

---

## Device Passthrough Configuration

### Configure USB and PCIe Passthrough for VM 102

```bash
# On Proxmox host

# 1. Find USB ports
lsusb -t
# Note: Bus 01, Ports 2-5 for STBs 1-4

# 2. Find HDMI capture cards
lspci -nn | grep -i capture
# Note: 01:00.0 for first card

# 3. Pass USB ports to VM 102
qm set 102 \
  --usb0 host=1-2 \      # STB 1
  --usb1 host=1-3 \      # STB 2
  --usb2 host=1-4 \      # STB 3
  --usb3 host=1-5        # STB 4

# 4. Pass HDMI capture card to VM 102
qm set 102 --hostpci0 01:00.0,pcie=1

# 5. Start VM
qm start 102

# Wait and SSH
sleep 30
ssh ubuntu@192.168.1.102
```

### Setup Host VM

```bash
# Inside Host VM (192.168.1.102)

# Install Docker
sudo apt update
sudo apt install -y docker.io docker-compose git curl adb
sudo usermod -aG docker ubuntu
exit && ssh ubuntu@192.168.1.102

# Verify USB devices
lsusb
# Should show 4 devices (STBs 1-4)

adb devices
# May show devices if STBs have ADB enabled

# Verify HDMI capture card
lspci | grep -i capture
# Should show capture card

ls -l /dev/video*
# Should show:
# /dev/video0  (HDMI input 1 → STB 1)
# /dev/video1  (HDMI input 2 → STB 2)
# /dev/video2  (HDMI input 3 → STB 3)
# /dev/video3  (HDMI input 4 → STB 4)

# Clone repository
git clone https://github.com/youruser/virtualpytest.git
cd virtualpytest

# Copy .env from server
scp ubuntu@192.168.1.101:~/virtualpytest/.env .
```

### Create Host Configuration Files

```bash
# Inside Host VM 102

cd ~/virtualpytest

# Create .env files for each backend_host
for i in 1 2 3 4; do
  mkdir -p backend_host_$i
  VIDEO_DEV=$((i - 1))  # video0, video1, video2, video3
  PORT=$((5000 + i))
  
  cat > backend_host_$i/.env <<EOF
# Backend Host $i Configuration
SERVER_URL=http://192.168.1.101:8001
HOST_NAME=proxmox-host$i
HOST_PORT=$PORT
HOST_URL=https://virtualpytest.example.com/host$i
HOST_API_URL=http://backend_host_$i:80
HOST_VIDEO_CAPTURE_PATH=/var/www/html/stream/capture$i
HOST_VIDEO_STREAM_PATH=/host/stream/capture$i
HOST_VNC_STREAM_PATH=https://virtualpytest.example.com/host$i/vnc/vnc_lite.html
HOST_VIDEO_SOURCE=/dev/video$VIDEO_DEV
HOST_VIDEO_AUDIO=null
HOST_VIDEO_FPS=2
DEBUG=0
PYTHONUNBUFFERED=1
API_KEY=${API_KEY}
EOF
  
  echo "✅ Created backend_host_$i/.env"
done
```

**Create docker-compose.host.yml:**
```bash
nano ~/virtualpytest/docker-compose.host.yml
```

```yaml
services:
  # Build base image once
  backend_host_base:
    build:
      context: .
      dockerfile: backend_host/Dockerfile
    image: virtualpytest-backend-host:latest
    profiles:
      - build-only

  # Host 1 (uses /dev/video0, USB device 1)
  backend_host_1:
    image: virtualpytest-backend-host:latest
    container_name: virtualpytest-backend-host-1
    ports:
      - "5001:80"
    volumes:
      - /dev:/dev
      - ./.env:/app/.env:ro
      - ./backend_host_1/.env:/app/backend_host/src/.env:ro
      - ./test_scripts:/app/test_scripts:ro
    devices:
      - /dev/video0:/dev/video0  # HDMI input 1
    tmpfs:
      - /var/www/html/stream/capture1/hot:size=200M,mode=777
    privileged: true
    restart: unless-stopped
    networks:
      - virtualpytest

  # Host 2 (uses /dev/video1, USB device 2)
  backend_host_2:
    image: virtualpytest-backend-host:latest
    container_name: virtualpytest-backend-host-2
    ports:
      - "5002:80"
    volumes:
      - /dev:/dev
      - ./.env:/app/.env:ro
      - ./backend_host_2/.env:/app/backend_host/src/.env:ro
      - ./test_scripts:/app/test_scripts:ro
    devices:
      - /dev/video1:/dev/video1  # HDMI input 2
    tmpfs:
      - /var/www/html/stream/capture2/hot:size=200M,mode=777
    privileged: true
    restart: unless-stopped
    networks:
      - virtualpytest

  # Host 3 (uses /dev/video2, USB device 3)
  backend_host_3:
    image: virtualpytest-backend-host:latest
    container_name: virtualpytest-backend-host-3
    ports:
      - "5003:80"
    volumes:
      - /dev:/dev
      - ./.env:/app/.env:ro
      - ./backend_host_3/.env:/app/backend_host/src/.env:ro
      - ./test_scripts:/app/test_scripts:ro
    devices:
      - /dev/video2:/dev/video2  # HDMI input 3
    tmpfs:
      - /var/www/html/stream/capture3/hot:size=200M,mode=777
    privileged: true
    restart: unless-stopped
    networks:
      - virtualpytest

  # Host 4 (uses /dev/video3, USB device 4)
  backend_host_4:
    image: virtualpytest-backend-host:latest
    container_name: virtualpytest-backend-host-4
    ports:
      - "5004:80"
    volumes:
      - /dev:/dev
      - ./.env:/app/.env:ro
      - ./backend_host_4/.env:/app/backend_host/src/.env:ro
      - ./test_scripts:/app/test_scripts:ro
    devices:
      - /dev/video3:/dev/video3  # HDMI input 4
    tmpfs:
      - /var/www/html/stream/capture4/hot:size=200M,mode=777
    privileged: true
    restart: unless-stopped
    networks:
      - virtualpytest

networks:
  virtualpytest:
    driver: bridge
```

**Start containers:**
```bash
# Build image first
docker-compose -f docker-compose.host.yml build backend_host_base

# Start all hosts
docker-compose -f docker-compose.host.yml up -d

# Verify
docker ps
# Should show: backend_host_1, backend_host_2, backend_host_3, backend_host_4

# Test host 1
curl http://localhost:5001/host/health
# Should return: {"status":"ok"}
```

---

## Deployment

### Complete Deployment Script (Automated)

Create this script on Proxmox host:

```bash
# On Proxmox host
cd /root/virtualpytest/setup/docker/proxmox
nano deploy_scalable.sh
```

```bash
#!/bin/bash
# deploy_scalable.sh - Automated deployment of scalable VirtualPyTest

set -e

echo "🚀 VirtualPyTest Scalable Deployment"
echo "====================================="
echo ""

# Configuration
NUM_HOST_VMS=4        # Number of host VMs (4 hosts each)
SERVER_VM_ID=101
HOST_VM_START=102
DOMAIN="virtualpytest.example.com"

# Verify IOMMU
if ! dmesg | grep -q "IOMMU enabled"; then
    echo "❌ IOMMU not enabled! Enable in BIOS and GRUB."
    exit 1
fi

echo "✅ IOMMU enabled"
echo ""

# Download cloud image if not exists
if [ ! -f /tmp/ubuntu-cloud.img ]; then
    echo "📦 Downloading Ubuntu cloud image..."
    wget https://cloud-images.ubuntu.com/jammy/current/jammy-server-cloudimg-amd64.img \
      -O /tmp/ubuntu-cloud.img
fi

# Create Server VM
echo "🔧 Creating Server VM (101)..."
if ! qm status $SERVER_VM_ID &>/dev/null; then
    qm create $SERVER_VM_ID \
      --name virtualpytest-server \
      --memory 2048 --cores 2 \
      --net0 virtio,bridge=vmbr0 \
      --agent enabled=1 --ostype l26
    
    qm importdisk $SERVER_VM_ID /tmp/ubuntu-cloud.img local-lvm --format qcow2
    qm set $SERVER_VM_ID --scsihw virtio-scsi-pci
    qm set $SERVER_VM_ID --scsi0 local-lvm:vm-$SERVER_VM_ID-disk-0
    qm set $SERVER_VM_ID --ide2 local-lvm:cloudinit
    qm set $SERVER_VM_ID --boot order=scsi0
    qm set $SERVER_VM_ID --serial0 socket --vga serial0
    qm resize $SERVER_VM_ID scsi0 20G
    qm set $SERVER_VM_ID --ciuser ubuntu --cipassword "Change123"
    qm set $SERVER_VM_ID --ipconfig0 ip=192.168.1.101/24,gw=192.168.1.1
    qm start $SERVER_VM_ID
    echo "✅ Server VM created"
else
    echo "✅ Server VM already exists"
fi

# Create Host VMs
for i in $(seq 1 $NUM_HOST_VMS); do
    VM_ID=$((HOST_VM_START + i - 1))
    VM_IP=$((101 + i))
    PCIE_SLOT=$((i))  # Assumes cards are 01:00.0, 02:00.0, etc.
    USB_START=$((1 + (i - 1) * 4 + 2))  # Ports 2-5, 6-9, 10-13, 14-17
    
    echo ""
    echo "🔧 Creating Host VM $i (VM $VM_ID)..."
    
    if ! qm status $VM_ID &>/dev/null; then
        qm create $VM_ID \
          --name virtualpytest-host-$i \
          --memory 4096 --cores 2 \
          --net0 virtio,bridge=vmbr0 \
          --agent enabled=1 --ostype l26
        
        qm importdisk $VM_ID /tmp/ubuntu-cloud.img local-lvm --format qcow2
        qm set $VM_ID --scsihw virtio-scsi-pci
        qm set $VM_ID --scsi0 local-lvm:vm-$VM_ID-disk-0
        qm set $VM_ID --ide2 local-lvm:cloudinit
        qm set $VM_ID --boot order=scsi0
        qm set $VM_ID --serial0 socket --vga serial0
        qm resize $VM_ID scsi0 40G
        qm set $VM_ID --ciuser ubuntu --cipassword "Change123"
        qm set $VM_ID --ipconfig0 ip=192.168.1.$VM_IP/24,gw=192.168.1.1
        
        # USB passthrough (4 ports per VM)
        qm set $VM_ID --usb0 host=1-$USB_START
        qm set $VM_ID --usb1 host=1-$((USB_START + 1))
        qm set $VM_ID --usb2 host=1-$((USB_START + 2))
        qm set $VM_ID --usb3 host=1-$((USB_START + 3))
        
        # PCIe capture card passthrough
        PCIE_ADDR=$(printf "%02d:00.0" $PCIE_SLOT)
        if lspci | grep -q "$PCIE_ADDR"; then
            qm set $VM_ID --hostpci0 $PCIE_ADDR,pcie=1
            echo "✅ PCIe card $PCIE_ADDR passed to VM $VM_ID"
        else
            echo "⚠️  PCIe card $PCIE_ADDR not found"
        fi
        
        qm start $VM_ID
        echo "✅ Host VM $i created"
    else
        echo "✅ Host VM $i already exists"
    fi
done

echo ""
echo "===================================="
echo "✅ Infrastructure Deployed!"
echo "===================================="
echo ""
echo "📋 Created VMs:"
echo "   • VM 101: Server (192.168.1.101)"
for i in $(seq 1 $NUM_HOST_VMS); do
    VM_IP=$((101 + i))
    HOST_START=$((1 + (i - 1) * 4))
    HOST_END=$((HOST_START + 3))
    echo "   • VM $((HOST_VM_START + i - 1)): Hosts $HOST_START-$HOST_END (192.168.1.$VM_IP)"
done
echo ""
echo "📝 Next Steps:"
echo "1. Wait 60 seconds for VMs to boot"
echo "2. SSH into each VM and run setup (see documentation)"
echo "3. Configure Nginx on Proxmox host"
echo ""
```

Make executable and run:
```bash
chmod +x deploy_scalable.sh
./deploy_scalable.sh
```

---

## Scaling Operations

### Add New Host VM (Hosts 17-20)

```bash
# On Proxmox host

# Clone existing host VM
qm clone 102 106 --name virtualpytest-host-5 --full

# Configure IP
qm set 106 --ipconfig0 ip=192.168.1.106/24,gw=192.168.1.1

# Update USB passthrough (ports 18-21)
qm set 106 --usb0 host=1-18
qm set 106 --usb1 host=1-19
qm set 106 --usb2 host=1-20
qm set 106 --usb3 host=1-21

# Update PCIe passthrough (5th capture card)
qm set 106 --hostpci0 05:00.0,pcie=1

# Start VM
qm start 106

# SSH and configure
ssh ubuntu@192.168.1.106
cd virtualpytest

# Update backend_host_.env files for hosts 17-20
for i in 17 18 19 20; do
  CONTAINER_NUM=$((i % 4))
  if [ $CONTAINER_NUM -eq 0 ]; then CONTAINER_NUM=4; fi
  VIDEO_DEV=$((CONTAINER_NUM - 1))
  
  mkdir -p backend_host_$i
  cat > backend_host_$i/.env <<EOF
SERVER_URL=http://192.168.1.101:8001
HOST_NAME=proxmox-host$i
HOST_URL=https://virtualpytest.example.com/host$i
HOST_VIDEO_SOURCE=/dev/video$VIDEO_DEV
# ... rest of config
EOF
done

# Update docker-compose to use hosts 17-20
# Then start
docker-compose -f docker-compose.host.yml up -d
```

### Remove Host VM

```bash
# Stop containers inside VM
ssh ubuntu@192.168.1.106
docker-compose down

# On Proxmox host
qm stop 106
qm destroy 106
```

---

## Management

### Start/Stop All VMs

```bash
# On Proxmox host

# Start all
for vm_id in 101 102 103 104 105; do
  qm start $vm_id
done

# Stop all (graceful)
for vm_id in 101 102 103 104 105; do
  qm shutdown $vm_id
done
```

### Monitor Resources

```bash
# All VMs summary
pvesh get /nodes/$(hostname)/qemu --output-format=table

# Specific VM
qm status 102
qm monitor 102

# Inside VM
ssh ubuntu@192.168.1.102
htop
docker stats
```

### Snapshots

```bash
# Create snapshot for all VMs
for vm_id in 101 102 103 104; do
  qm snapshot $vm_id before-update --description "Before update $(date)"
done

# List snapshots
qm listsnapshot 102

# Rollback
qm rollback 102 before-update
```

### Backups

```bash
# Backup all VMs
vzdump 101 102 103 104 --mode snapshot --compress zstd --dumpdir /mnt/backup

# Restore
qmrestore /mnt/backup/vzdump-qemu-102-*.vma.zst 102
```

---

## High Availability

### Proxmox Cluster Setup (3+ Nodes)

```bash
# On first Proxmox node
pvecm create my-cluster

# On other nodes
pvecm add <first-node-ip>

# Verify
pvecm status
```

### Enable HA for VMs

```bash
# Server VM (high priority)
ha-manager add vm:101 --state started --max_restart 3 --group ha-group

# Host VMs (lower priority)
ha-manager add vm:102 --state started
ha-manager add vm:103 --state started
```

### Live Migration

```bash
# Move VM 102 from node1 to node2 (zero downtime!)
# Note: VMs with device passthrough cannot be live migrated
# Stop VM first, then migrate, then start on new node

qm migrate 102 node2 --online  # Won't work with USB/PCIe passthrough

# Alternative: Offline migration
qm stop 102
qm migrate 102 node2
# Reconfigure USB/PCIe passthrough on node2
qm start 102
```

---

## Troubleshooting

### USB Devices Not Visible in VM

```bash
# On Proxmox host
lsusb -t  # Verify devices connected

# Check VM config
qm config 102 | grep usb

# Verify passthrough
qm monitor 102
info usbhost

# Inside VM
lsusb  # Should show devices
```

### HDMI Capture Card Not Working

```bash
# On Proxmox host
lspci | grep -i capture  # Verify card detected

# Check IOMMU group
find /sys/kernel/iommu_groups/ -type l | grep 01:00.0

# Inside VM
lspci | grep -i capture  # Should show card
ls -l /dev/video*        # Should show video0-3

# Test capture
ffmpeg -f v4l2 -list_formats all -i /dev/video0
```

### VM Out of Memory

```bash
# Check usage
ssh ubuntu@192.168.1.102
free -h
docker stats

# Stop some containers
docker-compose stop backend_host_4

# Or increase RAM
qm set 102 --memory 6144
qm reboot 102
```

### Network Issues Between VMs

```bash
# Test connectivity
ssh ubuntu@192.168.1.102
ping 192.168.1.101  # Should work

# Check routes
ip route

# Test server API
curl http://192.168.1.101:8001/health
```

### Devices Not Recognized After VM Reboot

```bash
# USB devices may need replug
# Or use USB port passthrough (host=1-2) instead of device ID

# PCIe devices should persist
# If not, check IOMMU groups
find /sys/kernel/iommu_groups/ -type l
```

---

## Summary

**This scalable architecture enables:**
- ✅ Horizontal scaling (add VMs for more capacity)
- ✅ Physical device integration (USB + HDMI capture)
- ✅ Fault isolation (VM crashes don't affect others)
- ✅ Flexible resource allocation (per-VM scaling)
- ✅ High availability (with Proxmox cluster)

**Key Points:**
- 1 Server VM handles orchestration (2GB RAM)
- Each Host VM runs 4 containers with 4 devices (4GB RAM)
- USB passthrough by port for stability
- PCIe passthrough for HDMI capture (4 inputs per card)
- Scale by adding more Host VMs

**Total Capacity Examples:**
- 16 hosts = 1 server VM + 4 host VMs = 18GB RAM
- 32 hosts = 1 server VM + 8 host VMs = 34GB RAM
- 64 hosts = 1 server VM + 16 host VMs = 66GB RAM

Your Hetzner Docker setup works unchanged inside each VM! 🎉

