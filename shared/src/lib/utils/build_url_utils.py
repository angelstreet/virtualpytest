"""
Centralized URL Building Utilities

Single source of truth for all URL construction patterns.
Eliminates hardcoded URLs and inconsistent building patterns.
Supports multi-device hosts with device-specific paths.
"""
import os
import requests
import json
import urllib3

# Disable InsecureRequestWarning for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# =====================================================
# CORE URL BUILDING FUNCTION (No Dependencies)
# =====================================================

def call_host(
    host_info: dict,
    endpoint: str,
    method: str = 'POST',
    data: dict = None,
    query_params: dict = None,
    timeout: int = 30,
    extra_headers: dict = None
) -> tuple:
    """
    **SINGLE SOURCE OF TRUTH** for all server-to-host API calls.
    
    This function centralizes:
    - URL building (buildHostUrl)
    - API key injection (X-API-Key header) - the "decorator equivalent" for server side
    - Request execution (requests.post/get)
    - Error handling
    
    This is the server-side equivalent of @app.before_request decorator on host.
    
    Args:
        host_info: Complete host information (from get_host_manager)
        endpoint: The endpoint path (e.g., '/host/monitoring/latest-json')
        method: HTTP method ('GET', 'POST', 'PUT', 'DELETE')
        data: Request body data (dict)
        query_params: URL query parameters (dict)
        timeout: Request timeout in seconds (default: 30)
        extra_headers: Additional headers to include (dict)
        
    Returns:
        Tuple of (response_data, status_code)
        
    Example:
        response_data, status = call_host(
            host_info,
            '/host/monitoring/latest-json',
            method='POST',
            data={'device_id': 'device1'}
        )
    """
    try:
        # Build URL
        full_url = buildHostUrl(host_info, endpoint)
        
        # Prepare request kwargs
        kwargs = {
            'timeout': (60, timeout),  # (connect_timeout, read_timeout)
            'verify': False  # For self-signed certificates
        }
        
        # Add query parameters
        if query_params:
            kwargs['params'] = query_params
        
        # Build headers with automatic API key injection
        headers = {}
        
        # Add Content-Type for POST/PUT with data
        if data and method.upper() in ['POST', 'PUT']:
            headers['Content-Type'] = 'application/json'
            kwargs['json'] = data
        
        # **AUTOMATIC API KEY INJECTION** - the "decorator equivalent" for server side
        # This single line replaces all scattered os.getenv('API_KEY') calls
        api_key = os.getenv('API_KEY')
        if api_key:
            headers['X-API-Key'] = api_key
        else:
            print(f"[@call_host] ⚠️ WARNING: API_KEY not found in environment - request to {endpoint} will fail!")
        
        # Merge with extra headers
        if extra_headers:
            headers.update(extra_headers)
        
        if headers:
            kwargs['headers'] = headers
        
        # Execute request
        method_upper = method.upper()
        if method_upper == 'GET':
            response = requests.get(full_url, **kwargs)
        elif method_upper == 'POST':
            response = requests.post(full_url, **kwargs)
        elif method_upper == 'PUT':
            response = requests.put(full_url, **kwargs)
        elif method_upper == 'DELETE':
            response = requests.delete(full_url, **kwargs)
        else:
            return {
                'success': False,
                'error': f'Unsupported HTTP method: {method}'
            }, 400
        
        # Parse response
        try:
            response_data = response.json()
        except json.JSONDecodeError:
            response_data = {
                'success': False,
                'error': 'Invalid JSON response from host',
                'raw_response': response.text[:500]
            }
        
        return response_data, response.status_code
        
    except requests.exceptions.Timeout:
        return {
            'success': False,
            'error': f'Request to host timed out (timeout={timeout}s)'
        }, 504
    except requests.exceptions.ConnectionError as e:
        return {
            'success': False,
            'error': f'Could not connect to host: {str(e)}'
        }, 503
    except Exception as e:
        return {
            'success': False,
            'error': f'Host call error: {str(e)}'
        }, 500

def _get_nginx_host_url(host_info: dict) -> str:
    """
    Get host URL for nginx static file serving (strips Flask server port)
    
    Args:
        host_info: Host information from registry
        
    Returns:
        Host URL without port for nginx serving (preserves original protocol)
    """
    host_url = host_info.get('host_url', '')
    
    # Strip port numbers but preserve protocol
    if ':' in host_url:
        import re
        # Only strip port numbers, not the protocol
        # Preserves original protocol (http:// stays http://, https:// stays https://)
        host_url = re.sub(r':(\d+)$', '', host_url)
    
    # For local IP addresses without protocol, default to HTTP
    if host_url and ('192.168.' in host_url or '10.' in host_url or '127.0.0.1' in host_url):
        if not host_url.startswith(('http://', 'https://')):
            # No protocol specified, default to HTTP for local IPs
            host_url = f'http://{host_url}'
    
    return host_url

