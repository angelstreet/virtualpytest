# VirtualPyTest - Production Setup (80 Devices)

Complete production deployment with **identical hardware** as demo, scaled to 5 Proxmox servers.

**Philosophy:** Demo is Server #1. Production adds 4 more identical servers. Linear scaling proven.

**Capacity:** 5 servers = 80 devices (60 STBs + 20 Mobiles or any mix)

---

## Architecture: 2-Rack Modular Design

### Separation of Concerns: Compute vs Devices

```
Datacenter Floor
┌──────────────────┐  ┌──────────────────┐
│   RACK A         │  │   RACK B         │
│   COMPUTE ONLY   │  │   DEVICES ONLY   │
│                  │  │                  │
│ • 5 Servers      │  │ • 0 Servers      │
│ • 20 Capture Cards│──┼──> • 60 STBs    │
│ • 5 USB Hubs     │──┼──> • 20 Mobiles  │
│ • 5 IR Controllers│──┼──> • Shelves    │
│ • Network        │  │                  │
│ • Cable Mgmt     │  │ • Power          │
│                  │  │                  │
│ 42U = 80 devices │  │ 42U = 80 devices │
└──────────────────┘  └──────────────────┘
        ↑                     ↑
        └───── 10GbE ─────────┘
           5m cables
```

**Why 2 Racks:**
- ✅ **Clean separation:** Expensive compute vs cheap device shelves
- ✅ **Scalable:** Add more rack pairs to scale (80→160→240→320+)
- ✅ **Flexible:** Change device mix without touching compute
- ✅ **Serviceable:** Access servers without disturbing devices

---

## Hardware Specifications (Production-Grade)

### Proxmox Servers (5× Identical - Same as Demo)

**Model:** Supermicro AS-1114S-WN10RT or equivalent 4U server

| Component | Specification | Purpose |
|-----------|---------------|---------|
| **CPU** | AMD EPYC 7313P | 16 cores, 32 threads @ 3.0-3.7GHz |
| **RAM** | 128GB DDR4-3200 ECC | 8× 16GB modules, expandable to 2TB |
| **Storage** | 2× 2TB NVMe SSD (RAID1) | Samsung PM9A3, PCIe 4.0 |
| **Motherboard** | Supermicro H12SSL-i | 8× PCIe slots, IPMI, dual 10GbE |
| **Form Factor** | 4U Rackmount | 482mm × 710mm × 177mm (W×D×H) |
| **Weight** | 28kg (empty) / 35kg (populated) |
| **Power Supply** | Dual 800W 80+ Platinum | Redundant, hot-swappable |
| **Network** | 2× 10GbE + 4× 1GbE | Intel X710 + Intel i350 |
| **IPMI** | AST2500 BMC | Remote management, KVM-over-IP |
| **Price** | $6,000 (new) / $3,500 (refurbished) |

**Total Servers:** 5× $6,000 = **$30,000**

**PCIe Slot Configuration (per server):**
- Slot 1-4: 4× Magewell Quad HDMI (16 inputs total)
- Slot 5: USB 3.0 Controller
- Slot 6: Reserved
- Slot 7-8: Expansion

---

### HDMI Capture Cards (20× Total)

**Model:** Magewell Pro Capture Quad HDMI (Model 11160)

| Specification | Value |
|---------------|-------|
| **Video Inputs** | 4× HDMI 2.0 (independent) |
| **Max Resolution** | 4K@60Hz per input (4:4:4) |
| **PCIe Interface** | PCIe 3.0 x4 (8GB/s bandwidth) |
| **Encoding** | Hardware H.264/H.265 on-board |
| **Latency** | 60-100ms (very low) |
| **Linux Support** | V4L2 native (/dev/video0-3 per card) |
| **Power Consumption** | 25W per card |
| **Price** | $1,295 per card |

**Production:**
- **Server 1:** 4 cards = 16 HDMI inputs = $5,180
- **Server 2:** 4 cards = 16 HDMI inputs = $5,180
- **Server 3:** 4 cards = 16 HDMI inputs = $5,180
- **Server 4:** 4 cards = 16 HDMI inputs = $5,180
- **Server 5:** 4 cards = 16 HDMI inputs = $5,180
- **Total:** 20 cards = 80 HDMI inputs = **$25,900**

---

### HDMI Splitters (80× Total - For Live Monitor View)

**Model:** OREI HD-102 (1-in-2-out HDMI Splitter)

