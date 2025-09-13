#!/usr/bin/env python3
"""
Simple incident manager - state machine + DB operations
Single thread, minimal complexity
"""
import os
import sys
import logging
from datetime import datetime

# Add project paths
current_dir = os.path.dirname(os.path.abspath(__file__))  # backend_host/scripts/
backend_host_dir = os.path.dirname(current_dir)           # backend_host/
project_root = os.path.dirname(backend_host_dir)          # project root

sys.path.insert(0, project_root)

# Load environment variables from .env
try:
    from dotenv import load_dotenv
    env_root_path = os.path.join(project_root, '.env')
    
    if os.path.exists(env_root_path):
        load_dotenv(env_root_path)
        print(f"[@incident_manager] Loaded environment from {env_root_path}")
    else:
        print(f"[@incident_manager] Warning: .env not found at {env_root_path}")
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
            from shared.lib.supabase.alerts_db import create_alert_safe as _create_alert_safe, resolve_alert as _resolve_alert
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
        self.device_states = {}  # {device_id: {state: int, active_incidents: {type: incident_id}}}
        
    def get_device_state(self, device_id):
        """Get current state for device"""
        if device_id not in self.device_states:
            self.device_states[device_id] = {
                'state': NORMAL,
                'active_incidents': {}
            }
        return self.device_states[device_id]
    
    def get_device_info_from_capture_folder(self, capture_folder):
        """Get device info from .env by matching capture path"""
        import os
        capture_path = f"/var/www/html/stream/{capture_folder}"
        
        # Check HOST first
        if os.getenv('HOST_VIDEO_CAPTURE_PATH') == capture_path:
            host_name = os.getenv('HOST_NAME', 'unknown')
            return {
                'device_name': f"{host_name}_Host",
                'stream_path': os.getenv('HOST_VIDEO_STREAM_PATH'),
                'capture_path': os.getenv('HOST_VIDEO_CAPTURE_PATH')
            }
        
        # Check DEVICE1-4
        for i in range(1, 5):
            if os.getenv(f'DEVICE{i}_VIDEO_CAPTURE_PATH') == capture_path:
                return {
                    'device_name': os.getenv(f'DEVICE{i}_NAME', f'device{i}'),
                    'stream_path': os.getenv(f'DEVICE{i}_VIDEO_STREAM_PATH'),
                    'capture_path': os.getenv(f'DEVICE{i}_VIDEO_CAPTURE_PATH')
                }
        
        return {'device_name': capture_folder, 'stream_path': None, 'capture_path': None}
    
    def create_incident(self, device_id, capture_folder, issue_type, host_name, analysis_result=None):
        """Create new incident in DB using original working method"""
        try:
            logger.info(f"[{device_id}] DB INSERT: Creating {issue_type} incident")
            
            # Get device info from .env by matching capture folder
            device_info = self.get_device_info_from_capture_folder(capture_folder)
            device_name = device_info['device_name']
            
            # Use lazy import exactly as before
            _lazy_import_db()
            if not create_alert_safe or create_alert_safe is False:
                logger.warning("Database module not available, skipping alert creation")
                return None
            
            # Prepare enhanced metadata with all details
            enhanced_metadata = {
                'stream_path': device_info['stream_path'],
                'capture_path': device_info['capture_path']
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
                
                # Add frame information for incidents (SAME AS ORIGINAL)
                last_3_filenames = analysis_result.get('last_3_filenames', [])
                last_3_thumbnails = analysis_result.get('last_3_thumbnails', [])
                enhanced_metadata['last_3_filenames'] = last_3_filenames
                enhanced_metadata['last_3_thumbnails'] = last_3_thumbnails
                
                # Upload frames to R2 for all incident types (SAME AS ORIGINAL)
                if last_3_filenames:
                    from datetime import datetime
                    current_time = datetime.now().isoformat()
                    r2_urls = self.upload_freeze_frames_to_r2(last_3_filenames, last_3_thumbnails, device_id, current_time)
                    if r2_urls:
                        enhanced_metadata['r2_images'] = r2_urls
            
            # Call database exactly as before
            result = create_alert_safe(
                host_name=host_name,
                device_id=device_id,
                incident_type=issue_type,
                consecutive_count=1,  # Always start with 1
                metadata=enhanced_metadata,  # NOW WITH RICH DATA AND IMAGES!
                device_name=device_name  # Add device_name like metrics system
            )
            
            if result.get('success'):
                alert_id = result.get('alert_id')
                logger.info(f"[{device_id}] DB INSERT SUCCESS: Created alert {alert_id}")
                return alert_id
            else:
                logger.error(f"[{device_id}] DB INSERT FAILED: {result.get('error')}")
                return None
            
        except Exception as e:
            logger.error(f"[{device_id}] DB ERROR: Failed to create {issue_type} incident: {e}")
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
    
    def process_detection(self, device_id, capture_folder, detection_result, host_name):
        """Process detection result and update state"""
        device_state = self.get_device_state(device_id)
        active_incidents = device_state['active_incidents']
        
        # Check each issue type
        for issue_type in ['blackscreen', 'freeze', 'audio_loss']:
            if issue_type == 'audio_loss':
                is_detected = not detection_result.get('audio', True)
            else:
                is_detected = detection_result.get(issue_type, False)
            was_active = issue_type in active_incidents
            
            if is_detected and not was_active:
                incident_id = self.create_incident(device_id, capture_folder, issue_type, host_name, detection_result)
                if incident_id:
                    active_incidents[issue_type] = incident_id
                    device_state['state'] = INCIDENT
                    
            elif not is_detected and was_active:
                incident_id = active_incidents[issue_type]
                self.resolve_incident(device_id, incident_id, issue_type)
                del active_incidents[issue_type]
                
                if not active_incidents:
                    device_state['state'] = NORMAL

    def upload_freeze_frames_to_r2(self, last_3_filenames, last_3_thumbnails, device_id, timestamp):
        """Upload freeze incident frames to R2 storage - EXACT COPY FROM ORIGINAL"""
        try:
            # Import R2 utilities (from shared library) - EXACT COPY
            from shared.lib.utils.cloudflare_utils import get_cloudflare_utils
            
            uploader = get_cloudflare_utils()
            if not uploader:
                logger.warning("R2 uploader not available, skipping frame upload")
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
            
            logger.info(f"[{device_id}] Uploading freeze frames to R2 at {timestamp}")
            
            # Upload original frames (last 3)
            for i, filename in enumerate(last_3_filenames):
                if not filename or not os.path.exists(filename):
                    logger.warning(f"Original frame file not found: {filename}")
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
                    logger.warning(f"Thumbnail file not found: {thumbnail_path}")
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
                    logger.info(f"Uploaded thumbnail {i}: {r2_path}")
                else:
                    logger.error(f"Failed to upload thumbnail {i}: {upload_result.get('error')}")
            
            # Return results if we uploaded at least some files
            if r2_results['original_urls'] or r2_results['thumbnail_urls']:
                logger.info(f"Successfully uploaded {len(r2_results['original_urls'])} originals and {len(r2_results['thumbnail_urls'])} thumbnails to R2")
                return r2_results
            else:
                logger.warning("No files were successfully uploaded to R2")
                return None
                
        except Exception as e:
            logger.error(f"Error uploading freeze frames to R2: {e}")
            return None
