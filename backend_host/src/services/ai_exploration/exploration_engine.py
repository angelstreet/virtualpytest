"""
Exploration Engine - Main orchestrator for AI-driven navigation tree generation
Coordinates screen analysis, navigation, and tree building
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional
import traceback

from services.ai_exploration.screen_analyzer import ScreenAnalyzer
from services.ai_exploration.navigation_strategy import NavigationStrategy
from services.ai_exploration.node_generator import NodeGenerator
from shared.src.lib.database.navigation_trees_db import (
    save_node,
    save_edge,
    create_sub_tree,
    get_tree_metadata
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
        
        Note: Exploration depth is FIXED at 2 levels (level-1 main items + level-2 sub-items)
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
        
        # 4. Create node and edge
        new_node_name = f"{item}_temp"
        
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
        Mobile/Web validation: FIXED 2-LEVEL EXPLORATION
        
        Level 1: Main navigation items (home → settings, tv_guide, etc.)
        Level 2: Sub-navigation items (settings → settings_wifi, settings_bluetooth, etc.)
        
        Workflow for each level-1 item:
        1. Click level-1 element
        2. Wait and analyze screen for level-2 items
        3. Create subtree with parent_child naming (e.g., settings_wifi)
        4. For each level-2 item: click, test, create node/edge
        5. Navigate back to level-1
        6. Navigate back to home
        
        Args:
            current_node: Current node name (e.g., 'home_temp')
            prediction: AI prediction with items to click
            depth: Current depth (0=home, 1=main items, 2=sub-items)
        """
        print(f"\n[@exploration_engine] 📱 MOBILE/WEB 2-LEVEL EXPLORATION: {current_node} (depth={depth})")
        
        predicted_items = prediction.get('items', [])
        print(f"  Level-1 items to explore: {len(predicted_items)}")
        
        # Get a known source element to verify BACK (use first non-target item or 'Home')
        home_indicator = predicted_items[0] if predicted_items else 'Home'
        
        import time
        
        # ════════════════════════════════════════════════════════════════
        # LEVEL 1: Explore main navigation items
        # ════════════════════════════════════════════════════════════════
        for i, level1_item in enumerate(predicted_items):
            print(f"\n  ┌─ LEVEL 1 [{i+1}/{len(predicted_items)}]: {level1_item}")
            
            # Notify progress
            if self.progress_callback:
                self.progress_callback(
                    step=f"Level 1: Exploring {i+1}/{len(predicted_items)}: {level1_item}",
                    screenshot=None,
                    analysis={'screen_name': level1_item, 'elements_found': [level1_item], 'reasoning': f'Clicking on {level1_item}'}
                )
            
            # 1.1. Click level-1 element
            click_success = False
            if level1_item.startswith('dynamic_'):
                print(f"    ⚠️ Dynamic element {level1_item} - skipping")
                continue
            else:
                try:
                    result = self.controller.click_element(text=level1_item)
                    click_success = result if isinstance(result, bool) else result.get('success', False)
                except Exception as e:
                    print(f"    ❌ Click failed: {e}")
                    click_success = False
            
            if not click_success:
                print(f"    ⏭️ Click failed - skipping {level1_item}")
                continue
            
            print(f"    ✅ Level-1 click succeeded")
            time.sleep(2)
            
            # 1.2. Generate level-1 node name (e.g., "TV Guide Tab" → "tvguide")
            level1_node_name = f"{self.node_generator.target_to_node_name(level1_item)}_temp"
            
            # 1.3. Get UI dump for level-2 analysis
            print(f"    📊 Analyzing screen for level-2 items...")
            try:
                level2_prediction = self.screen_analyzer.anticipate_tree(None)  # Analyze current screen
                level2_items = level2_prediction.get('items', [])
                print(f"    ✅ Found {len(level2_items)} level-2 items: {level2_items[:5]}...")
            except Exception as e:
                print(f"    ⚠️ Level-2 analysis failed: {e}")
                level2_items = []
            
            # ════════════════════════════════════════════════════════════════
            # LEVEL 2: Explore sub-navigation items (if any)
            # ════════════════════════════════════════════════════════════════
            level2_nodes_created = []
            if level2_items:
                print(f"    │")
                print(f"    ├─ LEVEL 2: Exploring {len(level2_items)} sub-items")
                
                for j, level2_item in enumerate(level2_items[:10]):  # Limit to 10 sub-items
                    print(f"    │  ├─ [{j+1}/{min(len(level2_items), 10)}]: {level2_item}")
                    
                    # 2.1. Click level-2 element
                    click2_success = False
                    if level2_item.startswith('dynamic_'):
                        print(f"    │  │  ⚠️ Dynamic element - skipping")
                        continue
                    else:
                        try:
                            result2 = self.controller.click_element(text=level2_item)
                            click2_success = result2 if isinstance(result2, bool) else result2.get('success', False)
                        except Exception as e:
                            print(f"    │  │  ❌ Click failed: {e}")
                            click2_success = False
                    
                    if not click2_success:
                        print(f"    │  │  ⏭️ Click failed - skipping")
                        continue
                    
                    print(f"    │  │  ✅ Click succeeded")
                    time.sleep(2)
                    
                    # 2.2. Press BACK to return to level-1
                    print(f"    │  │  ⬅️ Pressing BACK to level-1...")
                    try:
                        self.controller.press_key('BACK')
                        time.sleep(2)
                        
                        # Verify we're back on level-1 (check for level1_item)
                        is_back = self.controller.wait_for_element_by_text(
                            text=level2_items[0] if level2_items else level1_item,
                            timeout=3
                        )
                        back2_success = is_back if isinstance(is_back, bool) else is_back.get('success', False)
                    except Exception as e:
                        print(f"    │  │  ⚠️ BACK failed: {e}")
                        back2_success = False
                    
                    if back2_success:
                        print(f"    │  │  ✅ BACK succeeded")
                    else:
                        print(f"    │  │  ⚠️ BACK failed")
                    
                    # 2.3. Generate level-2 node name with parent prefix (e.g., "settings_wifi_temp")
                    level2_base_name = self.node_generator.target_to_node_name(level2_item)
                    level1_base_name = level1_node_name.replace('_temp', '')
                    level2_node_name = f"{level1_base_name}_{level2_base_name}_temp"
                    
                    # 2.4. Create level-2 node
                    position_x = 250 + (len(self.created_nodes) % 5) * 250
                    position_y = 400 + (len(self.created_nodes) // 5) * 180
                    
                    node2_data = self.node_generator.create_node_data(
                        node_name=level2_node_name,
                        position={'x': position_x, 'y': position_y},
                        ai_analysis={
                            'suggested_name': level2_item,
                            'screen_type': 'screen',
                            'reasoning': f'Sub-item of {level1_item}'
                        },
                        node_type='screen'
                    )
                    
                    node2_result = save_node(self.tree_id, node2_data, self.team_id)
                    if node2_result['success']:
                        self.created_nodes.append(level2_node_name)
                        level2_nodes_created.append(level2_node_name)
                        print(f"    │  │  ✅ Created node: {level2_node_name}")
                    else:
                        print(f"    │  │  ❌ Failed to create node: {node2_result.get('error')}")
                        continue
                    
                    # 2.5. Create level-2 edge (level1 → level2)
                    forward2_actions = [
                        {'command': 'click_element', 'params': {'text': level2_item}, 'delay': 2000}
                    ]
                    backward2_actions = [
                        {'command': 'press_key', 'params': {'key': 'BACK'}, 'delay': 2000}
                    ] if back2_success else []
                    
                    edge2_data = self.node_generator.create_edge_data(
                        source=level1_node_name,
                        target=level2_node_name,
                        actions=forward2_actions,
                        reverse_actions=backward2_actions
                    )
                    
                    edge2_result = save_edge(self.tree_id, edge2_data, self.team_id)
                    if edge2_result['success']:
                        self.created_edges.append(edge2_data['edge_id'])
                        print(f"    │  │  ✅ Created edge: {level1_node_name} ↔ {level2_node_name}")
            
            # ════════════════════════════════════════════════════════════════
            # Back to home from level-1
            # ════════════════════════════════════════════════════════════════
            print(f"    │")
            print(f"    └─ ⬅️ Returning to home...")
            try:
                self.controller.press_key('BACK')
                time.sleep(2)
                
                # Verify we're back home
                is_home = self.controller.wait_for_element_by_text(
                    text=home_indicator,
                    timeout=5
                )
                back1_success = is_home if isinstance(is_home, bool) else is_home.get('success', False)
            except Exception as e:
                print(f"       ⚠️ BACK to home failed: {e}")
                back1_success = False
            
            if back1_success:
                print(f"       ✅ BACK to home succeeded")
            else:
                print(f"       ⚠️ BACK to home failed")
            
            # ════════════════════════════════════════════════════════════════
            # Create level-1 node and edge (home → level1)
            # ════════════════════════════════════════════════════════════════
            position_x = 250 + (len(self.created_nodes) % 5) * 250
            position_y = 250
            
            node1_data = self.node_generator.create_node_data(
                node_name=level1_node_name,
                position={'x': position_x, 'y': position_y},
                ai_analysis={
                    'suggested_name': level1_item,
                    'screen_type': 'screen',
                    'reasoning': f'Main navigation item'
                },
                node_type='screen'
            )
            
            node1_result = save_node(self.tree_id, node1_data, self.team_id)
            if node1_result['success']:
                self.created_nodes.append(level1_node_name)
                print(f"       ✅ Created level-1 node: {level1_node_name}")
            else:
                print(f"       ❌ Failed to create level-1 node: {node1_result.get('error')}")
                continue
            
            # Create level-1 edge (home → level1)
            forward1_actions = [
                {'command': 'click_element', 'params': {'text': level1_item}, 'delay': 2000}
            ]
            backward1_actions = [
                {'command': 'press_key', 'params': {'key': 'BACK'}, 'delay': 2000}
            ] if back1_success else []
            
            edge1_data = self.node_generator.create_edge_data(
                source=current_node,
                target=level1_node_name,
                actions=forward1_actions,
                reverse_actions=backward1_actions
            )
            
            edge1_result = save_edge(self.tree_id, edge1_data, self.team_id)
            if edge1_result['success']:
                self.created_edges.append(edge1_data['edge_id'])
                print(f"       ✅ Created edge: {current_node} ↔ {level1_node_name}")
            
            # ════════════════════════════════════════════════════════════════
            # Create subtree for level-1 node (if level-2 nodes exist)
            # ════════════════════════════════════════════════════════════════
            if level2_nodes_created:
                print(f"       🌲 Creating subtree for {level1_node_name}...")
                subtree_name = level1_node_name.replace('_temp', '')
                
                subtree_result = create_sub_tree(
                    parent_tree_id=self.tree_id,
                    parent_node_id=level1_node_name,
                    tree_data={
                        'name': f'{subtree_name}_subtree',
                        'userinterface_id': None
                    },
                    team_id=self.team_id
                )
                
                if subtree_result['success']:
                    self.created_subtrees.append(subtree_result['tree']['id'])
                    print(f"       ✅ Subtree created with {len(level2_nodes_created)} children")
        
        print(f"\n[@exploration_engine] 2-level exploration complete:")
        print(f"  → Level-1 nodes: {len([n for n in self.created_nodes if n.count('_') == 1])}")
        print(f"  → Level-2 nodes: {len([n for n in self.created_nodes if n.count('_') >= 2])}")
        print(f"  → Total edges: {len(self.created_edges)}")
        print(f"  → Subtrees: {len(self.created_subtrees)}")
    
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

