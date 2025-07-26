import React, { useState, useCallback, useEffect, useMemo, useRef } from 'react';
import { useLocation } from 'react-router-dom';

import { useUserSession } from '../hooks/useUserSession';
import { Host, Device } from '../types/common/Host_Types';

import { HostManagerContext } from './HostManagerContext';

interface HostManagerProviderProps {
  children: React.ReactNode;
  userInterface?: {
    models?: string[];
  };
}

/**
 * Provider component for host management
 * This component provides access to host data and device control functionality
 */
export const HostManagerProvider: React.FC<HostManagerProviderProps> = ({
  children,
  userInterface,
}) => {
  // ========================================
  // STATE
  // ========================================

  // Host data state
  const [availableHosts, setAvailableHosts] = useState<Host[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Panel and UI state
  const [selectedHost, setSelectedHost] = useState<Host | null>(null);
  const [selectedDeviceId, setSelectedDeviceId] = useState<string | null>(null);
  const [isControlActive, setIsControlActive] = useState(false);
  const [isRemotePanelOpen, setIsRemotePanelOpen] = useState(false);
  const [showRemotePanel, setShowRemotePanel] = useState(false);
  const [showAVPanel, setShowAVPanel] = useState(false);
  const [isVerificationActive, _setIsVerificationActive] = useState(false);

  // Filtered hosts based on interface models
  const [filteredAvailableHosts, setFilteredAvailableHosts] = useState<Host[]>([]);

  // Track active locks by host name -> user ID
  const [activeLocks, setActiveLocks] = useState<Map<string, string>>(new Map());
  const reclaimInProgressRef = useRef(false);
  const initializedRef = useRef(false);

  // Use shared user session for consistent identification
  const { userId, sessionId: browserSessionId, isOurLock } = useUserSession();

  // Get current location to determine if we should skip device locking
  const location = useLocation();
  const isHeatmapPage = location.pathname.includes('/monitoring/heatmap');

  // Memoize userInterface to prevent unnecessary re-renders
  const stableUserInterface = useMemo(() => userInterface, [userInterface]);

  // Host loading logic
  const loadHosts = useCallback(async (): Promise<{ hosts: Host[]; error: string | null }> => {
    try {
      const fullUrl = '/server/system/getAllHosts';
      const response = await fetch(fullUrl);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const result = await response.json();

      if (result.success) {
        const rawHosts = result.hosts || [];
        return { hosts: rawHosts, error: null };
      } else {
        throw new Error(result.error || 'Server returned success: false');
      }
    } catch (err: any) {
      console.error('[@context:HostManagerProvider] Error fetching hosts:', err);
      return { hosts: [], error: err.message || 'Failed to fetch hosts' };
    }
  }, []);

  // Auto-load hosts on mount
  useEffect(() => {
    const loadHostsOnMount = async () => {
      setIsLoading(true);
      setError(null);

      const result = await loadHosts();

      setAvailableHosts(result.hosts);
      setError(result.error);
      setIsLoading(false);
    };

    loadHostsOnMount();
  }, [loadHosts]);

  // ========================================
  // DIRECT DATA ACCESS FUNCTIONS
  // ========================================

  // Get all hosts without filtering (raw data from server)
  const getAllHosts = useCallback((): Host[] => {
    return availableHosts;
  }, [availableHosts]);

  // Get host by name
  const getHostByName = useCallback(
    (hostName: string): Host | null => {
      return availableHosts.find((h) => h.host_name === hostName) || null;
    },
    [availableHosts],
  );

  // Get hosts filtered by device models
  const getHostsByModel = useCallback(
    (models: string[]): Host[] => {
      const filtered = availableHosts
        .map((host) => ({
          ...host,
          devices: (host.devices || []).filter((device) => models.includes(device.device_model)),
        }))
        .filter((host) => host.devices.length > 0);

      return filtered;
    },
    [availableHosts],
  );

  // Get all devices from all available hosts
  const getAllDevices = useCallback((): Device[] => {
    const allDevices = availableHosts.flatMap((host) =>
      (host.devices || []).map((device) => ({ ...device, hostName: host.host_name })),
    );
    return allDevices;
  }, [availableHosts]);

  // Get all devices from specific host
  const getDevicesFromHost = useCallback(
    (hostName: string): Device[] => {
      const host = availableHosts.find((h) => h.host_name === hostName);
      const devices = host?.devices || [];
      return devices;
    },
    [availableHosts],
  );

  // Get devices with specific capability, returning {host, device} pairs
  const getDevicesByCapability = useCallback(
    (capability: string): { host: Host; device: Device }[] => {
      const matchingDevices: { host: Host; device: Device }[] = [];

      availableHosts.forEach((host) => {
        if (host.devices) {
          host.devices.forEach((device) => {
            // Check if device has the specified capability in device.device_capabilities object
            if (device.device_capabilities && (device.device_capabilities as any)[capability]) {
              matchingDevices.push({ host, device });
            }
          });
        }
      });

      return matchingDevices;
    },
    [availableHosts],
  );

  // ========================================
  // DEVICE CONTROL HANDLERS
  // ========================================

  // Automatically reclaim locks for devices that belong to this user
  const reclaimUserLocks = useCallback(async () => {
    // Prevent multiple simultaneous reclaim operations
    if (reclaimInProgressRef.current) {
      console.log('[@context:HostManagerProvider] Reclaim already in progress, skipping');
      return;
    }

    reclaimInProgressRef.current = true;

    try {
      console.log(
        `[@context:HostManagerProvider] Checking for locks to reclaim for user: ${userId}`,
      );

      // Get list of all locked devices from server
      const response = await fetch('/server/control/lockedDevices', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const result = await response.json();
        if (result.success && result.locked_devices) {
          const userLockedDevices = Object.entries(result.locked_devices).filter(
            ([_, lockInfo]: [string, any]) => isOurLock(lockInfo),
          );

          if (userLockedDevices.length > 0) {
            console.log(
              `[@context:HostManagerProvider] Found ${userLockedDevices.length} devices locked by current user, reclaiming...`,
            );

            // Reclaim each device lock
            for (const [deviceKey, _lockInfo] of userLockedDevices) {
              // deviceKey must be "hostname:device_id" format
              if (!deviceKey.includes(':')) {
                console.warn(
                  `[@context:HostManagerProvider] Skipping legacy lock key without device_id: ${deviceKey}`,
                );
                continue;
              }

              const [hostName, deviceId] = deviceKey.split(':');
              if (!deviceId) {
                console.warn(
                  `[@context:HostManagerProvider] Skipping lock key with empty device_id: ${deviceKey}`,
                );
                continue;
              }

              console.log(
                `[@context:HostManagerProvider] Reclaiming lock for device: ${hostName}:${deviceId}`,
              );
              setActiveLocks((prev) => new Map(prev).set(`${hostName}:${deviceId}`, userId));
            }
          }
        }
      }
    } catch (error) {
      console.error(`[@context:HostManagerProvider] Error reclaiming user locks:`, error);
    } finally {
      reclaimInProgressRef.current = false;
    }
  }, [userId, isOurLock]);

  // Take control via server control endpoint with comprehensive error handling
  const takeControl = useCallback(
    async (
      host: Host,
      device_id?: string,
      sessionId?: string,
    ): Promise<{
      success: boolean;
      error?: string;
      errorType?:
        | 'stream_service_error'
        | 'adb_connection_error'
        | 'device_locked'
        | 'device_not_found'
        | 'network_error'
        | 'generic_error';
      details?: any;
    }> => {
      try {
        const effectiveSessionId = sessionId || browserSessionId;
        const effectiveDeviceId = device_id || 'device1';

        console.log(
          `[@context:HostManagerProvider] Taking control of device: ${host.host_name}, device_id: ${effectiveDeviceId}`,
        );
        console.log(`[@context:HostManagerProvider] Using user ID for lock: ${userId}`);

        const response = await fetch('/server/control/takeControl', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            host: host,
            device_id: effectiveDeviceId,
            session_id: effectiveSessionId,
            user_id: userId,
          }),
        });

        const result = await response.json();

        if (response.ok && result.success) {
          console.log(
            `[@context:HostManagerProvider] Successfully took control of device: ${host.host_name}:${effectiveDeviceId}`,
          );
          // Store lock using device-oriented key
          setActiveLocks((prev) =>
            new Map(prev).set(`${host.host_name}:${effectiveDeviceId}`, userId),
          );
          return { success: true };
        } else {
          // Handle specific error cases
          console.error(`[@context:HostManagerProvider] Failed to take control:`, result);

          let errorType: any = 'generic_error';
          let errorMessage = result.error || 'Failed to take control of device';

          if (result.error_type === 'stream_service_error') {
            errorType = 'stream_service_error';
            errorMessage = `AV Stream Error: ${result.error}`;
          } else if (result.error_type === 'adb_connection_error') {
            errorType = 'adb_connection_error';
            errorMessage = `Remote Connection Error: ${result.error}`;
          } else if (result.status === 'device_locked') {
            errorType = 'device_locked';
            errorMessage = `Device is locked by ${result.locked_by || 'another user'}`;
          } else if (result.status === 'device_not_found') {
            errorType = 'device_not_found';
            errorMessage = `Device ${host.host_name}:${effectiveDeviceId} not found or offline`;
          } else if (result.error && result.error.includes('secret key')) {
            errorType = 'server_configuration_error';
            errorMessage = `Server configuration error: Flask secret key not configured. Please restart the server.`;
          } else if (response.status === 409 && result.locked_by_same_user) {
            console.log(
              `[@context:HostManagerProvider] Device ${host.host_name}:${effectiveDeviceId} locked by same user, reclaiming lock`,
            );
            setActiveLocks((prev) =>
              new Map(prev).set(`${host.host_name}:${effectiveDeviceId}`, userId),
            );
            return { success: true };
          }

          return {
            success: false,
            error: errorMessage,
            errorType,
            details: result,
          };
        }
      } catch (error: any) {
        console.error(
          `[@context:HostManagerProvider] Exception taking control of device ${host.host_name}:${device_id || 'device1'}:`,
          error,
        );
        return {
          success: false,
          error: `Network error: ${error.message || 'Failed to communicate with server'}`,
          errorType: 'network_error',
          details: error,
        };
      }
    },
    [browserSessionId, userId],
  );

  // Release control via server control endpoint
  const releaseControl = useCallback(
    async (
      host: Host,
      device_id?: string,
      sessionId?: string,
    ): Promise<{
      success: boolean;
      error?: string;
      errorType?: 'network_error' | 'generic_error';
      details?: any;
    }> => {
      try {
        const effectiveSessionId = sessionId || browserSessionId;
        const effectiveDeviceId = device_id || 'device1';

        console.log(
          `[@context:HostManagerProvider] Releasing control of device: ${host.host_name}, device_id: ${effectiveDeviceId}`,
        );
        console.log(`[@context:HostManagerProvider] Using user ID for unlock: ${userId}`);

        const response = await fetch('/server/control/releaseControl', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            host: host,
            device_id: effectiveDeviceId,
            session_id: effectiveSessionId,
            user_id: userId,
          }),
        });

        if (!response.ok) {
          throw new Error(`Failed to release control of device: ${response.statusText}`);
        }

        const result = await response.json();

        if (result.success) {
          console.log(
            `[@context:HostManagerProvider] Successfully released control of device: ${host.host_name}:${effectiveDeviceId}`,
          );
          // Remove lock using device-oriented key
          setActiveLocks((prev) => {
            const newMap = new Map(prev);
            newMap.delete(`${host.host_name}:${effectiveDeviceId}`);
            return newMap;
          });
          return { success: true };
        } else {
          console.error(
            `[@context:HostManagerProvider] Server failed to release control of device: ${result.error}`,
          );
          return {
            success: false,
            error: result.error || 'Failed to release control of device',
            errorType: 'generic_error',
            details: result,
          };
        }
      } catch (error: any) {
        console.error(
          `[@context:HostManagerProvider] Exception releasing control of device ${host.host_name}:${device_id || 'device1'}:`,
          error,
        );
        return {
          success: false,
          error: `Network error: ${error.message || 'Failed to communicate with server'}`,
          errorType: 'network_error',
          details: error,
        };
      }
    },
    [browserSessionId, userId],
  );

  // Check if we have an active lock for a device
  const hasActiveLock = useCallback(
    (deviceKey: string): boolean => {
      // Support both legacy "hostname" and new "hostname:device_id" formats
      if (deviceKey.includes(':')) {
        return activeLocks.has(deviceKey);
      } else {
        // Legacy support: check for any device on this host
        const hostLocks = Array.from(activeLocks.keys()).filter((key) =>
          key.startsWith(`${deviceKey}:`),
        );
        return hostLocks.length > 0 || activeLocks.has(deviceKey);
      }
    },
    [activeLocks],
  );

  // Check if device is locked (based on host data and local active locks)
  const isDeviceLocked = useCallback(
    (host: Host | null, deviceId?: string): boolean => {
      if (!host) return false;

      const deviceKey = deviceId ? `${host.host_name}:${deviceId}` : host.host_name;

      // If we have an active lock for this device, it's not locked for us
      if (hasActiveLock(deviceKey)) {
        return false;
      }

      // Otherwise, check the server-provided lock status
      return host.isLocked || false;
    },
    [hasActiveLock],
  );

  // Check if device can be locked (based on host data)
  const canLockDevice = useCallback(
    (host: Host | null, deviceId?: string): boolean => {
      if (!host) return false;

      // Check if specific device exists if deviceId is provided
      if (deviceId && host.devices) {
        const device = host.devices.find((d) => d.device_id === deviceId);
        if (!device) return false;
      }

      return host.status === 'online' && !isDeviceLocked(host, deviceId);
    },
    [isDeviceLocked],
  );

  // ========================================
  // UI HANDLERS
  // ========================================

  // Handle device selection
  const handleDeviceSelect = useCallback((host: Host | null, deviceId: string | null) => {
    if (!host || !deviceId) {
      setSelectedHost(null);
      setSelectedDeviceId(null);
      return;
    }

    // Verify device exists in host
    const device = host.devices?.find((d) => d.device_id === deviceId);
    if (!device) {
      console.error(
        `[@context:HostManagerProvider] Device ${deviceId} not found in host ${host.host_name}`,
      );
      setSelectedHost(null);
      setSelectedDeviceId(null);
      return;
    }

    setSelectedHost(host);
    setSelectedDeviceId(deviceId);
  }, []);

  // Handle control state changes (called from header after successful device control)
  const handleControlStateChange = useCallback((active: boolean) => {
    setIsControlActive(active);

    if (active) {
      // Show panels when control is active
      setShowRemotePanel(true);
      setShowAVPanel(true);
      setIsRemotePanelOpen(true);
    } else {
      // Hide panels when control is inactive
      setShowRemotePanel(false);
      setShowAVPanel(false);
      setIsRemotePanelOpen(false);
    }
  }, []);

  // Handle remote panel toggle
  const handleToggleRemotePanel = useCallback(() => {
    const newState = !isRemotePanelOpen;
    setIsRemotePanelOpen(newState);
  }, [isRemotePanelOpen]);

  // Handle connection change (for panels)
  const handleConnectionChange = useCallback((_connected: boolean) => {
    // Could update UI state based on connection status
  }, []);

  // Handle disconnect complete (for panels)
  const handleDisconnectComplete = useCallback(() => {
    setIsControlActive(false);
    setShowRemotePanel(false);
    setShowAVPanel(false);
    setIsRemotePanelOpen(false);
  }, []);

  // ========================================
  // EFFECTS
  // ========================================

  // Initialize lock reclaim on mount (skip for Heatmap page)
  useEffect(() => {
    if (!initializedRef.current && !isHeatmapPage) {
      initializedRef.current = true;
      reclaimUserLocks();
    }
  }, [reclaimUserLocks, isHeatmapPage]);

  // Clean up locks on unmount
  useEffect(() => {
    return () => {
      // Clean up any active locks when component unmounts
      activeLocks.forEach(async (_lockUserId, hostName) => {
        try {
          console.log(`[@context:HostManagerProvider] Cleaning up lock for ${hostName} on unmount`);
          const host = availableHosts.find((h) => h.host_name === hostName);
          if (host) {
            await releaseControl(host);
          }
        } catch (error) {
          console.error(
            `[@context:HostManagerProvider] Error cleaning up lock for ${hostName}:`,
            error,
          );
        }
      });
    };
  }, [releaseControl, activeLocks, availableHosts]);

  // Update filtered hosts when availableHosts changes
  useEffect(() => {
    if (stableUserInterface?.models && availableHosts.length > 0) {
      // Filter hosts to only include those with devices matching the interface models
      const compatibleHosts = availableHosts.filter((host) =>
        host.devices?.some((device) => stableUserInterface.models!.includes(device.device_model)),
      );

      setFilteredAvailableHosts(compatibleHosts);
    } else {
      setFilteredAvailableHosts(availableHosts);
    }
  }, [availableHosts, stableUserInterface?.models]);

  // ========================================
  // CONTEXT VALUE
  // ========================================

  const contextValue = useMemo(
    () => ({
      // Panel and UI state
      selectedHost,
      selectedDeviceId,
      isControlActive,
      isRemotePanelOpen,
      showRemotePanel,
      showAVPanel,
      isVerificationActive,

      // Host data (filtered by interface models)
      availableHosts: filteredAvailableHosts,
      getHostByName,
      isLoading,
      error,

      // Direct data access functions
      getAllHosts,
      getHostsByModel,
      getAllDevices,
      getDevicesFromHost,
      getDevicesByCapability,

      // Panel and control actions
      setSelectedHost,
      setSelectedDeviceId,
      setIsControlActive,
      setIsRemotePanelOpen,
      setShowRemotePanel,
      setShowAVPanel,
      setIsVerificationActive: (active: boolean) => _setIsVerificationActive(active),

      // Lock management
      reclaimLocks: async () => {
        await reclaimUserLocks();
        return true;
      },

      // Device control methods
      takeControl,
      releaseControl,
      isDeviceLocked,
      canLockDevice,
      hasActiveLock,

      // Panel and UI handlers
      handleDeviceSelect,
      handleControlStateChange,
      handleToggleRemotePanel,
      handleConnectionChange,
      handleDisconnectComplete,
    }),
    [
      // Include all dependencies
      selectedHost,
      selectedDeviceId,
      isControlActive,
      isRemotePanelOpen,
      showRemotePanel,
      showAVPanel,
      isVerificationActive,
      filteredAvailableHosts,
      getHostByName,
      isLoading,
      error,
      getAllHosts,
      getHostsByModel,
      getAllDevices,
      getDevicesFromHost,
      getDevicesByCapability,
      reclaimUserLocks,
      takeControl,
      releaseControl,
      isDeviceLocked,
      canLockDevice,
      hasActiveLock,
      handleDeviceSelect,
      handleControlStateChange,
      handleToggleRemotePanel,
      handleConnectionChange,
      handleDisconnectComplete,
    ],
  );

  return <HostManagerContext.Provider value={contextValue}>{children}</HostManagerContext.Provider>;
};

HostManagerProvider.displayName = 'HostManagerProvider';
