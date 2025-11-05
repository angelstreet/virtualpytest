"""
AI Generation Routes - HTTP endpoints for AI-driven tree exploration
Auto-proxied from /server/ai-generation/* to /host/ai-generation/*
"""

from flask import Blueprint, request, jsonify
import threading
from uuid import uuid4
from datetime import datetime, timezone
from typing import Dict

from services.ai_exploration import ExplorationEngine
from shared.src.lib.database.navigation_trees_db import (
    save_node,
    save_edge,
    get_node_by_id,
    get_edge_by_id,
    delete_node,
    delete_tree_cascade,
    get_tree_nodes,
    get_tree_edges
)

ai_generation_bp = Blueprint('ai_generation', __name__, url_prefix='/host/ai-generation')

# In-memory exploration state (minimalist!)
_exploration_sessions: Dict[str, Dict] = {}
_exploration_locks = {}


@ai_generation_bp.route('/start-exploration', methods=['POST'])
def start_exploration():
    """
    Start AI exploration in background thread
    
    Request body:
    {
        'tree_id': 'uuid',
        'host_name': 'sunri-pi1',
        'device_id': 'device1',
        'exploration_depth': 5,
        'userinterface_name': 'horizon_android_mobile'
    }
    Query params (auto-added by buildServerUrl):
        'team_id': 'team_1'
    
    Response:
    {
        'success': True,
        'exploration_id': 'uuid',
        'message': 'Exploration started'
    }
    """
    try:
        from flask import current_app
        
        data = request.get_json() or {}
        team_id = request.args.get('team_id')  # Auto-added by buildServerUrl
        
        # Extract parameters from body
        tree_id = data.get('tree_id')
        device_id = data.get('device_id', 'device1')
        host_name = data.get('host_name')
        userinterface_name = data.get('userinterface_name')
        exploration_depth = data.get('exploration_depth', 5)
        
        # Validate required params
        if not team_id:
            return jsonify({'success': False, 'error': 'team_id required in query parameters'}), 400
        if not tree_id:
            return jsonify({'success': False, 'error': 'tree_id is required'}), 400
        if not host_name:
            return jsonify({'success': False, 'error': 'host_name is required'}), 400
        if not userinterface_name:
            return jsonify({'success': False, 'error': 'userinterface_name is required'}), 400
        
        # Get device info from registry (like testcase routes do)
        if not hasattr(current_app, 'host_devices') or device_id not in current_app.host_devices:
            return jsonify({'success': False, 'error': f'Device {device_id} not found in registry'}), 404
        
        device = current_app.host_devices[device_id]
        device_name = device.device_name
        device_model_name = device.device_model
        
        # ✅ CRITICAL: Capture actual Flask app object for background thread
        # Similar to how goto_live.py gets device in context before execution
        app = current_app._get_current_object()
        
        # Generate exploration ID
        exploration_id = str(uuid4())
        
        print(f"[@route:ai_generation:start_exploration] Starting exploration {exploration_id}")
        print(f"  Tree: {tree_id}")
        print(f"  Device: {device_model_name} ({device_id})")
        print(f"  Host: {host_name}")
        print(f"  UI: {userinterface_name}")
        print(f"  Depth: {exploration_depth}")
        
        # Initialize exploration state
        _exploration_sessions[exploration_id] = {
            'exploration_id': exploration_id,
            'tree_id': tree_id,
            'team_id': team_id,
            'host_name': host_name,  # Store for status polling
            'device_id': device_id,
            'device_model_name': device_model_name,
            'userinterface_name': userinterface_name,
            'status': 'starting',
            'phase': 'analysis',  # NEW: 'analysis' or 'exploration'  
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
                'screenshot': None  # Add screenshot URL/path
            },
            'exploration_plan': None,  # NEW: Store AI's plan for user to review
            'created_nodes': [],
            'created_edges': [],
            'created_subtrees': [],
            'proposed_nodes': [],
            'proposed_edges': [],
            'started_at': datetime.now(timezone.utc).isoformat(),
            'completed_at': None,
            'error': None
        }
        
        # Start exploration in background thread
        def run_exploration():
            # ✅ Use captured app object (not current_app proxy) for background thread context
            with app.app_context():
                try:
                    # Update status
                    _exploration_sessions[exploration_id]['status'] = 'exploring'
                    _exploration_sessions[exploration_id]['current_step'] = 'Capturing initial screenshot...'
                    
                    # Create exploration engine with progress callback
                    def update_screenshot(screenshot_path: str):
                        """Convert screenshot path to URL and update session"""
                        try:
                            from shared.src.lib.utils.build_url_utils import buildHostImageUrl
                            from backend_host.src.lib.utils.host_utils import get_host_instance
                            
                            host = get_host_instance()
                            host_dict = host.to_dict()
                            
                            print(f"\n{'='*80}")
                            print(f"[@route:ai_generation:update_screenshot] BUILDING URL")
                            print(f"{'='*80}")
                            print(f"📸 Local Path: {screenshot_path}")
                            print(f"🏠 Host: {host_dict.get('host_name')} ({host_dict.get('host_ip')})")
                            
                            # Use buildHostImageUrl which handles any file path (not just capture_*.jpg format)
                            screenshot_url = buildHostImageUrl(host_dict, screenshot_path)
                            
                            print(f"🌐 Built URL: {screenshot_url}")
                            print(f"{'='*80}\n")
                            
                            _exploration_sessions[exploration_id]['current_analysis']['screenshot'] = screenshot_url
                        except Exception as e:
                            print(f"[@route:ai_generation] Failed to convert screenshot path to URL: {e}")
                            import traceback
                            traceback.print_exc()
                    
                    def update_progress(step: str, screenshot: str = None, analysis: dict = None):
                        """Update progress in session (step, screenshot, analysis)"""
                        try:
                            _exploration_sessions[exploration_id]['current_step'] = step
                            print(f"[@route:ai_generation] Progress: {step}")
                            
                            # Update screenshot if provided
                            if screenshot:
                                update_screenshot(screenshot)
                            
                            # Update analysis if provided
                            if analysis:
                                _exploration_sessions[exploration_id]['current_analysis'].update({
                                    'screen_name': analysis.get('screen_name', ''),
                                    'elements_found': analysis.get('elements_found', []),
                                    'reasoning': analysis.get('reasoning', '')
                                })
                            
                        except Exception as e:
                            print(f"[@route:ai_generation] Failed to update progress: {e}")
                    
                    engine = ExplorationEngine(
                        tree_id=tree_id,
                        device_id=device_id,
                        host_name=host_name,
                        device_model_name=device_model_name,
                        team_id=team_id,
                        userinterface_name=userinterface_name,
                        depth_limit=exploration_depth,
                        screenshot_callback=update_screenshot,  # Pass callback for screenshot updates
                        progress_callback=update_progress  # Pass callback for progress updates
                    )
                    
                    # ✅ PHASE 1 ONLY: Analyze and create plan (don't explore yet)
                    result = engine.analyze_and_plan()
                    
                    # Update state with analysis results
                    if result['success']:
                        _exploration_sessions[exploration_id]['status'] = 'awaiting_approval'
                        _exploration_sessions[exploration_id]['phase'] = 'analysis_complete'
                        _exploration_sessions[exploration_id]['current_step'] = 'Analysis complete. Review the plan below.'
                        _exploration_sessions[exploration_id]['exploration_plan'] = result['plan']
                        
                        # Update current_analysis but PRESERVE the screenshot that was already set
                        existing_screenshot = _exploration_sessions[exploration_id]['current_analysis'].get('screenshot')
                        _exploration_sessions[exploration_id]['current_analysis'] = {
                            'screen_name': result['plan'].get('screen_name', 'Initial Screen'),
                            'elements_found': result['plan'].get('items', []),
                            'reasoning': result['plan'].get('reasoning', ''),
                            'screenshot': existing_screenshot  # ✅ PRESERVE screenshot!
                        }
                        
                        # Store engine state for Phase 2
                        _exploration_sessions[exploration_id]['engine'] = engine
                    else:
                        _exploration_sessions[exploration_id]['status'] = 'failed'
                        _exploration_sessions[exploration_id]['error'] = result.get('error', 'Failed to analyze screen')
                        _exploration_sessions[exploration_id]['current_step'] = f"Analysis failed: {result.get('error')}"
                    
                    _exploration_sessions[exploration_id]['completed_at'] = datetime.now(timezone.utc).isoformat()
                    
                except Exception as e:
                    print(f"[@route:ai_generation:run_exploration] Error: {e}")
                    _exploration_sessions[exploration_id]['status'] = 'failed'
                    _exploration_sessions[exploration_id]['error'] = str(e)
                    _exploration_sessions[exploration_id]['current_step'] = f"Error: {str(e)}"
                    _exploration_sessions[exploration_id]['completed_at'] = datetime.now(timezone.utc).isoformat()
        
        # Start thread
        thread = threading.Thread(target=run_exploration, daemon=True)
        thread.start()
        
        return jsonify({
            'success': True,
            'exploration_id': exploration_id,
            'host_name': host_name,  # Return so frontend can use in status polls
            'message': 'Exploration started'
        })
        
    except Exception as e:
        print(f"[@route:ai_generation:start_exploration] Error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_generation_bp.route('/exploration-status/<exploration_id>', methods=['GET'])
def exploration_status(exploration_id):
    """
    Get current exploration status (polling endpoint)
    
    Response:
    {
        'success': True,
        'exploration_id': 'uuid',
        'status': 'exploring',
        'current_step': '...',
        'progress': {...},
        'proposed_nodes': [...],  # Only when completed
        'proposed_edges': [...]   # Only when completed
    }
    """
    try:
        if exploration_id not in _exploration_sessions:
            return jsonify({
                'success': False,
                'error': 'Exploration session not found'
            }), 404
        
        session = _exploration_sessions[exploration_id]
        
        response = {
            'success': True,
            'exploration_id': exploration_id,
            'status': session['status'],
            'phase': session.get('phase', 'analysis'),  # NEW: Include phase
            'current_step': session['current_step'],
            'progress': session['progress'],
            'current_analysis': session['current_analysis'],
            'exploration_plan': session.get('exploration_plan')  # NEW: Include plan
        }
        
        # Include proposed nodes/edges when completed
        if session['status'] == 'completed':
            response['proposed_nodes'] = session['proposed_nodes']
            response['proposed_edges'] = session['proposed_edges']
        
        # Include error if failed
        if session['status'] == 'failed':
            response['error'] = session['error']
        
        return jsonify(response)
        
    except Exception as e:
        print(f"[@route:ai_generation:exploration_status] Error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_generation_bp.route('/continue-exploration', methods=['POST'])
def continue_exploration():
    """
    Phase 2a: CREATE all nodes and edges structure (instant)
    
    This creates:
    - Root node: home_temp
    - Child nodes: en_temp, search_temp, etc. (all with _temp suffix)
    - Edges: home_temp → en_temp, etc. (with EMPTY action_sets for now)
    
    Body:
    {
        'exploration_id': 'abc123',
        'host_name': 'sunri-pi1'
    }
    
    Query params (auto-added):
        'team_id': 'team_1'
    
    Response:
    {
        'success': True,
        'nodes_created': 11,
        'edges_created': 10,
        'message': 'Structure created, ready to validate'
    }
    """
    try:
        data = request.get_json() or {}
        team_id = request.args.get('team_id')
        exploration_id = data.get('exploration_id')
        
        if not team_id:
            return jsonify({'success': False, 'error': 'team_id required'}), 400
        
        if not exploration_id:
            return jsonify({'success': False, 'error': 'exploration_id required'}), 400
        
        if exploration_id not in _exploration_sessions:
            return jsonify({'success': False, 'error': 'Exploration session not found'}), 404
        
        session = _exploration_sessions[exploration_id]
        
        if session['status'] != 'awaiting_approval':
            return jsonify({
                'success': False,
                'error': f"Cannot continue: status is {session['status']}, expected 'awaiting_approval'"
            }), 400
        
        print(f"[@route:ai_generation:continue_exploration] Creating structure for {exploration_id}")
        
        # Get necessary data from session
        tree_id = session['tree_id']
        items = session['exploration_plan']['items']
        engine = session.get('engine')
        
        if not engine:
            return jsonify({'success': False, 'error': 'Engine not found'}), 500
        
        # Create root node: home_temp
        from backend_host.src.services.ai_exploration.node_generator import NodeGenerator
        from shared.src.lib.database.navigation_trees_db import save_node, save_edge
        
        node_gen = NodeGenerator(tree_id, team_id)
        
        # 1. Create home_temp node
        home_node = node_gen.create_node_data(
            node_name='home_temp',
            position={'x': 250, 'y': 100},
            ai_analysis={
                'suggested_name': 'home',
                'screen_type': 'screen',
                'reasoning': 'Root node - initial screen'
            },
            node_type='screen'
        )
        
        home_result = save_node(tree_id, home_node, team_id)
        if not home_result['success']:
            return jsonify({'success': False, 'error': f"Failed to create home node: {home_result.get('error')}"}), 500
        
        nodes_created = ['home_temp']
        edges_created = []
        
        # 2. Create all child nodes (using UNIVERSAL naming)
        for idx, item in enumerate(items):
            # item is a navigation target (EDGE) - convert to node name (DESTINATION)
            node_name_clean = node_gen.target_to_node_name(item)
            
            # Skip if it's 'home' (already created as root)
            if node_name_clean == 'home':
                continue
            
            node_name = f"{node_name_clean}_temp"
            position_x = 250 + (idx % 5) * 200
            position_y = 300 + (idx // 5) * 150
            
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
            
            node_result = save_node(tree_id, node_data, team_id)
            if node_result['success']:
                nodes_created.append(node_name)
                
                # Store mapping: original_text → node_name for validation
                if 'target_to_node_map' not in session:
                    session['target_to_node_map'] = {}
                session['target_to_node_map'][item] = node_name
            
            # 3. Create edge with EMPTY actions (to be filled during validation)
            edge_data = node_gen.create_edge_data(
                source='home_temp',
                target=node_name,
                actions=[],  # Empty - will be filled during validation
                reverse_actions=[],  # Empty - will be filled during validation
                label=''
            )
            
            edge_result = save_edge(tree_id, edge_data, team_id)
            if edge_result['success']:
                edges_created.append(edge_data['edge_id'])
        
        # Update session
        session['status'] = 'structure_created'
        session['nodes_created'] = nodes_created
        session['edges_created'] = edges_created
        session['current_step'] = f'Created {len(nodes_created)} nodes and {len(edges_created)} edges. Ready to validate.'
        session['items_to_validate'] = items
        session['current_validation_index'] = 0
        
        return jsonify({
            'success': True,
            'nodes_created': len(nodes_created),
            'edges_created': len(edges_created),
            'message': 'Structure created successfully',
            'node_ids': nodes_created,
            'edge_ids': edges_created
        })
        
    except Exception as e:
        print(f"[@route:ai_generation:continue_exploration] Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@ai_generation_bp.route('/start-validation', methods=['POST'])
def start_validation():
    """
    Phase 2b: Start validation process
    Sets status to ready for validation
    
    Body:
    {
        'exploration_id': 'abc123',
        'host_name': 'sunri-pi1'
    }
    
    Response:
    {
        'success': True,
        'message': 'Ready to validate',
        'total_items': 10
    }
    """
    try:
        data = request.get_json() or {}
        team_id = request.args.get('team_id')
        exploration_id = data.get('exploration_id')
        
        if not team_id:
            return jsonify({'success': False, 'error': 'team_id required'}), 400
        
        if not exploration_id:
            return jsonify({'success': False, 'error': 'exploration_id required'}), 400
        
        if exploration_id not in _exploration_sessions:
            return jsonify({'success': False, 'error': 'Exploration session not found'}), 404
        
        session = _exploration_sessions[exploration_id]
        
        if session['status'] != 'structure_created':
            return jsonify({
                'success': False,
                'error': f"Cannot start validation: status is {session['status']}, expected 'structure_created'"
            }), 400
        
        session['status'] = 'awaiting_validation'
        session['current_validation_index'] = 0
        
        return jsonify({
            'success': True,
            'message': 'Ready to start validation',
            'total_items': len(session['items_to_validate'])
        })
        
    except Exception as e:
        print(f"[@route:ai_generation:start_validation] Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@ai_generation_bp.route('/validate-next-item', methods=['POST'])
def validate_next_item():
    """
    Phase 2b: Validate ONE edge by testing click → back
    
    This will:
    1. Click the element
    2. Press BACK
    3. Verify we're back on home screen
    4. UPDATE the edge's action_sets with the tested actions
    
    Body:
    {
        'exploration_id': 'abc123',
        'host_name': 'sunri-pi1'
    }
    
    Query params (auto-added):
        'team_id': 'team_1'
    
    Response:
    {
        'success': True,
        'item': 'En',
        'click_result': 'success' | 'failed',
        'back_result': 'success' | 'failed',
        'edge_updated': True,
        'has_more_items': True/False,
        'progress': {
            'current_item': 2,
            'total_items': 10
        }
    }
    """
    try:
        data = request.get_json() or {}
        team_id = request.args.get('team_id')
        exploration_id = data.get('exploration_id')
        
        if not team_id:
            return jsonify({'success': False, 'error': 'team_id required'}), 400
        
        if not exploration_id:
            return jsonify({'success': False, 'error': 'exploration_id required'}), 400
        
        if exploration_id not in _exploration_sessions:
            return jsonify({'success': False, 'error': 'Exploration session not found'}), 404
        
        session = _exploration_sessions[exploration_id]
        
        if session['status'] not in ['awaiting_validation', 'validating']:
            return jsonify({
                'success': False,
                'error': f"Cannot validate: status is {session['status']}, expected 'awaiting_validation'"
            }), 400
        
        # Get current item to validate
        current_index = session.get('current_validation_index', 0)
        items_to_validate = session.get('items_to_validate', [])
        
        if current_index >= len(items_to_validate):
            # All items validated
            session['status'] = 'validation_complete'
            return jsonify({
                'success': True,
                'message': 'All items validated',
                'has_more_items': False
            })
        
        current_item = items_to_validate[current_index]
        
        # Get node name from mapping (current_item is the original target text)
        target_to_node_map = session.get('target_to_node_map', {})
        node_name = target_to_node_map.get(current_item)
        
        if not node_name:
            # Fallback: try to generate node name
            from backend_host.src.services.ai_exploration.node_generator import NodeGenerator
            node_gen = NodeGenerator(tree_id, team_id)
            node_name_clean = node_gen.target_to_node_name(current_item)
            node_name = f"{node_name_clean}_temp"
        
        # Skip 'home' if it appears
        if 'home' in node_name.lower() and node_name != 'home_temp':
            session['current_validation_index'] = current_index + 1
            return validate_next_item()  # Recursive call for next item
        
        print(f"[@route:ai_generation:validate_next_item] Validating item {current_index + 1}/{len(items_to_validate)}")
        print(f"  Target text: {current_item}")
        print(f"  Destination node: {node_name}")
        
        session['status'] = 'validating'
        session['current_step'] = f"Validating {current_index + 1}/{len(items_to_validate)}: {current_item}"
        
        # Get controller from engine
        engine = session.get('engine')
        if not engine:
            return jsonify({'success': False, 'error': 'Engine not found'}), 500
        
        controller = engine.controller
        tree_id = session['tree_id']
        
        # Perform validation: click → back → verify
        import time
        click_result = 'failed'
        back_result = 'failed'
        
        # Get first item from exploration plan as home indicator
        all_items = session.get('exploration_plan', {}).get('items', [])
        home_indicator = all_items[0] if all_items else 'home'
        
        # 1. Click element (navigation target)
        try:
            result = controller.click_element(text=current_item)
            click_success = result if isinstance(result, bool) else result.get('success', False)
            click_result = 'success' if click_success else 'failed'
            print(f"    {'✅' if click_success else '❌'} Click {click_result}")
            time.sleep(2)
        except Exception as e:
            print(f"    ❌ Click failed: {e}")
            click_result = 'failed'
        
        # 2. Press BACK
        if click_result == 'success':
            try:
                controller.press_key('BACK')
                time.sleep(2)
                
                # 3. Verify we're back on HOME (not by finding current_item, but by finding home indicator)
                print(f"    🔍 Verifying return to home by checking: {home_indicator}")
                is_back = controller.wait_for_element_by_text(
                    text=home_indicator,
                    timeout=5
                )
                back_success = is_back if isinstance(is_back, bool) else is_back.get('success', False)
                back_result = 'success' if back_success else 'failed'
                print(f"    {'✅' if back_success else '❌'} Back {back_result}")
            except Exception as e:
                print(f"    ⚠️ Back failed: {e}")
                back_result = 'failed'
        
        # 4. Update edge with validated actions
        from shared.src.lib.database.navigation_trees_db import get_edge_by_id, update_edge
        
        # Build correct edge_id using the actual node name
        edge_id = f"edge_home_temp_to_{node_name}_temp"
        edge_result = get_edge_by_id(tree_id, edge_id, team_id)
        
        if edge_result['success']:
            edge = edge_result['edge']
            action_sets = edge.get('action_sets', [])
            
            # Update forward action_set
            if len(action_sets) >= 1 and click_result == 'success':
                action_sets[0]['actions'] = [
                    {'command': 'click_element', 'params': {'text': current_item}, 'delay': 2000}
                ]
            
            # Update reverse action_set
            if len(action_sets) >= 2 and back_result == 'success':
                action_sets[1]['actions'] = [
                    {'command': 'press_key', 'params': {'key': 'BACK'}, 'delay': 2000}
                ]
            
            # Save updated edge
            edge['action_sets'] = action_sets
            update_result = update_edge(tree_id, edge_id, edge, team_id)
            edge_updated = update_result.get('success', False)
        else:
            edge_updated = False
        
        # Move to next item
        session['current_validation_index'] = current_index + 1
        has_more = session['current_validation_index'] < len(items_to_validate)
        
        if not has_more:
            session['status'] = 'validation_complete'
        else:
            session['status'] = 'awaiting_validation'
        
        return jsonify({
            'success': True,
            'item': current_item,
            'click_result': click_result,
            'back_result': back_result,
            'edge_updated': edge_updated,
            'has_more_items': has_more,
            'progress': {
                'current_item': session['current_validation_index'],
                'total_items': len(items_to_validate)
            }
        })
        
    except Exception as e:
        print(f"[@route:ai_generation:validate_next_item] Error: {e}")
        import traceback
        traceback.print_exc()
        
        if exploration_id in _exploration_sessions:
            _exploration_sessions[exploration_id]['status'] = 'awaiting_validation'
        
        return jsonify({'success': False, 'error': str(e)}), 500
        if exploration_id in _exploration_sessions:
            _exploration_sessions[exploration_id]['status'] = 'awaiting_item_approval'
        
        return jsonify({'success': False, 'error': str(e)}), 500


@ai_generation_bp.route('/continue-exploration-legacy', methods=['POST'])
def continue_exploration_legacy():
    """
    Continue to Phase 2: Execute the approved exploration plan
    
    Body:
    {
        'exploration_id': 'abc123'
    }
    
    Query params (auto-added):
        'team_id': 'team_1'
    
    Response:
    {
        'success': True,
        'message': 'Phase 2 started'
    }
    """
    try:
        data = request.get_json() or {}
        team_id = request.args.get('team_id')
        exploration_id = data.get('exploration_id')
        
        if not team_id:
            return jsonify({'success': False, 'error': 'team_id required'}), 400
        
        if not exploration_id:
            return jsonify({'success': False, 'error': 'exploration_id required'}), 400
        
        if exploration_id not in _exploration_sessions:
            return jsonify({'success': False, 'error': 'Exploration session not found'}), 404
        
        session = _exploration_sessions[exploration_id]
        
        if session['status'] != 'awaiting_approval':
            return jsonify({
                'success': False,
                'error': f"Cannot continue: status is {session['status']}, expected 'awaiting_approval'"
            }), 400
        
        print(f"[@route:ai_generation:continue_exploration] Starting Phase 2 for {exploration_id}")
        
        # Get engine from session
        engine = session.get('engine')
        if not engine:
            return jsonify({
                'success': False,
                'error': 'Exploration engine not found in session'
            }), 500
        
        # Capture Flask app context
        app = current_app._get_current_object()
        
        # Start Phase 2 in background thread
        def run_phase2():
            with app.app_context():
                try:
                    _exploration_sessions[exploration_id]['status'] = 'exploring'
                    _exploration_sessions[exploration_id]['phase'] = 'exploration'
                    _exploration_sessions[exploration_id]['current_step'] = 'Starting Phase 2: Exploring navigation tree...'
                    
                    # Run Phase 2: actual exploration with the plan
                    result = engine.execute_exploration()
                    
                    # Update state with results
                    if result['success']:
                        _exploration_sessions[exploration_id]['status'] = 'completed'
                        _exploration_sessions[exploration_id]['current_step'] = f"Exploration completed. Found {result['nodes_created']} nodes."
                        _exploration_sessions[exploration_id]['progress'] = {
                            'total_screens_found': result['nodes_created'],
                            'screens_analyzed': result['nodes_created'],
                            'nodes_proposed': result['nodes_created'],
                            'edges_proposed': result['edges_created']
                        }
                        _exploration_sessions[exploration_id]['created_nodes'] = result['created_node_ids']
                        _exploration_sessions[exploration_id]['created_edges'] = result['created_edge_ids']
                        _exploration_sessions[exploration_id]['created_subtrees'] = result['created_subtree_ids']
                        
                        # Build proposed nodes/edges for frontend
                        from shared.src.lib.database.navigation_trees_db import get_node_by_id, get_edge_by_id
                        
                        proposed_nodes = []
                        for node_id in result['created_node_ids']:
                            node_result = get_node_by_id(session['tree_id'], node_id, team_id)
                            if node_result['success']:
                                node = node_result['node']
                                proposed_nodes.append({
                                    'id': node_id,
                                    'name': node.get('label', node_id),
                                    'screen_type': node.get('data', {}).get('screen_type', 'screen'),
                                    'reasoning': node.get('data', {}).get('reasoning', '')
                                })
                        
                        proposed_edges = []
                        for edge_id in result['created_edge_ids']:
                            edge_result = get_edge_by_id(session['tree_id'], edge_id, team_id)
                            if edge_result['success']:
                                edge = edge_result['edge']
                                proposed_edges.append({
                                    'id': edge_id,
                                    'source': edge.get('source_node_id', ''),
                                    'target': edge.get('target_node_id', ''),
                                    'reasoning': f"Navigation from {edge.get('source_node_id', '')} to {edge.get('target_node_id', '')}"
                                })
                        
                        _exploration_sessions[exploration_id]['proposed_nodes'] = proposed_nodes
                        _exploration_sessions[exploration_id]['proposed_edges'] = proposed_edges
                    else:
                        _exploration_sessions[exploration_id]['status'] = 'failed'
                        _exploration_sessions[exploration_id]['error'] = result.get('error', 'Unknown error')
                        _exploration_sessions[exploration_id]['current_step'] = f"Exploration failed: {result.get('error')}"
                    
                except Exception as e:
                    print(f"[@route:ai_generation:run_phase2] Error: {e}")
                    import traceback
                    traceback.print_exc()
                    _exploration_sessions[exploration_id]['status'] = 'failed'
                    _exploration_sessions[exploration_id]['error'] = str(e)
                    _exploration_sessions[exploration_id]['current_step'] = f"Error: {str(e)}"
        
        # Start thread
        thread = threading.Thread(target=run_phase2, daemon=True)
        thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Phase 2 exploration started'
        })
        
    except Exception as e:
        print(f"[@route:ai_generation:continue_exploration] Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_generation_bp.route('/approve-generation', methods=['POST'])
def approve_generation():
    """
    Approve generation - rename all _temp nodes/edges
    
    Request body:
    {
        'exploration_id': 'uuid',
        'tree_id': 'uuid',
        'approved_nodes': ['home_temp', 'settings_temp'],
        'approved_edges': ['edge_home_to_settings_temp']
    }
    Query params (auto-added by buildServerUrl):
        'team_id': 'team_1'
    
    Response:
    {
        'success': True,
        'nodes_created': 2,
        'edges_created': 1
    }
    """
    try:
        data = request.get_json() or {}
        team_id = request.args.get('team_id')  # Auto-added by buildServerUrl
        
        exploration_id = data.get('exploration_id')
        tree_id = data.get('tree_id')
        approved_nodes = data.get('approved_nodes', [])
        approved_edges = data.get('approved_edges', [])
        
        if not team_id:
            return jsonify({'success': False, 'error': 'team_id required in query parameters'}), 400
        
        if exploration_id not in _exploration_sessions:
            return jsonify({
                'success': False,
                'error': 'Exploration session not found'
            }), 404
        
        print(f"[@route:ai_generation:approve_generation] Approving {len(approved_nodes)} nodes, {len(approved_edges)} edges")
        
        from services.ai_exploration.node_generator import NodeGenerator
        node_generator = NodeGenerator(tree_id, team_id)
        
        nodes_created = 0
        edges_created = 0
        
        # Rename approved nodes (remove _temp)
        for node_id in approved_nodes:
            node_result = get_node_by_id(tree_id, node_id, team_id)
            if node_result['success']:
                node_data = node_result['node']
                renamed_data = node_generator.rename_node(node_data)
                
                # Delete old node
                delete_node(tree_id, node_id, team_id)
                
                # Save renamed node
                save_result = save_node(tree_id, renamed_data, team_id)
                if save_result['success']:
                    nodes_created += 1
                    print(f"  ✅ Renamed: {node_id} → {renamed_data['node_id']}")
        
        # Rename approved edges (remove _temp)
        for edge_id in approved_edges:
            edge_result = get_edge_by_id(tree_id, edge_id, team_id)
            if edge_result['success']:
                edge_data = edge_result['edge']
                renamed_data = node_generator.rename_edge(edge_data)
                
                # Delete old edge (will be handled by save_edge upsert)
                # save_edge handles update if exists
                save_result = save_edge(tree_id, renamed_data, team_id)
                if save_result['success']:
                    edges_created += 1
                    print(f"  ✅ Renamed: {edge_id} → {renamed_data['edge_id']}")
        
        # Clean up session
        del _exploration_sessions[exploration_id]
        
        print(f"[@route:ai_generation:approve_generation] ✅ Complete: {nodes_created} nodes, {edges_created} edges")
        
        return jsonify({
            'success': True,
            'nodes_created': nodes_created,
            'edges_created': edges_created,
            'message': f'Successfully created {nodes_created} nodes and {edges_created} edges'
        })
        
    except Exception as e:
        print(f"[@route:ai_generation:approve_generation] Error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_generation_bp.route('/cancel-exploration', methods=['POST'])
def cancel_exploration():
    """
    Cancel exploration - delete all _temp nodes/edges
    
    Request body:
    {
        'exploration_id': 'uuid'
    }
    Query params (auto-added by buildServerUrl):
        'team_id': 'team_1'
    
    Response:
    {
        'success': True,
        'message': 'Exploration cancelled'
    }
    """
    try:
        data = request.get_json() or {}
        team_id = request.args.get('team_id')  # Auto-added by buildServerUrl
        
        exploration_id = data.get('exploration_id')
        
        if not team_id:
            return jsonify({'success': False, 'error': 'team_id required in query parameters'}), 400
        
        if exploration_id not in _exploration_sessions:
            return jsonify({
                'success': False,
                'error': 'Exploration session not found'
            }), 404
        
        session = _exploration_sessions[exploration_id]
        tree_id = session['tree_id']
        
        print(f"[@route:ai_generation:cancel_exploration] Cancelling exploration {exploration_id}")
        
        # Delete all created _temp nodes (cascade will delete edges)
        for node_id in session['created_nodes']:
            delete_node(tree_id, node_id, team_id)
            print(f"  🗑️  Deleted node: {node_id}")
        
        # Delete any created _temp subtrees
        for subtree_id in session['created_subtrees']:
            delete_tree_cascade(subtree_id, team_id)
            print(f"  🗑️  Deleted subtree: {subtree_id}")
        
        # Clean up session
        del _exploration_sessions[exploration_id]
        
        print(f"[@route:ai_generation:cancel_exploration] ✅ Exploration cancelled")
        
        return jsonify({
            'success': True,
            'message': 'Exploration cancelled, temporary nodes deleted'
        })
        
    except Exception as e:
        print(f"[@route:ai_generation:cancel_exploration] Error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

