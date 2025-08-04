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
        
        # Execution tracking
        self.step_results = []
        self.screenshot_paths = []
        self.overall_success = False
        self.error_message = ""
        self.script_result_id = None
        
        # Custom data for specific scripts
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
            
            print(f"✅ [{self.script_name}] Execution context setup completed")
            
        except Exception as e:
            context.error_message = f"Setup error: {str(e)}"
            print(f"❌ [{self.script_name}] {context.error_message}")
        
        return context
    
    def load_navigation_tree(self, context: ScriptExecutionContext, userinterface_name: str) -> bool:
        """Load navigation tree and populate cache"""
        try:
            print(f"🗺️ [{self.script_name}] Loading navigation tree...")
            tree_result = load_navigation_tree(userinterface_name, self.script_name)
            if not tree_result['success']:
                context.error_message = f"Tree loading failed: {tree_result['error']}"
                print(f"❌ [{self.script_name}] {context.error_message}")
                return False
            
            context.tree_data = tree_result['tree']
            context.tree_id = tree_result['tree_id']
            context.nodes = tree_result['nodes']
            context.edges = tree_result['edges']
            
            print(f"✅ [{self.script_name}] Loaded tree with {len(context.nodes)} nodes and {len(context.edges)} edges")
            
            # Populate navigation cache
            print(f"🔄 [{self.script_name}] Populating navigation cache...")
            populate_cache(context.tree_id, context.team_id, context.nodes, context.edges)
            
            return True
            
        except Exception as e:
            context.error_message = f"Navigation tree loading error: {str(e)}"
            print(f"❌ [{self.script_name}] {context.error_message}")
            return False
    
    def execute_navigation_sequence(self, context: ScriptExecutionContext, navigation_path: List[Dict],
                                  custom_step_handler: Callable = None) -> bool:
        """Execute a sequence of navigation steps with optional custom handling per step"""
        try:
            print(f"🎮 [{self.script_name}] Starting navigation on device {context.selected_device.device_id}")
            
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
                        context.host, context.selected_device, step, context.team_id, context.tree_id
                    )
                
                step_end_timestamp = datetime.now().strftime('%H:%M:%S')
                step_execution_time = int((time.time() - step_start_time) * 1000)
                
                # Capture screenshot after step execution
                step_screenshot = capture_validation_screenshot(
                    context.host, context.selected_device, f"step_{step_num}", self.script_name
                )
                context.add_screenshot(step_screenshot)
                
                if step_screenshot:
                    print(f"📸 [{self.script_name}] Step {step_num} screenshot captured")
                
                # Record step result
                step_result = {
                    'step_number': step_num,
                    'success': result.get('success', False),
                    'screenshot_path': step_screenshot,
                    'message': f"Navigation step {step_num}: {from_node} → {to_node}",
                    'execution_time_ms': step_execution_time,
                    'start_time': step_start_timestamp,
                    'end_time': step_end_timestamp,
                    'from_node': from_node,
                    'to_node': to_node,
                    'actions': step.get('actions', []),
                    'verifications': step.get('verifications', []),
                    'verification_results': result.get('verification_results', [])
                }
                context.step_results.append(step_result)
                
                if not result.get('success', False):
                    context.error_message = f"Navigation failed at step {step_num}: {result.get('error', 'Unknown error')}"
                    print(f"❌ [{self.script_name}] {context.error_message}")
                    return False
                
                print(f"✅ [{self.script_name}] Step {step_num} completed successfully in {step_execution_time}ms")
            
            print(f"🎉 [{self.script_name}] All navigation steps completed successfully!")
            return True
            
        except Exception as e:
            context.error_message = f"Navigation execution error: {str(e)}"
            print(f"❌ [{self.script_name}] {context.error_message}")
            return False
    
    def generate_final_report(self, context: ScriptExecutionContext, userinterface_name: str) -> str:
        """Generate and upload final execution report"""
        try:
            # Capture final screenshot
            print(f"📸 [{self.script_name}] Capturing final state screenshot...")
            final_screenshot = capture_validation_screenshot(
                context.host, context.selected_device, "final_state", self.script_name
            )
            context.add_screenshot(final_screenshot)
            
            if final_screenshot:
                print(f"✅ [{self.script_name}] Final screenshot captured")
            
            # Generate and upload report
            device_info = {
                'device_name': context.selected_device.device_name,
                'device_model': context.selected_device.device_model,
                'device_id': context.selected_device.device_id
            }
            host_info = {
                'host_name': context.host.host_name
            }
            
            report_url = generate_and_upload_script_report(
                script_name=f"{self.script_name}.py",
                device_info=device_info,
                host_info=host_info,
                execution_time=context.get_execution_time_ms(),
                success=context.overall_success,
                step_results=context.step_results,
                screenshot_paths=context.screenshot_paths,
                error_message=context.error_message,
                userinterface_name=userinterface_name
            )
            
            if report_url:
                print(f"📊 [{self.script_name}] Report generated: {report_url}")
            
            return report_url
            
        except Exception as e:
            print(f"⚠️ [{self.script_name}] Error in report generation: {e}")
            return ""
    
    def cleanup_and_exit(self, context: ScriptExecutionContext, userinterface_name: str):
        """Cleanup resources and exit with appropriate code"""
        try:
            # Generate report if we have valid execution context
            if context.host and context.selected_device:
                self.generate_final_report(context, userinterface_name)
            
            # Update database if tracking is enabled
            if context.script_result_id and context.error_message and not context.overall_success:
                print(f"📝 [{self.script_name}] Recording error in database...")
                update_script_execution_result(
                    script_result_id=context.script_result_id,
                    success=False,
                    execution_time_ms=context.get_execution_time_ms(),
                    error_msg=context.error_message
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
        if context.overall_success:
            print(f"✅ [{self.script_name}] Exiting with success code 0")
            sys.exit(0)
        else:
            print(f"❌ [{self.script_name}] Exiting with failure code 1")
            sys.exit(1)
    
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