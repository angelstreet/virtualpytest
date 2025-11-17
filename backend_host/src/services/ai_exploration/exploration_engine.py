"""
Exploration Engine - Main orchestrator for AI-driven navigation tree generation
Coordinates screen analysis, navigation, and tree building
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional
import traceback

from backend_host.src.services.ai_exploration.screen_analyzer import ScreenAnalyzer
from backend_host.src.services.ai_exploration.navigation_strategy import NavigationStrategy
from backend_host.src.services.ai_exploration.node_generator import NodeGenerator
from shared.src.lib.database.navigation_trees_db import (
    save_node,
    save_edge,
    create_sub_tree,
    get_tree_metadata,
    get_node_by_id
)


class ExplorationEngine:
    """Main orchestrator for AI-driven exploration"""
    
    def __init__(
        self,
        tree_id: str,
        device,  # Device instance (passed from ExplorationExecutor)
        team_id: str,
        userinterface_name: str,
        screenshot_callback=None,
        progress_callback=None
    ):
        """
        Initialize exploration engine
        
        Args:
            tree_id: Tree ID to add nodes to
            device: Device instance (from ExplorationExecutor)
            team_id: Team ID
            userinterface_name: UI name (e.g., 'horizon_android_mobile')
            screenshot_callback: Optional callback function to notify when screenshot is captured
            progress_callback: Optional callback function to notify of progress updates
        
        Note: Exploration is SIMPLE - only 1 level (click → back → create node/edge)
        """
        self.device = device
        self.tree_id = tree_id
        self.device_id = device.device_id
        self.host_name = device.host_name
        self.device_model_name = device.device_model
        self.team_id = team_id
        self.userinterface_name = userinterface_name
        self.screenshot_callback = screenshot_callback
        self.progress_callback = progress_callback
        
        # Use existing remote controller (already initialized with correct device_ip)
        self.controller = self.device._get_controller('remote')
        if not self.controller:
            raise ValueError(f"No remote controller found for device {self.device_id}")
        
        # Initialize components with existing controller
        self.screen_analyzer = ScreenAnalyzer(
            device=self.device,  # Pass device directly
            controller=self.controller,
            ai_model='qwen'
        )
        
        self.navigation_strategy = NavigationStrategy(self.controller, self.screen_analyzer)
        self.node_generator = NodeGenerator(tree_id, team_id)
        
        # Exploration state
        self.created_nodes = []
        self.created_edges = []
        self.created_subtrees = []
        self.exploration_log = []
        
        # Phase 1 state (stored for Phase 2)
        self.initial_screenshot = None
        self.prediction = None
        
    def analyze_and_plan(self) -> Dict:
        """
        PHASE 1: Analyze screenshot and create exploration plan
        
        Returns:
            {
                'success': True,
                'plan': {
                    'menu_type': 'horizontal',
                    'items': ['home', 'settings', 'profile'],
                    'strategy': 'test_right_left_first_then_ok',
                    'reasoning': 'AI reasoning here...',
                    'screenshot': 'url',
                    'screen_name': 'Initial Screen'
                }
            }
        """
        try:
            print(f"\n{'='*60}")
            print(f"[@exploration_engine] PHASE 1: Analysis & Planning")
            print(f"Tree: {self.tree_id}")
            print(f"Device: {self.device_model_name} ({self.device_id})")
            print(f"{'='*60}\n")
            
            # Capture initial screenshot
            self.initial_screenshot = self.screen_analyzer.capture_screenshot()
            if not self.initial_screenshot:
                return {
                    'success': False,
                    'error': 'Failed to capture initial screenshot'
                }
            
            # Notify callbacks
            if self.screenshot_callback:
                self.screenshot_callback(self.initial_screenshot)
            if self.progress_callback:
                self.progress_callback(
                    step="Phase 1: Analyzing initial screenshot with AI...",
                    screenshot=self.initial_screenshot,
                    analysis=None
                )
            
            print(f"[@exploration_engine:analyze_and_plan] About to call _phase1_anticipation with screenshot: {self.initial_screenshot}")
            
            # AI analyzes and predicts structure
            self.prediction = self._phase1_anticipation(self.initial_screenshot)
            
            print(f"[@exploration_engine:analyze_and_plan] _phase1_anticipation completed, prediction: {self.prediction}")
            
            # Build reasoning for user
            reasoning = f"""Menu Type: {self.prediction.get('menu_type', 'unknown')}
