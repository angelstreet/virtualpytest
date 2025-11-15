"""
Heatmap Processor Service

Continuous background service that generates heatmap mosaics every minute.
Uses circular buffer with HHMM naming (1440 fixed files).
"""

import sys
import os

# Add project root to path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(CURRENT_DIR))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Apply global typing compatibility early to fix third-party package issues
try:
    from shared.src.lib.utils.typing_compatibility import ensure_typing_compatibility
    ensure_typing_compatibility()
except ImportError:
    print("⚠️  Warning: Could not apply typing compatibility fix")

# Now import everything else after typing fix
import time
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from PIL import Image
import io
import math
from concurrent.futures import ThreadPoolExecutor, as_completed

from shared.src.lib.utils.cloudflare_utils import get_cloudflare_utils

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    project_env_path = os.path.join(PROJECT_ROOT, '.env')
    if os.path.exists(project_env_path):
        load_dotenv(project_env_path)
        print(f"[@heatmap_processor] Loaded environment from {project_env_path}")
        print(f"[@heatmap_processor] SERVER_URL={os.getenv('SERVER_URL')}")
    else:
        print(f"[@heatmap_processor] Warning: .env not found at {project_env_path}")
except ImportError:
    print("[@heatmap_processor] Warning: python-dotenv not installed")

