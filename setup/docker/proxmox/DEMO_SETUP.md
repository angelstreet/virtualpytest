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

**Note:** This card does NOT have HDMI loop-through, so we use HDMI splitters for live monitoring.

---

### HDMI Splitters (For Live Monitor View)

**Model:** OREI HD-102 (1-in-2-out HDMI Splitter)

| Specification | Value |
|---------------|-------|
| **Inputs** | 1× HDMI 2.0 |
| **Outputs** | 2× HDMI 2.0 (identical copies) |
| **Max Resolution** | 4K@60Hz |
| **Power** | Passive (no power needed) |
| **Latency** | 0ms (pure signal split) |
| **Dimensions** | 100mm × 60mm × 20mm (tiny!) |
| **Mounting** | In cable management tray |
| **Price** | $18 per splitter |

**For Demo:** 16 splitters (one per device, hidden in cable tray)

**Signal Flow:**
```
Device HDMI Out → Splitter Input
                   ↓         ↓
              Output A   Output B
                   ↓         ↓
             Capture Card  Matrix Switch
             (recording)   (live monitor)
```

**Why Splitters:**
- ✅ Each device signal goes to 2 places simultaneously
- ✅ Zero latency (passive hardware)
- ✅ Capture card records for automation
- ✅ Matrix shows live on physical monitor (0ms delay for demos)

---

### HDMI Matrix Switch (For Demo Live View)

**Model:** OREI HMA-161 (16×1 HDMI Matrix)

| Specification | Value |
|---------------|-------|
| **Inputs** | 16× HDMI (from splitters) |
| **Outputs** | 1× HDMI (to monitor) |
| **Max Resolution** | 4K@60Hz |
| **Control** | Front panel buttons + IR remote |
| **Switching Speed** | <1 second |
| **Mounting** | 1U rackmount |
| **Dimensions** | 482mm × 200mm × 44mm (1U) |
| **Power** | 12V DC adapter (included) |
| **Price** | $299 |

**Purpose:** Press button 1-16 to instantly view any device on monitor (0ms latency)

**Why This is Critical:**
- ✅ Web UI has 4-6s latency (not good for live demos)
- ✅ Physical monitor shows real-time device output
- ✅ Clients see actual device = trust + wow factor
- ✅ Troubleshooting: instant visual feedback

---

### Demo Monitor (Live Device View)

**Model:** UPERFECT 15.6" Portable Monitor

| Specification | Value |
|---------------|-------|
| **Screen Size** | 15.6" diagonal |
| **Resolution** | 1920×1080 (Full HD) |
| **Input** | HDMI (from matrix switch) |
| **Power** | USB-C (5V/2A) |
| **Mounting** | Sits on top of rack |
| **Weight** | 800g (lightweight) |
| **Price** | $120 |

**Purpose:** Shows selected device in real-time (0ms delay via HDMI)

**Placement:** On top of 12U rack, connected to matrix output

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
├── 16× HDMI Splitters (signal split for capture + live view)
├── 1× HDMI Matrix (16×1 switch for monitor)
└── Devices:
    ├── 4× STBs (HDMI → Splitter → Capture + Matrix)
    ├── 4× Mobiles (HDMI → Splitter → Capture + Matrix)
    └── 8× Web hosts (no physical hardware)

