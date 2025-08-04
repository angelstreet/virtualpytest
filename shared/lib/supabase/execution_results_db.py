"""
Execution Results Database Operations

This module provides functions for managing execution results in the database.
Execution results track edge actions and node verifications with metrics.
Now aligned with embedded actions/verifications architecture.
"""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import uuid4

from shared.lib.utils.supabase_utils import get_supabase_client

def get_supabase():
    """Get the Supabase client instance."""
    return get_supabase_client()

def get_execution_results(
    team_id: str,
    execution_type: Optional[str] = None,
    tree_id: Optional[str] = None,
    limit: int = 100,
    userinterface_name: Optional[str] = None
) -> Dict:
    """Get execution results with filtering and enriched with tree/node/edge names."""
    try:
        print(f"[@db:execution_results:get_execution_results] Getting execution results:")
        print(f"  - team_id: {team_id}")
        print(f"  - execution_type: {execution_type}")
        print(f"  - tree_id: {tree_id}")
        print(f"  - limit: {limit}")
        
        supabase = get_supabase()
        query = supabase.table('execution_results').select('*').eq('team_id', team_id)
        
        # Add filters
        if execution_type:
            query = query.eq('execution_type', execution_type)
        if tree_id:
            query = query.eq('tree_id', tree_id)
        
        # Execute query with ordering and limit
        result = query.order('executed_at', desc=True).limit(limit).execute()
        
        print(f"[@db:execution_results:get_execution_results] Found {len(result.data)} execution results")
        
        # Enrich results with tree names and node/edge names using new normalized structure
        enriched_results = []
        tree_cache = {}  # Cache trees to avoid repeated queries
        
        for execution in result.data:
            enriched_execution = execution.copy()
            
            # Get tree information from normalized tables
            tree_id = execution.get('tree_id')
            if tree_id and tree_id not in tree_cache:
                tree_query = supabase.table('navigation_trees').select('name').eq('id', tree_id).eq('team_id', team_id).execute()
                tree_cache[tree_id] = tree_query.data[0] if tree_query.data else None
            
            tree_data = tree_cache.get(tree_id)
            if tree_data:
                enriched_execution['tree_name'] = tree_data.get('name', userinterface_name or 'Unknown Tree')
                
                if execution.get('execution_type') == 'action' and execution.get('edge_id'):
                    # Get edge information from normalized structure
                    edge_id = execution.get('edge_id')
                    edge_query = supabase.table('navigation_edges').select(
                        'label, source_node_id, target_node_id'
                    ).eq('edge_id', edge_id).eq('tree_id', tree_id).execute()
                    
                    if edge_query.data:
                        edge_data = edge_query.data[0]
                        source_id = edge_data.get('source_node_id')
                        target_id = edge_data.get('target_node_id')
                        
                        # Get node labels for better edge description
                        source_label = 'Unknown'
                        target_label = 'Unknown'
                        
                        if source_id:
                            source_query = supabase.table('navigation_nodes').select('label').eq('node_id', source_id).eq('tree_id', tree_id).execute()
                            if source_query.data:
                                source_label = source_query.data[0].get('label', source_id)
                        
                        if target_id:
                            target_query = supabase.table('navigation_nodes').select('label').eq('node_id', target_id).eq('tree_id', tree_id).execute()
                            if target_query.data:
                                target_label = target_query.data[0].get('label', target_id)
                        
                        edge_name = edge_data.get('label') or f"{source_label} → {target_label}"
                        enriched_execution['element_name'] = edge_name
                    else:
                        enriched_execution['element_name'] = f"Edge {edge_id[:8]}"
                    
                elif execution.get('execution_type') == 'verification' and execution.get('node_id'):
                    # Get node information from normalized structure
                    node_id = execution.get('node_id')
                    node_query = supabase.table('navigation_nodes').select('label').eq('node_id', node_id).eq('tree_id', tree_id).execute()
                    
                    if node_query.data:
                        node_label = node_query.data[0].get('label', f"Node {node_id[:8]}")
                        enriched_execution['element_name'] = node_label
                    else:
                        enriched_execution['element_name'] = f"Node {node_id[:8]}"
            else:
                enriched_execution['tree_name'] = userinterface_name or 'Unknown Tree'
            
            enriched_results.append(enriched_execution)
        
        return {
            'success': True,
            'execution_results': enriched_results,
            'count': len(enriched_results)
        }
        
    except Exception as e:
        print(f"[@db:execution_results:get_execution_results] Error: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'execution_results': [],
            'count': 0
        }

