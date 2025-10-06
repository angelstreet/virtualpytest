/**
 * Centralized URL Building Utilities (Frontend)
 *
 * Single source of truth for all URL construction patterns.
 * Mirrors the Python buildUrlUtils.py for consistency.
 *
 * CRITICAL: Always use these functions for URL building to ensure:
 * - Environment-specific configuration (dev vs prod)
 * - Consistent URL patterns across the application
 * - Easy maintenance and debugging
 * - Proper routing in different deployment scenarios
 *
 * URL Building Categories:
 * 1. Server URLs - Backend API endpoints (buildServerUrl)
 * 2. Host URLs - Direct device communication (buildHostUrl)
 * 3. Image URLs - Static assets and captures (buildHostImageUrl, buildCloudImageUrl)
 * 4. Stream URLs - Live video streams (buildStreamUrl)
 */

// =====================================================
// SERVER URL BUILDING (Frontend to Backend Server)
// =====================================================


export const buildServerUrl = (endpoint: string): string => {
  // Try to get selected server from localStorage first, fallback to env variable
  let serverUrl: string;
  try {
    const selectedServer = localStorage.getItem('selectedServer');
    serverUrl = selectedServer || (import.meta as any).env?.VITE_SERVER_URL || 'http://localhost:5109';
  } catch {
    // Fallback if localStorage is not available
    serverUrl = (import.meta as any).env?.VITE_SERVER_URL || 'http://localhost:5109';
  }
  
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint.slice(1) : endpoint;
  const url = `${serverUrl}/${cleanEndpoint}`;
  
  // Always add team_id to all server URLs
  const teamId = "7fdeb4bb-3639-4ec3-959f-b54769a219ce";
  return `${url}${url.includes('?') ? '&' : '?'}team_id=${teamId}`;
};

/**
 * Get all configured server URLs (primary + slaves)
 * Reads VITE_SERVER_URL and VITE_SLAVE_SERVER_URL
 */
export const getAllServerUrls = (): string[] => {
  const urls: string[] = [];
  
  // Primary server (always first)
  const primaryUrl = (import.meta as any).env?.VITE_SERVER_URL;
  if (primaryUrl && typeof primaryUrl === 'string') {
    urls.push(primaryUrl);
  }
  
  // Slave servers (can be multiple URLs)
  const slaveUrls = (import.meta as any).env?.VITE_SLAVE_SERVER_URL;
  if (slaveUrls && typeof slaveUrls === 'string') {
    try {
      // Try to parse as JSON array first
      const parsedUrls = JSON.parse(slaveUrls);
      if (Array.isArray(parsedUrls)) {
        urls.push(...parsedUrls.filter(url => typeof url === 'string'));
      } else {
        // If not an array, treat as single URL
        urls.push(slaveUrls);
      }
    } catch (error) {
      // If JSON parsing fails, try comma-separated values
      const commaSeparated = slaveUrls.split(',').map(url => url.trim()).filter(url => url.length > 0);
      urls.push(...commaSeparated);
    }
  }
  
  // Fallback to localhost if no URLs configured
  if (urls.length === 0) {
    urls.push('http://localhost:5109');
  }
  
  console.log('getAllServerUrls:', urls);
  return urls;
};

/**
 * Build URL for specific server with team_id
 * @param serverUrl - The server base URL
 * @param endpoint - API endpoint
 * @returns Complete URL with team_id
 */
export const buildServerUrlForServer = (serverUrl: string, endpoint: string): string => {
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint.slice(1) : endpoint;
  const url = `${serverUrl}/${cleanEndpoint}`;
  
  // Always add team_id to all server URLs
  const teamId = "7fdeb4bb-3639-4ec3-959f-b54769a219ce";
  return `${url}${url.includes('?') ? '&' : '?'}team_id=${teamId}`;
};

/**
 * Build URL using a specific selected server
 * @param endpoint - API endpoint
 * @param selectedServerUrl - The currently selected server URL
 * @returns Complete URL with team_id
 */
