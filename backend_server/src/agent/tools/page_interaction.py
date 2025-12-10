"""
Page Interaction Tools for AI Agent

Provides generic tools for AI to interact with any page element
based on the page schema, without hard-coding each action.
"""

import logging
import requests
from typing import Dict, Any, Optional, List
from ..socket_manager import socket_manager

logger = logging.getLogger(__name__)

# Backend API base URL (same server)
BACKEND_API_BASE = "http://localhost:5109"

# Mirror of frontend PAGE_SCHEMAS - key pages and their elements
# This should stay in sync with frontend/src/lib/ai/pageSchema.ts
PAGE_SCHEMAS = {
    '/device-control': {
        'name': 'Device Control',
        'description': 'View and control connected devices with live streams',
        'elements': ['device-grid', 'host-filter', 'model-filter', 'stream-modal'],
    },
    '/monitoring/heatmap': {
        'name': 'Heatmap',
        'description': 'Real-time device health monitoring',
        'elements': ['mosaic-player', 'timeline-slider', 'status-filter', 'analysis-table'],
    },
    '/builder/test-builder': {
        'name': 'Test Builder',
        'description': 'Visual test case builder',
        'elements': ['step-canvas', 'action-palette', 'save-btn', 'device-preview'],
    },
    '/builder/campaign-builder': {
        'name': 'Campaign Builder',
        'description': 'Create and manage test campaigns',
        'elements': ['campaign-canvas', 'script-sequence', 'device-selector', 'save-campaign-btn'],
    },
    '/builder/navigation-editor': {
        'name': 'Navigation Editor',
        'description': 'Edit and manage navigation trees',
        'elements': ['tree-canvas', 'node-editor', 'edge-editor', 'save-navigation-btn'],
    },
}

# Navigation aliases for natural language
NAVIGATION_ALIASES = {
    'device control': '/device-control',
    'device-control': '/device-control',
    'devices': '/device-control',
    'device': '/device-control',
    'rec': '/device-control',
    'streams': '/device-control',
    'live': '/device-control',
    'heatmap': '/monitoring/heatmap',
    'monitoring': '/monitoring/heatmap',
    'test builder': '/builder/test-builder',
    'builder': '/builder/test-builder',
    'campaign builder': '/builder/campaign-builder',
    'campaign-builder': '/builder/campaign-builder',
    'navigation editor': '/builder/navigation-editor',
    'navigation-editor': '/builder/navigation-editor',
    'navigation': '/builder/navigation-editor',
}


def get_available_pages() -> str:
    """
    Returns a list of all navigable pages with their descriptions.
    Use this to understand what pages exist in the application.
    """
    logger.info("🔍 get_available_pages called")
    
    lines = ["📄 Available Pages:\n"]
    for path, info in PAGE_SCHEMAS.items():
        lines.append(f"- **{info['name']}** ({path})")
        lines.append(f"  {info['description']}")
        lines.append(f"  Elements: {', '.join(info['elements'][:4])}{'...' if len(info['elements']) > 4 else ''}")
        lines.append("")
    
    return "\n".join(lines)


def get_page_schema(page_path: str) -> str:
    """
    Returns the interactive elements available on a specific page.
    
    Args:
        page_path: The page path (e.g., '/device-control', '/test-results/reports')
    """
    logger.info(f"🔍 get_page_schema called: page_path={page_path}")
    
    schema = PAGE_SCHEMAS.get(page_path)
    if not schema:
        # Try to find by name
        for path, info in PAGE_SCHEMAS.items():
            if info['name'].lower() == page_path.lower():
                schema = info
                page_path = path
                break
    
    if not schema:
        return f"❌ Page '{page_path}' not found. Use get_available_pages() to see available pages."
    
    lines = [
        f"📄 **{schema['name']}** ({page_path})",
        f"Description: {schema['description']}",
        "",
        "Interactive Elements:",
    ]
    
    for elem_id in schema['elements']:
        lines.append(f"  - {elem_id}")
    
    return "\n".join(lines)


