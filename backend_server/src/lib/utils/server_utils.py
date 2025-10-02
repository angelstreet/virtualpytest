"""
Server Utilities

Host registration and management for the backend server.
Handles tracking of registered hosts without device controller dependencies.
"""

import threading
import time
import os
import psutil
import subprocess
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

# Speedtest shared cache
SPEEDTEST_CACHE = '/tmp/speedtest_cache.json'
CACHE_DURATION = 600  # 10 minutes

def get_network_speed_cached():
    """Get network speed with 10-min shared cache"""
    try:
        # Read shared cache
        if os.path.exists(SPEEDTEST_CACHE):
            with open(SPEEDTEST_CACHE, 'r') as f:
                cache = json.load(f)
            
            age = time.time() - cache['timestamp']
            if age < CACHE_DURATION:
                # Cache valid - reuse
                return {
                    'download_mbps': cache['download_mbps'],
                    'upload_mbps': cache['upload_mbps'],
                    'speedtest_last_run': datetime.fromtimestamp(cache['timestamp'], tz=timezone.utc).isoformat(),
                    'speedtest_age_seconds': int(age)
                }
        
        # Cache expired or missing - run test
        result = measure_network_speed()
        
        # Save to shared cache
        with open(SPEEDTEST_CACHE, 'w') as f:
            json.dump({
                'timestamp': time.time(),
                'download_mbps': result['download_mbps'],
                'upload_mbps': result['upload_mbps']
            }, f)
        
        return {
            'download_mbps': result['download_mbps'],
            'upload_mbps': result['upload_mbps'],
            'speedtest_last_run': datetime.now(timezone.utc).isoformat(),
            'speedtest_age_seconds': 0
        }
    except Exception as e:
        print(f"⚠️ [SPEEDTEST] Error: {e}")
        return {}  # Fail gracefully

def measure_network_speed():
    """Run speedtest with fallback strategies"""
    try:
        import speedtest
        print("🌐 [SPEEDTEST] Running network speed test...")
        
        # Initialize with timeout and secure mode disabled (helps with some ISPs)
        st = speedtest.Speedtest(secure=True)
        
        # Try to get best server with timeout
        try:
            st.get_best_server()
        except Exception as server_error:
            print(f"⚠️ [SPEEDTEST] Best server failed ({server_error}), trying manual server selection...")
            # Fallback: Try to get any available server
            servers = st.get_servers()
            if servers:
                # Use first available server
                st.get_servers(list(servers.keys())[:1])
        
        # Run tests with shorter timeout
        download = round(st.download(threads=None) / 1_000_000, 2)
        upload = round(st.upload(threads=None) / 1_000_000, 2)
        
        print(f"✅ [SPEEDTEST] Download: {download} Mbps, Upload: {upload} Mbps")
        return {
            'download_mbps': download,
            'upload_mbps': upload
        }
    except Exception as e:
        error_msg = str(e)
        # Check if it's a known blocking issue
        if '403' in error_msg or 'Forbidden' in error_msg:
            print(f"⚠️ [SPEEDTEST] Blocked by network/ISP (403 Forbidden) - skipping test")
        elif 'timeout' in error_msg.lower():
            print(f"⚠️ [SPEEDTEST] Timeout - network too slow or unavailable")
        else:
            print(f"❌ [SPEEDTEST] Failed: {e}")
        
        # Return zeros on failure (graceful degradation)
        return {'download_mbps': 0, 'upload_mbps': 0}


