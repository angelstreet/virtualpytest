#!/usr/bin/env python3
"""
Script Utilities for VirtualPyTest

Unified script execution utilities and framework that provides:
- Script environment setup and device management
- Script execution with real-time output streaming  
- Unified framework for navigation and validation scripts
- Device script executor integration
- No device locking (handled by server)

Usage:
    # Basic script execution
    from lib.utils.script_utils import execute_script, setup_script_environment, select_device
    
    # Framework usage
    from lib.utils.script_utils import ScriptExecutor
    
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
import os
import subprocess
import uuid
import glob
import select
from datetime import datetime
from typing import Tuple, Dict, Any, Optional, List, Callable

from shared.src.lib.utils.app_utils import load_environment_variables
from src.lib.utils.host_utils import get_host_instance, list_available_devices, get_controller
from src.lib.utils.navigation_cache import populate_cache
from src.lib.utils.report_utils import generate_and_upload_script_report
from shared.src.lib.supabase.script_results_db import record_script_execution_start, update_script_execution_result
from src.lib.utils.ai_utils import setup_script_environment, select_device, execute_script


# =====================================================
# BASIC SCRIPT EXECUTION UTILITIES
# =====================================================

# Host-specific functions are now imported from ai_utils.py


def get_scripts_directory() -> str:
    """Get the scripts directory path - single source of truth"""
    current_dir = os.path.dirname(os.path.abspath(__file__))  # /backend_host/src/lib/utils
    lib_dir = os.path.dirname(current_dir)  # /backend_host/src/lib
    src_dir = os.path.dirname(lib_dir)  # /backend_host/src
    backend_host_dir = os.path.dirname(src_dir)  # /backend_host
    project_root = os.path.dirname(backend_host_dir)  # /virtualpytest
    
    # Use test_scripts folder as the primary scripts location
    return os.path.join(project_root, 'test_scripts')


def get_script_path(script_name: str) -> str:
    """Get full path to a script file"""
    scripts_dir = get_scripts_directory()
    
    # Handle script names that already have .py extension
    if script_name.endswith('.py'):
        script_path = os.path.join(scripts_dir, script_name)
    else:
        script_path = os.path.join(scripts_dir, f'{script_name}.py')
    
    if not os.path.exists(script_path):
        raise ValueError(f'Script not found: {script_path}')
    
    return script_path


def list_available_scripts() -> list:
    """List all available Python scripts in the scripts directory"""
    scripts_dir = get_scripts_directory()
    
    if not os.path.exists(scripts_dir):
        return []
    
    # Find all Python files in the scripts directory
    script_pattern = os.path.join(scripts_dir, '*.py')
    script_files = glob.glob(script_pattern)
    
    # Extract just the filenames without path and extension
    available_scripts = []
    for script_file in script_files:
        filename = os.path.basename(script_file)
        script_name = os.path.splitext(filename)[0]  # Remove .py extension
        
        # Hide internal AI executor script from user interface
        if script_name == 'ai_testcase_executor':
            continue
            
        available_scripts.append(script_name)
    
    # Sort alphabetically
    available_scripts.sort()
    
    return available_scripts


def execute_command(command: str, timeout: int = 30) -> Tuple[bool, str, str, int]:
    """Execute a shell command with timeout"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        success = result.returncode == 0
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        exit_code = result.returncode
        
        return success, stdout, stderr, exit_code
        
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out", -1
    except Exception as e:
        return False, "", str(e), -1


# execute_script is now imported from ai_utils.py


# =====================================================
# SCRIPT EXECUTION FRAMEWORK
# =====================================================

