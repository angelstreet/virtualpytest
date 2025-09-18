# Grafana Local Setup for VirtualPyTest

This document explains how to install and use Grafana for local development and monitoring of VirtualPyTest.

## 🚀 Quick Start

### 1. Install Grafana
```bash
# Install Grafana and setup local configuration
./setup/local/install_grafana.sh
```

### 2. Start Grafana (Standalone)
```bash
# Start Grafana only
./setup/local/launch_grafana.sh
```

### 3. Start All Services with Grafana
```bash
# Start all VirtualPyTest services including Grafana
./setup/local/launch_all.sh --with-grafana
```

### 4. Install Everything with Grafana
```bash
# Install all components including Grafana
./setup/local/install_all.sh --with-grafana
```

## 📊 Access Grafana

- **URL**: http://localhost:3000
- **Username**: admin
- **Password**: admin123

## 🏗️ Architecture

### Local Grafana Setup
```
VirtualPyTest Local Development
├── Frontend (Port 3000)
├── backend_server (Port 5109)
├── backend_host (Port 6109)
├── Grafana (Port 3001)
└── PostgreSQL (Port 5432)
    ├── grafana_metrics (Local metrics)
    └── supabase_db (Application data - optional)
```

### Data Sources

1. **VirtualPyTest Metrics (Local)** - Default
   - Local PostgreSQL database for storing custom metrics
   - Database: `grafana_metrics`
   - User: `grafana_user` / `grafana_pass`
   - Used for: Custom dashboards, local development metrics

2. **VirtualPyTest Supabase (Read-Only)** - Optional
   - Production Supabase database (read-only)
   - Configured via `SUPABASE_DB_URI` environment variable
   - Used for: Production data analysis, dashboard development

### Dashboard Sources

1. **VirtualPyTest Dashboards** (from backend_server)
   - Location: `./backend_server/config/grafana/dashboards/`
   - Contains: Production dashboards (system-health.json, virtualpytest-overview.json)
   - Auto-imported and updated

2. **Local Development Dashboards**
   - Location: `./grafana/dashboards/`
   - Contains: Local development and testing dashboards
   - Editable and customizable

## 🔧 Configuration Files

### Main Configuration
- **Grafana Config**: `grafana/config/grafana.ini`
- **Data Directory**: `grafana/data/`
- **Logs Directory**: `grafana/logs/`

### Provisioning
- **Datasources**: `grafana/provisioning/datasources/local.yml`
- **Dashboards**: `grafana/provisioning/dashboards/dashboards.yml`

## 🛠️ Development Workflow

### 1. Basic Setup
```bash
# Install and start everything
./setup/local/install_all.sh --with-grafana
./setup/local/launch_all.sh --with-grafana
```

### 2. Dashboard Development
1. Access Grafana at http://localhost:3000
2. Create/edit dashboards in the "Local" folder
3. Export dashboards to `./grafana/dashboards/` for version control
4. Test with local metrics database

### 3. Production Dashboard Testing
1. Set `SUPABASE_DB_URI` environment variable
2. Use "VirtualPyTest Supabase (Read-Only)" datasource
3. Test production dashboards with real data

### 4. Custom Metrics
1. Use "VirtualPytest Metrics (Local)" datasource
2. Create tables in `grafana_metrics` database
3. Build custom panels and dashboards

## 📈 Example Queries

### Local Metrics Database
```sql
-- Example: Create a simple metrics table
CREATE TABLE test_metrics (
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    test_name VARCHAR(255),
    duration_ms INTEGER,
    status VARCHAR(50),
    device_id VARCHAR(100)
);

-- Insert sample data
INSERT INTO test_metrics (test_name, duration_ms, status, device_id) 
VALUES ('login_test', 1500, 'success', 'device_001');
```

### Dashboard Panel Query
```sql
-- Test execution trends
SELECT 
    DATE_TRUNC('hour', timestamp) as time,
    COUNT(*) as test_count,
    AVG(duration_ms) as avg_duration
FROM test_metrics 
WHERE $__timeFilter(timestamp)
GROUP BY time
ORDER BY time;
```

## 🔍 Troubleshooting

### Grafana Won't Start
```bash
# Check if port 3001 is available
lsof -ti:3001

# Check PostgreSQL is running
pg_isready

# Check configuration
cat grafana/config/grafana.ini
```

### Database Connection Issues
```bash
# Test local metrics database
PGPASSWORD=grafana_pass psql -h localhost -U grafana_user -d grafana_metrics -c "SELECT version();"

# Check Supabase connection (if configured)
psql "$SUPABASE_DB_URI" -c "SELECT version();"
```

### Missing Dashboards
```bash
# Check dashboard provisioning
ls -la backend_server/config/grafana/dashboards/
ls -la grafana/dashboards/

# Check provisioning config
cat grafana/provisioning/dashboards/dashboards.yml
```

## 🔄 Integration with Existing Config

The local Grafana setup integrates with the existing backend_server Grafana configuration:

1. **Reuses Dashboards**: Automatically imports dashboards from `backend_server/config/grafana/dashboards/`
2. **Compatible Config**: Uses similar structure and naming conventions
3. **Environment Variables**: Supports same environment variables (SUPABASE_DB_URI, etc.)
4. **Port Separation**: Uses port 3001 to avoid conflicts with frontend (port 3000)

## 📝 Environment Variables

```bash
# Optional: Supabase database connection for production data
export SUPABASE_DB_URI="postgresql://user:pass@host:5432/postgres"

# Optional: Custom Grafana admin credentials
export GRAFANA_ADMIN_USER="admin"
export GRAFANA_ADMIN_PASSWORD="admin123"
```

## 🚀 Next Steps

1. **Install**: Run `./setup/local/install_grafana.sh`
2. **Configure**: Set environment variables if needed
3. **Start**: Run `./setup/local/launch_all.sh --with-grafana`
4. **Access**: Open http://localhost:3000 (admin/admin123)
5. **Develop**: Create custom dashboards and metrics
6. **Deploy**: Export dashboards to production when ready

## 📚 Additional Resources

- [Grafana Documentation](https://grafana.com/docs/)
- [PostgreSQL Datasource](https://grafana.com/docs/grafana/latest/datasources/postgres/)
- [Dashboard Provisioning](https://grafana.com/docs/grafana/latest/administration/provisioning/#dashboards)
- [VirtualPyTest Grafana Integration](../../docs/architecture/GRAFANA_INTEGRATION.md)
