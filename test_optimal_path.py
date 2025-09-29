#!/usr/bin/env python3
"""
Simple test script for optimal path validation preview
Tests the validation preview endpoint after ensuring the tree is loaded.
"""

import sys
import os
import requests
import json

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

def test_optimal_path(userinterface_name: str, team_id: str, host_name: str):
    """Test optimal path validation preview"""
    
    base_url = "https://dev.virtualpytest.com"
    
    print(f"🚀 Testing Optimal Path for: {userinterface_name}")
    print(f"   Team: {team_id}")
    print(f"   Host: {host_name}")
    print("="*60)
    
    try:
        # Step 1: Load the navigation tree first
        print("📋 Step 1: Loading navigation tree...")
        load_url = f"{base_url}/server/navigation/tree/{userinterface_name}"
        load_params = {'team_id': team_id}
        
        load_response = requests.get(load_url, params=load_params, timeout=30)
        
        if load_response.status_code != 200:
            print(f"❌ Failed to load tree: HTTP {load_response.status_code}")
            print(f"   Response: {load_response.text}")
            return False
            
        load_result = load_response.json()
        if not load_result.get('success'):
            print(f"❌ Tree loading failed: {load_result.get('error')}")
            return False
            
        print(f"✅ Tree loaded successfully")
        
        # Step 2: Test validation preview
        print("🧪 Step 2: Testing validation preview...")
        preview_url = f"{base_url}/server/validation/preview/{userinterface_name}"
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
    
    # Test configuration
    userinterface_name = "horizon_android_mobile"
    team_id = "7fdeb4bb-3639-4ec3-959f-b54769a219ce"
    host_name = "sunri-pi1"
    
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