def buildHostUrl(host_info: dict, endpoint: str) -> str:
    """
    Build URL for SERVER-TO-SERVER API calls to host
    
    This function is used by backend servers to call host APIs directly.
    It uses host_api_url (HTTP direct connection) instead of host_url (HTTPS via nginx).
    
    Args:
        host_info: Complete host information (from registration)
        endpoint: The endpoint path to append
        
    Returns:
        Complete URL to the host API endpoint for direct server-to-server communication
        
    Examples:
        # Same network (direct HTTP):
        buildHostUrl(host_data, '/host/av/takeScreenshot')
        -> 'http://192.168.1.34:6109/host/av/takeScreenshot'
        
        # Different networks (HTTPS):
        buildHostUrl(host_data, '/host/av/takeScreenshot')
        -> 'https://remote-host.com/host/av/takeScreenshot'
    """
    if not host_info:
        raise ValueError("host_info is required for buildHostUrl")
    
    # Prefer host_api_url for server-to-server communication (direct, HTTP)
    # Falls back to host_url if host_api_url not available (backward compatibility)
    host_base_url = host_info.get('host_api_url') or host_info.get('host_url')
    
    if not host_base_url:
        raise ValueError(f"Host missing host_api_url and host_url: {host_info.get('host_name', 'unknown')}")
    
    # Clean endpoint
    clean_endpoint = endpoint.lstrip('/')
    
    return f"{host_base_url}/{clean_endpoint}"

# =====================================================
# SPECIALIZED URL BUILDERS
# =====================================================

def buildCaptureUrl(host_info: dict, filename: str, device_id: str) -> str:
    """
    Build URL for live screenshot captures (served by nginx, not Flask)
    
    Args:
        host_info: Host information from registry
        filename: Screenshot filename (sequential format like 'capture_0001.jpg')
        device_id: Device ID for multi-device hosts (required)
        
    Returns:
        Complete URL to screenshot capture
        
    Example:
        buildCaptureUrl(host_info, 'capture_0001.jpg', 'device1')
        -> 'https://host/host/stream/capture1/captures/capture_0001.jpg'
    """
    # Get device-specific capture path
    capture_path = _get_device_capture_path(host_info, device_id)
    
    # For static files (images), prefer host_api_url for server-to-server (Docker internal)
    # Fallback to nginx URL for browser/frontend access
    host_url = host_info.get('host_api_url') or _get_nginx_host_url(host_info)
    
    return f"{host_url}/host{capture_path}/{filename}"

def buildThumbnailUrl(host_info: dict, filename: str, device_id: str) -> str:
    """
    Build URL for thumbnail images (hot/cold architecture - separate folder)
    
    Args:
        host_info: Host information from registry
        filename: Thumbnail filename (e.g., 'capture_0001_thumbnail.jpg')
        device_id: Device ID for multi-device hosts (required)
        
    Returns:
        Complete URL to thumbnail image
        
    Example:
        buildThumbnailUrl(host_info, 'capture_0001_thumbnail.jpg', 'device1')
        -> 'https://host/host/stream/capture1/thumbnails/capture_0001_thumbnail.jpg'
    """
    # Get device-specific stream path (not capture path)
    stream_path = _get_device_stream_path(host_info, device_id)
    
    # For static files, prefer host_api_url for server-to-server (Docker internal)
    # Fallback to nginx URL for browser/frontend access
    host_url = host_info.get('host_api_url') or _get_nginx_host_url(host_info)
    
    # Hot/cold architecture: thumbnails are in separate folder
    return f"{host_url}/host{stream_path}/thumbnails/{filename}"

def buildMetadataUrl(host_info: dict, filename: str, device_id: str) -> str:
    """
    Build URL for metadata JSON files (hot/cold architecture - separate folder)
    
    Args:
        host_info: Host information from registry
        filename: Metadata filename (e.g., 'capture_0001.json')
        device_id: Device ID for multi-device hosts (required)
        
    Returns:
        Complete URL to metadata file
        
    Example:
        buildMetadataUrl(host_info, 'capture_0001.json', 'device1')
        -> 'https://host/host/stream/capture1/metadata/capture_0001.json'
    """
    # Get device-specific stream path
    stream_path = _get_device_stream_path(host_info, device_id)
    
    # For static files, prefer host_api_url for server-to-server (Docker internal)
    # Fallback to nginx URL for browser/frontend access
    host_url = host_info.get('host_api_url') or _get_nginx_host_url(host_info)
    
    # Hot/cold architecture: metadata in separate folder
    return f"{host_url}/host{stream_path}/metadata/{filename}"

