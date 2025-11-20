"""
AI Exploration Executor - Device-bound singleton for exploration management

Architecture pattern: Same as NavigationExecutor
- One instance per device (created during device initialization)
- Persistent state across requests (no global session dict)
- Direct access to device controllers (av, remote, verification)
"""

import time
import threading
from uuid import uuid4
from datetime import datetime, timezone
from typing import Dict, Optional, Any

from backend_host.src.services.ai_exploration.exploration_engine import ExplorationEngine
from backend_host.src.services.ai_exploration.exploration_context import ExplorationContext, create_exploration_context
from backend_host.src.services.ai_exploration.node_generator import NodeGenerator
from shared.src.lib.database.navigation_trees_db import (
    save_node,
    save_edge,
    get_node_by_id,
    get_edge_by_id,
    delete_node,
    delete_edge
)


class ExplorationExecutor:
    """
    Device-bound exploration executor (singleton per device).
    Manages AI exploration state and orchestrates ExplorationEngine.
    
    CRITICAL: Do not create instances directly! Use device.exploration_executor instead.
    Each device has a singleton ExplorationExecutor that preserves exploration state.
    """
    
    @classmethod
    def get_for_device(cls, device):
        """
        Factory method to get the device's existing ExplorationExecutor.
        
        RECOMMENDED: Use device.exploration_executor directly instead.
        
        Args:
            device: Device instance
            
        Returns:
            The device's existing ExplorationExecutor instance
            
        Raises:
            ValueError: If device doesn't have exploration_executor
        """
        if not hasattr(device, 'exploration_executor') or not device.exploration_executor:
            raise ValueError(f"Device {device.device_id} does not have ExplorationExecutor. "
                           "ExplorationExecutors are created during device initialization.")
        return device.exploration_executor
    
    def __init__(self, device, _from_device_init: bool = False):
        """Initialize ExplorationExecutor (should only be called during device init)"""
        # Validate required parameters
        if not device:
            raise ValueError("Device instance is required")
        if not device.host_name:
            raise ValueError("Device must have host_name")
        if not device.device_id:
            raise ValueError("Device must have device_id")
        
        # Warn if creating instance outside of device initialization
        if not _from_device_init:
            import traceback
            print(f"⚠️ [ExplorationExecutor] WARNING: Creating new ExplorationExecutor for {device.device_id}")
            print(f"⚠️ [ExplorationExecutor] This may cause state loss! Use device.exploration_executor instead.")
            print(f"⚠️ [ExplorationExecutor] Call stack:")
            for line in traceback.format_stack()[-3:-1]:
                print(f"⚠️ [ExplorationExecutor]   {line.strip()}")
        
        # Store device reference
        self.device = device
        self.host_name = device.host_name
        self.device_id = device.device_id
        self.device_model = device.device_model
        
        # Persistent exploration state (replaces global _exploration_sessions dict)
        self.current_exploration_id: Optional[str] = None
        self.exploration_engine: Optional[ExplorationEngine] = None
        
        # ✅ NEW v2.0: Context instance
        self.context: Optional[ExplorationContext] = None
        
        self.exploration_state: Dict[str, Any] = {
            'status': 'idle',  # idle, exploring, awaiting_approval, structure_created, validating, validation_complete
            'phase': None,  # analysis, structure_creation, validation
            'tree_id': None,
            'team_id': None,
            'userinterface_name': None,
            'current_step': '',
            'progress': {
                'total_screens_found': 0,
                'screens_analyzed': 0,
                'nodes_proposed': 0,
                'edges_proposed': 0
            },
            'current_analysis': {
                'screen_name': '',
                'elements_found': [],
                'reasoning': '',
                'screenshot': None
            },
            'exploration_plan': None,
            'items_to_validate': [],
            'current_validation_index': 0,
            'target_to_node_map': {},
            'home_id': None,
            'nodes_created': [],
            'edges_created': [],
            'started_at': None,
            'completed_at': None,
            'error': None
        }
        
        # Thread lock for concurrent access
        self._lock = threading.Lock()
        
        print(f"[@ExplorationExecutor] Initialized for device {device.device_id}")
    
    def start_exploration(self, tree_id: str, userinterface_name: str, team_id: str, original_prompt: str = "") -> Dict[str, Any]:
        """
        Start AI exploration (Phase 0+1: Strategy Detection + Analysis)
        
        v2.0: Now accepts original_prompt for context-aware execution
        
        Args:
            tree_id: Navigation tree ID
            userinterface_name: User interface name
            team_id: Team ID
            original_prompt: User's goal (NEW in v2.0)
            
        Returns:
            {
                'success': True,
                'exploration_id': 'uuid',
                'message': 'Exploration started'
            }
        """
        with self._lock:
            # Reset state for new exploration
            exploration_id = str(uuid4())
            self.current_exploration_id = exploration_id
            
            # ✅ NEW v2.0: Create context
            self.context = create_exploration_context(
                original_prompt=original_prompt or f"Explore {userinterface_name}",
                tree_id=tree_id,
                userinterface_name=userinterface_name,
                device_model=self.device_model,
                device_id=self.device_id,
                host_name=self.host_name,
                team_id=team_id
            )
            
            # Reset exploration state (keep for compatibility)
            self.exploration_state = {
                'status': 'starting',
                'phase': 'analysis',
                'tree_id': tree_id,
                'team_id': team_id,
                'userinterface_name': userinterface_name,
                'current_step': 'Initializing exploration...',
                'progress': {
                    'total_screens_found': 0,
                    'screens_analyzed': 0,
                    'nodes_proposed': 0,
                    'edges_proposed': 0
                },
                'current_analysis': {
                    'screen_name': '',
                    'elements_found': [],
                    'reasoning': '',
                    'screenshot': None
                },
                'exploration_plan': None,
                'items_to_validate': [],
                'current_validation_index': 0,
                'target_to_node_map': {},
                'home_id': None,
                'nodes_created': [],
                'edges_created': [],
                'started_at': datetime.now(timezone.utc).isoformat(),
                'completed_at': None,
                'error': None
            }
            
            print(f"[@ExplorationExecutor:start_exploration] Starting exploration {exploration_id}")
            print(f"  Tree: {tree_id}")
            print(f"  Device: {self.device_model} ({self.device_id})")
            print(f"  UI: {userinterface_name}")
            print(f"  Depth: FIXED at 2 levels")
        
        # Start exploration in background thread
        def run_exploration():
            try:
                # Update state (acquire lock briefly)
                with self._lock:
                    self.exploration_state['status'] = 'exploring'
                    self.exploration_state['current_step'] = 'Capturing initial screenshot...'
                
                # Create exploration engine with callbacks
                def update_screenshot(screenshot_path: str):
                    """Convert screenshot path to URL"""
                    try:
                        from shared.src.lib.utils.build_url_utils import buildHostImageUrl
                        
                        # Use self.device.host directly (no Flask context needed!)
                        host_dict = {
                            'host_name': self.host_name,
                            'host_ip': getattr(self.device, 'host_ip', 'localhost'),
                            'host_port': getattr(self.device, 'host_port', 6109)
                        }
                        screenshot_url = buildHostImageUrl(host_dict, screenshot_path)
                        
                        with self._lock:
                            self.exploration_state['current_analysis']['screenshot'] = screenshot_url
                    except Exception as e:
                        print(f"[@ExplorationExecutor] Screenshot URL conversion failed: {e}")
                        import traceback
                        traceback.print_exc()
                
                def update_progress(step: str, screenshot: str = None, analysis: dict = None):
                    """Update progress (avoid nested lock acquisition)."""
                    screenshot_to_update = None
                    with self._lock:
                        self.exploration_state['current_step'] = step
                        
                        if analysis:
                            self.exploration_state['current_analysis'].update({
                                'screen_name': analysis.get('screen_name', ''),
                                'elements_found': analysis.get('elements_found', []),
                                'reasoning': analysis.get('reasoning', '')
                            })
                        
                        # Defer screenshot update outside the lock to avoid deadlock
                        if screenshot:
                            screenshot_to_update = screenshot
                    
                    if screenshot_to_update:
                        update_screenshot(screenshot_to_update)
                
                # Create or reuse engine
                self.exploration_engine = ExplorationEngine(
                    tree_id=tree_id,
                    device=self.device,  # Pass device directly (no Flask context needed!)
                    team_id=team_id,
                    userinterface_name=userinterface_name,
                    screenshot_callback=update_screenshot,
                    progress_callback=update_progress
                )
                
                # Run Phase 1: Analysis
                result = self.exploration_engine.analyze_and_plan()
                
                with self._lock:
                    if result['success']:
                        self.exploration_state['status'] = 'awaiting_approval'
                        self.exploration_state['phase'] = 'analysis_complete'
                        self.exploration_state['current_step'] = 'Analysis complete. Review the plan below.'
                        self.exploration_state['exploration_plan'] = result['plan']
                        
                        # Preserve screenshot
                        existing_screenshot = self.exploration_state['current_analysis'].get('screenshot')
                        self.exploration_state['current_analysis'] = {
                            'screen_name': result['plan'].get('screen_name', 'Initial Screen'),
                            'elements_found': result['plan'].get('items', []),
                            'reasoning': result['plan'].get('reasoning', ''),
                            'screenshot': existing_screenshot
                        }
                    else:
                        error_msg = result.get('error', 'Failed to analyze screen')
                        print(f"[@ExplorationExecutor:run_exploration] ❌ EXPLORATION FAILED: {error_msg}")
                        self.exploration_state['status'] = 'failed'
                        self.exploration_state['error'] = error_msg
                        self.exploration_state['current_step'] = f"❌ Failed: {error_msg}"
                    
                    self.exploration_state['completed_at'] = datetime.now(timezone.utc).isoformat()
                
            except Exception as e:
                print(f"[@ExplorationExecutor:run_exploration] Error: {e}")
                import traceback
                traceback.print_exc()
                
                with self._lock:
                    self.exploration_state['status'] = 'failed'
                    self.exploration_state['error'] = str(e)
                    self.exploration_state['current_step'] = f"Error: {str(e)}"
                    self.exploration_state['completed_at'] = datetime.now(timezone.utc).isoformat()
        
        # Start thread
        thread = threading.Thread(target=run_exploration, daemon=True)
        thread.start()
        
        return {
            'success': True,
            'exploration_id': exploration_id,
            'host_name': self.host_name,
            'message': 'Exploration started'
        }
    
    def get_exploration_status(self) -> Dict[str, Any]:
        """
        Get current exploration status (polling endpoint)
        
        Returns:
            {
                'success': True,
                'exploration_id': 'uuid',
                'status': 'exploring',
                'current_step': '...',
                'progress': {...},
                'exploration_plan': {...}
            }
        """
        with self._lock:
            if not self.current_exploration_id:
                return {
                    'success': False,
                    'error': 'No active exploration'
                }
            
            state = self.exploration_state.copy()
            
            return {
                'success': True,
                'exploration_id': self.current_exploration_id,
                'status': state['status'],
                'phase': state.get('phase'),
                'current_step': state['current_step'],
                'progress': state['progress'],
                'current_analysis': state['current_analysis'],
                'exploration_plan': state.get('exploration_plan'),
                'error': state.get('error')
            }
    
    def continue_exploration(self, team_id: str) -> Dict[str, Any]:
        """
        Phase 2a: Create all nodes and edges structure (instant)
        Uses BATCH SAVE for efficiency.
        
        Returns:
            {
                'success': True,
                'nodes_created': 11,
                'edges_created': 10
            }
        """
        with self._lock:
            if not self.current_exploration_id:
                return {'success': False, 'error': 'No active exploration'}
            
            if self.exploration_state['status'] != 'awaiting_approval':
                return {
                    'success': False,
                    'error': f"Cannot continue: status is {self.exploration_state['status']}"
                }
            
            tree_id = self.exploration_state['tree_id']
            items = self.exploration_state['exploration_plan']['items']
            
            print(f"[@ExplorationExecutor:continue_exploration] Creating structure for {self.current_exploration_id}")
            
            node_gen = NodeGenerator(tree_id, team_id)
            
            # Home node should already exist - userinterfaces have home by default
            home_node_result = get_node_by_id(tree_id, 'home', team_id)
            if not (home_node_result.get('success') and home_node_result.get('node')):
                return {'success': False, 'error': 'Home node does not exist. Userinterface should have home node by default.'}
            
            home_id = home_node_result['node']['node_id']
            nodes_created = []
            print(f"  ♻️  Using existing '{home_id}' node")
            
            # ✅ BATCH COLLECTION: Collect all nodes and edges before saving
            nodes_to_save = []
            edges_to_save = []
            
            # Create child nodes and edges
            for idx, item in enumerate(items):
                node_name_clean = node_gen.target_to_node_name(item)
                
                if node_name_clean == 'home' or 'home' in node_name_clean:
                    print(f"  ⏭️  Skipping '{node_name_clean}' (home indicator)")
                    continue
                
                node_name = f"{node_name_clean}_temp"
                position_x = 250 + (idx % 5) * 200
                position_y = 300 + (idx // 5) * 150
                
                # Create node data
                node_data = node_gen.create_node_data(
                    node_name=node_name,
                    position={'x': position_x, 'y': position_y},
                    ai_analysis={
                        'suggested_name': node_name_clean,
                        'screen_type': 'screen',
                        'reasoning': f'Navigation target: {item}'
                    },
                    node_type='screen'
                )
                nodes_to_save.append(node_data)
                nodes_created.append(node_name)
                
                # Store mapping
                self.exploration_state['target_to_node_map'][item] = node_name
                
                # ✅ Create edge with predicted actions (use element_id for frontend compatibility)
                forward_actions = [{
                    "command": "click_element",
                    "params": {"element_id": item},  # Frontend expects "element_id", not "text"
                    "delay": 2000
                }]
                
                reverse_actions = [{
                    "command": "press_key",
                    "params": {"key": "BACK"},
                    "delay": 2000
                }]
                
                edge_data = node_gen.create_edge_data(
                    source=home_id,
                    target=node_name,
                    actions=forward_actions,
                    reverse_actions=reverse_actions,
                    label=item
                )
                edges_to_save.append(edge_data)
            
            # ✅ BATCH SAVE: Save all nodes at once
            print(f"  💾 Batch saving {len(nodes_to_save)} nodes...")
            for node_data in nodes_to_save:
                node_result = save_node(tree_id, node_data, team_id)
                if node_result['success']:
                    print(f"  ✅ Created node: {node_data['node_id']}")
                else:
                    print(f"  ❌ Failed to create node {node_data['node_id']}: {node_result.get('error')}")
            
            # ✅ BATCH SAVE: Save all edges at once
            print(f"  💾 Batch saving {len(edges_to_save)} edges...")
            edges_created = []
            for edge_data in edges_to_save:
                edge_result = save_edge(tree_id, edge_data, team_id)
                if edge_result['success']:
                    edges_created.append(edge_data['edge_id'])
                    print(f"  ✅ Created edge: {edge_data['source_node_id']} → {edge_data['target_node_id']}")
                else:
                    print(f"  ❌ Failed to create edge {edge_data['edge_id']}: {edge_result.get('error')}")
            
            # Update state
            self.exploration_state['status'] = 'structure_created'
            self.exploration_state['nodes_created'] = nodes_created
            self.exploration_state['edges_created'] = edges_created
            self.exploration_state['home_id'] = home_id
            self.exploration_state['current_step'] = f'Created {len(nodes_created)} nodes and {len(edges_created)} edges. Ready to validate.'
            self.exploration_state['items_to_validate'] = items
            self.exploration_state['current_validation_index'] = 0
            
            return {
                'success': True,
                'nodes_created': len(nodes_created),
                'edges_created': len(edges_created),
                'message': 'Structure created successfully',
                'node_ids': nodes_created,
                'edge_ids': edges_created
            }
    
    def start_validation(self) -> Dict[str, Any]:
        """
        Phase 2b: Start validation process
        
        Returns:
            {
                'success': True,
                'total_items': 10
            }
        """
        with self._lock:
            if self.exploration_state['status'] != 'structure_created':
                return {
                    'success': False,
                    'error': f"Cannot start validation: status is {self.exploration_state['status']}"
                }
            
            self.exploration_state['status'] = 'awaiting_validation'
            self.exploration_state['current_validation_index'] = 0
            
            return {
                'success': True,
                'message': 'Ready to start validation',
                'total_items': len(self.exploration_state['items_to_validate'])
            }
    
    def finalize_structure(self) -> Dict[str, Any]:
        """
        Finalize structure: Rename all _temp nodes/edges to permanent
        
        Returns:
            {
                'success': True,
                'nodes_renamed': 5,
                'edges_renamed': 4
            }
        """
        with self._lock:
            if not self.current_exploration_id:
                return {'success': False, 'error': 'No active exploration'}
            
            tree_id = self.exploration_state['tree_id']
            team_id = self.exploration_state['team_id']
            
            print(f"[@ExplorationExecutor:finalize_structure] Renaming _temp nodes/edges for {self.current_exploration_id}")
            
            # Get all nodes and edges from tree
            from backend_host.src.services.navigation.crud import get_tree_nodes, get_tree_edges, update_node, update_edge
            
            nodes_result = get_tree_nodes(tree_id, team_id)
            edges_result = get_tree_edges(tree_id, team_id)
            
            if not nodes_result.get('success') or not edges_result.get('success'):
                return {'success': False, 'error': 'Failed to get tree data'}
            
            nodes = nodes_result.get('nodes', [])
            edges = edges_result.get('edges', [])
            
            nodes_renamed = 0
            edges_renamed = 0
            
            # Rename nodes: remove _temp suffix
            for node in nodes:
                node_id = node.get('node_id', '')
                if node_id.endswith('_temp'):
                    new_node_id = node_id.replace('_temp', '')
                    node['node_id'] = new_node_id
                    
                    result = update_node(tree_id, node_id, node, team_id)
                    if result.get('success'):
                        nodes_renamed += 1
                        print(f"  ✅ Renamed node: {node_id} → {new_node_id}")
                    else:
                        print(f"  ❌ Failed to rename node: {node_id}")
            
            # Rename edges: remove _temp suffix from edge_id, source, target
            for edge in edges:
                edge_id = edge.get('edge_id', '')
                source = edge.get('source', '')
                target = edge.get('target', '')
                
                if '_temp' in edge_id or '_temp' in source or '_temp' in target:
                    new_edge_id = edge_id.replace('_temp', '')
                    new_source = source.replace('_temp', '')
                    new_target = target.replace('_temp', '')
                    
                    edge['edge_id'] = new_edge_id
                    edge['source'] = new_source
                    edge['target'] = new_target
                    
                    result = update_edge(tree_id, edge_id, edge, team_id)
                    if result.get('success'):
                        edges_renamed += 1
                        print(f"  ✅ Renamed edge: {edge_id} → {new_edge_id}")
                    else:
                        print(f"  ❌ Failed to rename edge: {edge_id}")
            
            # Update state
            self.exploration_state['status'] = 'finalized'
            self.exploration_state['current_step'] = f'Finalized: {nodes_renamed} nodes and {edges_renamed} edges renamed'
            
            return {
                'success': True,
                'nodes_renamed': nodes_renamed,
                'edges_renamed': edges_renamed,
                'message': 'Structure finalized successfully'
            }
    
    def validate_next_item(self) -> Dict[str, Any]:
        """
        Phase 2b: Validate ONE edge by testing click → back
        
        Returns:
            {
                'success': True,
                'item': 'En',
                'click_result': 'success',
                'back_result': 'success',
                'has_more_items': True,
                'progress': {...}
            }
        """
        with self._lock:
            if self.exploration_state['status'] not in ['awaiting_validation', 'validating']:
                return {
                    'success': False,
                    'error': f"Cannot validate: status is {self.exploration_state['status']}"
                }
            
            tree_id = self.exploration_state['tree_id']
            team_id = self.exploration_state['team_id']
            current_index = self.exploration_state['current_validation_index']
            items_to_validate = self.exploration_state['items_to_validate']
            
            if current_index >= len(items_to_validate):
                self.exploration_state['status'] = 'validation_complete'
                return {
                    'success': True,
                    'message': 'All items validated',
                    'has_more_items': False
                }
            
            current_item = items_to_validate[current_index]
            target_to_node_map = self.exploration_state['target_to_node_map']
            node_name = target_to_node_map.get(current_item)
            
            if not node_name:
                # Fallback
                node_gen = NodeGenerator(tree_id, team_id)
                node_name_clean = node_gen.target_to_node_name(current_item)
                node_name = f"{node_name_clean}_temp"
            
            # Skip home
            if 'home' in node_name.lower() and node_name != 'home_temp':
                self.exploration_state['current_validation_index'] = current_index + 1
                return self.validate_next_item()
            
            print(f"[@ExplorationExecutor:validate_next_item] Validating {current_index + 1}/{len(items_to_validate)}")
            print(f"  Target: {current_item} → {node_name}")
            
            self.exploration_state['status'] = 'validating'
            self.exploration_state['current_step'] = f"Validating {current_index + 1}/{len(items_to_validate)}: {current_item}"
        
        # Get controller from engine
        controller = self.exploration_engine.controller
        home_indicator = self.exploration_state['exploration_plan']['items'][0]
        
        # Perform validation
        click_result = 'failed'
        back_result = 'failed'
        screenshot_url = None
        
        # 1. Click element
        try:
            result = controller.click_element(current_item)
            click_success = result if isinstance(result, bool) else result.get('success', False)
            click_result = 'success' if click_success else 'failed'
            print(f"    {'✅' if click_success else '❌'} Click {click_result}")
            time.sleep(5)
            
            # 1.5. Capture screenshot
            if click_success:
                try:
                    av_controller = self.device._get_controller('av')
                    if av_controller:
                        node_name_clean = node_name.replace('_temp', '')
                        sanitized_name = node_name_clean.replace(' ', '_')
                        local_path = av_controller.save_screenshot(sanitized_name)
                        
                        if local_path:
                            from shared.src.lib.utils.cloudflare_utils import upload_navigation_screenshot
                            r2_filename = f"{sanitized_name}.jpg"
                            userinterface_name = self.exploration_state['userinterface_name']
                            upload_result = upload_navigation_screenshot(local_path, userinterface_name, r2_filename)
                            
                            if upload_result.get('success'):
                                screenshot_url = upload_result.get('url')
                                print(f"    📸 Screenshot: {screenshot_url}")
                except Exception as e:
                    print(f"    ⚠️ Screenshot failed: {e}")
        except Exception as e:
            print(f"    ❌ Click failed: {e}")
        
        # 2. Press BACK (with double-back fallback)
        if click_result == 'success':
            try:
                # Select verification controller based on device model
                device_model = self.device_model.lower()
                verifier = None
                
                if 'mobile' in device_model:
                    # Mobile: Use ADB verification
                    for v in self.device.get_controllers('verification'):
                        if getattr(v, 'verification_type', None) == 'adb':
                            verifier = v
                            print(f"    📱 Using ADB verification for mobile device")
                            break
                elif 'host' in device_model:
                    # Web (host): Use Playwright verification
                    for v in self.device.get_controllers('verification'):
                        if getattr(v, 'verification_type', None) == 'web':
                            verifier = v
                            print(f"    🌐 Using Playwright verification for web device")
                            break
                else:
                    # TV/STB: Image verification (not supported in AI exploration)
                    print(f"    ⚠️ Device model '{device_model}' requires image verification - not supported in AI exploration")
                
                controller.press_key('BACK')
                time.sleep(5)
                
                print(f"    🔍 Verifying return to home: {home_indicator}")
                
                back_success = False
                if verifier:
                    # Handle async (Playwright) vs sync (ADB) verifications
                    import inspect
                    if inspect.iscoroutinefunction(verifier.waitForElementToAppear):
                        import asyncio
                        success, message, details = asyncio.run(verifier.waitForElementToAppear(
                            search_term=home_indicator,
                            timeout=3.0
                        ))
                    else:
                        success, message, details = verifier.waitForElementToAppear(
                            search_term=home_indicator,
                            timeout=3.0
                        )
                    back_success = success
                    print(f"    {'✅' if back_success else '❌'} Back (1st) {('success' if back_success else 'failed')}: {message}")
                else:
                    # Fallback if no verifier available
                    print(f"    ⚠️ No verifier available for device model '{device_model}'")
                    back_success = False
                
                # Double-back fallback
                if not back_success:
                    print(f"    🔄 Trying second BACK...")
                    controller.press_key('BACK')
                    time.sleep(5)
                    
                    if verifier:
                        import inspect
                        if inspect.iscoroutinefunction(verifier.waitForElementToAppear):
                            import asyncio
                            success, message, details = asyncio.run(verifier.waitForElementToAppear(
                                search_term=home_indicator,
                                timeout=5.0
                            ))
                        else:
                            success, message, details = verifier.waitForElementToAppear(
                                search_term=home_indicator,
                                timeout=5.0
                            )
                        back_success = success
                        print(f"    {'✅' if back_success else '❌'} Back (2nd) {('success' if back_success else 'failed')}: {message}")
                    else:
                        back_success = False
                
                back_result = 'success' if back_success else 'failed'
                
                # ✅ RECOVERY: If BACK failed, use navigation to return to home
                if not back_success:
                    print(f"    🔄 BACK failed - attempting recovery via navigation goto home...")
                    try:
                        # Use device's navigation executor to go to home
                        nav_result = self.device.navigation_executor.goto_node(
                            tree_id=tree_id,
                            node_id=home_id,
                            team_id=team_id
                        )
                        if nav_result.get('success'):
                            print(f"    ✅ Recovery successful - navigated back to home")
                            # Update back_result to indicate recovery was used
                            back_result = 'success_via_recovery'
                        else:
                            print(f"    ❌ Recovery failed: {nav_result.get('error', 'Unknown error')}")
                    except Exception as recovery_error:
                        print(f"    ❌ Recovery exception: {recovery_error}")
                
            except Exception as e:
                print(f"    ⚠️ Back failed: {e}")
        
        # 3. Update edge with validation results (using action_sets like frontend)
        with self._lock:
            home_id = self.exploration_state['home_id']
            edge_id = f"edge_{home_id}_to_{node_name}_temp"
            
            edge_result = get_edge_by_id(tree_id, edge_id, team_id)
            edge_updated = False
            
            if edge_result['success']:
                edge = edge_result['edge']
                
                # ✅ CORRECT: action_sets[0] = forward (with actions), action_sets[1] = reverse (with actions)
                # NOT: action_sets[0] with reverse_actions - that's wrong!
                action_sets = edge.get('action_sets', [])
                if len(action_sets) >= 2:
                    # Update forward direction (action_sets[0])
                    if action_sets[0].get('actions') and len(action_sets[0]['actions']) > 0:
                        action_sets[0]['actions'][0]['validation_status'] = click_result
                        action_sets[0]['actions'][0]['validated_at'] = time.time()
                        action_sets[0]['actions'][0]['actual_result'] = click_result
                    
                    # ✅ FIX: Update reverse direction (action_sets[1].actions, NOT action_sets[0].reverse_actions)
                    if action_sets[1].get('actions') and len(action_sets[1]['actions']) > 0:
                        action_sets[1]['actions'][0]['validation_status'] = back_result
                        action_sets[1]['actions'][0]['validated_at'] = time.time()
                        action_sets[1]['actions'][0]['actual_result'] = back_result
                    
                    # Save updated edge with correct action_sets structure
                    update_result = save_edge(tree_id, edge, team_id)
                    edge_updated = update_result.get('success', False)
            
            # Move to next
            self.exploration_state['current_validation_index'] = current_index + 1
            has_more = self.exploration_state['current_validation_index'] < len(items_to_validate)
            
            if not has_more:
                self.exploration_state['status'] = 'validation_complete'
            else:
                self.exploration_state['status'] = 'awaiting_validation'
            
            node_name_display = node_name.replace('_temp', '')
            
            return {
                'success': True,
                'item': current_item,
                'node_name': node_name_display,
                'node_id': node_name,
                'click_result': click_result,
                'back_result': back_result,
                'edge_updated': edge_updated,
                'has_more_items': has_more,
                'screenshot_url': screenshot_url,
                'action_sets': {
                    'forward': {
                        'source': home_id,
                        'target': node_name_display,
                        'action': f'click_element("{current_item}")',
                        'result': click_result
                    },
                    'reverse': {
                        'source': node_name_display,
                        'target': home_id,
                        'action': 'press_key(BACK)',
                        'result': back_result
                    }
                },
                'progress': {
                    'current_item': self.exploration_state['current_validation_index'],
                    'total_items': len(items_to_validate)
                }
            }
    
    def approve_generation(self, tree_id: str, approved_nodes: list, approved_edges: list, team_id: str) -> Dict[str, Any]:
        """
        Approve generation - rename all _temp nodes/edges
        
        Returns:
            {
                'success': True,
                'nodes_created': 2,
                'edges_created': 1
            }
        """
        print(f"[@ExplorationExecutor:approve_generation] Approving {len(approved_nodes)} nodes, {len(approved_edges)} edges")
        
        node_generator = NodeGenerator(tree_id, team_id)
        nodes_created = 0
        edges_created = 0
        
        # Rename nodes
        for node_id in approved_nodes:
            node_result = get_node_by_id(tree_id, node_id, team_id)
            if node_result['success']:
                node_data = node_result['node']
                renamed_data = node_generator.rename_node(node_data)
                
                delete_node(tree_id, node_id, team_id)
                save_result = save_node(tree_id, renamed_data, team_id)
                
                if save_result['success']:
                    nodes_created += 1
                    print(f"  ✅ Renamed: {node_id} → {renamed_data['node_id']}")
        
        # Rename edges
        for edge_id in approved_edges:
            edge_result = get_edge_by_id(tree_id, edge_id, team_id)
            if edge_result['success']:
                edge_data = edge_result['edge']
                renamed_data = node_generator.rename_edge(edge_data)
                
                save_result = save_edge(tree_id, renamed_data, team_id)
                if save_result['success']:
                    edges_created += 1
                    print(f"  ✅ Renamed: {edge_id} → {renamed_data['edge_id']}")
        
        # Clean up state
        with self._lock:
            self.current_exploration_id = None
            self.exploration_engine = None
            self.exploration_state['status'] = 'idle'
        
        print(f"[@ExplorationExecutor:approve_generation] ✅ Complete: {nodes_created} nodes, {edges_created} edges")
        
        return {
            'success': True,
            'nodes_created': nodes_created,
            'edges_created': edges_created,
            'message': f'Successfully created {nodes_created} nodes and {edges_created} edges'
        }
    
    def cancel_exploration(self, tree_id: str, team_id: str) -> Dict[str, Any]:
        """
        Cancel exploration - delete all _temp nodes/edges
        
        Returns:
            {
                'success': True,
                'message': 'Exploration cancelled'
            }
        """
        with self._lock:
            nodes_to_delete = self.exploration_state.get('nodes_created', [])
            
            print(f"[@ExplorationExecutor:cancel_exploration] Cancelling exploration")
            
            for node_id in nodes_to_delete:
                delete_node(tree_id, node_id, team_id)
                print(f"  🗑️  Deleted node: {node_id}")
            
            # Reset state
            self.current_exploration_id = None
            self.exploration_engine = None
            self.exploration_state['status'] = 'idle'
            
            print(f"[@ExplorationExecutor:cancel_exploration] ✅ Cancelled")
            
            return {
                'success': True,
                'message': 'Exploration cancelled, temporary nodes deleted'
            }
    
    # ========== NEW v2.0: MCP-FIRST INCREMENTAL METHODS ==========
    
    def execute_phase0(self) -> Dict[str, Any]:
        """
        Execute Phase 0: Strategy detection
        
        NEW in v2.0
        
        Returns:
            {
                'success': True,
                'strategy': str,
                'has_dump_ui': bool,
                'context': dict
            }
        """
        if not self.context:
            return {'success': False, 'error': 'No active exploration'}
        
        # Call engine Phase 0
        self.context = self.exploration_engine.phase0_detect_strategy(self.context)
        
        return {
            'success': True,
            'strategy': self.context.strategy,
            'has_dump_ui': self.context.has_dump_ui,
            'context': self.context.to_dict()
        }
    
    def execute_phase1(self) -> Dict[str, Any]:
        """
        Execute Phase 1: Analyze and plan (with sanitized labels)
        
        NEW in v2.0
        
        Returns:
            {
                'success': True,
                'predicted_items': List[str],  # SANITIZED labels
                'menu_type': str,
                'context': dict
            }
        """
        if not self.context:
            return {'success': False, 'error': 'No active exploration'}
        
        # Call engine Phase 1
        self.context = self.exploration_engine.phase1_analyze_and_plan(self.context)
        
        return {
            'success': True,
            'predicted_items': self.context.predicted_items,  # SANITIZED
            'menu_type': self.context.menu_type,
            'total_items': self.context.total_steps,
            'context': self.context.to_dict()
        }
    
    def execute_phase2_next_item(self) -> Dict[str, Any]:
        """
        Execute Phase 2: Create and test ONE edge incrementally
        
        NEW in v2.0: Incremental approach
        
        Returns:
            {
                'success': bool,
                'item': str,
                'has_more_items': bool,
                'progress': dict
            }
        """
        if not self.context:
            return {'success': False, 'error': 'No active exploration'}
        
        items = self.context.predicted_items
        current_idx = self.context.current_step
        
        if current_idx >= len(items):
            return {
                'success': True,
                'has_more_items': False,
                'message': 'All items completed'
            }
        
        item = items[current_idx]
        
        # Create and test single edge via MCP
        result = self.exploration_engine.phase2_create_single_edge_mcp(item, self.context)
        
        if result['success']:
            self.context.completed_items.append(item)
            self.context.current_step += 1
            self.context.add_step_result(f'create_{item}', result)
            
            return {
                'success': True,
                'item': item,
                'node_created': True,
                'edge_created': True,
                'edge_tested': True,
                'has_more_items': self.context.current_step < len(items),
                'progress': {
                    'current_item': self.context.current_step,
                    'total_items': len(items)
                },
                'context': self.context.to_dict()
            }
        else:
            self.context.failed_items.append({
                'item': item,
                'error': result.get('error')
            })
            self.context.add_step_result(f'create_{item}', result)
            
            return {
                'success': False,
                'item': item,
                'error': result.get('error'),
                'has_more_items': False,  # Stop on failure
                'context': self.context.to_dict()
            }

