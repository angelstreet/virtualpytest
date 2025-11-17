import React, { useState, useCallback, useEffect, useMemo, useRef } from 'react';
import { useLocation } from 'react-router-dom';

import { useUserSession } from '../hooks/useUserSession';
import { useServerManager } from '../hooks/useServerManager';
import { Host, Device } from '../types/common/Host_Types';
import { buildServerUrl } from '../utils/buildUrlUtils';
import { clearUserInterfaceCaches } from '../hooks/pages/useUserInterface';
import { hasCompatibleDevice } from '../utils/userinterface/deviceCompatibilityUtils';
import { useToast } from '../hooks/useToast';

import { HostManagerContext } from './HostManagerContext';
import { HostDataContext } from './HostDataContext';
import { HostControlContext } from './HostControlContext';

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

  // Get server selection and server data from ServerManager (now centralized)
  const { selectedServer, availableServers, setSelectedServer, serverHostsData, isLoading: serverLoading, error: serverError, refreshServerData } = useServerManager();
  
  // Toast notifications
  const { showWarning } = useToast();

  // Extract hosts from server data, filtering by selected server only
  // This ensures we only show hosts from the currently selected server
  const [selectedServerError, setSelectedServerError] = useState<string | null>(null);
  const cacheRefreshAttemptedRef = useRef<string | null>(null);
  
  const allHostsFromServers = useMemo(() => {
    if (!selectedServer) return [];
    
    const selectedServerData = serverHostsData.find(
      serverData => serverData.server_info.server_url === selectedServer
    );
    
    if (!selectedServerData) {
      if (!serverLoading) {
        setSelectedServerError('Selected server is not responding. Please select another server.');
      }
      return [];
    } else {
      setSelectedServerError(null);
    }
    
    console.log('[@HostManagerProvider] Using hosts from selected server:', {
      serverUrl: selectedServer,
      serverName: selectedServerData.server_info.server_name,
      hostCount: selectedServerData.hosts.length
    });
    
    return selectedServerData.hosts;
  }, [serverHostsData, selectedServer, serverLoading]);
  
  // Invalidate cache if hostCount is 0 (side effect in useEffect, not useMemo)
  useEffect(() => {
    // Only attempt refresh once per selected server (don't include length in cache key)
    const cacheKey = `${selectedServer}`;
    
    if (
      allHostsFromServers.length === 0 && 
      !serverLoading && 
      selectedServer &&
      serverHostsData.length > 0 && // Only refresh if we have server data but no hosts for this server
      cacheRefreshAttemptedRef.current !== cacheKey
    ) {
      console.warn('[@HostManagerProvider] hostCount is 0 - invalidating cache and forcing refresh (once)');
      cacheRefreshAttemptedRef.current = cacheKey;
      refreshServerData();
    }
  }, [allHostsFromServers.length, serverLoading, selectedServer, serverHostsData.length, refreshServerData]);

  // Use hosts from ServerManager instead of fetching separately
  const [availableHosts, setAvailableHosts] = useState<Host[]>([]);
  const isLoading = serverLoading;
  const error = serverError;

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
  const isIncidentsPage = location.pathname.includes('/monitoring/incidents');
  const isAIQueuePage = location.pathname.includes('/monitoring/ai-queue');

  // Memoize userInterface to prevent unnecessary re-renders
  const stableUserInterface = useMemo(() => userInterface, [userInterface]);

  // Update availableHosts when server data changes (from ServerManager)
  // Only update if the hosts actually changed to prevent unnecessary re-renders
  useEffect(() => {
    setAvailableHosts(prev => {
      // Quick length check first
      if (prev.length !== allHostsFromServers.length) {
        console.log('[@context:HostManagerProvider] Hosts count changed:', prev.length, '->', allHostsFromServers.length);
        return allHostsFromServers;
      }
      
      // Deep comparison: check if any host data actually changed
      const hostsChanged = allHostsFromServers.some((newHost, index) => {
        const oldHost = prev[index];
        if (!oldHost) return true;
        
        // Compare key properties
        if (oldHost.host_name !== newHost.host_name) return true;
        if (oldHost.status !== newHost.status) return true;
        if ((oldHost.devices?.length || 0) !== (newHost.devices?.length || 0)) return true;
        
        return false;
      });
      
      if (hostsChanged) {
        console.log('[@context:HostManagerProvider] Host data changed, updating');
        return allHostsFromServers;
      }
      
      // No changes, keep previous reference to prevent re-renders
      return prev;
    });
  }, [allHostsFromServers]);

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

  // Get hosts filtered by device models or capabilities
  const getHostsByModel = useCallback(
    (models: string[]): Host[] => {
      const filtered = availableHosts
        .map((host) => ({
          ...host,
          devices: (host.devices || []).filter((device) => {
            // Check exact model match first
            if (models.includes(device.device_model)) {
              return true;
            }
            // Check capability match - if model is 'web' or 'desktop', 
            // match devices that have those capabilities
            return models.some(model => 
              device.device_capabilities && (device.device_capabilities as any)[model]
            );
          }),
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
      const response = await fetch(buildServerUrl('/server/control/lockedDevices'), {
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
      tree_id_or_userinterface_id?: string,
      id_type?: 'tree_id' | 'userinterface_id'  // NEW: specify which ID type
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
        if (tree_id_or_userinterface_id) {
          const idTypeLabel = id_type || 'tree_id';
          console.log(`[@context:HostManagerProvider] Including ${idTypeLabel} for cache population: ${tree_id_or_userinterface_id}`);
        }

        // Build request body with optional tree_id OR userinterface_id for cache population
        const requestBody: any = {
          host_name: host.host_name,
          device_id: effectiveDeviceId,
          session_id: effectiveSessionId,
          user_id: userId,
        };

        // Add tree_id OR userinterface_id if provided (server resolves tree_id from userinterface_id)
        if (tree_id_or_userinterface_id) {
          if (id_type === 'userinterface_id') {
            requestBody.userinterface_id = tree_id_or_userinterface_id;
          } else {
            // Default to tree_id for backward compatibility
            requestBody.tree_id = tree_id_or_userinterface_id;
          }
          // team_id is automatically added by buildServerUrl
        }

        const response = await fetch(buildServerUrl('/server/control/takeControl'), {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(requestBody),
        });

        const result = await response.json();

        if (response.ok && result.success) {
          // Show warning toast if controller failed (e.g., ADB connection failed)
          if (result.warning) {
            showWarning(result.warning, { duration: 6000 });
          }
          
          // Clear user interface caches to fetch fresh data on take-control
          // This ensures multi-user scenarios get latest data when taking control
          clearUserInterfaceCaches();
          
          console.log(
            `[@context:HostManagerProvider] Successfully took control of device: ${host.host_name}:${effectiveDeviceId}`,
          );
          // Store lock using device-oriented key
          setActiveLocks((prev) =>
            new Map(prev).set(`${host.host_name}:${effectiveDeviceId}`, userId),
          );
          
          // ✅ Reload device action schemas for editing capabilities
          // Only reload if action schemas are not already present (performance optimization)
          const deviceWithSchemas = host.devices?.find((d: any) => 
            d.device_id === effectiveDeviceId && 
            d.device_action_types && 
            Object.keys(d.device_action_types).length > 0
          );
          
          if (deviceWithSchemas) {
            console.log(`[@context:HostManagerProvider] Action schemas already loaded for ${host.host_name}:${effectiveDeviceId}, skipping reload`);
          } else {
            try {
              console.log(`[@context:HostManagerProvider] Loading action schemas for ${host.host_name}:${effectiveDeviceId}...`);
              const schemaResponse = await fetch(
                buildServerUrl(`/server/system/getDeviceActions?host_name=${encodeURIComponent(host.host_name)}&device_id=${encodeURIComponent(effectiveDeviceId)}`)
              );
              if (schemaResponse.ok) {
                const schemaData = await schemaResponse.json();
                if (schemaData.success) {
                  // Update just this device's action/verification schemas
                  setAvailableHosts((prev) => {
                    const updated = prev.map((h) => {
                      if (h.host_name === host.host_name) {
                        return {
                          ...h,
                          devices: h.devices?.map((d: any) => {
                            if (d.device_id === effectiveDeviceId) {
                              return {
                                ...d,
                                device_action_types: schemaData.device_action_types,
                                device_verification_types: schemaData.device_verification_types
                              };
                            }
                            return d;
                          })
                        };
                      }
                      return h;
                    });
                    
                    // Also update selectedHost if it's the same host
                    setSelectedHost((prevSelectedHost) => {
                      if (prevSelectedHost && prevSelectedHost.host_name === host.host_name) {
                        const updatedHost = updated.find(h => h.host_name === host.host_name);
                        if (updatedHost) {
                          console.log(`[@context:HostManagerProvider] Updating selectedHost with new schemas`);
                          return updatedHost;
                        }
                      }
                      return prevSelectedHost;
                    });
                    
                    return updated;
                  });
                  console.log(`[@context:HostManagerProvider] Action schemas loaded for ${host.host_name}:${effectiveDeviceId}`);
                }
              }
            } catch (error) {
              console.warn(`[@context:HostManagerProvider] Failed to load device action schemas (non-critical):`, error);
            }
          }
          
          return { success: true };
        } else {
          // Handle specific error cases
          console.error(`[@context:HostManagerProvider] Failed to take control:`, result);

          let errorType: any = 'generic_error';
          let errorMessage = result.error || 'Failed to take control of device';

          if (result.errorType === 'stream_service_error' || result.error_type === 'stream_service_error') {
            errorType = 'stream_service_error';
            errorMessage = `AV Stream Error: ${result.error}`;
          } else if (result.errorType === 'adb_connection_error' || result.error_type === 'adb_connection_error') {
            errorType = 'adb_connection_error';
            errorMessage = `Remote Connection Error: ${result.error}`;
          } else if (result.errorType === 'device_locked' || result.status === 'device_locked') {
            errorType = 'device_locked';
            errorMessage = `Device is locked by ${result.locked_by || 'another user'}`;
          } else if (result.errorType === 'device_not_found' || result.status === 'device_not_found') {
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

        const response = await fetch(buildServerUrl('/server/control/releaseControl'), {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            host_name: host.host_name,
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
      console.log('[@HostManagerProvider] Device control activated - panels shown');
    } else {
      // Hide panels when control is inactive
      setShowRemotePanel(false);
      setShowAVPanel(false);
      setIsRemotePanelOpen(false);
      console.log('[@HostManagerProvider] Device control deactivated - panels hidden');
    }
    
    // Note: Navigation tree lock is now handled in NavigationEditor
    // to maintain separation of concerns between device control and tree editing
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

  // Initialize lock reclaim on mount (skip for incidents and AI queue pages)
  useEffect(() => {
    if (!initializedRef.current && !isIncidentsPage && !isAIQueuePage) {
      initializedRef.current = true;
      reclaimUserLocks();
    }
  }, [reclaimUserLocks, isIncidentsPage, isAIQueuePage]);

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

  // Update filtered hosts when availableHosts changes - using shared compatibility logic
  useEffect(() => {
    if (stableUserInterface?.models && availableHosts.length > 0) {
      // Filter hosts to only include those with devices compatible with the interface
      const compatibleHosts = availableHosts.filter((host) =>
        hasCompatibleDevice(host.devices || [], stableUserInterface as any)
      );

      setFilteredAvailableHosts(compatibleHosts);
    } else {
      setFilteredAvailableHosts(availableHosts);
    }
  }, [availableHosts, stableUserInterface?.models]);

  // ========================================
  // CONTEXT VALUES - Split into Data and Control
  // ========================================

  // Host Data Context - static data (rarely changes)
  const hostDataValue = useMemo(
    () => ({
      // Server selection state
      selectedServer,
      availableServers,
      setSelectedServer,

      // Host data (filtered by interface models)
      availableHosts: filteredAvailableHosts,
      getHostByName,
      isLoading,
      error: serverError || selectedServerError, // Combine errors

      // Direct data access functions
      getAllHosts,
      getHostsByModel,
      getAllDevices,
      getDevicesFromHost,
      getDevicesByCapability,
    }),
    [
      selectedServer,
      availableServers,
      setSelectedServer,
      filteredAvailableHosts,
      getHostByName,
      isLoading,
      error,
      getAllHosts,
      getHostsByModel,
      getAllDevices,
      getDevicesFromHost,
      getDevicesByCapability,
      serverError,
      selectedServerError,
    ],
  );

  // Host Control Context - dynamic control state (changes frequently)
  const hostControlValue = useMemo(
    () => ({
      // Panel and UI state
      selectedHost,
      selectedDeviceId,
      isControlActive,
      isRemotePanelOpen,
      showRemotePanel,
      showAVPanel,
      isVerificationActive,

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
    }),
    [
      selectedHost,
      selectedDeviceId,
      isControlActive,
      isRemotePanelOpen,
      showRemotePanel,
      showAVPanel,
      isVerificationActive,
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
      reclaimUserLocks,
    ],
  );

  // Legacy combined context for backward compatibility
  const contextValue = useMemo(
    () => ({
      ...hostDataValue,
      ...hostControlValue,
    }),
    [hostDataValue, hostControlValue],
  );

  return (
    <HostDataContext.Provider value={hostDataValue}>
      <HostControlContext.Provider value={hostControlValue}>
        <HostManagerContext.Provider value={contextValue}>
          {children}
        </HostManagerContext.Provider>
      </HostControlContext.Provider>
    </HostDataContext.Provider>
  );
};

HostManagerProvider.displayName = 'HostManagerProvider';
