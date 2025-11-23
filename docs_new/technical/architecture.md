# VirtualPyTest Architecture

**High-level system design for developers and system administrators.**

---

## 🎯 **System Overview**

VirtualPyTest uses a **microservices architecture** with clear separation of concerns:

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
                                 │
                    ┌─────────────────┐
                    │  Backend Core   │
                    │ (Shared Library)│
                    │                 │
                    │ • Controllers   │
                    │ • Services      │
                    │ • Interfaces    │
                    └─────────────────┘
```

---

## 🏗️ **Component Architecture**

### Frontend (React TypeScript)
**Purpose**: Web-based user interface
- **Technology**: React 18, TypeScript, Material-UI, Vite
- **Deployment**: Static files (Vercel, Nginx)
- **Communication**: REST API + WebSocket to Backend Server

**Key Features**:
- Device management interface
- Test execution dashboard
- Real-time monitoring
- Campaign configuration

### Backend Server (Flask Python)
**Purpose**: API orchestration and business logic
- **Technology**: Flask, Gunicorn, SQLAlchemy
- **Deployment**: Docker container (Render, local)
- **Database**: PostgreSQL (Supabase)

**Key Features**:
- REST API endpoints
- WebSocket real-time updates
- Test orchestration
- Host coordination
- Grafana integration

### Backend Host (Flask Python)
**Purpose**: Hardware interface and device control
- **Technology**: Flask, device drivers, system libraries
- **Deployment**: Docker on hardware (Pi, local machine)
- **Hardware Access**: USB, video capture, GPIO

**Key Features**:
- Direct device control
- Hardware abstraction
- Screenshot capture
- Power management

### Backend Core (Python Library)
**Purpose**: Shared business logic and device controllers
- **Technology**: Pure Python, no web dependencies
- **Deployment**: Imported by other services
- **Structure**: Controllers, Services, Interfaces

**Key Features**:
- Device controller implementations
- Navigation pathfinding
- Test execution logic
- Verification services

### Shared Library (Python)
**Purpose**: Common utilities and configuration
- **Technology**: Python utilities, configuration management
- **Deployment**: Imported by all Python services
- **Structure**: Config, Models, Utils

**Key Features**:
- Environment configuration
- Data models
- Validation utilities
- Constants and exceptions

---

## 🔄 **Data Flow**

### Test Execution Flow
```
1. User creates test via Frontend
2. Frontend sends request to Backend Server
3. Backend Server finds available Backend Host
4. Backend Server sends execution request to Backend Host
5. Backend Host uses Backend Core controllers
6. Backend Host executes test on physical device
7. Results flow back: Host → Server → Frontend
8. Screenshots and logs stored for analysis
```

### Real-Time Monitoring Flow
```
1. Backend Host captures device state/screenshots
2. Backend Host sends updates to Backend Server
3. Backend Server stores metrics in database
4. Grafana queries database for dashboard updates
5. Frontend receives WebSocket updates
6. User sees real-time status in web interface
```

---

## 📊 **Database Design**

### Core Tables
- **devices**: Physical device configurations
- **hosts**: Available host machines
- **test_cases**: Test definitions
- **campaigns**: Test campaign configurations
- **test_executions**: Test run history
- **navigation_trees**: Device UI navigation maps
- **screenshots**: Captured images and metadata

### Relationships
```
campaigns (1) → (N) test_executions
test_executions (1) → (N) screenshots
devices (1) → (N) test_executions
hosts (1) → (N) test_executions
navigation_trees (1) → (N) devices
```

---

## 🌐 **API Architecture**

### REST API Endpoints
**Backend Server** exposes these endpoint categories:
- `/api/system/*` - System health and information
- `/api/testcases/*` - Test case CRUD operations
- `/api/campaigns/*` - Campaign management
- `/api/hosts/*` - Host registration and coordination
- `/api/devices/*` - Device configuration
- `/api/executions/*` - Test execution management

### WebSocket Events
**Real-time communication** for:
- Test execution progress
- Device status updates
- System health notifications
- Alert broadcasts

### Host Communication
**Backend Server ↔ Backend Host**:
- Host registration and heartbeat
- Test execution requests
- Status updates and results
- Screenshot and log transfer

---

## 🔧 **Deployment Architecture**

### Local Development
```
Docker Compose Environment:
├── frontend:3000          # React dev server
├── backend_server:5109    # Flask API + Grafana
├── backend_host:6109      # Hardware interface
└── shared volumes         # Code and data sharing
```

### Production Deployment
```
Hybrid Cloud + Local:
├── Frontend (Vercel)      # Static React app
├── Backend Server (Render) # API + Grafana
├── Backend Host (Local Pi) # Hardware control
└── Database (Supabase)    # PostgreSQL
```

### Container Architecture
```
backend_server container:
├── Flask application (port 5109)
├── Grafana service (port 3001)
├── Supervisor process manager
└── Shared volumes (backend_host, shared)

backend_host container:
├── Flask application (port 6109)
├── VNC server (port 5900)
├── NoVNC web interface (port 6080)
└── Hardware device access (/dev/*)
```

---

## 🔒 **Security Architecture**

### Authentication & Authorization
- **API Keys**: Service-to-service communication
- **CORS**: Frontend-backend communication
- **Environment Variables**: Sensitive configuration
- **Network Isolation**: Docker container networking

### Data Protection
- **Encrypted Storage**: Sensitive configuration data
- **Secure Communication**: HTTPS/WSS in production
- **Access Control**: Role-based permissions
- **Audit Logging**: Security event tracking

---

## ⚡ **Performance Architecture**

### Scalability Patterns
- **Horizontal Host Scaling**: Multiple Backend Host instances
- **Load Balancing**: Request distribution across hosts
- **Caching**: Configuration and navigation tree caching
- **Async Processing**: Non-blocking test execution

### Resource Management
- **Connection Pooling**: Database connections
- **Memory Management**: Screenshot and log cleanup
- **CPU Optimization**: Efficient image processing
- **Storage Management**: Automated cleanup policies

---

## 🔄 **Integration Architecture**

### External Services
- **Supabase**: PostgreSQL database hosting
- **Cloudflare R2**: Object storage for screenshots
- **OpenRouter**: AI service integration
- **Grafana**: Monitoring and alerting

### Hardware Integration
- **USB Devices**: Android ADB, iOS tools
- **Video Capture**: HDMI capture cards, cameras
- **Network Devices**: Smart plugs, IoT devices
- **Serial/GPIO**: Direct hardware control

---

## 📈 **Monitoring Architecture**

### Metrics Collection
```
Application Metrics:
├── Test execution statistics
├── Device performance data
├── System resource usage
└── Error rates and patterns

Infrastructure Metrics:
├── Container resource usage
├── Network connectivity
├── Database performance
└── External service health
```

### Alerting Strategy
- **Threshold-based**: Numeric metric alerts
- **Anomaly Detection**: Pattern-based alerts
- **Composite Alerts**: Multiple condition alerts
- **Escalation Policies**: Multi-level notifications

---

## 🔧 **Development Architecture**

### Code Organization
```
Project Structure:
├── frontend/              # React TypeScript app
├── backend_server/        # API orchestration service
├── backend_host/          # Hardware interface service
├── backend_host/          # Shared business logic library
├── shared/               # Common utilities library
├── docker/               # Container orchestration
└── docs_new/             # Documentation
```

### Build & Deployment Pipeline
- **Frontend**: Vite build → Static files → CDN
- **Backend Services**: Docker build → Container registry → Deploy
- **Libraries**: Python package → Import in services
- **Documentation**: Markdown → Static site generation

---

## 🎯 **Design Principles**

### Microservices Benefits
- **Separation of Concerns**: Each service has single responsibility
- **Technology Diversity**: Best tool for each job
- **Independent Scaling**: Scale components based on load
- **Fault Isolation**: Service failures don't cascade

### Shared Library Strategy
- **Code Reuse**: Common logic in backend_host and shared
- **Consistency**: Same interfaces across services
- **Maintainability**: Single source of truth for business logic
- **Testing**: Isolated unit testing of core functionality

---

**Want to understand specific components? Check our [Components Documentation](components/)!** 🔧
