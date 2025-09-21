# API Testing System

Comprehensive API endpoint testing with HTML report generation for VirtualPyTest system.

## Overview

The API Testing System provides automated testing of all server endpoints with detailed reporting capabilities. It's designed to be minimalist, comprehensive, and suitable for both manual testing and CI/CD integration.

## Components

### 1. Backend Routes (`backend_server/src/routes/server_api_testing_routes.py`)

#### Endpoints:
- `POST /server/api-testing/run` - Execute all API tests
- `POST /server/api-testing/quick` - Run critical endpoints only
- `GET /server/api-testing/config` - Get test configuration
- `GET /server/api-testing/report/:id/html` - Generate HTML report

#### Features:
- Git commit tracking
- Response time measurement
- Expected status code validation
- Comprehensive error handling

### 2. Frontend Hook (`frontend/src/hooks/useApiTesting.ts`)

#### Methods:
- `runAllTests()` - Execute comprehensive test suite
- `runQuickTest()` - Test critical endpoints only
- `downloadHtmlReport()` - Generate and download HTML report
- `getTestConfig()` - Fetch test configuration
- `clearResults()` - Clear test results

#### State Management:
- Real-time progress tracking
- Error handling and display
- Test result storage

### 3. Frontend Page (`frontend/src/pages/configuration/ApiTestingPage.tsx`)

#### Features:
- Clean, minimalist UI similar to OpenRouterDebug
- Live test execution with progress indicators
- Detailed results table with status indicators
- One-click HTML report download
- Color-coded status display (✅ pass, ❌ fail)

### 4. Standalone Script (`api_testing.sh`)

#### Usage:
```bash
./api_testing.sh [quick|full]
```

#### Features:
- Colored terminal output
- Git commit tracking
- HTML report generation
- Perfect for CI/CD pipelines

## Test Coverage

### System Endpoints
- `GET /server/system/health` - Basic health check
- `GET /server/system/status` - System status

### AI Execution Endpoints
- `POST /server/ai-execution/executeTask` - Main AI task execution
- Expected status codes: 200, 202, 400

### Navigation Endpoints
- `GET /server/navigation/getNodes` - Get navigation nodes
- Expected status codes: 200, 404

### Action Endpoints
- `GET /server/action/getActions` - Get available actions
- Expected status codes: 200

### Verification Endpoints
- `GET /server/verification/getVerifications` - Get verifications
- Expected status codes: 200

### Control Endpoints
- `POST /server/control/takeControl` - Take device control
- Expected status codes: 200, 400, 404

## Configuration

### Environment Variables

The system uses environment variables with fallback defaults:

```bash
# .env file or environment variables
SERVER_URL=http://localhost:5109          # Backend server URL
TEAM_ID=7fdeb4bb-3639-4ec3-959f-b54769a219ce  # Default team ID
HOST_NAME=sunri-pi1                       # Default host name
DEVICE_ID=device1                         # Default device ID
```

### Default Values (when env vars not set)
```javascript
BASE_URL = "http://localhost:5109"
TEAM_ID = "7fdeb4bb-3639-4ec3-959f-b54769a219ce"
HOST_NAME = "sunri-pi1"
DEVICE_ID = "device1"
TIMEOUT = 10 seconds
```

### Test Data
```json
{
  "task_description": "go to live",
  "userinterface_name": "horizon_android_mobile",
  "host_name": "sunri-pi1",
  "device_id": "device1"
}
```

## Environment Setup

### Creating .env File

Create a `.env` file in the project root:

```bash
# .env
SERVER_URL=http://localhost:5109
TEAM_ID=7fdeb4bb-3639-4ec3-959f-b54769a219ce
HOST_NAME=sunri-pi1
DEVICE_ID=device1
```

### Frontend Environment

For frontend (Vite), use `VITE_` prefix:

```bash
# .env
VITE_SERVER_URL=http://localhost:5109
```

The frontend automatically uses `buildServerUrl()` which reads `VITE_SERVER_URL`.

### Production Environment

```bash
# Production .env
SERVER_URL=https://virtualpytest.onrender.com
VITE_SERVER_URL=https://virtualpytest.onrender.com
TEAM_ID=your-production-team-id
HOST_NAME=your-production-host
DEVICE_ID=your-production-device
```

## Usage Examples

### Frontend Usage

1. **Navigate to API Testing Page**
   - Similar to OpenRouterDebug page
   - Located in configuration section

2. **Select Endpoints to Test**
   - **Default:** All endpoints selected
   - **Select All:** Click "Select All" button
   - **Deselect All:** Click "Deselect All" button
   - **Individual Selection:** Check/uncheck specific endpoints
   - **Visual Feedback:** Shows selected count (e.g., "5/7 selected")

