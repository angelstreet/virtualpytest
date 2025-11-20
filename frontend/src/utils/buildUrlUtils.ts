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

import { APP_CONFIG, SERVER_CONFIG, STORAGE_KEYS } from '../config/constants';

// =====================================================
// SERVER URL BUILDING (Frontend to Backend Server)
// =====================================================


export const buildServerUrl = (endpoint: string): string => {
  // Try to get selected server from localStorage first, fallback to env variable
  let serverUrl: string;
  try {
    const selectedServer = localStorage.getItem(STORAGE_KEYS.SELECTED_SERVER);
    serverUrl = selectedServer || SERVER_CONFIG.DEFAULT_URL;
  } catch {
    // Fallback if localStorage is not available
    serverUrl = SERVER_CONFIG.DEFAULT_URL;
  }
  
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint.slice(1) : endpoint;
  const url = `${serverUrl}/${cleanEndpoint}`;
  
  // Always add team_id to all server URLs
  return `${url}${url.includes('?') ? '&' : '?'}team_id=${APP_CONFIG.DEFAULT_TEAM_ID}`;
};

/**
 * Parse URL list from various formats
 * Handles: comma-separated strings, JSON arrays, stringified arrays, single URLs
 * 
 * Examples:
 *   "url1,url2,url3" -> ["url1", "url2", "url3"]
 *   '["url1", "url2"]' -> ["url1", "url2"]
 *   "['url1', 'url2']" -> ["url1", "url2"]
 *   "url1" -> ["url1"]
 *   '[]' -> []
 */
