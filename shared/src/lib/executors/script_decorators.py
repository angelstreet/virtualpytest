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
            
            # Add script-specific arguments from function attribute
            if hasattr(func, '_script_args'):
                def str_to_bool(v):
                    if isinstance(v, bool):
                        return v
                    if v.lower() in ('yes', 'true', 't', 'y', '1'):
                        return True
                    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
                        return False
                    else:
                        raise argparse.ArgumentTypeError('Boolean value expected.')
                
                for arg_spec in func._script_args:
                    # Parse format: '--name:type:default'
                    parts = arg_spec.split(':')
                    if len(parts) != 3:
                        continue
                    
                    arg_name, arg_type, default_value = parts
                    
                    # Convert type string to actual type
                    if arg_type == 'int':
                        parser.add_argument(arg_name, type=int, default=int(default_value),
                                           help=f'{arg_name.replace("--", "").replace("_", " ").title()} (default: {default_value})')
                    elif arg_type == 'str':
                        parser.add_argument(arg_name, type=str, default=default_value,
                                           help=f'{arg_name.replace("--", "").replace("_", " ").title()} (default: {default_value})')
                    elif arg_type == 'bool':
                        default_bool = default_value.lower() in ('true', 't', 'yes', 'y', '1')
                        parser.add_argument(arg_name, type=str_to_bool, default=default_bool,
                                           help=f'{arg_name.replace("--", "").replace("_", " ").title()} (default: {default_value})')
            
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
