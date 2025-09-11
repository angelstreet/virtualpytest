"""
AI Queue Status Routes

Provides queue monitoring endpoints that directly query Redis
without requiring the backend_discard service to be running.
"""

import os
import json
import requests
from datetime import datetime, timezone
from flask import Blueprint, jsonify, request

# No additional imports needed - using direct Redis access

# Create blueprint
server_ai_queue_bp = Blueprint('server_ai_queue', __name__, url_prefix='/server/ai-queue')

def get_redis_queue_lengths():
    """Get queue lengths directly from Upstash Redis"""
    try:
        # Load environment variables
        redis_url = os.getenv('UPSTASH_REDIS_REST_URL')
        redis_token = os.getenv('UPSTASH_REDIS_REST_TOKEN')
        
        if not redis_url or not redis_token:
            return None
            
        headers = {
            'Authorization': f'Bearer {redis_token}',
            'Content-Type': 'application/json'
        }
        
        # Get lengths of all queues
        queues = ['p1_alerts', 'p2_scripts', 'p3_reserved']
        queue_lengths = {}
        
        for queue in queues:
            response = requests.post(
                redis_url,
                headers=headers,
                json=['LLEN', queue],
                timeout=5
            )
            
            if response.status_code == 200:
                result = response.json()
                queue_lengths[queue] = result.get('result', 0)
            else:
                queue_lengths[queue] = 0
                
        return queue_lengths
        
    except Exception as e:
        print(f"[@routes:ai_queue] Error getting queue lengths: {e}")
        return None

def clear_redis_queue(queue_name):
    """Clear a specific queue in Redis"""
    try:
        redis_url = os.getenv('UPSTASH_REDIS_REST_URL')
        redis_token = os.getenv('UPSTASH_REDIS_REST_TOKEN')
        
        if not redis_url or not redis_token:
            return False
            
        headers = {
            'Authorization': f'Bearer {redis_token}',
            'Content-Type': 'application/json'
        }
        
        # Delete the queue (removes all items)
        response = requests.post(
            redis_url,
            headers=headers,
            json=['DEL', queue_name],
            timeout=5
        )
        
        return response.status_code == 200
        
    except Exception as e:
        print(f"[@routes:ai_queue] Error clearing queue {queue_name}: {e}")
        return False

def peek_redis_queue(queue_name, limit=50):
    """Peek at items in a Redis queue without removing them"""
    try:
        redis_url = os.getenv('UPSTASH_REDIS_REST_URL')
        redis_token = os.getenv('UPSTASH_REDIS_REST_TOKEN')
        
        if not redis_url or not redis_token:
            return []
            
        headers = {
            'Authorization': f'Bearer {redis_token}',
            'Content-Type': 'application/json'
        }
        
        # Get the last N items from the queue (LRANGE -N -1)
        response = requests.post(
            redis_url,
            headers=headers,
            json=['LRANGE', queue_name, f'-{limit}', '-1'],
            timeout=5
        )
        
        if response.status_code == 200:
            result = response.json()
            items = result.get('result', [])
            
            # Parse JSON items
            parsed_items = []
            for item in items:
                try:
                    parsed_item = json.loads(item)
                    parsed_items.append(parsed_item)
                except json.JSONDecodeError:
                    continue
                    
            return parsed_items
        else:
            return []
            
    except Exception as e:
        print(f"[@routes:ai_queue] Error peeking queue {queue_name}: {e}")
        return []

@server_ai_queue_bp.route('/status', methods=['GET'])
def get_ai_queue_status():
    """Get AI queue status with lengths and basic stats"""
    try:
        queue_lengths = get_redis_queue_lengths()
        include_items = request.args.get('include_items', 'false').lower() == 'true'
        
        if queue_lengths is None:
            return jsonify({
                'status': 'error',
                'error': 'Could not connect to Redis',
                'queues': {
                    'incidents': {'name': 'Incidents', 'length': 0, 'processed': 0, 'discarded': 0, 'validated': 0, 'items': []},
                    'scripts': {'name': 'Scripts', 'length': 0, 'processed': 0, 'discarded': 0, 'validated': 0, 'items': []}
                }
            }), 500
        
        # Get queue items if requested
        incidents_items = peek_redis_queue('p1_alerts', 50) if include_items else []
        scripts_items = peek_redis_queue('p2_scripts', 50) if include_items else []
        
        return jsonify({
            'status': 'healthy',
            'service': 'ai_queue_monitor',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'stats': {
                'service_running': False,  # backend_discard not required for queue monitoring
                'redis_connected': True
            },
            'queues': {
                'incidents': {
                    'name': 'Incidents',
                    'length': queue_lengths.get('p1_alerts', 0),
                    'processed': 0,  # Would need backend_discard stats for this
                    'discarded': 0,
                    'validated': 0,
                    'items': incidents_items
                },
                'scripts': {
                    'name': 'Scripts', 
                    'length': queue_lengths.get('p2_scripts', 0),
                    'processed': 0,
                    'discarded': 0,
                    'validated': 0,
                    'items': scripts_items
                }
            }
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'queues': {
                'incidents': {'name': 'Incidents', 'length': 0, 'processed': 0, 'discarded': 0, 'validated': 0},
                'scripts': {'name': 'Scripts', 'length': 0, 'processed': 0, 'discarded': 0, 'validated': 0}
            }
        }), 500

@server_ai_queue_bp.route('/clear', methods=['POST'])
def clear_queues():
    """Clear AI processing queues"""
    try:
        data = request.json if request.json else {}
        queue_type = data.get('queue_type', 'all')  # 'incidents', 'scripts', or 'all'
        
        results = {}
        
        if queue_type in ['incidents', 'all']:
            results['incidents'] = clear_redis_queue('p1_alerts')
            
        if queue_type in ['scripts', 'all']:
            results['scripts'] = clear_redis_queue('p2_scripts')
            
        if queue_type == 'all':
            results['reserved'] = clear_redis_queue('p3_reserved')
        
        success = all(results.values())
        
        return jsonify({
            'status': 'success' if success else 'partial_failure',
            'cleared': results,
            'message': f'Queue clearing {"completed" if success else "completed with some failures"}'
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500
