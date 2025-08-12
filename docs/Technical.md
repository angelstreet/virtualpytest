# Technical Overview – VirtualPyTest

## Project Overview

VirtualPyTest is an open-source framework for automating, monitoring, and remotely controlling various devices (TVs, STBs, mobile phones, etc.). It uses a model-view-controller (MVC) architecture to abstract device interfaces and automate workflows, making it easy to scale across platforms and hardware.

---

## Architecture

VirtualPyTest is organized into modular services:

- **Backend Server**: Orchestrates automation, exposes REST APIs, handles business logic.
- **Backend Host**: Interfaces directly with hardware (IR, Bluetooth, HDMI camera, etc.), exposes device control APIs.
- **Frontend**: React/TypeScript web UI for configuration, monitoring, and remote control.
- **Shared Libraries**: Common utilities for controllers, models, and verifications.
- **Docker**: Containerization for easy deployment across environments.

**MVC Approach**:  
- **Model**: Represents the user interface (nodes/edges for STBs, UI actions for mobile, etc.).
- **View**: HDMI camera, VNC, or video stream for UI observation and verification.
- **Controller**: Abstracts device control (IR, Bluetooth, ADB, Appium, etc.).

---

## Core Technologies

- **Backend**: Python (FastAPI or similar), device drivers, REST APIs
- **Frontend**: React + TypeScript
- **Containerization**: Docker, Docker Compose
- **Supported Hardware**: Linux, Raspberry Pi (recommended), other platforms via Docker
- **Cloud Deployment**: Vercel (frontend), Render (backend), Supabase/R2 (storage)

---

## How It Works

1. **Configure Models**: Define device UI (screens, nodes, actions, verifications) via web UI.
2. **Connect Controllers**: Select/control IR, Bluetooth, ADB, Appium, etc.
3. **Set Up Views**: Choose HDMI camera, VNC, or stream for UI verification.
4. **Automation & Monitoring**: Execute tasks/tests or monitor for events (e.g., blackscreen, subtitles, freezes) using AI-powered verification modules.
5. **Alerting & Reporting**: Get automatic alerts and view reports in the UI or external dashboards (Grafana integration supported).

**Typical Workflow:**  
- User sets up device and UI model in frontend  
- Backend orchestrates control and verification via REST APIs  
- Host service interacts with hardware devices  
- Monitoring and automation tasks run continuously or on schedule

---

## Extensibility

- **Add new controllers**: Implement in backend_host and register in shared libs.
- **Add verification modules**: Extend the verification framework (image, OCR, AI, etc.).
- **Expand UI models**: Update model definitions for new device types or UI flows.
- **Integrations**: Connect with external monitoring (Grafana), cloud storage, or other APIs.

See [CONTRIBUTING.md](../CONTRIBUTING.md) for details on extending the framework.

---

## Quick Start for Developers

- **Local Setup**:  
  - Clone the repo, install dependencies (see [Quick Start Guide](./quickstart.md)), run backend and frontend.
- **Docker**:  
  - Use provided `docker-compose.yml` for complete environment.
- **Cloud**:  
  - Deploy frontend/backend using Vercel/Render/Supabase as needed.

---

## Further Documentation

- [Quick Start Guide](./quickstart.md)
- [API Reference](./api.md)
- [Configuration Guide](./config.md)
- [Contributing Guide](../CONTRIBUTING.md)

---

## Questions?

Open an issue or check our [Wiki](../wiki) for more details!