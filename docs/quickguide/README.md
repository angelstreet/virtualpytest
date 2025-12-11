# VirtualPyTest QuickGuides

> **Fast-track deployment guides for VirtualPyTest**  
> From standalone dev setup to production-scale device farms

---

## Overview

These QuickGuides provide concise, actionable instructions for deploying VirtualPyTest across different environments and scales.

| Guide | Focus | Time |
|-------|-------|------|
| [1. Hardware](./quickguide-hardware.md) | Physical infrastructure | 15 min |
| [2. Network](./quickguide-network.md) | Connectivity & routing | 15 min |
| [3. Software](./quickguide-software.md) | Installation & services | 20 min |
| [4. Security](./quickguide-security.md) | Hardening & secrets | 15 min |

---

## Quick Start Paths

### 🏠 Standalone (Development/POC)

**1-4 devices, single host, local network**

```
Hardware → Raspberry Pi or Mini PC (~$300)
Network  → Single LAN, UFW firewall
Software → docker-compose standalone
Security → API keys, local HTTPS optional
```

**Start here:**
1. [Hardware: Part A](./quickguide-hardware.md#part-a-standalone-setup)
2. [Software: Part B](./quickguide-software.md#part-b-standalone-deployment)

---

### 🏢 Production (Enterprise)

**16-320+ devices, multi-server, datacenter**

```
Hardware → 2-rack design, Magewell capture (~$87k for 80 devices)
Network  → VLANs, 10GbE, firewall rules
Software → Hetzner/Proxmox deployment, Supabase
Security → TLS, RLS, VPN, secrets rotation
```

**Start here:**
1. [Hardware: Part B](./quickguide-hardware.md#part-b-production-setup)
2. [Network: Part B](./quickguide-network.md#part-b-production-network)
3. [Software: Part C](./quickguide-software.md#part-c-production-deployment)
4. [Security: Full Guide](./quickguide-security.md)

---

## Guide Summaries

### [1. Hardware Setup](./quickguide-hardware.md)

Physical infrastructure for device testing.

| Topic | Standalone | Production |
|-------|------------|------------|
| Host | RPi 5 / Mini PC | Supermicro EPYC servers |
| Capture | USB capture card | Magewell Quad HDMI |
| Control | FLIRC IR / USB | Global Caché iTach |
| Scale | 1-4 devices | 80-320+ devices |
| Cost | $300-800 | $87k per 80 devices |

---

### [2. Network Setup](./quickguide-network.md)

Connectivity, routing, and remote access.

| Topic | Standalone | Production |
|-------|------------|------------|
| Topology | Single LAN | 3 VLANs (Compute/Device/Mgmt) |
| Firewall | UFW basics | Inter-VLAN rules |
| SSL | Optional | Let's Encrypt required |
| Remote | ngrok / Tailscale | Cloudflare Tunnel / VPN |

**Key Ports:** 3000 (UI), 5109 (API), 6109+ (Hosts), 6080 (VNC)

---

### [3. Software Setup](./quickguide-software.md)

Application stack and deployment.

| Component | Technology | Port |
|-----------|------------|------|
| Frontend | React + Vite | 3000 |
| Backend Server | Flask + Gunicorn | 5109 |
| Backend Host | Flask + VNC + FFmpeg | 6109+ |
| Database | PostgreSQL / Supabase | 5432 |

**Deployment Options:**
- `standalone_server_host/` → Local with embedded DB
- `hetzner_custom/` → Cloud with Supabase
- `proxmox/` → VM-based scalable

---

### [4. Security Setup](./quickguide-security.md)

Hardening and secrets management.

| Layer | Implementation |
|-------|----------------|
| Transport | TLS 1.3, HTTPS, WSS |
| Network | UFW, VLANs, VPN |
| Application | API Keys, CORS, RLS |
| Secrets | .env files, rotation |
| Container | Non-root, minimal privileges |

**External Services:**
- Supabase (Row Level Security)
- Cloudflare R2 (Bucket policies)
- OpenRouter (Spending limits)
- Grafana (Auth, HTTPS)

---

## Architecture at a Glance

```
┌─────────────────────────────────────────────────────────────┐
│                     VIRTUALPYTEST                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌─────────┐    ┌─────────┐    ┌─────────┐               │
│   │Frontend │◄──►│ Server  │◄──►│  Host   │──► Devices    │
│   │ :3000   │    │ :5109   │    │ :6109+  │               │
│   └─────────┘    └─────────┘    └─────────┘               │
│                       │                                     │
│        ┌──────────────┼──────────────┐                     │
│        ▼              ▼              ▼                     │
│   ┌─────────┐   ┌─────────┐   ┌─────────┐                 │
│   │Supabase │   │   R2    │   │OpenRouter│                │
│   │   DB    │   │ Storage │   │   AI     │                │
│   └─────────┘   └─────────┘   └─────────┘                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Prerequisites Checklist

**All Deployments:**
- [ ] Linux host (Ubuntu 22.04+ recommended)
- [ ] Docker + Docker Compose
- [ ] Git

**Production Adds:**
- [ ] Domain name with DNS control
- [ ] Supabase account
- [ ] Cloudflare account (R2 storage)
- [ ] SSL certificate (Let's Encrypt)

---

## Quick Commands

```bash
# Clone
git clone https://github.com/angelstreet/virtualpytest.git
cd virtualpytest

# Standalone (local dev)
./setup/docker/standalone_server_host/launch.sh

# Production (Hetzner/Cloud)
cd setup/docker/hetzner_custom
./setup.sh
./launch.sh
```

---

## Support

- 📖 [Full Documentation](../docs/)
- 🐛 [Report Issues](https://github.com/angelstreet/virtualpytest/issues)
- 💬 [Discussions](https://github.com/angelstreet/virtualpytest/discussions)

---

**License:** MIT