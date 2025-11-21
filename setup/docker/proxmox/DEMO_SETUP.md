# VirtualPyTest - Demo Setup (Production-Grade Hardware)

Demonstration setup using **identical hardware** as production deployment, scaled to 1 Proxmox server.

**Philosophy:** Same hardware, same configuration, smaller scale. What works in demo works at scale.

**Capacity:** 1 server = 16 devices (4 STBs + 4 Mobiles + 8 Web) or any mix

---

## Hardware Specifications (Same as Production)

### Proxmox Server (Identical to Production Rack A)

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

**PCIe Slot Configuration (8 slots available):**
- Slot 1: PCIe 4.0 x16 (CPU) → HDMI Capture Card #1
- Slot 2: PCIe 4.0 x16 (CPU) → HDMI Capture Card #2
- Slot 3: PCIe 4.0 x8 (CPU) → HDMI Capture Card #3
- Slot 4: PCIe 4.0 x8 (CPU) → HDMI Capture Card #4
- Slot 5: PCIe 3.0 x4 (Chipset) → USB 3.0 Controller
- Slot 6: PCIe 3.0 x4 (Chipset) → IR Controller (PCIe)
- Slot 7: PCIe 3.0 x4 (Chipset) → Reserved/Expansion
- Slot 8: PCIe 3.0 x1 (Chipset) → Reserved/Expansion

---

### HDMI Capture Cards (Same as Production)

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
| **Dimensions** | Full-height, half-length |
| **Driver** | Included in Linux kernel 4.4+ |
| **Price** | $1,295 per card |

**For Demo:**
- **Minimum:** 2 cards = 8 HDMI inputs = $2,590
- **Full Demo:** 4 cards = 16 HDMI inputs = $5,180

**Why This Card:**
- ✅ Professional-grade (Magewell = industry standard)
- ✅ Low latency (critical for real-time testing)
- ✅ Hardware encoding (no CPU load)
- ✅ Linux native (Proxmox compatible)
- ✅ Proven at scale (used in broadcast industry)

---

### USB 3.0 Controller (Same as Production)

**Model:** StarTech PEXUSB3S44V (4-Port USB 3.0 PCIe Card)

| Specification | Value |
|---------------|-------|
| **USB Ports** | 4× USB 3.0 Type-A (5Gbps each) |
| **PCIe Interface** | PCIe 2.0 x1 |
| **Chipset** | VIA VL805 (Linux compatible) |
| **Power Delivery** | 900mA per port (USB 3.0 spec) |
| **Hot-Swap** | Supported |
| **Dimensions** | Low-profile bracket included |
| **Price** | $149.99 |

**For Demo:** 1 card (4 USB ports for mobiles)

**Why This Card:**
- ✅ Dedicated USB controller (better than motherboard)
- ✅ VIA chipset (proven Linux/ADB stability)
- ✅ PCIe passthrough compatible (Proxmox)

---

### IR Controller (Same as Production)

**Model:** Global Caché iTach IP2IR (Network-based)

| Specification | Value |
|---------------|-------|
| **IR Outputs** | 3× IR (expandable to 16 via flex ports) |
| **Interface** | Ethernet (TCP/IP) |
| **Control Protocol** | ASCII commands via TCP |
| **IR Database** | 10,000+ device codes included |
| **Power** | 5W (external adapter) |
| **Dimensions** | 127mm × 76mm × 25mm (standalone box) |
| **Price** | $299 |

**Why Network-based:**
- ✅ No PCIe slot consumed
- ✅ Easier VM access (network, not passthrough)
- ✅ Can be placed near STBs
- ✅ Hot-swappable (network cable)

**For Demo:** 1 unit (16 IR outputs for STBs)

---

### Powered USB Hub (Same as Production)

**Model:** Anker PowerPort 10 USB-C (60W)

| Specification | Value |
|---------------|-------|
| **USB Ports** | 10× USB 3.0 Type-A |
| **Total Power** | 60W (6A @ 5V) |
| **Per-Port Power** | 2.4A max (12W) - sufficient for mobile charging |
| **Data Speed** | 5Gbps (USB 3.0) |
| **Power Supply** | External 60W adapter |
| **Dimensions** | 165mm × 90mm × 28mm |
| **Price** | $49.99 |

