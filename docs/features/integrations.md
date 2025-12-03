# 🔌 Integrations

**Connect VirtualPyTest to your existing tools.**

Seamless integration with JIRA, Grafana, CI/CD pipelines, and more. Export data, sync requirements, and integrate with your workflow.

---

## Available Integrations

### 🎫 JIRA

**Sync test cases, requirements, and defects.**

**Features:**
- Bi-directional sync
- Automatic defect creation
- Requirement traceability
- Test execution updates

**Setup:**
```bash
# Configure JIRA credentials
backend_server/config/integrations/jira_instances.json
```

**Configuration:**
```json
{
  "instances": [
    {
      "name": "company_jira",
      "url": "https://your-company.atlassian.net",
      "username": "your-email@company.com",
      "api_token": "your-api-token",
      "project_key": "QA"
    }
  ]
}
```

**Use cases:**
- Create JIRA issues for test failures
- Sync test cases with JIRA test management
- Link requirements to test cases
- Update story status based on test results

**Learn more:** [JIRA Integration Guide](../integrations/JIRA_INTEGRATION.md)

---

### 📊 Grafana

**Real-time dashboards and analytics.**

**Features:**
- Pre-built dashboards
- Custom metrics
- Alerting
- Data visualization

**Access:**
- **Web Interface**: Plugins → Grafana
- **Direct Access**: http://localhost:3001

**Available Dashboards:**
1. Test Execution Metrics
2. Device Health Monitoring
3. Video Quality Analytics
4. System Performance

**Use cases:**
- Monitor test pass rates
- Track device uptime
- Alert on failures
- Executive reporting

**Learn more:** [Grafana Integration](../technical/architecture/GRAFANA_INTEGRATION.md)

---

### 🔄 CI/CD Pipelines

**Integrate with your DevOps workflow.**

#### GitHub Actions

```yaml
name: VirtualPyTest

on: [push]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Run VirtualPyTest
        run: |
          python test_scripts/validation.py
          
      - name: Upload Results
        if: always()
        uses: actions/upload-artifact@v2
        with:
          name: test-results
          path: test_results/
```

#### Jenkins

```groovy
pipeline {
    agent any
    stages {
        stage('Test') {
            steps {
                sh 'python test_scripts/fullzap.py'
            }
        }
    }
    post {
        always {
            junit 'test_results/*.xml'
            publishHTML([
                reportName: 'VirtualPyTest Report',
                reportDir: 'test_results',
                reportFiles: 'report.html'
            ])
        }
    }
}
```

#### GitLab CI

```yaml
test:
  script:
    - python test_scripts/validation.py
  artifacts:
    reports:
      junit: test_results/junit.xml
    paths:
      - test_results/
```

---

### 📧 Slack / Microsoft Teams

**Real-time notifications.**

**Features:**
- Test completion notifications
- Failure alerts
- Device status updates
- Daily summaries

**Setup:**
```python
# Configure webhook in settings
{
  "slack": {
    "webhook_url": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
    "channel": "#qa-alerts",
    "notify_on": ["failure", "success", "device_offline"]
  }
}
```

**Message Examples:**
```
✅ Test Campaign "Nightly Regression" completed
   - 45/50 tests passed (90%)
   - Duration: 32 minutes
   - View Report: https://virtualpytest.com/reports/123
```

```
❌ Critical: android_tv_1 offline
   - Last seen: 5 minutes ago
   - Action required
```

---

### 📁 Cloud Storage

**Store screenshots and videos in the cloud.**

#### Cloudflare R2

```env
CLOUDFLARE_R2_ENDPOINT=https://xxx.r2.cloudflarestorage.com
CLOUDFLARE_R2_ACCESS_KEY_ID=your_key
CLOUDFLARE_R2_SECRET_ACCESS_KEY=your_secret
CLOUDFLARE_R2_PUBLIC_URL=https://pub-xxx.r2.dev
```

#### AWS S3

```env
AWS_S3_BUCKET=virtualpytest-captures
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_REGION=us-east-1
```

#### Google Cloud Storage

```env
GCS_BUCKET=virtualpytest-captures
GCS_PROJECT_ID=your-project
GCS_CREDENTIALS_FILE=/path/to/credentials.json
```

---

### 🗄️ Databases

**Export test data to external databases.**

#### PostgreSQL

```python
# Custom data export
from shared.src.services.data_exporter import DataExporter

exporter = DataExporter(connection_string="postgresql://...")
exporter.export_test_results(timerange="30d")
```

#### MySQL

```python
exporter = DataExporter(connection_string="mysql://...")
exporter.export_device_metrics(timerange="7d")
```

---

### 📊 Data Analytics Tools

#### Tableau

