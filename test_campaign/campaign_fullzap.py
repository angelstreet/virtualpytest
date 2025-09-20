#!/usr/bin/env python3
"""
Campaign Script: Configurable Fullzap Execution

This script creates and executes a test campaign that runs fullzap.py with configurable
parameters. It first runs with goto_live=True, then runs multiple times with goto_live=False.

Usage:
    python test_campaign/campaign_fullzap.py [userinterface_name] [options]
    
Options:
    --host <host>               Host name to use (default: auto)
    --device <device>           Device name to use (default: auto)  
    --max-iteration <int>       Max iterations per execution (default: 2)
    --max-execution <int>       Number of executions with goto_live=False (default: 1)
    --timeout-minutes <int>     Campaign timeout in minutes (default: 60)
    
Examples:
    python test_campaign/campaign_fullzap.py
    python test_campaign/campaign_fullzap.py horizon_android_mobile
    python test_campaign/campaign_fullzap.py horizon_android_mobile --max-execution 5 --timeout-minutes 120
    python test_campaign/campaign_fullzap.py horizon_android_mobile --max-iteration 3 --max-execution 10 --timeout-minutes 180
"""

import sys
import os
import argparse
from datetime import datetime

# Add project root to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)

if project_root not in sys.path:
    sys.path.insert(0, project_root)

from shared.src.lib.utils.campaign_executor import CampaignExecutor, handle_keyboard_interrupt, handle_unexpected_error


def create_campaign_config(userinterface_name: str, host: str = "auto", device: str = "auto", max_iteration: int = 2, max_execution: int = 1, timeout_minutes: int = 60) -> dict:
    """Create campaign configuration for configurable fullzap execution
    
    Args:
        userinterface_name: Name of the user interface to test
        host: Host name to use (default: "auto")
        device: Device name to use (default: "auto") 
        max_iteration: Maximum iterations for each fullzap execution (default: 2)
        max_execution: Number of times to run the second script with goto_live=False (default: 1)
        timeout_minutes: Campaign timeout in minutes (default: 60)
    
    Returns:
        dict: Campaign configuration dictionary
    """
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    config = {
        "campaign_id": f"fullzap-configurable",
        "name": f"Fullzap Campaign",
        "description": f"Execute fullzap.py with goto_live=True once, then {max_execution} times with goto_live=False (max_iteration={max_iteration})",
        "userinterface_name": userinterface_name,
        "host": host,
        "device": device,
        "execution_config": {
            "continue_on_failure": True,  # Continue even if first script fails
            "timeout_minutes": timeout_minutes,  # Configurable timeout
            "parallel": False            # Execute scripts sequentially
        },
        "script_configurations": []
    }
    
    # Add the first script execution (with goto_live: True)
    config["script_configurations"].append({
        "script_name": "fullzap.py",
        "script_type": "fullzap",
        "description": "First fullzap execution - Channel Up with navigation to live",
        "parameters": {
            "action": "live_chup",
            "max_iteration": max_iteration,
            "goto_live": True,
        }
    })
    
    # Add multiple executions of the second script (with goto_live: False)
    for i in range(max_execution):
        execution_num = i + 1
        config["script_configurations"].append({
            "script_name": "fullzap.py", 
            "script_type": "fullzap",
            "description": f"Execution #{execution_num} - Channel Up without navigation to live",
            "parameters": {
                "action": "live_chup", 
                "max_iteration": max_iteration,
                "goto_live": False,
            }
        })
    
    return config


def print_campaign_summary(campaign_config: dict):
    """Print campaign configuration summary"""
    print("\n" + "="*80)
    print("🎯 CAMPAIGN CONFIGURATION SUMMARY")
    print("="*80)
    print(f"📋 Campaign ID: {campaign_config['campaign_id']}")
    print(f"📝 Name: {campaign_config['name']}")
    print(f"📄 Description: {campaign_config['description']}")
    print(f"🖥️  Host: {campaign_config['host']}")
    print(f"📱 Device: {campaign_config['device']}")
    print(f"🌐 Interface: {campaign_config['userinterface_name']}")
    
    print(f"\n⚙️  Execution Config:")
    exec_config = campaign_config['execution_config']
    print(f"   • Continue on failure: {exec_config['continue_on_failure']}")
    print(f"   • Timeout: {exec_config['timeout_minutes']} minutes")
    print(f"   • Parallel execution: {exec_config['parallel']}")
    
    print(f"\n📜 Script Configurations ({len(campaign_config['script_configurations'])} scripts):")
    for i, script_config in enumerate(campaign_config['script_configurations'], 1):
        print(f"   {i}. {script_config['script_name']} ({script_config['script_type']})")
        print(f"      📝 {script_config.get('description', 'No description')}")
        params = script_config.get('parameters', {})
        if params:
            print(f"      🔧 Parameters:")
            for param_name, param_value in params.items():
                print(f"         • {param_name}: {param_value}")
    
    print("="*80)


