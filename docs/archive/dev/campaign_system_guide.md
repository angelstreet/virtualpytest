# Test Campaign System Guide

This guide explains how to use the new Test Campaign System to execute multiple scripts in sequence and track their results in the database.

## 🎯 Overview

The Campaign System allows you to:
- Execute multiple scripts (like `fullzap.py`) in sequence
- Track campaign execution results in the database
- Map individual script results to campaign results
- Generate comprehensive reports for campaign executions
- Execute campaigns via API or command line

## 📊 Database Schema

The system adds two new tables:

### `campaign_results`
Tracks overall campaign executions with:
- Campaign metadata (id, name, description)
- Execution status and timing
- Script execution statistics
- Overall success/failure status

### `campaign_script_executions`  
Maps individual script executions to campaigns with:
- Links to both campaign_results and script_results
- Execution order and configuration
- Individual script status and timing

## 🚀 Usage Examples

### 1. Command Line Execution

#### Execute the pre-built double fullzap campaign:
```bash
# Basic execution with default interface
python test_scripts/campaign_fullzap_double.py

# Specify interface and host/device
python test_scripts/campaign_fullzap_double.py horizon_android_mobile --host host1 --device device2
```

#### Test the campaign system:
```bash
# Run system tests
python test_scripts/test_campaign_system.py

# Test with specific interface
python test_scripts/test_campaign_system.py horizon_android_mobile
```

### 2. Programmatic Usage

```python
from shared.lib.utils.campaign_executor import CampaignExecutor

# Create campaign configuration
campaign_config = {
    "campaign_id": "my-test-campaign",
    "name": "My Test Campaign",
    "description": "Execute fullzap.py twice with different parameters",
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
            "script_name": "fullzap.py",
            "script_type": "fullzap",
            "parameters": {
                "action": "live_chup",
                "max_iteration": 5,
                "goto_live": True
            }
        },
        {
            "script_name": "fullzap.py",
            "script_type": "fullzap", 
            "parameters": {
                "action": "live_chdown",
                "max_iteration": 3,
                "goto_live": False
            }
        }
    ]
}

# Execute campaign
executor = CampaignExecutor()
result = executor.execute_campaign(campaign_config)

if result["success"]:
    print(f"Campaign completed! {result['successful_scripts']}/{result['total_scripts']} scripts successful")
    print(f"Campaign Result ID: {result['campaign_result_id']}")
else:
    print(f"Campaign failed: {result['error']}")
```

### 3. API Usage

#### Execute Campaign (Asynchronous)
```bash
curl -X POST http://localhost:5000/server/campaigns/execute \
  -H "Content-Type: application/json" \
  -H "X-User-ID: your-user-id" \
  -d '{
    "campaign_id": "api-test-campaign",
    "name": "API Test Campaign",
    "description": "Campaign executed via API",
    "userinterface_name": "horizon_android_mobile",
    "async": true,
    "script_configurations": [
      {
        "script_name": "fullzap.py",
        "script_type": "fullzap",
        "parameters": {
          "action": "live_chup",
          "max_iteration": 3
        }
      },
      {
        "script_name": "fullzap.py",
        "script_type": "fullzap",
        "parameters": {
          "action": "live_chdown", 
          "max_iteration": 2
        }
      }
    ]
  }'
```

#### Check Campaign Status
```bash
curl http://localhost:5000/server/campaigns/status/campaign_exec_1234567890_abcdef12 \
  -H "X-User-ID: your-user-id"
```

#### Get Campaign Results
```bash
# Get all campaign results
curl http://localhost:5000/server/campaigns/results \
  -H "X-User-ID: your-user-id"

# Get specific campaign result details
curl http://localhost:5000/server/campaigns/results/uuid-campaign-result-id \
  -H "X-User-ID: your-user-id"
```

## 📋 Campaign Configuration

### Required Fields
- `campaign_id`: Unique identifier for the campaign
- `name`: Human-readable campaign name  
- `script_configurations`: Array of script configurations to execute

### Optional Fields
- `description`: Campaign description
- `userinterface_name`: Interface to use (default: "horizon_android_mobile")
- `host`: Host to use (default: "auto")
- `device`: Device to use (default: "auto")
- `execution_config`: Execution configuration object

### Execution Config Options
- `continue_on_failure`: Continue executing scripts even if one fails (default: true)
- `timeout_minutes`: Total campaign timeout in minutes (default: 60)
- `parallel`: Execute scripts in parallel (default: false, not yet implemented)

### Script Configuration
Each script configuration supports:
- `script_name`: Name of the script file (e.g., "fullzap.py")
- `script_type`: Type identifier for the script (e.g., "fullzap")
- `description`: Optional description of what this script does
- `parameters`: Dictionary of script-specific parameters

## 📊 Database Queries

### Get Campaign Results
```python
from shared.lib.supabase.campaign_results_db import get_campaign_results

# Get all campaign results for a team
results = get_campaign_results(team_id="your-team-id")

# Filter by campaign_id or status
results = get_campaign_results(
    team_id="your-team-id",
    campaign_id="specific-campaign",
    status="completed"
)
```