def record_edge_execution(
    team_id: str,
    tree_id: str,
    edge_id: str,
    host_name: str,
    success: bool,
    execution_time_ms: int,
    message: str = "",
    error_details: Optional[Dict] = None,
    script_result_id: Optional[str] = None,
    script_context: str = 'direct'
) -> Optional[str]:
    """Record edge action execution directly to database."""
    try:
        execution_id = str(uuid4())
        
        execution_data = {
            'id': execution_id,
            'team_id': team_id,
            'tree_id': tree_id,
            'edge_id': edge_id,
            'execution_type': 'action',
            'host_name': host_name,
            'success': success,
            'execution_time_ms': execution_time_ms,
            'message': message,
            'error_details': error_details,
            'executed_at': datetime.now().isoformat(),
            'script_result_id': script_result_id,
            'script_context': script_context
        }
        
        supabase = get_supabase()
        result = supabase.table('execution_results').insert(execution_data).execute()
        
        if result.data:
            return execution_id
        else:
            return None
            
    except Exception as e:
        print(f"[@db:execution_results:record_edge_execution] Error: {str(e)}")
        return None

def record_node_execution(
    team_id: str,
    tree_id: str,
    node_id: str,
    host_name: str,
    success: bool,
    execution_time_ms: int,
    message: str = "",
    error_details: Optional[Dict] = None,
    script_result_id: Optional[str] = None,
    script_context: str = 'direct'
) -> Optional[str]:
    """Record node verification execution directly to database."""
    try:
        execution_id = str(uuid4())
        
        execution_data = {
            'id': execution_id,
            'team_id': team_id,
            'tree_id': tree_id,
            'node_id': node_id,
            'execution_type': 'verification',
            'host_name': host_name,
            'success': success,
            'execution_time_ms': execution_time_ms,
            'message': message,
            'error_details': error_details,
            'executed_at': datetime.now().isoformat(),
            'script_result_id': script_result_id,
            'script_context': script_context
        }
        
        print(f"[@db:execution_results:record_node_execution] Recording execution:")
        print(f"  - execution_id: {execution_id}")
        print(f"  - team_id: {team_id}")
        print(f"  - tree_id: {tree_id}")
        print(f"  - node_id: {node_id}")
        print(f"  - host_name: {host_name}")
        print(f"  - success: {success}")
        print(f"  - execution_time_ms: {execution_time_ms}")
        print(f"  - message: {message}")
        print(f"  - error_details: {error_details}")
        
        supabase = get_supabase()
        result = supabase.table('execution_results').insert(execution_data).execute()
        
        if result.data:
            print(f"[@db:execution_results:record_node_execution] Success: {execution_id}")
            return execution_id
        else:
            print(f"[@db:execution_results:record_node_execution] Failed")
            return None
            
    except Exception as e:
        print(f"[@db:execution_results:record_node_execution] Error: {str(e)}")
        return None

def record_action_execution(
    team_id: str,
    tree_id: str,
    edge_id: str,
    action_command: str,
    action_params: Dict,
    action_index: int,
    is_retry_action: bool,

    success: bool,
    execution_time_ms: int,
    host_name: str,
    execution_id: Optional[str] = None,
    error_message: Optional[str] = None,
    error_details: Optional[Dict] = None
) -> Optional[str]:
    """Record individual action execution to history table."""
    try:
        action_execution_id = execution_id or str(uuid4())
        
        action_data = {
            'id': action_execution_id,
            'team_id': team_id,
            'tree_id': tree_id,
            'edge_id': edge_id,
            'action_command': action_command,
            'action_params': action_params,
            'action_index': action_index,
            'is_retry_action': is_retry_action,

            'success': success,
            'execution_time_ms': execution_time_ms,
            'host_name': host_name,
            'error_message': error_message,
            'error_details': error_details,
            'executed_at': datetime.now().isoformat()
        }
        
        print(f"[@db:execution_results:record_action_execution] Recording action execution:")
        print(f"  - action_execution_id: {action_execution_id}")
        print(f"  - edge_id: {edge_id}")
        print(f"  - action_command: {action_command}")
        print(f"  - success: {success}")
        print(f"  - execution_time_ms: {execution_time_ms}")
        
        supabase = get_supabase()
        result = supabase.table('action_execution_history').insert(action_data).execute()
        
        if result.data:
            print(f"[@db:execution_results:record_action_execution] Success: {action_execution_id}")
            return action_execution_id
        else:
            print(f"[@db:execution_results:record_action_execution] Failed")
            return None
            
    except Exception as e:
        print(f"[@db:execution_results:record_action_execution] Error: {str(e)}")
        return None

