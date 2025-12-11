# QuickGuide 1: Hardware Setup

> **Purpose**: Physical infrastructure requirements for VirtualPyTest  
> **Audience**: DevOps, QA Engineers, System Administrators

---

## Overview

VirtualPyTest supports two deployment models based on scale:

| Model | Devices | Use Case | Cost |
|-------|---------|----------|------|
| **Standalone** | 1-4 | Dev, POC, small QA team | $300-800 |
| **Production** | 16-320+ | Enterprise, device farms, 24/7 ops | $14k-350k |

---

## Part A: Standalone Setup

### Use Cases
- Local development and testing
- Proof of concept
- Small QA teams (1-4 devices)
- Home lab / learning environment

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    STANDALONE HOST                          │
│         (Raspberry Pi 4/5 / Mini PC / Linux Desktop)        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│   │ Flask API   │  │ VNC Server  │  │   FFmpeg    │        │
│   │ Port 6109   │  │ Port 5900   │  │  Capture    │        │
│   └──────┬──────┘  └──────┬──────┘  └──────┬──────┘        │
│          └────────────────┴────────────────┘                │
│                           │                                 │
│              Hardware Abstraction Layer                     │
│                           │                                 │
│   ┌─────────┬─────────┬─────────┬─────────┐                │
│   │USB/ADB  │  HDMI   │ GPIO/IR │ Network │                │
│   │Capture  │ Capture │ Control │ Control │                │
│   └────┬────┴────┬────┴────┬────┴────┬────┘                │
└────────┼─────────┼─────────┼─────────┼──────────────────────┘
         │         │         │         │
    ┌────┴───┐ ┌───┴───┐ ┌───┴───┐ ┌───┴────┐
    │ Mobile │ │  STB  │ │  STB  │ │ Smart  │
    │  ADB   │ │ HDMI  │ │  IR   │ │  Plug  │
    └────────┘ └───────┘ └───────┘ └────────┘
```

### Host Options

| Host Type | Specs | Best For | Price |
|-----------|-------|----------|-------|
| **Raspberry Pi 5** | 8GB RAM, ARM64 | Portable, low power | $80 |
| **Raspberry Pi 4** | 4-8GB RAM, ARM64 | Budget option | $55-75 |
| **Mini PC** | Intel N100, 16GB RAM | Performance | $150-300 |
| **Linux Desktop** | Any modern x64 | Max performance | Existing |

**Minimum Requirements:**
- 4GB RAM (8GB recommended)
- 32GB storage (SSD preferred)
- USB 3.0 ports
- Gigabit Ethernet

### Hardware Components

| Component | Purpose | Model Example | Price |
|-----------|---------|---------------|-------|
| **USB Capture Card** | HDMI video input | Elgato Cam Link 4K | $100 |
| **USB Hub** | Expand ports + power | Anker 10-Port USB 3.0 | $50 |
| **IR Blaster** (optional) | STB remote control | FLIRC USB | $25 |
| **USB-C to HDMI** | Mobile video output | Anker USB-C Hub | $30 |

### Connectivity Guide

#### STB (Set-Top Box) via HDMI
```
STB ──[HDMI]──► USB Capture Card ──[USB 3.0]──► Host
                     │
              Video to VirtualPyTest
```

#### STB via IR Control
```
Host ──[USB]──► IR Blaster ~~[IR Signal]~~► STB
                                    │
                           Remote Control Commands
```

#### Mobile Device via ADB
```
Mobile ──[USB-C]──► USB Hub ──[USB 3.0]──► Host
    │                                  │
    └── Charging ────────────────────┘
    └── ADB Control + Screen Mirror ──┘
```

#### Mobile Device via HDMI (for video capture)
```
Mobile ──[USB-C]──► USB-C Hub ──[HDMI]──► Capture Card ──► Host
                        │
                   [USB-C PD]
                        │
                    Charging
