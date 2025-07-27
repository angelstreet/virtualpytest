# VirtualPyTest Backend Server

Main API server handling client requests and orchestration for VirtualPyTest framework.

## 🎯 **Purpose**

backend_server provides the central API layer that coordinates between the frontend interface and backend_host hardware controllers. It handles business logic, user management, test orchestration, and serves as the communication hub for the entire system.

## 🔧 **Installation**

```bash
# Install dependencies
pip install -r requirements.txt

# Install shared library
pip install -e ../shared

# Run the service
python src/app.py
```

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
backend_server (API Layer)
├── Flask Application (Gunicorn)
├── REST API Routes (/api/*)
├── WebSocket Handlers (Socket.IO)
├── Business Logic Services
├── Host Communication Layer
└── Database Layer (if applicable)
```

## 🔧 **Configuration**

### Environment Variables

Copy the environment template and fill in your values:

```bash
# Copy template
cp env.example .env

# Edit with your values
nano .env
```

Required environment variables (see `env.example`):

```bash
# backend_server Environment Variables
NEXT_PUBLIC_SUPABASE_URL=your_supabase_project_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
CLOUDFLARE_R2_ENDPOINT=your_r2_endpoint
CLOUDFLARE_R2_ACCESS_KEY_ID=your_access_key
CLOUDFLARE_R2_SECRET_ACCESS_KEY=your_secret_key
CLOUDFLARE_R2_PUBLIC_URL=your_r2_public_url
OPENROUTER_API_KEY=your_openrouter_key
FLASK_SECRET_KEY=your_flask_secret
```

## 🚀 **Deployment**

### Render Deployment (Recommended)

1. **Connect Repository**: Link your GitHub repo to Render
2. **Build Command**: `cd backend_server && pip install -r requirements.txt`
3. **Start Command**: `cd backend_server && python src/app.py`
4. **Environment Variables**: Set in Render dashboard

```bash
# Render environment variables
SERVER_PORT=5109
SERVER_URL=https://your-app.onrender.com
CORS_ORIGINS=https://your-frontend.vercel.app
DEBUG=false
```

### Docker Deployment
```bash
# Build image
docker build -f Dockerfile -t virtualpytest/backend_server .

# Run container
docker run -d \
  -p 5109:5109 \
  -e SERVER_URL=http://localhost:5109 \
  -e CORS_ORIGINS=http://localhost:3000 \
  virtualpytest/backend_server
```

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