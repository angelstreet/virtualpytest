# API Testing Endpoints Configuration

Complete guide for managing and extending API endpoint testing in VirtualPyTest.

## Current Endpoint Coverage

### ✅ Currently Tested (7 endpoints)
- System Health (`GET /server/system/health`)
- System Status (`GET /server/system/status`) 
- AI Task Execution (`POST /server/ai-execution/executeTask`)
- Get Navigation Nodes (`GET /server/navigation/getNodes`)
- Get Actions (`GET /server/action/getActions`)
- Get Verifications (`GET /server/verification/getVerifications`)
- Take Control (`POST /server/control/takeControl`)

### 📋 Available Server Routes (35+ route files)

Based on `backend_server/src/routes/` directory:

#### **Core System Routes**
- `server_system_routes.py` - System health, status, metrics
- `server_core_routes.py` - Core functionality
- `server_frontend_routes.py` - Frontend-specific routes
- `server_monitoring_routes.py` - System monitoring

#### **Device & Control Routes**
- `server_control_routes.py` - Device control (take/release)
- `server_device_routes.py` - Device management
- `server_remote_routes.py` - Remote device operations
- `server_power_routes.py` - Power management

#### **Navigation & Pathfinding Routes**
- `server_navigation_routes.py` - Navigation operations
- `server_navigation_trees_routes.py` - Navigation tree management
- `server_navigation_execution_routes.py` - Navigation execution
- `server_pathfinding_routes.py` - Pathfinding algorithms

#### **Action & Verification Routes**
- `server_actions_routes.py` - Action execution
- `server_verification_routes.py` - Verification operations
- `server_validation_routes.py` - Validation services

#### **AI & Testing Routes**
- `server_ai_execution_routes.py` - AI task execution
- `server_ai_testcase_routes.py` - AI test case management
- `server_ai_generation_routes.py` - AI plan generation
- `server_ai_tools_routes.py` - AI tools and utilities
- `server_ai_queue_routes.py` - AI task queuing

#### **Campaign & Script Routes**
- `server_campaign_routes.py` - Campaign management
- `server_campaign_execution_routes.py` - Campaign execution
- `server_campaign_results_routes.py` - Campaign results
- `server_script_routes.py` - Script management
- `server_script_results_routes.py` - Script results
- `server_testcase_routes.py` - Test case management

#### **Media & Stream Routes**
- `server_stream_proxy_routes.py` - Stream proxying
- `server_av_routes.py` - Audio/video operations
- `server_web_routes.py` - Web interface routes

#### **Desktop & Automation Routes**
- `server_desktop_bash_routes.py` - Desktop bash operations
- `server_desktop_pyautogui_routes.py` - Desktop automation

#### **Data & Analytics Routes**
- `server_metrics_routes.py` - Metrics collection
- `server_heatmap_routes.py` - Heatmap generation
- `server_execution_results_routes.py` - Execution results
- `server_alerts_routes.py` - Alert management

#### **Configuration Routes**
- `server_userinterface_routes.py` - User interface config
- `server_devicemodel_routes.py` - Device model config
- `server_translation_routes.py` - Translation services
- `server_restart_routes.py` - System restart operations

## Adding New Endpoints

### 1. Update Test Configuration

Edit `backend_server/src/routes/server_api_testing_routes.py`:

```python
TEST_CONFIG = {
    "endpoints": [
        # Existing endpoints...
        
        # Add new endpoint
        {
            "name": "Campaign Management",
            "method": "GET",
            "url": "/server/campaign/getCampaigns",
            "params": {"team_id": "7fdeb4bb-3639-4ec3-959f-b54769a219ce"},
            "expected_status": [200, 404]
        },
        {
            "name": "Create Campaign",
            "method": "POST",
            "url": "/server/campaign/createCampaign",
            "body": {
                "name": "Test Campaign",
                "description": "API Test Campaign"
            },
            "params": {"team_id": "7fdeb4bb-3639-4ec3-959f-b54769a219ce"},
            "expected_status": [200, 201, 400]
        }
    ]
}
```

### 2. Endpoint Configuration Schema

Each endpoint configuration supports:

```python
{
    "name": "Human-readable name",           # Required: Display name
    "method": "GET|POST|PUT|DELETE",         # Required: HTTP method
    "url": "/server/path/endpoint",          # Required: Endpoint path
    "expected_status": [200, 201, 400],      # Required: Expected status codes
    "body": {...},                           # Optional: Request body (POST/PUT)
    "params": {...},                         # Optional: Query parameters
    "headers": {...}                         # Optional: Custom headers
}
```

### 3. Default Values for Common Endpoints

#### **Standard Query Parameters**
```python
# Most endpoints need team_id
"params": {"team_id": "7fdeb4bb-3639-4ec3-959f-b54769a219ce"}

# Device-specific endpoints
"params": {
    "team_id": "7fdeb4bb-3639-4ec3-959f-b54769a219ce",
    "device_model": "android_mobile",
    "host_name": "sunri-pi1",
    "device_id": "device1"
}
```

#### **Standard Request Bodies**
```python
# Campaign creation
"body": {
    "name": "API Test Campaign",
    "description": "Automated API testing campaign",
    "userinterface_name": "horizon_android_mobile"
}

# Script execution
"body": {
    "script_name": "test_script",
    "host_name": "sunri-pi1",
    "device_id": "device1"
}

# AI task execution
"body": {
    "task_description": "go to live",
    "userinterface_name": "horizon_android_mobile",
    "host_name": "sunri-pi1",
    "device_id": "device1"
}
```

### 4. Expected Status Codes Guide

#### **Success Codes**
- `200` - OK (GET, PUT, DELETE)
- `201` - Created (POST)
- `202` - Accepted (Async operations)

