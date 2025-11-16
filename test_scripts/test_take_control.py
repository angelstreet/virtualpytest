#!/usr/bin/env python3
"""
Test Take Control Flow

Simple script to test the take control endpoint and debug issues.
"""

import sys
import os
import requests
import json

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def test_take_control(server_url: str, team_id: str, device_name: str, tree_id: str = None):
    """
    Test the take control endpoint step by step.
    
    Args:
        server_url: Backend server URL (e.g., http://localhost:5109)
        team_id: Team ID
        device_name: Device name to control
        tree_id: Optional tree ID for navigation
    """
    print("=" * 80)
    print("🎮 TAKE CONTROL TEST")
    print("=" * 80)
    print(f"📍 Server: {server_url}")
    print(f"👥 Team ID: {team_id}")
    print(f"🖥️  Device: {device_name}")
    print(f"🗺️  Tree ID: {tree_id or 'None'}")
    print("=" * 80)
    print()
    
    # Step 1: Call take control endpoint
    print("📡 Step 1: Calling take control endpoint...")
    url = f"{server_url}/server/control/takeControl"
    params = {
        'team_id': team_id
    }
    payload = {
        'device_name': device_name
    }
    
    if tree_id:
        payload['tree_id'] = tree_id
    
    print(f"   URL: {url}")
    print(f"   Params: {params}")
    print(f"   Payload: {json.dumps(payload, indent=2)}")
    print()
    
    try:
        response = requests.post(url, params=params, json=payload, timeout=30)
        
        print(f"📊 Response Status: {response.status_code}")
        print(f"📊 Response Headers: {dict(response.headers)}")
        print()
        
        if response.status_code == 200:
            data = response.json()
            print("✅ SUCCESS!")
            print(f"📄 Response Data:")
            print(json.dumps(data, indent=2))
            
            # Check for specific fields
            if 'success' in data:
                print(f"\n   Success: {data['success']}")
            if 'device_name' in data:
                print(f"   Device: {data['device_name']}")
            if 'stream_url' in data:
                print(f"   Stream URL: {data['stream_url']}")
            if 'controllers' in data:
                print(f"   Controllers: {data['controllers']}")
                
        else:
            print("❌ FAILED!")
            print(f"📄 Response Text:")
            print(response.text)
            
            try:
                error_data = response.json()
                print(f"\n📄 Error Data:")
                print(json.dumps(error_data, indent=2))
            except:
                pass
                
    except requests.exceptions.Timeout:
        print("❌ Request timed out after 30 seconds")
        
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Connection error: {e}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    print("=" * 80)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Test take control endpoint')
    parser.add_argument('--server', default='http://localhost:5109', 
                       help='Backend server URL (default: http://localhost:5109)')
    parser.add_argument('--team-id', default='7fdeb4bb-3639-4ec3-959f-b54769a219ce',
                       help='Team ID (default: default team)')
    parser.add_argument('--device', required=True,
                       help='Device name to control')
    parser.add_argument('--tree-id', default=None,
                       help='Optional tree ID for navigation')
    
    args = parser.parse_args()
    
    test_take_control(
        server_url=args.server,
        team_id=args.team_id,
        device_name=args.device,
        tree_id=args.tree_id
    )

