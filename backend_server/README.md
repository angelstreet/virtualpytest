# VirtualPyTest Backend Server

Main API server handling client requests and orchestration for VirtualPyTest framework.

## 🚀 **Quick Deploy to Render**

**TL;DR**: Use Docker deployment with these settings:
- **Environment**: Docker (NOT Python)
- **Root Directory**: Empty
- **Dockerfile Path**: `backend_server/Dockerfile`
- **Port**: 5109

## 🎯 **Purpose**

backend_server provides the central API layer that coordinates between the frontend interface and backend_host hardware controllers. It handles business logic, user management, test orchestration, and serves as the communication hub for the entire system.

## 🔧 **Installation**

```bash
# Install dependencies
pip install -r requirements.txt

# Run the service
python src/app.py
```

**Note**: Both `shared` and `backend_core` are included via PYTHONPATH in Docker deployments. For local development, ensure the project structure is maintained.

## 🌐 **API Endpoints**

### System Management
- `GET /api/health` - Health check
- `GET /api/system/info` - System information
- `GET /api/system/status` - Overall system status

### Test Management
- `GET /api/testcases` - List test cases
- `POST /api/testcases` - Create test case
- `PUT /api/testcases/<id>` - Update test case
- `DELETE /api/testcases/<id>` - Delete test case

### Campaign Management
- `GET /api/campaigns` - List campaigns
- `POST /api/campaigns` - Create campaign
- `PUT /api/campaigns/<id>` - Update campaign
- `DELETE /api/campaigns/<id>` - Delete campaign

### Host Coordination
- `GET /api/hosts` - List registered hosts
- `POST /api/hosts/register` - Register new host
- `POST /api/hosts/<id>/execute` - Execute command on host

### Recording & Media
- `POST /server/rec/getRestartImages` - Get restart timeline images
- `GET /server/rec/stream/<host>` - Proxy stream from host

### Web Interface
- `GET /server/web/*` - Frontend asset serving
- `WebSocket /socket.io` - Real-time updates

## 🏗️ **Architecture**

```
backend_server (Multi-Service Container)
├── Flask Application (Port 5109)
│   ├── REST API Routes (/api/*)
│   ├── WebSocket Handlers (Socket.IO)
│   ├── Business Logic Services
│   ├── Host Communication Layer
│   └── Database Layer (Supabase PostgreSQL)
├── Grafana Service (Port 3000)
│   ├── PostgreSQL Datasource
│   ├── VirtualPyTest Dashboards
│   ├── System Health Monitoring
│   └── Real-time Metrics & Alerts
└── Supervisor Process Manager
    ├── Flask Process Control
    ├── Grafana Process Control
    └── Health Check Coordination
```

## 🔧 **Configuration**

### Environment Variables

Copy the project-level environment template:

```bash
# Copy project-level template (from project root)
cp .env.example .env

# Edit with your values
nano .env
```

Required environment variables (see project root `.env.example`):

```bash
# Server Configuration
SERVER_PORT=5109
SERVER_URL=http://localhost:5109
CORS_ORIGINS=http://localhost:3000

# Database (Supabase PostgreSQL)
NEXT_PUBLIC_SUPABASE_URL=your_supabase_project_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
DATABASE_URL=postgresql://postgres:password@db.project-id.supabase.co:5432/postgres

# Grafana Configuration
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=admin123
GRAFANA_SECRET_KEY=your_grafana_secret_key

# External Services
CLOUDFLARE_R2_ENDPOINT=your_r2_endpoint
OPENROUTER_API_KEY=your_openrouter_key
FLASK_SECRET_KEY=your_flask_secret
```

## 📊 **Grafana Monitoring**

backend_server includes integrated Grafana monitoring for real-time insights into your VirtualPyTest system.

### Features