```

### Bill of Materials (Standalone)

#### Minimum Setup (1-2 devices): ~$300
| Item | Qty | Price | Total |
|------|-----|-------|-------|
| Raspberry Pi 5 (8GB) | 1 | $80 | $80 |
| Power Supply (27W) | 1 | $15 | $15 |
| MicroSD Card (64GB) | 1 | $15 | $15 |
| USB Capture Card | 1 | $100 | $100 |
| USB Hub (powered) | 1 | $50 | $50 |
| HDMI Cable | 2 | $10 | $20 |
| Ethernet Cable | 1 | $10 | $10 |
| **Total** | | | **$290** |

#### Recommended Setup (3-4 devices): ~$600
| Item | Qty | Price | Total |
|------|-----|-------|-------|
| Mini PC (Intel N100) | 1 | $200 | $200 |
| USB Capture Card | 2 | $100 | $200 |
| USB 3.0 Hub (10-port) | 1 | $50 | $50 |
| IR Blaster (FLIRC) | 1 | $25 | $25 |
| USB-C to HDMI Adapter | 2 | $30 | $60 |
| HDMI Cables | 4 | $10 | $40 |
| Ethernet Cable | 1 | $10 | $10 |
| **Total** | | | **$585** |

---

## Part B: Production Setup

### Use Cases
- Enterprise QA departments
- Device testing farms
- 24/7 monitoring operations
- Multi-team shared infrastructure

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PRODUCTION DEPLOYMENT                               │
│                        (2-Rack Modular Design)                              │
└─────────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────┐         ┌─────────────────────────┐
  │      RACK A             │         │      RACK B             │
  │    COMPUTE ONLY         │         │    DEVICES ONLY         │
  │                         │         │                         │
  │  ┌───────────────────┐  │         │  ┌───────────────────┐  │
  │  │ Server #1 (4U)    │  │  HDMI   │  │ STB Shelf (4U)    │  │
  │  │ 16 capture inputs │──┼────────►│  │ 4× STBs           │  │
  │  │ 4 USB ports       │  │         │  └───────────────────┘  │
  │  │ 16 IR outputs     │  │         │                         │
  │  └───────────────────┘  │         │  ┌───────────────────┐  │
  │                         │  USB    │  │ Mobile Shelf (2U) │  │
  │  ┌───────────────────┐  │────────►│  │ 4× Mobiles        │  │
  │  │ Server #2 (4U)    │  │         │  └───────────────────┘  │
  │  │ 16 capture inputs │  │         │                         │
  │  └───────────────────┘  │   IR    │  ┌───────────────────┐  │
  │         ...             │~~~~~~~~~►  │ STB Shelf (4U)    │  │
  │  ┌───────────────────┐  │         │  │ 4× STBs           │  │
  │  │ Server #5 (4U)    │  │         │  └───────────────────┘  │
  │  │ 16 capture inputs │  │         │         ...             │
  │  └───────────────────┘  │         │                         │
  │                         │         │  Total: 80 devices      │
  │  ┌───────────────────┐  │         │  (60 STBs + 20 Mobile)  │
  │  │ Network Switch    │  │         │                         │
  │  │ 10GbE Core        │  │         │  ┌───────────────────┐  │
  │  └───────────────────┘  │         │  │ PDU + Power       │  │
  │                         │         │  └───────────────────┘  │
  │  ┌───────────────────┐  │         │                         │
  │  │ UPS + PDU         │  │         │                         │
  │  └───────────────────┘  │         │                         │
  └─────────────────────────┘         └─────────────────────────┘
         42U Rack                            42U Rack
```

### Why 2-Rack Design?

| Benefit | Description |
|---------|-------------|
| **Separation** | Expensive compute vs cheap device storage |
| **Scalability** | Add rack pairs: 80 → 160 → 240 → 320+ |
| **Flexibility** | Change device mix without touching compute |
| **Serviceability** | Access servers without disturbing devices |

### Server Specifications

**Per Server (5 total for 80 devices):**

| Component | Specification | Purpose |
|-----------|---------------|---------|
| **Model** | Supermicro AS-1114S-WN10RT | Datacenter-grade |
| **CPU** | AMD EPYC 7313P (16c/32t) | Processing power |
| **RAM** | 128GB DDR4 ECC | VM headroom |
| **Storage** | 2× 2TB NVMe (RAID1) | Reliability |
| **Network** | 2× 10GbE + 4× 1GbE | Bandwidth |
| **PCIe** | 8 slots | Capture cards |
| **Form** | 4U Rackmount | Density |
| **Price** | $6,000 | Per unit |

### Capture & Control Hardware

| Component | Model | Qty/80 | Unit Price | Total |
|-----------|-------|--------|------------|-------|
| **HDMI Capture** | Magewell Quad HDMI | 20 | $1,295 | $25,900 |
| **HDMI Splitter** | OREI HD-102 (1×2) | 80 | $18 | $1,440 |
| **HDMI Matrix** | OREI HMA-161 (16×1) | 5 | $299 | $1,495 |
| **USB Controller** | StarTech PEXUSB3S44V | 5 | $150 | $750 |
| **USB Hub** | Anker PowerPort 10 | 5 | $50 | $250 |
| **IR Controller** | Global Caché iTach IP2IR | 5 | $299 | $1,495 |

### Connectivity Guide (Production)

#### Signal Flow: STB with Live Monitor
```
STB ──[HDMI]──► Splitter (1×2) ──┬──► Capture Card ──► Server
                                 │
                                 └──► Matrix (16×1) ──► Live Monitor
```

#### Signal Flow: Mobile Device
```
Mobile ──[USB-C]──► Adapter ──┬──[HDMI]──► Splitter ──► Capture
                              │
                              └──[USB-C PD]──► USB Hub ──► Server (ADB)
```

#### IR Control Path
```
Server ──[Ethernet]──► iTach IP2IR ──[IR Cable]──► STB IR Receiver
```

### Network Infrastructure