Items Found: {len(self.prediction.get('items', []))} items
Predicted Depth: {self.prediction.get('predicted_depth', 1)} levels
Strategy: {self.prediction.get('strategy', 'unknown')}

AI identified the following menu items:
{', '.join(self.prediction.get('items', []))}

Exploration will navigate through these items using {self.prediction.get('strategy', 'default')} approach."""
            
            # Notify of prediction results
            if self.progress_callback:
                self.progress_callback(
                    step=f"Phase 1 Complete: Ready to explore {len(self.prediction.get('items', []))} items",
                    screenshot=self.initial_screenshot,
                    analysis={
                        'screen_name': 'Initial Analysis',
                        'elements_found': self.prediction.get('items', []),
                        'reasoning': reasoning
                    }
                )
            
            return {
                'success': True,
                'plan': {
                    'menu_type': self.prediction.get('menu_type'),
                    'items': self.prediction.get('items', []),
                    'lines': self.prediction.get('lines', []),
                    'strategy': self.prediction.get('strategy'),
                    'predicted_depth': self.prediction.get('predicted_depth', 1),
                    'reasoning': reasoning,
                    'screenshot': self.initial_screenshot,
                    'screen_name': 'Initial Screen'
                }
            }
            
        except Exception as e:
            print(f"[@exploration_engine:analyze_and_plan] Error: {e}")
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }
    
    def execute_exploration(self) -> Dict:
        """
        PHASE 2: Execute exploration based on approved plan
        
        Returns:
            {
                'success': True,
                'nodes_created': 3,
                'edges_created': 2,
                'subtrees_created': 1,
                'created_node_ids': ['home_temp', ...],
                'created_edge_ids': ['edge1_temp', ...],
                'created_subtree_ids': ['subtree1', ...]
            }
        """
        try:
            print(f"\n{'='*60}")
            print(f"[@exploration_engine] PHASE 2: Exploration Execution")
            print(f"{'='*60}\n")
            
            if not self.initial_screenshot or not self.prediction:
                return {
                    'success': False,
                    'error': 'Must run analyze_and_plan() first'
                }
            
            # PHASE 2: Validation - Explore to validate prediction
            self._phase2_validation(self.prediction, self.initial_screenshot)
            
            # Return results
            return {
                'success': True,
                'nodes_created': len(self.created_nodes),
                'edges_created': len(self.created_edges),
                'subtrees_created': len(self.created_subtrees),
                'created_node_ids': self.created_nodes,
                'created_edge_ids': self.created_edges,
                'created_subtree_ids': self.created_subtrees,
                'exploration_log': self.exploration_log
            }
            
        except Exception as e:
            print(f"[@exploration_engine:execute_exploration] Error: {e}")
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }
    
    def explore_single_item(self, item: str, depth: int = 0) -> Dict:
        """
        Explore a SINGLE item (for incremental approval workflow)
        
        Args:
            item: Item name to explore (e.g., "Search", "Settings", "dynamic_1")
            depth: Current depth in exploration
        
        Returns:
            {
                'success': True,
                'node': {...},  # Node data created
                'edge': {...}   # Edge data created
            }
        """
        try:
            print(f"\n[@exploration_engine] Exploring single item: {item} (depth={depth})")
            
            # Get root node (or parent node for depth > 0)
            root_node_name = "home_temp"  # For now, always use home as source
            
            # Determine strategy
            strategy = self.prediction.get('strategy', 'click_elements')
            
            if strategy == 'click_elements':
                # Mobile/Web: Click-based
                return self._explore_single_item_click(root_node_name, item, depth)
            else:
                # TV/STB: DPAD-based (TODO)
                return {'success': False, 'error': 'DPAD strategy not yet implemented for single item'}
        
        except Exception as e:
            print(f"[@exploration_engine:explore_single_item] Error: {e}")
            traceback.print_exc()
            return {'success': False, 'error': str(e)}
    
    def _explore_single_item_click(self, source_node: str, item: str, depth: int) -> Dict:
        """
        Explore a single item using click-based navigation
        
        Args:
            source_node: Source node name (e.g., "home_temp")
            item: Item to click
            depth: Current depth
        
        Returns:
            Dict with success, node, edge
        """
        import time
        
        # Generate node name that would be created
        new_node_name = f"{item}_temp"
        
        # ✅ PROTECTION: Check if node already exists (important for subtrees)
        existing_node = get_node_by_id(self.tree_id, new_node_name, self.team_id)
        if existing_node.get('success') and existing_node.get('node'):
            print(f"    ⏭️ Node '{new_node_name}' already exists - skipping exploration")
            return {'success': False, 'error': f'Node {new_node_name} already exists'}
        
        # 1. Click element
        click_success = False
        if item.startswith('dynamic_'):
            # Dynamic content - skip for now (TODO: need bounds)
            return {'success': False, 'error': f'Dynamic element {item} not yet supported'}
        else:
            # Static element - click by text
            try:
                result = self.controller.click_element(text=item)
                click_success = result if isinstance(result, bool) else result.get('success', False)
            except Exception as e:
                print(f"    ❌ Click failed: {e}")
                return {'success': False, 'error': f'Click failed: {str(e)}'}
        
        if not click_success:
            return {'success': False, 'error': f'Click on {item} failed'}
        
        print(f"    ✅ Click succeeded")
        time.sleep(2)  # Wait for navigation
        
        # 2. Press BACK
        print(f"    ⬅️ Pressing BACK...")
        try:
            self.controller.press_key('BACK')
            time.sleep(2)
        except Exception as e:
            print(f"    ❌ BACK failed: {e}")
            back_success = False
        else:
            # 3. Verify we're back on source screen
            # Get a known source element (use first item from prediction if available)
            predicted_items = self.prediction.get('items', [])
            source_element = predicted_items[0] if predicted_items else 'Home'
            
            print(f"    🔍 Verifying source element '{source_element}' is visible...")
            try:
                is_back = self.controller.wait_for_element_by_text(
                    text=source_element,
                    timeout=5
                )
                back_success = is_back if isinstance(is_back, bool) else is_back.get('success', False)
            except Exception as e:
                print(f"    ⚠️ Back verification failed: {e}")
                back_success = False
        
        if back_success:
            print(f"    ✅ BACK succeeded - both directions valid")
        else:
            print(f"    ⚠️ BACK failed - only forward edge created")
        
        # 4. Create node and edge (node name already generated above for duplicate check)
        
        # Calculate position
        position_x = 250 + (len(self.created_nodes) % 3) * 300
        position_y = 250 + (len(self.created_nodes) // 3) * 200
        
        # Create node
        node_data = self.node_generator.create_node_data(
            node_name=new_node_name,
            position={'x': position_x, 'y': position_y},
            ai_analysis={
                'suggested_name': item,
                'screen_type': 'screen',
                'reasoning': f'Reached by clicking {item}'
            },
            node_type='screen'
        )
        
        node_result = save_node(self.tree_id, node_data, self.team_id)
        if not node_result['success']:
            return {'success': False, 'error': f"Failed to save node: {node_result.get('error')}"}
        
        self.created_nodes.append(new_node_name)
        print(f"    ✅ Created node: {new_node_name}")
        
        # Create edge with bidirectional action sets
        forward_actions = [
            {'command': 'click_element', 'params': {'text': item}, 'delay': 2000}
        ]
        
        backward_actions = [
            {'command': 'press_key', 'params': {'key': 'BACK'}, 'delay': 2000}
        ] if back_success else []
        
        edge_data = self.node_generator.create_edge_data(
            source=source_node,
            target=new_node_name,
            actions=forward_actions,
            reverse_actions=backward_actions
        )
        
        edge_result = save_edge(self.tree_id, edge_data, self.team_id)
        if not edge_result['success']:
            return {'success': False, 'error': f"Failed to save edge: {edge_result.get('error')}"}
        
        self.created_edges.append(edge_data['edge_id'])
        print(f"    ✅ Created edge: {source_node} ↔ {new_node_name} ({'bidirectional' if back_success else 'forward only'})")
        
        return {
            'success': True,
            'node': node_data,
            'edge': edge_data
        }
        
    def start_exploration(self) -> Dict:
        """
        Full exploration (Phase 1 + Phase 2 together)
        
        Returns:
            {
                'success': True,
                'nodes_created': 3,
                'edges_created': 2,
                'subtrees_created': 1,
                'exploration_log': [...]
            }
        """
        # Phase 1
        plan_result = self.analyze_and_plan()
        if not plan_result['success']:
            return plan_result
        
        # Phase 2
        return self.execute_exploration()
    
    def _phase1_anticipation(self, screenshot_path: str) -> Dict:
        """
        Phase 1: AI anticipates tree structure from first screenshot
        
        Args:
            screenshot_path: Path to initial screenshot
            
        Returns:
            Prediction dict from AI
        """
        print(f"\n[@exploration_engine] === PHASE 1: ANTICIPATION ===")
        
        prediction = self.screen_analyzer.anticipate_tree(screenshot_path)
        
        print(f"Menu Type: {prediction.get('menu_type')}")
        print(f"Predicted Items: {prediction.get('items')}")
        print(f"Predicted Depth: {prediction.get('predicted_depth')}")
        print(f"Strategy: {prediction.get('strategy')}")
        
        self.exploration_log.append({
            'phase': 'anticipation',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'prediction': prediction
        })
        
        return prediction
    
    def _phase2_validation(self, prediction: Dict, initial_screenshot: str):
        """
        Phase 2: Validate predictions by testing navigation
        
        Strategy depends on device type:
        - Mobile/Web (click-based): Click element → if success, create forward edge → Press BACK → verify source visible
        - TV/STB (DPAD-based): Navigate with DPAD → Press OK → AI verify new screen → Press BACK → AI verify back
        
        Args:
            prediction: AI prediction from phase 1
            initial_screenshot: Path to initial screenshot
        """
        print(f"\n[@exploration_engine] === PHASE 2: VALIDATION ===")
        
        # Home node should already exist - userinterfaces have home by default
        root_node_name = "home"
        home_node_result = get_node_by_id(self.tree_id, root_node_name, self.team_id)
        if not (home_node_result.get('success') and home_node_result.get('node')):
            print(f"❌ Home node does not exist. Userinterface should have home node by default.")
            return
        
        print(f"✅ Using existing home node: {root_node_name}")
        
        # Determine strategy based on device type
        strategy = prediction.get('strategy', 'click_elements')
        
        if strategy == 'click_elements':
            # Mobile/Web: Click-based validation
            self._validate_click_based(
                current_node=root_node_name,
                prediction=prediction,
                depth=0
            )
        else:
            # TV/STB: DPAD-based validation (AI-guided)
            self._validate_dpad_based(
                current_node=root_node_name,
                parent_screenshot=initial_screenshot,
                prediction=prediction,
                depth=0
            )
    
    def _validate_click_based(
        self,
        current_node: str,
        prediction: Dict,
        depth: int
    ):
        """
        Mobile/Web validation: SIMPLE 1-LEVEL EXPLORATION
        
        Workflow for each item:
        1. Click element
        2. Wait 2s
        3. Press BACK
        4. Verify returned to home
        5. Create node and edge
        
        Args:
            current_node: Current node name (e.g., 'home_temp')
            prediction: AI prediction with items to click
            depth: Current depth (always 0 for simple exploration)
        """
        print(f"\n[@exploration_engine] 📱 MOBILE/WEB SIMPLE EXPLORATION: {current_node} (depth={depth})")
        
        predicted_items = prediction.get('items', [])
        print(f"  Items to explore: {len(predicted_items)}")
        
        # Get a known source element to verify BACK (use first item or 'Home')
        source_element = predicted_items[0] if predicted_items else 'Home'
        
        import time
        
        for i, item in enumerate(predicted_items):
            print(f"\n  [{i+1}/{len(predicted_items)}] Testing: {item}")
            
            # Generate node name that would be created
            new_node_name = f"{self.node_generator.target_to_node_name(item)}_temp"
            
            # ✅ PROTECTION: Check if node already exists (important for subtrees)
            existing_node = get_node_by_id(self.tree_id, new_node_name, self.team_id)
            if existing_node.get('success') and existing_node.get('node'):
                print(f"    ⏭️ Node '{new_node_name}' already exists - skipping exploration")
                continue
            
            # Notify progress
            if self.progress_callback:
                self.progress_callback(
                    step=f"Exploring {i+1}/{len(predicted_items)}: {item}",
                    screenshot=None,
                    analysis={'screen_name': item, 'elements_found': [item], 'reasoning': f'Clicking on {item}'}
                )
            
            # 1. Click element
            click_success = False
            if item.startswith('dynamic_'):
                print(f"    ⚠️ Dynamic element {item} - skipping")
                continue
            else:
                try:
                    result = self.controller.click_element(text=item)
                    click_success = result if isinstance(result, bool) else result.get('success', False)
                except Exception as e:
                    print(f"    ❌ Click failed: {e}")
                    click_success = False
            
            if not click_success:
                print(f"    ⏭️ Click failed - skipping {item}")
                continue
            
            print(f"    ✅ Click succeeded")
            time.sleep(2)
            
            # 2. Press BACK
            print(f"    ⬅️ Pressing BACK...")
            try:
                self.controller.press_key('BACK')
                time.sleep(2)
            except Exception as e:
                print(f"    ❌ BACK failed: {e}")
                continue
            
            # 3. Verify we're back on source screen
            print(f"    🔍 Verifying source element '{source_element}' is visible...")
            try:
                is_back = self.controller.wait_for_element_by_text(
                    text=source_element,
                    timeout=5
                )
                back_success = is_back if isinstance(is_back, bool) else is_back.get('success', False)
            except Exception as e:
                print(f"    ⚠️ Back verification failed: {e}")
                back_success = False
            
            if back_success:
                print(f"    ✅ BACK succeeded - both directions valid")
            else:
                print(f"    ⚠️ BACK failed - only forward edge created")
            
            # 4. Create node and edge (node name already generated above for duplicate check)
            
            # Calculate position
            position_x = 250 + (len(self.created_nodes) % 3) * 300
            position_y = 250 + (len(self.created_nodes) // 3) * 200
            
            # Create node
            node_data = self.node_generator.create_node_data(
                node_name=new_node_name,
                position={'x': position_x, 'y': position_y},
                ai_analysis={
                    'suggested_name': item,
                    'screen_type': 'screen',
                    'reasoning': f'Reached by clicking {item}'
                },
                node_type='screen'
            )
            
            node_result = save_node(self.tree_id, node_data, self.team_id)
            if node_result['success']:
                self.created_nodes.append(new_node_name)
                print(f"    ✅ Created node: {new_node_name}")
            else:
                print(f"    ❌ Failed to create node: {node_result.get('error')}")
                continue
            
            # Create edge with bidirectional action sets
            forward_actions = [
                {'command': 'click_element', 'params': {'text': item}, 'delay': 2000}
            ]
            
            backward_actions = [
                {'command': 'press_key', 'params': {'key': 'BACK'}, 'delay': 2000}
            ] if back_success else []
            
            edge_data = self.node_generator.create_edge_data(
                source=current_node,
                target=new_node_name,
                actions=forward_actions,
                reverse_actions=backward_actions
            )
            
            edge_result = save_edge(self.tree_id, edge_data, self.team_id)
            if edge_result['success']:
                self.created_edges.append(edge_data['edge_id'])
                print(f"    ✅ Created edge: {current_node} ↔ {new_node_name} ({'bidirectional' if back_success else 'forward only'})")
        
        print(f"\n[@exploration_engine] Simple exploration complete: {len(self.created_nodes)-1} nodes, {len(self.created_edges)} edges")
    
    def _validate_dpad_based(
        self,
        current_node: str,
        parent_screenshot: str,
        prediction: Dict,
        depth: int
    ):
        """
        TV/STB validation: DPAD-based navigation (AI verification required)
        
        Workflow:
        1. Navigate to item using DPAD
        2. AI verifies focus
        3. Press OK
        4. AI verifies new screen
        5. Press BACK
        6. AI verifies back to source
        
        Args:
            current_node: Current node name
            parent_screenshot: Screenshot at current position
            prediction: AI prediction
            depth: Current depth
        """
        # Call existing DPAD exploration logic
        self._explore_with_prediction(
            current_node=current_node,
            parent_screenshot=parent_screenshot,
            prediction=prediction,
            depth=depth
        )
    
    def _explore_with_prediction(
        self,
        current_node: str,
        parent_screenshot: str,
        prediction: Dict,
        depth: int
    ):
        """
        SMART exploration using AI prediction
        
        Strategy:
        1. Use predicted items to guide exploration
        2. Use menu type to determine navigation method
        3. Confirm predictions vs discover new items
        4. Recurse deeper for confirmed items
        
        Args:
            current_node: Current node name (with _temp)
            parent_screenshot: Screenshot at current position
            prediction: AI prediction (menu_type, items, etc)
            depth: Current depth in exploration
        """
        if depth >= self.depth_limit:
            print(f"[@exploration_engine] Max depth {self.depth_limit} reached")
            return
        
        print(f"\n[@exploration_engine] Smart Exploring: {current_node} (depth={depth})")
        
        # Extract prediction info
        menu_type = prediction.get('menu_type', 'mixed')
        predicted_items = prediction.get('items', [])
        
        print(f"  Menu Type: {menu_type}")
        print(f"  Predicted Items: {predicted_items}")
        
        confirmed_nodes = []
        
        # STRATEGY: Use prediction to guide exploration
        if menu_type == 'horizontal' and predicted_items:
            # Horizontal menu: Press RIGHT to move between items
            print(f"  🎯 Strategy: Horizontal menu with {len(predicted_items)} predicted items")
            
            for i, predicted_item in enumerate(predicted_items):
                print(f"\n  [{i+1}/{len(predicted_items)}] Looking for: {predicted_item}")
                
                # Move to position (press RIGHT i times from start)
                if i > 0:
                    self.navigation_strategy.test_direction('RIGHT', wait_time=500)
                
                # Press OK to enter
                ok_result = self.navigation_strategy.press_ok_and_analyze(parent_screenshot)
                
                # Notify progress
                if self.progress_callback and ok_result.get('screenshot'):
                    self.progress_callback(
                        step=f"Phase 2: Exploring item {i+1}/{len(predicted_items)}: {predicted_item}",
                        screenshot=ok_result['screenshot'],
                        analysis=ok_result.get('analysis')
                    )
                
                if ok_result['success'] and ok_result['is_new_screen']:
                    analysis = ok_result['analysis']
                    suggested_name = analysis.get('suggested_name', 'screen')
                    
                    # Check if prediction was correct
                    if predicted_item.lower() in suggested_name.lower():
                        print(f"  ✅ CONFIRMED: {predicted_item} (AI was right!)")
                    else:
                        print(f"  ⚠️  ADJUSTED: Expected '{predicted_item}', found '{suggested_name}'")
                    
                    # Create node with actual name
                    new_node_name = self.node_generator.generate_node_name(
                        ai_suggestion=suggested_name,
                        parent_node=current_node,
                        context_visible=analysis.get('context_visible', False)
                    )
                    
                    # Create and save node
                    confirmed_nodes.append(self._create_node_and_edge(
                        parent_node=current_node,
                        new_node_name=new_node_name,
                        analysis=analysis,
                        navigation_actions=[
                            {'command': 'RIGHT', 'params': {}, 'delay': 500} if i > 0 else None,
                            {'command': 'OK', 'params': {}, 'delay': 1000}
                        ],
                        after_screenshot=ok_result['after_screenshot'],
                        depth=depth
                    ))
                    
                    # Press BACK to return to menu
                    self.navigation_strategy.press_back_and_return()
                else:
                    print(f"  ⏭️  No new screen found")
                    self.navigation_strategy.press_back_and_return()
        
        elif menu_type == 'vertical' and predicted_items:
            # Vertical menu: Press DOWN to move between items
            print(f"  🎯 Strategy: Vertical menu with {len(predicted_items)} predicted items")
            
            for i, predicted_item in enumerate(predicted_items):
                print(f"\n  [{i+1}/{len(predicted_items)}] Looking for: {predicted_item}")
                
                if i > 0:
                    self.navigation_strategy.test_direction('DOWN', wait_time=500)
                
                ok_result = self.navigation_strategy.press_ok_and_analyze(parent_screenshot)
                
                if ok_result['success'] and ok_result['is_new_screen']:
                    analysis = ok_result['analysis']
                    suggested_name = analysis.get('suggested_name', 'screen')
                    
                    if predicted_item.lower() in suggested_name.lower():
                        print(f"  ✅ CONFIRMED: {predicted_item}")
                    else:
                        print(f"  ⚠️  ADJUSTED: Expected '{predicted_item}', found '{suggested_name}'")
                    
                    new_node_name = self.node_generator.generate_node_name(
                        ai_suggestion=suggested_name,
                        parent_node=current_node,
                        context_visible=analysis.get('context_visible', False)
                    )
                    
                    confirmed_nodes.append(self._create_node_and_edge(
                        parent_node=current_node,
                        new_node_name=new_node_name,
                        analysis=analysis,
                        navigation_actions=[
                            {'command': 'DOWN', 'params': {}, 'delay': 500} if i > 0 else None,
                            {'command': 'OK', 'params': {}, 'delay': 1000}
                        ],
                        after_screenshot=ok_result['after_screenshot'],
                        depth=depth
                    ))
                    
                    self.navigation_strategy.press_back_and_return()
        
        else:
            # Grid or mixed: Fallback to testing all directions
            print(f"  🎯 Strategy: Grid/Mixed menu - testing all directions")
            
            directions = self.navigation_strategy.get_directions_to_test(menu_type)
            
            for direction in directions:
                print(f"\n  Testing {direction}...")
                
                success = self.navigation_strategy.test_direction(direction, wait_time=500)
                
                if success:
                    ok_result = self.navigation_strategy.press_ok_and_analyze(parent_screenshot)
                    
                    if ok_result['success'] and ok_result['is_new_screen']:
                        analysis = ok_result['analysis']
                        
                        new_node_name = self.node_generator.generate_node_name(
                            ai_suggestion=analysis.get('suggested_name', 'screen'),
                            parent_node=current_node,
                            context_visible=analysis.get('context_visible', False)
                        )
                        
                        confirmed_nodes.append(self._create_node_and_edge(
                            parent_node=current_node,
                            new_node_name=new_node_name,
                            analysis=analysis,
                            navigation_actions=[
                                {'command': direction, 'params': {}, 'delay': 500},
                                {'command': 'OK', 'params': {}, 'delay': 1000}
                            ],
                            after_screenshot=ok_result['after_screenshot'],
                            depth=depth
                        ))
                        
                        self.navigation_strategy.press_back_and_return()
        
        # Recurse deeper into confirmed nodes
        print(f"\n[@exploration_engine] Recursing into {len(confirmed_nodes)} confirmed nodes...")
        
        for node_info in confirmed_nodes:
            if node_info and depth + 1 < self.depth_limit:
                # For deeper levels, re-analyze the screen to get new prediction
                new_screenshot = node_info.get('screenshot')
                
                if new_screenshot:
                    # Get fresh prediction for this screen
                    deeper_prediction = self.screen_analyzer.anticipate_tree(new_screenshot)
                    
                    # Recurse with new prediction
                    self._explore_with_prediction(
                        current_node=node_info['node_name'],
                        parent_screenshot=new_screenshot,
                        prediction=deeper_prediction,
                        depth=depth + 1
                    )
    
    def _create_node_and_edge(
        self,
        parent_node: str,
        new_node_name: str,
        analysis: Dict,
        navigation_actions: List[Dict],
        after_screenshot: str,
        depth: int
    ) -> Dict:
        """
        Helper to create node and edge, returns node info for recursion
        
        Returns:
            Dict with node_name and screenshot for deeper exploration
        """
        # Calculate position (simple grid layout)
        position_x = 250 + (len(self.created_nodes) % 3) * 300
        position_y = 250 + (len(self.created_nodes) // 3) * 200
        
        # Create node
        node_data = self.node_generator.create_node_data(
            node_name=new_node_name,
            position={'x': position_x, 'y': position_y},
            ai_analysis=analysis
        )
        
        # Save node to database
        node_result = save_node(self.tree_id, node_data, self.team_id)
        
        if not node_result['success']:
            print(f"    ❌ Failed to create node: {node_result.get('error')}")
            return None
        
        self.created_nodes.append(new_node_name)
        print(f"    ✅ Created node: {new_node_name}")
        
        # Create edge from parent to new node
        # Filter out None actions
        clean_actions = [a for a in navigation_actions if a is not None]
        
        edge_data = self.node_generator.create_edge_data(
            source=parent_node,
            target=new_node_name,
            actions=clean_actions
        )
        
        edge_result = save_edge(self.tree_id, edge_data, self.team_id)
        
        if edge_result['success']:
            self.created_edges.append(edge_data['edge_id'])
            print(f"    ✅ Created edge: {parent_node} → {new_node_name}")
        
        # Check if subtree should be created
        if self.node_generator.should_create_subtree(new_node_name, depth + 1):
            print(f"    🌲 Creating subtree for: {new_node_name}")
            
            subtree_result = create_sub_tree(
                parent_tree_id=self.tree_id,
                parent_node_id=new_node_name,
                tree_data={
                    'name': f'{new_node_name}_subtree',
                    'userinterface_id': None
                },
                team_id=self.team_id
            )
            
            if subtree_result['success']:
                self.created_subtrees.append(subtree_result['tree']['id'])
                print(f"    ✅ Subtree created: {subtree_result['tree']['id']}")
        
        return {
            'node_name': new_node_name,
            'screenshot': after_screenshot
        }

