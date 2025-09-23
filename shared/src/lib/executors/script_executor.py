"""
Unified Script Executor for VirtualPyTest

Complete script execution system that handles:
- Context preparation (device setup, navigation loading)
- Python script execution with real-time output streaming
- Screenshot/video capture and report generation
- Database tracking and cleanup

Usage:
    executor = ScriptExecutor("script_name", "Description")
    context = executor.prepare_context(args)
    result = executor.execute_script_with_context(context)
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
from typing import Dict, List, Optional, Any, Tuple

# Import required modules for context preparation
from shared.src.lib.utils.app_utils import load_environment_variables
from shared.src.lib.utils.report_generation_utils import generate_and_upload_script_report
from shared.src.lib.supabase.script_results_db import record_script_execution_start, update_script_execution_result

DEFAULT_TEAM_ID = '7fdeb4bb-3639-4ec3-959f-b54769a219ce'


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
        if hasattr(self, 'original_stdout') and self.original_stdout:
            sys.stdout = self.original_stdout
            self.original_stdout = None
    
    def get_captured_stdout(self) -> str:
        """Get captured stdout as string"""
        return ''.join(self.stdout_buffer)
    
    def record_step_dict(self, step_dict: dict):
        """Record a step using dict format (backward compatible with existing reporting)"""
        # Add step number
        step_dict['step_number'] = len(self.step_results) + 1
        
        # Add to step_results (existing reporting expects this)
        self.step_results.append(step_dict)
        
        # Add screenshots to context if present
        screenshots = step_dict.get('screenshots', [])
        for screenshot in screenshots:
            if screenshot:
                self.add_screenshot(screenshot)


class ScriptExecutor:
    """
    Unified script executor that handles:
    - Context preparation (device setup, navigation loading)
    - High-level navigation with automatic step recording
    - Script execution with real-time output streaming
    - AI test case redirection
    - Report generation integration
    """
    
    def __init__(self, script_name: str = None, description: str = "", host_name: str = None, device_id: str = None, device_model: str = None):
        """Initialize script executor - supports both context preparation and direct execution modes"""
        # For context preparation mode (test scripts)
        self.script_name = script_name or "unknown-script"
        self.description = description
        
        # For direct execution mode (API routes)
        self.host_name = host_name or "unknown-host"
        self.device_id = device_id or "unknown-device"
        self.device_model = device_model or "unknown-model"
        self.current_team_id = None
        
        print(f"[@script_executor] Initialized: {self.script_name} for device: {self.device_id}, model: {self.device_model}")
    
    def set_team_id(self, team_id: str):
        """Set team_id for script execution"""
        self.current_team_id = team_id
    
    def execute_script(self, script_name: str, parameters: str = "") -> Dict[str, Any]:
        """Execute a script with parameters and real-time output streaming"""
        start_time = time.time()
        
        # Check if this is an AI test case - redirect to ai_testcase_executor.py
        # IMPORTANT: Exclude the executor script itself to prevent infinite recursion
        if script_name.startswith("ai_testcase_") and script_name != "ai_testcase_executor":
            print(f"[@script_executor] AI test case detected: {script_name}")
            
            # Execute via ai_testcase_executor.py with SAME parameters as normal scripts
            actual_script = "ai_testcase_executor"
            
            print(f"[@script_executor] Redirecting to: {actual_script} with params: {parameters}")
            
            # Pass the original AI script name via environment so executor can find the test case
            original_env = os.environ.copy()
            os.environ['AI_SCRIPT_NAME'] = script_name
            
            # Set team_id if available in parameters (passed from route)
            if hasattr(self, 'current_team_id') and self.current_team_id:
                os.environ['TEAM_ID'] = self.current_team_id
            
            try:
                # DIRECT EXECUTION: Execute the actual script directly without recursive call
                actual_script_path = self._get_script_path(actual_script)
                
                # Execute directly using the same subprocess logic as normal scripts
                result = self._execute_script_subprocess(actual_script_path, parameters, script_name, start_time)
                
                return result
                
            finally:
                # Restore original environment
                os.environ.clear()
                os.environ.update(original_env)
        
        try:
            script_path = self._get_script_path(script_name)
            
            # Execute normal script
            result = self._execute_script_subprocess(script_path, parameters, script_name, start_time)
            
            return result
            
        except Exception as e:
            total_execution_time = int((time.time() - start_time) * 1000)
            print(f"[@script_executor] ERROR: {str(e)}")
            
            return {
                'success': False,
                'stdout': '',
                'stderr': str(e),
                'exit_code': 1,
                'script_name': script_name,
                'device_id': self.device_id,
                'parameters': parameters,
                'execution_time_ms': total_execution_time,
                'report_url': ""
            }
    
    def get_device_info_for_report(self) -> Dict[str, Any]:
        """Get device information for report generation"""
        return {
            'device_name': self.device_id,  # Use device_id as name if no device object
            'device_model': self.device_model,
            'device_id': self.device_id
        }
    
    def get_host_info_for_report(self) -> Dict[str, Any]:
        """Get host information for report generation"""
        return {
            'host_name': self.host_name
        }
    
    # Private methods
    
    def _get_script_path(self, script_name: str) -> str:
        """Get full path to a script file"""
        scripts_dir = self._get_scripts_directory()
        
        # Handle script names that already have .py extension
        if script_name.endswith('.py'):
            script_path = os.path.join(scripts_dir, script_name)
        else:
            script_path = os.path.join(scripts_dir, f'{script_name}.py')
        
        if not os.path.exists(script_path):
            raise ValueError(f'Script not found: {script_path}')
        
        return script_path
    
    def _get_scripts_directory(self) -> str:
        """Get the scripts directory path - single source of truth"""
        current_dir = os.path.dirname(os.path.abspath(__file__))  # /shared/src/lib/executors
        lib_dir = os.path.dirname(current_dir)                    # /shared/src/lib
        src_dir = os.path.dirname(lib_dir)                        # /shared/src
        shared_dir = os.path.dirname(src_dir)                     # /shared
        project_root = os.path.dirname(shared_dir)                # /virtualpytest
        
        # Use test_scripts folder as the primary scripts location
        return os.path.join(project_root, 'test_scripts')
    
    def _execute_script_subprocess(self, script_path: str, parameters: str, script_name: str, start_time: float) -> Dict[str, Any]:
        """Execute script using subprocess with real-time output streaming"""
        # Use PROJECT_ROOT environment variable or detect from current script location
        project_root = os.getenv('PROJECT_ROOT')
        if not project_root:
            # Auto-detect project root
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.abspath(os.path.join(current_dir, '..', '..', '..', '..'))
        
        venv_activate = os.path.join(project_root, 'venv', 'bin', 'activate')
        
        # Build command with parameters
        base_command = f"bash -c 'source {venv_activate} && python {script_path}"
        
        if parameters and parameters.strip():
            command = f"{base_command} {parameters.strip()}'"
        else:
            command = f"{base_command}'"
        
        print(f"[@script_executor] Executing: {command}")
        print(f"[@script_executor] === SCRIPT OUTPUT START ===")
        
        # Use streaming subprocess execution
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Merge stderr into stdout for unified streaming
            text=True,
            bufsize=1,  # Line buffered
            universal_newlines=True
        )
        
        # Stream output in real-time with timeout
        stdout_lines = []
        report_url = ""
        logs_url = ""
        timeout_seconds = 3600  # 1 hour timeout
        start_time_for_timeout = time.time()
        
        while True:
            # Use select to wait for output with timeout
            ready = select.select([process.stdout], [], [], 1.0)[0]  # 1 second timeout
            
            poll_result = process.poll()
            
            if ready:
                output = process.stdout.readline()
                if output:
                    line = output.rstrip()
                    
                    # Extract report URL from cloudflare upload logs  
                    if '[@cloudflare_utils:upload_script_report] INFO: Uploaded script report:' in line:
                        try:
                            report_path = line.split('Uploaded script report: ')[1]
                            base_url = os.environ.get('CLOUDFLARE_R2_PUBLIC_URL', 'https://pub-604f1a4ce32747778c6d5ac5e3100217.r2.dev')
                            report_url = f"{base_url.rstrip('/')}/{report_path}"
                            print(f"📊 [Script] Report URL captured: {report_url}")
                        except Exception as e:
                            print(f"⚠️ [Script] Failed to extract report URL: {e}")
                    
                    # Extract logs URL from upload logs
                    if '[@utils:report_utils:generate_and_upload_script_report] Logs uploaded:' in line:
                        try:
                            logs_url = line.split('Logs uploaded: ')[1].strip()
                            print(f"📝 [Script] Logs URL captured: {logs_url}")
                        except Exception as e:
                            print(f"⚠️ [Script] Failed to extract logs URL: {e}")
                    
                    # Stream all output with prefix
                    print(f"[{script_name}] {line}")
                    
                    stdout_lines.append(output)
                elif poll_result is not None:
                    print(f"[@script_executor] LOOP EXIT: Empty output and process ended (exit code: {poll_result})")
                    break
            elif poll_result is not None:
                print(f"[@script_executor] LOOP EXIT: No output ready and process ended (exit code: {poll_result})")
                break
            
            # Check for timeout
            current_time = time.time()
            elapsed_time = current_time - start_time_for_timeout
            if elapsed_time > timeout_seconds:
                print(f"❌ [Script] Script execution timed out after {timeout_seconds} seconds (elapsed: {elapsed_time:.1f}s)")
                if poll_result is None:
                    print(f"❌ [Script] Process still running, force killing...")
                    process.kill()
                    process.wait()
                else:
                    print(f"❌ [Script] Process already ended but loop didn't exit properly")
                stdout_lines.append(f"\n[TIMEOUT] Script execution timed out after {timeout_seconds} seconds\n")
                break
            
            # Log progress every 30 seconds to track long-running scripts
            if int(elapsed_time) % 30 == 0 and int(elapsed_time) > 0:
                poll_status = poll_result
                if poll_status is None:
                    print(f"[@script_executor] PROGRESS: Script running for {elapsed_time:.0f}s, process still active")
                else:
                    print(f"[@script_executor] PROGRESS: Script at {elapsed_time:.0f}s, process ended with code {poll_status} but loop still running")
        
        # Wait for process completion
        exit_code = process.wait()
        stdout = ''.join(stdout_lines)
        
        print(f"[@script_executor] === SCRIPT OUTPUT END ===")
        print(f"[@script_executor] Process completed with exit code: {exit_code}")
        print(f"[@script_executor] DEBUG: Total stdout lines captured: {len(stdout_lines)}")
        print(f"[@script_executor] DEBUG: Final stdout length: {len(stdout)}")
        
        total_execution_time = int((time.time() - start_time) * 1000)
        
        print(f"[@script_executor] PREPARE RETURN: Creating return dictionary...")
        print(f"[@script_executor] EXIT_CODE: {exit_code}, EXECUTION_TIME: {total_execution_time}ms")
        print(f"[@script_executor] REPORT_URL: {report_url}")
        
        # Extract SCRIPT_SUCCESS marker from stdout (critical for frontend result accuracy)
        script_success = None
        print(f"[@script_executor] DEBUG: Checking for SCRIPT_SUCCESS marker in stdout...")
        print(f"[@script_executor] DEBUG: stdout length: {len(stdout) if stdout else 0}")
        print(f"[@script_executor] DEBUG: stdout contains 'SCRIPT_SUCCESS:': {'SCRIPT_SUCCESS:' in stdout if stdout else False}")
        
        if stdout and 'SCRIPT_SUCCESS:' in stdout:
            import re
            success_match = re.search(r'SCRIPT_SUCCESS:(true|false)', stdout)
            if success_match:
                script_success = success_match.group(1) == 'true'
                print(f"[@script_executor] SCRIPT_SUCCESS extracted: {script_success}")
            else:
                print(f"[@script_executor] DEBUG: SCRIPT_SUCCESS found but regex didn't match")
        else:
            print(f"[@script_executor] DEBUG: No SCRIPT_SUCCESS marker found in stdout")
            # Print last 500 chars of stdout to see what's there
            if stdout:
                stdout_tail = stdout[-500:] if len(stdout) > 500 else stdout
                print(f"[@script_executor] DEBUG: Last 500 chars of stdout: {repr(stdout_tail)}")
            else:
                print(f"[@script_executor] DEBUG: stdout is empty or None")
        
        result = {
            'stdout': stdout,
            'stderr': '',  # We merged stderr into stdout
            'exit_code': exit_code,  # Raw exit code (0 = process success)
            'script_name': script_name,
            'device_id': self.device_id,
            'script_path': script_path,
            'parameters': parameters,
            'execution_time_ms': total_execution_time,
            'report_url': report_url,
            'logs_url': logs_url,
            'script_success': script_success  # Extracted from SCRIPT_SUCCESS marker
        }
        
        print(f"[@script_executor] RETURNING: About to return result dictionary")
        return result
    
    # =====================================================
    # CONTEXT PREPARATION METHODS (from script_utils.py)
    # =====================================================
    
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
            # 1. Load environment variables first
            current_dir = os.path.dirname(os.path.abspath(__file__))  # /shared/src/lib/executors
            lib_dir = os.path.dirname(current_dir)                    # /shared/src/lib
            src_dir = os.path.dirname(lib_dir)                        # /shared/src
            shared_dir = os.path.dirname(src_dir)                     # /shared
            project_root = os.path.dirname(shared_dir)                # /virtualpytest
            backend_host_src = os.path.join(project_root, 'backend_host', 'src')
            
            print(f"🔧 [{self.script_name}] Loading environment variables...")
            load_environment_variables(calling_script_dir=backend_host_src)
            
            # 2. Create host instance with specific device
            device_id_to_use = args.device or "device1"
            print(f"🏗️ [{self.script_name}] Creating host instance with device: {device_id_to_use}...")
            try:
                # Import controller manager directly (paths set up by script)
                from backend_host.src.controllers.controller_manager import get_host
                context.host = get_host(device_ids=[device_id_to_use])
                device_count = context.host.get_device_count()
                print(f"✅ [{self.script_name}] Host created with {device_count} devices")
                
                if device_count == 0:
                    context.error_message = "No devices configured"
                    print(f"❌ [{self.script_name}] {context.error_message}")
                    return context
                
                # Get team_id from environment (should be loaded by now)
                context.team_id = os.getenv('TEAM_ID', DEFAULT_TEAM_ID)
                
            except Exception as e:
                context.error_message = f"Failed to create host: {str(e)}"
                print(f"❌ [{self.script_name}] {context.error_message}")
                return context
            
            # 3. Select device from host instance
            device_id_to_use = args.device or "device1"
            print(f"🔍 [{self.script_name}] Selecting device: {device_id_to_use}")
            
            available_devices = [d.device_id for d in context.host.get_devices()]
            print(f"📱 [{self.script_name}] Available devices: {available_devices}")
            
            # Try to find the specific device by ID
            context.selected_device = next((d for d in context.host.get_devices() if d.device_id == device_id_to_use), None)
            
            if not context.selected_device:
                # If specific device not found, try to find first non-host device
                devices = [d for d in context.host.get_devices() if d.device_id != 'host']
                if devices:
                    context.selected_device = devices[0]
                    print(f"⚠️ [{self.script_name}] Device {device_id_to_use} not found, using first non-host device: {context.selected_device.device_id}")
                else:
                    # Fall back to any device if no non-host devices available
                    all_devices = context.host.get_devices()
                    if all_devices:
                        context.selected_device = all_devices[0]
                        print(f"⚠️ [{self.script_name}] No non-host devices found, using: {context.selected_device.device_id}")
                    else:
                        context.error_message = "No devices available"
                        print(f"❌ [{self.script_name}] {context.error_message}")
                        return context
            
            print(f"✅ [{self.script_name}] Selected device: {context.selected_device.device_name} ({context.selected_device.device_model})")
            
            # 4. Record script execution start in database (if enabled)
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
                    
                    # CRITICAL: Populate device navigation_context with script tracking info
                    # This enables all executors to record with script dependency
                    nav_context = context.selected_device.navigation_context
                    nav_context['script_id'] = context.script_result_id
                    nav_context['script_name'] = self.script_name
                    nav_context['script_context'] = 'script'
                    print(f"📝 [{self.script_name}] Script context populated in device navigation_context")
            
            # 5. Capture initial screenshot using device AV controller
            print(f"📸 [{self.script_name}] Capturing initial state screenshot...")
            try:
                av_controller = context.selected_device._get_controller('av')
                initial_screenshot = av_controller.take_screenshot()
                context.add_screenshot(initial_screenshot)
                print(f"✅ [{self.script_name}] Initial screenshot captured")
            except Exception as e:
                print(f"⚠️ [{self.script_name}] Screenshot failed: {e}, continuing...")
            
            print(f"✅ [{self.script_name}] Execution context setup completed")
            
        except Exception as e:
            context.error_message = f"Setup error: {str(e)}"
            print(f"❌ [{self.script_name}] {context.error_message}")
        
        return context
    
    def cleanup_and_exit(self, context: ScriptExecutionContext, userinterface_name: str):
        """Cleanup resources and exit with appropriate code - NO DEVICE UNLOCKING"""
        try:
            # Output results for execution system FIRST
            success_str = str(context.overall_success).lower()
            print(f"SCRIPT_SUCCESS:{success_str}")
            import sys
            sys.stdout.flush()  # Force immediate output so it gets captured even if process crashes
            
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
                    execution_time_for_db = getattr(context, 'baseline_execution_time_ms', context.get_execution_time_ms())
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
        
        # Clean up script context from device navigation_context
        if context.selected_device and hasattr(context.selected_device, 'navigation_context'):
            nav_context = context.selected_device.navigation_context
            if nav_context.get('script_id'):
                nav_context.pop('script_id', None)
                nav_context.pop('script_name', None)
                nav_context.pop('script_context', None)
                print(f"📝 [{self.script_name}] Script context cleaned from device navigation_context")
        
        # Print summary (use baseline time if available)
        baseline_time = getattr(context, 'baseline_execution_time_ms', None)
        self.print_execution_summary(context, userinterface_name, baseline_time)
        
        # Exit with proper code
        print(f"✅ [{self.script_name}] Script execution completed (test result: {'PASS' if context.overall_success else 'FAIL'})")
        sys.exit(0)
    
    def generate_final_report(self, context: ScriptExecutionContext, userinterface_name: str) -> Dict[str, str]:
        """Generate and upload final execution report using device info"""
        try:
            # Capture execution time BEFORE any additional processing
            actual_execution_time_ms = context.get_execution_time_ms()
            actual_test_duration_seconds = actual_execution_time_ms / 1000.0
            # Store in context for use in cleanup_and_exit
            context.baseline_execution_time_ms = actual_execution_time_ms
            
            # Capture final screenshot using device AV controller
            print(f"📸 [{self.script_name}] Capturing final state screenshot...")
            try:
                av_controller = context.selected_device._get_controller('av')
                final_screenshot = av_controller.take_screenshot()
                context.add_screenshot(final_screenshot)
                print(f"✅ [{self.script_name}] Final screenshot captured")
            except Exception as e:
                print(f"⚠️ [{self.script_name}] Screenshot failed: {e}")
            
            # Capture test execution video using device AV controller
            print(f"🎥 [{self.script_name}] Capturing test execution video...")
            try:
                av_controller = context.selected_device._get_controller('av')
                
                # Use the captured baseline execution time
                video_duration = max(10.0, actual_test_duration_seconds)
                test_video_url = av_controller.take_video(video_duration, context.start_time)
                context.test_video_url = test_video_url
                print(f"✅ [{self.script_name}] Test execution video captured: {test_video_url}")
            except Exception as e:
                print(f"⚠️ [{self.script_name}] Video capture failed: {e}")
                context.test_video_url = ""
            
            # Generate and upload report using device info
            device_info = self.get_device_info_for_report_context(context)
            host_info = self.get_host_info_for_report_context(context)
            
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
                        print(f"[@script_executor] Extracted logs URL: {logs_url}")
                except Exception as e:
                    print(f"[@script_executor] Failed to extract logs URL: {e}")
            
            if report_result.get('success') and report_result.get('report_url'):
                print(f"📊 [{self.script_name}] Report generated: {report_result['report_url']}")
                if report_result.get('logs_url'):
                    print(f"📝 [{self.script_name}] Logs uploaded: {report_result['logs_url']}")
            
            return report_result
            
        except Exception as e:
            print(f"⚠️ [{self.script_name}] Error in report generation: {e}")
            return {
                'success': False,
                'report_url': '',
                'report_path': ''
            }
    
    def get_device_info_for_report_context(self, context: ScriptExecutionContext) -> Dict[str, Any]:
        """Get device information for report generation from context"""
        if context.selected_device:
            return {
                'device_name': context.selected_device.device_name,
                'device_model': context.selected_device.device_model,
                'device_id': context.selected_device.device_id
            }
        else:
            return {
                'device_name': self.device_id,
                'device_model': self.device_model,
                'device_id': self.device_id
            }
    
    def get_host_info_for_report_context(self, context: ScriptExecutionContext) -> Dict[str, Any]:
        """Get host information for report generation from context"""
        if context.host:
            return {
                'host_name': context.host.host_name
            }
        else:
            return {
                'host_name': self.host_name
            }
    
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
    # HIGH-LEVEL NAVIGATION METHODS (Auto-record steps)
    # =====================================================
    
    def navigate_to(self, context: ScriptExecutionContext, target_node: str, userinterface_name: str) -> bool:
        """
        High-level navigation that handles everything automatically:
        - Loads navigation tree if needed
        - Executes navigation
        - Creates and records step automatically
        - Returns success/failure
        """
        try:
            # Load navigation tree if not already loaded
            nav_result = context.selected_device.navigation_executor.load_navigation_tree(
                userinterface_name, 
                context.team_id
            )
            if not nav_result['success']:
                context.error_message = f"Navigation tree loading failed: {nav_result.get('error', 'Unknown error')}"
                return False
            
            # Update context with loaded tree information
            context.tree_id = nav_result['tree_id']
            context.tree_data = nav_result
            context.nodes = nav_result.get('nodes', [])
            context.edges = nav_result.get('edges', [])
            
            # Execute navigation
            navigation_result = context.selected_device.navigation_executor.execute_navigation(
                tree_id=context.tree_id,
                target_node_label=target_node,
                team_id=context.team_id,
                context=context
            )
            
            # Navigation steps are already recorded by NavigationExecutor.execute_navigation()
            # No need to record duplicate step here
            
            success = navigation_result['success']
            if not success:
                context.error_message = navigation_result.get('error', 'Navigation failed')
            
            return success
            
        except Exception as e:
            context.error_message = f"Navigation error: {str(e)}"
            return False
    
    def test_success(self, context: ScriptExecutionContext):
        """Mark test as successful"""
        context.overall_success = True
        print(f"🎉 [{self.script_name}] Test completed successfully!")
    
    def test_fail(self, context: ScriptExecutionContext, error_message: str = None):
        """Mark test as failed with optional error message"""
        context.overall_success = False
        if error_message:
            context.error_message = error_message
        print(f"❌ [{self.script_name}] Test failed: {context.error_message}")


# =====================================================
# UTILITY FUNCTIONS (from script_utils.py)
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
