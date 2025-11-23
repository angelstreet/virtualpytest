# Backend Server Technical Documentation

**API orchestration service with Grafana monitoring integration.**

---

## 🎯 **Purpose**

Backend Server provides:
- **REST API**: Central API layer for frontend
- **WebSocket**: Real-time communication
- **Host Coordination**: Manages multiple Backend Host instances
- **Grafana Integration**: Built-in monitoring dashboards
- **Business Logic**: Test orchestration and campaign management

---

## 🏗️ **Architecture**

```
backend_server Container:
├── Flask Application (Port 5109)
│   ├── REST API Routes (/api/*)
│   ├── WebSocket Handlers (Socket.IO)
│   ├── Business Logic Services
│   └── Database Layer (Supabase PostgreSQL)
├── Grafana Service (Port 3001)
│   ├── PostgreSQL Datasource
│   ├── VirtualPyTest Dashboards
│   └── Real-time Metrics & Alerts
└── Supervisor Process Manager
    ├── Flask Process Control
    ├── Grafana Process Control
    └── Health Check Coordination
```

---

## 🌐 **API Endpoints**

### System Management
```python
GET  /api/health              # Health check
GET  /api/system/info         # System information  
GET  /api/system/status       # Overall system status
```

### Test Management
```python
GET    /api/testcases         # List test cases
POST   /api/testcases         # Create test case
PUT    /api/testcases/<id>    # Update test case
DELETE /api/testcases/<id>    # Delete test case
```

### Campaign Management
```python
GET    /api/campaigns         # List campaigns
POST   /api/campaigns         # Create campaign
PUT    /api/campaigns/<id>    # Update campaign
DELETE /api/campaigns/<id>    # Delete campaign
POST   /api/campaigns/<id>/execute  # Execute campaign
```

### Host Coordination
```python
GET  /api/hosts               # List registered hosts
POST /api/hosts/register      # Register new host
POST /api/hosts/<id>/execute  # Execute command on host
GET  /api/hosts/<id>/status   # Get host status
```

### Device Management
```python
GET    /api/devices           # List devices
POST   /api/devices           # Create device
PUT    /api/devices/<id>      # Update device
DELETE /api/devices/<id>      # Delete device
```

---

## 🔄 **Request Flow**

### Test Execution Flow
```python
# 1. Frontend sends test request
POST /api/testcases/123/execute
{
    "device_id": "device1",
    "host_id": "pi-host-1"  # Optional
}

# 2. Backend Server finds available host
available_host = host_manager.find_available_host(
    capabilities=['android_mobile']
)

# 3. Backend Server proxies to Backend Host  
response = requests.post(
    f"{host.url}/host/remote/executeAction",
    json=test_action
)

# 4. Results flow back to frontend
return {
    "execution_id": "exec_123",
    "status": "running",
    "host": available_host.name
}
```

### WebSocket Events
```python
# Real-time updates
socketio.emit('test_progress', {
    'execution_id': 'exec_123',
    'step': 5,
    'total_steps': 10,
    'status': 'running',
    'screenshot_url': '/screenshots/step_005.png'
})

socketio.emit('device_status', {
    'device_id': 'device1',
    'status': 'online',
    'last_seen': '2024-01-15T10:30:00Z'
})
```

---

## 🏢 **Business Logic Services**

### Test Orchestrator
**Purpose**: Coordinate test execution across hosts

```python
class TestOrchestrator:
    def execute_test_case(self, test_case_id: str, 
                         device_id: str, 
                         host_id: str = None) -> Dict:
        # Load test case
        test_case = self.load_test_case(test_case_id)
        
        # Find available host
        host = self.find_host(host_id, test_case.requirements)
        
        # Execute test
        execution_id = self.create_execution_record(test_case, host)
        
        # Send to host for execution
        result = self.send_to_host(host, test_case, execution_id)
        
        return {
            'execution_id': execution_id,
            'status': result.status,
            'host': host.name
        }
```

### Campaign Manager
**Purpose**: Manage batch test execution

