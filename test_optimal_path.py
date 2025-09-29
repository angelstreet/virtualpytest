#!/usr/bin/env python3
"""
Complete test script for optimal path validation preview
Checks host availability, loads tree, and tests validation preview.
"""

import sys
import os
import requests
import json
import time

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

def check_host_availability(base_url: str, host_name: str, team_id: str) -> bool:
    """Check if the host is registered and available"""
    try:
        print(f"🔍 Checking host availability: {host_name}")
        
        # Get all hosts
        hosts_url = f"{base_url}/server/system/getAllHosts"
        response = requests.get(hosts_url, timeout=10)
        
        if response.status_code != 200:
            print(f"❌ Failed to get hosts: HTTP {response.status_code}")
            return False
            
        result = response.json()
        if not result.get('success'):
            print(f"❌ Failed to get hosts: {result.get('error')}")
            return False
            
        hosts = result.get('hosts', [])
        host_found = False
        
        for host in hosts:
            if host.get('host_name') == host_name:
                host_found = True
                status = host.get('status', 'unknown')
                last_seen = host.get('last_seen', 0)
                time_since_seen = time.time() - last_seen if last_seen else float('inf')
                
                print(f"✅ Host found: {host_name}")
                print(f"   Status: {status}")
                print(f"   Last seen: {time_since_seen:.1f}s ago")
                print(f"   URL: {host.get('host_url', 'unknown')}")
                
                if status == 'online' and time_since_seen < 300:  # 5 minutes
                    return True
                else:
                    print(f"⚠️  Host is not online or stale")
                    return False
                    
        if not host_found:
            print(f"❌ Host {host_name} not found in registered hosts")
            print(f"   Available hosts: {[h.get('host_name') for h in hosts]}")
            return False
            
    except Exception as e:
        print(f"❌ Error checking host availability: {e}")
        return False

def test_optimal_path(userinterface_name: str, team_id: str, host_name: str):
    """Test optimal path validation preview"""
    
    base_url = "https://dev.virtualpytest.com"
    
    print(f"🚀 Testing Optimal Path for: {userinterface_name}")
    print(f"   Team: {team_id}")
    print(f"   Host: {host_name}")
    print("="*60)
    
    try:
        # Step 1: Check host availability
        print("🔍 Step 1: Checking host availability...")
        if not check_host_availability(base_url, host_name, team_id):
            print(f"❌ Host {host_name} is not available")
            print(f"💡 Make sure the host is running and registered with the server")
            return False
        print(f"✅ Host is available and online")
        
        # Step 2: Get userinterface and tree info
        print("📋 Step 2: Getting userinterface and navigation tree...")
        ui_url = f"{base_url}/server/userinterface/getAllUserInterfaces"
        ui_response = requests.get(ui_url, params={'team_id': team_id}, timeout=10)
        
        if ui_response.status_code != 200:
            print(f"❌ Failed to get userinterfaces: HTTP {ui_response.status_code}")
            return False
            
        all_uis = ui_response.json()
        target_ui = None
        
        for ui in all_uis:
            if ui.get('name') == userinterface_name:
                target_ui = ui
                break
                
        if not target_ui:
            print(f"❌ Userinterface '{userinterface_name}' not found")
            print(f"💡 Available userinterfaces:")
            for ui in all_uis[:5]:
                print(f"   - {ui.get('name', 'unknown')}")
            return False
            
        # Check if it has a root tree
        root_tree = target_ui.get('root_tree')
        if not root_tree:
            print(f"❌ Userinterface exists but has no navigation tree")
            print(f"💡 You need to create a navigation tree for this userinterface")
            return False
            
        tree_id = root_tree.get('id')
        print(f"✅ Navigation tree found")
        print(f"   Tree ID: {tree_id}")
        print(f"   Tree name: {root_tree.get('name', 'unknown')}")
        
        # Step 3: Test validation preview (this will auto-populate cache)
        print("🧪 Step 3: Testing validation preview...")
        preview_url = f"{base_url}/server/validation/preview/{tree_id}"  # Use tree_id, not userinterface_name
        preview_params = {
            'team_id': team_id,
            'host_name': host_name
        }
        
        preview_response = requests.get(preview_url, params=preview_params, timeout=60)
        
        if preview_response.status_code != 200:
            print(f"❌ Preview failed: HTTP {preview_response.status_code}")
            print(f"   Response: {preview_response.text}")
            return False
            
        preview_result = preview_response.json()
        if not preview_result.get('success'):
            print(f"❌ Preview failed: {preview_result.get('error')}")
            return False
            
        # Analyze results
        edges = preview_result.get('edges', [])
        total_steps = len(edges)
        algorithm = preview_result.get('algorithm', 'unknown')
        
        print(f"✅ Validation preview successful!")
        print(f"   Total steps: {total_steps}")
        print(f"   Algorithm: {algorithm}")
        
        # Show first 5 steps
        print(f"\n📋 First 5 steps:")
        for i, edge in enumerate(edges[:5], 1):
            from_name = edge.get('from_name', 'unknown')
            to_name = edge.get('to_name', 'unknown')
            step_type = edge.get('step_type', 'unknown')
            print(f"   {i}. {from_name} → {to_name} ({step_type})")
            
        if total_steps > 5:
            print(f"   ... and {total_steps - 5} more steps")
            
        print(f"\n🎉 SUCCESS: Optimal path generated with {total_steps} steps")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def main():
    """Main function"""
    
    # Test configuration - CORRECTED VALUES
    userinterface_name = "horizon_android_mobile"
    team_id = "7fdeb4bb-3639-4ec3-959f-b54769a219ce"
    host_name = "sunri-pi2"  # Corrected: sunri-pi1 doesn't exist, use sunri-pi2
    
    # Run test
    success = test_optimal_path(userinterface_name, team_id, host_name)
    
    print("="*60)
    if success:
        print("🎉 TEST PASSED - Optimal path working correctly!")
    else:
        print("❌ TEST FAILED - Check the output above for details")
    print("="*60)
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
