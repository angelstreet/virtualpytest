from typing import Dict, Any, List
import time
from backend_host.src.services.ai_exploration.node_generator import NodeGenerator
from shared.src.lib.database.navigation_trees_db import (
    get_node_by_id,
    save_nodes_batch,
    save_edges_batch,
    invalidate_navigation_cache_for_tree
)

def continue_exploration(executor, team_id: str, selected_items: List[str] = None, selected_screen_items: List[str] = None) -> Dict[str, Any]:
    """
    Phase 2a: Create nodes and edges structure for selected items
    
    Args:
        executor: ExplorationExecutor instance
        team_id: Team ID
        selected_items: List of focus nodes to create
        selected_screen_items: List of screen nodes to create (TV only)
    
    Returns:
        {
            'success': True,
            'nodes_created': 11,
            'edges_created': 10
        }
    """
    print(f"\n{'='*80}")
    print(f"[@ExplorationExecutor:continue_exploration] 🚀 PHASE 2: STRUCTURE CREATION STARTED")
    print(f"{'='*80}")
    
    with executor._lock:
        if not executor.current_exploration_id:
            return {'success': False, 'error': 'No active exploration'}
        
        if executor.exploration_state['status'] != 'awaiting_approval':
            return {
                'success': False,
                'error': f"Cannot continue: status is {executor.exploration_state['status']}"
            }
        
        tree_id = executor.exploration_state['tree_id']
        exploration_plan = executor.exploration_state.get('exploration_plan', {})
        all_items = exploration_plan.get('items', [])
        
        print(f"[@ExplorationExecutor:continue_exploration] All items from plan: {all_items}")
        print(f"[@ExplorationExecutor:continue_exploration] Received selected_items: {selected_items}")
        print(f"[@ExplorationExecutor:continue_exploration] 🔍 Exploration Plan Keys: {list(exploration_plan.keys())}")
        print(f"[@ExplorationExecutor:continue_exploration] 📊 Strategy from plan: {exploration_plan.get('strategy', 'NOT_FOUND')}")
        print(f"[@ExplorationExecutor:continue_exploration] 📊 Menu Type from plan: {exploration_plan.get('menu_type', 'NOT_FOUND')}")
        
        # ✅ Filter items based on user selection
        if selected_items is not None and len(selected_items) > 0:
            items = [item for item in all_items if item in selected_items]
            print(f"[@ExplorationExecutor:continue_exploration] ✅ User selected {len(items)}/{len(all_items)} items: {items}")
        else:
            items = all_items
            print(f"[@ExplorationExecutor:continue_exploration] ⚠️ No selection provided - creating all {len(items)} items")
        
        print(f"\n{'='*80}")
        print(f"[@ExplorationExecutor:continue_exploration] 📋 EDGE CREATION STRATEGY")
        print(f"{'='*80}")
        
        # Get strategy from exploration plan
        strategy = exploration_plan.get('strategy', 'click')
        menu_type = exploration_plan.get('menu_type', 'horizontal')
        lines = exploration_plan.get('lines', [])  # Row structure: [['home', 'tv guide', ...], ['watch'], ...]
        
        print(f"[@ExplorationExecutor:continue_exploration] 🎯 Strategy: {strategy}")
        print(f"[@ExplorationExecutor:continue_exploration] 🎯 Menu Type: {menu_type}")
        print(f"[@ExplorationExecutor:continue_exploration] 🎯 Device Model: {executor.device_model}")
        print(f"[@ExplorationExecutor:continue_exploration] 🎯 Row Structure: {len(lines)} rows")
        for row_idx, row_items in enumerate(lines):
            print(f"[@ExplorationExecutor:continue_exploration]    Row {row_idx + 1}: {len(row_items)} items - {row_items[:3]}{'...' if len(row_items) > 3 else ''}")
        
        if strategy in ['dpad_with_screenshot', 'test_dpad_directions']:
            print(f"[@ExplorationExecutor:continue_exploration] ✅ Will create D-PAD edges (press_key)")
        else:
            print(f"[@ExplorationExecutor:continue_exploration] ✅ Will create CLICK edges (click_element)")
        
        print(f"{'='*80}\n")
        
        print(f"[@ExplorationExecutor:continue_exploration] Creating structure for {executor.current_exploration_id}")
        
        node_gen = NodeGenerator(tree_id, team_id)
        
        # Get start node from state, default to 'home'
        start_node_label = executor.exploration_state.get('start_node', 'home')
        print(f"[@ExplorationExecutor:continue_exploration] 🏁 Start Node Label: {start_node_label}")
        
        # Start node should already exist
        start_node_result = get_node_by_id(tree_id, start_node_label, team_id)
        if not (start_node_result.get('success') and start_node_result.get('node')):
            return {'success': False, 'error': f"Start node '{start_node_label}' does not exist."}
        
        start_node_id = start_node_result['node']['node_id']
        nodes_created = []
        print(f"  ♻️  Using existing '{start_node_id}' node as START NODE")
        print(f"  🔍 Start Node ID: {start_node_id}")
        
        # ✅ BATCH COLLECTION: Collect all nodes and edges before saving
        nodes_to_save = []
        edges_to_save = []
        
        # ✅ NEW: DUAL-LAYER ARCHITECTURE for TV navigation
        if strategy in ['dpad_with_screenshot', 'test_dpad_directions']:
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
                    
                    # ✅ ALWAYS include start_node - it's the anchor for the menu structure
                    if node_name_clean.lower() == start_node_label.lower() or node_name_clean.lower() in ['home', 'accueil'] and start_node_label == 'home':
                        all_focus_nodes_row1.append(start_node_id)
                        print(f"    ♻️  Using existing '{start_node_id}' node (Row 1 anchor)")
                        continue
                    
                    # Only process OTHER selected items (start_node is always included)
                    if original_item not in items:
                        continue
                    
                    # Create FOCUS node (menu position): start_node_tvguide, start_node_apps, etc.
                    focus_node_name = f"{start_node_id}_{node_name_clean}"
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
                        executor.exploration_state['target_to_node_map'][original_item] = screen_node_name
                        print(f"    ✅ Created SCREEN node: {screen_node_name}_temp")
                    else:
                        print(f"    ⏭️  Skipped SCREEN node: {node_name_clean} (not selected)")
                
                print(f"\n  📊 Row 1 complete: {len(all_focus_nodes_row1)} focus nodes")
                
                # Step 1b: Create HORIZONTAL edges for Row 1 (outwards from 'home')
                print(f"\n  ➡️  Creating HORIZONTAL edges (Row 1 menu navigation):")
                
                try:
                    start_idx = all_focus_nodes_row1.index(start_node_id)
                except ValueError:
                    start_idx = 0
                    print(f"  ⚠️ '{start_node_id}' node not found in row 1, defaulting to index 0")

                # 1. Right side: Start Node -> Right (Action: RIGHT)
                for idx in range(start_idx, len(all_focus_nodes_row1) - 1):
                    source_focus = all_focus_nodes_row1[idx]
                    target_focus = all_focus_nodes_row1[idx + 1]
                    
                    # Forward: RIGHT, Reverse: LEFT
                    edge_horizontal = node_gen.create_edge_data(
                        source=source_focus,
                        target=target_focus,
                        actions=[{
                            "command": "press_key",
                            "action_type": "remote",
                            "params": {
                                "key": "RIGHT",
                                "wait_time": 2000
                            }
                        }],
                        reverse_actions=[{
                            "command": "press_key",
                            "action_type": "remote",
                            "params": {
                                "key": "LEFT",
                                "wait_time": 2000
                            }
                        }],
                        label=f"{source_focus}_to_{target_focus}_temp"
                    )
                    edges_to_save.append(edge_horizontal)
                    print(f"    ↔ {source_focus} → {target_focus}: RIGHT/LEFT")

                # 2. Left side: Start Node -> Left (Action: LEFT)
                # Iterate backwards from start node to start of list
                for idx in range(start_idx, 0, -1):
                    source_focus = all_focus_nodes_row1[idx]
                    target_focus = all_focus_nodes_row1[idx - 1]
                    
                    # Forward: LEFT, Reverse: RIGHT
                    edge_horizontal = node_gen.create_edge_data(
                        source=source_focus,
                        target=target_focus,
                        actions=[{
                            "command": "press_key",
                            "action_type": "remote",
                            "params": {
                                "key": "LEFT",
                                "wait_time": 2000
                            }
                        }],
                        reverse_actions=[{
                            "command": "press_key",
                            "action_type": "remote",
                            "params": {
                                "key": "RIGHT",
                                "wait_time": 2000
                            }
                        }],
                        label=f"{source_focus}_to_{target_focus}_temp"
                    )
                    edges_to_save.append(edge_horizontal)
                    print(f"    ↔ {source_focus} → {target_focus}: LEFT/RIGHT")
                    
            # ========== ROW 2+: VERTICAL MENU (DOWN/UP from start node) ==========
            if len(lines) > 1:
                print(f"\n  📊 Processing Rows 2-{len(lines)} (vertical menu): {len(lines) - 1} rows")
                
                prev_vertical_focus = start_node_id  # Start from start_node for vertical navigation
                
                for row_idx in range(1, len(lines)):
                    row_items = lines[row_idx]
                    print(f"\n  📊 Processing Row {row_idx + 1}: {len(row_items)} items")
                    
                    for idx, original_item in enumerate(row_items):
                        # Only process selected items
                        if original_item not in items:
                            continue
                        
                        node_name_clean = node_gen.target_to_node_name(original_item)
                        
                        # Create FOCUS node for vertical position
                        focus_node_name = f"{start_node_id}_{node_name_clean}"
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
                                "action_type": "remote",
                                "params": {
                                    "key": "DOWN",
                                    "wait_time": 2000
                                }
                            }],
                            reverse_actions=[{
                                "command": "press_key",
                                "action_type": "remote",
                                "params": {
                                    "key": "UP",
                                    "wait_time": 2000
                                }
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
                            executor.exploration_state['target_to_node_map'][original_item] = screen_node_name
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
                        "action_type": "remote",
                        "params": {
                            "key": "OK",
                            "wait_time": 8000
                        }
                    }],
                    reverse_actions=[{
                        "command": "press_key",
                        "action_type": "remote",
                        "params": {
                            "key": "BACK",
                            "wait_time": 6000
                        }
                    }],
                    label=f"{focus_node}_to_{screen_node}_temp"
                )
                edges_to_save.append(edge_vertical)
                print(f"    ↕ {focus_node} ↔ {screen_node}: OK/BACK (bidirectional)")
            
            print(f"\n{'='*80}")
            print(f"  ✅ TV NAVIGATION COMPLETE")
            print(f"     Row 1 (horizontal): {len(all_focus_nodes_row1)} focus nodes")
            print(f"     Rows 2+ (vertical): {len(all_vertical_focus_nodes)} focus nodes")
            print(f"     Screen nodes: {len(focus_screen_pairs)} total")
            print(f"     Edges created: {len(edges_to_save)} bidirectional edges")
            print(f"{'='*80}\n")
            
        else:
            # MOBILE/WEB: Original click-based navigation
            print(f"\n  📱 MOBILE/WEB MODE: Creating click-based structure")
            
            # Create child nodes and edges
            for idx, item in enumerate(items):
                node_name_clean = node_gen.target_to_node_name(item)
                
                # Skip start nodes - they already exist
                if node_name_clean == start_node_label or node_name_clean == start_node_id:
                    print(f"  ⏭️  Skipping '{node_name_clean}' (start node already exists)")
                    continue
                
                # ✅ Use clean node_id, add _temp to label for visual distinction
                node_name = node_name_clean
                position_x = 250 + (idx % 5) * 200
                position_y = 300 + (idx // 5) * 150
                
                # Create node data
                node_data = node_gen.create_node_data(
                    node_name=node_name,
                    label=f"{node_name}_temp",  # Add _temp to label only
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
                executor.exploration_state['target_to_node_map'][item] = node_name
                
                # Click navigation for mobile/web
                print(f"  📱 Creating CLICK edge for '{item}': click_element(\"{item}\")")
                print(f"  🔍 Edge Details:")
                print(f"     - Source (Start): {start_node_id}")
                print(f"     - Target (New):   {node_name}")
                print(f"     - Action:         click_element('{item}')")
                
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
                    source=start_node_id,
                    target=node_name,
                    actions=forward_actions,
                    reverse_actions=reverse_actions,
                    label=f"{item}_temp"  # Add _temp to label for visual distinction
                )
                edges_to_save.append(edge_data)
        
        # ✅ REAL BATCH SAVE: Save all nodes in ONE database call
        print(f"  💾 Batch saving {len(nodes_to_save)} nodes...")
        if nodes_to_save:
            nodes_result = save_nodes_batch(tree_id, nodes_to_save, team_id)
            if nodes_result['success']:
                print(f"  ✅ Batch created {len(nodes_to_save)} nodes")
            else:
                print(f"  ❌ Failed to batch create nodes: {nodes_result.get('error')}")
        
        # ✅ REAL BATCH SAVE: Save all edges in ONE database call
        print(f"  💾 Batch saving {len(edges_to_save)} edges...")
        edges_created = []
        if edges_to_save:
            edges_result = save_edges_batch(tree_id, edges_to_save, team_id)
            if edges_result['success']:
                edges_created = [e['edge_id'] for e in edges_result['edges']]
                print(f"  ✅ Batch created {len(edges_to_save)} edges")
            else:
                print(f"  ❌ Failed to batch create edges: {edges_result.get('error')}")
        
        # ✅ CRITICAL: Invalidate cache IMMEDIATELY after batch saves
        # This prevents race condition where frontend gets stale cached data
        if nodes_to_save or edges_to_save:
            invalidate_navigation_cache_for_tree(tree_id, team_id)
            print(f"  🔄 Cache invalidated immediately for tree {tree_id}")
            
            # DELAY: Wait 2s to let view refresh/propagate before frontend fetch
            time.sleep(2)
        
        # Update state
        executor.exploration_state['status'] = 'structure_created'
        executor.exploration_state['nodes_created'] = nodes_created
        executor.exploration_state['edges_created'] = edges_created
        executor.exploration_state['home_id'] = start_node_id  # Legacy name in state, but holds current start node
        executor.exploration_state['current_step'] = f'Created {len(nodes_created)} nodes and {len(edges_created)} edges. Ready to validate.'
        executor.exploration_state['items_to_validate'] = items
        executor.exploration_state['current_validation_index'] = 0
        
        return {
            'success': True,
            'nodes_created': len(nodes_created),
            'edges_created': len(edges_created),
            'message': 'Structure created successfully',
            'node_ids': nodes_created,
            'edge_ids': edges_created
        }

