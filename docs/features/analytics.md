# 📊 Real-time Analytics & Monitoring

**Know what's happening. Every second.**

Integrated Grafana dashboards provide real-time insights into test execution, device health, and system performance.

---

## The Problem

Testing without metrics is flying blind:
- ❌ No visibility into test trends
- ❌ Device issues discovered too late
- ❌ Performance problems hidden
- ❌ Can't prove ROI to management

---

## The VirtualPyTest Solution

✅ **Real-time dashboards** - See what's happening now  
✅ **Historical trends** - Track improvement over time  
✅ **Automated alerts** - Get notified of issues immediately  
✅ **Custom metrics** - Track what matters to your team  

---

## Built-in Dashboards

### 📈 Test Execution Dashboard

**Monitor test execution in real-time.**

**Metrics:**
- Test pass/fail rates (overall and per device)
- Execution duration trends
- Test frequency and coverage
- Flaky test detection
- Success rate by test type

**Visualizations:**
- Time series graphs
- Success rate gauges
- Test distribution pie charts
- Execution timeline
- Failure heatmap

**Use cases:**
- Track regression test results
- Identify problematic tests
- Monitor CI/CD pipeline health
- Prove QA effectiveness

---

### 🔌 Device Health Dashboard

**Monitor all your devices at a glance.**

**Metrics:**
- Device online/offline status
- Connection stability
- Response time
- Uptime percentage
- Error rates

**Visualizations:**
- Device status grid
- Uptime history
- Connection quality graphs
- Alert history
- Device utilization

**Alerts:**
- Device disconnected
- High error rate
- Slow response times
- Power failures

---

### 🎬 Video Quality Dashboard

**Monitor streaming and playback quality.**

**Metrics:**
- Black screen incidents
- Freeze detection events
- Frame drop rate
- Bitrate stability
- Subtitle presence

**Visualizations:**
- Quality score timeline
- Incident frequency
- Duration of issues
- Quality heatmap by time
- Stream health gauge

**Use cases:**
- 24/7 streaming quality assurance
- Live channel monitoring
- VOD playback validation
- QoE (Quality of Experience) tracking

---

### ⚡ System Performance Dashboard

**Monitor VirtualPyTest infrastructure.**

**Metrics:**
- API response times
- Database query performance
- Storage usage
- Memory and CPU utilization
- Request throughput

**Visualizations:**
- Latency percentiles (p50, p95, p99)
- Resource usage graphs
- Request rate timeline
- Error rate tracking
- Service health status

---

## Custom Metrics

### Define Your Own KPIs

```python
# Track custom business metrics
from shared.src.services.metrics import MetricsCollector

metrics = MetricsCollector()

# Custom metric: App launch time
metrics.record(
    name="app_launch_time",
    value=2.3,  # seconds
    tags={
        "app": "netflix",
        "device": "android_tv_1",
        "network": "wifi"
    }
)

# Custom metric: Content loading success
metrics.increment(
    name="content_loaded_successfully",
    tags={
        "content_type": "movie",
        "resolution": "4k"
    }
)
```

### View in Grafana

Metrics automatically appear in Grafana:
- Create custom panels
- Build your own dashboards
- Set up custom alerts
- Export to other tools

---

## Alerting

### Built-in Alert Rules

**Get notified when things go wrong.**

#### Device Alerts
```yaml
alerts:
  - name: "Device Offline"
    condition: device_status == "offline"
    duration: 5m
    severity: "critical"
    channels: ["slack", "email"]
    
  - name: "High Error Rate"
    condition: error_rate > 10%
    duration: 2m
    severity: "warning"
    channels: ["slack"]
```

#### Test Alerts
```yaml
  - name: "Test Failure Spike"
    condition: failure_rate > 20%
    duration: 10m
    severity: "warning"
    channels: ["slack", "pagerduty"]
    
  - name: "No Tests Running"
    condition: tests_per_hour == 0
    duration: 1h
    severity: "info"
    channels: ["email"]
```

#### Quality Alerts
```yaml
  - name: "Black Screen Detected"
    condition: black_screen == true
    duration: 10s
    severity: "critical"
    channels: ["slack", "pagerduty"]
    
  - name: "Stream Frozen"
    condition: freeze_detected == true
    duration: 30s
    severity: "critical"
    channels: ["slack"]
```

---

### Alert Channels

**Multiple notification methods:**

- **Slack** - Team notifications
- **Email** - Stakeholder reports
- **PagerDuty** - On-call alerts
- **Webhook** - Custom integrations
- **SMS** - Critical alerts

---

## Grafana Integration

### Access Dashboards

Two ways to access Grafana:

#### 1. VirtualPyTest Web Interface
- Navigate to **Plugins → Grafana**
- Embedded Grafana interface
- Single sign-on (SSO)
- Pre-configured dashboards

#### 2. Direct Grafana Access
- Open `http://localhost:3001`
- Default credentials: `admin` / `admin`
- Full Grafana capabilities
- Custom dashboard creation

---

### Pre-built Dashboard Gallery

