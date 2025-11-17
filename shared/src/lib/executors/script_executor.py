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
import shlex
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

# Import required modules for context preparation
from shared.src.lib.utils.app_utils import load_environment_variables
from shared.src.lib.utils.report_generation_utils import generate_and_upload_script_report
from shared.src.lib.database.script_results_db import record_script_execution_start, update_script_execution_result

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
        self.userinterface_name = None  # Legacy name (backward compatibility)
        self.userinterface = None        # NEW: Canonical access (framework parameter)
        
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
        
        # Builder-specific: Runtime variables (cleared after execution)
        self.variables = {}
        
        # Builder-specific: Metadata for DB storage (persisted to script_results.metadata)
        self.metadata = {}
        
        # Stdout capture for log upload
        self.stdout_buffer = []
        
        # Simple sequential step counter
        self.step_counter = 0
        
        # Running log tracking (for frontend overlay)
        self.running_log_path = None
        self.total_steps = 0
        self.planned_steps: List[Dict[str, Any]] = []
        self.estimated_duration_seconds = None
    
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
        """Store screenshot path - auto-copy to cold if in hot storage"""
        if screenshot_path:
            # Auto-copy from hot to cold if needed (makes images survive 1 hour)
            if '/hot/' in screenshot_path and not screenshot_path.startswith('https://'):
                import shutil
                cold_path = screenshot_path.replace('/hot/', '/')
                if not os.path.exists(cold_path):
                    os.makedirs(os.path.dirname(cold_path), mode=0o777, exist_ok=True)
                    shutil.copy2(screenshot_path, cold_path)
                screenshot_path = cold_path
            
            # DEBUG: Log who's adding screenshots to context
            import traceback
            caller_stack = traceback.extract_stack()
            # Get the last 3 stack frames (excluding this function)
            caller_info = []
            for frame in caller_stack[-4:-1]:  # -4 to -1 excludes this function
                caller_info.append(f"{frame.filename.split('/')[-1]}:{frame.lineno} in {frame.name}")
            
            screenshot_name = os.path.basename(screenshot_path)
            print(f"📸 [Context] add_screenshot called: {screenshot_name} (total: {len(self.screenshot_paths)+1})")
            print(f"   └─ Call stack: {' ← '.join(reversed(caller_info))}")
            
            self.screenshot_paths.append(screenshot_path)
    
    def upload_screenshots_to_r2(self) -> Dict[str, str]:
        """
        Batch upload all local screenshots to R2 at script end.
        
        Returns:
            Dict mapping local paths to R2 URLs for report generation
        """
        url_mapping = {}  # Map local_path -> r2_url
        
        if not self.screenshot_paths:
            return url_mapping
        
        print(f"📤 [Context] Batch uploading {len(self.screenshot_paths)} screenshots to R2...")
        
        try:
            from shared.src.lib.utils.cloudflare_utils import get_cloudflare_utils
            uploader = get_cloudflare_utils()
            device_id = self.selected_device.device_id if hasattr(self, 'selected_device') else 'unknown'
            
            # Store original paths for mapping
            original_paths = self.screenshot_paths.copy()
            
            # Separate already-uploaded URLs and local files
            already_uploaded = []
            file_mappings = []
            path_to_index = {}  # Track original index for each file
            
            for idx, path in enumerate(self.screenshot_paths):
                # Skip None paths - keep as None in final result
                if not path:
                    print(f"⚠️ [Context] Skipping None screenshot at index {idx}")
                    already_uploaded.append((idx, None))  # Track the None
                    continue
                
                # Already R2 URL - keep as-is
                if path.startswith('https://'):
                    already_uploaded.append((idx, path))
                    continue
                
                # Local path - check if exists
                if not os.path.exists(path):
                    print(f"⚠️ [Context] Screenshot not found: {path}")
                    already_uploaded.append((idx, path))  # Keep original path (even if missing)
                    continue
                
                # Add to batch upload
                filename = os.path.basename(path)
                remote_path = f"script-screenshots/{device_id}/{filename}"
                file_mappings.append({
                    'local_path': path,
                    'remote_path': remote_path
                })
                path_to_index[path] = idx
            
            # Upload all files at once
            if file_mappings:
                upload_result = uploader.upload_files(file_mappings)
                
                # Build updated paths list maintaining original order
                updated_paths = [None] * len(self.screenshot_paths)
                
                # Place already uploaded URLs back
                for idx, url in already_uploaded:
                    updated_paths[idx] = url
                
                # Place successfully uploaded files and delete local copies
                for uploaded_file in upload_result['uploaded_files']:
                    original_idx = path_to_index[uploaded_file['local_path']]
                    updated_paths[original_idx] = uploaded_file['url']
                    # Build mapping: local -> R2 URL
                    url_mapping[uploaded_file['local_path']] = uploaded_file['url']
                    
                    # Delete local file from cold storage after successful upload
                    local_path = uploaded_file['local_path']
                    try:
                        if os.path.exists(local_path):
                            os.remove(local_path)
                            print(f"🗑️  [Context] Deleted local file after upload: {os.path.basename(local_path)}")
                    except Exception as e:
                        print(f"⚠️ [Context] Failed to delete local file {os.path.basename(local_path)}: {e}")
                
                # Place failed uploads (keep original path)
                for failed_file in upload_result['failed_uploads']:
                    original_idx = path_to_index[failed_file['local_path']]
                    filename = os.path.basename(failed_file['local_path'])
                    print(f"⚠️ [Context] Upload failed for {filename}: {failed_file['error']}")
                    updated_paths[original_idx] = failed_file['local_path']
                
                self.screenshot_paths = updated_paths
                print(f"✅ [Context] Uploaded {upload_result['uploaded_count']}/{len(file_mappings)} screenshots to R2")
                print(f"📋 [Context] Built mapping with {len(url_mapping)} local->R2 URL pairs")
            else:
                print(f"✅ [Context] All {len(already_uploaded)} screenshots already uploaded")
            
            return url_mapping
            
        except Exception as e:
            print(f"❌ [Context] Batch upload error: {e}")
            import traceback
            traceback.print_exc()
            return url_mapping  # Return empty mapping on error
    
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
    
    def set_running_log_path(self, capture_folder: str):
        """Set the running log path for this execution"""
        from shared.src.lib.utils.storage_path_utils import get_running_log_path
        self.running_log_path = get_running_log_path(capture_folder)
    
    def set_planned_steps(self, steps: List[Dict[str, Any]]):
        """Store planned steps for display (call at script start)"""
        self.planned_steps = steps
        self.total_steps = len(steps)
    
    def write_running_log(self):
        """Write current execution state to running.log for frontend overlay - uses existing step_results"""
        if not self.running_log_path:
            return
        
        try:
            import json
            from datetime import datetime, timezone
            
            # Get current step number
            current_step_number = self.step_counter
            total_steps = self.total_steps if self.total_steps > 0 else len(self.step_results)
            
            # Build log data
            log_data = {
                "script_name": self.script_name,
                "total_steps": total_steps,
                "current_step_number": current_step_number,
                "start_time": datetime.fromtimestamp(self.start_time, tz=timezone.utc).isoformat(),
            }
            
            # Helper to extract step description from step_result
            def get_step_description(step):
                """Extract human-readable description from step_result"""
                # Try message first (navigation steps have this)
                if step.get('message'):
                    return step['message']
                # Try from_node -> to_node for navigation
                if step.get('from_node') and step.get('to_node'):
                    return f"{step['from_node']} → {step['to_node']}"
                # Try action_name
                if step.get('action_name'):
                    return step['action_name']
                # Fallback
                return step.get('step_category', 'Unknown step')
            
            def get_step_command(step):
                """Extract command/type from step_result"""
                # Try action_name first
                if step.get('action_name'):
                    return step['action_name']
                # Try step_category
                if step.get('step_category'):
                    return step['step_category']
                # Fallback
                return 'unknown'
            
            # Add all completed steps (for scrollable timeline) - user can scroll through all
            all_completed_steps = []
            if len(self.step_results) >= 2:
                # Get ALL completed steps (excluding current step which is the last one)
                for step in self.step_results[:-1]:  # All except the last (current) step
                    all_completed_steps.append({
                        "step_number": step.get('step_number'),
                        "description": get_step_description(step),
                        "command": get_step_command(step),
                        "status": "completed",
                        "actions": step.get('actions', []),
                        "verifications": step.get('verifications', []),
                    })
                log_data["completed_steps"] = all_completed_steps
            
            # LEGACY: Keep previous_step for backward compatibility
            if len(self.step_results) >= 2:
                prev_step = self.step_results[-2]
                log_data["previous_step"] = {
                    "step_number": prev_step.get('step_number'),
                    "description": get_step_description(prev_step),
                    "command": get_step_command(prev_step),
                    "status": "completed",
                    "actions": prev_step.get('actions', []),
                    "verifications": prev_step.get('verifications', []),
                }
            
            # Add current step (from step_results - last recorded step)
            if len(self.step_results) >= 1:
                current_step = self.step_results[-1]
                
                # Extract actions and verifications directly from step_result
                # Note: step_results store 'actions' and 'verifications' at the top level
                actions = current_step.get('actions', [])
                verifications = current_step.get('verifications', [])
                
                # Also check if there are retry_actions or failure_actions
                retry_actions = current_step.get('retry_actions', [])
                failure_actions = current_step.get('failure_actions', [])
                
                log_data["current_step"] = {
                    "step_number": current_step.get('step_number'),
                    "description": get_step_description(current_step),
                    "command": get_step_command(current_step),
                    "status": "current",
                    "actions": actions,
                    "verifications": verifications,
                    "retry_actions": retry_actions if retry_actions else None,
                    "failure_actions": failure_actions if failure_actions else None,
                    # Set progress to show completed count (e.g., "3/3" for all done)
                    "current_action_index": len(actions),  # All actions completed
                    "current_verification_index": len(verifications),  # All verifications completed
                }
            
            # Calculate estimated end time based on average step duration
            if len(self.step_results) >= 2:
                # Calculate average duration per step (execution_time_ms converted to seconds)
                total_duration = 0
                step_count = 0
                for step in self.step_results:
                    # Check both 'execution_time_ms' and 'duration' for compatibility
                    if step.get('execution_time_ms') is not None:
                        total_duration += step['execution_time_ms'] / 1000.0  # Convert ms to seconds
                        step_count += 1
                    elif step.get('duration') is not None:
                        total_duration += step['duration']
                        step_count += 1
                
                if step_count > 0 and total_steps > 0:
                    avg_duration = total_duration / step_count
                    remaining_steps = max(0, total_steps - current_step_number)
                    estimated_remaining = remaining_steps * avg_duration
                    estimated_end = datetime.fromtimestamp(time.time() + estimated_remaining, tz=timezone.utc).isoformat()
                    log_data["estimated_end"] = estimated_end
                    print(f"[@script_executor] Estimated end time: avg_duration={avg_duration:.1f}s, remaining_steps={remaining_steps}, estimated_remaining={estimated_remaining:.1f}s")
            
            # Fallback to historical average from deployment_scheduler
            if "estimated_end" not in log_data and self.estimated_duration_seconds:
                elapsed = time.time() - self.start_time
                remaining = max(0, self.estimated_duration_seconds - elapsed)
                estimated_end = datetime.fromtimestamp(time.time() + remaining, tz=timezone.utc).isoformat()
                log_data["estimated_end"] = estimated_end
                print(f"[@script_executor] Using historical average: total={self.estimated_duration_seconds:.1f}s, elapsed={elapsed:.1f}s, remaining={remaining:.1f}s")
            
            # Write atomically (write to temp file, then move)
            temp_path = self.running_log_path + '.tmp'
            with open(temp_path, 'w') as f:
                json.dump(log_data, f, indent=2)
            os.replace(temp_path, self.running_log_path)
            print(f"[@script_executor] Wrote running log: {self.running_log_path} (step {current_step_number}/{total_steps})")
            
        except Exception as e:
            # Log error but don't break script execution
            print(f"[@script_executor] ERROR writing running log to {self.running_log_path}: {e}")
            import traceback
            traceback.print_exc()
    
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
    
    def set_team_id(self, team_id: str):
        """Set team_id for script execution"""
        self.current_team_id = team_id
    
    def execute_script(self, script_name: str, parameters: str = "", estimated_duration_seconds: float = None) -> Dict[str, Any]:
        """Execute a script with parameters and real-time output streaming"""
        start_time = time.time()
        
        # Store estimated duration for use in setup_execution_context
        self.estimated_duration_seconds = estimated_duration_seconds
        
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
        
        # Build command with parameters - PROPER SHELL QUOTING
        # Auto-detect: Use venv if exists (Raspberry Pi), otherwise use system Python (Docker)
        if os.path.exists(venv_activate):
            base_command = f"source {venv_activate} && python {script_path}"
            print(f"[@script_executor] Using venv: {venv_activate}")
        else:
            base_command = f"python {script_path}"
            print(f"[@script_executor] No venv found, using system Python (Docker mode)")
        
        if parameters and parameters.strip():
            # Split parameters and properly quote each one to handle special characters
            param_parts = shlex.split(parameters.strip())
            quoted_params = ' '.join(shlex.quote(part) for part in param_parts)
            full_command = f"{base_command} {quoted_params}"
        else:
            full_command = base_command
        
        # Final bash command
        # SECURITY: Use shell=False and pass as array to prevent shell injection
        command_array = ['bash', '-c', full_command]
        
        print(f"[@script_executor] Executing: {' '.join(command_array)}")
        print(f"[@script_executor] === SCRIPT OUTPUT START ===")
        
        # Use streaming subprocess execution with shell=False for security
        process = subprocess.Popen(
            command_array,
            shell=False,
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
        
        # Standard framework arguments (always available)
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
        
        # Store userinterface if script declares it (framework parameter)
        # Accept both 'userinterface' (new) and 'userinterface_name' (legacy) for compatibility
        userinterface_value = getattr(args, 'userinterface', None) or getattr(args, 'userinterface_name', None)
        context.userinterface_name = userinterface_value  # Keep for backward compatibility
        context.userinterface = userinterface_value        # NEW: Canonical access
        
        # Start capturing stdout for log upload
        context.start_stdout_capture()
        
        if context.userinterface:
            print(f"🎯 [{self.script_name}] Starting execution for: {context.userinterface}")
        else:
            print(f"🎯 [{self.script_name}] Starting execution (no UI required)")
        
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
            
            # Setup running log path for automatic progress tracking (use centralized function)
            from shared.src.lib.utils.storage_path_utils import get_capture_folder_from_device_id
            try:
                capture_folder = get_capture_folder_from_device_id(device_id_to_use)
                context.set_running_log_path(capture_folder)
                print(f"📝 [{self.script_name}] Running log enabled: {context.running_log_path}")
            except ValueError as e:
                print(f"⚠️  [{self.script_name}] Could not set running log: {e}")
                # Continue without running log
            
            # Set estimated duration from historical data (if available)
            if hasattr(self, 'estimated_duration_seconds') and self.estimated_duration_seconds:
                context.estimated_duration_seconds = self.estimated_duration_seconds
                print(f"⏱️  [{self.script_name}] Estimated duration set: {self.estimated_duration_seconds:.1f}s")
            
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
                    userinterface_name=getattr(args, 'userinterface_name', None),
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
            
            # 5. Capture initial screenshot (stored in cold, uploaded at script end)
            from shared.src.lib.utils.device_utils import capture_screenshot
            print(f"📸 [{self.script_name}] Capturing initial state screenshot...")
            capture_screenshot(context.selected_device, context, f"[{self.script_name}]")
            
            print(f"✅ [{self.script_name}] Execution context setup completed")
            
        except Exception as e:
            context.error_message = f"Setup error: {str(e)}"
            print(f"❌ [{self.script_name}] {context.error_message}")
        
        return context
    
    def generate_report_for_context(self, context: ScriptExecutionContext, device_info: Dict[str, Any], host_info: Dict[str, Any], userinterface_name: str = "") -> Dict[str, str]:
        """
        Generate and upload report for a context (reusable by script_executor and testcase_executor).
        
        Args:
            context: Script execution context with step results and screenshots
            device_info: Device information dict
            host_info: Host information dict
            userinterface_name: Optional userinterface name
            
        Returns:
            Dict with 'success', 'report_url', 'logs_url', 'report_path', 'logs_path'
        """
        try:
            # Capture execution time BEFORE any additional processing
            actual_execution_time_ms = context.get_execution_time_ms()
            context.baseline_execution_time_ms = actual_execution_time_ms
            
            # Capture test execution video BEFORE report generation (for both scripts and test cases)
            print(f"🎥 [{self.script_name}] Capturing test execution video...")
            try:
                actual_test_duration_seconds = actual_execution_time_ms / 1000.0
                av_controller = context.selected_device._get_controller('av')
                video_duration = max(10.0, actual_test_duration_seconds)
                test_video_url = av_controller.take_video_for_report(video_duration, context.start_time)
                context.test_video_url = test_video_url
                print(f"✅ [{self.script_name}] Test execution video captured: {test_video_url}")
            except Exception as e:
                print(f"⚠️ [{self.script_name}] Video capture failed: {e}")
                context.test_video_url = ""
            
            # Batch upload all screenshots to R2 BEFORE report generation
            url_mapping = context.upload_screenshots_to_r2()
            context.screenshot_url_mapping = url_mapping
            
            # Stop stdout capture and get logs
            context.stop_stdout_capture()
            captured_stdout = context.get_captured_stdout()
            
            # Generate and upload report using device info
            report_result = generate_and_upload_script_report(
                script_name=f"{self.script_name}.py",
                device_info=device_info,
                host_info=host_info,
                execution_time=actual_execution_time_ms,
                success=context.overall_success,
                step_results=context.step_results,
                screenshot_paths=context.screenshot_paths,
                screenshot_url_mapping=url_mapping,
                error_message=context.error_message,
                userinterface_name=userinterface_name,
                execution_summary=getattr(context, 'execution_summary', ''),
                test_video_url=getattr(context, 'test_video_url', '') or '',
                stdout=captured_stdout,
                script_result_id=context.script_result_id,
                custom_data=context.custom_data,
                zap_detailed_summary=getattr(context, 'zap_detailed_summary', '')
            )
            
            if report_result.get('success'):
                print(f"📊 [{self.script_name}] Report generated: {report_result.get('report_url')}")
                if report_result.get('logs_url'):
                    print(f"📝 [{self.script_name}] Logs uploaded: {report_result.get('logs_url')}")
            
            return report_result
            
        except Exception as e:
            print(f"⚠️ [{self.script_name}] Error in report generation: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'report_url': '',
                'report_path': '',
                'logs_url': '',
                'logs_path': ''
            }
    
    def cleanup_and_exit(self, context: ScriptExecutionContext, userinterface_name: str):
        """Cleanup resources and exit with appropriate code - NO DEVICE UNLOCKING"""
        try:
            # Output results for execution system FIRST
            success_str = str(context.overall_success).lower()
            print(f"SCRIPT_SUCCESS:{success_str}")
            import sys
            sys.stdout.flush()
            
            # Capture final screenshot BEFORE report generation
            if context.host and context.selected_device:
                print(f"📸 [{self.script_name}] Capturing final state screenshot...")
                from shared.src.lib.utils.device_utils import capture_screenshot_for_script
                screenshot_id = capture_screenshot_for_script(context.selected_device, context, "final_state")
                if screenshot_id:
                    print(f"✅ [{self.script_name}] Final screenshot captured: {screenshot_id}")
            
            # Generate report using reusable method
            device_info = self.get_device_info_for_report_context(context)
            host_info = self.get_host_info_for_report_context(context)
            
            report_result = self.generate_report_for_context(context, device_info, host_info, userinterface_name)
            
            # Store report URLs for final summary
            if report_result and report_result.get('success') and report_result.get('report_url'):
                if not hasattr(context, 'custom_data'):
                    context.custom_data = {}
                context.custom_data['report_url'] = report_result['report_url']
                if report_result.get('logs_url'):
                    context.logs_url = report_result['logs_url']
            
            # Update database if tracking is enabled
            if context.script_result_id:
                if context.overall_success:
                    print(f"📝 [{self.script_name}] Recording success in database...")
                    execution_time_for_db = getattr(context, 'baseline_execution_time_ms', context.get_execution_time_ms())
                    
                    # Extract metadata from context if available
                    metadata_to_save = getattr(context, 'metadata', None)
                    if metadata_to_save:
                        print(f"📦 [{self.script_name}] Including metadata in database update: {list(metadata_to_save.keys())}")
                    
                    update_script_execution_result(
                        script_result_id=context.script_result_id,
                        success=True,
                        execution_time_ms=execution_time_for_db,
                        html_report_r2_path=report_result.get('report_path') if report_result and report_result.get('success') else None,
                        html_report_r2_url=report_result.get('report_url') if report_result and report_result.get('success') else None,
                        logs_r2_path=report_result.get('logs_path') if report_result and report_result.get('success') else None,
                        logs_r2_url=report_result.get('logs_url') if report_result and report_result.get('success') else None,
                        error_msg=None,
                        metadata=metadata_to_save
                    )
                else:
                    print(f"📝 [{self.script_name}] Recording failure in database...")
                    # Use baseline execution time if available, otherwise current time
                    execution_time_for_db = getattr(context, 'baseline_execution_time_ms', context.get_execution_time_ms())
                    
                    # Extract metadata from context if available (even on failure, metadata might be useful)
                    metadata_to_save = getattr(context, 'metadata', None)
                    if metadata_to_save:
                        print(f"📦 [{self.script_name}] Including metadata in database update: {list(metadata_to_save.keys())}")
                    
                    update_script_execution_result(
                        script_result_id=context.script_result_id,
                        success=False,
                        execution_time_ms=execution_time_for_db,
                        html_report_r2_path=report_result.get('report_path') if report_result and report_result.get('success') else None,
                        html_report_r2_url=report_result.get('report_url') if report_result and report_result.get('success') else None,
                        logs_r2_path=report_result.get('logs_path') if report_result and report_result.get('success') else None,
                        logs_r2_url=report_result.get('logs_url') if report_result and report_result.get('success') else None,
                        error_msg=context.error_message or 'Script execution failed',
                        metadata=metadata_to_save
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
        """Generate and upload final execution report using device info (DEPRECATED - use generate_report_for_context)"""
        print(f"[@script_executor] DEPRECATED: generate_final_report() called, use generate_report_for_context() instead")
        
        # Capture test execution video (testcase_executor doesn't need this yet)
        try:
            actual_test_duration_seconds = context.get_execution_time_ms() / 1000.0
            av_controller = context.selected_device._get_controller('av')
            video_duration = max(10.0, actual_test_duration_seconds)
            test_video_url = av_controller.take_video_for_report(video_duration, context.start_time)
            context.test_video_url = test_video_url
            print(f"✅ [{self.script_name}] Test execution video captured: {test_video_url}")
        except Exception as e:
            print(f"⚠️ [{self.script_name}] Video capture failed: {e}")
            context.test_video_url = ""
        
        # Use the new reusable method
        device_info = self.get_device_info_for_report_context(context)
        host_info = self.get_host_info_for_report_context(context)
        return self.generate_report_for_context(context, device_info, host_info, userinterface_name)
    
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
            
            # Execute navigation - convert target_node (label) to node_id
            # For script executor, target_node is typically a label, so we need to convert it
            try:
                target_node_id = context.selected_device.navigation_executor.get_node_id(target_node)
            except ValueError:
                # If conversion fails, assume target_node is already a node_id
                target_node_id = target_node
            
            # ✅ Wrap async call with asyncio.run for script context
            import asyncio
            navigation_result = asyncio.run(context.selected_device.navigation_executor.execute_navigation(
                tree_id=context.tree_id,
                userinterface_name=context.userinterface_name,  # MANDATORY parameter
                target_node_id=target_node_id,
                team_id=context.team_id,
                context=context
            ))
            
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
