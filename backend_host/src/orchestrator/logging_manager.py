"""
Logging Manager
Handles log capture for all execution types
"""

import io
import sys
from typing import Callable, Any, Dict


class Tee:
    """Write to multiple streams simultaneously"""
    def __init__(self, *streams):
        self.streams = streams
    
    def write(self, data):
        for stream in self.streams:
            stream.write(data)
            stream.flush()
    
    def flush(self):
        for stream in self.streams:
            stream.flush()


class LoggingManager:
    """Manages log capture for execution operations"""
    
    @staticmethod
    def execute_with_logging(execution_fn: Callable, *args, **kwargs) -> Dict[str, Any]:
        """
        Execute function and capture all stdout/stderr logs
        
        Args:
            execution_fn: Function to execute
            *args, **kwargs: Arguments to pass to execution_fn
            
        Returns:
            Dict with execution result + 'logs' field
        """
        log_buffer = io.StringIO()
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        
        try:
            # Redirect stdout/stderr to BOTH terminal and buffer
            sys.stdout = Tee(old_stdout, log_buffer)
            sys.stderr = Tee(old_stderr, log_buffer)
            
            # Execute the function
            result = execution_fn(*args, **kwargs)
            
            # Ensure result is a dict
            if not isinstance(result, dict):
                result = {'success': False, 'error': 'Invalid result type'}
            
            # Add logs to result
            result['logs'] = log_buffer.getvalue()
            
            return result
            
        finally:
            # Always restore stdout/stderr
            sys.stdout = old_stdout
            sys.stderr = old_stderr

