"""
Frame Metadata Utilities

Shared utilities for writing action metadata to frame JSON files.
This enables automatic zap measurement by correlating actions with captured frames.
"""

import os
import json
import fcntl
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from shared.src.lib.utils.storage_path_utils import get_metadata_path, get_capture_folder

# Get capture monitor logger for frame JSON operations
logger = logging.getLogger('capture_monitor')


def write_action_to_frame_json(device, action: Dict[str, Any], action_completion_timestamp: float):
    """
    Write action metadata to the frame JSON with timestamp closest to action completion.
    This enables automatic zap measurement by correlating actions with frames.
    
    ✅ NEW: Also stores action in device_state (in-memory) for instant zapping detection.
    Non-blocking - failures are logged but don't affect action success.
    
    Args:
        device: Device instance with get_capture_dir() method
        action: Action dictionary with 'command' and 'params' keys
        action_completion_timestamp: Unix timestamp when action completed
    """
    try:
        # Get capture_folder from device
        # Device has capture_dir attribute like '/var/www/html/stream/capture1'
        capture_dir = device.get_capture_dir('captures')
        if not capture_dir:
            return  # No capture directory configured
        
        # Extract capture_folder name (e.g., 'capture1')
        capture_folder = get_capture_folder(capture_dir)
        
        # ✅ STORE ACTION IN DEVICE STATE (in-memory for fast zapping detection)
        # Get device_id from capture_folder
        from shared.src.lib.utils.storage_path_utils import get_device_info_from_capture_folder
        device_info = get_device_info_from_capture_folder(capture_folder)
        device_id = device_info.get('device_id', capture_folder)
        
        # Store in global device state (same instance used by capture_monitor)
        from backend_host.scripts.incident_manager import get_global_incident_manager
        # Use the SAME incident_manager instance as capture_monitor (singleton)
        incident_manager = get_global_incident_manager()
        device_state = incident_manager.get_device_state(device_id)
        
        # Store last action with timestamp
        device_state['last_action'] = {
            'command': action.get('command'),
            'timestamp': action_completion_timestamp,
            'params': action.get('params', {})
        }
        
        logger.info(f"[@frame_metadata_utils] ✅ Stored action in device_state[{device_id}]: {action.get('command')} @ {action_completion_timestamp}")
        
        metadata_path = get_metadata_path(capture_folder)
        
        if not os.path.exists(metadata_path):
            print(f"[@frame_metadata_utils:write_action_to_frame_json] ❌ Metadata path does not exist: {metadata_path}")
            return  # No metadata directory yet
        
        # Get last 5 JSON files by mtime (fastest approach - uses cached stat)
        json_files = []
        with os.scandir(metadata_path) as entries:
            for entry in entries:
                if entry.name.startswith('capture_') and entry.name.endswith('.json'):
                    json_files.append((entry.path, entry.stat().st_mtime))
        
        if not json_files:
            print(f"[@frame_metadata_utils:write_action_to_frame_json] ❌ No JSON files found in {metadata_path}")
            return  # No JSON files yet
        
        # Sort by mtime (newest first) and take top 5
        json_files.sort(key=lambda x: x[1], reverse=True)
        last_5_files = [path for path, _ in json_files[:5]]
        
        # Find JSON with timestamp closest to action_completion_timestamp
        best_match_file = None
        min_delta = float('inf')
        
        for json_file in last_5_files:
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)
                
                frame_timestamp_str = data.get('timestamp')
                if not frame_timestamp_str:
                    continue
                
                # Handle both ISO format with and without Z suffix
                frame_timestamp = datetime.fromisoformat(frame_timestamp_str.replace('Z', '+00:00')).timestamp()
                delta = abs(frame_timestamp - action_completion_timestamp)
                
                if delta < min_delta:
                    min_delta = delta
                    best_match_file = json_file
            except Exception:
                # Skip files that can't be read or parsed (silent)
                continue
        
        # Update matching JSON if within 1500ms tolerance
        # Frames are written every 1s, so we need tolerance > 1000ms
        if best_match_file and min_delta < 1.5:
            lock_path = best_match_file + '.lock'
            try:
                with open(lock_path, 'w') as lock_file:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
                    try:
                        # Read current data
                        with open(best_match_file, 'r') as f:
                            data = json.load(f)
                        
                        # Add action metadata
                        data['last_action_executed'] = action.get('command')
                        data['last_action_timestamp'] = action_completion_timestamp
                        data['action_params'] = action.get('params', {})
                        
                        # Calculate action-to-frame delay
                        frame_timestamp_str = data.get('timestamp')
                        if frame_timestamp_str:
                            frame_timestamp = datetime.fromisoformat(frame_timestamp_str.replace('Z', '+00:00')).timestamp()
                            data['action_to_frame_delay_ms'] = int((frame_timestamp - action_completion_timestamp) * 1000)
                        
                        # Atomic write
                        with open(best_match_file + '.tmp', 'w') as f:
                            json.dump(data, f, indent=2)
                        os.rename(best_match_file + '.tmp', best_match_file)
                        
                        # Log to capture_monitor with prominent visual separators
                        logger.info("=" * 80)
                        logger.info("🎬 ACTION TIMESTAMP WRITTEN TO FRAME JSON")
                        logger.info("-" * 80)
                        logger.info(f"📁 File: {os.path.basename(best_match_file)}")
                        logger.info(f"⚡ Action: {action.get('command')}")
                        logger.info(f"⏱️  Timestamp: {action_completion_timestamp}")
                        logger.info(f"🎯 Delta: {int(min_delta*1000)}ms (tolerance: 1500ms)")
                        logger.info(f"📋 Params: {action.get('params', {})}")
                        logger.info("=" * 80)
                        
                        # Single-line success log
                        print(f"[@frame_metadata_utils:write_action_to_frame_json] ✅ {best_match_file} | delta={int(min_delta*1000)}ms | ts={action_completion_timestamp} | params={action.get('params', {})}")
                    finally:
                        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
                
                # Clean up lock file
                try:
                    os.remove(lock_path)
                except:
                    pass
                    
            except Exception as e:
                # Failure - detailed logging
                print(f"[@frame_metadata_utils:write_action_to_frame_json] ❌ Failed to update: {best_match_file} | error: {e}")
        elif best_match_file:
            # Tolerance exceeded - detailed logging
            print(f"[@frame_metadata_utils:write_action_to_frame_json] ⚠️ No match within 1500ms | best: {best_match_file} | delta: {int(min_delta*1000)}ms")
        else:
            # No files found - brief logging
            print(f"[@frame_metadata_utils:write_action_to_frame_json] ⚠️ No matching frames found")
    
    except Exception as e:
        # Non-blocking - log error but don't fail action execution
        print(f"[@frame_metadata_utils:write_action_to_frame_json] Error writing to frame JSON: {e}")

