#!/usr/bin/env python3
"""
Simple incident manager - state machine + DB operations
Single thread, minimal complexity
"""
import os
import sys
from datetime import datetime

# Add project paths
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, project_root)

from shared.lib.supabase.supabase_client import get_supabase_client

# Simple states
NORMAL = 0
INCIDENT = 1

class IncidentManager:
    def __init__(self):
        self.device_states = {}  # {device_id: {state: int, active_incidents: {type: incident_id}}}
        self.db = get_supabase_client()
        
    def get_device_state(self, device_id):
        """Get current state for device"""
        if device_id not in self.device_states:
            self.device_states[device_id] = {
                'state': NORMAL,
                'active_incidents': {}
            }
        return self.device_states[device_id]
    
    def create_incident(self, device_id, issue_type, host_name):
        """Create new incident in DB"""
        try:
            result = self.db.table('alerts').insert({
                'host_name': host_name,
                'device_id': device_id,
                'incident_type': issue_type,
                'status': 'active',
                'consecutive_count': 1,
                'start_time': datetime.now().isoformat(),
                'metadata': {}
            }).execute()
            
            if result.data:
                incident_id = result.data[0]['id']
                print(f"[{device_id}] Created {issue_type} incident: {incident_id}")
                return incident_id
        except Exception as e:
            print(f"[{device_id}] DB error creating incident: {e}")
        return None
    
    def resolve_incident(self, device_id, incident_id, issue_type):
        """Resolve incident in DB"""
        try:
            self.db.table('alerts').update({
                'status': 'resolved',
                'end_time': datetime.now().isoformat()
            }).eq('id', incident_id).execute()
            
            print(f"[{device_id}] Resolved {issue_type} incident: {incident_id}")
        except Exception as e:
            print(f"[{device_id}] DB error resolving incident: {e}")
    
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
        
        print(f"[{device_id}] State: {device_state['state']}, Active: {list(active_incidents.keys())}")