def buildCroppedImageUrl(host_info: dict, filename: str, device_id: str) -> str:
    """
    Build URL for cropped images (served by nginx, not Flask)
    
    Args:
        host_info: Host information from registry
        filename: Cropped image filename
        device_id: Device ID for multi-device hosts (required)
        
    Returns:
        Complete URL to cropped image
        
    Example:
        buildCroppedImageUrl(host_info, 'cropped_button_20250117134500.jpg', 'device1')
        -> 'https://host/host/stream/capture1/captures/cropped/cropped_button_20250117134500.jpg'
    """
    # Get device-specific capture path
    capture_path = _get_device_capture_path(host_info, device_id)
    
    # For static files, prefer host_api_url for server-to-server (Docker internal)
    # Fallback to nginx URL for browser/frontend access
    host_url = host_info.get('host_api_url') or _get_nginx_host_url(host_info)
    
    return f"{host_url}/host{capture_path}/cropped/{filename}"

def buildReferenceImageUrl(host_info: dict, device_model: str, filename: str) -> str:
    """
    Build URL for reference images (served by nginx, not Flask)
    
    Args:
        host_info: Host information from registry
        device_model: Device model (e.g., 'android_mobile', 'pixel_7')
        filename: Reference image filename
        
    Returns:
        Complete URL to reference image
        
    Example:
        buildReferenceImageUrl(host_info, 'android_mobile', 'login_button.jpg')
        -> 'https://host/host/stream/resources/android_mobile/login_button.jpg'
    """
    # For static files (images), use nginx (port 80) not Flask server port
    host_url = _get_nginx_host_url(host_info)
    
    return f"{host_url}/host/stream/resources/{device_model}/{filename}"

def buildVerificationResultUrl(host_info: dict, filename: str, device_id: str) -> str:
    """
    Build URL for verification result images (served by nginx, not Flask)
    
    Args:
        host_info: Host information from registry
        filename: Verification result filename
        device_id: Device ID for multi-device hosts (required)
        
    Returns:
        Complete URL to verification result image
        
    Example:
        buildVerificationResultUrl(host_info, 'source_image_0.png', 'device1')
        -> 'https://host/host/stream/capture1/captures/verification_results/source_image_0.png'
    """
    # Get device-specific capture path
    capture_path = _get_device_capture_path(host_info, device_id)
    
    # For static files (images), use nginx (port 80) not Flask server port
    host_url = _get_nginx_host_url(host_info)
    
    return f"{host_url}/host{capture_path}/verification_results/{filename}"

def buildStreamUrl(host_info: dict, device_id: str) -> str:
    """
    Build stream URL for any device (HLS for video devices, direct URL for VNC)
    
    Args:
        host_info: Host information from registry
        device_id: Device ID for multi-device hosts (required)
        
    Returns:
        Complete URL to stream for the device (HLS for video, raw URL for VNC)
        
    Examples:
        buildStreamUrl(host_info, 'device1')
        -> 'https://host:444/host/stream/capture1/segments/output.m3u8'
        
        buildStreamUrl(host_info, 'host_vnc')
        -> 'https://host:444/host/vnc/stream'
    """
    # Check if this is a VNC device
    device = get_device_by_id(host_info, device_id)
    if device and device.get('device_model') == 'host_vnc':
        # For VNC devices, return the video_stream_path directly
        vnc_stream_url = device.get('video_stream_path')
        if not vnc_stream_url:
            raise ValueError(f"VNC device {device_id} has no video_stream_path configured")
        
        # Replace localhost with actual host IP for network accessibility
        if 'localhost' in vnc_stream_url and host_info:
            host_ip = host_info.get('host_ip') or host_info.get('host_name')
            if host_ip:
                vnc_stream_url = vnc_stream_url.replace('localhost', host_ip)
        
        return vnc_stream_url
    else:
        # For regular devices, return HLS stream URL
        # Get device-specific stream path
        stream_path = _get_device_stream_path(host_info, device_id)
        
        # For local access, use relative URLs to avoid CORS and SSL overhead
        # For remote access via nginx proxy, use absolute URLs with proper prefixes
        host_url = host_info.get('host_url', '')
        
        # Check if this is a local IP access (direct to pi4)
        if '192.168.' in host_url or '10.' in host_url or '127.0.0.1' in host_url:
            # Use relative URL for local access - much faster, no CORS issues
            # NEW: Hot/cold architecture - manifest is in segments/ subfolder
            return f"/host{stream_path}/segments/output.m3u8"
        else:
            # Use absolute URL with nginx proxy prefixes for remote access
            nginx_host_url = _get_nginx_host_url(host_info)
            # NEW: Hot/cold architecture - manifest is in segments/ subfolder
            return f"{nginx_host_url}/host{stream_path}/segments/output.m3u8"

