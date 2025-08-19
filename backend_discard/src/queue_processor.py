"""
Queue Processor for Backend Discard Service

Handles Redis queue operations using Upstash REST API.
Processes tasks in priority order: P1 (alerts) → P2 (scripts) → P3 (reserved)
"""

import requests
import json
import os
import time
from typing import Optional, Dict, Any
from datetime import datetime


def _ensure_environment_loaded():
    """Ensure project environment variables are loaded"""
    # Check if critical Redis variables are already loaded
    if os.getenv('UPSTASH_REDIS_REST_URL') and os.getenv('UPSTASH_REDIS_REST_TOKEN'):
        return  # Already loaded
    
    try:
        # Load project environment only (no service-specific .env for Redis vars)
        from shared.lib.utils.app_utils import load_environment_variables
        load_environment_variables(mode='discard', calling_script_dir=None)
    except Exception as e:
        # Fallback: try loading project .env directly
        from dotenv import load_dotenv
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))  # Go up 2 levels: src -> backend_discard -> project_root
        project_env_path = os.path.join(project_root, '.env')
        if os.path.exists(project_env_path):
            load_dotenv(project_env_path)


class SimpleQueueProcessor:
    """Simple queue processor using Upstash Redis REST API"""
    
    def __init__(self):
        # Ensure environment variables are loaded (especially when called from shared services)
        _ensure_environment_loaded()
        
        # Use Upstash Redis REST API (from root .env)
        self.redis_url = os.getenv('UPSTASH_REDIS_REST_URL')
        self.redis_token = os.getenv('UPSTASH_REDIS_REST_TOKEN')
        
        if not self.redis_url or not self.redis_token:
            raise ValueError("Missing UPSTASH_REDIS_REST_URL or UPSTASH_REDIS_REST_TOKEN in environment")
        
        self.headers = {
            'Authorization': f'Bearer {self.redis_token}',
            'Content-Type': 'application/json'
        }
        self.queues = ['p1_alerts', 'p2_scripts', 'p3_reserved']
        
        print(f"[@queue_processor] Initialized with Upstash Redis: {self.redis_url[:50]}...")
    
    def _redis_command(self, command: list) -> Optional[dict]:
        """Execute Redis command via REST API"""
        try:
            response = requests.post(
                self.redis_url,
                headers=self.headers,
                json=command,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"[@queue_processor] Redis API error: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"[@queue_processor] Redis command failed: {e}")
        
        return None
    
    def add_alert_to_queue(self, alert_id: str, alert_data: Dict[str, Any]) -> bool:
        """Add alert to p1 queue (highest priority)"""
        try:
            task = {
                'type': 'alert',
                'id': alert_id,
                'data': alert_data,
                'created_at': datetime.now().isoformat(),
                'priority': 1
            }
            
            result = self._redis_command(['LPUSH', 'p1_alerts', json.dumps(task)])
            
            if result and result.get('result'):
                print(f"[@queue_processor] Added alert {alert_id} to P1 queue")
                return True
            else:
                print(f"[@queue_processor] Failed to add alert {alert_id} to queue")
                return False
                
        except Exception as e:
            print(f"[@queue_processor] Error adding alert to queue: {e}")
            return False
    
    def add_script_to_queue(self, script_id: str, script_data: Dict[str, Any]) -> bool:
        """Add script result to p2 queue"""
        try:
            task = {
                'type': 'script',
                'id': script_id,
                'data': script_data,
                'created_at': datetime.now().isoformat(),
                'priority': 2
            }
            
            result = self._redis_command(['LPUSH', 'p2_scripts', json.dumps(task)])
            
            if result and result.get('result'):
                print(f"[@queue_processor] Added script {script_id} to P2 queue")
                return True
            else:
                print(f"[@queue_processor] Failed to add script {script_id} to queue")
                return False
                
        except Exception as e:
            print(f"[@queue_processor] Error adding script to queue: {e}")
            return False
    
    def get_next_task(self) -> Optional[Dict[str, Any]]:
        """Get next task in priority order: p1 → p2 → p3"""
        for queue in self.queues:
            try:
                result = self._redis_command(['RPOP', queue])
                
                if result and result.get('result'):
                    task_data = json.loads(result['result'])
                    print(f"[@queue_processor] Retrieved task {task_data['id']} from {queue}")
                    return task_data
                    
            except Exception as e:
                print(f"[@queue_processor] Error retrieving from {queue}: {e}")
                continue
        
        return None
    
    def get_queue_length(self, queue_name: str) -> int:
        """Get length of specific queue"""
        try:
            result = self._redis_command(['LLEN', queue_name])
            if result and 'result' in result:
                return int(result['result'])
        except Exception as e:
            print(f"[@queue_processor] Error getting queue length for {queue_name}: {e}")
        
        return 0
    
    def get_all_queue_lengths(self) -> Dict[str, int]:
        """Get lengths of all queues"""
        lengths = {}
        for queue in self.queues:
            lengths[queue] = self.get_queue_length(queue)
        return lengths
    
    def health_check(self) -> bool:
        """Check if Redis connection is working"""
        try:
            result = self._redis_command(['PING'])
            return result and result.get('result') == 'PONG'
        except Exception:
            return False


# Global instance for easy import
queue_processor = None

def get_queue_processor() -> SimpleQueueProcessor:
    """Get or create global queue processor instance"""
    global queue_processor
    if queue_processor is None:
        queue_processor = SimpleQueueProcessor()
    return queue_processor
