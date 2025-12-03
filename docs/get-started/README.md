# Getting Started with VirtualPyTest

Welcome! Choose your setup path based on your needs.

---

## 🚀 Quick Start (Recommended)

**Just want to try it?** Use Docker for instant setup.

➡️ **[Quick Start with Docker](./quickstart.md)** (5 minutes)

Perfect for:
- First-time users
- Quick evaluation
- Demo purposes
- Simple standalone deployment

---

## 🏠 Local Development Setup

**Want to develop or customize?** Run everything locally.

➡️ **[Local Development Setup](./local-setup.md)** (30 minutes)

Perfect for:
- Contributing to the project
- Custom development
- Full control over components
- Debugging and testing

---

## ☁️ Cloud Deployment

**Need production-ready deployment?** Use our hybrid cloud setup.

➡️ **[Cloud Deployment Guide](./cloud-setup.md)** (1 hour)

Perfect for:
- Production environments
- Team collaboration
- Scalable infrastructure
- 24/7 monitoring

---

## 🗄️ Database Setup

**All setups require a database.** We use Supabase (PostgreSQL).

➡️ **[Supabase Setup Guide](./supabase-setup.md)** (15 minutes)  
➡️ **[Supabase Auth Setup](./supabase-auth-setup.md)** (Optional)

---

## Architecture Overview

VirtualPyTest consists of three main components:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│    Frontend     │    │ Backend Server  │    │  Backend Host   │
│   (React/TS)    │◄──►│   (Flask/Py)    │◄──►│   (Flask/Py)    │
│                 │    │                 │    │                 │
│ • Web UI        │    │ • API Routes    │    │ • Device Control│
│ • Dashboard     │    │ • Test Logic    │    │ • Hardware I/O  │
│ • Monitoring    │    │ • Data Storage  │    │ • Verification  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 ▼
                    ┌─────────────────┐
                    │    Supabase     │
                    │   (PostgreSQL)  │
                    └─────────────────┘
```

---

## Prerequisites

All setups require:

- **Python** 3.8 or higher
- **Node.js** 18 or higher
- **Git**
- **Supabase account** (free tier works)

Optional (for Docker setup):
- **Docker** & **Docker Compose**

---

## What's Next?

After setup, explore:

- ❓ **[FAQ](../faq/README.md)** - Common questions answered
- 📖 **[Features](../features/README.md)** - See what you can do
- 📚 **[User Guide](../user-guide/README.md)** - Learn how to use it
- 🔧 **[Technical Docs](../technical/README.md)** - Understand how it works
- 🔌 **[Integrations](../integrations/README.md)** - Connect external tools

---

## Need Help?

- 🐛 [Report Issues](https://github.com/angelstreet/virtualpytest/issues)
- 💬 [Community Discussions](https://github.com/angelstreet/virtualpytest/discussions)
- 📖 [Troubleshooting](../user-guide/troubleshooting.md)