class HostManager:
    """Host storage and management (no locking - use lock_utils for that)"""
    
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
                    print(f"🗑️ [HostManager] Unregistered host: {host_name}")
                    return True
                else:
                    print(f"⚠️ [HostManager] Host not found for unregistration: {host_name}")
                    return False
                    
            except Exception as e:
                print(f"❌ [HostManager] Error unregistering host {host_name}: {e}")
                return False
    
    def get_host(self, host_name: str) -> Optional[Dict[str, Any]]:
        """Get host data by name"""
        with self._lock:
            return self._hosts.get(host_name)
    
    def get_all_hosts(self) -> Dict[str, Dict[str, Any]]:
        """Get all registered hosts"""
        with self._lock:
            return self._hosts.copy()
    
    def update_host_ping(self, host_name: str, ping_data: Dict[str, Any] = None) -> bool:
        """Update host's last seen time (for ping responses)"""
        with self._lock:
            if host_name in self._hosts:
                self._hosts[host_name]['last_seen'] = time.time()
                self._hosts[host_name]['status'] = 'online'
                # Optionally update additional ping data if provided
                if ping_data:
                    # Store relevant ping data (system stats, device metrics, etc.)
                    self._hosts[host_name]['last_ping_data'] = ping_data
                    
                    # Update system_stats if provided in ping (for real-time display)
                    if 'system_stats' in ping_data:
                        self._hosts[host_name]['system_stats'] = ping_data['system_stats']
                return True
            return False
    
    def cleanup_stale_hosts(self, timeout_seconds: int = 300) -> int:
        """Remove hosts that haven't been seen for timeout_seconds (default 5 minutes)"""
        with self._lock:
            current_time = time.time()
            stale_hosts = []
            
            for host_name, host_data in self._hosts.items():
                last_seen = host_data.get('last_seen', 0)
                time_since_seen = current_time - last_seen
                if time_since_seen > timeout_seconds:
                    stale_hosts.append(host_name)
                    print(f"🧹 [HostManager] Host '{host_name}' is stale (last seen {time_since_seen:.1f}s ago, timeout {timeout_seconds}s)")
            
            # Remove stale hosts
            for host_name in stale_hosts:
                del self._hosts[host_name]
                print(f"🧹 [HostManager] Removed stale host: {host_name}")
            
            return len(stale_hosts)
    
    def get_host_count(self) -> int:
        """Get total number of registered hosts"""
        with self._lock:
            return len(self._hosts)
    
    def is_host_registered(self, host_name: str) -> bool:
        """Check if a host is registered"""
        with self._lock:
            return host_name in self._hosts


# Global instance for server
_host_manager = HostManager()


def get_host_manager() -> HostManager:
    """Get the global host manager instance for server"""
    global _host_manager
    return _host_manager


def get_cpu_temperature():
    """Get CPU temperature for server with fallback to thermal zones"""
    try:
        # Method 1: vcgencmd (Raspberry Pi specific)
        result = subprocess.run(['vcgencmd', 'measure_temp'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            temp_str = result.stdout.strip()  # "temp=42.8'C"
            temp_value = float(temp_str.split('=')[1].replace("'C", ""))
            return temp_value
    except Exception:
        pass
    
    try:
        # Method 2: thermal zone (more universal Linux)
        with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
            temp_millidegrees = int(f.read().strip())
            return temp_millidegrees / 1000.0
    except Exception:
        pass
    
    return None  # Temperature not available


def get_server_system_stats():
    """Get comprehensive system statistics for the server"""
    try:
        # Get server name from environment
        server_name = os.getenv('SERVER_NAME') or 'server'
        
        stats = {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent,
            'uptime_seconds': int(time.time() - psutil.boot_time()),
            'platform': os.uname().sysname if hasattr(os, 'uname') else 'unknown',
            'architecture': os.uname().machine if hasattr(os, 'uname') else 'unknown',
            'timestamp': datetime.now().isoformat(),
            'server_name': server_name  # Add server name for grouping
        }
        
        # Add CPU temperature if available
        cpu_temp = get_cpu_temperature()
        if cpu_temp is not None:
            stats['cpu_temperature_celsius'] = round(cpu_temp, 1)
        
        # Add network speed (cached)
        network_speed = get_network_speed_cached()
        stats.update(network_speed)
        
        return stats
    except Exception as e:
        print(f"❌ Error getting server system stats: {e}")
        return {
            'cpu_percent': 0,
            'memory_percent': 0,
            'disk_percent': 0,
            'uptime_seconds': 0,
            'platform': 'unknown',
            'architecture': 'unknown',
            'timestamp': datetime.now().isoformat()
        }