| Specification | Value |
|---------------|-------|
| **Inputs** | 1× HDMI 2.0 |
| **Outputs** | 2× HDMI 2.0 (identical copies) |
| **Max Resolution** | 4K@60Hz |
| **Power** | Passive (no power needed) |
| **Latency** | 0ms (pure signal split) |
| **Dimensions** | 100mm × 60mm × 20mm |
| **Mounting** | In cable management trays |
| **Price** | $18 per splitter |

**Total:** 80× $18 = **$1,440**

**Signal Flow (per device):**
```
Device HDMI → Splitter → ┬→ Capture Card (recording)
                          └→ Matrix Switch (live monitor)
```

---

### HDMI Matrix Switches (5× - One Per Server Group)

**Model:** OREI HMA-161 (16×1 HDMI Matrix)

| Specification | Value |
|---------------|-------|
| **Inputs** | 16× HDMI (from splitters) |
| **Outputs** | 1× HDMI (to monitor) |
| **Max Resolution** | 4K@60Hz |
| **Control** | Front panel buttons + IR remote |
| **Switching Speed** | <1 second |
| **Mounting** | 1U rackmount |
| **Price** | $299 per unit |

**Total:** 5× $299 = **$1,495**

**Purpose:** Each server group (16 devices) has dedicated matrix for live viewing

---

### Network Infrastructure

**Core Switch:** Arista 7050TX-48 (48-port 10GbE)

| Specification | Value |
|---------------|-------|
| **Ports** | 48× 10GbE SFP+ |
| **Uplinks** | 4× 40GbE QSFP+ |
| **Throughput** | 1.28 Tbps (non-blocking) |
| **Latency** | <1μs port-to-port |
| **Management** | Full Layer 3, VLAN, QoS |
| **Power** | Dual AC PSU (redundant) |
| **Mounting** | 2U rackmount |
| **Price** | $8,000 (new) / $3,000 (used) |

**Access Switches:** 2× Netgear GS728TP (24-port PoE+)
- **Purpose:** Device rack management ports
- **Price:** 2× $350 = $700

**Total Networking:** **$8,700**

---

### USB & IR Controllers

**USB Controllers:** 5× StarTech PEXUSB3S44V (4-port USB 3.0 PCIe)
- **Total USB Ports:** 20 (for 20 mobile devices)
- **Price:** 5× $150 = **$750**

**Powered USB Hubs:** 5× Anker PowerPort 10 (60W)
- **Total USB Ports:** 50 (20 used for mobile charging)
- **Price:** 5× $50 = **$250**

**IR Controllers:** 5× Global Caché iTach IP2IR
- **Total IR Outputs:** 80 (for 60 STBs + spares)
- **Price:** 5× $299 = **$1,495**

**Total USB/IR:** **$2,495**

---

### Power Distribution & UPS

**Primary PDUs (Rack A - Compute):**
- 2× Tripp Lite PDUMH32HVNET (32A, 24 outlets, metered)
- **Price:** 2× $450 = **$900**

**Secondary PDUs (Rack B - Devices):**
- 2× Tripp Lite PDUMH15ATNET (15A, 8 outlets, metered)
- **Price:** 2× $299 = **$598**

**UPS Systems:**
- 2× CyberPower OR3000LCDRM2U (3000VA, 2U)
- **Runtime:** 15 min at full load
- **Price:** 2× $800 = **$1,600**

**Total Power Distribution:** **$3,098**

---

### Cable Management & Infrastructure

**Cable Management (Rack A):**
- Vertical cable managers: 4× $150 = $600
- Horizontal cable trays: 8× $80 = $640
- Breakout panels (80× HDMI): 5× $200 = $1,000
- Rack labels (DEV-001-080): $200

**Total Cable Management:** **$2,440**

**Device Shelves (Rack B):**
- STB Shelves (15× shelves, 4 STBs each): 15× $180 = $2,700
- Mobile Shelves (4× shelves, 6 mobiles each): 4× $200 = $800

**Total Shelves:** **$3,500**

---

### Rack Hardware

**Rack A (Compute - 42U):**
- APC NetShelter SX 42U Rack with doors
- **Dimensions:** 482mm × 1070mm × 2000mm (W×D×H)
- **Weight Capacity:** 1360kg (3000 lbs)
- **Features:** Perforated doors, cable management, leveling feet
- **Price:** $1,800

