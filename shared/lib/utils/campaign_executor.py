#!/usr/bin/env python3
"""
Campaign Execution Framework for VirtualPyTest

This module provides functionality to execute test campaigns that consist of
multiple script executions with proper tracking and reporting.

Usage:
    from shared.lib.utils.campaign_executor import CampaignExecutor
    
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

from shared.lib.supabase.campaign_executions_db import (
    record_campaign_execution_start,
    update_campaign_execution_result,
    add_script_result_to_campaign
)
from shared.lib.utils.script_execution_utils import setup_script_environment


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
    """Campaign execution orchestrator"""
    
    def __init__(self):
        self.project_root = project_root
    
    def execute_campaign(self, campaign_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a test campaign with multiple scripts.
        
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
            
            # Setup environment
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
                campaign_result_id=context.campaign_result_id,
                status="completed" if context.overall_success else "failed",
                end_time=datetime.now(),
                total_duration_ms=context.get_execution_time_ms(),
                total_scripts=context.total_scripts,
                completed_scripts=context.completed_scripts,
                successful_scripts=context.successful_scripts,
                failed_scripts=context.failed_scripts,
                overall_success=context.overall_success,
                error_message=context.error_message
            )
            
            return self._build_success_result(context)
            
        except Exception as e:
            context.error_message = f"Campaign execution error: {str(e)}"
            print(f"💥 [Campaign] {context.error_message}")
            
            if context.campaign_result_id:
                update_campaign_execution_result(
                    campaign_result_id=context.campaign_result_id,
                    status="failed",
                    end_time=datetime.now(),
                    total_duration_ms=context.get_execution_time_ms(),
                    overall_success=False,
                    error_message=context.error_message
                )
            
            return self._build_failure_result(context, context.error_message)
    
    def _setup_campaign_environment(self, context: CampaignExecutionContext, campaign_config: Dict[str, Any]) -> bool:
        """Setup campaign execution environment"""
        try:
            # Setup script environment to get team_id and host info
            env_result = setup_script_environment("campaign")
            
            if not env_result["success"]:
                context.error_message = f"Environment setup failed: {env_result.get('error')}"
                return False
            
            context.team_id = env_result["team_id"]
            context.host = env_result["host"]
            
            print(f"🏗️ [Campaign] Environment setup completed")
            print(f"👥 Team ID: {context.team_id}")
            print(f"🖥️ Host: {context.host.host_name}")
            
            return True
            
        except Exception as e:
            context.error_message = f"Environment setup error: {str(e)}"
            return False
    
    def _find_and_link_script_result(self, context: CampaignExecutionContext, script_name: str, 
                                   start_time: float, execution_time_ms: int) -> Optional[str]:
        """Find the script result created by the script execution and link it to campaign"""
        try:
            from shared.lib.utils.supabase_utils import get_supabase_client
            
            supabase = get_supabase_client()
            
            # Look for script results created around the execution time
            # Allow for some time variance (±30 seconds)
            start_window = datetime.fromtimestamp(start_time - 30)
            end_window = datetime.fromtimestamp(start_time + (execution_time_ms/1000) + 30)
            
            result = supabase.table('script_results').select('id').eq('script_name', script_name).eq('team_id', context.team_id).gte('started_at', start_window.isoformat()).lte('started_at', end_window.isoformat()).order('started_at', desc=True).limit(1).execute()
            
            if result.data:
                script_result_id = result.data[0]['id']
                
                # Link this script result to the campaign
                if add_script_result_to_campaign(context.campaign_result_id, script_result_id):
                    print(f"🔗 [Campaign] Linked script result {script_result_id} to campaign")
                    return script_result_id
                else:
                    print(f"⚠️ [Campaign] Failed to link script result {script_result_id}")
            else:
                print(f"⚠️ [Campaign] Could not find script result for {script_name}")
                
        except Exception as e:
            print(f"❌ [Campaign] Error finding script result: {str(e)}")
            
        return None
    
    def _execute_single_script(self, context: CampaignExecutionContext, campaign_config: Dict[str, Any], 
                             script_config: Dict[str, Any], execution_order: int) -> Dict[str, Any]:
        """Execute a single script within the campaign"""
        script_start_time = time.time()
        script_name = script_config.get("script_name")
        script_type = script_config.get("script_type", script_name)
        parameters = script_config.get("parameters", {})
        
        try:
            # Build script command
            script_path = os.path.join(self.project_root, "test_scripts", script_name)
            if not os.path.exists(script_path):
                raise FileNotFoundError(f"Script not found: {script_path}")
            
            # Build command arguments
            cmd = ["python", script_path]
            
            # Add userinterface_name as positional argument
            if campaign_config.get("userinterface_name"):
                cmd.append(campaign_config["userinterface_name"])
            
            # Add host and device if specified
            if campaign_config.get("host") and campaign_config["host"] != "auto":
                cmd.extend(["--host", campaign_config["host"]])
            
            if campaign_config.get("device") and campaign_config["device"] != "auto":
                cmd.extend(["--device", campaign_config["device"]])
            
            # Add script-specific parameters
            for param_name, param_value in parameters.items():
                cmd.extend([f"--{param_name}", str(param_value)])
            
            print(f"🚀 [Campaign] Executing command: {' '.join(cmd)}")
            
            # Execute script
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )
            
            execution_time_ms = int((time.time() - script_start_time) * 1000)
            success = result.returncode == 0
            
            # Try to find and link the script result that was created by the script execution
            script_result_id = self._find_and_link_script_result(
                context, script_name, script_start_time, execution_time_ms
            )
            
            if success:
                print(f"✅ [Campaign] Script completed successfully in {execution_time_ms}ms")
                return {
                    "success": True,
                    "script_name": script_name,
                    "script_result_id": script_result_id,
                    "execution_time_ms": execution_time_ms,
                    "stdout": result.stdout,
                    "execution_order": execution_order
                }
            else:
                error_msg = f"Script failed with return code {result.returncode}"
                print(f"❌ [Campaign] {error_msg}")
                print(f"📝 [Campaign] STDERR: {result.stderr}")
                
                return {
                    "success": False,
                    "script_name": script_name,
                    "script_result_id": script_result_id,
                    "execution_time_ms": execution_time_ms,
                    "error": error_msg,
                    "stderr": result.stderr,
                    "stdout": result.stdout,
                    "execution_order": execution_order
                }
                
        except subprocess.TimeoutExpired:
            error_msg = "Script execution timed out"
            execution_time_ms = int((time.time() - script_start_time) * 1000)
            
            return {
                "success": False,
                "script_name": script_name,
                "script_result_id": None,
                "execution_time_ms": execution_time_ms,
                "error": error_msg,
                "execution_order": execution_order
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
                "execution_order": execution_order
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