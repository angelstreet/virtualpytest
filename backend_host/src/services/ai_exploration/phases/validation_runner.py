import time
from typing import Dict, Any
from backend_host.src.services.ai_exploration.node_generator import NodeGenerator
from shared.src.lib.database.navigation_trees_db import (
    get_edge_by_id, 
    save_edges_batch,
    invalidate_navigation_cache_for_tree
)
from shared.src.lib.utils.cloudflare_utils import upload_navigation_screenshot

def start_validation(executor) -> Dict[str, Any]:
    """
    Phase 2b: Start validation process
    
    Returns:
        {
            'success': True,
            'total_items': 10
        }
    """
    with executor._lock:
        if executor.exploration_state['status'] != 'structure_created':
            return {
                'success': False,
                'error': f"Cannot start validation: status is {executor.exploration_state['status']}"
            }
        
        items_to_validate = executor.exploration_state.get('items_to_validate', [])
        print(f"[@ExplorationExecutor:start_validation] Items to validate: {len(items_to_validate)}")
        print(f"[@ExplorationExecutor:start_validation] Items: {items_to_validate}")
        
        if not items_to_validate or len(items_to_validate) == 0:
            return {
                'success': False,
                'error': 'No items to validate. Structure may not have been created properly.'
            }
        
        executor.exploration_state['status'] = 'awaiting_validation'
        executor.exploration_state['current_validation_index'] = 0
        executor.exploration_state['node_verification_data'] = []  # Initialize for collecting dumps during validation
        
        # Copy data needed for summary (to use outside lock)
        tree_id = executor.exploration_state['tree_id']
        team_id = executor.exploration_state['team_id']
        start_node_id = executor.exploration_state.get('home_id', 'home')
        start_node_label = executor.exploration_state.get('start_node', 'home')
        lines = executor.exploration_state.get('exploration_plan', {}).get('lines', [])
        items_left = executor.exploration_state.get('exploration_plan', {}).get('items_left_of_home', [])
    
    # ✅ Print summaries OUTSIDE the lock to avoid deadlock
    print(f"\n{'='*100}")
    print(f"🚀 [VALIDATION START] Validation order for {len(items_to_validate)} items")
    print(f"{'='*100}")
    for idx, item in enumerate(items_to_validate):
        # Each item will create: home_{item} (focus node) and {item} (screen node)
        focus_node = f"home_{item.replace(' ', '_')}"
        screen_node = item.replace(' ', '_')
        print(f"  [{idx}] {item:20} -> will create: {focus_node} (focus), {screen_node} (screen)")
    print(f"{'='*100}\n")
    
    # ✅ NAVIGATION SUMMARY: Show edges (safe - no lock held, same as validate_next_item)
    print(f"\n{'='*100}")
    print(f"📍 [NAVIGATION SUMMARY] Edges to validate:")
    print(f"{'='*100}")
    
    # Simple node name sanitizer (same logic as NodeGenerator.target_to_node_name)
    def sanitize_name(target: str) -> str:
        return target.lower().replace(' ', '_').replace('&', '').replace('-', '_').replace("'", '')
    
    display_num = 0
    for idx, item in enumerate(items_to_validate):
        screen_node_name = sanitize_name(item)
        focus_node_name = f"{start_node_id}_{screen_node_name}"
        
        # Skip 'home' - it's skipped in validation too
        if 'home' in screen_node_name and screen_node_name != 'home_temp':
            continue
        
        display_num += 1
        
        # Simplified: Just show the item and edges (details during actual validation)
        print(f"\n  [{display_num}] {item}")
        print(f"      → {focus_node_name} (focus)")
        print(f"      ↓ {screen_node_name} (screen)")
        print(f"      ↑ {focus_node_name} (exit)")
    
    print(f"\n{'='*100}\n")
    
    print(f"[@ExplorationExecutor:start_validation] ✅ Ready to validate {len(items_to_validate)} items")
    
    return {
        'success': True,
        'message': 'Ready to start validation',
        'total_items': len(items_to_validate)
    }