**For Demo:** 1 hub (10 ports, use 4 for mobiles)

**Why External Hub:**
- ✅ 2.4A per port (phones charge during tests)
- ✅ No PCIe slot consumed
- ✅ Easy to expand (just add more hubs)
- ✅ Hot-swappable devices

---

### Power Distribution (Same as Production)

**Model:** Tripp Lite PDUMH15ATNET (Metered PDU)

| Specification | Value |
|---------------|-------|
| **Input** | 120V 15A (NEMA 5-15P) or 208/240V 15A (L6-15P) |
| **Outlets** | 8× NEMA 5-15R (front-facing) |
| **Capacity** | 1800W @ 120V or 3600W @ 208V |
| **Monitoring** | Network-based (web/SNMP) |
| **Current Display** | Digital LCD (real-time amps) |
| **Mounting** | Rack-mount 1U or desktop |
| **Price** | $299 |

---

## Demo Configuration (1 Server = 16 Devices)

**Standard Setup - Production Hardware at Demo Scale:**

```
1× Proxmox Server
├── 4× HDMI Capture Cards (16 inputs total)
├── 1× USB Controller (4 ports)
├── 1× IR Controller (16 outputs)
├── 1× Powered USB Hub (10 ports)
└── Devices:
    ├── 4× STBs (HDMI + IR control)
    ├── 4× Mobiles (HDMI + USB/ADB)
    └── 8× Web hosts (no physical hardware)
```

**Total Capacity:** 16 testing units (expandable to 80 by adding 4 more servers)

---

## Bill of Materials (Demo - 16 Device Capacity)

### Core Infrastructure (Same Hardware as Production)

| Item | Model | Qty | Unit Price | Total | Power |
|------|-------|-----|------------|-------|-------|
| **Proxmox Server** | Supermicro AS-1114S-WN10RT | 1 | $6,000 | $6,000 | 400W |
| **HDMI Capture Card** | Magewell Quad HDMI | 4 | $1,295 | $5,180 | 100W |
| **Network Switch** | Netgear GS108 (8-port 1GbE) | 1 | $29 | $29 | 5W |
| **Powered USB Hub** | Anker PowerPort 10 | 1 | $50 | $50 | 60W |
| **IR Controller** | Global Caché iTach IP2IR | 1 | $299 | $299 | 5W |
| **Cable Mgmt Kit** | Rack cable managers (3U) | 1 | $120 | $120 | 0W |
| **PDU (Metered)** | Tripp Lite PDUMH15ATNET | 1 | $299 | $299 | 0W |
| **UPS** | CyberPower OR1500LCDRM1U | 1 | $450 | $450 | 0W |
| **Subtotal Infrastructure** | | | | **$12,627** | **580W** |

### Cables & Accessories

| Item | Specs | Qty | Unit Price | Total |
|------|-------|-----|------------|-------|
| **HDMI Cables** | 2m, 4K@60Hz, certified | 16 | $8 | $128 |
| **USB 3.0 Cables** | 1.5m, shielded | 4 | $6 | $24 |
| USB-C to HDMI Adapters** | 4K@60Hz, DP alt mode | 4 | $15 | $60 |
| **IR Extension Cables** | 2m, 3.5mm | 16 | $10 | $160 |
| **Ethernet Cables** | Cat6a, 2m | 2 | $8 | $16 |
| **Cable Management** | Breakout panels + organizers | 1 | $120 | $120 |
| **Rack Labels** | Device labels (DEV-001-016) | 1 | $40 | $40 |
| **Subtotal Cables** | | | | **$524** |

### Physical Devices (Optional - Customer Provided)

| Item | Qty | Unit Price | Total | Power |
|------|-----|------------|-------|-------|
| **STBs** (Apple TV 4K or equivalent) | 4 | $129 | $516 | 20W |
| **Mobile Devices** (Google Pixel 7) | 4 | $599 | $2,396 | 40W |
| **Subtotal Devices** | | | **$2,912** | **60W** |

