#!/usr/bin/env python3
"""
Campaign Execution Framework for VirtualPyTest - Host Level

This module provides functionality to execute test campaigns that consist of
multiple script executions with proper tracking and reporting at the host level.

Usage:
    from  backend_host.src.lib.utils.campaign_executor import CampaignExecutor
    
    executor = CampaignExecutor()
    result = executor.execute_campaign(campaign_config)
"""

import os
import sys
import time
import subprocess
import threading
from datetime import datetime
from typing import Dict, List, Any, Optional
from uuid import uuid4

# Add project root to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))

if project_root not in sys.path:
    sys.path.insert(0, project_root)

from shared.src.lib.database.campaign_executions_db import (
    record_campaign_execution_start,
    update_campaign_execution_result
)
from shared.src.lib.utils.app_utils import load_environment_variables
# REMOVED top-level import: from backend_host.src.lib.utils.host_utils import get_host_instance
# Now lazy-loaded where needed
from .script_executor import DEFAULT_TEAM_ID


class CampaignExecutionContext:
    """Context object that holds campaign execution state"""
    
    def __init__(self, campaign_id: str, campaign_name: str):
        self.campaign_id = campaign_id
        self.campaign_name = campaign_name
        self.campaign_execution_id = f"campaign_exec_{int(time.time())}_{str(uuid4())[:8]}"
        self.start_time = time.time()
        
        # Infrastructure
        self.team_id = None
        self.host = None
        
        # Execution tracking
        self.campaign_result_id = None
        self.script_executions = []
        self.overall_success = False
        self.error_message = ""
        
        # Statistics
        self.total_scripts = 0
        self.completed_scripts = 0
        self.successful_scripts = 0
        self.failed_scripts = 0
    
    def get_execution_time_ms(self) -> int:
        """Get current execution time in milliseconds"""
        return int((time.time() - self.start_time) * 1000)