def validate_next_item(executor) -> Dict[str, Any]:
    """
    Phase 2b: Validate edges sequentially (depth-first for TV dual-layer)
    """
    # Check if we should skip 'home' (do this check outside lock to avoid recursive deadlock)
    should_skip_home = False
    with executor._lock:
        if executor.exploration_state['status'] not in ['awaiting_validation', 'validating']:
            error_msg = f"Cannot validate: status is {executor.exploration_state['status']}"
            return {
                'success': False,
                'error': error_msg
            }
        
        tree_id = executor.exploration_state['tree_id']
        team_id = executor.exploration_state['team_id']
        current_index = executor.exploration_state['current_validation_index']
        items_to_validate = executor.exploration_state['items_to_validate']
        
        if current_index >= len(items_to_validate):
            executor.exploration_state['status'] = 'validation_complete'
            return {
                'success': True,
                'message': 'All items validated',
                'has_more_items': False
            }
        
        current_item = items_to_validate[current_index]
        target_to_node_map = executor.exploration_state['target_to_node_map']
        node_name = target_to_node_map.get(current_item)
        
        if not node_name:
            # Fallback
            node_gen = NodeGenerator(tree_id, team_id)
            node_name_clean = node_gen.target_to_node_name(current_item)
            node_name = node_name_clean
        
        # Skip home - increment index and check outside lock
        should_skip_home = 'home' in node_name.lower() and node_name != 'home_temp'
        if should_skip_home:
            executor.exploration_state['current_validation_index'] = current_index + 1
    
    # ✅ Release lock before recursive call to avoid deadlock
    if should_skip_home:
        return validate_next_item(executor)
    
    # Continue with validation (reacquire lock for the rest)
    with executor._lock:
        # Re-read state after releasing and reacquiring lock
        tree_id = executor.exploration_state['tree_id']
        team_id = executor.exploration_state['team_id']
        current_index = executor.exploration_state['current_validation_index']
        items_to_validate = executor.exploration_state['items_to_validate']
        current_item = items_to_validate[current_index]
        target_to_node_map = executor.exploration_state['target_to_node_map']
        node_name = target_to_node_map.get(current_item)
        
        if not node_name:
            node_gen = NodeGenerator(tree_id, team_id)
            node_name_clean = node_gen.target_to_node_name(current_item)
            node_name = node_name_clean
        
        # ✅ NEW: Capture HOME dump before first navigation (Critical for Uniqueness)
        if current_index == 0:
            try:
                controller = executor.exploration_engine.controller
                print(f"[@ExplorationExecutor:validate_next_item] 🏠 Capturing HOME dump for uniqueness baseline...")
                
                home_dump_data = None
                home_screenshot_url = executor.exploration_state.get('current_analysis', {}).get('screenshot')
                
                # Try to get dump based on device type
                if hasattr(controller, 'dump_elements') and callable(getattr(controller, 'dump_elements')):
                    # Mobile/Web: Use dump_elements
                    dump_result = controller.dump_elements()
                    
                    # Handle async controllers (web) - run coroutine if needed
                    import inspect
                    if inspect.iscoroutine(dump_result):
                        import asyncio
                        dump_result = asyncio.run(dump_result)
                    
                    if isinstance(dump_result, tuple):
                        success, elements, error = dump_result
                        if success and elements:
                            home_dump_data = {'elements': elements, 'dump_type': 'xml'}
                    elif isinstance(dump_result, dict):
                        home_dump_data = {**dump_result, 'dump_type': 'xml'}
                else:
                    # TV: Use OCR dump - take fresh screenshot and extract OCR
                    print(f"    📊 TV device - using OCR for home dump")
                    
                    # Take fresh screenshot for OCR extraction
                    screenshot_path = None
                    try:
                        av_controllers = executor.device.get_controllers('av')
                        av_controller = av_controllers[0] if av_controllers else None
                        if av_controller:
                            screenshot_path = av_controller.take_screenshot()
                            if screenshot_path:
                                print(f"    📸 Fresh screenshot captured for OCR: {screenshot_path}")
                    except Exception as e:
                        print(f"    ⚠️ Failed to capture screenshot: {e}")
                    
                    # Extract OCR dump from screenshot
                    if screenshot_path:
                        text_controller = None
                        for v in executor.device.get_controllers('verification'):
                            if getattr(v, 'verification_type', None) == 'text':
                                text_controller = v
                                break
                        
                        if text_controller:
                            print(f"    📊 Extracting OCR dump from home screenshot...")
                            ocr_result = text_controller.extract_ocr_dump(screenshot_path, confidence_threshold=30)
                            
                            if ocr_result.get('success') and ocr_result.get('elements'):
                                home_dump_data = {'elements': ocr_result['elements'], 'dump_type': 'ocr'}
                                print(f"    📊 OCR Dump: {len(ocr_result['elements'])} text elements")
                            else:
                                # Even if empty, set structure so UI knows it's an OCR dump
                                home_dump_data = {'elements': [], 'dump_type': 'ocr'}
                                print(f"    ⚠️ OCR dump extraction found no text (empty)")
                        else:
                            print(f"    ⚠️ Text controller not available for OCR dump")
                    else:
                        print(f"    ⚠️ No screenshot available for OCR dump")
                    
                if home_dump_data or home_screenshot_url:
                    # Ensure list exists
                    if 'node_verification_data' not in executor.exploration_state:
                        executor.exploration_state['node_verification_data'] = []
                    
                    home_node_id = executor.exploration_state.get('home_id', 'home')
                    
                    print(f"\n{'='*80}")
                    print(f"📸 [SCREENSHOT CAPTURE] Adding HOME to verification data")
                    print(f"   Node ID: {home_node_id}")
                    print(f"   Node Label: home")
                    print(f"   Screenshot URL: {home_screenshot_url}")
                    print(f"   Array Index: {len(executor.exploration_state['node_verification_data'])}")
                    print(f"{'='*80}\n")
                    
                    # Store Home data (dump and/or screenshot)
                    executor.exploration_state['node_verification_data'].append({
                        'node_id': home_node_id,
                        'node_label': 'home',
                        'dump': home_dump_data,
                        'screenshot_url': home_screenshot_url
                    })
                    
                    # Track if start_node has verification for smart BACK validation
                    executor.exploration_state['start_node_has_verification'] = (home_dump_data is not None)
                    
                    print(f"    ✅ Home data stored (dump: {home_dump_data is not None}, screenshot: {home_screenshot_url is not None})")
            except Exception as e:
                print(f"    ⚠️ Failed to capture Home dump: {e}")

        print(f"[@ExplorationExecutor:validate_next_item] Validating {current_index + 1}/{len(items_to_validate)}")
        print(f"  Target: {current_item} → {node_name}")
        
        executor.exploration_state['status'] = 'validating'
        executor.exploration_state['current_step'] = f"Validating {current_index + 1}/{len(items_to_validate)}: {current_item}"
    
    # Get controller and context from engine
    controller = executor.exploration_engine.controller
    context = executor.exploration_engine.context
    strategy = executor.exploration_state.get('exploration_plan', {}).get('strategy', 'click')
    home_indicator = executor.exploration_state['exploration_plan']['items'][0]
    
    # ✅ TV DUAL-LAYER: Use depth-first sequential edge validation
    if strategy in ['dpad_with_screenshot', 'test_dpad_directions']:
        # ✅ DUAL-LAYER TV VALIDATION (Depth-first) with multi-row support
        print(f"\n  🎮 TV DUAL-LAYER VALIDATION (depth-first)")
        print(f"     Item {current_index + 1}/{len(items_to_validate)}: {current_item}")
        
        # Get row structure from exploration plan
        lines = executor.exploration_state.get('exploration_plan', {}).get('lines', [])
        
        # Calculate node names
        node_gen = NodeGenerator(tree_id, team_id)
        # Use start_node_id from state
        start_node_id = executor.exploration_state.get('home_id', 'home')
        start_node_label = executor.exploration_state.get('start_node', 'home')
        
        screen_node_name = node_gen.target_to_node_name(current_item)
        focus_node_name = f"{start_node_id}_{screen_node_name}"
        
        # ✅ FIX: TV menu structure
        # Row 0: home (starting point)
        # Row 1: home_tv_guide → home_apps → home_watch (lines[0])
        # Row 2: home_continue_watching → ... (lines[1])
        # Navigation: DOWN from row to row, RIGHT within row
        
        current_row_index = -1
        current_position_in_row = -1
        prev_row_index = -1
        prev_position_in_row = -1
        
        # Find current item's position in row structure
        for row_idx, row_items in enumerate(lines):
            if current_item in row_items:
                current_row_index = row_idx
                current_position_in_row = row_items.index(current_item)
                break
        
        # Find previous item's position (if exists)
        if current_index > 0:
            prev_item = items_to_validate[current_index - 1]
            for row_idx, row_items in enumerate(lines):
                if prev_item in row_items:
                    prev_row_index = row_idx
                    prev_position_in_row = row_items.index(prev_item)
                    break
        
        # Determine navigation type
        # Key insight: Check if we're in the SAME row or DIFFERENT row
        is_same_row = (prev_row_index == current_row_index) and (prev_row_index != -1)
        is_first_item_overall = (current_index == 0)
        
        print(f"\n  🐛 DEBUG: Navigation Decision Logic")
        print(f"     is_first_item_overall = {is_first_item_overall}")
        print(f"     current_row_index = {current_row_index}")
        print(f"     prev_row_index = {prev_row_index}")
        print(f"     is_same_row = {is_same_row}")
        
        # ✅ Check if this is a Row 0 LEFT item (horizontal menu, left of home)
        items_left = executor.exploration_state.get('exploration_plan', {}).get('items_left_of_home', [])
        is_row0_left_item = current_item in items_left and current_row_index == 0
        is_first_left_item = is_row0_left_item and (len(items_left) == 0 or current_item == items_left[0])
        
        # Check if previous item was also a LEFT item (for chaining LEFT items)
        prev_was_left_item = False
        if current_index > 0:
            prev_item = items_to_validate[current_index - 1]
            prev_was_left_item = prev_item in items_left
        
        if is_first_item_overall:
            # First item ever: check if 'home' (start_node) is in the same row
            # If start_node is in lines[0], it's horizontal navigation (RIGHT)
            # If start_node is NOT in any row, it's vertical navigation (DOWN)
            home_in_current_row = False
            if current_row_index >= 0 and current_row_index < len(lines):
                row_items_lower = [item.lower() for item in lines[current_row_index]]
                # Check for start_node_label or 'home' as fallback/alias
                home_in_current_row = (start_node_label.lower() in row_items_lower or 
                                     'home' in row_items_lower or 
                                     'accueil' in row_items_lower)
            
            prev_focus_name = start_node_id
            if home_in_current_row:
                # ROOT: start_node is in Row 1 - navigate LEFT or RIGHT from it
                is_left_item = current_item in items_left
                nav_direction = 'LEFT' if is_left_item else 'RIGHT'
                print(f"  🐛 DEBUG: ✅ Decision: FIRST ITEM, start_node IN Row {current_row_index + 1} → {nav_direction}")
                print(f"     Reason: '{start_node_label}' is part of Row {current_row_index + 1}, item is {'LEFT' if is_left_item else 'RIGHT'} of home")
            elif current_row_index == 0:
                # TV SUBTREE: start_node NOT in Row 1, but Row 1 is visible on that screen
                # First item in Row 1 is already focused - no navigation needed
                item_node_name = node_gen.target_to_node_name(current_item)
                prev_focus_name = f"{start_node_id}_{item_node_name}"
                nav_direction = None  # Already there
                print(f"  🐛 DEBUG: ✅ Decision: FIRST ITEM, SUBTREE Row 1 → NONE (already focused)")
                print(f"     Reason: '{start_node_label}' is subtree root, first item in Row 1 is already focused")
            else:
                # SUBTREE: start_node is Row 0, navigate DOWN to Row 2+
                nav_direction = 'DOWN'
                print(f"  🐛 DEBUG: ✅ Decision: FIRST ITEM, start_node NOT in rows → DOWN")
                print(f"     Reason: '{start_node_label}' is Row 0, navigating down to Row {current_row_index + 1}")
        elif is_first_left_item and not prev_was_left_item:
            # ✅ FIX: FIRST Row 0 LEFT item (coming from vertical rows) - navigate from HOME
            prev_focus_name = start_node_id  # Start from home, not from previous vertical item
            nav_direction = 'LEFT'
            print(f"  🐛 DEBUG: ✅ Decision: FIRST LEFT ITEM (from vertical) → LEFT from home")
            print(f"     Reason: '{current_item}' is first LEFT item, previous was vertical row")
            print(f"     prev_focus_name = {prev_focus_name} (home, not previous vertical item)")
        elif is_same_row and current_row_index == 0:
            # ✅ Row 0 same row: horizontal navigation - LEFT or RIGHT of home
            prev_item_name = node_gen.target_to_node_name(items_to_validate[current_index - 1])
            prev_focus_name = f"{start_node_id}_{prev_item_name}"
            is_left_item = current_item in items_left
            nav_direction = 'LEFT' if is_left_item else 'RIGHT'
            print(f"  🐛 DEBUG: ✅ Decision: ROW 0 SAME ROW → {nav_direction} within horizontal menu")
            print(f"     Reason: Both items in Row 0, item is {'LEFT' if is_left_item else 'RIGHT'} of home")
            print(f"     prev_focus_name = {prev_focus_name}")
        else:
            # ✅ Row 1+ (vertical): ALL items need DOWN from home
            # For Row 1+, we always go to home first and press DOWN to reach target
            # This is because we're exploring and don't know if chaining works
            prev_item_name = node_gen.target_to_node_name(items_to_validate[current_index - 1])
            prev_focus_name = f"{start_node_id}_{prev_item_name}"  # Edge recorded from previous item
            nav_direction = 'DOWN'
            
            if is_same_row:
                print(f"  🐛 DEBUG: ✅ Decision: ROW {current_row_index + 1} SAME ROW → DOWN (vertical menu)")
                print(f"     Reason: Vertical row - go to home first, then DOWN to target")
            else:
                print(f"  🐛 DEBUG: ✅ Decision: DIFFERENT ROW → DOWN to Row {current_row_index + 1}")
                print(f"     Reason: Row transition from Row {prev_row_index + 1} to Row {current_row_index + 1}")
            print(f"     prev_focus_name = {prev_focus_name} (for edge recording)")
        
        print(f"\n  🐛 DEBUG: Final Navigation Plan")
        print(f"     {prev_focus_name} → {focus_node_name}: {nav_direction}")
        print(f"     {'⬇️ VERTICAL' if nav_direction == 'DOWN' else '➡️ HORIZONTAL'}\n")
        
        # Row numbering: home is Row 0, lines[0] is Row 1, lines[1] is Row 2, etc.
        display_row = current_row_index + 1  # lines[0] = Row 1
        
        # ✅ TRANSITION: Navigate to start_node before first LEFT item
        items_left = executor.exploration_state.get('exploration_plan', {}).get('items_left_of_home', [])
        if items_left and current_item in items_left and current_item == items_left[0]:
            print(f"\n    🔄 LEFT TRANSITION: Navigating to '{start_node_label}' before first LEFT item...")
            print(f"      First LEFT item: {current_item}")
            print(f"      All LEFT items: {items_left}")
            try:
                import asyncio
                # ✅ Use root_tree_id for pathfinding (start_node is in parent tree!)
                root_tree_id = executor.exploration_state.get('root_tree_id', tree_id)
                nav_result = asyncio.run(executor.device.navigation_executor.execute_navigation(
                    tree_id=root_tree_id,
                    userinterface_name=executor.exploration_state['userinterface_name'],
                    target_node_label=start_node_label,
                    team_id=team_id
                ))
                
                if nav_result.get('success'):
                    print(f"    ✅ At '{start_node_label}' (used root_tree_id: {root_tree_id}) - ready for LEFT navigation")
                else:
                    error_msg = nav_result.get('error', 'Unknown error')
                    print(f"    ❌ Navigation to '{start_node_label}' failed: {error_msg}")
                    print(f"    ⚠️ Continuing anyway - validation may fail")
            except Exception as e:
                print(f"    ❌ LEFT transition exception: {e}")
                print(f"    ⚠️ Continuing anyway - validation may fail")
        
        # ✅ RECOVERY: Navigate to home before DOWN navigation (vertical rows)
        # For ALL vertical items: go to start_node first, then press DOWN to reach target
        # This is safe because we don't know if chaining DOWN from previous item works
        elif nav_direction == 'DOWN':
            print(f"\n    🔄 ROW {display_row} TRANSITION: Navigating to '{start_node_label}' before DOWN...")
            print(f"      Transitioning from Row {prev_row_index + 1 if prev_row_index >= 0 else 0} → Row {display_row}")
            try:
                import asyncio
                # ✅ Use root_tree_id for pathfinding (start_node is in parent tree!)
                root_tree_id = executor.exploration_state.get('root_tree_id', tree_id)
                nav_result = asyncio.run(executor.device.navigation_executor.execute_navigation(
                    tree_id=root_tree_id,
                    userinterface_name=executor.exploration_state['userinterface_name'],
                    target_node_label=start_node_label,
                    team_id=team_id
                ))
                
                if nav_result.get('success'):
                    print(f"    ✅ At '{start_node_label}' (used root_tree_id: {root_tree_id}) - ready for DOWN navigation to Row {display_row}")
                    # ✅ FIX: Update prev_focus_name to start_node since we navigated there
                    prev_focus_name = start_node_id
                else:
                    error_msg = nav_result.get('error', 'Unknown error')
                    print(f"    ❌ Navigation to '{start_node_label}' failed: {error_msg}")
                    print(f"    ⚠️ Continuing anyway - validation may fail")
            except Exception as e:
                print(f"    ❌ Recovery exception: {e}")
                print(f"    ⚠️ Continuing anyway - validation may fail")
        
        # Print validation info
        nav_type = '🔽 VERTICAL to new row' if nav_direction == 'DOWN' else ('✅ Already focused' if nav_direction is None else '➡️ HORIZONTAL within row')
        nav_display = nav_direction or 'NONE'
        print(f"     📍 Row {display_row}, Position {current_position_in_row + 1}")
        print(f"     {nav_type}")
        print(f"     Edges to test:")
        print(f"       1. {prev_focus_name} → {focus_node_name}: {nav_display}")
        print(f"       2. {focus_node_name} ↓ {screen_node_name}: OK")
        print(f"       3. {screen_node_name} ↑ {focus_node_name}: BACK")
        
        edge_results = {
            'horizontal': 'pending',
            'enter': 'pending',
            'exit': 'pending'
        }
        screenshot_url = None
        
        # Edge 1: Focus navigation (RIGHT/LEFT for horizontal, DOWN for vertical, None for already focused)
        horizontal_edge = None
        try:
            print(f"\n    Edge 1/3: {prev_focus_name} → {focus_node_name}")
            
            if nav_direction is None:
                # TV SUBTREE: First item in Row 1 is already focused
                print(f"    ✅ Already at {focus_node_name} (no navigation needed)")
                edge_results['horizontal'] = 'success'
            else:
                # Read edge from database to get iterator parameter
                edge_id = f"edge_{prev_focus_name}_to_{focus_node_name}"
                iterator = 1
                
                try:
                    edge_result = get_edge_by_id(tree_id, edge_id, team_id)
                    
                    if edge_result.get('success') and edge_result.get('edge'):
                        horizontal_edge = edge_result['edge']
                        action_sets = horizontal_edge.get('action_sets', [])
                        if len(action_sets) > 0 and action_sets[0].get('actions'):
                            first_action = action_sets[0]['actions'][0]
                            iterator = first_action.get('iterator', 1)
                            print(f"    📊 Edge iterator from database: {iterator}")
                    else:
                        print(f"    ⚠️ Edge not found: {edge_id}")
                except Exception as e:
                    print(f"    ⚠️ Could not read edge: {e}")
                
                if nav_direction == 'DOWN' and current_row_index >= 1:
                    total_downs = current_row_index + current_position_in_row
                    print(f"    🔽 Vertical navigation: pressing DOWN {total_downs}x from home")
                    print(f"       (Row {current_row_index + 1}, Position {current_position_in_row + 1})")
                    
                    for down_count in range(total_downs):
                        result = controller.press_key('DOWN')
                        import inspect
                        if inspect.iscoroutine(result):
                            import asyncio
                            result = asyncio.run(result)
                        print(f"       DOWN {down_count + 1}/{total_downs}")
                        time.sleep(0.8)
                else:
                    # Horizontal navigation (LEFT/RIGHT)
                    print(f"    ➡️ Horizontal navigation: pressing {nav_direction} {iterator}x")
                    for press_count in range(iterator):
                        result = controller.press_key(nav_direction)
                        import inspect
                        if inspect.iscoroutine(result):
                            import asyncio
                            result = asyncio.run(result)
                        if iterator > 1:
                            print(f"       {nav_direction} {press_count + 1}/{iterator}")
                        time.sleep(0.8)
                
                edge_results['horizontal'] = 'success'
                iterator_display = f" x{iterator}" if iterator > 1 else ""
                print(f"    ✅ Focus navigation: {nav_direction}{iterator_display}")
            
            # ✅ SAVE EDGE: Update database with confirmed iterator (no re-fetch needed!)
            if iterator > 1 and horizontal_edge:
                try:
                    action_sets = horizontal_edge.get('action_sets', [])
                    
                    # Ensure iterator is set in both directions (at action level, not in params)
                    if len(action_sets) >= 2:
                        if action_sets[0].get('actions') and len(action_sets[0]['actions']) > 0:
                            action_sets[0]['actions'][0]['iterator'] = iterator
                        if action_sets[1].get('actions') and len(action_sets[1]['actions']) > 0:
                            action_sets[1]['actions'][0]['iterator'] = iterator
                        
                        # Save updated edge (already in memory)
                        update_result = save_edges_batch(tree_id, [horizontal_edge], team_id)
                        if update_result.get('success'):
                            print(f"    💾 Edge saved with iterator={iterator}")
                except Exception as e:
                    print(f"    ⚠️ Failed to save iterator: {e}")
            
            time.sleep(2.0)  # 2000ms for D-PAD navigation (matches structure_creator.py)
            
            # 📸 Capture screenshot for focus node (no dump needed)
            try:
                av_controllers = executor.device.get_controllers('av')
                av_controller = av_controllers[0] if av_controllers else None
                if av_controller:
                    focus_screenshot_path = av_controller.take_screenshot()
                    if focus_screenshot_path:
                        sanitized_name = focus_node_name.replace(' ', '_')
                        r2_filename = f"{sanitized_name}.jpg"
                        userinterface_name = executor.exploration_state['userinterface_name']
                        upload_result = upload_navigation_screenshot(focus_screenshot_path, userinterface_name, r2_filename)
                        if upload_result.get('success'):
                            focus_screenshot_url = upload_result.get('url')
                            with executor._lock:
                                if 'node_verification_data' not in executor.exploration_state:
                                    executor.exploration_state['node_verification_data'] = []
                                
                                print(f"\n{'='*80}")
                                print(f"📸 [SCREENSHOT CAPTURE] Adding FOCUS node to verification data")
                                print(f"   Current Item: {current_item}")
                                print(f"   Node ID: {focus_node_name}")
                                print(f"   Node Label: {focus_node_name}")
                                print(f"   Screenshot URL: {focus_screenshot_url}")
                                print(f"   Array Index: {len(executor.exploration_state['node_verification_data'])}")
                                print(f"{'='*80}\n")
                                
                                executor.exploration_state['node_verification_data'].append({
                                    'node_id': focus_node_name,
                                    'node_label': focus_node_name,
                                    'dump': None,
                                    'screenshot_url': focus_screenshot_url
                                })
                            print(f"    📸 Focus screenshot saved: {focus_screenshot_url}")
            except Exception as e:
                print(f"    ⚠️ Focus screenshot failed: {e}")
        except Exception as e:
            edge_results['horizontal'] = 'failed'
            print(f"    ❌ Focus navigation failed: {e}")
        
        # Edge 2: Vertical enter (OK) - with screenshot + dump
        try:
            print(f"\n    Edge 2/3: {focus_node_name} ↓ {screen_node_name}")
            
            # Screenshot BEFORE OK (for similarity comparison)
            before_ok_screenshot = None
            try:
                from shared.src.lib.utils.device_utils import capture_screenshot
                from shared.src.lib.utils.build_url_utils import buildHostImageUrl
                from backend_host.src.controllers.controller_manager import get_host
                before_ok_screenshot = capture_screenshot(executor.device, context=None)
                if before_ok_screenshot:
                    print(f"    📸 Before OK screenshot: {before_ok_screenshot}")
                    host = get_host()
                    before_ok_url = buildHostImageUrl({'host_url': host.host_url, 'host_api_url': getattr(host, 'host_api_url', None)}, before_ok_screenshot)
                    print(f"    🔗 Before OK URL: {before_ok_url}")
            except Exception as e:
                print(f"    ⚠️ Failed to capture before-OK screenshot: {e}")
            
            result = controller.press_key('OK')
            import inspect
            if inspect.iscoroutine(result):
                import asyncio
                result = asyncio.run(result)
            
            edge_results['enter'] = 'success'
            print(f"    ✅ Vertical enter: OK")
            time.sleep(8.0)  # 8000ms for OK (matches structure_creator.py)
            
            # Screenshot AFTER OK and check similarity (should be LOW - moved to different screen)
            after_ok_screenshot = None
            try:
                from shared.src.lib.utils.device_utils import capture_screenshot
                from shared.src.lib.utils.build_url_utils import buildHostImageUrl
                from backend_host.src.controllers.controller_manager import get_host
                after_ok_screenshot = capture_screenshot(executor.device, context=None)
                if after_ok_screenshot:
                    print(f"    📸 After OK screenshot: {after_ok_screenshot}")
                    host = get_host()
                    after_ok_url = buildHostImageUrl({'host_url': host.host_url, 'host_api_url': getattr(host, 'host_api_url', None)}, after_ok_screenshot)
                    print(f"    🔗 After OK URL: {after_ok_url}")
            except Exception as e:
                print(f"    ⚠️ Failed to capture after-OK screenshot: {e}")
            
            # Compare screenshots if both captured successfully
            if before_ok_screenshot and after_ok_screenshot:
                try:
                    import cv2
                    import numpy as np
                    before_img = cv2.imread(before_ok_screenshot, cv2.IMREAD_COLOR)
                    after_img = cv2.imread(after_ok_screenshot, cv2.IMREAD_COLOR)
                    if before_img is not None and after_img is not None:
                        if before_img.shape != after_img.shape:
                            after_img = cv2.resize(after_img, (before_img.shape[1], before_img.shape[0]))
                        
                        # Exact pixel-by-pixel comparison (strict)
                        matches = np.all(before_img == after_img, axis=2)
                        exact_matching_pixels = np.sum(matches)
                        total_pixels = before_img.shape[0] * before_img.shape[1]
                        similarity = (exact_matching_pixels / total_pixels) * 100
                        
                        # Calculate mean difference for additional context
                        diff_gray = cv2.cvtColor(cv2.absdiff(before_img, after_img), cv2.COLOR_BGR2GRAY)
                        mean_diff = np.mean(diff_gray)
                        
                        print(f"    📊 OK similarity: {similarity:.1f}% (expect <30% - moved to different screen)")
                        print(f"    📊 Mean pixel difference: {mean_diff:.2f}")
                        if similarity >= 30:
                            print(f"    ⚠️ WARNING: High similarity after OK - may not have moved to new screen!")
                    else:
                        print(f"    ⚠️ Failed to load images for comparison (before: {before_img is not None}, after: {after_img is not None})")
                except Exception as e:
                    print(f"    ⚠️ Screenshot similarity comparison failed: {e}")
            
            # 📸 Capture screenshot + dump (ONLY for screen nodes)
            dump_data = None
            screenshot_path = None
            
            # First take screenshot (needed for both ADB dump and OCR dump)
            try:
                av_controllers = executor.device.get_controllers('av')
                av_controller = av_controllers[0] if av_controllers else None
                if av_controller:
                    screenshot_path = av_controller.take_screenshot()
                    if screenshot_path:
                        print(f"    📸 Screenshot captured: {screenshot_path}")
            except Exception as e:
                print(f"    ⚠️ Screenshot capture failed: {e}")
            
            # Try to get dump (method depends on device type)
            try:
                # Check if controller has dump_elements (mobile/web)
                if hasattr(controller, 'dump_elements') and callable(getattr(controller, 'dump_elements')):
                    # Mobile/Web: Use ADB/XML dump
                    print(f"    📊 Using ADB/Web dump_elements()")
                    dump_result = controller.dump_elements()
                    import inspect
                    if inspect.iscoroutine(dump_result):
                        import asyncio
                        dump_result = asyncio.run(dump_result)
                    
                    if isinstance(dump_result, tuple):
                        success, elements, error = dump_result
                        if success and elements:
                            dump_data = {'elements': elements, 'dump_type': 'xml'}
                            print(f"    📊 XML Dump: {len(elements)} elements")
                    elif isinstance(dump_result, dict):
                        dump_data = {**dump_result, 'dump_type': 'xml'}
                        print(f"    📊 XML Dump: {len(dump_result.get('elements', []))} elements")
                else:
                    # TV/IR device - use OCR dump extraction
                    print(f"    📊 Controller has no dump_elements → Using OCR dump for TV")
                    if screenshot_path:
                        # Get text verification controller for OCR dump
                        text_controller = None
                        for v in executor.device.get_controllers('verification'):
                            if getattr(v, 'verification_type', None) == 'text':
                                text_controller = v
                                break
                        
                        if text_controller:
                            print(f"    📊 Extracting OCR dump from screenshot...")
                            ocr_result = text_controller.extract_ocr_dump(screenshot_path, confidence_threshold=30)
                            
                            if ocr_result.get('success') and ocr_result.get('elements'):
                                dump_data = {'elements': ocr_result['elements'], 'dump_type': 'ocr'}
                                print(f"    📊 OCR Dump: {len(ocr_result['elements'])} text elements")
                            else:
                                # Even if empty, set structure so UI knows it's an OCR dump
                                dump_data = {'elements': [], 'dump_type': 'ocr'}
                                print(f"    ⚠️ OCR dump extraction failed or no text found")
                        else:
                            print(f"    ⚠️ Text controller not available for OCR dump")
                    else:
                        print(f"    ⚠️ No screenshot available for OCR dump")
            except Exception as dump_err:
                print(f"    ⚠️ Dump failed: {dump_err}")
                import traceback
                traceback.print_exc()
            
            # Upload screenshot to R2
            if screenshot_path:
                try:
                    sanitized_name = screen_node_name.replace(' ', '_')
                    r2_filename = f"{sanitized_name}.jpg"
                    userinterface_name = executor.exploration_state['userinterface_name']
                    upload_result = upload_navigation_screenshot(screenshot_path, userinterface_name, r2_filename)
                    
                    if upload_result.get('success'):
                        screenshot_url = upload_result.get('url')
                        print(f"    📸 Screenshot uploaded: {screenshot_url}")
                except Exception as e:
                    print(f"    ⚠️ Screenshot upload failed: {e}")
            else:
                print(f"    ⚠️ No screenshot to upload")
            
            # Store verification data (screenshot and/or dump)
            # ✅ TV FIX: Store even without dump (IR remote has no dump_elements)
            if screenshot_url or dump_data:
                with executor._lock:
                    if 'node_verification_data' not in executor.exploration_state:
                        executor.exploration_state['node_verification_data'] = []
                    
                    print(f"\n{'='*80}")
                    print(f"📸 [SCREENSHOT CAPTURE] Adding SCREEN node to verification data")
                    print(f"   Current Item: {current_item}")
                    print(f"   Node ID: {screen_node_name}")
                    print(f"   Node Label: {screen_node_name}")
                    print(f"   Screenshot URL: {screenshot_url}")
                    print(f"   Array Index: {len(executor.exploration_state['node_verification_data'])}")
                    print(f"{'='*80}\n")
                    
                    executor.exploration_state['node_verification_data'].append({
                        'node_id': screen_node_name,  # ← Fixed: ID doesn't have _temp, only label does
                        'node_label': screen_node_name,
                        'dump': dump_data,  # None for TV, that's OK
                        'screenshot_url': screenshot_url
                    })
                print(f"    ✅ Verification data stored (dump: {dump_data is not None}, screenshot: {screenshot_url is not None})")
                
        except Exception as e:
            edge_results['enter'] = 'failed'
            print(f"    ❌ Vertical enter failed: {e}")
        
        # Edge 3: Vertical exit (BACK)
        backs_needed = 1  # Default: 1 BACK
        
        try:
            print(f"\n    Edge 3/3: {screen_node_name} ↑ {focus_node_name}")
            
            # Screenshot BEFORE BACK (for similarity comparison)
            before_back_screenshot = None
            try:
                from shared.src.lib.utils.device_utils import capture_screenshot
                from shared.src.lib.utils.build_url_utils import buildHostImageUrl
                from backend_host.src.controllers.controller_manager import get_host
                before_back_screenshot = capture_screenshot(executor.device, context=None)
                if before_back_screenshot:
                    print(f"    📸 Before BACK screenshot: {before_back_screenshot}")
                    host = get_host()
                    before_back_url = buildHostImageUrl({'host_url': host.host_url, 'host_api_url': getattr(host, 'host_api_url', None)}, before_back_screenshot)
                    print(f"    🔗 Before BACK URL: {before_back_url}")
            except Exception as e:
                print(f"    ⚠️ Failed to capture before-BACK screenshot: {e}")
            
            result = controller.press_key('BACK')
            import inspect
            if inspect.iscoroutine(result):
                import asyncio
                asyncio.run(result)
            time.sleep(6.0)  # 6000ms for BACK (matches structure_creator.py)
            
            # Screenshot AFTER BACK and check similarity (should be HIGH - returned to same screen)
            after_back_screenshot = None
            try:
                from shared.src.lib.utils.device_utils import capture_screenshot
                from shared.src.lib.utils.build_url_utils import buildHostImageUrl
                from backend_host.src.controllers.controller_manager import get_host
                after_back_screenshot = capture_screenshot(executor.device, context=None)
                if after_back_screenshot:
                    print(f"    📸 After BACK screenshot: {after_back_screenshot}")
                    host = get_host()
                    after_back_url = buildHostImageUrl({'host_url': host.host_url, 'host_api_url': getattr(host, 'host_api_url', None)}, after_back_screenshot)
                    print(f"    🔗 After BACK URL: {after_back_url}")
            except Exception as e:
                print(f"    ⚠️ Failed to capture after-BACK screenshot: {e}")
            
            # Compare screenshots if both captured successfully
            # ✅ Use similarity to decide if BACK worked (>40% = still on same screen = BACK failed)
            back_worked_via_similarity = None
            if before_back_screenshot and after_back_screenshot:
                try:
                    import cv2
                    import numpy as np
                    before_img = cv2.imread(before_back_screenshot, cv2.IMREAD_COLOR)
                    after_img = cv2.imread(after_back_screenshot, cv2.IMREAD_COLOR)
                    if before_img is not None and after_img is not None:
                        if before_img.shape != after_img.shape:
                            after_img = cv2.resize(after_img, (before_img.shape[1], before_img.shape[0]))
                        
                        # Exact pixel-by-pixel comparison (strict)
                        matches = np.all(before_img == after_img, axis=2)
                        exact_matching_pixels = np.sum(matches)
                        total_pixels = before_img.shape[0] * before_img.shape[1]
                        similarity = (exact_matching_pixels / total_pixels) * 100
                        
                        # Calculate mean difference for additional context
                        diff_gray = cv2.cvtColor(cv2.absdiff(before_img, after_img), cv2.COLOR_BGR2GRAY)
                        mean_diff = np.mean(diff_gray)
                        
                        print(f"    📊 BACK similarity: {similarity:.1f}% (expect <40% - moved to different screen)")
                        print(f"    📊 Mean pixel difference: {mean_diff:.2f}")
                        
                        # ✅ Decision: If similarity > 40%, we're still on the same screen (BACK failed)
                        if similarity > 40:
                            back_worked_via_similarity = False
                            print(f"    ⚠️ BACK FAILED: Similarity {similarity:.1f}% > 40% - still on same screen!")
                        else:
                            back_worked_via_similarity = True
                            print(f"    ✅ BACK SUCCESS: Similarity {similarity:.1f}% ≤ 40% - moved to different screen")
                    else:
                        print(f"    ⚠️ Failed to load images for comparison (before: {before_img is not None}, after: {after_img is not None})")
                except Exception as e:
                    print(f"    ⚠️ Screenshot similarity comparison failed: {e}")
            
            # ✅ Try second BACK if similarity check indicates first BACK failed
            if back_worked_via_similarity == False:
                print(f"    🔄 Similarity check failed - trying second BACK...")
                result = controller.press_key('BACK')
                import inspect
                if inspect.iscoroutine(result):
                    import asyncio
                    asyncio.run(result)
                time.sleep(6.0)  # 6000ms for BACK
                
                # Check similarity again after second BACK
                try:
                    from shared.src.lib.utils.device_utils import capture_screenshot
                    after_second_back_screenshot = capture_screenshot(executor.device, context=None)
                    
                    if after_second_back_screenshot and before_back_screenshot:
                        import cv2
                        import numpy as np
                        before_img = cv2.imread(before_back_screenshot, cv2.IMREAD_COLOR)
                        after_img = cv2.imread(after_second_back_screenshot, cv2.IMREAD_COLOR)
                        
                        if before_img is not None and after_img is not None:
                            if before_img.shape != after_img.shape:
                                after_img = cv2.resize(after_img, (before_img.shape[1], before_img.shape[0]))
                            
                            matches = np.all(before_img == after_img, axis=2)
                            exact_matching_pixels = np.sum(matches)
                            total_pixels = before_img.shape[0] * before_img.shape[1]
                            similarity_after_2nd = (exact_matching_pixels / total_pixels) * 100
                            
                            print(f"    📊 After 2nd BACK similarity: {similarity_after_2nd:.1f}%")
                            
                            if similarity_after_2nd <= 40:
                                backs_needed = 2
                                print(f"    ✅ Second BACK worked! Edge requires 2x BACK")
                            else:
                                print(f"    ❌ Second BACK also failed (similarity {similarity_after_2nd:.1f}% > 40%)")
                                # Try recovery navigation
                                start_node_id = executor.exploration_state.get('home_id', 'home')
                                start_node_label = executor.exploration_state.get('start_node', 'home')
                                print(f"    🔄 Recovery to '{start_node_label}'...")
                                import asyncio
                                asyncio.run(executor.device.navigation_executor.execute_navigation(
                                    tree_id=tree_id, 
                                    userinterface_name=executor.exploration_state['userinterface_name'],
                                    target_node_label=start_node_label, 
                                    team_id=team_id
                                ))
                except Exception as e:
                    print(f"    ⚠️ Second BACK similarity check failed: {e}")
            
            edge_results['exit'] = 'success'
            print(f"    ✅ Vertical exit: BACK")
        except Exception as e:
            edge_results['exit'] = 'failed'
            print(f"    ❌ Vertical exit failed: {e}")
        
        # Update state and return
        with executor._lock:
            executor.exploration_state['current_validation_index'] = current_index + 1
            has_more = (current_index + 1) < len(items_to_validate)
            
            # ✅ Set status to validation_complete when done
            if not has_more:
                executor.exploration_state['status'] = 'validation_complete'
                executor.exploration_state['current_step'] = 'Edge validation complete - ready for node verification'
                
                # ✅ CRITICAL: Invalidate cache ONCE after ALL validations complete
                # This ensures frontend gets fresh data with all iterator/BACK x2 updates
                print(f"\n  🔄 All validations complete - invalidating cache...")
                invalidate_navigation_cache_for_tree(tree_id, team_id)
                print(f"  ✅ Cache invalidated for tree {tree_id}")
            else:
                executor.exploration_state['status'] = 'awaiting_validation'
        
        # ✅ TV: UPDATE VERTICAL EDGE with backs_needed (read ONLY when needed)
        if backs_needed == 2:
            print(f"\n  💾 Updating vertical edge with BACK x2...")
            try:
                # Read vertical edge from database (only when backs_needed == 2)
                # Edge IDs are constructed from node IDs (which never have _temp)
                vertical_edge_id = f"edge_{focus_node_name}_to_{screen_node_name}"
                edge_result = get_edge_by_id(tree_id, vertical_edge_id, team_id)
                
                if edge_result.get('success') and edge_result.get('edge'):
                    vertical_edge = edge_result['edge']
                    
                    # Update reverse action (BACK) - iterator at action level, not in params
                    action_sets = vertical_edge.get('action_sets', [])
                    if len(action_sets) >= 2:
                        # action_sets[1] is reverse (BACK)
                        if action_sets[1].get('actions') and len(action_sets[1]['actions']) > 0:
                            # Update BACK action to require 2 presses at action level
                            action_sets[1]['actions'][0]['iterator'] = 2
                            print(f"    ✅ Updated edge: {screen_node_name} → {focus_node_name}: BACK x2")
                            
                            # Save updated edge
                            update_result = save_edges_batch(tree_id, [vertical_edge], team_id)
                            if update_result.get('success'):
                                print(f"    ✅ Edge saved with BACK x2")
                            else:
                                print(f"    ⚠️ Failed to save edge: {update_result.get('error')}")
                else:
                    print(f"    ⚠️ Edge not found: {vertical_edge_id}")
            except Exception as e:
                print(f"    ⚠️ Failed to update edge with BACK x2: {e}")
        
        print(f"\n  📊 Depth-first cycle complete:")
        print(f"     Horizontal: {edge_results['horizontal']}")
        print(f"     Enter (OK): {edge_results['enter']}")
        print(f"     Exit (BACK): {edge_results['exit']}")
        print(f"     Progress: {current_index + 1}/{len(items_to_validate)}")
        
        # ✅ TV DUAL-LAYER: Return BOTH edges (horizontal + vertical)
        horizontal_result = edge_results['horizontal']
        vertical_enter_result = edge_results['enter']
        vertical_exit_result = edge_results['exit']
        
        # Determine reverse direction for horizontal edge
        if nav_direction == 'RIGHT':
            reverse_direction = 'LEFT'
        elif nav_direction == 'LEFT':
            reverse_direction = 'RIGHT'
        elif nav_direction == 'DOWN':
            reverse_direction = 'UP'
        elif nav_direction is None:
            reverse_direction = None  # No navigation needed
        else:
            reverse_direction = 'DOWN'  # Fallback
        
        # ✅ Get iterator for display (from edge already in memory)
        display_iterator = 1
        if horizontal_edge:
            try:
                action_sets = horizontal_edge.get('action_sets', [])
                if len(action_sets) > 0 and action_sets[0].get('actions'):
                    first_action = action_sets[0]['actions'][0]
                    # Read iterator at action level, not in params
                    display_iterator = first_action.get('iterator', 1)
            except Exception as e:
                print(f"    ⚠️ Could not read iterator for display: {e}")
        
        # Build action display with iterator
        if nav_direction is None:
            forward_action_display = 'NONE'
            reverse_action_display = 'NONE'
        else:
            forward_action_display = f"{nav_direction} x{display_iterator}" if display_iterator > 1 else nav_direction
            reverse_action_display = f"{reverse_direction} x{display_iterator}" if display_iterator > 1 else reverse_direction
        
        return {
            'success': True,
            'item': current_item,
            'node_name': focus_node_name,
            'node_id': f"{focus_node_name}_temp",
            'has_more_items': has_more,
            'screenshot_url': screenshot_url,
            # ✅ TV: Return BOTH edges with their action_sets (dynamic direction for multi-row)
            'edges': [
                {
                    'edge_type': 'horizontal',
                    'action_sets': {
                        'forward': {
                            'source': prev_focus_name,
                            'target': focus_node_name,
                            'action': forward_action_display,  # ✅ Now includes iterator (e.g., "RIGHT x6")
                            'result': horizontal_result
                        },
                        'reverse': {
                            'source': focus_node_name,
                            'target': prev_focus_name,
                            'action': reverse_action_display,  # ✅ Now includes iterator (e.g., "LEFT x6")
                            'result': horizontal_result
                        }
                    }
                },
                {
                    'edge_type': 'vertical',
                    'action_sets': {
                        'forward': {
                            'source': focus_node_name,
                            'target': screen_node_name,
                            'action': 'OK',
                            'result': vertical_enter_result
                        },
                        'reverse': {
                            'source': screen_node_name,
                            'target': focus_node_name,
                            'action': 'BACK' if backs_needed == 1 else 'BACK x2',
                            'result': vertical_exit_result,
                            'backs_needed': backs_needed
                        }
                    }
                }
            ],
            'progress': {
                'current_item': current_index + 1,
                'total_items': len(items_to_validate)
            }
        }
    
    # ✅ MOBILE/WEB: PRESERVE EXISTING VALIDATION (DO NOT MODIFY BELOW)
    # Perform validation
    click_result = 'failed'
    back_result = 'failed'
    screenshot_url = None
    
    # 1. Execute navigation action (D-pad or click based on strategy)
    try:
        # Use strategy-aware action from context
        if context and context.strategy in ['dpad_with_screenshot', 'test_dpad_directions']:
            # D-pad navigation for TV/STB
            item_index = context.predicted_items.index(current_item) if current_item in context.predicted_items else 0
            menu_type = getattr(context, 'menu_type', 'horizontal')
            dpad_key = 'RIGHT' if menu_type == 'horizontal' else 'DOWN'
            
            print(f"    🎮 D-pad navigation: {item_index} x {dpad_key} + OK")
            
            # Navigate to item
            for i in range(item_index):
                controller.press_key(dpad_key)
                time.sleep(0.5)
            
            # Select item
            result = controller.press_key('OK')
        else:
            # Click navigation for mobile/web
            result = controller.click_element(current_item)
        
        # Handle async controllers (web) - run coroutine if needed
        import inspect
        if inspect.iscoroutine(result):
            import asyncio
            result = asyncio.run(result)
        
        click_success = result if isinstance(result, bool) else result.get('success', False)
        click_result = 'success' if click_success else 'failed'
        print(f"    {'✅' if click_success else '❌'} Click {click_result}")
        time.sleep(5)
        
        # 1.5. Capture screenshot + dump
        if click_success:
            # A. Capture Screenshot first (needed for OCR dump fallback)
            screenshot_path = None
            try:
                av_controllers = executor.device.get_controllers('av')
                av_controller = av_controllers[0] if av_controllers else None
                if av_controller:
                    screenshot_path = av_controller.take_screenshot()
                    if screenshot_path:
                        print(f"    📸 Screenshot captured: {screenshot_path}")
            except Exception as e:
                print(f"    ⚠️ Screenshot capture failed: {e}")
            
            # B. Capture Dump (Critical for node verification)
            dump_data = None
            try:
                # Try ADB/Web dump first
                if hasattr(controller, 'dump_elements') and callable(getattr(controller, 'dump_elements')):
                    dump_result = controller.dump_elements()
                    
                    # Handle async controllers (web) - run coroutine if needed
                    import inspect
                    if inspect.iscoroutine(dump_result):
                        import asyncio
                        dump_result = asyncio.run(dump_result)
                    
                    # Normalize dump format (mobile returns tuple, web returns dict)
                    if isinstance(dump_result, tuple):
                        # Mobile: (success, elements, error)
                        success, elements, error = dump_result
                        if success and elements:
                            dump_data = {'elements': elements, 'dump_type': 'xml'}
                            print(f"    📱 XML Dump captured: {len(elements)} elements")
                        else:
                            print(f"    ⚠️ XML Dump failed: {error or 'no elements'}")
                    elif isinstance(dump_result, dict):
                        # Web: already dict format
                        dump_data = {**dump_result, 'dump_type': 'xml'}
                        element_count = len(dump_result.get('elements', []))
                        print(f"    🌐 XML Dump captured: {element_count} elements")
                    else:
                        print(f"    ⚠️ Unknown dump format: {type(dump_result)}")
                
                # Fallback to OCR dump if ADB/Web dump failed or not available
                if not dump_data and screenshot_path:
                    print(f"    📊 XML dump not available → Trying OCR dump fallback")
                    text_controller = None
                    for v in executor.device.get_controllers('verification'):
                        if getattr(v, 'verification_type', None) == 'text':
                            text_controller = v
                            break
                    
                    if text_controller:
                        print(f"    📊 Extracting OCR dump from screenshot...")
                        ocr_result = text_controller.extract_ocr_dump(screenshot_path, confidence_threshold=30)
                        
                        if ocr_result.get('success') and ocr_result.get('elements'):
                            dump_data = {'elements': ocr_result['elements'], 'dump_type': 'ocr'}
                            print(f"    📊 OCR Dump: {len(ocr_result['elements'])} text elements")
                        else:
                            print(f"    ⚠️ OCR dump extraction failed or no text found")
                    else:
                        print(f"    ⚠️ Text controller not available for OCR dump")
                    
            except Exception as dump_err:
                print(f"    ⚠️ Dump capture failed: {dump_err}")
            
            # C. Upload Screenshot to R2
            if screenshot_path:
                try:
                    node_name_clean = node_name.replace('_temp', '')
                    sanitized_name = node_name_clean.replace(' ', '_')
                    r2_filename = f"{sanitized_name}.jpg"
                    userinterface_name = executor.exploration_state['userinterface_name']
                    upload_result = upload_navigation_screenshot(screenshot_path, userinterface_name, r2_filename)
                    
                    if upload_result.get('success'):
                        screenshot_url = upload_result.get('url')
                        print(f"    📸 Screenshot uploaded: {screenshot_url}")
                    else:
                        print(f"    ⚠️ Screenshot upload failed: {upload_result.get('error')}")
                except Exception as e:
                    print(f"    ⚠️ Screenshot upload process failed: {e}")
            else:
                print(f"    ⚠️ No screenshot to upload")
            
            # D. Store Data (screenshot and/or dump)
            # ✅ MOBILE/WEB: Store if we have either screenshot or dump
            if screenshot_url or dump_data:
                with executor._lock:
                    # Ensure list exists
                    if 'node_verification_data' not in executor.exploration_state:
                        executor.exploration_state['node_verification_data'] = []
                        
                    executor.exploration_state['node_verification_data'].append({
                        'node_id': node_name,  # ← Already clean (no _temp)
                        'node_label': node_name,  # ← Already clean (no _temp)
                        'dump': dump_data,
                        'screenshot_url': screenshot_url
                    })
                print(f"    ✅ Node verification data stored (dump: {dump_data is not None}, screenshot: {screenshot_url is not None})")
            else:
                print(f"    ❌ Skipping node verification data storage (no dump or screenshot captured)")
    except Exception as e:
        print(f"    ❌ Click failed: {e}")
    
    # 2. Press BACK (with double-back fallback)
    if click_result == 'success':
        try:
            # Select verification controller based on device model
            device_model = executor.device_model.lower()
            verifier = None
            
            if 'mobile' in device_model:
                # Mobile: Use ADB verification
                for v in executor.device.get_controllers('verification'):
                    if getattr(v, 'verification_type', None) == 'adb':
                        verifier = v
                        print(f"    📱 Using ADB verification for mobile device")
                        break
            elif 'host' in device_model:
                # Web (host): Use Playwright controller itself (has dump_elements for verification)
                verifier = controller  # The Playwright controller can verify elements
                print(f"    🌐 Using Playwright controller for web verification")
            else:
                # TV/STB: Image verification (not supported in AI exploration)
                print(f"    ⚠️ Device model '{device_model}' requires image verification - not supported in AI exploration")
            
            press_result = controller.press_key('BACK')
            # Handle async controllers (web)
            import inspect
            if inspect.iscoroutine(press_result):
                import asyncio
                asyncio.run(press_result)
            time.sleep(5)
            
            print(f"    🔍 Verifying return to home: {home_indicator}")
            
            back_success = False
            if verifier:
                if 'host' in device_model:
                    # Web: Check if home element exists by dumping and searching
                    try:
                        dump_result = verifier.dump_elements()
                        # Handle async
                        import inspect
                        if inspect.iscoroutine(dump_result):
                            import asyncio
                            dump_result = asyncio.run(dump_result)
                        
                        if isinstance(dump_result, dict) and dump_result.get('success'):
                            elements = dump_result.get('elements', [])
                            # Search for home indicator in elements
                            found = any(
                                home_indicator.lower() in str(elem.get('text', '')).lower() or
                                home_indicator.lower() in str(elem.get('selector', '')).lower()
                                for elem in elements
                            )
                            back_success = found
                            message = f"Element '{home_indicator}' {'found' if found else 'not found'} in page"
                            print(f"    {'✅' if back_success else '❌'} Back (1st) {('success' if back_success else 'failed')}: {message}")
                        else:
                            print(f"    ❌ Back (1st) failed: Could not dump elements")
                    except Exception as e:
                        print(f"    ❌ Back (1st) failed: {e}")
                else:
                    # Mobile: Use waitForElementToAppear
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
                press_result = controller.press_key('BACK')
                # Handle async controllers (web)
                import inspect
                if inspect.iscoroutine(press_result):
                    import asyncio
                    asyncio.run(press_result)
                time.sleep(5)
                
                if verifier:
                    if 'host' in device_model:
                        # Web: Check if home element exists by dumping and searching
                        try:
                            dump_result = verifier.dump_elements()
                            # Handle async
                            import inspect
                            if inspect.iscoroutine(dump_result):
                                import asyncio
                                dump_result = asyncio.run(dump_result)
                            
                            if isinstance(dump_result, dict) and dump_result.get('success'):
                                elements = dump_result.get('elements', [])
                                # Search for home indicator in elements
                                found = any(
                                    home_indicator.lower() in str(elem.get('text', '')).lower() or
                                    home_indicator.lower() in str(elem.get('selector', '')).lower()
                                    for elem in elements
                                )
                                back_success = found
                                message = f"Element '{home_indicator}' {'found' if found else 'not found'} in page"
                                print(f"    {'✅' if back_success else '❌'} Back (2nd) {('success' if back_success else 'failed')}: {message}")
                            else:
                                print(f"    ❌ Back (2nd) failed: Could not dump elements")
                        except Exception as e:
                            print(f"    ❌ Back (2nd) failed: {e}")
                    else:
                        # Mobile: Use waitForElementToAppear
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
            
        except Exception as e:
            print(f"    ⚠️ Back failed: {e}")
    
    # ✅ PROACTIVE RECOVERY: If click OR back failed, go home to ensure clean state for next step
    if click_result == 'failed' or back_result == 'failed':
        print(f"    🔄 Validation failed (click={click_result}, back={back_result}) - going home for next step...")
        try:
            import asyncio
            home_id = executor.exploration_state['home_id']
            userinterface_name = executor.exploration_state['userinterface_name']
            
            # ✅ Use execute_navigation with target_node_label='home' (correct method)
            nav_result = asyncio.run(executor.device.navigation_executor.execute_navigation(
                tree_id=tree_id,
                userinterface_name=userinterface_name,
                target_node_label='home',
                team_id=team_id
            ))
            
            if nav_result.get('success'):
                print(f"    ✅ Recovery successful - ready for next validation")
                if back_result == 'failed':
                    back_result = 'failed_recovered'
            else:
                error_msg = nav_result.get('error', 'Unknown error')
                print(f"    ❌ Recovery failed: {error_msg}")
                
                # ✅ STOP VALIDATION: Recovery failed, no point continuing
                print(f"    🛑 STOPPING validation - recovery failed, cannot continue")
                with executor._lock:
                    executor.exploration_state['status'] = 'validation_failed'
                    executor.exploration_state['error'] = f"Validation recovery failed: {error_msg}. Cannot navigate to home."
                    executor.exploration_state['current_step'] = 'Validation stopped - recovery failed'
                
                return {
                    'success': False,
                    'error': f"Validation stopped: Cannot recover to home after failed validation.\n\n"
                            f"Reason: {error_msg}\n\n"
                            f"Current item: {current_item} (step {current_index + 1}/{len(items_to_validate)})\n\n"
                            f"Action required: Fix navigation to home before continuing validation.",
                    'validation_stopped': True,
                    'failed_at_item': current_item,
                    'failed_at_index': current_index
                }
                
        except Exception as recovery_error:
            print(f"    ❌ Recovery exception: {recovery_error}")
            
            # ✅ STOP VALIDATION: Recovery exception, no point continuing
            print(f"    🛑 STOPPING validation - recovery exception")
            with executor._lock:
                executor.exploration_state['status'] = 'validation_failed'
                executor.exploration_state['error'] = f"Validation recovery exception: {recovery_error}"
                executor.exploration_state['current_step'] = 'Validation stopped - recovery exception'
            
            return {
                'success': False,
                'error': f"Validation stopped: Recovery exception occurred.\n\n"
                        f"Exception: {recovery_error}\n\n"
                        f"Current item: {current_item} (step {current_index + 1}/{len(items_to_validate)})\n\n"
                        f"Action required: Check navigation configuration.",
                'validation_stopped': True,
                'failed_at_item': current_item,
                'failed_at_index': current_index
            }
    
    # 3. Update edge with validation results (using action_sets like frontend)
    with executor._lock:
        home_id = executor.exploration_state['home_id']
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
                
                # Save updated edge with correct action_sets structure using batch (upsert)
                update_result = save_edges_batch(tree_id, [edge], team_id)
                edge_updated = update_result.get('success', False)
        
        # Move to next
        executor.exploration_state['current_validation_index'] = current_index + 1
        has_more = executor.exploration_state['current_validation_index'] < len(items_to_validate)
        
        if not has_more:
            executor.exploration_state['status'] = 'validation_complete'
            executor.exploration_state['current_step'] = 'Edge validation complete - ready for node verification'
            
            # ✅ CRITICAL: Invalidate cache ONCE after ALL validations complete
            # This ensures frontend gets fresh data with all validation results
            print(f"\n  🔄 All validations complete - invalidating cache...")
            invalidate_navigation_cache_for_tree(tree_id, team_id)
            print(f"  ✅ Cache invalidated for tree {tree_id}")
        else:
            executor.exploration_state['status'] = 'awaiting_validation'
            # ✅ FIX: Update current_step to show NEXT item that will be validated
            next_index = executor.exploration_state['current_validation_index']
            next_item = items_to_validate[next_index]
            next_node_name = target_to_node_map.get(next_item, f"{next_item}_temp")
            next_node_display = next_node_name.replace('_temp', '')
            executor.exploration_state['current_step'] = f"Ready: Step {next_index + 1}/{len(items_to_validate)} - home → {next_node_display}: click_element(\"{next_item}\")"
        
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
                'current_item': executor.exploration_state['current_validation_index'],
                'total_items': len(items_to_validate)
            }
        }

