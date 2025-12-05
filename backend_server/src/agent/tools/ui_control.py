from typing import Optional, Dict, Any
from ..socket_manager import SocketManager

# Global reference to socket manager
_socket_manager: Optional[SocketManager] = None

def set_socket_manager(manager: SocketManager):
    global _socket_manager
    _socket_manager = manager

def navigate_to_page(page_name: str, context: Optional[Dict[str, Any]] = None) -> str:
    """
    Navigates the user's UI to a specific page.
    
    Args:
        page_name: One of:
            - 'dashboard': Main dashboard
            - 'device_control': Device control/streaming page
            - 'reports': Test execution reports
            - 'campaigns': Campaign editor
            - 'settings': System settings
            - 'monitor': System monitoring/Grafana
        context: Optional parameters to pass (e.g., {'device_id': 'pixel-5'})
    """
    global _socket_manager
    
    # Map friendly names to actual routes
    routes = {
        'dashboard': '/',
        'device_control': '/device-control',
        'reports': '/test-results/reports',
        'campaigns': '/test-plan/campaigns',
        'settings': '/configuration/settings',
        'monitor': '/monitoring/system'
    }
    
    path = routes.get(page_name)
    if not path:
        return f"Error: Unknown page '{page_name}'. Available: {', '.join(routes.keys())}"
    
    # Emit the event
    if _socket_manager:
        _socket_manager.emit_to_room(
            'agent_sessions', # Broadcast to all agent sessions or specific session if context has it
            'ui_action',
            {
                "action": "navigate",
                "payload": {
                    "path": path,
                    "context": context or {}
                },
                "agent_message": f"Navigating to {page_name}..."
            }
        )
        return f"Navigated user to {page_name} ({path})"
    
    return "Error: Socket manager not initialized"
