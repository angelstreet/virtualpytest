"""
TestCase Definition Database Operations

Manages test case definitions (graphs) created in TestCase Builder.
Test cases can be created visually (drag-drop) or via AI (prompt).
Execution results are stored in script_results table (unified tracking).
"""

import psycopg2
import psycopg2.extras
import json
from typing import Dict, List, Optional, Any
from shared.src.lib.database.database import get_db_connection

DEFAULT_TEAM_ID = '7fdeb4bb-3639-4ec3-959f-b54769a219ce'


def create_testcase(
    team_id: str,
    testcase_name: str,
    graph_json: Dict[str, Any],
    description: str = None,
    userinterface_name: str = None,
    created_by: str = None,
    creation_method: str = 'visual',
    ai_prompt: str = None,
    ai_analysis: str = None
) -> Optional[str]:
    """
    Create a new test case definition.
    
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
    
    Returns:
        testcase_id (UUID) or None on failure
    """
    conn = get_db_connection()
    if not conn:
        print("[@testcase_db] ERROR: Failed to get database connection")
        return None
    
    try:
        cursor = conn.cursor()
        
        query = """
            INSERT INTO testcase_definitions 
            (team_id, testcase_name, graph_json, description, userinterface_name, created_by, creation_method, ai_prompt, ai_analysis)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING testcase_id
        """
        
        cursor.execute(query, (
            team_id,
            testcase_name,
            json.dumps(graph_json),
            description,
            userinterface_name,
            created_by,
            creation_method,
            ai_prompt,
            ai_analysis
        ))
        
        testcase_id = cursor.fetchone()[0]
        conn.commit()
        
        print(f"[@testcase_db] Created test case: {testcase_name} (ID: {testcase_id}, method: {creation_method})")
        return str(testcase_id)
        
    except psycopg2.IntegrityError as e:
        conn.rollback()
        print(f"[@testcase_db] ERROR: Test case name already exists: {testcase_name}")
        return None
    except Exception as e:
        conn.rollback()
        print(f"[@testcase_db] ERROR creating test case: {e}")
        return None
    finally:
        conn.close()


def get_testcase(testcase_id: str, team_id: str = None) -> Optional[Dict[str, Any]]:
    """
    Get test case definition by ID.
    
    Args:
        testcase_id: Test case UUID
        team_id: Optional team ID for security check
    
    Returns:
        Test case dict or None
    """
    conn = get_db_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        query = """
            SELECT 
                testcase_id,
                team_id,
                testcase_name,
                description,
                userinterface_name,
                graph_json,
                created_at,
                updated_at,
                created_by,
                is_active
            FROM testcase_definitions
            WHERE testcase_id = %s
        """
        
        params = [testcase_id]
        
        if team_id:
            query += " AND team_id = %s"
            params.append(team_id)
        
        cursor.execute(query, params)
        result = cursor.fetchone()
        
        if result:
            # Convert to dict and parse JSON
            testcase = dict(result)
            testcase['graph_json'] = json.loads(testcase['graph_json']) if isinstance(testcase['graph_json'], str) else testcase['graph_json']
            testcase['testcase_id'] = str(testcase['testcase_id'])
            testcase['team_id'] = str(testcase['team_id'])
            return testcase
        
        return None
        
    except Exception as e:
        print(f"[@testcase_db] ERROR getting test case: {e}")
        return None
    finally:
        conn.close()


