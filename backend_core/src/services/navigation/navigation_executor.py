"""
Navigation Execution System

Clean, standardized navigation executor without legacy fallbacks.
"""

import time
from typing import Dict, List, Optional, Any

# Core imports
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
        """Initialize NavigationExecutor"""
        self.host = host
        self.device_id = device_id
        self.team_id = team_id or get_team_id()
        
        # Get device model
        from shared.lib.utils.build_url_utils import get_device_by_id
        device_dict = get_device_by_id(host, device_id)
        self.device_model = device_dict.get('device_model') if device_dict else None
    
    def get_available_context(self, userinterface_name: str) -> Dict[str, Any]:
        """Get available navigation context - userinterface_name required"""
        from shared.lib.utils.navigation_utils import load_navigation_tree
        tree_result = load_navigation_tree(userinterface_name, "navigation_executor")
        
        # Fail fast - no fallback
        if not tree_result['success']:
            raise ValueError(f"Failed to load navigation tree: {tree_result['error']}")
        
        tree_id = tree_result['tree_id']
        nodes = tree_result['nodes']
        available_nodes = [node.get('node_name') for node in nodes if node.get('node_name')]
        
        return {
            'service_type': 'navigation',
            'device_id': self.device_id,
            'device_model': self.device_model,
            'userinterface_name': userinterface_name,
            'tree_id': tree_id,
            'available_nodes': available_nodes
        }
    
    def _build_result(self, success: bool, message: str, tree_id: str, target_node_id: str, 
                     current_node_id: Optional[str], start_time: float, **kwargs) -> Dict[str, Any]:
        """Build standardized result dictionary"""
        result = {
            'success': success,
            'tree_id': tree_id,
            'target_node_id': target_node_id,
            'current_node_id': current_node_id,
            'execution_time': time.time() - start_time,
            'transitions_executed': 0,
            'total_transitions': 0,
            'actions_executed': 0,
            'total_actions': 0
        }
        
        if success:
            result['message'] = message
        else:
            result['error'] = message
            
        result.update(kwargs)
        return result
    
    
    def execute_navigation(self, 
                          tree_id: str, 
                          target_node_id: str, 
                          current_node_id: Optional[str] = None,
                          image_source_url: Optional[str] = None) -> Dict[str, Any]:
        """Execute navigation to target node"""
        start_time = time.time()
        
        # Get preview first (includes pathfinding)
        preview = self.get_navigation_preview(tree_id, target_node_id, current_node_id)
        if not preview['success']:
            return self._build_result(False, preview['error'], tree_id, target_node_id, current_node_id, start_time)
        
        # Execute using preview data
        transitions = preview['transitions']
        
        try:
            # Execute transitions
            transitions_executed = 0
            actions_executed = 0
            total_actions = preview['total_actions']
            success = True
            error_message = ""
            
            for i, transition in enumerate(transitions):
                actions = transition.get('actions', [])
                if not actions:
                    transitions_executed += 1
                    continue
                
                # Execute actions
                action_executor = ActionExecutor(
                    host=self.host,
                    device_id=self.device_id,
                    tree_id=tree_id,
                    edge_id=transition.get('edge_id'),
                    team_id=self.team_id
                )
                
                result = action_executor.execute_actions(
                    actions=actions,
                    retry_actions=transition.get('retryActions', [])
                )
                
                if not result.get('success'):
                    success = False
                    error_message = f'Action failed: {result.get("error", "Unknown error")}'
                    break
                
                actions_executed += result.get('passed_count', 0)
                transitions_executed += 1
            
            # Execute target verifications if actions succeeded
            if success and transitions:
                target_verifications = transitions[-1].get('target_verifications', [])
                if target_verifications:
                    verification_executor = VerificationExecutor(
                        host=self.host,
                        device_id=self.device_id,
                        tree_id=tree_id,
                        node_id=target_node_id,
                        team_id=self.team_id
                    )
                    
                    result = verification_executor.execute_verifications(
                        verifications=target_verifications,
                        image_source_url=image_source_url
                    )
                    
                    if not result.get('success'):
                        success = False
                        error_message = f'Verification failed: {result.get("error", "Unknown error")}'
            
            # Build result once
            message = f'Navigation to {target_node_id} completed' if success else error_message
            extra_kwargs = {'final_position_node_id': target_node_id} if success else {}
            
            return self._build_result(
                success, message, tree_id, target_node_id, current_node_id, start_time,
                transitions_executed=transitions_executed,
                total_transitions=preview['total_transitions'],
                actions_executed=actions_executed,
                total_actions=total_actions,
                **extra_kwargs
            )
            
        except Exception as e:
            return self._build_result(
                False,
                f'Navigation error: {str(e)}',
                tree_id, target_node_id, current_node_id, start_time
            )
    
    def get_navigation_preview(self, tree_id: str, target_node_id: str, 
                             current_node_id: Optional[str] = None) -> Dict[str, Any]:
        """Get navigation preview without executing"""
        transitions = find_shortest_path(tree_id, target_node_id, self.team_id, current_node_id)
        
        success = bool(transitions)
        error_message = 'No navigation path found' if not success else ''
        
        return {
            'success': success,
            'error': error_message if not success else None,
            'tree_id': tree_id,
            'target_node_id': target_node_id,
            'current_node_id': current_node_id,
            'transitions': transitions or [],
            'total_transitions': len(transitions) if transitions else 0,
            'total_actions': sum(len(t.get('actions', [])) for t in transitions) if transitions else 0
        }
    
    