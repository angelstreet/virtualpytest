"""
Execution Results Database Operations

This module provides functions for managing execution results in the database.
Execution results track edge actions and node verifications with metrics.
"""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import uuid4

from src.utils.supabase_utils import get_supabase_client

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
        
        # Enrich results with tree names and node/edge names
        enriched_results = []
        tree_cache = {}  # Cache trees to avoid repeated queries
        
        for execution in result.data:
            enriched_execution = execution.copy()
            
            # Get tree information
            tree_id = execution.get('tree_id')
            if tree_id and tree_id not in tree_cache:
                tree_query = supabase.table('navigation_trees').select('name, metadata').eq('id', tree_id).eq('team_id', team_id).execute()
                tree_cache[tree_id] = tree_query.data[0] if tree_query.data else None
            
            tree_data = tree_cache.get(tree_id)
            if tree_data:
                # Caller must provide userinterface_name - no fallback
                enriched_execution['tree_name'] = userinterface_name
                
                # Get node/edge name from metadata
                metadata = tree_data.get('metadata', {})
                
                if execution.get('execution_type') == 'action' and execution.get('edge_id'):
                    # Find edge name using source -> target node labels
                    edge_id = execution.get('edge_id')
                    edges = metadata.get('edges', [])
                    nodes = metadata.get('nodes', [])
                    edge_name = 'Unknown Edge'
                    
                    # Create node lookup map for efficient label resolution
                    node_labels = {}
                    for node in nodes:
                        node_id = node.get('id')
                        node_data = node.get('data', {})
                        if node_id:
                            node_labels[node_id] = node_data.get('label') or node_data.get('description') or f"Node {node_id[:8]}"
                    
                    for edge in edges:
                        if edge.get('id') == edge_id:
                            # Get source and target node IDs
                            source_id = edge.get('source')
                            target_id = edge.get('target')
                            
                            if source_id and target_id:
                                source_label = node_labels.get(source_id, source_id)
                                target_label = node_labels.get(target_id, target_id)
                                edge_name = f"{source_label} -> {target_label}"
                            else:
                                # Fallback to edge data description or edge ID
                                edge_data = edge.get('data', {})
                                if edge_data.get('description'):
                                    edge_name = edge_data.get('description')
                                else:
                                    edge_name = f"Edge {edge_id[:8]}"
                            break
                    
                    enriched_execution['element_name'] = edge_name
                    
                elif execution.get('execution_type') == 'verification' and execution.get('node_id'):
                    # Find node name using label
                    node_id = execution.get('node_id')
                    nodes = metadata.get('nodes', [])
                    
                    for node in nodes:
                        if node.get('id') == node_id:
                            node_data = node.get('data', {})
                            node_name = node_data.get('label') or node_data.get('description') or f"Node {node_id[:8]}"
                            enriched_execution['element_name'] = node_name
                            break
            else:
                enriched_execution['tree_name'] = userinterface_name
            
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
    device_model: str,
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
            'device_model': device_model,
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
            print(f"[@db:execution_results:record_edge_execution] Success: {execution_id}")
            return execution_id
        else:
            print(f"[@db:execution_results:record_edge_execution] Failed")
            return None
            
    except Exception as e:
        print(f"[@db:execution_results:record_edge_execution] Error: {str(e)}")
        return None

def record_node_execution(
    team_id: str,
    tree_id: str,
    node_id: str,
    host_name: str,
    device_model: str,
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
            'device_model': device_model,
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
        print(f"  - device_model: {device_model}")
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

def get_tree_metrics(team_id: str, node_ids: List[str], edge_ids: List[str]) -> Dict:
    """Get all metrics for a tree in a single bulk query with defaults for missing metrics."""
    try:
        supabase = get_supabase()
        
        # Get all node metrics in one query
        node_metrics = {}
        if node_ids:
            node_result = supabase.table('node_metrics').select('*').eq('team_id', team_id).in_('node_id', node_ids).execute()
            for metric in node_result.data:
                node_metrics[metric['node_id']] = {
                    'volume': metric['total_executions'],
                    'success_rate': float(metric['success_rate']),
                    'avg_execution_time': metric['avg_execution_time_ms']
                }
        
        # Get all edge metrics in one query
        edge_metrics = {}
        if edge_ids:
            edge_result = supabase.table('edge_metrics').select('*').eq('team_id', team_id).in_('edge_id', edge_ids).execute()
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