class CampaignExecutor:
    """Campaign execution orchestrator for host-level execution"""
    
    def __init__(self):
        self.project_root = project_root
    
    def execute_campaign(self, campaign_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a test campaign with multiple scripts at host level.
        
        Args:
            campaign_config: Campaign configuration dictionary
            
        Example campaign_config:
        {
            "campaign_id": "fullzap-double-test",
            "name": "Fullzap Double Execution Test",
            "description": "Execute fullzap.py twice in a row",
            "userinterface_name": "horizon_android_mobile",
            "host": "auto",  # or specific host name
            "device": "auto",  # or specific device name
            "execution_config": {
                "continue_on_failure": True,
                "timeout_minutes": 60,
                "parallel": False
            },
            "script_configurations": [
                {
                    "script_name": "fullzap.py",
                    "script_type": "fullzap",
                    "parameters": {
                        "action": "live_chup",
                        "max_iteration": 5,
                        "goto_live": True
                    }
                },
                {
                    "script_name": "fullzap.py", 
                    "script_type": "fullzap",
                    "parameters": {
                        "action": "live_chdown", 
                        "max_iteration": 3,
                        "goto_live": False
                    }
                }
            ]
        }
        """
        context = CampaignExecutionContext(
            campaign_config["campaign_id"],
            campaign_config["name"]
        )
        
        try:
            print(f"🚀 [Campaign] Starting campaign: {context.campaign_name}")
            print(f"📋 [Campaign] Execution ID: {context.campaign_execution_id}")
            
            # Setup environment at host level
            if not self._setup_campaign_environment(context, campaign_config):
                return self._build_failure_result(context, "Failed to setup campaign environment")
            
            # Record campaign execution start in database (simplified single table)
            context.campaign_result_id = record_campaign_execution_start(
                team_id=context.team_id,
                campaign_name=context.campaign_name,
                campaign_execution_id=context.campaign_execution_id,
                userinterface_name=campaign_config.get("userinterface_name"),
                host_name=context.host.host_name,
                device_name=campaign_config.get("device", "auto"),
                description=campaign_config.get("description", ""),
                script_configurations=campaign_config.get("script_configurations", []),
                execution_config=campaign_config.get("execution_config", {}),
                executed_by=None  # Could be passed from API context
            )
            
            if not context.campaign_result_id:
                return self._build_failure_result(context, "Failed to record campaign start in database")
            
            # Execute scripts
            script_configs = campaign_config.get("script_configurations", [])
            context.total_scripts = len(script_configs)
            
            if context.total_scripts == 0:
                return self._build_failure_result(context, "No scripts configured for execution")
            
            print(f"📊 [Campaign] Executing {context.total_scripts} script configurations")
            
            execution_config = campaign_config.get("execution_config", {})
            continue_on_failure = execution_config.get("continue_on_failure", True)
            
            for i, script_config in enumerate(script_configs, 1):
                print(f"\n{'='*60}")
                print(f"🎯 [Campaign] Executing script {i}/{context.total_scripts}")
                print(f"📜 Script: {script_config.get('script_name')}")
                print(f"🔧 Type: {script_config.get('script_type')}")
                print(f"{'='*60}")
                
                script_result = self._execute_single_script(
                    context, campaign_config, script_config, i
                )
                
                context.script_executions.append(script_result)
                context.completed_scripts += 1
                
                if script_result["success"]:
                    context.successful_scripts += 1
                    print(f"✅ [Campaign] Script {i} completed successfully")
                else:
                    context.failed_scripts += 1
                    print(f"❌ [Campaign] Script {i} failed: {script_result.get('error')}")
                    
                    if not continue_on_failure:
                        context.error_message = f"Campaign stopped after script {i} failure"
                        print(f"🛑 [Campaign] {context.error_message}")
                        break
            
            # Determine overall success
            context.overall_success = (
                context.completed_scripts == context.total_scripts and 
                context.failed_scripts == 0
            )
            
            # Update campaign result in database
            update_campaign_execution_result(
                campaign_execution_id_uuid=context.campaign_result_id,
                status="completed" if context.overall_success else "failed",
                completed_at=datetime.now(),
                execution_time_ms=context.get_execution_time_ms(),
                success=context.overall_success,
                error_message=context.error_message
            )
            
            return self._build_success_result(context)
            
        except Exception as e:
            context.error_message = f"Campaign execution error: {str(e)}"
            print(f"💥 [Campaign] {context.error_message}")
            
            if context.campaign_result_id:
                update_campaign_execution_result(
                    campaign_execution_id_uuid=context.campaign_result_id,
                    status="failed",
                    completed_at=datetime.now(),
                    execution_time_ms=context.get_execution_time_ms(),
                    success=False,
                    error_message=context.error_message
                )
            
            return self._build_failure_result(context, context.error_message)
    
    def _setup_campaign_environment(self, context: CampaignExecutionContext, campaign_config: Dict[str, Any]) -> bool:
        """Setup campaign execution environment at host level"""
        try:
            # Load environment variables first
            current_dir = os.path.dirname(os.path.abspath(__file__))  # /shared/src/lib/executors
            lib_dir = os.path.dirname(current_dir)                    # /shared/src/lib
            src_dir = os.path.dirname(lib_dir)                        # /shared/src
            shared_dir = os.path.dirname(src_dir)                     # /shared
            project_root = os.path.dirname(shared_dir)                # /virtualpytest
            backend_host_src = os.path.join(project_root, 'backend_host', 'src')
            
            print(f"🔧 [Campaign] Loading environment variables...")
            load_environment_variables(calling_script_dir=backend_host_src)
            
            # Create host instance and get team_id
            print(f"🏗️ [Campaign] Creating host instance...")
            from backend_host.src.lib.utils.host_utils import get_host_instance  # Lazy import
            context.host = get_host_instance()
            device_count = context.host.get_device_count()
            print(f"✅ [Campaign] Host created with {device_count} devices")
            
            if device_count == 0:
                context.error_message = "No devices configured"
                return False
            
            # Get team_id from environment (should be loaded by now)
            context.team_id = os.getenv('TEAM_ID', DEFAULT_TEAM_ID)
            
            print(f"🏗️ [Campaign] Environment setup completed")
            print(f"👥 Team ID: {context.team_id}")
            print(f"🖥️ Host: {context.host.host_name}")
            
            return True
            
        except Exception as e:
            context.error_message = f"Environment setup error: {str(e)}"
            return False
    
    def _execute_single_script(self, context: CampaignExecutionContext, campaign_config: Dict[str, Any], 
                             script_config: Dict[str, Any], execution_order: int) -> Dict[str, Any]:
        """Execute a single script or testcase within the campaign"""
        script_start_time = time.time()
        script_name = script_config.get("script_name")
        script_type = script_config.get("script_type", script_name)
        parameters = script_config.get("parameters", {})
        testcase_id = script_config.get("testcase_id")  # NEW: For testcase execution
        
        # NEW: Resolve template variables in parameters (${previous.X}, ${script_N.X})
        resolved_parameters = self._resolve_template_parameters(context, parameters, execution_order)
        
        try:
            # NEW: Handle testcase execution differently
            if script_type == "testcase" and testcase_id:
                return self._execute_testcase(
                    context, 
                    campaign_config, 
                    script_config, 
                    execution_order,
                    resolved_parameters
                )
            
            # EXISTING: Script execution via ScriptExecutor
            print(f"🚀 [Campaign] Executing script via host device script executor")
            
            # Use shared script executor instead of device-specific one
            from .script_executor import ScriptExecutor
            device_id = campaign_config.get("device", "device1")
            
            # Get actual device model
            device_model = "unknown"
            try:
                from backend_host.src.lib.utils.host_utils import get_device_by_id
                device = get_device_by_id(device_id)
                if device:
                    device_model = device.device_model
            except Exception as e:
                print(f"🔍 [Campaign] Could not get device model: {e}")
            
            # Create script executor with device context
            script_executor = ScriptExecutor(
                script_name=script_name,  # Pass script name
                host_name=context.host.host_name,
                device_id=device_id,
                device_model=device_model  # Use actual device model
            )
            script_executor.set_team_id(context.team_id)
            
            # Build parameters string for script executor
            param_parts = []
            
            # Add userinterface_name as optional parameter (scripts declare if they need it)
            if campaign_config.get("userinterface_name"):
                param_parts.extend(["--userinterface", campaign_config["userinterface_name"]])
            
            # Add host and device if specified
            if campaign_config.get("host") and campaign_config["host"] != "auto":
                param_parts.extend(["--host", campaign_config["host"]])
            
            if campaign_config.get("device") and campaign_config["device"] != "auto":
                param_parts.extend(["--device", campaign_config["device"]])
            
            # Add script-specific parameters
            for param_name, param_value in parameters.items():
                param_parts.extend([f"--{param_name}", str(param_value)])
            
            # Join parameters with proper shell quoting to handle special characters
            import shlex
            parameters_string = " ".join(shlex.quote(part) for part in param_parts)
            
            print(f"🚀 [Campaign] Executing: {script_name} {parameters_string}")
            print(f"📋 [Campaign] Starting real-time script output:")
            print("=" * 80)
            
            # Execute script using shared script executor
            result = script_executor.execute_script(script_name, parameters_string)
            
            print("=" * 80)
            print(f"📋 [Campaign] Script output ended")
            
            execution_time_ms = int((time.time() - script_start_time) * 1000)
            
            # Determine success from script executor result
            # Check for script-reported success first, then fall back to exit code
            script_success = result.get('script_success')
            if script_success is not None:
                success = script_success
                print(f"📊 [Campaign] Using script-reported success status: {success}")
            else:
                success = result.get('exit_code', 1) == 0
                print(f"📊 [Campaign] Using exit code for success status: {success} (code: {result.get('exit_code')})")
            
            # Extract script result ID from stdout if available
            script_result_id = None
            stdout = result.get('stdout', '')
            if stdout and 'SCRIPT_RESULT_ID:' in stdout:
                import re
                result_id_match = re.search(r'SCRIPT_RESULT_ID:([^\s\n]+)', stdout)
                if result_id_match:
                    script_result_id = result_id_match.group(1)
                    print(f"🔗 [Campaign] Captured script result ID: {script_result_id}")
            
            # Extract URLs from script executor result
            report_url = result.get('report_url', '')
            logs_url = result.get('logs_url', '')
            
            if success:
                print(f"✅ [Campaign] Script completed successfully in {execution_time_ms}ms")
                return {
                    "success": True,
                    "script_name": script_name,
                    "script_result_id": script_result_id,
                    "execution_time_ms": execution_time_ms,
                    "stdout": stdout,
                    "execution_order": execution_order,
                    "report_url": report_url,
                    "logs_url": logs_url
                }
            else:
                error_msg = f"Script failed with exit code {result.get('exit_code', 1)}"
                print(f"❌ [Campaign] {error_msg}")
                print(f"📝 [Campaign] STDERR: {result.get('stderr', '')}")
                
                return {
                    "success": False,
                    "script_name": script_name,
                    "script_result_id": script_result_id,
                    "execution_time_ms": execution_time_ms,
                    "error": error_msg,
                    "stderr": result.get('stderr', ''),
                    "stdout": stdout,
                    "execution_order": execution_order,
                    "report_url": report_url,
                    "logs_url": logs_url
                }
                
        except Exception as e:
            error_msg = f"Script execution error: {str(e)}"
            execution_time_ms = int((time.time() - script_start_time) * 1000)
            
            return {
                "success": False,
                "script_name": script_name,
                "script_result_id": None,
                "execution_time_ms": execution_time_ms,
                "error": error_msg,
                "execution_order": execution_order,
                "report_url": None,
                "logs_url": None
            }
    
    def _resolve_template_parameters(self, context: CampaignExecutionContext, 
                                    parameters: Dict[str, Any], current_order: int) -> Dict[str, Any]:
        """
        Resolve template variables in parameters.
        Supports: ${previous.output_name} and ${script_N.output_name}
        
        Args:
            context: Campaign execution context with script_executions history
            parameters: Parameters dict with potential template strings
            current_order: Current script execution order (1-based)
            
        Returns:
            Dict with resolved parameter values
        """
        import re
        
        resolved = {}
        template_pattern = r'\$\{([^}]+)\}'  # Matches ${...}
        
        for param_name, param_value in parameters.items():
            # Only process string values
            if not isinstance(param_value, str):
                resolved[param_name] = param_value
                continue
            
            # Find all template variables in the string
            matches = re.findall(template_pattern, param_value)
            
            if not matches:
                # No templates, use as-is
                resolved[param_name] = param_value
                continue
            
            # Resolve each template
            resolved_value = param_value
            for match in matches:
                template_var = f"${{{match}}}"
                
                # Parse template: "previous.output_name" or "script_N.output_name"
                parts = match.split('.')
                if len(parts) != 2:
                    print(f"⚠️ [Campaign] Invalid template format: {template_var}")
                    continue
                
                source, output_name = parts
                
                # Resolve based on source
                if source == "previous":
                    # Get previous script's outputs
                    if current_order > 1 and len(context.script_executions) >= current_order - 1:
                        prev_script = context.script_executions[current_order - 2]  # 0-indexed
                        output_value = prev_script.get('script_outputs', {}).get(output_name)
                        if output_value is not None:
                            resolved_value = resolved_value.replace(template_var, str(output_value))
                            print(f"✓ [Campaign] Resolved {template_var} = {output_value}")
                        else:
                            print(f"⚠️ [Campaign] Output not found: {template_var}")
                    else:
                        print(f"⚠️ [Campaign] No previous script for: {template_var}")
                
                elif source.startswith("script_"):
                    # Get specific script's outputs by order
                    try:
                        script_order = int(source.split('_')[1])
                        if script_order >= 1 and len(context.script_executions) >= script_order:
                            target_script = context.script_executions[script_order - 1]  # 0-indexed
                            output_value = target_script.get('script_outputs', {}).get(output_name)
                            if output_value is not None:
                                resolved_value = resolved_value.replace(template_var, str(output_value))
                                print(f"✓ [Campaign] Resolved {template_var} = {output_value}")
                            else:
                                print(f"⚠️ [Campaign] Output not found: {template_var}")
                        else:
                            print(f"⚠️ [Campaign] Script order out of range: {template_var}")
                    except (ValueError, IndexError) as e:
                        print(f"⚠️ [Campaign] Invalid script reference: {template_var} - {e}")
                else:
                    print(f"⚠️ [Campaign] Unknown template source: {template_var}")
            
            resolved[param_name] = resolved_value
        
        return resolved
    
    def _execute_testcase(self, context: CampaignExecutionContext, campaign_config: Dict[str, Any],
                         script_config: Dict[str, Any], execution_order: int,
                         resolved_parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a testcase within the campaign.
        
        Args:
            context: Campaign execution context
            campaign_config: Overall campaign configuration
            script_config: Testcase script configuration
            execution_order: Execution order number
            resolved_parameters: Resolved input parameters
            
        Returns:
            Dict with execution result including script_outputs
        """
        script_start_time = time.time()
        testcase_id = script_config.get("testcase_id")
        script_name = script_config.get("script_name", f"testcase_{testcase_id}")
        
        print(f"🎯 [Campaign] Executing TestCase: {script_name} (ID: {testcase_id})")
        print(f"📥 [Campaign] Resolved Inputs: {resolved_parameters}")
        
        try:
            # Import testcase executor
            from backend_host.src.services.testcase.testcase_executor import TestCaseExecutor
            
            # Get device info
            device_id = campaign_config.get("device", "device1")
            device_name = device_id
            device_model = "unknown"
            
            try:
                from backend_host.src.lib.utils.host_utils import get_device_by_id
                device = get_device_by_id(device_id)
                if device:
                    device_model = device.device_model
                    device_name = device.device_name
            except Exception as e:
                print(f"🔍 [Campaign] Could not get device info: {e}")
            
            # Create testcase executor
            testcase_executor = TestCaseExecutor()
            
            # Execute testcase by ID
            # TODO: Add input parameter support to testcase_executor.execute_testcase()
            # For now, testcases run without explicit inputs
            result = testcase_executor.execute_testcase(
                testcase_id=testcase_id,
                team_id=context.team_id,
                host_name=context.host.host_name,
                device_id=device_id,
                device_name=device_name,
                device_model=device_model,
                userinterface_name=campaign_config.get("userinterface_name", "")
            )
            
            execution_time_ms = int((time.time() - script_start_time) * 1000)
            
            # Extract script_outputs from testcase execution result
            script_outputs = result.get('script_outputs', {})
            
            print(f"📤 [Campaign] TestCase Outputs: {script_outputs}")
            
            return {
                "script_name": script_name,
                "script_type": "testcase",
                "testcase_id": testcase_id,
                "execution_order": execution_order,
                "success": result.get('success', False),
                "execution_time_ms": execution_time_ms,
                "error": result.get('error'),
                "report_url": result.get('report_url'),
                "logs_url": result.get('logs_url'),
                "script_outputs": script_outputs,  # NEW: For campaign chaining
                "result_type": result.get('result_type')
            }
            
        except Exception as e:
            execution_time_ms = int((time.time() - script_start_time) * 1000)
            error_msg = f"TestCase execution error: {str(e)}"
            print(f"💥 [Campaign] {error_msg}")
            import traceback
            traceback.print_exc()
            
            return {
                "script_name": script_name,
                "script_type": "testcase",
                "testcase_id": testcase_id,
                "execution_order": execution_order,
                "success": False,
                "execution_time_ms": execution_time_ms,
                "error": error_msg,
                "script_outputs": {}
            }
    
    def _build_success_result(self, context: CampaignExecutionContext) -> Dict[str, Any]:
        """Build successful campaign result"""
        return {
            "success": True,
            "campaign_id": context.campaign_id,
            "campaign_execution_id": context.campaign_execution_id,
            "campaign_result_id": context.campaign_result_id,
            "total_scripts": context.total_scripts,
            "completed_scripts": context.completed_scripts,
            "successful_scripts": context.successful_scripts,
            "failed_scripts": context.failed_scripts,
            "execution_time_ms": context.get_execution_time_ms(),
            "script_executions": context.script_executions,
            "overall_success": context.overall_success
        }
    
    def _build_failure_result(self, context: CampaignExecutionContext, error_message: str) -> Dict[str, Any]:
        """Build failed campaign result"""
        return {
            "success": False,
            "campaign_id": context.campaign_id,
            "campaign_execution_id": context.campaign_execution_id,
            "campaign_result_id": context.campaign_result_id,
            "error": error_message,
            "total_scripts": context.total_scripts,
            "completed_scripts": context.completed_scripts,
            "successful_scripts": context.successful_scripts,
            "failed_scripts": context.failed_scripts,
            "execution_time_ms": context.get_execution_time_ms(),
            "script_executions": context.script_executions,
            "overall_success": False
        }


def handle_keyboard_interrupt(campaign_name: str):
    """Handle Ctrl+C gracefully during campaign execution"""
    print(f"\n⚠️ [Campaign:{campaign_name}] Keyboard interrupt received (Ctrl+C)")
    print(f"🛑 [Campaign:{campaign_name}] Campaign execution interrupted by user")
    sys.exit(130)  # Standard exit code for Ctrl+C


def handle_unexpected_error(campaign_name: str, error: Exception):
    """Handle unexpected errors during campaign execution"""
    print(f"\n💥 [Campaign:{campaign_name}] Unexpected error occurred:")
    print(f"❌ [Campaign:{campaign_name}] Error: {str(error)}")
    print(f"📋 [Campaign:{campaign_name}] Campaign execution failed")
    sys.exit(1)
