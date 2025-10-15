"""Host Deployment Routes - Manage scheduled script executions"""
from flask import Blueprint, request, jsonify
from backend_host.src.services.deployment_scheduler import get_deployment_scheduler

host_deployment_bp = Blueprint('host_deployment', __name__, url_prefix='/host/deployment')

@host_deployment_bp.route('/add', methods=['POST'])
def add_deployment():
    data = request.get_json()
    scheduler = get_deployment_scheduler()
    scheduler.add_deployment(data)
    return jsonify({'success': True})

@host_deployment_bp.route('/pause/<deployment_id>', methods=['POST'])
def pause_deployment(deployment_id):
    scheduler = get_deployment_scheduler()
    scheduler.pause_deployment(deployment_id)
    return jsonify({'success': True})

@host_deployment_bp.route('/resume/<deployment_id>', methods=['POST'])
def resume_deployment(deployment_id):
    scheduler = get_deployment_scheduler()
    scheduler.resume_deployment(deployment_id)
    return jsonify({'success': True})

@host_deployment_bp.route('/remove/<deployment_id>', methods=['DELETE'])
def remove_deployment(deployment_id):
    scheduler = get_deployment_scheduler()
    scheduler.remove_deployment(deployment_id)
    return jsonify({'success': True})

