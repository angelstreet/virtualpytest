"""
Reference utilities for resolving reference areas from database.

Centralized logic to avoid duplication across frontend and backend.
"""

from typing import Dict, Optional, Any


def resolve_reference_area_backend(reference_name: str, userinterface_name: str, team_id: str) -> Optional[Dict[str, Any]]:
    """
    Resolve reference area from database (backend version).
    
    Args:
        reference_name: Name of the reference
        userinterface_name: User interface name (e.g., 'horizon_android_tv')
        team_id: Team ID (required)
        
    Returns:
        Dict with area coordinates or None if not found
    """
    try:
        if not team_id:
            print(f"[@reference_utils:resolve_reference_area_backend] ERROR: team_id is required")
            return None
            
        from shared.src.lib.database.verifications_references_db import get_references
        
        # Try exact name first
        names_to_try = [reference_name]
        
        # Add variations (handle _text suffix logic matching frontend)
        if reference_name.endswith('_text'):
            names_to_try.append(reference_name[:-5])  # Remove _text
        else:
            names_to_try.append(f"{reference_name}_text")  # Add _text
            
        print(f"[@reference_utils] Attempting to resolve reference with variations: {names_to_try}")
            
        # Try each name variation
        for name_variant in names_to_try:
            result = get_references(team_id, userinterface_name=userinterface_name, name=name_variant)
            if result.get('success') and result.get('references'):
                references = result['references']
                # Find exact match for this variant
                reference_data = next((ref for ref in references if ref['name'] == name_variant), None)
                
                if reference_data and reference_data.get('area'):
                    print(f"[@reference_utils] ✅ Resolved reference '{reference_name}' as '{name_variant}'")
                    return reference_data['area']
        
        print(f"[@reference_utils] ❌ Failed to resolve reference '{reference_name}' (tried: {names_to_try})")
        return None
        
    except Exception as e:
        print(f"[@reference_utils:resolve_reference_area_backend] Error: {e}")
        return None
