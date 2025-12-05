"""
UI Control Tool - Navigate user's browser
"""
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

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
    # Import socket_manager lazily to avoid circular imports
    from ..socket_manager import socket_manager
    
    logger.info(f"🤖 navigate_to_page called: page_name={page_name}")
    logger.info(f"🤖 socket_manager.socketio initialized: {socket_manager.socketio is not None}")
    
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
        logger.warning(f"🤖 Unknown page: {page_name}")
        return f"Error: Unknown page '{page_name}'. Available: {', '.join(routes.keys())}"
    
    logger.info(f"🤖 Resolved path: {path}")
    
    # Emit the event (broadcast to all connected clients in /agent namespace)
    if socket_manager.socketio:
        logger.info(f"🤖 Broadcasting ui_action to /agent namespace...")
        result = socket_manager.broadcast(
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
        logger.info(f"🤖 Broadcast result: {result}")
        return f"Navigated user to {page_name} ({path})"
    
    logger.error("🤖 Socket manager not initialized!")
    return "Error: Socket manager not initialized"