- **System Overview Dashboard**: Test execution trends, campaign performance, device status
- **System Health Dashboard**: Database status, active alerts, error rates, device connectivity
- **Real-time Metrics**: Live monitoring with 30-second refresh intervals
- **PostgreSQL Integration**: Direct connection to your Supabase database
- **Custom Dashboards**: Pre-configured dashboards for VirtualPyTest metrics

### Access Grafana

After deployment, access Grafana at:

```bash
# Local development
http://localhost:3000

# Render deployment
https://your-app-name.onrender.com:3000
```

**Default Login**:
- Username: `admin`
- Password: `admin123` (change via `GRAFANA_ADMIN_PASSWORD`)

### Available Dashboards

1. **VirtualPyTest - System Overview**
   - Test execution trends over time
   - Active campaigns and connected devices
   - Test results distribution (success/failure)
   - Average execution times
   - Campaign performance metrics

2. **VirtualPyTest - System Health**  
   - Database connectivity status
   - Active alerts and error rates
   - Device status table
   - Alert trends and system health metrics

### Database Connection

Grafana automatically connects to your Supabase PostgreSQL database using:

```yaml
# Provisioned datasource configuration
datasources:
  - name: VirtualPyTest PostgreSQL
    type: postgres
    url: ${DATABASE_URL}
    database: postgres
    sslmode: require
```

### Custom Queries

Example queries for building custom dashboards:

```sql
-- Test execution success rate over time
SELECT
  $__timeGroupAlias(created_at,$__interval),
  COUNT(CASE WHEN status = 'completed' THEN 1 END)::numeric / 
  NULLIF(COUNT(*), 0) * 100 as "Success Rate %"
FROM test_executions
WHERE $__timeFilter(created_at)
GROUP BY 1 ORDER BY 1;

-- Device connectivity status
SELECT 
  name as "Device",
  status as "Status",
  updated_at as "Last Updated"
FROM device 
ORDER BY updated_at DESC;

-- Campaign performance metrics
SELECT 
  c.name as "Campaign",
  COUNT(te.id) as "Total Tests",
  COUNT(CASE WHEN te.status = 'completed' THEN 1 END) as "Completed"
FROM campaigns c
LEFT JOIN test_executions te ON c.id = te.campaign_id
GROUP BY c.id, c.name;
```

### Troubleshooting Grafana

```bash
# Check Grafana logs
docker logs <container_id> | grep grafana

# Verify database connection
curl http://localhost:3000/api/datasources/proxy/1/api/health

# Reset Grafana admin password
docker exec -it <container_id> grafana-cli admin reset-admin-password newpassword
```

## 🚀 **Deployment**

### Render Deployment (Recommended)

**IMPORTANT**: This project requires Docker deployment due to system dependencies (NoVNC, graphics libraries, multi-directory structure).

#### Step-by-Step Render Docker Deployment:

1. **Create New Web Service** on Render dashboard
2. **Connect Repository**: Link your GitHub repo to Render
3. **Configure Service Settings**:
   - **Environment**: Select **"Docker"** (NOT Python)
   - **Region**: Choose your preferred region
   - **Branch**: `dev` (or your deployment branch)
   - **Root Directory**: Leave **EMPTY** (uses project root)
   - **Dockerfile Path**: `backend_server/Dockerfile`

4. **Environment Variables**: Set these in Render dashboard:
```bash
# Required Render environment variables
SERVER_PORT=5109
SERVER_URL=https://your-app-name.onrender.com
CORS_ORIGINS=https://virtualpytest.vercel.app
DEBUG=false
RENDER=true

# Database connection (Supabase)
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_key
DATABASE_URL=postgresql://postgres:password@db.project-id.supabase.co:5432/postgres

# Grafana monitoring
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=your_secure_password
GRAFANA_SECRET_KEY=your_grafana_secret_key
GRAFANA_DOMAIN=virtualpytest.onrender.com
GF_SERVER_DOMAIN=virtualpytest.onrender.com
GF_SERVER_ROOT_URL=https://virtualpytest.onrender.com/grafana/
GF_SERVER_PROTOCOL=https

# Optional: Add your API keys
OPENROUTER_API_KEY=your_openrouter_key
FLASK_SECRET_KEY=your_flask_secret
```

