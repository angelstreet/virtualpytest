"""
Logging Manager
Handles log capture for all execution types
"""

import io
import sys
import asyncio
import inspect
from typing import Callable, Any, Dict


class Tee:
    """
    Write to multiple streams simultaneously with immediate flushing.
    Ensures logs appear in systemd journal while also being captured for API responses.
    """
    def __init__(self, *streams):
        self.streams = streams
    
    def write(self, data):
        """Write data to all streams and flush immediately"""
        for stream in self.streams:
            try:
                stream.write(data)
                stream.flush()  # Flush each write immediately for systemd
            except (IOError, OSError) as e:
                # Handle broken pipe or closed stream gracefully
                pass
    
    def flush(self):
        """Flush all streams"""
        for stream in self.streams:
            try:
                stream.flush()
            except (IOError, OSError):
                pass


class LoggingManager:
    """Manages log capture for execution operations"""
    
    @staticmethod
    async def execute_with_logging(execution_fn: Callable, *args, **kwargs) -> Dict[str, Any]:
        """
        Execute function and capture all stdout/stderr logs.
        Supports both sync and async callables.
        
        Thread-safe: Works correctly in background threads by redirecting the global
        sys.stdout/sys.stderr, which all threads share.
        
        Args:
            execution_fn: Function to execute (sync or async)
            *args, **kwargs: Arguments to pass to execution_fn
            
        Returns:
            Dict with execution result + 'logs' field
        """
        log_buffer = io.StringIO()
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        
        try:
            # Redirect stdout/stderr to BOTH terminal and buffer
            # This works in threads because sys.stdout/sys.stderr are global
            sys.stdout = Tee(old_stdout, log_buffer)
            sys.stderr = Tee(old_stderr, log_buffer)
            
            # Flush to ensure redirection is active
            sys.stdout.flush()
            sys.stderr.flush()
            
            print(f"[@LoggingManager] Log capture started (thread-safe)", flush=True)
            
            # Execute the function - handle both sync and async
            if inspect.iscoroutinefunction(execution_fn) or asyncio.iscoroutine(execution_fn):
                result = await execution_fn(*args, **kwargs)
            else:
                result = execution_fn(*args, **kwargs)
            
            print(f"[@LoggingManager] Log capture completed", flush=True)
            
            # Ensure result is a dict
            if not isinstance(result, dict):
                result = {'success': False, 'error': 'Invalid result type'}
            
            # Flush before capturing logs
            sys.stdout.flush()
            sys.stderr.flush()
            
            # Add logs to result
            result['logs'] = log_buffer.getvalue()
            
            return result
            
        finally:
            # Always restore stdout/stderr
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            # Final flush
            sys.stdout.flush()
            sys.stderr.flush()

