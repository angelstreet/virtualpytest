"""
Navigation Execution System

This module provides a clean, standardized way to execute navigation that can be used by:
- Python code directly (scripts, automation, etc.)
- API endpoints (maintaining consistency)
- Frontend hooks (via API calls)

The NavigationExecutor orchestrates ActionExecutor and VerificationExecutor to provide
complete navigation execution with proper error handling and logging.
"""

import time
from typing import Dict, List, Optional, Any
from backend_core.src.services.actions.action_executor import ActionExecutor
from backend_core.src.services.verifications.verification_executor import VerificationExecutor
from backend_core.src.services.navigation.navigation_pathfinding import find_shortest_path
from shared.lib.utils.app_utils import get_team_id


class NavigationExecutor:
    """
    Standardized navigation executor that orchestrates action and verification execution
    to provide complete navigation functionality.
    """
    
    def __init__(self, host: Dict[str, Any], device_id: Optional[str] = None, team_id: Optional[str] = None):
        """
        Initialize NavigationExecutor
        
        Args:
            host: Host configuration dict with host_name, devices, etc.
            device_id: Optional device ID for multi-device hosts
            team_id: Optional team ID, defaults to system team ID
        """
        self.host = host
        self.device_id = device_id
        self.team_id = team_id or get_team_id()
        
        # Initialize standardized executors (will be updated with navigation context per execution)
        self.action_executor = None
        self.verification_executor = None
        
        # Validate host configuration
        if not host or not host.get('host_name'):
            raise ValueError("Host configuration with host_name is required")
    
    def get_available_context(self, device_model: str = None, userinterface_name: str = None) -> Dict[str, Any]:
        """
        Get available navigation context for AI based on device model and user interface
        
        Args:
            device_model: Device model (e.g., 'android_mobile', 'android_tv')
            userinterface_name: User interface name for context
            
        Returns:
            Dict with available navigation nodes and tree information
        """
        try:
            from shared.lib.utils.navigation_utils import load_navigation_tree_with_hierarchy
            from shared.lib.utils.navigation_exceptions import NavigationTreeError, UnifiedCacheError
            
            print(f"[@navigation_executor] Loading navigation context for interface: {userinterface_name}")
            
            available_nodes = []
            tree_id = None
            
            if userinterface_name:
                # Load navigation tree with hierarchy (exactly like script framework)
                print(f"[@navigation_executor] Loading unified navigation tree hierarchy...")
                
                try:
                    # Use new unified loading - NO FALLBACK (exactly like script framework line 273)
                    tree_result = load_navigation_tree_with_hierarchy(userinterface_name, "ai_context")
                    
                    # Extract tree data
                    tree_id = tree_result['tree_id']
                    nodes = tree_result['root_tree']['nodes']
                    
                    # Extract node names for AI context
                    available_nodes = [node.get('node_name', node.get('node_id', '')) for node in nodes if node.get('node_name')]
                    
                    print(f"[@navigation_executor] Successfully loaded navigation tree: {tree_id}")
                    print(f"[@navigation_executor] Available nodes: {available_nodes}")
                    
                except (NavigationTreeError, UnifiedCacheError) as e:
                    print(f"[@navigation_executor] Navigation tree loading failed: {e}")
                    # Don't fallback - let it fail cleanly
                    tree_id = None
                    available_nodes = []
                except Exception as e:
                    print(f"[@navigation_executor] Unexpected error loading navigation tree: {e}")
                    tree_id = None
                    available_nodes = []
            
            print(f"[@navigation_executor] Loaded {len(available_nodes)} navigation nodes for tree: {tree_id}")
            
            return {
                'service_type': 'navigation',
                'device_id': self.device_id or 'device1',
                'device_model': device_model,
                'userinterface_name': userinterface_name,
                'tree_id': tree_id,
                'available_nodes': available_nodes
            }
            
        except Exception as e:
            print(f"[@navigation_executor] Error loading navigation context: {e}")
            return {
                'service_type': 'navigation',
                'device_id': self.device_id or 'device1',
                'device_model': device_model,
                'userinterface_name': userinterface_name,
                'tree_id': None,
                'available_nodes': []
            }
    
    def execute_navigation(self, 
                          tree_id: str, 
                          target_node_id: str, 
                          current_node_id: Optional[str] = None,
                          image_source_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute complete navigation to target node
        
        Args:
            tree_id: Navigation tree ID
            target_node_id: Target node to navigate to
            current_node_id: Optional current node ID (for pathfinding)
            image_source_url: Optional source image URL for verifications
            
        Returns:
            Dict with success status, execution details, and statistics
        """
        start_time = time.time()
        
        print(f"[@lib:navigation_execution:execute_navigation] Starting navigation to {target_node_id} in tree {tree_id}")
        print(f"[@lib:navigation_execution:execute_navigation] Current node: {current_node_id}")
        print(f"[@lib:navigation_execution:execute_navigation] Host: {self.host.get('host_name')}")
        
        try:
            # 1. Get navigation path using existing pathfinding
            print(f"[@lib:navigation_execution:execute_navigation] Getting navigation path...")
            transitions = find_shortest_path(tree_id, target_node_id, self.team_id, current_node_id)
            
            if not transitions:
                return {
                    'success': False,
                    'error': 'No navigation path found',
                    'tree_id': tree_id,
                    'target_node_id': target_node_id,
                    'current_node_id': current_node_id,
                    'transitions_executed': 0,
                    'total_transitions': 0,
                    'actions_executed': 0,
                    'total_actions': 0,
                    'execution_time': 0
                }
            
            print(f"[@lib:navigation_execution:execute_navigation] Found {len(transitions)} transitions")
            
            # 2. Execute each transition using standardized action executor
            transitions_executed = 0
            actions_executed = 0
            total_actions = sum(len(t.get('actions', [])) for t in transitions)
            
            print(f"[@lib:navigation_execution:execute_navigation] Executing {len(transitions)} transitions with {total_actions} total actions")
            
            for i, transition in enumerate(transitions):
                print(f"[@lib:navigation_execution:execute_navigation] Executing transition {i+1}/{len(transitions)}: {transition.get('description', 'Unknown')}")
                
                actions = transition.get('actions', [])
                retry_actions = transition.get('retryActions', [])
                
                if actions:
                    # Initialize action executor with navigation context
                    edge_id = transition.get('edge_id')
                    
                    # NEW: Handle cross-tree transitions with appropriate tree context
                    execution_tree_id = tree_id  # Default to original tree_id
                    if transition.get('tree_context_change', False):
                        # For cross-tree transitions, use the target tree context
                        execution_tree_id = transition.get('to_tree_id', tree_id)
                        print(f"[@lib:navigation_execution:execute_navigation] Cross-tree transition detected, using tree context: {execution_tree_id}")
                    
                    action_executor = ActionExecutor(
                        host=self.host,
                        device_id=self.device_id,
                        tree_id=execution_tree_id,
                        edge_id=edge_id,
                        team_id=self.team_id
                    )
                    
                    # NEW: Handle virtual cross-tree actions
                    if transition.get('is_virtual', False):
                        print(f"[@lib:navigation_execution:execute_navigation] Executing virtual cross-tree transition: {transition.get('transition_type')}")
                        result = self._execute_virtual_transition(transition)
                    else:
                        result = action_executor.execute_actions(
                            actions=actions,
                            retry_actions=retry_actions
                        )
                    
                    if not result.get('success'):
                        # Calculate where we actually are: if we're at transition i and it failed,
                        # we're still at the from_node_id of the failed transition
                        # (or at the to_node_id of the previous successful transition)
                        if transitions_executed > 0:
                            # We successfully completed some transitions, so we're at the to_node_id of the last successful one
                            final_position_node_id = transitions[transitions_executed - 1].get('to_node_id', current_node_id)
                        else:
                            # No transitions succeeded, we're still at the starting position
                            final_position_node_id = current_node_id
                        
                        # Build detailed error message with transition context
                        transition_description = transition.get('description', f'Transition {i+1}')
                        error_message = result.get('error', result.get('message', 'Unknown error'))
                        
                        detailed_error = f'Failed in "{transition_description}": {error_message}'
                        
                        return {
                            'success': False,
                            'error': detailed_error,
                            'tree_id': tree_id,
                            'target_node_id': target_node_id,
                            'current_node_id': current_node_id,
                            'final_position_node_id': final_position_node_id,  # Where we actually ended up
                            'transitions_executed': transitions_executed,
                            'total_transitions': len(transitions),
                            'actions_executed': actions_executed,
                            'total_actions': total_actions,
                            'execution_time': time.time() - start_time,
                            'failed_transition': i + 1,
                            'failed_transition_description': transition_description,
                            'action_results': result.get('results', []),
                            'failed_actions': result.get('failed_actions', [])
                        }
                    
                    actions_executed += result.get('passed_count', 0)
                
                transitions_executed += 1
                print(f"[@lib:navigation_execution:execute_navigation] Transition {i+1} completed successfully")
            
            # 3. Execute target node verifications using standardized verification executor
            print(f"[@lib:navigation_execution:execute_navigation] Checking for target node verifications...")
            target_node_verifications = self._get_node_verifications(tree_id, target_node_id)
            
            verification_results = []
            if target_node_verifications:
                print(f"[@lib:navigation_execution:execute_navigation] Executing {len(target_node_verifications)} target node verifications")
                
                # Initialize verification executor with navigation context
                verification_executor = VerificationExecutor(
                    host=self.host,
                    device_id=self.device_id,
                    tree_id=tree_id,
                    node_id=target_node_id,
                    team_id=self.team_id
                )
                
                result = verification_executor.execute_verifications(
                    verifications=target_node_verifications,
                    image_source_url=image_source_url
                )
                
                verification_results = result.get('results', [])
                
                if not result.get('success'):
                    # All transitions succeeded but verification failed - we're at the target node
                    final_position_node_id = target_node_id
                    
                    return {
                        'success': False,
                        'error': f'Target node verification failed: {result.get("error", "Unknown error")}',
                        'tree_id': tree_id,
                        'target_node_id': target_node_id,
                        'current_node_id': current_node_id,
                        'final_position_node_id': final_position_node_id,  # Where we actually ended up
                        'transitions_executed': transitions_executed,
                        'total_transitions': len(transitions),
                        'actions_executed': actions_executed,
                        'total_actions': total_actions,
                        'execution_time': time.time() - start_time,
                        'verification_results': verification_results
                    }
                
                print(f"[@lib:navigation_execution:execute_navigation] Target node verifications completed successfully")
            else:
                print(f"[@lib:navigation_execution:execute_navigation] No target node verifications found")
            
            # 4. Navigation completed successfully
            execution_time = time.time() - start_time
            
            print(f"[@lib:navigation_execution:execute_navigation] Navigation completed successfully in {execution_time:.2f}s")
            print(f"[@lib:navigation_execution:execute_navigation] Executed {transitions_executed}/{len(transitions)} transitions, {actions_executed}/{total_actions} actions")
            
            # Update current position to target node since all transitions succeeded
            final_position_node_id = target_node_id
            
            return {
                'success': True,
                'message': f'Navigation to {target_node_id} completed successfully',
                'tree_id': tree_id,
                'target_node_id': target_node_id,
                'current_node_id': current_node_id,
                'final_position_node_id': final_position_node_id,  # Where we actually ended up
                'transitions_executed': transitions_executed,
                'total_transitions': len(transitions),
                'actions_executed': actions_executed,
                'total_actions': total_actions,
                'execution_time': execution_time,
                'verification_results': verification_results,
                'navigation_path': [t.get('description', f"Transition {i+1}") for i, t in enumerate(transitions)]
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            print(f"[@lib:navigation_execution:execute_navigation] Navigation failed with error: {str(e)}")
            
            # On exception, we don't know exactly where we are, assume starting position
            final_position_node_id = current_node_id
            
            return {
                'success': False,
                'error': f'Navigation execution error: {str(e)}',
                'tree_id': tree_id,
                'target_node_id': target_node_id,
                'current_node_id': current_node_id,
                'final_position_node_id': final_position_node_id,  # Where we actually ended up
                'transitions_executed': 0,
                'total_transitions': 0,
                'actions_executed': 0,
                'total_actions': 0,
                'execution_time': execution_time
            }
    
    def get_navigation_preview(self, 
                             tree_id: str, 
                             target_node_id: str, 
                             current_node_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get navigation preview without executing
        
        Args:
            tree_id: Navigation tree ID
            target_node_id: Target node to navigate to
            current_node_id: Optional current node ID (for pathfinding)
            
        Returns:
            Dict with preview information
        """
        print(f"[@lib:navigation_execution:get_navigation_preview] Getting preview for navigation to {target_node_id} in tree {tree_id}")
        
        try:
            # Get navigation path using existing pathfinding
            transitions = find_shortest_path(tree_id, target_node_id, self.team_id, current_node_id)
            
            if not transitions:
                return {
                    'success': False,
                    'error': 'No navigation path found',
                    'tree_id': tree_id,
                    'target_node_id': target_node_id,
                    'current_node_id': current_node_id,
                    'transitions': [],
                    'total_transitions': 0,
                    'total_actions': 0
                }
            
            total_actions = sum(len(t.get('actions', [])) for t in transitions)
            
            return {
                'success': True,
                'tree_id': tree_id,
                'target_node_id': target_node_id,
                'current_node_id': current_node_id,
                'transitions': transitions,
                'total_transitions': len(transitions),
                'total_actions': total_actions,
                'navigation_type': 'preview'
            }
            
        except Exception as e:
            print(f"[@lib:navigation_execution:get_navigation_preview] Preview failed with error: {str(e)}")
            
            return {
                'success': False,
                'error': f'Navigation preview error: {str(e)}',
                'tree_id': tree_id,
                'target_node_id': target_node_id,
                'current_node_id': current_node_id,
                'transitions': [],
                'total_transitions': 0,
                'total_actions': 0
            }
    
    def _get_node_verifications(self, tree_id: str, node_id: str) -> List[Dict[str, Any]]:
        """
        Get verifications for a specific node
        
        Args:
            tree_id: Navigation tree ID
            node_id: Node ID to get verifications for
            
        Returns:
            List of verification dictionaries
        """
        try:
            # Get cached graph and node info
            from shared.lib.utils.navigation_cache import get_cached_graph
            from shared.lib.utils.navigation_graph import get_node_info
            
            G = get_cached_graph(tree_id, self.team_id)
            if not G:
                print(f"[@lib:navigation_execution:_get_node_verifications] No cached graph found for tree {tree_id}")
                return []
            
            node_info = get_node_info(G, node_id)
            if not node_info:
                print(f"[@lib:navigation_execution:_get_node_verifications] No node info found for node {node_id}")
                return []
            
            # Extract verifications from node data
            verifications = []
            if 'verifications' in node_info:
                verifications = node_info.get('verifications', [])
            elif 'data' in node_info and isinstance(node_info['data'], dict):
                verifications = node_info['data'].get('verifications', [])
            
            print(f"[@lib:navigation_execution:_get_node_verifications] Found {len(verifications)} verifications for node {node_id}")
            return verifications
            
        except Exception as e:
            print(f"[@lib:navigation_execution:_get_node_verifications] Error getting node verifications: {str(e)}")
            return []
    
    def _execute_virtual_transition(self, transition: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute virtual cross-tree transitions (ENTER_SUBTREE, EXIT_SUBTREE)
        
        Args:
            transition: Virtual transition dictionary
            
        Returns:
            Execution result dictionary
        """
        transition_type = transition.get('transition_type', 'UNKNOWN')
        from_tree_id = transition.get('from_tree_id')
        to_tree_id = transition.get('to_tree_id')
        
        print(f"[@lib:navigation_execution:_execute_virtual_transition] Executing {transition_type}: {from_tree_id} → {to_tree_id}")
        
        try:
            # Virtual transitions are always successful - they represent logical tree context changes
            # The actual navigation is handled by the unified pathfinding system
            
            if transition_type == 'ENTER_SUBTREE':
                print(f"[@lib:navigation_execution:_execute_virtual_transition] Entering subtree: {to_tree_id}")
                # Future: Could add subtree entry logic here (e.g., cache warming)
                
            elif transition_type == 'EXIT_SUBTREE':
                print(f"[@lib:navigation_execution:_execute_virtual_transition] Exiting subtree: {from_tree_id}")
                # Future: Could add subtree exit logic here (e.g., cleanup)
            
            # Virtual transitions complete instantly with success
            return {
                'success': True,
                'message': f'Virtual {transition_type} transition completed',
                'passed_count': 1,
                'failed_count': 0,
                'results': [{
                    'success': True,
                    'action_type': 'virtual_transition',
                    'transition_type': transition_type,
                    'from_tree_id': from_tree_id,
                    'to_tree_id': to_tree_id,
                    'execution_time': 0
                }]
            }
            
        except Exception as e:
            print(f"[@lib:navigation_execution:_execute_virtual_transition] Error executing virtual transition: {str(e)}")
            return {
                'success': False,
                'error': f'Virtual transition failed: {str(e)}',
                'passed_count': 0,
                'failed_count': 1,
                'results': []
            } 