"""
Navigation utilities for VirtualPyTest

This module contains navigation-related functions that provide compatibility
with the new navigation architecture while maintaining the old API.
"""

import os
import sys
import time
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

# Add project root to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
lib_dir = os.path.dirname(current_dir)
shared_dir = os.path.dirname(lib_dir)
project_root = os.path.dirname(shared_dir)

if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend_host.src.services.navigation.navigation_pathfinding import find_shortest_path
from backend_host.src.services.navigation.navigation_executor import NavigationExecutor


def find_node_by_label(nodes: List[Dict], target_label: str) -> Optional[Dict]:
    """
    Find a node by its label in the nodes list.
    
    Args:
        nodes: List of node dictionaries
        target_label: Label to search for
        
    Returns:
        Node dictionary if found, None otherwise
    """
    for node in nodes:
        if node.get('label') == target_label:
            return node
    return None


def find_edge_by_target_label(current_node_id: str, edges: List[Dict], all_nodes: List[Dict], target_label: str) -> Optional[Dict]:
    """
    Find an edge from current node that leads to a node with the target label.
    
    Args:
        current_node_id: Current node ID
        edges: List of edge dictionaries
        all_nodes: List of all nodes
        target_label: Target node label to find
        
    Returns:
        Edge dictionary if found, None otherwise
    """
    # Find edges from current node
    for edge in edges:
        if edge.get('from_node_id') == current_node_id:
            to_node_id = edge.get('to_node_id')
            # Find the target node
            for node in all_nodes:
                if node.get('node_id') == to_node_id and node.get('label') == target_label:
                    return edge
    return None


def goto_node(host, device, target_node_label: str, tree_id: str, team_id: str, context=None) -> Dict[str, Any]:
    """
    Navigate to target node using the new navigation architecture.
    This function provides compatibility with the old goto_node API.
    
    Args:
        host: Host instance
        device: Device instance  
        target_node_label: Label of the target node (e.g., 'home', 'live', 'settings')
        tree_id: Navigation tree ID
        team_id: Team ID
        context: Optional ScriptExecutionContext for tracking step results
        
    Returns:
        Dict with success status and details
    """
    try:
        print(f"[@navigation_utils:goto_node] Navigating to '{target_node_label}' using new navigation architecture")
        
        # Determine starting node from context
        start_node_id = None
        if context and hasattr(context, 'current_node_id') and context.current_node_id:
            start_node_id = context.current_node_id
            print(f"[@navigation_utils:goto_node] Starting from current location: {start_node_id}")
        else:
            print(f"[@navigation_utils:goto_node] Starting from default entry point (no current location)")
        
        # Use the new pathfinding system
        navigation_path = find_shortest_path(tree_id, target_node_label, team_id, start_node_id)
        
        if not navigation_path:
            return {
                'success': False,
                'error': f"No path found to '{target_node_label}'",
                'unified_pathfinding_used': True
            }
        
        print(f"[@navigation_utils:goto_node] Found path with {len(navigation_path)} steps")
        
        # Create NavigationExecutor and execute the path
        navigation_executor = NavigationExecutor(device)
        
        # Execute each step in the navigation path
        for i, step in enumerate(navigation_path):
            step_num = i + 1
            from_node = step.get('from_node_label', 'unknown')
            to_node = step.get('to_node_label', 'unknown')
            
            print(f"[@navigation_utils:goto_node] Step {step_num}/{len(navigation_path)}: {from_node} → {to_node}")
            
            # Execute the step using NavigationExecutor
            step_start_time = time.time()
            
            # Get the actions for this step
            actions = step.get('actions', [])
            if actions:
                from backend_host.src.services.actions.action_executor import ActionExecutor
                action_executor = ActionExecutor(device, tree_id, step.get('edge_id'))
                result = action_executor.execute_actions(actions, team_id=team_id)
                
                if not result.get('success', False):
                    error_msg = f"Navigation step {step_num} failed: {result.get('message', 'Unknown error')}"
                    print(f"❌ [@navigation_utils:goto_node] {error_msg}")
                    return {
                        'success': False,
                        'error': error_msg,
                        'step_failed': step_num,
                        'step_details': step
                    }
            
            step_execution_time = int((time.time() - step_start_time) * 1000)
            
            # Update context if provided
            if context:
                # Update current node ID
                context.current_node_id = step.get('to_node_id')
                
                # Record step result
                step_result = {
                    'step_number': step_num,
                    'from_node': from_node,
                    'to_node': to_node,
                    'from_node_id': step.get('from_node_id'),
                    'to_node_id': step.get('to_node_id'),
                    'action_type': 'navigation',
                    'action_command': step.get('action_command', 'navigate'),
                    'success': True,
                    'execution_time_ms': step_execution_time,
                    'timestamp': datetime.now().strftime('%H:%M:%S'),
                    'message': f"Navigation step {step_num}: {from_node} → {to_node}"
                }
                
                if hasattr(context, 'step_results'):
                    context.step_results.append(step_result)
            
            print(f"✅ [@navigation_utils:goto_node] Step {step_num} completed successfully")
        
        # Final success result
        total_time = sum(int((time.time() - time.time()) * 1000) for _ in navigation_path)  # Placeholder
        
        print(f"🎉 [@navigation_utils:goto_node] Successfully navigated to '{target_node_label}'!")
        
        return {
            'success': True,
            'message': f"Successfully navigated to '{target_node_label}'",
            'steps_executed': len(navigation_path),
            'total_time_ms': total_time,
            'target_node_label': target_node_label,
            'unified_pathfinding_used': True
        }
        
    except Exception as e:
        error_msg = f"Navigation to '{target_node_label}' failed: {str(e)}"
        print(f"❌ [@navigation_utils:goto_node] {error_msg}")
        return {
            'success': False,
            'error': error_msg,
            'exception': str(e)
        }


