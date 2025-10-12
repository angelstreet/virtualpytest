#!/usr/bin/env python3
"""
Simple incident manager - state machine + DB operations
Single thread, minimal complexity
"""
import os
import sys
import logging
import time
from datetime import datetime

from shared.src.lib.utils.storage_path_utils import get_device_info_from_capture_folder

current_dir = os.path.dirname(os.path.abspath(__file__))
backend_host_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(backend_host_dir)

try:
    from dotenv import load_dotenv
    
    project_env_path = os.path.join(project_root, '.env')
    if os.path.exists(project_env_path):
        load_dotenv(project_env_path)
        print(f"[@incident_manager] Loaded project environment from {project_env_path}")
        print(f"[@incident_manager] SUPABASE_URL={os.getenv('NEXT_PUBLIC_SUPABASE_URL')}")
        print(f"[@incident_manager] CLOUDFLARE_R2_ENDPOINT={os.getenv('CLOUDFLARE_R2_ENDPOINT')}")
    else:
        print(f"[@incident_manager] Warning: Project .env not found at {project_env_path}")
    
    # Load backend_host .env second (HOST/DEVICE config)
    backend_env_path = os.path.join(backend_host_dir, 'src', '.env')
    if os.path.exists(backend_env_path):
        load_dotenv(backend_env_path)
        print(f"[@incident_manager] Loaded backend_host environment from {backend_env_path}")
        # Debug: Show key environment variables
        print(f"[@incident_manager] HOST_NAME={os.getenv('HOST_NAME')}")
        print(f"[@incident_manager] HOST_VIDEO_CAPTURE_PATH={os.getenv('HOST_VIDEO_CAPTURE_PATH')}")
        print(f"[@incident_manager] HOST_VIDEO_STREAM_PATH={os.getenv('HOST_VIDEO_STREAM_PATH')}")
        print(f"[@incident_manager] DEVICE1_NAME={os.getenv('DEVICE1_NAME')}")
        print(f"[@incident_manager] DEVICE1_VIDEO_CAPTURE_PATH={os.getenv('DEVICE1_VIDEO_CAPTURE_PATH')}")
        print(f"[@incident_manager] DEVICE1_VIDEO_STREAM_PATH={os.getenv('DEVICE1_VIDEO_STREAM_PATH')}")
    else:
        print(f"[@incident_manager] Warning: Backend host .env not found at {backend_env_path}")
        
except ImportError:
    print("[@incident_manager] Warning: python-dotenv not available, skipping .env loading")

# Lazy import to reduce startup time
create_alert_safe = None
resolve_alert = None

def _lazy_import_db():
    """Lazy import database functions only when needed."""
    global create_alert_safe, resolve_alert
    if create_alert_safe is None:
        try:
            from shared.src.lib.supabase.alerts_db import create_alert_safe as _create_alert_safe, resolve_alert as _resolve_alert
            create_alert_safe = _create_alert_safe
            resolve_alert = _resolve_alert
            logger.info("Database functions imported successfully")
        except ImportError as e:
            logger.warning(f"Could not import alerts_db module: {e}. Database operations will be skipped.")
            create_alert_safe = False  # Mark as attempted
            resolve_alert = False

# Use same logger as capture_monitor
logger = logging.getLogger('capture_monitor')

# Simple states
NORMAL = 0
INCIDENT = 1

