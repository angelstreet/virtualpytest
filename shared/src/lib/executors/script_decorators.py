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