def buildHostImageUrl(host_info: dict, image_path: str) -> str:
    """
    Build URL for BROWSER to access images stored on host (nginx-served, not Flask)
    
    This function is used by frontend/browser to fetch static files (images, videos).
    It uses host_url (HTTPS via nginx proxy) instead of host_api_url (direct HTTP).
    
    Args:
        host_info: Host information from registry
        image_path: Relative or absolute image path on host
        
    Returns:
        Complete URL to host-served image for browser access via nginx
        
    Example:
        buildHostImageUrl(host_info, '/stream/captures/screenshot.jpg')
        -> 'https://dev.virtualpytest.com/pi4-server/host/stream/captures/screenshot.jpg'
    """
    # Handle absolute paths by converting to relative
    if image_path.startswith('/var/www/html/'):
        image_path = image_path.replace('/var/www/html/', '')
    
    # Ensure path doesn't start with /
    clean_path = image_path.lstrip('/')
    
    # For static files (images), use host_url (browser access via nginx)
    host_url = _get_nginx_host_url(host_info)
    
    return f"{host_url}/host/{clean_path}"

def buildCloudImageUrl(bucket_name: str, image_path: str, base_url: str) -> str:
    """
    Build URL for images stored in cloud storage (R2, S3, etc.)
    
    Args:
        bucket_name: Cloud storage bucket name
        image_path: Path to image in cloud storage
        base_url: Required base URL (set CLOUDFLARE_R2_PUBLIC_URL env var)
        
    Returns:
        Complete URL to cloud-stored image
        
    Example:
        buildCloudImageUrl('references', 'android_mobile/login_button.jpg', 'https://r2-bucket-url.com')
        -> 'https://r2-bucket-url.com/references/android_mobile/login_button.jpg'
    """
    # Clean the image path
    clean_path = image_path.lstrip('/')
    
    return f"{base_url.rstrip('/')}/{bucket_name}/{clean_path}"

def buildServerUrl(endpoint: str) -> str:
    """
    Host URL builder - Build URLs for server endpoints from host context
    
    Args:
        endpoint: The endpoint path to append
        
    Returns:
        Complete URL to the server endpoint for host use
    """
    import os
    import re
    
    # Host uses SERVER_URL environment variable to reach server
    server_url = os.getenv('SERVER_URL', 'http://localhost:5109')
    
    # Auto-detect local installation and force HTTP instead of HTTPS
    # This prevents SSL connection errors for local development/testing
    if _is_local_installation(server_url):
        original_url = server_url
        server_url = _convert_to_http_for_local(server_url)
        if original_url != server_url:
            print(f"🔄 [URL] Auto-converted local HTTPS to HTTP: {original_url} -> {server_url}")
    
    # Clean endpoint
    clean_endpoint = endpoint.lstrip('/')
    
    return f"{server_url}/{clean_endpoint}"

def _is_local_network_host(host_url: str) -> bool:
    """
    Check if a host URL is on the local network (should use HTTP instead of HTTPS)
    
    Args:
        host_url: The host URL to check
        
    Returns:
        True if the host is on local network, False if remote
    """
    import re
    
    # Extract hostname/IP from URL
    match = re.search(r'://([^:/]+)', host_url)
    if not match:
        return False
    
    hostname = match.group(1).lower()
    
    # Local network patterns
    local_patterns = [
        r'^192\.168\.',      # 192.168.x.x (most common home/office networks)
        r'^10\.',            # 10.x.x.x (corporate networks)
        r'^172\.(1[6-9]|2[0-9]|3[0-1])\.',  # 172.16.x.x - 172.31.x.x (private networks)
        r'^127\.',           # 127.x.x.x (localhost)
        r'^localhost$',      # localhost
        r'^.*\.local$',      # .local domains (mDNS)
    ]
    
    # Check if hostname matches any local pattern
    for pattern in local_patterns:
        if re.match(pattern, hostname):
            return True
    
    return False