export const buildSelectedServerUrl = (endpoint: string, selectedServerUrl: string): string => {
  return buildServerUrlForServer(selectedServerUrl, endpoint);
};

// =====================================================
// HOST URL BUILDING (Frontend to Device Hosts)
// =====================================================

/**
 * Build host URL for direct host communication (Frontend to host)
 * Core implementation for all host-based URL building
 */
const internalBuildHostUrl = (host: any, endpoint: string): string => {
  if (!host) {
    throw new Error('Host information is required for buildHostUrl');
  }

  const cleanEndpoint = endpoint.startsWith('/') ? endpoint.slice(1) : endpoint;

  // Use host_url if available (most efficient)
  if (host.host_url) {
    let hostUrl = host.host_url;
    
    // For static files (images, streams), strip port ONLY for direct local IP addresses
    // This logic is not needed when hosts register with proper nginx proxy URLs
    if (endpoint.includes('host/stream/') || endpoint.includes('host/captures/')) {
      const isDirectLocalIp = hostUrl.match(/^https?:\/\/(192\.168\.|10\.|127\.0\.0\.1)/);
      if (isDirectLocalIp && hostUrl.includes(':')) {
        hostUrl = hostUrl.replace(/:\d+$/, '');
      }
    }
    
    return `${hostUrl}/${cleanEndpoint}`;
  }

  throw new Error('Host must have either host_url or both host_ip and host_port');
};

/**
 * Build URL for live screenshot captures
 * Supports device-specific capture paths for multi-device hosts
 */
export const buildCaptureUrl = (host: any, timestamp: string, deviceId?: string): string => {
  if (!deviceId) {
    throw new Error('deviceId is required for buildCaptureUrl');
  }
  // Get device-specific capture path
  const capturePath = getDeviceCaptureUrlPath(host, deviceId);
  return internalBuildHostUrl(host, `host${capturePath}/capture_${timestamp}.jpg`);
};

/**
 * Build URL for cropped images
 * Supports device-specific capture paths for multi-device hosts
 */
export const buildCroppedImageUrl = (host: any, filename: string, deviceId?: string): string => {
  if (!deviceId) {
    throw new Error('deviceId is required for buildCroppedImageUrl');
  }
  // Get device-specific capture path
  const capturePath = getDeviceCaptureUrlPath(host, deviceId);
  return internalBuildHostUrl(host, `host${capturePath}/cropped/${filename}`);
};

/**
 * Build URL for reference images
 */
export const buildReferenceImageUrl = (
  host: any,
  deviceModel: string,
  filename: string,
  deviceId?: string,
): string => {
  if (!deviceId) {
    throw new Error('deviceId is required for buildReferenceImageUrl');
  }
  // Get device-specific capture path as base for resources
  const capturePath = getDeviceCaptureUrlPath(host, deviceId);
  return internalBuildHostUrl(host, `host${capturePath}/resources/${deviceModel}/${filename}`);
};

/**
 * Build URL for verification result images
 */
export const buildVerificationResultUrl = (host: any, resultsPath: string): string => {
  // Convert local path to URL path
  const urlPath = resultsPath.replace('/var/www/html/', '');
  // Add host/ prefix like other image URLs (cropping, captures, etc.)
  return internalBuildHostUrl(host, `host/${urlPath}`);
};

/**
 * Build URL for HLS stream
 * Supports device-specific stream paths for multi-device hosts
 */
