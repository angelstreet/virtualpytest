# Monitoring with VirtualPyTest

**How to use Grafana dashboards and monitoring features.**

---

## 🎯 **What You'll Learn**

- Access and navigate Grafana dashboards
- Monitor device health and test performance
- Set up alerts and notifications
- Analyze test trends and metrics

---

## 📊 **Accessing Grafana**

### Quick Access
```bash
# Open monitoring dashboard
http://localhost:5109/grafana

# Direct Grafana access
http://localhost:3000
```

**Default Login**:
- **Username**: admin
- **Password**: admin123

*[Image placeholder: Grafana login screen]*

---

## 🏠 **Main Dashboards**

### VirtualPyTest - System Overview
**What it shows**:
- Test execution trends over time
- Active campaigns and connected devices
- Test results distribution (success/failure)
- Average execution times
- Campaign performance metrics

**Use cases**:
- Daily health check of testing system
- Track testing progress over weeks/months
- Identify performance trends

*[Image placeholder: System Overview dashboard with various charts]*

### VirtualPyTest - System Health
**What it shows**:
- Database connectivity status
- Active alerts and error rates
- Device status table
- Alert trends and system health metrics

**Use cases**:
- Monitor system reliability
- Detect infrastructure issues
- Track device connectivity problems

*[Image placeholder: System Health dashboard showing device status]*

---

## 📈 **Key Metrics Explained**

### Test Success Rate
**What it measures**: Percentage of tests that complete successfully
- **Good**: 90%+ success rate
- **Warning**: 80-90% success rate  
- **Critical**: <80% success rate

**Troubleshooting low success rates**:
- Check device connectivity
- Review failed test screenshots
- Verify navigation tree accuracy

### Device Response Time
**What it measures**: How quickly devices respond to commands
- **Good**: <2 seconds average
- **Warning**: 2-5 seconds average
- **Critical**: >5 seconds average

**Improving response times**:
- Check network connectivity
- Restart slow devices
- Optimize test scripts

### Error Rate Trends
**What it measures**: Frequency of test failures over time
- **Stable**: Consistent low error rate
- **Increasing**: Growing number of failures
- **Spikes**: Sudden failure increases

---

## 🔔 **Setting Up Alerts**

### Email Notifications
**Configure email alerts**:
1. Go to **Alerting** → **Notification channels**
2. Click **"Add channel"**
3. Choose **Email** type
4. Enter recipient addresses
5. Test and save

*[Image placeholder: Email notification setup interface]*

### Alert Rules
**Create custom alerts**:
1. Go to **Alerting** → **Alert Rules**
2. Click **"Create Alert"**
3. Define conditions (e.g., success rate < 80%)
4. Set evaluation frequency
5. Choose notification channel

**Common alert conditions**:
- Test success rate drops below 80%
- Device offline for more than 5 minutes
- Error rate increases by 50%
- No tests executed in last hour

---

## 📊 **Custom Queries**

### Test Success Rate Over Time
```sql
SELECT
  $__timeGroupAlias(created_at,$__interval),
  COUNT(CASE WHEN status = 'completed' THEN 1 END)::numeric / 
  NULLIF(COUNT(*), 0) * 100 as "Success Rate %"
FROM test_executions
WHERE $__timeFilter(created_at)
GROUP BY 1 ORDER BY 1;
```

### Device Connectivity Status
```sql
SELECT 
  name as "Device",
  status as "Status",
  updated_at as "Last Updated"
FROM device 
ORDER BY updated_at DESC;
```

### Campaign Performance
```sql
SELECT 
  c.name as "Campaign",
  COUNT(te.id) as "Total Tests",
  COUNT(CASE WHEN te.status = 'completed' THEN 1 END) as "Completed"
FROM campaigns c
LEFT JOIN test_executions te ON c.id = te.campaign_id
GROUP BY c.id, c.name;
```

---

## 🎯 **Monitoring Best Practices**

### Daily Routine
1. **Check System Overview** - 2 minutes
2. **Review Device Status** - 1 minute  
3. **Investigate Alerts** - As needed
4. **Plan Maintenance** - Based on trends

### Weekly Review
1. **Analyze Success Rate Trends** - 10 minutes
2. **Review Performance Metrics** - 5 minutes
3. **Update Alert Thresholds** - As needed
4. **Plan Infrastructure Changes** - Based on data

### Monthly Analysis
1. **Export Performance Reports** - For management
2. **Review Alert Effectiveness** - Adjust rules
3. **Plan Capacity Scaling** - Based on growth
4. **Update Monitoring Strategy** - Continuous improvement

---

## 🔧 **Dashboard Customization**

### Adding New Panels
1. Click **"Add Panel"** on any dashboard
2. Choose visualization type (graph, table, etc.)
3. Write your query
4. Configure display options
5. Save panel

### Creating Custom Dashboards
1. Go to **Dashboards** → **"New Dashboard"**
2. Add panels for your specific metrics
3. Organize layout logically
4. Save with descriptive name
5. Share with team

*[Image placeholder: Dashboard editing interface]*

---

## 📱 **Mobile Monitoring**

### Grafana Mobile App
- Download from App Store/Google Play
- Login with same credentials
- View dashboards on mobile
- Receive push notifications

### Quick Mobile Checks
- Device status at a glance
- Recent test results
- Active alerts
- System health summary

---

## 🚨 **Troubleshooting Monitoring**

### Common Issues

#### Grafana Won't Load
```bash
# Check if Grafana is running
docker ps | grep grafana

# Restart Grafana service
docker restart virtualpytest-backend_server-1
```

#### No Data in Dashboards
```bash
# Check database connection
curl http://localhost:5109/api/health

# Verify data source configuration
# Go to Configuration → Data Sources
```

#### Alerts Not Working
1. Check notification channel configuration
2. Verify alert rule conditions
3. Test notification channel
4. Check Grafana logs for errors

### Performance Issues
- **Slow Loading**: Reduce time range or add filters
- **High Memory**: Limit concurrent queries
- **Database Load**: Optimize query performance

---

## 📈 **Advanced Features**

### Annotations
**Mark important events**:
- Deployment timestamps
- Maintenance windows
- Configuration changes
- Incident markers

### Variables
**Create dynamic dashboards**:
- Device selector dropdown
- Time range variables
- Campaign filters
- Host selection

### Templating
**Reusable dashboard components**:
- Standard panel layouts
- Common query patterns
- Consistent styling
- Team templates

---

## 📊 **Reporting**

### Automated Reports
**Schedule regular reports**:
1. Install reporting plugin
2. Configure report templates
3. Set delivery schedule
4. Choose recipients

### Manual Exports
**Export data for analysis**:
- **PNG**: Dashboard screenshots
- **PDF**: Multi-page reports
- **CSV**: Raw data for Excel
- **JSON**: Dashboard configuration

---

**Ready to troubleshoot issues? Check out our [Troubleshooting Guide](troubleshooting.md)!** 🔧
