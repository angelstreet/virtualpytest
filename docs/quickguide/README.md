# VirtualPyTest QuickGuides

> **Fast-track deployment guides for VirtualPyTest**

---

## Guides

| Guide | Description |
|-------|-------------|
| **[1. Hardware Setup](./01_hardware.md)** | Physical infrastructure, compute hosts, capture cards, device connectivity |
| **[2. Network Setup](./02_network.md)** | Network topology, firewall rules, SSL/TLS, remote access |
| **[3. Software Setup](./03_software.md)** | Stack installation, Docker deployment, environment configuration |
| **[4. Security Setup](./04_security.md)** | TLS certificates, secrets management, authentication, hardening |

---

## Quick Start

### Standalone (Local Development)
```bash
git clone https://github.com/angelstreet/virtualpytest.git
cd virtualpytest
./setup/docker/standalone_server_host/launch.sh
```
**Access:** http://localhost:3000

### Production (Cloud/Enterprise)
```bash
cd setup/docker/hetzner_custom
cp config.env.example config.env  # Edit configuration
./setup.sh && ./launch.sh
```

**See full deployment instructions in [Software Setup](./03_software.md)**

---

## Deployment Comparison

| | Standalone | Production |
|---|---|---|
| **Scale** | 1-4 devices | 80-320+ devices |
| **Hardware** | RPi/Mini PC (~$300) | Servers + racks (~$87k/80 devices) |
| **Network** | Single LAN | VLANs + 10GbE |
| **Database** | Local PostgreSQL | Supabase |
| **SSL** | Optional | Let's Encrypt required |

---

## Documentation

- 📖 [Full Documentation](../README.md)
- 🔧 [Technical Guides](../technical/)
- 🔐 [Security Details](../security/)
- 🐛 [Report Issues](https://github.com/angelstreet/virtualpytest/issues)

---

**License:** MIT