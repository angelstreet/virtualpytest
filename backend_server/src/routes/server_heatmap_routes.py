"""
Heatmap Management Routes

This module contains the heatmap management API endpoints for:
- Heatmap data retrieval (images, incidents, hosts)
- Heatmap generation (async job-based)
- Job status monitoring
"""

from flask import Blueprint, request, jsonify
import asyncio
import aiohttp
from datetime import datetime, timedelta
import time
import os

# Import database functions and utilities
from shared.src.lib.supabase.heatmap_db import (
    get_heatmap_incidents
)
from src.lib.utils.heatmap_utils import (
    create_heatmap_job,
    get_job_status,
    cancel_job,
    start_heatmap_generation
)

from shared.src.lib.utils.app_utils import check_supabase, get_team_id
from shared.src.lib.utils.build_url_utils import buildHostImageUrl

def get_device_capture_dir(host_data: dict, device_id: str) -> str:
    """
    Extract capture directory from host device configuration.
    Fails early if configuration is missing or invalid.
    
    Args:
        host_data: Host information containing devices
        device_id: Device ID to look up
        
    Returns:
        Capture directory name (e.g., 'capture1', 'capture2')
        
    Raises:
        ValueError: If device not found or video paths not configured
    """
    if not host_data:
        raise ValueError(f"Host data is required to resolve capture directory for device {device_id}")
    
    devices = host_data.get('devices', [])
    if not devices:
        raise ValueError(f"No devices configured in host data for device {device_id}")
    
    for device in devices:
        if device.get('device_id') == device_id:
            # Try video_capture_path first
            capture_path = device.get('video_capture_path')
            if capture_path:
                # Extract directory from path like '/var/www/html/stream/capture2' -> 'capture2'
                capture_dir = capture_path.split('/')[-1]
                if capture_dir.startswith('capture'):
                    return capture_dir
                else:
                    raise ValueError(f"Invalid video_capture_path format for device {device_id}: {capture_path}")
            
            # Try video_stream_path as alternative
            stream_path = device.get('video_stream_path')
            if stream_path:
                # Extract directory from path like '/host/stream/capture2' -> 'capture2'
                parts = stream_path.split('/')
                for part in reversed(parts):
                    if part.startswith('capture'):
                        return part
                raise ValueError(f"No capture directory found in video_stream_path for device {device_id}: {stream_path}")
            
            # Device found but no video paths configured
            raise ValueError(f"Device {device_id} has no video_capture_path or video_stream_path configured. Check .env file.")
    
    # Device not found in host configuration
    available_devices = [d.get('device_id', 'unknown') for d in devices]
    raise ValueError(f"Device {device_id} not found in host configuration. Available devices: {available_devices}")

# Create blueprint
server_heatmap_bp = Blueprint('server_heatmap', __name__, url_prefix='/server/heatmap')

# =====================================================
# HOST DATA FETCHING
# =====================================================

def get_hosts_devices():
    """Get hosts and devices from host manager"""
    from src.lib.utils.server_utils import get_host_manager
    host_manager = get_host_manager()
    
    hosts_devices = []
    all_hosts = host_manager.get_all_hosts()
    
    for host_data in all_hosts:
        host_name = host_data.get('host_name', host_data.get('name', 'unknown'))
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

async def query_host_analysis(session, host_device, timeframe_minutes):
    """Query single host for recent analysis data and download images"""
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
                'timeframe_minutes': timeframe_minutes
            },
            timeout=aiohttp.ClientTimeout(total=30),
            ssl=False
        ) as response:
            if response.status == 200:
                result = await response.json()
                if result.get('success'):
                    analysis_data = result.get('analysis_data', [])
                    
                    # Download images for each analysis item
                    for item in analysis_data:
                        filename = item['filename']
                        
                        # Extract just the filename if it's a full path
                        if '/' in filename:
                            filename = os.path.basename(filename)
                        
                        # Build image URL with correct device-to-capture directory mapping using buildHostImageUrl
                        # Extract capture directory from host device configuration
                        capture_dir = get_device_capture_dir(host_data, device_id)
                        
                        # Use buildHostImageUrl to properly handle nginx port stripping for static files
                        image_path = f"stream/{capture_dir}/captures/{filename}"
                        image_url = buildHostImageUrl(host_data, image_path)
                        print(f"[@query_host_analysis] URL built for {filename}: {image_url} (from host_data: {host_data.get('host_url', 'NO_HOST_URL')})")
                        
                        try:
                            async with session.get(image_url, timeout=aiohttp.ClientTimeout(total=10)) as img_response:
                                if img_response.status == 200:
                                    item['image_data'] = await img_response.read()
                                    item['image_url'] = image_url  # Keep URL for reference
                                else:
                                    print(f"[@query_host_analysis] Failed to download image {filename} from {host_name}: HTTP {img_response.status}")
                                    item['image_data'] = None
                                    item['image_url'] = image_url
                        except Exception as img_error:
                            print(f"[@query_host_analysis] Error downloading image {filename} from {host_name}: {img_error}")
                            item['image_data'] = None
                            item['image_url'] = image_url
                    
                    return {
                        'host_name': host_name,
                        'device_id': device_id,
                        'success': True,
                        'analysis_data': analysis_data,
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
            'host_name': host_name,
            'device_id': device_id,
            'success': False,
            'error': str(e)
        }

