# Grafana Cloud Database Migration Guide

**Migrate from local PostgreSQL to Supabase for cloud-hosted Grafana metrics**

## 📋 **Overview**

By default, VirtualPyTest uses a local PostgreSQL database for Grafana metrics. This guide shows how to migrate to **Supabase** for cloud-hosted database benefits:

- ✅ **Cloud-hosted** - No local database maintenance
- ✅ **Automatic backups** - Built-in data protection  
- ✅ **Scalability** - Handles growing metric data
- ✅ **Real-time features** - Advanced Supabase capabilities
- ✅ **Unified storage** - Same platform as main application data

---

## ⚠️ **Important Notes**

- **Complete local installation first** - Follow [Getting Started Guide](getting-started.md) before migrating
- **Backup existing data** - Migration will preserve historical metrics
- **Network dependency** - Requires stable internet connection
- **Supabase limits** - Free tier has connection and storage limits

---

## 🚀 **Step 1: Supabase Setup** (10 minutes)

### Create Supabase Project

1. **Sign up** at https://supabase.com
2. **Create new project**:
   - Project name: `virtualpytest-grafana` (or your choice)
   - Database password: Choose strong password
   - Region: Select closest to your location

3. **Wait for provisioning** (2-3 minutes)

### Get Connection Details

Once project is ready, go to **Settings → Database**:

```bash
# Note these values for later:
Host: db.[project-ref].supabase.co
Database: postgres
Port: 5432
User: postgres
Password: [your-chosen-password]
```

### Get API Keys

Go to **Settings → API**:

```bash
# Note these values:
Project URL: https://[project-ref].supabase.co
Service Role Key: eyJ... (long key starting with eyJ)
```

---

## 🔄 **Step 2: Backup Current Data** (5 minutes)

Before migrating, backup your existing Grafana data:

```bash
# Navigate to project root
cd /path/to/virtualpytest

# Backup current Grafana database
pg_dump -h localhost -U grafana_user -d grafana_metrics > grafana_backup_$(date +%Y%m%d).sql

# Verify backup was created
ls -la grafana_backup_*.sql
```

**Keep this backup safe** - you can restore it if needed.

---

## 🔧 **Step 3: Update Configuration Files**

### A. Main Environment File

Edit your main `.env` file:

```bash
# Open main .env file
nano .env
```

**Replace the Grafana database section:**

```bash
# OLD - Local Grafana Database (comment out or remove)
# GRAFANA_DATABASE_URL=postgresql://grafana_user:grafana_pass@localhost:5432/grafana_metrics

# NEW - Supabase Grafana Database
GRAFANA_DATABASE_URL=postgresql://postgres:[YOUR_SUPABASE_PASSWORD]@db.[YOUR_PROJECT_REF].supabase.co:5432/postgres?sslmode=require

# Supabase API Configuration (for advanced features)
SUPABASE_URL=https://[YOUR_PROJECT_REF].supabase.co
SUPABASE_SERVICE_KEY=[YOUR_SERVICE_ROLE_KEY]
```

### B. Grafana Configuration

Edit Grafana's database configuration:

```bash
# Open Grafana config
nano grafana/config/grafana.ini
```

**Update the `[database]` section:**

```ini
[database]
# Database type
type = postgres

# Supabase connection details
host = db.[YOUR_PROJECT_REF].supabase.co:5432
name = postgres
user = postgres
password = [YOUR_SUPABASE_PASSWORD]

# SSL is required for Supabase
ssl_mode = require

# Connection pool settings (adjust based on Supabase plan)
max_idle_conn = 2
max_open_conn = 5
conn_max_lifetime = 14400
```

### C. Backend Configuration (if applicable)

If your backend writes metrics directly to Grafana database, update those connection strings too:

```bash
# Check if backend_server uses Grafana database
grep -r "grafana_metrics" backend_server/src/ || echo "No direct Grafana DB usage found"

# Check if backend_host uses Grafana database  
grep -r "grafana_metrics" backend_host/src/ || echo "No direct Grafana DB usage found"
```

---

## 🔄 **Step 4: Migrate Historical Data** (10 minutes)

### Option A: Fresh Start (Recommended)
Skip historical data and let Grafana create fresh tables:

```bash
# Grafana will automatically create tables on first startup
# No additional steps needed
```

### Option B: Migrate Historical Data
If you want to preserve historical metrics:

```bash
# Install PostgreSQL client tools (if not already installed)
sudo apt-get install postgresql-client

# Restore backup to Supabase
psql "postgresql://postgres:[PASSWORD]@db.[PROJECT_REF].supabase.co:5432/postgres?sslmode=require" < grafana_backup_$(date +%Y%m%d).sql
```

**Note**: You may need to handle table conflicts if Grafana has already created tables.

---

## 🚀 **Step 5: Test Migration** (5 minutes)

### Stop Local Services

```bash
# Stop Grafana to release local database connections
sudo systemctl stop grafana-server

# Stop other services to ensure clean restart
./scripts/force_stop_all.sh
```

### Start with New Configuration

```bash
# Launch VirtualPyTest with new Supabase configuration
./scripts/launch_virtualpytest.sh
```

### Verify Connection

1. **Check Grafana startup logs**:
   ```bash
   sudo journalctl -u grafana-server -f
   ```
   Look for successful database connection messages.

2. **Access Grafana dashboard**:
   - Open http://localhost:3000
   - Login with admin/admin (or your configured credentials)
   - Verify dashboards load without errors

