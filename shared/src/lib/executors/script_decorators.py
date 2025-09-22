"""
Declarative Script Framework
Ultra-simple decorator-based script execution
"""

import functools
from typing import Callable, Any
from .script_executor import ScriptExecutor, handle_keyboard_interrupt, handle_unexpected_error

# Global context for current script execution
_current_context = None
_current_executor = None

def script(name: str, description: str):
    """
    Decorator that handles all script infrastructure automatically
    
    @script("goto_live", "Navigate to live node")
    def main():
        navigate_to("live")
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper():
            global _current_context, _current_executor
            
            # Setup everything automatically
            executor = ScriptExecutor(name, description)
            parser = executor.create_argument_parser()
            
            # Add custom arguments based on script name
            if name == "goto":
                parser.add_argument('--node', type=str, default='home', 
                                   help='Target node to navigate to (default: home)')
            elif name in ["validation", "fullzap"]:
                parser.add_argument('--max_iteration', type=int, default=10 if name == "validation" else 50,
                                   help='Maximum iterations')
            
            args = parser.parse_args()
            context = executor.setup_execution_context(args, enable_db_tracking=True)
            
            if context.error_message:
                executor.cleanup_and_exit(context, args.userinterface_name)
                return
            
            # Set global context for helper functions
            _current_context = context
            _current_executor = executor
            
            # Store args in context for access
            context.args = args
            
            try:
                # Execute user's business logic
                result = func()
                
                # Auto-determine success
                if result is None or result is True:
                    executor.test_success(context)
                else:
                    executor.test_fail(context)
                    
            except KeyboardInterrupt:
                handle_keyboard_interrupt(name)
            except Exception as e:
                handle_unexpected_error(name, e)
            finally:
                executor.cleanup_and_exit(context, args.userinterface_name)
                _current_context = None
                _current_executor = None
        
        return wrapper
    return decorator

# Helper functions that use global context
def get_device():
    """Get current device"""
    return _current_context.selected_device

def is_mobile_device() -> bool:
    """Check if current device is mobile"""
    return "mobile" in get_device().device_model.lower()

def navigate_to(target_node: str) -> bool:
    """Navigate to target node"""
    return _current_executor.navigate_to(
        _current_context, 
        target_node, 
        _current_context.args.userinterface_name
    )

def get_args():
    """Get parsed command line arguments"""
    return _current_context.args

def get_context():
    """Get current execution context"""
    return _current_context

def get_executor():
    """Get current script executor"""
    return _current_executor

def validate(max_iterations: int = None) -> bool:
    """Execute validation with recovery - complex validation logic"""
    from backend_host.src.services.navigation.navigation_pathfinding import find_optimal_edge_validation_sequence
    from backend_host.src.lib.utils.navigation_cache import get_cached_unified_graph
    from backend_host.src.lib.utils.navigation_graph import get_entry_points
    import time
    from datetime import datetime
    
    context = _current_context
    
    # Initialize current position to entry point for pathfinding
    unified_graph = get_cached_unified_graph(context.tree_id, context.team_id)
    if unified_graph:
        entry_points = get_entry_points(unified_graph)
        if entry_points:
            context.current_node_id = entry_points[0]
            print(f"📍 [validation] Starting validation from entry point: {context.current_node_id}")
    
    # Get validation sequence
    print("📋 [validation] Getting validation sequence...")
    validation_sequence = find_optimal_edge_validation_sequence(context.tree_id, context.team_id)
    
    if not validation_sequence:
        context.error_message = "No validation sequence found"
        print(f"❌ [validation] {context.error_message}")
        return False
    
    print(f"✅ [validation] Found {len(validation_sequence)} validation steps")
    
    # Execute validation sequence (using existing complex logic)
    from test_scripts.validation import execute_validation_sequence_with_force_recovery, custom_validation_step_handler
    success = execute_validation_sequence_with_force_recovery(
        _current_executor, context, validation_sequence, custom_validation_step_handler, max_iterations
    )
    
    # Calculate validation success based on executed step results only
    successful_steps = sum(1 for step in context.step_results if step.get('success', False))
    executed_steps = len(context.step_results)
    
    # Validation is successful if ALL EXECUTED steps pass
    context.overall_success = successful_steps == executed_steps and executed_steps > 0
    
    if context.overall_success:
        print(f"🎉 [validation] All {successful_steps}/{executed_steps} executed validation steps passed successfully!")
    else:
        print(f"❌ [validation] Validation failed: {successful_steps}/{executed_steps} executed steps passed")
    
    return context.overall_success

def execute_zaps(max_iterations: int, action: str = 'live_chup', goto_live: bool = True, audio_analysis: bool = False) -> bool:
    """Execute zap iterations with analysis - complex zap logic"""
    from backend_host.src.lib.utils.zap_controller import ZapController
    from shared.lib.utils.navigation_utils import goto_node, find_edge_by_target_label, find_node_by_label
    from backend_host.src.lib.utils.audio_menu_analyzer import analyze_audio_menu
    from datetime import datetime
    
    context = _current_context
    
    # Create ZapController
    zap_controller = ZapController()
    
    # Determine target node based on device model - same logic as goto_live.py
    if "mobile" in context.selected_device.device_model.lower():
        target_node = "live_fullscreen"
        print(f"📱 [fullzap] Mobile device detected - using live_fullscreen as base node")
    else:
        target_node = "live"
    
    # Map action command to be node-specific
    if target_node == "live_fullscreen" and action == "live_chup":
        mapped_action = "live_fullscreen_chup"
        print(f"🔄 [fullzap] Mapped action '{action}' to '{mapped_action}' for {target_node} node")
    elif target_node == "live_fullscreen" and action == "live_chdown":
        mapped_action = "live_fullscreen_chdown"
        print(f"🔄 [fullzap] Mapped action '{action}' to '{mapped_action}' for {target_node} node")
    else:
        mapped_action = action
    
    # Conditionally navigate to target node
    if goto_live:
        print(f"🗺️ [fullzap] Navigating to {target_node} node...")
        live_result = goto_node(context.host, context.selected_device, target_node, context.tree_id, context.team_id, context)
        
        if not live_result.get('success'):
            context.error_message = f"Failed to navigate to {target_node}: {live_result.get('error', 'Unknown error')}"
            print(f"❌ [fullzap] {context.error_message}")
            return False
        
        print(f"🎉 [fullzap] Successfully navigated to {target_node}!")
    else:
        print(f"⏭️ [fullzap] Skipping navigation to {target_node} node")
        # Set current node manually
        target_node_obj = find_node_by_label(context.nodes, target_node)
        if target_node_obj:
            context.current_node_id = target_node_obj.get('node_id')
            print(f"🎯 [fullzap] Manually set current position to {target_node} node")
    
    # Store mapped action in context
    context.custom_data['action_command'] = mapped_action
    
    # Set audio menu node for mobile devices
    if "mobile" in context.selected_device.device_model.lower():
        context.audio_menu_node = "live_fullscreen_audiomenu"
    else:
        context.audio_menu_node = "live_audiomenu"
    
    # Find the action edge
    action_edge = find_edge_by_target_label(
        context.current_node_id, 
        context.edges, 
        context.all_nodes, 
        mapped_action
    )
    
    if not action_edge:
        context.error_message = f"No edge found from current node to '{mapped_action}'"
        print(f"❌ [fullzap] {context.error_message}")
        return False
    
    print(f"✅ [fullzap] Found edge for action '{mapped_action}'")
    
    # Execute zap actions using existing complex logic
    from test_scripts.fullzap import execute_zap_actions
    try:
        zap_success = execute_zap_actions(context, action_edge, mapped_action, max_iterations, zap_controller, goto_live)
    except Exception as e:
        print(f"⚠️ [fullzap] ZapController error: {e}")
        zap_success = False
    
    # Handle audio analysis if requested
    if zap_success and audio_analysis:
        device_model = context.selected_device.device_model if context.selected_device else 'unknown'
        if device_model == 'host_vnc':
            print("⏭️ [fullzap] Skipping audio menu analysis for VNC device")
        else:
            print("🎧 [fullzap] Performing audio menu analysis...")
            audio_result = analyze_audio_menu(context)
            context.custom_data['audio_menu_analysis'] = audio_result
    
    return zap_success

def capture_validation_summary(userinterface_name: str, max_iteration: int = None) -> str:
    """Capture validation summary for reports"""
    from test_scripts.validation import capture_validation_summary as _capture_validation_summary
    return _capture_validation_summary(_current_context, userinterface_name, max_iteration)

def capture_fullzap_summary(userinterface_name: str) -> str:
    """Capture fullzap summary for reports"""
    from test_scripts.fullzap import capture_fullzap_summary as _capture_fullzap_summary
    return _capture_fullzap_summary(_current_context, userinterface_name)