def load_navigation_tree(userinterface_name: str, script_name: str = "script") -> Dict[str, Any]:
    """
    Load navigation tree using direct database access (no HTTP requests).
    This function is maintained for compatibility but delegates to the new system.
    
    Args:
        userinterface_name: Interface name (e.g., 'horizon_android_mobile')
        script_name: Name of the script for logging
        
    Returns:
        Dictionary with success status and tree data or error
    """
    try:
        team_id = "7fdeb4bb-3639-4ec3-959f-b54769a219ce"
        
        from shared.lib.supabase.userinterface_db import get_all_userinterfaces
        
        userinterfaces = get_all_userinterfaces(team_id)
        if not userinterfaces:
            return {
                'success': False,
                'error': 'No userinterfaces found for team'
            }
        
        # Find the matching userinterface
        target_ui = None
        for ui in userinterfaces:
            if ui.get('name') == userinterface_name:
                target_ui = ui
                break
        
        if not target_ui:
            return {
                'success': False,
                'error': f"Userinterface '{userinterface_name}' not found"
            }
        
        tree_id = target_ui.get('tree_id')
        if not tree_id:
            return {
                'success': False,
                'error': f"No tree_id found for userinterface '{userinterface_name}'"
            }
        
        # Load tree data from database
        from shared.lib.supabase.navigation_trees_db import get_navigation_tree_with_nodes_and_edges
        
        tree_data = get_navigation_tree_with_nodes_and_edges(tree_id, team_id)
        if not tree_data:
            return {
                'success': False,
                'error': f"Failed to load navigation tree data for tree_id: {tree_id}"
            }
        
        print(f"[@navigation_utils:load_navigation_tree] Successfully loaded tree '{tree_id}' for '{userinterface_name}'")
        
        return {
            'success': True,
            'tree_id': tree_id,
            'team_id': team_id,
            'userinterface_name': userinterface_name,
            'tree_data': tree_data,
            'nodes': tree_data.get('nodes', []),
            'edges': tree_data.get('edges', [])
        }
        
    except Exception as e:
        error_msg = f"Failed to load navigation tree for '{userinterface_name}': {str(e)}"
        print(f"❌ [@navigation_utils:load_navigation_tree] {error_msg}")
        return {
            'success': False,
            'error': error_msg,
            'exception': str(e)
        }