3. **Check Supabase dashboard**:
   - Go to your Supabase project → Database
   - Verify Grafana tables were created
   - Check for recent data entries

---

## 🔧 **Step 6: Configure Supabase Security** (Optional but Recommended)

### Enable Row Level Security

In Supabase SQL Editor, run:

```sql
-- Enable RLS on Grafana tables (adjust table names as needed)
ALTER TABLE dashboard ENABLE ROW LEVEL SECURITY;
ALTER TABLE dashboard_version ENABLE ROW LEVEL SECURITY;
ALTER TABLE data_source ENABLE ROW LEVEL SECURITY;

-- Create policy for service role access
CREATE POLICY "Service role access" ON dashboard
FOR ALL USING (auth.role() = 'service_role');

-- Repeat for other Grafana tables as needed
```

### Create Dedicated Database User (Advanced)

For better security, create a dedicated Grafana user:

```sql
-- Create Grafana-specific user
CREATE USER grafana_user WITH PASSWORD 'secure_grafana_password';

-- Grant necessary permissions
GRANT CONNECT ON DATABASE postgres TO grafana_user;
GRANT USAGE ON SCHEMA public TO grafana_user;
GRANT CREATE ON SCHEMA public TO grafana_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO grafana_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO grafana_user;
```

Then update your `grafana.ini` to use this dedicated user.

---

## 🔍 **Troubleshooting**

### Connection Issues

**Problem**: Grafana can't connect to Supabase
```bash
# Check connection manually
psql "postgresql://postgres:[PASSWORD]@db.[PROJECT_REF].supabase.co:5432/postgres?sslmode=require"
```

**Solutions**:
- Verify password and project reference
- Check internet connection
- Ensure SSL mode is set to `require`
- Verify Supabase project is active

### SSL Certificate Issues

**Problem**: SSL verification errors
```bash
# Test with SSL disabled (temporary troubleshooting only)
ssl_mode = disable
```

**Solution**: Update SSL configuration:
```ini
ssl_mode = require
ssl_cert = 
ssl_key = 
ssl_ca = 
```

### Performance Issues

**Problem**: Slow dashboard loading
**Solutions**:
- Increase connection pool settings
- Choose Supabase region closer to your location
- Consider upgrading Supabase plan for better performance
- Optimize Grafana queries

### Data Migration Issues

**Problem**: Historical data not showing
**Solutions**:
- Verify backup was restored correctly
- Check table names match Grafana expectations
- Ensure proper permissions on restored tables

---

## 🔄 **Rollback to Local Database**

If you need to revert to local database:

1. **Stop services**:
   ```bash
   ./scripts/force_stop_all.sh
   ```

2. **Restore original configuration**:
   ```bash
   # Restore .env file
   git checkout .env
   
   # Restore grafana.ini
   git checkout grafana/config/grafana.ini
   ```

3. **Start local PostgreSQL**:
   ```bash
   sudo systemctl start postgresql
   sudo systemctl start grafana-server
   ```

4. **Restore backup if needed**:
   ```bash
   psql -h localhost -U grafana_user -d grafana_metrics < grafana_backup_[date].sql
   ```

---

## 📊 **Monitoring Your Migration**

### Supabase Dashboard Monitoring

Monitor your Grafana database usage:

1. **Go to Supabase Dashboard → Database**
2. **Check metrics**:
   - Connection count
   - Query performance
   - Storage usage
   - API requests

### Grafana Performance

Monitor Grafana performance after migration:

1. **Dashboard load times**
2. **Query execution times**  
3. **Error rates in logs**
4. **Memory and CPU usage**

---

## 💡 **Best Practices**

### Regular Backups
```bash
# Create automated backup script
cat > backup_grafana_supabase.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump "postgresql://postgres:[PASSWORD]@db.[PROJECT_REF].supabase.co:5432/postgres?sslmode=require" > "grafana_supabase_backup_$DATE.sql"
echo "Backup created: grafana_supabase_backup_$DATE.sql"
EOF

chmod +x backup_grafana_supabase.sh
```

### Connection Optimization
- Use connection pooling
- Set appropriate timeouts
- Monitor connection limits
- Consider read replicas for heavy workloads

### Security
- Use strong passwords
- Enable RLS where appropriate
- Regular security updates
- Monitor access logs

---

## 🆘 **Need Help?**

### Common Issues
- **Connection timeouts**: Check network and Supabase status
- **Permission errors**: Verify user permissions and RLS policies
- **Performance issues**: Consider Supabase plan upgrade or query optimization

### Support Resources
- **Supabase Documentation**: https://supabase.com/docs
- **Grafana Documentation**: https://grafana.com/docs/
- **VirtualPyTest Issues**: GitHub repository issues section

---

## 🎉 **Migration Complete!**

**Congratulations!** Your Grafana metrics are now stored in Supabase cloud database.

### What You've Achieved:
- ✅ **Cloud-hosted metrics** - No local database maintenance
- ✅ **Automatic backups** - Built-in data protection
- ✅ **Scalability** - Ready for growing data needs
- ✅ **Professional setup** - Production-ready configuration

### Next Steps:
- Monitor performance and connection usage
- Set up automated backups
- Explore Supabase real-time features
- Consider additional Grafana optimizations

**Your VirtualPyTest system is now running with enterprise-grade cloud database infrastructure!**