---

## Cost Summary

### Infrastructure Only (Production-Grade)

| Category | Cost |
|----------|------|
| Server + Capture + Network + Cable Mgmt | $12,627 |
| Cables & Accessories | $524 |
| **Total Infrastructure** | **$13,151** |
| **Cost per device slot** | **$822** (16 slots) |

### With Devices (Turnkey Demo)

| Category | Cost |
|----------|------|
| Infrastructure | $13,151 |
| 4 STBs | $516 |
| 4 Mobile Devices | $2,396 |
| **Total Complete** | **$16,063** |

---

## Power Consumption (Production-Grade Hardware)

### Idle State (VMs Running, No Tests)

| Component | Power Draw | Qty | Total |
|-----------|------------|-----|-------|
| Server (idle) | 150W | 1 | 150W |
| Capture Cards (idle) | 10W | 4 | 40W |
| USB Controller | 5W | 1 | 5W |
| IR Controller | 5W | 1 | 5W |
| USB Hub | 10W | 1 | 10W |
| Network Switch | 5W | 1 | 5W |
| STBs (standby) | 2W | 4 | 8W |
| Mobiles (trickle charge) | 5W | 4 | 20W |
| **Total Idle** | | | **243W** |

### Active Testing (All Devices Running)

| Component | Power Draw | Qty | Total |
|-----------|------------|-----|-------|
| Server (75% load) | 400W | 1 | 400W |
| Capture Cards (active) | 25W | 4 | 100W |
| USB Controller | 5W | 1 | 5W |
| IR Controller | 5W | 1 | 5W |
| USB Hub (charging) | 60W | 1 | 60W |
| Network Switch | 5W | 1 | 5W |
| STBs (playback) | 15W | 4 | 60W |
| Mobiles (active) | 10W | 4 | 40W |
| **Total Active** | | | **675W** |

### Peak Load (Stress Test)

| Component | Power Draw | Qty | Total |
|-----------|------------|-----|-------|
| Server (100% CPU) | 600W | 1 | 600W |
| All peripherals | 275W | - | 275W |
| **Total Peak** | | | **875W** |

### Electrical Requirements

**Circuit Needed:**
- **Minimum:** 1× 15A @ 120V (1,800W capacity)
- **Recommended:** 1× 20A @ 120V (2,400W capacity)
- **UPS Protection:** 1500VA minimum

**Monthly Cost (8h/day testing):**
```
Active: 675W × 8h × 30 days = 162 kWh
Idle: 243W × 16h × 30 days = 117 kWh
Total: 279 kWh/month
Cost @ $0.12/kWh: $33.48/month
```

**Annual Electricity:** ~$402

---

## Physical Dimensions & Rack Layout

### 12U Desktop Rack (Required)

**Rack Model:** StarTech 12U Open Frame Rack
- **Dimensions:** 482mm × 610mm × 610mm (W×D×H)
- **Price:** $189
- **Weight Capacity:** 113kg (250 lbs)

### Rack Installation Diagram (U-by-U)

