"""
Automatic Zapping Detection Utilities - Shared Code

This module provides reusable functions for automatic zapping detection that can be
called from both capture_monitor.py and zap_executor.py.

Architecture:
- Reuses existing banner detection AI from device video controllers
- Updates frame JSON with zapping metadata (single source of truth!)
- Stores events in zap_results database table
- Frontend reads directly from frame JSON (1s polling)

✅ OPTIMIZED: No separate live events system - frame JSON has everything!
✅ NO CODE DUPLICATION - single source of truth!
"""

import os
import json
import fcntl
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
        
        # ✅ STANDALONE: Use AI utility (no controllers needed!)
        from shared.src.lib.utils.ai_utils import analyze_channel_banner_ai, get_banner_region_for_device
        from shared.src.lib.utils.storage_path_utils import get_captures_path
        
        # Get banner region for this device type
        banner_region = get_banner_region_for_device(device_model)
        
        # Build full frame path
        captures_path = get_captures_path(capture_folder)
        frame_path = os.path.join(captures_path, frame_filename)
        
        logger.debug(f"[{capture_folder}] Frame path: {frame_path}")
        if not os.path.exists(frame_path):
            logger.warning(f"[{capture_folder}] ❌ Frame not found: {frame_path}")
            return {'success': False, 'error': f'Frame not found: {frame_path}'}
        
        # ✅ STANDALONE: Call AI banner detection (works from any process!)
        logger.info(f"[{capture_folder}] 🤖 Calling AI banner analysis (region hint: {banner_region})...")
        banner_result = analyze_channel_banner_ai(
            image_path=frame_path,
            banner_region=banner_region,
            context_name=capture_folder
        )
        logger.info(f"[{capture_folder}] 🤖 AI analysis complete: success={banner_result.get('success')}, banner_detected={banner_result.get('banner_detected')}")
        
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
        
        # ❌ REMOVED: Live events queue - redundant! Frame JSON is single source of truth
        # Frontend polls frame JSON directly (1s interval) which already has zapping + action data
        
        # 2️⃣ Store in database
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


# ❌ REMOVED: _write_to_live_events_queue() - No longer needed!
# Frame JSON is the single source of truth (includes both action + zapping data)
# Frontend polls frame JSON directly - no need for separate live events system


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

