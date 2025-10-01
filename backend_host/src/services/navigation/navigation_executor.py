"""
Navigation Execution System

Unified navigation executor with complete tree management, pathfinding, and execution capabilities.
Consolidates all navigation functionality without external dependencies.
"""

import os
import time
from typing import Dict, List, Optional, Any, Tuple

# Core imports
from  backend_host.src.services.navigation.navigation_pathfinding import find_shortest_path
from  backend_host.src.lib.utils.navigation_exceptions import NavigationTreeError, UnifiedCacheError, PathfindingError, DatabaseError
from  backend_host.src.lib.utils.navigation_cache import populate_unified_cache

# KPI measurement
from backend_host.src.services.kpi_executor import get_kpi_executor, KPIMeasurementRequest


class NavigationExecutor:
    """
    Standardized navigation executor that orchestrates action and verification execution
    to provide complete navigation functionality.
    
    CRITICAL: Do not create new instances directly! Use device.navigation_executor instead.
    Each device has a singleton NavigationExecutor that preserves current position and tree state.
    """
    
    @classmethod
    def get_for_device(cls, device):
        """
        Factory method to get the device's existing NavigationExecutor.
        
        RECOMMENDED: Use device.navigation_executor directly instead of this method.
        
        Args:
            device: Device instance
            
        Returns:
            The device's existing NavigationExecutor instance
            
        Raises:
            ValueError: If device doesn't have a navigation_executor
        """
        if not hasattr(device, 'navigation_executor') or not device.navigation_executor:
            raise ValueError(f"Device {device.device_id} does not have a NavigationExecutor. "
                           "NavigationExecutors are created during device initialization.")
        return device.navigation_executor
    
    def __init__(self, device, _from_device_init: bool = False):
        """Initialize NavigationExecutor"""
        # Validate required parameters - fail fast if missing
        if not device:
            raise ValueError("Device instance is required")
        if not device.host_name:
            raise ValueError("Device must have host_name")
        if not device.device_id:
            raise ValueError("Device must have device_id")
        
        # Warn if creating instance outside of device initialization
        if not _from_device_init:
            import traceback
            print(f"⚠️ [NavigationExecutor] WARNING: Creating new NavigationExecutor instance for device {device.device_id}")
            print(f"⚠️ [NavigationExecutor] This may cause state loss! Use device.navigation_executor instead.")
            print(f"⚠️ [NavigationExecutor] Call stack:")
            for line in traceback.format_stack()[-3:-1]:  # Show last 2 stack frames
                print(f"⚠️ [NavigationExecutor]   {line.strip()}")
        
        # Store instances directly
        self.device = device
        self.host_name = device.host_name
        self.device_id = device.device_id
        self.device_model = device.device_model
        self.unified_graph = None
      
    def get_available_context(self, userinterface_name: str, team_id: str) -> Dict[str, Any]:
        """Get available navigation context using cache when possible"""
        # First check if we have a cached unified graph for this interface
        from shared.src.lib.supabase.userinterface_db import get_userinterface_by_name
        from shared.src.lib.supabase.navigation_trees_db import get_root_tree_for_interface
        from  backend_host.src.lib.utils.navigation_cache import get_cached_unified_graph
        
        # Get interface and root tree ID
        interface_info = get_userinterface_by_name(userinterface_name, team_id)
        if not interface_info:
            raise ValueError(f"Interface '{userinterface_name}' not found")
            
        root_tree_info = get_root_tree_for_interface(interface_info['id'], team_id)
        if not root_tree_info:
            raise ValueError(f"No root tree found for interface '{userinterface_name}'")
            
        tree_id = root_tree_info['id']
        
        # Check cache first - avoid reloading if already cached
        cached_graph = get_cached_unified_graph(tree_id, team_id)
        if cached_graph:
            print(f"[@navigation_executor] Using cached unified graph for '{userinterface_name}' (tree: {tree_id})")
            # Extract available nodes from cached graph - use labels, not node IDs
            available_nodes = []
            for node_id, node_data in cached_graph.nodes(data=True):
                if node_id != 'root':  # Skip root node
                    label = node_data.get('label', node_id)  # Use label if available, fallback to node_id
                    if label:  # Only add non-empty labels
                        available_nodes.append(label)
            
            print(f"[@navigation_executor] Extracted {len(available_nodes)} node labels: {available_nodes}")
            
            return {
                'service_type': 'navigation',
                'device_id': self.device_id,
                'device_model': self.device_model,
                'userinterface_name': userinterface_name,
                'tree_id': tree_id,
                'available_nodes': available_nodes,
                'cross_tree_capabilities': len(cached_graph.nodes()) > 10,  # Estimate based on graph size
                'unified_graph_nodes': len(cached_graph.nodes()),
                'unified_graph_edges': len(cached_graph.edges())
            }
        
        # Cache miss - load tree hierarchy and populate cache
        print(f"[@navigation_executor] Cache miss for '{userinterface_name}' - loading tree hierarchy")
        tree_result = self.load_navigation_tree(userinterface_name, team_id)
        
        # Fail fast - no fallback
        if not tree_result['success']:
            raise ValueError(f"Failed to load navigation tree: {tree_result['error']}")
        
        # Extract nodes directly from tree_result (load_navigation_tree returns 'nodes', not 'root_tree')
        nodes = tree_result['nodes']
        # Extract node labels (not node_name) for consistency with cached path
        available_nodes = []
        for node in nodes:
            label = node.get('label') or node.get('node_name')  # Try label first, fallback to node_name
            if label:
                available_nodes.append(label)
        
        print(f"[@navigation_executor] Extracted {len(available_nodes)} node labels from tree result: {available_nodes}")
        
        return {
            'service_type': 'navigation',
            'device_id': self.device_id,
            'device_model': self.device_model,
            'userinterface_name': userinterface_name,
            'tree_id': tree_id,
            'available_nodes': available_nodes,
            'cross_tree_capabilities': tree_result.get('cross_tree_capabilities', False),
            'unified_graph_nodes': tree_result.get('unified_graph_nodes', 0),
            'unified_graph_edges': tree_result.get('unified_graph_edges', 0)
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
                          target_node_id: str = None,
                          target_node_label: str = None,
                          current_node_id: Optional[str] = None,
                          image_source_url: Optional[str] = None,
                          team_id: str = None,
                          context=None) -> Dict[str, Any]:
        """
        Execute navigation to target node using ONLY unified pathfinding with nested tree support.
        Enhanced with all capabilities from old goto_node method.
        
        Args:
            tree_id: Navigation tree ID
            target_node_id: ID of the target node to navigate to (mutually exclusive with target_node_label)
            target_node_label: Label of the target node to navigate to (mutually exclusive with target_node_id)
            current_node_id: Optional current node ID for starting point
            image_source_url: Optional image source URL
            team_id: Team ID for security
            context: Optional ScriptExecutionContext for tracking step results
            
        Returns:
            Dict with success status and navigation details
        """
        start_time = time.time()
        
        # Validate parameters - exactly one of target_node_id or target_node_label must be provided
        if not target_node_id and not target_node_label:
            return self._build_result(
                False, 
                "Either target_node_id or target_node_label must be provided",
                tree_id, None, current_node_id, start_time
            )
        
        if target_node_id and target_node_label:
            return self._build_result(
                False, 
                "Cannot provide both target_node_id and target_node_label - use only one",
                tree_id, target_node_id, current_node_id, start_time
            )
        
        # Convert target_node_label to target_node_id if needed
        if target_node_label:
            try:
                target_node_id = self.get_node_id(target_node_label)
                print(f"[@navigation_executor:execute_navigation] Resolved label '{target_node_label}' to node_id '{target_node_id}'")
            except ValueError as e:
                return self._build_result(
                    False, 
                    f"Could not resolve target_node_label '{target_node_label}' to node_id: {str(e)}",
                    tree_id, None, current_node_id, start_time
                )
        
        # Update shared navigation context with team_id
        if team_id:
            self.device.navigation_context['team_id'] = team_id
        
        # Store previous position before navigation attempt
        nav_context = self.device.navigation_context
        nav_context['previous_node_id'] = nav_context['current_node_id']
        nav_context['previous_node_label'] = nav_context['current_node_label']
        
        # Get target node label for logging (if unified graph is available)
        target_node_label = None
        if self.unified_graph:
            try:
                target_node_label = self.get_node_label(target_node_id)
            except ValueError:
                print(f"[@navigation_executor:execute_navigation] Could not find label for node_id '{target_node_id}' - will use ID for logging")
                target_node_label = target_node_id
        
        try:
            from backend_host.src.services.navigation.navigation_pathfinding import find_shortest_path
            from backend_host.src.lib.utils.navigation_exceptions import UnifiedCacheError, PathfindingError
            
            # Handle current_node_id parameter - update navigation context if provided
            if current_node_id:
                # Update navigation context with provided starting position
                nav_context['current_node_id'] = current_node_id
                nav_context['current_node_label'] = self.get_node_label(current_node_id)
                print(f"[@navigation_executor:execute_navigation] Starting from provided location: {current_node_id} ({nav_context['current_node_label']})")
            elif nav_context.get('current_node_id'):
                current_label = nav_context.get('current_node_label', 'unknown')
                print(f"[@navigation_executor:execute_navigation] Starting from device current position: {nav_context['current_node_id']} ({current_label})")
            else:
                print(f"[@navigation_executor:execute_navigation] Starting from default entry point (no current location)")
            
            print(f"[@navigation_executor:execute_navigation] Navigating to '{target_node_label or target_node_id}' using unified pathfinding")
            
            # Check if already at target BEFORE pathfinding - but VERIFY first (context may be corrupted)
            if nav_context.get('current_node_id') == target_node_id:
                print(f"[@navigation_executor:execute_navigation] Context indicates already at target '{target_node_label or target_node_id}' - verifying...")
                
                # Verify we're actually at this node (context may be corrupted)
                verification_result = self.device.verification_executor.verify_node(target_node_id, team_id)
                
                if verification_result.get('success'):
                    print(f"[@navigation_executor:execute_navigation] ✅ Verified at target '{target_node_label or target_node_id}' - no navigation needed")
                    # Update position to ensure consistency
                    self.update_current_position(target_node_id, tree_id, target_node_label)
                    # Mark navigation as successful
                    nav_context['current_node_navigation_success'] = True
                    
                    return self._build_result(
                        True,
                        f"Already at target '{target_node_label or target_node_id}'",
                        tree_id, target_node_id, current_node_id, start_time,
                        transitions_executed=0,
                        total_transitions=0,
                        actions_executed=0,
                        total_actions=0,
                        path_length=0,
                        already_at_target=True,
                        unified_pathfinding_used=True,
                        navigation_path=[]
                    )
                else:
                    print(f"[@navigation_executor:execute_navigation] ⚠️ Verification failed - context corrupted, proceeding with navigation")
                    # Clear corrupted position and continue with normal navigation
                    nav_context['current_node_id'] = None
                    nav_context['current_node_label'] = None
            
            # Use unified pathfinding with current navigation context position
            navigation_path = find_shortest_path(tree_id, target_node_id, team_id, nav_context.get('current_node_id'))
            
            if not navigation_path:
                # Empty path but not at target - this is an error
                nav_context['current_node_navigation_success'] = False
                return self._build_result(
                    False, 
                    f"No unified path found to '{target_node_label or target_node_id}'",
                    tree_id, target_node_id, current_node_id, start_time,
                    unified_pathfinding_used=True
                )
            
            print(f"[@navigation_executor:execute_navigation] Found path with {len(navigation_path)} steps")
            
            # Execute navigation sequence with early stopping for navigation functions
            transitions_executed = 0
            actions_executed = 0
            total_actions = sum(len(step.get('actions', [])) for step in navigation_path)
            
            for i, step in enumerate(navigation_path):
                step_num = i + 1
                from_node = step.get('from_node_label', 'unknown')
                to_node = step.get('to_node_label', 'unknown')
                
                print(f"[@navigation_executor:execute_navigation] Step {step_num}/{len(navigation_path)}: {from_node} → {to_node}")
                
                # Step start screenshot - capture BEFORE action execution (like old goto_node)
                step_start_screenshot_path = ""
                if context:
                    from backend_host.src.lib.utils.report_utils import capture_and_upload_screenshot
                    step_name = f"step_{step_num}_{from_node}_{to_node}"
                    step_start_screenshot_result = capture_and_upload_screenshot(self.device, f"{step_name}_start", "navigation")
                    step_start_screenshot_path = step_start_screenshot_result.get('screenshot_path', '')
                    
                    if step_start_screenshot_path:
                        print(f"📸 [@navigation_executor:execute_navigation] Step-start screenshot captured: {step_start_screenshot_path}")
                        context.add_screenshot(step_start_screenshot_path)
                
                step_start_time = time.time()
                
                # Execute actions using device's existing executor
                actions = step.get('actions', [])
                retry_actions = step.get('retryActions', [])
                failure_actions = step.get('failureActions', [])
                
                # Consolidated action count logging
                total_step_actions = len(actions) + len(retry_actions) + len(failure_actions)
                if total_step_actions > 0:
                    action_summary = f"{len(actions)}"
                    if len(retry_actions) > 0:
                        action_summary += f"+{len(retry_actions)}r"
                    if len(failure_actions) > 0:
                        action_summary += f"+{len(failure_actions)}f"
                    print(f"[@navigation_executor:execute_navigation] Step {step_num}: {action_summary} actions")
                
                if actions:
                    # Update context for this navigation step
                    self.device.action_executor.tree_id = tree_id
                    self.device.action_executor.edge_id = step.get('edge_id')
                    self.device.action_executor.action_set_id = step.get('action_set_id')
                    # Script context is automatically available in device navigation_context
                    # ActionExecutor will read it directly from there - no need to pass it
                    
                    result = self.device.action_executor.execute_actions(
                        actions=actions,
                        retry_actions=retry_actions,
                        failure_actions=failure_actions,
                        team_id=team_id,
                        context=context
                    )
                    
                    actions_executed += result.get('passed_count', 0)
                else:
                    # No actions to execute, just mark as successful
                    result = {'success': True}
                
                step_execution_time = int((time.time() - step_start_time) * 1000)
                
                # Note: ActionExecutor now handles screenshots during action execution
                # No need for redundant main action screenshot here
                
                # Step end screenshot - capture AFTER action execution (like old goto_node)
                step_end_screenshot_path = ""
                if context:
                    step_end_screenshot_result = capture_and_upload_screenshot(self.device, f"{step_name}_end", "navigation")
                    step_end_screenshot_path = step_end_screenshot_result.get('screenshot_path', '')
                    
                    if step_end_screenshot_path:
                        print(f"📸 [@navigation_executor:execute_navigation] Step-end screenshot captured: {step_end_screenshot_path}")
                        context.add_screenshot(step_end_screenshot_path)
                
                # If context is provided, record the step result (like old goto_node)
                if context:
                    from datetime import datetime
                    step_start_timestamp = datetime.fromtimestamp(step_start_time).strftime('%H:%M:%S')
                    step_end_timestamp = datetime.now().strftime('%H:%M:%S')
                    
                    # Extract action name for labeling (like old goto_node)
                    action_name = "navigation_step"  # Default fallback
                    step_actions = step.get('actions', [])
                    if step_actions and len(step_actions) > 0:
                        first_action = step_actions[0]
                        if isinstance(first_action, dict) and first_action.get('command'):
                            action_name = first_action.get('command')
                    
                    step_result = {
                        'success': result.get('success', False),
                        'screenshot_path': step_end_screenshot_path,  # Use step end screenshot since ActionExecutor handles action screenshots
                        'screenshot_url': result.get('screenshot_url'),
                        'step_start_screenshot_path': step_start_screenshot_path,
                        'step_end_screenshot_path': step_end_screenshot_path,
                        'message': f"Navigation step: {from_node} → {to_node}",  # Will be updated with step number
                        'execution_time_ms': step_execution_time,
                        'start_time': step_start_timestamp,
                        'end_time': step_end_timestamp,
                        'from_node': from_node,
                        'to_node': to_node,
                        'action_name': action_name,  # Store action name like old goto_node
                        'actions': step.get('actions', []),
                        'retry_actions': step.get('retryActions', []),  # Include retry actions
                        'failure_actions': step.get('failureActions', []),  # Include failure actions
                        'action_results': result.get('results', []),  # Individual action results with categories and screenshots
                        'action_screenshots': result.get('action_screenshots', []),  # All action screenshots
                        'verifications': step.get('verifications', []),
                        'verification_results': result.get('verification_results', []),
                        'error': result.get('error'),  # Store actual error message from action execution
                        'step_category': 'navigation'
                    }
                    
                    # Record step immediately - step number shown in table
                    context.record_step_immediately(step_result)
                    # Simple message without redundant step number
                    step_result['message'] = f"{from_node} → {to_node}"
                
                # Queue KPI measurement if step succeeded and target node has kpi_references
                if result.get('success', False):
                    # Get actual action completion timestamp from navigation context
                    # (ActionExecutor updates this after all iterations and waits complete)
                    nav_context = self.device.navigation_context
                    action_completion_timestamp = nav_context.get('last_action_timestamp', step_start_time)
                    
                    self._queue_kpi_measurement_if_configured(
                        step=step,
                        action_timestamp=action_completion_timestamp,
                        team_id=team_id
                    )
                
                if not result.get('success', False):
                    error_msg = result.get('error', 'Unknown error')
                    error_details = result.get('error_details', {})
                    
                    print(f"[@navigation_executor:execute_navigation] NAVIGATION STEP FAILED:")
                    print(f"[@navigation_executor:execute_navigation]   Step {step_num}/{len(navigation_path)}: {from_node} → {to_node}")
                    print(f"[@navigation_executor:execute_navigation]   Error: {error_msg}")
                    print(f"[@navigation_executor:execute_navigation]   Execution time: {step_execution_time}ms")
                    
                    # Log additional error details if available
                    if error_details:
                        if error_details.get('edge_id'):
                            print(f"[@navigation_executor:execute_navigation]   Edge ID: {error_details.get('edge_id')}")
                        if error_details.get('actions_count'):
                            print(f"[@navigation_executor:execute_navigation]   Actions attempted: {error_details.get('actions_count')}")
                        if error_details.get('retry_actions_count'):
                            print(f"[@navigation_executor:execute_navigation]   Retry actions attempted: {error_details.get('retry_actions_count')}")
                        if error_details.get('failure_actions_count'):
                            print(f"[@navigation_executor:execute_navigation]   Failure actions attempted: {error_details.get('failure_actions_count')}")
                        
                        # Log specific actions that failed
                        failed_actions = error_details.get('actions', [])
                        if failed_actions:
                            print(f"[@navigation_executor:execute_navigation]   Failed actions:")
                            for j, action in enumerate(failed_actions):
                                cmd = action.get('command', 'unknown')
                                params = action.get('params', {})
                                print(f"[@navigation_executor:execute_navigation]     {j+1}. {cmd}: {params}")
                    
                    # NAVIGATION FUNCTIONS: Stop immediately on ANY step failure (no recovery attempts)
                    print(f"🛑 [@navigation_executor:execute_navigation] STOPPING navigation - navigation functions do not recover from failures")
                    
                    # Mark navigation as failed
                    nav_context['current_node_navigation_success'] = False
                    
                    detailed_error_msg = f"Navigation failed at step {step_num} ({from_node} → {to_node}): {error_msg}"
                    return self._build_result(
                        False, 
                        detailed_error_msg,
                        tree_id, target_node_id, current_node_id, start_time,
                        transitions_executed=transitions_executed,
                        total_transitions=len(navigation_path),
                        actions_executed=actions_executed,
                        total_actions=total_actions,
                        error_details={
                            'step_number': step_num,
                            'total_steps': len(navigation_path),
                            'from_node': from_node,
                            'to_node': to_node,
                            'execution_time_ms': step_execution_time,
                            'original_error': error_msg,
                            'action_details': error_details
                        }
                    )
                
                transitions_executed += 1
            
            # Get final destination for consolidated success message
            final_step = navigation_path[-1] if navigation_path else {}
            final_node_id = final_step.get('to_node_id')
            
            # Update current location in context after successful navigation
            if context and hasattr(context, 'current_node_id') and final_node_id:
                context.current_node_id = final_node_id
            
            # Consolidated success message with timing and final position
            total_time = int((time.time() - start_time) * 1000)
            print(f"[@navigation_executor] Navigation to '{target_node_label or target_node_id}' completed successfully in {total_time}ms → {final_node_id}")
            
            # Update position if navigation succeeded
            if navigation_path:
                self.update_current_position(final_node_id, tree_id, target_node_label)
            
            # Mark navigation as successful
            nav_context['current_node_navigation_success'] = True
            
            # Count cross-tree transitions
            cross_tree_transitions = len([step for step in navigation_path if step.get('tree_context_change')])
            
            return self._build_result(
                True,
                f"Successfully navigated to '{target_node_label or target_node_id}' in {len(navigation_path)} steps",
                tree_id, target_node_id, current_node_id, start_time,
                transitions_executed=transitions_executed,
                total_transitions=len(navigation_path),
                actions_executed=actions_executed,
                total_actions=total_actions,
                path_length=len(navigation_path),
                cross_tree_transitions=cross_tree_transitions,
                unified_pathfinding_used=True,
                navigation_path=navigation_path  # Include full transition data for AI/frontend
            )
            
        except (UnifiedCacheError, PathfindingError) as e:
            print(f"❌ [@navigation_executor:execute_navigation] Unified navigation failed: {str(e)}")
            # Mark navigation as failed
            self.device.navigation_context['current_node_navigation_success'] = False
            return self._build_result(
                False,
                str(e),
                tree_id, target_node_id, current_node_id, start_time,
                unified_pathfinding_required=True
            )
        except Exception as e:
            error_msg = f"Unexpected navigation error to '{target_node_label or target_node_id}': {str(e)}"
            print(f"❌ [@navigation_executor:execute_navigation] ERROR: {error_msg}")
            # Mark navigation as failed
            self.device.navigation_context['current_node_navigation_success'] = False
            return self._build_result(
                False,
                error_msg,
                tree_id, target_node_id, current_node_id, start_time,
                unified_pathfinding_used=True
            )
    
    def get_navigation_preview(self, tree_id: str, target_node_id: str, 
                             current_node_id: Optional[str] = None, team_id: str = None) -> Dict[str, Any]:
        """Get navigation preview without executing - expects unified cache to be pre-populated"""
        
        try:
            # Get navigation path using unified cache (should be pre-populated by tree loading)
            transitions = find_shortest_path(tree_id, target_node_id, team_id, current_node_id)
            
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
            
        except UnifiedCacheError as e:
            # Cache missing - this indicates the tree wasn't loaded properly
            print(f"[@navigation_executor:get_navigation_preview] Unified cache missing for tree {tree_id}")
            print(f"[@navigation_executor:get_navigation_preview] This indicates the NavigationEditor didn't load the tree properly")
            return {
                'success': False,
                'error': f'Navigation tree {tree_id} not loaded. Please reload the NavigationEditor to populate the navigation cache.',
                'tree_id': tree_id,
                'target_node_id': target_node_id,
                'current_node_id': current_node_id,
                'transitions': [],
                'total_transitions': 0,
                'total_actions': 0,
                'cache_missing': True
            }
        
        except Exception as e:
            print(f"[@navigation_executor:get_navigation_preview] Unexpected error: {str(e)}")
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
    
    # ========================================
    # NAVIGATION TREE MANAGEMENT METHODS
    # ========================================
    
    def load_navigation_tree(self, userinterface_name: str, team_id: str) -> Dict[str, Any]:
        """
        Load navigation tree and populate unified cache.
        This is the unified function that always works for both simple and nested trees.
        
        Args:
            userinterface_name: Interface name (e.g., 'horizon_android_mobile')
            team_id: Team ID (required)
            
        Returns:
            Dictionary with success status and tree data
            
        Raises:
            NavigationTreeError: If any part of the loading fails
        """
        try:
            print(f"🗺️ [NavigationExecutor] Loading navigation tree for '{userinterface_name}'")
            
            # 1. Load root tree data
            from shared.src.lib.supabase.userinterface_db import get_userinterface_by_name
            userinterface = get_userinterface_by_name(userinterface_name, team_id)
            if not userinterface:
                return {'success': False, 'error': f"User interface '{userinterface_name}' not found"}
            
            userinterface_id = userinterface['id']
            
            # Use the same approach as NavigationEditor - call the working API endpoint
            from shared.src.lib.supabase.navigation_trees_db import get_root_tree_for_interface, get_full_tree
            
            # Get the root tree for this user interface (same as navigation page)
            tree = get_root_tree_for_interface(userinterface_id, team_id)
            
            if not tree:
                return {'success': False, 'error': f"No root tree found for interface: {userinterface_id}"}
            
            # Get full tree data with nodes and edges (same as navigation page)
            tree_data = get_full_tree(tree['id'], team_id)
            
            if not tree_data['success']:
                return {'success': False, 'error': f"Failed to load tree data: {tree_data.get('error', 'Unknown error')}"}
            
            root_tree_id = tree['id']
            nodes = tree_data['nodes']
            edges = tree_data['edges']
            
            # Create root tree result for hierarchy processing
            root_tree_result = {
                'success': True,
                'tree': {
                    'id': root_tree_id,
                    'name': tree.get('name', ''),
                    'metadata': {
                        'nodes': nodes,
                        'edges': edges
                    }
                },
                'tree_id': root_tree_id,
                'userinterface_id': userinterface_id,
                'nodes': nodes,
                'edges': edges
            }
            
            print(f"✅ [NavigationExecutor] Root tree loaded: {root_tree_id}")
            
            # 2. Discover complete tree hierarchy
            hierarchy_data = self.discover_complete_hierarchy(root_tree_id, team_id)
            if not hierarchy_data:
                # If no nested trees, create single-tree hierarchy
                hierarchy_data = [self.format_tree_for_hierarchy(root_tree_result, is_root=True)]
                print(f"📋 [NavigationExecutor] No nested trees found, using single root tree")
            else:
                print(f"📋 [NavigationExecutor] Found {len(hierarchy_data)} trees in hierarchy")
            
            # 3. Build unified tree data structure
            all_trees_data = self.build_unified_tree_data(hierarchy_data)
            if not all_trees_data:
                raise NavigationTreeError("Failed to build unified tree data structure")
            
            # 4. Populate unified cache (MANDATORY)
            print(f"🔄 [NavigationExecutor] Populating unified cache...")
            from backend_host.src.lib.utils.navigation_cache import populate_unified_cache
            unified_graph = populate_unified_cache(root_tree_id, team_id, all_trees_data)
            if not unified_graph:
                from backend_host.src.lib.utils.navigation_cache import UnifiedCacheError
                raise UnifiedCacheError("Failed to populate unified cache - navigation will not work")
            
            print(f"✅ [NavigationExecutor] Unified cache populated: {len(unified_graph.nodes)} nodes, {len(unified_graph.edges)} edges")
            
            # Store unified graph for direct access
            self.unified_graph = unified_graph
            
            # 5. Return result compatible with script executor expectations
            return {
                'success': True,
                'tree_id': root_tree_id,
                'tree': {
                    'id': root_tree_id,
                    'name': tree.get('name', ''),
                    'metadata': {
                        'nodes': nodes,
                        'edges': edges
                    }
                },
                'userinterface_id': userinterface_id,
                'nodes': nodes,
                'edges': edges,
                # Additional hierarchy info for advanced use cases
                'hierarchy': hierarchy_data,
                'unified_graph_nodes': len(unified_graph.nodes),
                'unified_graph_edges': len(unified_graph.edges),
                'cross_tree_capabilities': len(hierarchy_data) > 1
            }
            
        except Exception as e:
            # Import exceptions locally to avoid circular imports
            from backend_host.src.lib.utils.navigation_cache import NavigationTreeError, UnifiedCacheError
            if isinstance(e, (NavigationTreeError, UnifiedCacheError)):
                # Re-raise navigation-specific errors
                raise e
            else:
                # FAIL EARLY - no fallback
                return {'success': False, 'error': f"Navigation tree loading failed: {str(e)}"}

    def discover_complete_hierarchy(self, root_tree_id: str, team_id: str) -> List[Dict]:
        """
        Discover all nested trees in hierarchy using enhanced database functions.
        
        Args:
            root_tree_id: Root tree ID
            team_id: Team ID
            
        Returns:
            List of tree data dictionaries for the complete hierarchy
        """
        try:
            from shared.src.lib.supabase.navigation_trees_db import get_complete_tree_hierarchy
            
            print(f"🔍 [NavigationExecutor] Discovering complete tree hierarchy using enhanced database function...")
            
            # Use the new enhanced database function
            hierarchy_result = get_complete_tree_hierarchy(root_tree_id, team_id)
            if not hierarchy_result['success']:
                print(f"⚠️ [NavigationExecutor] Failed to get complete hierarchy: {hierarchy_result.get('error', 'Unknown error')}")
                return []
            
            hierarchy_data = hierarchy_result['hierarchy']
            if not hierarchy_data:
                print(f"📋 [NavigationExecutor] Empty hierarchy returned from database")
                return []
            
            total_trees = hierarchy_result.get('total_trees', len(hierarchy_data))
            max_depth = hierarchy_result.get('max_depth', 0)
            has_nested = hierarchy_result.get('has_nested_trees', False)
            
            print(f"✅ [NavigationExecutor] Complete hierarchy discovered:")
            print(f"   • Total trees: {total_trees}")
            print(f"   • Maximum depth: {max_depth}")
            print(f"   • Has nested trees: {has_nested}")
            
            # The data is already in the correct format from the database function
            return hierarchy_data
            
        except Exception as e:
            print(f"❌ [NavigationExecutor] Error discovering hierarchy: {str(e)}")
            return []

    def format_tree_for_hierarchy(self, tree_data: Dict, tree_info: Dict = None, is_root: bool = False) -> Dict:
        """
        Format tree data for unified hierarchy structure.
        
        Args:
            tree_data: Tree data from database
            tree_info: Optional hierarchy metadata
            is_root: Whether this is the root tree
            
        Returns:
            Formatted tree data for unified processing
        """
        if is_root:
            # Root tree from load_navigation_tree
            return {
                'tree_id': tree_data['tree_id'],
                'tree_info': {
                    'name': tree_data['tree']['name'],
                    'is_root_tree': True,
                    'tree_depth': 0,
                    'parent_tree_id': None,
                    'parent_node_id': None
                },
                'nodes': tree_data['nodes'],
                'edges': tree_data['edges']
            }
        else:
            # Nested tree from hierarchy
            return {
                'tree_id': tree_info['tree_id'],
                'tree_info': {
                    'name': tree_info.get('tree_name', ''),
                    'is_root_tree': tree_info.get('depth', 0) == 0,
                    'tree_depth': tree_info.get('depth', 0),
                    'parent_tree_id': tree_info.get('parent_tree_id'),
                    'parent_node_id': tree_info.get('parent_node_id')
                },
                'nodes': tree_data['nodes'],
                'edges': tree_data['edges']
            }

    def build_unified_tree_data(self, hierarchy_data: List[Dict]) -> List[Dict]:
        """
        Build unified data structure for cache population.
        
        Args:
            hierarchy_data: List of formatted tree data
            
        Returns:
            Data structure ready for create_unified_networkx_graph()
        """
        try:
            if not hierarchy_data:
                print(f"⚠️ [NavigationExecutor] No hierarchy data to build unified structure")
                return []
            
            print(f"🔧 [NavigationExecutor] Building unified data structure from {len(hierarchy_data)} trees")
            
            # The hierarchy_data is already in the correct format for create_unified_networkx_graph
            # Just validate and return
            for tree_data in hierarchy_data:
                required_keys = ['tree_id', 'tree_info', 'nodes', 'edges']
                for key in required_keys:
                    if key not in tree_data:
                        raise NavigationTreeError(f"Missing required key '{key}' in tree data")
            
            print(f"✅ [NavigationExecutor] Unified data structure validated")
            return hierarchy_data
            
        except Exception as e:
            print(f"❌ [NavigationExecutor] Error building unified data: {str(e)}")
            return []


    # ========================================
    # NODE AND EDGE FINDING METHODS
    # ========================================

    def find_node_by_label(self, nodes: List[Dict], label: str) -> Dict:
        """
        Find node by its label in a generic way.
        
        Args:
            nodes: List of node dictionaries
            label: Node label to search for
            
        Returns:
            Node dictionary with the matching label, or None if not found
        """
        for node in nodes:
            if node.get('label') == label:
                return node
        return None

    def find_edges_from_node(self, source_node_id: str, edges: List[Dict]) -> List[Dict]:
        """
        Find all edges originating from a specific node (generic version).
        
        Args:
            source_node_id: Source node ID
            edges: List of edge dictionaries
            
        Returns:
            List of edges originating from the specified node
        """
        return [edge for edge in edges if edge.get('source_node_id') == source_node_id]

    def find_edge_by_target_label(self, source_node_id: str, edges: List[Dict], nodes: List[Dict], target_label: str) -> Dict:
        """
        Find edge from source node to a target node with specific label.
        This is the proper generic way to find action edges.
        
        Args:
            source_node_id: Source node ID
            edges: List of edge dictionaries
            nodes: List of node dictionaries  
            target_label: Label of target node to find
            
        Returns:
            Edge dictionary going to target node with specified label, or None if not found
        """
        # First find the target node by label
        target_node = self.find_node_by_label(nodes, target_label)
        if not target_node:
            return None
        
        target_node_id = target_node.get('node_id')
        if not target_node_id:
            return None
        
        # Find edge from source to target
        source_edges = self.find_edges_from_node(source_node_id, edges)
        for edge in source_edges:
            if edge.get('target_node_id') == target_node_id:
                return edge
        
        return None

    def find_edge_with_action_command(self, node_id: str, edges: List[Dict], action_command: str) -> Dict:
        """
        Find edge from node_id that contains the specified action command in its action sets.
        
        Args:
            node_id: Source node ID
            edges: List of edge dictionaries 
            action_command: Action command to search for (e.g., 'tap_coordinates', 'press_key')
            
        Returns:
            Edge dictionary containing the action, or None if not found
        """
        source_edges = self.find_edges_from_node(node_id, edges)
        
        for edge in source_edges:
            action_sets = edge.get('action_sets', [])
            for action_set in action_sets:
                actions = action_set.get('actions', [])
                for action in actions:
                    if action.get('command') == action_command:
                        return edge
        
        return None

    def get_node_sub_trees_with_actions(self, node_id: str, tree_id: str, team_id: str) -> Dict:
        """Get all sub-trees for a node and return their nodes and edges for action checking."""
        from shared.src.lib.supabase.navigation_trees_db import get_node_sub_trees, get_full_tree
        
        # Get sub-trees for this node
        sub_trees_result = get_node_sub_trees(tree_id, node_id, team_id)
        if not sub_trees_result.get('success'):
            return {'success': False, 'error': sub_trees_result.get('error'), 'sub_trees': [], 'all_nodes': [], 'all_edges': []}
        
        sub_trees = sub_trees_result.get('sub_trees', [])
        all_nodes = []
        all_edges = []
        
        # Load nodes and edges from all sub-trees
        for sub_tree in sub_trees:
            sub_tree_id = sub_tree.get('id')
            if sub_tree_id:
                tree_data = get_full_tree(sub_tree_id, team_id)
                if tree_data.get('success'):
                    all_nodes.extend(tree_data.get('nodes', []))
                    all_edges.extend(tree_data.get('edges', []))
        
        return {
            'success': True,
            'sub_trees': sub_trees,
            'all_nodes': all_nodes,
            'all_edges': all_edges
        }

    def find_action_in_nested_trees(self, source_node_id: str, tree_id: str, nodes: List[Dict], edges: List[Dict], action_command: str, team_id: str) -> Dict:
        """Find action in main tree and sub-trees of the specific source node only."""
        
        # First check in the main tree
        action_edge = self.find_edge_by_target_label(source_node_id, edges, nodes, action_command)
        if action_edge:
            return {'success': True, 'edge': action_edge, 'tree_type': 'main', 'tree_id': tree_id}
        
        action_edge = self.find_edge_with_action_command(source_node_id, edges, action_command)
        if action_edge:
            return {'success': True, 'edge': action_edge, 'tree_type': 'main', 'tree_id': tree_id}
        
        # Check sub-trees for this specific node only
        print(f"🔍 [navigation_executor] Checking sub-trees for node: {source_node_id}")
        sub_trees_data = self.get_node_sub_trees_with_actions(source_node_id, tree_id, team_id)
        
        if not sub_trees_data.get('success') or not sub_trees_data.get('sub_trees'):
            print(f"🔍 [navigation_executor] Node {source_node_id} has no sub-trees")
            return {'success': False, 'error': f"Action '{action_command}' not found in main tree and node has no sub-trees"}
        
        sub_nodes = sub_trees_data.get('all_nodes', [])
        sub_edges = sub_trees_data.get('all_edges', [])
        sub_trees = sub_trees_data.get('sub_trees', [])
        
        print(f"🔍 [navigation_executor] Found {len(sub_trees)} sub-trees with {len(sub_nodes)} nodes and {len(sub_edges)} edges")
        
        # Simple search: try to find action in any sub-tree node
        for node in sub_nodes:
            node_id = node.get('node_id')
            if node_id:
                # Check by target label
                sub_action_edge = self.find_edge_by_target_label(node_id, sub_edges, sub_nodes, action_command)
                if sub_action_edge:
                    return {'success': True, 'edge': sub_action_edge, 'tree_type': 'sub', 'tree_id': sub_trees[0].get('id'), 'source_node_id': node_id}
                
                # Check by action command
                sub_action_edge = self.find_edge_with_action_command(node_id, sub_edges, action_command)
                if sub_action_edge:
                    return {'success': True, 'edge': sub_action_edge, 'tree_type': 'sub', 'tree_id': sub_trees[0].get('id'), 'source_node_id': node_id}
        
        return {'success': False, 'error': f"Action '{action_command}' not found in main tree or sub-trees"}

    # ========================================
    # KPI MEASUREMENT METHODS
    # ========================================
    
    def _queue_kpi_measurement_if_configured(
        self,
        step: Dict[str, Any],
        action_timestamp: float,
        team_id: str
    ):
        """
        Queue KPI measurement if target node has kpi_references configured.
        Fail early if any required data missing.
        """
        try:
            target_node_id = step.get('to_node_id')
            if not target_node_id:
                return
            
            # Get target node's KPI references
            from shared.src.lib.supabase.navigation_trees_db import get_node_by_id
            node_result = get_node_by_id(step.get('tree_id', ''), target_node_id, team_id)
            
            if not node_result.get('success'):
                return
            
            node_data = node_result['node']
            kpi_references = node_data.get('kpi_references', [])
            
            if not kpi_references:
                return
            
            # Get capture directory from device (MANDATORY)
            capture_dir = self._get_device_capture_dir()
            if not capture_dir:
                print(f"⚠️ [NavigationExecutor] No capture_dir for device {self.device_id} - KPI skipped")
                return
            
            # Get timeout from KPI references (use maximum timeout)
            timeout_ms = max([ref.get('timeout', 5000) for ref in kpi_references])
            
            # Record edge execution to get execution_result_id
            from shared.src.lib.supabase.execution_results_db import record_edge_execution
            execution_result_id = record_edge_execution(
                team_id=team_id,
                tree_id=step.get('tree_id', ''),
                edge_id=step.get('edge_id', ''),
                host_name=self.host_name,
                device_model=self.device_model,
                success=True,
                execution_time_ms=0,  # Will be updated by KPI measurement
                message="KPI measurement queued",
                action_set_id=step.get('action_set_id')
            )
            
            if not execution_result_id:
                print(f"❌ [NavigationExecutor] Failed to create execution_result - KPI skipped")
                return
            
            # Create KPI measurement request - will fail early if validation fails
            request = KPIMeasurementRequest(
                execution_result_id=execution_result_id,
                team_id=team_id,
                capture_dir=capture_dir,
                action_timestamp=action_timestamp,
                kpi_references=kpi_references,
                timeout_ms=timeout_ms
            )
            
            # Enqueue for background processing
            kpi_executor = get_kpi_executor()
            if kpi_executor.enqueue_measurement(request):
                print(f"📊 [NavigationExecutor] KPI queued for {step.get('to_node_label')} ({len(kpi_references)} refs, {timeout_ms}ms timeout)")
            else:
                print(f"⚠️ [NavigationExecutor] Failed to queue KPI - queue full")
        
        except ValueError as e:
            # Validation errors from KPIMeasurementRequest - log and skip
            print(f"❌ [NavigationExecutor] KPI validation failed: {e}")
        except Exception as e:
            # Unexpected errors - log and skip
            print(f"❌ [NavigationExecutor] KPI queue error: {e}")
    
    def _get_device_capture_dir(self) -> Optional[str]:
        """
        Get capture directory for this device from active_captures.conf.
        Returns None if not found - no fallback.
        """
        active_captures_file = '/tmp/active_captures.conf'
        
        if not os.path.exists(active_captures_file):
            print(f"⚠️ [NavigationExecutor] {active_captures_file} not found")
            return None
        
        try:
            with open(active_captures_file, 'r') as f:
                for line in f:
                    capture_base = line.strip()
                    if not capture_base:
                        continue
                    
                    # Match device: /var/www/html/stream/capture1 → device1
                    if self.device_id in capture_base:
                        capture_dir = os.path.join(capture_base, 'captures')
                        if os.path.exists(capture_dir):
                            return capture_dir
            
            print(f"⚠️ [NavigationExecutor] No matching capture dir for {self.device_id}")
            return None
        
        except Exception as e:
            print(f"❌ [NavigationExecutor] Error reading active_captures.conf: {e}")
            return None

    # ========================================
    # POSITION TRACKING METHODS
    # ========================================
    
    def get_current_position(self) -> Dict[str, Any]:
        """Get current navigation position for this device"""
        nav_context = self.device.navigation_context
        return {
            'success': True,
            'device_id': self.device_id,
            'current_node_id': nav_context['current_node_id'],
            'current_node_label': nav_context['current_node_label'],
            'current_tree_id': nav_context['current_tree_id']
        }
    
    def get_node_id(self, node_label: str) -> str:
        """Get node_id by label using loaded unified graph"""
        if not self.unified_graph:
            raise ValueError("Unified graph not loaded - call load_navigation_tree() first")
        for node_id, node_data in self.unified_graph.nodes(data=True):
            if node_data.get('label') == node_label:
                return node_id
        raise ValueError(f"Node with label '{node_label}' not found in navigation graph")
    
    def get_node_label(self, node_id: str) -> str:
        """Find node label by node_id using loaded unified graph"""
        if not self.unified_graph:
            raise ValueError("Unified graph not loaded - call load_navigation_tree() first")
        
        if node_id in self.unified_graph.nodes:
            node_data = self.unified_graph.nodes[node_id]
            return node_data.get('label')  # Fallback to node_id if no label
        
        raise ValueError(f"Node with id '{node_id}' not found in navigation graph")
    
    def update_current_position(self, node_id: str, tree_id: str = None, node_label: str = None) -> Dict[str, Any]:
        """Update current navigation position for this device"""
        nav_context = self.device.navigation_context
        nav_context['current_node_id'] = node_id
        nav_context['current_tree_id'] = tree_id
        nav_context['current_node_label'] = node_label
        
        # Only log position updates when called directly (not from navigation completion)
        # Navigation completion already logs the final position
        import inspect
        caller_function = inspect.stack()[1].function
        if caller_function != 'execute_navigation':
            print(f"[@navigation_executor] Position updated: {self.device_id} → {node_id}")
        
        return {
            'success': True,
            'device_id': self.device_id,
            'current_node_id': nav_context['current_node_id'],
            'current_node_label': nav_context['current_node_label'],
            'current_tree_id': nav_context['current_tree_id']
        }
    
    def clear_current_position(self) -> Dict[str, Any]:
        """Clear current navigation position (e.g., when switching interfaces)"""
        nav_context = self.device.navigation_context
        old_position = {
            'node_id': nav_context['current_node_id'],
            'tree_id': nav_context['current_tree_id'],
            'node_label': nav_context['current_node_label']
        }
        
        nav_context['current_node_id'] = None
        nav_context['current_tree_id'] = None
        nav_context['current_node_label'] = None
        
        print(f"[@navigation_executor] Cleared position for {self.device_id} (was: {old_position['node_id']})")
        
        return {
            'success': True,
            'device_id': self.device_id,
            'previous_position': old_position,
            'current_position': None
        }