def _is_local_installation(server_url: str) -> bool:
    """
    Detect if this is a local installation that should use HTTP instead of HTTPS.
    
    Args:
        server_url: The server URL to check
        
    Returns:
        True if this appears to be a local installation
    """
    import re
    
    if not server_url:
        return True
    
    # Convert to lowercase for checking
    url_lower = server_url.lower()
    
    # Local indicators
    local_patterns = [
        'localhost',
        '127.0.0.1',
        '0.0.0.0',
        # Private IP ranges (RFC 1918)
        r'192\.168\.\d+\.\d+',
        r'10\.\d+\.\d+\.\d+', 
        r'172\.(1[6-9]|2[0-9]|3[0-1])\.\d+\.\d+',
        # Link-local addresses
        r'169\.254\.\d+\.\d+',
        # Docker/container common addresses
        r'172\.17\.\d+\.\d+',
        r'172\.18\.\d+\.\d+',
    ]
    
    # Check for local patterns
    for pattern in local_patterns:
        if re.search(pattern, url_lower):
            return True
    
    # Check for development/local domains
    local_domains = [
        '.local',
        '.localhost',
        '.dev',
        '.test',
        'virtualpytest-local',
    ]
    
    for domain in local_domains:
        if domain in url_lower:
            return True
    
    return False

def _convert_to_http_for_local(server_url: str) -> str:
    """
    Convert HTTPS URLs to HTTP for local installations.
    
    Args:
        server_url: The server URL to convert
        
    Returns:
        HTTP version of the URL for local use
    """
    import re
    
    if not server_url:
        return 'http://localhost:5109'
    
    # If already HTTP, return as-is
    if server_url.startswith('http://'):
        return server_url
    
    # Convert HTTPS to HTTP
    if server_url.startswith('https://'):
        http_url = server_url.replace('https://', 'http://', 1)
        
        # For local installations, also check if we need to adjust the port
        # HTTPS typically uses 443, but local HTTP servers often use different ports
        if ':443' in http_url or http_url.endswith(':443'):
            # Replace 443 with common local server port
            http_url = http_url.replace(':443', ':5109')
        elif not re.search(r':\d+', http_url.split('//')[1]):
            # No port specified, add default local server port
            # Extract the domain part and add port
            parts = http_url.split('/')
            if len(parts) >= 3:
                domain_part = parts[2]
                if ':' not in domain_part:
                    parts[2] = f"{domain_part}:5109"
                    http_url = '/'.join(parts)
        
        return http_url
    
    # If no protocol specified, assume HTTP for local
    if not server_url.startswith(('http://', 'https://')):
        # Add http:// prefix and ensure port is specified
        if ':' not in server_url:
            return f"http://{server_url}:5109"
        else:
            return f"http://{server_url}"
    
    return server_url

# =====================================================
# MULTI-DEVICE HELPER FUNCTIONS
# =====================================================

def get_device_local_captures_path(host_info: dict, device_id: str) -> str:
    """
    Get device-specific local captures path for file system operations.
    
    Args:
        host_info: Host information from registry
        device_id: Device ID (required - no fallbacks)
        
    Returns:
        Local file system path for captures from device configuration (DEVICE1_VIDEO_CAPTURE_PATH)
        
    Raises:
        ValueError: If device configuration or capture path is not found
    """
    if not host_info:
        raise ValueError("host_info is required for device path resolution")
    
    if not device_id:
        raise ValueError("device_id is required - no fallbacks allowed")
    
    # Get devices configuration from host_info
    devices = host_info.get('devices', [])
    if not devices:
        raise ValueError(f"No devices configured in host_info for device_id: {device_id}")
    
    # Find the specific device
    for device in devices:
        if device.get('device_id') == device_id:
            capture_path = device.get('video_capture_path')
            if not capture_path:
                raise ValueError(f"Device {device_id} has no video_capture_path configured (DEVICE{device_id.replace('device', '')}_VIDEO_CAPTURE_PATH missing)")
            
            print(f"[@build_url_utils:get_device_local_captures_path] Using device {device_id} capture path: {capture_path}")
            return capture_path
    
    raise ValueError(f"Device {device_id} not found in host configuration. Available devices: {[d.get('device_id') for d in devices]}")