```python
# Export data in Tableau-friendly format
from shared.src.services.analytics import AnalyticsExporter

exporter = AnalyticsExporter()
exporter.export_for_tableau(
    metrics=["pass_rate", "duration", "device_uptime"],
    output="tableau_data.csv"
)
```

#### Power BI

```python
# Export to Power BI compatible format
exporter.export_for_powerbi(
    dashboard="Test Execution",
    output="powerbi_data.xlsx"
)
```

---

### 🔐 SSO / Authentication

#### SAML Integration

```yaml
authentication:
  method: "saml"
  idp_url: "https://your-idp.com/saml"
  entity_id: "virtualpytest"
  certificate: "/path/to/cert.pem"
```

#### OAuth 2.0

```yaml
authentication:
  method: "oauth2"
  provider: "google"  # or "github", "okta"
  client_id: "your_client_id"
  client_secret: "your_client_secret"
```

---

### 📱 Mobile Device Clouds

#### BrowserStack

```python
# Use BrowserStack devices
controller = ControllerFactory.get_controller(
    device="browserstack_android",
    capabilities={
        "deviceName": "Samsung Galaxy S21",
        "osVersion": "11.0",
        "browserstack.user": "your_user",
        "browserstack.key": "your_key"
    }
)
```

#### Sauce Labs

```python
# Use Sauce Labs devices
controller = ControllerFactory.get_controller(
    device="saucelabs_ios",
    capabilities={
        "deviceName": "iPhone 13",
        "platformVersion": "15.0",
        "username": "your_user",
        "accessKey": "your_key"
    }
)
```

---

### 🤖 AI Services

#### OpenRouter

**Already integrated for AI-powered validation.**

```env
OPENROUTER_API_KEY=your_key
```

Provides access to:
- GPT-4 Vision
- Claude 3.5 Sonnet
- And 100+ other models

#### Custom AI Endpoints

```python
# Use your own AI service
from shared.src.services.ai_analyzer import AIAnalyzer

analyzer = AIAnalyzer(
    endpoint="https://your-ai-service.com/api",
    api_key="your_key"
)
```

---

### 📡 IoT & Smart Home

#### Tapo Smart Plugs

**Control device power remotely.**

```python
from shared.src.services.power_manager import TapoController

# Power cycle a device
power = TapoController(
    ip="192.168.1.50",
    email="your_email",
    password="your_password"
)

power.turn_off()
time.sleep(10)
power.turn_on()
```

#### Other Smart Devices

- Home Assistant integration
- Zigbee device control
- IR transmitter control

---

## API Access

### REST API

**Full API access for custom integrations.**

**Documentation:**
- **Web Interface**: Docs → API Reference
- **OpenAPI Specs**: `/docs/api/openapi/`

**Example:**
```bash
# Get test results
curl -X GET "http://localhost:5109/api/test-results" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Create test execution
curl -X POST "http://localhost:5109/api/test-execution" \
  -H "Content-Type: application/json" \
  -d '{
    "test_case_id": "tc_001",
    "device": "android_tv_1"
  }'
```

---

### Webhooks

**Get notified of events.**

```python
# Configure webhooks
{
  "webhooks": [
    {
      "url": "https://your-service.com/webhook",
      "events": ["test.completed", "device.offline"],
      "secret": "your_webhook_secret"
    }
  ]
}
```

**Event Examples:**
- `test.started`
- `test.completed`
- `test.failed`
- `device.online`
- `device.offline`
- `alert.triggered`

---

## Custom Integrations

### Create Your Own

VirtualPyTest is designed to be extensible:

1. **Use the REST API** - Full programmatic access
2. **Database access** - Direct Supabase queries
3. **Webhook listeners** - React to events
4. **Python SDK** - Import VirtualPyTest modules

**Example Custom Integration:**
```python
from shared.src.services.test_executor import TestExecutor
from your_custom_service import CustomService

class CustomIntegration:
    def __init__(self):
        self.executor = TestExecutor()
        self.custom_service = CustomService()
        
    def sync_results(self):
        results = self.executor.get_recent_results()
        self.custom_service.upload(results)
```

---

## Benefits

### 🔗 Seamless Workflow
Integrate with tools you already use. No need to change your processes.

### 📊 Centralized Data
All test data accessible from your favorite analytics tools.

### ⚡ Automation
Trigger tests from CI/CD, get results in Slack, create JIRA tickets automatically.

### 🎯 Flexibility
Use pre-built integrations or create your own with the API.

---

## Next Steps

- 📖 [JIRA Integration Guide](../integrations/JIRA_INTEGRATION.md)
- 📖 [API Reference](../api/README.md)
- 📚 [User Guide](../user-guide/README.md)
- 🔧 [Technical Docs](../technical/README.md)

---

**Ready to connect VirtualPyTest to your workflow?**  
➡️ [Get Started](../get-started/quickstart.md)