def main():
    """Main function to execute configurable fullzap campaign"""
    script_name = "campaign_fullzap"
    
    # Create argument parser
    parser = argparse.ArgumentParser(
        description="Execute configurable fullzap campaign - runs fullzap.py with customizable parameters"
    )
    
    parser.add_argument(
        'userinterface_name',
        nargs='?',
        default='horizon_android_mobile',
        help='User interface name (default: horizon_android_mobile)'
    )
    
    parser.add_argument(
        '--host',
        default='auto',
        help='Host name to use (default: auto - selects automatically)'
    )
    
    parser.add_argument(
        '--device',
        default='auto', 
        help='Device name to use (default: auto - selects automatically)'
    )
    
    parser.add_argument(
        '--max-iteration',
        type=int,
        default=2,
        help='Maximum iterations for each fullzap execution (default: 2)'
    )
    
    parser.add_argument(
        '--max-execution',
        type=int,
        default=1,
        help='Number of times to run the second script (goto_live: False) (default: 1)'
    )
    
    parser.add_argument(
        '--timeout-minutes',
        type=int,
        default=60,
        help='Campaign timeout in minutes (default: 60). Consider increasing for higher max-execution values'
    )
    
    args = parser.parse_args()
    
    print(f"🚀 [{script_name}] Starting fullzap campaign execution")
    print(f"🌐 Interface: {args.userinterface_name}")
    print(f"🖥️  Host: {args.host}")
    print(f"📱 Device: {args.device}")
    print(f"🔄 Max Iteration: {getattr(args, 'max_iteration')}")
    print(f"🔢 Max Execution: {getattr(args, 'max_execution')}")
    print(f"⏱️  Timeout: {getattr(args, 'timeout_minutes')} minutes")
    
    try:
        # Create campaign configuration
        campaign_config = create_campaign_config(
            userinterface_name=args.userinterface_name,
            host=args.host,
            device=args.device,
            max_iteration=getattr(args, 'max_iteration'),
            max_execution=getattr(args, 'max_execution'),
            timeout_minutes=getattr(args, 'timeout_minutes')
        )
        
        # Print campaign summary
        print_campaign_summary(campaign_config)
        
        # Execute campaign
        print(f"\n🎬 [{script_name}] Starting campaign execution...")
        
        executor = CampaignExecutor()
        result = executor.execute_campaign(campaign_config)
        
        # Print results
        print(f"\n{'='*80}")
        print("🎯 CAMPAIGN EXECUTION RESULTS")
        print("="*80)
        
        if result["success"]:
            print(f"✅ Campaign completed successfully!")
            print(f"📋 Campaign ID: {result['campaign_id']}")
            print(f"🆔 Execution ID: {result['campaign_execution_id']}")
            print(f"🗃️  Database ID: {result['campaign_result_id']}")
            print(f"⏱️  Total Time: {result['execution_time_ms']/1000:.1f}s")
            print(f"📊 Scripts: {result['successful_scripts']}/{result['total_scripts']} successful")
            
            if result['script_executions']:
                print(f"\n📜 Script Execution Details:")
                for i, script_exec in enumerate(result['script_executions'], 1):
                    status = "✅ SUCCESS" if script_exec['success'] else "❌ FAILED"
                    time_s = script_exec['execution_time_ms'] / 1000
                    print(f"   {i}. {script_exec['script_name']}: {status} ({time_s:.1f}s)")
                    
                    # Display report URL if available
                    if script_exec.get('report_url'):
                        print(f"      📊 Report: {script_exec['report_url']}")
                    
                    # Display logs URL if available
                    if script_exec.get('logs_url'):
                        print(f"      📝 Logs: {script_exec['logs_url']}")
                    
                    if not script_exec['success'] and 'error' in script_exec:
                        print(f"      ❌ Error: {script_exec['error']}")
            
            if result['overall_success']:
                print(f"\n🎉 All scripts executed successfully!")
                exit_code = 0
            else:
                print(f"\n⚠️  Some scripts failed, but campaign completed")
                exit_code = 0  # Campaign completed, even with some failures
        else:
            print(f"❌ Campaign failed!")
            print(f"📋 Campaign ID: {result.get('campaign_id', 'Unknown')}")
            print(f"🆔 Execution ID: {result.get('campaign_execution_id', 'Unknown')}")
            print(f"⏱️  Total Time: {result.get('execution_time_ms', 0)/1000:.1f}s")
            print(f"❌ Error: {result.get('error', 'Unknown error')}")
            
            if result.get('script_executions'):
                print(f"\n📜 Completed Script Executions:")
                for i, script_exec in enumerate(result['script_executions'], 1):
                    status = "✅ SUCCESS" if script_exec['success'] else "❌ FAILED"
                    time_s = script_exec['execution_time_ms'] / 1000
                    print(f"   {i}. {script_exec['script_name']}: {status} ({time_s:.1f}s)")
                    
                    # Display report URL if available
                    if script_exec.get('report_url'):
                        print(f"      📊 Report: {script_exec['report_url']}")
                    
                    # Display logs URL if available
                    if script_exec.get('logs_url'):
                        print(f"      📝 Logs: {script_exec['logs_url']}")
            
            exit_code = 1
        
        print("="*80)
        
        # Exit with appropriate code
        print(f"🏁 [{script_name}] Exiting with code {exit_code}")
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        handle_keyboard_interrupt(script_name)
    except Exception as e:
        handle_unexpected_error(script_name, e)


if __name__ == "__main__":
    main()