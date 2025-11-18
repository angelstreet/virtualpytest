"""
TestCase Definition Database Operations

Manages test case definitions (graphs) created in TestCase Builder.
Test cases can be created visually (drag-drop) or via AI (prompt).
Execution results are stored in script_results table (unified tracking).
"""

import json
from typing import Dict, List, Optional, Any
from shared.src.lib.utils.supabase_utils import get_supabase_client
from shared.src.lib.database.folder_tag_db import (
    get_or_create_folder,
    get_or_create_tag,
    set_executable_tags,
    get_executable_tags
)

DEFAULT_TEAM_ID = '7fdeb4bb-3639-4ec3-959f-b54769a219ce'

def get_supabase():
    """Get the Supabase client instance."""
    return get_supabase_client()


def validate_testcase_graph(
    graph_json: Dict[str, Any],
    userinterface_name: str,
    team_id: str
) -> Dict[str, Any]:
    """
    Validate testcase graph before saving - checks that all referenced nodes, edges, and actions exist.
    
    This prevents AI-generated or manually created test cases from referencing non-existent resources,
    which would cause runtime failures during execution.
    
    Args:
        graph_json: Test case graph {nodes: [...], edges: [...]}
        userinterface_name: User interface name (e.g., 'sauce-demo')
        team_id: Team ID for database queries
        
    Returns:
        {
            'success': bool,
            'errors': List[str] (if validation fails),
            'warnings': List[str] (non-critical issues)
        }
    """
    from shared.src.lib.database.navigation_trees_db import get_tree_nodes
    from shared.src.lib.database.userinterface_db import get_userinterface_by_name
    
    errors = []
    warnings = []
    
    try:
        # Get userinterface to find tree_id
        ui_result = get_userinterface_by_name(userinterface_name, team_id)
        if not ui_result or not ui_result.get('success'):
            return {
                'success': False,
                'errors': [f"User interface '{userinterface_name}' not found"]
            }
        
        tree_id = ui_result['userinterface'].get('root_tree_id')
        if not tree_id:
            return {
                'success': False,
                'errors': [f"No navigation tree found for '{userinterface_name}'"]
            }
        
        # Get available navigation nodes from tree
        nodes_result = get_tree_nodes(tree_id, team_id)
        if not nodes_result.get('success'):
            errors.append(f"Failed to load navigation tree: {nodes_result.get('error')}")
            return {'success': False, 'errors': errors}
        
        # Extract valid node labels
        valid_node_labels = set()
        for node in nodes_result.get('nodes', []):
            label = node.get('label')
            if label:
                valid_node_labels.add(label)
        
        print(f"[@testcase_db:validate] Valid navigation nodes: {valid_node_labels}")
        
        # Validate each node in the graph
        graph_nodes = graph_json.get('nodes', [])
        for idx, graph_node in enumerate(graph_nodes):
            node_id = graph_node.get('id', f'node_{idx}')
            node_type = graph_node.get('type', 'unknown')
            node_data = graph_node.get('data', {})
            
            # Check navigation blocks
            if node_type == 'navigation':
                target_label = node_data.get('target_node_label')
                target_id = node_data.get('target_node_id')
                
                # Validation: Must have at least one target
                if not target_label and not target_id:
                    errors.append(
                        f"Navigation block '{node_id}' missing both target_node_label and target_node_id"
                    )
                    continue
                
                # Validate target_node_label if provided
                if target_label:
                    if target_label not in valid_node_labels:
                        errors.append(
                            f"Navigation block '{node_id}' references non-existent node '{target_label}'. "
                            f"Valid nodes: {sorted(valid_node_labels)}"
                        )
                
                # Validate target_node_id if provided (should match label)
                if target_id and target_id not in valid_node_labels:
                    # target_node_id should also be a label in new architecture
                    warnings.append(
                        f"Navigation block '{node_id}' uses target_node_id='{target_id}' "
                        f"which doesn't match any known label. Consider using target_node_label instead."
                    )
            
            # Check action blocks (future enhancement - would need device context)
            elif node_type == 'action':
                # For now, just warn if action looks suspicious
                action_command = node_data.get('command')
                if not action_command:
                    warnings.append(
                        f"Action block '{node_id}' has no command specified"
                    )
            
            # Check verification blocks (future enhancement)
            elif node_type == 'verification':
                verification_command = node_data.get('command')
                if not verification_command:
                    warnings.append(
                        f"Verification block '{node_id}' has no command specified"
                    )
        
        # Return validation result
        if errors:
            print(f"[@testcase_db:validate] ❌ Validation FAILED: {len(errors)} error(s)")
            for error in errors:
                print(f"[@testcase_db:validate]   - {error}")
            return {
                'success': False,
                'errors': errors,
                'warnings': warnings
            }
        
        if warnings:
            print(f"[@testcase_db:validate] ⚠️  Validation passed with {len(warnings)} warning(s)")
            for warning in warnings:
                print(f"[@testcase_db:validate]   - {warning}")
        else:
            print(f"[@testcase_db:validate] ✅ Validation passed - all references valid")
        
        return {
            'success': True,
            'warnings': warnings
        }
        
    except Exception as e:
        print(f"[@testcase_db:validate] Exception during validation: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'errors': [f"Validation failed with exception: {str(e)}"]
        }


