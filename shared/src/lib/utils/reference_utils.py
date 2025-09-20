"""
Reference utilities for resolving reference areas from database.

Centralized logic to avoid duplication across frontend and backend.
"""

from typing import Dict, Optional, Any


def resolve_reference_area_backend(reference_name: str, device_model: str, team_id: str) -> Optional[Dict[str, Any]]:
    """
    Resolve reference area from database (backend version).
    
    Args:
        reference_name: Name of the reference
        device_model: Device model (e.g., 'android_tv')
        team_id: Team ID (required)
        
    Returns:
        Dict with area coordinates or None if not found
    """
    try:
        if not team_id:
            print(f"[@reference_utils:resolve_reference_area_backend] ERROR: team_id is required")
            return None
            
        from shared.src.lib.supabase.verifications_references_db import get_references
        
        result = get_references(team_id, device_model=device_model, name=reference_name)
        if result.get('success') and result.get('references'):
            references = result['references']
            reference_data = next((ref for ref in references if ref['name'] == reference_name), None)
            if reference_data and reference_data.get('area'):
                return reference_data['area']
                
        return None
        
    except Exception as e:
        print(f"[@reference_utils:resolve_reference_area_backend] Error: {e}")
        return None