def navigate_to_page(page_name: str, context: Optional[Dict[str, Any]] = None) -> str:
    """
    Navigates the user's browser to a specific page.
    
    Args:
        page_name: Page name or path. Examples: 'device control', 'heatmap', 
                   'test builder', 'campaign builder', 'navigation editor'
        context: Optional parameters (e.g., {'device_id': 's21'})
    
    Available pages: device control, heatmap, test builder, campaign builder, navigation editor
    """
    logger.info(f"🤖 navigate_to_page called: page_name={page_name}, context={context}")
    
    # Normalize input
    normalized = page_name.lower().strip()
    
    # Check aliases first
    path = NAVIGATION_ALIASES.get(normalized)
    
    # If not in aliases, check if it's a direct path
    if not path:
        if normalized.startswith('/'):
            if normalized in PAGE_SCHEMAS:
                path = normalized
        else:
            # Try to match partial name
            for alias, alias_path in NAVIGATION_ALIASES.items():
                if normalized in alias or alias in normalized:
                    path = alias_path
                    break
    
    if not path:
        available = list(NAVIGATION_ALIASES.keys())
        return f"❌ Cannot navigate to '{page_name}'. Available pages: {', '.join(sorted(set(available)))}"
    
    # Emit navigation event
    if not socket_manager.socketio:
        logger.error("🤖 Socket manager not initialized!")
        return "❌ Backend UI control system not ready."
    
    page_info = PAGE_SCHEMAS.get(path, {})
    page_display_name = page_info.get('name', page_name)
    
    socket_manager.broadcast(
        'ui_action',
        {
            "action": "navigate",
            "payload": {"path": path, "context": context},
            "agent_message": f"Navigating to {page_display_name}..."
        },
        namespace='/agent'
    )
    
    logger.info(f"🟢 Broadcasting 'ui_action' to navigate to {page_display_name} (path: {path})")
    return f"✅ Navigated to {page_display_name} ({path})"


def interact_with_element(element_id: str, action: str, params: Optional[Dict[str, Any]] = None) -> str:
    """
    Interact with a specific element on the current page.
    
    Args:
        element_id: The element ID from the page schema (e.g., 'reports-table', 'run-btn')
        action: The action to perform (e.g., 'click', 'select', 'filter', 'open')
        params: Optional parameters for the action (e.g., {'value': 'failed'}, {'row_id': '123'})
    
    Common actions:
        - click: Click a button
        - select: Select an item in a dropdown or table row
        - filter: Apply a filter
        - open: Open a modal or expand a section
        - close: Close a modal or collapse a section
        - type: Type text into an input
        - scroll_to: Scroll to make element visible
    """
    logger.info(f"🤖 interact_with_element called: element={element_id}, action={action}, params={params}")
    
    if not socket_manager.socketio:
        logger.error("🤖 Socket manager not initialized!")
        return "❌ Backend UI control system not ready."
    
    socket_manager.broadcast(
        'ui_action',
        {
            "action": "interact",
            "payload": {
                "element_id": element_id,
                "action": action,
                "params": params or {}
            },
            "agent_message": f"Interacting with {element_id}: {action}"
        },
        namespace='/agent'
    )
    
    logger.info(f"🟢 Broadcasting 'ui_action' for element interaction: {element_id}.{action}")
    return f"✅ Triggered {action} on {element_id}"


def highlight_element(element_id: str, duration_ms: int = 2000) -> str:
    """
    Highlight an element on the page to draw user's attention.
    
    Args:
        element_id: The element ID to highlight
        duration_ms: How long to show the highlight (default 2000ms)
    """
    logger.info(f"🤖 highlight_element called: element={element_id}, duration={duration_ms}ms")
    
    if not socket_manager.socketio:
        return "❌ Backend UI control system not ready."
    
    socket_manager.broadcast(
        'ui_action',
        {
            "action": "highlight",
            "payload": {
                "element_id": element_id,
                "duration_ms": duration_ms
            },
            "agent_message": f"Highlighting {element_id}"
        },
        namespace='/agent'
    )
    
    return f"✅ Highlighting {element_id} for {duration_ms}ms"