def create_testcase(
    team_id: str,
    testcase_name: str,
    graph_json: Dict[str, Any],
    description: str = None,
    userinterface_name: str = None,
    created_by: str = None,
    creation_method: str = 'visual',
    ai_prompt: str = None,
    ai_analysis: str = None,
    overwrite: bool = False,
    environment: str = 'dev',
    folder: str = None,
    tags: List[str] = None
) -> Optional[str]:
    """
    Create a new test case definition, or update if it exists and overwrite=True.
    
    Args:
        team_id: Team ID
        testcase_name: Unique name for the test case (used as script_name)
        graph_json: React Flow graph structure {nodes: [...], edges: [...]}
        description: Optional description
        userinterface_name: Navigation tree to use
        created_by: Username who created it
        creation_method: 'visual' (drag-drop) or 'ai' (prompt)
        ai_prompt: Original prompt if AI-generated
        ai_analysis: AI reasoning if AI-generated
        overwrite: If True, update existing test case with same name
        environment: Environment ('dev', 'test', 'prod') - defaults to 'dev'
        folder: Folder name (user-selected or typed) - defaults to '(Root)'
        tags: List of tag names (existing or new) - auto-created if not exist
    
    Returns:
        testcase_id (UUID) or None on failure
    """
    supabase = get_supabase()
    if not supabase:
        print("[@testcase_db] ERROR: Failed to get Supabase client")
        return None
    
    try:
        # 🛡️ VALIDATION: Validate graph before saving (if userinterface_name provided)
        if userinterface_name and graph_json:
            print(f"[@testcase_db] 🛡️ Validating test case graph...")
            validation_result = validate_testcase_graph(graph_json, userinterface_name, team_id)
            
            if not validation_result['success']:
                errors = validation_result.get('errors', [])
                print(f"[@testcase_db] ❌ Validation FAILED - cannot save test case")
                for error in errors:
                    print(f"[@testcase_db]   - {error}")
                # Return special error code so caller knows why it failed
                return 'VALIDATION_FAILED'
            
            warnings = validation_result.get('warnings', [])
            if warnings:
                print(f"[@testcase_db] ⚠️  Validation passed with warnings:")
                for warning in warnings:
                    print(f"[@testcase_db]   - {warning}")
        
        # Check if test case with this name already exists in this environment
        if overwrite:
            existing = get_testcase_by_name(testcase_name, team_id, environment)
            if existing:
                # Update existing test case
                success = update_testcase(
                    testcase_id=existing['testcase_id'],
                    graph_json=graph_json,
                    description=description,
                    userinterface_name=userinterface_name,
                    team_id=team_id
                )
                if success:
                    print(f"[@testcase_db] Updated test case: {testcase_name} (overwrite mode)")
                    return existing['testcase_id']
                else:
                    return None
        
        # Get or create folder
        folder_id = get_or_create_folder(folder) if folder else 0
        
        data = {
            'team_id': team_id,
            'testcase_name': testcase_name,
            'graph_json': graph_json,
            'description': description,
            'userinterface_name': userinterface_name,
            'created_by': created_by,
            'creation_method': creation_method,
            'ai_prompt': ai_prompt,
            'ai_analysis': ai_analysis,
            'environment': environment,
            'folder_id': folder_id
        }
        
        result = supabase.table('testcase_definitions').insert(data).execute()
        
        if result.data and len(result.data) > 0:
            testcase_id = result.data[0]['testcase_id']
            
            # Set tags if provided
            if tags:
                set_executable_tags('testcase', str(testcase_id), tags)
            
            print(f"[@testcase_db] Created test case: {testcase_name} (ID: {testcase_id}, method: {creation_method}, env: {environment}, folder_id: {folder_id}, tags: {len(tags) if tags else 0})")
            return str(testcase_id)
        else:
            print(f"[@testcase_db] ERROR: No data returned after insert")
            return None
        
    except Exception as e:
        error_msg = str(e)
        if 'duplicate key' in error_msg.lower() or 'unique constraint' in error_msg.lower():
            print(f"[@testcase_db] ERROR: Test case name already exists: {testcase_name} in {environment}")
            return 'DUPLICATE_NAME'  # Return special value to indicate duplicate
        else:
            print(f"[@testcase_db] ERROR creating test case: {e}")
        return None