3. **Run Tests**
   ```typescript
   // Run selected tests (respects checkbox selection)
   await runAllTests();
   
   // Run quick test (critical endpoints only, ignores selection)
   await runQuickTest();
   ```

4. **Download Report**
   ```typescript
   // Generate and download HTML report
   downloadHtmlReport(lastReport);
   ```

### Command Line Usage

1. **Quick Test (Critical Endpoints)**
   ```bash
   ./api_testing.sh quick
   ```

2. **Full Test Suite**
   ```bash
   ./api_testing.sh full
   ```

3. **Make Script Executable**
   ```bash
   chmod +x api_testing.sh
   ```

### API Usage

1. **Execute All Tests**
   ```bash
   curl -X POST ${SERVER_URL:-http://localhost:5109}/server/api-testing/run
   ```

2. **Execute Selected Tests**
   ```bash
   curl -X POST ${SERVER_URL:-http://localhost:5109}/server/api-testing/run \
     -H "Content-Type: application/json" \
     -d '{"selected_endpoints": ["System Health", "AI Task Execution"]}'
   ```

3. **Quick Test**
   ```bash
   curl -X POST ${SERVER_URL:-http://localhost:5109}/server/api-testing/quick
   ```

4. **Get Configuration**
   ```bash
   curl ${SERVER_URL:-http://localhost:5109}/server/api-testing/config
   ```

## Report Format

### JSON Response
```json
{
  "success": true,
  "report": {
    "id": "uuid",
    "timestamp": "2025-09-21T17:00:00Z",
    "git_commit": "abc1234",
    "total_tests": 7,
    "passed": 5,
    "failed": 2,
    "results": [
      {
        "endpoint": "System Health",
        "method": "GET",
        "url": "/server/system/health",
        "status": "pass",
        "status_code": 200,
        "response_time": 45,
        "error": null
      }
    ]
  }
}
```

### HTML Report
- Clean, professional layout
- Git commit and timestamp tracking
- Color-coded results (green/red)
- Detailed error messages
- Response time metrics
- Success rate percentage

## CI/CD Integration

### GitHub Actions Example
```yaml
name: API Tests
on: [push, pull_request]

jobs:
  api-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Start Services
        run: docker-compose up -d
      - name: Wait for Services
        run: sleep 30
      - name: Run API Tests
        run: ./api_testing.sh full
      - name: Upload Report
        if: always()
        uses: actions/upload-artifact@v2
        with:
          name: api-test-report
          path: api-test-report-*.html
```

### Expected Exit Codes
- `0` - All tests passed
- `1` - Some tests failed
- `1` - No tests executed (error)

## Error Handling

### Common Scenarios
- **Network timeouts** - 10 second timeout per request
- **Service unavailable** - Expected 400/404 responses for some endpoints
- **Invalid responses** - Detailed error messages in reports
- **Missing services** - Graceful failure with error reporting

### Status Code Interpretation
- `200` - Success
- `202` - Accepted (async operations)
- `400` - Bad request (expected for some scenarios)
- `404` - Not found (expected for missing resources)
- `500` - Server error (unexpected)

## Development

### Adding New Tests
1. Update `TEST_CONFIG` in `server_api_testing_routes.py`
2. Add endpoint configuration with expected status codes
3. Test configuration is automatically loaded by frontend

### Customizing Reports
- Modify `generate_html_report()` function
- Update CSS styles in HTML template
- Add additional metrics as needed

### Extending Functionality
- Add R2 storage integration for report persistence
- Implement report history and comparison
- Add performance benchmarking
- Include response payload validation

## Troubleshooting

### Common Issues

1. **Connection Refused**
   - Check if server is running on correct port
   - Verify BASE_URL configuration

2. **Tests Timing Out**
   - Increase timeout value
   - Check server performance

3. **Unexpected Status Codes**
   - Review expected_status configuration
   - Check server logs for errors

4. **Script Permission Denied**
   ```bash
   chmod +x api_testing.sh
   ```

### Debug Mode
Enable verbose output by modifying script:
```bash
# Add to api_testing.sh
set -x  # Enable debug mode
```

## Future Enhancements

- **R2 Storage Integration** - Store reports in cloud storage
- **Report History** - Compare test results over time
- **Performance Benchmarks** - Track response time trends
- **Slack/Email Notifications** - Alert on test failures
- **Custom Test Suites** - User-defined test configurations
- **Load Testing** - Concurrent request testing
- **API Documentation Generation** - Auto-generate API docs from tests
