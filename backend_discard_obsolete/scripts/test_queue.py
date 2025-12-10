#!/usr/bin/env python3
"""
Test script for Backend Discard Service

Tests queue functionality and AI analysis.
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
from ai_analyzer import SimpleAIAnalyzer

def test_queue_operations():
    """Test basic queue operations"""
    print("🧪 Testing Queue Operations...")
    
    try:
        queue_processor = SimpleQueueProcessor()
        
        # Test health check
        if queue_processor.health_check():
            print("✅ Redis health check passed")
        else:
            print("❌ Redis health check failed")
            return False
        
        # Test adding to queues
        test_alert = {
            'id': 'test-alert-123',
            'incident_type': 'blackscreen',
            'host_name': 'test-host',
            'device_id': 'test-device',
            'consecutive_count': 3
        }
        
        test_script = {
            'id': 'test-script-456',
            'script_name': 'test_script.py',
            'success': False,
            'error_msg': 'Element not found'
        }
        
        # Add test items
        if queue_processor.add_alert_to_queue('test-alert-123', test_alert):
            print("✅ Added test alert to P1 queue")
        else:
            print("❌ Failed to add test alert")
            
        if queue_processor.add_script_to_queue('test-script-456', test_script):
            print("✅ Added test script to P2 queue")
        else:
            print("❌ Failed to add test script")
        
        # Check queue lengths
        lengths = queue_processor.get_all_queue_lengths()
        print(f"📊 Queue lengths: {lengths}")
        
        # Test retrieving tasks
        task1 = queue_processor.get_next_task()
        if task1 and task1['type'] == 'alert':
            print("✅ Retrieved alert task (P1 priority worked)")
        else:
            print("❌ Failed to retrieve alert task or wrong priority")
            
        task2 = queue_processor.get_next_task()
        if task2 and task2['type'] == 'script':
            print("✅ Retrieved script task (P2 priority worked)")
        else:
            print("❌ Failed to retrieve script task")
        
        return True
        
    except Exception as e:
        print(f"❌ Queue test failed: {e}")
        return False

def test_ai_analysis():
    """Test AI analysis functionality"""
    print("\n🤖 Testing AI Analysis...")
    
    try:
        ai_analyzer = SimpleAIAnalyzer()
        
        # Test alert analysis
        test_alert = {
            'incident_type': 'blackscreen',
            'host_name': 'test-host',
            'device_id': 'test-device',
            'consecutive_count': 1,
            'metadata': {'duration': '2 seconds'}
        }
        
        print("🔍 Analyzing test alert...")
        alert_result = ai_analyzer.analyze_alert(test_alert)
        
        if alert_result.success:
            print(f"✅ Alert analysis succeeded:")
            print(f"   • Discard: {alert_result.discard}")
            print(f"   • Category: {alert_result.category}")
            print(f"   • Confidence: {alert_result.confidence:.2f}")
            print(f"   • Explanation: {alert_result.explanation}")
        else:
            print(f"❌ Alert analysis failed: {alert_result.error}")
        
        # Test script analysis
        test_script = {
            'script_name': 'test_navigation.py',
            'success': False,
            'error_msg': 'TimeoutException: Element not found after 10 seconds',
            'execution_time_ms': 15000
        }
        
        print("\n🔍 Analyzing test script...")
        script_result = ai_analyzer.analyze_script_result(test_script)
        
        if script_result.success:
            print(f"✅ Script analysis succeeded:")
            print(f"   • Discard: {script_result.discard}")
            print(f"   • Category: {script_result.category}")
            print(f"   • Confidence: {script_result.confidence:.2f}")
            print(f"   • Explanation: {script_result.explanation}")
        else:
            print(f"❌ Script analysis failed: {script_result.error}")
        
        return alert_result.success and script_result.success
        
    except Exception as e:
        print(f"❌ AI analysis test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Backend Discard Service - Test Suite")
    print("=" * 50)
    
    # Test queue operations
    queue_success = test_queue_operations()
    
    # Test AI analysis
    ai_success = test_ai_analysis()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    print(f"   • Queue Operations: {'✅ PASS' if queue_success else '❌ FAIL'}")
    print(f"   • AI Analysis: {'✅ PASS' if ai_success else '❌ FAIL'}")
    
    overall_success = queue_success and ai_success
    print(f"\n🎯 Overall: {'✅ ALL TESTS PASSED' if overall_success else '❌ SOME TESTS FAILED'}")
    
    return 0 if overall_success else 1

if __name__ == '__main__':
    sys.exit(main())