def get_testcase_by_name(testcase_name: str, team_id: str) -> Optional[Dict[str, Any]]:
    """
    Get test case definition by name.
    
    Args:
        testcase_name: Test case name
        team_id: Team ID
    
    Returns:
        Test case dict or None
    """
    conn = get_db_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        query = """
            SELECT 
                testcase_id,
                team_id,
                testcase_name,
                description,
                userinterface_name,
                graph_json,
                created_at,
                updated_at,
                created_by,
                is_active
            FROM testcase_definitions
            WHERE testcase_name = %s AND team_id = %s
        """
        
        cursor.execute(query, (testcase_name, team_id))
        result = cursor.fetchone()
        
        if result:
            testcase = dict(result)
            testcase['graph_json'] = json.loads(testcase['graph_json']) if isinstance(testcase['graph_json'], str) else testcase['graph_json']
            testcase['testcase_id'] = str(testcase['testcase_id'])
            testcase['team_id'] = str(testcase['team_id'])
            return testcase
        
        return None

    except Exception as e:
        print(f"[@testcase_db] ERROR getting test case by name: {e}")
        return None
    finally:
        conn.close()


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
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Build dynamic update query
        updates = []
        params = []
        
        if graph_json is not None:
            updates.append("graph_json = %s")
            params.append(json.dumps(graph_json))
        
        if description is not None:
            updates.append("description = %s")
            params.append(description)
        
        if userinterface_name is not None:
            updates.append("userinterface_name = %s")
            params.append(userinterface_name)
        
        if not updates:
            print("[@testcase_db] WARNING: No fields to update")
            return True
        
        query = f"""
            UPDATE testcase_definitions
            SET {', '.join(updates)}
            WHERE testcase_id = %s
        """
        params.append(testcase_id)
        
        if team_id:
            query += " AND team_id = %s"
            params.append(team_id)
        
        cursor.execute(query, params)
        conn.commit()
        
        rows_updated = cursor.rowcount
        
        if rows_updated > 0:
            print(f"[@testcase_db] Updated test case: {testcase_id}")
            return True
        else:
            print(f"[@testcase_db] WARNING: No test case updated (ID: {testcase_id})")
            return False
        
    except Exception as e:
        conn.rollback()
        print(f"[@testcase_db] ERROR updating test case: {e}")
        return False
    finally:
        conn.close()


def delete_testcase(testcase_id: str, team_id: str = None) -> bool:
    """
    Soft delete test case (set is_active = false).
    
    Args:
        testcase_id: Test case UUID
        team_id: Team ID for security check
    
    Returns:
        True on success, False on failure
    """
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        query = """
            UPDATE testcase_definitions
            SET is_active = FALSE
            WHERE testcase_id = %s
        """
        params = [testcase_id]
        
        if team_id:
            query += " AND team_id = %s"
            params.append(team_id)
        
        cursor.execute(query, params)
        conn.commit()
        
        rows_updated = cursor.rowcount
        
        if rows_updated > 0:
            print(f"[@testcase_db] Deleted test case: {testcase_id}")
            return True
        else:
            print(f"[@testcase_db] WARNING: No test case deleted (ID: {testcase_id})")
            return False
        
    except Exception as e:
        conn.rollback()
        print(f"[@testcase_db] ERROR deleting test case: {e}")
        return False
    finally:
        conn.close()


def list_testcases(team_id: str, include_inactive: bool = False) -> List[Dict[str, Any]]:
    """
    List all test cases for a team.
    
    Args:
        team_id: Team ID
        include_inactive: Include soft-deleted test cases
    
    Returns:
        List of test case dicts (without full graph_json)
    """
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        query = """
            SELECT 
                testcase_id,
                team_id,
                testcase_name,
                description,
                userinterface_name,
                created_at,
                updated_at,
                created_by,
                is_active,
                (SELECT COUNT(*) FROM script_results 
                 WHERE script_type = 'testcase' 
                   AND script_name = testcase_definitions.testcase_name
                ) as execution_count,
                (SELECT success FROM script_results 
                 WHERE script_type = 'testcase' 
                   AND script_name = testcase_definitions.testcase_name
                 ORDER BY started_at DESC LIMIT 1
                ) as last_execution_success
            FROM testcase_definitions
            WHERE team_id = %s
        """
        
        if not include_inactive:
            query += " AND is_active = TRUE"
        
        query += " ORDER BY updated_at DESC"
        
        cursor.execute(query, (team_id,))
        results = cursor.fetchall()
        
        testcases = []
        for row in results:
            testcase = dict(row)
            testcase['testcase_id'] = str(testcase['testcase_id'])
            testcase['team_id'] = str(testcase['team_id'])
            testcases.append(testcase)
        
        return testcases
        
    except Exception as e:
        print(f"[@testcase_db] ERROR listing test cases: {e}")
        return []
    finally:
        conn.close()


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
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        query = """
            SELECT 
                script_result_id,
                script_name,
                started_at,
                completed_at,
                execution_time_ms,
                success,
                error_msg,
                host_name,
                device_name,
                html_report_r2_url,
                logs_r2_url
            FROM script_results
            WHERE script_type = 'testcase' 
              AND script_name = %s
              AND team_id = %s
            ORDER BY started_at DESC
            LIMIT %s
        """
        
        cursor.execute(query, (testcase_name, team_id, limit))
        results = cursor.fetchall()
        
        executions = []
        for row in results:
            execution = dict(row)
            execution['script_result_id'] = str(execution['script_result_id'])
            executions.append(execution)
        
        return executions
        
    except Exception as e:
        print(f"[@testcase_db] ERROR getting execution history: {e}")
        return []
    finally:
        conn.close()
