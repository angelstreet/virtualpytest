"""
Page Interaction Tools for AI Agent

Provides generic tools for AI to interact with any page element
based on the page schema, without hard-coding each action.
"""

import logging
from typing import Dict, Any, Optional, List
from ..socket_manager import socket_manager

logger = logging.getLogger(__name__)

# Mirror of frontend PAGE_SCHEMAS - key pages and their elements
# This should stay in sync with frontend/src/lib/ai/pageSchema.ts
PAGE_SCHEMAS = {
    '/': {
        'name': 'Dashboard',
        'description': 'Overview of system status, hosts, devices',
        'elements': ['host-accordion', 'refresh-btn', 'restart-service-btn', 'restart-stream-btn'],
    },
    '/device-control': {
        'name': 'Device Control',
        'description': 'View and control connected devices with live streams',
        'elements': ['device-grid', 'host-filter', 'model-filter', 'stream-modal'],
    },
    '/test-execution/run-tests': {
        'name': 'Run Tests',
        'description': 'Execute test cases on devices',
        'elements': ['host-selector', 'device-selector', 'script-selector', 'run-btn', 'execution-table'],
    },
    '/test-execution/run-campaigns': {
        'name': 'Run Campaigns',
        'description': 'Execute multi-device test campaigns',
        'elements': ['campaign-stepper', 'script-sequence', 'launch-btn', 'history-table'],
    },
    '/test-plan/test-cases': {
        'name': 'Test Cases',
        'description': 'Manage test cases',
        'elements': ['testcase-table', 'interface-filter', 'create-btn', 'search-input'],
    },
    '/test-plan/campaigns': {
        'name': 'Campaigns',
        'description': 'Manage campaign definitions',
        'elements': ['campaign-table', 'create-btn'],
    },
    '/monitoring/incidents': {
        'name': 'Incidents',
        'description': 'View and manage alerts',
        'elements': ['active-alerts-table', 'closed-alerts-table', 'freeze-modal'],
    },
    '/monitoring/heatmap': {
        'name': 'Heatmap',
        'description': 'Real-time device health monitoring',
        'elements': ['mosaic-player', 'timeline-slider', 'status-filter', 'analysis-table'],
    },
    '/test-results/reports': {
        'name': 'Test Reports',
        'description': 'View test execution reports',
        'elements': ['reports-table', 'detail-toggle', 'stats-cards'],
    },
    '/test-results/campaign-reports': {
        'name': 'Campaign Reports',
        'description': 'View campaign results',
        'elements': ['campaign-reports-table', 'trend-chart'],
    },
    '/builder/test-builder': {
        'name': 'Test Builder',
        'description': 'Visual test case builder',
        'elements': ['step-canvas', 'action-palette', 'save-btn', 'device-preview'],
    },
    '/configuration/settings': {
        'name': 'Settings',
        'description': 'System configuration',
        'elements': ['settings-form', 'save-btn'],
    },
    '/ai-agent': {
        'name': 'AI Agent Chat',
        'description': 'Interactive AI assistant',
        'elements': ['chat-input', 'chat-history', 'mode-selector'],
    },
}

# Navigation aliases for natural language
NAVIGATION_ALIASES = {
    'dashboard': '/',
    'home': '/',
    'device control': '/device-control',
    'devices': '/device-control',
    'rec': '/device-control',
    'streams': '/device-control',
    'run tests': '/test-execution/run-tests',
    'execute tests': '/test-execution/run-tests',
    'test execution': '/test-execution/run-tests',
    'run campaigns': '/test-execution/run-campaigns',
    'campaigns': '/test-plan/campaigns',
    'test cases': '/test-plan/test-cases',
    'testcases': '/test-plan/test-cases',
    'incidents': '/monitoring/incidents',
    'alerts': '/monitoring/incidents',
    'heatmap': '/monitoring/heatmap',
    'monitoring': '/monitoring/heatmap',
    'reports': '/test-results/reports',
    'test reports': '/test-results/reports',
    'campaign reports': '/test-results/campaign-reports',
    'test builder': '/builder/test-builder',
    'builder': '/builder/test-builder',
    'settings': '/configuration/settings',
    'config': '/configuration/settings',
    'ai agent': '/ai-agent',
    'chat': '/ai-agent',
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
        page_name: Page name or path. Examples: 'dashboard', 'device control', 'reports', 
                   '/test-execution/run-tests', 'heatmap', 'incidents'
        context: Optional parameters (e.g., {'device_id': 's21'})
    
    Available pages: dashboard, device control, run tests, run campaigns, test cases,
                     campaigns, incidents, heatmap, reports, campaign reports, 
                     test builder, settings, ai agent
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


# Export all tools
PAGE_INTERACTION_TOOLS = [
    "get_available_pages",
    "get_page_schema", 
    "navigate_to_page",
    "interact_with_element",
    "highlight_element",
    "show_toast",
]