def get_device_local_stream_path(host_info: dict, device_id: str) -> str:
    """
    Get device-specific local stream path for file system operations.
    
    Args:
        host_info: Host information from registry
        device_id: Device ID (required - no fallbacks)
        
    Returns:
        Local file system path for stream from device configuration (DEVICE1_VIDEO_STREAM_PATH)
        
    Raises:
        ValueError: If device configuration or stream path is not found
    """
    if not host_info:
        raise ValueError("host_info is required for device path resolution")
    
    if not device_id:
        raise ValueError("device_id is required - no fallbacks allowed")
    
    # Get devices configuration from host_info
    devices = host_info.get('devices', [])
    if not devices:
        raise ValueError(f"No devices configured in host_info for device_id: {device_id}")
    
    # Find the specific device
    for device in devices:
        if device.get('device_id') == device_id:
            stream_path = device.get('video_stream_path')
            if not stream_path:
                raise ValueError(f"Device {device_id} has no video_stream_path configured (DEVICE{device_id.replace('device', '')}_VIDEO_STREAM_PATH missing)")
            
            # Convert URL path to local file system path
            # Remove '/host' prefix and convert to absolute path
            clean_path = stream_path.replace('/host', '')
            local_path = f'/var/www/html{clean_path}'
            
            print(f"[@build_url_utils:get_device_local_stream_path] Using device {device_id} stream path: {local_path}")
            return local_path
    
    raise ValueError(f"Device {device_id} not found in host configuration. Available devices: {[d.get('device_id') for d in devices]}")

def get_device_local_thumbnails_path(capture_path: str) -> str:
    """
    Get local thumbnails path from a capture image path.
    HOT/COLD ARCHITECTURE: Thumbnails are in /thumbnails/ folder (sibling to /captures/)
    
    Args:
        capture_path: Full path to capture image (e.g., /var/www/html/stream/capture1/captures/image.jpg)
        
    Returns:
        Local file system path to thumbnails folder (e.g., /var/www/html/stream/capture1/thumbnails)
        
    Example:
        get_device_local_thumbnails_path('/var/www/html/stream/capture1/captures/image.jpg')
        -> '/var/www/html/stream/capture1/thumbnails'
    """
    # Get parent directory of captures folder
    captures_dir = os.path.dirname(capture_path)  # /var/www/html/stream/captureX/captures
    device_dir = os.path.dirname(captures_dir)    # /var/www/html/stream/captureX
    thumbnails_dir = os.path.join(device_dir, 'thumbnails')
    
    return thumbnails_dir

def get_device_directory_from_captures(captures_dir: str) -> str:
    """
    Get device base directory from captures directory.
    HOT/COLD ARCHITECTURE: Device dir is parent of /captures/, /thumbnails/, /segments/
    
    Args:
        captures_dir: Full path to captures directory (e.g., /var/www/html/stream/capture1/captures)
        
    Returns:
        Device base directory (e.g., /var/www/html/stream/capture1)
        
    Example:
        get_device_directory_from_captures('/var/www/html/stream/capture1/captures')
        -> '/var/www/html/stream/capture1'
    """
    # Remove trailing slash if present
    captures_dir = captures_dir.rstrip('/')
    
    # Get parent directory (device base)
    device_dir = os.path.dirname(captures_dir)
    
    return device_dir

def get_current_device_id() -> str:
    """
    Get the current device ID from Flask app context.
    This helps routes determine which device they're working with.
    
    Returns:
        Device ID (e.g., 'device1', 'device2') or raises error if not available
    """
    try:
        from flask import current_app, request
        
        # First try to get device_id from request parameters
        if request and request.method in ['POST', 'GET']:
            if request.method == 'POST' and request.is_json:
                data = request.get_json() or {}
                device_id = data.get('device_id')
                if device_id:
                    return device_id
            elif request.method == 'GET':
                device_id = request.args.get('device_id')
                if device_id:
                    return device_id
        
        # No fallbacks - device_id must be explicitly provided
        raise ValueError("device_id is required in request parameters - no fallbacks allowed")
        
    except Exception as e:
        print(f"[@build_url_utils:get_current_device_id] Error getting device ID: {e}")
        raise ValueError("device_id is required in request parameters - no fallbacks allowed")

def _get_device_stream_path(host_info: dict, device_id: str) -> str:
    """
    Get device-specific stream path from host configuration.
    
    Args:
        host_info: Host information from registry
        device_id: Device ID (required - no fallbacks)
        
    Returns:
        Stream path for the device from device configuration (DEVICE1_VIDEO_STREAM_PATH)
        
    Raises:
        ValueError: If device configuration or stream path is not found
    """
    if not host_info:
        raise ValueError("host_info is required for device path resolution")
    
    if not device_id:
        raise ValueError("device_id is required - no fallbacks allowed")
    
    # Get devices configuration from host_info
    devices = host_info.get('devices', [])
    if not devices:
        raise ValueError(f"No devices configured in host_info for device_id: {device_id}")
    
    # Find the specific device
    for device in devices:
        if device.get('device_id') == device_id:
            stream_path = device.get('video_stream_path')
            if not stream_path:
                raise ValueError(f"Device {device_id} has no video_stream_path configured (DEVICE{device_id.replace('device', '')}_VIDEO_STREAM_PATH missing)")
            
            # Remove '/host' prefix if present and ensure starts with /
            clean_path = stream_path.replace('/host', '').lstrip('/')
            url_path = f'/{clean_path}'
            
            print(f"[@build_url_utils:_get_device_stream_path] Using device {device_id} stream path: {url_path}")
            return url_path
    
    raise ValueError(f"Device {device_id} not found in host configuration. Available devices: {[d.get('device_id') for d in devices]}")

