"""
Event System REST API Routes

Provides HTTP endpoints for manual event triggering and event statistics.
"""

from flask import Blueprint, request, jsonify
import asyncio

from events import Event, EventPriority, get_event_bus
from events.event_router import EventRouter, get_event_router
from agent.async_utils import run_async

# Create blueprint
server_event_bp = Blueprint('server_events', __name__, url_prefix='/api/events')


def get_team_id() -> str:
    """Get team ID from request"""
    return request.headers.get('X-Team-ID', 'default')


@server_event_bp.route('/publish', methods=['POST'])
def publish_event():
    """
    Manually publish an event
    
    Body:
        - type: Event type (required)
        - payload: Event payload (required)
        - priority: Priority level (optional, default: normal)
    """
    try:
        data = request.get_json()
        
        if not data or 'type' not in data or 'payload' not in data:
            return jsonify({'error': 'type and payload required'}), 400
        
        team_id = data.get('team_id', get_team_id())
        
        # Parse priority
        priority_str = data.get('priority', 'normal').upper()
        try:
            priority = EventPriority[priority_str]
        except KeyError:
            priority = EventPriority.NORMAL
        
        # Create event
        event = Event(
            type=data['type'],
            payload=data['payload'],
            priority=priority,
            team_id=team_id
        )
        
        # Publish via router
        router = get_event_router()
        success = run_async(router.route_event(event))
        
        return jsonify({
            'event_id': event.id,
            'routed': success,
            'message': 'Event published successfully'
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@server_event_bp.route('/types', methods=['GET'])
def list_event_types():
    """List all event types seen in the system"""
    try:
        team_id = get_team_id()
        
        router = get_event_router()
        event_types = run_async(router.get_event_types(team_id))
        
        return jsonify({
            'event_types': event_types,
            'count': len(event_types)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@server_event_bp.route('/stats', methods=['GET'])
def get_event_stats():
    """Get event routing statistics"""
    try:
        team_id = get_team_id()
        
        router = get_event_router()
        stats = run_async(router.get_routing_stats(team_id))
        
        return jsonify(stats), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Alert event shortcuts
@server_event_bp.route('/alerts/blackscreen', methods=['POST'])
def emit_blackscreen_alert():
    """
    Emit blackscreen alert event
    
    Body:
        - device_id: Device identifier (required)
    """
    try:
        data = request.get_json()
        
        if not data or 'device_id' not in data:
            return jsonify({'error': 'device_id required'}), 400
        
        team_id = data.get('team_id', get_team_id())
        
        event = Event(
            type="alert.blackscreen",
            payload={
                "device_id": data['device_id'],
                "severity": "critical"
            },
            priority=EventPriority.CRITICAL,
            team_id=team_id
        )
        
        router = get_event_router()
        success = run_async(router.route_event(event))
        
        return jsonify({
            'event_id': event.id,
            'routed': success,
            'message': 'Blackscreen alert published'
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@server_event_bp.route('/alerts/device-offline', methods=['POST'])
def emit_device_offline_alert():
    """
    Emit device offline alert event
    
    Body:
        - device_id: Device identifier (required)
        - duration_seconds: Offline duration (optional)
    """
    try:
        data = request.get_json()
        
        if not data or 'device_id' not in data:
            return jsonify({'error': 'device_id required'}), 400
        
        team_id = data.get('team_id', get_team_id())
        
        event = Event(
            type="alert.device_offline",
            payload={
                "device_id": data['device_id'],
                "duration_seconds": data.get('duration_seconds', 300),
                "severity": "high"
            },
            priority=EventPriority.HIGH,
            team_id=team_id
        )
        
        router = get_event_router()
        success = run_async(router.route_event(event))
        
        return jsonify({
            'event_id': event.id,
            'routed': success,
            'message': 'Device offline alert published'
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Build event shortcuts
@server_event_bp.route('/builds/deployed', methods=['POST'])
def emit_build_deployed():
    """
    Emit build deployed event
    
    Body:
        - version: Build version (required)
        - userinterface: UI name (required)
        - environment: Environment (optional, default: staging)
    """
    try:
        data = request.get_json()
        
        if not data or 'version' not in data or 'userinterface' not in data:
            return jsonify({'error': 'version and userinterface required'}), 400
        
        team_id = data.get('team_id', get_team_id())
        
        event = Event(
            type="build.deployed",
            payload={
                "version": data['version'],
                "userinterface": data['userinterface'],
                "environment": data.get('environment', 'staging')
            },
            priority=EventPriority.HIGH,
            team_id=team_id
        )
        
        router = get_event_router()
        success = run_async(router.route_event(event))
        
        return jsonify({
            'event_id': event.id,
            'routed': success,
            'message': 'Build deployed event published'
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

