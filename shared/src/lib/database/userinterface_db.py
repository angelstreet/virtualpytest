"""
User Interface Database Operations

This module provides functions for managing user interfaces in the database.
User interfaces define the different UI contexts for applications being tested.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional

from shared.src.lib.utils.supabase_utils import get_supabase_client

def get_supabase():
    """Get the Supabase client instance."""
    return get_supabase_client()

def get_all_userinterfaces(team_id: str) -> List[Dict]:
    """Retrieve all user interfaces for a team from Supabase."""
    supabase = get_supabase()
    try:
        result = supabase.table('userinterfaces').select(
            'id', 'name', 'models', 'min_version', 'max_version', 'team_id', 'created_at', 'updated_at'
        ).eq('team_id', team_id).order('created_at', desc=False).execute()
        
        userinterfaces = []
        for ui in result.data:
            userinterfaces.append({
                'id': ui['id'],
                'name': ui['name'],
                'models': ui.get('models', []),
                'min_version': ui.get('min_version', ''),
                'max_version': ui.get('max_version', ''),
                'team_id': ui['team_id'],
                'created_at': ui['created_at'],
                'updated_at': ui['updated_at']
            })
        
        return userinterfaces
    except Exception as e:
        print(f"[@db:userinterface_db:get_all_userinterfaces] Error: {e}")
        return []

def get_userinterface(interface_id: str, team_id: str) -> Optional[Dict]:
    """Retrieve a user interface by ID and team ID from Supabase."""
    supabase = get_supabase()
    try:
        result = supabase.table('userinterfaces').select(
            'id', 'name', 'models', 'min_version', 'max_version', 'team_id', 'created_at', 'updated_at'
        ).eq('id', interface_id).eq('team_id', team_id).single().execute()
        
        if result.data:
            ui = result.data
            return {
                'id': ui['id'],
                'name': ui['name'],
                'models': ui.get('models', []),
                'min_version': ui.get('min_version', ''),
                'max_version': ui.get('max_version', ''),
                'team_id': ui['team_id'],
                'created_at': ui['created_at'],
                'updated_at': ui['updated_at']
            }
        return None
    except Exception as e:
        print(f"[@db:userinterface_db:get_userinterface] Error: {e}")
        return None

def get_userinterface_by_name(interface_name: str, team_id: str) -> Optional[Dict]:
    """
    Retrieve a user interface by name and team ID from Supabase.
    
    Returns:
        {
            'success': bool,
            'userinterface': {
                'id': str,
                'name': str,
                'models': list,
                'root_tree_id': str (from root_tree.id)
            }
        }
    """
    supabase = get_supabase()
    try:
        # Get userinterface with root tree (filter for is_root_tree=true)
        result = supabase.table('userinterfaces').select(
            'id, name, models, root_tree:navigation_trees!userinterface_id(id)'
        ).eq('name', interface_name).eq('team_id', team_id).single().execute()
        
        if result.data:
            ui = result.data
            # root_tree comes back as a list, find the one with is_root_tree=true
            root_trees = ui.get('root_tree', [])
            root_tree_id = None
            
            if isinstance(root_trees, list) and len(root_trees) > 0:
                # Take the first tree (should be the root tree)
                # TODO: Filter by is_root_tree=true in the query
                root_tree_id = root_trees[0].get('id')
            elif isinstance(root_trees, dict):
                # In case it's a single object
                root_tree_id = root_trees.get('id')
            
            return {
                'success': True,
                'userinterface': {
                    'id': ui['id'],
                    'name': ui['name'],
                    'models': ui.get('models', []),
                    'root_tree_id': root_tree_id
                }
            }
        return None
    except Exception as e:
        print(f"[@db:userinterface_db:get_userinterface_by_name] Error: {e}")
        return None

def create_userinterface(interface_data: Dict, team_id: str, creator_id: str = None) -> Optional[Dict]:
    """Create a new user interface."""
    supabase = get_supabase()
    try:
        insert_data = {
            'name': interface_data['name'],
            'models': interface_data.get('models', []),
            'min_version': interface_data.get('min_version', ''),
            'max_version': interface_data.get('max_version', ''),
            'team_id': team_id,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        
        result = supabase.table('userinterfaces').insert(insert_data).execute()
        
        if result.data and len(result.data) > 0:
            ui = result.data[0]
            return {
                'id': ui['id'],
                'name': ui['name'],
                'models': ui.get('models', []),
                'min_version': ui.get('min_version', ''),
                'max_version': ui.get('max_version', ''),
                'team_id': ui['team_id'],
                'created_at': ui['created_at'],
                'updated_at': ui['updated_at']
            }
        return None
    except Exception as e:
        print(f"[@db:userinterface_db:create_userinterface] Error: {e}")
        return None

def update_userinterface(interface_id: str, interface_data: Dict, team_id: str) -> Optional[Dict]:
    """Update an existing user interface."""
    supabase = get_supabase()
    try:
        update_data = {
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        
        if 'name' in interface_data:
            update_data['name'] = interface_data['name']
        if 'min_version' in interface_data:
            update_data['min_version'] = interface_data.get('min_version', '')
        if 'max_version' in interface_data:
            update_data['max_version'] = interface_data.get('max_version', '')
        if 'models' in interface_data:
            update_data['models'] = interface_data['models']
        
        result = supabase.table('userinterfaces').update(update_data).eq('id', interface_id).eq('team_id', team_id).execute()
        
        if result.data and len(result.data) > 0:
            ui = result.data[0]
            return {
                'id': ui['id'],
                'name': ui['name'],
                'models': ui.get('models', []),
                'min_version': ui.get('min_version', ''),
                'max_version': ui.get('max_version', ''),
                'team_id': ui['team_id'],
                'created_at': ui['created_at'],
                'updated_at': ui['updated_at']
            }
        return None
    except Exception as e:
        print(f"[@db:userinterface_db:update_userinterface] Error: {e}")
        return None

def delete_userinterface(interface_id: str, team_id: str) -> bool:
    """Delete a user interface."""
    supabase = get_supabase()
    try:
        result = supabase.table('userinterfaces').delete().eq('id', interface_id).eq('team_id', team_id).execute()
        return len(result.data) > 0
    except Exception as e:
        print(f"[@db:userinterface_db:delete_userinterface] Error: {e}")
        return False

def check_userinterface_name_exists(name: str, team_id: str, exclude_id: str = None) -> bool:
    """Check if a user interface name already exists for a team."""
    supabase = get_supabase()
    try:
        query = supabase.table('userinterfaces').select('id').eq('name', name).eq('team_id', team_id)
        
        if exclude_id:
            query = query.neq('id', exclude_id)
        
        result = query.execute()
        return len(result.data) > 0
    except Exception as e:
        print(f"[@db:userinterface_db:check_userinterface_name] Error: {e}")
        return False

def duplicate_userinterface_with_tree(source_id: str, new_name: str, team_id: str, creator_id: str = None) -> Optional[Dict]:
    """Duplicate a user interface and its entire navigation tree."""
    try:
        from shared.src.lib.database.navigation_trees_db import get_root_tree_for_interface, duplicate_tree
        
        # Get source and create new UI
        source_ui = get_userinterface(source_id, team_id)
        if not source_ui:
            return None
        
        new_ui = create_userinterface({
            'name': new_name,
            'models': source_ui.get('models', []),
            'min_version': source_ui.get('min_version', ''),
            'max_version': source_ui.get('max_version', '')
        }, team_id, creator_id)
        
        if not new_ui:
            return None
        
        # Get and duplicate tree
        source_tree = get_root_tree_for_interface(source_id, team_id)
        if not source_tree:
            return {**new_ui, 'duplication_stats': {'tree_duplicated': False, 'nodes_count': 0, 'edges_count': 0}}
        
        dup_result = duplicate_tree(source_tree['id'], new_ui['id'], new_ui['name'], team_id)
        
        return {
            **new_ui,
            'duplication_stats': {
                'tree_duplicated': dup_result['success'],
                'tree_id': dup_result.get('tree_id'),
                'nodes_count': dup_result.get('nodes_count', 0),
                'edges_count': dup_result.get('edges_count', 0),
                'error': dup_result.get('error')
            } if dup_result['success'] else {
                'tree_duplicated': False,
                'nodes_count': 0,
                'edges_count': 0,
                'error': dup_result.get('error')
            }
        }
        
    except Exception as e:
        print(f"[@db:userinterface_db:duplicate_userinterface_with_tree] Error: {e}")
        return None