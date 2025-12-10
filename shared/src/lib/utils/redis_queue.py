"""
Redis Queue Processor

Handles Redis queue operations using native Redis client with BLPOP.
Processes tasks in priority order: P1 (alerts) → P2 (scripts) → P3 (reserved)
"""

import redis
import json
import os
from typing import Optional, Dict, Any
from datetime import datetime


class RedisQueueProcessor:
    """Queue processor using native Redis client with efficient BLPOP"""
    
    def __init__(self):
        # Get Redis connection details from environment
        # Upstash provides both REST API and native Redis protocol
        redis_url = os.getenv('UPSTASH_REDIS_REST_URL', '')
        redis_token = os.getenv('UPSTASH_REDIS_REST_TOKEN', '')
        
        # Parse host from REST URL (e.g., https://host.upstash.io -> host.upstash.io)
        if redis_url:
            host = redis_url.replace('https://', '').replace('http://', '').split('/')[0]
            # For Upstash, password is the token, port is typically 6379 (or 6380 for TLS)
            self.redis_client = redis.Redis(
                host=host,
                port=6379,
                password=redis_token,
                ssl=True,
                ssl_cert_reqs=None,
                decode_responses=True,  # Automatically decode bytes to strings
                socket_connect_timeout=5,
                socket_timeout=5
            )
        else:
            # Fallback to local Redis if Upstash not configured
            redis_host = os.getenv('REDIS_HOST', 'localhost')
            redis_port = int(os.getenv('REDIS_PORT', '6379'))
            redis_password = os.getenv('REDIS_PASSWORD', None)
            
            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                password=redis_password,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
        
        self.queues = ['p1_alerts', 'p2_scripts', 'p3_reserved']
        
        print(f"[@redis_queue] Initialized Redis client")
    
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
            
            result = self.redis_client.lpush('p1_alerts', json.dumps(task))
            
            if result:
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
            
            result = self.redis_client.lpush('p2_scripts', json.dumps(task))
            
            if result:
                print(f"[@redis_queue] Added script {script_id} to P2 queue")
                return True
            else:
                print(f"[@redis_queue] Failed to add script {script_id} to queue")
                return False
                
        except Exception as e:
            print(f"[@redis_queue] Error adding script to queue: {e}")
            return False
    
    def get_next_task_blocking(self, timeout: int = 60) -> Optional[Dict[str, Any]]:
        """
        Get next task using BLPOP (blocking pop) - EFFICIENT!
        
        Waits up to 'timeout' seconds for a task to arrive.
        Checks queues in priority order: p1 → p2 → p3
        
        Returns immediately when task arrives, or after timeout if no tasks.
        """
        try:
            # BLPOP blocks until data is available or timeout
            result = self.redis_client.blpop(self.queues, timeout=timeout)
            
            if result:
                queue_name, task_json = result
                task_data = json.loads(task_json)
                print(f"[@redis_queue] Retrieved task {task_data['id']} from {queue_name}")
                return task_data
                
        except redis.TimeoutError:
            # Timeout is normal when queues are empty
            return None
        except Exception as e:
            print(f"[@redis_queue] Error retrieving task: {e}")
            return None
        
        return None
    
    def get_queue_length(self, queue_name: str) -> int:
        """Get length of specific queue"""
        try:
            return self.redis_client.llen(queue_name)
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
            return self.redis_client.ping()
        except Exception:
            return False
    
    def close(self):
        """Close Redis connection"""
        try:
            self.redis_client.close()
        except Exception:
            pass


# Global instance for easy import
_queue_processor = None

def get_queue_processor() -> RedisQueueProcessor:
    """Get or create global queue processor instance"""
    global _queue_processor
    if _queue_processor is None:
        _queue_processor = RedisQueueProcessor()
    return _queue_processor

