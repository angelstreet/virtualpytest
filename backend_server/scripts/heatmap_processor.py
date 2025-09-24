"""
Heatmap Processor Service

Continuous background service that generates heatmap mosaics every minute.
Uses circular buffer with HHMM naming (1440 fixed files).
"""

import sys
import os

# Add project root to path FIRST
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Apply global typing compatibility early to fix third-party package issues
try:
    from shared.src.lib.utils.typing_compatibility import ensure_typing_compatibility
    ensure_typing_compatibility()
except ImportError:
    print("⚠️  Warning: Could not apply typing compatibility fix")

# Now import everything else after typing fix
import time
import json
from datetime import datetime
from typing import Dict, List, Optional
from PIL import Image
import io
import math

from shared.src.lib.utils.cloudflare_utils import get_cloudflare_utils

class HeatmapProcessor:
    """Background processor for continuous heatmap generation"""
    
    def __init__(self):
        self.running = False
        
    def start(self):
        """Start continuous processing every minute"""
        print("🚀 Starting HeatmapProcessor...")
        self.running = True
        
        while self.running:
            try:
                self.process_current_minute()
                self.wait_for_next_minute()
            except KeyboardInterrupt:
                print("🛑 HeatmapProcessor stopped by user")
                self.running = False
            except Exception as e:
                print(f"❌ HeatmapProcessor error: {e}")
                time.sleep(60)  # Wait a minute before retrying
    
    def process_current_minute(self):
        """Generate mosaic and analysis for current minute"""
        now = datetime.now()
        time_key = f"{now.hour:02d}{now.minute:02d}"  # "1425"
        
        print(f"🔄 Processing heatmap for {time_key}")
        
        try:
            # Get hosts and analysis data
            hosts_devices = self.get_hosts_devices()
            if not hosts_devices:
                print(f"⚠️ No hosts available for {time_key}")
                return
                
            # Fetch current captures using latest-json endpoint (same as useMonitoring)
            current_captures = self.fetch_current_captures(hosts_devices)
            if not current_captures:
                print(f"⚠️ No current captures retrieved for {time_key}")
                return
            
            print(f"✅ Got {len(current_captures)} current captures (expected: {len(hosts_devices)})")
            
            # Use current captures directly - no complex timestamp processing needed
            images_data = current_captures
            
            # Create mosaic image
            mosaic_image = self.create_mosaic_image(images_data)
            
            # Create analysis JSON
            analysis_json = self.create_analysis_json(images_data, time_key)
            
            # Upload to R2 with time-only naming
            success = self.upload_heatmap_files(time_key, mosaic_image, analysis_json)
            
            if not success:
                print(f"❌ Failed to upload files for {time_key}")
                return
            
            print(f"✅ Generated heatmap for {time_key} ({len(images_data)} devices)")
            
        except Exception as e:
            print(f"❌ Error processing {time_key}: {e}")
    
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
            print(f"📡 Making API request to: {api_url}")
            response = requests.get(api_url, timeout=10)
            print(f"📨 Response status: {response.status_code}")
            
            if response.status_code != 200:
                print(f"❌ Server API returned status {response.status_code}")
                return []
            
            api_result = response.json()
            if not api_result.get('success', False):
                print(f"❌ Server API error: {api_result.get('error', 'Unknown error')}")
                return []
            
            # API returns hosts as a list, not a dict
            hosts_list = api_result.get('hosts', [])
            print(f"✅ Successfully fetched {len(hosts_list)} hosts from server")
            
            all_hosts = {host['host_name']: host for host in hosts_list}
            hosts_devices = []
            
            for host_name, host_data in all_hosts.items():
                print(f"🔍 Processing host: {host_name}")
                devices = host_data.get('devices', [])
                host_av_devices = 0
                
                if isinstance(devices, list) and devices:
                    print(f"   📱 Host has {len(devices)} devices")
                    for device in devices:
                        device_id = device.get('device_id', 'device1')
                        device_name = device.get('device_name', 'Unknown')
                        capabilities = device.get('device_capabilities', {})
                        av_capability = capabilities.get('av')
                        
                        print(f"   🔧 Device {device_id} ({device_name}): AV={av_capability}")
                        
                        if (isinstance(capabilities, dict) and 'av' in capabilities and av_capability):
                            hosts_devices.append({
                                'host_name': host_name,
                                'device_id': device_id,
                                'host_data': host_data
                            })
                            host_av_devices += 1
                            print(f"   ✅ Added AV device: {device_id}")
                else:
                    print(f"   📱 Host has no device list, checking host capabilities")
                    host_capabilities = host_data.get('capabilities', {})
                    av_capability = host_capabilities.get('av')
                    print(f"   🔧 Host capabilities: AV={av_capability}")
                    
                    if (isinstance(host_capabilities, dict) and 'av' in host_capabilities and av_capability):
                        hosts_devices.append({
                            'host_name': host_name,
                            'device_id': 'device1',
                            'host_data': host_data
                        })
                        host_av_devices += 1
                        print(f"   ✅ Added AV host: {host_name}")
                
                print(f"   📊 Host {host_name}: {host_av_devices} AV devices")
            
            print(f"🎯 Total AV devices found: {len(hosts_devices)}")
            return hosts_devices
            
        except Exception as e:
            print(f"❌ Error getting hosts from API: {e}")
            return []
    
    def fetch_current_captures(self, hosts_devices: List[Dict]) -> List[Dict]:
        """Fetch current capture (latest JSON + image) for each device using latest-json endpoint"""
        try:
            import requests
            from shared.src.lib.utils.build_url_utils import buildServerUrl
            
            current_captures = []
            
            for device in hosts_devices:
                host_name = device['host_name']
                device_id = device['device_id']
                
                try:
                    # Use same endpoint as useMonitoring - proven to work
                    api_url = buildServerUrl('server/monitoring/latest-json')
                    
                    response = requests.post(
                        api_url,
                        json={
                            'host_name': host_name,
                            'device_id': device_id
                        },
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        if result.get('success') and result.get('latest_json_url'):
                            # Extract sequence from JSON URL to build image URL
                            json_url = result['latest_json_url']
                            sequence_match = json_url.split('capture_')[-1].split('.json')[0] if 'capture_' in json_url else ''
                            
                            if sequence_match:
                                from shared.src.lib.utils.build_url_utils import buildCaptureUrl
                                image_url = buildCaptureUrl(device['host_data'], sequence_match, device_id)
                                
                                # Load JSON analysis data
                                json_response = requests.get(json_url, timeout=5)
                                analysis_data = json_response.json() if json_response.status_code == 200 else {}
                                
                                current_captures.append({
                                    'host_name': host_name,
                                    'device_id': device_id,
                                    'image_url': image_url,
                                    'json_url': json_url,
                                    'analysis': analysis_data,
                                    'timestamp': result.get('timestamp', ''),
                                    'sequence': sequence_match
                                })
                                
                                print(f"✅ Got current capture for {host_name}/{device_id}: {sequence_match}")
                            else:
                                print(f"⚠️ Could not extract sequence from {json_url}")
                        else:
                            print(f"⚠️ No latest JSON for {host_name}/{device_id}: {result.get('error', 'Unknown error')}")
                    else:
                        print(f"❌ API error for {host_name}/{device_id}: HTTP {response.status_code}")
                        
                except Exception as e:
                    print(f"❌ Error fetching current capture for {host_name}/{device_id}: {e}")
                    continue
            
            print(f"🎯 Fetched {len(current_captures)} current captures from {len(hosts_devices)} devices")
            return current_captures
            
        except Exception as e:
            print(f"❌ Error fetching current captures: {e}")
            return []
    
    
    
    def create_mosaic_image(self, images_data: List[Dict]) -> Image.Image:
        """Create mosaic image from device images"""
        if not images_data:
            # Create empty black image
            return Image.new('RGB', (800, 600), color='black')
        
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
            cols = math.ceil(math.sqrt(count))
            rows = math.ceil(count / cols)
        
        # Create mosaic
        cell_width, cell_height = 400, 300
        mosaic_width = cols * cell_width
        mosaic_height = rows * cell_height
        
        mosaic = Image.new('RGB', (mosaic_width, mosaic_height), color='black')
        
        for i, image_data in enumerate(images_data):
            if i >= cols * rows:
                break
                
            row = i // cols
            col = i % cols
            
            x = col * cell_width
            y = row * cell_height
            
            try:
                # Download and resize image
                import requests
                response = requests.get(image_data['image_url'], timeout=10)
                if response.status_code == 200:
                    img = Image.open(io.BytesIO(response.content))
                    img = img.resize((cell_width, cell_height), Image.Resampling.LANCZOS)
                    mosaic.paste(img, (x, y))
                    print(f"✅ Added image for {image_data['host_name']}/{image_data['device_id']}")
            except Exception as e:
                print(f"❌ Error loading image {image_data['image_url']}: {e}")
                # Create placeholder
                placeholder = Image.new('RGB', (cell_width, cell_height), color='gray')
                mosaic.paste(placeholder, (x, y))
        
        return mosaic
    
    def create_analysis_json(self, images_data: List[Dict], time_key: str) -> Dict:
        """Create analysis JSON for the minute"""
        devices = []
        incidents_count = 0
        
        for image_data in images_data:
            analysis = image_data.get('analysis', {})
            
            # Check for incidents
            has_incidents = (
                analysis.get('blackscreen', False) or
                analysis.get('freeze', False) or
                not analysis.get('audio', True)
            )
            
            if has_incidents:
                incidents_count += 1
            
            devices.append({
                'host_name': image_data['host_name'],
                'device_id': image_data['device_id'],
                'image_url': image_data['image_url'],
                'json_url': image_data['json_url'],
                'sequence': image_data['sequence'],
                'analysis': analysis
            })
        
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
    
    def upload_heatmap_files(self, time_key: str, mosaic_image: Image.Image, analysis_json: Dict) -> bool:
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
            
            try:
                # Prepare file mappings for batch upload
                file_mappings = [
                    {
                        'local_path': img_temp_path,
                        'remote_path': f'heatmaps/{time_key}.jpg',
                        'content_type': 'image/jpeg'
                    },
                    {
                        'local_path': json_temp_path,
                        'remote_path': f'heatmaps/{time_key}.json',
                        'content_type': 'application/json'
                    }
                ]
                
                # Upload files using CloudflareUtils
                cloudflare_utils = get_cloudflare_utils()
                result = cloudflare_utils.upload_files(file_mappings)
                
                if result['success'] and len(result['uploaded_files']) == 2:
                    print(f"✅ Uploaded heatmap files for {time_key}")
                    return True
                else:
                    print(f"❌ Upload failed for {time_key}: {result.get('error', 'Unknown error')}")
                    if result['failed_uploads']:
                        for failed in result['failed_uploads']:
                            print(f"   Failed: {failed['remote_path']} - {failed['error']}")
                    return False
                    
            finally:
                # Clean up temporary files
                if os.path.exists(img_temp_path):
                    os.unlink(img_temp_path)
                if os.path.exists(json_temp_path):
                    os.unlink(json_temp_path)
                    
        except Exception as e:
            print(f"❌ Error uploading heatmap files for {time_key}: {e}")
            return False
    
    def wait_for_next_minute(self):
        """Wait until next minute boundary"""
        now = datetime.now()
        seconds_to_wait = 60 - now.second
        print(f"⏳ Waiting {seconds_to_wait}s for next minute...")
        time.sleep(seconds_to_wait)


if __name__ == "__main__":
    # Run processor directly
    processor = HeatmapProcessor()
    processor.start()
