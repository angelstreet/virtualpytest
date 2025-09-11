"""
AI Queue Status Routes

Provides queue monitoring endpoints that directly query Redis
without requiring the backend_discard service to be running.
"""

import os
import json
import requests
from datetime import datetime, timezone
from flask import Blueprint, jsonify

# Import shared utilities
from shared.lib.utils.env_utils import load_environment_variables

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

@server_ai_queue_bp.route('/status', methods=['GET'])
def get_ai_queue_status():
    """Get AI queue status with lengths and basic stats"""
    try:
        queue_lengths = get_redis_queue_lengths()
        
        if queue_lengths is None:
            return jsonify({
                'status': 'error',
                'error': 'Could not connect to Redis',
                'queues': {
                    'incidents': {'name': 'Incidents', 'length': 0, 'processed': 0, 'discarded': 0, 'validated': 0},
                    'scripts': {'name': 'Scripts', 'length': 0, 'processed': 0, 'discarded': 0, 'validated': 0}
                }
            }), 500
        
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
                    'validated': 0
                },
                'scripts': {
                    'name': 'Scripts', 
                    'length': queue_lengths.get('p2_scripts', 0),
                    'processed': 0,
                    'discarded': 0,
                    'validated': 0
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