```
FRONT VIEW                                    REAR VIEW (Cable Side)
┌──────────────────────────────────────┐    ┌──────────────────────────────────────┐
│ U12│🖥️ PROXMOX SERVER (Supermicro)   │    │ U12│[PWR][PWR] [10GbE][1GbE][IPMI]   │
├────┼──────────────────────────────────┤    ├────┼──────────────────────────────────┤
│ U11│🖥️ SERVER (4U continued)          │    │ U11│[PCIe Breakout Panel]             │
├────┼──────────────────────────────────┤    ├────┼──────────────────────────────────┤
│ U10│🖥️ SERVER (continued)             │    │ U10│ HDMI: [1][2][3][4]              │
├────┼──────────────────────────────────┤    ├────┼──────────────────────────────────┤
│ U9 │🖥️ SERVER (continued)             │    │ U9 │ HDMI: [5][6][7][8]              │
├────┼──────────────────────────────────┤    ├────┼──────────────────────────────────┤
│ U8 │📡 NETWORK SWITCH (8-port 1GbE)   │    │ U8 │[8× RJ45] [Uplink] [Power]       │
├────┼──────────────────────────────────┤    ├────┼──────────────────────────────────┤
│ U7 │🔌 USB HUB + IR CONTROLLER        │    │ U7 │[10× USB3.0] [IR: 16 outputs]    │
├────┼──────────────────────────────────┤    ├────┼──────────────────────────────────┤
│ U6 │🔋 UPS (CyberPower 1500VA - 2U)   │    │ U6 │[Battery Bay] [AC Input] [AC Out] │
├────┼──────────────────────────────────┤    ├────┼──────────────────────────────────┤
│ U5 │🔋 UPS (continued)                │    │ U5 │[AC Outlets: Server + Network]    │
├────┼──────────────────────────────────┤    ├────┼──────────────────────────────────┤
│ U4 │📦 CABLE MANAGEMENT (Breakout)    │    │ U4 │[16× HDMI Female] [Cable Routing] │
├────┼──────────────────────────────────┤    ├────┼──────────────────────────────────┤
│ U3 │📦 CABLE MANAGEMENT (Vertical)    │    │ U3 │[Cable Channels] [Velcro Straps] │
├────┼──────────────────────────────────┤    ├────┼──────────────────────────────────┤
│ U2 │📦 CABLE MANAGEMENT (Routing)     │    │ U2 │[D-Ring Organizers] [Airflow]    │
├────┼──────────────────────────────────┤    ├────┼──────────────────────────────────┤
│ U1 │🔌 PDU (Metered, 8 outlets)       │    │ U1 │[AC Input] → [Outlets: 1-8]      │
└────┴──────────────────────────────────┘    └────┴──────────────────────────────────┘
  ↑ Bottom (Floor Level)                       ↑ Bottom

External Equipment (On desk near rack):
├── 📱 4× STBs (shelves with power/HDMI/IR)
├── 📱 4× Mobiles (charging stands with HDMI/USB)
└── 🌐 8× Web devices (no physical hardware)

CRITICAL: This is NOT a "demo-only" setup.
This is Production Server #1 that will become part of 5-server production!
```

### Installation Order (Top to Bottom - Practical)

**Install heavy equipment first (top), lighter equipment last (bottom):**

1. **U9-U12 (Top):** Install Proxmox server (4U)
   - Heaviest component (35kg) goes at top for stability
   - Mount 4× Magewell capture cards in PCIe slots
   - Mount 1× StarTech USB controller in PCIe slot
   - Better cooling (hot air rises, exhausts at top)

2. **U8:** Install network switch (1U)
   - 8-port managed switch
   - Connect to server 10GbE port
   - Uplink to internet/router

3. **U7:** Install USB hub array + IR controller (1U shelf)
   - 1× Anker 10-port powered USB hub (for mobiles)
   - 1× Global Caché iTach (network IR controller)
   - Both mounted on 1U shelf

4. **U5-U6:** Install UPS (2U) in middle
   - Sliding rails for battery access
   - Power cables route up to server, switch, hubs

5. **U4:** Install cable breakout panel (1U)
   - 16× HDMI female ports (routes to devices on desk)
   - Labeled: DEV-001 to DEV-016
   - Professional cable presentation

6. **U3-U2:** Install vertical cable management (2U)
   - Cable routing channels
   - Velcro straps for organization
   - Maintains proper airflow

7. **U1 (Bottom):** Install PDU (1U) at floor level
   - Easy access for plugging/unplugging
   - Front-facing outlets pointing forward
   - Connect to wall outlet (shortest cable run)
   - Feeds power up to UPS

8. **Cable routing from server (U9-U10) to breakout panel (U4):**
   - 16× HDMI cables drop down through cable management
   - 16× USB cables (from hub at U7)
   - 16× IR cables (from iTach at U7)
   - All cables labeled matching devices