def process_host_results(host_results):
    """Process host results and group by timestamp"""
    images_by_timestamp = {}
    images_with_data_by_timestamp = {}  # For background processing with image data
    device_latest_by_bucket = {}
    
    print(f"[@process_host_results] Processing {len(host_results)} host results")
    
    for result in host_results:
        if isinstance(result, Exception):
            print(f"[@process_host_results] Skipping exception result: {result}")
            continue
        if not result.get('success'):
            print(f"[@process_host_results] Skipping failed result: {result.get('error', 'Unknown error')}")
            continue
        
        analysis_data = result.get('analysis_data', [])
        print(f"[@process_host_results] Host {result.get('host_name')} has {len(analysis_data)} analysis items")
        
        for item in analysis_data:
            timestamp = item.get('timestamp', '')
            # Process timestamp for grouping
            
            if timestamp:
                try:
                    # Handle different timestamp formats after migration
                    if isinstance(timestamp, (int, float)) or (isinstance(timestamp, str) and timestamp.isdigit()):
                        # Unix timestamp in milliseconds (from sequential naming)
                        timestamp_seconds = int(timestamp) / 1000.0
                        dt = datetime.fromtimestamp(timestamp_seconds)
                    elif isinstance(timestamp, str) and 'T' in timestamp:
                        # ISO format timestamp (from analysis data after migration)
                        # Remove microseconds if present and parse
                        timestamp_clean = timestamp.split('.')[0] if '.' in timestamp else timestamp
                        dt = datetime.fromisoformat(timestamp_clean.replace('Z', '+00:00'))
                    else:
                        # Fallback for old YYYYMMDDHHMMSS format (should not occur after migration)
                        dt = datetime.strptime(str(timestamp), '%Y%m%d%H%M%S')
                    
                    # Create 10-second buckets for grouping
                    seconds = (dt.second // 10) * 10
                    bucket_dt = dt.replace(second=seconds, microsecond=0)
                    bucket_key = bucket_dt.strftime('%Y%m%d%H%M%S')
                    # Group into 10-second buckets for heatmap generation
                    
                    device_key = f"{result['host_name']}_{result['device_id']}"
                    
                    if bucket_key not in device_latest_by_bucket:
                        device_latest_by_bucket[bucket_key] = {}
                    
                    if (device_key not in device_latest_by_bucket[bucket_key] or 
                        timestamp > device_latest_by_bucket[bucket_key][device_key]['frontend']['timestamp']):
                        
                        # Build image URL
                        host_data = result.get('host_data', {})
                        device_id = result['device_id']
                        filename = item['filename']
                        
                        # Extract just the filename if it's a full path
                        if '/' in filename:
                            filename = os.path.basename(filename)
                        
                        # Build image URL with correct device-to-capture directory mapping using buildHostImageUrl
                        # Extract capture directory from host device configuration
                        capture_dir = get_device_capture_dir(host_data, device_id)
                        
                        # Use buildHostImageUrl to properly handle nginx port stripping for static files
                        image_path = f"stream/{capture_dir}/captures/{filename}"
                        image_url = buildHostImageUrl(host_data, image_path)
                        print(f"[@process_host_results] URL built for {filename}: {image_url} (from host_data: {host_data.get('host_url', 'NO_HOST_URL')})")
                        
                        # Frontend data (without image bytes)
                        frontend_device_data = {
                            'host_name': result['host_name'],
                            'device_id': result['device_id'],
                            'filename': filename,
                            'image_url': image_url,
                            'timestamp': timestamp,
                            'analysis_json': item.get('analysis_json')  # Direct pass-through
                        }
                        
                        # Background processing data (with image bytes)
                        background_device_data = {
                            'host_name': result['host_name'],
                            'device_id': result['device_id'],
                            'filename': filename,
                            'image_url': image_url,
                            'timestamp': timestamp,
                            'analysis_json': item.get('analysis_json'),  # Direct pass-through
                            'image_data': item.get('image_data')  # Image bytes for background processing
                        }
                        
                        device_latest_by_bucket[bucket_key][device_key] = {
                            'frontend': frontend_device_data,
                            'background': background_device_data
                        }
                        
                except Exception as e:
                    print(f"[@process_host_results] Failed to parse timestamp '{timestamp}': {e}")
                    continue
    
    # Separate frontend and background data
    print(f"[@process_host_results] Final buckets: {list(device_latest_by_bucket.keys())}")
    for bucket_key, devices in device_latest_by_bucket.items():
        images_by_timestamp[bucket_key] = [device_data['frontend'] for device_data in devices.values()]
        images_with_data_by_timestamp[bucket_key] = [device_data['background'] for device_data in devices.values()]
    
    print(f"[@process_host_results] Returning {len(images_by_timestamp)} timestamp buckets")
    return images_by_timestamp, images_with_data_by_timestamp

# =====================================================
# HEATMAP ENDPOINTS
# =====================================================

@server_heatmap_bp.route('/getData', methods=['GET'])
def get_data():
    """Get heatmap data (hosts, recent images, incidents) for the team"""
    # Check if Supabase is available, but don't fail if it's not
    supabase_available = check_supabase() is None
    
    # Use default team_id if Supabase is not available
    if supabase_available:
        team_id = get_team_id()
    else:
        team_id = "offline-mode"  # Use a default team_id for offline mode
        print("⚠️ [heatmap:getData] Supabase not available - running in offline mode")
    
    try:
        # Fetch analysis data from hosts
        hosts_devices = get_hosts_devices()
        images_by_timestamp = {}
        
        if hosts_devices:
            # Add small delay to allow analysis processing to complete
            time.sleep(2)
            
            async def query_all_hosts():
                async with aiohttp.ClientSession() as session:
                    tasks = [query_host_analysis(session, hd, 1) for hd in hosts_devices]
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    return results
            
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                host_results = loop.run_until_complete(query_all_hosts())
                loop.close()
            except Exception:
                host_results = []
            
            images_by_timestamp, images_with_data_by_timestamp = process_host_results(host_results)
        
        # Get incidents from database if available, otherwise use empty list
        incidents = []
        if supabase_available:
            try:
                incidents = get_heatmap_incidents(team_id, 1)
            except Exception as e:
                print(f"⚠️ [heatmap:getData] Failed to get incidents from database: {e}")
                incidents = []
        else:
            print("ℹ️ [heatmap:getData] Skipping incident lookup - database not available")
        
        timeline_timestamps = sorted(images_by_timestamp.keys())
        
        frontend_hosts_devices = [
            {
                'host_name': hd['host_name'],
                'device_id': hd['device_id']
            }
            for hd in hosts_devices
        ]
        
        heatmap_data = {
            'hosts_devices': frontend_hosts_devices,
            'images_by_timestamp': images_by_timestamp,
            'incidents': incidents,
            'timeline_timestamps': timeline_timestamps
        }
        
        # Add warning if database features are unavailable
        if not supabase_available:
            heatmap_data['warning'] = 'Database unavailable - history and incident features disabled'
            heatmap_data['offline_mode'] = True
        
        return jsonify(heatmap_data)
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@server_heatmap_bp.route('/generate', methods=['POST'])
def generate():
    """Start heatmap generation job"""
    # Check if Supabase is available, but don't fail if it's not
    supabase_available = check_supabase() is None
    
    # Use default team_id if Supabase is not available
    if supabase_available:
        team_id = get_team_id()
    else:
        team_id = "offline-mode"  # Use a default team_id for offline mode
        print("⚠️ [heatmap:generate] Supabase not available - running in offline mode")
    
    try:
        data = request.get_json() or {}
        timeframe_minutes = data.get('timeframe_minutes', 1)
        
        job_id = create_heatmap_job(timeframe_minutes)
        
        hosts_devices = get_hosts_devices()
        images_by_timestamp = {}
        
        if hosts_devices:
            # Add small delay to allow analysis processing to complete
            time.sleep(2)
            async def query_all_hosts():
                async with aiohttp.ClientSession() as session:
                    tasks = [query_host_analysis(session, hd, timeframe_minutes) for hd in hosts_devices]
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    return results
            
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                host_results = loop.run_until_complete(query_all_hosts())
                loop.close()
            except Exception:
                host_results = []
            
            images_by_timestamp, images_with_data_by_timestamp = process_host_results(host_results)
        
        # Get incidents from database if available, otherwise use empty list
        incidents = []
        if supabase_available:
            try:
                incidents = get_heatmap_incidents(team_id, timeframe_minutes)
            except Exception as e:
                print(f"⚠️ [heatmap:generate] Failed to get incidents from database: {e}")
                incidents = []
        else:
            print("ℹ️ [heatmap:generate] Skipping incident lookup - database not available")
        
        timeline_timestamps = sorted(images_by_timestamp.keys())
        
        frontend_hosts_devices = [
            {
                'host_name': hd['host_name'],
                'device_id': hd['device_id']
            }
            for hd in hosts_devices
        ]
        
        heatmap_data = {
            'hosts_devices': frontend_hosts_devices,
            'images_by_timestamp': images_by_timestamp,
            'incidents': incidents,
            'timeline_timestamps': timeline_timestamps
        }
        
        start_heatmap_generation(
            job_id, 
            images_with_data_by_timestamp,  # Use background data with image bytes
            heatmap_data.get('incidents', []),
            heatmap_data,
            team_id  # Pass team_id to background thread
        )
        
        response_data = {
            'success': True,
            'job_id': job_id,
            'message': 'Heatmap generation started'
        }
        
        # Add warning if database features are unavailable
        if not supabase_available:
            response_data['warning'] = 'Database unavailable - history and incident features disabled'
            response_data['offline_mode'] = True
        
        return jsonify(response_data)
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@server_heatmap_bp.route('/status/<job_id>', methods=['GET'])
def get_status(job_id):
    """Get heatmap generation job status"""
    try:
        status = get_job_status(job_id)
        
        if status:
            return jsonify(status)
        else:
            return jsonify({'error': 'Job not found'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@server_heatmap_bp.route('/cancel/<job_id>', methods=['POST'])
def cancel(job_id):
    """Cancel heatmap generation job"""
    try:
        success = cancel_job(job_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Job cancelled successfully'
            })
        else:
            return jsonify({'error': 'Job not found or cannot be cancelled'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@server_heatmap_bp.route('/history', methods=['GET'])
def get_history():
    """Get recent heatmap reports history"""
    error = check_supabase()
    if error:
        return error
        
    team_id = get_team_id()
    
    try:
        limit = request.args.get('limit', 10, type=int)
        
        from shared.src.lib.supabase.heatmap_db import get_recent_heatmaps
        heatmaps = get_recent_heatmaps(team_id, limit)
        
        # Transform data to match frontend expectations
        reports = []
        for heatmap in heatmaps:
            # Format timestamp for display
            timestamp = heatmap.get('timestamp', '')
            if timestamp:
                try:
                    # Parse timestamp and format for display
                    dt = datetime.strptime(timestamp, '%Y%m%d%H%M%S')
                    formatted_timestamp = dt.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    formatted_timestamp = timestamp
            else:
                formatted_timestamp = 'Unknown'
            
            # Generate report name from timestamp
            report_name = f"Heatmap Report {formatted_timestamp}"
            
            # Format processing time for display
            processing_time = heatmap.get('processing_time')
            if processing_time is not None:
                # Round to 2 decimal places for display
                processing_time = round(float(processing_time), 2)
            
            reports.append({
                'id': heatmap.get('id'),
                'timestamp': formatted_timestamp,
                'name': report_name,
                'html_url': heatmap.get('html_r2_url'),
                'devices_count': heatmap.get('hosts_included', 0),
                'incidents_count': heatmap.get('incidents_count', 0),
                'processing_time': processing_time,
                'created_at': heatmap.get('generated_at')
            })
        
        return jsonify({
            'success': True,
            'reports': reports
        })
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500 