class IncidentManager:
    def __init__(self, skip_startup_cleanup=False):
        self.device_states = {}  # {device_id: {state: int, active_incidents: {type: incident_id}, pending_incidents: {type: timestamp}}}
        self.INCIDENT_REPORT_DELAY = 30  # Only report to DB after 30 seconds of continuous detection
        # Start fresh on service restart - resolve any stale incidents from previous run
        # Skip cleanup if called from transcript_accumulator (only report audio, don't manage incident lifecycle)
        if not skip_startup_cleanup:
            self._resolve_all_incidents_on_startup()
        
    def get_device_state(self, device_id):
        """Get current state for device"""
        if device_id not in self.device_states:
            self.device_states[device_id] = {
                'state': NORMAL,
                'active_incidents': {},  # {issue_type: alert_id} - incidents in DB
                'pending_incidents': {}  # {issue_type: first_detected_timestamp} - not yet in DB
            }
        return self.device_states[device_id]
    
    def _resolve_all_incidents_on_startup(self):
        """Resolve all active incidents on service restart - start fresh with no stale state"""
        try:
            logger.info("[@incident_manager] 🔄 Service restart detected - resolving all stale incidents...")
            
            # Use lazy import to get database functions
            _lazy_import_db()
            if not resolve_alert or resolve_alert is False:
                logger.warning("[@incident_manager] Database module not available, starting with empty state")
                return
            
            # Import the get_active_alerts function
            try:
                from shared.src.lib.supabase.alerts_db import get_active_alerts
            except ImportError as e:
                logger.warning(f"[@incident_manager] Could not import get_active_alerts: {e}")
                return
            
            # Get all active alerts from database
            result = get_active_alerts()
            
            if not result.get('success'):
                logger.error(f"[@incident_manager] Failed to load active incidents: {result.get('error')}")
                return
            
            active_alerts = result.get('alerts', [])
            
            if not active_alerts:
                logger.info("[@incident_manager] ✓ No stale incidents to resolve - starting fresh")
                return
            
            logger.info(f"[@incident_manager] Found {len(active_alerts)} stale incidents - resolving all...")
            
            # Resolve all active incidents (they're from previous service run)
            resolved_count = 0
            for alert in active_alerts:
                alert_id = alert.get('id')
                device_id = alert.get('device_id')
                incident_type = alert.get('incident_type')
                
                if not alert_id:
                    logger.warning(f"[@incident_manager] Skipping alert without ID: {alert}")
                    continue
                
                # Resolve the incident in database
                resolve_result = resolve_alert(alert_id)
                
                if resolve_result.get('success'):
                    resolved_count += 1
                    logger.info(f"[@incident_manager] ✓ Resolved stale incident: {device_id} -> {incident_type} (alert_id: {alert_id})")
                else:
                    logger.error(f"[@incident_manager] ✗ Failed to resolve incident {alert_id}: {resolve_result.get('error')}")
            
            logger.info(f"[@incident_manager] ✅ Service restart cleanup: Resolved {resolved_count}/{len(active_alerts)} stale incidents")
            logger.info(f"[@incident_manager] Starting fresh - incidents will re-create if issues persist for 5+ minutes")
            
        except Exception as e:
            logger.error(f"[@incident_manager] Error resolving stale incidents on startup: {e}")
            # Continue with empty state - don't crash the service
    
    def cleanup_orphaned_incidents(self, monitored_capture_folders, host_name):
        """Auto-resolve incidents for capture folders that are no longer being monitored"""
        try:
            logger.info(f"[@incident_manager] Cleaning up orphaned incidents for unmonitored capture folders...")
            
            # Get list of device_ids we're currently monitoring
            monitored_device_ids = set()
            for capture_folder in monitored_capture_folders:
                device_info = get_device_info_from_capture_folder(capture_folder)
                device_id = device_info.get('device_id', capture_folder)
                monitored_device_ids.add(device_id)
            
            logger.info(f"[@incident_manager] Monitored device IDs: {monitored_device_ids}")
            
            # Check all loaded device states for orphaned incidents
            orphaned_count = 0
            for device_id, device_state in list(self.device_states.items()):
                # Skip if this device is being monitored
                if device_id in monitored_device_ids:
                    continue
                
                # This device has incidents but is NOT monitored locally - resolve all its incidents
                active_incidents = device_state.get('active_incidents', {})
                if active_incidents:
                    logger.info(f"[@incident_manager] Found orphaned device '{device_id}' with {len(active_incidents)} active incidents - resolving...")
                    
                    for issue_type, incident_id in list(active_incidents.items()):
                        logger.info(f"[@incident_manager] Resolving orphaned incident: {device_id} -> {issue_type} (alert_id: {incident_id})")
                        success = self.resolve_incident(device_id, incident_id, issue_type)
                        if success:
                            orphaned_count += 1
                    
                    # Clear the device state after resolving all incidents
                    del self.device_states[device_id]
            
            if orphaned_count > 0:
                logger.info(f"[@incident_manager] ✅ Cleaned up {orphaned_count} orphaned incidents")
            else:
                logger.info(f"[@incident_manager] No orphaned incidents found")
                
        except Exception as e:
            logger.error(f"[@incident_manager] Error cleaning up orphaned incidents: {e}")
    
    def create_incident(self, capture_folder, issue_type, host_name, analysis_result=None):
        """Create new incident in DB using original working method"""
        try:
            logger.info(f"[{capture_folder}] DB INSERT: Creating {issue_type} incident")
            
            # Get device info from .env by matching capture folder
            device_info = get_device_info_from_capture_folder(capture_folder)
            device_id = device_info.get('device_id', capture_folder)  # Use logical device_id
            device_name = device_info['device_name']
            capture_path = device_info.get('capture_path', capture_folder)  # Use capture folder name
            
            # Use lazy import exactly as before
            _lazy_import_db()
            if not create_alert_safe or create_alert_safe is False:
                logger.warning("Database module not available, skipping alert creation")
                return None
            
            # Prepare enhanced metadata with all details
            enhanced_metadata = {
                'stream_path': device_info.get('stream_path'),
                'capture_path': capture_path
            }
            if analysis_result:
                for key, value in analysis_result.items():
                    enhanced_metadata[key] = value
            
            # Add specific metadata based on incident type (SAME AS ORIGINAL)
            if issue_type == 'blackscreen':
                enhanced_metadata['blackscreen_percentage'] = analysis_result.get('blackscreen_percentage', 0)
            elif issue_type == 'freeze':
                enhanced_metadata['freeze_diffs'] = analysis_result.get('freeze_diffs', [])
            elif issue_type == 'macroblocks':
                enhanced_metadata['quality_score'] = analysis_result.get('quality_score', 0)
            elif issue_type == 'audio_loss':
                enhanced_metadata['volume_percentage'] = analysis_result.get('volume_percentage', 0)
                enhanced_metadata['mean_volume_db'] = analysis_result.get('mean_volume_db', -100)
            
            # Add frame information and R2 URLs (uploaded immediately by capture_monitor)
            if 'last_3_filenames' in analysis_result:
                enhanced_metadata['last_3_filenames'] = analysis_result['last_3_filenames']
                logger.info(f"[{capture_folder}] 📋 Added last_3_filenames to metadata: {len(analysis_result['last_3_filenames'])} files")
                
            if 'last_3_thumbnails' in analysis_result:
                enhanced_metadata['last_3_thumbnails'] = analysis_result['last_3_thumbnails']
                logger.info(f"[{capture_folder}] 📋 Added last_3_thumbnails to metadata: {len(analysis_result['last_3_thumbnails'])} items")
                
            if 'r2_images' in analysis_result:
                enhanced_metadata['r2_images'] = analysis_result['r2_images']
                
                # Handle both freeze (multiple thumbnails) and blackscreen/macroblocks (single thumbnail)
                if 'thumbnail_urls' in analysis_result['r2_images']:
                    # Freeze incident - multiple thumbnails
                    r2_count = len(analysis_result['r2_images']['thumbnail_urls'])
                    logger.info(f"[{capture_folder}] 📋 Creating {issue_type.upper()} incident with {r2_count} R2 image URLs:")
                    for i, url in enumerate(analysis_result['r2_images']['thumbnail_urls']):
                        logger.info(f"[{capture_folder}]     🖼️  R2 Image {i+1}: {url}")
                elif 'thumbnail_url' in analysis_result['r2_images']:
                    # Blackscreen/Macroblocks - single thumbnail with optional closure
                    logger.info(f"[{capture_folder}] 📋 Creating {issue_type.upper()} incident with R2 images:")
                    logger.info(f"[{capture_folder}]     🖼️  Start: {analysis_result['r2_images']['thumbnail_url']}")
                    if 'closure_url' in analysis_result['r2_images']:
                        logger.info(f"[{capture_folder}]     🖼️  End: {analysis_result['r2_images']['closure_url']}")
                else:
                    # Only warn for freeze - blackscreen/macroblocks may not have images if < 5s
                    if issue_type == 'freeze':
                        logger.warning(f"[{capture_folder}] ⚠️  NO r2_images in analysis_result for {issue_type} incident!")
            
            # Call database exactly as before
            result = create_alert_safe(
                host_name=host_name,
                device_id=device_id,  # Use logical device_id (device1, device2, host)
                incident_type=issue_type,
                consecutive_count=1,
                metadata=enhanced_metadata,
                device_name=device_name
            )
            
            if result.get('success'):
                alert_id = result.get('alert_id')
                logger.info(f"[{capture_folder}] DB INSERT SUCCESS: Created alert {alert_id}")
                return alert_id
            else:
                logger.error(f"[{capture_folder}] DB INSERT FAILED: {result.get('error')}")
                return None
            
        except Exception as e:
            logger.error(f"[{capture_folder}] DB ERROR: Failed to create {issue_type} incident: {e}")
            return None
    
    def resolve_incident(self, device_id, incident_id, issue_type, closure_metadata=None):
        """Resolve incident in DB with optional closure metadata (e.g., closure image URL)"""
        try:
            logger.info(f"[{device_id}] DB UPDATE: Resolving incident {incident_id}")
            
            # Use lazy import exactly as before
            _lazy_import_db()
            if not resolve_alert or resolve_alert is False:
                logger.warning(f"[{device_id}] Database module not available, skipping alert resolution")
                return False
            
            # Call database with closure metadata if provided
            result = resolve_alert(incident_id, closure_metadata=closure_metadata)
            
            if result.get('success'):
                if closure_metadata:
                    logger.info(f"[{device_id}] DB UPDATE SUCCESS: Resolved alert {incident_id} with closure data")
                else:
                    logger.info(f"[{device_id}] DB UPDATE SUCCESS: Resolved alert {incident_id}")
                return True
            else:
                logger.error(f"[{device_id}] DB UPDATE FAILED: {result.get('error')}")
                return False
            
        except Exception as e:
            logger.error(f"[{device_id}] DB ERROR: Failed to resolve incident {incident_id}: {e}")
            return False
    
    def process_detection(self, capture_folder, detection_result, host_name):
        """Process detection result and update state with 30-second delay before DB reporting
        
        Returns:
            dict: State transitions that occurred, e.g. {'freeze': 'first_detected', 'audio_loss': 'cleared'}
        """
        logger.debug(f"[{capture_folder}] process_detection called with result: {detection_result}")
        
        # Get device_id from capture_folder
        device_info = get_device_info_from_capture_folder(capture_folder)
        device_id = device_info.get('device_id', capture_folder)
        is_host = (device_id == 'host')
        
        logger.debug(f"[{capture_folder}] device_id={device_id}, is_host={is_host}")
        
        device_state = self.get_device_state(device_id)
        active_incidents = device_state['active_incidents']      # {issue_type: alert_id} - in DB
        pending_incidents = device_state['pending_incidents']    # {issue_type: timestamp} - not yet in DB
        
        logger.debug(f"[{capture_folder}] State: active={active_incidents}, pending={pending_incidents}")
        
        current_time = time.time()
        transitions = {}  # Track state changes for this detection
        
        # Determine issue types based on what's in detection_result
        issue_types = []
        if 'blackscreen' in detection_result:
            issue_types.append('blackscreen')
        if 'freeze' in detection_result:
            issue_types.append('freeze')
        if 'macroblocks' in detection_result:
            issue_types.append('macroblocks')
        if 'audio' in detection_result and not is_host:
            issue_types.append('audio_loss')
        
        # PRIORITY HANDLING: Blackscreen > Freeze > Macroblocks > Audio Loss
        # Priority 1: Blackscreen clears freeze, macroblocks, and audio_loss
        if detection_result.get('blackscreen', False):
            for suppressed_type in ['freeze', 'macroblocks', 'audio_loss']:
                if suppressed_type in active_incidents:
                    incident_id = active_incidents[suppressed_type]
                    logger.info(f"[{capture_folder}] 🔄 Blackscreen detected - auto-resolving active {suppressed_type} incident {incident_id}")
                    self.resolve_incident(device_id, incident_id, suppressed_type)
                    del active_incidents[suppressed_type]
                    if not active_incidents:
                        device_state['state'] = NORMAL
                    transitions[suppressed_type] = 'cleared_by_blackscreen'
                
                if suppressed_type in pending_incidents:
                    logger.debug(f"[{capture_folder}] Blackscreen detected - clearing pending {suppressed_type} incident")
                    del pending_incidents[suppressed_type]
                    transitions[suppressed_type] = 'cleared_by_blackscreen'
        
        # Priority 2: Freeze clears macroblocks and audio_loss
        if detection_result.get('freeze', False):
            for suppressed_type in ['macroblocks', 'audio_loss']:
                if suppressed_type in active_incidents:
                    incident_id = active_incidents[suppressed_type]
                    logger.info(f"[{capture_folder}] 🔄 Freeze detected - auto-resolving active {suppressed_type} incident {incident_id}")
                    self.resolve_incident(device_id, incident_id, suppressed_type)
                    del active_incidents[suppressed_type]
                    if not active_incidents:
                        device_state['state'] = NORMAL
                    transitions[suppressed_type] = 'cleared_by_freeze'
                
                if suppressed_type in pending_incidents:
                    logger.debug(f"[{capture_folder}] Freeze detected - clearing pending {suppressed_type} incident")
                    del pending_incidents[suppressed_type]
                    transitions[suppressed_type] = 'cleared_by_freeze'
        
        # Check each issue type
        logger.debug(f"[{capture_folder}] Checking issue types: {issue_types}")
        
        for issue_type in issue_types:
            if issue_type == 'audio_loss':
                is_detected = not detection_result.get('audio', True)
            else:
                is_detected = detection_result.get(issue_type, False)
            
            # SUPPRESSION: Don't create audio_loss if blackscreen or freeze is present
            if issue_type == 'audio_loss' and is_detected:
                has_blackscreen = detection_result.get('blackscreen', False)
                has_freeze = detection_result.get('freeze', False)
                if has_blackscreen or has_freeze:
                    logger.debug(f"[{capture_folder}] Suppressing audio_loss (blackscreen={has_blackscreen}, freeze={has_freeze})")
                    is_detected = False  # Override - don't create audio_loss incident
            
            is_in_db = issue_type in active_incidents
            is_pending = issue_type in pending_incidents
            
            logger.debug(f"[{capture_folder}] {issue_type}: detected={is_detected}, in_db={is_in_db}, pending={is_pending}")
            
            if is_detected:
                # Issue is currently detected
                if is_in_db:
                    # Already reported to DB, nothing to do
                    pass
                    
                elif is_pending:
                    # Check if it's been pending long enough to report to DB
                    first_detected_time = pending_incidents[issue_type]
                    elapsed_time = current_time - first_detected_time
                    
                    if elapsed_time >= self.INCIDENT_REPORT_DELAY:
                        # Issue has persisted for threshold duration, report to DB
                        logger.info(f"[{capture_folder}] ⏰ {issue_type} persisted for {elapsed_time:.1f}s, reporting to DB NOW")
                        
                        # ENSURE R2 images are uploaded BEFORE creating DB incident
                        # This handles case where INCIDENT_REPORT_DELAY < 5s (testing) or = 5s edge case
                        has_r2_images = 'r2_images' in detection_result and detection_result['r2_images']
                        
                        if not has_r2_images and issue_type in ['blackscreen', 'freeze', 'macroblocks', 'audio_loss']:
                            # Missing R2 images - upload them NOW before DB insert
                            logger.info(f"[{capture_folder}] Uploading {issue_type} start images to R2 before DB insert...")
                            from datetime import datetime
                            now = datetime.now()
                            time_key = f"{now.year}{now.month:02d}{now.day:02d}_{now.hour:02d}{now.minute:02d}{now.second:02d}"
                            
                            if issue_type == 'freeze':
                                # Upload 3 thumbnails for freeze (paths already in detection_result)
                                last_3_thumbnails = detection_result.get('last_3_thumbnails', [])
                                last_3_captures = detection_result.get('last_3_filenames', [])
                                if last_3_thumbnails:
                                    # Copy to cold first (freeze thumbnails may be in hot storage)
                                    from shared.src.lib.utils.storage_path_utils import copy_to_cold_storage
                                    cold_thumbnails = [copy_to_cold_storage(t) for t in last_3_thumbnails if t]
                                    cold_thumbnails = [t for t in cold_thumbnails if t]  # Remove None
                                    
                                    if cold_thumbnails:
                                        r2_urls = self.upload_freeze_frames_to_r2(
                                            last_3_captures, cold_thumbnails, capture_folder, time_key, thumbnails_only=True
                                        )
                                        if r2_urls and r2_urls.get('thumbnail_urls'):
                                            detection_result['r2_images'] = r2_urls
                                            has_r2_images = True
                                            logger.info(f"[{capture_folder}] ✅ Uploaded {len(r2_urls['thumbnail_urls'])} freeze thumbnails")
                            else:
                                # Upload single thumbnail for blackscreen/macroblocks/audio_loss from cold path
                                device_id = get_device_info_from_capture_folder(capture_folder).get('device_id', capture_folder)
                                device_state = self.get_device_state(device_id)
                                cold_thumbnail_path = device_state.get(f'{issue_type}_start_thumbnail_cold')
                                
                                if cold_thumbnail_path and os.path.exists(cold_thumbnail_path):
                                    r2_urls = self.upload_incident_frame_to_r2(
                                        cold_thumbnail_path, capture_folder, time_key, issue_type, 'start'
                                    )
                                    if r2_urls and r2_urls.get('thumbnail_url'):
                                        detection_result['r2_images'] = r2_urls
                                        has_r2_images = True
                                        logger.info(f"[{capture_folder}] ✅ Uploaded {issue_type} start thumbnail from cold")
                                else:
                                    logger.warning(f"[{capture_folder}] ⚠️  Cold thumbnail not found for {issue_type}: {cold_thumbnail_path}")
                        
                        # Log R2 image status
                        if has_r2_images:
                            if 'thumbnail_urls' in detection_result.get('r2_images', {}):
                                r2_count = len(detection_result['r2_images']['thumbnail_urls'])
                                logger.info(f"[{capture_folder}] ✅ {issue_type.upper()} incident has {r2_count} R2 thumbnail URLs")
                            elif 'thumbnail_url' in detection_result.get('r2_images', {}):
                                logger.info(f"[{capture_folder}] ✅ {issue_type.upper()} incident has start thumbnail: {detection_result['r2_images']['thumbnail_url']}")
                        else:
                            logger.debug(f"[{capture_folder}] {issue_type.upper()} incident has no R2 images (duration may be < 5s)")
                        
                        logger.info(f"[{capture_folder}] Calling create_incident for {issue_type}...")
                        incident_id = self.create_incident(capture_folder, issue_type, host_name, detection_result)
                        if incident_id:
                            active_incidents[issue_type] = incident_id
                            device_state['state'] = INCIDENT
                            # Remove from pending since it's now active
                            del pending_incidents[issue_type]
                            logger.info(f"[{capture_folder}] ✅ Incident {incident_id} created and moved to active")
                        else:
                            logger.error(f"[{capture_folder}] ❌ create_incident returned None - incident creation FAILED")
                    else:
                        # Still waiting for 5 minutes
                        remaining_time = self.INCIDENT_REPORT_DELAY - elapsed_time
                        if elapsed_time > 60:
                            logger.info(f"[{capture_folder}] {issue_type} still pending (elapsed={elapsed_time:.1f}s), waiting {remaining_time/60:.1f}min more before reporting")
                        else:
                            logger.debug(f"[{capture_folder}] {issue_type} still pending (elapsed={elapsed_time:.0f}s), waiting {remaining_time:.0f}s more before reporting")
                        
                else:
                    # First detection of this issue - check if it meets minimum duration threshold
                    # Only track incidents that last > 5 seconds (prevents false positives from glitches)
                    event_duration_ms = detection_result.get(f'{issue_type}_event_duration_ms', 0)
                    
                    # Skip tracking if duration < 5 seconds (still ramping up or brief glitch)
                    if event_duration_ms > 0 and event_duration_ms < 5000:
                        logger.debug(f"[{capture_folder}] {issue_type} detected but too short ({event_duration_ms/1000:.1f}s < 5s), not tracking")
                        continue
                    
                    # Add to pending for tracking
                    pending_incidents[issue_type] = current_time
                    transitions[issue_type] = 'first_detected'  # Mark transition
                    logger.info(f"[{capture_folder}] {issue_type} first detected, will report to DB if persists for {self.INCIDENT_REPORT_DELAY/60:.0f}min")
                    
            else:
                # Issue is NOT detected (cleared)
                if is_in_db:
                    # Issue was in DB, resolve it immediately
                    incident_id = active_incidents[issue_type]
                    transitions[issue_type] = 'cleared'  # Mark transition
                    logger.info(f"[{capture_folder}] {issue_type} cleared, resolving DB incident")
                    
                    # Get closure frame from device_state and upload it now
                    closure_metadata = None
                    closure_frame_key = f'{issue_type}_closure_frame'
                    
                    if closure_frame_key in device_state and device_state[closure_frame_key]:
                        # We have a closure frame stored - upload it now
                        closure_frame_path = device_state[closure_frame_key]
                        
                        # Get time_key from start image or use current timestamp (YYYYMMDD_HHMMSS)
                        from datetime import datetime
                        now = datetime.now()
                        
                        # Try to get time_key from existing r2_images (to match start image naming)
                        existing_r2_images = device_state.get(f'{issue_type}_r2_images', {})
                        time_key = existing_r2_images.get('time_key', f"{now.year}{now.month:02d}{now.day:02d}_{now.hour:02d}{now.minute:02d}{now.second:02d}")
                        
                        logger.info(f"[{capture_folder}] 📤 Uploading {issue_type.upper()} closure image to R2...")
                        
                        if issue_type == 'freeze':
                            # For freeze, we might want to upload the last 3 frames again as closure
                            # For now, skip closure for freeze (already has 3 comparison images)
                            logger.debug(f"[{capture_folder}] Freeze uses comparison images, skipping closure upload")
                        else:
                            # Upload closure for blackscreen/macroblocks
                            closure_r2 = self.upload_incident_frame_to_r2(
                                closure_frame_path, capture_folder, time_key, issue_type, 'end'
                            )
                            
                            if closure_r2 and closure_r2.get('thumbnail_url'):
                                # Merge closure into existing r2_images or create new
                                existing_r2_images = device_state.get(f'{issue_type}_r2_images', {})
                                existing_r2_images['closure_url'] = closure_r2['thumbnail_url']
                                existing_r2_images['closure_r2_path'] = closure_r2.get('thumbnail_r2_path')
                                closure_metadata = {'r2_images': existing_r2_images}
                                logger.info(f"[{capture_folder}] ✅ {issue_type.upper()} closure uploaded: {closure_r2['thumbnail_url']}")
                        
                        # Clean up closure frame from device_state
                        del device_state[closure_frame_key]
                        if f'{issue_type}_closure_filename' in device_state:
                            del device_state[f'{issue_type}_closure_filename']
                    
                    self.resolve_incident(device_id, incident_id, issue_type, closure_metadata=closure_metadata)
                    del active_incidents[issue_type]
                    
                    if not active_incidents:
                        device_state['state'] = NORMAL
                        
                elif is_pending:
                    # Issue was pending but cleared before reaching threshold
                    elapsed_time = current_time - pending_incidents[issue_type]
                    transitions[issue_type] = 'cleared'  # Mark transition
                    
                    # Cleanup: Remove cold copy for visual incidents (won't be uploaded to R2)
                    if issue_type in ['blackscreen', 'macroblocks', 'audio_loss']:
                        cold_path_key = f'{issue_type}_start_thumbnail_cold'
                        if cold_path_key in device_state:
                            cold_path = device_state[cold_path_key]
                            if cold_path and os.path.exists(cold_path):
                                try:
                                    os.remove(cold_path)
                                    logger.debug(f"[{capture_folder}] Cleaned up {issue_type} cold thumbnail (cleared before {self.INCIDENT_REPORT_DELAY}s)")
                                except:
                                    pass
                            del device_state[cold_path_key]
                    
                    del pending_incidents[issue_type]
        
        return transitions  # Return all transitions that occurred

    def upload_freeze_frames_to_r2(self, last_3_filenames, last_3_thumbnails=None, device_id=None, time_key=None, thumbnails_only=False):
        """Upload freeze incident frames to R2 storage with unique timestamp-based naming
        
        Args:
            last_3_filenames: List of capture image paths
            last_3_thumbnails: List of pre-generated thumbnail paths (from FFmpeg)
            device_id: Device identifier (capture folder name)
            time_key: Unique timestamp key (e.g., "20251012_183705" for 2025-10-12 18:37:05)
            thumbnails_only: If True, only upload thumbnails. Default False
        """
        try:
            # Import utilities
            from shared.src.lib.utils.cloudflare_utils import get_cloudflare_utils
            
            uploader = get_cloudflare_utils()
            if not uploader:
                logger.warning(f"[{device_id}] R2 uploader not available, skipping frame upload")
                return None
            
            # Create R2 folder path: alerts/freeze/{capture_folder}/{YYYYMMDD_HHMMSS}_thumb_{i}.jpg
            # Unique naming ensures no overwrites across different incidents
            base_r2_path = f"alerts/freeze/{device_id}"
            
            r2_results = {
                'original_urls': [],
                'thumbnail_urls': [],
                'original_r2_paths': [],
                'thumbnail_r2_paths': [],
                'time_key': time_key
            }
            
            # Upload original frames (last 3) - SKIP if thumbnails_only
            if not thumbnails_only:
                logger.info(f"[{device_id}] R2 upload started for {len(last_3_filenames)} frames")
                
                for i, filename in enumerate(last_3_filenames):
                    if not filename or not os.path.exists(filename):
                        logger.warning(f"[{device_id}] Original frame file not found: {filename}")
                        continue
                    
                    # R2 path: alerts/freeze/capture2/20251012_183705_frame_0.jpg
                    r2_path = f"{base_r2_path}/{time_key}_frame_{i}.jpg"
                    
                    file_mappings = [{'local_path': filename, 'remote_path': r2_path}]
                    upload_result = uploader.upload_files(file_mappings)
                    
                    # Convert to single file result
                    if upload_result['uploaded_files']:
                        upload_result = {
                            'success': True,
                            'url': upload_result['uploaded_files'][0]['url']
                        }
                    else:
                        upload_result = {'success': False}
                    if upload_result.get('success'):
                        r2_results['original_urls'].append(upload_result['url'])
                        r2_results['original_r2_paths'].append(r2_path)
                        logger.info(f"[{device_id}] Uploaded original frame {i}: {r2_path}")
                    else:
                        logger.error(f"[{device_id}] Failed to upload original frame {i}: {upload_result.get('error')}")
            
            # Upload pre-generated thumbnails from FFmpeg
            if last_3_thumbnails:
                logger.info(f"[{device_id}] R2 upload started for {len(last_3_thumbnails)} thumbnails")
                
                for i, thumbnail_path in enumerate(last_3_thumbnails):
                    if not thumbnail_path or not os.path.exists(thumbnail_path):
                        logger.warning(f"[{device_id}] Thumbnail file not found: {thumbnail_path}")
                        continue
                    
                    # R2 path: alerts/freeze/capture2/20251012_183705_thumb_0.jpg
                    r2_path = f"{base_r2_path}/{time_key}_thumb_{i}.jpg"
                    
                    file_mappings = [{'local_path': thumbnail_path, 'remote_path': r2_path}]
                    upload_result = uploader.upload_files(file_mappings)
                    
                    # Convert to single file result
                    if upload_result['uploaded_files']:
                        upload_result = {
                            'success': True,
                            'url': upload_result['uploaded_files'][0]['url']
                        }
                    else:
                        upload_result = {'success': False}
                    
                    if upload_result.get('success'):
                        r2_results['thumbnail_urls'].append(upload_result['url'])
                        r2_results['thumbnail_r2_paths'].append(r2_path)
                        logger.info(f"[{device_id}] Uploaded thumbnail {i}: {r2_path}")
                    else:
                        logger.error(f"[{device_id}] Failed to upload thumbnail {i}: {upload_result.get('error')}")
            else:
                logger.warning(f"[{device_id}] No thumbnails provided for upload")
            
            # Log completion results
            if r2_results['original_urls'] or r2_results['thumbnail_urls']:
                logger.info(f"[{device_id}] R2 upload completed: {len(r2_results['original_urls'])} originals, {len(r2_results['thumbnail_urls'])} thumbnails")
                return r2_results
            else:
                logger.warning(f"[{device_id}] R2 upload completed with no successful uploads")
                return None
                
        except Exception as e:
            logger.error(f"[{device_id}] Error in R2 upload: {e}")
            return None
    
    def _delete_r2_freeze_images(self, freeze_r2_images, capture_folder):
        """
        Delete orphaned freeze images from R2 when freeze is discarded (< 5min).
        Called when freeze ends before reaching the 5-minute reporting threshold.
        
        Args:
            freeze_r2_images: Dict with 'original_r2_paths' and 'thumbnail_r2_paths'
            capture_folder: Device capture folder name for logging
        """
        try:
            from shared.src.lib.utils.cloudflare_utils import get_cloudflare_utils
            
            uploader = get_cloudflare_utils()
            if not uploader:
                logger.warning(f"[{capture_folder}] R2 uploader not available, cannot delete orphaned images")
                return
            
            # Collect all R2 paths to delete
            paths_to_delete = []
            if 'original_r2_paths' in freeze_r2_images:
                paths_to_delete.extend(freeze_r2_images['original_r2_paths'])
            if 'thumbnail_r2_paths' in freeze_r2_images:
                paths_to_delete.extend(freeze_r2_images['thumbnail_r2_paths'])
            
            if not paths_to_delete:
                logger.debug(f"[{capture_folder}] No R2 paths to delete for discarded freeze")
                return
            
            # Delete each file from R2
            deleted_count = 0
            failed_count = 0
            deleted_files = []
            for r2_path in paths_to_delete:
                if uploader.delete_file(r2_path):
                    deleted_count += 1
                    deleted_files.append(os.path.basename(r2_path))
                else:
                    failed_count += 1
            
            # Single-line log with file names
            if deleted_count > 0 or failed_count > 0:
                files_str = ', '.join(deleted_files) if deleted_files else 'none'
                status = f"✅ {deleted_count}" if failed_count == 0 else f"✅ {deleted_count}, ❌ {failed_count}"
                logger.info(f"[{capture_folder}] 🗑️  R2 cleanup (freeze < 5min): {status} | Files: {files_str}")
                
        except Exception as e:
            logger.error(f"[{capture_folder}] Error deleting R2 freeze images: {e}")
    
    def upload_incident_frame_to_r2(self, thumbnail_path, device_id, time_key, incident_type, stage='start'):
        """Upload single incident frame to R2 storage (for blackscreen/macroblocks)
        
        Args:
            thumbnail_path: Path to thumbnail image
            device_id: Device identifier (capture folder name)
            time_key: Unique timestamp key (e.g., "20251012_183705" for 2025-10-12 18:37:05)
            incident_type: Type of incident ('blackscreen', 'macroblocks')
            stage: 'start' or 'end' for naming
        
        Returns:
            Dict with thumbnail_url and r2_path, or None if failed
        """
        try:
            from shared.src.lib.utils.cloudflare_utils import get_cloudflare_utils
            
            uploader = get_cloudflare_utils()
            if not uploader:
                logger.warning(f"[{device_id}] R2 uploader not available, skipping {incident_type} frame upload")
                return None
            
            # R2 path: alerts/{incident_type}/{capture_folder}/{YYYYMMDD_HHMMSS}_{stage}.jpg
            # e.g., alerts/blackscreen/capture1/20251012_183705_start.jpg, alerts/blackscreen/capture1/20251012_183705_end.jpg
            r2_path = f"alerts/{incident_type}/{device_id}/{time_key}_{stage}.jpg"
            
            if not os.path.exists(thumbnail_path):
                logger.warning(f"[{device_id}] Thumbnail not found: {thumbnail_path}")
                return None
            
            file_mappings = [{'local_path': thumbnail_path, 'remote_path': r2_path}]
            upload_result = uploader.upload_files(file_mappings)
            
            # Convert to single file result
            if upload_result['uploaded_files']:
                thumbnail_url = upload_result['uploaded_files'][0]['url']
                return {
                    'thumbnail_url': thumbnail_url,
                    'thumbnail_r2_path': r2_path,
                    'time_key': time_key,
                    'stage': stage
                }
            else:
                logger.error(f"[{device_id}] Failed to upload {incident_type} {stage} thumbnail")
                return None
                
        except Exception as e:
            logger.error(f"[{device_id}] Error uploading {incident_type} frame to R2: {e}")
            return None
    
    def _delete_r2_incident_images(self, r2_images, capture_folder, incident_type):
        """Delete orphaned incident images from R2 (generic for any incident type)
        
        Args:
            r2_images: Dict with R2 paths (thumbnail_r2_path, closure_r2_path, etc)
            capture_folder: Device capture folder name for logging
            incident_type: Type of incident for logging
        """
        try:
            from shared.src.lib.utils.cloudflare_utils import get_cloudflare_utils
            
            uploader = get_cloudflare_utils()
            if not uploader:
                logger.warning(f"[{capture_folder}] R2 uploader not available, cannot delete orphaned {incident_type} images")
                return
            
            # Collect all R2 paths to delete
            paths_to_delete = []
            if 'thumbnail_r2_path' in r2_images:
                paths_to_delete.append(r2_images['thumbnail_r2_path'])
            if 'closure_r2_path' in r2_images:
                paths_to_delete.append(r2_images['closure_r2_path'])
            
            if not paths_to_delete:
                logger.debug(f"[{capture_folder}] No R2 paths to delete for discarded {incident_type}")
                return
            
            # Delete each file from R2
            deleted_count = 0
            failed_count = 0
            deleted_files = []
            for r2_path in paths_to_delete:
                if uploader.delete_file(r2_path):
                    deleted_count += 1
                    deleted_files.append(os.path.basename(r2_path))
                else:
                    failed_count += 1
            
            # Single-line log with file names
            if deleted_count > 0 or failed_count > 0:
                files_str = ', '.join(deleted_files) if deleted_files else 'none'
                status = f"✅ {deleted_count}" if failed_count == 0 else f"✅ {deleted_count}, ❌ {failed_count}"
                logger.info(f"[{capture_folder}] 🗑️  R2 cleanup ({incident_type} < 5min): {status} | Files: {files_str}")
                
        except Exception as e:
            logger.error(f"[{capture_folder}] Error deleting R2 {incident_type} images: {e}")