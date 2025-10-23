"""
Host Utilities

Host registration, storage, and management using the new Host/Device/Controller architecture.
Focused on host-related functionality only.
"""

import os
import sys
import time
import threading
import signal
import atexit
import requests
import uuid
import psutil
import platform
from typing import Dict, Any, Optional, List
from datetime import datetime

from .system_info_utils import get_host_system_stats, get_enhanced_system_stats, get_per_device_metrics
# Import get_host dynamically to avoid relative import issues
try:
    import sys
    import os
    # Try to find backend_host path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    shared_lib = os.path.dirname(os.path.dirname(current_dir))
    project_root = os.path.dirname(shared_lib)
    backend_host_path = os.path.join(project_root, 'backend_host', 'src')
    if backend_host_path not in sys.path:
        sys.path.insert(0, backend_host_path)
    from backend_host.src.controllers.controller_manager import get_host
except ImportError as e:
    # No fallback - fail with detailed error message
    raise ImportError(f"Failed to import controller_manager: {e}. Check your Python path and environment setup.")
from shared.src.lib.utils.build_url_utils import buildServerUrl

# Disable SSL warnings for self-signed certificates
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# =====================================================
# HOST STORAGE AND MANAGEMENT
# =====================================================

class HostManager:
    """Host storage and management (device locking is handled by server)"""
    
    def __init__(self):
        # Thread-safe storage for hosts
        self._hosts: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
    
    def register_host(self, host_name: str, host_data: Dict[str, Any]) -> bool:
        """Register or update a host"""
        with self._lock:
            try:
                # Ensure required fields
                if not host_name or not host_data.get('host_url'):
                    return False
                
                # Add metadata
                current_time = time.time()
                host_data['last_seen'] = current_time
                host_data['status'] = 'online'
                
                # If updating existing host, preserve registration time
                if host_name in self._hosts:
                    existing_host = self._hosts[host_name]
                    host_data['registered_at'] = existing_host.get('registered_at', datetime.now().isoformat())
                    host_data['reconnected_at'] = datetime.now().isoformat()
                    print(f"🔄 [HostManager] Updating existing host: {host_name}")
                else:
                    host_data['registered_at'] = datetime.now().isoformat()
                    print(f"✅ [HostManager] Registering new host: {host_name}")
                
                self._hosts[host_name] = host_data
                return True
                
            except Exception as e:
                print(f"❌ [HostManager] Error registering host {host_name}: {e}")
                return False
    
    def unregister_host(self, host_name: str) -> bool:
        """Unregister a host"""
        with self._lock:
            try:
                if host_name in self._hosts:
                    del self._hosts[host_name]
                    print(f"🔌 [HostManager] Unregistered host: {host_name}")
                    return True
                return False
            except Exception as e:
                print(f"❌ [HostManager] Error unregistering host {host_name}: {e}")
                return False
    
    def get_host(self, host_name: str) -> Optional[Dict[str, Any]]:
        """Get a specific host by name"""
        with self._lock:
            return self._hosts.get(host_name)
    
    def get_all_hosts(self) -> List[Dict[str, Any]]:
        """Get all registered hosts"""
        with self._lock:
            return list(self._hosts.values())
    
    def get_hosts_by_model(self, models: List[str]) -> List[Dict[str, Any]]:
        """Get hosts that have devices with specified models"""
        with self._lock:
            filtered_hosts = []
            for host_data in self._hosts.values():
                devices = host_data.get('devices', [])
                if any(device.get('device_model') in models for device in devices):
                    filtered_hosts.append(host_data)
            return filtered_hosts
    
    def update_host_ping(self, host_name: str, ping_data: Dict[str, Any]) -> bool:
        """Update host with ping data"""
        with self._lock:
            try:
                if host_name not in self._hosts:
                    return False
                
                host_data = self._hosts[host_name]
                current_time = time.time()
                host_data['last_seen'] = current_time
                host_data['status'] = 'online'
                
                # Update system stats if provided
                if 'system_stats' in ping_data:
                    host_data['system_stats'] = ping_data['system_stats']
                
                # Update device-level data if provided
                if 'devices' in ping_data:
                    for updated_device in ping_data['devices']:
                        device_id = updated_device.get('device_id')
                        if device_id:
                            # Find and update corresponding device
                            for existing_device in host_data.get('devices', []):
                                if existing_device.get('device_id') == device_id:
                                    # Update device-level verification and action types
                                    if 'available_verification_types' in updated_device:
                                        existing_device['available_verification_types'] = updated_device['available_verification_types']
                                    if 'available_action_types' in updated_device:
                                        existing_device['available_action_types'] = updated_device['available_action_types']
                                    break
                
                # Update other provided fields
                for field in ['host_ip', 'host_port_external']:
                    if field in ping_data:
                        host_data[field] = ping_data[field]
                
                return True
                
            except Exception as e:
                print(f"❌ [HostManager] Error updating host ping for {host_name}: {e}")
                return False
    
    def cleanup_stale_hosts(self, timeout_seconds: int = 120) -> int:
        """Remove hosts that haven't been seen for a while"""
        with self._lock:
            current_time = time.time()
            stale_hosts = []
            
            for host_name, host_data in self._hosts.items():
                if current_time - host_data.get('last_seen', 0) > timeout_seconds:
                    stale_hosts.append(host_name)
            
            for host_name in stale_hosts:
                del self._hosts[host_name]
                print(f"⚠️ [HostManager] Removed stale host: {host_name}")
            
            return len(stale_hosts)

