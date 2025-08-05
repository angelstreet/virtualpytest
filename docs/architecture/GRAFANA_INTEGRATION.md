# 📊 Grafana Integration Architecture

Comprehensive monitoring and analytics integration for VirtualPyTest using Grafana embedded within the backend_server container.

## 🏗️ **Architecture Overview**

```
VirtualPyTest Monitoring Stack
┌─────────────────────────────────────────────────────────────┐
│                    backend_server Container                 │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐    ┌─────────────────────────────────┐ │
│  │  Flask API      │    │         Grafana                 │ │
│  │  (Port 5109)    │    │       (Port 3000)              │ │
│  │                 │    │                                 │ │
│  │ • REST Routes   │    │ • PostgreSQL Datasource        │ │
│  │ • WebSocket     │    │ • Pre-built Dashboards         │ │
│  │ • Business      │    │ • Real-time Monitoring         │ │
│  │   Logic         │    │ • Alert Management             │ │
│  └─────────────────┘    └─────────────────────────────────┘ │
│                                    │                        │
│  ┌─────────────────────────────────┴─────────────────────┐  │
│  │            Supervisor Process Manager                │  │
│  │  • Flask Process Control                            │  │
│  │  • Grafana Process Control                          │  │
│  │  • Health Check Coordination                        │  │
│  │  • Log Management                                   │  │
│  └─────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 Supabase PostgreSQL                         │
│  • Core Tables (devices, campaigns, test_executions)       │
│  • Navigation Data (trees, nodes, edges)                   │
│  • Monitoring Data (alerts, metrics, heatmaps)             │
│  • Real-time Subscriptions                                 │
└─────────────────────────────────────────────────────────────┘
```

## 🎯 **Integration Strategy**

### **Single Container Approach**
- **Rationale**: Simplifies deployment on platforms like Render
- **Benefits**: 
  - Single Docker image deployment
  - Shared environment variables
  - Unified logging and monitoring
  - Reduced network complexity

### **Process Management**
- **Supervisor**: Manages both Flask and Grafana processes
- **Health Checks**: Monitors both services for availability
- **Auto-restart**: Automatic process recovery on failures
- **Log Aggregation**: Centralized logging for both services

## 📁 **File Structure**

```
backend_server/
├── config/
│   ├── grafana/
│   │   ├── grafana.ini                    # Main Grafana configuration
│   │   ├── provisioning/
│   │   │   ├── datasources/
│   │   │   │   └── supabase.yml          # PostgreSQL datasource config
│   │   │   └── dashboards/
│   │   │       └── dashboard.yml         # Dashboard provider config
│   │   └── dashboards/
│   │       ├── virtualpytest-overview.json    # System overview dashboard
│   │       └── system/
│   │           └── system-health.json         # System health dashboard
│   └── supervisor/
│       └── supervisord.conf               # Process management config
├── Dockerfile                             # Multi-service container build
└── README.md                             # Updated with Grafana documentation
```

## 🔧 **Configuration Management**

### **Environment Variables**

#### **Core Grafana Settings**
```bash
# Admin Access
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=admin123
GRAFANA_SECRET_KEY=your_grafana_secret_key_here

# Server Configuration
GRAFANA_DOMAIN=localhost
GRAFANA_PORT=3000
```

#### **Database Connection**
```bash
# Option 1: Direct PostgreSQL URL
DATABASE_URL=postgresql://postgres:password@db.project-id.supabase.co:5432/postgres

# Option 2: Individual parameters
SUPABASE_DB_HOST=db.project-id.supabase.co
SUPABASE_DB_PORT=5432
SUPABASE_DB_NAME=postgres
SUPABASE_DB_USER=postgres
SUPABASE_DB_PASSWORD=your_database_password

# Option 3: Supabase API (for additional features)
NEXT_PUBLIC_SUPABASE_URL=https://project-id.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
```

### **Grafana Configuration (`grafana.ini`)**

#### **Security Settings**
```ini
[security]
admin_user = ${GRAFANA_ADMIN_USER}
admin_password = ${GRAFANA_ADMIN_PASSWORD}
secret_key = ${GRAFANA_SECRET_KEY}
allow_embedding = true
disable_gravatar = false
```

