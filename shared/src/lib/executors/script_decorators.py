"""
Declarative Script Framework
Ultra-simple decorator-based script execution
"""

import functools
import argparse
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
            # Check both the original function and the wrapper (since _script_args is set after decoration)
            script_args = None
            if hasattr(func, '_script_args'):
                script_args = func._script_args
            elif hasattr(wrapper, '_script_args'):
                script_args = wrapper._script_args
            
            if script_args:
                def str_to_bool(v):
                    if isinstance(v, bool):
                        return v
                    if v.lower() in ('yes', 'true', 't', 'y', '1'):
                        return True
                    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
                        return False
                    else:
                        raise argparse.ArgumentTypeError('Boolean value expected.')
                
                for arg_spec in script_args:
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
            context.args = args
            
            try:
                result = func()
            
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

def get_device():
    """Get current device"""
    return _current_context.selected_device

def get_context():
    """Get current execution context"""
    return _current_context

def get_args():
    """Get parsed command line arguments"""
    return _current_context.args