export const buildStreamUrl = (host: any, deviceId?: string): string => {
  console.log('[buildStreamUrl] Starting stream URL construction', {
    hostName: host?.host_name,
    hostUrl: host?.host_url,
    hostIp: host?.host_ip,
    hostPort: host?.host_port,
    deviceId,
    devicesCount: host?.devices?.length || 0
  });

  if (!deviceId) {
    console.error('[buildStreamUrl] deviceId is required but not provided');
    throw new Error('deviceId is required for buildStreamUrl');
  }

  try {
    // Get device-specific stream path
    const streamPath = getDeviceStreamUrlPath(host, deviceId);
    console.log('[buildStreamUrl] Device stream path resolved', {
      deviceId,
      streamPath
    });

    // NEW: Manifest is in segments/ subfolder (hot/cold architecture)
    const fullEndpoint = `host${streamPath}/segments/output.m3u8`;
    const finalUrl = internalBuildHostUrl(host, fullEndpoint);
    
    console.log('[buildStreamUrl] Stream URL constructed successfully', {
      deviceId,
      streamPath,
      fullEndpoint,
      finalUrl
    });

    return finalUrl;
  } catch (error) {
    console.error('[buildStreamUrl] Failed to construct stream URL', {
      deviceId,
      hostName: host?.host_name,
      error: error instanceof Error ? error.message : error
    });
    throw error;
  }
};

/**
 * Build URL for host API endpoints (Flask routes)
 */
export const buildHostUrl = (host: any, endpoint: string): string => {
  return internalBuildHostUrl(host, endpoint);
};

/**
 * Build URL for any image stored on the host (nginx-served)
 * This replaces the scattered local buildImageUrl functions
 */
export const buildHostImageUrl = (host: any, imagePath: string): string => {
  if (!imagePath) return '';

  // If it's already a complete URL, return as is
  if (imagePath.startsWith('http://') || imagePath.startsWith('https://')) {
    return imagePath;
  }

  // Handle absolute paths by converting to relative
  let cleanPath = imagePath;
  if (cleanPath.startsWith('/var/www/html/')) {
    cleanPath = cleanPath.replace('/var/www/html/', '');
  }

  // Ensure path doesn't start with / for buildHostUrl
  cleanPath = cleanPath.startsWith('/') ? cleanPath.slice(1) : cleanPath;

  // Use buildHostUrl for relative URLs
  if (host?.host_name) {
    return internalBuildHostUrl(host, `host/${cleanPath}`);
  }

  // Fallback if no host selected
  return imagePath;
};

/**
 * Build thumbnail URL from freeze frame filename and original image URL
 * HOT/COLD ARCHITECTURE: Thumbnails are in /thumbnails/ folder
 * 
 * Converts paths like:
 *   /host/stream/capture3/captures/image.jpg → /host/stream/capture3/thumbnails/image_thumbnail.jpg
 *   /host/stream/capture3/metadata/image.json → /host/stream/capture3/thumbnails/image_thumbnail.jpg
 * 
 * @param filename - Frame filename (e.g., "capture_000139798.jpg" or full path)
 * @param originalImageUrl - Original image URL to extract device path from
 * @returns Complete URL to thumbnail in /thumbnails/ folder
 */
export const buildThumbnailUrlFromFrame = (filename: string, originalImageUrl: string): string => {
  // Extract just the filename if it's a full path
  const cleanFilename = filename.includes('/') ? filename.split('/').pop() || filename : filename;
  
  // Ensure it has _thumbnail suffix
  const thumbnailFilename = cleanFilename.includes('_thumbnail.jpg')
    ? cleanFilename
    : cleanFilename.replace('.jpg', '_thumbnail.jpg');
  
  // Extract base URL and device path from original image URL
  // Example: https://dev.virtualpytest.com/pi2/host/stream/capture3/captures/image.jpg
  //       -> https://dev.virtualpytest.com/pi2/host/stream/capture3/
  const urlParts = originalImageUrl.split('/');
  
  if (urlParts.length < 2) {
    console.warn('[buildThumbnailUrlFromFrame] Invalid original URL format:', originalImageUrl);
    return thumbnailFilename;
  }
  
  // Remove filename and folder name (captures, metadata, etc.)
  urlParts.pop(); // Remove filename
  urlParts.pop(); // Remove folder (captures, metadata, etc.)
  
  // Build base URL to device root (e.g., .../host/stream/capture3/)
  const deviceBaseUrl = urlParts.join('/');
  
  // HOT/COLD ARCHITECTURE: Thumbnails are in /thumbnails/ folder
  const thumbnailUrl = `${deviceBaseUrl}/thumbnails/${thumbnailFilename}`;
  
  console.log(`[buildThumbnailUrlFromFrame] ${filename} → ${thumbnailUrl}`);
  return thumbnailUrl;
};