def record_verification_execution(
    team_id: str,
    tree_id: str,
    node_id: str,
    verification_type: str,
    verification_command: str,
    verification_params: Dict,
    verification_index: int,
    success: bool,
    execution_time_ms: int,
    host_name: str,
    execution_id: Optional[str] = None,
    error_message: Optional[str] = None,
    error_details: Optional[Dict] = None,
    confidence_score: Optional[float] = None,
    result_data: Optional[Dict] = None
) -> Optional[str]:
    """Record individual verification execution to history table."""
    try:
        verification_execution_id = execution_id or str(uuid4())
        
        verification_data = {
            'id': verification_execution_id,
            'team_id': team_id,
            'tree_id': tree_id,
            'node_id': node_id,
            'verification_type': verification_type,
            'verification_command': verification_command,
            'verification_params': verification_params,
            'verification_index': verification_index,
            'success': success,
            'execution_time_ms': execution_time_ms,
            'host_name': host_name,
            'error_message': error_message,
            'error_details': error_details,
            'confidence_score': confidence_score,
            'result_data': result_data,
            'executed_at': datetime.now().isoformat()
        }
        
        print(f"[@db:execution_results:record_verification_execution] Recording verification execution:")
        print(f"  - verification_execution_id: {verification_execution_id}")
        print(f"  - node_id: {node_id}")
        print(f"  - verification_command: {verification_command}")
        print(f"  - success: {success}")
        print(f"  - execution_time_ms: {execution_time_ms}")
        
        supabase = get_supabase()
        result = supabase.table('verification_execution_history').insert(verification_data).execute()
        
        if result.data:
            print(f"[@db:execution_results:record_verification_execution] Success: {verification_execution_id}")
            return verification_execution_id
        else:
            print(f"[@db:execution_results:record_verification_execution] Failed")
            return None
            
    except Exception as e:
        print(f"[@db:execution_results:record_verification_execution] Error: {str(e)}")
        return None

def get_tree_metrics(team_id: str, node_ids: List[str], edge_ids: List[str]) -> Dict:
    """Get all metrics for a tree in a single bulk query with defaults for missing metrics."""
    try:
        supabase = get_supabase()
        
        # Get all node metrics in one query using new aggregated structure
        node_metrics = {}
        if node_ids:
            node_result = supabase.table('node_metrics').select(
                'node_id, total_executions, success_rate, avg_execution_time_ms'
            ).eq('team_id', team_id).in_('node_id', node_ids).execute()
            
            for metric in node_result.data:
                node_metrics[metric['node_id']] = {
                    'volume': metric['total_executions'],
                    'success_rate': float(metric['success_rate']),
                    'avg_execution_time': metric['avg_execution_time_ms']
                }
        
        # Get all edge metrics in one query using new aggregated structure
        edge_metrics = {}
        if edge_ids:
            edge_result = supabase.table('edge_metrics').select(
                'edge_id, total_executions, success_rate, avg_execution_time_ms'
            ).eq('team_id', team_id).in_('edge_id', edge_ids).execute()
            
            for metric in edge_result.data:
                edge_metrics[metric['edge_id']] = {
                    'volume': metric['total_executions'],
                    'success_rate': float(metric['success_rate']),
                    'avg_execution_time': metric['avg_execution_time_ms']
                }
        
        # Fill in defaults for missing metrics
        default_metrics = {'volume': 0, 'success_rate': 0.0, 'avg_execution_time': 0}
        
        for node_id in node_ids:
            if node_id not in node_metrics:
                node_metrics[node_id] = default_metrics
        
        for edge_id in edge_ids:
            if edge_id not in edge_metrics:
                edge_metrics[edge_id] = default_metrics
        
        return {
            'nodes': node_metrics,
            'edges': edge_metrics
        }
        
    except Exception as e:
        print(f"[@db:execution_results:get_tree_metrics] Error: {str(e)}")
        # Return defaults for all requested IDs on error
        default_metrics = {'volume': 0, 'success_rate': 0.0, 'avg_execution_time': 0}
        return {
            'nodes': {node_id: default_metrics for node_id in node_ids},
            'edges': {edge_id: default_metrics for edge_id in edge_ids}
        }

