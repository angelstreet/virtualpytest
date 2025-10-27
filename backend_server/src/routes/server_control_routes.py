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
                        
                        # Populate navigation cache for the controlled device (if tree_id provided)
                        # Run in background thread to avoid blocking takeControl response (was 5.78s!)
                        tree_id = data.get('tree_id')
                        team_id = request.args.get('team_id') # team_id comes from buildServerUrl query params
                        if tree_id and team_id:
                            import threading
                            
                            def populate_cache_async():
                                """Background task to populate navigation cache"""
                                try:
                                    print(f"🗺️ [CONTROL:ASYNC] Populating navigation cache for tree: {tree_id}")
                                    cache_success = populate_navigation_cache_for_control(tree_id, team_id, host_name)
                                    if cache_success:
                                        print(f"✅ [CONTROL:ASYNC] Navigation cache populated successfully")
                                    else:
                                        print(f"⚠️ [CONTROL:ASYNC] Navigation cache population failed (non-critical)")
                                except Exception as cache_error:
                                    print(f"⚠️ [CONTROL:ASYNC] Navigation cache population error: {cache_error}")
                            
                            # Start cache population in background (non-blocking)
                            threading.Thread(target=populate_cache_async, daemon=True).start()
                            print(f"🗺️ [CONTROL] Navigation cache population started in background")
                        
                        return jsonify({
                            'success': True,
                            'message': f'Successfully took control of host: {host_name}, device: {device_id}',
                            'session_id': session_id,
                            'host_name': host_name,
                            'device_id': device_id,
                            'host_result': result,
                            'cache_status': 'populating' if tree_id and team_id else 'not_applicable'
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
        
        # Forward request to host
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
    Populate navigation cache when taking control of a device
    
    Uses TWO-LEVEL CACHE COHERENCE CHECK:
    - Level 1: In-memory tracker (fast - avoids DB queries and network calls)
    - Level 2: HOST verification (safe - ensures cache file actually exists)
    
    This prevents cache incoherence when:
    - HOST process restarts and /tmp cache is cleared
    - Cache file is manually deleted on HOST
    - HOST cache TTL expires but SERVER tracker is still valid
    - Disk space issues cause cache eviction
    
    Args:
        tree_id: Navigation tree ID
        team_id: Team ID
        host_name: Host name to populate cache on
        
    Returns:
        True if cache exists or was successfully populated, False otherwise
    """
    try:
        import time
        cache_key = (tree_id, team_id, host_name)
        
        # Get host info first (needed for verification)
        host_manager = get_host_manager()
        host_info = host_manager.get_host(host_name)
        if not host_info:
            print(f"[@control:cache] Host {host_name} not found")
            return False
        
        # OPTION 3: Two-Level Check (Fast + Safe)
        # Level 1: Check in-memory tracker (fast path - avoid DB queries)
        cache_tracked = cache_key in _navigation_cache_tracker
        if cache_tracked:
            last_populated = _navigation_cache_tracker[cache_key]
            age = time.time() - last_populated
            if age < _cache_tracker_ttl:
                print(f"[@control:cache] 🔍 In-memory tracker says cache exists (age: {int(age)}s) - verifying with HOST...")
                
                # Level 2: ALWAYS verify HOST actually has the file (cache coherence check)
                check_result, status_code = proxy_to_host_direct(
                    host_info,
                    f'/host/navigation/cache/check/{tree_id}?team_id={team_id}',
                    'GET'
                )
                
                if check_result and check_result.get('success') and check_result.get('exists'):
                    print(f"[@control:cache] ✅ HOST confirmed cache exists - cache coherent, skipping population")
                    # Refresh tracker timestamp to extend TTL
                    _navigation_cache_tracker[cache_key] = time.time()
                    return True
                else:
                    # CACHE COHERENCE FAILURE: Tracker says yes, but HOST says no!
                    print(f"[@control:cache] ⚠️ CACHE INCOHERENT: Tracker cached but HOST missing file - invalidating tracker and re-populating")
                    del _navigation_cache_tracker[cache_key]
                    # Fall through to re-populate
            else:
                print(f"[@control:cache] Cache tracker expired (age: {int(age)}s), re-checking host")
                del _navigation_cache_tracker[cache_key]
        
        # Either tracker expired, or HOST cache missing, or no tracker entry - verify with HOST
        print(f"[@control:cache] Checking if cache exists on HOST for tree {tree_id}")
        check_result, status_code = proxy_to_host_direct(
            host_info,
            f'/host/navigation/cache/check/{tree_id}?team_id={team_id}',
            'GET'
        )
        
        if check_result and check_result.get('success') and check_result.get('exists'):
            print(f"[@control:cache] ✅ Cache already exists on HOST for tree {tree_id}, updating tracker and skipping")
            # Update tracker with current timestamp
            _navigation_cache_tracker[cache_key] = time.time()
            return True
        
        # Load tree data from database
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
            
            # Format as single-tree hierarchy for unified cache
            all_trees_data = [{
                'tree_id': tree_id,
                'tree_info': {
                    'name': tree_result['tree'].get('name', 'Unknown'),
                    'is_root_tree': True,
                    'tree_depth': 0,
                    'parent_tree_id': None,
                    'parent_node_id': None
                },
                'nodes': tree_result['nodes'],
                'edges': tree_result['edges']
            }]
            print(f"[@control:cache] Loaded single tree as fallback")
        
        # Populate cache on host
        cache_result, status_code = proxy_to_host_direct(
            host_info,
            f'/host/navigation/cache/populate/{tree_id}',
            'POST',
            {
                'team_id': team_id,
                'all_trees_data': all_trees_data,
                'force_repopulate': True
            }
        )
        
        if cache_result and cache_result.get('success'):
            print(f"[@control:cache] Successfully populated cache on {host_name}: {cache_result.get('nodes_count', 0)} nodes")
            # Track in memory so subsequent takeControl calls are instant
            import time
            _navigation_cache_tracker[cache_key] = time.time()
            print(f"[@control:cache] Cache tracker updated for tree {tree_id}")
            return True
        else:
            print(f"[@control:cache] Cache population failed: {cache_result.get('error', 'Unknown error') if cache_result else 'No response'}")
            return False
            
    except Exception as e:
        print(f"[@control:cache] Error populating cache: {str(e)}")
        return False 