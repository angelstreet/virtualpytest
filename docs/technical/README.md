# Technical Documentation

**Deep dive into VirtualPyTest architecture and internals.**

Comprehensive technical documentation for developers, architects, and advanced users.

---

## 📐 Architecture

### System Architecture

**[Architecture Overview](./architecture/architecture.md)**

High-level system design and component interaction.

**Components:**
- **[Backend Server](./architecture/components/backend-server.md)** - API server, test orchestration
- **[Backend Host](./architecture/components/backend-host.md)** - Device control, hardware interface
- **[Frontend](./architecture/components/frontend.md)** - React web interface
- **[Shared](./architecture/components/shared.md)** - Common libraries and utilities

---

### Core Systems

**Navigation & Pathfinding:**
- **[Navigation System](./architecture/navigation.md)** - Navigation tree architecture
- **[Pathfinding](./architecture/PATHFINDING.md)** - Shortest path algorithms
- **[Navigation Metrics](./architecture/navigation_metrics.md)** - Performance tracking
- **[Node & Edges Metrics](./architecture/node_edges_metrics.md)** - Graph analytics

**Controllers:**
- **[Controller Creation Guide](./architecture/CONTROLLER_CREATION_GUIDE.md)** - Build custom controllers
- **[Direct Python Controller Usage](./architecture/DIRECT_PYTHON_CONTROLLER_USAGE.md)** - Use controllers in scripts

**Workflows:**
- **[Orchestrator Workflow](./architecture/ORCHESTRATOR_WORKFLOW.md)** - Test execution orchestration

---

### Infrastructure

**Deployment:**
- **[Deployment Guide](./architecture/deployment.md)** - Production deployment
- **[Storage Paths](./architecture/storage-paths.md)** - File organization
- **[URL Builders](./architecture/url-builders.md)** - URL construction patterns

**Integrations:**
- **[Grafana Integration](./architecture/GRAFANA_INTEGRATION.md)** - Analytics setup
- **[Appium Remote Implementation](./architecture/APPIUM_REMOTE_IMPLEMENTATION.md)** - Mobile automation

**Monitoring:**
- **[Incidents](./architecture/incidents.md)** - Incident management system
- **[AI Monitoring](./architecture/AI_MONITORING_IMPLEMENTATION.md)** - AI-powered monitoring

**Standards:**
- **[Global Naming Convention](./architecture/GLOBAL_NAMING_CONVENTION.md)** - Code style guide
- **[Z-Index Management](./architecture/Z_INDEX_MANAGEMENT.md)** - UI layering

---

## 🤖 AI Systems

### AI Architecture

**Core AI:**
- **[AI Centralization Plan](./architecture/AI_CENTRALIZATION_PLAN.md)** - AI service architecture

**AI Services:**
- **[Tree Creation](./ai/tree-creation.md)** - AI-generated navigation trees
- **[Exploration](./ai/exploration.md)** - AI-driven app exploration
- **[Builder](./ai/builder.md)** - AI test generation
- **[Detector](./ai/detector.md)** - AI content detection
- **[Detector Schema](./ai/detector-schema.md)** - Detection data models
- **[Disambiguation](./ai/disambiguation.md)** - AI element disambiguation

---

## 🔧 Development

### Development Guides

**Architecture:**
- **[Mobile Architecture](./dev/mobile-architecture.md)** - Mobile testing design
- **[Validation Improvements](./dev/validation-improvements.md)** - Enhanced validation
- **[Validation Summary](./dev/validation-summary.md)** - Validation overview

**Storage:**
- **[Storage - Audio](./dev/storage-audio.md)** - Audio file management
- **[Storage - Hot RAM](./dev/storage-hot-ram.md)** - In-memory caching

**Infrastructure:**
- **[Timezone Handling](./dev/timezone.md)** - Timezone management

---

## 🔌 MCP (Model Context Protocol)

**[MCP Overview](./mcp/README.md)**

VirtualPyTest's MCP integration provides AI-powered tools for test automation.

### MCP Tools

**Core:**
- **[MCP Core](./mcp/mcp_core.md)** - Core MCP functionality
- **[MCP Playground](./mcp/mcp_playground.md)** - Interactive MCP testing

**Test Management:**
- **[Test Case Tools](./mcp/mcp_tools_testcase.md)** - Test case operations
- **[Script Tools](./mcp/mcp_tools_script.md)** - Script management
- **[Requirements Tools](./mcp/mcp_tools_requirements.md)** - Requirements management

**Navigation:**
- **[Navigation Tools](./mcp/mcp_tools_navigation.md)** - Navigation tree operations
- **[Tree Tools](./mcp/mcp_tools_tree.md)** - Tree manipulation
- **[UI Tools](./mcp/mcp_tools_userinterface.md)** - UI interface management

**Execution:**
- **[Action Tools](./mcp/mcp_tools_action.md)** - Test actions
- **[Control Tools](./mcp/mcp_tools_control.md)** - Device control
- **[Verification Tools](./mcp/mcp_tools_verification.md)** - Result verification

**AI Services:**
- **[AI Tools](./mcp/mcp_tools_ai.md)** - AI-powered analysis
- **[Exploration Tools](./mcp/mcp_tools_exploration.md)** - AI exploration
- **[Screenshot Tools](./mcp/mcp_tools_screenshot.md)** - Screenshot analysis

---

## 🗺️ Documentation Map

### By Role

**For Architects:**
- System architecture
- Component design
- Integration patterns
- Deployment architecture

**For Backend Developers:**
- Backend Server architecture
- Backend Host architecture
- API design
- Database schema

**For Frontend Developers:**
- Frontend architecture
- Component structure
- State management
- UI/UX patterns

**For DevOps:**
- Deployment guide
- Infrastructure setup
- Monitoring integration
- Performance optimization

**For AI/ML Engineers:**
- AI systems overview
- MCP integration
- Model integration
- AI service architecture

---

## 🔍 Quick Reference

### Common Tasks

**Adding a new device controller:**
→ [Controller Creation Guide](./architecture/CONTROLLER_CREATION_GUIDE.md)

**Understanding navigation:**
→ [Navigation System](./architecture/navigation.md)

**Integrating AI features:**
→ [AI Centralization Plan](./architecture/AI_CENTRALIZATION_PLAN.md)

**Deploying to production:**
→ [Deployment Guide](./architecture/deployment.md)

**Setting up Grafana:**
→ [Grafana Integration](./architecture/GRAFANA_INTEGRATION.md)

**Using MCP tools:**
→ [MCP README](./mcp/README.md)

---

## 📚 Related Documentation

- **[Features](../features/README.md)** - What VirtualPyTest can do
- **[User Guide](../user-guide/README.md)** - How to use VirtualPyTest
- **[API Reference](../api/README.md)** - API documentation
- **[Get Started](../get-started/README.md)** - Installation
- **[Examples](../examples/README.md)** - Code examples

---

## 🤝 Contributing

Want to contribute to VirtualPyTest?

1. Read the architecture docs
2. Check [GLOBAL_NAMING_CONVENTION.md](./architecture/GLOBAL_NAMING_CONVENTION.md)
3. Follow the patterns in existing code
4. Submit a pull request!

---

## 🆘 Support

- 💬 [Technical Discussions](https://github.com/angelstreet/virtualpytest/discussions)
- 🐛 [Report Issues](https://github.com/angelstreet/virtualpytest/issues)
- 📖 [Architecture Questions](https://github.com/angelstreet/virtualpytest/discussions/categories/architecture)

---

**Ready to dive deep?**  
➡️ [System Architecture](./architecture/architecture.md)  
➡️ [MCP Overview](./mcp/README.md)