def _get_device_capture_path(host_info: dict, device_id: str) -> str:
    """
    Get device-specific capture path from host configuration.
    
    Args:
        host_info: Host information from registry
        device_id: Device ID (required - no fallbacks)
        
    Returns:
        Capture path for the device from device configuration (DEVICE1_VIDEO_STREAM_PATH + /captures)
        
    Raises:
        ValueError: If device configuration or stream path is not found
    """
    if not host_info:
        raise ValueError("host_info is required for device path resolution")
    
    if not device_id:
        raise ValueError("device_id is required - no fallbacks allowed")
    
    # Get devices configuration from host_info
    devices = host_info.get('devices', [])
    if not devices:
        raise ValueError(f"No devices configured in host_info for device_id: {device_id}")
    
    # Find the specific device
    for device in devices:
        if device.get('device_id') == device_id:
            # Special handling for VNC devices - they use video_capture_path directly
            if device.get('device_model') == 'host_vnc':
                capture_path = device.get('video_capture_path')
                if not capture_path:
                    raise ValueError(f"VNC device {device_id} has no video_capture_path configured")
                
                # Convert capture path to URL path format
                url_path = capture_path.replace('/var/www/html', '')
                if not url_path.startswith('/'):
                    url_path = f'/{url_path}'
                
                # Add /captures suffix if not already present
                if not url_path.endswith('/captures'):
                    url_path = f'{url_path}/captures'
                
                return url_path
            else:
                # Regular devices derive capture path from video_stream_path
                stream_path = device.get('video_stream_path')
                if not stream_path:
                    raise ValueError(f"Device {device_id} has no video_stream_path configured (DEVICE{device_id.replace('device', '')}_VIDEO_STREAM_PATH missing)")
                
                # Remove '/host' prefix if present and ensure starts with /
                clean_path = stream_path.replace('/host', '').lstrip('/')
                url_path = f'/{clean_path}/captures'
                
                return url_path
    
    raise ValueError(f"Device {device_id} not found in host configuration. Available devices: {[d.get('device_id') for d in devices]}")

def get_device_by_id(host_info: dict, device_id: str) -> dict:
    """
    Get device configuration by device ID.
    
    Args:
        host_info: Host information from registry
        device_id: Device ID to find (e.g., 'device1', 'device2')
        
    Returns:
        Device configuration dictionary or None if not found
    """
    if not host_info or not device_id:
        return None
    
    devices = host_info.get('devices', [])
    
    for device in devices:
        if device.get('device_id') == device_id:
            return device
    
    return None

def buildCaptureUrlFromPath(host_info: dict, capture_path: str, device_id: str) -> str:
    """
    Build URL for capture from a local file path by extracting filename
    
    Args:
        host_info: Host information from registry
        capture_path: Local file path to capture (e.g., '/path/capture_0001.jpg')
        device_id: Device ID for multi-device hosts (required)
        
    Returns:
        Complete URL to capture
        
    Raises:
        ValueError: If filename cannot be extracted from path
        
    Example:
        buildCaptureUrlFromPath(host_info, '/tmp/capture_0001.jpg', 'device1')
        -> 'https://host:444/host/stream/capture1/captures/capture_0001.jpg'
    """
    import os
    
    # Extract filename from capture path
    filename = os.path.basename(capture_path)
    # Allow 'verification_source.jpg' (fixed name for verification persistence) or standard 'capture_*' format
    if not (filename.startswith('capture_') or filename == 'verification_source.jpg'):
        raise ValueError(f'Invalid capture filename format: {filename}')
    
    # Use existing buildCaptureUrl function
    return buildCaptureUrl(host_info, filename, device_id)


def resolveCaptureFilePath(filename: str) -> str:
    """
    Resolve local file path for a capture filename
    
    Args:
        filename: Capture filename (e.g., 'capture_0001.jpg')
        
    Returns:
        Local file path to capture
        
    Raises:
        ValueError: If filename is invalid or unsafe
        
    Example:
        resolveCaptureFilePath('capture_0001.jpg')
        -> '/tmp/captures/capture_0001.jpg'
    """
    # Security validation - ensure the path is safe
    if '..' in filename or filename.startswith('/'):
        raise ValueError(f'Invalid filename: {filename}')
    
    # Extract the base filename without query parameters
    base_filename = filename.split('?')[0]
    
    # Use host's tmp directory for captures
    capture_path = f"/tmp/captures/{base_filename}"
    
    return capture_path

