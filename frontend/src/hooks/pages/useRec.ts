import { useState, useEffect, useCallback, useMemo, useRef } from 'react';

import { Host, Device } from '../../types/common/Host_Types';
import { useHostManager } from '../useHostManager';
import { calculateVncScaling } from '../../utils/vncUtils';

import { buildServerUrl } from '../../utils/buildUrlUtils';
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
  const [baseUrlPatterns] = useState<Map<string, string>>(new Map());

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
  ]);
  
  return returnValue;
};
