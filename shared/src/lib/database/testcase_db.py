"""
TestCase Definition Database Operations

Manages test case definitions (graphs) created in TestCase Builder.
Test cases can be created visually (drag-drop) or via AI (prompt).
Execution results are stored in script_results table (unified tracking).
"""

import json
from typing import Dict, List, Optional, Any
from shared.src.lib.utils.supabase_utils import get_supabase_client

DEFAULT_TEAM_ID = '7fdeb4bb-3639-4ec3-959f-b54769a219ce'

def get_supabase():
    """Get the Supabase client instance."""
    return get_supabase_client()


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
    overwrite: bool = False
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
    
    Returns:
        testcase_id (UUID) or None on failure
    """
    supabase = get_supabase()
    if not supabase:
        print("[@testcase_db] ERROR: Failed to get Supabase client")
        return None
    
    try:
        # Check if test case with this name already exists
        if overwrite:
            existing = get_testcase_by_name(testcase_name, team_id)
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
        
        data = {
            'team_id': team_id,
            'testcase_name': testcase_name,
            'graph_json': graph_json,
            'description': description,
            'userinterface_name': userinterface_name,
            'created_by': created_by,
            'creation_method': creation_method,
            'ai_prompt': ai_prompt,
            'ai_analysis': ai_analysis
        }
        
        result = supabase.table('testcase_definitions').insert(data).execute()
        
        if result.data and len(result.data) > 0:
            testcase_id = result.data[0]['testcase_id']
            print(f"[@testcase_db] Created test case: {testcase_name} (ID: {testcase_id}, method: {creation_method})")
            return str(testcase_id)
        else:
            print(f"[@testcase_db] ERROR: No data returned after insert")
            return None
        
    except Exception as e:
        error_msg = str(e)
        if 'duplicate key' in error_msg.lower() or 'unique constraint' in error_msg.lower():
            print(f"[@testcase_db] ERROR: Test case name already exists: {testcase_name}")
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


def get_testcase_by_name(testcase_name: str, team_id: str) -> Optional[Dict[str, Any]]:
    """
    Get test case definition by name.
    
    Args:
        testcase_name: Test case name
        team_id: Team ID
    
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
    team_id: str = None
) -> bool:
    """
    Update test case definition.
    
    Args:
        testcase_id: Test case UUID
        graph_json: Updated graph structure
        description: Updated description
        userinterface_name: Updated navigation tree
        team_id: Team ID for security check
    
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
        
        if not update_data:
            print("[@testcase_db] WARNING: No fields to update")
            return True
        
        query = supabase.table('testcase_definitions').update(update_data).eq('testcase_id', testcase_id)
        
        if team_id:
            query = query.eq('team_id', team_id)
        
        result = query.execute()
        
        if result.data and len(result.data) > 0:
            print(f"[@testcase_db] Updated test case: {testcase_id}")
            return True
        else:
            print(f"[@testcase_db] WARNING: No test case updated (ID: {testcase_id})")
            return False
        
    except Exception as e:
        print(f"[@testcase_db] ERROR updating test case: {e}")
        return False


def delete_testcase(testcase_id: str, team_id: str = None) -> bool:
    """
    Soft delete test case (set is_active = false).
    
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
            .update({'is_active': False})\
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


def list_testcases(team_id: str, include_inactive: bool = False) -> List[Dict[str, Any]]:
    """
    List all test cases for a team.
    
    Args:
        team_id: Team ID
        include_inactive: Include soft-deleted test cases
    
    Returns:
        List of test case dicts (without full graph_json)
    """
    supabase = get_supabase()
    if not supabase:
        return []
    
    try:
        # Note: Supabase doesn't support subqueries in select, so we get execution counts separately
        query = supabase.table('testcase_definitions')\
            .select('testcase_id,team_id,testcase_name,description,userinterface_name,created_at,updated_at,created_by,is_active')\
            .eq('team_id', team_id)
        
        if not include_inactive:
            query = query.eq('is_active', True)
        
        query = query.order('updated_at', desc=True)
        
        result = query.execute()
        
        testcases = []
        for testcase in result.data:
            testcase['testcase_id'] = str(testcase['testcase_id'])
            testcase['team_id'] = str(testcase['team_id'])
            
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
