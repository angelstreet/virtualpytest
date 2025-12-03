"""
System routes for client registration and health management
Handles server/client communication and registry
"""

from flask import Blueprint, request, jsonify, current_app
import threading
import time
import requests
import os
import psutil
from datetime import datetime
import json
from typing import TypedDict, Optional, List, Any
print("[@server_system_routes] Importing server_utils")
from  backend_server.src.lib.utils.server_utils import get_host_manager, get_server_system_stats
print("[@server_system_routes] Importing system_metrics_db")
from shared.src.lib.database.system_metrics_db import store_system_metrics
print("[@server_system_routes] Importing server_system_bp")
server_system_bp = Blueprint('server_system', __name__, url_prefix='/server/system')
print("[@server_system_routes] Server_system_bp imported")
@server_system_bp.route('/register', methods=['POST'])
def register_host():
    """Host registers with server"""
    try:
        host_info = request.get_json()
        
        print(f"[@route:register_host] Host registration request received:")
        print(f"   Host info keys: {list(host_info.keys()) if host_info else 'None'}")
        print(f"   Host name: {host_info.get('host_name', 'Not provided')}")
        print(f"   Host URL: {host_info.get('host_url', 'Not provided')}")
        devices_list = host_info.get('devices', [])
        print(f"   Devices: {len(devices_list)} device(s)")
        if len(devices_list) == 0:
            print(f"   ✅ Host with no devices - this is valid")
        
        # Check for required fields
        required_fields = ['host_url', 'host_name', 'devices']
        missing_fields = []
        for field in required_fields:
            if field not in host_info:
                missing_fields.append(field)
            elif field == 'devices':
                # devices can be an empty list, that's valid
                if not isinstance(host_info[field], list):
                    missing_fields.append(field)
                else:
                    print(f"   ✅ Devices field validation passed (list with {len(host_info[field])} items)")
            elif not host_info[field]:
                missing_fields.append(field)
        
        if missing_fields:
            error_msg = f'Missing required fields: {", ".join(missing_fields)}'
            print(f"❌ [SERVER] Registration failed: {error_msg}")
            print(f"   Required fields: {required_fields}")
            print(f"   Received fields: {list(host_info.keys()) if host_info else 'None'}")
            return jsonify({'error': error_msg}), 400
        
        # Extract port from host_url or use provided port
        host_port = host_info.get('host_port', '6109')
        devices = host_info.get('devices', [])
        
        print(f"[@route:register_host] Host configuration:")
        print(f"   Host URL (browser): {host_info['host_url']}")
        print(f"   Host API URL (server): {host_info.get('host_api_url', 'NOT PROVIDED - will fallback to host_url')}")
        print(f"   Host Port: {host_port}")
        print(f"   Devices: {len(devices)} devices")
        
        # Process each device
        devices_with_controllers = []
        
        for device in devices:
            device_name = device.get('device_name')
            device_model = device.get('device_model') 
            device_capabilities = device.get('device_capabilities', {})
            
            print(f"[@route:register_host] Processing device: {device_name} ({device_model})")
            print(f"[@route:register_host] Device capabilities: {device_capabilities}")
            
            # DEBUG: Check if video paths are being sent by host
            video_stream_path = device.get('video_stream_path')
            video_capture_path = device.get('video_capture_path')
            video = device.get('video')
            print(f"[@route:register_host] Video paths from host:")
            print(f"   video_stream_path: {video_stream_path}")
            print(f"   video_capture_path: {video_capture_path}")
            print(f"   video: {video}")
            
            # Check for device-level verification and action types
            device_verification_types = device.get('device_verification_types', {})
            device_action_types = device.get('device_action_types', {})
            
            if device_verification_types:
                print(f"[@route:register_host] Device {device_name} has {len(device_verification_types)} verification controller types")
            if device_action_types:
                print(f"[@route:register_host] Device {device_name} has {len(device_action_types)} action categories")
            
            # Add device with processed info - INCLUDE VIDEO PATHS FOR HEATMAP
            device_with_controllers = {
                'device_id': device.get('device_id'),
                'device_name': device_name,
                'device_model': device_model,
                'device_ip': device.get('device_ip'),
                'device_port': device.get('device_port'),
                'ir_type': device.get('ir_type'),  # Include IR type for remote configuration
                'video_stream_path': device.get('video_stream_path'),  # CRITICAL: Include for heatmap
                'video_capture_path': device.get('video_capture_path'),  # CRITICAL: Include for heatmap  
                'video': device.get('video'),  # Include video device path
                'device_capabilities': device_capabilities,
                'device_verification_types': device_verification_types,
                'device_action_types': device_action_types
            }
            devices_with_controllers.append(device_with_controllers)
        
        # Create host object with multi-device support
        host_object: Host = {
            # === PRIMARY IDENTIFICATION ===
            'host_name': host_info['host_name'],
            'description': f"Host: {host_info['host_name']} with {len(devices)} device(s)",
            
            # === NETWORK CONFIGURATION ===
            'host_url': host_info['host_url'],  # Required: For browser/frontend (HTTPS via nginx)
            'host_api_url': host_info.get('host_api_url'),  # Optional: For server-to-server (HTTP direct), fallback to host_url if not provided
            'host_port': int(host_port),
            
            # === MULTI-DEVICE CONFIGURATION ===
            'devices': devices_with_controllers,
            'device_count': len(devices),
            
            # === STATUS AND METADATA ===
            'status': 'online',
            'last_seen': time.time(),
            'registered_at': datetime.now().isoformat(),
            'system_stats': host_info.get('system_stats', {}),  # Host provides its own stats
            
            # === DEVICE LOCK MANAGEMENT ===
            'isLocked': False,
            'lockedBy': None,
            'lockedAt': None,
        }
        
        # Store host using the host manager
        host_manager = get_host_manager()
        success = host_manager.register_host(host_info['host_name'], host_object)
        
        # Auto-register devices in flags table
        try:
            from routes.server_device_flags_routes import upsert_device_on_registration
            for device in devices_with_controllers:
                upsert_device_on_registration(
                    host_info['host_name'],
                    device['device_id'],
                    device['device_name']
                )
        except Exception as e:
            print(f"⚠️ [SERVER] Failed to auto-register devices in flags table: {e}")
        
        if not success:
            error_msg = f"Failed to register host {host_info['host_name']}"
            print(f"❌ [SERVER] {error_msg}")
            return jsonify({'error': error_msg}), 500
        
        response_data = host_object
        
        return jsonify({
            'status': 'success',
            'message': 'Host registered successfully',
            'host_name': host_info['host_name'],
            'host_data': response_data
        }), 200
        
    except Exception as e:
        error_msg = f"Server error during registration: {str(e)}"
        print(f"❌ [SERVER] {error_msg}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': error_msg}), 500
print("[@server_system_routes] Unregister host route imported")
@server_system_bp.route('/unregister', methods=['POST'])
def unregister_host():
    """Host unregisters from server"""
    try:
        data = request.get_json()
        
        host_name = data.get('host_name')
        
        if not host_name:
            return jsonify({'error': 'Missing host_name'}), 400
        
        host_manager = get_host_manager()
        success = host_manager.unregister_host(host_name)
        
        if success:
            print(f"🔌 Host unregistered: {host_name}")
            return jsonify({
                'status': 'success',
                'message': 'Host unregistered successfully'
            }), 200
        else:
            error_msg = f'Host not found with host_name: {host_name}'
            return jsonify({'error': error_msg}), 404
            
    except Exception as e:
        print(f"❌ Error unregistering host: {e}")
        return jsonify({'error': str(e)}), 500
print("[@server_system_routes] Health check route imported")

@server_system_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for clients"""
    system_stats = get_server_system_stats()
    
    return jsonify({
        'status': 'healthy',
        'timestamp': time.time(),
        'mode': os.getenv('SERVER_MODE', 'server'),
        'system_stats': system_stats
    }), 200

print("[@server_system_routes] Get all hosts route imported")
@server_system_bp.route('/getAllHosts', methods=['GET'])
def getAllHosts():
    """
    Return all registered hosts - single REST endpoint for host listing
    
    Query parameters:
        include_actions: boolean (default: false) - Include device_action_types and device_verification_types
                        Set to true only when you need action/verification schemas (for control pages)
        include_system_stats: boolean (default: false) - Include full system stats and device details
                        Set to true when you need system metrics (CPU, RAM, disk) for dashboard/monitoring
    """
    try:
        # Check if we should include action schemas (defaults to false for performance)
        include_actions = request.args.get('include_actions', 'false').lower() == 'true'
        # Check if we should include full system stats and device details (defaults to false for performance)
        include_system_stats = request.args.get('include_system_stats', 'false').lower() == 'true'
        
        host_manager = get_host_manager()
        
        # Get all hosts from manager (no automatic cleanup - hosts are only removed on explicit unregister)
        all_hosts = host_manager.get_all_hosts()
        # Verify required fields are present
        valid_hosts = []
        required_fields = ['host_name', 'host_url']
        
        # all_hosts is a dict {host_name: host_data}, so iterate over values
        for host_info in all_hosts.values():
            # Check required fields
            is_valid = True
            for field in required_fields:
                if field not in host_info or not host_info[field]:
                    print(f"⚠️ [HOSTS] Host {host_info.get('host_name')} missing required field: {field}")
                    is_valid = False
                    break
            
            if is_valid:
                # If both flags are false, create ultra-lightweight response (for Rec page)
                if not include_actions and not include_system_stats and 'devices' in host_info:
                    # Create a minimal copy - only include fields actually used by Rec page
                    lightweight_host = {
                        'host_name': host_info.get('host_name'),
                        'host_url': host_info.get('host_url'),
                        'host_port': host_info.get('host_port'),
                        'status': host_info.get('status', 'online'),
                        'device_count': host_info.get('device_count', 0),
                        # Minimal system_stats - only status indicators for stuck detection
                        'system_stats': {
                            'ffmpeg_status': {
                                'status': host_info.get('system_stats', {}).get('ffmpeg_status', {}).get('status', 'unknown')
                            },
                            'monitor_status': {
                                'status': host_info.get('system_stats', {}).get('monitor_status', {}).get('status', 'unknown')
                            }
                        } if host_info.get('system_stats') else {},
                        'devices': []
                    }
                    
                    # For each device, only include fields actually used by Rec page
                    for device in host_info.get('devices', []):
                        lightweight_device = {
                            'device_id': device.get('device_id'),
                            'device_name': device.get('device_name'),
                            'device_model': device.get('device_model'),
                            'device_capabilities': device.get('device_capabilities'),
                            'video_stream_path': device.get('video_stream_path'),
                            'has_running_deployment': device.get('has_running_deployment', False),
                            # STRIPPED for performance:
                            # - device_action_types (~150KB)
                            # - device_verification_types (~40KB)
                            # - device_ip, device_port, ir_type (not displayed)
                            # - video_capture_path, video (not needed for streaming)
                        }
                        lightweight_host['devices'].append(lightweight_device)
                    
                    valid_hosts.append(lightweight_host)
                
                # If include_system_stats is true but include_actions is false (Dashboard use case)
                elif include_system_stats and not include_actions and 'devices' in host_info:
                    # Include full system stats and device details, but strip action schemas
                    dashboard_host = {
                        'host_name': host_info.get('host_name'),
                        'host_url': host_info.get('host_url'),
                        'host_port': host_info.get('host_port'),
                        'status': host_info.get('status', 'online'),
                        'device_count': host_info.get('device_count', 0),
                        'last_seen': host_info.get('last_seen'),
                        'registered_at': host_info.get('registered_at'),
                        # Include FULL system_stats for Dashboard
                        'system_stats': host_info.get('system_stats', {}),
                        'devices': []
                    }
                    
                    # For each device, include full details except action schemas
                    for device in host_info.get('devices', []):
                        dashboard_device = {
                            'device_id': device.get('device_id'),
                            'device_name': device.get('device_name'),
                            'device_model': device.get('device_model'),
                            'device_ip': device.get('device_ip'),
                            'device_port': device.get('device_port'),
                            'device_capabilities': device.get('device_capabilities'),
                            'video_stream_path': device.get('video_stream_path'),
                            'video_capture_path': device.get('video_capture_path'),  # Required for monitoring capture URLs
                            'video_fps': device.get('video_fps'),  # Required for monitoring capture alignment
                            'has_running_deployment': device.get('has_running_deployment', False),
                            'ir_type': device.get('ir_type'),
                            # STRIPPED for performance:
                            # - device_action_types (~150KB)
                            # - device_verification_types (~40KB)
                        }
                        dashboard_host['devices'].append(dashboard_device)
                    
                    valid_hosts.append(dashboard_host)
                
                else:
                    # Include full data (for control pages that need action schemas)
                    valid_hosts.append(host_info)
        
        print(f"🖥️ [HOSTS] Returning {len(valid_hosts)} valid hosts (include_actions={include_actions}, include_system_stats={include_system_stats})")
        for host in valid_hosts:
            device_count = host.get('device_count', 0)
            print(f"   Host: {host['host_name']} ({host['host_url']}) - {device_count} device(s)")
        
        # Get server info from environment variables
        server_name = os.getenv('SERVER_NAME', 'Unknown Server')
        server_url = os.getenv('SERVER_URL', 'Unknown URL')
        server_port = os.getenv('SERVER_PORT', 'Unknown Port')
        
        # Build server_info object
        server_info = {
            'server_name': server_name,
            'server_url': server_url,
            'server_port': server_port
        }
        
        # Include server system stats if requested (for Dashboard monitoring)
        if include_system_stats:
            # Skip speedtest if cache doesn't exist - avoid blocking the getAllHosts response
            # Speedtest will run in background thread and be cached for next request
            server_info['system_stats'] = get_server_system_stats(skip_speedtest=True)
        
        return jsonify({
            'success': True,
            'server_info': server_info,
            'hosts': valid_hosts
        }), 200
        
    except Exception as e:
        print(f"❌ [HOSTS] Error listing hosts: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

print("[@server_system_routes] Get device actions route imported")
@server_system_bp.route('/getDeviceActions', methods=['GET'])
def getDeviceActions():
    """
    Return action schemas for a specific device - lightweight endpoint for editing
    
    Query parameters:
    - host_name: Name of the host
    - device_id: ID of the device
    - team_id: Team ID (required for multi-tenancy)
    
    Returns:
    {
        "success": true,
        "device_action_types": {...},
        "device_verification_types": {...}
    }
    """
    try:
        host_name = request.args.get('host_name')
        device_id = request.args.get('device_id')
        team_id = request.args.get('team_id')
        
        if not host_name or not device_id:
            return jsonify({
                'success': False,
                'error': 'Missing required parameters: host_name and device_id'
            }), 400
        
        host_manager = get_host_manager()
        
        # Get host data
        host_data = host_manager.get_host(host_name)
        if not host_data:
            return jsonify({
                'success': False,
                'error': f'Host {host_name} not found'
            }), 404
        
        # Find the specific device
        devices = host_data.get('devices', [])
        device_data = next((d for d in devices if d.get('device_id') == device_id), None)
        
        if not device_data:
            return jsonify({
                'success': False,
                'error': f'Device {device_id} not found on host {host_name}'
            }), 404
        
        # Return just the action and verification schemas for this device
        return jsonify({
            'success': True,
            'host_name': host_name,
            'device_id': device_id,
            'device_model': device_data.get('device_model'),
            'device_action_types': device_data.get('device_action_types', {}),
            'device_verification_types': device_data.get('device_verification_types', {})
        }), 200
        
    except Exception as e:
        print(f"❌ [DEVICE_ACTIONS] Error getting device actions: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

print("[@server_system_routes] Ping route imported")
@server_system_bp.route('/ping', methods=['POST'])
def client_ping():
    """Client sends periodic health ping to server"""
    try:
        ping_data = request.get_json()
        
        if not ping_data:
            return jsonify({'error': 'No ping data received'}), 400
        
        host_name = ping_data.get('host_name')
        
        if not host_name:
            return jsonify({'error': 'Missing host_name in ping'}), 400
        
        host_manager = get_host_manager()
        
        # Check if host is registered
        host_data = host_manager.get_host(host_name)
        if not host_data:
            # Host not registered, ask them to register
            print(f"📍 [PING] Unknown host {host_name} sending registration request")
            return jsonify({
                'status': 'not_registered',
                'message': 'Host not registered, please register first',
                'action': 'register'
            }), 404
        
        # Update host information using the manager
        success = host_manager.update_host_ping(host_name, ping_data)
        
        if not success:
            return jsonify({'error': 'Failed to update host ping'}), 500
        
        # Server only receives device status for monitoring/display purposes
        per_device_metrics = ping_data.get('per_device_metrics', [])
        device_count = len(per_device_metrics) if per_device_metrics else 0
        print(f"📊 [PING] Host {host_name} reported {device_count} devices")
        
        print(f"💓 [PING] Host {host_name} ping received - status updated")
        
        return jsonify({
            'status': 'success',
            'message': 'Ping received successfully',
            'server_time': time.time()
        }), 200
        
    except Exception as e:
        print(f"❌ [PING] Error processing host ping: {e}")
        return jsonify({'error': str(e)}), 500
print("[@server_system_routes] Host type imported")
# Define Host type matching Host_Types.ts
class Host(TypedDict):
    # === PRIMARY IDENTIFICATION ===
    host_name: str
    description: Optional[str]
    
    # === NETWORK CONFIGURATION ===
    host_url: str
    host_port: int
    
    # === MULTI-DEVICE CONFIGURATION ===
    devices: List[Any]  # Array of device configurations
    device_count: int
    
    # === STATUS AND METADATA ===
    status: str  # 'online' | 'offline' | 'unreachable' | 'maintenance'
    last_seen: float
    registered_at: str
    system_stats: Any  # SystemStats type
    
    # === DEVICE LOCK MANAGEMENT ===
    isLocked: bool
    lockedBy: Optional[str]
    lockedAt: Optional[float]
print("[@server_system_routes] Host type imported")

# =============================================================================
# SERVER SYSTEM CONTROL ROUTES
# =============================================================================

@server_system_bp.route('/restartServerService', methods=['POST'])
def restart_server_service():
    """Restart vpt_server_host systemd service on server"""
    try:
        from shared.src.lib.utils.system_utils import restart_systemd_service
        
        result = restart_systemd_service('vpt_server_host')
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to restart vpt_server_host service: {str(e)}'
        }), 500


@server_system_bp.route('/rebootServer', methods=['POST'])
def reboot_server():
    """Reboot the server machine"""
    try:
        from shared.src.lib.utils.system_utils import reboot_system
        
        result = reboot_system()
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to reboot server: {str(e)}'
        }), 500


# =============================================================================
# HOST SYSTEM CONTROL PROXY ROUTES  
# =============================================================================

@server_system_bp.route('/restartHostService', methods=['POST'])
def restart_host_service_proxy():
    """Proxy restart vpt_host service request to specific host"""
    try:
        data = request.get_json() or {}
        host_name = data.get('host_name')
        
        if not host_name:
            return jsonify({
                'success': False,
                'error': 'host_name is required'
            }), 400
        
        # Get host info
        host_manager = get_host_manager()
        host_data = host_manager.get_host(host_name)
        if not host_data:
            return jsonify({
                'success': False,
                'error': f'Host {host_name} not found'
            }), 404
        
        # Forward request to host
        from shared.src.lib.utils.build_url_utils import call_host
        
        response_data, status_code = call_host(
            host_data,
            '/host/system/restartHostService',
            method='POST',
            data={},
            timeout=30
        )
        
        if status_code == 200:
            return jsonify(response_data), 200
        else:
            return jsonify({
                'success': False,
                'error': f'Host returned status {status_code}'
            }), status_code
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to restart host service: {str(e)}'
        }), 500


@server_system_bp.route('/rebootHost', methods=['POST'])
def reboot_host_proxy():
    """Proxy reboot host request to specific host"""
    try:
        data = request.get_json() or {}
        host_name = data.get('host_name')
        
        if not host_name:
            return jsonify({
                'success': False,
                'error': 'host_name is required'
            }), 400
        
        # Get host info
        host_manager = get_host_manager()
        host_data = host_manager.get_host(host_name)
        if not host_data:
            return jsonify({
                'success': False,
                'error': f'Host {host_name} not found'
            }), 404
        
        # Forward request to host
        from shared.src.lib.utils.build_url_utils import call_host
        
        response_data, status_code = call_host(
            host_data,
            '/host/system/rebootHost',
            method='POST',
            data={},
            timeout=10
        )
        
        if status_code == 200:
            return jsonify(response_data), 200
        elif status_code == 504:
            # Timeout is expected for reboot
            return jsonify({
                'success': True,
                'message': 'Reboot command sent (timeout expected)'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': f'Host returned status {status_code}'
            }), status_code
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to reboot host: {str(e)}'
        }), 500


@server_system_bp.route('/restartHostStreamService', methods=['POST'])
def restart_host_stream_service_proxy():
    """Proxy restart host stream service request to specific host"""
    try:
        data = request.get_json() or {}
        host_name = data.get('host_name')
        device_id = data.get('device_id', 'device1')
        quality = data.get('quality', 'sd')  # Extract quality parameter
        
        if not host_name:
            return jsonify({
                'success': False,
                'error': 'host_name is required'
            }), 400
        
        # Get host info
        host_manager = get_host_manager()
        host_data = host_manager.get_host(host_name)
        if not host_data:
            return jsonify({
                'success': False,
                'error': f'Host {host_name} not found'
            }), 404
        
        # Forward request to host
        from shared.src.lib.utils.build_url_utils import call_host
        
        response_data, status_code = call_host(
            host_data,
            '/host/system/restartHostStreamService',
            method='POST',
            data={'device_id': device_id, 'quality': quality},
            timeout=60
        )
        
        if status_code == 200:
            return jsonify(response_data), 200
        else:
            return jsonify({
                'success': False,
                'error': f'Host returned status {status_code}'
            }), status_code
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to restart host stream service: {str(e)}'
        }), 500


# =============================================================================
# HOST MONITORING PROXY ROUTES
# =============================================================================

@server_system_bp.route('/diskUsage', methods=['GET'])
def disk_usage_diagnostics_proxy():
    """
    Proxy disk usage diagnostics request to specific host.
    Returns comprehensive disk space analysis for all capture directories.
    
    Query params:
        - host_name: Required - which host to query
        - capture_dir: Optional - specific capture (e.g., 'capture1') or 'all' (default)
    """
    try:
        host_name = request.args.get('host_name')
        capture_dir = request.args.get('capture_dir', 'all')
        
        if not host_name:
            return jsonify({
                'success': False,
                'error': 'host_name query parameter is required'
            }), 400
        
        # Get host info
        host_manager = get_host_manager()
        host_data = host_manager.get_host(host_name)
        if not host_data:
            return jsonify({
                'success': False,
                'error': f'Host {host_name} not found'
            }), 404
        
        # Forward request to host
        from shared.src.lib.utils.build_url_utils import call_host
        
        response_data, status_code = call_host(
            host_data,
            f'/host/monitoring/disk-usage?capture_dir={capture_dir}',
            method='GET',
            timeout=30  # Long timeout for file scanning
        )
        
        if status_code == 200:
            # Add host identification to response
            response_data['host_name'] = host_name
            return jsonify(response_data), 200
        elif status_code == 504:
            return jsonify({
                'success': False,
                'error': 'Request timeout - disk analysis taking too long (check host logs)'
            }), 504
        else:
            return jsonify({
                'success': False,
                'error': f'Host returned status {status_code}',
                'host_response': response_data.get('error', 'Unknown error')
            }), status_code
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to get disk usage: {str(e)}'
        }), 500

print("[@server_system_routes] END")