**Rack B (Devices - 42U):**
- APC NetShelter SX 42U Rack (same model)
- **Price:** $1,800

**Total Racks:** **$3,600**

---

## Bill of Materials (Production - 80 Devices)

### Core Infrastructure (Rack A - Compute)

| Item | Model | Qty | Unit Price | Total | Power |
|------|-------|-----|------------|-------|-------|
| **Proxmox Servers** | Supermicro AS-1114S-WN10RT | 5 | $6,000 | $30,000 | 2,000W |
| **HDMI Capture Cards** | Magewell Quad HDMI | 20 | $1,295 | $25,900 | 500W |
| **HDMI Splitters** | OREI HD-102 (1×2) | 80 | $18 | $1,440 | 0W |
| **HDMI Matrices** | OREI HMA-161 (16×1) | 5 | $299 | $1,495 | 75W |
| **Core Network Switch** | Arista 7050TX-48 | 1 | $8,000 | $8,000 | 300W |
| **Access Switches** | Netgear GS728TP | 2 | $350 | $700 | 50W |
| **USB Controllers** | StarTech PEXUSB3S44V | 5 | $150 | $750 | 25W |
| **Powered USB Hubs** | Anker PowerPort 10 | 5 | $50 | $250 | 300W |
| **IR Controllers** | Global Caché iTach | 5 | $299 | $1,495 | 25W |
| **PDUs (Compute)** | Tripp Lite 32A Metered | 2 | $450 | $900 | 0W |
| **UPS Systems** | CyberPower 3000VA | 2 | $800 | $1,600 | 0W |
| **Cable Management** | Vertical + Horizontal | - | - | $2,440 | 0W |
| **42U Rack (Compute)** | APC NetShelter SX | 1 | $1,800 | $1,800 | 0W |
| **Subtotal Rack A** | | | | **$76,770** | **3,275W** |

### Device Infrastructure (Rack B)

| Item | Model | Qty | Unit Price | Total | Power |
|------|-------|-----|------------|-------|-------|
| **Device Shelves (STB)** | 4U shelf, 4 STBs | 15 | $180 | $2,700 | 0W |
| **Device Shelves (Mobile)** | 2U shelf, 6 mobiles | 4 | $200 | $800 | 0W |
| **PDUs (Devices)** | Tripp Lite 15A Metered | 2 | $299 | $598 | 0W |
| **42U Rack (Devices)** | APC NetShelter SX | 1 | $1,800 | $1,800 | 0W |
| **Subtotal Rack B** | | | | **$5,898** | **0W** |

### Cables & Accessories

| Item | Specs | Qty | Unit Price | Total |
|------|-------|-----|------------|-------|
| **HDMI Cables (2m)** | 4K@60Hz, certified | 80 | $8 | $640 |
| **HDMI Cables (1m)** | For splitter→matrix | 80 | $5 | $400 |
| **HDMI Cables (0.5m)** | For splitter→capture | 80 | $5 | $400 |
| **USB 3.0 Cables** | 1.5m, shielded | 20 | $6 | $120 |
| **USB-C to HDMI Adapters** | With USB-C PD passthrough | 20 | $30 | $600 |
| **IR Extension Cables** | 2m, 3.5mm | 80 | $10 | $800 |
| **Ethernet Cables (10GbE)** | Cat6a, 2m, SFP+ | 10 | $25 | $250 |
| **Ethernet Cables (1GbE)** | Cat6a, 2m | 20 | $8 | $160 |
| **Power Cables (C13)** | 2m, 15A | 50 | $8 | $400 |
| **Rack Labels** | Device + Server labels | 1 | $500 | $500 |
| **Subtotal Cables** | | | | **$4,270** |

### Optional: Live Monitoring Displays

| Item | Model | Qty | Unit Price | Total |
|------|-------|-----|------------|-------|
| **Monitors (per server group)** | 15.6" portable HDMI | 5 | $120 | $600 |
| **Monitor Mounts** | Rack-top mounts | 5 | $40 | $200 |
| **Subtotal Monitors** | | | | **$800** |

---

## Cost Summary

### Infrastructure Only

| Category | Cost |
|----------|------|
| Rack A (Compute Infrastructure) | $76,770 |
| Rack B (Device Shelves) | $5,898 |
| Cables & Accessories | $4,270 |
| Live Monitoring (Optional) | $800 |
| **Total Infrastructure** | **$87,738** |
| **Cost per device slot** | **$1,097** (80 slots) |

