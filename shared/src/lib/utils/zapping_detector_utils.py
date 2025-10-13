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
    action_info: Optional[Dict[str, Any]] = None,
    audio_info: Optional[Dict[str, Any]] = None
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
        audio_info: Optional dict with audio analysis metadata:
            {
                'has_continuous_audio': False,
                'silence_duration': 0.56,
                'mean_volume_db': -100.0,
                'segment_duration': 1.0
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
        from shared.src.lib.utils.ai_utils import analyze_channel_banner_ai
        from shared.src.lib.utils.storage_path_utils import get_captures_path
        
        # Build full frame path
        captures_path = get_captures_path(capture_folder)
        frame_path = os.path.join(captures_path, frame_filename)
        
        logger.info(f"[{capture_folder}] 📸 FULL FRAME PATH: {frame_path}")
        logger.info(f"[{capture_folder}] 📂 Captures directory: {captures_path}")
        logger.info(f"[{capture_folder}] 📄 Frame filename: {frame_filename}")
        logger.info(f"[{capture_folder}] ✓ Frame exists: {os.path.exists(frame_path)}")
        if os.path.exists(frame_path):
            file_size = os.path.getsize(frame_path)
            logger.info(f"[{capture_folder}] 📏 Frame size: {file_size} bytes ({file_size/1024:.1f} KB)")
        
        if not os.path.exists(frame_path):
            logger.warning(f"[{capture_folder}] ❌ Frame not found: {frame_path}")
            return {'success': False, 'error': f'Frame not found: {frame_path}'}
        
        # ✅ STANDALONE: Call AI banner detection (works from any process!)
        logger.info(f"[{capture_folder}] 🤖 Calling AI banner analysis...")
        banner_result = analyze_channel_banner_ai(
            image_path=frame_path,
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
            is_automatic=is_automatic,
            audio_info=audio_info
        )
        
        # ❌ REMOVED: Live events queue - redundant! Frame JSON is single source of truth
        # Frontend polls frame JSON directly (1s interval) which already has zapping + action data
        
        # 2️⃣ Write last_zapping.json (instant read for zap_executor - no searching needed!)
        _write_last_zapping_json(
            capture_folder=capture_folder,
            frame_filename=frame_filename,
            channel_info=channel_info,
            blackscreen_duration_ms=blackscreen_duration_ms,
            is_automatic=is_automatic,
            action_info=action_info,
            audio_info=audio_info
        )
        
        # 3️⃣ Store in database
        _store_zapping_event(
            device_id=device_id,
            blackscreen_duration_ms=blackscreen_duration_ms,
            channel_info=channel_info,
            action_info=action_info,
            detection_type=detection_type,
            frame_path=frame_path,
            audio_info=audio_info
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
    is_automatic: bool,
    audio_info: Optional[Dict[str, Any]] = None
):
    """
    Update frame JSON with zapping metadata.
    
    ✅ RACE CONDITION FIX: Write to current frame + next 5 frames
    This ensures frontend catches the zapping event even if AI analysis completes
    after frontend has already read the original frame.
    """
    try:
        from shared.src.lib.utils.storage_path_utils import get_metadata_path
        
        metadata_path = get_metadata_path(capture_folder)
        
        # Extract sequence number from frame_filename
        try:
            sequence = int(frame_filename.split('_')[1].split('.')[0])
        except:
            logger.warning(f"[{capture_folder}] Could not extract sequence from {frame_filename}")
            return
        
        # Prepare zapping metadata
        zapping_id = f"zap_{sequence}_{int(datetime.now().timestamp())}"
        detected_at = datetime.now().isoformat()
        
        zapping_metadata = {
            'zapping_detected': True,
            'zapping_id': zapping_id,  # Unique ID for frontend caching
            'zapping_channel_name': channel_info.get('channel_name', ''),
            'zapping_channel_number': channel_info.get('channel_number', ''),
            'zapping_program_name': channel_info.get('program_name', ''),
            'zapping_program_start_time': channel_info.get('start_time', ''),
            'zapping_program_end_time': channel_info.get('end_time', ''),
            'zapping_confidence': channel_info.get('confidence', 0.0),
            'zapping_blackscreen_duration_ms': blackscreen_duration_ms,
            'zapping_detection_type': 'automatic' if is_automatic else 'manual',
            'zapping_detected_at': detected_at,
            # Audio dropout analysis (silence duration only - used for zapping pre-check)
            'zapping_audio_silence_duration': audio_info.get('silence_duration', 0.0) if audio_info else 0.0,
        }
        
        # Write to current frame + next 5 frames (ensures frontend catches it)
        frames_written = 0
        for offset in range(6):  # Current frame + next 5
            target_sequence = sequence + offset
            target_filename = f"capture_{target_sequence:09d}.json"
            target_file = os.path.join(metadata_path, target_filename)
            
            if not os.path.exists(target_file):
                continue  # Frame doesn't exist yet, skip
            
            # Atomic update with file locking
            lock_path = target_file + '.lock'
            try:
                with open(lock_path, 'w') as lock_file:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
                    
                    try:
                        # Read current JSON
                        with open(target_file, 'r') as f:
                            data = json.load(f)
                        
                        # Add zapping metadata
                        data.update(zapping_metadata)
                        
                        # Atomic write
                        with open(target_file + '.tmp', 'w') as f:
                            json.dump(data, f, indent=2)
                        os.rename(target_file + '.tmp', target_file)
                        
                        frames_written += 1
                        
                    finally:
                        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
                
                # Clean up lock file
                try:
                    os.remove(lock_path)
                except:
                    pass
                    
            except Exception as e:
                logger.debug(f"[{capture_folder}] Failed to update {target_filename}: {e}")
                continue
        
        logger.info(f"[{capture_folder}] ✅ Updated {frames_written}/6 frames with zapping metadata (ID: {zapping_id})")
            
    except Exception as e:
        logger.error(f"[{capture_folder}] ❌ Failed to update frame JSON: {e}")


def _write_last_zapping_json(
    capture_folder: str,
    frame_filename: str,
    channel_info: Dict[str, Any],
    blackscreen_duration_ms: int,
    is_automatic: bool,
    action_info: Optional[Dict[str, Any]],
    audio_info: Optional[Dict[str, Any]] = None
):
    """
    Write last_zapping.json for instant read by zap_executor.
    
    ✅ INSTANT ACCESS: Single file read instead of searching 100+ JSONs.
    ✅ SAME PATH AS METADATA: Uses get_metadata_path() - hot or cold based on mode.
    ✅ NO GUESSING: Write where metadata is written, read where metadata is read.
    """
    try:
        from shared.src.lib.utils.storage_path_utils import get_metadata_path
        
        # ✅ WRITE TO SAME LOCATION AS METADATA (hot or cold based on mode)
        # RAM mode: /var/www/html/stream/capture1/hot/metadata/last_zapping.json
        # SD mode:  /var/www/html/stream/capture1/metadata/last_zapping.json
        metadata_path = get_metadata_path(capture_folder)
        last_zapping_path = os.path.join(metadata_path, 'last_zapping.json')
        
        logger.info(f"[{capture_folder}] 📝 Writing last_zapping.json to: {last_zapping_path}")
        
        # Ensure directory exists
        os.makedirs(metadata_path, exist_ok=True)
        
        # Prepare complete zapping data
        detected_at = datetime.now().isoformat()
        
        zapping_data = {
            'zapping_detected': True,
            'detected_at': detected_at,
            'frame_filename': frame_filename,
            
            # Channel info
            'channel_name': channel_info.get('channel_name', ''),
            'channel_number': channel_info.get('channel_number', ''),
            'program_name': channel_info.get('program_name', ''),
            'program_start_time': channel_info.get('start_time', ''),
            'program_end_time': channel_info.get('end_time', ''),
            'confidence': channel_info.get('confidence', 0.0),
            
            # Zapping details
            'blackscreen_duration_ms': blackscreen_duration_ms,
            'detection_type': 'automatic' if is_automatic else 'manual',
            
            # Action info (for matching by zap_executor)
            'action_timestamp': action_info.get('last_action_timestamp') if action_info else None,
            'action_command': action_info.get('last_action_executed') if action_info else None,
            'time_since_action_ms': action_info.get('time_since_action_ms') if action_info else None,
            
            # Audio dropout analysis (silence duration only - used for zapping pre-check)
            'audio_silence_duration': audio_info.get('silence_duration', 0.0) if audio_info else 0.0,
        }
        
        # Atomic write
        with open(last_zapping_path + '.tmp', 'w') as f:
            json.dump(zapping_data, f, indent=2)
        os.rename(last_zapping_path + '.tmp', last_zapping_path)
        
        # Verify file exists
        if os.path.exists(last_zapping_path):
            file_size = os.path.getsize(last_zapping_path)
            logger.info(f"[{capture_folder}] ✅ last_zapping.json written successfully: {last_zapping_path} ({file_size} bytes)")
        else:
            logger.error(f"[{capture_folder}] ❌ last_zapping.json write failed - file doesn't exist after write!")
        
    except Exception as e:
        logger.error(f"[{capture_folder}] ❌ Failed to write last_zapping.json: {e}")
        import traceback
        logger.error(f"[{capture_folder}] Traceback: {traceback.format_exc()}")


# ❌ REMOVED: _write_to_live_events_queue() - No longer needed!
# Frame JSON is the single source of truth (includes both action + zapping data)
# Frontend polls frame JSON directly - no need for separate live events system


def _store_zapping_event(
    device_id: str,
    blackscreen_duration_ms: int,
    channel_info: Dict[str, Any],
    action_info: Optional[Dict[str, Any]],
    detection_type: str,
    frame_path: str,
    audio_info: Optional[Dict[str, Any]] = None
):
    """
    Store zapping event in zap_results table.
    For automatic zapping (not part of a script), script_result_id will be None.
    
    Args:
        audio_info: Optional audio dropout analysis data (stored in frame JSON, logged here for visibility)
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
        
        # Log audio dropout analysis (simplified - silence duration only)
        if audio_info:
            silence_duration = audio_info.get('silence_duration', 0.0)
            logger.info(f"🔊 Audio silence: {silence_duration:.2f}s")
        
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