def resolveImageFilePath(image_path: str) -> str:
    """
    Resolve and validate local file path for an image
    
    Args:
        image_path: Image path from request
        
    Returns:
        Validated local file path to image
        
    Raises:
        ValueError: If path is invalid, unsafe, or not allowed
        
    Example:
        resolveImageFilePath('/tmp/verification_results/source_image_0.png')
        -> '/tmp/verification_results/source_image_0.png'
    """
    if not image_path:
        raise ValueError('No image path specified')
    
    # Security check - allow /tmp/ paths and project paths
    project_root = os.getenv('PROJECT_ROOT', '/home/pi/virtualpytest')  # fallback for compatibility
    allowed_paths = ['/tmp/', project_root, '/var/www/html/']
    
    if not any(image_path.startswith(path) for path in allowed_paths):
        raise ValueError(f'Invalid image path: {image_path}. Allowed paths: {allowed_paths}')
    
    return image_path


def convertHostUrlToLocalPath(host_url: str) -> str:
    """
    Convert a host URL back to local file system path.
    This is the reverse operation of buildHostImageUrl.
    
    Args:
        host_url: Host URL (e.g., 'https://host.com/host/stream/capture1/captures/image.jpg')
        
    Returns:
        Local file system path (e.g., '/var/www/html/stream/capture1/captures/image.jpg')
        
    Raises:
        ValueError: If URL format is invalid or unsafe
        
    Example:
        convertHostUrlToLocalPath('https://host.com/host/stream/capture1/captures/image.jpg')
        -> '/var/www/html/stream/capture1/captures/image.jpg'
    """
    if not host_url:
        raise ValueError("host_url is required")
    
    from urllib.parse import urlparse
    
    try:
        parsed_url = urlparse(host_url)
        url_path = parsed_url.path
        
        # Handle URLs that are missing /host/ prefix (common issue with server port URLs)
        if '/host/' not in url_path:
            # Check if this looks like a direct nginx path (starts with /stream/, /captures/, etc.)
            if url_path.startswith(('/stream/', '/captures/', '/resources/')):
                # This is a direct nginx path, just convert to local path
                relative_path = url_path.lstrip('/')
                local_path = f"/var/www/html/{relative_path}"
                return local_path
            else:
                raise ValueError(f"Invalid host URL format - expected /host/ in path or direct nginx path: {host_url}")
        
        # Find and remove everything up to and including '/host/' to get the relative path
        host_index = url_path.find('/host/')
        relative_path = url_path[host_index + 6:]  # Remove everything up to and including '/host/'
        
        # Security validation - prevent path traversal
        if '..' in relative_path or relative_path.startswith('/'):
            raise ValueError(f"Unsafe path detected in URL: {host_url}")
        
        # Convert to absolute local path using nginx document root
        local_path = f"/var/www/html/{relative_path}"
        
        return local_path
        
    except Exception as e:
        raise ValueError(f"Failed to convert host URL to local path: {e}")

def buildScriptReportUrl(device_model: str, script_name: str, timestamp: str, base_url: str = None) -> str:
    """
    Build URL for script reports stored in cloud storage (R2).
    
    Args:
        device_model: Device model (e.g., 'android_mobile')
        script_name: Script name (e.g., 'validation')
        timestamp: Timestamp in YYYYMMDDHHMMSS format
        base_url: Optional custom base URL (defaults to R2)
        
    Returns:
        Complete URL to script report
        
    Example:
        buildScriptReportUrl('android_mobile', 'validation', '20250117134500')
        -> 'https://r2-bucket-url/script-reports/android_mobile/validation_20250117_20250117134500/report.html'
    """
    if base_url is None:
        # Use environment variable for R2 public URL
        import os
        base_url = os.environ.get('CLOUDFLARE_R2_PUBLIC_URL', 'https://your-r2-domain.com')
    
    # Create folder structure: script-reports/{device_model}/{script_name}_{date}_{timestamp}/
    date_str = timestamp[:8]  # YYYYMMDD from YYYYMMDDHHMMSS
    folder_name = f"{script_name}_{date_str}_{timestamp}"
    report_path = f"script-reports/{device_model}/{folder_name}/report.html"
    
    # Clean the base URL and build complete URL
    clean_base_url = base_url.rstrip('/')
    
    return f"{clean_base_url}/{report_path}"