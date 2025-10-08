import { useState, useEffect, useCallback, useMemo, useRef } from 'react';

import { Host, Device } from '../../types/common/Host_Types';
import { useHostManager } from '../useHostManager';
import { calculateVncScaling } from '../../utils/vncUtils';

import { buildServerUrl, buildStreamUrl, buildCaptureUrl } from '../../utils/buildUrlUtils';
// Removed global state - no longer needed for simple monitoring patterns

interface UseRecReturn {
  avDevices: Array<{ host: Host; device: Device }>;
  isLoading: boolean;
  error: string | null;
  refreshHosts: () => Promise<void>;
  baseUrlPatterns: Map<string, string>; // host_name-device_id -> base URL pattern (for monitoring)
  restartStreams: () => Promise<void>; // Restart streams for all AV devices
  isRestarting: boolean; // Loading state for restart operation
  adaptiveInterval: number; // Adaptive interval based on device count
  calculateVncScaling: (targetSize: { width: number; height: number }) => { // VNC scaling calculation for any target size
    transform: string;
    transformOrigin: string;
    width: string;
    height: string;
  };
  getCaptureUrlFromStream: (streamUrl: string, device?: Device, host?: Host) => string | null; // Calculate capture URL from segment URL
  pollForFreshStream: (host: Host, deviceId: string, onReady: () => void, onTimeout: (error: string) => void) => () => void; // Returns cleanup function
}

/**
 * Hook for managing recording/AV device discovery and display
 *
 * Simplified to only handle device discovery:
 * - Stream URL fetching: Use useStream hook
 * - Device control: Use HostManager takeControl/releaseControl directly
 * 
 * Note: This hook will re-execute when HostManager updates (e.g., on take/release control),
 * but the return value is memoized to prevent consumer re-renders when data hasn't changed.
 * All callbacks use refs to remain stable across HostManager updates.
 */
