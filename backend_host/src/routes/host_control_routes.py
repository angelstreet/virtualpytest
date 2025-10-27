"""
Host Control Routes

This module contains host-side control endpoints that:
- Handle controller status checking on host devices
- Manage local device control operations
- Execute device-specific control commands
- Use stored host_device objects for controller access
"""

from flask import Blueprint, request, jsonify, current_app
from  backend_host.src.lib.utils.host_utils import get_controller, get_device_by_id, list_available_devices

# Create blueprint
host_control_bp = Blueprint('host_control', __name__, url_prefix='/host')

# =====================================================
# HOST-SIDE DEVICE CONTROL ENDPOINTS
# =====================================================

@host_control_bp.route('/takeControl', methods=['POST'])
def take_control():
    """Host-side take control - Check controllers AND rebuild navigation cache"""
    try:
        data = request.get_json() or {}
        device_id = data.get('device_id', 'default')
        tree_id = data.get('tree_id')  # Optional: tree_id for navigation cache
        team_id = request.args.get('team_id')  # team_id from query params
        
        print(f"[@route:take_control] Host checking controllers for device: {device_id}, tree_id: {tree_id}")
        
        # Check AV controller
        av_available = False
        try:
            av_controller = get_controller(device_id, 'av')
            
            if av_controller:
                print(f"[@route:take_control] Using AV controller: {type(av_controller).__name__}")
                av_status = av_controller.get_status()
                print(f"[@route:take_control] AV controller status: {av_status}")
                av_available = av_status.get('success', False)
            else:
                print(f"[@route:take_control] ⚠️ WARNING: No AV controller found for device {device_id}")
            
        except Exception as e:
            print(f"[@route:take_control] ⚠️ WARNING: AV controller error: {e}")
        
        # Check remote controller
        remote_available = False
        try:
            remote_controller = get_controller(device_id, 'remote')
            
            if remote_controller:
                controller_type = type(remote_controller).__name__
                print(f"[@route:take_control] Using remote controller: {controller_type}")
                
                if controller_type == 'AppiumRemoteController':
                    print(f"[@route:take_control] Appium controller - checking server status only")
                    remote_status = remote_controller.get_status()
                    remote_available = remote_status.get('success', False)
                    print(f"[@route:take_control] Appium server status: {remote_status}")
                else:
                    if not remote_controller.is_connected:
                        print(f"[@route:take_control] Connecting remote controller to device...")
                        connection_success = remote_controller.connect()
                        remote_available = connection_success
                    else:
                        print(f"[@route:take_control] Remote controller already connected")
                        remote_available = True
                    
                    if remote_available:
                        remote_status = remote_controller.get_status()
                        print(f"[@route:take_control] Remote controller status: {remote_status}")
                        remote_available = remote_status.get('success', False)
            else:
                print(f"[@route:take_control] ⚠️ WARNING: No remote controller found for device {device_id}")
                    
        except Exception as e:
            print(f"[@route:take_control] ⚠️ WARNING: Remote controller error: {e}")
        
        # Build list of available controllers
        available_controllers = []
        if av_available:
            available_controllers.append('av')
        if remote_available:
            available_controllers.append('remote')
        
        # ALWAYS succeed - just warn if no controllers available (needed for localhost testing)
        if not av_available and not remote_available:
            print(f"[@route:take_control] ⚠️ WARNING: No controllers available for device {device_id}, but allowing control for localhost testing")
        
        # REBUILD NAVIGATION CACHE if tree_id provided
        if tree_id and team_id:
            print(f"[@route:take_control] 🔨 Rebuilding navigation cache for tree {tree_id}")
            try:
                # STEP 1: Clear cache
                from backend_host.src.lib.utils.navigation_cache import clear_unified_cache
                clear_unified_cache(tree_id, team_id)
                print(f"[@route:take_control] ✅ Cache cleared")
                
                # STEP 2: Load tree data from database
                from shared.src.lib.database.navigation_trees_db import get_complete_tree_hierarchy, get_full_tree
                
                hierarchy_result = get_complete_tree_hierarchy(tree_id, team_id)
                if hierarchy_result.get('success'):
                    all_trees_data = hierarchy_result.get('all_trees_data', [])
                    print(f"[@route:take_control] Loaded tree hierarchy: {len(all_trees_data)} trees")
                else:
                    # Fallback: Load single tree
                    tree_result = get_full_tree(tree_id, team_id)
                    if tree_result.get('success'):
                        all_trees_data = [tree_result.get('tree')]
                        print(f"[@route:take_control] Loaded single tree")
                    else:
                        print(f"[@route:take_control] ⚠️ Failed to load tree data: {tree_result.get('error')}")
                        all_trees_data = None
                
                # STEP 3: Rebuild cache
                if all_trees_data:
                    from backend_host.src.lib.utils.navigation_cache import populate_unified_cache
                    unified_graph = populate_unified_cache(tree_id, team_id, all_trees_data)
                    
                    if unified_graph:
                        print(f"[@route:take_control] ✅ Cache rebuilt: {len(unified_graph.nodes)} nodes, {len(unified_graph.edges)} edges")
                    else:
                        print(f"[@route:take_control] ⚠️ Cache rebuild failed")
            except Exception as cache_error:
                print(f"[@route:take_control] ⚠️ Cache rebuild error (non-critical): {cache_error}")
        
        print(f"[@route:take_control] SUCCESS: Take control succeeded for device: {device_id} with controllers: {available_controllers}")
        return jsonify({
            'success': True,
            'available_controllers': available_controllers
        })
            
    except Exception as e:
        print(f"[@route:take_control] FAILED: Take control failed with error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@host_control_bp.route('/releaseControl', methods=['POST'])
def release_control():
    """Host-side release control"""
    try:
        print(f"[@route:release_control] Host releasing control using own stored host_device")
        
        host_device = getattr(current_app, 'my_host_device', None)
        
        if not host_device:
            print(f"[@route:release_control] No host_device found, assuming already released")
            return jsonify({'success': True})
        
        if not isinstance(host_device, dict):
            return jsonify({
                'success': False,
                'error': 'Host device object invalid'
            }), 500
            
        print(f"[@route:release_control] Host device releasing controllers")
        
        return jsonify({'success': True})
            
    except Exception as e:
        print(f"[@route:release_control] Error releasing control: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@host_control_bp.route('/devices', methods=['GET'])
def list_devices():
    """List all available devices on this host"""
    try:
        print(f"[@route:list_devices] Getting available devices")
        
        host_device = getattr(current_app, 'my_host_device', None)
        
        if not host_device:
            return jsonify({
                'success': False,
                'error': 'Host device object not initialized'
            })
        
        # Get devices from host configuration
        devices = host_device.get('devices', [])
        
        if not devices:
            device_info = {
                'device_id': 'default',
                'device_name': host_device.get('device_name', 'Unknown Device'),
                'device_model': host_device.get('device_model', 'unknown'),
                'device_ip': host_device.get('device_ip'),
                'device_port': host_device.get('device_port'),
                'video_device': None,
                'video_stream_path': None,
                'video_capture_path': None
            }
            devices = [device_info]
        
        # Get available controller types for each device
        available_device_ids = list_available_devices()
        
        for device in devices:
            device_id = device.get('device_id')
            device['controllers'] = {}
            device['controller_status'] = 'unknown'
            
            # Check if controllers exist for this device
            if device_id in available_device_ids or device_id == 'default':
                # Check AV controller
                av_controller = get_controller(device_id, 'av')
                if av_controller:
                    device['controllers']['av'] = {
                        'available': True,
                        'type': type(av_controller).__name__
                    }
                
                # Check remote controller
                remote_controller = get_controller(device_id, 'remote')
                if remote_controller:
                    device['controllers']['remote'] = {
                        'available': True,
                        'type': type(remote_controller).__name__
                    }
                
                # Check verification controller
                verification_controller = get_controller(device_id, 'verification')
                if verification_controller:
                    device['controllers']['verification'] = {
                        'available': True,
                        'type': type(verification_controller).__name__
                    }
                
                # Check power controller
                power_controller = get_controller(device_id, 'power')
                if power_controller:
                    device['controllers']['power'] = {
                        'available': True,
                        'type': type(power_controller).__name__
                    }
                
                device['controller_status'] = 'ready' if device['controllers'] else 'no_controllers'
            else:
                device['controller_status'] = 'not_registered'
        
        return jsonify({
            'success': True,
            'devices': devices
        })
        
    except Exception as e:
        print(f"[@route:list_devices] Error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@host_control_bp.route('/controllerStatus', methods=['GET'])
def controller_status():
    """Get status of all controllers on this host"""
    try:
        print(f"[@route:controller_status] Getting controller status")
        
        host_device = getattr(current_app, 'my_host_device', None)
        
        if not host_device:
            return jsonify({
                'success': False,
                'error': 'Host device object not initialized'
            })
        
        if not isinstance(host_device, dict):
            return jsonify({
                'success': False,
                'error': 'Host device object invalid'
            }), 500
            
        controller_status = {}
        controller_objects = host_device.get('controller_objects', {})
        
        # Check each controller
        for controller_name, controller_obj in controller_objects.items():
            try:
                if hasattr(controller_obj, 'get_status'):
                    status = controller_obj.get_status()
                    controller_status[controller_name] = {
                        'available': True,
                        'status': status,
                        'type': type(controller_obj).__name__
                    }
                else:
                    controller_status[controller_name] = {
                        'available': True,
                        'status': {'message': 'No status method available'},
                        'type': type(controller_obj).__name__
                    }
            except Exception as e:
                controller_status[controller_name] = {
                    'available': False,
                    'error': str(e),
                    'type': type(controller_obj).__name__
                }
        
        return jsonify({
            'success': True,
            'controllers': controller_status
        })
        
    except Exception as e:
        print(f"[@route:controller_status] Error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
