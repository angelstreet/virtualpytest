# Script & Campaign Execution Architecture

## Overview

The VirtualPyTest framework provides unified script and campaign execution through shared executors that can run on both server and host environments. This architecture separates execution logic from device management for better flexibility and reusability.

## Architecture

### Shared Executors Location
```
shared/src/lib/executors/
├── __init__.py
├── script_executor.py      # Core script execution logic
└── campaign_executor.py    # Campaign orchestration logic
```

### Key Components

#### 1. ScriptExecutor (Shared)
- **Location**: `shared/src/lib/executors/script_executor.py`
- **Purpose**: Core script execution with real-time output streaming
- **Features**:
  - Python script execution via subprocess
  - AI test case redirection
  - Real-time output capture
  - Report URL extraction
  - Environment variable handling

#### 2. CampaignExecutor (Shared)
- **Location**: `shared/src/lib/executors/campaign_executor.py`
- **Purpose**: Multi-script campaign orchestration
- **Features**:
  - Sequential script execution
  - Database tracking
  - Error handling and recovery
  - Execution statistics

#### 3. ScriptExecutor (Framework)
- **Location**: `backend_host/src/lib/utils/script_utils.py`
- **Purpose**: Framework wrapper for test scripts
- **Features**:
  - Device integration
  - Navigation tree loading
  - Screenshot/video capture
  - Report generation

## Usage Patterns

### 1. Direct Script Execution

#### Server Route
```python
# backend_server/src/routes/server_script_routes.py
from shared.src.lib.executors.script_executor import ScriptExecutor

executor = ScriptExecutor(host_name, device_id, device_model)
result = executor.execute_script(script_name, parameters)
```

#### Host Route
```python
# backend_host/src/routes/host_script_routes.py
from shared.src.lib.executors.script_executor import ScriptExecutor

executor = ScriptExecutor(host_name, device_id, device_model)
result = executor.execute_script(script_name, parameters)
```

### 2. Campaign Execution

#### Server Route
```python
# backend_server/src/routes/server_campaign_execution_routes.py
from shared.src.lib.executors.campaign_executor import CampaignExecutor

executor = CampaignExecutor()
result = executor.execute_campaign(campaign_config)
```

#### Host Route
```python
# backend_host/src/routes/host_campaign_routes.py
from shared.src.lib.executors.campaign_executor import CampaignExecutor

executor = CampaignExecutor()
result = executor.execute_campaign(campaign_config)
```

### 3. Test Script Framework

#### Script Implementation
```python
# test_scripts/example_script.py
from backend_host.src.lib.utils.script_utils import ScriptExecutor

def main():
    executor = ScriptExecutor("script_name", "Description")
    
    # Parse arguments
    parser = executor.create_argument_parser()
    args = parser.parse_args()
    
    # Setup execution context with device
    context = executor.setup_execution_context(args, enable_db_tracking=True)
    if context.error_message:
        executor.cleanup_and_exit(context, args.userinterface_name)
        return
    
    try:
        # Your script logic here
        # Device available as context.selected_device
        # Script executor available as context.script_executor
        
        context.overall_success = True
        
    except KeyboardInterrupt:
        handle_keyboard_interrupt("script_name")
    except Exception as e:
        handle_unexpected_error("script_name", e)
    finally:
        executor.cleanup_and_exit(context, args.userinterface_name)
```

## Configuration

### Script Execution Context

The framework automatically provides:

- **Host Instance**: `context.host`
- **Selected Device**: `context.selected_device`
- **Script Executor**: `context.script_executor`
- **Team ID**: `context.team_id`
- **Navigation Tree**: `context.tree_data`, `context.nodes`, `context.edges`

### Campaign Configuration

```python
campaign_config = {
    "campaign_id": "example-campaign",
    "name": "Example Campaign",
    "description": "Execute multiple scripts in sequence",
    "userinterface_name": "horizon_android_mobile",
    "host": "auto",
    "device": "auto",
    "execution_config": {
        "continue_on_failure": True,
        "timeout_minutes": 60,
        "parallel": False
    },
    "script_configurations": [
        {
            "script_name": "script1.py",
            "script_type": "navigation",
            "parameters": {
                "node": "home",
                "timeout": 30
            }
        },
        {
            "script_name": "script2.py",
            "script_type": "validation",
            "parameters": {
                "check_audio": True,
                "check_video": True
            }
        }
    ]
}
```

## Environment Variables

### Required
- `TEAM_ID`: Team identifier (defaults to `7fdeb4bb-3639-4ec3-959f-b54769a219ce`)
- `PROJECT_ROOT`: Project root directory (auto-detected if not set)

### Optional
- `AI_SCRIPT_NAME`: For AI test case redirection
- `CLOUDFLARE_R2_PUBLIC_URL`: For report URL generation

## Database Integration

### Script Results
- **Table**: `script_results`
- **Tracking**: Execution start, completion, success/failure
- **Metadata**: Device info, execution time, report URLs

