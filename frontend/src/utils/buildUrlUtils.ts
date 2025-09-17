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

/**
 * Build server URL for backend API endpoints (Frontend to backend_server)
 * 
 * Uses VITE_SERVER_URL environment variable to determine the backend server location.
 * This ensures requests go to the correct backend regardless of deployment environment.
 * 
 * Examples:
 * - Development: buildServerUrl('/server/control/lockedDevices') 
 *   → http://localhost:5109/server/control/lockedDevices
 * - Production: buildServerUrl('/server/control/lockedDevices')
 *   → https://virtualpytest.onrender.com/server/control/lockedDevices
 * 
 * @param endpoint - API endpoint (e.g., '/server/control/lockedDevices')
 * @returns Complete URL to backend server endpoint
 */
export const buildServerUrl = (endpoint: string): string => {
  const serverUrl = (import.meta as any).env?.VITE_SERVER_URL || 'http://localhost:5109';
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint.slice(1) : endpoint;
  return `${serverUrl}/${cleanEndpoint}`;
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

  // Use host_url if available (most efficient)
  if (host.host_url) {
    const cleanEndpoint = endpoint.startsWith('/') ? endpoint.slice(1) : endpoint;
    return `${host.host_url}/${cleanEndpoint}`;
  }

  // Fallback: construct from host_ip and host_port
  if (host.host_ip && host.host_port) {
    const cleanEndpoint = endpoint.startsWith('/') ? endpoint.slice(1) : endpoint;
    return `https://${host.host_ip}:${host.host_port}/${cleanEndpoint}`;
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

    const fullEndpoint = `host${streamPath}/output.m3u8`;
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
    return internalBuildHostUrl(host, cleanPath);
  }

  // Fallback if no host selected
  return imagePath;
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
      const urlPath = capturePath.replace('/var/www/html', '').replace(/^\/+/, '/');
      return urlPath;
    }
  }

  const availableDevices = devices.map((d: any) => d?.device_id).filter(Boolean);
  throw new Error(
    `Device ${deviceId} not found in host configuration. Available devices: ${availableDevices.join(', ')}`,
  );
};

// =====================================================
// DOCUMENTATION & USAGE GUIDELINES
// =====================================================

/**
 * URL BUILDING BEST PRACTICES
 * 
 * WHY CENTRALIZED URL BUILDING IS CRITICAL:
 * 
 * 1. ENVIRONMENT FLEXIBILITY
 *    - Development: APIs run on localhost:5109
 *    - Production: APIs run on virtualpytest.onrender.com
 *    - Without centralized building, you get hardcoded URLs that break in different environments
 * 
 * 2. DEPLOYMENT ARCHITECTURE SUPPORT
 *    - Frontend deployed on Vercel (www.virtualpytest.com)
 *    - Backend deployed on Render (virtualpytest.onrender.com)
 *    - Direct fetch('/server/...') goes to frontend domain, not backend!
 * 
 * 3. DEBUGGING & MAINTENANCE
 *    - Single place to change URL patterns
 *    - Easy to trace URL construction issues
 *    - Consistent error handling and validation
 * 
 * 4. SECURITY & CORS
 *    - Proper cross-origin request handling
 *    - Environment-specific CORS configuration
 *    - Prevents accidental exposure of internal URLs
 * 
 * USAGE PATTERNS:
 * 
 * ❌ WRONG - Direct fetch with relative URLs:
 *    await fetch('/server/control/lockedDevices')
 *    → Goes to: https://www.virtualpytest.com/server/control/lockedDevices (WRONG!)
 * 
 * ✅ CORRECT - Use buildServerUrl:
 *    import { buildServerUrl } from '../utils/buildUrlUtils';
 *    await fetch(buildServerUrl('/server/control/lockedDevices'))
 *    → Goes to: https://virtualpytest.onrender.com/server/control/lockedDevices (CORRECT!)
 * 
 * ❌ WRONG - Hardcoded constants:
 *    const API_BASE = '/server/campaigns';
 * 
 * ✅ CORRECT - Use buildServerUrl in constants:
 *    const API_BASE = buildServerUrl('/server/campaigns');
 * 
 * FUNCTION SELECTION GUIDE:
 * 
 * - buildServerUrl()     → Backend API calls (campaigns, scripts, control, etc.)
 * - buildHostUrl()       → Direct device communication (screenshots, actions, etc.)
 * - buildStreamUrl()     → Live video streams from devices
 * - buildCaptureUrl()    → Screenshot and capture images
 * - buildHostImageUrl()  → Any image served by device hosts
 * - buildCloudImageUrl() → Images stored in cloud storage (R2, S3)
 * 
 * ENVIRONMENT VARIABLES REQUIRED:
 * 
 * - VITE_SERVER_URL: Backend server URL (e.g., https://virtualpytest.onrender.com)
 *   Used by: buildServerUrl()
 * 
 * - Host configuration in database: host_url, host_ip, host_port
 *   Used by: buildHostUrl(), buildStreamUrl(), buildCaptureUrl()
 */
