import time
from typing import Dict, Any
from backend_host.src.services.ai_exploration.node_generator import NodeGenerator
from shared.src.lib.database.navigation_trees_db import get_edge_by_id, save_edges_batch
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
    with executor._lock:
        print(f"\n{'='*80}")
        print(f"[@ExplorationExecutor:validate_next_item] VALIDATION STEP START")
        print(f"{'='*80}")
        
        if executor.exploration_state['status'] not in ['awaiting_validation', 'validating']:
            error_msg = f"Cannot validate: status is {executor.exploration_state['status']}"
            print(f"[@ExplorationExecutor:validate_next_item] ❌ {error_msg}")
            return {
                'success': False,
                'error': error_msg
            }
        
        tree_id = executor.exploration_state['tree_id']
        team_id = executor.exploration_state['team_id']
        current_index = executor.exploration_state['current_validation_index']
        items_to_validate = executor.exploration_state['items_to_validate']
        
        print(f"[@ExplorationExecutor:validate_next_item] Current index: {current_index}")
        print(f"[@ExplorationExecutor:validate_next_item] Total items: {len(items_to_validate)}")
        print(f"[@ExplorationExecutor:validate_next_item] Items to validate: {items_to_validate}")
        
        if current_index >= len(items_to_validate):
            print(f"[@ExplorationExecutor:validate_next_item] ✅ All items validated!")
            executor.exploration_state['status'] = 'validation_complete'
            return {
                'success': True,
                'message': 'All items validated',
                'has_more_items': False
            }
        
        current_item = items_to_validate[current_index]
        target_to_node_map = executor.exploration_state['target_to_node_map']
        node_name = target_to_node_map.get(current_item)
        
        print(f"[@ExplorationExecutor:validate_next_item] Validating item: {current_item}")
        print(f"[@ExplorationExecutor:validate_next_item] Node name: {node_name}")
        
        if not node_name:
            # Fallback
            node_gen = NodeGenerator(tree_id, team_id)
            node_name_clean = node_gen.target_to_node_name(current_item)
            node_name = node_name_clean  # ← Fixed: ID doesn't have _temp, only label does
            print(f"[@ExplorationExecutor:validate_next_item] Using fallback node name: {node_name}")
        
        # Skip home
        if 'home' in node_name.lower() and node_name != 'home_temp':
            print(f"[@ExplorationExecutor:validate_next_item] ⏭️  Skipping home node: {node_name}")
            executor.exploration_state['current_validation_index'] = current_index + 1
            return validate_next_item(executor)
        
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
                    
                    # Store Home data (dump and/or screenshot)
                    executor.exploration_state['node_verification_data'].append({
                        'node_id': executor.exploration_state.get('home_id', 'home'),
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
        
        print(f"\n  🐛 DEBUG: Row Structure Analysis")
        print(f"     lines = {lines}")
        print(f"     Total rows: {len(lines)}")
        for idx, row in enumerate(lines):
            print(f"     Row {idx}: {len(row)} items = {row}")
        
        # Calculate node names
        node_gen = NodeGenerator(tree_id, team_id)
        # Use start_node_id from state
        start_node_id = executor.exploration_state.get('home_id', 'home')
        start_node_label = executor.exploration_state.get('start_node', 'home')
        
        screen_node_name = node_gen.target_to_node_name(current_item)
        focus_node_name = f"{start_node_id}_{screen_node_name}"
        
        print(f"\n  🐛 DEBUG: Current Item Analysis")
        print(f"     current_item = '{current_item}'")
        print(f"     current_index = {current_index}")
        print(f"     screen_node_name = '{screen_node_name}'")
        print(f"     focus_node_name = '{focus_node_name}'")
        print(f"     start_node_id = '{start_node_id}'")
        
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
                print(f"  🐛 DEBUG: Found current_item '{current_item}' in Row {row_idx}, Position {current_position_in_row}")
                break
        
        if current_row_index == -1:
            print(f"  🐛 DEBUG: ⚠️ current_item '{current_item}' NOT FOUND in any row!")
        
        # Find previous item's position (if exists)
        if current_index > 0:
            prev_item = items_to_validate[current_index - 1]
            print(f"\n  🐛 DEBUG: Previous Item Analysis")
            print(f"     prev_item = '{prev_item}'")
            for row_idx, row_items in enumerate(lines):
                if prev_item in row_items:
                    prev_row_index = row_idx
                    prev_position_in_row = row_items.index(prev_item)
                    print(f"  🐛 DEBUG: Found prev_item '{prev_item}' in Row {row_idx}, Position {prev_position_in_row}")
                    break
            
            if prev_row_index == -1:
                print(f"  🐛 DEBUG: ⚠️ prev_item '{prev_item}' NOT FOUND in any row!")
        
        # Determine navigation type
        # Key insight: Check if we're in the SAME row or DIFFERENT row
        is_same_row = (prev_row_index == current_row_index) and (prev_row_index != -1)
        is_first_item_overall = (current_index == 0)
        
        print(f"\n  🐛 DEBUG: Navigation Decision Logic")
        print(f"     is_first_item_overall = {is_first_item_overall}")
        print(f"     current_row_index = {current_row_index}")
        print(f"     prev_row_index = {prev_row_index}")
        print(f"     is_same_row = {is_same_row}")
        
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
                # Check if item is LEFT or RIGHT of home
                items_left = executor.exploration_state.get('exploration_plan', {}).get('items_left_of_home', [])
                is_left_item = current_item in items_left
                nav_direction = 'LEFT' if is_left_item else 'RIGHT'
                print(f"  🐛 DEBUG: ✅ Decision: FIRST ITEM, start_node IN Row {current_row_index + 1} → {nav_direction}")
                print(f"     Reason: '{start_node_label}' is part of Row {current_row_index + 1}, item is {'LEFT' if is_left_item else 'RIGHT'} of home")
            else:
                nav_direction = 'DOWN'  # start_node is NOT in this row, vertical navigation
                print(f"  🐛 DEBUG: ✅ Decision: FIRST ITEM, start_node NOT in rows → DOWN")
                print(f"     Reason: '{start_node_label}' is Row 0, navigating down to Row {current_row_index + 1}")
        elif is_same_row:
            # Same row: horizontal navigation - check if LEFT or RIGHT of home
            prev_item_name = node_gen.target_to_node_name(items_to_validate[current_index - 1])
            prev_focus_name = f"{start_node_id}_{prev_item_name}"
            items_left = executor.exploration_state.get('exploration_plan', {}).get('items_left_of_home', [])
            is_left_item = current_item in items_left
            nav_direction = 'LEFT' if is_left_item else 'RIGHT'
            print(f"  🐛 DEBUG: ✅ Decision: SAME ROW → {nav_direction} within row")
            print(f"     Reason: Both items in Row {current_row_index + 1}, item is {'LEFT' if is_left_item else 'RIGHT'} of home")
            print(f"     prev_focus_name = {prev_focus_name}")
        else:
            # Different rows: vertical navigation
            prev_item_name = node_gen.target_to_node_name(items_to_validate[current_index - 1])
            prev_focus_name = f"{start_node_id}_{prev_item_name}"
            nav_direction = 'DOWN'  # Moving to new row vertically
            print(f"  🐛 DEBUG: ✅ Decision: DIFFERENT ROW → DOWN to new row")
            print(f"     Reason: Row transition from Row {prev_row_index + 1} to Row {current_row_index + 1}")
            print(f"     prev_focus_name = {prev_focus_name}")
        
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
                nav_result = asyncio.run(executor.device.navigation_executor.execute_navigation(
                    tree_id=tree_id,
                    userinterface_name=executor.exploration_state['userinterface_name'],
                    target_node_label=start_node_label,
                    team_id=team_id
                ))
                
                if nav_result.get('success'):
                    print(f"    ✅ At '{start_node_label}' - ready for LEFT navigation")
                else:
                    error_msg = nav_result.get('error', 'Unknown error')
                    print(f"    ❌ Navigation to '{start_node_label}' failed: {error_msg}")
                    print(f"    ⚠️ Continuing anyway - validation may fail")
            except Exception as e:
                print(f"    ❌ LEFT transition exception: {e}")
                print(f"    ⚠️ Continuing anyway - validation may fail")
        
        # ✅ RECOVERY: Only navigate to home if we're doing DOWN navigation (home not in same row)
        elif is_first_item_overall and nav_direction == 'DOWN':
            print(f"\n    🔄 ROW {display_row} START: Ensuring we're at home (Row 0)...")
            try:
                import asyncio
                nav_result = asyncio.run(executor.device.navigation_executor.execute_navigation(
                    tree_id=tree_id,
                    userinterface_name=executor.exploration_state['userinterface_name'],
                    target_node_label='home',
                    team_id=team_id
                ))
                
                if nav_result.get('success'):
                    print(f"    ✅ At home (Row 0) - ready for DOWN navigation to Row {display_row}")
                else:
                    error_msg = nav_result.get('error', 'Unknown error')
                    print(f"    ❌ Navigation to home failed: {error_msg}")
                    print(f"    ⚠️ Continuing anyway - validation may fail")
            except Exception as e:
                print(f"    ❌ Recovery exception: {e}")
                print(f"    ⚠️ Continuing anyway - validation may fail")
        
        # ✅ ROW TRANSITION: For different rows (DOWN navigation)
        elif not is_same_row and not is_first_item_overall:
            print(f"\n    🔽 ROW {display_row} TRANSITION: From Row {prev_row_index + 1} via DOWN")
            # No recovery needed - we're already positioned at previous row's last item
        
        # Print validation info
        print(f"     📍 Row {display_row}, Position {current_position_in_row + 1}")
        print(f"     {'🔽 VERTICAL to new row' if nav_direction == 'DOWN' else '➡️ HORIZONTAL within row'}")
        print(f"     Edges to test:")
        print(f"       1. {prev_focus_name} → {focus_node_name}: {nav_direction}")
        print(f"       2. {focus_node_name} ↓ {screen_node_name}: OK")
        print(f"       3. {screen_node_name} ↑ {focus_node_name}: BACK")
        
        edge_results = {
            'horizontal': 'pending',
            'enter': 'pending',
            'exit': 'pending'
        }
        screenshot_url = None
        
        # Edge 1: Focus navigation (RIGHT for horizontal, DOWN for new row)
        try:
            print(f"\n    Edge 1/3: {prev_focus_name} → {focus_node_name}")
            result = controller.press_key(nav_direction)
            import inspect
            if inspect.iscoroutine(result):
                import asyncio
                result = asyncio.run(result)
            
            edge_results['horizontal'] = 'success'
            print(f"    ✅ Focus navigation: {nav_direction}")
            time.sleep(1.5)  # 1500ms for D-PAD navigation
            
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
            result = controller.press_key('OK')
            import inspect
            if inspect.iscoroutine(result):
                import asyncio
                result = asyncio.run(result)
            
            edge_results['enter'] = 'success'
            print(f"    ✅ Vertical enter: OK")
            time.sleep(3)
            
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
            result = controller.press_key('BACK')
            import inspect
            if inspect.iscoroutine(result):
                import asyncio
                asyncio.run(result)
            time.sleep(2)
            
            # Verify if start_node has verification
            if executor.exploration_state.get('start_node_has_verification', False):
                start_node_id = executor.exploration_state.get('home_id', 'home')
                start_node_label = executor.exploration_state.get('start_node', 'home')
                
                import asyncio
                verify = asyncio.run(executor.device.verification_executor.verify_node(
                    node_id=start_node_id, 
                    userinterface_name=executor.exploration_state['userinterface_name'],
                    team_id=team_id, 
                    tree_id=tree_id
                ))
                
                if not verify.get('success'):
                    print(f"    🔄 Trying second BACK...")
                    result = controller.press_key('BACK')
                    if inspect.iscoroutine(result):
                        asyncio.run(result)
                    time.sleep(2)
                    
                    verify = asyncio.run(executor.device.verification_executor.verify_node(
                        node_id=start_node_id, 
                        userinterface_name=executor.exploration_state['userinterface_name'],
                        team_id=team_id, 
                        tree_id=tree_id
                    ))
                    
                    if verify.get('success'):
                        backs_needed = 2
                        print(f"    ✅ Double BACK worked")
                    else:
                        print(f"    🔄 Recovery to '{start_node_label}'...")
                        asyncio.run(executor.device.navigation_executor.execute_navigation(
                            tree_id=tree_id, 
                            userinterface_name=executor.exploration_state['userinterface_name'],
                            target_node_label=start_node_label, 
                            team_id=team_id
                        ))
            
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
            else:
                executor.exploration_state['status'] = 'awaiting_validation'
        
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
        reverse_direction = 'LEFT' if nav_direction == 'RIGHT' else 'UP'
        
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
                            'action': nav_direction,  # RIGHT for same row, DOWN for new row
                            'result': horizontal_result
                        },
                        'reverse': {
                            'source': focus_node_name,
                            'target': prev_focus_name,
                            'action': reverse_direction,  # LEFT for same row, UP for new row
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