# Global instance
_host_manager = HostManager()

def get_host_manager() -> HostManager:
    """Get the global host manager instance"""
    global _host_manager
    if _host_manager is None:
        _host_manager = get_host()
    return _host_manager

# =====================================================
# HOST REGISTRATION AND CLIENT COMMUNICATION
# =====================================================

# Client registration state for host mode
client_registration_state = {
    'registered': False,
    'host_name': None,
    'urls': {},
    'ping_failures': 0,
    'last_ping_time': 0  # To prevent duplicate pings
}

# Ping thread for host mode
ping_thread = None
ping_stop_event = threading.Event()

def register_host_with_server():
    """Register this host with the server using new architecture."""
    global client_registration_state
    
    print("=" * 50)
    print("🔗 [HOST] Starting registration with server...")
    
    try:
        # Get host with all devices and controllers
        host = get_host()
        
        print(f"   Host Name: {host.host_name}")
        print(f"   Host URL: {host.host_ip}:{host.host_port}")
        print(f"   Configured Devices: {host.get_device_count()}")
        
        # Display device information
        for device in host.get_devices():
            print(f"     - {device.device_name} ({device.device_model}) [{device.device_id}]")
            capabilities = device.get_capabilities()
            if capabilities:
                print(f"       Capabilities: {', '.join(capabilities)}")
        
        # Get enhanced system stats for registration (skip speedtest to avoid startup delay)
        system_stats = get_enhanced_system_stats(skip_speedtest=True)
        
        # Get HOST_URL from environment variable (for browser/frontend access via nginx)
        host_url = os.getenv('HOST_URL', f"http://{host.host_ip}:{host.host_port}")
        
        # Get HOST_API_URL for direct server-to-server communication (HTTP, no SSL)
        # This allows servers to bypass nginx and talk directly to each other
        host_api_url = os.getenv('HOST_API_URL', f"http://{host.host_ip}:{host.host_port}")
        
        print(f"   Browser URL (via nginx): {host_url}")
        print(f"   API URL (direct): {host_api_url}")
        
        # Create registration payload
        registration_data = {
            'host_name': host.host_name,
            'host_url': host_url,  # For browser: HTTPS via nginx proxy
            'host_api_url': host_api_url,  # For server: HTTP direct connection
            'host_port': host.host_port,
            'host_ip': host.host_ip,
            'device_count': host.get_device_count(),
            'devices': [device.to_dict() for device in host.get_devices()],
            'capabilities': host.get_all_capabilities(),
            'system_stats': system_stats
        }
        
        # Build server URLs
        registration_url = buildServerUrl('/server/system/register')
        
        print(f"\n📡 [HOST] Sending registration to: {registration_url}")
        
        # Send registration request
        response = requests.post(
            registration_url,
            json=registration_data,
            timeout=30
        )
        
        if response.status_code == 200:
            print("✅ [HOST] Registration successful!")
            
            # Update registration state
            client_registration_state.update({
                'registered': True,
                'host_name': host.host_name,
                'urls': {
                    'register': registration_url,
                    'ping': buildServerUrl('/server/system/ping'),
                    'unregister': buildServerUrl('/server/system/unregister')
                },
                'ping_failures': 0,
                'last_ping_time': 0
            })
            
            print(f"   Registered as: {host.host_name}")
            print(f"   Devices: {host.get_device_count()}")
            print(f"   Total capabilities: {len(host.get_all_capabilities())}")
            
            return True
            
        else:
            print(f"❌ [HOST] Registration failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
        
    except Exception as e:
        print(f"❌ [HOST] Registration error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def get_devices_with_running_deployments():
    """Check which devices have running deployments"""
    try:
        from shared.src.lib.utils.supabase_utils import get_supabase_client
        supabase = get_supabase_client()
        host = get_host()
        
        # Get all deployments for this host
        deployments_result = supabase.table('deployments').select('id, device_id').eq('host_name', host.host_name).execute()
        
        if not deployments_result.data:
            return set()
        
        deployment_ids = [d['id'] for d in deployments_result.data]
        device_deployment_map = {d['id']: d['device_id'] for d in deployments_result.data}
        
        # Check for running executions
        running_executions = supabase.table('deployment_executions')\
            .select('deployment_id')\
            .in_('deployment_id', deployment_ids)\
            .eq('status', 'running')\
            .execute()
        
        # Return set of device_ids with running deployments
        running_devices = set()
        for execution in running_executions.data:
            deployment_id = execution['deployment_id']
            device_id = device_deployment_map.get(deployment_id)
            if device_id:
                running_devices.add(device_id)
        
        return running_devices
    except Exception as e:
        print(f"[@host] Error checking running deployments: {e}")
        return set()

def send_ping_to_server():
    """Send ping to server to maintain registration."""
    global client_registration_state
    
    # Prevent duplicate pings within 5 seconds
    current_time = time.time()
    if current_time - client_registration_state.get('last_ping_time', 0) < 5:
        return
    
    client_registration_state['last_ping_time'] = current_time
    
    # If not registered, try to register first
    if not client_registration_state.get('registered'):
        print("🔄 [HOST] Not registered - attempting registration before ping...")
        if register_host_with_server():
            print("✅ [HOST] Registration successful, continuing with ping...")
        else:
            print("❌ [HOST] Registration failed, will retry next ping cycle")
            return
    
    try:
        host = get_host()
        
        # Store host's own system metrics (same routine as server)
        host_system_stats = get_host_system_stats()
        
        # Debug: Show host's own system stats including service uptime and load averages
        disk_write = host_system_stats.get('disk_write_mb_per_sec', 'N/A')
        disk_write_str = f", Write={disk_write}MB/s" if disk_write != 'N/A' and disk_write != 0 else ""
        
        temp_str = f", Temp={host_system_stats.get('cpu_temperature_celsius', 'N/A')}°C" if 'cpu_temperature_celsius' in host_system_stats else ""
        
        # Load averages
        load_1m = host_system_stats.get('load_average_1m', 'N/A')
        load_5m = host_system_stats.get('load_average_5m', 'N/A')
        load_15m = host_system_stats.get('load_average_15m', 'N/A')
        load_str = f", Load: {load_1m}/{load_5m}/{load_15m}"
        
        # Service uptimes
        ffmpeg_service_uptime = host_system_stats.get('ffmpeg_service_uptime_seconds', 0)
        monitor_service_uptime = host_system_stats.get('monitor_service_uptime_seconds', 0)
        service_uptime_str = f", Services: FFmpeg={ffmpeg_service_uptime}s, Monitor={monitor_service_uptime}s"
        
        print(f"[@host:debug] 🔍 Host system stats: CPU={host_system_stats.get('cpu_percent', 'N/A')}%, RAM={host_system_stats.get('memory_percent', 'N/A')}%, Disk={host_system_stats.get('disk_percent', 'N/A')}%{disk_write_str}{temp_str}{load_str}{service_uptime_str}")
        
        # Store host system metrics directly (same function as server uses)
        from shared.src.lib.database.system_metrics_db import store_system_metrics
        store_system_metrics(host.host_name, host_system_stats)
        print(f"✅ Host system metrics stored: {host.host_name}")
        
        # Get only operational device metrics (no config recalculation)
        per_device_metrics = get_per_device_metrics(host.get_devices())
        
        # HOST INDEPENDENCE: Store device metrics locally (not via server)
        from shared.src.lib.database.system_metrics_db import store_device_metrics
        for device_metric in per_device_metrics:
            device_name = device_metric.get('device_name', 'Unknown')
            capture_folder = device_metric.get('capture_folder', 'unknown')
            ffmpeg_status = device_metric.get('ffmpeg_status', 'unknown')
            monitor_status = device_metric.get('monitor_status', 'unknown')
            ffmpeg_working_time = device_metric.get('ffmpeg_working_uptime_seconds', 0)
            monitor_working_time = device_metric.get('monitor_working_uptime_seconds', 0)
            print(f"[@host:device_debug] 📹 {device_name} ({capture_folder}): FFmpeg={ffmpeg_status}({ffmpeg_working_time}s), Monitor={monitor_status}({monitor_working_time}s)")
            
            # Store device metrics independently on host
            store_device_metrics(host.host_name, device_metric, host_system_stats)
        
        # Check which devices have running deployments
        running_deployment_devices = get_devices_with_running_deployments()
        
        # Add deployment status to device data
        devices_with_status = []
        for device in host.get_devices():
            device_dict = device.to_dict()
            device_dict['has_running_deployment'] = device.device_id in running_deployment_devices
            devices_with_status.append(device_dict)
        
        ping_data = {
            'host_name': host.host_name,
            'timestamp': time.time(),
            'device_count': host.get_device_count(),
            'system_stats': host_system_stats,  # Include host system stats in ping
            'per_device_metrics': per_device_metrics,  # Only operational status
            'devices': devices_with_status  # Include device deployment status
        }
        
        ping_url = client_registration_state['urls'].get('ping')
        if ping_url:
            response = requests.post(ping_url, json=ping_data, timeout=60)
            
            if response.status_code == 200:
                # Reset failure counter on success
                client_registration_state['ping_failures'] = 0
                print(f"📡 [HOST] Ping sent successfully at {time.strftime('%H:%M:%S')}")
            elif response.status_code == 404:
                # Check if server says we're not registered (server restart scenario)
                try:
                    response_data = response.json()
                    if response_data.get('status') == 'not_registered':
                        print("🔄 [HOST] Server reports host not registered - attempting immediate re-registration...")
                        # Don't count as failure, just try to re-register immediately
                        if register_host_with_server():
                            print("✅ [HOST] Immediate re-registration successful!")
                            client_registration_state['ping_failures'] = 0
                            return
                        else:
                            print("❌ [HOST] Immediate re-registration failed")
                except:
                    pass  # Fall through to normal failure handling
                
                # Count as normal failure if not a "not_registered" response
                client_registration_state['ping_failures'] += 1
                failure_count = client_registration_state['ping_failures']
                print(f"⚠️ [HOST] Ping failed ({failure_count}/3): {response.status_code}")
                
                # After 3 failures, try to reconnect
                if failure_count >= 3:
                    print("🔄 [HOST] 3 ping failures - attempting reconnection...")
                    try_reconnect()
            else:
                # Count failure for other status codes
                client_registration_state['ping_failures'] += 1
                failure_count = client_registration_state['ping_failures']
                print(f"⚠️ [HOST] Ping failed ({failure_count}/3): {response.status_code}")
                
                # After 3 failures, try to reconnect
                if failure_count >= 3:
                    print("🔄 [HOST] 3 ping failures - attempting reconnection...")
                    try_reconnect()
                
    except Exception as e:
        # Check if this is a connection error that might indicate server restart
        error_str = str(e).lower()
        if any(keyword in error_str for keyword in ['connection refused', 'connection error', 'timeout']):
            print(f"🔄 [HOST] Connection error detected (possible server restart): {str(e)}")
            # Try immediate re-registration for connection errors
            if register_host_with_server():
                print("✅ [HOST] Immediate re-registration after connection error successful!")
                client_registration_state['ping_failures'] = 0
                return
            else:
                print("❌ [HOST] Immediate re-registration after connection error failed")
        
        # Count failure for network errors too
        client_registration_state['ping_failures'] += 1
        failure_count = client_registration_state['ping_failures']
        print(f"⚠️ [HOST] Ping failed ({failure_count}/3): {str(e)}")
        
        # After 3 failures, try to reconnect
        if failure_count >= 3:
            print("🔄 [HOST] 3 ping failures - attempting reconnection...")
            try_reconnect()


def try_reconnect():
    """Simple reconnection: try 10 times with 20s delay"""
    global client_registration_state
    
    # Don't disable pings - let the ping function handle re-registration
    print("🔄 [HOST] Starting reconnection attempts...")
    
    for attempt in range(1, 11):  # 1 to 10
        print(f"🔍 [HOST] Reconnection attempt {attempt}/10")
        
        if register_host_with_server():
            print("✅ [HOST] Reconnection successful!")
            return
        
        if attempt < 10:  # Don't wait after last attempt
            print("⏳ [HOST] Waiting 20 seconds before next attempt...")
            time.sleep(20)
    
    print("❌ [HOST] Failed to reconnect after 10 attempts - ping will continue trying")


def unregister_from_server():
    """Unregister this host from the server."""
    global client_registration_state
    
    if not client_registration_state.get('registered'):
        return
    
    try:
        host = get_host()
        
        unregister_data = {
            'host_name': host.host_name,
            'timestamp': time.time()
        }
        
        unregister_url = client_registration_state['urls'].get('unregister')
        if unregister_url:
            response = requests.post(unregister_url, json=unregister_data, timeout=10)
            
            if response.status_code == 200:
                print("✅ [HOST] Unregistered successfully")
            else:
                print(f"⚠️ [HOST] Unregister failed: {response.status_code}")
        
        # Reset registration state
        client_registration_state.update({
            'registered': False,
            'host_name': None,
            'urls': {},
            'ping_failures': 0,
            'last_ping_time': 0
        })
        
    except Exception as e:
        print(f"❌ [HOST] Unregister error: {str(e)}")


def start_ping_thread():
    """Start the ping thread."""
    global ping_thread, ping_stop_event
    
    # Stop existing thread if running
    if ping_thread and ping_thread.is_alive():
        print("🔄 [HOST] Stopping existing ping thread...")
        ping_stop_event.set()
        ping_thread.join(timeout=2)
    
    ping_stop_event.clear()
    
    def ping_worker():
        while not ping_stop_event.is_set():
            send_ping_to_server()
            # Align to minute boundaries for synchronized data collection
            current_time = time.time()
            next_minute = (int(current_time / 60) + 1) * 60
            wait_time = next_minute - current_time
            ping_stop_event.wait(wait_time)
    
    ping_thread = threading.Thread(target=ping_worker, daemon=True)
    ping_thread.start()
    print("🔄 [HOST] Ping thread started")


def stop_ping_thread():
    """Stop the ping thread."""
    global ping_thread, ping_stop_event
    
    if ping_thread and ping_thread.is_alive():
        ping_stop_event.set()
        ping_thread.join(timeout=5)
        print("⏹️ [HOST] Ping thread stopped")


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    print(f"\n🛑 [HOST] Received signal {signum}, shutting down gracefully...")
    cleanup_on_exit()
    sys.exit(0)


def cleanup_on_exit():
    """Cleanup function called on exit."""
    print("🧹 [HOST] Cleaning up...")
    stop_ping_thread()
    unregister_from_server()
    # Host instance will be cleaned up automatically when process exits


def setup_host_signal_handlers():
    """Setup signal handlers for graceful shutdown."""
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    atexit.register(cleanup_on_exit) 


# =====================================================
# CLEAN CONTROLLER ACCESS FUNCTIONS
# =====================================================

def get_host_instance(device_ids: List[str] = None):
    """Get the host instance."""
    return get_host(device_ids)


def get_device_by_id(device_id: str):
    """Get a device by its ID."""
    host = get_host()
    return host.get_device(device_id)


def get_controller(device_id: str, controller_type: str):
    """
    Get a controller from a specific device with proper abstraction.
    
    Args:
        device_id: Device identifier (can be None for host operations - will use 'host' device)
        controller_type: Abstract controller type ('av', 'remote', 'verification', 'web', 'desktop') 
                        OR specific verification type ('verification_image', 'verification_adb', 'verification_text')
    
    Returns:
        Controller instance or None if not found
    """
    host = get_host()
    
    # If device_id is None, use the host device
    if device_id is None:
        device_id = 'host'
        print(f"[@host_utils:get_controller] Using host device for controller: {controller_type}")
    
    # Handle specific verification controller types
    if controller_type.startswith('verification_'):
        verification_impl = controller_type.replace('verification_', '')
        device = host.get_device(device_id)
        
        if not device:
            print(f"[@host_utils:get_controller] Device {device_id} not found")
            return None
        
        # Look for specific verification controller implementation
        verification_controllers = device.get_controllers('verification')
        for controller in verification_controllers:
            # Check if this controller matches the requested implementation
            if hasattr(controller, 'verification_type') and controller.verification_type == verification_impl:
                print(f"[@host_utils:get_controller] Found {verification_impl} verification controller for device {device_id}")
                return controller
        
        print(f"[@host_utils:get_controller] No {verification_impl} verification controller found for device {device_id}")
        return None
    
    # Handle abstract controller types (av, remote, verification, web, desktop)
    return host.get_controller(device_id, controller_type)


def get_remote_controller_by_type(device_id: str, remote_type: str):
    """
    Get a specific remote controller by implementation type.
    
    Args:
        device_id: Device identifier
        remote_type: Remote implementation type ('android_tv', 'ir_remote', 'android_mobile', 'appium')
    
    Returns:
        Specific remote controller instance or None if not found
    """
    host = get_host()
    
    # If device_id is None, use the host device
    if device_id is None:
        device_id = 'host'
        print(f"[@host_utils:get_remote_controller_by_type] Using host device for remote controller: {remote_type}")
    
    device = host.get_device(device_id)
    if not device:
        print(f"[@host_utils:get_remote_controller_by_type] Device {device_id} not found")
        return None
    
    # Get all remote controllers for this device
    remote_controllers = device.get_controllers('remote')
    
    # Map remote types to controller class name patterns
    controller_class_patterns = {
        'android_tv': 'AndroidTVRemoteController',
        'ir_remote': 'IRRemoteController', 
        'android_mobile': 'AndroidMobileRemoteController',
        'appium': 'AppiumRemoteController'
    }
    
    target_pattern = controller_class_patterns.get(remote_type)
    if not target_pattern:
        print(f"[@host_utils:get_remote_controller_by_type] Unknown remote type: {remote_type}")
        return None
    
    # Find controller matching the pattern
    for controller in remote_controllers:
        controller_class_name = controller.__class__.__name__
        if controller_class_name == target_pattern:
            print(f"[@host_utils:get_remote_controller_by_type] Found {remote_type} controller ({controller_class_name}) for device {device_id}")
            return controller
    
    print(f"[@host_utils:get_remote_controller_by_type] No {remote_type} controller found for device {device_id}")
    return None


def list_available_devices():
    """List all available devices."""
    host = get_host()
    return [
        {
            'device_id': device.device_id,
            'name': device.device_name,
            'model': device.device_model,
            'capabilities': device.get_capabilities()
        }
        for device in host.get_devices()
    ]


def get_device_capabilities(device_id: str):
    """Get capabilities for a specific device."""
    device = get_device_by_id(device_id)
    if device:
        return device.get_capabilities()
    return []


def has_device_capability(device_id: str, capability: str):
    """Check if a device has a specific capability."""
    capabilities = get_device_capabilities(device_id)
    return capability in capabilities
