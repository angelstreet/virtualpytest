"""
Sherlock Handler - Script Analysis Background Tasks

Handles script execution results from p2_scripts queue.
Builds analysis messages and sends results to Slack #sherlock channel.
"""

import json
from typing import Dict, Any


class SherlockHandler:
    """Handler for Sherlock (analyzer) background tasks"""
    
    def __init__(self, nickname: str = "Sherlock"):
        self.nickname = nickname
    
    def build_task_message(self, task_type: str, task_id: str, task_data: Dict[str, Any]) -> str:
        """Build agent message from queue task. Pre-fetches report to save tokens."""
        if task_type == 'script':
            script_name = task_data.get('script_name', 'Unknown')
            success = task_data.get('success', False)
            error_msg = task_data.get('error_msg', 'None')
            execution_time_ms = task_data.get('execution_time_ms', 0)
            report_url = task_data.get('html_report_r2_url', '')
            logs_url = task_data.get('logs_url', '')
            
            msg = f"""Analyze this script execution for false positive detection:

SCRIPT: {script_name}
SCRIPT_RESULT_ID: {task_id}
RESULT: {'PASSED' if success else 'FAILED'}
ERROR: {error_msg}
DURATION: {execution_time_ms}ms
"""
            
            # Pre-fetch report content
            if report_url:
                try:
                    from backend_server.src.lib.report_fetcher import fetch_execution_report
                    report_data = fetch_execution_report(report_url, logs_url)
                    
                    # Include parsed report directly in message
                    if report_data.get('summary'):
                        msg += f"\n\n{report_data['summary']}"
                    else:
                        msg += f"\n\nReport URL: {report_url}"
                        if logs_url:
                            msg += f"\nLogs URL: {logs_url}"
                except Exception as e:
                    print(f"[{self.nickname}] ⚠️  Failed to pre-fetch report: {e}")
                    msg += f"\n\nReport URL: {report_url}"
                    if logs_url:
                        msg += f"\nLogs URL: {logs_url}"
            
            msg += f"""

Based on the report above, classify this execution and call:
update_execution_analysis(script_result_id='{task_id}', discard=<true/false>, classification=<CLASSIFICATION>, explanation=<brief explanation>)

CLASSIFICATIONS:
- VALID_PASS: Test passed, legitimate success (discard=false)
- VALID_FAIL: Test failed, real bug detected (discard=false)
- BUG: Screenshot shows element BUT error says "not found" (discard=false)
- SCRIPT_ISSUE: Test automation problem - bad selector/timing/expected value (discard=true)
- SYSTEM_ISSUE: Infrastructure problem - black screen/no signal/device disconnected (discard=true)"""
            
            return msg
        
        else:
            return f"Unknown task type: {task_type}"
    
    def send_to_slack(self, task_type: str, task_id: str, task_data: Dict[str, Any], result: str, success: bool = True):
        """Send analysis result to Slack #sherlock channel"""
        try:
            try:
                from backend_server.src.integrations.agent_slack_hook import send_to_slack_channel
                SLACK_AVAILABLE = True
            except ImportError:
                SLACK_AVAILABLE = False
                return
            
            if not SLACK_AVAILABLE:
                return
            
            # Build Slack message
            script_name = task_data.get('script_name', 'Unknown')
            script_success = task_data.get('success', False)
            error_msg = task_data.get('error_msg', 'None')
            
            status_emoji = "✅" if success else "❌"
            result_emoji = "🟢" if script_success else "🔴"
            
            slack_message = f"""
{status_emoji} *{self.nickname} Analysis Complete*

*Script*: `{script_name}`
*Result*: {result_emoji} {'PASSED' if script_success else 'FAILED'}
*Error*: {error_msg}

*Analysis*:
```
{result[:500]}...
```

*Task ID*: `{task_id}`
"""
            
            # Send to #sherlock channel
            send_to_slack_channel(
                channel='#sherlock',
                message=slack_message,
                agent_name=self.nickname
            )
            print(f"[{self.nickname}] 📬 Sent result to Slack #sherlock")
            
        except Exception as e:
            print(f"[{self.nickname}] ⚠️  Failed to send to Slack: {e}")