def show_toast(message: str, severity: str = "info") -> str:
    """
    Show a toast notification to the user.
    
    Args:
        message: The message to display
        severity: One of 'info', 'success', 'warning', 'error'
    """
    logger.info(f"🤖 show_toast called: message={message}, severity={severity}")
    
    if not socket_manager.socketio:
        return "❌ Backend UI control system not ready."
    
    socket_manager.broadcast(
        'ui_action',
        {
            "action": "toast",
            "payload": {
                "message": message,
                "severity": severity
            }
        },
        namespace='/agent'
    )
    
    return f"✅ Showed toast: {message}"


def get_alerts(
    status: Optional[str] = None,
    host_name: Optional[str] = None,
    device_id: Optional[str] = None,
    incident_type: Optional[str] = None,
    limit: int = 20
) -> str:
    """
    Fetch alerts from the monitoring system.
    
    Args:
        status: Filter by status ('active' or 'resolved'). If not set, returns both.
        host_name: Filter by specific host
        device_id: Filter by specific device
        incident_type: Filter by incident type (e.g., 'freeze', 'blackscreen')
        limit: Maximum number of alerts to return (default 20)
    
    Returns:
        Summary of alerts with counts and details
    """
    logger.info(f"🔍 get_alerts called: status={status}, host={host_name}, device={device_id}, type={incident_type}, limit={limit}")
    
    try:
        # Determine which endpoint to call based on status filter
        if status == 'active':
            url = f"{BACKEND_API_BASE}/server/alerts/getActiveAlerts"
            params = {}
        elif status == 'resolved':
            url = f"{BACKEND_API_BASE}/server/alerts/getClosedAlerts"
            params = {}
        else:
            # Get all alerts (both active and resolved)
            url = f"{BACKEND_API_BASE}/server/alerts/getAllAlerts"
            params = {
                'active_limit': limit,
                'resolved_limit': limit
            }
        
        # Add optional filters
        if host_name:
            params['host_name'] = host_name
        if device_id:
            params['device_id'] = device_id
        if incident_type:
            params['incident_type'] = incident_type
            
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if not data.get('success', False):
            return f"❌ Error fetching alerts: {data.get('error', 'Unknown error')}"
        
        # Format the response - handle different endpoint response formats
        alerts = data.get('alerts', [])
        total_count = data.get('count', len(alerts))
        
        # For filtered queries (active/resolved), the count IS the filtered count
        if status == 'active':
            active_count = total_count
            resolved_count = 0
        elif status == 'resolved':
            active_count = 0
            resolved_count = total_count
        else:
            # getAllAlerts returns both counts
            active_count = data.get('active_count', 0)
            resolved_count = data.get('resolved_count', 0)
        
        # Build summary based on what was requested
        lines = [f"📊 **Alert Summary**"]
        if status == 'active':
            lines.append(f"- **Active alerts**: {active_count}")
        elif status == 'resolved':
            lines.append(f"- **Resolved alerts**: {resolved_count}")
        else:
            lines.append(f"- **Active alerts**: {active_count}")
            lines.append(f"- **Resolved alerts**: {resolved_count}")
            lines.append(f"- **Total**: {total_count}")
        
        if alerts:
            lines.append("")
            lines.append("**Recent Alerts:**")
            
            # Show up to 10 alerts with details
            for i, alert in enumerate(alerts[:10]):
                alert_status = alert.get('status', 'unknown')
                status_icon = "🔴" if alert_status == 'active' else "✅"
                incident = alert.get('incident_type', 'unknown')
                host = alert.get('host_name', 'unknown')
                device = alert.get('device_id', 'unknown')
                start = alert.get('start_time', 'unknown')[:19] if alert.get('start_time') else 'unknown'
                
                lines.append(f"{status_icon} **{incident}** on {host}/{device} - Started: {start}")
            
            if len(alerts) > 10:
                lines.append(f"... and {len(alerts) - 10} more alerts")
        
        return "\n".join(lines)
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching alerts: {e}")
        return f"❌ Error fetching alerts: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error in get_alerts: {e}")
        return f"❌ Error: {str(e)}"


# Export all tools
PAGE_INTERACTION_TOOLS = [
    "get_available_pages",
    "get_page_schema", 
    "navigate_to_page",
    "interact_with_element",
    "highlight_element",
    "show_toast",
    "get_alerts",
]