def get_testcase(testcase_id: str, team_id: str = None) -> Optional[Dict[str, Any]]:
    """
    Get test case definition by ID.
    
    Args:
        testcase_id: Test case UUID
        team_id: Optional team ID for security check
    
    Returns:
        Test case dict or None
    """
    supabase = get_supabase()
    if not supabase:
        return None
    
    try:
        query = supabase.table('testcase_definitions').select('*').eq('testcase_id', testcase_id)
        
        if team_id:
            query = query.eq('team_id', team_id)
        
        result = query.execute()
        
        if result.data and len(result.data) > 0:
            testcase = result.data[0]
            # Ensure IDs are strings
            testcase['testcase_id'] = str(testcase['testcase_id'])
            testcase['team_id'] = str(testcase['team_id'])
            # Parse graph_json if it's a string
            if isinstance(testcase.get('graph_json'), str):
                testcase['graph_json'] = json.loads(testcase['graph_json'])
            return testcase
        
        return None
        
    except Exception as e:
        print(f"[@testcase_db] ERROR getting test case: {e}")
        return None


def get_testcase_by_name(testcase_name: str, team_id: str, environment: str = 'dev') -> Optional[Dict[str, Any]]:
    """
    Get test case definition by name and environment.
    
    Args:
        testcase_name: Test case name
        team_id: Team ID
        environment: Environment ('dev', 'test', 'prod') - defaults to 'dev'
    
    Returns:
        Test case dict or None
    """
    supabase = get_supabase()
    if not supabase:
        return None
    
    try:
        result = supabase.table('testcase_definitions')\
            .select('*')\
            .eq('testcase_name', testcase_name)\
            .eq('team_id', team_id)\
            .eq('environment', environment)\
            .execute()
        
        if result.data and len(result.data) > 0:
            testcase = result.data[0]
            testcase['testcase_id'] = str(testcase['testcase_id'])
            testcase['team_id'] = str(testcase['team_id'])
            # Parse graph_json if it's a string
            if isinstance(testcase.get('graph_json'), str):
                testcase['graph_json'] = json.loads(testcase['graph_json'])
            return testcase
        
        return None

    except Exception as e:
        print(f"[@testcase_db] ERROR getting test case by name: {e}")
        return None