### Get Campaign Execution Summary
```python
from shared.lib.supabase.campaign_results_db import get_campaign_execution_summary

summary = get_campaign_execution_summary(
    team_id="your-team-id",
    campaign_result_id="campaign-result-uuid"
)

if summary["success"]:
    campaign_result = summary["campaign_result"]
    script_executions = summary["script_executions"]
```

## 🔍 Monitoring and Debugging

### Campaign Execution Logs
The system provides detailed logging during execution:
- Campaign start/completion status
- Individual script execution progress
- Database recording confirmations
- Error messages and stack traces

### Database Tracking
Every campaign execution creates:
1. A `campaign_results` record with overall status
2. `campaign_script_executions` records for each script
3. Individual `script_results` records (created by the script framework)
4. Detailed `execution_results` records for actions/verifications

### Example Log Output
```
🚀 [Campaign] Starting campaign: Double Fullzap Campaign - 20241216_143022
📋 [Campaign] Execution ID: campaign_exec_1734361822_a1b2c3d4
🏗️ [Campaign] Environment setup completed
👥 Team ID: 7fdeb4bb-3639-4ec3-959f-b54769a219ce
🖥️ Host: host1
📝 [Campaign] Script execution recorded with ID: script_result_uuid
📊 [Campaign] Executing 2 script configurations

============================================================
🎯 [Campaign] Executing script 1/2
📜 Script: fullzap.py
🔧 Type: fullzap
============================================================
🚀 [Campaign] Executing command: python test_scripts/fullzap.py horizon_android_mobile --action live_chup --max_iteration 5 --goto_live True
✅ [Campaign] Script completed successfully in 45230ms
✅ [Campaign] Script 1 completed successfully

============================================================
🎯 [Campaign] Executing script 2/2  
📜 Script: fullzap.py
🔧 Type: fullzap
============================================================
🚀 [Campaign] Executing command: python test_scripts/fullzap.py horizon_android_mobile --action live_chdown --max_iteration 3 --goto_live False
✅ [Campaign] Script completed successfully in 32150ms
✅ [Campaign] Script 2 completed successfully
```

## 🛠️ Creating Custom Campaigns

### 1. Create a Campaign Script
```python
#!/usr/bin/env python3
"""
Custom Campaign Script
"""

import sys
import os
from datetime import datetime

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from shared.lib.utils.campaign_executor import CampaignExecutor

def create_custom_campaign_config():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    return {
        "campaign_id": f"custom-campaign-{timestamp}",
        "name": f"Custom Campaign - {timestamp}",
        "description": "Custom campaign description",
        "userinterface_name": "horizon_android_mobile",
        "host": "auto",
        "device": "auto",
        "execution_config": {
            "continue_on_failure": True,
            "timeout_minutes": 120
        },
        "script_configurations": [
            # Add your script configurations here
            {
                "script_name": "your_script.py",
                "script_type": "custom",
                "parameters": {
                    "param1": "value1",
                    "param2": "value2"
                }
            }
        ]
    }

def main():
    campaign_config = create_custom_campaign_config()
    executor = CampaignExecutor()
    result = executor.execute_campaign(campaign_config)
    
    if result["success"]:
        print("Campaign completed successfully!")
    else:
        print(f"Campaign failed: {result['error']}")

if __name__ == "__main__":
    main()
```

### 2. Register API Routes (if needed)
Add the campaign execution routes to your Flask app:

```python
# In your main Flask app file
from backend_server.src.routes.server_campaign_execution_routes import server_campaign_execution_bp

app.register_blueprint(server_campaign_execution_bp)
```

## 🎯 Example: Fullzap Double Campaign

The included `campaign_fullzap_double.py` demonstrates executing `fullzap.py` twice:

1. **First execution**: Channel up with navigation to live (5 iterations)
2. **Second execution**: Channel down without navigation (3 iterations)

This creates a comprehensive test that:
- Tests navigation to live functionality
- Tests zapping in both directions
- Verifies motion detection and channel analysis
- Tracks all results in the database
- Generates detailed reports

## 📈 Benefits

1. **Comprehensive Testing**: Execute multiple related scripts as a cohesive test suite
2. **Database Tracking**: Full audit trail of campaign and script executions
3. **Reporting**: Detailed reports showing overall campaign success and individual script results  
4. **Flexibility**: Easy to configure different script combinations and parameters
5. **Scalability**: Can be extended to support parallel execution and more complex workflows
6. **API Integration**: Full REST API support for integration with CI/CD systems

## 🔧 Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Verify Supabase credentials are correct
   - Check network connectivity
   - Ensure tables were created successfully

2. **Script Execution Failures**
   - Verify script paths are correct
   - Check script parameters are valid
   - Ensure required dependencies are installed

3. **Environment Setup Issues**
   - Verify host and device are available
   - Check userinterface_name is valid
   - Ensure team_id can be determined

### Debug Mode
Add debug logging to campaigns:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Your campaign execution code here
```

This system provides a robust foundation for executing and tracking complex test campaigns in your VirtualPyTest environment!