def get_action_execution_history(
    team_id: str,
    edge_id: Optional[str] = None,
    tree_id: Optional[str] = None,
    limit: int = 100
) -> Dict:
    """Get detailed action execution history."""
    try:
        supabase = get_supabase()
        query = supabase.table('action_execution_history').select('*').eq('team_id', team_id)
        
        if edge_id:
            query = query.eq('edge_id', edge_id)
        if tree_id:
            query = query.eq('tree_id', tree_id)
        
        result = query.order('executed_at', desc=True).limit(limit).execute()
        
        return {
            'success': True,
            'action_executions': result.data,
            'count': len(result.data)
        }
        
    except Exception as e:
        print(f"[@db:execution_results:get_action_execution_history] Error: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'action_executions': [],
            'count': 0
        }

def get_verification_execution_history(
    team_id: str,
    node_id: Optional[str] = None,
    tree_id: Optional[str] = None,
    limit: int = 100
) -> Dict:
    """Get detailed verification execution history."""
    try:
        supabase = get_supabase()
        query = supabase.table('verification_execution_history').select('*').eq('team_id', team_id)
        
        if node_id:
            query = query.eq('node_id', node_id)
        if tree_id:
            query = query.eq('tree_id', tree_id)
        
        result = query.order('executed_at', desc=True).limit(limit).execute()
        
        return {
            'success': True,
            'verification_executions': result.data,
            'count': len(result.data)
        }
        
    except Exception as e:
        print(f"[@db:execution_results:get_verification_execution_history] Error: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'verification_executions': [],
            'count': 0
        }

def update_node_metrics_from_embedded_verifications(
    team_id: str,
    tree_id: str,
    node_id: str,
    verifications: List[Dict]
) -> bool:
    """Update node metrics by analyzing embedded verifications count and types."""
    try:
        verification_types = []
        for verification in verifications:
            v_type = verification.get('verification_type') or verification.get('type')
            if v_type and v_type not in verification_types:
                verification_types.append(v_type)
        
        supabase = get_supabase()
        
        # Upsert node metrics with verification metadata
        upsert_data = {
            'node_id': node_id,
            'tree_id': tree_id,
            'team_id': team_id,
            'verification_count': len(verifications),
            'verification_types': verification_types,
            'updated_at': datetime.now().isoformat()
        }
        
        result = supabase.table('node_metrics').upsert(
            upsert_data,
            on_conflict='node_id,tree_id,team_id'
        ).execute()
        
        return bool(result.data)
        
    except Exception as e:
        print(f"[@db:execution_results:update_node_metrics_from_embedded_verifications] Error: {str(e)}")
        return False

def update_edge_metrics_from_embedded_actions(
    team_id: str,
    tree_id: str,
    edge_id: str,
    actions: List[Dict],
    retry_actions: List[Dict] = None,

    final_wait_time: int = 2000
) -> bool:
    """Update edge metrics by analyzing embedded actions count and types."""
    try:
        retry_actions = retry_actions or []

        
        action_types = []
        for action in actions:
            a_type = action.get('command') or action.get('action_type')
            if a_type and a_type not in action_types:
                action_types.append(a_type)
        
        for retry_action in retry_actions:
            a_type = retry_action.get('command') or retry_action.get('action_type')
            if a_type and a_type not in action_types:
                action_types.append(a_type)
        
        supabase = get_supabase()
        
        # Upsert edge metrics with action metadata
        upsert_data = {
            'edge_id': edge_id,
            'tree_id': tree_id,
            'team_id': team_id,
            'action_count': len(actions),
            'retry_action_count': len(retry_actions),

            'action_types': action_types,
            'final_wait_time': final_wait_time,
            'updated_at': datetime.now().isoformat()
        }
        
        result = supabase.table('edge_metrics').upsert(
            upsert_data,
            on_conflict='edge_id,tree_id,team_id'
        ).execute()
        
        return bool(result.data)
        
    except Exception as e:
        print(f"[@db:execution_results:update_edge_metrics_from_embedded_actions] Error: {str(e)}")
        return False 