const parseUrlList = (value: string | string[]): string[] => {
  // Already an array
  if (Array.isArray(value)) {
    return value.map(u => u.trim()).filter(u => u);
  }
  
  if (!value || typeof value !== 'string') {
    return [];
  }
  
  const trimmed = value.trim();
  
  // Empty or invalid patterns
  if (!trimmed || trimmed === '[]' || trimmed === '{}' || trimmed === 'null' || trimmed === 'undefined') {
    return [];
  }
  
  // Try to parse as JSON array first (handles '["url1", "url2"]')
  if (trimmed.startsWith('[') && trimmed.endsWith(']')) {
    try {
      // Try direct JSON parse
      const parsed = JSON.parse(trimmed);
      if (Array.isArray(parsed)) {
        return parsed.map(u => String(u).trim()).filter(u => u);
      }
    } catch {
      // Not valid JSON, try to extract URLs from stringified array
      // Handle cases like "['url1', 'url2']" or '["url1", "url2"]'
      const urlMatch = trimmed.match(/\[(.*)\]/);
      if (urlMatch) {
        const inner = urlMatch[1];
        // Split by comma and clean up quotes
        return inner
          .split(',')
          .map(u => u.trim().replace(/^["']|["']$/g, ''))
          .filter(u => u);
      }
    }
  }
  
  // Comma-separated string (handles "url1,url2,url3")
  if (trimmed.includes(',')) {
    return trimmed.split(',').map(u => u.trim()).filter(u => u);
  }
  
  // Single URL
  return [trimmed];
};

/**
 * Validate if a string is a valid server URL
 */
const isValidServerUrl = (url: string): boolean => {
  if (!url || !url.trim()) return false;
  const trimmed = url.trim();
  // Reject common invalid patterns
  if (trimmed === '[]' || trimmed === '{}' || trimmed === 'null' || trimmed === 'undefined') {
    return false;
  }
  // Reject if still contains brackets (malformed)
  if (trimmed.includes('[') || trimmed.includes(']')) {
    return false;
  }
  // Must have at least a domain or localhost
  if (trimmed.includes('localhost') || trimmed.includes('.') || trimmed.match(/^\d+\.\d+\.\d+\.\d+/)) {
    return true;
  }
  return false;
};

/**
 * Get all configured server URLs (primary + slaves)
 * Reads VITE_SERVER_URL and VITE_SLAVE_SERVER_URL
 * 
 * Smart parsing handles multiple formats:
 * - Comma-separated: "url1,url2"
 * - JSON array: ["url1", "url2"]
 * - Stringified array: '["url1", "url2"]' or "['url1', 'url2']"
 * - Single URL: "url1"
 */
export const getAllServerUrls = (): string[] => {
  const urls: string[] = [];
  
  // Parse primary URL
  const primaryUrl = (import.meta as any).env?.VITE_SERVER_URL;
  if (primaryUrl) {
    const parsedPrimary = parseUrlList(primaryUrl);
    urls.push(...parsedPrimary.filter(url => isValidServerUrl(url)));
  }
  
  // Parse slave URLs (supports all formats)
  const slaveUrls = (import.meta as any).env?.VITE_SLAVE_SERVER_URL;
  if (slaveUrls) {
    const parsedSlaves = parseUrlList(slaveUrls);
    urls.push(...parsedSlaves.filter(url => isValidServerUrl(url)));
  }
  
  // Only add default if it's valid and we have no other URLs
  if (urls.length === 0) {
    if (SERVER_CONFIG.DEFAULT_URL && isValidServerUrl(SERVER_CONFIG.DEFAULT_URL)) {
      urls.push(SERVER_CONFIG.DEFAULT_URL);
    } else {
      console.error('[getAllServerUrls] No valid server URLs configured! Set VITE_SERVER_URL environment variable.');
    }
  }
  
  console.log('[getAllServerUrls] Resolved URLs:', urls);
  return urls;
};

/**
 * Build URL for specific server with team_id
 * @param serverUrl - The server base URL
 * @param endpoint - API endpoint
 * @returns Complete URL with team_id
 */
export const buildServerUrlForServer = (serverUrl: string, endpoint: string): string => {
  // Validate serverUrl is not empty
  if (!serverUrl || serverUrl.trim() === '') {
    const error = `[buildServerUrlForServer] Invalid serverUrl: "${serverUrl}" - check VITE_SERVER_URL environment variable`;
    console.error(error);
    throw new Error(error);
  }
  
  // Ensure serverUrl has protocol (http:// or https://)
  let normalizedServerUrl = serverUrl;
  if (!serverUrl.match(/^https?:\/\//)) {
    normalizedServerUrl = `http://${serverUrl}`;
    console.log(`[buildServerUrlForServer] Added protocol: ${serverUrl} -> ${normalizedServerUrl}`);
  }
  
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint.slice(1) : endpoint;
  const url = `${normalizedServerUrl}/${cleanEndpoint}`;
  
  // Always add team_id to all server URLs
  return `${url}${url.includes('?') ? '&' : '?'}team_id=${APP_CONFIG.DEFAULT_TEAM_ID}`;
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

      // Special case: VNC devices have full URL in video_stream_path (for live iframe)
      // For HLS recordings, use video_capture_path instead (converted to stream path)
      if (device?.device_model === 'host_vnc' && streamPath.startsWith('http')) {
        // Get capture path and convert to stream path (remove /captures suffix if present)
        const capturePath = getDeviceCaptureUrlPath(host, deviceId);
        const streamPathFromCapture = capturePath.replace('/captures', '');
        return streamPathFromCapture;
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

// =====================================================
// METADATA CHUNK UTILITIES (Archive Mode)
// =====================================================

/**
 * Build URL for metadata chunk JSON file (direct file access).
 * Chunks contain metadata for 10 minutes of recording (up to 3000 frames at 5fps).
 * 
 * IMPORTANT: Chunk location calculation is done in useArchivePlayer.ts (hour * 3600 + chunk_index * 600)
 * This ensures consistency with video playback timeline. DO NOT duplicate the calculation here!
 * 
 * @param host - Host object
 * @param deviceId - Device ID
 * @param hour - Hour (0-23) - from useArchivePlayer's globalCurrentTime
 * @param chunkIndex - Chunk index within hour (0-5) - from useArchivePlayer's globalCurrentTime
 * @returns URL to metadata chunk file
 * 
 * Example:
 *   buildMetadataChunkUrl(host, 'device1', 15, 0)
 *   -> "http://host/stream/capture1/metadata/15/chunk_10min_0.json"
 */
export const buildMetadataChunkUrl = (
  host: any,
  deviceId: string,
  hour: number,
  chunkIndex: number
): string => {
  if (!deviceId) {
    throw new Error('deviceId is required for buildMetadataChunkUrl');
  }
  
  // Get device capture path and convert to metadata path
  const capturePath = getDeviceCaptureUrlPath(host, deviceId);
  // Remove /captures suffix and add /metadata/{hour}/chunk_10min_{chunkIndex}.json
  const basePath = capturePath.replace('/captures', '');
  const chunkPath = `${basePath}/metadata/${hour}/chunk_10min_${chunkIndex}.json`;
  
  return internalBuildHostUrl(host, `host${chunkPath}`);
};

// =====================================================
// AUDIO/TRANSCRIPT UTILITIES
// =====================================================

/**
 * Build URL for original MP3 audio file (10-minute chunk)
 * @param host - Host object
 * @param deviceId - Device ID
 * @param hour - Hour (0-23)
 * @param chunkIndex - Chunk index within hour (0-5)
 * @returns URL to original MP3 file
 */
export const buildAudioMp3Url = (
  host: any,
  deviceId: string,
  hour: number,
  chunkIndex: number
): string => {
  if (!deviceId) {
    throw new Error('deviceId is required for buildAudioMp3Url');
  }
  
  // Get device stream path for audio
  const streamPath = getDeviceStreamUrlPath(host, deviceId);
  const audioPath = `${streamPath}/audio/${hour}/chunk_10min_${chunkIndex}.mp3`;
  
  return internalBuildHostUrl(host, `host${audioPath}`);
};

/**
 * Build URL for dubbed audio file (10-minute chunk with language)
 * @param host - Host object
 * @param deviceId - Device ID
 * @param hour - Hour (0-23)
 * @param chunkIndex - Chunk index within hour (0-5)
 * @param language - Target language code (e.g., 'es', 'fr')
 * @returns URL to dubbed MP3 file
 */
export const buildDubbedAudioUrl = (
  host: any,
  deviceId: string,
  hour: number,
  chunkIndex: number,
  language: string
): string => {
  if (!deviceId) {
    throw new Error('deviceId is required for buildDubbedAudioUrl');
  }
  
  // Get device stream path for audio
  const streamPath = getDeviceStreamUrlPath(host, deviceId);
  const audioPath = `${streamPath}/audio/${hour}/chunk_10min_${chunkIndex}_${language}.mp3`;
  
  return internalBuildHostUrl(host, `host${audioPath}`);
};

/**
 * Build URL for temporary 1-minute dubbed audio file
 * @param host - Host object
 * @param deviceId - Device ID
 * @param minute - Minute within chunk (0-9)
 * @param language - Target language code (e.g., 'es', 'fr')
 * @returns URL to temporary 1-minute MP3 file
 */
export const buildDubbedAudio1MinUrl = (
  host: any,
  deviceId: string,
  minute: number,
  language: string
): string => {
  if (!deviceId) {
    throw new Error('deviceId is required for buildDubbedAudio1MinUrl');
  }
  
  // Get device stream path for audio
  const streamPath = getDeviceStreamUrlPath(host, deviceId);
  const audioPath = `${streamPath}/audio/temp/1min_${minute}_${language}.mp3`;
  
  return internalBuildHostUrl(host, `host${audioPath}`);
};

/**
 * Build URL for transcript chunk JSON file
 * @param host - Host object
 * @param deviceId - Device ID
 * @param hour - Hour (0-23)
 * @param chunkIndex - Chunk index within hour (0-5)
 * @param language - Language code (optional, 'original' if not specified)
 * @returns URL to transcript JSON file
 */
export const buildTranscriptChunkUrl = (
  host: any,
  deviceId: string,
  hour: number,
  chunkIndex: number,
  language: string = 'original'
): string => {
  if (!deviceId) {
    throw new Error('deviceId is required for buildTranscriptChunkUrl');
  }
  
  // Get device stream path for transcript
  const streamPath = getDeviceStreamUrlPath(host, deviceId);
  const langSuffix = language === 'original' ? '' : `_${language}`;
  const transcriptPath = `${streamPath}/transcript/${hour}/chunk_10min_${chunkIndex}${langSuffix}.json`;
  
  return internalBuildHostUrl(host, `host${transcriptPath}`);
};

/**
 * Build URL for transcript manifest JSON file
 * @param host - Host object
 * @param deviceId - Device ID
 * @returns URL to transcript manifest
 */
export const buildTranscriptManifestUrl = (
  host: any,
  deviceId: string
): string => {
  if (!deviceId) {
    throw new Error('deviceId is required for buildTranscriptManifestUrl');
  }
  
  // Get device stream path for transcript manifest
  const streamPath = getDeviceStreamUrlPath(host, deviceId);
  const manifestPath = `${streamPath}/transcript/transcript_manifest.json`;
  
  return internalBuildHostUrl(host, `host${manifestPath}`);
};

/**
 * Build URL for script running log file (hot storage)
 * @param host - Host object
 * @param deviceId - Device ID
 * @returns URL to running.log file
 */
export const buildRunningLogUrl = (
  host: any,
  deviceId: string
): string => {
  if (!deviceId) {
    throw new Error('deviceId is required for buildRunningLogUrl');
  }
  
  // Get device stream path for running log
  const streamPath = getDeviceStreamUrlPath(host, deviceId);
  const runningLogPath = `${streamPath}/hot/running.log`;
  
  return internalBuildHostUrl(host, `host${runningLogPath}`);
};

// =====================================================
// STREAM UTILITIES (Quality Changes & Captures)
// =====================================================

/**
 * Poll for fresh stream after quality change
 * Returns cleanup function to cancel polling
 */
export const pollForFreshStream = (
  host: any,
  deviceId: string,
  onReady: () => void,
  onTimeout: (error: string) => void
): (() => void) => {
  // Use proper buildStreamUrl to handle all host-specific paths (e.g., /pi2/, /pi3/, etc.)
  const manifestUrl = buildStreamUrl(host, deviceId);
  console.log(`[@utils:buildUrlUtils] Starting manifest polling for fresh stream: ${manifestUrl}`);

  let pollCount = 0;
  const maxPolls = 15; // 15 seconds max (1000ms * 15)
  const requiredSegments = 3; // Need at least 3 segments in manifest

  const pollingInterval = setInterval(async () => {
    pollCount++;

    // Check timeout FIRST before polling
    if (pollCount > maxPolls) {
      console.warn(
        `[@utils:buildUrlUtils] Polling timeout after ${maxPolls} attempts for ${host.host_name}-${deviceId}`
      );
      clearInterval(pollingInterval);
      onTimeout('Stream restart took longer than expected');
      return;
    }

    console.log(
      `[@utils:buildUrlUtils] Polling attempt ${pollCount}/${maxPolls} for ${host.host_name}-${deviceId}`
    );

    try {
      // Add timestamp to prevent caching
      const cacheBustUrl = `${manifestUrl}?_t=${Date.now()}`;
      const response = await fetch(cacheBustUrl, {
        method: 'GET',
        cache: 'no-store', // Stronger than no-cache
        headers: {
          'Cache-Control': 'no-cache, no-store, must-revalidate',
          Pragma: 'no-cache',
        },
      });

      if (!response.ok) {
        console.log(
          `[@utils:buildUrlUtils] Manifest not ready yet (status: ${response.status}) for ${host.host_name}-${deviceId}`
        );
        return;
      }

      const manifestText = await response.text();
      console.log(
        `[@utils:buildUrlUtils] Manifest received for ${host.host_name}-${deviceId}, length: ${manifestText.length} bytes`
      );

      // Check if manifest has proper header
      if (!manifestText.includes('#EXTM3U')) {
        console.log(
          `[@utils:buildUrlUtils] Invalid manifest for ${host.host_name}-${deviceId} - no #EXTM3U header. First 100 chars:`,
          manifestText.substring(0, 100)
        );
        return;
      }

      // Count segments in manifest by counting #EXTINF lines
      const segmentCount = (manifestText.match(/#EXTINF/g) || []).length;

      // Extract media sequence number to ensure we have a fresh stream
      const mediaSequenceMatch = manifestText.match(/#EXT-X-MEDIA-SEQUENCE:(\d+)/);
      const mediaSequence = mediaSequenceMatch ? parseInt(mediaSequenceMatch[1], 10) : -1;

      console.log(
        `[@utils:buildUrlUtils] Manifest valid for ${host.host_name}-${deviceId}! Has ${segmentCount} segments (need ${requiredSegments}), media sequence: ${mediaSequence}`
      );

      // Check both segment count AND that we have a fresh stream (low media sequence)
      // Fresh stream should start from 0 or very low numbers (allow up to 10 for some tolerance)
      const isFreshStream = mediaSequence >= 0 && mediaSequence <= 10;

      if (segmentCount >= requiredSegments && isFreshStream) {
        console.log(
          `[@utils:buildUrlUtils] ✅ Fresh stream ready for ${host.host_name}-${deviceId}! ${segmentCount} segments, sequence ${mediaSequence}`
        );
        clearInterval(pollingInterval);
        onReady();
      } else if (segmentCount >= requiredSegments && !isFreshStream) {
        console.log(
          `[@utils:buildUrlUtils] ⏳ Manifest for ${host.host_name}-${deviceId} has ${segmentCount} segments but sequence ${mediaSequence} is too high - waiting for fresh stream restart`
        );
      }
    } catch (error) {
      console.log(
        `[@utils:buildUrlUtils] Manifest check failed for ${host.host_name}-${deviceId}: ${error}`
      );
    }
  }, 1000); // 1 second interval

  // Return cleanup function
  return () => {
    console.log(`[@utils:buildUrlUtils] Cleaning up polling for ${host.host_name}-${deviceId}`);
    clearInterval(pollingInterval);
  };
};

/**
 * Get capture URL from stream segment (calls backend to copy hot->cold)
 * Backend handles: segment→capture calculation, hot→cold copy, URL building
 */
export const getCaptureUrlFromStream = async (
  streamUrl: string,
  device?: any,
  host?: any
): Promise<string | null> => {
  if (!streamUrl || !device || !host) {
    console.warn('[@utils:buildUrlUtils] Missing required parameters:', {
      streamUrl: !!streamUrl,
      device: !!device,
      host: !!host,
    });
    return null;
  }

  try {
    // Extract segment number from stream URL (e.g., segment_000078741.ts)
    const segmentMatch = streamUrl.match(/segment_(\d+)\.ts/);
    if (!segmentMatch) {
      console.warn('[@utils:buildUrlUtils] Could not extract segment number from URL:', streamUrl);
      return null;
    }

    const segmentNumber = parseInt(segmentMatch[1], 10);
    const fps = device.video_fps || 5;

    console.log(`[@utils:buildUrlUtils] Requesting capture: segment=${segmentNumber}, fps=${fps}`);

    // Call backend to get capture (handles hot→cold copy)
    const response = await fetch(buildServerUrl('/server/av/getSegmentCapture'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        host_name: host.host_name,
        device_id: device.device_id,
        segment_number: segmentNumber,
        fps: fps,
      }),
    });

    if (!response.ok) {
      console.error('[@utils:buildUrlUtils] Backend request failed:', response.status);
      return null;
    }

    const result = await response.json();
    if (result.success && result.capture_url) {
      console.log(`[@utils:buildUrlUtils] Got capture URL (COLD): ${result.capture_url}`);
      return result.capture_url;
    }

    console.error('[@utils:buildUrlUtils] Backend returned error:', result.error);
    return null;
  } catch (error) {
    console.error('[@utils:buildUrlUtils] Failed to get capture URL:', error);
    return null;
  }
};