def update_testcase(
    testcase_id: str,
    graph_json: Dict[str, Any] = None,
    description: str = None,
    userinterface_name: str = None,
    team_id: str = None,
    folder: str = None,
    tags: List[str] = None,
    testcase_name: str = None
) -> bool:
    """
    Update test case definition.
    
    Args:
        testcase_id: Test case UUID
        graph_json: Updated graph structure
        description: Updated description
        userinterface_name: Updated navigation tree
        team_id: Team ID for security check
        folder: Updated folder name (user-selected or typed)
        tags: Updated list of tag names
        testcase_name: Updated testcase name (for renaming)
    
    Returns:
        True on success, False on failure
    """
    supabase = get_supabase()
    if not supabase:
        return False
    
    try:
        # Build update data
        update_data = {}
        
        if graph_json is not None:
            update_data['graph_json'] = graph_json
        
        if description is not None:
            update_data['description'] = description
        
        if userinterface_name is not None:
            update_data['userinterface_name'] = userinterface_name
        
        if testcase_name is not None:
            update_data['testcase_name'] = testcase_name
        
        if folder is not None:
            folder_id = get_or_create_folder(folder)
            update_data['folder_id'] = folder_id
        
        if not update_data and tags is None:
            print("[@testcase_db] WARNING: No fields to update")
            return True
        
        # Update testcase record if there's data
        if update_data:
            query = supabase.table('testcase_definitions').update(update_data).eq('testcase_id', testcase_id)
            
            if team_id:
                query = query.eq('team_id', team_id)
            
            result = query.execute()
            
            if not result.data or len(result.data) == 0:
                print(f"[@testcase_db] WARNING: No test case updated (ID: {testcase_id})")
                return False
        
        # Update tags if provided
        if tags is not None:
            set_executable_tags('testcase', testcase_id, tags)
        
        name_info = f" -> {testcase_name}" if testcase_name else ""
        print(f"[@testcase_db] Updated test case: {testcase_id}{name_info}")
        return True
        
    except Exception as e:
        error_msg = str(e)
        if testcase_name and ('duplicate key' in error_msg.lower() or 'unique constraint' in error_msg.lower()):
            print(f"[@testcase_db] ERROR: Testcase name already exists: {testcase_name}")
        else:
            print(f"[@testcase_db] ERROR updating test case: {e}")
        return False


def get_next_version_number(testcase_id: str, team_id: str) -> int:
    """
    Get the next version number for a test case.
    Returns 1 for new test cases (no history), or MAX(version_number) + 1 for existing ones.
    
    Args:
        testcase_id: Test case UUID
        team_id: Team ID for security check
    
    Returns:
        Next version number (1 for new, or incremented from history)
    """
    supabase = get_supabase()
    if not supabase:
        return 1
    
    try:
        # Check if this test case exists and has history
        result = supabase.table('testcase_definitions_history')\
            .select('version_number')\
            .eq('testcase_id', testcase_id)\
            .eq('team_id', team_id)\
            .order('version_number', desc=True)\
            .limit(1)\
            .execute()
        
        if result.data and len(result.data) > 0:
            # Has history, return next version
            return result.data[0]['version_number'] + 1
        else:
            # No history, this will be version 1 (trigger will save current as v1)
            return 1
    except Exception as e:
        print(f"[@testcase_db] ERROR getting next version number: {e}")
        return 1


def delete_testcase(testcase_id: str, team_id: str = None) -> bool:
    """
    Delete test case permanently.
    
    Args:
        testcase_id: Test case UUID
        team_id: Team ID for security check
    
    Returns:
        True on success, False on failure
    """
    supabase = get_supabase()
    if not supabase:
        return False
    
    try:
        query = supabase.table('testcase_definitions')\
            .delete()\
            .eq('testcase_id', testcase_id)
        
        if team_id:
            query = query.eq('team_id', team_id)
        
        result = query.execute()
        
        if result.data and len(result.data) > 0:
            print(f"[@testcase_db] Deleted test case: {testcase_id}")
            return True
        else:
            print(f"[@testcase_db] WARNING: No test case deleted (ID: {testcase_id})")
            return False
        
    except Exception as e:
        print(f"[@testcase_db] ERROR deleting test case: {e}")
        return False