#### **Database Configuration**
```ini
[database]
type = sqlite3
path = /var/lib/grafana/grafana.db
```

#### **Server Configuration**
```ini
[server]
http_addr = 0.0.0.0
http_port = 3000
domain = ${GRAFANA_DOMAIN}
root_url = %(protocol)s://%(domain)s:%(http_port)s/
```

## 📊 **Dashboard Architecture**

### **Pre-built Dashboards**

#### **1. VirtualPyTest System Overview**
- **Purpose**: High-level system monitoring
- **Metrics**:
  - Test execution trends over time
  - Active campaigns and connected devices
  - Test results distribution (success/failure)
  - Average execution times
  - Campaign performance metrics

#### **2. VirtualPyTest System Health**
- **Purpose**: Infrastructure and system health
- **Metrics**:
  - Database connectivity status
  - Active alerts and error rates
  - Device status monitoring
  - Controller health
  - System resource usage

### **Dashboard Provisioning**
```yaml
# dashboard.yml
providers:
  - name: 'VirtualPyTest Dashboards'
    orgId: 1
    folder: 'VirtualPyTest'
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /app/backend_server/config/grafana/dashboards
```

## 🔌 **Database Integration**

### **PostgreSQL Datasource Configuration**
```yaml
# supabase.yml
datasources:
  - name: VirtualPyTest PostgreSQL
    type: postgres
    access: proxy
    url: ${SUPABASE_DB_HOST}:${SUPABASE_DB_PORT}
    database: ${SUPABASE_DB_NAME}
    user: ${SUPABASE_DB_USER}
    secureJsonData:
      password: ${SUPABASE_DB_PASSWORD}
    jsonData:
      sslmode: require
      postgresVersion: 1300
      maxOpenConns: 5
      maxIdleConns: 2
      connMaxLifetime: 14400
    isDefault: true
    editable: false
```

### **Key Database Tables**

#### **Core Tables**
- `teams` - Team and tenant management
- `device_models` - Device type definitions
- `device` - Physical device instances
- `controllers` - Device controller configurations
- `campaigns` - Test campaign definitions

#### **Test Execution**
- `test_cases` - Individual test definitions
- `test_executions` - Test run instances
- `test_results` - Test outcome data
- `execution_results` - Detailed execution logs

#### **Navigation & UI**
- `navigation_trees` - Navigation flow definitions
- `navigation_nodes` - Individual navigation points
- `navigation_edges` - Navigation connections
- `userinterfaces` - UI element definitions

#### **Monitoring & Analytics**
- `alerts` - System alerts and notifications
- `heatmaps` - User interaction heatmaps
- `node_metrics` - Navigation node performance
- `edge_metrics` - Navigation edge analytics

## 📈 **Custom Queries & Metrics**

### **Test Execution Metrics**
```sql
-- Test execution success rate over time
SELECT
  $__timeGroupAlias(created_at,$__interval),
  COUNT(CASE WHEN status = 'completed' THEN 1 END)::numeric / 
  NULLIF(COUNT(*), 0) * 100 as "Success Rate %"
FROM test_executions
WHERE $__timeFilter(created_at)
GROUP BY 1 ORDER BY 1;
```

### **Device Health Monitoring**
```sql
-- Device connectivity status
SELECT 
  name as "Device",
  model as "Model",
  COALESCE(status, 'unknown') as "Status",
  updated_at as "Last Updated"
FROM device 
ORDER BY updated_at DESC;
```

### **Campaign Performance**
```sql
-- Campaign success metrics
SELECT 
  c.name as "Campaign",
  COUNT(te.id) as "Total Tests",
  COUNT(CASE WHEN te.status = 'completed' THEN 1 END) as "Completed",
  ROUND(
    COUNT(CASE WHEN te.status = 'completed' THEN 1 END)::numeric / 
    NULLIF(COUNT(te.id), 0) * 100, 2
  ) as "Success Rate %"
FROM campaigns c
LEFT JOIN test_executions te ON c.id = te.campaign_id
GROUP BY c.id, c.name
ORDER BY "Success Rate %" DESC;
```