5. **Deploy**: Click "Create Web Service" - Render will build and deploy automatically

#### Why Docker is Required:
- ✅ **System Dependencies**: NoVNC, graphics libraries (libGL, Xvfb)
- ✅ **Multi-Directory Structure**: Needs `shared/`, `backend_core/`, `backend_server/`
- ✅ **Python Package Management**: Complex dependency resolution
- ✅ **Consistent Environment**: Same setup across dev/staging/prod

#### Troubleshooting Render Deployment:
- **Build fails**: Ensure "Docker" environment is selected, not "Python"
- **Wrong paths**: Root Directory should be empty, Dockerfile Path should be `backend_server/Dockerfile`
- **Port issues**: Ensure SERVER_PORT=5109 is set in environment variables

### Docker Deployment
```bash
# Build image
docker build -f Dockerfile -t virtualpytest/backend_server .

# Run container with both Flask and Grafana ports
docker run -d \
  -p 5109:5109 \
  -p 3000:3000 \
  -e SERVER_URL=http://localhost:5109 \
  -e CORS_ORIGINS=http://localhost:3000 \
  -e DATABASE_URL=postgresql://postgres:password@db.project-id.supabase.co:5432/postgres \
  -e GRAFANA_ADMIN_USER=admin \
  -e GRAFANA_ADMIN_PASSWORD=admin123 \
  virtualpytest/backend_server
```

**Access Services**:
- Flask API: http://localhost:5109
- Grafana Dashboard: http://localhost:3000

### Local Deployment
```bash
# Development mode
DEBUG=true python src/app.py

# Production mode (with gunicorn)
gunicorn -w 2 -b 0.0.0.0:5109 src.app:app
```

### Systemd Service (Local Server)
```bash
# Install service
sudo cp ../deployment/systemd/backend_server.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable backend_server
sudo systemctl start backend_server

# Check status
sudo systemctl status backend_server
sudo journalctl -u backend_server -f
```

## 🌐 **Host Communication**

### Host Registration
backend_server maintains a registry of available hosts:

```python
# Host registration data
{
    "host_name": "sunri-pi2",
    "host_url": "http://sunri-pi2:6109",
    "capabilities": ["mobile", "desktop", "av", "power"],
    "status": "available",
    "last_ping": "2024-01-15T10:30:00Z"
}
```

### Request Proxying
Proxies requests to appropriate hosts:

```python
# Client request to backend_server
POST /api/hosts/sunri-pi2/execute
{
    "action": "tap",
    "x": 100,
    "y": 200
}

# backend_server proxies to backend_host
POST http://sunri-pi2:6109/host/remote/executeAction
{
    "action": "tap", 
    "x": 100,
    "y": 200
}
```

### Load Balancing
- Distributes requests across available hosts
- Health monitoring and failover
- Capability-based routing

## 🔄 **Business Logic**

### Test Orchestration
```python
from backend_server.services.test_orchestrator import TestOrchestrator

orchestrator = TestOrchestrator()
result = orchestrator.execute_test_case(
    test_case_id="test123",
    host_id="sunri-pi2",
    device_id="device1"
)
```

### Campaign Management
```python
from backend_server.services.campaign_manager import CampaignManager

manager = CampaignManager()
campaign = manager.create_campaign({
    "name": "Regression Suite",
    "test_cases": ["test1", "test2", "test3"],
    "schedule": "daily"
})
```

### Data Validation
- Request/response validation using Pydantic
- Input sanitization and security
- Error handling and logging

## 🧪 **Testing**

### Health Check
```bash
curl http://localhost:5109/api/health
```

