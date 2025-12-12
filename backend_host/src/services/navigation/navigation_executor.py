"""
Navigation Execution System

Unified navigation executor with complete tree management, pathfinding, and execution capabilities.
Consolidates all navigation functionality without external dependencies.
"""

import os
import time
import threading
import uuid
import json
from typing import Dict, List, Optional, Any, Tuple

# Core imports
from  backend_host.src.services.navigation.navigation_pathfinding import find_shortest_path
from shared.src.lib.utils.navigation_exceptions import NavigationTreeError, UnifiedCacheError, PathfindingError, DatabaseError
from shared.src.lib.utils.navigation_cache import populate_unified_cache

# Helper functions (extracted for maintainability)
from backend_host.src.services.navigation.navigation_executor_helpers import (
    find_node_by_label,
    find_edges_from_node,
    find_edge_by_target_label,
    find_edge_with_action_command,
    get_node_sub_trees_with_actions,
    find_action_in_nested_trees
)

# Tree management functions (extracted for maintainability)
from backend_host.src.services.navigation.navigation_executor_tree_manager import (
    load_navigation_tree as tree_manager_load_navigation_tree,
    discover_complete_hierarchy as tree_manager_discover_complete_hierarchy,
    format_tree_for_hierarchy as tree_manager_format_tree_for_hierarchy,
    build_unified_tree_data as tree_manager_build_unified_tree_data
)


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
        self.device_name = device.device_name
        self.unified_graph = None
        # Preview cache: (tree_id, current_node, target_node) -> preview_result
        self._preview_cache = {}
        
        # Async execution tracking (for navigation polling)
        self._executions: Dict[str, Dict[str, Any]] = {}  # execution_id -> execution state
        self._lock = threading.Lock()
      
    def clear_preview_cache(self, tree_id: str = None):
        """Clear preview cache for a specific tree or all trees"""
        if tree_id:
            # Clear only cache entries for this tree
            keys_to_delete = [k for k in self._preview_cache.keys() if k[0] == tree_id]
            for key in keys_to_delete:
                del self._preview_cache[key]
            print(f"[@navigation_executor:clear_preview_cache] Cleared {len(keys_to_delete)} cached previews for tree {tree_id}")
        else:
            # Clear entire cache
            count = len(self._preview_cache)
            self._preview_cache = {}
            print(f"[@navigation_executor:clear_preview_cache] Cleared all {count} cached previews")
    
    def get_available_context(self, userinterface_name: str, team_id: str) -> Dict[str, Any]:
        """Get available navigation context using cache when possible"""
        # First check if we have a cached unified graph for this interface
        from shared.src.lib.database.userinterface_db import get_userinterface_by_name
        from shared.src.lib.database.navigation_trees_db import get_root_tree_for_interface
        from shared.src.lib.utils.navigation_cache import get_cached_unified_graph
        
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
    
    
    async def execute_navigation(self, 
                          tree_id: str,
                          userinterface_name: str,  # MANDATORY for reference resolution
                          target_node_id: str = None,
                          target_node_label: str = None,
                          navigation_path: List[Dict] = None,
                          current_node_id: Optional[str] = None,
                          frontend_sent_position: bool = False,  # NEW: Did frontend explicitly send position?
                          image_source_url: Optional[str] = None,
                          team_id: str = None,
                          context=None) -> Dict[str, Any]:
        
        print(f"\n[@navigation_executor:execute_navigation] 🎯 EXECUTE NAVIGATION CALLED:")
        print(f"[@navigation_executor:execute_navigation]   → tree_id: {tree_id}")
        print(f"[@navigation_executor:execute_navigation]   → target_node_id: {target_node_id}")
        print(f"[@navigation_executor:execute_navigation]   → target_node_label: {target_node_label}")
        print(f"[@navigation_executor:execute_navigation]   → current_node_id: {current_node_id}")
        print(f"[@navigation_executor:execute_navigation]   → frontend_sent_position: {frontend_sent_position}")
        print(f"[@navigation_executor:execute_navigation]   → userinterface_name: {userinterface_name}\n")
        """
        Execute navigation to target node using ONLY unified pathfinding with nested tree support.
        Enhanced with all capabilities from old goto_node method.
        
        Args:
            tree_id: Navigation tree ID
            userinterface_name: User interface name (REQUIRED for reference resolution, e.g., 'horizon_android_tv')
            target_node_id: ID of the target node to navigate to (mutually exclusive with target_node_label)
            target_node_label: Label of the target node to navigate to (mutually exclusive with target_node_id)
            navigation_path: Optional pre-computed navigation path (for validation scripts)
                           If provided, pathfinding is skipped and this path is executed directly
            current_node_id: Optional current node ID for starting point
            image_source_url: Optional image source URL
            team_id: Team ID for security
            context: Optional ScriptExecutionContext for tracking step results
            
        Returns:
            Dict with success status and navigation details
        """
        start_time = time.time()
        
        # 🔄 AUTO-SYNC: If unified_graph not loaded but cache exists, sync from cache
        if not self.unified_graph and team_id:
            from shared.src.lib.utils.navigation_cache import get_cached_unified_graph
            cached_graph = get_cached_unified_graph(tree_id, team_id)
            if cached_graph:
                self.unified_graph = cached_graph
                print(f"[@navigation_executor:execute_navigation] ✅ Auto-synced unified_graph from cache ({len(cached_graph.nodes)} nodes)")
            else:
                print(f"[@navigation_executor:execute_navigation] ⚠️ No cached graph found for tree {tree_id}")
        
        # Validate parameters - either navigation_path OR target must be provided
        if navigation_path:
            # Pre-computed path mode (validation scripts)
            if target_node_id or target_node_label:
                return self._build_result(
                    False,
                    "Cannot provide both navigation_path and target - use only one",
                    tree_id, None, current_node_id, start_time
                )
            print(f"[@navigation_executor:execute_navigation] 🔄 Pre-computed path mode: {len(navigation_path)} transitions provided")
        else:
            # Normal pathfinding mode (goto scripts)
            if not target_node_id and not target_node_label:
                return self._build_result(
                    False, 
                    "Either target_node_id, target_node_label, or navigation_path must be provided",
                    tree_id, None, current_node_id, start_time
                )
            
            if target_node_id and target_node_label:
                return self._build_result(
                    False, 
                    "Cannot provide both target_node_id and target_node_label - use only one",
                    tree_id, target_node_id, current_node_id, start_time
                )
        
        # Resolve target_node_label to target_node_id if label provided
        if target_node_label:
            try:
                target_node_id = self.get_node_id(target_node_label, tree_id, team_id)
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
        # Note: target_node_label might already be set if provided as input parameter
        if not target_node_label:
            if self.unified_graph or (tree_id and team_id):
                try:
                    target_node_label = self.get_node_label(target_node_id, tree_id, team_id)
                except ValueError:
                    print(f"[@navigation_executor:execute_navigation] Could not find label for node_id '{target_node_id}' - will use ID for logging")
                    target_node_label = target_node_id
        
        try:
            from backend_host.src.services.navigation.navigation_pathfinding import find_shortest_path
            from shared.src.lib.utils.navigation_exceptions import UnifiedCacheError, PathfindingError
            
            # SIMPLE RULE: Frontend is source of truth when it sends position (even if None)
            if frontend_sent_position:
                if current_node_id:
                    # Frontend says "start from this node"
                    nav_context['current_node_id'] = current_node_id
                    nav_context['current_node_label'] = self.get_node_label(current_node_id, tree_id, team_id)
                    print(f"[@navigation_executor:execute_navigation] Starting from frontend position: {current_node_id} ({nav_context['current_node_label']})")
                else:
                    # Frontend says "I don't know position" → clear backend, use entry
                    if nav_context.get('current_node_id'):
                        print(f"[@navigation_executor:execute_navigation] Frontend cleared position (was: {nav_context.get('current_node_id')})")
                    nav_context['current_node_id'] = None
                    nav_context['current_node_label'] = None
                    print(f"[@navigation_executor:execute_navigation] Starting from entry (frontend doesn't know position)")
            else:
                # Frontend didn't send position → trust backend (set by previous navigation in script)
                # BUT verify if position is stale (>30s old)
                if nav_context.get('current_node_id'):
                    position_timestamp = nav_context.get('position_timestamp', 0)
                    time_since_position = time.time() - position_timestamp if position_timestamp else 999
                    
                    if time_since_position > 30:
                        # Position is stale (>30s old) - verify before trusting
                        print(f"[@navigation_executor:execute_navigation] ⏰ Backend position is {int(time_since_position)}s old - verifying before use")
                        stale_node_id = nav_context['current_node_id']
                        stale_node_label = nav_context.get('current_node_label', 'unknown')
                        
                        verification_result = await self.device.verification_executor.verify_node(
                            node_id=stale_node_id,
                            userinterface_name=userinterface_name,
                            team_id=team_id,
                            tree_id=tree_id
                        )
                        
                        if verification_result.get('success') and verification_result.get('has_verifications', True):
                            print(f"[@navigation_executor:execute_navigation] ✅ Stale position verified - still at {stale_node_label}")
                            # Update timestamp to mark as fresh
                            nav_context['position_timestamp'] = time.time()
                            nav_context['last_verified_timestamp'] = time.time()
                        else:
                            print(f"[@navigation_executor:execute_navigation] ❌ Stale position verification failed - clearing position (was: {stale_node_label})")
                            # Clear stale position - we're not there anymore
                            nav_context['current_node_id'] = None
                            nav_context['current_node_label'] = None
                            nav_context['current_tree_id'] = None
                            nav_context['position_timestamp'] = 0
                            nav_context['last_verified_timestamp'] = 0
                            print(f"[@navigation_executor:execute_navigation] Starting from entry (stale position cleared)")
                    else:
                        print(f"[@navigation_executor:execute_navigation] Starting from backend position: {nav_context['current_node_id']} ({nav_context.get('current_node_label', 'unknown')}) [{int(time_since_position)}s old]")
                else:
                    print(f"[@navigation_executor:execute_navigation] Starting from entry (no position tracked)")
            
            # Skip "already at target" optimization if using pre-computed path (validation mode)
            if navigation_path:
                print(f"[@navigation_executor:execute_navigation] Pre-computed path mode - skipping position checks")
            else:
                print(f"[@navigation_executor:execute_navigation] Navigating to '{target_node_label or target_node_id}' using unified pathfinding")
            
            # Check if already at target BEFORE pathfinding - but ONLY if we know our current position
            # Skip this check if using pre-computed path (validation needs to test the transition)
            current_position = nav_context.get('current_node_id')
            if not navigation_path:
                print(f"[@navigation_executor:execute_navigation] Current position: {current_position}, Target: {target_node_id}")
            
            # 🔍 POSITION TRACKING BUG DETECTION: If position tracking says we're elsewhere but target is close,
            # verify target first to catch stale position tracking (e.g., "android_home" vs "home" confusion)
            if not navigation_path and current_position and current_position != target_node_id:
                # Quick pathfinding check: is target reachable in 1 step?
                from shared.src.lib.utils.navigation_cache import get_cached_unified_graph
                cached_graph = get_cached_unified_graph(tree_id, team_id)
                if cached_graph and current_position in cached_graph.nodes and target_node_id in cached_graph.nodes:
                    # Check if target is a direct neighbor (1 step away)
                    if cached_graph.has_edge(current_position, target_node_id):
                        print(f"[@navigation_executor:execute_navigation] 🔍 Target is 1 step away - verifying if already there to catch position tracking bugs")
                        verification_result = await self.device.verification_executor.verify_node(
                            node_id=target_node_id,
                            userinterface_name=userinterface_name,
                            team_id=team_id,
                            tree_id=tree_id
                        )
                        
                        # If we're ACTUALLY at the target visually, update position and skip navigation
                        if verification_result.get('success') and verification_result.get('has_verifications', True):
                            current_label = nav_context.get('current_node_label', 'unknown')
                            print(f"[@navigation_executor:execute_navigation] ⚠️ POSITION TRACKING BUG DETECTED!")
                            print(f"[@navigation_executor:execute_navigation]   System thought we were at: {current_position} ({current_label})")
                            print(f"[@navigation_executor:execute_navigation]   But verification confirms we're already at: {target_node_id} ({target_node_label or target_node_id})")
                            print(f"[@navigation_executor:execute_navigation] ✅ Correcting position and skipping navigation")
                            
                            # Correct the position tracking
                            self.update_current_position(target_node_id, tree_id, target_node_label)
                            nav_context['last_verified_timestamp'] = time.time()
                            nav_context['current_node_navigation_success'] = True
                            
                            # Record dummy step showing position correction
                            if context:
                                from datetime import datetime
                                from shared.src.lib.utils.device_utils import capture_screenshot_for_script
                                
                                screenshot_path = ""
                                screenshot_id = capture_screenshot_for_script(self.device, context, f"position_corrected_{target_node_label or target_node_id}")
                                if screenshot_id and context.screenshot_paths:
                                    screenshot_path = context.screenshot_paths[-1]
                                
                                dummy_step_result = {
                                    'success': True,
                                    'from_node': target_node_label or target_node_id,
                                    'to_node': target_node_label or target_node_id,
                                    'message': f"Position tracking corrected: {current_label} → {target_node_label or target_node_id}",
                                    'already_at_destination': True,
                                    'position_tracking_bug_detected': True,
                                    'execution_time_ms': 0,
                                    'start_time': datetime.now().strftime('%H:%M:%S'),
                                    'end_time': datetime.now().strftime('%H:%M:%S'),
                                    'actions': [],
                                    'step_category': 'navigation',
                                    'step_end_screenshot_path': screenshot_path,
                                    'screenshot_path': screenshot_path
                                }
                                context.record_step_immediately(dummy_step_result)
                                if hasattr(context, 'write_running_log'):
                                    context.write_running_log()
                            
                            return self._build_result(
                                True,
                                f"Position tracking bug detected and corrected - already at '{target_node_label or target_node_id}'",
                                tree_id, target_node_id, current_node_id, start_time,
                                transitions_executed=0,
                                total_transitions=0,
                                actions_executed=0,
                                total_actions=0,
                                path_length=0,
                                already_at_target=True,
                                position_tracking_bug_corrected=True,
                                unified_pathfinding_used=True,
                                navigation_path=[]
                            )
                        else:
                            print(f"[@navigation_executor:execute_navigation] Verification failed - position tracking is correct, proceeding with navigation")
            
            if current_position and current_position == target_node_id and not navigation_path:
                print(f"[@navigation_executor:execute_navigation] 🔍 Context indicates already at target '{target_node_label or target_node_id}' - verifying...")
                
                # Always verify we're actually at this node (context may be stale or corrupted)
                verification_result = await self.device.verification_executor.verify_node(
                    node_id=target_node_id,
                    userinterface_name=userinterface_name,  # MANDATORY parameter
                    team_id=team_id,
                    tree_id=tree_id
                )
                
                # Only trust verification if verifications are defined AND passed
                if verification_result.get('success') and verification_result.get('has_verifications', True):
                    print(f"[@navigation_executor:execute_navigation] ✅ Verified at target '{target_node_label or target_node_id}' - no navigation needed")
                    # Store verification timestamp for caching
                    nav_context['last_verified_timestamp'] = time.time()
                    # Update position to ensure consistency
                    self.update_current_position(target_node_id, tree_id, target_node_label)
                    # Mark navigation as successful
                    nav_context['current_node_navigation_success'] = True
                    
                    # Record dummy step to show from/target nodes in report
                    if context:
                        from datetime import datetime
                        from shared.src.lib.utils.device_utils import capture_screenshot_for_script
                        
                        # Capture screenshot to show verified destination state
                        screenshot_path = ""
                        screenshot_id = capture_screenshot_for_script(self.device, context, f"already_at_{target_node_label or target_node_id}")
                        if screenshot_id and context.screenshot_paths:
                            screenshot_path = context.screenshot_paths[-1]
                            print(f"📸 [@navigation_executor:execute_navigation] Screenshot captured for 'already at destination': {screenshot_id}")
                        
                        dummy_step_result = {
                            'success': True,
                            'from_node': target_node_label or target_node_id,
                            'to_node': target_node_label or target_node_id,
                            'message': f"{target_node_label or target_node_id} → {target_node_label or target_node_id}",
                            'already_at_destination': True,
                            'execution_time_ms': 0,
                            'start_time': datetime.now().strftime('%H:%M:%S'),
                            'end_time': datetime.now().strftime('%H:%M:%S'),
                            'actions': [],
                            'step_category': 'navigation',
                            'step_end_screenshot_path': screenshot_path,
                            'screenshot_path': screenshot_path
                        }
                        context.record_step_immediately(dummy_step_result)
                        # Auto-write to running.log for frontend overlay
                        if hasattr(context, 'write_running_log'):
                            context.write_running_log()
                    
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
                elif not verification_result.get('has_verifications', True):
                    print(f"[@navigation_executor:execute_navigation] ⚠️ No verifications defined for target node - cannot verify position, proceeding with navigation from entry")
                    # Clear position since we can't verify
                    nav_context['current_node_id'] = None
                    nav_context['current_node_label'] = None
                    nav_context['last_verified_timestamp'] = 0
                else:
                    print(f"[@navigation_executor:execute_navigation] ⚠️ Verification failed - context corrupted, proceeding with navigation")
                    # Clear corrupted position and verification timestamp
                    nav_context['current_node_id'] = None
                    nav_context['current_node_label'] = None
                    nav_context['last_verified_timestamp'] = 0
            elif not current_position and not navigation_path:
                # No current position - verify if already at destination before starting navigation
                print(f"[@navigation_executor:execute_navigation] No current position - checking if already at target '{target_node_label or target_node_id}'")
                
                verification_result = await self.device.verification_executor.verify_node(
                    node_id=target_node_id,
                    userinterface_name=userinterface_name,
                    team_id=team_id,
                    tree_id=tree_id
                )
                
                # Only skip navigation if verifications exist AND passed
                if verification_result.get('success') and verification_result.get('has_verifications', True):
                    print(f"[@navigation_executor:execute_navigation] ✅ Already at target '{target_node_label or target_node_id}' - no navigation needed")
                    nav_context['last_verified_timestamp'] = time.time()
                    self.update_current_position(target_node_id, tree_id, target_node_label)
                    nav_context['current_node_navigation_success'] = True
                    
                    # Record dummy step to show from/target nodes in report
                    if context:
                        from datetime import datetime
                        from shared.src.lib.utils.device_utils import capture_screenshot_for_script
                        
                        screenshot_path = ""
                        screenshot_id = capture_screenshot_for_script(self.device, context, f"already_at_{target_node_label or target_node_id}")
                        if screenshot_id and context.screenshot_paths:
                            screenshot_path = context.screenshot_paths[-1]
                            print(f"📸 [@navigation_executor:execute_navigation] Screenshot captured for 'already at destination': {screenshot_id}")
                        
                        dummy_step_result = {
                            'success': True,
                            'from_node': target_node_label or target_node_id,
                            'to_node': target_node_label or target_node_id,
                            'message': f"{target_node_label or target_node_id} → {target_node_label or target_node_id}",
                            'already_at_destination': True,
                            'execution_time_ms': 0,
                            'start_time': datetime.now().strftime('%H:%M:%S'),
                            'end_time': datetime.now().strftime('%H:%M:%S'),
                            'actions': [],
                            'step_category': 'navigation',
                            'step_end_screenshot_path': screenshot_path,
                            'screenshot_path': screenshot_path
                        }
                        context.record_step_immediately(dummy_step_result)
                        if hasattr(context, 'write_running_log'):
                            context.write_running_log()
                    
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
                elif not verification_result.get('has_verifications', True):
                    print(f"[@navigation_executor:execute_navigation] ⚠️ No verifications defined for '{target_node_label or target_node_id}' - cannot verify position, proceeding with navigation from entry")
                else:
                    # Not at target - check if at home as fallback starting position
                    # IMPORTANT: Only check home if target is NOT home (avoid duplicate verification)
                    print(f"[@navigation_executor:execute_navigation] Not at target '{target_node_label or target_node_id}' - checking if at HOME as fallback position")
                    
                    # Find home node by trying common variations: "home", "Home", "HOME"
                    home_id = None
                    home_node_label = None
                    for potential_home_label in ["home", "Home", "HOME"]:
                        try:
                            home_id = self.get_node_id(potential_home_label, tree_id, team_id)
                            home_node_label = potential_home_label
                            print(f"[@navigation_executor:execute_navigation] Found home node: {home_id} (label: {home_node_label})")
                            break
                        except ValueError:
                            continue
                    
                    # Only verify home if: (1) home exists, (2) target is NOT home
                    if home_id and home_id != target_node_id:
                        print(f"[@navigation_executor:execute_navigation] Target is not home - verifying if at home")
                        home_verification = await self.device.verification_executor.verify_node(
                            node_id=home_id,
                            userinterface_name=userinterface_name,
                            team_id=team_id,
                            tree_id=tree_id
                        )
                        
                        if home_verification.get('success') and home_verification.get('has_verifications', True):
                            print(f"[@navigation_executor:execute_navigation] ✅ Already at HOME - will navigate from HOME → {target_node_label or target_node_id}")
                            # Update position to home so pathfinding starts from there
                            self.update_current_position(home_id, tree_id, home_node_label)
                            nav_context['last_verified_timestamp'] = time.time()
                            # Continue to pathfinding (don't return)
                        else:
                            print(f"[@navigation_executor:execute_navigation] Not at home - will navigate from entry")
                    elif home_id == target_node_id:
                        print(f"[@navigation_executor:execute_navigation] Target IS home - skipping duplicate home verification")
                    else:
                        print(f"[@navigation_executor:execute_navigation] No home node found in tree - will navigate from entry")
            else:
                # Positions don't match - proceed with navigation
                print(f"[@navigation_executor:execute_navigation] Current position ({current_position}) != target ({target_node_id}) - proceeding with navigation")
            
            # Use unified pathfinding with current navigation context position (unless path already provided)
            if not navigation_path:
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
            else:
                print(f"[@navigation_executor:execute_navigation] Using pre-computed path with {len(navigation_path)} steps (pathfinding skipped)")
            
            # Execute navigation sequence with early stopping for navigation functions
            transitions_executed = 0
            actions_executed = 0
            total_actions = sum(len(step.get('actions', [])) for step in navigation_path)
            
            for i, step in enumerate(navigation_path):
                step_num = i + 1
                from_node = step.get('from_node_label', 'unknown')
                to_node = step.get('to_node_label', 'unknown')
                from_node_id = step.get('from_node_id')  # UUID
                to_node_id = step.get('to_node_id')  # UUID
                
                print(f"[@navigation_executor:execute_navigation] Step {step_num}/{len(navigation_path)}: {from_node} → {to_node}")
                
                # Step start screenshot - capture BEFORE action execution (like old goto_node)
                step_start_screenshot_path = ""
                if context:
                    from shared.src.lib.utils.device_utils import capture_screenshot_for_script
                    step_name = f"step_{step_num}_{from_node}_{to_node}"
                    screenshot_id = capture_screenshot_for_script(self.device, context, f"{step_name}_start")
                    if screenshot_id:
                        # Get the actual path from context - it's the last added screenshot
                        if context.screenshot_paths:
                            step_start_screenshot_path = context.screenshot_paths[-1]
                        print(f"📸 [@navigation_executor:execute_navigation] Step-start screenshot captured: {screenshot_id}")
                
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
                    
                    # Use orchestrator for unified logging
                    from backend_host.src.orchestrator import ExecutionOrchestrator
                    result = await ExecutionOrchestrator.execute_actions(
                        device=self.device,
                        actions=actions,
                        retry_actions=retry_actions,
                        failure_actions=failure_actions,
                        team_id=team_id,
                        context=context
                    )
                    
                    actions_executed += result.get('passed_count', 0)
                    
                    # ✅ Track last action timestamp for zapping detection sync
                    if result.get('results'):
                        last_action_result = result['results'][-1]  # Get last executed action
                        last_action_timestamp = last_action_result.get('action_timestamp')
                        if last_action_timestamp:
                            nav_context['last_action_timestamp'] = last_action_timestamp
                else:
                    # No actions to execute, just mark as successful
                    result = {'success': True, 'main_actions_succeeded': True}
                
                # Execute verifications after actions (if any)
                verification_result = {'success': True, 'results': []}
                step_verifications = step.get('verifications', [])
                if step_verifications:
                    print(f"[@navigation_executor:execute_navigation] Executing {len(step_verifications)} verifications for step")
                    
                    # ✅ SIMPLIFIED: Use verify_node() which automatically handles verification_pass_condition from node
                    # No need to manually extract and pass it - the verification executor knows the node's settings
                    to_node_id = step.get('to_node_id')
                    verification_result = await self.device.verification_executor.verify_node(
                        node_id=to_node_id,
                        userinterface_name=userinterface_name,
                        team_id=team_id,
                        tree_id=tree_id
                    )
                    print(f"[@navigation_executor:execute_navigation] Verifications: {verification_result.get('passed_count', 0)}/{verification_result.get('total_count', 0)} passed")
                    
                    # ✅ VERIFICATION-DRIVEN RETRY: If main actions succeeded BUT verifications failed, try retry actions
                    if result.get('success', False) and result.get('main_actions_succeeded', False) and not verification_result.get('success', True) and retry_actions:
                        print(f"[@navigation_executor:execute_navigation] ⚠️ Main actions succeeded but verifications failed - attempting retry actions")
                        
                        # Execute retry actions as main actions (no retry/failure for retry)
                        from backend_host.src.orchestrator import ExecutionOrchestrator
                        retry_result = await ExecutionOrchestrator.execute_actions(
                            device=self.device,
                            actions=retry_actions,
                            retry_actions=[],
                            failure_actions=[],
                            team_id=team_id,
                            context=context
                        )
                        
                        # Track retry action timestamp
                        if retry_result.get('results'):
                            last_retry_action = retry_result['results'][-1]
                            last_retry_timestamp = last_retry_action.get('action_timestamp')
                            if last_retry_timestamp:
                                nav_context['last_action_timestamp'] = last_retry_timestamp
                        
                        # Re-execute verifications after retry actions
                        if retry_result.get('success', False):
                            print(f"[@navigation_executor:execute_navigation] Retry actions succeeded - re-verifying node")
                            
                            # ✅ SIMPLIFIED: Use verify_node() which automatically handles verification_pass_condition
                            to_node_id = step.get('to_node_id')
                            verification_result = await self.device.verification_executor.verify_node(
                                node_id=to_node_id,
                                userinterface_name=userinterface_name,
                                team_id=team_id,
                                tree_id=tree_id
                            )
                            print(f"[@navigation_executor:execute_navigation] Post-retry verifications: {verification_result.get('passed_count', 0)}/{verification_result.get('total_count', 0)} passed")
                            
                            # Update result to reflect retry success
                            if verification_result.get('success', True):
                                print(f"[@navigation_executor:execute_navigation] ✅ Retry actions + verifications succeeded")
                                result = retry_result  # Use retry result for KPI tracking
                        else:
                            print(f"[@navigation_executor:execute_navigation] ❌ Retry actions failed - verification remains failed")
                
                step_execution_time = int((time.time() - step_start_time) * 1000)
                
                # Note: ActionExecutor now handles screenshots during action execution
                # No need for redundant main action screenshot here
                
                # Step end screenshot - capture AFTER action execution (like old goto_node)
                step_end_screenshot_path = ""
                if context:
                    from shared.src.lib.utils.device_utils import capture_screenshot_for_script
                    screenshot_id = capture_screenshot_for_script(self.device, context, f"{step_name}_end")
                    if screenshot_id:
                        # Get the actual path from context - it's the last added screenshot
                        if context.screenshot_paths:
                            step_end_screenshot_path = context.screenshot_paths[-1]
                        print(f"📸 [@navigation_executor:execute_navigation] Step-end screenshot captured: {screenshot_id}")
                
                # Determine final error message - verification error takes precedence over action error
                final_error = None
                debug_report_url = None  # ✅ NEW: Track debug report URL
                if not verification_result.get('success', True):
                    # Verification failed - use verification error
                    final_error = verification_result.get('error', 'Verification failed')
                    # ✅ NEW: Get debug report URL if available
                    debug_report_url = verification_result.get('debug_report_url')
                elif not result.get('success', False):
                    # Actions failed - use action error
                    final_error = result.get('error', 'Action failed')
                
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
                        'success': result.get('success', False) and verification_result.get('success', True),  # Both actions AND verifications must succeed
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
                        'verification_results': verification_result.get('results', []),  # From verification execution
                        'verification_screenshots': verification_result.get('verification_screenshots', []),  # All verification screenshots
                        'error': final_error,  # Verification error takes precedence over action error
                        'debug_report_url': debug_report_url,  # ✅ NEW: Include debug report URL for frontend
                        'step_category': 'navigation'
                    }
                    
                    # Add verification screenshots to main screenshot collection for R2 upload
                    # This ensures cropped verification result images get uploaded to R2
                    for verif_screenshot in verification_result.get('verification_screenshots', []):
                        if verif_screenshot and context and hasattr(context, 'add_screenshot'):
                            context.add_screenshot(verif_screenshot)
                    
                    # Record step immediately - step number shown in table
                    context.record_step_immediately(step_result)
                    # Auto-write to running.log for frontend overlay
                    if hasattr(context, 'write_running_log'):
                        context.write_running_log()
                    # Simple message without redundant step number
                    step_result['message'] = f"{from_node} → {to_node}"
                
                # Store action success for KPI queueing after final verification
                if result.get('success', False) and result.get('main_actions_succeeded', False):
                    # Get actual action completion timestamp from navigation context
                    nav_context = self.device.navigation_context
                    action_completion_timestamp = nav_context.get('last_action_timestamp', step_start_time)
                    # Get action screenshots: before-action from separate field, after-action from screenshot list
                    before_action_screenshot = result.get('before_action_screenshot')  # From separate field (not in validation report)
                    action_screenshots = result.get('action_screenshots', [])
                    after_action_screenshot = action_screenshots[-1] if len(action_screenshots) > 0 else None
                    # Get action details from last action result for KPI report
                    action_details = None
                    if result.get('results'):
                        last_action_result = result['results'][-1]  # Last action in batch
                        action_details = last_action_result.get('action_details')
                    # Store for KPI queueing after final verification
                    nav_context['kpi_step'] = step
                    nav_context['kpi_action_timestamp'] = action_completion_timestamp
                    nav_context['kpi_before_screenshot'] = before_action_screenshot  # ✅ Before action screenshot
                    nav_context['kpi_action_screenshot'] = after_action_screenshot  # After action screenshot
                    nav_context['kpi_userinterface_name'] = userinterface_name  # Store for reference resolution
                    nav_context['kpi_action_details'] = action_details  # ✅ NEW: Store action details
                    print(f"[@navigation_executor:execute_navigation] Main actions succeeded for step {step_num}/{len(navigation_path)} - KPI will be queued after final verification")
                
                # Check if EITHER actions OR verifications failed - both must succeed for step to continue
                step_failed = not result.get('success', False) or not verification_result.get('success', True)
                
                if step_failed:
                    # Determine which component failed
                    if not verification_result.get('success', True):
                        error_msg = verification_result.get('error', 'Verification failed')
                        error_details = verification_result.get('error_details', {})
                        failure_type = "verification"
                        # ✅ Extract debug report path and URL if available
                        debug_report_path = verification_result.get('debug_report_path')
                        debug_report_url = verification_result.get('debug_report_url')
                    else:
                        error_msg = result.get('error', 'Unknown error')
                        error_details = result.get('error_details', {})
                        failure_type = "action"
                        debug_report_path = None
                        debug_report_url = None
                    
                    print(f"[@navigation_executor:execute_navigation] NAVIGATION STEP FAILED:")
                    print(f"[@navigation_executor:execute_navigation]   Step {step_num}/{len(navigation_path)}: {from_node} → {to_node}")
                    print(f"[@navigation_executor:execute_navigation]   Failure type: {failure_type}")
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
                    
                    # CONDITIONAL EDGE RECOVERY: If verification failed after successful action, try sibling edges
                    if failure_type == "verification" and result.get('success', False):
                        print(f"[@navigation_executor:execute_navigation] 🔄 Verification failed - checking for conditional edge siblings")
                        recovery_result = await self._try_conditional_edge_siblings(
                            step=step,
                            from_node_id=from_node_id,
                            expected_target_node_id=to_node_id,
                            target_node_id=target_node_id,  # Final destination
                            userinterface_name=userinterface_name,
                            team_id=team_id,
                            tree_id=tree_id,
                            context=context,
                            image_source_url=image_source_url,
                            max_attempts=3
                        )
                        
                        if recovery_result.get('success'):
                            # Successfully recovered - update position and continue
                            actual_node = recovery_result.get('actual_node_id')
                            print(f"[@navigation_executor:execute_navigation] ✅ Conditional edge recovery succeeded → landed at {actual_node}")
                            
                            # Update device position
                            self.device.current_node_id = actual_node
                            
                            # Check if we reached final destination
                            if actual_node == target_node_id:
                                print(f"[@navigation_executor:execute_navigation] 🎯 Reached final destination via conditional edge")
                                transitions_executed += 1
                                # Exit step loop and continue to final verification
                                break
                            else:
                                # Try to find recovery path from actual_node to target
                                print(f"[@navigation_executor:execute_navigation] 🔍 Searching recovery path: {actual_node} → {target_node_id}")
                                recovery_path = self._find_recovery_path(
                                    current_node_id=actual_node,
                                    target_node_id=target_node_id,
                                    tree_id=tree_id,
                                    team_id=team_id,
                                    visited_nodes=set([from_node_id])  # Only prevent going back to the original source
                                )
                                
                                if recovery_path:
                                    print(f"[@navigation_executor:execute_navigation] ✅ Found recovery path with {len(recovery_path)} steps")
                                    # Insert recovery steps into navigation path
                                    navigation_path = navigation_path[:step_num] + recovery_path
                                    transitions_executed += 1
                                    continue  # Continue with next step in updated path
                                else:
                                    print(f"[@navigation_executor:execute_navigation] ❌ No recovery path found from {actual_node} to {target_node_id}")
                                    # Fall through to failure handling below
                        # ✅ SIMPLIFIED: Skip logging for conditional edge recovery attempts (internal technical detail)
                        # Don't confuse user with "no siblings found" messages
                    
                    # NAVIGATION FUNCTIONS: Stop immediately on ANY step failure (no recovery attempts)
                    print(f"🛑 [@navigation_executor:execute_navigation] STOPPING navigation - navigation functions do not recover from failures")
                    
                    # Mark navigation as failed
                    nav_context['current_node_navigation_success'] = False
                    
                    detailed_error_msg = f"Navigation failed at step {step_num} ({from_node} → {to_node}): {failure_type} failed - {error_msg}"
                    
                    # Build error details with debug report path if available
                    build_error_details = {
                        'step_number': step_num,
                        'total_steps': len(navigation_path),
                        'from_node': from_node,
                        'to_node': to_node,
                        'execution_time_ms': step_execution_time,
                        'original_error': error_msg,
                        'action_details': error_details
                    }
                    
                    # ✅ Add debug report path and URL to error details if available
                    if debug_report_path:
                        build_error_details['debug_report_path'] = debug_report_path
                        print(f"[@navigation_executor:execute_navigation] Including debug_report_path in error: {debug_report_path}")
                    if debug_report_url:
                        build_error_details['debug_report_url'] = debug_report_url
                        print(f"[@navigation_executor:execute_navigation] Including debug_report_url in error: {debug_report_url}")
                    
                    return self._build_result(
                        False, 
                        detailed_error_msg,
                        tree_id, target_node_id, current_node_id, start_time,
                        transitions_executed=transitions_executed,
                        total_transitions=len(navigation_path),
                        actions_executed=actions_executed,
                        total_actions=total_actions,
                        error_details=build_error_details
                    )
                
                transitions_executed += 1
            
            # Get final destination for consolidated success message
            final_step = navigation_path[-1] if navigation_path else {}
            final_node_id = final_step.get('to_node_id')
            final_tree_id = final_step.get('to_tree_id', tree_id)
            
            # Update current location in context after successful navigation
            if context and hasattr(context, 'current_node_id') and final_node_id:
                context.current_node_id = final_node_id
            
            # Consolidated success message with timing and final position
            total_time = int((time.time() - start_time) * 1000)
            print(f"[@navigation_executor] Navigation to '{target_node_label or target_node_id}' completed successfully in {total_time}ms → {final_node_id}")
            
            # ✅ VERIFY FINAL DESTINATION
            print(f"[@navigation_executor] 🔍 Verifying final destination: {target_node_label or target_node_id}")
            verification_start_time = time.time()
            verification_result = await self.device.verification_executor.verify_node(
                node_id=final_node_id,
                userinterface_name=userinterface_name,  # MANDATORY parameter
                team_id=team_id,
                tree_id=final_tree_id,
                image_source_url=image_source_url
            )
            # Only set verification_timestamp if there were actual verifications
            if verification_result.get('has_verifications', True):
                verification_timestamp = time.time()
            else:
                verification_timestamp = None  # No verifications - KPI will use last_action_wait_ms
            
            # Only fail if verifications exist and they failed
            # If no verifications are defined (has_verifications=False), don't fail - we just can't verify
            if not verification_result.get('success') and verification_result.get('has_verifications', True):
                print(f"[@navigation_executor] ❌ Final verification failed: {verification_result.get('error', 'Unknown error')}")
                nav_context['current_node_navigation_success'] = False
                return self._build_result(
                    False,
                    f"Navigation completed but final verification failed: {verification_result.get('error', 'Unknown error')}",
                    tree_id, target_node_id, current_node_id, start_time,
                    transitions_executed=transitions_executed,
                    total_transitions=len(navigation_path),
                    actions_executed=actions_executed,
                    total_actions=total_actions,
                    verification_failed=True
                )
            
            # Report verification status
            if verification_result.get('has_verifications', True):
                if verification_result.get('success'):
                    print(f"[@navigation_executor] ✅ Final verification passed")
                else:
                    # This shouldn't happen (caught above), but log just in case
                    print(f"[@navigation_executor] ⚠️ Final verification had issues but continuing")
            else:
                print(f"[@navigation_executor] ⚠️ No verifications defined for target node - cannot verify final position, but navigation completed successfully")
            
            # Queue KPI measurement AFTER final verification passes
            # Only if main actions were executed and succeeded
            # IMPORTANT: KPI queueing must NEVER block navigation - it's observability, not critical path
            kpi_step = nav_context.get('kpi_step')
            kpi_action_timestamp = nav_context.get('kpi_action_timestamp')
            kpi_userinterface_name = nav_context.get('kpi_userinterface_name')
            kpi_before_screenshot = nav_context.get('kpi_before_screenshot')  # ✅ Before screenshot
            kpi_action_screenshot = nav_context.get('kpi_action_screenshot')  # After screenshot
            kpi_action_details = nav_context.get('kpi_action_details')  # ✅ NEW: Action details
            kpi_verification_evidence = verification_result.get('verification_evidence_list', [])  # ✅ NEW: Verification evidence
            
            if kpi_step and kpi_action_timestamp and kpi_userinterface_name:
                try:
                    # Log accurate message based on verification status
                    if verification_result.get('has_verifications', True):
                        print(f"[@navigation_executor] Final verification passed - queueing KPI measurement")
                    else:
                        print(f"[@navigation_executor] Navigation completed (no verifications) - queueing KPI measurement")
                    
                    self._queue_kpi_measurement(
                        step=kpi_step,
                        action_timestamp=kpi_action_timestamp,
                        verification_timestamp=verification_timestamp,
                        team_id=team_id,
                        userinterface_name=kpi_userinterface_name,
                        before_action_screenshot_path=kpi_before_screenshot,  # ✅ Before screenshot
                        action_screenshot_path=kpi_action_screenshot,  # After screenshot
                        action_details=kpi_action_details,  # ✅ NEW: Action details
                        verification_evidence_list=kpi_verification_evidence  # ✅ NEW: Verification evidence
                    )
                except Exception as e:
                    # KPI queueing failed - log but DO NOT block navigation
                    print(f"⚠️ [NavigationExecutor] KPI queueing failed (non-blocking): {e}")
                finally:
                    # Always clear KPI context regardless of success/failure
                    nav_context['kpi_step'] = None
                    nav_context['kpi_action_timestamp'] = None
                    nav_context['kpi_before_screenshot'] = None  # ✅ NEW: Clear before screenshot
                    nav_context['kpi_action_screenshot'] = None  # Clear after screenshot
                    nav_context['kpi_userinterface_name'] = None
            else:
                print(f"[@navigation_executor] No KPI to queue (no actions were executed or actions failed)")
            
            # Update position if navigation succeeded (but NOT for action nodes)
            if navigation_path:
                # Check if final node is an action node - actions don't update device position
                from shared.src.lib.utils.navigation_cache import get_cached_unified_graph
                unified_graph = get_cached_unified_graph(tree_id, team_id)
                if unified_graph:
                    final_node_data = unified_graph.nodes.get(final_node_id, {})
                    if final_node_data.get('node_type') == 'action':
                        print(f"[@navigation_executor] Action executed - device position remains at: {nav_context.get('current_node_label', 'unknown')}")
                    else:
                        self.update_current_position(final_node_id, tree_id, target_node_label)
                else:
                    # Fallback: update position if no graph available
                    self.update_current_position(final_node_id, tree_id, target_node_label)
            
            # Store verification timestamp
            nav_context['last_verified_timestamp'] = time.time()
            
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
    
    def get_execution_status(self, execution_id: str) -> Dict[str, Any]:
        """
        Get status of async navigation execution (called by route polling).
        
        Returns:
            {
                'success': bool,
                'execution_id': str,
                'status': 'running' | 'completed' | 'error',
                'result': dict (if completed),
                'error': str (if error),
                'progress': int,
                'message': str
            }
        """
        with self._lock:
            if execution_id not in self._executions:
                return {
                    'success': False,
                    'error': f'Execution {execution_id} not found'
                }
            
            execution = self._executions[execution_id].copy()
        
        return {
            'success': True,
            'execution_id': execution['execution_id'],
            'status': execution['status'],
            'result': execution.get('result'),
            'error': execution.get('error'),
            'progress': execution.get('progress', 0),
            'message': execution.get('message', ''),
            'tree_id': execution.get('tree_id'),
            'target_node_id': execution.get('target_node_id'),
            'elapsed_time_ms': int((time.time() - execution['start_time']) * 1000)
        }
    
    def get_navigation_preview(self, tree_id: str, target_node_id: str, 
                             current_node_id: Optional[str] = None, team_id: str = None) -> Dict[str, Any]:
        """
        Get navigation preview without executing - used by frontend NodeGotoPanel
        Expects unified cache to be pre-populated by tree loading
        
        Args:
            tree_id: Tree ID for pathfinding
            target_node_id: Target node UUID
            current_node_id: Optional current position
            team_id: Team ID
            
        Returns:
            {
                'success': bool,
                'error': str (if failed),
                'tree_id': str,
                'target_node_id': str,
                'current_node_id': str,
                'transitions': List[Dict],  # Navigation path
                'total_transitions': int,
                'total_actions': int
            }
        """
        # Check cache first (pure function: same inputs = same outputs until tree changes)
        cache_key = (tree_id, current_node_id or 'root', target_node_id)
        if cache_key in self._preview_cache:
            print(f"[@navigation_executor:get_navigation_preview] ✅ Cache HIT for {target_node_id} from {current_node_id or 'root'}")
            return self._preview_cache[cache_key]
        
        try:
            # Get navigation path using unified cache (should be pre-populated by tree loading)
            transitions = find_shortest_path(tree_id, target_node_id, team_id, current_node_id)
            
            success = bool(transitions)
            error_message = 'No navigation path found' if not success else ''
            
            result = {
                'success': success,
                'error': error_message if not success else None,
                'tree_id': tree_id,
                'target_node_id': target_node_id,
                'current_node_id': current_node_id,
                'transitions': transitions or [],
                'total_transitions': len(transitions) if transitions else 0,
                'total_actions': sum(len(t.get('actions', [])) for t in transitions) if transitions else 0
            }
            
            # Cache the result (invalidated when tree changes via populate_cache)
            self._preview_cache[cache_key] = result
            print(f"[@navigation_executor:get_navigation_preview] Cached preview for {target_node_id}")
            
            return result
            
        except PathfindingError as e:
            # No path found - target node may not exist or be unreachable
            error_message = str(e)
            print(f"[@navigation_executor:get_navigation_preview] ❌ Pathfinding error: {error_message}")
            result = {
                'success': False,
                'error': error_message,
                'tree_id': tree_id,
                'target_node_id': target_node_id,
                'current_node_id': current_node_id,
                'transitions': [],
                'total_transitions': 0,
                'total_actions': 0
            }
            # Don't cache errors
            return result
        
        except UnifiedCacheError as e:
            # Cache missing - this indicates the tree wasn't loaded properly
            print(f"[@navigation_executor:get_navigation_preview] Unified cache missing for tree {tree_id}")
            print(f"[@navigation_executor:get_navigation_preview] This indicates the NavigationEditor didn't load the tree properly")
            result = {
                'success': False,
                'error': f'Navigation tree {tree_id} not loaded. Please reload the NavigationEditor to populate the navigation cache.',
                'tree_id': tree_id,
                'target_node_id': target_node_id,
                'current_node_id': current_node_id,
                'transitions': [],
                'total_transitions': 0,
                'total_actions': 0
            }
            # Don't cache errors
            return result
        
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
    # Note: Core tree management moved to navigation_executor_tree_manager.py for maintainability
    # These wrapper methods maintain backward compatibility with existing code
    # ========================================
    
    def load_navigation_tree(self, userinterface_name: str, team_id: str) -> Dict[str, Any]:
        """Wrapper for tree manager function - maintains backward compatibility"""
        # Use tree manager and store unified_graph in self
        storage = {}
        result = tree_manager_load_navigation_tree(userinterface_name, team_id, storage)
        if 'graph' in storage:
            self.unified_graph = storage['graph']
        return result

    def discover_complete_hierarchy(self, root_tree_id: str, team_id: str) -> List[Dict]:
        """Wrapper for tree manager function - maintains backward compatibility"""
        return tree_manager_discover_complete_hierarchy(root_tree_id, team_id)

    def format_tree_for_hierarchy(self, tree_data: Dict, tree_info: Dict = None, is_root: bool = False) -> Dict:
        """Wrapper for tree manager function - maintains backward compatibility"""
        return tree_manager_format_tree_for_hierarchy(tree_data, tree_info, is_root)

    def build_unified_tree_data(self, hierarchy_data: List[Dict], team_id: str) -> List[Dict]:
        """Wrapper for tree manager function - maintains backward compatibility"""
        return tree_manager_build_unified_tree_data(hierarchy_data, team_id)


    # ========================================
    # NODE AND EDGE FINDING METHODS
    # Note: Core finder methods moved to navigation_executor_helpers.py for maintainability
    # These wrapper methods maintain backward compatibility with existing code
    # ========================================

    def find_node_by_label(self, nodes: List[Dict], label: str) -> Dict:
        """Wrapper for helper function - maintains backward compatibility"""
        return find_node_by_label(nodes, label)

    def find_edges_from_node(self, source_node_id: str, edges: List[Dict]) -> List[Dict]:
        """Wrapper for helper function - maintains backward compatibility"""
        return find_edges_from_node(source_node_id, edges)

    def find_edge_by_target_label(self, source_node_id: str, edges: List[Dict], nodes: List[Dict], target_label: str) -> Dict:
        """Wrapper for helper function - maintains backward compatibility"""
        return find_edge_by_target_label(source_node_id, edges, nodes, target_label)

    def find_edge_with_action_command(self, node_id: str, edges: List[Dict], action_command: str) -> Dict:
        """Wrapper for helper function - maintains backward compatibility"""
        return find_edge_with_action_command(node_id, edges, action_command)

    def get_node_sub_trees_with_actions(self, node_id: str, tree_id: str, team_id: str) -> Dict:
        """Wrapper for helper function - maintains backward compatibility"""
        return get_node_sub_trees_with_actions(node_id, tree_id, team_id)

    def find_action_in_nested_trees(self, source_node_id: str, tree_id: str, nodes: List[Dict], edges: List[Dict], action_command: str, team_id: str) -> Dict:
        """Wrapper for helper function - maintains backward compatibility"""
        return find_action_in_nested_trees(source_node_id, tree_id, nodes, edges, action_command, team_id)

    # ========================================
    # KPI MEASUREMENT METHODS
    # ========================================
    
    def _queue_kpi_measurement(
        self,
        step: Dict[str, Any],
        action_timestamp: float,
        verification_timestamp: float,
        team_id: str,
        userinterface_name: str,
        before_action_screenshot_path: Optional[str] = None,  # ✅ Before action screenshot
        action_screenshot_path: Optional[str] = None,  # After action screenshot
        action_details: Optional[Dict] = None,  # ✅ NEW: Action execution details
        verification_evidence_list: Optional[List[Dict]] = None  # ✅ NEW: Verification evidence
    ):
        """
        Queue KPI measurement for action_set.
        Writes JSON request file for standalone KPI executor service.
        Uses data from unified graph - no database queries needed.
        """
        try:
            print(f"[@navigation_executor:KPI:DEBUG] _queue_kpi_measurement called")
            
            # ✅ Get all data from step (already from unified graph)
            target_node_id = step.get('to_node_id')
            target_tree_id = step.get('to_tree_id')
            edge_id = step.get('edge_id')
            action_set_id = step.get('action_set_id')
            
            print(f"[@navigation_executor:KPI:DEBUG] Step data: node={target_node_id}, tree={target_tree_id}, edge={edge_id}, action_set={action_set_id}")
            
            # Get edge's tree_id
            original_edge_data = step.get('original_edge_data', {})
            edge_tree_id = original_edge_data.get('tree_id', target_tree_id)
            
            if not target_node_id or not target_tree_id or not edge_id or not action_set_id:
                print(f"[@navigation_executor:KPI:DEBUG] ❌ Missing required fields - EARLY RETURN #1")
                return
            
            # Strip _reverse suffix for display (edge_id from graph might have it)
            display_edge_id = edge_id.replace('_reverse', '') if edge_id.endswith('_reverse') else edge_id
            
            # ✅ Get action_set data directly from step (no database query!)
            # Pathfinding already included all edge data in the step
            action_sets = original_edge_data.get('action_sets', [])
            if not action_sets:
                print(f"[@navigation_executor:KPI:DEBUG] ❌ No action_sets in step data for edge '{display_edge_id}' - EARLY RETURN #2")
                print(f"[@navigation_executor] No action_sets in step data for edge '{display_edge_id}' - skipping KPI")
                return
            
            # Find the specific action_set that was executed
            action_set = next((a for a in action_sets if a.get('id') == action_set_id), None)
            if not action_set:
                print(f"[@navigation_executor:KPI:DEBUG] ❌ Action set '{action_set_id}' not found in step - EARLY RETURN #3")
                print(f"[@navigation_executor] Action set '{action_set_id}' not found in step - skipping KPI")
                return
            
            action_set_label = action_set.get('label', action_set_id)
            
            # Get last action's wait time (for KPI scan window when no verification)
            actions = step.get('actions', [])
            last_action_wait_ms = 0
            if actions:
                last_action = actions[-1]
                params = last_action.get('params', {})
                print(f"[@navigation_executor:KPI] Last action command: {last_action.get('command')}")
                print(f"[@navigation_executor:KPI] Last action params: {params}")
                
                # Check for wait_time embedded in action params (e.g., press_key with wait_time)
                if 'wait_time' in params:
                    last_action_wait_ms = int(params['wait_time'])
                    print(f"[@navigation_executor:KPI] Found wait_time in action params: {last_action_wait_ms}ms")
                elif last_action.get('command') == 'wait' and 'duration' in params:
                    last_action_wait_ms = int(params['duration'] * 1000)
                    print(f"[@navigation_executor:KPI] Found wait action with duration: {last_action_wait_ms}ms")
            
            # ✅ Get KPI references directly from action_set or target node verifications
            use_verifications_for_kpi = action_set.get('use_verifications_for_kpi', False)
            
            print(f"[@navigation_executor:KPI:DEBUG] use_verifications_for_kpi={use_verifications_for_kpi}")
            
            if use_verifications_for_kpi:
                # Get target node verifications from unified graph
                if not self.unified_graph:
                    print(f"[@navigation_executor:KPI:DEBUG] ❌ No unified graph loaded - EARLY RETURN #4")
                    print(f"[@navigation_executor] No unified graph loaded - cannot get node verifications for KPI")
                    return
                
                if target_node_id not in self.unified_graph.nodes:
                    print(f"[@navigation_executor:KPI:DEBUG] ❌ Target node {target_node_id} not in graph - EARLY RETURN #5")
                    print(f"[@navigation_executor] Target node {target_node_id} not in graph - cannot get verifications for KPI")
                    return
                
                node_data = self.unified_graph.nodes[target_node_id]
                kpi_references = node_data.get('verifications', [])
            else:
                # Use action_set's kpi_references (default behavior)
                kpi_references = action_set.get('kpi_references', [])
            
            print(f"[@navigation_executor:KPI:DEBUG] Found {len(kpi_references)} KPI references")
            
            # Early exit if no KPI configured
            if not kpi_references:
                print(f"[@navigation_executor:KPI:DEBUG] ❌ No KPI references - EARLY RETURN #6")
                print(f"[@navigation_executor] No KPI configured for action_set '{action_set_label}' - skipping measurement")
                return
            
            # Get capture directory from device (MANDATORY)
            capture_dir = self.device.get_capture_dir('captures')
            if not capture_dir:
                print(f"[@navigation_executor:KPI:DEBUG] ❌ No capture_dir - EARLY RETURN #7")
                print(f"⚠️ [NavigationExecutor] No capture_dir for device {self.device_id} - KPI skipped")
                return
            
            # Get timeout from KPI references (use maximum timeout)
            # KPI references store timeout in SECONDS - convert to milliseconds
            timeout_seconds = max([ref.get('timeout', 5) for ref in kpi_references])
            timeout_ms = int(timeout_seconds * 1000)
            
            # Record edge execution to get execution_result_id
            from shared.src.lib.database.execution_results_db import record_edge_execution
            execution_result_id = record_edge_execution(
                team_id=team_id,
                tree_id=edge_tree_id,  # ✅ Use edge's tree_id (both forward/reverse use same tree)
                edge_id=edge_id,
                host_name=self.host_name,
                device_model=self.device_model,
                device_name=self.device_name,
                success=True,
                execution_time_ms=0,  # Will be updated by KPI measurement
                message="KPI measurement queued",
                action_set_id=step.get('action_set_id')
            )
            
            print(f"[@navigation_executor:KPI:DEBUG] execution_result_id={execution_result_id}")
            
            if not execution_result_id:
                print(f"[@navigation_executor:KPI:DEBUG] ❌ Failed to create execution_result - EARLY RETURN #8")
                print(f"❌ [NavigationExecutor] Failed to create execution_result - KPI skipped")
                return
            
            # Create KPI measurement request data
            request_data = {
                'execution_result_id': execution_result_id,
                'team_id': team_id,
                'capture_dir': capture_dir,
                'action_timestamp': action_timestamp,
                'verification_timestamp': verification_timestamp,
                'kpi_references': kpi_references,
                'timeout_ms': timeout_ms,
                'device_id': self.device_id,
                'device_model': self.device_model,
                'userinterface_name': userinterface_name,  # MANDATORY for reference resolution
                'last_action_wait_ms': last_action_wait_ms,
                # Extended metadata for report
                'host_name': self.host_name,
                'device_name': self.device_name,
                'tree_id': edge_tree_id,
                'action_set_id': step.get('action_set_id'),
                'from_node_label': step.get('from_node_label'),
                'to_node_label': step.get('to_node_label'),
                'last_action': step.get('last_action'),  # Last action pressed
                'before_action_screenshot_path': before_action_screenshot_path,  # ✅ Before screenshot
                'action_screenshot_path': action_screenshot_path,  # After screenshot
                'action_details': action_details or {},  # ✅ NEW: Action execution details
                'verification_evidence_list': verification_evidence_list or []  # ✅ NEW: Verification evidence
            }
            
            # Write to JSON file queue for standalone KPI executor service (atomic write for inotify)
            kpi_queue_dir = '/tmp/kpi_queue'
            os.makedirs(kpi_queue_dir, exist_ok=True)
            
            request_id = str(uuid.uuid4())
            temp_file = os.path.join(kpi_queue_dir, f'kpi_request_{request_id}.json.tmp')
            final_file = os.path.join(kpi_queue_dir, f'kpi_request_{request_id}.json')
            
            # Atomic write: write to .tmp, then rename (triggers inotify IN_MOVED_TO)
            with open(temp_file, 'w') as f:
                json.dump(request_data, f, indent=2)
            os.rename(temp_file, final_file)
            
            print(f"📊 [NavigationExecutor] KPI queued for {step.get('to_node_label')} ({len(kpi_references)} refs, {timeout_ms}ms timeout)")
            print(f"📝 [NavigationExecutor] KPI request file: {os.path.basename(final_file)}")
        
        except ValueError as e:
            # Validation errors from KPIMeasurementRequest - log and skip
            print(f"❌ [NavigationExecutor] KPI validation failed: {e}")
        except Exception as e:
            # Unexpected errors - log and skip
            print(f"❌ [NavigationExecutor] KPI queue error: {e}")
    
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
    
    def get_node_id(self, node_label: str, tree_id: str = None, team_id: str = None) -> str:
        """
        Get node_id by label using loaded unified graph
        
        Args:
            node_label: Label to search for
            tree_id: Optional tree ID for auto-sync if graph not loaded
            team_id: Optional team ID for auto-sync if graph not loaded
            
        Returns:
            Node ID matching the label
        """
        # 🔄 AUTO-SYNC: Try to sync from cache if graph not loaded
        if not self.unified_graph and tree_id and team_id:
            from shared.src.lib.utils.navigation_cache import get_cached_unified_graph
            cached_graph = get_cached_unified_graph(tree_id, team_id)
            if cached_graph:
                self.unified_graph = cached_graph
                print(f"[@navigation_executor:get_node_id] ✅ Auto-synced unified_graph from cache ({len(cached_graph.nodes)} nodes)")
        
        if not self.unified_graph:
            raise ValueError("Unified graph not loaded - call load_navigation_tree() first or provide tree_id and team_id")
        
        for node_id, node_data in self.unified_graph.nodes(data=True):
            if node_data.get('label') == node_label:
                return node_id
        raise ValueError(f"Node with label '{node_label}' not found in navigation graph")
    
    def get_node_label(self, node_id: str, tree_id: str = None, team_id: str = None) -> str:
        """
        Find node label by node_id using loaded unified graph
        
        Args:
            node_id: Node ID to search for
            tree_id: Optional tree ID for auto-sync if graph not loaded
            team_id: Optional team ID for auto-sync if graph not loaded
            
        Returns:
            Node label
        """
        # 🔄 AUTO-SYNC: Try to sync from cache if graph not loaded
        if not self.unified_graph and tree_id and team_id:
            from shared.src.lib.utils.navigation_cache import get_cached_unified_graph
            cached_graph = get_cached_unified_graph(tree_id, team_id)
            if cached_graph:
                self.unified_graph = cached_graph
                print(f"[@navigation_executor:get_node_label] ✅ Auto-synced unified_graph from cache ({len(cached_graph.nodes)} nodes)")
        
        if not self.unified_graph:
            raise ValueError("Unified graph not loaded - call load_navigation_tree() first or provide tree_id and team_id")
        
        if node_id in self.unified_graph.nodes:
            node_data = self.unified_graph.nodes[node_id]
            return node_data.get('label')  # Fallback to node_id if no label
        
        raise ValueError(f"Node with id '{node_id}' not found in navigation graph")
    
    async def _try_conditional_edge_siblings(
        self,
        step: Dict,
        from_node_id: str,
        expected_target_node_id: str,
        target_node_id: str,
        userinterface_name: str,
        team_id: str,
        tree_id: str,
        context: Any,
        image_source_url: str,
        max_attempts: int = 3
    ) -> Dict[str, Any]:
        """
        Try verifying sibling edges (conditional edges with same action_set_id).
        
        When a verification fails after successful action execution, this tries to verify
        alternative target nodes that share the same action (same action_set_id from same source).
        
        Args:
            step: The failed step dict
            from_node_id: Source node ID
            expected_target_node_id: The target we expected but failed to verify
            target_node_id: Final destination node ID
            userinterface_name: UI name
            team_id: Team ID
            tree_id: Tree ID
            context: Execution context
            image_source_url: Screenshot source
            max_attempts: Max sibling attempts (default 3)
            
        Returns:
            Dict with success=True and actual_node_id if found, or success=False
        """
        print(f"[@navigation_executor:_try_conditional_edge_siblings] Checking for sibling edges from {from_node_id}")
        
        # Get unified graph to find sibling edges
        if not self.unified_graph:
            return {'success': False, 'error': 'No unified graph loaded'}
        
        # Get the edge data for the failed transition
        if not self.unified_graph.has_edge(from_node_id, expected_target_node_id):
            print(f"[@navigation_executor:_try_conditional_edge_siblings] Edge not found in graph")
            return {'success': False, 'error': 'Edge not found'}
        
        failed_edge_data = self.unified_graph.edges[from_node_id, expected_target_node_id]
        
        # ✅ Use pre-computed sibling list from graph (stored during graph creation)
        sibling_node_ids = failed_edge_data.get('sibling_node_ids', [])
        
        if not sibling_node_ids:
            print(f"[@navigation_executor:_try_conditional_edge_siblings] ⚠️ No pre-computed siblings found for this edge")
            return {'success': False, 'error': 'No conditional siblings'}
        
        print(f"[@navigation_executor:_try_conditional_edge_siblings] Found {len(sibling_node_ids)} pre-computed sibling(s)")
        
        # Build sibling edges list with labels
        sibling_edges = []
        for sibling_node_id in sibling_node_ids:
            sibling_node_data = self.unified_graph.nodes.get(sibling_node_id, {})
            sibling_label = sibling_node_data.get('label', sibling_node_id)
            sibling_edges.append({
                'target_node_id': sibling_node_id,
                'target_label': sibling_label,
                'edge_data': self.unified_graph.edges.get((from_node_id, sibling_node_id), {})
            })
            print(f"[@navigation_executor:_try_conditional_edge_siblings] Sibling: {sibling_label} ({sibling_node_id})")
        
        # Try verifying each sibling (max attempts)
        attempts = 0
        for sibling in sibling_edges:
            if attempts >= max_attempts:
                print(f"[@navigation_executor:_try_conditional_edge_siblings] Max attempts ({max_attempts}) reached")
                break
            
            attempts += 1
            sibling_node_id = sibling['target_node_id']
            sibling_label = sibling['target_label']
            
            print(f"[@navigation_executor:_try_conditional_edge_siblings] Attempt {attempts}/{max_attempts}: Verifying {sibling_label} ({sibling_node_id})")
            
            # Verify sibling node
            verification_result = await self.device.verification_executor.verify_node(
                node_id=sibling_node_id,
                userinterface_name=userinterface_name,
                team_id=team_id,
                tree_id=tree_id,
                image_source_url=image_source_url
            )
            
            if verification_result.get('success'):
                print(f"[@navigation_executor:_try_conditional_edge_siblings] ✅ Verification passed for {sibling_label}")
                return {
                    'success': True,
                    'actual_node_id': sibling_node_id,
                    'actual_node_label': sibling_label,
                    'attempts': attempts
                }
            else:
                print(f"[@navigation_executor:_try_conditional_edge_siblings] ❌ Verification failed for {sibling_label}")
        
        return {'success': False, 'error': f'All {attempts} sibling verification(s) failed'}
    
    def _find_recovery_path(
        self,
        current_node_id: str,
        target_node_id: str,
        tree_id: str,
        team_id: str,
        visited_nodes: set = None
    ) -> Optional[List[Dict]]:
        """
        Find recovery path from current position to target after conditional edge recovery.
        
        Args:
            current_node_id: Where we actually landed
            target_node_id: Where we want to go
            tree_id: Tree ID
            team_id: Team ID
            visited_nodes: Set of already visited nodes to prevent loops
            
        Returns:
            List of navigation steps or None if no path found
        """
        if visited_nodes is None:
            visited_nodes = set()
        
        # Prevent infinite loops
        if current_node_id in visited_nodes:
            print(f"[@navigation_executor:_find_recovery_path] Loop detected - {current_node_id} already visited")
            return None
        
        visited_nodes.add(current_node_id)
        
        try:
            # Use pathfinding to find route from current to target
            recovery_path = find_shortest_path(
                tree_id=tree_id,
                target_node_id=target_node_id,
                team_id=team_id,
                start_node_id=current_node_id
            )
            
            if recovery_path:
                print(f"[@navigation_executor:_find_recovery_path] Found path with {len(recovery_path)} steps")
                return recovery_path
            else:
                print(f"[@navigation_executor:_find_recovery_path] No path found")
                return None
                
        except Exception as e:
            print(f"[@navigation_executor:_find_recovery_path] Error finding path: {e}")
            return None
    
    def update_current_position(self, node_id: str, tree_id: str = None, node_label: str = None) -> Dict[str, Any]:
        """Update current navigation position for this device"""
        nav_context = self.device.navigation_context
        
        # Clear verification timestamp if position changed
        old_position = nav_context.get('current_node_id')
        if old_position != node_id:
            nav_context['last_verified_timestamp'] = 0
        
        nav_context['current_node_id'] = node_id
        nav_context['current_tree_id'] = tree_id
        nav_context['current_node_label'] = node_label
        # Track when position was set for staleness checks
        nav_context['position_timestamp'] = time.time()
        
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
        nav_context['position_timestamp'] = 0
        nav_context['last_verified_timestamp'] = 0
        
        print(f"[@navigation_executor] Cleared position for {self.device_id} (was: {old_position['node_id']})")
        
        return {
            'success': True,
            'device_id': self.device_id,
            'previous_position': old_position,
            'current_position': None
        }
