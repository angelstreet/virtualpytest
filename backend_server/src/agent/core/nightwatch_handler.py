"""
Nightwatch Handler - Incident/Alert Background Tasks

Handles alerts from p1_alerts queue.
Supports dry-run mode for monitoring without AI processing.
Sends events to Slack #nightwatch channel.
"""

import json
import time
from typing import Dict, Any


class NightwatchHandler:
    """Handler for Nightwatch (monitor) background tasks"""
    
    def __init__(self, nickname: str = "Nightwatch"):
        self.nickname = nickname
    
    def handle_dry_run_task(self, task_type: str, task_id: str, task_data: Dict[str, Any], queue_name: str):
        """Handle task in dry-run mode: print, emit Socket.IO, send to Slack, but no AI processing"""
        print(f"[{self.nickname}] 🏃 DRY RUN MODE - Task received:")
        print(f"[{self.nickname}]    Type: {task_type}")
        print(f"[{self.nickname}]    ID: {task_id}")
        print(f"[{self.nickname}]    Queue: {queue_name}")
        print(f"[{self.nickname}]    Data: {json.dumps(task_data, indent=2, default=str)[:500]}...")
        
        # Get Socket.IO manager
        from ..socket_manager import socket_manager
        
        # Build event for Socket.IO
        event_content = self.build_event_content(task_type, task_id, task_data)
        
        event_dict = {
            'type': 'incident_received',
            'agent': self.nickname,
            'content': event_content,
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'task_id': task_id,
            'task_type': task_type,
            'task_data': task_data,
            'queue_name': queue_name,
            'dry_run': True,
        }
        
        # Emit to Socket.IO background_tasks room
        try:
            socket_manager.emit_to_room(
                room='background_tasks',
                event='agent_event',
                data=event_dict,
                namespace='/agent'
            )
            print(f"[{self.nickname}] 📡 Emitted dry-run event to background_tasks room")
        except Exception as emit_error:
            print(f"[{self.nickname}] ⚠️  Failed to emit event: {emit_error}")
        
        # Send to Slack #nightwatch channel
        self.send_to_slack(task_type, task_id, task_data)
        
        print(f"[{self.nickname}] ✅ DRY RUN complete for task {task_id}")
    
    def build_event_content(self, task_type: str, task_id: str, task_data: Dict[str, Any]) -> str:
        """Build human-readable event content for dry-run mode"""
        if task_type == 'incident':
            incident_type = task_data.get('incident_type', 'unknown')
            host_name = task_data.get('host_name', 'Unknown')
            severity = task_data.get('severity', 'unknown')
            description = task_data.get('description', 'No description')
            
            return f"""INCIDENT_ID: {task_id}
TYPE: {incident_type}
HOST: {host_name}
SEVERITY: {severity}
DESCRIPTION: {description}"""
        
        elif task_type == 'alert':
            alert_type = task_data.get('alert_type', 'unknown')
            host_name = task_data.get('host_name', 'Unknown')
            message = task_data.get('message', 'No message')
            
            return f"""ALERT_ID: {task_id}
TYPE: {alert_type}
HOST: {host_name}
MESSAGE: {message}"""
        
        else:
            return f"""TASK_ID: {task_id}
TYPE: {task_type}
DATA: {json.dumps(task_data, indent=2, default=str)[:300]}"""
    
    def build_task_message(self, task_type: str, task_id: str, task_data: Dict[str, Any]) -> str:
        """Build agent message for actual processing (non dry-run mode)"""
        if task_type == 'alert':
            alert_type = task_data.get('alert_type', 'unknown')
            host_name = task_data.get('host_name', 'Unknown')
            message = task_data.get('message', 'No message')
            severity = task_data.get('severity', 'normal')
            
            return f"""Analyze this alert and determine appropriate action:

ALERT_ID: {task_id}
TYPE: {alert_type}
HOST: {host_name}
SEVERITY: {severity}
MESSAGE: {message}

Based on the alert, determine:
1. Is this a real incident requiring action?
2. What is the root cause?
3. What action should be taken?
"""
        
        elif task_type == 'incident':
            incident_type = task_data.get('incident_type', 'unknown')
            host_name = task_data.get('host_name', 'Unknown')
            severity = task_data.get('severity', 'unknown')
            description = task_data.get('description', 'No description')
            
            return f"""Analyze this incident and determine appropriate action:

INCIDENT_ID: {task_id}
TYPE: {incident_type}
HOST: {host_name}
SEVERITY: {severity}
DESCRIPTION: {description}

Based on the incident, determine:
1. What is the severity level?
2. What is the root cause?
3. What immediate action should be taken?
"""
        
        else:
            return f"Unknown task type: {task_type}"
    
    def send_to_slack(self, task_type: str, task_id: str, task_data: Dict[str, Any], result: str = None, dry_run: bool = True):
        """Send incident event to Slack #nightwatch channel"""
        try:
            try:
                from backend_server.src.integrations.agent_slack_hook import send_to_slack_channel
                SLACK_AVAILABLE = True
            except ImportError:
                SLACK_AVAILABLE = False
                return
            
            if not SLACK_AVAILABLE:
                return
            
            dry_run_label = " (DRY RUN)" if dry_run else ""
            dry_run_note = "\n_⚠️ Dry-run mode: Not processing, just monitoring_" if dry_run else ""
            
            # Build Slack message based on task type
            if task_type == 'incident':
                incident_type = task_data.get('incident_type', 'unknown')
                host_name = task_data.get('host_name', 'Unknown')
                severity = task_data.get('severity', 'unknown')
                description = task_data.get('description', 'No description')
                
                severity_emoji = {"critical": "🔴", "high": "🟠", "normal": "🟡", "low": "🟢"}.get(severity.lower(), "⚪")
                
                slack_message = f"""
{severity_emoji} *{self.nickname} Incident Detected*{dry_run_label}

*Type*: `{incident_type}`
*Host*: `{host_name}`
*Severity*: {severity}
*Description*: {description}

*Task ID*: `{task_id}`{dry_run_note}
"""
            
            elif task_type == 'alert':
                alert_type = task_data.get('alert_type', 'unknown')
                host_name = task_data.get('host_name', 'Unknown')
                message = task_data.get('message', 'No message')
                
                slack_message = f"""
🚨 *{self.nickname} Alert Received*{dry_run_label}

*Type*: `{alert_type}`
*Host*: `{host_name}`
*Message*: {message}

*Task ID*: `{task_id}`{dry_run_note}
"""
            
            else:
                slack_message = f"""
📋 *{self.nickname} Event Received*{dry_run_label}

*Type*: `{task_type}`
*Task ID*: `{task_id}`
*Data*: ```{json.dumps(task_data, indent=2, default=str)[:300]}```
{dry_run_note}
"""
            
            # Add result if provided (non dry-run)
            if result:
                slack_message += f"\n*Analysis*:\n```\n{result[:500]}...\n```"
            
            # Send to #nightwatch channel
            send_to_slack_channel(
                channel='#nightwatch',
                message=slack_message,
                agent_name=self.nickname
            )
            print(f"[{self.nickname}] 📬 Sent event to Slack #nightwatch")
            
        except Exception as e:
            print(f"[{self.nickname}] ⚠️  Failed to send to Slack: {e}")