```python
class CampaignManager:
    def execute_campaign(self, campaign_id: str) -> Dict:
        campaign = self.load_campaign(campaign_id)
        
        execution_results = []
        for test_case in campaign.test_cases:
            result = self.orchestrator.execute_test_case(
                test_case.id,
                test_case.device_id
            )
            execution_results.append(result)
            
            # Handle failures based on campaign settings
            if not result.success and campaign.stop_on_failure:
                break
        
        return {
            'campaign_execution_id': str(uuid.uuid4()),
            'results': execution_results,
            'summary': self.generate_summary(execution_results)
        }
```

### Host Manager
**Purpose**: Track and coordinate Backend Host instances

```python
class HostManager:
    def register_host(self, host_info: Dict) -> bool:
        host = Host(
            name=host_info['host_name'],
            url=host_info['host_url'],
            capabilities=host_info['capabilities'],
            status='available'
        )
        
        # Store in database
        self.db.add_host(host)
        
        # Start health monitoring
        self.start_health_check(host)
        
        return True
    
    def find_available_host(self, capabilities: List[str]) -> Host:
        return self.db.find_host_with_capabilities(
            capabilities, 
            status='available'
        )
```

---

## 📊 **Database Integration**

### Database Models
```python
class TestCase(db.Model):
    id = db.Column(db.String, primary_key=True)
    name = db.Column(db.String, nullable=False)
    description = db.Column(db.Text)
    steps = db.Column(db.JSON)
    device_model = db.Column(db.String)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class TestExecution(db.Model):
    id = db.Column(db.String, primary_key=True)
    test_case_id = db.Column(db.String, db.ForeignKey('test_case.id'))
    host_id = db.Column(db.String, db.ForeignKey('host.id'))
    status = db.Column(db.String)  # running, completed, failed
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    results = db.Column(db.JSON)
```

### Query Examples
```python
# Get test success rate
def get_success_rate(days: int = 30) -> float:
    since = datetime.utcnow() - timedelta(days=days)
    
    total = TestExecution.query.filter(
        TestExecution.started_at >= since
    ).count()
    
    successful = TestExecution.query.filter(
        TestExecution.started_at >= since,
        TestExecution.status == 'completed'
    ).count()
    
    return (successful / total * 100) if total > 0 else 0

# Get device health metrics
def get_device_metrics() -> List[Dict]:
    return db.session.query(
        Device.name,
        Device.status,
        func.count(TestExecution.id).label('test_count'),
        func.avg(
            extract('epoch', TestExecution.completed_at - TestExecution.started_at)
        ).label('avg_duration')
    ).join(TestExecution).group_by(Device.id).all()
```

---

## 📈 **Grafana Integration**

### Dashboard Provisioning
```yaml
# config/grafana/dashboards/virtualpytest-overview.json
{
  "dashboard": {
    "title": "VirtualPyTest - System Overview",
    "panels": [
      {
        "title": "Test Success Rate",
        "type": "stat",
        "targets": [
          {
            "rawSql": "SELECT COUNT(CASE WHEN status = 'completed' THEN 1 END)::numeric / NULLIF(COUNT(*), 0) * 100 FROM test_executions WHERE created_at >= NOW() - INTERVAL '24 hours'"
          }
        ]
      }
    ]
  }
}
```

### Datasource Configuration
```yaml
# config/grafana/datasources/postgres.yml
apiVersion: 1
datasources:
  - name: VirtualPyTest PostgreSQL
    type: postgres
    url: ${DATABASE_URL}
    database: postgres
    user: ${DB_USER}
    password: ${DB_PASSWORD}
    sslmode: require
```

---

## 🔧 **Configuration**

### Environment Variables
```bash
# Server Configuration
SERVER_PORT=5109
SERVER_URL=http://localhost:5109
CORS_ORIGINS=http://localhost:3000,https://virtualpytest.vercel.app

# Database Configuration
DATABASE_URL=postgresql://postgres:password@db.project.supabase.co:5432/postgres
SUPABASE_URL=https://project.supabase.co
SUPABASE_ANON_KEY=your_anon_key

# Grafana Configuration
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=admin123
GRAFANA_SECRET_KEY=your_grafana_secret_key

# External Services
OPENROUTER_API_KEY=your_openrouter_key
CLOUDFLARE_R2_ENDPOINT=your_r2_endpoint
```