**Why This Layout Matches Production (DEPLOYMENT_GUIDE.md Rack A):**
- ✅ **Same structure:** Server top, network/infrastructure middle, power bottom
- ✅ **Same cable management:** Professional breakout panels + routing
- ✅ **Scalable:** Add 4 more servers = become 5-server Rack A
- ✅ **No surprises:** Demo setup IS production Server #1

### Cable Management

**Rear of Server (U10-U11 - PCIe Breakout Panel):**
```
┌──────────────────────────────────────────────────────┐
│  CAPTURE CARD 1: [HDMI1] [HDMI2] [HDMI3] [HDMI4]   │ ← U11
│  CAPTURE CARD 2: [HDMI5] [HDMI6] [HDMI7] [HDMI8]   │ ← U10
│  CAPTURE CARD 3: [HDMI9] [HDMI10][HDMI11][HDMI12]  │ ← U10
│  CAPTURE CARD 4: [HDMI13][HDMI14][HDMI15][HDMI16]  │ ← U10
│                                                      │
│  USB CONTROLLER: [USB1] [USB2] [USB3] [USB4]        │ ← U10
└──────────────────────────────────────────────────────┘

Power & Network (U12 - Top Rear):
┌──────────────────────────────────────────────────────┐
│  POWER: [PSU1 - Redundant] [PSU2 - Redundant]       │
│  NETWORK: [10GbE-1] [10GbE-2] [1GbE-MGMT] [IPMI]   │
└──────────────────────────────────────────────────────┘
```

**Device Connections:**
- STB 1: HDMI1 → Server, IR1 → iTach port 1
- STB 2: HDMI2 → Server, IR2 → iTach port 2
- STB 3: HDMI3 → Server, IR3 → iTach port 3
- STB 4: HDMI4 → Server, IR4 → iTach port 4
- Mobile 1: HDMI5 (via USB-C) → Server, USB1 → USB hub
- Mobile 2: HDMI6 (via USB-C) → Server, USB2 → USB hub
- Mobile 3: HDMI7 (via USB-C) → Server, USB3 → USB hub
- Mobile 4: HDMI8 (via USB-C) → Server, USB4 → USB hub

### Space Requirements

**Total Footprint:**
- **Rack:** 482mm × 610mm (W×D)
- **Desk/Table:** 1500mm × 800mm (for devices + rack)
- **Ventilation:** 200mm clearance on all sides
- **Height:** 610mm (rack) + devices on desk

---

## Scaling Path (Demo → Production)

### Phase 1: Demo (1 Server = 16 Devices) - **$13,151**

This demo server **becomes Production Server #1**

```
1× Proxmox Server → 16 devices
```

### Phase 2: Add Servers 2-5 (80 Devices) - **+$54k**

Add 4 identical servers (same model, same config):
- Server #2: $12,000 (server + 4 capture cards)
- Server #3: $12,000
- Server #4: $12,000
- Server #5: $12,000

```
5× Proxmox Servers (Rack A - Compute)
1× Device Rack (Rack B - Shelves)
Total: 80 devices
```

**Your demo server is now Server #1 in production!**

### Phase 3: Scale to 160 Devices - **+$67k**

Add 1 more server rack + 1 device rack:
- Rack C (5 servers): $60k
- Rack D (device shelves): $7k

```
10× Proxmox Servers (2 compute racks)
2× Device Racks
Total: 160 devices
```

---

## Comparison to Production Deployment

### Demo (1 Server) vs Production (5 Servers)

| Metric | Demo | Production (Rack A) |
|--------|------|---------------------|
| **Servers** | 1 | 5 |
| **Devices** | 16 | 80 |
| **Capture Cards** | 4 | 20 |
| **Power** | 675W | 2,650W |
| **Space** | 12U rack | 42U rack |
| **Cost** | $13,151 | $67k |
| **Scalability** | Becomes Server #1 | Linear to 320+ |

**Hardware is Identical:**
- ✅ Same CPU/RAM
- ✅ Same capture cards
- ✅ Same USB/IR controllers
- ✅ Same network interfaces
- ✅ Same BIOS/firmware

**Only Difference is Quantity!**

---