"""
Sleep Block

Wait for specified duration (simple delay).
"""

import time
from typing import Dict, Any
from backend_host.src.builder.decorators import capture_logs
from shared.src.lib.schemas.param_types import create_param, ParamType


def get_block_info() -> Dict[str, Any]:
    """Return block metadata for registration"""
    return {
        'command': 'sleep',
        'label': 'Sleep',  # Short name for toolbox
        'description': 'Wait for specified duration',  # Longer description
        'params': {
            'duration': create_param(
                ParamType.NUMBER,
                required=True,
                default=1.0,
                description="Duration to wait (seconds)",
                placeholder="Enter duration in seconds",
                min=0.1,
                max=60.0
            )
        },
        'block_type': 'standard'
    }


@capture_logs
def execute(duration: float = 1.0, context=None, **kwargs) -> Dict[str, Any]:
    """
    Execute sleep block - simple wait/delay.
    
    Args:
        duration: Time to wait in seconds
        context: Execution context (unused for sleep)
        **kwargs: Additional parameters
        
    Returns:
        Dict with success status
    """
    print(f"[@block:sleep] Sleeping for {duration}s")
    
    try:
        time.sleep(duration)
        
        print(f"[@block:sleep] Sleep completed")
        
        return {
            'result_success': 0,  # 0=success, 1=failure, -1=error
            'message': f'Slept for {duration}s'
        }
        
    except Exception as e:
        error_msg = f"Error during sleep: {str(e)}"
        print(f"[@block:sleep] ERROR: {error_msg}")
        
        return {
            'result_success': -1,  # 0=success, 1=failure, -1=error
            'message': error_msg
        }

