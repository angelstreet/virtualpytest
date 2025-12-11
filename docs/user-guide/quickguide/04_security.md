# Quick Guide: Security

## Overview
This guide covers security best practices for VirtualPytest deployment, including authentication, network security, and system hardening.

## Security Architecture

### Security Layers

```
┌───────────────────────────────────────────────────┐
│                 VirtualPytest Security              │
├───────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────┐    ┌─────────┐  │
│  │  Network    │    │  System     │    │  Data    │  │
│  │  Security   │    │  Hardening  │    │  Security │  │
│  └─────────────┘    └─────────────┘    └─────────┘  │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────┐  │
│  │  Auth        │    │  Monitoring │    │  Backup  │  │
│  │  & Access    │    │  & Logging  │    │  & Recovery│  │
│  └─────────────┘    └─────────────┘    └─────────┘  │
└───────────────────────────────────────────────────┘
```

## Network Security

### Firewall Configuration

```bash
# Install and configure UFW
sudo apt install ufw
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow essential ports only
sudo ufw allow 22/tcp       # SSH (consider changing port)
sudo ufw allow 80/tcp       # HTTP
sudo ufw allow 443/tcp      # HTTPS
sudo ufw allow 3000/tcp     # Frontend (internal only)
sudo ufw allow 8000/tcp     # Backend Server (internal only)
sudo ufw allow 5000/tcp     # Backend Host (internal only)

# Enable firewall
sudo ufw enable
sudo ufw status verbose
```

### Fail2Ban Configuration

```bash
# Install Fail2Ban
sudo apt install fail2ban

# Configure jail
sudo nano /etc/fail2ban/jail.local
```

Example configuration:
```ini
[DEFAULT]
bantime = 1h
findtime = 10m
maxretry = 3

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3

[nginx-badbots]
enabled = true
port = http,https
filter = nginx-badbots
logpath = /var/log/nginx/error.log
maxretry = 2
```

```bash
# Restart Fail2Ban
sudo systemctl restart fail2ban
sudo systemctl enable fail2ban
```

## Authentication and Access Control

### User Management

```bash
# Create dedicated user
sudo adduser virtualpytest --system --no-create-home

# Add to necessary groups
sudo usermod -aG sudo,dialout,plugdev,video virtualpytest

# Set up SSH keys
sudo mkdir /home/virtualpytest/.ssh
sudo chown virtualpytest:virtualpytest /home/virtualpytest/.ssh
sudo chmod 700 /home/virtualpytest/.ssh
```

### SSH Hardening

```bash
# Edit SSH configuration
sudo nano /etc/ssh/sshd_config
```

Recommended settings:
```
Port 2222
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
X11Forwarding no
AllowUsers virtualpytest
MaxAuthTries 3
LoginGraceTime 30
ClientAliveInterval 300
ClientAliveCountMax 2
```

```bash
# Restart SSH service
sudo systemctl restart sshd
```

## System Hardening

### System Updates

```bash
# Configure automatic updates
sudo apt install unattended-upgrades
sudo dpkg-reconfigure unattended-upgrades

# Edit configuration
sudo nano /etc/apt/apt.conf.d/50unattended-upgrades
```

Enable automatic updates:
```
Unattended-Upgrade::Allowed-Origins {
    "${distro_id}:${distro_codename}-security";
    "${distro_id}:${distro_codename}-updates";
};
Unattended-Upgrade::Automatic-Reboot "true";
Unattended-Upgrade::Automatic-Reboot-Time "02:00";
```

### File System Security

```bash
# Set secure permissions
sudo chmod 700 /boot
sudo chmod 600 /boot/grub/grub.cfg

# Configure umask
sudo nano /etc/login.defs
```

Set umask:
```
UMASK 027
```

### Kernel Hardening

```bash
# Edit sysctl configuration
sudo nano /etc/sysctl.conf
```

Add security settings:
```
# Network security
net.ipv4.conf.all.rp_filter=1
net.ipv4.conf.default.rp_filter=1
net.ipv4.conf.all.accept_source_route=0
net.ipv4.conf.default.accept_source_route=0

# TCP/IP stack hardening
net.ipv4.tcp_syncookies=1
net.ipv4.conf.all.accept_redirects=0
net.ipv4.conf.default.accept_redirects=0
net.ipv6.conf.all.accept_redirects=0
net.ipv6.conf.default.accept_redirects=0

# Memory protection
vm.mmap_rnd_bits=32
vm.mmap_rnd_compat_bits=16

# ASLR
kernel.randomize_va_space=2
```

```bash
# Apply sysctl settings
sudo sysctl -p
```

## Application Security

### Environment Variables

```bash
# Secure environment files
sudo chmod 600 .env
sudo chown virtualpytest:virtualpytest .env

# Never commit .env files to version control
echo ".env" >> .gitignore
```

### Database Security

```bash
# Secure PostgreSQL
sudo -u postgres psql
```

SQL commands:
```sql
-- Create secure user
CREATE USER virtualpytest_user WITH PASSWORD 'strong_password';

-- Grant minimal privileges
GRANT CONNECT ON DATABASE virtualpytest TO virtualpytest_user;
GRANT USAGE ON SCHEMA public TO virtualpytest_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO virtualpytest_user;

-- Revoke public privileges
REVOKE ALL ON DATABASE virtualpytest FROM public;
```