Live Monitor (15.6" on rack top):
└── Shows selected device in real-time (0ms delay)
```

**Total Capacity:** 16 testing units (expandable to 80 by adding 4 more servers)

---

## Bill of Materials (Demo - 16 Device Capacity)

### Core Infrastructure (Same Hardware as Production)

| Item | Model | Qty | Unit Price | Total | Power |
|------|-------|-----|------------|-------|-------|
| **Proxmox Server** | Supermicro AS-1114S-WN10RT | 1 | $6,000 | $6,000 | 400W |
| **HDMI Capture Card** | Magewell Quad HDMI | 4 | $1,295 | $5,180 | 100W |
| **HDMI Splitters** | OREI HD-102 (1×2) | 16 | $18 | $288 | 0W |
| **HDMI Matrix** | OREI HMA-161 (16×1) | 1 | $299 | $299 | 15W |
| **Demo Monitor** | UPERFECT 15.6" Portable | 1 | $120 | $120 | 10W |
| **Network Switch** | Netgear GS108 (8-port 1GbE) | 1 | $29 | $29 | 5W |
| **Powered USB Hub** | Anker PowerPort 10 | 1 | $50 | $50 | 60W |
| **IR Controller** | Global Caché iTach IP2IR | 1 | $299 | $299 | 5W |
| **Cable Mgmt Kit** | Rack cable managers (3U) | 1 | $120 | $120 | 0W |
| **PDU (Metered)** | Tripp Lite PDUMH15ATNET | 1 | $299 | $299 | 0W |
| **UPS** | CyberPower OR1500LCDRM1U | 1 | $450 | $450 | 0W |
| **Subtotal Infrastructure** | | | | **$13,342** | **610W** |

### Cables & Accessories

| Item | Specs | Qty | Unit Price | Total |
|------|-------|-----|------------|-------|
| **HDMI Cables** | 2m, 4K@60Hz, certified | 16 | $8 | $128 |
| **HDMI Cables (Short)** | 1m for splitter→matrix | 16 | $5 | $80 |
| **HDMI Cables (Short)** | 0.5m for splitter→capture | 16 | $5 | $80 |
| **USB 3.0 Cables** | 1.5m, shielded (for ADB) | 4 | $6 | $24 |
| **USB-C to HDMI Adapters** | With USB-C PD passthrough | 4 | $30 | $120 |
| **Note:** Mobile adapters have built-in USB-C passthrough for charging while outputting HDMI | | | | |
| **IR Extension Cables** | 2m, 3.5mm | 16 | $10 | $160 |
| **Ethernet Cables** | Cat6a, 2m | 2 | $8 | $16 |
| **Cable Management** | Breakout panels + organizers | 1 | $120 | $120 |
| **Rack Labels** | Device labels (DEV-001-016) | 1 | $40 | $40 |
| **Subtotal Cables** | | | | **$704** |

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
| Cables & Accessories | $704 |
| Live Monitor System (Splitters + Matrix + Screen) | $707 |
| **Total Infrastructure** | **$14,038** |
| **Cost per device slot** | **$877** (16 slots) |

### With Devices (Turnkey Demo)

| Category | Cost |
|----------|------|
| Infrastructure | $14,038 |
| 4 STBs | $516 |
| 4 Mobile Devices | $2,396 |
| **Total Complete** | **$16,950** |

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
│ U10│🖥️ SERVER (continued)             │    │ U10│ HDMI IN: [1-4] ← from splitters │
├────┼──────────────────────────────────┤    ├────┼──────────────────────────────────┤
│ U9 │🖥️ SERVER (continued)             │    │ U9 │ HDMI IN: [5-8] ← from splitters │
├────┼──────────────────────────────────┤    ├────┼──────────────────────────────────┤
│ U8 │📡 NETWORK + 🎬 MATRIX (1U)      │    │ U8 │[8× RJ45] [Matrix: 16×1 HDMI]   │
├────┼──────────────────────────────────┤    ├────┼──────────────────────────────────┤
│ U7 │🔌 USB HUB + IR CONTROLLER        │    │ U7 │[10× USB3.0] [IR: 16 outputs]    │
├────┼──────────────────────────────────┤    ├────┼──────────────────────────────────┤
│ U6 │🔋 UPS (CyberPower 1500VA - 2U)   │    │ U6 │[Battery Bay] [AC Input] [AC Out] │
├────┼──────────────────────────────────┤    ├────┼──────────────────────────────────┤
│ U5 │🔋 UPS (continued)                │    │ U5 │[AC Outlets: Server + Network]    │
├────┼──────────────────────────────────┤    ├────┼──────────────────────────────────┤
│ U4 │📦 CABLE BREAKOUT (16× HDMI)      │    │ U4 │[16× HDMI] → To devices on desk │
├────┼──────────────────────────────────┤    ├────┼──────────────────────────────────┤
│ U3 │📦 CABLE MGMT + 🔀 SPLITTERS      │    │ U3 │[16× HDMI Splitters] ┬→Capture  │
│    │   (16× splitters mounted here)    │    │    │ Device→Split       └→Matrix    │
├────┼──────────────────────────────────┤    ├────┼──────────────────────────────────┤
│ U2 │📦 CABLE MANAGEMENT (Routing)     │    │ U2 │[D-Ring Organizers] [Airflow]    │
├────┼──────────────────────────────────┤    ├────┼──────────────────────────────────┤
│ U1 │🔌 PDU (Metered, 8 outlets)       │    │ U1 │[AC Input] → [Outlets: 1-8]      │
└────┴──────────────────────────────────┘    └────┴──────────────────────────────────┘
  ↑ Bottom (Floor Level)                       ↑ Bottom

External Equipment (On desk near rack):
├── 📱 4× STBs (HDMI out → Breakout U4 → Splitter U3)
├── 📱 4× Mobiles (USB-C → HDMI adapter → Breakout U4 → Splitter U3)
└── 🌐 8× Web devices (no physical hardware)

ON TOP OF RACK:
📺 15.6" Monitor (shows selected device, 0ms latency from matrix U8)

SIGNAL FLOW:
┌─ STBs:    Device HDMI → Breakout (U4) → Splitter (U3) → ┬→ Capture (U10-U11)
│                                                           └→ Matrix (U8) → Monitor
│
└─ Mobiles: Device USB-C → Adapter (USB-C input, HDMI out) → Breakout (U4) → Splitter (U3) → Same split
            └─ USB-C passthrough on adapter → USB Hub (U7) for charging + ADB

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