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
import asyncio
import aiohttp
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
                
            # Fetch analysis data from all hosts
            host_results = self.fetch_all_host_data(hosts_devices)
            if not host_results:
                print(f"⚠️ No host data retrieved for {time_key}")
                return
                
            # Process results into images by timestamp
            images_by_timestamp = self.process_host_results(host_results)
            if not images_by_timestamp:
                print(f"⚠️ No processed images for {time_key}")
                return
                
            # Use the most recent timestamp data
            latest_timestamp = max(images_by_timestamp.keys())
            images_data = images_by_timestamp[latest_timestamp]
            
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
            response = requests.get(api_url, timeout=10)
            if response.status_code != 200:
                print(f"❌ Server API returned status {response.status_code}")
                return []
            
            api_result = response.json()
            if not api_result.get('success', False):
                print(f"❌ Server API error: {api_result.get('error', 'Unknown error')}")
                return []
            
            # API returns hosts as a list, not a dict
            hosts_list = api_result.get('hosts', [])
            all_hosts = {host['host_name']: host for host in hosts_list}
            hosts_devices = []
            
            for host_name, host_data in all_hosts.items():
                devices = host_data.get('devices', [])
                if isinstance(devices, list) and devices:
                    for device in devices:
                        capabilities = device.get('device_capabilities', {})
                        av_capability = capabilities.get('av')
                        
                        if (isinstance(capabilities, dict) and 'av' in capabilities and av_capability):
                            hosts_devices.append({
                                'host_name': host_name,
                                'device_id': device.get('device_id', 'device1'),
                                'host_data': host_data
                            })
                else:
                    host_capabilities = host_data.get('capabilities', {})
                    av_capability = host_capabilities.get('av')
                    
                    if (isinstance(host_capabilities, dict) and 'av' in host_capabilities and av_capability):
                        hosts_devices.append({
                            'host_name': host_name,
                            'device_id': 'device1',
                            'host_data': host_data
                        })
            
            return hosts_devices
            
        except Exception as e:
            print(f"❌ Error getting hosts from API: {e}")
            return []
    
    def fetch_all_host_data(self, hosts_devices: List[Dict]) -> List[Dict]:
        """Fetch analysis data from all hosts"""
        try:
            async def query_all_hosts():
                async with aiohttp.ClientSession() as session:
                    tasks = [self.query_host_analysis(session, hd) for hd in hosts_devices]
                    results = []
                    for task in asyncio.as_completed(tasks):
                        try:
                            result = await task
                            results.append(result)
                        except Exception as e:
                            print(f"Host query failed: {str(e)}")
                    return results
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            host_results = loop.run_until_complete(query_all_hosts())
            loop.close()
            
            return host_results
            
        except Exception as e:
            print(f"❌ Error fetching host data: {e}")
            return []
    
    async def query_host_analysis(self, session: aiohttp.ClientSession, host_device: Dict) -> Dict:
        """Query single host for recent analysis data"""
        try:
            host_data = host_device['host_data']
            device_id = host_device['device_id']
            host_name = host_device['host_name']
            
            from shared.src.lib.utils.build_url_utils import buildHostUrl
            host_url = buildHostUrl(host_data, '/host/heatmap/listRecentAnalysis')
            
            async with session.post(
                host_url,
                json={
                    'device_id': device_id,
                    'timeframe_minutes': 1
                },
                timeout=aiohttp.ClientTimeout(total=30),
                ssl=False
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get('success'):
                        return {
                            'host_name': host_name,
                            'device_id': device_id,
                            'success': True,
                            'analysis_data': result.get('analysis_data', []),
                            'host_data': host_data
                        }
                
                return {
                    'host_name': host_name,
                    'device_id': device_id,
                    'success': False,
                    'error': f'HTTP {response.status}'
                }
                
        except Exception as e:
            return {
                'host_name': host_device.get('host_name', 'unknown'),
                'device_id': host_device.get('device_id', 'unknown'),
                'success': False,
                'error': str(e)
            }
    
    def process_host_results(self, host_results: List[Dict]) -> Dict[str, List[Dict]]:
        """Process host results and group by timestamp"""
        images_by_timestamp = {}
        
        for result in host_results:
            if isinstance(result, Exception):
                continue
            if not isinstance(result, dict) or not result.get('success'):
                continue
                
            analysis_data = result.get('analysis_data', [])
            
            for item in analysis_data:
                timestamp = item.get('timestamp', '')
                if not timestamp:
                    continue
                    
                try:
                    # Handle different timestamp formats
                    if isinstance(timestamp, (int, float)) or (isinstance(timestamp, str) and timestamp.isdigit()):
                        timestamp_seconds = int(timestamp) / 1000.0
                        dt = datetime.fromtimestamp(timestamp_seconds)
                    elif isinstance(timestamp, str) and 'T' in timestamp:
                        timestamp_clean = timestamp.split('.')[0] if '.' in timestamp else timestamp
                        dt = datetime.fromisoformat(timestamp_clean.replace('Z', '+00:00'))
                    else:
                        dt = datetime.strptime(str(timestamp), '%Y%m%d%H%M%S')
                    
                    # Create 10-second buckets
                    seconds = (dt.second // 10) * 10
                    bucket_dt = dt.replace(second=seconds, microsecond=0)
                    bucket_key = bucket_dt.strftime('%Y%m%d%H%M%S')
                    
                    if bucket_key not in images_by_timestamp:
                        images_by_timestamp[bucket_key] = []
                    
                    # Build image data
                    host_data = result.get('host_data', {})
                    device_id = result['device_id']
                    filename = item.get('filename', '')
                    
                    from shared.src.lib.utils.build_url_utils import buildHostImageUrl
                    from backend_server.src.routes.server_heatmap_routes import get_device_capture_dir
                    
                    if filename and '/' in filename:
                        filename = filename.split('/')[-1]
                    
                    if filename:
                        capture_dir = get_device_capture_dir(host_data, device_id)
                        image_path = f"stream/{capture_dir}/captures/{filename}"
                        image_url = buildHostImageUrl(host_data, image_path)
                        
                        images_by_timestamp[bucket_key].append({
                            'host_name': result['host_name'],
                            'device_id': result['device_id'],
                            'filename': filename,
                            'image_url': image_url,
                            'timestamp': timestamp,
                            'analysis_json': item.get('analysis_json', {})
                        })
                        
                except Exception as e:
                    print(f"Error processing timestamp '{timestamp}': {e}")
                    continue
        
        return images_by_timestamp
    
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
            except Exception as e:
                print(f"Error loading image {image_data['image_url']}: {e}")
                # Create placeholder
                placeholder = Image.new('RGB', (cell_width, cell_height), color='gray')
                mosaic.paste(placeholder, (x, y))
        
        return mosaic
    
    def create_analysis_json(self, images_data: List[Dict], time_key: str) -> Dict:
        """Create analysis JSON for the minute"""
        devices = []
        incidents_count = 0
        
        for image_data in images_data:
            analysis_json = image_data.get('analysis_json', {})
            
            # Check for incidents
            has_incidents = (
                analysis_json.get('blackscreen', False) or
                analysis_json.get('freeze', False) or
                not analysis_json.get('audio', True)
            )
            
            if has_incidents:
                incidents_count += 1
            
            devices.append({
                'host_name': image_data['host_name'],
                'device_id': image_data['device_id'],
                'image_url': image_data['image_url'],
                'analysis_json': analysis_json
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
