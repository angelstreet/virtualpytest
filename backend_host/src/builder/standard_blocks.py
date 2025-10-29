"""
Standard Blocks

Builder-specific blocks for test case construction.
These functions are called during test case execution.

Functions:
- getMenuInfo: Extract menu information using OCR
- set_variable: Set variable in execution context
- set_metadata: Push variables to metadata for DB storage
"""

import os
import io
import sys
from typing import Dict, Any, Optional, List


def get_available_standard_blocks() -> List[Dict[str, Any]]:
    """
    Get available standard blocks with typed parameters.
    This is called by the toolbox builder to populate the standard blocks section.
    """
    from shared.src.lib.schemas.param_types import create_param, ParamType
    
    return [
        {
            'command': 'set_variable',
            'params': {
                'variable_name': create_param(
                    ParamType.STRING,
                    required=True,
                    default='',
                    description="Variable name to set",
                    placeholder="Enter variable name"
                ),
                'variable_value': create_param(
                    ParamType.STRING,
                    required=True,
                    default='',
                    description="Value to store in the variable",
                    placeholder="Enter value"
                )
            },
            'block_type': 'standard',
            'description': 'Set a variable value'
        },
        {
            'command': 'set_metadata',
            'params': {
                'source_variable': create_param(
                    ParamType.STRING,
                    required=False,
                    default=None,
                    description="Variable to push (leave empty for all)",
                    placeholder="Enter variable name or leave empty"
                ),
                'mode': create_param(
                    ParamType.SELECT,
                    required=False,
                    default='append',
                    description="How to update metadata",
                    options=[
                        {'label': 'Append (merge)', 'value': 'append'},
                        {'label': 'Set (replace)', 'value': 'set'}
                    ]
                )
            },
            'block_type': 'standard',
            'description': 'Push variables to metadata for DB storage'
        }
    ]


def _capture_logs(func):
    """Decorator to capture logs from standard block execution"""
    def wrapper(*args, **kwargs):
        # Start capturing logs
        log_buffer = io.StringIO()
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        
        try:
            # Redirect stdout/stderr to buffer
            sys.stdout = log_buffer
            sys.stderr = log_buffer
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Add captured logs to result
            if isinstance(result, dict):
                result['logs'] = log_buffer.getvalue()
            
            return result
        finally:
            # Always restore stdout/stderr
            sys.stdout = old_stdout
            sys.stderr = old_stderr
    
    return wrapper