### Flask Configuration
```python
class Config:
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # CORS settings
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '').split(',')
    
    # WebSocket settings
    SOCKETIO_ASYNC_MODE = 'threading'
    
    # Upload settings
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
```

---

## 🚀 **Deployment**

### Docker Configuration
```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Grafana
RUN curl -fsSL https://packages.grafana.com/gpg.key | apt-key add -
RUN echo "deb https://packages.grafana.com/oss/deb stable main" | tee -a /etc/apt/sources.list.d/grafana.list
RUN apt-get update && apt-get install -y grafana

# Copy application code
COPY backend_server/ /app/backend_server/
COPY shared/ /app/shared/
COPY backend_host/ /app/backend_host/

# Set Python path
ENV PYTHONPATH="/app/shared:/app/shared/lib:/app/backend_host/src"

# Install Python dependencies
RUN pip install -r /app/backend_server/requirements.txt

# Copy supervisor configuration
COPY backend_server/config/supervisor/supervisord.conf /etc/supervisor/conf.d/

# Expose ports
EXPOSE 5109 3001

# Start supervisor
CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
```

### Supervisor Configuration
```ini
[supervisord]
nodaemon=true

[program:flask]
command=gunicorn -w 2 -b 0.0.0.0:5109 src.app:app
directory=/app/backend_server
autostart=true
autorestart=true
stdout_logfile=/var/log/flask.log
stderr_logfile=/var/log/flask.error.log

[program:grafana]
command=/usr/sbin/grafana-server --config=/app/backend_server/config/grafana/grafana.ini
autostart=true
autorestart=true
stdout_logfile=/var/log/grafana.log
stderr_logfile=/var/log/grafana.error.log
```

---

## 🔍 **Monitoring & Logging**

### Health Checks
```python
@app.route('/api/health')
def health_check():
    checks = {
        'database': check_database_connection(),
        'grafana': check_grafana_health(),
        'hosts': check_registered_hosts(),
        'external_services': check_external_services()
    }
    
    overall_health = all(checks.values())
    
    return {
        'status': 'healthy' if overall_health else 'unhealthy',
        'checks': checks,
        'timestamp': datetime.utcnow().isoformat()
    }, 200 if overall_health else 503
```

### Structured Logging
```python
import structlog

logger = structlog.get_logger()

@app.route('/api/testcases/<test_case_id>/execute', methods=['POST'])
def execute_test_case(test_case_id):
    logger.info("test_execution_started",
               test_case_id=test_case_id,
               user_id=request.user_id,
               host_id=request.json.get('host_id'))
    
    try:
        result = test_orchestrator.execute_test_case(test_case_id)
        
        logger.info("test_execution_completed",
                   test_case_id=test_case_id,
                   execution_id=result['execution_id'],
                   duration=result.get('duration'))
        
        return result
    except Exception as e:
        logger.error("test_execution_failed",
                    test_case_id=test_case_id,
                    error=str(e),
                    exc_info=True)
        raise
```

---

## 🔐 **Security**

### Authentication
```python
from functools import wraps
import jwt

def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        if not token:
            return {'error': 'No token provided'}, 401
        
        try:
            # Verify JWT token
            payload = jwt.decode(token, app.config['SECRET_KEY'], 
                               algorithms=['HS256'])
            request.user_id = payload['user_id']
        except jwt.InvalidTokenError:
            return {'error': 'Invalid token'}, 401
        
        return f(*args, **kwargs)
    return decorated_function
```

### Input Validation
```python
from marshmallow import Schema, fields, validate

class TestCaseSchema(Schema):
    name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    description = fields.Str(validate=validate.Length(max=1000))
    steps = fields.List(fields.Dict(), required=True)
    device_model = fields.Str(required=True)

@app.route('/api/testcases', methods=['POST'])
def create_test_case():
    schema = TestCaseSchema()
    try:
        data = schema.load(request.json)
    except ValidationError as err:
        return {'errors': err.messages}, 400
    
    # Create test case with validated data
    test_case = TestCase(**data)
    db.session.add(test_case)
    db.session.commit()
    
    return schema.dump(test_case), 201
```

---

**Want to understand host communication? Check [Backend Host Documentation](backend-host.md)!** 🔧