# Setup logging to /tmp/heatmap.log
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('/tmp/heatmap.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def cleanup_logs_on_startup():
    """Clean up heatmap log file on service restart for fresh debugging"""
    try:
        log_file = '/tmp/heatmap.log'
        
        print(f"[@heatmap_processor] Cleaning heatmap log on service restart...")
        
        if os.path.exists(log_file):
            # Truncate the file instead of deleting to avoid permission issues
            with open(log_file, 'w') as f:
                f.write(f"=== LOG CLEANED ON HEATMAP PROCESSOR RESTART: {datetime.now().isoformat()} ===\n")
            print(f"[@heatmap_processor] ✓ Cleaned: {log_file}")
        else:
            print(f"[@heatmap_processor] ○ Not found (will be created): {log_file}")
            
        print(f"[@heatmap_processor] Log cleanup complete - fresh logs for debugging")
            
    except Exception as e:
        print(f"[@heatmap_processor] Warning: Could not clean log file: {e}")

class HeatmapProcessor:
    """Background processor for continuous heatmap generation"""
    
    def __init__(self):
        self.running = False
        self.server_path = self._get_server_path()
        # Performance: Reuse session for connection pooling
        import requests
        self.session = requests.Session()
        # Performance: Cache fonts to avoid repeated loading
        self._fonts_cache = {}
        logger.info(f"🏷️ HeatmapProcessor server path: {self.server_path}")
    
    def _get_server_path(self) -> str:
        """Get server path for R2 storage organization - uses backend SERVER_URL"""
        import re
        
        # Use backend's own SERVER_URL (not frontend's VITE_SERVER_URL)
        # This is the actual server URL where this backend is running
        server_url = os.getenv('SERVER_URL', 'http://localhost:5109')
        
        # Remove protocol and replace all special chars (. : /) with - for folder structure
        without_protocol = re.sub(r'^https?://', '', server_url)
        server_path = re.sub(r'[.:/]', '-', without_protocol)
        
        logger.info(f"📍 Using SERVER_URL: {server_url} → R2 path: heatmaps/{server_path}/")
        return server_path
        
    def start(self):
        """Start continuous processing every minute"""
        cleanup_logs_on_startup()  # Clean logs on startup
        logger.info("🚀 Starting HeatmapProcessor...")
        self.running = True
        
        while self.running:
            try:
                self.process_current_minute()
                self.wait_for_next_minute()
            except KeyboardInterrupt:
                logger.info("🛑 HeatmapProcessor stopped by user")
                self.running = False
            except Exception as e:
                logger.error(f"❌ HeatmapProcessor error: {e}")
                time.sleep(60)  # Wait a minute before retrying
    
    def process_current_minute(self):
        """Generate mosaic and analysis for current minute"""
        now = datetime.now()
        time_key = f"{now.hour:02d}{now.minute:02d}"  # "1425"
        
        logger.info(f"🔄 Processing heatmap for {time_key}")
        
        try:
            # Get hosts and analysis data
            hosts_devices = self.get_hosts_devices()
            if not hosts_devices:
                logger.warning(f"⚠️ No hosts available for {time_key}")
                return
                
            # Fetch current captures using latest-json endpoint (same as useMonitoring)
            current_captures = self.fetch_current_captures(hosts_devices)
            if not current_captures:
                logger.warning(f"⚠️ No current captures retrieved for {time_key}")
                return
                
                
            # Create complete device list with placeholders for missing captures
            complete_device_list = self.create_complete_device_list(hosts_devices, current_captures)
            
            # Create mosaic image (always full grid)
            mosaic_image = self.create_mosaic_image(complete_device_list)
            
            # Create OK and KO mosaics - OPTIMIZED: single pass filtering
            ok_devices, ko_devices = self.filter_devices_by_status(complete_device_list)
            
            ko_mosaic_image = self.create_mosaic_image(ko_devices) if ko_devices else None
            ok_mosaic_image = self.create_mosaic_image(ok_devices) if ok_devices else None
            
            logger.info(f"📊 Created mosaics: ALL({len(complete_device_list)}), OK({len(ok_devices)}), KO({len(ko_devices)})")
            
            # Create analysis JSON (includes all devices, even missing ones)
            analysis_json = self.create_analysis_json(complete_device_list, time_key)
            
            # Display consolidated JSON data in logs
            self.log_consolidated_json(analysis_json)
            
            # Upload to R2 with time-only naming
            success, uploaded_urls = self.upload_heatmap_files(time_key, mosaic_image, analysis_json, ok_mosaic_image, ko_mosaic_image)
            
            # Log raw JSON data after upload
            logger.info(f"📄 RAW JSON DATA for {time_key}:")
            logger.info(json.dumps(analysis_json, indent=2))
            
            logger.info(f"✅ Generated heatmap for {time_key} ({len(complete_device_list)} devices)")
            
        except Exception as e:
            logger.error(f"❌ Error processing {time_key}: {e}")
    
    def get_hosts_devices(self) -> List[Dict]:
        """Get hosts and devices via server API endpoint"""
        try:
            import requests
            
            # Load environment and use proper URL building
            from shared.src.lib.utils.app_utils import load_environment_variables
            from shared.src.lib.utils.build_url_utils import buildServerUrl
            
            # Load environment variables (same as server does)
            load_environment_variables(mode='server')
            
            # Build proper server URL using the same utility the server uses
            api_url = buildServerUrl('server/system/getAllHosts')
            
            # Call server API to get all hosts
            logger.info(f"📡 Making API request to: {api_url}")
            response = requests.get(api_url, timeout=10)
            logger.info(f"📨 Response status: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"❌ Server API returned status {response.status_code}")
                return []
            
            api_result = response.json()
            if not api_result.get('success', False):
                logger.error(f"❌ Server API error: {api_result.get('error', 'Unknown error')}")
                return []
            
            # API returns hosts as a list, not a dict
            hosts_list = api_result.get('hosts', [])
            logger.info(f"✅ Successfully fetched {len(hosts_list)} hosts from server")
            
            all_hosts = {host['host_name']: host for host in hosts_list}
            hosts_devices = []
            
            for host_name, host_data in all_hosts.items():
                devices = host_data.get('devices', [])
                
                if isinstance(devices, list) and devices:
                    for device in devices:
                        device_id = device.get('device_id', 'device1')
                        device_name = device.get('device_name', 'Unknown')
                        capabilities = device.get('device_capabilities', {})
                        av_capability = capabilities.get('av')
                        
                        logger.debug(f"🔧 Device {device_id} ({device_name}): AV={av_capability}")
                        
                        if (isinstance(capabilities, dict) and 'av' in capabilities and av_capability):
                            hosts_devices.append({
                                'host_name': host_name,
                                'device_id': device_id,
                                'device_name': device_name,
                                'host_data': host_data
                            })
                else:
                    host_capabilities = host_data.get('capabilities', {})
                    av_capability = host_capabilities.get('av')
                    logger.debug(f"🔧 Host {host_name}: AV={av_capability}")
                    
                    if (isinstance(host_capabilities, dict) and 'av' in host_capabilities and av_capability):
                        hosts_devices.append({
                            'host_name': host_name,
                            'device_id': 'host',
                            'device_name': 'host',
                            'host_data': host_data
                        })
            
            logger.info(f"🎯 Total AV devices found: {len(hosts_devices)}")
            return hosts_devices
            
        except Exception as e:
            logger.error(f"❌ Error getting hosts from API: {e}")
            return []
    
    def _fetch_device_capture(self, device: Dict) -> Optional[Dict]:
        """Fetch current capture for a single device (for parallel execution)"""
        try:
            from shared.src.lib.utils.build_url_utils import buildHostUrl
            
            host_name = device['host_name']
            device_id = device['device_id']
            device_name = device.get('device_name', 'Unknown')
            host_data = device['host_data']
            
            # Call host directly (not via central server proxy) since we're running as standalone script
            api_url = buildHostUrl(host_data, 'host/monitoring/latest-json')
            
            logger.info(f"🔗 [{host_name}/{device_id}/{device_name}] Calling: {api_url}")
            
            response = self.session.post(
                api_url,
                json={
                    'device_id': device_id
                },
                timeout=10,
                verify=False  # For self-signed certificates
            )
            
            logger.info(f"📥 [{host_name}/{device_id}/{device_name}] Response: HTTP {response.status_code}")
                    
            if response.status_code == 200:
                result = response.json()
                logger.info(f"📦 [{host_name}/{device_id}/{device_name}] Response body: {result}")
                
                if result.get('success') and 'json_data' in result and 'filename' in result:
                    # Host returns json_data directly - no need for separate request
                    json_data = result['json_data']
                    filename = result['filename']
                    
                    # Extract sequence from filename
                    import re
                    sequence_match = re.search(r'capture_(\d+)', filename)
                    sequence = sequence_match.group(1) if sequence_match else ''
                    
                    if sequence:
                        from shared.src.lib.utils.build_url_utils import buildCaptureUrl, buildMetadataUrl
                        
                        # Special handling for device_id='host' - need to add host device to host_data
                        if device_id == 'host':
                            # Create a synthetic device entry for the host if not already in devices array
                            devices = host_data.get('devices', [])
                            host_device_exists = any(d.get('device_id') == 'host' for d in devices)
                            
                            if not host_device_exists:
                                # Extract capture folder from the JSON data itself (not from env vars)
                                # The json_data should contain paths like /var/www/html/stream/capture3/...
                                capture_folder = None
                                try:
                                    # Look for capture folder in various fields in json_data
                                    for field in ['frame_path', 'thumbnail_path', 'last_3_filenames']:
                                        if field in json_data and json_data[field]:
                                            path = json_data[field] if isinstance(json_data[field], str) else json_data[field][0]
                                            # Extract capture folder from path like /var/www/html/stream/capture3/...
                                            match = re.search(r'/stream/(capture\d+)/', path)
                                            if match:
                                                capture_folder = match.group(1)
                                                logger.info(f"✅ Extracted capture folder '{capture_folder}' from {field}: {path}")
                                                break
                                    
                                    if not capture_folder:
                                        raise ValueError(f"Could not extract capture folder from json_data fields")
                                    
                                    host_device = {
                                        'device_id': 'host',
                                        'device_name': f"{host_name}_Host",
                                        'device_model': 'host_vnc',  # Required for URL building
                                        'video_stream_path': f'/stream/{capture_folder}/segments/output.m3u8',
                                        'video_capture_path': f'/var/www/html/stream/{capture_folder}'
                                    }
                                    # Temporarily add to host_data for URL building
                                    host_data = host_data.copy()
                                    host_data['devices'] = devices + [host_device]
                                    logger.info(f"✅ Created synthetic host device entry for {host_name} with capture_folder={capture_folder}")
                                except Exception as e:
                                    logger.error(f"❌ Could not create host device entry: {e}")
                                    logger.error(f"   json_data keys: {list(json_data.keys())}")
                                    # Can't proceed without proper device config
                                    return None
                        
                        # Build URLs based on filename
                        capture_filename = f"capture_{sequence}.jpg"
                        json_filename = f"capture_{sequence}.json"
                        image_url = buildCaptureUrl(host_data, capture_filename, device_id)
                        json_url = buildMetadataUrl(host_data, json_filename, device_id)
                        
                        # Analysis data is already in json_data
                        analysis_data = json_data if json_data.get('analyzed') else None
                        
                        logger.info(f"✅ Got json_data for {host_name}/{device_id}/{device_name}: sequence={sequence}")
                        
                        return {
                            'host_name': host_name,
                            'device_id': device_id,
                            'device_name': device_name,
                            'image_url': image_url,
                            'json_url': json_url,
                            'analysis': analysis_data,
                            'timestamp': result.get('timestamp', ''),
                            'sequence': sequence
                        }
                    else:
                    error_msg = result.get('error', 'Unknown error')
                    logger.warning(f"⚠️ No latest JSON for {host_name}/{device_id}/{device_name}: {error_msg}")
                    logger.warning(f"   Full response: {result}")
            else:
                logger.error(f"❌ API error for {host_name}/{device_id}/{device_name}: HTTP {response.status_code}")
                try:
                    error_body = response.text[:500]  # First 500 chars
                    logger.error(f"   Error body: {error_body}")
                except:
                    pass
        except Exception as e:
            logger.error(f"❌ Error fetching capture for {host_name}/{device_id}/{device_name}: {e}")
            logger.error(f"   Exception type: {type(e).__name__}")
            logger.error(f"   Exception details: {str(e)}")
        
        return None
    
    def fetch_current_captures(self, hosts_devices: List[Dict]) -> List[Dict]:
        """Fetch current captures for all devices IN PARALLEL (OPTIMIZED)"""
        try:
            logger.info(f"🚀 Fetching captures for {len(hosts_devices)} devices in parallel...")
            start_time = time.time()
            
            current_captures = []
            
            # PERFORMANCE: Parallel execution with ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=min(10, len(hosts_devices))) as executor:
                # Submit all tasks
                future_to_device = {
                    executor.submit(self._fetch_device_capture, device): device 
                    for device in hosts_devices
                }
                
                # Collect results as they complete
                for future in as_completed(future_to_device):
                    device = future_to_device[future]
                    try:
                        result = future.result()
                        if result:
                            current_captures.append(result)
                            logger.info(f"✅ {result['host_name']}/{result['device_id']}: capture_{result['sequence']}.jpg")
                    except Exception as e:
                        logger.error(f"❌ Future failed for {device.get('host_name')}/{device.get('device_id')}: {e}")
            
            elapsed = time.time() - start_time
            logger.info(f"🎯 Fetched {len(current_captures)} captures from {len(hosts_devices)} devices in {elapsed:.2f}s (parallel)")
            return current_captures
            
        except Exception as e:
            logger.error(f"❌ Error fetching current captures: {e}")
            return []
    
    def create_complete_device_list(self, hosts_devices: List[Dict], current_captures: List[Dict]) -> List[Dict]:
        """Create complete device list with placeholders for missing captures"""
        complete_list = []
        
        # Create lookup for current captures
        captures_by_device = {}
        for capture in current_captures:
            key = f"{capture['host_name']}/{capture['device_id']}"
            captures_by_device[key] = capture
        
        # Process all expected devices
        for device in hosts_devices:
            host_name = device['host_name']
            device_id = device['device_id']
            key = f"{host_name}/{device_id}"
            
            if key in captures_by_device:
                # Device has current capture - use it
                complete_list.append(captures_by_device[key])
            else:
                # Device missing capture - create placeholder
                placeholder = {
                    'host_name': host_name,
                    'device_id': device_id,
                    'device_name': device.get('device_name', 'Unknown'),
                    'image_url': None,  # No image available
                    'json_url': None,   # No JSON available
                    'analysis': {},     # Empty analysis
                    'timestamp': '',    # No timestamp
                    'sequence': 'missing',
                    'is_placeholder': True,  # Mark as placeholder
                    'host_data': device['host_data']  # Keep host data for device info
                }
                complete_list.append(placeholder)
        
        return complete_list
    
    def save_heatmap_locally(self, time_key: str, mosaic_image: Image.Image) -> str:
        """Save heatmap locally before uploading for preview/debugging"""
        try:
            import os
            
            # Create heatmaps directory if it doesn't exist
            heatmaps_dir = os.path.join(os.path.dirname(__file__), '..', 'heatmaps')
            os.makedirs(heatmaps_dir, exist_ok=True)
            
            # Save with timestamp for uniqueness
            local_path = os.path.join(heatmaps_dir, f'heatmap_{time_key}.jpg')
            mosaic_image.save(local_path, format='JPEG', quality=85)
            
            return local_path
            
        except Exception as e:
            logger.warning(f"⚠️ Could not save heatmap locally: {e}")
            return "Failed to save locally"
    
    def log_consolidated_json(self, analysis_json: Dict):
        """Display consolidated JSON data in logs"""
        logger.info(f"📊 CONSOLIDATED JSON DATA:")
        logger.info(f"   🕐 Time Key: {analysis_json['time_key']}")
        logger.info(f"   📅 Timestamp: {analysis_json['timestamp']}")
        logger.info(f"   🖥️  Total Devices: {analysis_json['hosts_count']}")
        logger.info(f"   🚨 Incidents Count: {analysis_json['incidents_count']}")
        
        logger.info(f"   📋 Device Status Summary:")
        active_count = 0
        missing_count = 0
        incident_devices = []
        
        for device in analysis_json['devices']:
            if device['status'] == 'missing':
                missing_count += 1
            else:
                active_count += 1
                
            # Check for incidents using raw analysis data (handle None)
            analysis_data = device.get('analysis_json') or {}
            has_incident = (
                analysis_data.get('blackscreen', False) or
                analysis_data.get('freeze', False) or
                not analysis_data.get('audio', True)
            )
            
            if has_incident and device['status'] != 'missing':
                incident_types = []
                if analysis_data.get('blackscreen', False):
                    incident_types.append('blackscreen')
                if analysis_data.get('freeze', False):
                    incident_types.append('freeze')
                if not analysis_data.get('audio', True):
                    incident_types.append('no_audio')
                
                device_name = device.get('device_name', 'Unknown')
                incident_devices.append({
                    'device': f"{device['host_name']}/{device['device_id']}/{device_name}",
                    'incidents': incident_types
                })
        
        logger.info(f"      ✅ Active: {active_count}")
        logger.info(f"      ❌ Missing: {missing_count}")
        
        if incident_devices:
            logger.info(f"   🚨 Devices with Incidents:")
            for incident_device in incident_devices:
                incidents_str = ', '.join(incident_device['incidents'])
                logger.info(f"      🔴 {incident_device['device']}: {incidents_str}")
        else:
            logger.info(f"   ✅ No incidents detected")
    
    
    def filter_devices_by_status(self, devices_data: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """Filter devices into OK and KO lists in single pass (OPTIMIZED)"""
        ok_devices = []
        ko_devices = []
        
        for device in devices_data:
            analysis_data = device.get('analysis', {})
            is_placeholder = device.get('is_placeholder', False)
            
            has_incident = False
            has_real_analysis = analysis_data and any(key in analysis_data for key in ['blackscreen', 'freeze', 'audio'])
            
            if not is_placeholder and has_real_analysis:
                has_incident = (
                    analysis_data.get('blackscreen', False) or
                    analysis_data.get('freeze', False) or
                    not analysis_data.get('audio', True)
                )
                
                if has_incident:
                    ko_devices.append(device)
                else:
                    ok_devices.append(device)
        
        return ok_devices, ko_devices
    
    def _get_cached_font(self, font_name: str, size: int = None):
        """Get font from cache or load it (OPTIMIZED)"""
        from PIL import ImageFont
        
        cache_key = f"{font_name}_{size}" if size else font_name
        
        if cache_key not in self._fonts_cache:
            if font_name == 'default':
                self._fonts_cache[cache_key] = ImageFont.load_default()
            else:
                try:
                    self._fonts_cache[cache_key] = ImageFont.truetype(font_name, size)
                except:
                    self._fonts_cache[cache_key] = ImageFont.load_default()
        
        return self._fonts_cache[cache_key]
    
    def add_border_and_label(self, img: Image.Image, image_data: Dict, cell_width: int, cell_height: int) -> Image.Image:
        """Add colored border and label to device image"""
        from PIL import ImageDraw
        
        # Check for incidents in raw analysis data
        analysis_data = image_data.get('analysis_json', {}) or image_data.get('analysis', {})
        is_placeholder = image_data.get('is_placeholder', False)
        
        has_real_analysis = analysis_data and any(key in analysis_data for key in ['blackscreen', 'freeze', 'audio'])
        
        has_incident = False
        if not is_placeholder and has_real_analysis:
            has_incident = (
                analysis_data.get('blackscreen', False) or
                analysis_data.get('freeze', False) or
                not analysis_data.get('audio', True)
            )
        
        # Add border
        if is_placeholder or not has_real_analysis:
            border_color = (128, 128, 128)
        elif has_incident:
            border_color = (255, 0, 0)
        else:
            border_color = (0, 255, 0)
            
        draw = ImageDraw.Draw(img)
        draw.rectangle([0, 0, cell_width-1, cell_height-1], outline=border_color, width=4)
        
        # Add label - use cached font (OPTIMIZED)
        host_name = image_data.get('host_name', '')
        device_name = image_data.get('device_name', image_data.get('device_id', ''))
        label = f"{host_name}_{device_name}"
        
        try:
            font = self._get_cached_font('default')
            bbox = draw.textbbox((0, 0), label, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            x_pos = cell_width - text_width - 5
            y_pos = cell_height - text_height - 5
            
            draw.text((x_pos, y_pos), label, fill='white', font=font)
        except:
            draw.text((cell_width-150, cell_height-20), label, fill='white', font=self._get_cached_font('default'))
        
        return img
    
    def _download_and_process_image(self, image_data: Dict, cell_width: int, cell_height: int) -> Tuple[Optional[Image.Image], Dict]:
        """Download and process a single image for mosaic (for parallel execution)"""
        try:
            image_url = image_data.get('image_url')
            
            if not image_url or image_url == 'None':
                return None, image_data
            
            response = self.session.get(image_url, timeout=10)
            if response.status_code == 200:
                img = Image.open(io.BytesIO(response.content))
                # PERFORMANCE: Use BILINEAR instead of LANCZOS (5x faster, minimal quality loss for thumbnails)
                img = img.resize((cell_width, cell_height), Image.Resampling.BILINEAR)
                img_with_border = self.add_border_and_label(img, image_data, cell_width, cell_height)
                return img_with_border, image_data
            else:
                raise Exception(f"HTTP {response.status_code}")
        except Exception as e:
            logger.error(f"❌ Error loading image {image_data.get('image_url')}: {e}")
            return None, image_data
    
    def create_mosaic_image(self, images_data: List[Dict]) -> Image.Image:
        """Create mosaic image from device images - OPTIMIZED with parallel downloads"""
        if not images_data:
            logger.warning("⚠️ No images provided for mosaic - creating empty black image")
            return Image.new('RGB', (800, 600), color='black')
        
        logger.info(f"🎨 Creating mosaic from {len(images_data)} images")
        start_time = time.time()
        
        # Calculate grid layout
        count = len(images_data)
        if count <= 1:
            cols, rows = 1, 1
        elif count == 2:
            cols, rows = 2, 1
        elif count <= 4:
            cols, rows = 2, 2
        elif count <= 6:
            cols, rows = 3, 2
        elif count <= 9:
            cols, rows = 3, 3
        else:
            # For more than 9 devices, use 6 columns max
            cols = min(6, count)
            rows = math.ceil(count / cols)
        
        logger.info(f"📐 Grid layout: {cols}x{rows} (total cells: {cols*rows})")
        
        # Create mosaic
        cell_width, cell_height = 400, 300
        mosaic_width = cols * cell_width
        mosaic_height = rows * cell_height
        
        logger.info(f"🖼️ Mosaic dimensions: {mosaic_width}x{mosaic_height} pixels ({cell_width}x{cell_height} per cell)")
        mosaic = Image.new('RGB', (mosaic_width, mosaic_height), color='black')
        
        # PERFORMANCE: Download and process images in parallel
        processed_images = {}
        images_to_download = []
        
        for i, image_data in enumerate(images_data):
            if i >= cols * rows:
                break
            
            image_url = image_data.get('image_url')
            is_placeholder = image_data.get('is_placeholder', False)
            
            if not is_placeholder and image_url and image_url != 'None':
                images_to_download.append((i, image_data))
        
        # Download images in parallel if there are any
        if images_to_download:
            logger.info(f"📥 Downloading {len(images_to_download)} images in parallel...")
            with ThreadPoolExecutor(max_workers=min(10, len(images_to_download))) as executor:
                future_to_index = {
                    executor.submit(self._download_and_process_image, img_data, cell_width, cell_height): idx
                    for idx, img_data in images_to_download
                }
                
                for future in as_completed(future_to_index):
                    idx = future_to_index[future]
                    try:
                        result_img, img_data = future.result()
                        if result_img:
                            processed_images[idx] = result_img
                            device_name = img_data.get('device_name', 'Unknown')
                            logger.debug(f"✅ Downloaded {img_data['host_name']}/{img_data['device_id']}/{device_name}")
                    except Exception as e:
                        logger.error(f"❌ Future failed for image {idx}: {e}")
        
        # Now assemble the mosaic
        for i, image_data in enumerate(images_data):
            if i >= cols * rows:
                break
                
            row = i // cols
            col = i % cols
            
            x = col * cell_width
            y = row * cell_height
            
            # Check if we have a pre-downloaded image
            if i in processed_images:
                # Use pre-downloaded and processed image
                mosaic.paste(processed_images[i], (x, y))
                continue
            
            # Otherwise create placeholder
            image_url = image_data.get('image_url')
            is_placeholder = image_data.get('is_placeholder', False)
            
            if True:  # Always create placeholder for non-downloaded images
                # Create placeholder with device info
                placeholder_color = '#2a2a2a' if is_placeholder else '#4a2a2a'  # Dark gray for missing, dark red for None
                placeholder = Image.new('RGB', (cell_width, cell_height), color=placeholder_color)
                
                # Add text overlay with device info
                try:
                    from PIL import ImageDraw
                    draw = ImageDraw.Draw(placeholder)
                    
                    # Use cached fonts (OPTIMIZED)
                    font = self._get_cached_font("/System/Library/Fonts/Arial.ttf", 24)
                    small_font = self._get_cached_font("/System/Library/Fonts/Arial.ttf", 16)
                    
                    # Device info text
                    host_name = image_data['host_name']
                    device_name = image_data.get('device_name', image_data.get('device_id', 'Unknown'))
                    
                    # Center the text
                    text1 = f"{host_name}"
                    text2 = f"{device_name}"
                    text3 = "NO CAPTURE" if is_placeholder else "NOT FOUND"
                    
                    # Calculate text positions (centered)
                    bbox1 = draw.textbbox((0, 0), text1, font=font)
                    bbox2 = draw.textbbox((0, 0), text2, font=small_font)
                    bbox3 = draw.textbbox((0, 0), text3, font=small_font)
                    
                    text1_x = (cell_width - (bbox1[2] - bbox1[0])) // 2
                    text2_x = (cell_width - (bbox2[2] - bbox2[0])) // 2
                    text3_x = (cell_width - (bbox3[2] - bbox3[0])) // 2
                    
                    # Draw text
                    draw.text((text1_x, cell_height//2 - 40), text1, fill='white', font=font)
                    draw.text((text2_x, cell_height//2 - 10), text2, fill='lightgray', font=small_font)
                    draw.text((text3_x, cell_height//2 + 15), text3, fill='red', font=small_font)
                    
                except Exception as e:
                    logger.warning(f"⚠️ Could not add text to placeholder: {e}")
                
                mosaic.paste(placeholder, (x, y))
                status_text = "placeholder" if is_placeholder else "not found"
                device_name = image_data.get('device_name', 'Unknown')
                logger.debug(f"📝 Added {status_text} for {image_data['host_name']}/{image_data['device_id']}/{device_name}")
        
        elapsed = time.time() - start_time
        logger.info(f"🎨 Mosaic created in {elapsed:.2f}s ({len(processed_images)} images downloaded in parallel)")
        return mosaic
    
    def create_analysis_json(self, images_data: List[Dict], time_key: str) -> Dict:
        """Create analysis JSON for the minute - replace local paths with R2 URLs from alerts"""
        devices = []
        incidents_count = 0
        
        for image_data in images_data:
            analysis = image_data.get('analysis', {})
            is_placeholder = image_data.get('is_placeholder', False)
            
            # Check for incidents using raw analysis data (only for real captures with real data)
            has_incidents = False
            has_real_analysis = analysis and any(key in analysis for key in ['blackscreen', 'freeze', 'audio'])
            if not is_placeholder and has_real_analysis:
                has_incidents = (
                    analysis.get('blackscreen', False) or
                    analysis.get('freeze', False) or
                    not analysis.get('audio', True)
                )
            
            if has_incidents:
                incidents_count += 1
            
            # Build device entry - use raw analysis data with local paths (24h retention allows local access)
            device_entry = {
                'host_name': image_data['host_name'],
                'device_id': image_data['device_id'],
                'device_name': image_data.get('device_name'),  # Include device_name for frontend tooltip
                'image_url': image_data.get('image_url'),
                'json_url': image_data.get('json_url'),
                'sequence': image_data.get('sequence', 'missing'),
                'analysis_json': analysis,  # Raw analysis with local paths (available for 24h)
                'status': 'missing' if is_placeholder else 'active',
                'is_placeholder': is_placeholder
            }
            
            devices.append(device_entry)
        
        return {
            'time_key': time_key,
            'timestamp': datetime.now().isoformat(),
            'devices': devices,
            'incidents_count': incidents_count,
            'hosts_count': len(images_data)
        }
    
    def image_to_bytes(self, image: Image.Image) -> bytes:
        """Convert PIL Image to bytes"""
        buffer = io.BytesIO()
        image.save(buffer, format='JPEG', quality=85)
        return buffer.getvalue()
    
    def upload_heatmap_files(self, time_key: str, mosaic_image: Image.Image, analysis_json: Dict, ok_mosaic_image: Optional[Image.Image] = None, ko_mosaic_image: Optional[Image.Image] = None) -> Tuple[bool, Dict]:
        """Upload mosaic image and analysis JSON to R2"""
        try:
            import tempfile
            import os
            
            # Create temporary files
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as img_temp:
                mosaic_image.save(img_temp.name, format='JPEG', quality=85)
                img_temp_path = img_temp.name
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as json_temp:
                json.dump(analysis_json, json_temp, indent=2)
                json_temp_path = json_temp.name
            
            # Handle OK and KO mosaics if provided
            ok_img_temp_path = None
            ko_img_temp_path = None
            if ok_mosaic_image:
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as ok_img_temp:
                    ok_mosaic_image.save(ok_img_temp.name, format='JPEG', quality=85)
                    ok_img_temp_path = ok_img_temp.name
            if ko_mosaic_image:
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as ko_img_temp:
                    ko_mosaic_image.save(ko_img_temp.name, format='JPEG', quality=85)
                    ko_img_temp_path = ko_img_temp.name
            
            try:
                # Prepare file mappings for batch upload
                file_mappings = [
                    {
                        'local_path': img_temp_path,
                        'remote_path': f'heatmaps/{self.server_path}/{time_key}.jpg',
                        'content_type': 'image/jpeg'
                    },
                    {
                        'local_path': json_temp_path,
                        'remote_path': f'heatmaps/{self.server_path}/{time_key}.json',
                        'content_type': 'application/json'
                    }
                ]
                
                # Add OK and KO mosaics if available
                if ok_img_temp_path:
                    file_mappings.append({
                        'local_path': ok_img_temp_path,
                        'remote_path': f'heatmaps/{self.server_path}/{time_key}_ok.jpg',
                        'content_type': 'image/jpeg'
                    })
                if ko_img_temp_path:
                    file_mappings.append({
                        'local_path': ko_img_temp_path,
                        'remote_path': f'heatmaps/{self.server_path}/{time_key}_ko.jpg',
                        'content_type': 'image/jpeg'
                    })
                
                # Upload files using CloudflareUtils
                cloudflare_utils = get_cloudflare_utils()
                result = cloudflare_utils.upload_files(file_mappings)
                
                # Log all uploaded URLs
                uploaded_urls = {}
                if result.get('uploaded_files'):
                    logger.info(f"✅ Uploaded {len(result['uploaded_files'])} files for {time_key}:")
                    for uploaded in result['uploaded_files']:
                        url = uploaded.get('url', 'URL not available')
                        logger.info(f"   🔗 {uploaded['remote_path']}: {url}")
                        
                        # Store main URLs for return
                        if uploaded['remote_path'].endswith(f'{time_key}.jpg'):
                            uploaded_urls['mosaic_url'] = url
                        elif uploaded['remote_path'].endswith(f'{time_key}.json'):
                            uploaded_urls['json_url'] = url
                
                if result.get('failed_uploads'):
                    logger.error(f"❌ Failed uploads for {time_key}:")
                    for failed in result['failed_uploads']:
                        logger.error(f"   ❌ {failed['remote_path']}: {failed['error']}")
                
                return True, uploaded_urls
                    
            finally:
                # Clean up temporary files
                if os.path.exists(img_temp_path):
                    os.unlink(img_temp_path)
                if os.path.exists(json_temp_path):
                    os.unlink(json_temp_path)
                if ok_img_temp_path and os.path.exists(ok_img_temp_path):
                    os.unlink(ok_img_temp_path)
                if ko_img_temp_path and os.path.exists(ko_img_temp_path):
                    os.unlink(ko_img_temp_path)
                    
        except Exception as e:
            logger.error(f"❌ Error uploading heatmap files for {time_key}: {e}")
            return False, {}
    
    def wait_for_next_minute(self):
        """Wait until next minute boundary"""
        now = datetime.now()
        seconds_to_wait = 60 - now.second
        logger.info(f"⏳ Waiting {seconds_to_wait}s for next minute...")
        time.sleep(seconds_to_wait)


if __name__ == "__main__":
    # Run processor directly
    processor = HeatmapProcessor()
    processor.start()