class ScriptExecutionContext:
    """Context object that holds all execution state"""
    
    def __init__(self, script_name: str):
        self.script_name = script_name
        self.start_time = time.time()
        
        # Infrastructure objects
        self.host = None
        self.team_id = None
        self.selected_device = None
        
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
        
        # Stdout capture for log upload
        self.stdout_buffer = []
        
        # Simple sequential step counter
        self.step_counter = 0
    
    def get_execution_time_ms(self) -> int:
        """Get current execution time in milliseconds"""
        return int((time.time() - self.start_time) * 1000)
    
    def record_step_immediately(self, step_data: Dict[str, Any]) -> int:
        """Record step immediately with simple sequential numbering - returns step number"""
        self.step_counter += 1
        step_data['step_number'] = self.step_counter
        step_data['timestamp'] = time.time()
        self.step_results.append(step_data)
        return self.step_counter

    def add_screenshot(self, screenshot_path: str):
        """Add a screenshot to the collection"""
        if screenshot_path:
            self.screenshot_paths.append(screenshot_path)
    
    def start_stdout_capture(self):
        """Start capturing stdout for log upload"""
        import sys
        import io
        
        # Store original stdout
        self.original_stdout = sys.stdout
        
        # Create a custom stdout that captures and forwards
        class StdoutCapture:
            def __init__(self, original_stdout, buffer):
                self.original_stdout = original_stdout
                self.buffer = buffer
            
            def write(self, text):
                # Write to original stdout (so output still shows)
                self.original_stdout.write(text)
                # Capture in buffer for log upload
                self.buffer.append(text)
                return len(text)
            
            def flush(self):
                self.original_stdout.flush()
            
            def __getattr__(self, name):
                # Forward other attributes to original stdout
                return getattr(self.original_stdout, name)
        
        # Replace stdout with capturing version
        sys.stdout = StdoutCapture(self.original_stdout, self.stdout_buffer)
    
    def stop_stdout_capture(self):
        """Stop capturing stdout and restore original"""
        import sys
        if self.original_stdout:
            sys.stdout = self.original_stdout
            self.original_stdout = None
    
    def get_captured_stdout(self) -> str:
        """Get captured stdout as string"""
        return ''.join(self.stdout_buffer)


