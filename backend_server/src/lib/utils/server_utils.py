"""
Server Utilities

Host registration and management for the backend server.
Handles tracking of registered hosts without device controller dependencies.
"""

import threading
import time
from datetime import datetime
from typing import Dict, Any, Optional, List


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
    
    def update_host_ping(self, host_name: str) -> bool:
        """Update host's last seen time (for ping responses)"""
        with self._lock:
            if host_name in self._hosts:
                self._hosts[host_name]['last_seen'] = time.time()
                self._hosts[host_name]['status'] = 'online'
                return True
            return False
    
    def cleanup_stale_hosts(self, timeout_seconds: int = 120) -> int:
        """Remove hosts that haven't been seen for timeout_seconds"""
        with self._lock:
            current_time = time.time()
            stale_hosts = []
            
            for host_name, host_data in self._hosts.items():
                last_seen = host_data.get('last_seen', 0)
                if current_time - last_seen > timeout_seconds:
                    stale_hosts.append(host_name)
            
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
