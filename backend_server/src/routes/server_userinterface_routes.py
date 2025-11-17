"""
User Interface Management Routes

This module contains the user interface management API endpoints for:
- User interfaces management
- Device compatibility management
"""

import time
import threading
from flask import Blueprint, request, jsonify

# Import database functions from src/lib/supabase (uses absolute import)
from shared.src.lib.database.userinterface_db import (
    get_all_userinterfaces, 
    get_userinterface, 
    get_userinterface_by_name,
    create_userinterface, 
    delete_userinterface,
    update_userinterface,
    check_userinterface_name_exists
)
from shared.src.lib.database.navigation_trees_db import (
    get_root_tree_for_interface,
    get_tree_nodes
)

from shared.src.lib.utils.app_utils import check_supabase
from shared.src.lib.config.constants import CACHE_CONFIG

# Create blueprint
server_userinterface_bp = Blueprint('server_userinterface', __name__, url_prefix='/server/userinterface')

# ============================================================================
# IN-MEMORY CACHE FOR COMPATIBLE INTERFACES AND ALL INTERFACES
# ============================================================================
_compatible_cache = {}  # {cache_key: {'data': {...}, 'timestamp': time.time()}}
_interfaces_cache = {}  # {team_id: {'data': [...], 'timestamp': time.time()}}
_cache_lock = threading.Lock()

def _invalidate_interfaces_cache(team_id):
    """Invalidate all user interface caches for a specific team"""
    with _cache_lock:
        # Invalidate the main interfaces cache
        if team_id in _interfaces_cache:
            del _interfaces_cache[team_id]
            print(f"[@cache] INVALIDATE: User interfaces for team {team_id}")
        
        # Invalidate all compatible interfaces cache entries for this team
        keys_to_delete = [key for key in _compatible_cache.keys() if key.startswith(f"{team_id}:")]
        for key in keys_to_delete:
            del _compatible_cache[key]
            print(f"[@cache] INVALIDATE: Compatible interfaces cache key {key}")

# =====================================================
# USER INTERFACES ENDPOINTS
# =====================================================