**Ready-to-use dashboards included:**

1. **Executive Summary**
   - High-level KPIs
   - Success rates
   - System health
   - Cost metrics

2. **QA Operations**
   - Test execution details
   - Device utilization
   - Failure analysis
   - Coverage metrics

3. **DevOps Monitoring**
   - Infrastructure health
   - Performance metrics
   - Error tracking
   - Resource usage

4. **Quality Assurance**
   - Video quality metrics
   - Content validation
   - User experience scores
   - SLA compliance

---

## Advanced Analytics

### Trend Analysis

**Identify patterns over time:**

```sql
-- Grafana query: Test success trend
SELECT
  time_bucket('1 day', timestamp) AS day,
  AVG(CASE WHEN status = 'passed' THEN 1 ELSE 0 END) * 100 AS pass_rate
FROM test_executions
WHERE timestamp > NOW() - INTERVAL '30 days'
GROUP BY day
ORDER BY day
```

### Correlation Analysis

**Find relationships between metrics:**

```python
# Example: Correlate device temperature with test failures
correlation = analytics.correlate(
    metric_a="device_temperature",
    metric_b="test_failure_rate",
    timerange="7d"
)

if correlation > 0.7:
    print("⚠️ High temperature correlates with failures!")
```

---

## Data Export

### Export for Further Analysis

**Get your data in any format:**

```python
from shared.src.services.analytics import AnalyticsExporter

exporter = AnalyticsExporter()

# Export to CSV
exporter.export_to_csv(
    query="test_executions",
    timerange="30d",
    output="test_results_30days.csv"
)

# Export to Excel with charts
exporter.export_to_excel(
    dashboards=["QA Operations", "Device Health"],
    output="monthly_report.xlsx"
)

# Export to JSON for external tools
exporter.export_to_json(
    metrics=["pass_rate", "avg_duration", "device_uptime"],
    output="api_data.json"
)
```

---

## Integration with CI/CD

### Jenkins Integration

```groovy
// Jenkinsfile
pipeline {
    stages {
        stage('Test') {
            steps {
                sh 'python run_tests.py'
            }
        }
        stage('Report Metrics') {
            steps {
                // Metrics automatically sent to Grafana
                grafana.sendMetrics([
                    buildNumber: env.BUILD_NUMBER,
                    testsPassed: env.TESTS_PASSED,
                    testsFailed: env.TESTS_FAILED
                ])
            }
        }
    }
}
```

### GitHub Actions

```yaml
# .github/workflows/test.yml
- name: Run Tests and Report Metrics
  run: |
    python run_tests.py
    # Metrics auto-reported via VirtualPyTest
```

---

## Performance Metrics

### Key Performance Indicators (KPIs)

**Automatically tracked:**

- **MTBF** (Mean Time Between Failures)
- **MTTR** (Mean Time To Resolution)
- **Test Execution Speed**
- **Device Availability**
- **Quality Score** (composite metric)

### SLA Monitoring

```yaml
sla:
  targets:
    device_uptime: 99.5%      # Devices available 99.5% of time
    test_pass_rate: 95%       # 95% of tests pass
    avg_test_duration: 120s   # Tests complete in <2 minutes
    api_response_time: 500ms  # API responds in <500ms
  
  reporting:
    frequency: "daily"
    recipients: ["qa-team@company.com"]
```

---

## Visualization Examples

### Success Rate Gauge

```
┌─────────────────┐
│  Test Pass Rate │
│                 │
│      95.7%      │
│   ████████░░    │
│                 │
│  Target: 95%    │
└─────────────────┘
```

### Execution Timeline

```
Tests/Hour
   30 │           ╭─╮
   25 │     ╭─╮   │ │   ╭─╮
   20 │ ╭─╮ │ │ ╭─╯ │ ╭─╯ │
   15 │ │ │ │ │ │   │ │   │
   10 │ │ │ │ │ │   ╰─╯   │
    5 │ │ │ │ │ │         │
    0 │─┴─┴─┴─┴─┴─────────┴─
      00:00    12:00    24:00
```

---

## Mobile App Integration

**View metrics on the go:**

- Grafana mobile app supported
- Responsive dashboards
- Push notifications for alerts
- Offline access to recent data

---

## Benefits

### 📈 Data-Driven Decisions
Make informed decisions based on real metrics, not gut feeling.

### ⚡ Faster Issue Detection
Spot problems immediately with real-time dashboards and alerts.

### 💰 Prove ROI
Show management exactly how much testing saves in production bugs.

### 🎯 Continuous Improvement
Track improvement over time and identify optimization opportunities.

---

## Next Steps

- 📖 [Test Automation](./test-automation.md) - Generate the metrics
- 📚 [User Guide - Monitoring](../user-guide/monitoring.md) - Set up monitoring
- 🔧 [Technical Docs - Grafana Integration](../technical/architecture/GRAFANA_INTEGRATION.md)
- 🔌 [Integrations](./integrations.md) - Connect other tools

---

**Ready to see your testing metrics?**  
➡️ [Get Started](../get-started/quickstart.md)

