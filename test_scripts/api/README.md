# API Testing Framework

Modular API testing script that integrates with the VirtualPyTest deployment and monitoring system.

## ✅ Features

- **3 Testing Modes**: Profiles, Custom endpoints, OpenAPI specs
- **Follows validation.py pattern**: Uses `@script` decorator, execution context, and formatted reports
- **Deployment Integration**: Works seamlessly with existing cron scheduling
- **Grafana Ready**: Results stored in database for visualization
- **Modular Profiles**: Easy to add/modify test profiles via JSON

---

## 🚀 Usage

### Mode 1: Predefined Profiles

```bash
# Quick sanity check (2 endpoints, ~1s)
python test_scripts/api_test.py --profile sanity

# Full API test (all major endpoints)
python test_scripts/api_test.py --profile full

# Device management only
python test_scripts/api_test.py --profile devices

# Campaign management only
python test_scripts/api_test.py --profile campaigns

# Testcase & requirements
python test_scripts/api_test.py --profile testcases

# Deployment & monitoring
python test_scripts/api_test.py --profile deployment

# Host service endpoints
python test_scripts/api_test.py --profile host
```

### Mode 2: Custom Endpoint List

```bash
# Test specific endpoints
python test_scripts/api_test.py --endpoints "/server/health,/server/devices/getAllDevices,/server/campaigns/getAllCampaigns"
```

### Mode 3: Auto from OpenAPI Spec

```bash
# Test all endpoints from a spec
python test_scripts/api_test.py --spec server-device-management
python test_scripts/api_test.py --spec host-verification-suite
```

---

## 📊 Integration with Deployments Page

In your **Deployments** page (`frontend/src/pages/Deployments.tsx`), create deployments like this:

### Example 1: Sanity Check Every 10 Minutes

```
Name: API Health Check
Script: api_test.py
Parameters: --profile sanity
Cron: */10 * * * *  (every 10 min)
```

### Example 2: Full Test Every Hour

```
Name: API Full Test
Script: api_test.py
Parameters: --profile full
Cron: 0 * * * *  (every hour)
```

### Example 3: Device APIs Every 30 Minutes

```
Name: Device API Test
Script: api_test.py
Parameters: --spec server-device-management
Cron: */30 * * * *  (every 30 min)
```

### Example 4: Custom Endpoints Daily

```
Name: Critical Endpoints Check
Script: api_test.py
Parameters: --endpoints "/server/health,/server/deployment/list,/server/alerts/getActiveAlerts"
Cron: 0 8 * * *  (every day at 8am)
```

---

## 📋 Execution Report

The script generates a formatted execution summary **matching validation.py format**:

```
------------------------------------------------------------
🎯 [API TEST] EXECUTION SUMMARY
------------------------------------------------------------
📋 Test Profile: Full API Test
📝 Description: Comprehensive test of all major endpoints
🌐 Server URL: http://localhost:5109
⏱️  Total Time: 2.3s
⚡ Avg Response Time: 45ms
📊 Endpoints Tested: 11
✅ Successful: 11
❌ Failed: 0
🎯 Success Rate: 100.0%
🎯 Result: SUCCESS
------------------------------------------------------------
```

---

## 🎨 Adding New Profiles

Edit `test_scripts/api/api_profiles.json`:

```json
{
  "my_custom_profile": {
    "name": "My Custom Test",
    "description": "Test my specific endpoints",
    "endpoints": [
      {
        "path": "/server/my-endpoint",
        "method": "GET",
        "expected_status": 200,
        "description": "My endpoint description"
      }
    ]
  }
}
```

Then use it:
```bash
python test_scripts/api_test.py --profile my_custom_profile
```

---

## 📈 Grafana Integration

**It's automatic!** Because `api_test.py` uses the `@script` decorator:

1. **Execution results** → Stored in `deployment_executions` table (Supabase)
2. **Step details** → Available in `context.step_results`
3. **Summary** → Available in `context.execution_summary`

Your existing Grafana dashboard (`GrafanaDashboard.tsx`) can visualize:
- Success rate over time
- Average response times
- Failed endpoints
- API health trends

---

## 🔄 How It Works

```
┌─────────────────────────────────────────────────────────┐
│  Deployment System (Cron Scheduler)                    │
│  - Triggers api_test.py based on schedule              │
└───────────────────┬─────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│  api_test.py (@script decorator)                       │
│  - Loads profile/endpoints/spec                        │
│  - Tests each endpoint                                  │
│  - Records steps in context.step_results               │
│  - Generates execution_summary                         │
└───────────────────┬─────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│  Database (Supabase)                                    │
│  - Stores execution results                             │
│  - Stores step details                                  │
│  - Stores summary                                       │
└───────────────────┬─────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│  Grafana Dashboard                                      │
│  - Visualizes API health                                │
│  - Shows success rates                                  │
│  - Displays response times                              │
│  - Alerts on failures                                   │
└─────────────────────────────────────────────────────────┘
```

---

## 🎯 Best Practices

1. **Start with sanity profile**: Quick health check every 10 min
2. **Full test less frequently**: Every hour or daily
3. **Category-specific tests**: For critical modules (devices, campaigns)
4. **Custom endpoints**: For your most critical paths
5. **Monitor in Grafana**: Set up alerts for failures

---

## 📝 Environment Variables

```bash
# Optional: Override server URL
export SERVER_URL=http://localhost:5109

# For production
export SERVER_URL=https://api.yourproduction.com
```

---

## 🔍 Debugging

```bash
# Test a single profile locally
python test_scripts/api_test.py --profile sanity

# Test custom endpoints
python test_scripts/api_test.py --endpoints "/server/health"

# Check which profiles are available
cat test_scripts/api/api_profiles.json | jq 'keys'
```

---

## ✨ Summary

**One modular script, multiple ways to use it, fully integrated with your existing deployment system!**

No need for Newman, Postman Monitors, or separate tools - everything stays in your VirtualPyTest ecosystem.

