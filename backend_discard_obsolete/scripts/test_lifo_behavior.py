#!/usr/bin/env python3
"""
Test script to verify LIFO (Last In, First Out) behavior for alert queue.

Tests that the most recent alerts are processed first.
"""

import sys
import os
import time
from datetime import datetime

# Add project paths
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_discard_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(backend_discard_dir)

if project_root not in sys.path:
    sys.path.insert(0, project_root)

sys.path.append(os.path.join(backend_discard_dir, 'src'))

from queue_processor import SimpleQueueProcessor

def test_lifo_behavior():
    """Test that most recent alerts are processed first (LIFO)"""
    print("🧪 Testing LIFO Behavior for Alert Queue")
    print("=" * 50)
    
    try:
        queue_processor = SimpleQueueProcessor()
        
        # Test health check first
        if not queue_processor.health_check():
            print("❌ Redis health check failed")
            return False
        
        print("✅ Redis connection healthy")
        
        # Clear any existing alerts for clean test
        print("🧹 Clearing existing alerts...")
        while queue_processor.get_next_task():
            pass  # Clear all existing tasks
        
        # Create test alerts with timestamps
        test_alerts = []
        for i in range(1, 4):  # Create 3 test alerts
            alert = {
                'id': f'test-alert-{i}',
                'incident_type': 'blackscreen',
                'host_name': f'test-host-{i}',
                'device_id': f'test-device-{i}',
                'consecutive_count': 1,
                'test_sequence': i,
                'created_at': datetime.now().isoformat()
            }
            test_alerts.append(alert)
            
            # Add small delay to ensure different timestamps
            time.sleep(0.1)
        
        # Add alerts to queue in order: 1, 2, 3
        print("\n📥 Adding alerts to queue:")
        for alert in test_alerts:
            success = queue_processor.add_alert_to_queue(alert['id'], alert)
            if success:
                print(f"   ✅ Added alert {alert['test_sequence']} (ID: {alert['id']})")
            else:
                print(f"   ❌ Failed to add alert {alert['test_sequence']}")
                return False
        
        # Check queue length
        lengths = queue_processor.get_all_queue_lengths()
        alert_count = lengths.get('p1_alerts', 0)
        print(f"\n📊 Queue length: {alert_count} alerts")
        
        if alert_count != 3:
            print(f"❌ Expected 3 alerts in queue, got {alert_count}")
            return False
        
        # Retrieve alerts and check order (should be LIFO: 3, 2, 1)
        print("\n📤 Retrieving alerts (expecting LIFO order: 3, 2, 1):")
        retrieved_order = []
        
        for expected_sequence in [3, 2, 1]:
            task = queue_processor.get_next_task()
            if task and task['type'] == 'alert':
                actual_sequence = task['data']['test_sequence']
                retrieved_order.append(actual_sequence)
                print(f"   📦 Retrieved alert {actual_sequence} (ID: {task['id']})")
                
                if actual_sequence == expected_sequence:
                    print(f"   ✅ Correct LIFO order! Expected {expected_sequence}, got {actual_sequence}")
                else:
                    print(f"   ❌ Wrong order! Expected {expected_sequence}, got {actual_sequence}")
                    return False
            else:
                print(f"   ❌ Failed to retrieve alert or wrong task type")
                return False
        
        # Verify queue is empty
        remaining_task = queue_processor.get_next_task()
        if remaining_task:
            print(f"   ❌ Queue should be empty but found task: {remaining_task.get('id')}")
            return False
        
        print(f"\n🎯 LIFO Test Results:")
        print(f"   📥 Added order: {[1, 2, 3]}")
        print(f"   📤 Retrieved order: {retrieved_order}")
        print(f"   ✅ LIFO behavior confirmed: Most recent alerts processed first!")
        
        return True
        
    except Exception as e:
        print(f"❌ LIFO test failed: {e}")
        return False

def main():
    """Run LIFO behavior test"""
    print("🧪 Alert Queue LIFO Behavior Test")
    print("=" * 50)
    
    success = test_lifo_behavior()
    
    print(f"\n" + "=" * 50)
    if success:
        print("🎉 LIFO behavior is working correctly!")
        print("✨ Most recent alerts will be processed first")
    else:
        print("❌ LIFO behavior test failed")
        print("⚠️  Queue may not be processing most recent alerts first")
    
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())