/**
 * Build URL for images stored in cloud storage (R2, S3, etc.)
 */
export const buildCloudImageUrl = (
  bucketName: string,
  imagePath: string,
  baseUrl: string,
): string => {
  // Clean the image path
  const cleanPath = imagePath.startsWith('/') ? imagePath.slice(1) : imagePath;

  return `${baseUrl.replace(/\/$/, '')}/${bucketName}/${cleanPath}`;
};

/**
 * Convert thumbnail path to usable URL
 * - If already a URL (http/https) → return as-is
 * - If local path (/var/www/html) → convert to host URL
 */
export const buildThumbnailUrl = (thumbnailPath: string, host: any): string => {
  if (thumbnailPath.startsWith('http://') || thumbnailPath.startsWith('https://')) {
    return thumbnailPath;
  }
  
  return buildHostImageUrl(host, thumbnailPath);
};

// =====================================================
// MULTI-DEVICE HELPER FUNCTIONS (Frontend)
// =====================================================

/**
 * Get device-specific stream URL path from host configuration.
 * Mirrors the Python _get_device_stream_path function.
 */
const getDeviceStreamUrlPath = (host: any, deviceId: string): string => {
  if (!host) {
    throw new Error('Host information is required for device stream path resolution');
  }

  if (!deviceId) {
    throw new Error('deviceId is required - no fallbacks allowed');
  }

  // Get devices configuration from host
  const devices = host?.devices || [];
  if (!devices.length) {
    throw new Error(`No devices configured in host configuration for device_id: ${deviceId}`);
  }

  // Find the specific device
  for (const device of devices) {
    if (device?.device_id === deviceId) {
      const streamPath = device?.video_stream_path;
      if (!streamPath) {
        throw new Error(`Device ${deviceId} has no video_stream_path configured`);
      }

      // Remove '/host' prefix if present and ensure starts with /
      const cleanPath = streamPath.replace('/host', '').replace(/^\/+/, '/');
      return cleanPath;
    }
  }

  const availableDevices = devices.map((d: any) => d?.device_id).filter(Boolean);
  throw new Error(
    `Device ${deviceId} not found in host configuration. Available devices: ${availableDevices.join(', ')}`,
  );
};

/**
 * Get device-specific capture URL path from host configuration.
 * Uses video_capture_path from device configuration.
 */
const getDeviceCaptureUrlPath = (host: any, deviceId: string): string => {
  if (!host) {
    throw new Error('Host information is required for device capture path resolution');
  }

  if (!deviceId) {
    throw new Error('deviceId is required - no fallbacks allowed');
  }

  // Get devices configuration from host
  const devices = host?.devices || [];
  if (!devices.length) {
    throw new Error(`No devices configured in host configuration for device_id: ${deviceId}`);
  }

  // Find the specific device
  for (const device of devices) {
    if (device?.device_id === deviceId) {
      const capturePath = device?.video_capture_path;
      if (!capturePath) {
        throw new Error(`Device ${deviceId} has no video_capture_path configured`);
      }

      // Convert local path to URL path by removing '/var/www/html' prefix
      let urlPath = capturePath.replace('/var/www/html', '').replace(/^\/+/, '/');
      
      // Add /captures suffix if not already present
      if (!urlPath.endsWith('/captures')) {
        urlPath = `${urlPath}/captures`;
      }
      
      return urlPath;
    }
  }

  const availableDevices = devices.map((d: any) => d?.device_id).filter(Boolean);
  throw new Error(
    `Device ${deviceId} not found in host configuration. Available devices: ${availableDevices.join(', ')}`,
  );
};

