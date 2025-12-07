"""
Alert Data Tools for AI Agent

Provides tools for the AI to fetch alert/incident data from the database.
These complement the navigation tools - navigate to show context, then fetch data.
"""

import logging
from typing import Dict, Any, Optional, List

# Import database functions
from shared.src.lib.database.alerts_db import (
    get_all_alerts,
    get_active_alerts,
    get_closed_alerts,
)

logger = logging.getLogger(__name__)


def get_alert_summary(
    host_name: Optional[str] = None,
    device_id: Optional[str] = None,
    incident_type: Optional[str] = None
) -> str:
    """
    Get a summary of alerts (counts and breakdown).
    Use this to answer "how many alerts?" questions.
    
    Args:
        host_name: Optional filter by host
        device_id: Optional filter by device
        incident_type: Optional filter by type (e.g., 'blackscreen', 'freeze')
    
    Returns:
        Summary string with alert counts
    """
    logger.info(f"🔍 get_alert_summary called: host={host_name}, device={device_id}, type={incident_type}")
    
    try:
        result = get_all_alerts(
            host_name=host_name,
            device_id=device_id,
            incident_type=incident_type,
            active_limit=100,
            resolved_limit=100
        )
        
        if not result.get('success'):
            return f"❌ Failed to fetch alerts: {result.get('error', 'Unknown error')}"
        
        active_count = result.get('active_count', 0)
        resolved_count = result.get('resolved_count', 0)
        total_count = result.get('count', 0)
        
        # Build summary
        lines = [
            f"📊 **Alert Summary**",
            f"",
            f"- **Active Alerts**: {active_count}",
            f"- **Closed/Resolved Alerts**: {resolved_count}",
            f"- **Total**: {total_count}",
        ]
        
        # Add filter info if applied
        filters = []
        if host_name:
            filters.append(f"host: {host_name}")
        if device_id:
            filters.append(f"device: {device_id}")
        if incident_type:
            filters.append(f"type: {incident_type}")
        
        if filters:
            lines.append(f"")
            lines.append(f"Filters applied: {', '.join(filters)}")
        
        return "\n".join(lines)
        
    except Exception as e:
        logger.error(f"Error in get_alert_summary: {e}")
        return f"❌ Error fetching alert summary: {str(e)}"


def list_alerts(
    status: str = "all",
    host_name: Optional[str] = None,
    device_id: Optional[str] = None,
    incident_type: Optional[str] = None,
    limit: int = 20
) -> str:
    """
    List alerts with details.
    
    Args:
        status: Filter by status - "active", "closed", or "all" (default: "all")
        host_name: Optional filter by host
        device_id: Optional filter by device
        incident_type: Optional filter by type
        limit: Maximum number of alerts to return (default: 20)
    
    Returns:
        Formatted list of alerts
    """
    logger.info(f"🔍 list_alerts called: status={status}, limit={limit}")
    
    try:
        # Fetch based on status filter
        if status.lower() == "active":
            result = get_active_alerts()
            alerts = result.get('alerts', [])[:limit]
        elif status.lower() == "closed":
            result = get_closed_alerts()
            alerts = result.get('alerts', [])[:limit]
        else:
            result = get_all_alerts(
                host_name=host_name,
                device_id=device_id,
                incident_type=incident_type,
                active_limit=limit,
                resolved_limit=limit
            )
            alerts = result.get('alerts', [])[:limit]
        
        if not result.get('success'):
            return f"❌ Failed to fetch alerts: {result.get('error', 'Unknown error')}"
        
        if not alerts:
            return f"✅ No {status} alerts found."
        
        # Format alerts
        lines = [f"📋 **{status.title()} Alerts** (showing {len(alerts)} of {result.get('count', len(alerts))}):", ""]
        
        for i, alert in enumerate(alerts, 1):
            alert_id = alert.get('id', 'N/A')[:8]
            incident_type_val = alert.get('incident_type', 'Unknown')
            device = alert.get('device_id', 'Unknown')
            host = alert.get('host_name', 'Unknown')
            created = alert.get('created_at', 'Unknown')[:19] if alert.get('created_at') else 'Unknown'
            is_resolved = alert.get('is_resolved', False)
            status_icon = "✅" if is_resolved else "🔴"
            
            lines.append(f"{i}. {status_icon} **{incident_type_val}** on `{device}@{host}`")
            lines.append(f"   ID: {alert_id}... | Created: {created}")
        
        return "\n".join(lines)
        
    except Exception as e:
        logger.error(f"Error in list_alerts: {e}")
        return f"❌ Error listing alerts: {str(e)}"


def get_alert_details(alert_id: str) -> str:
    """
    Get detailed information about a specific alert.
    
    Args:
        alert_id: The alert ID (full or partial)
    
    Returns:
        Detailed alert information
    """
    logger.info(f"🔍 get_alert_details called: alert_id={alert_id}")
    
    try:
        # Fetch all alerts and find matching one
        result = get_all_alerts(active_limit=500, resolved_limit=500)
        
        if not result.get('success'):
            return f"❌ Failed to fetch alerts: {result.get('error', 'Unknown error')}"
        
        alerts = result.get('alerts', [])
        
        # Find matching alert (partial ID match)
        matching = [a for a in alerts if alert_id.lower() in str(a.get('id', '')).lower()]
        
        if not matching:
            return f"❌ Alert with ID '{alert_id}' not found."
        
        if len(matching) > 1:
            return f"⚠️ Multiple alerts match '{alert_id}'. Please be more specific."
        
        alert = matching[0]
        
        # Format detailed info
        lines = [
            f"📋 **Alert Details**",
            f"",
            f"- **ID**: {alert.get('id', 'N/A')}",
            f"- **Type**: {alert.get('incident_type', 'Unknown')}",
            f"- **Device**: {alert.get('device_id', 'Unknown')}",
            f"- **Host**: {alert.get('host_name', 'Unknown')}",
            f"- **Status**: {'Resolved ✅' if alert.get('is_resolved') else 'Active 🔴'}",
            f"- **Created**: {alert.get('created_at', 'Unknown')}",
        ]
        
        if alert.get('resolved_at'):
            lines.append(f"- **Resolved**: {alert.get('resolved_at')}")
        
        if alert.get('screenshot_url'):
            lines.append(f"- **Screenshot**: {alert.get('screenshot_url')}")
        
        if alert.get('description'):
            lines.append(f"- **Description**: {alert.get('description')}")
        
        return "\n".join(lines)
        
    except Exception as e:
        logger.error(f"Error in get_alert_details: {e}")
        return f"❌ Error fetching alert details: {str(e)}"


# Export all tools
ALERT_TOOLS = [
    "get_alert_summary",
    "list_alerts",
    "get_alert_details",
]

