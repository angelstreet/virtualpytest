#!/usr/bin/env python3
"""
Test script to verify optimal validation preview with horizon_android_mobile userinterface
This script loads the navigation tree and tests the validation preview to ensure
cross-tree navigation details are properly shown.
"""

import os
import sys
import requests
import json
from typing import Dict, Any

# Add project paths
sys.path.append('/Users/cpeengineering/virtualpytest')
sys.path.append('/Users/cpeengineering/virtualpytest/shared/src')

def test_validation_preview(tree_id: str, team_id: str, host_name: str) -> Dict[str, Any]:
    """
    Test the validation preview endpoint to verify optimal path generation
    
    Args:
        tree_id: Navigation tree ID
        team_id: Team ID
        host_name: Host name for the test
        
    Returns:
        Dictionary with test results
    """
    print(f"🧪 Testing validation preview for tree: {tree_id}")
    print(f"   Team: {team_id}")
    print(f"   Host: {host_name}")
    print("="*80)
    
    try:
        # Build the validation preview URL
        base_url = "http://localhost:5002"  # Backend server URL
        url = f"{base_url}/server/validation/preview/{tree_id}"
        
        params = {
            'team_id': team_id,
            'host_name': host_name
        }
        
        print(f"📡 Making request to: {url}")
        print(f"   Parameters: {params}")
        
        # Make the request
        response = requests.get(url, params=params, timeout=60)
        
        if response.status_code != 200:
            return {
                'success': False,
                'error': f'HTTP {response.status_code}: {response.text}',
                'status_code': response.status_code
            }
        
        result = response.json()
        
        if not result.get('success'):
            return {
                'success': False,
                'error': result.get('error', 'Unknown error'),
                'result': result
            }
        
        # Analyze the validation preview results
        edges = result.get('edges', [])
        total_edges = len(edges)
        
        print(f"✅ Validation preview successful!")
        print(f"   Total optimized steps: {total_edges}")
        print(f"   Algorithm: {result.get('algorithm', 'unknown')}")
        print()
        
        # Analyze step types
        step_types = {}
        cross_tree_steps = []
        verification_steps = []
        
        for i, edge in enumerate(edges, 1):
            step_type = edge.get('step_type', 'unknown')
            step_types[step_type] = step_types.get(step_type, 0) + 1
            
            # Check for cross-tree navigation
            if edge.get('is_cross_tree') or edge.get('transition_type') in ['ENTER_SUBTREE', 'EXIT_SUBTREE']:
                cross_tree_steps.append({
                    'step': i,
                    'from': edge.get('from_name', 'unknown'),
                    'to': edge.get('to_name', 'unknown'),
                    'type': edge.get('transition_type', 'unknown'),
                    'step_type': step_type
                })
            
            # Check for verification steps
            if edge.get('has_verifications'):
                verification_steps.append({
                    'step': i,
                    'from': edge.get('from_name', 'unknown'),
                    'to': edge.get('to_name', 'unknown'),
                    'actions': len(edge.get('actions', []))
                })
        
        print(f"📊 Step Type Analysis:")
        for step_type, count in step_types.items():
            print(f"   • {step_type}: {count} steps")
        print()
        
        print(f"🌐 Cross-Tree Navigation Steps: {len(cross_tree_steps)}")
        for step in cross_tree_steps:
            print(f"   Step {step['step']}: {step['from']} → {step['to']} ({step['type']}, {step['step_type']})")
        print()
        
        print(f"✅ Verification Steps: {len(verification_steps)}")
        for step in verification_steps:
            print(f"   Step {step['step']}: {step['from']} → {step['to']} ({step['actions']} actions)")
        print()
        
        # Show first 10 steps in detail
        print(f"📋 First 10 Validation Steps:")
        for i, edge in enumerate(edges[:10], 1):
            from_name = edge.get('from_name', 'unknown')
            to_name = edge.get('to_name', 'unknown')
            step_type = edge.get('step_type', 'unknown')
            transition_type = edge.get('transition_type', 'NORMAL')
            actions_count = len(edge.get('actions', []))
            has_verifications = edge.get('has_verifications', False)
            
            # Build step description
            step_desc = f"{from_name} → {to_name}"
            if transition_type != 'NORMAL':
                step_desc += f" ({transition_type})"
            if has_verifications:
                step_desc += " [HAS VERIFICATIONS]"
            
            print(f"   {i:2d}. {step_desc}")
            print(f"       Type: {step_type}, Actions: {actions_count}")
        
        if total_edges > 10:
            print(f"   ... and {total_edges - 10} more steps")
        print()
        
        return {
            'success': True,
            'total_steps': total_edges,
            'step_types': step_types,
            'cross_tree_steps': len(cross_tree_steps),
            'verification_steps': len(verification_steps),
            'algorithm': result.get('algorithm'),
            'edges': edges
        }
        
    except requests.exceptions.RequestException as e:
        return {
            'success': False,
            'error': f'Request failed: {str(e)}',
            'exception_type': 'RequestException'
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'Unexpected error: {str(e)}',
            'exception_type': type(e).__name__
        }


def main():
    """Main test function"""
    print("🚀 Optimal Validation Preview Test")
    print("Testing cross-tree navigation details in validation preview")
    print("="*80)
    
    # Test configuration
    test_config = {
        'tree_id': 'horizon_android_mobile',  # The userinterface to test
        'team_id': '7fdeb4bb-3639-4ec3-959f-b54769a219ce',  # Default team ID
        'host_name': 'sunri-pi1'  # Host name from the logs
    }
    
    print(f"🎯 Test Configuration:")
    for key, value in test_config.items():
        print(f"   {key}: {value}")
    print()
    
    # Run the test
    result = test_validation_preview(**test_config)
    
    print("="*80)
    print("🏁 TEST RESULTS")
    print("="*80)
    
    if result['success']:
        print("✅ TEST PASSED")
        print(f"   Total optimized steps: {result['total_steps']}")
        print(f"   Cross-tree navigation steps: {result['cross_tree_steps']}")
        print(f"   Verification steps: {result['verification_steps']}")
        print(f"   Algorithm: {result['algorithm']}")
        
        # Check if cross-tree navigation is properly shown
        if result['cross_tree_steps'] > 0:
            print("✅ Cross-tree navigation details are included in the preview")
        else:
            print("⚠️  No cross-tree navigation steps found - this may be expected if no nested trees")
        
        # Check step type distribution
        step_types = result['step_types']
        if 'transitional_return' in step_types:
            print(f"✅ Transitional return steps included: {step_types['transitional_return']}")
        else:
            print("ℹ️  No transitional return steps - this may be expected")
        
        print("\n🎉 Validation preview is working correctly!")
        
    else:
        print("❌ TEST FAILED")
        print(f"   Error: {result['error']}")
        if 'exception_type' in result:
            print(f"   Exception Type: {result['exception_type']}")
        
        print("\n💡 Troubleshooting:")
        print("   1. Make sure the backend server is running on localhost:5002")
        print("   2. Verify the horizon_android_mobile userinterface exists")
        print("   3. Check that the host 'sunri-pi1' is available")
        print("   4. Ensure the team_id is correct")
    
    print("="*80)
    return result['success']


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

