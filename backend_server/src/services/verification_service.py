"""
Verification Service

Handles verification-related business logic that was previously in routes.
This service layer separates business logic from HTTP handling.
"""

from typing import Dict, Any, List, Optional

class VerificationService:
    """Service for handling verification business logic"""
    
    def get_verification_types(self, device_model: str = 'android_mobile') -> Dict[str, Any]:
        """
        Get available verification types for a device model.
        
        Args:
            device_model: The device model to get verifications for
            
        Returns:
            Dict containing success status and verification types
        """
        try:
            # Business logic for verification types
            verifications = [
                {
                    'id': 'waitForElementToAppear',
                    'name': 'waitForElementToAppear',
                    'command': 'waitForElementToAppear',
                    'device_model': device_model,
                    'verification_type': 'adb',
                    'params': {
                        'search_term': '',
                        'timeout': 10,
                        'check_interval': 1
                    }
                },
                {
                    'id': 'image_verification',
                    'name': 'image_verification',
                    'command': 'image_verification',
                    'device_model': device_model,
                    'verification_type': 'image',
                    'params': {
                        'reference_image': '',
                        'confidence_threshold': 0.8
                    }
                }
            ]
            
            return {
                'success': True,
                'verifications': verifications
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to get verification types: {str(e)}'
            }
    
    def get_all_references(self, team_id: str, device_model: str = None) -> Dict[str, Any]:
        """
        Get all reference images/data for a team.
        Only returns references where userinterface_name matches actual userinterface names.
        Optionally filters by device_model compatibility.
        
        Args:
            team_id: The team ID to get references for
            device_model: Optional device model to filter compatible userinterfaces
            
        Returns:
            Dict containing success status and references
        """
        try:
            if not team_id:
                return {
                    'success': False,
                    'error': 'team_id is required',
                    'status_code': 400
                }
            
            # Get valid userinterface names from database
            from shared.src.lib.database.userinterface_db import get_all_userinterfaces
            userinterfaces = get_all_userinterfaces(team_id)
            
            if not userinterfaces:
                print(f'[VerificationService] No userinterfaces found for team')
                return {
                    'success': True,
                    'references': []
                }
            
            # Filter by device_model compatibility if provided
            if device_model:
                compatible_uis = [
                    ui for ui in userinterfaces 
                    if device_model in ui.get('models', [])
                ]
                print(f'[VerificationService] Filtered {len(userinterfaces)} userinterfaces to {len(compatible_uis)} compatible with device_model: {device_model}')
                userinterfaces = compatible_uis
            
            if not userinterfaces:
                print(f'[VerificationService] No compatible userinterfaces found')
                return {
                    'success': True,
                    'references': []
                }
            
            # Extract valid userinterface names
            valid_ui_names = {ui['name'] for ui in userinterfaces}
            print(f'[VerificationService] Valid userinterface names: {valid_ui_names}')
            
            # Get all references from database
            from shared.src.lib.database.verifications_references_db import get_references
            
            print(f'[VerificationService] Getting all references for team: {team_id}')
            
            result = get_references(team_id=team_id)
            
            if not result['success']:
                print(f'[VerificationService] Error getting references: {result.get("error")}')
                return {
                    'success': False,
                    'error': result.get('error', 'Failed to get references'),
                    'status_code': 500
                }
            
            # Filter references to ONLY include those matching valid userinterfaces
            filtered_references = [
                ref for ref in result['references']
                if (ref.get('userinterface_name') or ref.get('device_model')) in valid_ui_names
            ]
            
            print(f'[VerificationService] Filtered {len(result["references"])} references down to {len(filtered_references)} matching compatible userinterfaces')
            
            return {
                'success': True,
                'references': filtered_references
            }
                
        except Exception as e:
            print(f'[VerificationService] ERROR: {e}')
            return {
                'success': False,
                'error': f'Service error: {str(e)}',
                'status_code': 500
            }

# Singleton instance
verification_service = VerificationService()
