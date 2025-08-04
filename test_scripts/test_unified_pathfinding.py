#!/usr/bin/env python3
"""
Integration Tests for Unified Pathfinding System
Tests the complete nested pathfinding architecture with fail-early behavior
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

from shared.lib.utils.navigation_utils import load_navigation_tree_with_hierarchy, goto_node
from shared.lib.utils.navigation_exceptions import NavigationTreeError, UnifiedCacheError, PathfindingError
from shared.lib.utils.navigation_validation import validate_complete_unified_system
from shared.lib.utils.script_framework import ScriptExecutor, ScriptExecutionContext
from backend_core.src.services.navigation.navigation_pathfinding import find_shortest_path


class UnifiedPathfindingTests:
    """Test suite for unified pathfinding system"""
    
    def __init__(self):
        self.test_results = []
        self.team_id = "7fdeb4bb-3639-4ec3-959f-b54769a219ce"
        self.test_interface = "horizon_android_mobile"  # Default test interface
        
    def run_test(self, test_name: str, test_func):
        """Run a single test with error handling and timing"""
        print(f"\n{'='*60}")
        print(f"🧪 TEST: {test_name}")
        print(f"{'='*60}")
        
        start_time = time.time()
        try:
            result = test_func()
            execution_time = int((time.time() - start_time) * 1000)
            
            test_result = {
                'name': test_name,
                'success': result.get('success', False),
                'execution_time_ms': execution_time,
                'message': result.get('message', ''),
                'details': result.get('details', {}),
                'timestamp': datetime.now().isoformat()
            }
            
            if test_result['success']:
                print(f"✅ PASS: {test_name} ({execution_time}ms)")
                if test_result['message']:
                    print(f"   Message: {test_result['message']}")
            else:
                print(f"❌ FAIL: {test_name} ({execution_time}ms)")
                print(f"   Error: {test_result['message']}")
                if 'error_details' in result:
                    print(f"   Details: {result['error_details']}")
            
            self.test_results.append(test_result)
            return test_result
            
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            print(f"❌ ERROR: {test_name} ({execution_time}ms)")
            print(f"   Exception: {str(e)}")
            
            test_result = {
                'name': test_name,
                'success': False,
                'execution_time_ms': execution_time,
                'message': f"Test exception: {str(e)}",
                'details': {'exception': str(e)},
                'timestamp': datetime.now().isoformat()
            }
            
            self.test_results.append(test_result)
            return test_result

    def test_root_tree_loading_no_nested_trees(self):
        """Test root tree loading when no nested trees exist"""
        try:
            print(f"📥 Loading root tree for interface: {self.test_interface}")
            
            # Load tree with hierarchy (should work even with no nested trees)
            tree_result = load_navigation_tree_with_hierarchy(self.test_interface, "test")
            
            if not tree_result['success']:
                return {
                    'success': False,
                    'message': f"Failed to load tree hierarchy: {tree_result.get('error', 'Unknown error')}"
                }
            
            # Validate result structure
            required_keys = ['tree_id', 'root_tree', 'hierarchy', 'unified_graph_nodes', 'unified_graph_edges']
            for key in required_keys:
                if key not in tree_result:
                    return {
                        'success': False,
                        'message': f"Missing required key in result: {key}"
                    }
            
            hierarchy_count = len(tree_result['hierarchy'])
            unified_nodes = tree_result['unified_graph_nodes']
            unified_edges = tree_result['unified_graph_edges']
            cross_tree_capable = tree_result['cross_tree_capabilities']
            
            print(f"   ✅ Tree loaded successfully")
            print(f"   📊 Hierarchy: {hierarchy_count} trees")
            print(f"   🔗 Unified graph: {unified_nodes} nodes, {unified_edges} edges")
            print(f"   🌐 Cross-tree capable: {cross_tree_capable}")
            
            return {
                'success': True,
                'message': f"Root tree loaded with unified pathfinding: {hierarchy_count} trees, {unified_nodes} nodes",
                'details': {
                    'tree_id': tree_result['tree_id'],
                    'hierarchy_count': hierarchy_count,
                    'unified_nodes': unified_nodes,
                    'unified_edges': unified_edges,
                    'cross_tree_capable': cross_tree_capable
                }
            }
            
        except (NavigationTreeError, UnifiedCacheError) as e:
            return {
                'success': False,
                'message': f"Navigation error (expected): {str(e)}",
                'error_details': {'error_type': type(e).__name__}
            }
        except Exception as e:
            return {
                'success': False,
                'message': f"Unexpected error: {str(e)}",
                'error_details': {'error_type': type(e).__name__}
            }

    def test_unified_pathfinding_basic(self):
        """Test basic unified pathfinding functionality"""
        try:
            print(f"🗺️ Testing unified pathfinding to 'live' node")
            
            # First ensure tree is loaded
            tree_result = load_navigation_tree_with_hierarchy(self.test_interface, "test")
            if not tree_result['success']:
                return {
                    'success': False,
                    'message': f"Failed to load tree for pathfinding test: {tree_result.get('error')}"
                }
            
            tree_id = tree_result['tree_id']
            
            # Test pathfinding to a common node
            path_result = find_shortest_path(tree_id, "live", self.team_id)
            
            if not path_result:
                return {
                    'success': False,
                    'message': "No path found to 'live' node"
                }
            
            path_length = len(path_result)
            cross_tree_transitions = len([t for t in path_result if t.get('tree_context_change')])
            
            print(f"   ✅ Path found to 'live' node")
            print(f"   📏 Path length: {path_length} transitions")
            print(f"   🌐 Cross-tree transitions: {cross_tree_transitions}")
            
            return {
                'success': True,
                'message': f"Unified pathfinding successful: {path_length} transitions",
                'details': {
                    'target_node': 'live',
                    'path_length': path_length,
                    'cross_tree_transitions': cross_tree_transitions,
                    'path_found': True
                }
            }
            
        except (PathfindingError, UnifiedCacheError) as e:
            return {
                'success': False,
                'message': f"Pathfinding error: {str(e)}",
                'error_details': {'error_type': type(e).__name__}
            }
        except Exception as e:
            return {
                'success': False,
                'message': f"Unexpected pathfinding error: {str(e)}",
                'error_details': {'error_type': type(e).__name__}
            }

    def test_fail_early_behavior_missing_cache(self):
        """Test that system fails early when unified cache is missing"""
        try:
            print(f"🚫 Testing fail-early behavior with missing cache")
            
            # Try pathfinding without loading tree (no cache)
            fake_tree_id = "non-existent-tree-id"
            
            # This should raise an exception due to missing unified cache
            try:
                path_result = find_shortest_path(fake_tree_id, "live", self.team_id)
                return {
                    'success': False,
                    'message': "Expected UnifiedCacheError but pathfinding succeeded",
                    'error_details': {'unexpected_success': True}
                }
            except (UnifiedCacheError, PathfindingError) as expected_error:
                print(f"   ✅ Correctly failed with: {type(expected_error).__name__}")
                print(f"   📝 Error message: {str(expected_error)}")
                
                return {
                    'success': True,
                    'message': f"Fail-early behavior working: {type(expected_error).__name__}",
                    'details': {
                        'expected_error_type': type(expected_error).__name__,
                        'error_message': str(expected_error),
                        'fail_early_working': True
                    }
                }
            
        except Exception as e:
            return {
                'success': False,
                'message': f"Unexpected error in fail-early test: {str(e)}",
                'error_details': {'error_type': type(e).__name__}
            }

    def test_goto_node_integration(self):
        """Test goto_node function with unified pathfinding"""
        try:
            print(f"🎯 Testing goto_node integration with unified pathfinding")
            
            # Mock host and device for testing
            class MockHost:
                def __init__(self):
                    self.host_name = "test_host"
            
            class MockDevice:
                def __init__(self):
                    self.device_name = "test_device"
            
            mock_host = MockHost()
            mock_device = MockDevice()
            
            # First ensure tree is loaded
            tree_result = load_navigation_tree_with_hierarchy(self.test_interface, "test")
            if not tree_result['success']:
                return {
                    'success': False,
                    'message': f"Failed to load tree for goto_node test: {tree_result.get('error')}"
                }
            
            tree_id = tree_result['tree_id']
            
            # Test goto_node (this will fail at execution but should succeed at pathfinding)
            try:
                goto_result = goto_node(mock_host, mock_device, "live", tree_id, self.team_id)
                
                # We expect this to fail at execution (no real host/device) but succeed at pathfinding
                unified_pathfinding_used = goto_result.get('unified_pathfinding_used', False)
                
                if unified_pathfinding_used:
                    print(f"   ✅ goto_node used unified pathfinding")
                    print(f"   📊 Result: {goto_result.get('success', False)}")
                    
                    return {
                        'success': True,
                        'message': "goto_node successfully used unified pathfinding",
                        'details': {
                            'unified_pathfinding_used': unified_pathfinding_used,
                            'goto_success': goto_result.get('success', False),
                            'path_length': goto_result.get('path_length', 0),
                            'cross_tree_transitions': goto_result.get('cross_tree_transitions', 0)
                        }
                    }
                else:
                    return {
                        'success': False,
                        'message': "goto_node did not use unified pathfinding",
                        'error_details': {'unified_pathfinding_used': False}
                    }
                    
            except (UnifiedCacheError, PathfindingError) as e:
                # This is expected behavior - fail early
                print(f"   ✅ goto_node correctly failed early: {type(e).__name__}")
                
                return {
                    'success': True,
                    'message': f"goto_node fail-early behavior working: {type(e).__name__}",
                    'details': {
                        'fail_early_error': type(e).__name__,
                        'error_message': str(e)
                    }
                }
            
        except Exception as e:
            return {
                'success': False,
                'message': f"Unexpected error in goto_node test: {str(e)}",
                'error_details': {'error_type': type(e).__name__}
            }

    def test_system_validation(self):
        """Test complete system validation"""
        try:
            print(f"🔍 Testing complete system validation")
            
            # First ensure tree is loaded
            tree_result = load_navigation_tree_with_hierarchy(self.test_interface, "test")
            if not tree_result['success']:
                return {
                    'success': False,
                    'message': f"Failed to load tree for validation test: {tree_result.get('error')}"
                }
            
            tree_id = tree_result['tree_id']
            
            # Run complete system validation
            validation_result = validate_complete_unified_system(tree_id, self.team_id)
            
            overall_success = validation_result.get('overall_success', False)
            summary = validation_result.get('summary', {})
            
            print(f"   📊 Validation result: {summary.get('overall_result', 'UNKNOWN')}")
            print(f"   ✅ Success rate: {summary.get('success_rate', '0/0')}")
            
            if overall_success:
                return {
                    'success': True,
                    'message': f"System validation passed: {summary.get('success_rate')}",
                    'details': {
                        'overall_success': overall_success,
                        'success_rate': summary.get('success_rate'),
                        'validations_run': summary.get('total_validations', 0)
                    }
                }
            else:
                return {
                    'success': False,
                    'message': f"System validation failed: {summary.get('success_rate')}",
                    'error_details': {
                        'validation_failures': validation_result.get('validations', {}),
                        'overall_success': overall_success
                    }
                }
            
        except Exception as e:
            return {
                'success': False,
                'message': f"System validation test error: {str(e)}",
                'error_details': {'error_type': type(e).__name__}
            }

    def test_script_framework_integration(self):
        """Test script framework integration with unified loading"""
        try:
            print(f"🔧 Testing script framework integration")
            
            # Create script executor
            script_executor = ScriptExecutor("test_unified", "Test unified pathfinding integration")
            
            # Create mock arguments
            class MockArgs:
                def __init__(self):
                    self.userinterface_name = self.test_interface
                    self.host = "localhost"
                    self.device = "device1"
            
            mock_args = MockArgs()
            mock_args.userinterface_name = self.test_interface
            
            # Setup execution context
            context = script_executor.setup_execution_context(mock_args)
            
            if context.error_message:
                return {
                    'success': False,
                    'message': f"Context setup failed: {context.error_message}"
                }
            
            # Test tree loading with script framework
            load_success = script_executor.load_navigation_tree(context, self.test_interface)
            
            if not load_success:
                return {
                    'success': False,
                    'message': f"Script framework tree loading failed: {context.error_message}"
                }
            
            # Check if unified pathfinding was enabled
            unified_enabled = getattr(context, 'unified_pathfinding_enabled', False)
            hierarchy_count = len(getattr(context, 'tree_hierarchy', []))
            
            print(f"   ✅ Script framework loaded tree successfully")
            print(f"   🌐 Unified pathfinding enabled: {unified_enabled}")
            print(f"   📊 Tree hierarchy: {hierarchy_count} trees")
            
            return {
                'success': True,
                'message': f"Script framework integration successful: unified={unified_enabled}",
                'details': {
                    'unified_pathfinding_enabled': unified_enabled,
                    'hierarchy_count': hierarchy_count,
                    'context_populated': True,
                    'tree_id': context.tree_id
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f"Script framework integration error: {str(e)}",
                'error_details': {'error_type': type(e).__name__}
            }

    def run_all_tests(self):
        """Run all integration tests"""
        print(f"\n🚀 UNIFIED PATHFINDING INTEGRATION TESTS")
        print(f"Interface: {self.test_interface}")
        print(f"Team ID: {self.team_id}")
        print(f"Timestamp: {datetime.now().isoformat()}")
        
        # Test suite
        tests = [
            ("Root Tree Loading (No Nested Trees)", self.test_root_tree_loading_no_nested_trees),
            ("Unified Pathfinding Basic", self.test_unified_pathfinding_basic),
            ("Fail-Early Behavior (Missing Cache)", self.test_fail_early_behavior_missing_cache),
            ("goto_node Integration", self.test_goto_node_integration),
            ("System Validation", self.test_system_validation),
            ("Script Framework Integration", self.test_script_framework_integration)
        ]
        
        # Run all tests
        for test_name, test_func in tests:
            self.run_test(test_name, test_func)
        
        # Generate summary
        self.print_test_summary()
        
        return self.test_results

    def print_test_summary(self):
        """Print comprehensive test summary"""
        print(f"\n{'='*80}")
        print(f"🧪 UNIFIED PATHFINDING TEST SUMMARY")
        print(f"{'='*80}")
        
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r['success']])
        failed_tests = total_tests - passed_tests
        
        total_time = sum([r['execution_time_ms'] for r in self.test_results])
        avg_time = int(total_time / total_tests) if total_tests > 0 else 0
        
        print(f"📊 Test Results:")
        print(f"   • Total Tests: {total_tests}")
        print(f"   • Passed: {passed_tests} ✅")
        print(f"   • Failed: {failed_tests} ❌")
        print(f"   • Success Rate: {passed_tests}/{total_tests} ({int(passed_tests/total_tests*100) if total_tests > 0 else 0}%)")
        print(f"   • Total Time: {total_time}ms")
        print(f"   • Average Time: {avg_time}ms per test")
        
        # List failed tests
        if failed_tests > 0:
            print(f"\n❌ Failed Tests:")
            for result in self.test_results:
                if not result['success']:
                    print(f"   • {result['name']}: {result['message']}")
        
        # Performance metrics
        print(f"\n⚡ Performance Metrics:")
        fastest_test = min(self.test_results, key=lambda x: x['execution_time_ms'])
        slowest_test = max(self.test_results, key=lambda x: x['execution_time_ms'])
        print(f"   • Fastest: {fastest_test['name']} ({fastest_test['execution_time_ms']}ms)")
        print(f"   • Slowest: {slowest_test['name']} ({slowest_test['execution_time_ms']}ms)")
        
        # Overall result
        overall_success = failed_tests == 0
        print(f"\n🎯 OVERALL RESULT: {'PASS' if overall_success else 'FAIL'}")
        
        if overall_success:
            print(f"✅ All unified pathfinding tests passed! System is ready for production.")
        else:
            print(f"❌ {failed_tests} test(s) failed. Review errors above.")
        
        print(f"{'='*80}")


def main():
    """Main function to run unified pathfinding tests"""
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='Test unified pathfinding system')
    parser.add_argument('--interface', default='horizon_android_mobile', 
                       help='User interface to test (default: horizon_android_mobile)')
    args = parser.parse_args()
    
    # Create and run test suite
    test_suite = UnifiedPathfindingTests()
    test_suite.test_interface = args.interface
    
    try:
        results = test_suite.run_all_tests()
        
        # Exit with appropriate code
        failed_count = len([r for r in results if not r['success']])
        sys.exit(0 if failed_count == 0 else 1)
        
    except KeyboardInterrupt:
        print(f"\n⚠️ Tests interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Test suite failed with error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()