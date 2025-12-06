# API Reference

**Complete API documentation for VirtualPyTest.**

Access the full REST API, OpenAPI specifications, and integration guides.

---

## 📡 REST API Documentation

VirtualPyTest provides a comprehensive REST API for:
- Test execution and management
- Device control and configuration
- Results and analytics
- System administration

### Access API Documentation

#### Interactive API Docs (Recommended)

Browse and test the API directly in your browser:

**Server API:**
- **HTML Docs**: [View in Web Interface](http://localhost:5109/docs)
- **OpenAPI Explorer**: http://localhost:5109/api/docs

**Host API:**
- **HTML Docs**: [View in Web Interface](http://localhost:6109/docs)
- **OpenAPI Explorer**: http://localhost:6109/api/docs

#### OpenAPI Specifications

Download or view the raw OpenAPI specs:

**Server API Specs** (`/docs/api/openapi/specs/`):
- `server-core-system.yaml` - Core API endpoints
- `server-testcase-management.yaml` - Test case CRUD
- `server-campaign-management.yaml` - Campaign management
- `server-device-management.yaml` - Device control
- `server-navigation-management.yaml` - Navigation trees
- `server-requirements-management.yaml` - Requirements
- `server-ai-analysis.yaml` - AI services
- `server-metrics-analytics.yaml` - Analytics
- `server-deployment-scheduling.yaml` - Scheduling
- `server-script-management.yaml` - Script management
- `server-user-interface-management.yaml` - UI management

**Host API Specs** (`/docs/api/openapi/specs/`):
- `host-testcase-execution.yaml` - Test execution
- `host-ai-exploration.yaml` - AI exploration
- `host-verification-suite.yaml` - Verification methods

#### HTML Documentation

Pre-generated HTML docs available in `/docs/api/openapi/docs/`:
- `index.html` - Documentation landing page
- `server-*.html` - Server API docs
- `host-*.html` - Host API docs

---

## 🔑 Authentication

### API Keys

Generate an API key in the web interface:

1. Go to **Settings → API Keys**
2. Click **Generate New Key**
3. Copy and save the key securely

### Using API Keys

```bash
# Include in Authorization header
curl -H "Authorization: Bearer YOUR_API_KEY" \
  http://localhost:5109/api/test-cases
```

### Supabase Auth

For frontend integration, use Supabase authentication:

```typescript
import { supabase } from './supabaseClient';

const { data, error } = await supabase.auth.signInWithPassword({
  email: 'user@example.com',
  password: 'password'
});

// Use session token for API calls
const token = data.session?.access_token;
```

---

## 📝 Quick Start Examples

### Get All Test Cases

```bash
curl -X GET "http://localhost:5109/api/test-cases" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### Execute a Test

```bash
curl -X POST "http://localhost:5109/api/test-execution" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "test_case_id": "tc_001_launch_netflix",
    "device": "android_tv_1",
    "capture_video": true
  }'
```

### Get Test Results

```bash
curl -X GET "http://localhost:5109/api/test-results/123" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### Control a Device

```bash
# Press a key
curl -X POST "http://localhost:6109/api/device/android_tv_1/press-key" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"key": "HOME"}'

# Take screenshot
curl -X GET "http://localhost:6109/api/device/android_tv_1/screenshot" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  --output screenshot.png
```

---

## 🐍 Python SDK

### Import VirtualPyTest Modules

```python
from shared.src.controller_factory import ControllerFactory
from shared.src.services.test_executor import TestExecutor
from shared.src.supabase_manager import SupabaseManager

# Get a device controller
controller = ControllerFactory.get_controller(device="android_tv_1")

# Execute tests
executor = TestExecutor()
result = executor.execute_test_case("tc_001")

# Access database
db = SupabaseManager()
test_cases = db.get_test_cases()
```

### Using the API Client

```python
from shared.src.api.client import VirtualPyTestClient

# Initialize client
client = VirtualPyTestClient(
    server_url="http://localhost:5109",
    api_key="YOUR_API_KEY"
)

# Get test cases
test_cases = client.get_test_cases()

# Execute a test
result = client.execute_test(
    test_case_id="tc_001",
    device="android_tv_1"
)

# Get results
results = client.get_test_results(limit=10)
```

---

## 📚 Postman Collection

Import pre-configured API collections into Postman:

**Collections available:**
- `postman.md` - Postman integration guide
- `postman_phase_summary.md` - API development phases

**Import into Postman:**
1. Open Postman
2. Click **Import**
3. Select files from `/docs/api/`
4. Configure environment variables

---

## 🔗 API Endpoints Overview

### Server API (Port 5109)

#### Test Management
- `GET /api/test-cases` - List all test cases
- `POST /api/test-cases` - Create test case
- `GET /api/test-cases/{id}` - Get test case details
- `PUT /api/test-cases/{id}` - Update test case
- `DELETE /api/test-cases/{id}` - Delete test case

#### Test Execution
- `POST /api/test-execution` - Execute test
- `GET /api/test-execution/{id}` - Get execution status
- `POST /api/test-execution/{id}/stop` - Stop execution

#### Campaigns
- `GET /api/campaigns` - List campaigns
- `POST /api/campaigns` - Create campaign
- `POST /api/campaigns/{id}/execute` - Execute campaign

#### Devices
- `GET /api/devices` - List devices
- `GET /api/devices/{id}/status` - Get device status
- `POST /api/devices/{id}/restart` - Restart device

#### Navigation
- `GET /api/navigation/{model}` - Get navigation tree
- `POST /api/navigation/{model}/nodes` - Add node
- `PUT /api/navigation/{model}/nodes/{id}` - Update node

#### Results & Analytics
- `GET /api/test-results` - List test results
- `GET /api/test-results/{id}` - Get result details
- `GET /api/metrics` - Get system metrics

---

### Host API (Port 6109)

#### Device Control
- `POST /api/device/{name}/press-key` - Press key
- `POST /api/device/{name}/navigate` - Navigate to node
- `GET /api/device/{name}/screenshot` - Capture screenshot

#### Verification
- `POST /api/device/{name}/verify-text` - Verify text on screen
- `POST /api/device/{name}/verify-image` - Verify image present
- `GET /api/device/{name}/detect-black-screen` - Check for black screen

#### AI Services
- `POST /api/ai/analyze-screen` - Analyze screenshot with AI
- `POST /api/ai/generate-test` - Generate test from prompt
- `POST /api/ai/explore` - AI-driven exploration

---

## 🌐 Webhooks

### Configure Webhooks

Receive real-time notifications:

```json
{
  "webhooks": [
    {
      "url": "https://your-service.com/webhook",
      "events": ["test.completed", "test.failed", "device.offline"],
      "secret": "your_webhook_secret"
    }
  ]
}
```

### Webhook Payload Example

```json
{
  "event": "test.completed",
  "timestamp": "2025-11-27T10:30:00Z",
  "data": {
    "test_case_id": "tc_001",
    "device": "android_tv_1",
    "status": "passed",
    "duration": 45.2,
    "screenshots": [
      "https://cdn.virtualpytest.com/screenshots/123.png"
    ]
  }
}
```

---

## 🔒 Security

### Rate Limiting

API requests are rate-limited:
- **Authenticated**: 1000 requests/hour
- **Unauthenticated**: 100 requests/hour

### CORS

Configure allowed origins in `.env`:

```env
CORS_ALLOWED_ORIGINS=http://localhost:3000,https://your-app.com
```

### HTTPS

For production, use HTTPS:
- Configure SSL certificates
- Use reverse proxy (nginx)
- Enable HSTS headers

---

## 📊 Response Formats

### Success Response

```json
{
  "success": true,
  "data": {
    "id": "123",
    "name": "Test Case Name",
    "status": "passed"
  }
}
```

### Error Response

```json
{
  "success": false,
  "error": {
    "code": "TEST_NOT_FOUND",
    "message": "Test case with ID 123 not found",
    "details": {}
  }
}
```

---

## 🚀 Performance Tips

### Pagination

Use pagination for large datasets:

```bash
curl "http://localhost:5109/api/test-results?page=1&limit=50"
```

### Filtering

Filter results:

```bash
curl "http://localhost:5109/api/test-results?status=failed&device=android_tv_1"
```

### Caching

Use ETag headers for caching:

```bash
curl -H "If-None-Match: \"abc123\"" \
  http://localhost:5109/api/test-cases/123
```

---

## 📖 Related Documentation

- **[Features](../features/README.md)** - What the API enables
- **[User Guide](../user-guide/README.md)** - Using the web interface
- **[Technical Docs](../technical/README.md)** - API architecture
- **[Examples](../examples/README.md)** - Code examples

---

## 🆘 Support

- 📧 API Questions: [GitHub Discussions](https://github.com/angelstreet/virtualpytest/discussions)
- 🐛 Report API Bugs: [GitHub Issues](https://github.com/angelstreet/virtualpytest/issues)
- 📖 OpenAPI Specs: `/docs/api/openapi/specs/`

---

**Ready to integrate VirtualPyTest?**  
➡️ [Get Started](../get-started/quickstart.md)



