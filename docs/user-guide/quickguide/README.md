# VirtualPytest Quick Guides

This directory contains focused, concise guides for setting up and securing VirtualPytest.

## Available Guides

### 1. [Linux Hardware and Devices](01_linux_hardware_devices.md)
Covers hardware requirements, supported devices, and performance optimization for Linux systems running VirtualPytest.

**Topics:**
- Minimum and recommended hardware specifications
- Raspberry Pi and server configurations
- USB device permissions and udev rules
- Network interface configuration
- Performance tuning (CPU, memory, disk I/O)

### 2. [Network Configuration](02_network_configuration.md)
Provides network setup instructions for VirtualPytest components to communicate effectively.

**Topics:**
- Network architecture and port requirements
- Static IP configuration
- Firewall setup with UFW
- DNS and hostname configuration
- VPN setup with WireGuard
- SSL/TLS configuration with Certbot
- Network troubleshooting

### 3. [Software Stack](03_software_stack.md)
Comprehensive guide to the VirtualPytest software components and their installation.

**Topics:**
- Software architecture overview
- Frontend (React/TypeScript) installation
- Backend Server (FastAPI) setup
- Backend Host (Python) configuration
- Supporting services (PostgreSQL, Grafana, Redis)
- Systemd service management
- Software update procedures

### 4. [Security](04_security.md)
Best practices for securing your VirtualPytest deployment.

**Topics:**
- Network security (firewall, Fail2Ban)
- Authentication and access control
- System hardening (updates, file permissions, kernel settings)
- Application security (environment variables, database security)
- Monitoring and logging setup
- Backup and recovery strategies
- Security testing and incident response

## Usage Recommendations

1. **Start with Hardware**: Begin with the [Linux Hardware and Devices](01_linux_hardware_devices.md) guide to ensure your system meets requirements.

2. **Configure Network**: Proceed to [Network Configuration](02_network_configuration.md) to set up proper networking.

3. **Install Software**: Follow the [Software Stack](03_software_stack.md) guide for component installation.

4. **Secure Deployment**: Finally, implement security measures from the [Security](04_security.md) guide.

## Quick Start

For a rapid deployment:

```bash
# 1. Set up hardware (follow guide 1)
# 2. Configure network (follow guide 2)
# 3. Install software stack
cd /Users/cpeengineering/virtualpytest
./setup/install_all.sh

# 4. Apply security measures (follow guide 4)
```

## Additional Resources

- [Main Documentation](../README.md)
- [Getting Started](../../get-started/README.md)
- [Technical Documentation](../../technical/README.md)

## Contributing

To contribute to these guides:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

Please ensure all code examples are tested and documentation is clear and concise.