@_capture_logs
def getMenuInfo(area: Optional[Dict[str, Any]] = None, context=None, **kwargs) -> Dict[str, Any]:
    """
    Extract menu information from screen using OCR, parse key-value pairs, and auto-store to metadata.
    
    This replicates the get_info.py script behavior:
    1. Takes screenshot
    2. Extracts text using OCR
    3. Parses key-value pairs (format: "Key: Value" or "Key = Value")
    4. Auto-stores to context.metadata for DB persistence
    
    Args:
        area: Optional area to extract from {'x': int, 'y': int, 'width': int, 'height': int}
        context: Execution context (contains device, host, etc.)
        **kwargs: Additional parameters
        
    Returns:
        Dict with:
            - success: bool
            - output_data: dict with parsed data and OCR text
            - message: str
            
    Example output stored in context.metadata (FLAT JSON):
        {
            "serial_number": "ABC123",
            "mac_address": "00:11:22:33:44:55",
            "firmware_version": "1.2.3",
            "extraction_timestamp": "2025-10-28T10:30:00",
            "ocr_text": "Serial Number: ABC123\nMAC: 00:11:22:33:44:55",
            "device_name": "device1",
            "ocr_area": "{'x': 0, 'y': 0, 'width': 1920, 'height': 1080}"
        }
    """
    print(f"[@builder:getMenuInfo] Extracting menu info from screen (with auto-parsing)")
    
    try:
        # Validate context
        if not context:
            return {
                'success': False,
                'output_data': {},
                'message': 'No execution context provided'
            }
        
        # Get device from context
        device = getattr(context, 'selected_device', None)
        if not device:
            return {
                'success': False,
                'output_data': {},
                'message': 'No device available in context'
            }
        
        # Get text controller from device
        text_controller = device._get_controller('text')
        if not text_controller:
            return {
                'success': False,
                'output_data': {},
                'message': 'Text verification controller not available'
            }
        
        # Take screenshot (source image for OCR)
        av_controller = device._get_controller('av')
        if not av_controller:
            return {
                'success': False,
                'output_data': {},
                'message': 'AV controller not available for screenshot'
            }
        
        screenshot_path = av_controller.take_screenshot()
        if not screenshot_path or not os.path.exists(screenshot_path):
            return {
                'success': False,
                'output_data': {},
                'message': 'Failed to capture screenshot'
            }
        
        print(f"[@builder:getMenuInfo] Screenshot captured: {screenshot_path}")
        
        # Extract text using text controller's helper
        helpers = text_controller.helpers
        result = helpers.detect_text_in_area(screenshot_path, area)
        
        extracted_text = result.get('extracted_text', '')
        
        if not extracted_text:
            print(f"[@builder:getMenuInfo] No text extracted from area")
            return {
                'success': False,
                'output_data': {'ocr_text': ''},
                'message': 'No text detected in specified area'
            }
        
        print(f"[@builder:getMenuInfo] Extracted text ({len(extracted_text)} chars):")
        print(f"--- OCR TEXT START ---")
        print(extracted_text)
        print(f"--- OCR TEXT END ---")
        
        # Parse key-value pairs (horizontal format: "Key: Value" or "Key = Value")
        parsed_data = {}
        lines = extracted_text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Try to split by common delimiters: colon, equals, dash
            for delimiter in [':', '=', '-']:
                if delimiter in line:
                    parts = line.split(delimiter, 1)  # Split only on first occurrence
                    if len(parts) == 2:
                        key = parts[0].strip().lower().replace(' ', '_')
                        value = parts[1].strip()
                        if key and value:
                            parsed_data[key] = value
                            print(f"[@builder:getMenuInfo] Parsed: {key} = {value}")
                    break
        
        print(f"[@builder:getMenuInfo] Parsed {len(parsed_data)} key-value pairs")
        
        if not parsed_data:
            print(f"[@builder:getMenuInfo] WARNING: No key-value pairs found in OCR text")
            # Don't fail - still return OCR text for debugging
        
        # Auto-store to context.metadata (like get_info.py script)
        # FLAT JSON: Each key-value pair is added directly to metadata (not nested)
        from datetime import datetime
        
        # Initialize metadata if not exists
        if not hasattr(context, 'metadata'):
            context.metadata = {}
        
        # Append parsed data directly to metadata (flat structure)
        for key, value in parsed_data.items():
            context.metadata[key] = value
        
        # Add extraction metadata
        context.metadata['extraction_timestamp'] = datetime.now().isoformat()
        context.metadata['ocr_text'] = extracted_text
        
        if hasattr(device, 'device_name'):
            context.metadata['device_name'] = device.device_name
        
        if area:
            context.metadata['ocr_area'] = str(area)  # Store as string for JSON compatibility
        
        print(f"[@builder:getMenuInfo] ✅ AUTO-APPENDED to context.metadata (FLAT)")
        print(f"[@builder:getMenuInfo] Metadata keys: {list(context.metadata.keys())}")
        print(f"[@builder:getMenuInfo] New fields added: {list(parsed_data.keys())}")
        
        # Also store in variables for potential linking to other blocks
        if not hasattr(context, 'variables'):
            context.variables = {}
        
        context.variables['menu_info'] = {
            'parsed_data': parsed_data,
            'ocr_text': extracted_text
        }
        
        output_data = {
            'parsed_data': parsed_data,
            'ocr_text': extracted_text,
            'character_count': result.get('character_count', 0),
            'word_count': result.get('word_count', 0),
            'language': result.get('language', 'en'),
            'area': area,
            'source_image': screenshot_path,
            'processed_image': result.get('image_textdetected_path', '')
        }
        
        return {
            'success': True,
            'output_data': output_data,
            'message': f'Parsed {len(parsed_data)} fields and auto-stored to metadata'
        }
        
    except Exception as e:
        error_msg = f"Error extracting menu info: {str(e)}"
        print(f"[@builder:getMenuInfo] ERROR: {error_msg}")
        import traceback
        traceback.print_exc()
        
        return {
            'success': False,
            'output_data': {},
            'message': error_msg
        }