### API Testing
```bash
# List test cases
curl http://localhost:5109/api/testcases

# Create test case
curl -X POST http://localhost:5109/api/testcases \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Case 1", "steps": [...]}'

# Execute on host
curl -X POST http://localhost:5109/api/hosts/sunri-pi2/execute \
  -H "Content-Type: application/json" \
  -d '{"action": "tap", "x": 100, "y": 200}'
```

### Integration Tests
```bash
# Run API tests
python -m pytest tests/api/

# Run integration tests
python -m pytest tests/integration/

# Load testing
python -m pytest tests/load/
```

## 📊 **Monitoring**

### Health Monitoring
- Service health endpoints
- Host availability tracking
- Database connection monitoring
- External service status

### Metrics & Logging
```python
# Structured logging
import structlog
logger = structlog.get_logger()

logger.info("test_execution_started", 
           test_case_id="test123",
           host_id="sunri-pi2")
```

### Performance Monitoring
- Response time tracking
- Request rate monitoring
- Error rate analysis
- Resource usage metrics

## 🔐 **Security**

### Authentication
```python
from backend_server.middleware.auth import require_auth

@app.route('/api/protected')
@require_auth
def protected_endpoint():
    return {"message": "Access granted"}
```

### CORS Configuration
```python
from flask_cors import CORS

CORS(app, origins=[
    "http://localhost:3000",
    "https://your-frontend.vercel.app"
])
```

### Input Validation
```python
from pydantic import BaseModel

class TestCaseRequest(BaseModel):
    name: str
    description: str
    steps: List[TestStep]
```

## 🔧 **Development**

### Adding New Endpoints
```python
# In src/routes/new_feature_routes.py
from flask import Blueprint

new_feature_bp = Blueprint('new_feature', __name__, url_prefix='/api/feature')

@new_feature_bp.route('/', methods=['GET'])
def list_features():
    return {"features": []}

# Register in src/app.py
app.register_blueprint(new_feature_routes.new_feature_bp)
```

### Database Integration
```python
# Using shared configuration
from shared.lib.config.settings import shared_config

db_config = shared_config.database
```

### WebSocket Events
```python
from flask_socketio import emit

@socketio.on('test_status_update')
def handle_test_update(data):
    emit('test_progress', data, broadcast=True)
```

## 🚀 **Scaling**

### Horizontal Scaling
- Multiple backend_server instances
- Load balancer configuration
- Session management

### Database Scaling
- Connection pooling
- Read replicas
- Caching strategies

### Host Management
- Dynamic host registration
- Auto-scaling hosts
- Geographic distribution

## 🔧 **Troubleshooting**

### Common Issues

#### Port Conflicts
```bash
# Check port usage
sudo netstat -tlnp | grep :5109

# Kill conflicting process
sudo kill -9 <PID>
```

#### Host Communication
```bash
# Test host connectivity
curl http://sunri-pi2:6109/host/health

# Check host registration
curl http://localhost:5109/api/hosts
```

#### CORS Issues
```bash
# Check CORS configuration
curl -H "Origin: http://localhost:3000" \
     -H "Access-Control-Request-Method: POST" \
     -H "Access-Control-Request-Headers: X-Requested-With" \
     -X OPTIONS \
     http://localhost:5109/api/testcases
```

### Service Recovery
```bash
# Restart service
sudo systemctl restart backend_server

# View logs
sudo journalctl -u backend_server -f

# Clear cache/sessions
rm -rf /tmp/backend_server-*
```

## 📋 **Requirements**

### System Requirements
- Python 3.8+
- 1GB+ RAM
- Network connectivity to hosts
- Database access (if applicable)

### Dependencies
See `requirements.txt` for full list:
- **Flask**: Web framework
- **Gunicorn**: WSGI server
- **Requests**: HTTP client
- **Pydantic**: Data validation
- **StructLog**: Structured logging

## 🤝 **Contributing**

1. Add new API endpoints in `src/routes/`
2. Implement business logic in `src/services/`
3. Add middleware in `src/middleware/`
4. Update API documentation
5. Add comprehensive tests 