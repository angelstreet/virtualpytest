#!/usr/bin/env python3
"""
Test Campaign Proxy Flow

This script tests the complete campaign execution flow from server to host.
"""

import requests
import json
import time

# Test configuration
SERVER_URL = "http://localhost:5001"  # Backend server
CAMPAIGN_CONFIG = {
    "campaign_id": "test-proxy-campaign",
    "name": "Test Proxy Campaign",
    "description": "Test campaign execution via proxy to host",
    "userinterface_name": "horizon_android_mobile",
    "host": "sunri-pi1",  # Specify host for proxy
    "device": "device1",
    "execution_config": {
        "continue_on_failure": True,
        "timeout_minutes": 10,
        "parallel": False
    },
    "script_configurations": [
        {
            "script_name": "validation.py",
            "script_type": "validation",
            "parameters": {
                "target_node": "live_fullscreen",
                "max_iteration": 2
            }
        }
    ],
    "async": True
}

def test_campaign_proxy():
    """Test campaign execution via proxy"""
    print("🧪 Testing Campaign Proxy Flow")
    print("=" * 50)
    
    # Headers for authentication
    headers = {
        'Content-Type': 'application/json',
        'X-User-ID': 'test-user'
    }
    
    try:
        # Step 1: Start campaign execution
        print("📤 Step 1: Starting campaign execution...")
        response = requests.post(
            f"{SERVER_URL}/server/campaigns/execute",
            json=CAMPAIGN_CONFIG,
            headers=headers,
            timeout=30
        )
        
        print(f"Response Status: {response.status_code}")
        print(f"Response Body: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code != 202:
            print("❌ Campaign execution failed to start")
            return False
        
        result = response.json()
        execution_id = result.get('execution_id')
        
        if not execution_id:
            print("❌ No execution_id returned")
            return False
        
        print(f"✅ Campaign started with execution_id: {execution_id}")
        
        # Step 2: Monitor campaign status
        print(f"\n📊 Step 2: Monitoring campaign status...")
        max_wait_time = 300  # 5 minutes
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            try:
                status_response = requests.get(
                    f"{SERVER_URL}/server/campaigns/status/{execution_id}",
                    headers=headers,
                    timeout=10
                )
                
                if status_response.status_code == 200:
                    status_result = status_response.json()
                    status = status_result.get('status')
                    runtime = status_result.get('runtime_seconds', 0)
                    
                    print(f"⏱️  Status: {status}, Runtime: {runtime}s")
                    
                    if status in ['completed', 'failed']:
                        print(f"\n🎯 Campaign finished with status: {status}")
                        print(f"Final result: {json.dumps(status_result, indent=2)}")
                        
                        if status == 'completed':
                            print("✅ Campaign proxy test PASSED")
                            return True
                        else:
                            print("❌ Campaign proxy test FAILED - campaign failed")
                            return False
                
                time.sleep(10)  # Wait 10 seconds between status checks
                
            except Exception as e:
                print(f"⚠️  Error checking status: {e}")
                time.sleep(5)
        
        print("⏰ Campaign proxy test TIMEOUT - campaign took too long")
        return False
        
    except Exception as e:
        print(f"❌ Campaign proxy test ERROR: {e}")
        return False

def test_campaign_list():
    """Test listing running campaigns"""
    print("\n📋 Testing campaign list...")
    
    headers = {
        'Content-Type': 'application/json',
        'X-User-ID': 'test-user'
    }
    
    try:
        response = requests.get(
            f"{SERVER_URL}/server/campaigns/running",
            headers=headers,
            timeout=10
        )
        
        print(f"List Response Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            campaigns = result.get('running_campaigns', [])
            print(f"Running campaigns: {len(campaigns)}")
            for campaign in campaigns:
                print(f"  - {campaign.get('campaign_id')} ({campaign.get('status')})")
            return True
        else:
            print(f"❌ Failed to list campaigns: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error listing campaigns: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Campaign Proxy Test Suite")
    print("=" * 50)
    
    # Test campaign execution
    proxy_success = test_campaign_proxy()
    
    # Test campaign listing
    list_success = test_campaign_list()
    
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    print(f"Campaign Proxy: {'✅ PASS' if proxy_success else '❌ FAIL'}")
    print(f"Campaign List: {'✅ PASS' if list_success else '❌ FAIL'}")
    
    if proxy_success and list_success:
        print("🎉 All tests PASSED!")
        exit(0)
    else:
        print("💥 Some tests FAILED!")
        exit(1)
