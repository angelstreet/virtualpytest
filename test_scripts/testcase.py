#!/usr/bin/env python3
"""
TestCase CLI Wrapper

Execute test cases created in TestCase Builder from command line.
Integrates with ScriptExecutor for consistent execution and reporting.

Usage:
    python testcase.py --testcase-name "login_test" --device device1
    python testcase.py --testcase-name "navigation_check" --host sunri-pi1
"""

import sys
import os
import argparse

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from backend_host.src.services.testcase.testcase_executor import TestCaseExecutor
from shared.src.lib.database.testcase_db import get_testcase_by_name
from shared.src.lib.utils.app_utils import load_environment_variables

DEFAULT_TEAM_ID = '7fdeb4bb-3639-4ec3-959f-b54769a219ce'


def main():
    """Execute test case from command line"""
    parser = argparse.ArgumentParser(description='Execute visual test case from TestCase Builder')
    
    # Required arguments
    parser.add_argument('--testcase-name', required=True, help='Name of the test case to execute')
    
    # Optional framework arguments
    parser.add_argument('--host', default='sunri-pi1', help='Host to use (default: sunri-pi1)')
    parser.add_argument('--device', default='device1', help='Device to use (default: device1)')
    parser.add_argument('--team-id', default=DEFAULT_TEAM_ID, help='Team ID')
    
    args = parser.parse_args()
    
    print(f"🎯 [testcase] Executing test case: {args.testcase_name}")
    print(f"📱 [testcase] Device: {args.device}")
    print(f"🏢 [testcase] Team: {args.team_id}")
    
    try:
        # Load environment variables
        backend_host_src = os.path.join(project_root, 'backend_host', 'src')
        load_environment_variables(calling_script_dir=backend_host_src)
        
        # Verify test case exists
        testcase = get_testcase_by_name(args.testcase_name, args.team_id)
        if not testcase:
            print(f"❌ [testcase] Test case not found: {args.testcase_name}")
            sys.exit(1)
        
        print(f"✅ [testcase] Found test case: {testcase['description'] or 'No description'}")
        print(f"📋 [testcase] Blocks: {len(testcase['graph_json'].get('nodes', []))}")
        print(f"🔗 [testcase] Connections: {len(testcase['graph_json'].get('edges', []))}")
        
        # Get device info
        from backend_host.src.controllers.controller_manager import get_host
        host = get_host(device_ids=[args.device])
        
        device = next((d for d in host.get_devices() if d.device_id == args.device), None)
        if not device:
            print(f"❌ [testcase] Device not found: {args.device}")
            sys.exit(1)
        
        # Execute test case
        executor = TestCaseExecutor()
        result = executor.execute_testcase(
            testcase_name=args.testcase_name,
            team_id=args.team_id,
            host_name=host.host_name,
            device_id=device.device_id,
            device_name=device.device_name,
            device_model=device.device_model
        )
        
        # Print results
        print("\n" + "="*60)
        print("🎯 TESTCASE EXECUTION SUMMARY")
        print("="*60)
        print(f"📋 Test Case: {args.testcase_name}")
        print(f"⏱️  Execution Time: {result['execution_time_ms']/1000:.1f}s")
        print(f"📊 Steps: {result['step_count']}")
        print(f"🎯 Result: {'SUCCESS' if result['success'] else 'FAILED'}")
        
        if not result['success'] and result.get('error'):
            print(f"❌ Error: {result['error']}")
        
        if result.get('script_result_id'):
            print(f"📝 Script Result ID: {result['script_result_id']}")
        
        print("="*60)
        
        # Exit with appropriate code
        sys.exit(0 if result['success'] else 1)
        
    except KeyboardInterrupt:
        print("\n⚠️  [testcase] Execution interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"❌ [testcase] Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