export const useRec = (): UseRecReturn => {
  const [avDevices, setAvDevices] = useState<Array<{ host: Host; device: Device }>>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isRestarting, setIsRestarting] = useState(false);
  
  // Track re-renders caused by useHostManager
  const renderCountRef = useRef(0);
  renderCountRef.current += 1;

  // Adaptive interval based on device count
  const adaptiveInterval = useMemo(() => {
    const count = avDevices.length;
    if (count <= 5) return 1000;   // 5 FPS with batch of 5
    if (count <= 10) return 5000;  // 1 FPS
    if (count <= 20) return 10000; // 0.5 FPS
    return Math.round(5000 / 0.3);  // ~16667ms for 0.3 FPS
  }, [avDevices.length]);

  // Remove modal context hook - no longer needed for thumbnail generation

  // Simple state for monitoring base URL patterns (read-only for now)
  // Use useMemo to ensure stable reference across re-renders
  const baseUrlPatterns = useMemo(() => new Map<string, string>(), []);

  // Use the simplified HostManager function and loading state
  const { getDevicesByCapability, isLoading: isHostManagerLoading } = useHostManager();
  
  // Use refs to store latest values and prevent callback recreation
  const getDevicesByCapabilityRef = useRef(getDevicesByCapability);
  const isHostManagerLoadingRef = useRef(isHostManagerLoading);
  
  getDevicesByCapabilityRef.current = getDevicesByCapability;
  isHostManagerLoadingRef.current = isHostManagerLoading;

  console.log(`[@hook:useRec] Hook render #${renderCountRef.current}`, {
    isHostManagerLoading,
    avDevicesCount: avDevices.length
  });

  // Get AV-capable devices - only when HostManager is ready
  // Stabilized with ref to prevent recreation on every HostManager update
  const refreshHosts = useCallback(async (): Promise<void> => {
    // Don't fetch if HostManager is still loading
    if (isHostManagerLoadingRef.current) {
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const devices = getDevicesByCapabilityRef.current('av');
      
      // Only update if devices actually changed (prevent unnecessary re-renders)
      setAvDevices(prev => {
        // Check if the device list actually changed
        if (prev.length !== devices.length) {
          return devices;
        }
        
        // Compare device keys to detect changes
        const prevKeys = prev.map(({ host, device }) => `${host.host_name}-${device.device_id}`).sort().join(',');
        const newKeys = devices.map(({ host, device }) => `${host.host_name}-${device.device_id}`).sort().join(',');
        
        if (prevKeys !== newKeys) {
          return devices;
        }
        
        // No changes, keep previous reference to prevent re-renders
        return prev;
      });
    } catch (error) {
      console.error('[@hook:useRec] Error refreshing devices:', error);
      setError(error instanceof Error ? error.message : 'Failed to refresh devices');
    } finally {
      setIsLoading(false);
    }
  }, []); // No dependencies - use refs instead to keep callback stable

  // Trigger refresh when HostManager finishes loading
  useEffect(() => {
    if (!isHostManagerLoading) {
      refreshHosts();
    }
  }, [isHostManagerLoading, refreshHosts]);

  // Initialize on mount and set up auto-refresh
  useEffect(() => {
    // Initial refresh (will be skipped if HostManager is loading)
    refreshHosts();

    // Auto-refresh every 30 seconds
    const interval = setInterval(() => {
      refreshHosts();
    }, 30000);

    return () => {
      clearInterval(interval);
    };
  }, [refreshHosts]);

  // Use ref to store the latest avDevices and isRestarting to avoid dependency issues
  const avDevicesRef = useRef(avDevices);
  const isRestartingRef = useRef(isRestarting);
  
  avDevicesRef.current = avDevices;
  isRestartingRef.current = isRestarting;

  // Restart streams for all AV devices
  // Stabilized with ref to prevent recreation
  const restartStreams = useCallback(async (): Promise<void> => {
    if (isRestartingRef.current) return; // Prevent multiple concurrent restarts

    setIsRestarting(true);
    setError(null);

    try {
      const currentAvDevices = avDevicesRef.current;
      // console.log(`[@hook:useRec] Starting stream restart for ${currentAvDevices.length} devices`);

      // Restart streams sequentially for each AV device
      for (const { host, device } of currentAvDevices) {
        try {
          // console.log(`[@hook:useRec] Restarting stream for ${host.host_name}-${device.device_id}`);

          const response = await fetch(buildServerUrl('/server/system/restartHostStreamService'), {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              host_name: host.host_name,
              device_id: device.device_id || 'device1',
            }),
          });

          if (response.ok) {
            const result = await response.json();
            if (result.success) {
              console.log(
                `[@hook:useRec] Successfully restarted stream for ${host.host_name}-${device.device_id}`,
              );
            } else {
              console.error(
                `[@hook:useRec] Failed to restart stream for ${host.host_name}-${device.device_id}:`,
                result.error,
              );
            }
          } else {
            console.error(
              `[@hook:useRec] Restart request failed for ${host.host_name}-${device.device_id}:`,
              response.status,
            );
          }
        } catch (deviceError) {
          console.error(
            `[@hook:useRec] Error restarting stream for ${host.host_name}-${device.device_id}:`,
            deviceError,
          );
        }
      }

      // console.log(`[@hook:useRec] Completed stream restart for all devices`);
    } catch (error) {
      console.error('[@hook:useRec] Error restarting streams:', error);
      setError(error instanceof Error ? error.message : 'Failed to restart streams');
    } finally {
      setIsRestarting(false);
    }
  }, []); // No dependencies - use refs instead to keep callback stable

  // Calculate capture URL from stream segment URL using FPS
  // Uses existing buildCaptureUrl utility - no manual URL building!
  const getCaptureUrlFromStream = useCallback((streamUrl: string, device?: Device, host?: Host): string | null => {
    if (!streamUrl || !device || !host) {
      console.warn('[@hook:useRec] Missing required parameters:', { streamUrl: !!streamUrl, device: !!device, host: !!host });
      return null;
    }
    
    try {
      // Get FPS from device (default: 5 for HDMI, 2 for VNC)
      const fps = device.video_fps || 5;
      
      // Extract segment number from stream URL (e.g., segment_000078741.ts)
      const segmentMatch = streamUrl.match(/segment_(\d+)\.ts/);
      if (!segmentMatch) {
        console.warn('[@hook:useRec] Could not extract segment number from URL:', streamUrl);
        return null;
      }
      
      const segmentNumber = parseInt(segmentMatch[1], 10);
      const captureNumber = segmentNumber * fps; // segment * fps = capture
      
      // Format as padded string (buildCaptureUrl expects timestamp format)
      const captureSequence = String(captureNumber).padStart(10, '0');
      
      // Use existing buildCaptureUrl utility (handles cold storage path automatically)
      const captureUrl = buildCaptureUrl(host, captureSequence, device.device_id);
      
      console.log(`[@hook:useRec] Calculated capture: segment=${segmentNumber}, fps=${fps}, capture=${captureNumber}`);
      return captureUrl;
    } catch (error) {
      console.error('[@hook:useRec] Failed to calculate capture URL:', error);
      return null;
    }
  }, []);

  // Poll for fresh stream after quality change - reusable across components
  const pollForFreshStream = useCallback((
    host: Host, 
    deviceId: string, 
    onReady: () => void, 
    onTimeout: (error: string) => void
  ): (() => void) => {
    // Use proper buildStreamUrl to handle all host-specific paths (e.g., /pi2/, /pi3/, etc.)
    const manifestUrl = buildStreamUrl(host, deviceId);
    console.log(`[@hook:useRec] Starting manifest polling for fresh stream: ${manifestUrl}`);
    
    let pollCount = 0;
    const maxPolls = 15; // 15 seconds max (1000ms * 15)
    const requiredSegments = 3; // Need at least 3 segments in manifest
    
    const pollingInterval = setInterval(async () => {
      pollCount++;
      
      // Check timeout FIRST before polling
      if (pollCount > maxPolls) {
        console.warn(`[@hook:useRec] Polling timeout after ${maxPolls} attempts for ${host.host_name}-${deviceId}`);
        clearInterval(pollingInterval);
        onTimeout('Stream restart took longer than expected');
        return;
      }
      
      console.log(`[@hook:useRec] Polling attempt ${pollCount}/${maxPolls} for ${host.host_name}-${deviceId}`);
      
      try {
        // Add timestamp to prevent caching
        const cacheBustUrl = `${manifestUrl}?_t=${Date.now()}`;
        const response = await fetch(cacheBustUrl, { 
          method: 'GET',
          cache: 'no-store', // Stronger than no-cache
          headers: {
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache'
          }
        });
        
        if (!response.ok) {
          console.log(`[@hook:useRec] Manifest not ready yet (status: ${response.status}) for ${host.host_name}-${deviceId}`);
          return;
        }
        
        const manifestText = await response.text();
        console.log(`[@hook:useRec] Manifest received for ${host.host_name}-${deviceId}, length: ${manifestText.length} bytes`);
        
        // Check if manifest has proper header
        if (!manifestText.includes('#EXTM3U')) {
          console.log(`[@hook:useRec] Invalid manifest for ${host.host_name}-${deviceId} - no #EXTM3U header. First 100 chars:`, manifestText.substring(0, 100));
          return;
        }
        
        // Count segments in manifest by counting #EXTINF lines
        const segmentCount = (manifestText.match(/#EXTINF/g) || []).length;
        
        // Extract media sequence number to ensure we have a fresh stream
        const mediaSequenceMatch = manifestText.match(/#EXT-X-MEDIA-SEQUENCE:(\d+)/);
        const mediaSequence = mediaSequenceMatch ? parseInt(mediaSequenceMatch[1], 10) : -1;
        
        console.log(`[@hook:useRec] Manifest valid for ${host.host_name}-${deviceId}! Has ${segmentCount} segments (need ${requiredSegments}), media sequence: ${mediaSequence}`);
        
        // Check both segment count AND that we have a fresh stream (low media sequence)
        // Fresh stream should start from 0 or very low numbers (allow up to 10 for some tolerance)
        const isFreshStream = mediaSequence >= 0 && mediaSequence <= 10;
        
        if (segmentCount >= requiredSegments && isFreshStream) {
          console.log(`[@hook:useRec] ✅ Fresh stream ready for ${host.host_name}-${deviceId}! ${segmentCount} segments, sequence ${mediaSequence}`);
          clearInterval(pollingInterval);
          onReady();
        } else if (segmentCount >= requiredSegments && !isFreshStream) {
          console.log(`[@hook:useRec] ⏳ Manifest for ${host.host_name}-${deviceId} has ${segmentCount} segments but sequence ${mediaSequence} is too high - waiting for fresh stream restart`);
        }
      } catch (error) {
        console.log(`[@hook:useRec] Manifest check failed for ${host.host_name}-${deviceId}: ${error}`);
      }
    }, 1000); // 1 second interval
    
    // Return cleanup function
    return () => {
      console.log(`[@hook:useRec] Cleaning up polling for ${host.host_name}-${deviceId}`);
      clearInterval(pollingInterval);
    };
  }, []); // No dependencies - pure function

  // Memoize return value to prevent RecContent re-renders when context changes
  // but our actual values haven't changed
  const returnValue = useMemo(() => {
    console.log('[@hook:useRec] Return value changed - consumers will re-render');
    return {
      avDevices,
      isLoading,
      error,
      refreshHosts,
      baseUrlPatterns, // Only used for monitoring now
      restartStreams,
      isRestarting,
      adaptiveInterval,
      calculateVncScaling, // Now using the imported version
      getCaptureUrlFromStream, // Calculate capture URL from segment
      pollForFreshStream, // New polling function for quality changes
    };
  }, [
    avDevices,
    isLoading,
    error,
    refreshHosts,
    baseUrlPatterns,
    restartStreams,
    isRestarting,
    adaptiveInterval,
    getCaptureUrlFromStream,
    pollForFreshStream, // Add new function to dependency list
  ]);
  
  return returnValue;
};
