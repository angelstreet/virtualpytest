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

# Add project paths
current_dir = os.path.dirname(os.path.abspath(__file__))  # backend_host/scripts/
backend_host_dir = os.path.dirname(current_dir)           # backend_host/
project_root = os.path.dirname(backend_host_dir)          # project root

sys.path.insert(0, project_root)

# Load environment variables from BOTH .env files
try:
    from dotenv import load_dotenv
    
    # Load project root .env first (database, R2, etc.)
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
        self.device_mapping_cache = {}  # Cache device mappings to avoid repeated lookups
        self.INCIDENT_REPORT_DELAY = 300  # Only report to DB after 5 minutes of continuous detection
        self._load_active_incidents_from_db()
        
    def get_device_state(self, device_id):
        """Get current state for device"""
        if device_id not in self.device_states:
            self.device_states[device_id] = {
                'state': NORMAL,
                'active_incidents': {},  # {issue_type: alert_id} - incidents in DB
                'pending_incidents': {}  # {issue_type: first_detected_timestamp} - not yet in DB
            }
        return self.device_states[device_id]
    
    def _load_active_incidents_from_db(self):
        """Load all active incidents from database to initialize state"""
        try:
            logger.info("[@incident_manager] Loading active incidents from database...")
            
            # Use lazy import to get database functions
            _lazy_import_db()
            if not create_alert_safe or create_alert_safe is False:
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
            logger.info(f"[@incident_manager] Found {len(active_alerts)} active incidents in database")
            
            # Process each active alert and populate device_states
            for alert in active_alerts:
                host_name = alert.get('host_name')
                device_id = alert.get('device_id')
                incident_type = alert.get('incident_type')
                alert_id = alert.get('id')
                
                if not all([host_name, device_id, incident_type, alert_id]):
                    logger.warning(f"[@incident_manager] Skipping incomplete alert: {alert}")
                    continue
                
                # Use device_id directly as the key for our local state
                device_state = self.get_device_state(device_id)
                
                # Add the active incident to our state
                device_state['active_incidents'][incident_type] = alert_id
                device_state['state'] = INCIDENT
                
                logger.info(f"[@incident_manager] Loaded active incident: {device_id} -> {incident_type} (alert_id: {alert_id})")
            
            logger.info(f"[@incident_manager] Successfully initialized state with {len(active_alerts)} active incidents")
            
        except Exception as e:
            logger.error(f"[@incident_manager] Error loading active incidents from database: {e}")
            # Continue with empty state - don't crash the service
    
    def cleanup_orphaned_incidents(self, monitored_capture_folders, host_name):
        """Auto-resolve incidents for capture folders that are no longer being monitored"""
        try:
            logger.info(f"[@incident_manager] Cleaning up orphaned incidents for unmonitored capture folders...")
            
            # Get list of device_ids we're currently monitoring
            monitored_device_ids = set()
            for capture_folder in monitored_capture_folders:
                device_info = self.get_device_info_from_capture_folder(capture_folder)
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
    
    def get_device_info_from_capture_folder(self, capture_folder):
        """Get device info from .env by matching capture path - with caching to reduce log spam"""
        # Check cache first
        if capture_folder in self.device_mapping_cache:
            return self.device_mapping_cache[capture_folder]
        
        import os
        capture_path = f"/var/www/html/stream/{capture_folder}"
        
        logger.debug(f"[{capture_folder}] Performing device mapping lookup for capture_folder='{capture_folder}'")
        
        # Check HOST first
        host_capture_path = os.getenv('HOST_VIDEO_CAPTURE_PATH')
        
        if host_capture_path == capture_path:
            host_name = os.getenv('HOST_NAME', 'unknown')
            host_stream_path = os.getenv('HOST_VIDEO_STREAM_PATH')
            device_info = {
                'device_id': 'host',
                'device_name': f"{host_name}_Host",
                'stream_path': host_stream_path,
                'capture_path': capture_folder
            }
            logger.info(f"[{capture_folder}] Mapped to HOST device: {host_name}_Host")
            self.device_mapping_cache[capture_folder] = device_info
            return device_info
        
        # Check DEVICE1-4
        for i in range(1, 5):
            device_capture_path = os.getenv(f'DEVICE{i}_VIDEO_CAPTURE_PATH')
            device_name = os.getenv(f'DEVICE{i}_NAME', f'device{i}')
            device_stream_path = os.getenv(f'DEVICE{i}_VIDEO_STREAM_PATH')
            
            if device_capture_path == capture_path:
                device_info = {
                    'device_id': f'device{i}',
                    'device_name': device_name,
                    'stream_path': device_stream_path,
                    'capture_path': capture_folder
                }
                logger.info(f"[{capture_folder}] Mapped to DEVICE{i}: {device_name}")
                self.device_mapping_cache[capture_folder] = device_info
                return device_info
        
        # Fallback
        logger.warning(f"[{capture_folder}] No device mapping found, using capture_folder as fallback")
        device_info = {'device_id': capture_folder, 'device_name': capture_folder, 'stream_path': None, 'capture_path': capture_folder}
        self.device_mapping_cache[capture_folder] = device_info
        return device_info
    
    def create_incident(self, capture_folder, issue_type, host_name, analysis_result=None):
        """Create new incident in DB using original working method"""
        try:
            logger.info(f"[{capture_folder}] DB INSERT: Creating {issue_type} incident")
            
            # Get device info from .env by matching capture folder
            device_info = self.get_device_info_from_capture_folder(capture_folder)
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
        """Process detection result and update state with 30-second delay before DB reporting"""
        # Get device_id from capture_folder
        device_info = self.get_device_info_from_capture_folder(capture_folder)
        device_id = device_info.get('device_id', capture_folder)
        
        device_state = self.get_device_state(device_id)
        active_incidents = device_state['active_incidents']      # {issue_type: alert_id} - in DB
        pending_incidents = device_state['pending_incidents']    # {issue_type: timestamp} - not yet in DB
        
        current_time = time.time()
        
        # Check each issue type
        for issue_type in ['blackscreen', 'freeze', 'audio_loss']:
            if issue_type == 'audio_loss':
                is_detected = not detection_result.get('audio', True)
            else:
                is_detected = detection_result.get(issue_type, False)
            
            is_in_db = issue_type in active_incidents
            is_pending = issue_type in pending_incidents
            
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
                        # Issue has persisted for 5+ minutes, report to DB
                        logger.info(f"[{capture_folder}] {issue_type} persisted for {elapsed_time/60:.1f}min, reporting to DB")
                        incident_id = self.create_incident(capture_folder, issue_type, host_name, detection_result)
                        if incident_id:
                            active_incidents[issue_type] = incident_id
                            device_state['state'] = INCIDENT
                            # Remove from pending since it's now active
                            del pending_incidents[issue_type]
                    else:
                        # Still waiting for 5 minutes
                        remaining_time = self.INCIDENT_REPORT_DELAY - elapsed_time
                        logger.debug(f"[{capture_folder}] {issue_type} detected, waiting {remaining_time/60:.1f}min more before reporting")
                        
                else:
                    # First detection of this issue, add to pending
                    pending_incidents[issue_type] = current_time
                    logger.info(f"[{capture_folder}] {issue_type} first detected, will report to DB if persists for {self.INCIDENT_REPORT_DELAY/60:.0f}min")
                    
            else:
                # Issue is NOT detected (cleared)
                if is_in_db:
                    # Issue was in DB, resolve it immediately
                    incident_id = active_incidents[issue_type]
                    logger.info(f"[{capture_folder}] {issue_type} cleared, resolving DB incident")
                    self.resolve_incident(device_id, incident_id, issue_type)
                    del active_incidents[issue_type]
                    
                    if not active_incidents:
                        device_state['state'] = NORMAL
                        
                elif is_pending:
                    # Issue was pending but cleared before reaching 5min threshold
                    elapsed_time = current_time - pending_incidents[issue_type]
                    if elapsed_time >= 60:
                        logger.info(f"[{capture_folder}] {issue_type} cleared after {elapsed_time/60:.1f}min (never reported to DB)")
                    else:
                        logger.info(f"[{capture_folder}] {issue_type} cleared after {elapsed_time:.1f}s (never reported to DB)")
                    del pending_incidents[issue_type]

    def upload_freeze_frames_to_r2(self, last_3_filenames, last_3_thumbnails, device_id, timestamp):
        """Upload freeze incident frames to R2 storage - SYNCHRONOUS to ensure URLs are in DB"""
        try:
            # Import R2 utilities (from shared library)
            from shared.src.lib.utils.cloudflare_utils import get_cloudflare_utils
            
            uploader = get_cloudflare_utils()
            if not uploader:
                logger.warning(f"[{device_id}] R2 uploader not available, skipping frame upload")
                return None
            
            # Create R2 folder path for this incident: alerts/freeze/{device_id}/{timestamp}/
            timestamp_str = timestamp.replace(':', '').replace('-', '').replace('T', '').replace('.', '')[:14]
            base_r2_path = f"alerts/freeze/{device_id}/{timestamp_str}"
            
            r2_results = {
                'original_urls': [],
                'thumbnail_urls': [],
                'original_r2_paths': [],
                'thumbnail_r2_paths': [],
                'timestamp': timestamp
            }
            
            logger.info(f"[{device_id}] R2 upload started for {len(last_3_filenames)} frames")
            
            # Upload original frames (last 3)
            for i, filename in enumerate(last_3_filenames):
                if not filename or not os.path.exists(filename):
                    logger.warning(f"[{device_id}] Original frame file not found: {filename}")
                    continue
                
                # R2 path: alerts/freeze/device1/20250124123456/frame_0.jpg
                r2_path = f"{base_r2_path}/frame_{i}.jpg"
                
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
            
            # Upload thumbnail frames (last 3)
            for i, thumbnail_filename in enumerate(last_3_thumbnails):
                if not thumbnail_filename:
                    continue
                    
                # Construct full path if needed
                if not os.path.isabs(thumbnail_filename):
                    # Assume thumbnails are in same directory as originals
                    if last_3_filenames and i < len(last_3_filenames):
                        original_dir = os.path.dirname(last_3_filenames[i])
                        thumbnail_path = os.path.join(original_dir, thumbnail_filename)
                    else:
                        continue
                else:
                    thumbnail_path = thumbnail_filename
                
                if not os.path.exists(thumbnail_path):
                    logger.warning(f"[{device_id}] Thumbnail file not found: {thumbnail_path}")
                    continue
                
                # R2 path: alerts/freeze/device1/20250124123456/thumb_0.jpg
                r2_path = f"{base_r2_path}/thumb_{i}.jpg"
                
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
