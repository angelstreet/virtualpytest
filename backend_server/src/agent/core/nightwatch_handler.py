"""
Nightwatch Handler - Incident/Alert Background Tasks

Handles alerts from p1_alerts queue.
Supports dry-run mode for monitoring without AI processing.
In dry-run mode: logs only, NO Slack (avoids rate limits).

AI PROCESSING FILTERS:
1. DURATION FILTER (ALERT_MIN_DURATION_SECONDS = 30s):
   - Only alerts lasting >= 30 seconds are processed with AI
   - Short events are dropped and marked as checked_by='system'
   - Prevents AI processing of transient/flickering issues

2. RATE LIMIT FILTER (ALERT_RATE_LIMIT_SECONDS = 3600s):
   - Max 1 AI analysis per device per hour
   - Subsequent alerts within window are dropped and marked as checked_by='system'
   - Prevents token usage explosion from repeated alerts on same device
   - Rate limit tracked per host_name/device_id in Redis

Both filters help control AI token costs while maintaining alert visibility in DB.
Filters are configured as class constants and can be adjusted in this file.
"""

import json
import time
import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional


class NightwatchHandler:
    """Handler for Nightwatch (monitor) background tasks"""
    
    # Alert processing filters
    ALERT_MIN_DURATION_SECONDS = 30    # Only process alerts >= 30 seconds
    ALERT_RATE_LIMIT_SECONDS = 3600    # Max 1 AI analysis per device per hour
    
    def __init__(self, nickname: str = "Nightwatch"):
        self.nickname = nickname
    
    def should_process_with_ai(self, task_id: str, task_data: Dict[str, Any]) -> bool:
        """
        Check if alert should be processed with AI based on duration and rate limits.
        
        Returns:
            True if should process with AI, False if should skip
            
        Side effects:
            - Marks alert as checked_by='system' in DB if skipped
            - Updates rate limit timestamp in Redis if checks pass
        """
        host_name = task_data.get('host_name', 'unknown')
        device_id = task_data.get('device_id', 'unknown')
        
        # FILTER 1: Duration check - skip alerts under minimum duration
        if task_data.get('start_time'):
            try:
                start_time_str = task_data.get('start_time', '')
                start_dt = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                now_dt = datetime.now(timezone.utc)
                duration_seconds = (now_dt - start_dt).total_seconds()
                
                print(f"[{self.nickname}] ⏱️  Alert duration: {duration_seconds:.1f}s")
                
                if duration_seconds < self.ALERT_MIN_DURATION_SECONDS:
                    print(f"[{self.nickname}] ⏭️  Skipping short event ({duration_seconds:.1f}s < {self.ALERT_MIN_DURATION_SECONDS}s)")
                    print(f"[{self.nickname}] 📝 Marking as checked_by=system in DB")
                    
                    # Mark in DB as checked without comment
                    from shared.src.lib.database.alerts_db import update_alert_checked_status
                    update_alert_checked_status(task_id, checked=True, check_type='system')
                    
                    print(f"[{self.nickname}] ✅ Short event {task_id} dropped (no AI processing)")
                    return False
                else:
                    print(f"[{self.nickname}] ✅ Alert duration sufficient ({duration_seconds:.1f}s >= {self.ALERT_MIN_DURATION_SECONDS}s)")
                    
            except Exception as duration_error:
                print(f"[{self.nickname}] ⚠️  Failed to calculate duration: {duration_error}")
                # Continue with processing if duration check fails
        
        # FILTER 2: Rate limit check - max 1 AI analysis per device per hour
        try:
            redis_config = self._setup_redis_rest_api()
            if redis_config:
                rate_limit_key = f"nightwatch:ratelimit:{host_name}:{device_id}"
                
                # Get last processing timestamp
                result = self._redis_command(redis_config, ['GET', rate_limit_key])
                
                if result and result.get('result'):
                    last_processed_ts = float(result['result'])
                    current_ts = time.time()
                    time_since_last = current_ts - last_processed_ts
                    
                    print(f"[{self.nickname}] 🕐 Last AI analysis for {host_name}/{device_id}: {time_since_last:.0f}s ago")
                    
                    # Skip if within rate limit window
                    if time_since_last < self.ALERT_RATE_LIMIT_SECONDS:
                        time_remaining = self.ALERT_RATE_LIMIT_SECONDS - time_since_last
                        print(f"[{self.nickname}] 🚫 Rate limit hit for {host_name}/{device_id}")
                        print(f"[{self.nickname}] ⏰ Next AI analysis allowed in {time_remaining/60:.1f} minutes")
                        print(f"[{self.nickname}] 📝 Marking as checked_by=system in DB")
                        
                        # Mark in DB as checked
                        from shared.src.lib.database.alerts_db import update_alert_checked_status
                        update_alert_checked_status(task_id, checked=True, check_type='system')
                        
                        print(f"[{self.nickname}] ✅ Alert {task_id} dropped (rate limited, no AI processing)")
                        return False
                    else:
                        print(f"[{self.nickname}] ✅ Rate limit OK for {host_name}/{device_id}")
                else:
                    print(f"[{self.nickname}] ✅ First AI analysis for {host_name}/{device_id}")
                    
        except Exception as rate_limit_error:
            print(f"[{self.nickname}] ⚠️  Rate limit check failed: {rate_limit_error}")
            # Continue with processing if rate limit check fails
        
        # All checks passed - proceed with AI processing
        print(f"[{self.nickname}] ✅ All checks passed, proceeding with AI analysis")
        return True
    
    def update_rate_limit(self, task_data: Dict[str, Any]):
        """Update rate limit timestamp after successful AI processing"""
        try:
            host_name = task_data.get('host_name', 'unknown')
            device_id = task_data.get('device_id', 'unknown')
            rate_limit_key = f"nightwatch:ratelimit:{host_name}:{device_id}"
            
            redis_config = self._setup_redis_rest_api()
            if redis_config:
                current_ts = str(time.time())
                # Set with TTL = rate_limit + 1 hour buffer
                ttl_seconds = self.ALERT_RATE_LIMIT_SECONDS + 3600
                self._redis_command(redis_config, ['SETEX', rate_limit_key, ttl_seconds, current_ts])
                print(f"[{self.nickname}] ✅ Rate limit timestamp updated for {host_name}/{device_id}")
        except Exception as e:
            print(f"[{self.nickname}] ⚠️  Failed to update rate limit: {e}")
    
    def _setup_redis_rest_api(self):
        """Setup Redis REST API client (uses Upstash REST API)"""
        try:
            redis_url = os.getenv('UPSTASH_REDIS_REST_URL', '')
            redis_token = os.getenv('UPSTASH_REDIS_REST_TOKEN', '')
            
            if not redis_url or not redis_token:
                return None
            
            return {
                'url': redis_url,
                'headers': {
                    'Authorization': f'Bearer {redis_token}',
                    'Content-Type': 'application/json'
                }
            }
        except Exception as e:
            print(f"[{self.nickname}] Failed to setup Redis REST API: {e}")
            return None
    
    def _redis_command(self, redis_config: dict, command: list):
        """Execute Redis command via REST API"""
        try:
            import requests
            response = requests.post(
                redis_config['url'],
                headers=redis_config['headers'],
                json=command,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return None
                
        except Exception as e:
            print(f"[{self.nickname}] Redis command failed: {e}")
            return None
    
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
        
        # DRY RUN: No Slack to avoid rate limits - just log + Socket.IO
        print(f"[{self.nickname}] ✅ DRY RUN complete for task {task_id} (no Slack)")
    
    def build_event_content(self, task_type: str, task_id: str, task_data: Dict[str, Any]) -> str:
        """Build human-readable event content for dry-run mode"""
        # Alert data structure: incident_type, host_name, device_name, status, consecutive_count, metadata
        incident_type = task_data.get('incident_type') or task_data.get('alert_type', 'unknown')
        host_name = task_data.get('host_name', 'Unknown')
        device_name = task_data.get('device_name', '')
        status = task_data.get('status', 'active')
        consecutive_count = task_data.get('consecutive_count', 0)
        
        # Extract severity from metadata if available
        metadata = task_data.get('metadata', {})
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except:
                metadata = {}
        
        # Build summary from metadata
        summary_parts = []
        if metadata.get('freeze'):
            summary_parts.append('FREEZE detected')
        if metadata.get('blackscreen'):
            summary_parts.append('BLACKSCREEN detected')
        if metadata.get('audio') is False or metadata.get('mean_volume_db', 0) < -80:
            summary_parts.append('AUDIO LOSS detected')
        
        summary = ' | '.join(summary_parts) if summary_parts else f'{incident_type} detected'
        device_info = f" ({device_name})" if device_name else ""
        
        return f"""ALERT_ID: {task_id}
TYPE: {incident_type}
HOST: {host_name}{device_info}
STATUS: {status}
COUNT: {consecutive_count}
SUMMARY: {summary}"""
    
    def build_task_message(self, task_type: str, task_id: str, task_data: Dict[str, Any]) -> str:
        """Build agent message for actual processing (non dry-run mode)"""
        # Alert data structure from DB
        incident_type = task_data.get('incident_type') or task_data.get('alert_type', 'unknown')
        host_name = task_data.get('host_name', 'Unknown')
        device_name = task_data.get('device_name', '')
        status = task_data.get('status', 'active')
        consecutive_count = task_data.get('consecutive_count', 0)
        start_time = task_data.get('start_time', '')
        
        # Parse metadata for details
        metadata = task_data.get('metadata', {})
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except:
                metadata = {}
        
        # Build context from metadata
        context_lines = []
        if metadata.get('freeze'):
            freeze_debug = metadata.get('freeze_debug', {})
            context_lines.append(f"- FREEZE: {freeze_debug.get('frames_found', '?')} frozen frames detected")
        if metadata.get('blackscreen'):
            context_lines.append(f"- BLACKSCREEN: {metadata.get('blackscreen_percentage', '?')}% black")
        if metadata.get('mean_volume_db') is not None:
            context_lines.append(f"- AUDIO: {metadata.get('mean_volume_db', '?')} dB")
        if metadata.get('r2_images', {}).get('thumbnail_urls'):
            context_lines.append(f"- IMAGES: {len(metadata['r2_images']['thumbnail_urls'])} thumbnails available")
        
        context = '\n'.join(context_lines) if context_lines else 'No additional context'
        device_info = f" ({device_name})" if device_name else ""
        
        return f"""Analyze this alert and determine appropriate action:

ALERT_ID: {task_id}
TYPE: {incident_type}
HOST: {host_name}{device_info}
STATUS: {status}
CONSECUTIVE_COUNT: {consecutive_count}
START_TIME: {start_time}

DETECTION DETAILS:
{context}

Based on the alert, determine:
1. Is this a real incident requiring action?
2. What is the root cause?
3. What action should be taken?
"""
    
    def send_to_slack(self, task_type: str, task_id: str, task_data: Dict[str, Any], result: str = None, dry_run: bool = False):
        """Send incident event to Slack #nightwatch channel (only when dry_run=False)"""
        try:
            try:
                from backend_server.src.integrations.agent_slack_hook import send_to_slack_channel
                SLACK_AVAILABLE = True
            except ImportError:
                SLACK_AVAILABLE = False
                return
            
            if not SLACK_AVAILABLE:
                return
            
            # Extract alert data
            incident_type = task_data.get('incident_type') or task_data.get('alert_type', 'unknown')
            host_name = task_data.get('host_name', 'Unknown')
            device_name = task_data.get('device_name', '')
            status = task_data.get('status', 'active')
            consecutive_count = task_data.get('consecutive_count', 0)
            
            # Parse metadata
            metadata = task_data.get('metadata', {})
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except:
                    metadata = {}
            
            # Build summary from metadata
            issues = []
            if metadata.get('freeze'):
                issues.append('🧊 FREEZE')
            if metadata.get('blackscreen'):
                issues.append('⬛ BLACKSCREEN')
            if metadata.get('audio') is False or metadata.get('mean_volume_db', 0) < -80:
                issues.append('🔇 AUDIO LOSS')
            
            issues_str = ' | '.join(issues) if issues else incident_type
            device_info = f" ({device_name})" if device_name else ""
            
            # Severity based on consecutive count
            if consecutive_count >= 10:
                severity_emoji = "🔴"
                severity = "critical"
            elif consecutive_count >= 5:
                severity_emoji = "🟠"
                severity = "high"
            else:
                severity_emoji = "🟡"
                severity = "normal"
            
            slack_message = f"""
{severity_emoji} *{self.nickname} Alert*

*Type*: `{incident_type}`
*Host*: `{host_name}`{device_info}
*Issues*: {issues_str}
*Status*: {status} (count: {consecutive_count})
*Severity*: {severity}

*Alert ID*: `{task_id}`
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

