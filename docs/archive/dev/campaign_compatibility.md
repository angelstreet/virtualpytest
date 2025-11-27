# Campaign System Compatibility Guide

This document explains how to make test scripts compatible with the VirtualPyTest campaign system for automated execution and real-time logging.

## Overview

The campaign system allows you to execute multiple test scripts in sequence or parallel, with real-time logging, automatic result tracking, and database integration. For scripts to be fully compatible, they must follow specific patterns for outputting execution information.

## Required Output Format

For a script to be campaign-compatible, it must output two key pieces of information during execution:

### 1. Script Result ID
```
SCRIPT_RESULT_ID:<database_id>
```
- **When**: Output when the script starts and creates a database record
- **Purpose**: Allows the campaign system to link the script execution to the database record
- **Example**: `SCRIPT_RESULT_ID:script_result_12345`

### 2. Script Success Status
```
SCRIPT_SUCCESS:<true|false>
```
- **When**: Output at the end of script execution, before exit
- **Purpose**: Tells the campaign system whether the script succeeded or failed
- **Example**: `SCRIPT_SUCCESS:true` or `SCRIPT_SUCCESS:false`

## Implementation Using ScriptExecutor Framework

The easiest way to make a script campaign-compatible is to use the `ScriptExecutor` framework, which automatically handles the required output format.

### Basic Pattern

```python
#!/usr/bin/env python3
import sys
import os

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from shared.lib.utils.script_framework import ScriptExecutor, handle_keyboard_interrupt, handle_unexpected_error

def main():
    script_name = "your_script_name"
    executor = ScriptExecutor(script_name, "Script description")
    
    # Create argument parser
    parser = executor.create_argument_parser()
    args = parser.parse_args()
    
    # Setup execution context with database tracking enabled
    context = executor.setup_execution_context(args, enable_db_tracking=True)
    if context.error_message:
        executor.cleanup_and_exit(context, args.userinterface_name)
        return
    
    try:
        # Your script logic here
        # Set context.overall_success based on your script's result
        context.overall_success = True  # or False
        
    except KeyboardInterrupt:
        handle_keyboard_interrupt(script_name)
    except Exception as e:
        handle_unexpected_error(script_name, e)
    finally:
        # This automatically outputs SCRIPT_RESULT_ID and SCRIPT_SUCCESS
        executor.cleanup_and_exit(context, args.userinterface_name)

if __name__ == "__main__":
    main()
```

### Key Points

1. **Enable Database Tracking**: Set `enable_db_tracking=True` in `setup_execution_context()`
2. **Set Success Status**: Set `context.overall_success = True/False` based on your script's result
3. **Use cleanup_and_exit()**: This automatically outputs the required campaign information
4. **Handle Exceptions**: Use the standard exception handlers for consistency

## Compatible Scripts in test_scripts/

The following scripts are already campaign-compatible:

### ✅ goto_live_fullscreen.py
- **Purpose**: Navigate to live_fullscreen node
- **Campaign Usage**: `goto_live_fullscreen.py [userinterface_name] [--host <host>] [--device <device>]`
- **Success Criteria**: Successfully navigates to the target node

### ✅ validation.py
- **Purpose**: Validate all transitions in a navigation tree
- **Campaign Usage**: `validation.py <userinterface_name> [--host <host>] [--device <device>]`
- **Success Criteria**: Completes validation sequence (allows some step failures)

### ✅ fullzap.py
- **Purpose**: Execute zapping actions with motion detection
- **Campaign Usage**: `fullzap.py [userinterface_name] [--action <action>] [--max_iteration <count>] [--goto_live <true|false>]`
- **Success Criteria**: Successfully completes all zap iterations

## Campaign Configuration

To use these scripts in a campaign, create a campaign configuration like this:

```python
campaign_config = {
    "campaign_id": "my-campaign-123",
    "name": "My Test Campaign",
    "description": "Campaign description",
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
            "script_name": "goto_live_fullscreen.py",
            "script_type": "navigation",
            "description": "Navigate to live fullscreen",
            "parameters": {}
        },
        {
            "script_name": "validation.py",
            "script_type": "validation", 
            "description": "Validate navigation tree",
            "parameters": {}
        },
        {
            "script_name": "fullzap.py",
            "script_type": "fullzap",
            "description": "Execute zapping test",
            "parameters": {
                "action": "live_chup",
                "max_iteration": 5,
                "goto_live": False
            }
        }
    ]
}
```

## Real-Time Logging

When scripts are executed through the campaign system, you'll see:

1. **Campaign orchestration logs** with `[Campaign]` prefix
2. **Real-time script output** with `[Script]` prefix  
3. **Script result ID capture** when the script outputs `SCRIPT_RESULT_ID:`
4. **Script success status** when the script outputs `SCRIPT_SUCCESS:`

Example output:
```
🚀 [Campaign] Executing command: python /path/to/script.py args...
📋 [Campaign] Starting real-time script output:
================================================================================
[Script] 📝 [script] Script execution recorded with ID: script_result_12345
🔗 [Campaign] Captured script result ID: script_result_12345
[Script] ✅ [script] Script logic completed successfully
[Script] SCRIPT_SUCCESS:true
✅ [Campaign] Script reported success: true
================================================================================
📋 [Campaign] Script output ended
✅ [Campaign] Script completed successfully in 5432ms
```

## Testing Campaign Compatibility

To test if your script is campaign-compatible:

1. **Manual Test**: Run your script standalone and verify it outputs `SCRIPT_RESULT_ID:` and `SCRIPT_SUCCESS:`
2. **Campaign Test**: Create a simple campaign with just your script and run it
3. **Check Logs**: Verify the campaign system captures the script result ID and success status

## Troubleshooting

### Script Result ID Not Found
- **Issue**: Campaign shows "Could not find script result"
- **Solution**: Ensure `enable_db_tracking=True` and script outputs `SCRIPT_RESULT_ID:`

### Wrong Success Status
- **Issue**: Campaign reports wrong success/failure status
- **Solution**: Ensure `context.overall_success` is set correctly before `cleanup_and_exit()`

### No Real-Time Logs
- **Issue**: Script output not showing in real-time
- **Solution**: Ensure script uses `print()` statements and flushes output regularly

## Migration Guide

To make an existing script campaign-compatible:

1. **Add ScriptExecutor**: Replace custom argument parsing with `ScriptExecutor`
2. **Enable DB Tracking**: Set `enable_db_tracking=True`
3. **Set Success Status**: Set `context.overall_success` based on your logic
4. **Use Standard Cleanup**: Replace custom exit logic with `executor.cleanup_and_exit()`
5. **Test**: Verify the script outputs required information

This ensures your scripts work seamlessly with both standalone execution and campaign orchestration.