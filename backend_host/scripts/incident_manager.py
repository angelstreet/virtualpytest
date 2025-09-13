#!/usr/bin/env python3
"""
Simple incident manager - state machine + DB operations
Single thread, minimal complexity
"""
import os
import sys
import logging
from datetime import datetime

# Add project paths
current_dir = os.path.dirname(os.path.abspath(__file__))  # backend_host/scripts/
backend_host_dir = os.path.dirname(current_dir)           # backend_host/
project_root = os.path.dirname(backend_host_dir)          # project root

sys.path.insert(0, project_root)

# Lazy import to reduce startup time
create_alert_safe = None
resolve_alert = None

def _lazy_import_db():
    """Lazy import database functions only when needed."""
    global create_alert_safe, resolve_alert
    if create_alert_safe is None:
        try:
            from shared.lib.supabase.alerts_db import create_alert_safe as _create_alert_safe, resolve_alert as _resolve_alert
            create_alert_safe = _create_alert_safe
            resolve_alert = _resolve_alert
            logger.info("Database functions imported successfully")
        except ImportError as e:
            logger.warning(f"Could not import alerts_db module: {e}. Database operations will be skipped.")
            create_alert_safe = False  # Mark as attempted
            resolve_alert = False

# Use same logger as capture_monitor
logger = logging.getLogger('capture_monitor')

# Simple states
NORMAL = 0
INCIDENT = 1

class IncidentManager:
    def __init__(self):
        self.device_states = {}  # {device_id: {state: int, active_incidents: {type: incident_id}}}
        
    def get_device_state(self, device_id):
        """Get current state for device"""
        if device_id not in self.device_states:
            self.device_states[device_id] = {
                'state': NORMAL,
                'active_incidents': {}
            }
        return self.device_states[device_id]
    
    def create_incident(self, device_id, issue_type, host_name):
        """Create new incident in DB using original working method"""
        try:
            logger.info(f"[{device_id}] DB INSERT: Creating {issue_type} incident")
            
            # Use lazy import exactly as before
            _lazy_import_db()
            if not create_alert_safe or create_alert_safe is False:
                logger.warning("Database module not available, skipping alert creation")
                return None
            
            # Call database exactly as before
            result = create_alert_safe(
                host_name=host_name,
                device_id=device_id,
                incident_type=issue_type,
                consecutive_count=1,  # Always start with 1
                metadata={}
            )
            
            if result.get('success'):
                alert_id = result.get('alert_id')
                logger.info(f"[{device_id}] DB INSERT SUCCESS: Created alert {alert_id}")
                return alert_id
            else:
                logger.error(f"[{device_id}] DB INSERT FAILED: {result.get('error')}")
                return None
            
        except Exception as e:
            logger.error(f"[{device_id}] DB ERROR: Failed to create {issue_type} incident: {e}")
            return None
    
    def resolve_incident(self, device_id, incident_id, issue_type):
        """Resolve incident in DB using original working method"""
        try:
            logger.info(f"[{device_id}] DB UPDATE: Resolving incident {incident_id}")
            
            # Use lazy import exactly as before
            _lazy_import_db()
            if not resolve_alert or resolve_alert is False:
                logger.warning(f"[{device_id}] Database module not available, skipping alert resolution")
                return False
            
            # Call database exactly as before
            result = resolve_alert(incident_id)
            
            if result.get('success'):
                logger.info(f"[{device_id}] DB UPDATE SUCCESS: Resolved alert {incident_id}")
                return True
            else:
                logger.error(f"[{device_id}] DB UPDATE FAILED: {result.get('error')}")
                return False
            
        except Exception as e:
            logger.error(f"[{device_id}] DB ERROR: Failed to resolve incident {incident_id}: {e}")
            return False
    
    def process_detection(self, device_id, detection_result, host_name):
        """Process detection result and update state"""
        device_state = self.get_device_state(device_id)
        active_incidents = device_state['active_incidents']
        
        # Check each issue type
        for issue_type in ['blackscreen', 'freeze', 'audio_loss']:
            is_detected = detection_result.get(issue_type, False)
            was_active = issue_type in active_incidents
            
            if is_detected and not was_active:
                # New incident
                incident_id = self.create_incident(device_id, issue_type, host_name)
                if incident_id:
                    active_incidents[issue_type] = incident_id
                    device_state['state'] = INCIDENT
                    
            elif not is_detected and was_active:
                # Resolve incident
                incident_id = active_incidents[issue_type]
                self.resolve_incident(device_id, incident_id, issue_type)
                del active_incidents[issue_type]
                
                # If no more active incidents, back to normal
                if not active_incidents:
                    device_state['state'] = NORMAL
        
        logger.debug(f"[{device_id}] State: {device_state['state']}, Active: {list(active_incidents.keys())}")