#### **Expected Error Codes**
- `400` - Bad Request (Invalid data, missing host)
- `404` - Not Found (Resource doesn't exist)
- `409` - Conflict (Resource already exists)
- `422` - Unprocessable Entity (Validation errors)

#### **Unexpected Error Codes**
- `500` - Internal Server Error (Should be investigated)
- `503` - Service Unavailable (System issues)

## Comprehensive Endpoint List

### High Priority Endpoints (Should be tested)

```python
# System & Health
{"name": "System Health", "method": "GET", "url": "/server/system/health", "expected_status": [200]},
{"name": "System Status", "method": "GET", "url": "/server/system/status", "expected_status": [200]},
{"name": "System Metrics", "method": "GET", "url": "/server/system/metrics", "expected_status": [200]},

# Device Control
{"name": "Get Locked Devices", "method": "GET", "url": "/server/control/lockedDevices", "expected_status": [200]},
{"name": "Take Control", "method": "POST", "url": "/server/control/takeControl", "expected_status": [200, 400, 404]},
{"name": "Release Control", "method": "POST", "url": "/server/control/releaseControl", "expected_status": [200, 400]},

# Navigation
{"name": "Get Navigation Nodes", "method": "GET", "url": "/server/navigation/getNodes", "expected_status": [200, 404]},
{"name": "Execute Navigation", "method": "POST", "url": "/server/navigation/executeNavigation", "expected_status": [200, 400]},

# Actions & Verifications
{"name": "Get Actions", "method": "GET", "url": "/server/action/getActions", "expected_status": [200]},
{"name": "Execute Actions", "method": "POST", "url": "/server/action/executeBatch", "expected_status": [200, 400]},
{"name": "Get Verifications", "method": "GET", "url": "/server/verification/getVerifications", "expected_status": [200]},

# AI Operations
{"name": "AI Task Execution", "method": "POST", "url": "/server/ai-execution/executeTask", "expected_status": [200, 202, 400]},
{"name": "AI Generation", "method": "POST", "url": "/server/ai-generation/generatePlan", "expected_status": [200, 400]},

# Campaign Management
{"name": "Get Campaigns", "method": "GET", "url": "/server/campaign/getCampaigns", "expected_status": [200]},
{"name": "Create Campaign", "method": "POST", "url": "/server/campaign/createCampaign", "expected_status": [200, 201, 400]},

# Script Management
{"name": "Get Scripts", "method": "GET", "url": "/server/script/getScripts", "expected_status": [200]},
{"name": "Execute Script", "method": "POST", "url": "/server/script/executeScript", "expected_status": [200, 202, 400]},
```

### Medium Priority Endpoints

```python
# Configuration
{"name": "Get User Interfaces", "method": "GET", "url": "/server/userinterface/getUserInterfaces", "expected_status": [200]},
{"name": "Get Device Models", "method": "GET", "url": "/server/devicemodel/getDeviceModels", "expected_status": [200]},

# Monitoring & Metrics
{"name": "Get Metrics", "method": "GET", "url": "/server/metrics/getMetrics", "expected_status": [200]},
{"name": "Get Alerts", "method": "GET", "url": "/server/alerts/getAlerts", "expected_status": [200]},

# Results & Analytics
{"name": "Get Execution Results", "method": "GET", "url": "/server/execution-results/getResults", "expected_status": [200]},
{"name": "Get Script Results", "method": "GET", "url": "/server/script-results/getResults", "expected_status": [200]},
```

## Environment-Specific Default Values

### Development Environment
```python
DEFAULT_VALUES = {
    "team_id": "7fdeb4bb-3639-4ec3-959f-b54769a219ce",
    "host_name": "sunri-pi1", 
    "device_id": "device1",
    "device_model": "android_mobile",
    "userinterface_name": "horizon_android_mobile"
}
```

### Production Environment
```python
DEFAULT_VALUES = {
    "team_id": os.getenv("PRODUCTION_TEAM_ID"),
    "host_name": os.getenv("PRODUCTION_HOST_NAME"),
    "device_id": os.getenv("PRODUCTION_DEVICE_ID"),
    "device_model": "android_mobile",
    "userinterface_name": "horizon_android_mobile"
}
```

## Testing Categories

### 1. **Critical Endpoints** (Must always work)
- System health/status
- Device control (take/release)
- Basic navigation
- AI task execution

### 2. **Core Functionality** (Should work)
- Actions and verifications
- Campaign management
- Script execution
- Configuration endpoints

### 3. **Advanced Features** (Nice to have)
- Analytics and metrics
- Heatmap generation
- Advanced AI features
- Stream proxying

## Maintenance Guidelines

### 1. **Regular Updates**
- Review route files monthly for new endpoints
- Update test configuration when new routes are added
- Verify expected status codes match actual behavior

### 2. **Default Value Management**
- Use environment variables for team/host/device IDs
- Provide sensible defaults for development
- Document required vs optional parameters

### 3. **Error Handling**
- Test both success and expected failure scenarios
- Document which error codes are expected vs unexpected
- Include timeout handling for slow endpoints

### 4. **Performance Considerations**
- Group related endpoints for efficient testing
- Use quick test mode for critical endpoints only
- Consider endpoint dependencies (some require others to work)

## Implementation Checklist

- [ ] Audit all route files for available endpoints
- [ ] Categorize endpoints by priority (critical/core/advanced)
- [ ] Define default values for common parameters
- [ ] Update TEST_CONFIG with comprehensive endpoint list
- [ ] Test endpoint selection UI with larger endpoint list
- [ ] Document expected vs unexpected error codes
- [ ] Add environment-specific configuration
- [ ] Create endpoint dependency mapping
- [ ] Implement endpoint grouping/categories in UI
- [ ] Add performance metrics and timeout handling