### With Physical Devices (Turnkey)

| Category | Cost |
|----------|------|
| Infrastructure | $87,738 |
| 60× STBs (Apple TV 4K) | 60 × $129 = $7,740 |
| 20× Mobile Devices (Pixel 7) | 20 × $599 = $11,980 |
| **Total Complete** | **$107,458** |

### ROI Analysis vs Cloud Device Farms

| Service | Cost Model | 80 Devices | Break-Even |
|---------|------------|------------|------------|
| **BrowserStack** | $2,000/month per device | $160,000/month | 0.5 months |
| **Sauce Labs** | $1,500/month per device | $120,000/month | 0.7 months |
| **LambdaTest** | $1,000/month per device | $80,000/month | 1.1 months |
| **Your Setup** | $87,738 CAPEX | $0/month recurring | **Paid off in 1 month!** |

**Annual Savings:** $960,000 - $1,920,000 vs cloud farms! 💰

---

## Rack Layout Diagrams

### Rack A: Compute Infrastructure (42U - Full Utilization)

```
┌─────────────────────────────────────────────────────────────┐
│ RACK A - COMPUTE ONLY (No Physical Devices)                 │
├─────────────────────────────────────────────────────────────┤
│ U42-41 (2U): Core Network Switch (Arista 48-port 10GbE)     │
│              - Uplink to datacenter                          │
│              - 10× 10GbE to servers                          │
│              - Inter-rack connectivity                       │
├─────────────────────────────────────────────────────────────┤
│ U40-37 (4U): Proxmox Server #1 (Frontend + 16 devices)      │
│              CPU: AMD EPYC 7313P (16 cores)                  │
│              RAM: 128GB DDR4 ECC                             │
│              PCIe: 4× Magewell Quad HDMI (16 inputs)         │
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
│              - 5× Anker 10-port hubs (60W each)             │
│              - 50 USB ports total (20 used for mobiles)      │
│              - Power: 300W                                   │
├─────────────────────────────────────────────────────────────┤
│ U16-15 (2U): IR Blaster Controller Array                    │
│              - 5× Global Caché iTach (16 ports each)         │
│              - 80 IR outputs total                           │
│              - Network controlled                            │
├─────────────────────────────────────────────────────────────┤
│ U14-11 (4U): Cable Breakout Panels + HDMI Splitters         │
│              - 80× HDMI female → to Device Rack              │
│              - 80× HDMI Splitters (signal split)            │
│              - 80× USB pass-through → to Device Rack         │
│              - 80× IR pass-through → to Device Rack          │
│              - Labeled: DEV-001 to DEV-080                   │
├─────────────────────────────────────────────────────────────┤
│ U10-07 (4U): HDMI Matrix Array + Monitors (Optional)        │
│              - 5× OREI 16×1 HDMI Matrix                     │
│              - 5× 15.6" monitors on rack-top                │
│              - Live view for each server group               │
├─────────────────────────────────────────────────────────────┤
│ U06-03 (4U): Cable Management                               │
│              - Vertical cable managers                       │
│              - Cable routing channels                        │
│              - Proper airflow maintained                     │
├─────────────────────────────────────────────────────────────┤
│ U02-01 (2U): UPS Systems                                    │
│              - 2× CyberPower 3000VA                         │
│              - 15min runtime at full load                   │
│              - Automatic shutdown triggers                   │
└─────────────────────────────────────────────────────────────┘

Total: 42U (100% utilized)
Power: 3,275W (servers + capture + network + hubs + IR)
Weight: ~500kg (servers dominate)
```

### Rack B: Device Shelves (42U - Full Utilization)