@_capture_logs
def set_variable(variable_name: str, variable_value: Any, context=None, **kwargs) -> Dict[str, Any]:
    """
    Set a variable in execution context.
    
    Phase 3: Simple key-value storage (no type conversion yet).
    
    Args:
        variable_name: Name of the variable to set
        variable_value: Value to store (any type)
        context: Execution context
        **kwargs: Additional parameters
        
    Returns:
        Dict with success status
    """
    print(f"[@builder:set_variable] Setting variable: {variable_name} = {variable_value}")
    
    try:
        if not context:
            return {
                'success': False,
                'message': 'No execution context provided'
            }
        
        # Initialize variables dict if not exists
        if not hasattr(context, 'variables'):
            context.variables = {}
        
        # Store variable
        context.variables[variable_name] = variable_value
        
        print(f"[@builder:set_variable] SUCCESS - Stored in context.variables['{variable_name}']")
        
        return {
            'success': True,
            'message': f'Variable "{variable_name}" set successfully'
        }
        
    except Exception as e:
        error_msg = f"Error setting variable: {str(e)}"
        print(f"[@builder:set_variable] ERROR: {error_msg}")
        
        return {
            'success': False,
            'message': error_msg
        }


@_capture_logs
def set_metadata(source_variable: Optional[str] = None, mode: str = 'set', context=None, **kwargs) -> Dict[str, Any]:
    """
    Push variables to metadata for DB storage.
    
    Phase 4: Copy variables to context.metadata (saved to script_results.metadata).
    
    Args:
        source_variable: Variable name to push (None = push all variables)
        mode: 'set' (replace) or 'append' (merge) - default 'set'
        context: Execution context
        **kwargs: Additional parameters
        
    Returns:
        Dict with success status
    """
    print(f"[@builder:set_metadata] Pushing to metadata - mode: {mode}, source: {source_variable or 'ALL'}")
    
    try:
        if not context:
            return {
                'success': False,
                'message': 'No execution context provided'
            }
        
        # Initialize variables and metadata if not exists
        if not hasattr(context, 'variables'):
            context.variables = {}
        if not hasattr(context, 'metadata'):
            context.metadata = {}
        
        # Determine what to push
        if source_variable:
            # Push specific variable
            if source_variable not in context.variables:
                return {
                    'success': False,
                    'message': f'Variable "{source_variable}" not found in context'
                }
            
            data_to_push = {source_variable: context.variables[source_variable]}
        else:
            # Push all variables
            data_to_push = context.variables.copy()
        
        # Apply based on mode
        if mode == 'set':
            # Replace entire metadata
            context.metadata = data_to_push
            print(f"[@builder:set_metadata] Replaced metadata with {len(data_to_push)} variables")
        elif mode == 'append':
            # Merge into existing metadata
            context.metadata.update(data_to_push)
            print(f"[@builder:set_metadata] Merged {len(data_to_push)} variables into metadata")
        else:
            return {
                'success': False,
                'message': f'Invalid mode: {mode}. Use "set" or "append"'
            }
        
        print(f"[@builder:set_metadata] SUCCESS - Metadata now contains {len(context.metadata)} keys")
        
        return {
            'success': True,
            'message': f'Metadata updated successfully ({mode} mode)'
        }
        
    except Exception as e:
        error_msg = f"Error setting metadata: {str(e)}"
        print(f"[@builder:set_metadata] ERROR: {error_msg}")
        
        return {
            'success': False,
            'message': error_msg
        }