```bash
# Edit pg_hba.conf
sudo nano /etc/postgresql/14/main/pg_hba.conf
```

Secure configuration:
```
# TYPE  DATABASE        USER            ADDRESS                 METHOD
local   all             all                                     peer
host    all             all             127.0.0.1/32            md5
host    all             all             ::1/128                 md5
host    virtualpytest    virtualpytest_user  192.168.1.0/24         md5
```

```bash
# Restart PostgreSQL
sudo systemctl restart postgresql
```

## Monitoring and Logging

### Log Configuration

```bash
# Configure rsyslog
sudo nano /etc/rsyslog.conf
```

Enable remote logging:
```
module(load="imtcp")
input(type="imtcp" port="514")
```

```bash
# Restart rsyslog
sudo systemctl restart rsyslog
```

### Audit Logging

```bash
# Install auditd
sudo apt install auditd

# Configure audit rules
sudo nano /etc/audit/rules.d/audit.rules
```

Example rules:
```
-w /etc/passwd -p wa -k identity
-w /etc/shadow -p wa -k identity
-w /etc/group -p wa -k identity
-w /etc/sudoers -p wa -k privilege_escalation
-w /var/log/auth.log -p wa -k log_access
-w /home/virtualpytest/ -p wa -k user_access
```

```bash
# Restart auditd
sudo systemctl restart auditd
sudo systemctl enable auditd
```

## Backup and Recovery

### Database Backup

```bash
# Create backup script
sudo nano /usr/local/bin/pg_backup.sh
```

Example script:
```bash
#!/bin/bash
BACKUP_DIR="/backups/postgresql"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR
pg_dump -U virtualpytest_user -d virtualpytest -F c -f $BACKUP_DIR/virtualpytest_$DATE.dump

# Keep last 7 backups
find $BACKUP_DIR -type f -name "*.dump" -mtime +7 -delete
```

```bash
# Make executable
sudo chmod +x /usr/local/bin/pg_backup.sh

# Create cron job
sudo crontab -e
```

Add cron entry:
```
0 2 * * * /usr/local/bin/pg_backup.sh
```

### File System Backup

```bash
# Install backup tools
sudo apt install rsync

# Create backup script
sudo nano /usr/local/bin/system_backup.sh
```

Example script:
```bash
#!/bin/bash
BACKUP_DIR="/backups/system"
SOURCE_DIR="/Users/cpeengineering/virtualpytest"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR
rsync -a --delete $SOURCE_DIR $BACKUP_DIR/virtualpytest_$DATE/

# Keep last 3 backups
find $BACKUP_DIR -type d -name "virtualpytest_*" -mtime +3 -exec rm -rf {} \;
```

```bash
# Make executable
sudo chmod +x /usr/local/bin/system_backup.sh

# Create cron job
sudo crontab -e
```

Add cron entry:
```
30 2 * * * /usr/local/bin/system_backup.sh
```

## Security Testing

### Vulnerability Scanning

```bash
# Install security tools
sudo apt install lynis rkhunter clamav

# Run Lynis audit
sudo lynis audit system

# Run rkhunter
sudo rkhunter --check

# Update ClamAV and scan
sudo freshclam
sudo clamscan -r /home/virtualpytest/
```

### Penetration Testing

```bash
# Install Nikto for web scanning
sudo apt install nikto

# Scan web interfaces
nikto -h http://localhost:3000
nikto -h http://localhost:8000
nikto -h http://localhost:5000
```

## Incident Response

### Incident Response Plan

1. **Containment**: Isolate affected systems
2. **Eradication**: Remove malicious code/access
3. **Recovery**: Restore from clean backups
4. **Analysis**: Determine root cause
5. **Prevention**: Implement fixes and monitoring

### Emergency Procedures

```bash
# Lock down system
sudo ufw deny all

# Disable user accounts
sudo usermod -L suspicious_user

# Kill suspicious processes
sudo pkill -9 suspicious_process

# Restore from backup
sudo systemctl stop virtualpytest-server
sudo systemctl stop virtualpytest-host
sudo rsync -a /backups/system/virtualpytest_20231115_023000/ /Users/cpeengineering/virtualpytest/
sudo systemctl start virtualpytest-server
sudo systemctl start virtualpytest-host
```

## Security Checklist

### Pre-Deployment Checklist

- [ ] Change all default passwords
- [ ] Configure firewall with minimal required ports
- [ ] Set up SSH key authentication only
- [ ] Disable root SSH access
- [ ] Configure automatic security updates
- [ ] Set up database with secure credentials
- [ ] Configure proper file permissions
- [ ] Set up monitoring and alerting
- [ ] Create backup strategy and test restoration
- [ ] Conduct security audit

### Regular Maintenance Checklist

- [ ] Review system logs daily
- [ ] Update all software packages weekly
- [ ] Test backups monthly
- [ ] Review user accounts and permissions quarterly
- [ ] Conduct security audit quarterly
- [ ] Test incident response plan annually

## Next Steps

After security configuration:
1. Test all security measures
2. Document security procedures
3. Train team on security policies
4. Set up monitoring and alerting
5. Conduct regular security audits