| Component | Model | Qty | Price |
|-----------|-------|-----|-------|
| **Core Switch** | Arista 7050TX-48 (10GbE) | 1 | $8,000 |
| **Access Switch** | Netgear GS728TP (PoE+) | 2 | $700 |

**Port Allocation:**
- 10GbE: Server uplinks (5 ports)
- 1GbE: Management, IR controllers, devices

### Power & Cooling

| Component | Model | Qty | Price |
|-----------|-------|-----|-------|
| **PDU (Compute)** | Tripp Lite 32A Metered | 2 | $900 |
| **PDU (Devices)** | Tripp Lite 15A Metered | 2 | $598 |
| **UPS** | CyberPower 3000VA 2U | 2 | $1,600 |

**Power Budget:**
- Idle: ~1,600W
- Active: ~4,300W
- UPS Runtime: 15 min at full load

### Bill of Materials (Production - 80 Devices)

#### Infrastructure Summary

| Category | Cost |
|----------|------|
| Servers (5×) | $30,000 |
| Capture Cards | $25,900 |
| HDMI (Splitters + Matrix) | $2,935 |
| USB + IR Controllers | $2,495 |
| Network | $8,700 |
| Power (PDU + UPS) | $3,098 |
| Cable Management | $2,440 |
| Device Shelves | $3,500 |
| Racks (2× 42U) | $3,600 |
| Cables & Accessories | $4,270 |
| **Total Infrastructure** | **$87,738** |

#### Cost Analysis

| Metric | Value |
|--------|-------|
| Cost per device slot | $1,097 |
| Monthly electricity (~$0.10/kWh) | $216 |
| Break-even vs BrowserStack | <1 month |
| Annual savings vs cloud | $960k - $1.9M |

### Scaling Path

| Phase | Devices | Racks | Servers | Cost |
|-------|---------|-------|---------|------|
| **Demo** | 16 | 1 | 1 | $14k |
| **Phase 1** | 80 | 2 | 5 | $88k |
| **Phase 2** | 160 | 4 | 10 | $175k |
| **Phase 3** | 240 | 6 | 15 | $263k |
| **Phase 4** | 320 | 8 | 20 | $350k |

**Formula:** +2 racks = +80 devices = +$87k

---

## Appendix

### A. Supported Device Types

| Type | Connection | Control Method | Video Capture |
|------|------------|----------------|---------------|
| **Android Mobile** | USB | ADB | USB/HDMI |
| **Android TV** | Network/USB | ADB | HDMI |
| **Apple TV** | Network | Shortcuts/IR | HDMI |
| **Roku** | Network | ECP API | HDMI |
| **Fire TV** | USB/Network | ADB | HDMI |
| **Generic STB** | IR | IR Blaster | HDMI |
| **Smart TV** | Network | Varies | HDMI |
| **Web Browser** | N/A | Selenium | Virtual |

### B. Hardware Compatibility

#### USB Capture Cards (Tested)
| Brand | Model | Inputs | Max Resolution | Price |
|-------|-------|--------|----------------|-------|
| Magewell | Quad HDMI | 4 | 4K@30fps | $1,295 |
| Elgato | Cam Link 4K | 1 | 4K@30fps | $100 |
| AVerMedia | Live Gamer | 1 | 1080p@60fps | $150 |
| Generic | HDMI to USB3 | 1 | 1080p@30fps | $20 |

#### IR Controllers (Tested)
| Brand | Model | Ports | Interface | Price |
|-------|-------|-------|-----------|-------|
| Global Caché | iTach IP2IR | 3 | Ethernet | $100 |
| FLIRC | USB IR | 1 | USB | $25 |

### C. Rack Layout Reference

#### Production Rack A (Compute) - 42U
```
U42-41: Network Switch (2U)
U40-37: Server #1 (4U)
U36-33: Server #2 (4U)
U32-29: Server #3 (4U)
U28-25: Server #4 (4U)
U24-21: Server #5 (4U)
U20-19: Cable Management (2U)
U18-15: UPS #1 (4U)
U14-11: UPS #2 (4U)
U10-09: PDU #1 (2U)
U08-07: PDU #2 (2U)
U06-01: Cable Management + Spare
```

#### Demo Rack (12U Standalone)
```
U12-09: Server (4U)
U08: Network Switch (1U)
U07: USB Hub + IR Controller (1U)
U06-05: UPS (2U)
U04: Cable Breakout (1U)
U03-02: Cable Management (2U)
U01: PDU (1U)
```

---

## Quick Reference

### Standalone Checklist
- [ ] Host machine (Pi/Mini PC/Desktop)
- [ ] USB capture card(s)
- [ ] USB hub (powered)
- [ ] HDMI cables
- [ ] Network connection
- [ ] Optional: IR blaster

### Production Checklist
- [ ] 2× 42U racks
- [ ] 5× Servers with capture cards
- [ ] Network switch (10GbE)
- [ ] IR controllers
- [ ] PDUs + UPS
- [ ] Cable management
- [ ] Device shelves

---

**Next:** [QuickGuide 2: Network Setup](./quickguide-network.md)