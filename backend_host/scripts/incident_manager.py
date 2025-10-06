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
    def __init__(self):
        self.device_states = {}  # {device_id: {state: int, active_incidents: {type: incident_id}, pending_incidents: {type: timestamp}}}
        self.INCIDENT_REPORT_DELAY = 300  # Only report to DB after 5 minutes of continuous detection
        # Start fresh on service restart - resolve any stale incidents from previous run
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
            if analysis_result:
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
                if 'last_3_thumbnails' in analysis_result:
                    enhanced_metadata['last_3_thumbnails'] = analysis_result['last_3_thumbnails']
                if 'r2_images' in analysis_result:
                    enhanced_metadata['r2_images'] = analysis_result['r2_images']
            
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
    
    def resolve_incident(self, device_id, incident_id, issue_type):
        """Resolve incident in DB using original working method"""
        try:
            logger.info(f"[{device_id}] DB UPDATE: Resolving incident {incident_id}")
            
            # Use lazy import exactly as before
            _lazy_import_db()
            if not resolve_alert or resolve_alert is False:
                logger.warning(f"[{device_id}] Database module not available, skipping alert resolution")
                return False
            
            # Call database exactly as before
            result = resolve_alert(incident_id)
            
            if result.get('success'):
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
        
        # Skip audio_loss for host device (no audio capture)
        issue_types = ['blackscreen', 'freeze']
        if not is_host:
            issue_types.append('audio_loss')
        
        # Check each issue type
        logger.debug(f"[{capture_folder}] Checking issue types: {issue_types}")
        
        for issue_type in issue_types:
            if issue_type == 'audio_loss':
                is_detected = not detection_result.get('audio', True)
            else:
                is_detected = detection_result.get(issue_type, False)
            
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
                    
                    logger.info(f"[{capture_folder}] {issue_type} still pending: elapsed={elapsed_time:.1f}s, threshold={self.INCIDENT_REPORT_DELAY}s, will_report={elapsed_time >= self.INCIDENT_REPORT_DELAY}")
                    
                    if elapsed_time >= self.INCIDENT_REPORT_DELAY:
                        # Issue has persisted for 5+ minutes, report to DB
                        logger.info(f"[{capture_folder}] ⏰ {issue_type} persisted for {elapsed_time/60:.1f}min, reporting to DB NOW")
                        
                        # DON'T upload again - freeze thumbnails already uploaded immediately when first detected
                        # r2_images should already be in detection_result from capture_monitor
                        logger.info(f"[{capture_folder}] Using r2_images from initial freeze detection (no duplicate upload)")
                        
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
                            logger.info(f"[{capture_folder}] {issue_type} detected, waiting {remaining_time/60:.1f}min more before reporting")
                        else:
                            logger.debug(f"[{capture_folder}] {issue_type} detected, waiting {remaining_time:.0f}s more before reporting")
                        
                else:
                    # First detection of this issue, add to pending
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
                    self.resolve_incident(device_id, incident_id, issue_type)
                    del active_incidents[issue_type]
                    
                    # Clear cached R2 URLs for freeze when it ends
                    if issue_type == 'freeze':
                        device_state.pop('freeze_r2_urls', None)
                        device_state.pop('freeze_r2_images', None)
                        logger.debug(f"[{capture_folder}] Cleared freeze R2 URL cache")
                    
                    if not active_incidents:
                        device_state['state'] = NORMAL
                        
                elif is_pending:
                    # Issue was pending but cleared before reaching 5min threshold
                    elapsed_time = current_time - pending_incidents[issue_type]
                    transitions[issue_type] = 'cleared'  # Mark transition
                    if elapsed_time >= 60:
                        logger.info(f"[{capture_folder}] {issue_type} cleared after {elapsed_time/60:.1f}min (never reported to DB)")
                    else:
                        logger.info(f"[{capture_folder}] {issue_type} cleared after {elapsed_time:.1f}s (never reported to DB)")
                    del pending_incidents[issue_type]
                    
                    # Clear cached R2 URLs for freeze when it ends
                    if issue_type == 'freeze':
                        device_state.pop('freeze_r2_urls', None)
                        device_state.pop('freeze_r2_images', None)
                        logger.debug(f"[{capture_folder}] Cleared freeze R2 URL cache")
        
        return transitions  # Return all transitions that occurred

    def upload_freeze_frames_to_r2(self, last_3_filenames, last_3_thumbnails=None, device_id=None, time_key=None, thumbnails_only=False):
        """Upload freeze incident frames to R2 storage with HHMM-based naming
        
        Args:
            last_3_filenames: List of capture image paths
            last_3_thumbnails: List of pre-generated thumbnail paths (from FFmpeg)
            device_id: Device identifier (capture folder name)
            time_key: HHMM time key (e.g., "1300" for 13:00)
            thumbnails_only: If True, only upload thumbnails. Default False
        """
        try:
            # Import utilities
            from shared.src.lib.utils.cloudflare_utils import get_cloudflare_utils
            
            uploader = get_cloudflare_utils()
            if not uploader:
                logger.warning(f"[{device_id}] R2 uploader not available, skipping frame upload")
                return None
            
            # Create R2 folder path: alerts/freeze/{capture_folder}/{HHMM}_thumb_{i}.jpg
            # Simple, predictable naming that frontend can construct from any timestamp
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
                    
                    # R2 path: alerts/freeze/capture2/1300_frame_0.jpg
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
                    
                    # R2 path: alerts/freeze/capture2/1300_thumb_0.jpg
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
