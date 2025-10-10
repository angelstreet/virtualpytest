"""
Automatic Zapping Detection Utilities - Shared Code

This module provides reusable functions for automatic zapping detection that can be
called from both capture_monitor.py and zap_executor.py.

Architecture:
- Reuses existing banner detection AI from device video controllers
- Updates frame JSON for archive/playback
- Writes to live_events.json for real-time monitoring overlay
- Stores events in database

No code duplication - single source of truth!
"""

import os
import json
import fcntl
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def detect_and_record_zapping(
    device_id: str,
    device_model: str,
    capture_folder: str,
    frame_filename: str,
    blackscreen_duration_ms: int,
    action_info: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Detect zapping by analyzing channel banner and record the event.
    
    This function:
    1. Gets device video controller (reuses existing code)
    2. Analyzes frame for channel banner using AI
    3. Updates frame JSON with zapping metadata
    4. Writes to live_events.json for real-time display
    5. Stores in database
    
    Args:
        device_id: Device identifier
        device_model: Device model (for banner region)
        capture_folder: Capture folder name (e.g., 'capture1')
        frame_filename: Frame to analyze (e.g., 'capture_12345.jpg')
        blackscreen_duration_ms: Duration of blackscreen in milliseconds
        action_info: Optional dict with action metadata:
            {
                'last_action_executed': 'live_chup',
                'last_action_timestamp': 1234567890.123,
                'time_since_action_ms': 450
            }
    
    Returns:
        Dict with detection results:
        {
            'success': True/False,
            'zapping_detected': True/False,
            'channel_name': 'BBC One',
            'channel_number': '1',
            'detection_type': 'automatic'/'manual',
            'error': 'error message' (if failed)
        }
    """
    
    try:
        logger.info(f"[{capture_folder}] 🔍 Analyzing frame for channel banner: {frame_filename}")
        
        # ✅ REUSE: Get device instance and video controller
        from backend_host.src.lib.utils.host_utils import get_device_by_id
        
        device = get_device_by_id(device_id)
        if not device:
            return {'success': False, 'error': f'Device not found: {device_id}'}
        
        video_controller = device._get_controller('verification_video')
        if not video_controller:
            return {'success': False, 'error': f'No video verification controller for {device_id}'}
        
        # ✅ REUSE: Get banner region (same as zap_executor.py)
        banner_region = _get_banner_region(device_model)
        
        # Build full frame path
        from shared.src.lib.utils.storage_path_utils import get_captures_path
        captures_path = get_captures_path(capture_folder)
        frame_path = os.path.join(captures_path, frame_filename)
        
        if not os.path.exists(frame_path):
            return {'success': False, 'error': f'Frame not found: {frame_path}'}
        
        # ✅ REUSE: Call existing banner detection AI (same as zap_executor.py)
        banner_result = video_controller.ai_helpers.analyze_channel_banner_ai(
            image_path=frame_path,
            banner_region=banner_region
        )
        
        if not banner_result.get('success'):
            logger.info(f"[{capture_folder}] ❌ No banner detected - regular blackscreen, not zapping")
            return {
                'success': True,
                'zapping_detected': False,
                'error': 'No banner detected'
            }
        
        if not banner_result.get('banner_detected'):
            logger.info(f"[{capture_folder}] ❌ Banner analysis completed but no banner found")
            return {
                'success': True,
                'zapping_detected': False,
                'error': 'Banner not detected'
            }
        
        # ✅ Banner detected - this is a zapping event!
        channel_info = banner_result.get('channel_info', {})
        confidence = channel_info.get('confidence', 0.0)
        
        logger.info(f"[{capture_folder}] ✅ Channel banner detected!")
        logger.info(f"[{capture_folder}]    • Channel: {channel_info.get('channel_name', 'Unknown')} ({channel_info.get('channel_number', '')})")
        logger.info(f"[{capture_folder}]    • Program: {channel_info.get('program_name', 'Unknown')}")
        logger.info(f"[{capture_folder}]    • Confidence: {confidence:.2f}")
        
        # Determine if automatic or manual zapping
        is_automatic = action_info is not None
        detection_type = 'automatic' if is_automatic else 'manual'
        
        if is_automatic:
            logger.info(f"[{capture_folder}]    • Action: {action_info['last_action_executed']} ({action_info['time_since_action_ms']}ms before)")
        else:
            logger.info(f"[{capture_folder}]    • Action: MANUAL (no action found within 10s)")
        
        # 1️⃣ Update frame JSON (for archive/playback)
        _update_frame_json_with_zapping(
            capture_folder=capture_folder,
            frame_filename=frame_filename,
            channel_info=channel_info,
            blackscreen_duration_ms=blackscreen_duration_ms,
            is_automatic=is_automatic
        )
        
        # 2️⃣ Write to live events queue (for real-time display)
        _write_to_live_events_queue(
            capture_folder=capture_folder,
            frame_filename=frame_filename,
            channel_info=channel_info,
            blackscreen_duration_ms=blackscreen_duration_ms,
            is_automatic=is_automatic,
            action_info=action_info
        )
        
        # 3️⃣ Store in database
        _store_zapping_event(
            device_id=device_id,
            blackscreen_duration_ms=blackscreen_duration_ms,
            channel_info=channel_info,
            action_info=action_info,
            detection_type=detection_type,
            frame_path=frame_path
        )
        
        return {
            'success': True,
            'zapping_detected': True,
            'channel_name': channel_info.get('channel_name', ''),
            'channel_number': channel_info.get('channel_number', ''),
            'program_name': channel_info.get('program_name', ''),
            'confidence': confidence,
            'detection_type': detection_type
        }
        
    except Exception as e:
        logger.error(f"[{capture_folder}] ❌ Error in zapping detection: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}


def _get_banner_region(device_model: str) -> Dict[str, int]:
    """
    Get device-specific banner region for channel detection.
    ✅ REUSED from zap_executor.py (lines 454-456)
    """
    if 'android_mobile' in device_model.lower() or 'ios_mobile' in device_model.lower():
        return {'x': 470, 'y': 230, 'width': 280, 'height': 70}
    else:
        return {'x': 245, 'y': 830, 'width': 1170, 'height': 120}


def _update_frame_json_with_zapping(
    capture_folder: str,
    frame_filename: str,
    channel_info: Dict[str, Any],
    blackscreen_duration_ms: int,
    is_automatic: bool
):
    """Update frame JSON with zapping metadata (for archive/playback)"""
    try:
        from shared.src.lib.utils.storage_path_utils import get_metadata_path
        
        metadata_path = get_metadata_path(capture_folder)
        json_filename = frame_filename.replace('.jpg', '.json')
        json_file = os.path.join(metadata_path, json_filename)
        
        if not os.path.exists(json_file):
            logger.warning(f"[{capture_folder}] Frame JSON not found: {json_filename}")
            return
        
        # Atomic update with file locking
        lock_path = json_file + '.lock'
        with open(lock_path, 'w') as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            
            try:
                # Read current JSON
                with open(json_file, 'r') as f:
                    data = json.load(f)
                
                # Add zapping metadata
                data['zapping_detected'] = True
                data['zapping_channel_name'] = channel_info.get('channel_name', '')
                data['zapping_channel_number'] = channel_info.get('channel_number', '')
                data['zapping_program_name'] = channel_info.get('program_name', '')
                data['zapping_confidence'] = channel_info.get('confidence', 0.0)
                data['zapping_blackscreen_duration_ms'] = blackscreen_duration_ms
                data['zapping_detection_type'] = 'automatic' if is_automatic else 'manual'
                data['zapping_detected_at'] = datetime.now().isoformat()
                
                # Atomic write
                with open(json_file + '.tmp', 'w') as f:
                    json.dump(data, f, indent=2)
                os.rename(json_file + '.tmp', json_file)
                
                logger.info(f"[{capture_folder}] ✅ Updated {json_filename} with zapping metadata")
                
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        
        # Clean up lock file
        try:
            os.remove(lock_path)
        except:
            pass
            
    except Exception as e:
        logger.error(f"[{capture_folder}] ❌ Failed to update frame JSON: {e}")


def _write_to_live_events_queue(
    capture_folder: str,
    frame_filename: str,
    channel_info: Dict[str, Any],
    blackscreen_duration_ms: int,
    is_automatic: bool,
    action_info: Optional[Dict[str, Any]]
):
    """
    Write zapping event to live_events.json for real-time monitoring overlay.
    Events auto-expire after 10 seconds.
    """
    try:
        from shared.src.lib.utils.storage_path_utils import get_metadata_path
        
        metadata_path = get_metadata_path(capture_folder)
        live_events_file = os.path.join(metadata_path, 'live_events.json')
        
        # Create zapping event
        zapping_event = {
            'event_id': str(uuid.uuid4()),
            'event_type': 'zapping',
            'timestamp': datetime.now().isoformat(),
            'frame_filename': frame_filename,
            'detection_type': 'automatic' if is_automatic else 'manual',
            'blackscreen_duration_ms': blackscreen_duration_ms,
            'channel_name': channel_info.get('channel_name', ''),
            'channel_number': channel_info.get('channel_number', ''),
            'program_name': channel_info.get('program_name', ''),
            'confidence': channel_info.get('confidence', 0.0),
            'expires_at': (datetime.now().timestamp() + 10)  # Expires in 10 seconds
        }
        
        # Add action info if automatic
        if is_automatic and action_info:
            zapping_event['action_command'] = action_info.get('last_action_executed', '')
            zapping_event['action_timestamp'] = action_info.get('last_action_timestamp', 0)
        
        # Atomic update with file locking
        lock_path = live_events_file + '.lock'
        with open(lock_path, 'w') as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            
            try:
                # Read existing events
                events = []
                if os.path.exists(live_events_file):
                    try:
                        with open(live_events_file, 'r') as f:
                            data = json.load(f)
                            events = data.get('events', [])
                    except:
                        events = []
                
                # Remove expired events
                current_time = datetime.now().timestamp()
                events = [e for e in events if e.get('expires_at', 0) > current_time]
                
                # Add new event (newest first)
                events.insert(0, zapping_event)
                
                # Keep only last 5 events
                events = events[:5]
                
                # Write back
                data = {
                    'events': events,
                    'updated_at': datetime.now().isoformat()
                }
                
                with open(live_events_file + '.tmp', 'w') as f:
                    json.dump(data, f, indent=2)
                os.rename(live_events_file + '.tmp', live_events_file)
                
                logger.info(f"[{capture_folder}] ✅ Added to live_events.json (total: {len(events)})")
                
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        
        # Clean up lock file
        try:
            os.remove(lock_path)
        except:
            pass
            
    except Exception as e:
        logger.error(f"[{capture_folder}] ❌ Failed to write live events: {e}")


def _store_zapping_event(
    device_id: str,
    blackscreen_duration_ms: int,
    channel_info: Dict[str, Any],
    action_info: Optional[Dict[str, Any]],
    detection_type: str,
    frame_path: str
):
    """
    Store zapping event in zap_results table.
    For automatic zapping (not part of a script), script_result_id will be None.
    """
    try:
        from shared.src.lib.supabase.zap_results_db import record_zap_iteration
        from shared.src.lib.utils.storage_path_utils import get_device_info_from_capture_folder
        
        # Get device info for host_name and device_name
        # device_id might be in format 'device1', extract capture_folder
        # For now, use device_id as device_name
        
        # Determine action command and timestamps
        if action_info:
            action_command = action_info.get('last_action_executed', 'unknown')
            started_at = datetime.fromtimestamp(action_info.get('last_action_timestamp', 0))
            completed_at = datetime.now()
        else:
            action_command = 'manual_zap'  # Manual zapping (no action in system)
            completed_at = datetime.now()
            started_at = completed_at  # No action timestamp for manual
        
        duration_seconds = blackscreen_duration_ms / 1000.0
        
        # Record in zap_results table (reuses existing function)
        # Note: script_result_id is None for automatic zapping (not part of a script execution)
        result = record_zap_iteration(
            script_result_id=None,  # None for automatic zapping (requires schema update to allow NULL)
            team_id='00000000-0000-0000-0000-000000000000',  # TODO: Get from context
            host_name=os.getenv('HOST_NAME', 'unknown'),
            device_name=device_id,
            device_model='unknown',  # TODO: Get from device info
            userinterface_name='monitoring',  # Indicates automatic detection
            iteration_index=0,  # Not part of iteration loop
            action_command=action_command,
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=duration_seconds,
            blackscreen_freeze_detected=True,  # Zapping was detected
            blackscreen_freeze_duration_seconds=duration_seconds,
            detection_method=detection_type,  # 'automatic' or 'manual'
            channel_name=channel_info.get('channel_name', ''),
            channel_number=channel_info.get('channel_number', ''),
            program_name=channel_info.get('program_name', ''),
            program_start_time=channel_info.get('start_time', ''),
            program_end_time=channel_info.get('end_time', '')
        )
        
        if result:
            logger.info(f"💾 Stored {detection_type} zapping in zap_results table")
        else:
            logger.warning(f"⚠️  Failed to store zapping in database")
            
    except Exception as e:
        logger.error(f"❌ Error storing zapping event: {e}")
        import traceback
        traceback.print_exc()