### Campaign Results
- **Table**: `campaign_executions`
- **Tracking**: Campaign start, completion, script results
- **Statistics**: Total/successful/failed script counts

## Error Handling

### Script Level
- **Timeout**: 1 hour default timeout
- **Recovery**: Single recovery attempt for navigation failures
- **Reporting**: Detailed error messages and stack traces

### Campaign Level
- **Continue on Failure**: Configurable behavior
- **Error Aggregation**: Collect all script failures
- **Rollback**: No automatic rollback (stateless execution)

## Video & Screenshot Capture

### Automatic Capture
- **Initial Screenshot**: Captured at script start
- **Step Screenshots**: Captured during navigation
- **Final Screenshot**: Captured at script end
- **Execution Video**: Full test execution recording

### Video Compression
- **Method**: HLS segments → MP4 compression
- **Tool**: VideoCompressionUtils
- **Quality**: Medium compression (configurable)
- **Upload**: Automatic R2 upload with public URLs

## Report Generation

### Components
- **HTML Report**: Detailed execution report with screenshots
- **Execution Logs**: Complete stdout/stderr capture
- **Video**: Test execution recording
- **Database**: Structured execution data

### Upload
- **Storage**: Cloudflare R2
- **URLs**: Public URLs for easy access
- **Retention**: Configurable retention policies

## Migration Notes

### From Device-Specific Executors
- **Old**: `device.script_executor.execute_script()`
- **New**: `context.script_executor.execute_script()`

### From Host-Specific Campaign Executor
- **Old**: `backend_host.src.lib.utils.campaign_executor`
- **New**: `shared.src.lib.executors.campaign_executor`

## Best Practices

### Script Development
1. Use the framework's ScriptExecutor for consistency
2. Enable database tracking for production scripts
3. Handle keyboard interrupts gracefully
4. Provide meaningful error messages

### Campaign Design
1. Keep scripts independent and stateless
2. Use continue_on_failure for resilient campaigns
3. Set appropriate timeouts
4. Group related scripts logically

### Error Handling
1. Fail fast for configuration errors
2. Retry transient failures
3. Log detailed error information
4. Provide actionable error messages

## Troubleshooting

### Common Issues

#### Script Not Found
```
ValueError: Script not found: /path/to/script.py
```
**Solution**: Ensure script exists in `test_scripts/` directory

#### Device Not Available
```
Device device1 not found. Available: ['host']
```
**Solution**: Check device configuration and ensure device is properly configured

#### Navigation Tree Not Found
```
User interface 'horizon_android_mobile' not found
```
**Solution**: Verify team_id and ensure userinterface exists in database

#### Video Compression Failed
```
Video compression failed: FFmpeg failed
```
**Solution**: Check FFmpeg installation and HLS segment availability

### Debug Commands

```bash
# Test shared script executor
python3 -c "
from shared.src.lib.executors.script_executor import ScriptExecutor
executor = ScriptExecutor('test-host', 'device1', 'android_mobile')
print('✅ ScriptExecutor created successfully')
"

# Test campaign executor
python3 -c "
from shared.src.lib.executors.campaign_executor import CampaignExecutor
executor = CampaignExecutor()
print('✅ CampaignExecutor created successfully')
"

# Check available userinterfaces
python3 -c "
from shared.src.lib.supabase.userinterface_db import get_all_userinterfaces
interfaces = get_all_userinterfaces('7fdeb4bb-3639-4ec3-959f-b54769a219ce')
print(f'Available interfaces: {[ui[\"name\"] for ui in interfaces]}')
"
```

## API Reference

### ScriptExecutor Methods
- `execute_script(script_name, parameters)`: Execute a script
- `set_team_id(team_id)`: Set team context
- `get_device_info_for_report()`: Get device info for reports
- `get_host_info_for_report()`: Get host info for reports

### CampaignExecutor Methods
- `execute_campaign(campaign_config)`: Execute a campaign
- `_setup_campaign_environment()`: Setup execution environment
- `_execute_single_script()`: Execute individual script

### Framework ScriptExecutor Methods
- `create_argument_parser()`: Create argument parser
- `setup_execution_context()`: Setup execution context
- `load_navigation_tree()`: Load navigation tree
- `execute_navigation_sequence()`: Execute navigation steps
- `generate_final_report()`: Generate execution report
- `cleanup_and_exit()`: Cleanup and exit

## Future Enhancements

### Planned Features
- **Parallel Campaign Execution**: Execute scripts in parallel
- **Dynamic Device Selection**: Smart device selection based on availability
- **Enhanced Error Recovery**: Multi-level recovery strategies
- **Real-time Monitoring**: Live execution monitoring dashboard
- **Resource Management**: CPU/memory usage optimization

### Architecture Improvements
- **Plugin System**: Extensible executor plugins
- **Event System**: Execution event broadcasting
- **Caching Layer**: Execution result caching
- **Load Balancing**: Distribute execution across hosts
