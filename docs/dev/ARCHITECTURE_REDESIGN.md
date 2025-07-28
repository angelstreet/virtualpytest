# VirtualPyTest Architecture Redesign

## Overview

This document outlines the new microservices-based architecture for VirtualPyTest, designed to separate concerns, enable Docker containerization, and improve maintainability.

## Current Problems

- Mixed responsibilities in single codebase
- Web components and device controllers intermingled
- Difficult to scale individual components
- Complex dependencies between UI and hardware layers
- Hard to deploy and maintain

## New Architecture

### Component Separation

```
virtualpytest/
├── shared/                    # Shared libraries and utilities
├── backend_core/              # Core Python logic (device controllers)
├── backend_server/            # Flask API server (business logic)
├── backend_host/              # Flask host controller (hardware interface)
├── frontend/                  # React UI application
└── docker/                    # Container orchestration
```

## Component Responsibilities

### 1. Shared (`shared/`)

**Purpose**: Common libraries used across all backend services

**Contents**:

- Configuration management
- Data models and schemas
- Utility functions
- Custom exceptions
- System constants

**Key Files**:

```
shared/lib/
├── config/settings.py         # Shared configuration
├── models/test_models.py      # Test case data models
├── utils/db_utils.py          # Database utilities
└── exceptions/custom_exceptions.py
```

**Dependencies**: None (base package)

---

### 2. Backend Core (`backend_core/`)

**Purpose**: Pure Python business logic and device controllers

**Contents**:

- Device controllers (desktop, mobile, A/V, network)
- Test execution services
- Automation logic
- Controller management

**Key Files**:

```
backend_core/src/
├── controllers/               # Device control logic
│   ├── base_controller.py
│   ├── controller_manager.py
│   ├── desktop/               # Desktop automation
│   ├── mobile/                # Mobile device control
│   └── audiovideo/            # A/V controllers
├── services/                  # Business services
│   ├── test_execution_service.py
│   └── automation_service.py
└── interfaces/                # Abstract interfaces
```

**Dependencies**: `shared`

---

### 3. Backend Server (`backend_server/`)

**Purpose**: Main API server handling client requests and orchestration

**Contents**:

- REST API endpoints
- WebSocket handling
- Authentication/authorization
- Request orchestration
- Client-facing business logic

**Route Categories**:

```
/api/testcases          # Test case management
/api/campaigns          # Test campaign operations
/api/execution          # Test execution control
/api/users              # User management
/api/teams              # Team/tenant management
/api/hosts              # Host coordination
```

**Key Files**:

```
backend_server/src/
├── routes/
│   ├── test_routes.py         # Test management endpoints
│   ├── campaign_routes.py     # Campaign operations
│   ├── execution_routes.py    # Test execution
│   └── proxy_routes.py        # Proxy to host services
├── middleware/                # Flask middleware
├── websockets/                # Real-time communication
└── serializers/               # API data serialization
```

**Dependencies**: `shared`, calls `backend_host` via HTTP

---

### 4. Backend Host (`backend_host/`)

**Purpose**: Direct hardware interface and device management

**Contents**:

- Device-specific routes
- Hardware abstraction
- System monitoring
- Device discovery
- Direct file system access

**Route Categories**:

```
/host/rec               # Recording/capture operations (your current routes)
/host/device            # Direct device control
/host/hardware          # Hardware management
/host/health            # System health monitoring
/host/discovery         # Device detection
```

**Key Files**:

```
backend_host/src/
├── routes/
│   ├── host_rec_routes.py     # Image capture (your current file)
│   ├── device_control_routes.py
│   ├── hardware_routes.py
│   └── system_health_routes.py
├── services/
│   ├── host_manager.py        # Host system management
│   └── device_discovery.py    # Device enumeration
└── agents/                    # Device-specific agents
```

**Dependencies**: `shared`, `backend_core`

---

### 5. Frontend (`frontend/`)

**Purpose**: React-based user interface

**Contents**:

- React components
- UI state management
- API service layer
- User experience

**Key Files**:

```
frontend/src/
├── components/                # React components
│   ├── dashboard/
│   ├── test-management/
│   └── device-control/
├── services/
│   ├── api.ts                 # Main API client
│   ├── testService.ts         # Test management API
│   └── deviceService.ts       # Device control API
└── pages/                     # Page components
```

**Dependencies**: Calls `backend_server` via HTTP/WebSocket

## Route Distribution

### Current Route: `host_rec_routes.py`

**Current Location**: `src/web/routes/host_rec_routes.py`
**New Location**: `backend_host/src/routes/host_rec_routes.py`

**Rationale**:

- Direct file system access (`capture_folder`)
- Device controller interaction (`get_controller`)
- Host-specific operations
- Hardware-level functionality

### Route Categories by Service

#### Backend Server Routes (Client-facing)

```python
# User and system management
/api/users              # User management
/api/teams              # Team operations
/api/auth               # Authentication

# Test management
/api/testcases          # Test case CRUD
/api/campaigns          # Campaign management
/api/execution          # Test execution orchestration

# System coordination
/api/hosts              # Host management
/api/monitoring         # System-wide monitoring
```

#### Backend Host Routes (Hardware-facing)

```python
# Device operations
/host/devices           # Device enumeration and control
/host/rec               # Recording and capture (your routes)
/host/hardware          # Hardware management

# System operations
/host/health            # Host system health
/host/discovery         # Device discovery
/host/files             # File system operations
```

## Communication Flow

### Request Flow Example: List Restart Images

```
1. Frontend → GET /api/restart/images?device_id=device1
2. backend_server receives request
3. backend_server validates and proxies to backend_host
4. backend_server → POST /host/rec/listRestartImages
5. backend_host processes device-specific logic
6. backend_host returns image data
7. backend_server formats response for frontend
8. backend_server → Response to frontend
```

### Data Flow

```
Frontend ←→ backend_server ←→ backend_host ←→ Hardware/Devices
   ↑              ↑              ↑
   UI         Business        Hardware
 Logic         Logic          Interface
```

## Benefits

### 1. Separation of Concerns

- **UI Logic**: Isolated in frontend
- **Business Logic**: Centralized in backend_server
- **Hardware Logic**: Isolated in backend_host
- **Shared Logic**: Reusable in shared libraries

### 2. Scalability

- Scale UI and API independently
- Multiple host controllers for different hardware
- Load balance API servers
- Independent deployment cycles

### 3. Development

- Teams can work on different services
- Clear interfaces and contracts
- Independent testing and debugging
- Technology flexibility per service

### 4. Deployment

- Docker containerization per service
- Independent versioning
- Rollback capabilities per component
- Environment-specific configurations

## Docker Strategy

### Service Containers

```yaml
# Individual service containers
backend_server: # API and business logic
backend_host: # Hardware interface
frontend: # UI application
shared: # Shared libraries volume
```

### Development Environment

```bash
# Start all services
docker-compose -f docker/docker-compose.dev.yml up

# Start individual services
docker-compose up backend_server
docker-compose up backend_host
docker-compose up frontend
```

### Production Environment

```bash
# Production deployment
docker-compose -f docker/docker-compose.prod.yml up -d

# With load balancing and scaling
docker-compose up --scale backend_server=3
```

## Migration Benefits

1. **Maintainability**: Clear component boundaries
2. **Testability**: Isolated testing per service
3. **Deployability**: Independent deployments
4. **Scalability**: Component-level scaling
5. **Development**: Parallel team development
6. **Technology**: Service-specific tech choices

## Next Steps

See `MIGRATION_GUIDE.md` for detailed step-by-step migration instructions.
