"""Host Deployment Routes - Manage scheduled script executions"""
from flask import Blueprint, request, jsonify

host_deployment_bp = Blueprint('host_deployment', __name__, url_prefix='/host/deployment')

def get_deployment_scheduler():
    """Lazy import to avoid APScheduler dependency at module level"""
    try:
        from backend_host.src.services.deployment_scheduler import get_deployment_scheduler as _get_scheduler
        return _get_scheduler()
    except ImportError as e:
        print(f"[@host_deployment_routes] Warning: APScheduler not available: {e}")
        return None

@host_deployment_bp.route('/add', methods=['POST'])
def add_deployment():
    """Add new deployment to scheduler"""
    scheduler = get_deployment_scheduler()
    if not scheduler:
        return jsonify({'success': False, 'error': 'Scheduler not available'}), 503
    
    data = request.get_json()
    try:
        scheduler.add_deployment(data)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@host_deployment_bp.route('/pause/<deployment_id>', methods=['POST'])
def pause_deployment(deployment_id):
    """Pause deployment"""
    scheduler = get_deployment_scheduler()
    if not scheduler:
        return jsonify({'success': False, 'error': 'Scheduler not available'}), 503
    
    try:
        scheduler.pause_deployment(deployment_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@host_deployment_bp.route('/resume/<deployment_id>', methods=['POST'])
def resume_deployment(deployment_id):
    """Resume deployment"""
    scheduler = get_deployment_scheduler()
    if not scheduler:
        return jsonify({'success': False, 'error': 'Scheduler not available'}), 503
    
    try:
        scheduler.resume_deployment(deployment_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@host_deployment_bp.route('/remove/<deployment_id>', methods=['DELETE'])
def remove_deployment(deployment_id):
    """Remove deployment"""
    scheduler = get_deployment_scheduler()
    if not scheduler:
        return jsonify({'success': False, 'error': 'Scheduler not available'}), 503
    
    try:
        scheduler.remove_deployment(deployment_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@host_deployment_bp.route('/status', methods=['GET'])
def deployment_status():
    """Check if deployment scheduler is available"""
    scheduler = get_deployment_scheduler()
    return jsonify({
        'available': scheduler is not None,
        'message': 'Deployment scheduler ready' if scheduler else 'APScheduler dependency missing'
    })

