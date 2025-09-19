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
    
    def __init__(self, host: Dict[str, Any], device_id: str, team_id: Optional[str] = None):
        """
        Initialize NavigationExecutor with all required parameters
        
        Args:
            host: Host configuration dict with host_name, devices, etc.
            device_id: Device ID string
            team_id: Optional team ID, defaults to system team ID
        """
        self.host = host
        self.device_id = device_id
        self.team_id = team_id or get_team_id()
        
        # Validate required parameters - fail fast if missing
        if not device_id:
            raise ValueError("Device ID is required")
        
        # Validate host configuration - fail fast if missing
        if not self.host or not self.host.get('host_name'):
            raise ValueError("Host configuration with host_name is required")
        self.host_name = self.host['host_name']
        
        # Extract device_model from host configuration
        from shared.lib.utils.build_url_utils import get_device_by_id
        device_dict = get_device_by_id(host, device_id)
        if not device_dict:
            raise ValueError(f"Device {device_id} not found in host")
        
        self.device_model = device_dict.get('device_model')
        if not self.device_model:
            raise ValueError(f"Device {device_id} has no device_model")
        
        # Get AV controller during initialization
        from shared.lib.utils.host_utils import get_controller
        self.av_controller = get_controller(self.device_id, 'av')
        if not self.av_controller:
            print(f"[@navigation_executor] Warning: No AV controller found for device {self.device_id}")
        
        print(f"[@navigation_executor] Initialized with host: {self.host_name}, device_id: {self.device_id}, device_model: {self.device_model}, team_id: {self.team_id}, av_controller: {self.av_controller is not None}")
    
    def get_available_context(self, userinterface_name: str = None) -> Dict[str, Any]:
        """
        Get available navigation context for AI based on user interface
        
        Args:
            userinterface_name: User interface name for context
            
        Returns:
            Dict with available navigation nodes and tree information
        """
        from shared.lib.utils.navigation_cache import get_cached_graph, populate_cache
        from shared.lib.utils.navigation_utils import load_navigation_tree_with_hierarchy
        
        if not userinterface_name:
            return {
                'service_type': 'navigation',
                'device_id': self.device_id,
                'device_model': self.device_model,
                'userinterface_name': userinterface_name,
                'tree_id': None,
                'available_nodes': []
            }
        
        tree_id = self._get_tree_id_for_interface(userinterface_name)
        if not tree_id:
            return {
                'service_type': 'navigation',
                'device_id': self.device_id,
                'device_model': self.device_model,
                'userinterface_name': userinterface_name,
                'tree_id': None,
                'available_nodes': []
            }
        
        # Check cache first
        cached_graph = get_cached_graph(tree_id, self.team_id)
        if cached_graph:
            nodes = [data for _, data in cached_graph.nodes(data=True)]
            available_nodes = [node.get('node_name') for node in nodes if node.get('node_name')]
        else:
            # Load and cache
            tree_result = load_navigation_tree_with_hierarchy(userinterface_name, "navigation_executor")
            nodes = tree_result['root_tree']['nodes']
            edges = tree_result['root_tree']['edges']
            populate_cache(tree_id, self.team_id, nodes, edges)
            available_nodes = [node.get('node_name') for node in nodes if node.get('node_name')]
        
        return {
            'service_type': 'navigation',
            'device_id': self.device_id,
            'device_model': self.device_model,
            'userinterface_name': userinterface_name,
            'tree_id': tree_id,
            'available_nodes': available_nodes
        }
    
    def _get_tree_id_for_interface(self, userinterface_name: str) -> Optional[str]:
        """Get tree_id for interface"""
        from shared.lib.supabase.userinterface_db import get_userinterface_by_name
        from shared.lib.supabase.navigation_trees_db import get_root_tree_for_interface
        
        interface = get_userinterface_by_name(userinterface_name, self.team_id)
        if not interface:
            return None
        
        root_tree = get_root_tree_for_interface(interface['id'], self.team_id)
        return root_tree['id'] if root_tree else None
    
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
            
            # Initialize step screenshot tracking
            step_screenshots = []
            
            for i, transition in enumerate(transitions):
                step_num = i + 1
                from_node = transition.get('from_node_label', 'unknown')
                to_node = transition.get('to_node_label', 'unknown')
                
                print(f"[@navigation_executor] Step {step_num}: {from_node} → {to_node}")
                
                # ALWAYS capture step-start screenshot
                try:
                    if self.av_controller:
                        step_start_screenshot = self.av_controller.take_screenshot()
                    else:
                        step_start_screenshot = ""
                except Exception as e:
                    print(f"[@navigation_executor] Screenshot failed: {e}")
                    step_start_screenshot = ""
                
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
                    
                    # ALWAYS capture step-end screenshot
                    try:
                        if self.av_controller:
                            step_end_screenshot = self.av_controller.take_screenshot()
                        else:
                            step_end_screenshot = ""
                    except Exception as e:
                        print(f"[@navigation_executor] Screenshot failed: {e}")
                        step_end_screenshot = ""
                    
                    # Execute per-step verifications (NEW)
                    step_verifications = transition.get('verifications', [])
                    verification_result = self._execute_step_verifications(step_verifications, transition.get('to_node_id'), execution_tree_id)
                    
                    # Store step screenshots
                    step_screenshots.extend([
                        step_start_screenshot,
                        step_end_screenshot
                    ])
                    
                    # Check overall step success (actions + verifications)
                    step_success = result.get('success') and verification_result.get('success', True)
                    
                    if not step_success:
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
                            'failed_actions': result.get('failed_actions', []),
                            'failed_at_step': step_num,
                            'step_start_screenshot_path': step_start_screenshot,
                            'step_end_screenshot_path': step_end_screenshot,
                            'action_screenshots': result.get('action_screenshots', []),
                            'verification_results': verification_result.get('results', []),
                            'step_screenshots': step_screenshots
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
                'step_screenshots': step_screenshots,  # NEW: Include step screenshots
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
    
    def _execute_step_verifications(self, verifications: List[Dict[str, Any]], node_id: str, tree_id: str) -> Dict[str, Any]:
        """Execute verifications for a single step (not just target node)"""
        if not verifications:
            return {'success': True, 'results': []}
        
        verification_executor = VerificationExecutor(
            host=self.host,
            device_id=self.device_id,
            tree_id=tree_id,
            node_id=node_id,
            team_id=self.team_id
        )
        
        return verification_executor.execute_verifications(verifications)
    
    
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