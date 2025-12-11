# Quick Guide: Network Configuration

## Overview
This guide covers network configuration requirements for VirtualPytest components to communicate effectively.

## Network Architecture

### Basic Topology
```
[Client Devices] → [Network] → [VirtualPytest Server] → [Host Machines]
                          ↓
                     [Database]
                          ↓
                     [Grafana]
```

### Port Requirements

| Component | Port | Protocol | Description |
|-----------|------|----------|-------------|
| Frontend | 3000 | HTTP/HTTPS | Web interface |
| Backend Server | 8000 | HTTP/HTTPS | API server |
| Backend Host | 5000 | HTTP/HTTPS | Device control |
| Grafana | 3001 | HTTP/HTTPS | Monitoring dashboard |
| PostgreSQL | 5432 | TCP | Database |
| VNC | 5900-5999 | TCP | Remote control |
| NoVNC | 6080 | HTTP | Web-based VNC |
| HLS Stream | 8080 | HTTP | Video streaming |

## Network Configuration Steps

### 1. Static IP Configuration

```bash
# Ubuntu/Debian with netplan
sudo nano /etc/netplan/01-netcfg.yaml
```

Example configuration:
```yaml
network:
  version: 2
  renderer: networkd
  ethernets:
    eth0:
      dhcp4: no
      addresses: [192.168.1.100/24]
      gateway4: 192.168.1.1
      nameservers:
        addresses: [8.8.8.8, 8.8.4.4, 1.1.1.1]
```

Apply configuration:
```bash
sudo netplan apply
```

### 2. Firewall Configuration

```bash
# Install and enable UFW
sudo apt install ufw
sudo ufw enable

# Allow required ports
sudo ufw allow 22/tcp       # SSH
sudo ufw allow 80/tcp       # HTTP
sudo ufw allow 443/tcp      # HTTPS
sudo ufw allow 3000/tcp     # Frontend
sudo ufw allow 8000/tcp     # Backend Server
sudo ufw allow 5000/tcp     # Backend Host
sudo ufw allow 3001/tcp     # Grafana
sudo ufw allow 5432/tcp     # PostgreSQL
sudo ufw allow 5900:5999/tcp # VNC
sudo ufw allow 6080/tcp     # NoVNC
sudo ufw allow 8080/tcp     # HLS Stream

# Check status
sudo ufw status verbose
```

### 3. DNS Configuration

```bash
# Edit resolv.conf
sudo nano /etc/resolv.conf
```

Add nameservers:
```
nameserver 8.8.8.8
nameserver 8.8.4.4
nameserver 1.1.1.1
```

### 4. Hostname Configuration

```bash
# Set hostname
sudo hostnamectl set-hostname virtualpytest-server

# Edit hosts file
sudo nano /etc/hosts
```

Add entry:
```
127.0.0.1   virtualpytest-server localhost
192.168.1.100 virtualpytest-server
```

## Network Security

### VPN Configuration (Optional)

```bash
# Install WireGuard
sudo apt install wireguard

# Generate keys
wg genkey | sudo tee /etc/wireguard/privatekey
sudo chmod go= /etc/wireguard/privatekey

# Create configuration
sudo nano /etc/wireguard/wg0.conf
```

Example WireGuard config:
```ini
[Interface]
PrivateKey = <server-private-key>
Address = 10.0.0.1/24
ListenPort = 51820

[Peer]
PublicKey = <client-public-key>
AllowedIPs = 10.0.0.2/32
```

### SSL/TLS Configuration

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d yourdomain.com

# Auto-renewal
sudo certbot renew --dry-run
```

## Network Troubleshooting

### Common Issues

1. **Port Conflicts**: Check with `netstat -tuln` or `ss -tuln`
2. **Firewall Blocking**: Check UFW status and rules
3. **DNS Resolution**: Test with `dig` or `nslookup`
4. **Network Latency**: Use `ping` and `traceroute`

### Diagnostic Commands

```bash
# Check network interfaces
ip a

# Check routing table
ip route

# Test connectivity
ping google.com

# Check open ports
netstat -tuln

# Test specific port
nc -zv 192.168.1.100 8000

# Check DNS resolution
dig google.com
nslookup google.com

# Network speed test
speedtest-cli
```

## Network Performance Optimization

### Quality of Service (QoS)

```bash
# Install tc for traffic control
sudo apt install iproute2

# Limit bandwidth for specific interface
sudo tc qdisc add dev eth0 root tbf rate 100mbit burst 32kbit latency 400ms
```

### Network Buffer Tuning

```bash
# Increase TCP buffer sizes
sudo sysctl -w net.core.rmem_max=16777216
sudo sysctl -w net.core.wmem_max=16777216
sudo sysctl -w net.core.rmem_default=16777216
sudo sysctl -w net.core.wmem_default=16777216
```

## Next Steps

After network configuration:
1. Verify all ports are accessible
2. Test connectivity between components
3. Configure SSL/TLS for secure communication
4. Proceed to software installation
