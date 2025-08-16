#!/usr/bin/env python3
"""
Script Framework for VirtualPyTest

This module provides a unified framework for executing navigation and validation scripts,
eliminating code duplication across multiple script files.

Usage:
    from shared.lib.utils.script_framework import ScriptExecutor
    
    executor = ScriptExecutor("script_name", "Script description")
    result = executor.execute_navigation_script(
        userinterface_name="horizon_android_mobile",
        target_node="live_fullscreen",
        custom_execution_func=my_custom_function
    )
"""

import sys
import argparse
import time
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable
import os

# Add project root to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))

if project_root not in sys.path:
    sys.path.insert(0, project_root)

from shared.lib.utils.script_execution_utils import (
    setup_script_environment,
    select_device,
    take_device_control,
    release_device_control
)
from shared.lib.utils.navigation_utils import load_navigation_tree
from shared.lib.utils.action_utils import (
    execute_navigation_with_verifications,
    capture_validation_screenshot
)

from shared.lib.utils.navigation_cache import populate_cache
from shared.lib.utils.report_utils import generate_and_upload_script_report
from shared.lib.supabase.script_results_db import record_script_execution_start, update_script_execution_result


class ScriptExecutionContext:
    """Context object that holds all execution state"""
    
    def __init__(self, script_name: str):
        self.script_name = script_name
        self.start_time = time.time()
        
        # Infrastructure objects
        self.host = None
        self.team_id = None
        self.selected_device = None
        self.session_id = None
        self.device_key = None
        
        # Navigation objects
        self.tree_data = None
        self.tree_id = None
        self.nodes = []
        self.edges = []
        self.current_node_id = None  # Track current location for pathfinding
        
        # Execution tracking
        self.step_results = []
        self.screenshot_paths = []
        self.overall_success = False
        self.error_message = ""
        self.script_result_id = None
        
        # Recovery tracking for resilient validation
        self.failed_steps: List[Dict] = []        # Track failed steps
        self.recovery_attempts: int = 0           # Count total recovery attempts
        self.recovered_steps: int = 0             # Count successful recoveries
        
        # Global verification counter to prevent overwriting verification images
        self.global_verification_counter: int = 0
        
        # Custom data for display in final summary
        self.custom_data = {}
    
    def get_execution_time_ms(self) -> int:
        """Get current execution time in milliseconds"""
        return int((time.time() - self.start_time) * 1000)
    
    def add_screenshot(self, screenshot_path: str):
        """Add a screenshot to the collection"""
        if screenshot_path:
            self.screenshot_paths.append(screenshot_path)


