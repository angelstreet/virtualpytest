"""
Server Control Routes

This module contains server-side control endpoints that:
- Handle device locking and unlocking on server side
- Coordinate with hosts for device control operations
- Forward requests to appropriate hosts
- Manage device registry and host discovery
- Provide controller type information
"""

from flask import Blueprint, request, jsonify, session
import uuid
import json
import requests
import time
import threading
from datetime import datetime
from typing import Dict, Any, Optional

from shared.src.lib.utils.build_url_utils import buildHostUrl
from  backend_server.src.lib.utils.server_utils import get_host_manager
from  backend_server.src.lib.utils.lock_utils import lock_device, unlock_device, get_all_locked_devices, get_device_lock_info, get_client_ip
from  backend_server.src.lib.utils.route_utils import proxy_to_host_direct

# Create blueprint
server_control_bp = Blueprint('server_control', __name__, url_prefix='/server/control')

# =====================================================
# SERVER-SIDE DEVICE CONTROL ENDPOINTS
# =====================================================

@server_control_bp.route('/takeControl', methods=['POST'])
def take_control():
    """Take control of a device"""
    try:
        data = request.get_json()
        host_name = data.get('host_name')
        device_id = data.get('device_id')
        
        if not host_name:
            return jsonify({'error': 'host_name is required'}), 400
        
        
        # Generate session ID if not exists
        if 'session_id' not in session:
            session['session_id'] = str(uuid.uuid4())
        
        session_id = session['session_id']
        
        # Extract client IP address
        client_ip = get_client_ip()
        
        print(f"🎮 [CONTROL] Taking control of host: {host_name}, device: {device_id} (session: {session_id}, IP: {client_ip})")
        
        # Check if host is registered
        host_manager = get_host_manager()
        host_data = host_manager.get_host(host_name)
        if not host_data:
            return jsonify({
                'success': False,
                'error': f'Host {host_name} not found',
                'errorType': 'device_not_found'
            }), 404
        
        # Use lock utils for device locking (still lock by host_name for coordination)
        success = lock_device(host_name, session_id, client_ip)
        
        if success:
            # Forward take-control request to the specific host with device_id
            try:
                host_endpoint = '/host/takeControl'
                host_url = buildHostUrl(host_data, host_endpoint)
                
                print(f"📡 [CONTROL] Forwarding take-control to host: {host_url}")
                
                # Send device_id as provided, let host handle device ID mapping
                request_payload = {}
                if device_id:
                    request_payload['device_id'] = device_id
                
                response = requests.post(
                    host_url,
                    json=request_payload,
                    timeout=30
                )
                    
                if response.status_code == 200:
                    result = response.json()
                    if result.get('success'):
                        print(f"✅ [CONTROL] Host confirmed control of device: {device_id}")
                        
                        # Populate navigation cache for the controlled device
                        # Accept EITHER tree_id OR userinterface_id (resolve tree_id if needed)
                        # SYNCHRONOUS - blocks until cache is ready to prevent "cache not ready" errors
                        tree_id = data.get('tree_id')
                        userinterface_id = data.get('userinterface_id')
                        team_id = request.args.get('team_id') # team_id comes from buildServerUrl query params
                        
                        # Resolve tree_id from userinterface_id if provided
                        if userinterface_id and team_id and not tree_id:
                            print(f"🔍 [CONTROL] Resolving tree_id from userinterface_id: {userinterface_id}")
                            from shared.src.lib.database.navigation_trees_db import get_root_tree_for_interface
                            
                            tree = get_root_tree_for_interface(userinterface_id, team_id)
                            if tree:
                                tree_id = tree['id']
                                print(f"✅ [CONTROL] Resolved tree_id: {tree_id}")
                            else:
                                print(f"⚠️ [CONTROL] No tree found for userinterface_id: {userinterface_id}")
                        
                        if tree_id and team_id:
                            print(f"🗺️ [CONTROL] Populating navigation cache for tree: {tree_id}")
                            
                            cache_success = populate_navigation_cache_for_control(tree_id, team_id, host_name)
                            
                            if not cache_success:
                                # Cache population failed - unlock device and fail takeControl
                                print(f"❌ [CONTROL] Navigation cache population FAILED for tree: {tree_id}")
                                unlock_device(host_name, session_id)
                                return jsonify({
                                    'success': False,
                                    'error': f'Failed to populate navigation cache for tree {tree_id}. Check server logs for details.',
                                    'errorType': 'cache_error'
                                }), 500
                            
                            print(f"✅ [CONTROL] Navigation cache populated successfully")
                        
                        return jsonify({
                            'success': True,
                            'message': f'Successfully took control of host: {host_name}, device: {device_id}',
                            'session_id': session_id,
                            'host_name': host_name,
                            'device_id': device_id,
                            'host_result': result,
                            'cache_ready': True,
                            'warning': result.get('warning')  # Pass through warning from host (e.g., ADB connection failed)
                        })
                    else:
                        # Host rejected control - unlock and return error
                        unlock_device(host_name, session_id)
                        return jsonify({
                            'success': False,
                            'error': result.get('error', 'Host failed to take control'),
                            'errorType': result.get('error_type', 'host_error'),
                            'host_result': result
                        }), 500
                else:
                    # Host communication failed - unlock and return error  
                    unlock_device(host_name, session_id)
                    return jsonify({
                        'success': False,
                        'error': f'Host communication failed: {response.status_code}',
                        'errorType': 'network_error'
                    }), 500
                    
            except requests.exceptions.Timeout:
                unlock_device(host_name, session_id)
                return jsonify({
                    'success': False,
                    'error': 'Host communication timeout',
                    'errorType': 'network_error'
                }), 408
            except requests.exceptions.RequestException as e:
                unlock_device(host_name, session_id)
                return jsonify({
                    'success': False,
                    'error': f'Network error: {str(e)}',
                    'errorType': 'network_error'
                }), 500
        else:
            lock_info = get_device_lock_info(host_name)
            if lock_info:
                return jsonify({
                    'success': False,
                    'error': f'Host {host_name} is already locked by another session',
                    'errorType': 'device_locked',
                    'locked_by': lock_info.get('lockedBy'),
                    'locked_at': lock_info.get('lockedAt'),
                    'locked_ip': lock_info.get('lockedIp')
                }), 423  # HTTP 423 Locked
            else:
                return jsonify({
                    'success': False,
                    'error': f'Failed to lock host {host_name}',
                    'errorType': 'generic_error'
                }), 500
        
    except Exception as e:
        print(f"❌ [CONTROL] Error taking control: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@server_control_bp.route('/releaseControl', methods=['POST'])
def release_control():
    """Release control of a device (instant response, host notification in background)"""
    try:
        data = request.get_json()
        host_name = data.get('host_name')
        device_id = data.get('device_id')
        
        if not host_name:
            return jsonify({'error': 'host_name is required'}), 400
        
        session_id = session.get('session_id')
        
        print(f"🔓 [CONTROL] Releasing control of host: {host_name}, device: {device_id} (session: {session_id})")
        
        # 1. Release server lock IMMEDIATELY (critical - must be fast!)
        unlock_success = unlock_device(host_name, session_id)
        
        if not unlock_success:
            print(f"⚠️ [CONTROL] Failed to unlock device on server")
        
        # 2. Notify host in background (non-blocking - we don't wait for host)
        host_manager = get_host_manager()
        host_data = host_manager.get_host(host_name)
        if host_data:
            import threading
            
            def notify_host_async():
                """Background task to notify host of control release"""
                try:
                    host_endpoint = '/host/releaseControl'
                    host_url = buildHostUrl(host_data, host_endpoint)
                    
                    print(f"📡 [CONTROL:ASYNC] Notifying host of release: {host_url}")
                    
                    response = requests.post(
                        host_url,
                        json={'device_id': device_id},
                        timeout=10  # Reduced timeout for background task
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        print(f"✅ [CONTROL:ASYNC] Host confirmed release of device: {device_id}")
                    else:
                        print(f"⚠️ [CONTROL:ASYNC] Host responded with status {response.status_code}")
                        
                except Exception as e:
                    print(f"⚠️ [CONTROL:ASYNC] Host notification error: {e}")
            
            # Start host notification in background (non-blocking)
            threading.Thread(target=notify_host_async, daemon=True).start()
            print(f"🔓 [CONTROL] Server lock released, host notification in progress")
        else:
            print(f"⚠️ [CONTROL] Host {host_name} not found, but server lock released")
        
        # Return IMMEDIATELY after releasing server lock
        return jsonify({
            'success': unlock_success,
            'message': f'Control released for host: {host_name}, device: {device_id}',
            'host_notification': 'in_progress' if host_data else 'host_not_found'
        })
        
    except Exception as e:
        print(f"❌ [CONTROL] Error releasing control: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@server_control_bp.route('/checkLock', methods=['POST'])
def check_device_lock():
    """Check if a specific device is locked"""
    try:
        data = request.get_json()
        host_name = data.get('host_name')
        
        if not host_name:
            return jsonify({'error': 'host_name is required'}), 400
        
        lock_info = get_device_lock_info(host_name)
        
        if lock_info:
            return jsonify({
                'success': True,
                'is_locked': True,
                'lock_info': lock_info
            })
        else:
            return jsonify({
                'success': True,
                'is_locked': False,
                'lock_info': None
            })
        
    except Exception as e:
        print(f"❌ [CONTROL] Error checking device lock: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@server_control_bp.route('/lockedDevices', methods=['GET'])
def get_locked_devices():
    """Get information about all currently locked devices"""
    try:
        locked_devices = get_all_locked_devices()
        
        return jsonify({
            'success': True,
            'locked_devices': locked_devices
        })
        
    except Exception as e:
        print(f"❌ [CONTROL] Error getting locked devices: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@server_control_bp.route('/forceUnlock', methods=['POST'])
def force_unlock():
    """Force unlock a device (useful when user's IP changes or session is stuck)"""
    try:
        from backend_server.src.lib.utils.lock_utils import force_unlock_device
        
        data = request.get_json()
        host_name = data.get('host_name')
        
        if not host_name:
            return jsonify({'error': 'host_name is required'}), 400
        
        print(f"🔓 [CONTROL] Force unlocking device: {host_name}")
        
        success = force_unlock_device(host_name)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Successfully force unlocked device: {host_name}'
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Failed to force unlock device: {host_name}'
            }), 500
        
    except Exception as e:
        print(f"❌ [CONTROL] Error force unlocking device: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@server_control_bp.route('/navigation/execute', methods=['POST'])
def execute_navigation():
    """Execute navigation on a host device."""
    try:
        data = request.get_json()
        host_name = data.get('host_name')
        navigation_data = data.get('navigation_data')
        
        if not host_name:
            return jsonify({'error': 'host_name is required'}), 400
        
        if not navigation_data:
            return jsonify({'error': 'Navigation data is required'}), 400
        
        
        print(f"🧭 [NAVIGATION] Executing navigation on host: {host_name}")
        print(f"   Navigation data keys: {list(navigation_data.keys())}")
        
        # Check if host is registered
        host_manager = get_host_manager()
        host_data = host_manager.get_host(host_name)
        if not host_data:
            return jsonify({'error': f'Host {host_name} not found'}), 404
        
        # Forward request to host with async support
        host_endpoint = '/host/navigation/execute'
        host_url = buildHostUrl(host_data, host_endpoint)
        
        print(f"📡 [NAVIGATION] Forwarding to: {host_url}")
        
        response = requests.post(
            host_url,
            json={'navigation_data': navigation_data},
            timeout=90
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ [NAVIGATION] Navigation completed successfully")
            return jsonify(result)
        else:
            error_msg = f"Navigation failed with status {response.status_code}: {response.text}"
            print(f"❌ [NAVIGATION] {error_msg}")
            return jsonify({'error': error_msg}), response.status_code
        
    except requests.exceptions.Timeout:
        return jsonify({'error': 'Navigation request timed out'}), 408
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'Network error: {str(e)}'}), 500
    except Exception as e:
        print(f"❌ [NAVIGATION] Error executing navigation: {e}")
        return jsonify({'error': str(e)}), 500

@server_control_bp.route('/navigationBatchExecute', methods=['POST'])
def batch_execute_navigation():
    """Execute batch navigation on a host device."""
    try:
        data = request.get_json()
        host_name = data.get('host_name')
        batch_data = data.get('batch_data')
        
        if not host_name:
            return jsonify({'error': 'host_name is required'}), 400
        
        if not batch_data or not isinstance(batch_data, list):
            return jsonify({'error': 'Batch data must be a list of navigation items'}), 400
        
        
        print(f"🧭 [BATCH-NAVIGATION] Executing batch navigation on host: {host_name}")
        print(f"   Batch size: {len(batch_data)} items")
        
        # Check if host is registered
        host_manager = get_host_manager()
        host_data = host_manager.get_host(host_name)
        if not host_data:
            return jsonify({'error': f'Host {host_name} not found'}), 404
        
        # Forward request to host
        host_endpoint = '/host/navigation/batchExecute'
        host_url = buildHostUrl(host_data, host_endpoint)
        
        print(f"📡 [BATCH-NAVIGATION] Forwarding to: {host_url}")
        
        response = requests.post(
            host_url,
            json={'batch_data': batch_data},
            timeout=180  # Longer timeout for batch operations
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ [BATCH-NAVIGATION] Batch navigation completed successfully")
            return jsonify(result)
        else:
            error_msg = f"Batch navigation failed with status {response.status_code}: {response.text}"
            print(f"❌ [BATCH-NAVIGATION] {error_msg}")
            return jsonify({'error': error_msg}), response.status_code
        
    except requests.exceptions.Timeout:
        return jsonify({'error': 'Batch navigation request timed out'}), 408
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'Network error: {str(e)}'}), 500
    except Exception as e:
        print(f"❌ [BATCH-NAVIGATION] Error executing batch navigation: {e}")
        return jsonify({'error': str(e)}), 500

# =====================================================
# CONTROLLER INFORMATION ENDPOINTS
# =====================================================

@server_control_bp.route('/getAllControllers', methods=['GET'])
def get_all_controllers():
    """Get all available controller implementations from Python code"""
    try:
        print("[@route:getAllControllers] Fetching all available controller implementations")
        
        # Get controller configurations for different device models to understand available implementations
        controller_types = {
            'remote': [
                {
                    'id': 'android_tv',
                    'name': 'Android TV (ADB)',
                    'description': 'Android TV control with ADB',
                    'implementation': 'android_tv',
                    'status': 'available',
                    'parameters': ['device_ip', 'device_port', 'connection_timeout']
                },
                {
                    'id': 'android_mobile',
                    'name': 'Android Mobile (ADB)',
                    'description': 'Android Mobile control with ADB',
                    'implementation': 'android_mobile',
                    'status': 'available',
                    'parameters': ['device_ip', 'device_port', 'connection_timeout']
                },
                {
                    'id': 'ir_remote',
                    'name': 'IR Remote',
                    'description': 'Infrared remote control with classic TV/STB buttons',
                    'implementation': 'ir_remote',
                    'status': 'available',
                    'parameters': ['device_path', 'protocol', 'frequency']
                },
                {
                    'id': 'bluetooth_remote',
                    'name': 'Bluetooth Remote',
                    'description': 'Bluetooth HID remote control',
                    'implementation': 'bluetooth_remote',
                    'status': 'available',
                    'parameters': ['device_address', 'pairing_pin', 'connection_timeout']
                }
            ],
            'av': [
                {
                    'id': 'hdmi_stream',
                    'name': 'HDMI Stream (Video Capture)',
                    'description': 'HDMI video capture via Flask host with video device',
                    'implementation': 'hdmi_stream',
                    'status': 'available',
                    'parameters': ['video_device', 'resolution', 'fps', 'stream_path', 'service_name']
                }
            ],
            'verification': [
                {
                    'id': 'adb',
                    'name': 'ADB Verification',
                    'description': 'Android device verification via ADB',
                    'implementation': 'adb',
                    'status': 'available',
                    'parameters': ['device_ip', 'device_port', 'connection_timeout']
                },
                {
                    'id': 'ocr',
                    'name': 'OCR Verification',
                    'description': 'Optical Character Recognition verification',
                    'implementation': 'ocr',
                    'status': 'available',
                    'parameters': []
                }
            ],
            'power': [
                {
                    'id': 'tapo',
                    'name': 'Tapo power Control',
                    'description': 'Tapo power control via uhubctl',
                    'implementation': 'tapo',
                    'status': 'available',
                    'parameters': ['hub_location', 'port_number']
                }
            ]
        }
        
        print(f"[@route:getAllControllers] Successfully retrieved {len(controller_types)} controller types")
        
        return jsonify({
            'success': True,
            'controller_types': controller_types
        }), 200
        
    except Exception as e:
        print(f"[@route:getAllControllers] Error: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to get controller types: {str(e)}'
        }), 500


# =====================================================
# NAVIGATION CACHE POPULATION HELPER
# =====================================================

# In-memory cache to track which trees have been populated on which hosts
# Format: {(tree_id, team_id, host_name): timestamp}
_navigation_cache_tracker = {}
_cache_tracker_ttl = 3600  # 1 hour TTL for cache tracker

def populate_navigation_cache_for_control(tree_id: str, team_id: str, host_name: str) -> bool:
    """
    Rebuild navigation cache when taking control of a device
    ALWAYS clears and rebuilds cache on take-control to ensure fresh data
    
    Args:
        tree_id: Navigation tree ID
        team_id: Team ID
        host_name: Host name to populate cache on
        
    Returns:
        True if cache was successfully populated, False otherwise
    """
    try:
        import time
        cache_key = (tree_id, team_id, host_name)
        
        # Get host info first
        host_manager = get_host_manager()
        host_info = host_manager.get_host(host_name)
        if not host_info:
            print(f"[@control:cache] Host {host_name} not found")
            return False
        
        # STEP 1: Load tree data from database
        print(f"[@control:cache] Loading tree data from database for tree {tree_id}")
        from shared.src.lib.database.navigation_trees_db import get_complete_tree_hierarchy, get_full_tree
        
        # Try to load complete hierarchy first (for nested trees)
        hierarchy_result = get_complete_tree_hierarchy(tree_id, team_id)
        
        if hierarchy_result.get('success'):
            all_trees_data = hierarchy_result.get('all_trees_data', [])
            print(f"[@control:cache] Loaded tree hierarchy: {len(all_trees_data)} trees")
        else:
            # Fallback: Load single tree
            tree_result = get_full_tree(tree_id, team_id)
            if not tree_result.get('success'):
                print(f"[@control:cache] Failed to load tree {tree_id}: {tree_result.get('error', 'Unknown error')}")
                return False
            
            all_trees_data = [tree_result.get('tree')]
            print(f"[@control:cache] Loaded single tree")
        
        # STEP 2: Populate cache on HOST (overwrites any existing cache)
        # CRITICAL: Use force_repopulate=True to rebuild stale cache (nodes/edges may have been added since last build)
        print(f"[@control:cache] 🔨 Building cache on HOST for tree {tree_id} (force_repopulate=True)")
        populate_result, status_code = proxy_to_host_direct(
            host_info,
            f'/host/navigation/cache/populate/{tree_id}?team_id={team_id}',
            'POST',
            data={
                'all_trees_data': all_trees_data,
                'force_repopulate': True  # Always rebuild on takeControl to ensure fresh data
            }
        )
        
        if populate_result and populate_result.get('success'):
            print(f"[@control:cache] ✅ Cache built successfully on HOST for tree {tree_id}")
            # Track in memory
            _navigation_cache_tracker[cache_key] = time.time()
            return True
        else:
            print(f"[@control:cache] ❌ Cache build failed: {populate_result}")
            return False
            
    except Exception as e:
        print(f"[@control:cache] Error rebuilding cache: {e}")
        import traceback
        traceback.print_exc()
        return False 