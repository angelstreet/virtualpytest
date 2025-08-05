#!/usr/bin/env python3
"""
Test Campaign System

This script tests the campaign execution system by creating and executing
a simple test campaign.

Usage:
    python test_scripts/test_campaign_system.py [userinterface_name]
"""

import sys
import os
import time
from datetime import datetime

# Add project root to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)

if project_root not in sys.path:
    sys.path.insert(0, project_root)

from shared.lib.utils.campaign_executor import CampaignExecutor
from shared.lib.supabase.campaign_executions_db import get_campaign_results


def create_test_campaign_config(userinterface_name: str = "horizon_android_mobile") -> dict:
    """Create a simple test campaign configuration"""
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    return {
        "campaign_id": f"test-campaign-{timestamp}",
        "name": f"Test Campaign System - {timestamp}",
        "description": "Simple test campaign to verify the campaign execution system works",
        "userinterface_name": userinterface_name,
        "host": "auto",
        "device": "auto",
        "execution_config": {
            "continue_on_failure": True,
            "timeout_minutes": 30,
            "parallel": False
        },
        "script_configurations": [
            {
                "script_name": "fullzap.py",
                "script_type": "fullzap",
                "description": "Test fullzap execution with minimal iterations",
                "parameters": {
                    "action": "live_chup",
                    "max_iteration": 2,
                    "goto_live": True
                }
            }
        ]
    }


def test_campaign_database_functions():
    """Test campaign database functions"""
    print("\n🧪 Testing campaign database functions...")
    
    try:
        from shared.lib.utils.script_execution_utils import setup_script_environment
        
        # Setup environment to get team_id
        env_result = setup_script_environment("horizon_android_mobile", "auto", "auto")
        if not env_result["success"]:
            print(f"❌ Environment setup failed: {env_result.get('error')}")
            return False
        
        team_id = env_result["team_id"]
        print(f"✅ Environment setup successful, team_id: {team_id}")
        
        # Test getting campaign results
        results = get_campaign_results(team_id=team_id, limit=5)
        if results["success"]:
            print(f"✅ Database query successful, found {results['count']} campaign results")
            
            # Show recent campaigns if any
            if results["campaign_results"]:
                print("📋 Recent campaigns:")
                for campaign in results["campaign_results"][:3]:
                    status = campaign.get("status", "unknown")
                    name = campaign.get("name", "Unknown")
                    created = campaign.get("created_at", "Unknown")
                    print(f"   • {name} - {status} ({created})")
            else:
                print("📋 No previous campaign results found")
        else:
            print(f"❌ Database query failed: {results.get('error')}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {str(e)}")
        return False


def main():
    """Main test function"""
    print("🧪 Testing Campaign Execution System")
    print("="*60)
    
    # Get userinterface_name from command line
    userinterface_name = sys.argv[1] if len(sys.argv) > 1 else "horizon_android_mobile"
    print(f"🌐 Using interface: {userinterface_name}")
    
    # Test 1: Database functions
    if not test_campaign_database_functions():
        print("❌ Database tests failed, exiting")
        sys.exit(1)
    
    # Test 2: Campaign execution
    print(f"\n🧪 Testing campaign execution...")
    
    try:
        # Create test campaign config
        campaign_config = create_test_campaign_config(userinterface_name)
        
        print(f"📋 Campaign ID: {campaign_config['campaign_id']}")
        print(f"📝 Campaign Name: {campaign_config['name']}")
        print(f"📜 Scripts to execute: {len(campaign_config['script_configurations'])}")
        
        # Execute campaign
        print(f"\n🚀 Starting campaign execution...")
        start_time = time.time()
        
        executor = CampaignExecutor()
        result = executor.execute_campaign(campaign_config)
        
        execution_time = time.time() - start_time
        
        # Print results
        print(f"\n📊 Campaign Execution Results:")
        print(f"⏱️  Execution time: {execution_time:.1f}s")
        
        if result["success"]:
            print(f"✅ Campaign executed successfully!")
            print(f"🆔 Campaign Result ID: {result.get('campaign_result_id')}")
            print(f"📊 Scripts: {result['successful_scripts']}/{result['total_scripts']} successful")
            print(f"🎯 Overall success: {result['overall_success']}")
            
            # Test database retrieval
            if result.get('campaign_result_id'):
                print(f"\n🔍 Testing database retrieval...")
                
                # Get team_id for database query
                from shared.lib.utils.script_execution_utils import setup_script_environment
                env_result = setup_script_environment(userinterface_name, "auto", "auto")
                
                if env_result["success"]:
                    team_id = env_result["team_id"]
                    
                    # Get campaign summary from database
                    summary = get_campaign_execution_summary(
                        team_id=team_id,
                        campaign_result_id=result['campaign_result_id']
                    )
                    
                    if summary["success"]:
                        print(f"✅ Database retrieval successful!")
                        campaign_result = summary["campaign_result"]
                        script_executions = summary["script_executions"]
                        
                        print(f"📋 Campaign: {campaign_result.get('name')}")
                        print(f"📊 Status: {campaign_result.get('status')}")
                        print(f"🕐 Duration: {campaign_result.get('total_duration_ms', 0)/1000:.1f}s")
                        print(f"📜 Script executions: {len(script_executions)}")
                        
                        for i, script_exec in enumerate(script_executions, 1):
                            script_name = script_exec.get('script_name', 'Unknown')
                            script_status = "✅" if script_exec.get('success') else "❌"
                            exec_time = script_exec.get('execution_time_ms', 0) / 1000
                            print(f"   {i}. {script_name}: {script_status} ({exec_time:.1f}s)")
                    else:
                        print(f"❌ Database retrieval failed: {summary.get('error')}")
                else:
                    print(f"❌ Could not get team_id for database query")
            
            print(f"\n🎉 All tests passed!")
            sys.exit(0)
            
        else:
            print(f"❌ Campaign execution failed!")
            print(f"❌ Error: {result.get('error', 'Unknown error')}")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Test failed with exception: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()