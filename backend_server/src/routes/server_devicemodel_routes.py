"""
Device Model Routes (Server-Only)

API endpoints for device model management operations.
"""

from flask import Blueprint, request, jsonify
import json
import time
import threading

# Import database functions from src/lib/supabase (uses absolute import)
from shared.src.lib.database.device_models_db import (
    get_all_device_models,
    get_device_model,
    create_device_model,
    update_device_model, 
    delete_device_model,
    check_device_model_name_exists
)

from shared.src.lib.utils.app_utils import check_supabase
from shared.src.lib.config.constants import CACHE_CONFIG

# Create blueprint
server_devicemodel_bp = Blueprint('server_devicemodel', __name__, url_prefix='/server/devicemodel')

# ============================================================================
# IN-MEMORY CACHE FOR DEVICE MODELS
# ============================================================================
_models_cache = {}  # {team_id: {'data': [...], 'timestamp': time.time()}}
_cache_lock = threading.Lock()

def _invalidate_models_cache(team_id):
    """Invalidate the device models cache for a specific team"""
    with _cache_lock:
        if team_id in _models_cache:
            del _models_cache[team_id]
            print(f"[@cache] INVALIDATE: Device models for team {team_id}")

# =====================================================
# DEVICE MODELS ENDPOINTS
# =====================================================

@server_devicemodel_bp.route('/getAllModels', methods=['GET'])
def get_device_models():
    """Get all device models for the team"""
    error = check_supabase()
    if error:
        return error
        
    team_id = request.args.get('team_id')
    
    # Check cache first
    with _cache_lock:
        if team_id in _models_cache:
            cached = _models_cache[team_id]
            age = time.time() - cached['timestamp']
            if age < CACHE_CONFIG['LONG_TTL']:
                print(f"[@cache] HIT: Device models for team {team_id} (age: {age/3600:.1f}h)")
                return jsonify(cached['data'])
            else:
                del _models_cache[team_id]
    
    try:
        models = get_all_device_models(team_id)
        
        # Store in cache
        with _cache_lock:
            _models_cache[team_id] = {
                'data': models,
                'timestamp': time.time()
            }
            print(f"[@cache] SET: Device models for team {team_id} (24h TTL)")
        
        return jsonify(models)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@server_devicemodel_bp.route('/createDeviceModel', methods=['POST'])
def create_device_model_endpoint():
    """Create a new device model"""
    error = check_supabase()
    if error:
        return error
        
    team_id = request.args.get('team_id')
    
    try:
        model_data = request.json
        
        # Validate required fields
        if not model_data.get('name'):
            return jsonify({'error': 'Name is required'}), 400
        
        if not model_data.get('types') or len(model_data.get('types', [])) == 0:
            return jsonify({'error': 'At least one type must be selected'}), 400
        
        # Check for duplicate names
        if check_device_model_name_exists(model_data['name'], team_id):
            return jsonify({'error': 'A device model with this name already exists'}), 400
        
        # Create the device model
        created_model = create_device_model(model_data, team_id)
        if created_model:
            # Invalidate cache after successful creation
            _invalidate_models_cache(team_id)
            return jsonify({'status': 'success', 'model': created_model}), 201
        else:
            return jsonify({'error': 'Failed to create device model'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@server_devicemodel_bp.route('/getDeviceModel/<model_id>', methods=['GET'])
def get_device_model_endpoint(model_id):
    """Get a specific device model by ID"""
    error = check_supabase()
    if error:
        return error
        
    team_id = request.args.get('team_id')
    
    try:
        model = get_device_model(model_id, team_id)
        if model:
            return jsonify(model)
        else:
            return jsonify({'error': 'Device model not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@server_devicemodel_bp.route('/updateDeviceModel/<model_id>', methods=['PUT'])
def update_device_model_endpoint(model_id):
    """Update a specific device model"""
    error = check_supabase()
    if error:
        return error
        
    team_id = request.args.get('team_id')
    
    try:
        model_data = request.json
        
        # Validate required fields
        if not model_data.get('name'):
            return jsonify({'error': 'Name is required'}), 400
        
        if not model_data.get('types') or len(model_data.get('types', [])) == 0:
            return jsonify({'error': 'At least one type must be selected'}), 400
        
        # Check for duplicate names (excluding current model)
        if check_device_model_name_exists(model_data['name'], team_id, model_id):
            return jsonify({'error': 'A device model with this name already exists'}), 400
        
        # Update the device model
        updated_model = update_device_model(model_id, model_data, team_id)
        if updated_model:
            # Invalidate cache after successful update
            _invalidate_models_cache(team_id)
            return jsonify({'status': 'success', 'model': updated_model})
        else:
            return jsonify({'error': 'Device model not found or failed to update'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@server_devicemodel_bp.route('/deleteDeviceModel/<model_id>', methods=['DELETE'])
def delete_device_model_endpoint(model_id):
    """Delete a specific device model"""
    error = check_supabase()
    if error:
        return error
        
    team_id = request.args.get('team_id')
    
    try:
        success = delete_device_model(model_id, team_id)
        if success:
            # Invalidate cache after successful deletion
            _invalidate_models_cache(team_id)
            return jsonify({'status': 'success'})
        else:
            return jsonify({'error': 'Device model not found or failed to delete'}), 404
    except ValueError as ve:
        # Handle default model deletion attempt
        return jsonify({'error': str(ve)}), 403
    except Exception as e:
        return jsonify({'error': str(e)}), 500 