"""
Host Action Routes - Device Action Execution (Legacy API - uses Orchestrator internally)

This module maintains backward compatibility for existing API consumers
while using the new ExecutionOrchestrator internally.
"""

from flask import Blueprint, request, jsonify, current_app
from backend_host.src.orchestrator import ExecutionOrchestrator

# Create blueprint
host_actions_bp = Blueprint('host_actions', __name__, url_prefix='/host/action')

@host_actions_bp.route('/executeBatch', methods=['POST'])
def action_execute_batch():
    """Execute batch of actions using ExecutionOrchestrator"""
    try:
        print("[@route:host_actions:action_execute_batch] Starting batch action execution")
        
        # Get request data
        data = request.get_json() or {}
        actions = data.get('actions', [])
        retry_actions = data.get('retry_actions', [])
        failure_actions = data.get('failure_actions', [])
        device_id = data.get('device_id', 'device1')
        team_id = request.args.get('team_id')
        
        print(f"[@route:host_actions:action_execute_batch] Processing {len(actions)} actions for device: {device_id}, team: {team_id}")
        
        # Validate
        if not actions:
            return jsonify({'success': False, 'error': 'actions are required'}), 400
        if not device_id:
            return jsonify({'success': False, 'error': 'device_id is required'}), 400
        if not team_id:
            return jsonify({'success': False, 'error': 'team_id is required'}), 400
        
        # Get host device registry from app context
        host_devices = getattr(current_app, 'host_devices', {})
        if device_id not in host_devices:
            return jsonify({'success': False, 'error': f'Device {device_id} not found in host'}), 404
        
        device = host_devices[device_id]
        
        # Execute actions through orchestrator (unified architecture)
        result = ExecutionOrchestrator.execute_actions(
            device=device,
            actions=actions,
            retry_actions=retry_actions,
            failure_actions=failure_actions,
            team_id=team_id
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        print(f"[@route:host_actions:action_execute_batch] Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@host_actions_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for host action service"""
    return jsonify({
        'success': True,
        'message': 'Host action service is running'
    })