class ScriptExecutor:
    """Unified script execution framework using device script executor"""
    
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
        """Setup execution context with infrastructure components - NO DEVICE LOCKING"""
        context = ScriptExecutionContext(self.script_name)
        
        # Start capturing stdout for log upload
        context.start_stdout_capture()
        
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
            
            # 4. Capture initial screenshot using device script executor
            print(f"📸 [{self.script_name}] Capturing initial state screenshot...")
            try:
                # Use device's AV controller directly
                av_controller = context.selected_device.get_controller('av')
                if av_controller:
                    initial_screenshot = av_controller.take_screenshot()
                    context.add_screenshot(initial_screenshot)
                    if initial_screenshot:
                        print(f"✅ [{self.script_name}] Initial screenshot captured")
                    else:
                        print(f"⚠️ [{self.script_name}] Failed to capture initial screenshot, continuing...")
                else:
                    print(f"⚠️ [{self.script_name}] No AV controller found, continuing without screenshot...")
            except Exception as e:
                print(f"[@script_utils] Screenshot failed: {e}")
                print(f"⚠️ [{self.script_name}] Failed to capture initial screenshot, continuing...")
            
            print(f"✅ [{self.script_name}] Execution context setup completed")
            
        except Exception as e:
            context.error_message = f"Setup error: {str(e)}"
            print(f"❌ [{self.script_name}] {context.error_message}")
        
        return context
    
    def load_navigation_tree(self, context: ScriptExecutionContext, userinterface_name: str) -> bool:
        """Load navigation tree using device navigation executor"""
        try:
            print(f"🗺️ [{self.script_name}] Loading unified navigation tree hierarchy...")
            
            # Use device's navigation executor
            if not hasattr(context.selected_device, 'navigation_executor'):
                context.error_message = "Device does not have navigation executor"
                print(f"❌ [{self.script_name}] {context.error_message}")
                return False
            
            nav_executor = context.selected_device.navigation_executor
            
            # Load navigation tree with hierarchy
            tree_result = nav_executor.load_navigation_tree_with_hierarchy(userinterface_name, self.script_name)
            
            # Populate context with hierarchy data
            context.tree_data = tree_result['root_tree']['tree']
            context.tree_id = tree_result['tree_id']
            context.nodes = tree_result['root_tree']['nodes']
            
            # Load unified graph edges for cross-tree action resolution
            from lib.utils.navigation_cache import get_cached_unified_graph
            unified_graph = get_cached_unified_graph(tree_result['tree_id'], context.team_id)
            if unified_graph:
                # Convert NetworkX graph edges to dictionary format for script usage
                unified_edges = []
                for from_node, to_node, edge_data in unified_graph.edges(data=True):
                    unified_edges.append({
                        'source_node_id': from_node,
                        'target_node_id': to_node,
                        **edge_data
                    })
                context.edges = unified_edges
                print(f"[@script_utils] Loaded unified graph edges: {len(unified_edges)} edges (includes cross-tree)")
            else:
                context.edges = tree_result['root_tree']['edges']
                print(f"[@script_utils] Fallback to root tree edges: {len(context.edges)} edges")
            
            context.tree_hierarchy = tree_result['hierarchy']
            context.unified_pathfinding_enabled = True
            
            # Initialize current location to ENTRY node for pathfinding
            context.current_node_id = None  # Will be set to ENTRY by pathfinding system
            
            print(f"✅ [{self.script_name}] Unified hierarchy loaded:")
            print(f"   • Root tree: {len(context.nodes)} nodes, {len(context.edges)} edges")
            print(f"   • Total hierarchy: {len(tree_result['hierarchy'])} trees")
            print(f"   • Unified graph: {tree_result['unified_graph_nodes']} nodes, {tree_result['unified_graph_edges']} edges")
            print(f"   • Cross-tree pathfinding: {'ENABLED' if tree_result['cross_tree_capabilities'] else 'SINGLE-TREE'}")
            
            # After hierarchy loading
            all_nodes = []
            for tree in context.tree_hierarchy:
                all_nodes.extend(tree.get('nodes', []))

            # Store in context
            context.all_nodes = all_nodes
            print(f"   • Total nodes across hierarchy: {len(all_nodes)}")
            
            return True
            
        except Exception as e:
            context.error_message = f"Navigation loading error: {str(e)}"
            print(f"❌ [{self.script_name}] {context.error_message}")
            return False
    
    def execute_navigation_sequence(self, context: ScriptExecutionContext, navigation_path: List[Dict],
                                  custom_step_handler: Callable = None, early_stop_on_failure: bool = False) -> bool:
        """Execute navigation sequence using device action executor"""
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
                
                # Capture step-start screenshot
                step_name = f"step_{step_num}_{from_node}_{to_node}"
                try:
                    av_controller = context.selected_device.get_controller('av')
                    step_start_screenshot = av_controller.take_screenshot() if av_controller else ""
                except Exception as e:
                    print(f"[@script_utils] Screenshot failed: {e}")
                    step_start_screenshot = ""
                
                # Use custom handler if provided, otherwise use device action executor
                if custom_step_handler:
                    result = custom_step_handler(context, step, step_num)
                    # Ensure custom handlers return consistent format with screenshot paths
                    if not result.get('step_start_screenshot_path'):
                        result['step_start_screenshot_path'] = step_start_screenshot
                else:
                    # Use device's action executor for single step execution
                    actions = step.get('actions', [])
                    if actions:
                        # Set navigation context for action executor
                        action_executor = context.selected_device.action_executor
                        action_executor.tree_id = context.tree_id
                        action_executor.edge_id = step.get('edge_id')
                        result = action_executor.execute_actions(actions, team_id=context.team_id)
                    else:
                        result = {'success': True, 'message': 'No actions to execute'}
                
                # Capture step-end screenshot
                try:
                    av_controller = context.selected_device.get_controller('av')
                    step_end_screenshot = av_controller.take_screenshot() if av_controller else ""
                except Exception as e:
                    print(f"[@script_utils] Screenshot failed: {e}")
                    step_end_screenshot = ""
                if not result.get('step_end_screenshot_path'):
                    result['step_end_screenshot_path'] = step_end_screenshot
                
                step_end_timestamp = datetime.now().strftime('%H:%M:%S')
                step_execution_time = int((time.time() - step_start_time) * 1000)
                
                # Collect screenshots
                action_screenshots = result.get('action_screenshots', [])
                for screenshot_path in action_screenshots:
                    context.add_screenshot(screenshot_path)
                
                # Add step screenshots (both start and end)
                if result.get('step_start_screenshot_path'):
                    context.add_screenshot(result.get('step_start_screenshot_path'))
                    print(f"[@script_utils] Added step start screenshot: {result.get('step_start_screenshot_path')}")
                    
                if result.get('step_end_screenshot_path'):
                    context.add_screenshot(result.get('step_end_screenshot_path'))
                    print(f"[@script_utils] Added step end screenshot: {result.get('step_end_screenshot_path')}")
                    
                # Legacy support for single screenshot_path
                if result.get('screenshot_path'):
                    context.add_screenshot(result.get('screenshot_path'))
                
                # Collect verification images (source and reference)
                verification_images = result.get('verification_images', [])
                for verification_image in verification_images:
                    context.add_screenshot(verification_image)
                    print(f"[@script_utils] Added verification image to upload: {verification_image}")
                
                # Update global verification counter for next step
                counter_increment = result.get('global_verification_counter_increment', 0)
                context.global_verification_counter += counter_increment
                print(f"[@script_utils] Updated global verification counter: +{counter_increment} = {context.global_verification_counter}")
                
                # Record step result
                step_result = {
                    'step_number': step_num,
                    'success': result.get('success', False),
                    'step_start_screenshot_path': result.get('step_start_screenshot_path'),
                    'step_end_screenshot_path': result.get('step_end_screenshot_path'),
                    'screenshot_path': result.get('screenshot_path'),  # Legacy support
                    'screenshot_url': result.get('screenshot_url'),
                    'action_screenshots': action_screenshots,
                    'verification_images': verification_images,
                    'message': f"Navigation step {step_num}: {from_node} → {to_node}",
                    'execution_time_ms': step_execution_time,
                    'start_time': step_start_timestamp,
                    'end_time': step_end_timestamp,
                    'from_node': from_node,
                    'to_node': to_node,
                    'actions': step.get('actions', []),
                    'verifications': step.get('verifications', []),
                    'verification_results': result.get('verification_results', []),
                    'error': result.get('error'),
                    'recovered': False  # Will be updated if recovery happens
                }
                
                # Debug log step result screenshots for failed steps
                if not result.get('success', False):
                    print(f"[@script_utils] Failed step {step_num} screenshot data:")
                    print(f"  - step_start_screenshot_path: {step_result.get('step_start_screenshot_path')}")
                    print(f"  - step_end_screenshot_path: {step_result.get('step_end_screenshot_path')}")
                    print(f"  - action_screenshots: {len(action_screenshots)} screenshots")
                    error_msg = result.get('error', 'Unknown error')
                    error_preview = str(error_msg)[:100] + "..." if error_msg and len(str(error_msg)) > 100 else (str(error_msg) if error_msg else 'Unknown error')
                    print(f"  - error: {error_preview}")
                
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
        """Single recovery attempt for failed navigation step using device navigation executor"""
        recovery_target = failed_step.get('from_node_label')
        
        if not recovery_target:
            print(f"🔄 [{self.script_name}] No recovery target identified for step {step_num}")
            return False
        
        print(f"🔄 [{self.script_name}] Attempting single recovery to '{recovery_target}'...")
        context.recovery_attempts += 1
        
        try:
            recovery_start_time = time.time()
            nav_executor = context.selected_device.navigation_executor
            result = nav_executor.execute_navigation(context.tree_id, recovery_target, context.current_node_id)
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
        """Generate and upload final execution report using device info"""
        try:
            print(f"[@script_utils:generate_final_report] DEBUG: Starting final report generation...")
            
            # Capture execution time BEFORE any additional processing
            actual_execution_time_ms = context.get_execution_time_ms()
            actual_test_duration_seconds = actual_execution_time_ms / 1000.0
            # Store in context for use in cleanup_and_exit
            context.baseline_execution_time_ms = actual_execution_time_ms
            print(f"[@script_utils:generate_final_report] DEBUG: Captured baseline execution time: {actual_test_duration_seconds:.1f}s ({actual_execution_time_ms}ms)")
            
            # Capture final screenshot using device AV controller
            print(f"[@script_utils:generate_final_report] DEBUG: Step 1 - Capturing final screenshot...")
            print(f"📸 [{self.script_name}] Capturing final state screenshot...")
            try:
                av_controller = context.selected_device.get_controller('av')
                final_screenshot = av_controller.take_screenshot() if av_controller else ""
                context.add_screenshot(final_screenshot)
                if final_screenshot:
                    print(f"✅ [{self.script_name}] Final screenshot captured")
            except Exception as e:
                print(f"[@script_utils] Screenshot failed: {e}")
            print(f"[@script_utils:generate_final_report] DEBUG: Step 1 completed")
            
            # Capture test execution video using device AV controller
            print(f"[@script_utils:generate_final_report] DEBUG: Step 2 - Capturing video...")
            print(f"🎥 [{self.script_name}] Capturing test execution video...")
            context.test_video_url = ""  # Initialize with empty string
            try:
                av_controller = context.selected_device.get_controller('av')
                
                if av_controller and hasattr(av_controller, 'take_video'):
                    # Use the captured baseline execution time
                    test_start_time = context.start_time
                    current_time = time.time()
                    
                    # Video size logic: same size or more, never less
                    video_duration = max(10.0, actual_test_duration_seconds)
                    
                    print(f"🎥 [{self.script_name}] Test duration: {actual_test_duration_seconds:.1f}s, capturing {video_duration:.1f}s of video")
                    print(f"🕐 [{self.script_name}] Test started: {test_start_time}, current: {current_time}")
                    
                    # Pass both duration and start time for synchronized capture
                    test_video_url = av_controller.take_video(video_duration, test_start_time)
                    if test_video_url:
                        context.test_video_url = test_video_url
                        print(f"✅ [{self.script_name}] Test execution video captured: {test_video_url}")
                    else:
                        print(f"⚠️ [{self.script_name}] Failed to capture test video, continuing with report generation...")
                        context.test_video_url = ""
                else:
                    print(f"⚠️ [{self.script_name}] AV controller doesn't support video capture, continuing with report generation...")
                    context.test_video_url = ""
            except Exception as e:
                print(f"⚠️ [{self.script_name}] Error capturing test video: {e}, continuing with report generation...")
                context.test_video_url = ""
            print(f"[@script_utils:generate_final_report] DEBUG: Step 2 completed")
            
            # Generate and upload report using device script executor info
            print(f"[@script_utils:generate_final_report] DEBUG: Step 3 - Preparing report data...")
            device_info = context.selected_device.script_executor.get_device_info_for_report()
            host_info = context.selected_device.script_executor.get_host_info_for_report()
            print(f"[@script_utils:generate_final_report] DEBUG: Step 3 completed")
            
            print(f"[@script_utils:generate_final_report] DEBUG: Step 4 - Calling generate_and_upload_script_report...")
            print(f"[@script_utils:generate_final_report] DEBUG: Screenshot count: {len(context.screenshot_paths)}")
            print(f"[@script_utils:generate_final_report] DEBUG: Step results count: {len(context.step_results)}")
            
            # Stop stdout capture before generating report
            context.stop_stdout_capture()
            captured_stdout = context.get_captured_stdout()
            
            # Capture report generation output to get URLs
            import io
            import sys
            
            # Capture the report generation output
            old_stdout = sys.stdout
            report_output = io.StringIO()
            sys.stdout = report_output
            
            report_result = generate_and_upload_script_report(
                script_name=f"{self.script_name}.py",
                device_info=device_info,
                host_info=host_info,
                execution_time=actual_execution_time_ms,  # Use captured baseline time
                success=context.overall_success,
                step_results=context.step_results,
                screenshot_paths=context.screenshot_paths,
                error_message=context.error_message,
                userinterface_name=userinterface_name,
                execution_summary=getattr(context, 'execution_summary', ''),
                test_video_url=getattr(context, 'test_video_url', '') or '',
                stdout=captured_stdout,
                script_result_id=context.script_result_id,
                custom_data=context.custom_data
            )
            
            # Restore stdout and get the captured output
            sys.stdout = old_stdout
            report_generation_output = report_output.getvalue()
            
            # Print the captured output so it appears in logs
            print(report_generation_output, end='')
            
            # Extract logs URL from the captured output
            if 'Logs uploaded:' in report_generation_output:
                try:
                    logs_line = [line for line in report_generation_output.split('\n') if 'Logs uploaded:' in line][0]
                    logs_url = logs_line.split('Logs uploaded: ')[1].strip()
                    # Add logs_url to report_result if not already there
                    if report_result and not report_result.get('logs_url'):
                        report_result['logs_url'] = logs_url
                        print(f"[@script_utils] Extracted logs URL: {logs_url}")
                except Exception as e:
                    print(f"[@script_utils] Failed to extract logs URL: {e}")
            
            print(f"[@script_utils:generate_final_report] DEBUG: Step 4 completed - generate_and_upload_script_report returned")
            print(f"[@script_utils:generate_final_report] DEBUG: Report result keys: {list(report_result.keys()) if report_result else 'None'}")
            
            if report_result.get('success') and report_result.get('report_url'):
                print(f"📊 [{self.script_name}] Report generated: {report_result['report_url']}")
                # Display log URL right after report URL
                if report_result.get('logs_url'):
                    print(f"📝 [{self.script_name}] Logs uploaded: {report_result['logs_url']}")
            
            print(f"[@script_utils:generate_final_report] DEBUG: Step 5 - About to return report_result")
            return report_result
            
        except Exception as e:
            print(f"[@script_utils:generate_final_report] ERROR: Exception in generate_final_report: {e}")
            import traceback
            print(f"[@script_utils:generate_final_report] ERROR: Traceback: {traceback.format_exc()}")
            print(f"⚠️ [{self.script_name}] Error in report generation: {e}")
            return {
                'success': False,
                'report_url': '',
                'report_path': ''
            }
    
    def cleanup_and_exit(self, context: ScriptExecutionContext, userinterface_name: str):
        """Cleanup resources and exit with appropriate code - NO DEVICE UNLOCKING"""
        try:
            # Output results for execution system FIRST
            success_str = str(context.overall_success).lower()
            print(f"[@script_utils:cleanup_and_exit] DEBUG: About to output SCRIPT_SUCCESS marker")
            print(f"[@script_utils:cleanup_and_exit] DEBUG: context.overall_success = {context.overall_success}")
            print(f"[@script_utils:cleanup_and_exit] DEBUG: success_str = {success_str}")
            print(f"SCRIPT_SUCCESS:{success_str}")
            import sys
            sys.stdout.flush()  # Force immediate output so it gets captured even if process crashes
            print(f"[@script_utils:cleanup_and_exit] DEBUG: SCRIPT_SUCCESS marker printed and flushed")
            
            # Generate report AFTER outputting success marker
            report_result = None
            if context.host and context.selected_device:
                print(f"📊 [{self.script_name}] Generating report...")
                report_result = self.generate_final_report(context, userinterface_name)
                
            if report_result and report_result.get('success') and report_result.get('report_url'):
                print(f"📊 [{self.script_name}] Report generated: {report_result['report_url']}")
                # Display log URL right after report URL
                if report_result.get('logs_url'):
                    print(f"📝 [{self.script_name}] Logs uploaded: {report_result['logs_url']}")
                # Store report URL and logs URL for final summary
                if not hasattr(context, 'custom_data'):
                    context.custom_data = {}
                context.custom_data['report_url'] = report_result['report_url']
                # Store logs URL in context for later display
                if report_result.get('logs_url'):
                    context.logs_url = report_result['logs_url']
            
            # Update database if tracking is enabled
            if context.script_result_id:
                if context.overall_success:
                    print(f"📝 [{self.script_name}] Recording success in database...")
                    # Use baseline execution time if available, otherwise current time
                    execution_time_for_db = getattr(context, 'baseline_execution_time_ms', context.get_execution_time_ms())
                    print(f"[@script_utils:cleanup_and_exit] DEBUG: Using execution time for DB: {execution_time_for_db}ms ({execution_time_for_db/1000:.1f}s)")
                    update_script_execution_result(
                        script_result_id=context.script_result_id,
                        success=True,
                        execution_time_ms=execution_time_for_db,
                        html_report_r2_path=report_result.get('report_path') if report_result and report_result.get('success') else None,
                        html_report_r2_url=report_result.get('report_url') if report_result and report_result.get('success') else None,
                        logs_r2_path=report_result.get('logs_path') if report_result and report_result.get('success') else None,
                        logs_r2_url=report_result.get('logs_url') if report_result and report_result.get('success') else None,
                        error_msg=None
                    )
                else:
                    print(f"📝 [{self.script_name}] Recording failure in database...")
                    # Use baseline execution time if available, otherwise current time
                    execution_time_for_db = getattr(context, 'baseline_execution_time_ms', context.get_execution_time_ms())
                    update_script_execution_result(
                        script_result_id=context.script_result_id,
                        success=False,
                        execution_time_ms=execution_time_for_db,
                        html_report_r2_path=report_result.get('report_path') if report_result and report_result.get('success') else None,
                        html_report_r2_url=report_result.get('report_url') if report_result and report_result.get('success') else None,
                        logs_r2_path=report_result.get('logs_path') if report_result and report_result.get('success') else None,
                        logs_r2_url=report_result.get('logs_url') if report_result and report_result.get('success') else None,
                        error_msg=context.error_message or 'Script execution failed'
                    )
        except Exception as e:
            print(f"⚠️ [{self.script_name}] Error during report generation: {e}")
        
        # Always stop stdout capture - NO DEVICE UNLOCKING (handled by server)
        context.stop_stdout_capture()
        
        # Print summary (use baseline time if available)
        baseline_time = getattr(context, 'baseline_execution_time_ms', None)
        self.print_execution_summary(context, userinterface_name, baseline_time)
        
        # Exit with proper code
        print(f"✅ [{self.script_name}] Script execution completed (test result: {'PASS' if context.overall_success else 'FAIL'})")
        sys.exit(0)
    
    def print_execution_summary(self, context: ScriptExecutionContext, userinterface_name: str, execution_time_ms: int = None):
        """Print execution summary"""
        print("\n" + "="*60)
        print(f"🎯 [{self.script_name.upper()}] EXECUTION SUMMARY")
        print("="*60)
        
        if context.selected_device and context.host:
            print(f"📱 Device: {context.selected_device.device_name} ({context.selected_device.device_model})")
            print(f"🖥️  Host: {context.host.host_name}")
        
        print(f"📋 Interface: {userinterface_name}")
        # Use passed execution time if available, otherwise fall back to context time
        display_time_ms = execution_time_ms if execution_time_ms is not None else context.get_execution_time_ms()
        print(f"⏱️  Total Time: {display_time_ms/1000:.1f}s")
        print(f"📊 Steps: {len(context.step_results)} executed")
        print(f"📸 Screenshots: {len(context.screenshot_paths)} captured")
        print(f"🎯 Result: {'SUCCESS' if context.overall_success else 'FAILED'}")
        
        if context.error_message:
            print(f"❌ Error: {context.error_message}")
        
        # Show simple step summary
        print(f"\n📋 Steps executed: {len(context.step_results)}")
        
        # Show custom data from scripts
        if hasattr(context, 'custom_data') and context.custom_data:
            for key, value in context.custom_data.items():
                print(f"{key}: {value}")
                # Display log URL right after report URL
                if key == 'report_url' and hasattr(context, 'logs_url') and context.logs_url:
                    print(f"logs_url: {context.logs_url}")
        
        print("="*60)


# =====================================================
# UTILITY FUNCTIONS
# =====================================================

def handle_keyboard_interrupt(script_name: str):
    """Standard keyboard interrupt handler"""
    print(f"\n⚠️ [{script_name}] Execution interrupted by user")
    sys.exit(130)  # Standard exit code for keyboard interrupt


def handle_unexpected_error(script_name: str, error: Exception):
    """Standard unexpected error handler"""
    error_message = f"Unexpected error: {str(error)}"
    print(f"❌ [{script_name}] {error_message}")
    sys.exit(1)