@server_userinterface_bp.route('/getCompatibleInterfaces', methods=['GET'])
def get_compatible_interfaces():
    """Get user interfaces compatible with a specific device model"""
    error = check_supabase()
    if error:
        return error
        
    team_id = request.args.get('team_id')
    device_model = request.args.get('device_model')
    
    if not device_model:
        return jsonify({'success': False, 'error': 'device_model parameter required'}), 400
    
    # Create cache key from device_model and team_id
    cache_key = f"{team_id}:{device_model}"
    
    # Check cache first
    with _cache_lock:
        if cache_key in _compatible_cache:
            cached = _compatible_cache[cache_key]
            age = time.time() - cached['timestamp']
            # Use UI_TTL (60 seconds) for compatible interfaces
            if age < CACHE_CONFIG['UI_TTL']:
                print(f"[@cache] HIT: Compatible interfaces for {device_model} (age: {age/60:.1f}m)")
                return jsonify(cached['data'])
            else:
                del _compatible_cache[cache_key]
    
    try:
        # Get all interfaces for the team
        all_interfaces = get_all_userinterfaces(team_id)
        
        # Map host_vnc to also be compatible with web and desktop interfaces
        compatible_models = [device_model]
        if device_model == 'host_vnc':
            compatible_models.extend(['web', 'desktop'])
            print(f"[@server_userinterface] host_vnc device - also checking for web and desktop interfaces")
        
        # Filter to compatible ones (where device_model OR mapped models are in the models array)
        compatible_interfaces = [
            interface for interface in all_interfaces
            if any(model in (interface.get('models') or []) for model in compatible_models)
        ]
        
        response_data = {
            'success': True,
            'interfaces': compatible_interfaces,
            'device_model': device_model,
            'count': len(compatible_interfaces)
        }
        
        # Store in cache
        with _cache_lock:
            _compatible_cache[cache_key] = {
                'data': response_data,
                'timestamp': time.time()
            }
            print(f"[@cache] SET: Compatible interfaces for {device_model} ({CACHE_CONFIG['UI_TTL']}s TTL)")
        
        return jsonify(response_data)
    except Exception as e:
        print(f"[@server_userinterface] Error getting compatible interfaces: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@server_userinterface_bp.route('/getAllUserInterfaces', methods=['GET'])
def get_userinterfaces():
    """Get all user interfaces for the team"""
    error = check_supabase()
    if error:
        return error
        
    team_id = request.args.get('team_id')
    force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'
    
    print(f"[@userinterface:getAllUserInterfaces] Request for team_id: {team_id}, force_refresh: {force_refresh}")
    
    # Check cache first (unless force_refresh)
    if not force_refresh:
        with _cache_lock:
            if team_id in _interfaces_cache:
                cached = _interfaces_cache[team_id]
                age = time.time() - cached['timestamp']
                # Use MEDIUM_TTL (5 minutes) for user interfaces instead of LONG_TTL (24 hours)
                # User interfaces metadata is relatively stable but can change when trees are modified
                if age < CACHE_CONFIG['MEDIUM_TTL']:
                    print(f"[@cache] HIT: User interfaces for team {team_id} (age: {age/60:.1f}m), returning {len(cached['data'])} interfaces")
                    return jsonify(cached['data'])
                else:
                    del _interfaces_cache[team_id]
                    print(f"[@cache] EXPIRED: User interfaces cache for team {team_id}")
    else:
        print(f"[@cache] BYPASS: Force refresh requested for team {team_id}")
    
    try:
        interfaces = get_all_userinterfaces(team_id)
        print(f"[@userinterface] Retrieved {len(interfaces)} interfaces from database")
        
        # Enrich interfaces with root tree information (only if tree has nodes)
        enriched_interfaces = []
        for interface in interfaces:
            try:
                interface_id = interface.get('id')
                if interface_id:
                    # Fetch root tree for this interface
                    root_tree = get_root_tree_for_interface(interface_id, team_id)
                    if root_tree:
                        # Check if tree actually has nodes (not just empty metadata)
                        try:
                            nodes_result = get_tree_nodes(root_tree['id'], team_id, page=0, limit=1)
                            nodes = nodes_result.get('nodes', []) if nodes_result else []
                            if nodes and len(nodes) > 0:
                                # Only add root_tree if it has actual nodes
                                interface['root_tree'] = root_tree
                                print(f"[@userinterface] Interface '{interface.get('name')}' has tree with nodes")
                            else:
                                print(f"[@userinterface] Interface '{interface.get('name')}' has tree but no nodes")
                        except Exception as e:
                            print(f"[@userinterface] Error checking nodes for interface '{interface.get('name')}': {e}")
                            # Continue without tree info if nodes check fails
            except Exception as e:
                print(f"[@userinterface] Error enriching interface: {e}")
                # Continue with next interface
            
            # Always append the interface, even if enrichment failed
            enriched_interfaces.append(interface)
        
        # Store in cache
        with _cache_lock:
            _interfaces_cache[team_id] = {
                'data': enriched_interfaces,
                'timestamp': time.time()
            }
            print(f"[@cache] SET: User interfaces for team {team_id} ({len(enriched_interfaces)} interfaces, 5m TTL)")
        
        print(f"[@userinterface:getAllUserInterfaces] Returning {len(enriched_interfaces)} interfaces")
        return jsonify(enriched_interfaces)
    except Exception as e:
        print(f"[@userinterface:getAllUserInterfaces] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@server_userinterface_bp.route('/createUserInterface', methods=['POST'])
def create_userinterface_route():
    """Create a new user interface"""
    error = check_supabase()
    if error:
        return error
        
    team_id = request.args.get('team_id')
    
    try:
        interface_data = request.json
        
        # Validate required fields
        if not interface_data.get('name'):
            return jsonify({'error': 'Name is required'}), 400
        
        if not interface_data.get('models') or len(interface_data.get('models', [])) == 0:
            return jsonify({'error': 'At least one model must be selected'}), 400
        
        # Check for duplicate names
        if check_userinterface_name_exists(interface_data['name'], team_id):
            return jsonify({'error': 'A user interface with this name already exists'}), 400
        
        # Create the user interface
        created_interface = create_userinterface(interface_data, team_id)
        if created_interface:
            # Invalidate cache after successful creation
            _invalidate_interfaces_cache(team_id)
            return jsonify({'status': 'success', 'userinterface': created_interface}), 201
        else:
            return jsonify({'error': 'Failed to create user interface'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@server_userinterface_bp.route('/getUserInterface/<interface_id>', methods=['GET'])
def get_userinterface_route(interface_id):
    """Get a specific user interface by ID"""
    error = check_supabase()
    if error:
        return error
        
    team_id = request.args.get('team_id')
    
    try:
        interface = get_userinterface(interface_id, team_id)
        if interface:
            # Enrich with root tree information
            root_tree = get_root_tree_for_interface(interface_id, team_id)
            if root_tree:
                interface['root_tree'] = root_tree
            return jsonify(interface)
        else:
            return jsonify({'error': 'User interface not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@server_userinterface_bp.route('/getUserInterfaceByName/<interface_name>', methods=['GET'])
def get_userinterface_by_name_route(interface_name):
    """Get a specific user interface by name (for navigation editor)"""
    error = check_supabase()
    if error:
        return error
        
    team_id = request.args.get('team_id')
    
    try:
        interface = get_userinterface_by_name(interface_name, team_id)
        if interface:
            return jsonify(interface)
        else:
            return jsonify({'error': 'User interface not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@server_userinterface_bp.route('/updateUserInterface/<interface_id>', methods=['PUT'])
def update_userinterface_route(interface_id):
    """Update a specific user interface"""
    error = check_supabase()
    if error:
        return error
        
    team_id = request.args.get('team_id')
    
    try:
        interface_data = request.json
        
        # Validate required fields
        if not interface_data.get('name'):
            return jsonify({'error': 'Name is required'}), 400
        
        if not interface_data.get('models') or len(interface_data.get('models', [])) == 0:
            return jsonify({'error': 'At least one model must be selected'}), 400
        
        # Check for duplicate names (excluding current interface)
        if check_userinterface_name_exists(interface_data['name'], team_id, interface_id):
            return jsonify({'error': 'A user interface with this name already exists'}), 400
        
        # Update the user interface
        updated_interface = update_userinterface(interface_id, interface_data, team_id)
        if updated_interface:
            # Invalidate cache after successful update
            _invalidate_interfaces_cache(team_id)
            return jsonify({'status': 'success', 'userinterface': updated_interface})
        else:
            return jsonify({'error': 'User interface not found or failed to update'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@server_userinterface_bp.route('/deleteUserInterface/<interface_id>', methods=['DELETE'])
def delete_userinterface_route(interface_id):
    """Delete a specific user interface"""
    error = check_supabase()
    if error:
        return error
        
    team_id = request.args.get('team_id')
    
    try:
        success = delete_userinterface(interface_id, team_id)
        if success:
            # Invalidate cache after successful deletion
            _invalidate_interfaces_cache(team_id)
            return jsonify({'status': 'success'})
        else:
            return jsonify({'error': 'User interface not found or failed to delete'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500 