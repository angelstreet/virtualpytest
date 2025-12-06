"""
Agent Runtime REST API Routes

Provides HTTP endpoints for agent instance management, status, and control.
"""

from flask import Blueprint, request, jsonify
from typing import Optional
import asyncio

from agent.runtime import AgentRuntime, get_agent_runtime
from events import get_event_bus
from agent.async_utils import run_async

# Create blueprint
server_agent_runtime_bp = Blueprint('server_agent_runtime', __name__, url_prefix='/api/runtime')


def get_team_id() -> str:
    """Get team ID from request"""
    return request.headers.get('X-Team-ID', 'default')


@server_agent_runtime_bp.route('/instances', methods=['GET'])
def list_instances():
    """
    List all running agent instances
    
    Query params:
        - team_id: Filter by team
    """
    try:
        team_id = request.args.get('team_id', get_team_id())
        
        runtime = get_agent_runtime()
        instances = runtime.list_instances(team_id)
        
        return jsonify({
            'instances': instances,
            'count': len(instances)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@server_agent_runtime_bp.route('/instances/<instance_id>', methods=['GET'])
def get_instance_status(instance_id: str):
    """Get status of specific agent instance"""
    try:
        runtime = get_agent_runtime()
        status = runtime.get_status(instance_id)
        
        if not status:
            return jsonify({'error': 'Instance not found'}), 404
        
        return jsonify(status), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@server_agent_runtime_bp.route('/instances/start', methods=['POST'])
def start_agent_instance():
    """
    Start new agent instance
    
    Body:
        - agent_id: Agent to start (required)
        - version: Version (optional, defaults to latest)
        - team_id: Team namespace (optional)
    """
    try:
        data = request.get_json()
        
        if not data or 'agent_id' not in data:
            return jsonify({'error': 'agent_id required'}), 400
        
        agent_id = data['agent_id']
        version = data.get('version')
        team_id = data.get('team_id', get_team_id())
        
        runtime = get_agent_runtime()
        
        # Start runtime if not running
        if not runtime._running:
            run_async(runtime.start())
        
        # Start agent
        instance_id = run_async(
            runtime.start_agent(agent_id, version, team_id)
        )
        
        return jsonify({
            'instance_id': instance_id,
            'message': 'Agent started successfully'
        }), 201
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@server_agent_runtime_bp.route('/instances/<instance_id>/stop', methods=['POST'])
def stop_agent_instance(instance_id: str):
    """Stop agent instance"""
    try:
        runtime = get_agent_runtime()
        success = run_async(runtime.stop_agent(instance_id))
        
        if success:
            return jsonify({'message': 'Agent stopped successfully'}), 200
        else:
            return jsonify({'error': 'Instance not found'}), 404
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@server_agent_runtime_bp.route('/instances/<instance_id>/pause', methods=['POST'])
def pause_agent_instance(instance_id: str):
    """Pause agent instance (placeholder)"""
    # TODO: Implement pause/resume logic
    return jsonify({'error': 'Not implemented yet'}), 501


@server_agent_runtime_bp.route('/instances/<instance_id>/resume', methods=['POST'])
def resume_agent_instance(instance_id: str):
    """Resume paused agent instance (placeholder)"""
    # TODO: Implement pause/resume logic
    return jsonify({'error': 'Not implemented yet'}), 501


@server_agent_runtime_bp.route('/start', methods=['POST'])
def start_runtime():
    """Start the agent runtime system"""
    try:
        runtime = get_agent_runtime()
        
        if runtime._running:
            return jsonify({'message': 'Runtime already running'}), 200
        
        run_async(runtime.start())
        
        return jsonify({'message': 'Runtime started successfully'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@server_agent_runtime_bp.route('/stop', methods=['POST'])
def stop_runtime():
    """Stop the agent runtime system"""
    try:
        runtime = get_agent_runtime()
        
        if not runtime._running:
            return jsonify({'message': 'Runtime not running'}), 200
        
        run_async(runtime.stop())
        
        return jsonify({'message': 'Runtime stopped successfully'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@server_agent_runtime_bp.route('/status', methods=['GET'])
def get_runtime_status():
    """Get overall runtime status"""
    try:
        runtime = get_agent_runtime()
        event_bus = get_event_bus()
        
        return jsonify({
            'running': runtime._running,
            'total_instances': len(runtime.instances),
            'active_tasks': len(runtime.tasks),
            'event_bus_connected': event_bus.redis_client is not None
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# WebSocket endpoint for real-time status updates
# Note: This would require additional WebSocket support
# For now, clients can poll the status endpoints

