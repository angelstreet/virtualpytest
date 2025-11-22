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
from backend_host.src.services.ai_exploration.tv_validation import TVValidationStrategy
from backend_host.src.services.ai_exploration.mobile_validation import MobileValidationStrategy
from shared.src.lib.database.navigation_trees_db import (
    save_node,
    save_nodes_batch,
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
        # Warn if creating instance outside of device initialization
        if not _from_device_init:
            import traceback
            device_id = getattr(device, 'device_id', 'unknown')
            print(f"⚠️ [ExplorationExecutor] WARNING: Creating new ExplorationExecutor for {device_id}")
            print(f"⚠️ [ExplorationExecutor] This may cause state loss! Use device.exploration_executor instead.")
            print(f"⚠️ [ExplorationExecutor] Call stack:")
            for line in traceback.format_stack()[-3:-1]:
                print(f"⚠️ [ExplorationExecutor]   {line.strip()}")
        
        # Store device reference
        self.device = device
        self.host_name = getattr(device, 'host_name', None)
        self.device_id = getattr(device, 'device_id', None)
        self.device_model = getattr(device, 'device_model', None)
        
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
            'node_verification_data': [],
            'node_verification_suggestions': [],
            'started_at': None,
            'completed_at': None,
            'error': None
        }
        
        # Thread lock for concurrent access
        self._lock = threading.Lock()
        
        print(f"[@ExplorationExecutor] Initialized for device {device.device_id}")
    
    # ========== HELPER METHODS (Eliminate Code Duplication) ==========
    
    def _capture_and_upload_screenshot(self, node_name: str) -> Optional[str]:
        """
        Capture screenshot and upload to R2
        
        Used by: TV validation, Mobile validation, verification approval
        Returns: screenshot URL or None
        """
        try:
            # Capture screenshot
            av_controllers = self.device.get_controllers('av')
            av_controller = av_controllers[0] if av_controllers else None
            if not av_controller:
                print(f"    ⚠️ No AV controller available")
                return None
            
            screenshot_path = av_controller.take_screenshot()
            if not screenshot_path:
                print(f"    ⚠️ Screenshot capture failed")
                return None
            
            print(f"    📸 Screenshot captured: {screenshot_path}")
            
            # Upload to R2
            from shared.src.lib.utils.cloudflare_utils import upload_navigation_screenshot
            sanitized_name = node_name.replace(' ', '_').replace('_temp', '')
            r2_filename = f"{sanitized_name}.jpg"
            userinterface_name = self.exploration_state['userinterface_name']
            upload_result = upload_navigation_screenshot(screenshot_path, userinterface_name, r2_filename)
            
            if upload_result.get('success'):
                screenshot_url = upload_result.get('url')
                print(f"    📸 Screenshot uploaded: {screenshot_url}")
                return screenshot_url
            else:
                print(f"    ⚠️ Screenshot upload failed: {upload_result.get('error')}")
                return None
                
        except Exception as e:
            print(f"    ⚠️ Screenshot process failed: {e}")
            return None
    
    def _extract_dump(self, controller, screenshot_path: Optional[str] = None) -> Optional[Dict]:
        """
        Extract UI dump (auto-detects ADB/Web/OCR based on device)
        
        Used by: TV validation, Mobile validation
        Returns: {'elements': [...]} or None
        """
        try:
            # Try ADB/Web dump first
            if hasattr(controller, 'dump_elements') and callable(getattr(controller, 'dump_elements')):
                dump_result = controller.dump_elements()
                
                # Handle async controllers (web)
                import inspect
                if inspect.iscoroutine(dump_result):
                    import asyncio
                    dump_result = asyncio.run(dump_result)
                
                # Normalize dump format (mobile returns tuple, web returns dict)
                if isinstance(dump_result, tuple):
                    # Mobile: (success, elements, error)
                    success, elements, error = dump_result
                    if success and elements:
                        print(f"    📱 ADB Dump: {len(elements)} elements")
                        return {'elements': elements}
                    else:
                        print(f"    ⚠️ ADB Dump failed: {error or 'no elements'}")
                elif isinstance(dump_result, dict):
                    # Web: already dict format
                    element_count = len(dump_result.get('elements', []))
                    print(f"    🌐 Web Dump: {element_count} elements")
                    return dump_result
            
            # Fallback to OCR dump if ADB/Web dump failed AND screenshot available
            if screenshot_path:
                print(f"    📊 Using OCR dump fallback")
                text_controller = None
                for v in self.device.get_controllers('verification'):
                    if getattr(v, 'verification_type', None) == 'text':
                        text_controller = v
                        break
                
                if text_controller:
                    ocr_result = text_controller.extract_ocr_dump(screenshot_path, confidence_threshold=30)
                    
                    if ocr_result.get('success') and ocr_result.get('elements'):
                        print(f"    📊 OCR Dump: {len(ocr_result['elements'])} text elements")
                        return {'elements': ocr_result['elements']}
                    else:
                        print(f"    ⚠️ OCR dump failed or no text found")
                else:
                    print(f"    ⚠️ Text controller not available for OCR")
            
            return None
            
        except Exception as e:
            print(f"    ⚠️ Dump extraction failed: {e}")
            return None
    
    def _capture_screen_data(self, node_name: str, node_label: str, controller) -> tuple[Optional[str], Optional[Dict]]:
        """
        Capture screenshot + dump and store verification data
        
        Combines _capture_and_upload_screenshot + _extract_dump + storage
        Used by: TV validation, Mobile validation
        
        Returns: (screenshot_url, dump_data)
        """
        # Capture and upload screenshot
        screenshot_url = self._capture_and_upload_screenshot(node_name)
        screenshot_path = None
        
        # Get local screenshot path for dump extraction
        if screenshot_url:
            try:
                av_controllers = self.device.get_controllers('av')
                av_controller = av_controllers[0] if av_controllers else None
                if av_controller and hasattr(av_controller, 'last_screenshot_path'):
                    screenshot_path = av_controller.last_screenshot_path
            except:
                pass
        
        # Extract dump
        dump_data = self._extract_dump(controller, screenshot_path)
        
        # Store verification data
        if screenshot_url or dump_data:
            with self._lock:
                if 'node_verification_data' not in self.exploration_state:
                    self.exploration_state['node_verification_data'] = []
                
                self.exploration_state['node_verification_data'].append({
                    'node_id': node_name,
                    'node_label': node_label,
                    'dump': dump_data,
                    'screenshot_url': screenshot_url
                })
            print(f"    ✅ Verification data stored (dump: {dump_data is not None}, screenshot: {screenshot_url is not None})")
        
        return screenshot_url, dump_data
    
    def _navigate_to_home(self) -> Dict[str, Any]:
        """
        Recovery navigation to home node
        
        Used by: Mobile validation recovery
        Returns: Navigation result
        """
        try:
            import asyncio
            tree_id = self.exploration_state['tree_id']
            team_id = self.exploration_state['team_id']
            userinterface_name = self.exploration_state['userinterface_name']
            
            nav_result = asyncio.run(self.device.navigation_executor.execute_navigation(
                tree_id=tree_id,
                userinterface_name=userinterface_name,
                target_node_label='home',
                team_id=team_id
            ))
            
            if nav_result.get('success'):
                print(f"    ✅ Navigation to home successful")
            else:
                print(f"    ❌ Navigation to home failed: {nav_result.get('error')}")
            
            return nav_result
            
        except Exception as e:
            print(f"    ❌ Navigation exception: {e}")
            return {'success': False, 'error': str(e)}
    
    # ========== END HELPER METHODS ==========
    
    def start_exploration(self, tree_id: str, userinterface_name: str, team_id: str, original_prompt: str = "", start_node: str = 'home') -> Dict[str, Any]:
        """
        Start AI exploration (Phase 0+1: Strategy Detection + Analysis)
        
        v2.0: Now accepts original_prompt for context-aware execution
        v2.1: Now accepts start_node for recursive exploration (depth 0, 1, 2...)
        
        Args:
            tree_id: Navigation tree ID
            userinterface_name: User interface name
            team_id: Team ID
            original_prompt: User's goal (NEW in v2.0)
            start_node: Node to start exploration from (NEW in v2.1, defaults to 'home')
            
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
            print(f"  Start node: {start_node}")
        
        # ✅ PRE-FLIGHT CHECK: Test navigation to start_node BEFORE starting exploration        
        # ✅ Pre-flight check: Verify start node exists (don't navigate - graph not loaded yet)
        print(f"\n[@ExplorationExecutor:start_exploration] 🔍 Pre-flight check: Verifying '{start_node}' node exists...")
        from shared.src.lib.database.navigation_trees_db import get_tree_nodes
        
        nodes_result = get_tree_nodes(tree_id, team_id)
        if not nodes_result.get('success'):
            error_msg = f"Failed to load tree nodes: {nodes_result.get('error')}"
            print(f"[@ExplorationExecutor:start_exploration] ❌ Pre-flight check FAILED: {error_msg}")
            
            with self._lock:
                self.exploration_state['status'] = 'failed'
                self.exploration_state['error'] = error_msg
            
            return {
                'success': False,
                'error': f"Cannot start AI exploration: {error_msg}",
                'exploration_id': exploration_id
            }
            
        nodes = nodes_result.get('nodes', [])
        start_node_exists = any(n.get('label') == start_node for n in nodes)
        
        if not start_node_exists:
            error_msg = f"Start node '{start_node}' not found in tree"
            print(f"[@ExplorationExecutor:start_exploration] ❌ Pre-flight check FAILED: {error_msg}")
            
            with self._lock:
                self.exploration_state['status'] = 'failed'
                self.exploration_state['error'] = error_msg
            
            return {
                'success': False,
                'error': f"Cannot start AI exploration: {error_msg}.\n\n"
                        f"Action required: Ensure '{start_node}' node exists in the navigation tree.",
                'exploration_id': exploration_id
            }
        
        print(f"[@ExplorationExecutor:start_exploration] ✅ Pre-flight check PASSED: '{start_node}' node exists")
        
        # ✅ Load navigation tree for the navigation executor
        # This ensures the graph is loaded before any navigation attempts (critical for start_node != 'home')
        try:
            print(f"\n[@ExplorationExecutor:start_exploration] 📥 Loading navigation tree...")
            result = self.device.navigation_executor.load_navigation_tree(
                userinterface_name=userinterface_name,
                team_id=team_id
            )
            if not result.get('success'):
                raise Exception(result.get('error', 'Unknown error'))
            print(f"[@ExplorationExecutor:start_exploration] ✅ Navigation tree loaded successfully")
        except Exception as e:
            error_msg = f"Failed to load navigation tree: {e}"
            print(f"[@ExplorationExecutor:start_exploration] ❌ {error_msg}")
            
            with self._lock:
                self.exploration_state['status'] = 'failed'
                self.exploration_state['error'] = error_msg
            
            return {
                'success': False,
                'error': f"Cannot start AI exploration: {error_msg}",
                'exploration_id': exploration_id
            }
        
        # Start exploration in background thread
        def run_exploration():
            try:
                # Update state (acquire lock briefly)
                with self._lock:
                    self.exploration_state['status'] = 'exploring'
                    self.exploration_state['current_step'] = 'Capturing initial screenshot...'
                
                # Create exploration engine with callbacks
                def update_screenshot(screenshot_path: str):
                    """Upload screenshot to R2 (same as validation screenshots)"""
                    try:
                        from shared.src.lib.utils.cloudflare_utils import upload_navigation_screenshot
                        
                        # Upload to R2 (same as other navigation screenshots)
                        r2_filename = "home_initial.jpg"
                        userinterface_name = self.exploration_state['userinterface_name']
                        upload_result = upload_navigation_screenshot(screenshot_path, userinterface_name, r2_filename)
                        
                        if upload_result.get('success'):
                            screenshot_url = upload_result.get('url')
                            print(f"[@ExplorationExecutor] Home screenshot uploaded to R2: {screenshot_url}")
                            
                            with self._lock:
                                self.exploration_state['current_analysis']['screenshot'] = screenshot_url
                        else:
                            print(f"[@ExplorationExecutor] Screenshot upload failed: {upload_result.get('error')}")
                    except Exception as e:
                        print(f"[@ExplorationExecutor] Screenshot upload failed: {e}")
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
                
            except ValueError as ve:
                # Clean ValueError (no stack trace) - user-friendly message
                error_msg = str(ve)
                print(f"[@ExplorationExecutor:run_exploration] ⚠️ EXPLORATION STOPPED: {error_msg}")
                
                with self._lock:
                    self.exploration_state['status'] = 'failed'
                    self.exploration_state['error'] = error_msg
                    self.exploration_state['current_step'] = f"⚠️ {error_msg}"
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
    
    def continue_exploration(self, team_id: str, selected_items: List[str] = None, selected_screen_items: List[str] = None) -> Dict[str, Any]:
        """
        Phase 2a: Create nodes and edges structure for selected items
        
        Dispatcher method - delegates to device-specific implementation
        """
        print(f"\n{'='*80}")
        print(f"[@ExplorationExecutor:continue_exploration] 🚀 PHASE 2: STRUCTURE CREATION STARTED")
        print(f"{'='*80}")
        
        with self._lock:
            if not self.current_exploration_id:
                return {'success': False, 'error': 'No active exploration'}
            
            if self.exploration_state['status'] != 'awaiting_approval':
                return {
                    'success': False,
                    'error': f"Cannot continue: status is {self.exploration_state['status']}"
                }
            
            exploration_plan = self.exploration_state.get('exploration_plan', {})
            strategy = exploration_plan.get('strategy', 'click')
            
            # Dispatch to device-specific implementation
            if strategy in ['dpad_with_screenshot', 'test_dpad_directions']:
                return self._create_tv_structure(team_id, selected_items, selected_screen_items)
            else:
                return self._create_mobile_structure(team_id, selected_items, selected_screen_items)
    
    def _create_tv_structure(self, team_id: str, selected_items: List[str] = None, selected_screen_items: List[str] = None) -> Dict[str, Any]:
        """TV dual-layer structure creation: Focus nodes + Screen nodes"""
        tree_id = self.exploration_state['tree_id']
        exploration_plan = self.exploration_state.get('exploration_plan', {})
        all_items = exploration_plan.get('items', [])
        strategy = exploration_plan.get('strategy', 'dpad_with_screenshot')
        menu_type = exploration_plan.get('menu_type', 'horizontal')
        lines = exploration_plan.get('lines', [])
        
        print(f"[@ExplorationExecutor:_create_tv_structure] All items from plan: {all_items}")
        print(f"[@ExplorationExecutor:_create_tv_structure] Received selected_items: {selected_items}")
        print(f"[@ExplorationExecutor:_create_tv_structure] 🎯 Strategy: {strategy}")
        print(f"[@ExplorationExecutor:_create_tv_structure] 🎯 Menu Type: {menu_type}")
        print(f"[@ExplorationExecutor:_create_tv_structure] 🎯 Row Structure: {len(lines)} rows")
        
        # Filter items based on user selection
        if selected_items is not None and len(selected_items) > 0:
            items = [item for item in all_items if item in selected_items]
            print(f"[@ExplorationExecutor:_create_tv_structure] ✅ User selected {len(items)}/{len(all_items)} items: {items}")
        else:
            items = all_items
            print(f"[@ExplorationExecutor:_create_tv_structure] ⚠️ No selection - creating all {len(items)} items")
        
        node_gen = NodeGenerator(tree_id, team_id)
        
        # Get home node
        home_node_result = get_node_by_id(tree_id, 'home', team_id)
        if not (home_node_result.get('success') and home_node_result.get('node')):
            return {'success': False, 'error': 'Home node does not exist'}
        
        home_id = home_node_result['node']['node_id']
        nodes_created = []
        nodes_to_save = []
        edges_to_save = []
        
        print(f"  ♻️  Using existing '{home_id}' node")
        
        with self._lock:
                print(f"\n{'='*80}")
                print(f"  🎮 TV NAVIGATION MODE: Creating dual-layer structure")
                print(f"     Layer 1: Focus nodes (menu positions)")
                print(f"     Layer 2: Screen nodes (actual screens)")
                print(f"{'='*80}\n")
                
                # Track all focus nodes and pairs across ALL rows
                all_focus_nodes_row1 = []  # Horizontal menu focus nodes
                all_vertical_focus_nodes = []  # Vertical menu focus nodes (Row 2+)
                focus_screen_pairs = []  # Store (focus, screen) pairs for vertical edges
                
                # ========== ROW 1: HORIZONTAL MENU ==========
                if len(lines) > 0 and len(lines[0]) > 1:
                    row1_items = lines[0]
                    
                    print(f"  📊 Processing Row 1 (horizontal menu): {len(row1_items)} items")
                    
                    # Step 1a: Create Row 1 focus nodes and screen nodes
                    for idx, original_item in enumerate(row1_items):
                        node_name_clean = node_gen.target_to_node_name(original_item)
                        
                        # ✅ ALWAYS include 'home' - it's the anchor for the menu structure
                        if node_name_clean.lower() in ['home', 'accueil']:
                            all_focus_nodes_row1.append('home')
                            print(f"    ♻️  Using existing 'home' node (Row 1 anchor)")
                            continue
                        
                        # Only process OTHER selected items (home is always included)
                        if original_item not in items:
                            continue
                        
                        # Create FOCUS node (menu position): home_tvguide, home_apps, etc.
                        focus_node_name = f"home_{node_name_clean}"
                        focus_position_x = 250 + (idx % 5) * 200
                        focus_position_y = 100 + (idx // 5) * 100
                        
                        focus_node_data = node_gen.create_node_data(
                            node_name=focus_node_name,
                            label=f"{focus_node_name}_temp",
                            position={'x': focus_position_x, 'y': focus_position_y},
                            ai_analysis={
                                'suggested_name': focus_node_name,
                                'screen_type': 'screen',
                                'reasoning': f'Row 1 menu focus position for: {original_item}'
                            },
                            node_type='screen'
                        )
                        nodes_to_save.append(focus_node_data)
                        all_focus_nodes_row1.append(focus_node_name)
                        nodes_created.append(focus_node_name)
                        print(f"    ✅ Created FOCUS node: {focus_node_name}_temp")
                        
                        # Create SCREEN node ONLY if selected
                        if selected_screen_items is None or original_item in selected_screen_items:
                            screen_node_name = node_name_clean
                            screen_position_x = 250 + (idx % 5) * 200
                            screen_position_y = 300 + (idx // 5) * 150
                            
                            screen_node_data = node_gen.create_node_data(
                                node_name=screen_node_name,
                                label=f"{screen_node_name}_temp",
                                position={'x': screen_position_x, 'y': screen_position_y},
                                ai_analysis={
                                    'suggested_name': screen_node_name,
                                    'screen_type': 'screen',
                                    'reasoning': f'Screen for: {original_item}'
                                },
                                node_type='screen'
                            )
                            nodes_to_save.append(screen_node_data)
                            nodes_created.append(screen_node_name)
                            
                            # Store focus-screen pair for vertical edges
                            focus_screen_pairs.append((focus_node_name, screen_node_name))
                            
                            # Store mapping
                            self.exploration_state['target_to_node_map'][original_item] = screen_node_name
                            print(f"    ✅ Created SCREEN node: {screen_node_name}_temp")
                        else:
                            print(f"    ⏭️  Skipped SCREEN node: {node_name_clean} (not selected)")
                    
                    print(f"\n  📊 Row 1 complete: {len(all_focus_nodes_row1)} focus nodes")
                    
                    # Step 1b: Create HORIZONTAL edges for Row 1 (LEFT/RIGHT between adjacent focus nodes)
                    print(f"\n  ➡️  Creating HORIZONTAL edges (Row 1 menu navigation):")
                    for idx in range(len(all_focus_nodes_row1) - 1):
                        source_focus = all_focus_nodes_row1[idx]
                        target_focus = all_focus_nodes_row1[idx + 1]
                        
                        # ✅ BIDIRECTIONAL: Single edge with action_sets[0]=RIGHT, action_sets[1]=LEFT
                        edge_horizontal = node_gen.create_edge_data(
                            source=source_focus,
                            target=target_focus,
                            actions=[{
                                "command": "press_key",
                                "params": {"key": "RIGHT"},
                                "delay": 1500
                            }],
                            reverse_actions=[{
                                "command": "press_key",
                                "params": {"key": "LEFT"},
                                "delay": 1500
                            }],
                            label=f"{source_focus}_to_{target_focus}_temp"
                        )
                        edges_to_save.append(edge_horizontal)
                        print(f"    ↔ {source_focus} ↔ {target_focus}: RIGHT/LEFT (bidirectional)")
                        
                # ========== ROW 2+: VERTICAL MENU (DOWN/UP from home) ==========
                if len(lines) > 1:
                    print(f"\n  📊 Processing Rows 2-{len(lines)} (vertical menu): {len(lines) - 1} rows")
                    
                    prev_vertical_focus = 'home'  # Start from home for vertical navigation
                    
                    for row_idx in range(1, len(lines)):
                        row_items = lines[row_idx]
                        print(f"\n  📊 Processing Row {row_idx + 1}: {len(row_items)} items")
                        
                        for idx, original_item in enumerate(row_items):
                            # Only process selected items
                            if original_item not in items:
                                continue
                            
                            node_name_clean = node_gen.target_to_node_name(original_item)
                            
                            # Create FOCUS node for vertical position
                            focus_node_name = f"home_{node_name_clean}"
                            focus_position_x = 50  # Left aligned for vertical menu
                            focus_position_y = 100 + (row_idx * 150)
                            
                            focus_node_data = node_gen.create_node_data(
                                node_name=focus_node_name,
                                label=f"{focus_node_name}_temp",
                                position={'x': focus_position_x, 'y': focus_position_y},
                                ai_analysis={
                                    'suggested_name': focus_node_name,
                                    'screen_type': 'screen',
                                    'reasoning': f'Row {row_idx + 1} vertical menu focus position for: {original_item}'
                                },
                                node_type='screen'
                            )
                            nodes_to_save.append(focus_node_data)
                            all_vertical_focus_nodes.append(focus_node_name)
                            nodes_created.append(focus_node_name)
                            print(f"    ✅ Created FOCUS node: {focus_node_name}_temp")
                            
                            # Create DOWN/UP edge from previous vertical focus
                            edge_vertical_nav = node_gen.create_edge_data(
                                source=prev_vertical_focus,
                                target=focus_node_name,
                                actions=[{
                                    "command": "press_key",
                                    "params": {"key": "DOWN"},
                                    "delay": 1500
                                }],
                                reverse_actions=[{
                                    "command": "press_key",
                                    "params": {"key": "UP"},
                                    "delay": 1500
                                }],
                                label=f"{prev_vertical_focus}_to_{focus_node_name}_temp"
                            )
                            edges_to_save.append(edge_vertical_nav)
                            print(f"    ↕ {prev_vertical_focus} ↔ {focus_node_name}: DOWN/UP (bidirectional)")
                            
                            # Create SCREEN node if selected
                            if selected_screen_items is None or original_item in selected_screen_items:
                                screen_node_name = node_name_clean
                                screen_position_x = 250
                                screen_position_y = 100 + (row_idx * 150)
                                
                                screen_node_data = node_gen.create_node_data(
                                    node_name=screen_node_name,
                                    label=f"{screen_node_name}_temp",
                                    position={'x': screen_position_x, 'y': screen_position_y},
                                    ai_analysis={
                                        'suggested_name': screen_node_name,
                                        'screen_type': 'screen',
                                        'reasoning': f'Screen for: {original_item}'
                                    },
                                    node_type='screen'
                                )
                                nodes_to_save.append(screen_node_data)
                                nodes_created.append(screen_node_name)
                                
                                # Store focus-screen pair for vertical edges
                                focus_screen_pairs.append((focus_node_name, screen_node_name))
                    
                                # Store mapping
                                self.exploration_state['target_to_node_map'][original_item] = screen_node_name
                                print(f"    ✅ Created SCREEN node: {screen_node_name}_temp")
                            else:
                                print(f"    ⏭️  Skipped SCREEN node: {node_name_clean} (not selected)")
                            
                            # Update previous vertical focus for next row
                            prev_vertical_focus = focus_node_name
                    
                    print(f"\n  📊 Rows 2+ complete: {len(all_vertical_focus_nodes)} vertical focus nodes")
                
                # ========== VERTICAL EDGES: OK/BACK (Focus ↔ Screen for ALL rows) ==========
                print(f"\n  ⬇️  Creating VERTICAL edges (enter/exit screens for all rows):")
                for focus_node, screen_node in focus_screen_pairs:
                    # ✅ BIDIRECTIONAL: Single edge with action_sets[0]=OK, action_sets[1]=BACK
                    edge_vertical = node_gen.create_edge_data(
                        source=focus_node,
                        target=screen_node,
                        actions=[{
                            "command": "press_key",
                            "params": {"key": "OK"},
                            "delay": 5000
                        }],
                        reverse_actions=[{
                            "command": "press_key",
                            "params": {"key": "BACK"},
                            "delay": 5000
                        }],
                        label=f"{focus_node}_to_{screen_node}_temp"
                    )
                    edges_to_save.append(edge_vertical)
                    print(f"    ↕ {focus_node} ↔ {screen_node}: OK/BACK (bidirectional)")
                
                print(f"\n{'='*80}")
                print(f"  ✅ TV NAVIGATION COMPLETE")
                print(f"     Row 1 (horizontal): {len(all_focus_nodes_row1)} focus nodes")
                print(f"     Rows 2+ (vertical): {len(all_vertical_focus_nodes)} vertical focus nodes")
                print(f"     Screen nodes: {len(focus_screen_pairs)} total")
                print(f"     Edges created: {len(edges_to_save)} bidirectional edges")
                print(f"{'='*80}\n")
        
        # Save nodes and edges
        return self._save_structure(tree_id, team_id, nodes_to_save, edges_to_save, nodes_created, items)
    
    def _create_mobile_structure(self, team_id: str, selected_items: List[str] = None, selected_screen_items: List[str] = None) -> Dict[str, Any]:
        """Mobile/Web click-based structure creation"""
        tree_id = self.exploration_state['tree_id']
        exploration_plan = self.exploration_state.get('exploration_plan', {})
        all_items = exploration_plan.get('items', [])
        
        print(f"\n  📱 MOBILE/WEB MODE: Creating click-based structure")
        print(f"[@ExplorationExecutor:_create_mobile_structure] All items: {all_items}")
        print(f"[@ExplorationExecutor:_create_mobile_structure] Selected: {selected_items}")
        
        # Filter items based on user selection
        if selected_items is not None and len(selected_items) > 0:
            items = [item for item in all_items if item in selected_items]
            print(f"[@ExplorationExecutor:_create_mobile_structure] ✅ User selected {len(items)}/{len(all_items)} items")
        else:
            items = all_items
            print(f"[@ExplorationExecutor:_create_mobile_structure] ⚠️ No selection - creating all {len(items)} items")
        
        node_gen = NodeGenerator(tree_id, team_id)
        
        # Get home node
        home_node_result = get_node_by_id(tree_id, 'home', team_id)
        if not (home_node_result.get('success') and home_node_result.get('node')):
            return {'success': False, 'error': 'Home node does not exist'}
        
        home_id = home_node_result['node']['node_id']
        nodes_created = []
        nodes_to_save = []
        edges_to_save = []
        
        print(f"  ♻️  Using existing '{home_id}' node")
        
        with self._lock:
            # Create child nodes and edges
            for idx, item in enumerate(items):
                node_name_clean = node_gen.target_to_node_name(item)
                
                # Skip home nodes - they already exist by default
                if node_name_clean == 'home' or 'home' in node_name_clean or node_name_clean.lower() in ['home', 'accueil']:
                    print(f"  ⏭️  Skipping '{node_name_clean}' (home node already exists)")
                    continue
                
                # ✅ Use clean node_id, add _temp to label for visual distinction
                node_name = node_name_clean
                position_x = 250 + (idx % 5) * 200
                position_y = 300 + (idx // 5) * 150
                
                # Create node data
                node_data = node_gen.create_node_data(
                    node_name=node_name,
                    label=f"{node_name}_temp",
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
                
                # Click navigation for mobile/web
                print(f"  📱 Creating CLICK edge for '{item}': click_element(\"{item}\")")
                
                forward_actions = [{
                    "command": "click_element",
                    "params": {"element_id": item},
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
                    label=f"{item}_temp"
                )
                edges_to_save.append(edge_data)
        
        # Save nodes and edges
        return self._save_structure(tree_id, team_id, nodes_to_save, edges_to_save, nodes_created, items)
    
    def _save_structure(self, tree_id: str, team_id: str, nodes_to_save: list, edges_to_save: list, nodes_created: list, items: list) -> Dict[str, Any]:
        """Common method to save nodes and edges (used by TV and Mobile)"""
        # Get home_id from state
        home_id = self.exploration_state.get('home_id')
        if not home_id:
            home_node_result = get_node_by_id(tree_id, 'home', team_id)
            if home_node_result.get('success') and home_node_result.get('node'):
                home_id = home_node_result['node']['node_id']
        
        # Save nodes
        print(f"  💾 Batch saving {len(nodes_to_save)} nodes...")
        for node_data in nodes_to_save:
            node_result = save_node(tree_id, node_data, team_id)
            if node_result['success']:
                print(f"  ✅ Created node: {node_data['node_id']}")
            else:
                print(f"  ❌ Failed to create node {node_data['node_id']}: {node_result.get('error')}")
        
        # Save edges
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
        with self._lock:
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
            
            items_to_validate = self.exploration_state.get('items_to_validate', [])
            print(f"[@ExplorationExecutor:start_validation] Items to validate: {len(items_to_validate)}")
            print(f"[@ExplorationExecutor:start_validation] Items: {items_to_validate}")
            
            if not items_to_validate or len(items_to_validate) == 0:
                return {
                    'success': False,
                    'error': 'No items to validate. Structure may not have been created properly.'
                }
            
            self.exploration_state['status'] = 'awaiting_validation'
            self.exploration_state['current_validation_index'] = 0
            self.exploration_state['node_verification_data'] = []  # Initialize for collecting dumps during validation
            
            print(f"[@ExplorationExecutor:start_validation] ✅ Ready to validate {len(items_to_validate)} items")
            
            return {
                'success': True,
                'message': 'Ready to start validation',
                'total_items': len(items_to_validate)
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
        Phase 2b: Validate edges sequentially
        
        Dispatcher method - delegates to device-specific validation
        """
        with self._lock:
            print(f"\n{'='*80}")
            print(f"[@ExplorationExecutor:validate_next_item] VALIDATION STEP START")
            print(f"{'='*80}")
            
            if self.exploration_state['status'] not in ['awaiting_validation', 'validating']:
                error_msg = f"Cannot validate: status is {self.exploration_state['status']}"
                print(f"[@ExplorationExecutor:validate_next_item] ❌ {error_msg}")
                return {
                    'success': False,
                    'error': error_msg
                }
            
            current_index = self.exploration_state['current_validation_index']
            items_to_validate = self.exploration_state['items_to_validate']
            
            print(f"[@ExplorationExecutor:validate_next_item] Progress: {current_index + 1}/{len(items_to_validate)}")
            
            if current_index >= len(items_to_validate):
                print(f"[@ExplorationExecutor:validate_next_item] ✅ All items validated!")
                self.exploration_state['status'] = 'validation_complete'
                return {
                    'success': True,
                    'message': 'All items validated',
                    'has_more_items': False
                }
            
            strategy = self.exploration_state.get('exploration_plan', {}).get('strategy', 'click')
            
            # Dispatch to device-specific validation
            if strategy in ['dpad_with_screenshot', 'test_dpad_directions']:
                return self._validate_tv_item()
            else:
                return self._validate_mobile_item()
    
    def _validate_tv_item(self) -> Dict[str, Any]:
        """TV validation - delegates to TVValidationStrategy"""
        strategy = TVValidationStrategy(self)
        return strategy.validate_item()
    
    def _validate_mobile_item(self) -> Dict[str, Any]:
        """Mobile validation - delegates to MobileValidationStrategy"""
        strategy = MobileValidationStrategy(self)
        return strategy.validate_item()
    
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
    
    def start_node_verification(self) -> Dict[str, Any]:
        """
        Phase 2c: Analyze dumps and suggest verifications
        
        Returns:
            {
                'success': True,
                'suggestions': [...],
                'total_nodes': 5
            }
        """
        with self._lock:
            if self.exploration_state['status'] != 'validation_complete':
                return {
                    'success': False,
                    'error': f"Cannot start node verification: status is {self.exploration_state['status']}"
                }
            
            node_verification_data = self.exploration_state.get('node_verification_data', [])
            
            if not node_verification_data:
                return {
                    'success': False,
                    'error': 'No node verification data available'
                }
            
            print(f"[@ExplorationExecutor:start_node_verification] Analyzing {len(node_verification_data)} nodes")
            
            # Analyze dumps to find unique elements
            from backend_host.src.services.ai_exploration.dump_analyzer import analyze_unique_elements
            suggestions = analyze_unique_elements(node_verification_data, device_model=self.device_model)
            
            # Store suggestions
            self.exploration_state['node_verification_suggestions'] = suggestions
            self.exploration_state['status'] = 'awaiting_node_verification'
            self.exploration_state['current_step'] = 'Node verification suggestions ready - review and approve'
            
            print(f"[@ExplorationExecutor:start_node_verification] Generated {len(suggestions)} suggestions")
            
            return {
                'success': True,
                'suggestions': suggestions,
                'total_nodes': len(suggestions),
                'message': 'Node verification analysis complete'
            }
    
    def approve_node_verifications(self, approved_verifications: List[Dict], team_id: str) -> Dict[str, Any]:
        """
        Update nodes with approved verifications + screenshots
        
        Args:
            approved_verifications: [
                {
                    'node_id': 'search',
                    'verification': {
                        'text': 'TV Guide',  # For TV: text found by OCR
                        'area': {...},       # For TV: area where text was found
                        'command': 'waitForTextToAppear'  # Or from mobile/web analysis
                    },
                    'screenshot_url': '...'
                }
            ]
            
        Returns:
            {
                'success': True,
                'nodes_updated': 5,
                'references_created': 3  # TV only
            }
        """
        with self._lock:
            if self.exploration_state['status'] != 'awaiting_node_verification':
                return {
                    'success': False,
                    'error': f"Cannot approve: status is {self.exploration_state['status']}"
                }
            
            tree_id = self.exploration_state['tree_id']
            userinterface_name = self.exploration_state.get('userinterface_name')
            
            print(f"[@ExplorationExecutor:approve_node_verifications] Updating {len(approved_verifications)} nodes")
            
            nodes_updated = 0
            references_created = 0
            nodes_to_save = []
            
            for item in approved_verifications:
                node_id = item['node_id']
                verification = item.get('verification')
                screenshot_url = item.get('screenshot_url')
                
                # Get node
                node_result = get_node_by_id(tree_id, node_id, team_id)
                if not node_result.get('success'):
                    print(f"  ❌ Node {node_id} not found")
                    continue
                
                node_data = node_result['node']
                
                # Update node with screenshot + verification
                if screenshot_url:
                    # Ensure data field exists
                    if 'data' not in node_data or node_data['data'] is None:
                        node_data['data'] = {}
                    
                    # Store screenshot in data JSONB column, not as root column
                    node_data['data']['screenshot'] = screenshot_url
                    node_data['data']['screenshot_timestamp'] = int(time.time() * 1000)
                
                # 🛡️ VALIDATION: Only save valid verifications (same logic as useNodeEdit.ts)
                if verification:
                    # ✅ TV/TEXT: Check if this is a text verification that needs reference creation
                    is_text_verification = verification.get('text') and verification.get('area')
                    
                    if is_text_verification:
                        # 📝 CREATE TEXT REFERENCE FIRST (TV workflow)
                        print(f"  📝 Creating text reference for node {node_id}")
                        
                        # Get node label (remove _temp suffix)
                        node_label = node_data.get('label', node_id).replace('_temp', '')
                        
                        # Create reference name: {userinterface_name}_{node_label}
                        reference_name = f"{userinterface_name}_{node_label}"
                        
                        # Save text reference to database
                        from shared.src.lib.database.verifications_references_db import save_reference
                        
                        # Merge text with area data
                        area_with_text = {
                            **(verification['area'] or {}),
                            'text': verification['text']
                        }
                        
                        reference_result = save_reference(
                            name=reference_name,
                            userinterface_name=userinterface_name,
                            reference_type='reference_text',
                            team_id=team_id,
                            r2_path=f'text-references/{userinterface_name}/{reference_name}',
                            r2_url='',  # Text references don't have URLs
                            area=area_with_text
                        )
                        
                        if reference_result.get('success'):
                            references_created += 1
                            print(f"    ✅ Text reference created: {reference_name}")
                            
                            # Create verification that uses the reference
                            if 'verifications' not in node_data:
                                node_data['verifications'] = []
                            
                            # Add text verification with reference_name
                            node_data['verifications'].append({
                                'command': 'waitForTextToAppear',
                                'verification_type': 'text',
                                'params': {
                                    'reference_name': reference_name  # ← Points to DB entry
                                },
                                'expected': True
                            })
                            
                            print(f"    ✅ Verification added with reference: {reference_name}")
                        else:
                            print(f"    ❌ Failed to create text reference: {reference_result.get('error')}")
                            continue
                    
                    elif verification.get('params'):
                        # 📱 MOBILE/WEB: Direct params (no reference needed)
                        # Validate: params must not be empty dict
                        params = verification['params']
                        if not params or not isinstance(params, dict):
                            print(f"  ⚠️ Skipping verification for node {node_id}: empty or invalid params")
                            continue
                        
                        # Validate: at least one param key must have a non-empty value
                        has_valid_param = any(
                            v and str(v).strip() != '' 
                            for v in params.values()
                        )
                        
                        if not has_valid_param:
                            print(f"  ⚠️ Skipping verification for node {node_id}: all param values are empty")
                            continue
                        
                        # Validate: command must exist and not be empty
                        command = verification.get('method', '')
                        if not command or command.strip() == '':
                            print(f"  ⚠️ Skipping verification for node {node_id}: missing command")
                            continue
                        
                        # Add verification to node
                        if 'verifications' not in node_data:
                            node_data['verifications'] = []
                        
                        # Check if verification already exists to avoid duplicates
                        verification_exists = False
                        new_params = verification['params']
                        
                        for v in node_data['verifications']:
                            if v.get('command') == verification.get('method') and v.get('params') == new_params:
                                verification_exists = True
                                break
                        
                        if not verification_exists:
                            # Map 'method' to 'command' for standard verification format
                            node_data['verifications'].append({
                                'command': command,  # Use validated command
                                'verification_type': verification.get('type', 'adb'),
                                'params': verification['params'],
                                'expected': True
                            })
                            print(f"    ✅ Verification added (direct params)")
                
                nodes_to_save.append(node_data)
            
            # Save all updated nodes in a SINGLE BATCH
            # This ensures the materialized view refresh trigger fires only ONCE
            if nodes_to_save:
                save_result = save_nodes_batch(tree_id, nodes_to_save, team_id)
                if save_result.get('success'):
                    nodes_updated = len(nodes_to_save)
                    print(f"  ✅ Successfully updated {nodes_updated} nodes (batch)")
                    for n in nodes_to_save:
                        print(f"    • {n.get('node_id')}")
                else:
                    print(f"  ❌ Failed to batch update nodes: {save_result.get('error')}")
            
            # Update state
            self.exploration_state['status'] = 'node_verification_complete'
            
            if references_created > 0:
                self.exploration_state['current_step'] = f'Updated {nodes_updated} nodes ({references_created} text references created) - ready to finalize'
            else:
                self.exploration_state['current_step'] = f'Updated {nodes_updated} nodes - ready to finalize'
            
            return {
                'success': True,
                'nodes_updated': nodes_updated,
                'references_created': references_created,
                'message': f'Updated {nodes_updated} nodes with verifications' + (f' ({references_created} text references created)' if references_created > 0 else '')
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