### **System Health Queries**
```sql
-- Active alerts monitoring
SELECT
  $__timeGroupAlias(created_at,$__interval),
  COUNT(CASE WHEN status = 'active' THEN 1 END) as "Active Alerts",
  COUNT(CASE WHEN status = 'resolved' THEN 1 END) as "Resolved Alerts"
FROM alerts
WHERE $__timeFilter(created_at)
GROUP BY 1 ORDER BY 1;
```

## 🚀 **Deployment Configurations**

### **Local Development**
```bash
# Docker Compose
services:
  backend_server:
    ports:
      - "5109:5109"  # Flask API
      - "3001:3000"  # Grafana (mapped to avoid frontend conflict)
    environment:
      - GRAFANA_ADMIN_USER=admin
      - GRAFANA_ADMIN_PASSWORD=admin123
      - DATABASE_URL=postgresql://...
```

### **Render Cloud Deployment**
```bash
# Environment Variables in Render Dashboard
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=your_secure_password
GRAFANA_SECRET_KEY=your_grafana_secret_key
GRAFANA_DOMAIN=your-app-name.onrender.com
DATABASE_URL=postgresql://postgres:password@db.project-id.supabase.co:5432/postgres
```

### **Docker Standalone**
```bash
# Build and run with both services
docker build -f backend_server/Dockerfile -t virtualpytest/backend_server .
docker run -d \
  -p 5109:5109 \
  -p 3000:3000 \
  -e DATABASE_URL=postgresql://... \
  -e GRAFANA_ADMIN_USER=admin \
  -e GRAFANA_ADMIN_PASSWORD=admin123 \
  virtualpytest/backend_server
```

## 🔒 **Security Considerations**

### **Authentication & Authorization**
- **Admin Access**: Configurable admin credentials
- **Session Security**: Secure cookie configuration
- **Database Access**: Read-only database user recommended
- **Network Security**: Internal container communication

### **Data Protection**
- **Secret Management**: Environment variable based secrets
- **SSL/TLS**: Encrypted database connections
- **Access Control**: Grafana user management
- **Audit Logging**: Query and access logging

## 🔧 **Maintenance & Operations**

### **Health Monitoring**
```bash
# Check service status
curl http://localhost:5109/server/health  # Flask API
curl http://localhost:3000/api/health     # Grafana

# View process status
docker exec -it <container> supervisorctl status

# Check logs
docker logs <container> | grep grafana
docker logs <container> | grep flask
```

### **Backup & Recovery**
- **Grafana Settings**: Stored in SQLite database
- **Dashboard Definitions**: Version controlled in git
- **Data Source**: Backed up with main Supabase database
- **Configuration**: Environment variables and config files

### **Performance Optimization**
- **Query Caching**: Grafana built-in query caching
- **Connection Pooling**: PostgreSQL connection management
- **Resource Limits**: Container resource constraints
- **Dashboard Optimization**: Efficient query design

## 🎯 **Access & Usage**

### **Service Endpoints**
- **Flask API**: `http://localhost:5109`
- **Grafana Dashboard**: `http://localhost:3000`
- **Health Checks**: 
  - Flask: `/server/health`
  - Grafana: `/api/health`

### **Default Credentials**
- **Username**: `admin`
- **Password**: `admin123` (change via `GRAFANA_ADMIN_PASSWORD`)

### **Dashboard Navigation**
1. **Login** to Grafana with admin credentials
2. **Browse** to "VirtualPyTest" folder
3. **Select** dashboard:
   - "VirtualPyTest - System Overview"
   - "VirtualPyTest - System Health"
4. **Customize** time ranges and refresh intervals
5. **Create** custom dashboards as needed

## 🔄 **Future Enhancements**

### **Planned Features**
- **Alert Rules**: Automated alerting for system issues
- **Custom Panels**: Additional visualization types
- **Data Retention**: Long-term metrics storage
- **Multi-tenancy**: Team-based dashboard isolation
- **API Integration**: Grafana API for programmatic access

### **Scalability Considerations**
- **External Database**: Dedicated Grafana database for large deployments
- **Load Balancing**: Multiple Grafana instances
- **Caching Layer**: Redis for query caching
- **Data Aggregation**: Pre-computed metrics for performance

This architecture provides a robust, scalable monitoring solution integrated seamlessly with the VirtualPyTest platform while maintaining deployment simplicity and operational efficiency.