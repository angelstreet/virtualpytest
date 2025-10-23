"""
Automatic Zapping Detection Utilities - Shared Code

This module provides reusable functions for automatic zapping detection that can be
called from both capture_monitor.py and zap_executor.py.

Architecture:
- Reuses existing banner detection AI from device video controllers
- Writes truth to single frame only (historical record)
- capture_monitor writes cache to next 5 frames as they arrive
- Stores events in zap_results database table
- Frontend reads directly from frame JSON (1s polling)

✅ SIMPLE: Write truth to 1 frame, capture_monitor handles cache
✅ NO CODE DUPLICATION - single source of truth!
"""

import os
import json
import fcntl
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def detect_and_record_zapping(
    device_id: str,
    device_model: str,
    capture_folder: str,
    frame_filename: str,
    blackscreen_duration_ms: int,
    action_info: Optional[Dict[str, Any]] = None,
    audio_info: Optional[Dict[str, Any]] = None,
    transition_images: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Detect zapping by analyzing channel banner and record the event.
    
    This function:
    1. Analyzes frame for channel banner using AI
    2. Writes truth to single frame only (historical record)
    3. Writes last_zapping.json for instant access
    4. Stores in database
    5. capture_monitor writes cache to next 5 frames as they arrive
    
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
        transition_images: Optional dict with zapping transition images:
            {
                'before_frame': 'capture_12344.jpg',
                'before_thumbnail_path': '/path/to/cold/thumbnail.jpg',
                'first_blackscreen_frame': 'capture_12345.jpg',
                'first_blackscreen_thumbnail_path': '/path/to/cold/thumbnail.jpg',
                'last_blackscreen_frame': 'capture_12347.jpg',
                'last_blackscreen_thumbnail_path': '/path/to/cold/thumbnail.jpg',
                'after_frame': 'capture_12348.jpg',
                'after_thumbnail_path': '/path/to/cold/thumbnail.jpg'
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
        # Result already logged by ai_utils.py
        
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
        
        # Log action type with params (channel info already logged by ai_utils.py)
        is_automatic = action_info is not None
        detection_type = 'automatic' if is_automatic else 'manual'
        
        if is_automatic:
            action_params = action_info.get('action_params', {})
            params_str = f" {action_params}" if action_params else ""
            logger.info(f"[{capture_folder}] ⚡ AUTOMATIC zapping: {action_info['last_action_executed']}{params_str} ({action_info['time_since_action_ms']}ms before)")
        else:
            logger.info(f"[{capture_folder}] 👤 MANUAL zapping (no action found within 10s)")
        
        # ✅ ENSURE analyzed frame (after blackscreen) is in cold storage
        # This frame was just analyzed for banner - it's the "after" frame we need!
        from shared.src.lib.utils.storage_path_utils import get_thumbnails_path, copy_to_cold_storage
        analyzed_frame_cold_original = None
        analyzed_frame_cold_thumbnail = None
        
        if os.path.exists(frame_path):
            analyzed_frame_cold_original = copy_to_cold_storage(frame_path)
            if analyzed_frame_cold_original:
                logger.info(f"[{capture_folder}] 📸 Copied analyzed frame (AFTER) original to cold")
        
        # Also copy thumbnail
        thumbnails_path = get_thumbnails_path(capture_folder)
        thumbnail_filename = frame_filename.replace('.jpg', '_thumbnail.jpg')
        thumbnail_path = os.path.join(thumbnails_path, thumbnail_filename)
        
        if os.path.exists(thumbnail_path):
            analyzed_frame_cold_thumbnail = copy_to_cold_storage(thumbnail_path)
            if analyzed_frame_cold_thumbnail:
                logger.info(f"[{capture_folder}] 📸 Copied analyzed frame (AFTER) thumbnail to cold")
        
        # Update transition_images with analyzed frame as "after" (overwrite if capture_monitor provided it)
        if transition_images and analyzed_frame_cold_thumbnail:
            transition_images['after_frame'] = frame_filename
            transition_images['after_original_path'] = analyzed_frame_cold_original
            transition_images['after_thumbnail_path'] = analyzed_frame_cold_thumbnail
            logger.info(f"[{capture_folder}] ✅ Using analyzed frame as AFTER image (no need to fetch separately)")
        
        # ✅ UPLOAD transition images to R2 (images already in cold storage from capture_monitor)
        r2_images = None
        if transition_images:
            logger.info(f"[{capture_folder}] 📤 Uploading zapping transition images to R2...")
            from datetime import datetime
            now = datetime.now()
            time_key = f"{now.year}{now.month:02d}{now.day:02d}_{now.hour:02d}{now.minute:02d}{now.second:02d}"
            
            # Import incident_manager to reuse R2 upload logic (same as freeze/blackscreen)
            try:
                # Get incident manager from capture_monitor's global instance
                # Alternative: Create temporary instance just for upload
                from backend_host.scripts.incident_manager import IncidentManager
                incident_manager = IncidentManager(skip_startup_cleanup=True)  # Don't cleanup on temp instance
                
                r2_images = incident_manager.upload_zapping_transition_images_to_r2(
                    transition_images=transition_images,
                    capture_folder=capture_folder,
                    time_key=time_key
                )
                
                if r2_images:
                    uploaded_count = sum(1 for url in [r2_images.get('before_url'), r2_images.get('first_blackscreen_url'), 
                                                       r2_images.get('last_blackscreen_url'), r2_images.get('after_url')] if url)
                    logger.info(f"[{capture_folder}] ✅ R2 upload complete: {uploaded_count}/4 transition images")
                else:
                    logger.warning(f"[{capture_folder}] ⚠️  R2 upload failed or no images available")
                    
            except Exception as e:
                logger.error(f"[{capture_folder}] Error uploading to R2: {e}")
                import traceback
                traceback.print_exc()
        
        # 1️⃣ Write truth to single frame only (historical record)
        # capture_monitor will write cache to next 5 frames as they arrive
        zapping_data = {
            'channel_name': channel_info.get('channel_name', ''),
            'channel_number': channel_info.get('channel_number', ''),
            'program_name': channel_info.get('program_name', ''),
            'program_start_time': channel_info.get('start_time', ''),
            'program_end_time': channel_info.get('end_time', ''),
            'confidence': channel_info.get('confidence', 0.0),
            'blackscreen_duration_ms': blackscreen_duration_ms,
            'detection_type': 'automatic' if is_automatic else 'manual',
            'audio_silence_duration': audio_info.get('silence_duration', 0.0) if audio_info else 0.0,
        }
        
        _write_zapping_to_frame(
            capture_folder=capture_folder,
            frame_filename=frame_filename,
            zapping_data=zapping_data
        )
        
        # 2️⃣ Write last_zapping.json (instant read for zap_executor - no searching needed!)
        _write_last_zapping_json(
            capture_folder=capture_folder,
            frame_filename=frame_filename,
            channel_info=channel_info,
            blackscreen_duration_ms=blackscreen_duration_ms,
            is_automatic=is_automatic,
            action_info=action_info,
            audio_info=audio_info,
            transition_images=transition_images,
            r2_images=r2_images
        )
        
        # 3️⃣ Store in database
        # Calculate total zap duration for automatic zaps (action → blackscreen end)
        time_since_action_ms = action_info.get('time_since_action_ms') if action_info else None
        total_zap_duration_ms = (time_since_action_ms + blackscreen_duration_ms) if time_since_action_ms else blackscreen_duration_ms
        
        _store_zapping_event(
            device_id=device_id,
            device_model=device_model,
            blackscreen_duration_ms=blackscreen_duration_ms,
            channel_info=channel_info,
            action_info=action_info,
            detection_type=detection_type,
            frame_path=frame_path,
            audio_info=audio_info,
            time_since_action_ms=time_since_action_ms,
            total_zap_duration_ms=total_zap_duration_ms
        )
        
        return {
            'success': True,
            'zapping_detected': True,
            'id': f"zap_cache_{frame_filename}",  # ✅ ADD: ID for deduplication
            'channel_name': channel_info.get('channel_name', ''),
            'channel_number': channel_info.get('channel_number', ''),
            'program_name': channel_info.get('program_name', ''),
            'program_start_time': channel_info.get('start_time', ''),  # ✅ ADD: Missing field
            'program_end_time': channel_info.get('end_time', ''),      # ✅ ADD: Missing field
            'confidence': confidence,
            'detection_type': detection_type,
            'blackscreen_duration_ms': blackscreen_duration_ms,        # ✅ ADD: For frontend display
            'time_since_action_ms': time_since_action_ms,              # ✅ ADD: For total calculation
            'total_zap_duration_ms': total_zap_duration_ms,            # ✅ ADD: Backend calculated total
            'audio_silence_duration': audio_info.get('silence_duration', 0.0) if audio_info else 0.0,  # ✅ ADD: Audio info
            'r2_images': r2_images if r2_images else {}  # ✅ ADD: R2 URLs for capture_monitor logging
        }
        
    except Exception as e:
        logger.error(f"[{capture_folder}] ❌ Error in zapping detection: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}




def _write_zapping_to_frame(
    capture_folder: str,
    frame_filename: str,
    zapping_data: Dict[str, Any]
):
    """
    Write zapping truth to single frame only (where blackscreen ended).
    capture_monitor will handle writing cache to next 5 frames as they arrive.
    
    Args:
        capture_folder: Device folder (e.g., 'capture1')
        frame_filename: Target frame (e.g., 'capture_000003655.jpg')
        zapping_data: Dict with channel info, duration, confidence, etc.
    """
    try:
        from shared.src.lib.utils.storage_path_utils import get_metadata_path
        
        metadata_path = get_metadata_path(capture_folder)
        
        # Extract sequence number
        try:
            sequence = int(frame_filename.split('_')[1].split('.')[0])
        except:
            logger.warning(f"[{capture_folder}] Could not extract sequence from {frame_filename}")
            return
        
        # Build JSON path
        json_filename = f"capture_{sequence:09d}.json"
        json_path = os.path.join(metadata_path, json_filename)
        
        if not os.path.exists(json_path):
            logger.warning(f"[{capture_folder}] Frame JSON not found: {json_path}")
            return
        
        # Prepare zapping metadata
        zapping_id = f"zap_{sequence}_{int(datetime.now().timestamp())}"
        zapping_metadata = {
            'detected': True,
            'id': zapping_id,
            'detected_at': datetime.now().isoformat(),
            **zapping_data
        }
        
        # Atomic update with file locking
        lock_path = json_path + '.lock'
        try:
            with open(lock_path, 'w') as lock_file:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
                
                try:
                    # Read current JSON
                    with open(json_path, 'r') as f:
                        data = json.load(f)
                    
                    # Add zapping truth
                    data['zap'] = zapping_metadata
                    
                    # Atomic write
                    with open(json_path + '.tmp', 'w') as f:
                        json.dump(data, f, indent=2)
                    os.rename(json_path + '.tmp', json_path)
                    
                    logger.info(f"[{capture_folder}] ✅ Wrote truth to {json_filename} (ID: {zapping_id})")
                    
                finally:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            
            # Clean up lock file
            try:
                os.remove(lock_path)
            except:
                pass
                
        except Exception as e:
            logger.error(f"[{capture_folder}] Failed to update {json_filename}: {e}")
            
    except Exception as e:
        logger.error(f"[{capture_folder}] ❌ Failed to write truth: {e}")


def _write_last_zapping_json(
    capture_folder: str,
    frame_filename: str,
    channel_info: Dict[str, Any],
    blackscreen_duration_ms: int,
    is_automatic: bool,
    action_info: Optional[Dict[str, Any]],
    audio_info: Optional[Dict[str, Any]] = None,
    transition_images: Optional[Dict[str, Any]] = None,
    r2_images: Optional[Dict[str, Any]] = None
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
        
        # Calculate total zap duration (action → blackscreen end)
        time_since_action_ms = action_info.get('time_since_action_ms') if action_info else None
        total_zap_duration_ms = (time_since_action_ms + blackscreen_duration_ms) if time_since_action_ms else None
        
        zapping_data = {
            'status': 'completed',  # ✅ Mark as completed (zap_executor polls until not 'in_progress')
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
            'action_params': action_info.get('action_params', {}) if action_info else {},  # ✅ ADD: Full params (e.g., {"key": "CHANNEL_UP"})
            'time_since_action_ms': time_since_action_ms,
            'total_zap_duration_ms': total_zap_duration_ms,  # ✅ NEW: Total zap duration (action → after blackscreen)
            
            # Audio dropout analysis (silence duration only - used for zapping pre-check)
            'audio_silence_duration': audio_info.get('silence_duration', 0.0) if audio_info else 0.0,
            
            # ✅ NEW: Transition images (before → first blackscreen → last blackscreen → after)
            'transition_images': transition_images if transition_images else {},
            
            # ✅ NEW: R2 image URLs (uploaded above when zapping confirmed)
            'r2_images': r2_images if r2_images else {}
        }
        
        # Atomic write
        with open(last_zapping_path + '.tmp', 'w') as f:
            json.dump(zapping_data, f, indent=2)
        os.rename(last_zapping_path + '.tmp', last_zapping_path)
        
        # Verify file exists
        if os.path.exists(last_zapping_path):
            file_size = os.path.getsize(last_zapping_path)
            logger.info(f"[{capture_folder}] ✅ last_zapping.json written successfully ({file_size} bytes)")
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
    device_model: str,
    blackscreen_duration_ms: int,
    channel_info: Dict[str, Any],
    action_info: Optional[Dict[str, Any]],
    detection_type: str,
    frame_path: str,
    audio_info: Optional[Dict[str, Any]] = None,
    time_since_action_ms: Optional[int] = None,
    total_zap_duration_ms: Optional[int] = None
):
    """
    Store zapping event in zap_results table.
    For automatic zapping (not part of a script), script_result_id will be None.
    
    Args:
        device_model: Device model (used as userinterface_name for automatic zapping)
        audio_info: Optional audio dropout analysis data (stored in frame JSON, logged here for visibility)
    """
    try:
        from shared.src.lib.database.zap_results_db import record_zap_iteration
        from shared.src.lib.utils.storage_path_utils import get_device_info_from_capture_folder
        
        # Get device info for host_name and device_name
        # device_id might be in format 'device1', extract capture_folder
        # For now, use device_id as device_name
        
        # Determine action command and timestamps
        # Use high-precision timestamp to prevent 409 conflicts from duplicate entries
        import time
        current_timestamp = time.time()  # High precision (includes microseconds)
        
        if action_info:
            action_command = action_info.get('last_action_executed', 'unknown')
            # ✅ FIX: Use UTC timezone to match database expectations
            started_at = datetime.fromtimestamp(action_info.get('last_action_timestamp', 0), tz=timezone.utc)
            completed_at = datetime.fromtimestamp(current_timestamp, tz=timezone.utc)
        else:
            action_command = 'manual_zap'  # Manual zapping (no action in system)
            # ✅ FIX: Use UTC timezone to match database expectations
            completed_at = datetime.fromtimestamp(current_timestamp, tz=timezone.utc)
            started_at = datetime.fromtimestamp(current_timestamp - 0.001, tz=timezone.utc)  # 1ms before
        
        duration_seconds = blackscreen_duration_ms / 1000.0
        
        # Log audio dropout analysis (simplified - silence duration only)
        if audio_info:
            silence_duration = audio_info.get('silence_duration', 0.0)
            logger.info(f"🔊 Audio silence: {silence_duration:.2f}s")
        
        # Get default team_id for automatic zapping (same as used in script_executor)
        team_id ='7fdeb4bb-3639-4ec3-959f-b54769a219ce'
        
        # Record in zap_results table (reuses existing function)
        # Note: script_result_id is None for automatic zapping (not part of a script execution)
        result = record_zap_iteration(
            script_result_id=None,  # None for automatic zapping (not part of a script execution)
            team_id=team_id,  # Use default team_id (same pattern as script_executor)
            host_name=os.getenv('HOST_NAME', 'unknown'),
            device_name=device_id,
            device_model=device_model,
            userinterface_name=device_model,  # Use device_model instead of 'monitoring'
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
            program_end_time=channel_info.get('end_time', ''),
            audio_silence_duration=audio_info.get('silence_duration', 0.0) if audio_info else None,  # ✅ Audio silence tracking
            action_params=action_info.get('action_params') if action_info else None,  # ✅ Action parameters (e.g., {"key": "CHANNEL_UP"})
            time_since_action_ms=time_since_action_ms,  # ✅ NEW: Time from action to blackscreen end
            total_zap_duration_ms=total_zap_duration_ms  # ✅ NEW: Total zap duration
        )
        
        if result:
            logger.info(f"💾 Stored {detection_type} zapping in zap_results table")
        else:
            logger.warning(f"⚠️  Failed to store zapping in database")
            
    except Exception as e:
        logger.error(f"❌ Error storing zapping event: {e}")
        import traceback
        traceback.print_exc()

