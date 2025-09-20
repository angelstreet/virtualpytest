"""
Script Executor Per Device

Unified script executor that integrates AI executor, action executor, and verification executor
for complete script execution capabilities per device.
"""

import time
import uuid
import subprocess
import os
import select
import threading
from typing import Dict, List, Optional, Any, Tuple

from src.services.ai.ai_executor import AIExecutor
from src.services.actions.action_executor import ActionExecutor
from src.services.verifications.verification_executor import VerificationExecutor
from src.services.navigation.navigation_executor import NavigationExecutor


class ScriptExecutor:
    """
    Unified script executor per device that orchestrates all execution capabilities:
    - Script execution with real-time output streaming
    - AI plan generation and execution via AIExecutor
    - Action execution via ActionExecutor
    - Verification execution via VerificationExecutor
    - Navigation execution via NavigationExecutor
    """
    
    def __init__(self, device):
        """Initialize script executor for a specific device"""
        # Validate required parameters - fail fast if missing
        if not device:
            raise ValueError("Device instance is required")
        if not device.host_name:
            raise ValueError("Device must have host_name")
        if not device.device_id:
            raise ValueError("Device must have device_id")
        
        # Store device instance
        self.device = device
        self.host_name = device.host_name
        self.device_id = device.device_id
        self.device_model = device.device_model
        
        # Initialize integrated executors
        self.ai_executor = AIExecutor(device)
        self.action_executor = ActionExecutor(device)
        self.verification_executor = VerificationExecutor(device)
        self.navigation_executor = NavigationExecutor(device)
        
        print(f"[@script_executor] Initialized for device: {self.device_id}, model: {self.device_model}")
    
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
    
    def execute_ai_prompt(self, 
                         prompt: str, 
                         userinterface_name: str,
                         current_node_id: Optional[str] = None,
                         async_execution: bool = True,
                         team_id: Optional[str] = None) -> Dict[str, Any]:
        """Execute AI prompt via integrated AI executor"""
        return self.ai_executor.execute_prompt(
            prompt=prompt,
            userinterface_name=userinterface_name,
            current_node_id=current_node_id,
            async_execution=async_execution,
            team_id=team_id
        )
    
    def execute_actions(self, 
                       actions: List[Dict[str, Any]], 
                       retry_actions: Optional[List[Dict[str, Any]]] = None,
                       failure_actions: Optional[List[Dict[str, Any]]] = None,
                       team_id: Optional[str] = None) -> Dict[str, Any]:
        """Execute batch of actions via integrated action executor"""
        return self.action_executor.execute_actions(
            actions=actions,
            retry_actions=retry_actions,
            failure_actions=failure_actions,
            team_id=team_id
        )
    
    def execute_verifications(self, 
                             verifications: List[Dict[str, Any]], 
                             team_id: Optional[str] = None) -> Dict[str, Any]:
        """Execute batch of verifications via integrated verification executor"""
        return self.verification_executor.execute_verifications(
            verifications=verifications,
            team_id=team_id
        )
    
    def execute_navigation(self, 
                          tree_id: str,
                          target_node_id: str,
                          current_node_id: Optional[str] = None,
                          team_id: Optional[str] = None) -> Dict[str, Any]:
        """Execute navigation via integrated navigation executor"""
        return self.navigation_executor.execute_navigation(
            tree_id=tree_id,
            target_node_id=target_node_id,
            current_node_id=current_node_id
        )
    
    def get_device_position(self) -> Dict[str, Any]:
        """Get current device position from navigation executor"""
        return self.navigation_executor.get_current_position()
    
    def update_device_position(self, node_id: str, tree_id: str = None, node_label: str = None) -> Dict[str, Any]:
        """Update device position via navigation executor"""
        return self.navigation_executor.update_current_position(node_id, tree_id, node_label)
    
    def get_execution_status(self, execution_id: str) -> Dict[str, Any]:
        """Get AI execution status via AI executor"""
        return self.ai_executor.get_execution_status(execution_id)
    
    def get_device_info_for_report(self) -> Dict[str, Any]:
        """Get device information for report generation"""
        return {
            'device_name': self.device.device_name,
            'device_model': self.device.device_model,
            'device_id': self.device.device_id
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
        current_dir = os.path.dirname(os.path.abspath(__file__))  # /backend_host/src/services/scripts
        src_dir = os.path.dirname(current_dir)  # /backend_host/src
        backend_host_dir = os.path.dirname(src_dir)  # /backend_host
        project_root = os.path.dirname(backend_host_dir)  # /virtualpytest
        
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