def list_testcases(team_id: str, include_inactive: bool = False, environment: str = None) -> List[Dict[str, Any]]:
    """
    List all test cases for a team.
    
    Args:
        team_id: Team ID
        include_inactive: (Deprecated - kept for backward compatibility)
        environment: Filter by environment ('dev', 'test', 'prod') - None returns all
    
    Returns:
        List of test case dicts (without full graph_json)
    """
    supabase = get_supabase()
    if not supabase:
        return []
    
    try:
        # Note: Supabase doesn't support subqueries in select, so we get execution counts separately
        query = supabase.table('testcase_definitions')\
            .select('testcase_id,team_id,testcase_name,description,userinterface_name,created_at,updated_at,created_by,environment,graph_json')\
            .eq('team_id', team_id)
        
        # Filter by environment if specified
        if environment:
            query = query.eq('environment', environment)
        
        query = query.order('updated_at', desc=True)
        
        result = query.execute()
        
        testcases = []
        for testcase in result.data:
            testcase['testcase_id'] = str(testcase['testcase_id'])
            testcase['team_id'] = str(testcase['team_id'])
            
            # Get current version number from history
            try:
                version_result = supabase.table('testcase_definitions_history')\
                    .select('version_number')\
                    .eq('testcase_id', testcase['testcase_id'])\
                    .eq('team_id', team_id)\
                    .order('version_number', desc=True)\
                    .limit(1)\
                    .execute()
                
                # If there's history, the current version is MAX(version_number)
                # If no history, this is version 1 (not yet updated)
                testcase['current_version'] = version_result.data[0]['version_number'] if version_result.data else 1
            except:
                testcase['current_version'] = 1
            
            # Get execution count and last success
            try:
                exec_result = supabase.table('script_results')\
                    .select('success')\
                    .eq('script_type', 'testcase')\
                    .eq('script_name', testcase['testcase_name'])\
                    .order('started_at', desc=True)\
                    .execute()
                
                testcase['execution_count'] = len(exec_result.data) if exec_result.data else 0
                testcase['last_execution_success'] = exec_result.data[0]['success'] if exec_result.data else None
            except:
                testcase['execution_count'] = 0
                testcase['last_execution_success'] = None
            
            testcases.append(testcase)
        
        return testcases
        
    except Exception as e:
        print(f"[@testcase_db] ERROR listing test cases: {e}")
        return []


def get_testcase_execution_history(testcase_name: str, team_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Get execution history for a test case from script_results table.
    
    Args:
        testcase_name: Test case name
        team_id: Team ID
        limit: Max number of results
    
    Returns:
        List of execution records
    """
    supabase = get_supabase()
    if not supabase:
        return []
    
    try:
        result = supabase.table('script_results')\
            .select('script_result_id,script_name,started_at,completed_at,execution_time_ms,success,error_msg,host_name,device_name,html_report_r2_url,logs_r2_url')\
            .eq('script_type', 'testcase')\
            .eq('script_name', testcase_name)\
            .eq('team_id', team_id)\
            .order('started_at', desc=True)\
            .limit(limit)\
            .execute()
        
        executions = []
        for execution in result.data:
            execution['script_result_id'] = str(execution['script_result_id'])
            executions.append(execution)
        
        return executions
        
    except Exception as e:
        print(f"[@testcase_db] ERROR getting execution history: {e}")
        return []


def migrate_testcase_environment(testcase_id: str, team_id: str, target_environment: str) -> bool:
    """
    Migrate a testcase to a different environment (dev -> test -> prod).
    
    Args:
        testcase_id: Test case UUID
        team_id: Team ID for security
        target_environment: Target environment ('dev', 'test', 'prod')
    
    Returns:
        True on success, False on failure
    """
    if target_environment not in ['dev', 'test', 'prod']:
        print(f"[@testcase_db] ERROR: Invalid environment: {target_environment}")
        return False
    
    supabase = get_supabase()
    if not supabase:
        return False
    
    try:
        query = supabase.table('testcase_definitions')\
            .update({'environment': target_environment})\
            .eq('testcase_id', testcase_id)
        
        if team_id:
            query = query.eq('team_id', team_id)
        
        result = query.execute()
        
        if result.data and len(result.data) > 0:
            testcase_name = result.data[0].get('testcase_name', testcase_id)
            print(f"[@testcase_db] Migrated test case '{testcase_name}' to environment: {target_environment}")
            return True
        else:
            print(f"[@testcase_db] WARNING: No test case migrated (ID: {testcase_id})")
            return False
        
    except Exception as e:
        print(f"[@testcase_db] ERROR migrating test case: {e}")
        return False
