"""
Redis Queue Processor

Handles Redis queue operations using Upstash REST API.
Processes tasks in priority order: P1 (alerts) → P2 (scripts) → P3 (reserved)
"""

import requests
import json
import os
from typing import Optional, Dict, Any
from datetime import datetime


class RedisQueueProcessor:
    """Queue processor using Upstash Redis REST API"""
    
    def __init__(self):
        # Use Upstash Redis REST API
        self.redis_url = os.getenv('UPSTASH_REDIS_REST_URL')
        self.redis_token = os.getenv('UPSTASH_REDIS_REST_TOKEN')
        
        if not self.redis_url or not self.redis_token:
            raise ValueError("Missing UPSTASH_REDIS_REST_URL or UPSTASH_REDIS_REST_TOKEN in environment")
        
        self.headers = {
            'Authorization': f'Bearer {self.redis_token}',
            'Content-Type': 'application/json'
        }
        self.queues = ['p1_alerts', 'p2_scripts', 'p3_reserved']
        
        print(f"[@redis_queue] Initialized with Upstash Redis REST API: {self.redis_url[:50]}...")
    
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
                print(f"[@redis_queue] Redis API error: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"[@redis_queue] Redis command failed: {e}")
        
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
                print(f"[@redis_queue] Added alert {alert_id} to P1 queue")
                return True
            else:
                print(f"[@redis_queue] Failed to add alert {alert_id} to queue")
                return False
                
        except Exception as e:
            print(f"[@redis_queue] Error adding alert to queue: {e}")
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
                print(f"[@redis_queue] Added script {script_id} to P2 queue")
                return True
            else:
                print(f"[@redis_queue] Failed to add script {script_id} to queue")
                return False
                
        except Exception as e:
            print(f"[@redis_queue] Error adding script to queue: {e}")
            return False
    
    def get_queue_length(self, queue_name: str) -> int:
        """Get length of specific queue"""
        try:
            result = self._redis_command(['LLEN', queue_name])
            if result and 'result' in result:
                return int(result['result'])
        except Exception as e:
            print(f"[@redis_queue] Error getting queue length for {queue_name}: {e}")
        
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
_queue_processor = None

def get_queue_processor() -> RedisQueueProcessor:
    """Get or create global queue processor instance"""
    global _queue_processor
    if _queue_processor is None:
        _queue_processor = RedisQueueProcessor()
    return _queue_processor