def execute_phase2_next_item(executor) -> Dict[str, Any]:
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
    if not executor.context:
        return {'success': False, 'error': 'No active exploration'}
    
    items = executor.context.predicted_items
    current_idx = executor.context.current_step
    
    if current_idx >= len(items):
        return {
            'success': True,
            'has_more_items': False,
            'message': 'All items completed'
        }
    
    item = items[current_idx]
    
    # ✅ SPECIAL HANDLING: First LEFT item - navigate to home first
    # For horizontal D-pad navigation, after exploring RIGHT items,
    # we need to physically move cursor back to home before exploring LEFT items
    items_left = getattr(executor.context, 'items_left_of_home', [])
    if items_left and item == items_left[0]:
        # This is the first left item - navigate to home node first
        print(f"\n[@exploration_executor] TRANSITION: Navigating to HOME before exploring LEFT items")
        print(f"  First left item: {item}")
        print(f"  All left items: {items_left}")
        
        try:
            # Use MCP navigate_to_node tool to physically move to home
            if hasattr(executor.exploration_engine, 'mcp_server') and executor.exploration_engine.mcp_server:
                nav_result = executor.exploration_engine.mcp_server.call_tool('navigate_to_node', {
                    'tree_id': executor.context.tree_id,
                    'target_node_label': 'home',
                    'device_id': executor.context.device_id,
                    'host_name': executor.context.host_name,
                    'userinterface_name': executor.context.userinterface_name,
                    'team_id': executor.context.team_id
                })
                
                if nav_result and not nav_result.get('isError', False):
                    print(f"  ✅ Successfully navigated to home")
                else:
                    print(f"  ⚠️ Navigation to home failed: {nav_result}")
                    # Continue anyway - edge creation will handle it
            else:
                print(f"  ⚠️ MCP server not available - skipping navigation")
                
        except Exception as e:
            print(f"  ⚠️ Navigation to home error: {e}")
            import traceback
            traceback.print_exc()
            # Continue anyway
    
    # Create and test single edge via MCP
    result = executor.exploration_engine.phase2_create_single_edge_mcp(item, executor.context)
    
    if result['success']:
        executor.context.completed_items.append(item)
        executor.context.current_step += 1
        executor.context.add_step_result(f'create_{item}', result)
        
        return {
            'success': True,
            'item': item,
            'node_created': True,
            'edge_created': True,
            'edge_tested': True,
            'has_more_items': executor.context.current_step < len(items),
            'progress': {
                'current_item': executor.context.current_step,
                'total_items': len(items)
            },
            'context': executor.context.to_dict()
        }
    else:
        executor.context.failed_items.append({
            'item': item,
            'error': result.get('error')
        })
        executor.context.add_step_result(f'create_{item}', result)
        
        return {
            'success': False,
            'item': item,
            'error': result.get('error'),
            'has_more_items': False,  # Stop on failure
            'context': executor.context.to_dict()
        }