class ScriptExecutor:
    """Unified script execution framework"""
    
    def __init__(self, script_name: str, description: str = ""):
        self.script_name = script_name
        self.description = description
    
    def create_argument_parser(self, additional_args: List[Dict] = None) -> argparse.ArgumentParser:
        """Create standard argument parser with optional additional arguments"""
        parser = argparse.ArgumentParser(description=self.description)
        
        # Standard arguments for all scripts
        parser.add_argument('userinterface_name', nargs='?', default='horizon_android_mobile',
                          help='Name of the userinterface to use (default: horizon_android_mobile)')
        parser.add_argument('--host', help='Specific host to use (default: sunri-pi1)')
        parser.add_argument('--device', help='Specific device to use (default: device1)')
        
        # Add additional custom arguments
        if additional_args:
            for arg in additional_args:
                parser.add_argument(arg['name'], **arg['kwargs'])
        
        return parser
    
    def setup_execution_context(self, args, enable_db_tracking: bool = False) -> ScriptExecutionContext:
        """Setup execution context with infrastructure components"""
        context = ScriptExecutionContext(self.script_name)
        
        print(f"🎯 [{self.script_name}] Starting execution for: {args.userinterface_name}")
        
        try:
            # 1. Setup script environment
            setup_result = setup_script_environment(self.script_name)
            if not setup_result['success']:
                context.error_message = f"Setup failed: {setup_result['error']}"
                print(f"❌ [{self.script_name}] {context.error_message}")
                return context
            
            context.host = setup_result['host']
            context.team_id = setup_result['team_id']
            
            # 2. Select device
            device_id_to_use = args.device or "device1"
            device_result = select_device(context.host, device_id_to_use, self.script_name)
            if not device_result['success']:
                context.error_message = f"Device selection failed: {device_result['error']}"
                print(f"❌ [{self.script_name}] {context.error_message}")
                return context
            
            context.selected_device = device_result['device']
            
            # 3. Record script execution start in database (if enabled)
            if enable_db_tracking:
                context.script_result_id = record_script_execution_start(
                    team_id=context.team_id,
                    script_name=self.script_name,
                    script_type=self.script_name,
                    userinterface_name=args.userinterface_name,
                    host_name=context.host.host_name,
                    device_name=context.selected_device.device_name,
                    metadata={
                        'device_id': context.selected_device.device_id,
                        'device_model': context.selected_device.device_model
                    }
                )
                
                if context.script_result_id:
                    print(f"📝 [{self.script_name}] Script execution recorded with ID: {context.script_result_id}")
                    # Output script result ID in a format that campaign executor can parse
                    print(f"SCRIPT_RESULT_ID:{context.script_result_id}")
            
            # 4. Take device control
            control_result = take_device_control(context.host, context.selected_device, self.script_name)
            if not control_result['success']:
                context.error_message = f"Failed to take device control: {control_result['error']}"
                print(f"❌ [{self.script_name}] {context.error_message}")
                return context
            
            context.session_id = control_result['session_id']
            context.device_key = control_result['device_key']
            
            # 5. Capture initial screenshot
            print(f"📸 [{self.script_name}] Capturing initial state screenshot...")
            initial_screenshot = capture_validation_screenshot(
                context.host, context.selected_device, "initial_state", self.script_name
            )
            context.add_screenshot(initial_screenshot)
            
            if initial_screenshot:
                print(f"✅ [{self.script_name}] Initial screenshot captured")
            else:
                print(f"⚠️ [{self.script_name}] Failed to capture initial screenshot, continuing...")
            
            # Note: Video will be captured at the end to cover the entire test execution
            
            print(f"✅ [{self.script_name}] Execution context setup completed")
            
        except Exception as e:
            context.error_message = f"Setup error: {str(e)}"
            print(f"❌ [{self.script_name}] {context.error_message}")
        
        return context
    
    def load_navigation_tree(self, context: ScriptExecutionContext, userinterface_name: str) -> bool:
        """Load navigation tree with mandatory unified pathfinding support"""
        try:
            from shared.lib.utils.navigation_utils import load_navigation_tree_with_hierarchy
            from shared.lib.utils.navigation_exceptions import NavigationTreeError, UnifiedCacheError
            
            print(f"🗺️ [{self.script_name}] Loading unified navigation tree hierarchy...")
            
            # Use new unified loading - NO FALLBACK
            tree_result = load_navigation_tree_with_hierarchy(userinterface_name, self.script_name)
            
            # Populate context with hierarchy data
            context.tree_data = tree_result['root_tree']['tree']
            context.tree_id = tree_result['tree_id']
            context.nodes = tree_result['root_tree']['nodes']
            context.edges = tree_result['root_tree']['edges']
            context.tree_hierarchy = tree_result['hierarchy']
            context.unified_pathfinding_enabled = True
            
            # Initialize current location to ENTRY node for pathfinding
            context.current_node_id = None  # Will be set to ENTRY by pathfinding system
            
            print(f"✅ [{self.script_name}] Unified hierarchy loaded:")
            print(f"   • Root tree: {len(context.nodes)} nodes, {len(context.edges)} edges")
            print(f"   • Total hierarchy: {len(tree_result['hierarchy'])} trees")
            print(f"   • Unified graph: {tree_result['unified_graph_nodes']} nodes, {tree_result['unified_graph_edges']} edges")
            print(f"   • Cross-tree pathfinding: {'ENABLED' if tree_result['cross_tree_capabilities'] else 'SINGLE-TREE'}")
            
            return True
            
        except (NavigationTreeError, UnifiedCacheError) as e:
            context.error_message = f"Unified navigation loading failed: {str(e)}"
            print(f"❌ [{self.script_name}] {context.error_message}")
            return False
        except Exception as e:
            context.error_message = f"Unexpected navigation loading error: {str(e)}"
            print(f"❌ [{self.script_name}] {context.error_message}")
            return False
    
    def execute_navigation_sequence(self, context: ScriptExecutionContext, navigation_path: List[Dict],
                                  custom_step_handler: Callable = None, early_stop_on_failure: bool = False) -> bool:
        """Execute navigation sequence with single-retry recovery on failures
        
        Args:
            context: Script execution context
            navigation_path: List of navigation steps to execute
            custom_step_handler: Optional custom handler for step execution
            early_stop_on_failure: If True, stop immediately when first step fails (goto behavior)
                                  If False, continue with recovery attempts (validation behavior)
        """
        try:
            print(f"🎮 [{self.script_name}] Starting resilient navigation on device {context.selected_device.device_id}")
            
            for i, step in enumerate(navigation_path):
                step_num = i + 1
                from_node = step.get('from_node_label', 'unknown')
                to_node = step.get('to_node_label', 'unknown')
                
                print(f"⚡ [{self.script_name}] Executing step {step_num}/{len(navigation_path)}: {from_node} → {to_node}")
                
                # Execute the navigation step
                step_start_time = time.time()
                step_start_timestamp = datetime.now().strftime('%H:%M:%S')
                
                # Use custom handler if provided, otherwise use default navigation
                if custom_step_handler:
                    result = custom_step_handler(context, step, step_num)
                else:
                    result = execute_navigation_with_verifications(
                        context.host, context.selected_device, step, context.team_id, context.tree_id,
                        script_result_id=context.script_result_id, script_context='script', 
                        global_verification_counter=context.global_verification_counter
                    )
                
                step_end_timestamp = datetime.now().strftime('%H:%M:%S')
                step_execution_time = int((time.time() - step_start_time) * 1000)
                
                # Collect screenshots
                action_screenshots = result.get('action_screenshots', [])
                for screenshot_path in action_screenshots:
                    context.add_screenshot(screenshot_path)
                
                # Add step screenshots (both start and end)
                if result.get('step_start_screenshot_path'):
                    context.add_screenshot(result.get('step_start_screenshot_path'))
                if result.get('step_end_screenshot_path'):
                    context.add_screenshot(result.get('step_end_screenshot_path'))
                    
                # Legacy support for single screenshot_path
                if result.get('screenshot_path'):
                    context.add_screenshot(result.get('screenshot_path'))
                
                # Collect verification images (source and reference)
                verification_images = result.get('verification_images', [])
                for verification_image in verification_images:
                    context.add_screenshot(verification_image)
                    print(f"[@script_framework] Added verification image to upload: {verification_image}")
                
                # Update global verification counter for next step
                counter_increment = result.get('global_verification_counter_increment', 0)
                context.global_verification_counter += counter_increment
                print(f"[@script_framework] Updated global verification counter: +{counter_increment} = {context.global_verification_counter}")
                
                # Record step result
                step_result = {
                    'step_number': step_num,
                    'success': result.get('success', False),
                    'step_start_screenshot_path': result.get('step_start_screenshot_path'),
                    'step_end_screenshot_path': result.get('step_end_screenshot_path'),
                    'screenshot_path': result.get('screenshot_path'),  # Legacy support
                    'screenshot_url': result.get('screenshot_url'),
                    'action_screenshots': action_screenshots,
                    'verification_images': verification_images,  # Store verification images with step
                    'message': f"Navigation step {step_num}: {from_node} → {to_node}",
                    'execution_time_ms': step_execution_time,
                    'start_time': step_start_timestamp,
                    'end_time': step_end_timestamp,
                    'from_node': from_node,
                    'to_node': to_node,
                    'actions': step.get('actions', []),
                    'verifications': step.get('verifications', []),
                    'verification_results': result.get('verification_results', []),
                    'error': result.get('error'),  # Store actual error message from action execution
                    'recovered': False  # Will be updated if recovery happens
                }
                context.step_results.append(step_result)
                
                # Handle step failure with single recovery attempt
                if not result.get('success', False):
                    failure_msg = f"Step {step_num} failed: {result.get('error', 'Unknown error')}"
                    print(f"⚠️ [{self.script_name}] {failure_msg}")
                    
                    # Record failed step
                    context.failed_steps.append({
                        'step_number': step_num,
                        'from_node': from_node,
                        'to_node': to_node,
                        'error': result.get('error'),
                        'verification_results': result.get('verification_results', [])
                    })
                    
                    # For goto functions: stop immediately on first failure
                    if early_stop_on_failure:
                        print(f"🛑 [{self.script_name}] Early stop enabled - stopping navigation after first step failure")
                        context.error_message = f"Navigation stopped early: {failure_msg}"
                        context.overall_success = False
                        return False
                    
                    # For validation: attempt single recovery and continue
                    recovery_success = self._attempt_single_recovery(context, step, step_num)
                    if recovery_success:
                        step_result['recovered'] = True
                        context.recovered_steps += 1
                    
                    # Continue with next step regardless of recovery result
                    continue
                else:
                    print(f"✅ [{self.script_name}] Step {step_num} completed successfully in {step_execution_time}ms")
                    print(f"📸 [{self.script_name}] Step {step_num} captured {len(action_screenshots)} action screenshots")
            
            # Determine overall success based on actual step success rate
            total_successful = len([s for s in context.step_results if s.get('success', False)])
            total_steps = len(navigation_path)
            success_rate = total_successful / total_steps if total_steps > 0 else 0
            
            print(f"🎉 [{self.script_name}] Navigation sequence completed!")
            print(f"📊 [{self.script_name}] Results: {total_successful}/{total_steps} steps successful ({success_rate:.1%})")
            print(f"🔄 [{self.script_name}] Recovery: {context.recovered_steps} successful recoveries")
            
            # Define success criteria: at least 80% of steps must succeed
            navigation_success = success_rate >= 0.8
            print(f"🎯 [{self.script_name}] Navigation {'SUCCESS' if navigation_success else 'FAILED'} (threshold: 80%)")
            
            return navigation_success
            
        except Exception as e:
            context.error_message = f"Navigation execution error: {str(e)}"
            print(f"❌ [{self.script_name}] {context.error_message}")
            return False
    
    def _attempt_single_recovery(self, context: ScriptExecutionContext, failed_step: Dict, step_num: int) -> bool:
        """
        Single recovery attempt for failed navigation step
        
        Strategy: Try to navigate to the source node of the failed step
        If source node was 'live' and we're trying to go to 'live_audiomenu',
        attempt to go back to 'live' to continue validation from there.
        """
        recovery_target = failed_step.get('from_node_label')
        
        if not recovery_target:
            print(f"🔄 [{self.script_name}] No recovery target identified for step {step_num}")
            return False
        
        print(f"🔄 [{self.script_name}] Attempting single recovery to '{recovery_target}'...")
        context.recovery_attempts += 1
        
        try:
            from shared.lib.utils.navigation_utils import goto_node
            
            recovery_start_time = time.time()
            result = goto_node(
                context.host, 
                context.selected_device, 
                recovery_target, 
                context.tree_id, 
                context.team_id,
                context
            )
            recovery_time = int((time.time() - recovery_start_time) * 1000)
            
            if result.get('success'):
                print(f"✅ [{self.script_name}] Recovery successful: navigated to '{recovery_target}' in {recovery_time}ms")
                return True
            else:
                print(f"❌ [{self.script_name}] Recovery failed: {result.get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            print(f"❌ [{self.script_name}] Recovery exception: {str(e)}")
            return False
    
    def generate_final_report(self, context: ScriptExecutionContext, userinterface_name: str) -> Dict[str, str]:
        """Generate and upload final execution report"""
        try:
            print(f"[@script_framework:generate_final_report] DEBUG: Starting final report generation...")
            
            # Capture final screenshot
            print(f"[@script_framework:generate_final_report] DEBUG: Step 1 - Capturing final screenshot...")
            print(f"📸 [{self.script_name}] Capturing final state screenshot...")
            final_screenshot = capture_validation_screenshot(
                context.host, context.selected_device, "final_state", self.script_name
            )
            context.add_screenshot(final_screenshot)
            
            if final_screenshot:
                print(f"✅ [{self.script_name}] Final screenshot captured")
            print(f"[@script_framework:generate_final_report] DEBUG: Step 1 completed")
            
            # Capture test execution video (duration based on test execution time)
            print(f"[@script_framework:generate_final_report] DEBUG: Step 2 - Capturing video...")
            print(f"🎥 [{self.script_name}] Capturing test execution video...")
            context.test_video_url = ""  # Initialize with empty string
            try:
                # Use same pattern as screenshots - get AV controller directly
                from .host_utils import get_controller
                av_controller = get_controller(context.selected_device.device_id, 'av')
                
                if av_controller and hasattr(av_controller, 'take_video'):
                    # Calculate time-synchronized video capture
                    test_duration_seconds = context.get_execution_time_ms() / 1000.0
                    test_start_time = context.start_time
                    current_time = time.time()
                    
                    # Video size logic: same size or more, never less
                    video_duration = max(10.0, test_duration_seconds)  # At least 10s, but capture full test
                    
                    print(f"🎥 [{self.script_name}] Test duration: {test_duration_seconds:.1f}s, capturing {video_duration:.1f}s of video")
                    print(f"🕐 [{self.script_name}] Test started: {test_start_time}, current: {current_time}")
                    
                    # Pass both duration and start time for synchronized capture
                    test_video_url = av_controller.take_video(video_duration, test_start_time)
                    if test_video_url:
                        context.test_video_url = test_video_url
                        print(f"✅ [{self.script_name}] Test execution video captured: {test_video_url}")
                    else:
                        print(f"⚠️ [{self.script_name}] Failed to capture test video, continuing with report generation...")
                        context.test_video_url = ""  # Ensure it's empty string, not None
                else:
                    print(f"⚠️ [{self.script_name}] AV controller doesn't support video capture, continuing with report generation...")
                    context.test_video_url = ""
            except Exception as e:
                print(f"⚠️ [{self.script_name}] Error capturing test video: {e}, continuing with report generation...")
                context.test_video_url = ""  # Ensure report generation continues
            print(f"[@script_framework:generate_final_report] DEBUG: Step 2 completed")
            
            # Generate and upload report
            print(f"[@script_framework:generate_final_report] DEBUG: Step 3 - Preparing report data...")
            device_info = {
                'device_name': context.selected_device.device_name,
                'device_model': context.selected_device.device_model,
                'device_id': context.selected_device.device_id
            }
            host_info = {
                'host_name': context.host.host_name
            }
            print(f"[@script_framework:generate_final_report] DEBUG: Step 3 completed")
            
            print(f"[@script_framework:generate_final_report] DEBUG: Step 4 - Calling generate_and_upload_script_report...")
            print(f"[@script_framework:generate_final_report] DEBUG: Screenshot count: {len(context.screenshot_paths)}")
            print(f"[@script_framework:generate_final_report] DEBUG: Step results count: {len(context.step_results)}")
            
            report_result = generate_and_upload_script_report(
                script_name=f"{self.script_name}.py",
                device_info=device_info,
                host_info=host_info,
                execution_time=context.get_execution_time_ms(),
                success=context.overall_success,
                step_results=context.step_results,
                screenshot_paths=context.screenshot_paths,
                error_message=context.error_message,
                userinterface_name=userinterface_name,
                execution_summary=getattr(context, 'execution_summary', ''),
                test_video_url=getattr(context, 'test_video_url', '') or ''
            )
            print(f"[@script_framework:generate_final_report] DEBUG: Step 4 completed - generate_and_upload_script_report returned")
            print(f"[@script_framework:generate_final_report] DEBUG: Report result keys: {list(report_result.keys()) if report_result else 'None'}")
            
            if report_result.get('success') and report_result.get('report_url'):
                print(f"📊 [{self.script_name}] Report generated: {report_result['report_url']}")
            
            print(f"[@script_framework:generate_final_report] DEBUG: Step 5 - About to return report_result")
            return report_result
            
        except Exception as e:
            print(f"[@script_framework:generate_final_report] ERROR: Exception in generate_final_report: {e}")
            import traceback
            print(f"[@script_framework:generate_final_report] ERROR: Traceback: {traceback.format_exc()}")
            print(f"⚠️ [{self.script_name}] Error in report generation: {e}")
            return {
                'success': False,
                'report_url': '',
                'report_path': ''
            }
    
    def cleanup_and_exit(self, context: ScriptExecutionContext, userinterface_name: str):
        """Cleanup resources and exit with appropriate code"""
        try:
            # Output results for execution system FIRST (before potentially failing report generation)
            success_str = str(context.overall_success).lower()
            print(f"[@script_framework:cleanup_and_exit] DEBUG: About to output SCRIPT_SUCCESS marker")
            print(f"[@script_framework:cleanup_and_exit] DEBUG: context.overall_success = {context.overall_success}")
            print(f"[@script_framework:cleanup_and_exit] DEBUG: success_str = {success_str}")
            print(f"SCRIPT_SUCCESS:{success_str}")
            import sys
            sys.stdout.flush()  # Force immediate output so it gets captured even if process crashes
            print(f"[@script_framework:cleanup_and_exit] DEBUG: SCRIPT_SUCCESS marker printed and flushed")
            
            # Generate report AFTER outputting success marker (so it's captured even if report fails)
            report_result = None
            if context.host and context.selected_device:
                print(f"📊 [{self.script_name}] Generating report...")
                report_result = self.generate_final_report(context, userinterface_name)
                
            if report_result and report_result.get('success') and report_result.get('report_url'):
                print(f"SCRIPT_REPORT_URL:{report_result['report_url']}")
                print(f"[@script_framework:cleanup_and_exit] DEBUG: SCRIPT_REPORT_URL printed")
                # Store report URL for final summary in custom_data (consistent with validation.py)
                if not hasattr(context, 'custom_data'):
                    context.custom_data = {}
                context.custom_data['report_url'] = report_result['report_url']
            
            # Update database if tracking is enabled
            if context.script_result_id:
                if context.overall_success:
                    print(f"📝 [{self.script_name}] Recording success in database...")
                    update_script_execution_result(
                        script_result_id=context.script_result_id,
                        success=True,
                        execution_time_ms=context.get_execution_time_ms(),
                        html_report_r2_path=report_result.get('report_path') if report_result and report_result.get('success') else None,
                        html_report_r2_url=report_result.get('report_url') if report_result and report_result.get('success') else None,
                        error_msg=None
                    )
                else:
                    print(f"📝 [{self.script_name}] Recording failure in database...")
                    update_script_execution_result(
                        script_result_id=context.script_result_id,
                        success=False,
                        execution_time_ms=context.get_execution_time_ms(),
                        html_report_r2_path=report_result.get('report_path') if report_result and report_result.get('success') else None,
                        html_report_r2_url=report_result.get('report_url') if report_result and report_result.get('success') else None,
                        error_msg=context.error_message or 'Script execution failed'
                    )
        except Exception as e:
            print(f"⚠️ [{self.script_name}] Error during report generation: {e}")
        
        # Always release device control
        if context.device_key and context.session_id:
            print(f"🔓 [{self.script_name}] Releasing control of device...")
            release_device_control(context.device_key, context.session_id, self.script_name)
        
        # Print summary
        self.print_execution_summary(context, userinterface_name)
        
        # Exit with proper code
        print(f"✅ [{self.script_name}] Script execution completed (test result: {'PASS' if context.overall_success else 'FAIL'})")
        sys.exit(0)
    
    def print_execution_summary(self, context: ScriptExecutionContext, userinterface_name: str):
        """Print execution summary"""
        print("\n" + "="*60)
        print(f"🎯 [{self.script_name.upper()}] EXECUTION SUMMARY")
        print("="*60)
        
        if context.selected_device and context.host:
            print(f"📱 Device: {context.selected_device.device_name} ({context.selected_device.device_model})")
            print(f"🖥️  Host: {context.host.host_name}")
        
        print(f"📋 Interface: {userinterface_name}")
        print(f"⏱️  Total Time: {context.get_execution_time_ms()/1000:.1f}s")
        print(f"📊 Steps: {len(context.step_results)} executed")
        print(f"📸 Screenshots: {len(context.screenshot_paths)} captured")
        print(f"🎯 Result: {'SUCCESS' if context.overall_success else 'FAILED'}")
        
        if context.error_message:
            print(f"❌ Error: {context.error_message}")
        
        # Show custom data from scripts
        if hasattr(context, 'custom_data') and context.custom_data:
            for key, value in context.custom_data.items():
                print(f"{key}: {value}")
        
        print("="*60)


def handle_keyboard_interrupt(script_name: str):
    """Standard keyboard interrupt handler"""
    print(f"\n⚠️ [{script_name}] Execution interrupted by user")
    sys.exit(130)  # Standard exit code for keyboard interrupt


def handle_unexpected_error(script_name: str, error: Exception):
    """Standard unexpected error handler"""
    error_message = f"Unexpected error: {str(error)}"
    print(f"❌ [{script_name}] {error_message}")
    sys.exit(1)