```
┌─────────────────────────────────────────────────────────────┐
│ RACK B - DEVICES ONLY (No Servers or Compute)               │
├─────────────────────────────────────────────────────────────┤
│ U42 (1U): PDU #2 (15A, 8 outlets)                          │
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
│ Configuration: 60 STBs + 20 Mobiles = 80 devices            │
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
│ U07-06 (2U): STB Shelf #14 (4 STBs: 57-60)                  │
├─────────────────────────────────────────────────────────────┤
│ U05-04 (2U): Environmental Monitoring                       │
│              - Temperature/humidity sensors                  │
│              - Smoke detector                                │
│              - Network-connected alerts                      │
├─────────────────────────────────────────────────────────────┤
│ U03-01 (3U): PDU #3 + Cable Management Tray                 │
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

---

## Power Consumption (Production)

### Rack A (Compute) - Idle State

| Component | Power Draw | Qty | Total |
|-----------|------------|-----|-------|
| Servers (idle) | 150W | 5 | 750W |
| Capture Cards (idle) | 10W | 20 | 200W |
| USB Controllers | 5W | 5 | 25W |
| IR Controllers | 5W | 5 | 25W |
| USB Hubs | 10W | 5 | 50W |
| Network Switch (core) | 300W | 1 | 300W |
| Network Switch (access) | 25W | 2 | 50W |
| **Total Idle Rack A** | | | **1,400W** |

### Rack A (Compute) - Active Testing

| Component | Power Draw | Qty | Total |
|-----------|------------|-----|-------|
| Servers (75% load) | 400W | 5 | 2,000W |
| Capture Cards (active) | 25W | 20 | 500W |
| USB Controllers | 5W | 5 | 25W |
| IR Controllers | 5W | 5 | 25W |
| USB Hubs (charging) | 60W | 5 | 300W |
| Network Switch (core) | 300W | 1 | 300W |
| Network Switch (access) | 25W | 2 | 50W |
| **Total Active Rack A** | | | **3,200W** |

### Rack B (Devices) - Active Testing

| Component | Power Draw | Qty | Total |
|-----------|------------|-----|-------|
| STBs (playback) | 15W | 60 | 900W |
| Mobiles (active) | 10W | 20 | 200W |
| PDUs | 0W | 2 | 0W |
| **Total Active Rack B** | | | **1,100W** |

### Combined Power Requirements

| State | Rack A | Rack B | Total | Circuit |
|-------|--------|--------|-------|---------|
| **Idle** | 1,400W | 200W | 1,600W | 2× 15A @ 120V |
| **Active** | 3,200W | 1,100W | 4,300W | 2× 20A @ 208V |
| **Peak** | 4,000W | 1,200W | 5,200W | 2× 30A @ 208V |

### Electrical Requirements

**Datacenter Circuits Needed:**
- **Rack A:** 2× 20A @ 208V circuits (minimum)
- **Rack B:** 1× 15A @ 120V circuit (sufficient)
- **UPS Protection:** 2× 3000VA (handles Rack A during outages)

**Monthly Electricity Cost:**
```
Active: 4,300W × 8h × 30 days = 1,032 kWh
Idle: 1,600W × 16h × 30 days = 768 kWh
Total: 1,800 kWh/month
Cost @ $0.12/kWh: $216/month
```

**Annual Electricity:** ~$2,592 (negligible vs cloud costs)

---

## Cooling Requirements

### Heat Output (BTU/hr)

| State | Power (Watts) | BTU/hr | AC Tonnage |
|-------|---------------|--------|------------|
| **Idle** | 1,600W | 5,461 BTU/hr | 0.5 tons |
| **Active** | 4,300W | 14,673 BTU/hr | 1.2 tons |
| **Peak** | 5,200W | 17,746 BTU/hr | 1.5 tons |

**Datacenter AC Requirements:**
- **Minimum:** 2 tons (24,000 BTU/hr) dedicated AC
- **Recommended:** 3 tons (36,000 BTU/hr) for headroom
- **Redundancy:** N+1 AC units (2× 2-ton units)

**Airflow:**
- **Front-to-rear** airflow in servers
- **Hot aisle / cold aisle** layout
- **Rack A (Compute):** Requires more cooling (servers generate most heat)
- **Rack B (Devices):** Minimal cooling (devices are low-power)

---

## Physical Dimensions & Space Requirements

### Rack Footprint

| Rack | Width | Depth | Height | Weight | Clearance |
|------|-------|-------|--------|--------|-----------|
| **Rack A (Compute)** | 482mm (19") | 1,070mm | 2,000mm | 500kg | 1,200mm rear |
| **Rack B (Devices)** | 482mm (19") | 1,070mm | 2,000mm | 400kg | 800mm rear |

**Total Floor Space:**
- **Width:** 1,500mm (2 racks + clearance)
- **Depth:** 2,000mm (rack + rear clearance)
- **Total:** 3.0 m² (32 sq ft) for 80 devices

**Cable Run Between Racks:**
- **Distance:** 5m (16 ft) recommended
- **Bundle Size:** 80× HDMI + 80× USB + 80× IR = 240 cables
- **Cable Tray:** 300mm wide × 5m long

---

## Scaling Path

### Phase 1: Production (5 Servers = 80 Devices) - **$87,738**

**Current Setup:**
```
2× Racks (Compute + Devices)
5× Proxmox Servers
80× Device slots
```

### Phase 2: Scale to 160 Devices - **+$87k**

**Add:**
- 2× New racks (Rack C + Rack D)
- 5× Identical servers (same as Phase 1)
- Double all peripherals

**Total:**
```
4× Racks (2 compute + 2 device racks)
10× Proxmox Servers
160× Device slots
$175k total investment
```

### Phase 3: Scale to 320 Devices - **+$175k**

**Add:**
- 4× New racks (2 compute + 2 device pairs)
- 10× Identical servers

**Total:**
```
8× Racks (4 compute + 4 device racks)
20× Proxmox Servers
320× Device slots
$350k total investment
```

**Scaling Formula:** Every 2 racks = +80 devices = +$87k

---

## Comparison: Demo vs Production

| Metric | Demo (1 Server) | Production (5 Servers) |
|--------|-----------------|------------------------|
| **Servers** | 1 | 5 |
| **Devices** | 16 | 80 |
| **Capture Cards** | 4 | 20 |
| **Power (Active)** | 675W | 4,300W |
| **Racks** | 1× 12U desktop | 2× 42U datacenter |
| **Cost** | $14,038 | $87,738 |
| **Space** | 0.3 m² | 3.0 m² |
| **Cost per device** | $877 | $1,097 |
| **Monthly electricity** | $33 | $216 |

**Hardware is Identical:**
- ✅ Same CPU/RAM per server
- ✅ Same capture cards
- ✅ Same USB/IR controllers
- ✅ Same network architecture
- ✅ Same HDMI splitter system

**Demo → Production Path:**
```
Demo Server #1 → Moves to Production Rack A (Server #1)
Add 4 more identical servers → Production complete
```

**Your demo investment becomes production infrastructure!** 🎯

---

## Why This Architecture is Production-Ready

### Technical Excellence

| Aspect | Implementation |
|--------|----------------|
| **Zero Single Point of Failure** | Decentralized: Each server group independent |
| **Linear Scaling** | Add rack pairs: 80→160→240→320+ devices |
| **Hot Maintenance** | Swap devices without downtime |
| **Proven Hardware** | Magewell (broadcast), Supermicro (datacenter) |
| **Network Performance** | 10GbE non-blocking fabric |
| **Power Redundancy** | Dual PSUs, UPS backup |

### Business Benefits

| Benefit | Value |
|---------|-------|
| **ROI vs Cloud** | Break-even in 1 month vs BrowserStack |
| **Annual Savings** | $960k - $1.9M vs cloud device farms |
| **Capital Efficiency** | $1,097 per device (vs $2k/month cloud) |
| **Data Sovereignty** | Your devices, your data, your security |
| **Infinite Scaling** | Add racks as needed, no vendor limits |

### Operational Excellence

| Feature | Advantage |
|---------|-----------|
| **Same as Demo** | Zero surprises, proven architecture |
| **Modular Design** | Rack A independent of Rack B |
| **Standard Hardware** | Available globally, easy replacement |
| **Full Automation** | Proxmox + Docker + VirtualPyTest |
| **Live Monitoring** | Physical screens + Grafana dashboards |

---

## Summary

**Production Configuration:**

| Specification | Value |
|---------------|-------|
| **Capacity** | 80 devices (60 STBs + 20 Mobiles or any mix) |
| **Hardware** | 5× Supermicro EPYC servers + Magewell capture |
| **Racks** | 2× 42U (Compute + Devices) |
| **Infrastructure Cost** | $87,738 |
| **Power** | 1,600W idle / 4,300W active |
| **Space** | 3.0 m² (32 sq ft) |
| **Scalability** | Linear: +2 racks = +80 devices |

**Key Advantages:**

✅ **Production-Grade:** Netflix/Roku/Comcast-level hardware  
✅ **Cost Effective:** 98% cheaper than cloud ($1,097 vs $2k/month per device)  
✅ **Proven Architecture:** Demo is Server #1, production adds 4 more  
✅ **Zero Risk:** Same hardware from demo to 320+ devices  
✅ **Infinite Scale:** Add rack pairs as needed  
✅ **Fast ROI:** Break-even in 1 month vs cloud alternatives  

**Your demo validates the production system. Production is just 5× demo!** 🚀

