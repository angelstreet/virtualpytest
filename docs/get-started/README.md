# Getting Started with VirtualPyTest

VirtualPyTest is a comprehensive testing automation platform that consists of three main components:

- **Frontend**: React-based web interface for managing tests and monitoring
- **Backend Server**: API server for test orchestration and data management  
- **Backend Host**: Hardware interface for device control and test execution

## 🚀 Quick Start Options

Choose your deployment strategy:

### 🏠 [Local Development Setup](./local-setup.md)
Perfect for development and testing. All components run on your local machine with hardware access.

### ☁️ [Cloud + Local Hybrid Setup](./cloud-setup.md)  
Production-ready setup with frontend on Vercel, server on Render, and local host for hardware control.

### 🗄️ [Database Setup (Supabase)](./supabase-setup.md)
Required for both local and cloud setups. Set up your PostgreSQL database on Supabase.

## 📋 Prerequisites

- **Node.js** 18+ and npm
- **Python** 3.8+ 
- **Git**
- **Supabase account** (for database)

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│    Frontend     │    │ Backend Server  │    │  Backend Host   │
│   (React/TS)    │◄──►│   (Flask/Py)    │◄──►│   (Flask/Py)    │
│                 │    │                 │    │                 │
│ • Test UI       │    │ • API Routes    │    │ • Device Control│
│ • Monitoring    │    │ • Test Logic    │    │ • Hardware I/O  │
│ • Config        │    │ • Data Storage  │    │ • Verification  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 ▼
                    ┌─────────────────┐
                    │    Supabase     │
                    │   (PostgreSQL)  │
                    │                 │
                    │ • Test Data     │
                    │ • Configurations│
                    │ • Results       │
                    └─────────────────┘
```

## 🎯 Recommended Setup Path

1. **Start with Database**: [Set up Supabase](./supabase-setup.md) first
2. **Choose your path**:
   - For development: [Local Setup](./local-setup.md)
   - For production: [Cloud Setup](./cloud-setup.md)

## 🔗 Next Steps

After setup, explore these features:
- Device management and configuration
- Test automation and execution
- Real-time monitoring and analytics
- Custom controller implementations

## 🆘 Need Help?

- Check the [troubleshooting section](../TROUBLESHOOTING.md)
- Review [architecture documentation](../ARCHITECTURE_REDESIGN.md)
- See [implementation guides](../) for specific features 