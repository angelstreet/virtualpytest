"""
Device Service

Handles device management business logic that was previously in routes.
This service manages devices, controllers, and environment profiles.
"""

from typing import Dict, Any, List, Optional
from shared.src.lib.supabase.devices_db import (
    get_all_devices, get_device, save_device as create_device, 
    delete_device
)
from shared.src.lib.utils.app_utils import check_supabase

class DeviceService:
    """Service for handling device management business logic"""
    
    def check_device_name_exists(self, name: str, team_id: str, exclude_device_id: str = None) -> bool:
        """Check if a device name already exists for the team"""
        try:
            devices = get_all_devices(team_id)
            for device in devices:
                if device.get('name') == name:
                    if exclude_device_id and device.get('id') == exclude_device_id:
                        continue
                    return True
            return False
        except Exception:
            return False
    
    def update_device(self, device_id: str, device_data: Dict[str, Any], team_id: str) -> Optional[Dict[str, Any]]:
        """Update an existing device"""
        try:
            # Get the existing device
            existing_device = get_device(device_id, team_id)
            if not existing_device:
                return None
                
            # Update the device data
            updated_data = {**existing_device, **device_data}
            updated_data['id'] = device_id
            
            # Save the updated device
            return create_device(updated_data, team_id)
        except Exception as e:
            print(f"[DeviceService] Error updating device: {e}")
            return None
    
    def get_all_devices(self, team_id: str) -> Dict[str, Any]:
        """Get all devices for a team"""
        try:
            if not team_id:
                return {
                    'success': False,
                    'error': 'team_id is required',
                    'status_code': 400
                }
            
            print(f"[DeviceService] Getting all devices for team: {team_id}")
            
            # Check if Supabase is available
            supabase_error = check_supabase()
            if supabase_error:
                return {
                    'success': False,
                    'error': f'Database not available: {supabase_error}',
                    'status_code': 503
                }
            
            devices = get_all_devices(team_id)
            
            print(f"[DeviceService] Found {len(devices)} devices")
            
            return {
                'success': True,
                'devices': devices,
                'count': len(devices)
            }
            
        except Exception as e:
            print(f"[DeviceService] Exception: {e}")
            return {
                'success': False,
                'error': f'Service error: {str(e)}',
                'status_code': 500
            }
    
    def get_device(self, device_id: str, team_id: str) -> Dict[str, Any]:
        """Get a specific device"""
        try:
            if not device_id or not team_id:
                return {
                    'success': False,
                    'error': 'device_id and team_id are required',
                    'status_code': 400
                }
            
            print(f"[DeviceService] Getting device: {device_id}")
            
            device = get_device(device_id, team_id)
            
            if device:
                return {
                    'success': True,
                    'device': device
                }
            else:
                return {
                    'success': False,
                    'error': 'Device not found',
                    'status_code': 404
                }
                
        except Exception as e:
            print(f"[DeviceService] Exception: {e}")
            return {
                'success': False,
                'error': f'Service error: {str(e)}',
                'status_code': 500
            }
    
    def save_device(self, device_data: Dict[str, Any], team_id: str) -> Dict[str, Any]:
        """Create or update a device"""
        try:
            if not device_data or not team_id:
                return {
                    'success': False,
                    'error': 'device_data and team_id are required',
                    'status_code': 400
                }
            
            device_name = device_data.get('name')
            if not device_name:
                return {
                    'success': False,
                    'error': 'Device name is required',
                    'status_code': 400
                }
            
            device_id = device_data.get('id')
            
            # Check for duplicate names
            if self.check_device_name_exists(device_name, team_id, device_id):
                return {
                    'success': False,
                    'error': f'Device name "{device_name}" already exists',
                    'status_code': 409
                }
            
            print(f"[DeviceService] Saving device: {device_name}")
            
            if device_id:
                # Update existing device
                result = self.update_device(device_id, device_data, team_id)
                if result:
                    return {
                        'success': True,
                        'device': result,
                        'message': 'Device updated successfully'
                    }
                else:
                    return {
                        'success': False,
                        'error': 'Failed to update device',
                        'status_code': 500
                    }
            else:
                # Create new device
                result = create_device(device_data, team_id)
                if result:
                    return {
                        'success': True,
                        'device': result,
                        'message': 'Device created successfully'
                    }
                else:
                    return {
                        'success': False,
                        'error': 'Failed to create device',
                        'status_code': 500
                    }
                
        except Exception as e:
            print(f"[DeviceService] Exception: {e}")
            return {
                'success': False,
                'error': f'Service error: {str(e)}',
                'status_code': 500
            }
    
    def delete_device(self, device_id: str, team_id: str) -> Dict[str, Any]:
        """Delete a device"""
        try:
            if not device_id or not team_id:
                return {
                    'success': False,
                    'error': 'device_id and team_id are required',
                    'status_code': 400
                }
            
            print(f"[DeviceService] Deleting device: {device_id}")
            
            # Check if device exists
            existing_device = get_device(device_id, team_id)
            if not existing_device:
                return {
                    'success': False,
                    'error': 'Device not found',
                    'status_code': 404
                }
            
            result = delete_device(device_id, team_id)
            
            if result:
                return {
                    'success': True,
                    'message': 'Device deleted successfully'
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to delete device',
                    'status_code': 500
                }
                
        except Exception as e:
            print(f"[DeviceService] Exception: {e}")
            return {
                'success': False,
                'error': f'Service error: {str(e)}',
                'status_code': 500
            }

# Singleton instance
device_service = DeviceService()
