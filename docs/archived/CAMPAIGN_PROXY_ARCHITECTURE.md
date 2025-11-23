# Campaign Proxy Architecture

## Overview

The campaign execution system has been refactored to execute campaigns at the **host level** instead of the server level. This ensures that scripts have proper access to devices and infrastructure while maintaining the same API interface.

## Architecture Flow

```
Frontend/API → Server → Host → Device Script Executors → Scripts
```

### 1. Server Level (Proxy)
- **Location**: `backend_server/src/routes/server_campaign_execution_routes.py`
- **Role**: Receives campaign requests and proxies them to the appropriate host
- **Key Changes**:
  - Validates campaign configuration
  - Determines target host from request
  - Proxies execution to host via `/host/campaigns/execute`
  - Tracks campaign status via callbacks
  - Provides unified API interface

### 2. Host Level (Execution)
- **Location**: `backend_host/src/routes/host_campaign_routes.py`
- **Role**: Executes campaigns using local device infrastructure
- **Key Components**:
  - **Campaign Executor**: `backend_host/src/lib/utils/campaign_executor.py`
  - **Device Script Executors**: Uses existing device script execution infrastructure
  - **Environment Setup**: Proper host-level environment and device access

### 3. Script Execution
- **Method**: Uses device script executors (same as individual script execution)
- **Environment**: Host-level with proper device access
- **Tracking**: Database tracking and report generation maintained

## API Compatibility

The API interface remains **exactly the same**:

```bash
# Start campaign (async)
POST /server/campaigns/execute
{
  "campaign_id": "test-campaign",
  "name": "Test Campaign",
  "host": "sunri-pi1",  # Required for proxy routing
  "script_configurations": [...]
}

# Check status
GET /server/campaigns/status/{execution_id}

# List running campaigns
GET /server/campaigns/running
```

## Key Benefits

1. **Proper Device Access**: Scripts execute on hosts with direct device access
2. **Infrastructure Consistency**: Uses same script execution path as individual scripts
3. **Environment Isolation**: Each host manages its own campaign executions
4. **Scalability**: Multiple hosts can execute campaigns simultaneously
5. **API Compatibility**: No changes required to frontend or API consumers

## Implementation Details

### Server-Side Changes
- Removed direct campaign execution
- Added proxy logic to forward requests to hosts
- Added callback handling for completion notifications
- Enhanced status checking with host polling

### Host-Side Changes
- Added campaign execution routes (`/host/campaigns/*`)
- Moved campaign executor to host level
- Integrated with device script executors
- Added callback notifications to server

### Campaign Executor Changes
- Now runs at host level with proper environment
- Uses device script executors instead of subprocess calls
- Maintains same database tracking and reporting
- Proper error handling and recovery

## Testing

Use the provided test script to verify the proxy flow:

```bash
python test_campaign_proxy.py
```

This tests:
- Campaign execution via proxy
- Status monitoring
- Campaign listing
- End-to-end flow validation

## Migration Notes

### For Existing Campaigns
- No changes required to campaign configurations
- Must specify `host` parameter for proxy routing
- All existing campaign IDs and tracking continue to work

### For Developers
- Campaign executor now at `backend_host/src/lib/utils/campaign_executor.py`
- Server-side campaign executor removed (was at `backend_server/src/lib/utils/campaign_executor.py`)
- Host routes registered in `backend_host/src/app.py`

## Error Handling

The system provides comprehensive error handling:

1. **Server-Level Errors**: Host not found, proxy failures
2. **Host-Level Errors**: Device not found, script execution failures  
3. **Script-Level Errors**: Individual script failures with continue/stop logic
4. **Network Errors**: Timeout handling and retry logic

## Monitoring

Campaign execution can be monitored at multiple levels:

1. **Server Level**: Overall campaign status and proxy health
2. **Host Level**: Individual campaign execution details
3. **Script Level**: Individual script execution results and reports
4. **Database Level**: Complete execution history and analytics
