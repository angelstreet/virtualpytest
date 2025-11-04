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
from backend_host.src.services.controller.controller_factory import ControllerFactory
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
        device_id: str,
        host_name: str,
        device_model_name: str,
        team_id: str,
        userinterface_name: str,
        depth_limit: int = 5
    ):
        """
        Initialize exploration engine
        
        Args:
            tree_id: Tree ID to add nodes to
            device_id: Device ID
            host_name: Host name
            device_model_name: Device model (e.g., 'android_mobile')
            team_id: Team ID
            userinterface_name: UI name (e.g., 'horizon_android_mobile')
            depth_limit: Maximum depth to explore
        """
        self.tree_id = tree_id
        self.device_id = device_id
        self.host_name = host_name
        self.device_model_name = device_model_name
        self.team_id = team_id
        self.userinterface_name = userinterface_name
        self.depth_limit = depth_limit
        
        # Initialize components
        self.screen_analyzer = ScreenAnalyzer(device_id, host_name)
        self.controller = ControllerFactory.get_controller(device_model_name)
        self.navigation_strategy = NavigationStrategy(self.controller, self.screen_analyzer)
        self.node_generator = NodeGenerator(tree_id, team_id)
        
        # Exploration state
        self.created_nodes = []
        self.created_edges = []
        self.created_subtrees = []
        self.exploration_log = []
        
    def start_exploration(self) -> Dict:
        """
        Main exploration flow
        
        Returns:
            {
                'success': True,
                'nodes_created': 3,
                'edges_created': 2,
                'subtrees_created': 1,
                'exploration_log': [...]
            }
        """
        try:
            print(f"\n{'='*60}")
            print(f"[@exploration_engine] Starting AI Exploration")
            print(f"Tree: {self.tree_id}")
            print(f"Device: {self.device_model_name} ({self.device_id})")
            print(f"Depth Limit: {self.depth_limit}")
            print(f"{'='*60}\n")
            
            # PHASE 1: Anticipation - AI predicts tree structure
            initial_screenshot = self.screen_analyzer.capture_screenshot()
            if not initial_screenshot:
                return {
                    'success': False,
                    'error': 'Failed to capture initial screenshot'
                }
            
            prediction = self._phase1_anticipation(initial_screenshot)
            
            # PHASE 2: Validation - Explore to validate prediction
            self._phase2_validation(prediction, initial_screenshot)
            
            # Summary
            print(f"\n{'='*60}")
            print(f"[@exploration_engine] Exploration Complete!")
            print(f"Nodes created: {len(self.created_nodes)}")
            print(f"Edges created: {len(self.created_edges)}")
            print(f"Subtrees created: {len(self.created_subtrees)}")
            print(f"{'='*60}\n")
            
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
            print(f"[@exploration_engine:start_exploration] Error: {e}")
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e),
                'exploration_log': self.exploration_log
            }
    
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
        Phase 2: Depth-first exploration to validate prediction
        
        Args:
            prediction: AI prediction from phase 1
            initial_screenshot: Path to initial screenshot
        """
        print(f"\n[@exploration_engine] === PHASE 2: VALIDATION ===")
        
        # Create root node (home_temp)
        root_node_name = "home_temp"
        root_node_data = self.node_generator.create_node_data(
            node_name=root_node_name,
            position={'x': 250, 'y': 250},
            ai_analysis={
                'suggested_name': 'home',
                'screen_type': 'menu',
                'reasoning': 'Root node of exploration'
            },
            node_type='menu'
        )
        
        # Save root node to database
        result = save_node(self.tree_id, root_node_data, self.team_id)
        if result['success']:
            self.created_nodes.append(root_node_name)
            print(f"✅ Created root node: {root_node_name}")
        else:
            print(f"❌ Failed to create root node: {result.get('error')}")
            return
        
        # Start depth-first exploration from root
        self._explore_depth_first(
            current_node=root_node_name,
            parent_screenshot=initial_screenshot,
            depth=0,
            menu_type=prediction.get('menu_type', 'mixed')
        )
    
    def _explore_depth_first(
        self,
        current_node: str,
        parent_screenshot: str,
        depth: int,
        menu_type: str = 'mixed'
    ):
        """
        Recursive depth-first exploration
        
        Args:
            current_node: Current node name (with _temp)
            parent_screenshot: Screenshot at current position
            depth: Current depth in exploration
            menu_type: Menu type for direction testing
        """
        if depth >= self.depth_limit:
            print(f"[@exploration_engine] Max depth {self.depth_limit} reached")
            return
        
        print(f"\n[@exploration_engine] Exploring: {current_node} (depth={depth})")
        
        # Get directions to test based on menu type
        directions = self.navigation_strategy.get_directions_to_test(menu_type)
        print(f"Testing directions: {directions}")
        
        siblings_found = []
        
        # Test each direction to discover siblings
        for direction in directions:
            print(f"\n  Testing {direction}...")
            
            # Test direction (just move focus, don't analyze yet)
            success = self.navigation_strategy.test_direction(direction, wait_time=500)
            
            if success:
                # Now press OK to see if we enter a new screen
                ok_result = self.navigation_strategy.press_ok_and_analyze(parent_screenshot)
                
                if ok_result['success'] and ok_result['is_new_screen']:
                    # Found a new screen!
                    analysis = ok_result['analysis']
                    
                    print(f"  ✅ NEW SCREEN FOUND: {analysis.get('suggested_name')}")
                    
                    # Generate node name
                    new_node_name = self.node_generator.generate_node_name(
                        ai_suggestion=analysis.get('suggested_name', 'screen'),
                        parent_node=current_node,
                        context_visible=analysis.get('context_visible', False)
                    )
                    
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
                    
                    if node_result['success']:
                        self.created_nodes.append(new_node_name)
                        print(f"    ✅ Created node: {new_node_name}")
                        
                        # Create edge from current to new node
                        edge_data = self.node_generator.create_edge_data(
                            source=current_node,
                            target=new_node_name,
                            actions=[
                                {'command': direction, 'params': {}, 'delay': 500},
                                {'command': 'OK', 'params': {}, 'delay': 1000}
                            ]
                        )
                        
                        edge_result = save_edge(self.tree_id, edge_data, self.team_id)
                        
                        if edge_result['success']:
                            self.created_edges.append(edge_data['edge_id'])
                            print(f"    ✅ Created edge: {current_node} → {new_node_name}")
                        
                        # Check if subtree should be created
                        if self.node_generator.should_create_subtree(new_node_name, depth + 1):
                            print(f"    🌲 Creating subtree for: {new_node_name}")
                            
                            subtree_result = create_sub_tree(
                                parent_tree_id=self.tree_id,
                                parent_node_id=new_node_name,
                                tree_data={
                                    'name': f'{new_node_name}_subtree',
                                    'userinterface_id': None  # Inherits from parent
                                },
                                team_id=self.team_id
                            )
                            
                            if subtree_result['success']:
                                self.created_subtrees.append(subtree_result['tree']['id'])
                                print(f"    ✅ Subtree created: {subtree_result['tree']['id']}")
                        
                        # Remember this sibling for deeper exploration
                        siblings_found.append({
                            'node_name': new_node_name,
                            'screenshot': ok_result['after_screenshot']
                        })
                    
                    # Press BACK to return
                    self.navigation_strategy.press_back_and_return()
                else:
                    # Not a new screen or failed - just go back
                    print(f"  ⏭️  Same screen or failed, moving on...")
                    self.navigation_strategy.press_back_and_return()
            
            # Return to starting position for next direction test
            # (Simple approach: press opposite direction)
            opposite = {
                'RIGHT': 'LEFT',
                'LEFT': 'RIGHT',
                'UP': 'DOWN',
                'DOWN': 'UP'
            }.get(direction)
            
            if opposite:
                self.navigation_strategy.test_direction(opposite, wait_time=300)
        
        # Now explore each sibling depth-first
        print(f"\n[@exploration_engine] Exploring {len(siblings_found)} siblings deeper...")
        
        for sibling in siblings_found:
            # Navigate to sibling (we know the path)
            # For simplicity, we'll skip re-navigation in v1
            # Just recurse with sibling info
            
            # Recursive exploration
            self._explore_depth_first(
                current_node=sibling['node_name'],
                parent_screenshot=sibling['screenshot'],
                depth=depth + 1,
                menu_type='mixed'  # Re-analyze menu type for each screen
            )

