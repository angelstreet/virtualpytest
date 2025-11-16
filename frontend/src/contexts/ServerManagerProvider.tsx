import React, { useState, useCallback, useEffect, useMemo, useRef } from 'react';
import { ServerManagerContext } from './ServerManagerContext';
import { ServerHostData } from '../types/common/Server_Types';
import { getAllServerUrls, buildServerUrlForServer } from '../utils/buildUrlUtils';
import { CACHE_CONFIG, STORAGE_KEYS } from '../config/constants';

interface ServerManagerProviderProps {
  children: React.ReactNode;
}

interface CachedData {
  data: ServerHostData[];
  timestamp: number;
}

/**
 * Server Manager Provider
 * 
 * Manages backend server selection and server data fetching.
 * Handles multi-server architecture where frontend can connect to multiple backend servers.
 * 
 * Features:
 * - Server selection with localStorage persistence
 * - Fetches server info and hosts from all configured servers
 * - Provides centralized server state management
 * - Caches server data for 30 seconds to show fresh host status after reboot
 */
export const ServerManagerProvider: React.FC<ServerManagerProviderProps> = ({ children }) => {
  // ========================================
  // STATE
  // ========================================

  // Get all configured server URLs from environment
  const availableServers = useMemo(() => getAllServerUrls(), []);

  // Selected server state with localStorage persistence
  const [selectedServer, setSelectedServerState] = useState<string>(() => {
    try {
      const saved = localStorage.getItem('selectedServer');
      return saved && availableServers.includes(saved) ? saved : availableServers[0] || '';
    } catch {
      return availableServers[0] || '';
    }
  });

  // Server data state - Initialize from cache if available (even if stale, for immediate display)
  const [serverHostsData, setServerHostsData] = useState<ServerHostData[]>(() => {
    try {
      const cached = localStorage.getItem(STORAGE_KEYS.SERVER_HOSTS_CACHE);
      if (cached) {
        const { data, timestamp }: CachedData = JSON.parse(cached);
        const age = Date.now() - timestamp;
        // Use cached data even if stale (better than showing empty combobox)
        // Background refresh will update it if stale
        console.log(`[@ServerManager] Using cached data (age: ${Math.round(age / 1000)}s, ${age < CACHE_CONFIG.VERY_SHORT_TTL ? 'FRESH' : 'STALE - will refresh'})`);
        return data;
      }
    } catch (error) {
      console.warn('[@ServerManager] Failed to load cached data:', error);
    }
    return [];
  });

  // Check if we have FRESH (not stale) cached data on initial load
  const hasFreshCache = useMemo(() => {
    try {
      const cached = localStorage.getItem(STORAGE_KEYS.SERVER_HOSTS_CACHE);
      if (cached) {
        const { timestamp }: CachedData = JSON.parse(cached);
        const age = Date.now() - timestamp;
        return age < CACHE_CONFIG.VERY_SHORT_TTL;
      }
    } catch {
      return false;
    }
    return false;
  }, []);

  const [isLoading, setIsLoading] = useState(!hasFreshCache);
  const [error, setError] = useState<string | null>(null);
  const [pendingServers, setPendingServers] = useState<Set<string>>(new Set());
  const [failedServers, setFailedServers] = useState<Set<string>>(new Set());

  // Ref to prevent duplicate API calls
  const isRequestInProgress = useRef(false);

  // ========================================
  // SERVER SELECTION
  // ========================================

  // Wrapper to persist server selection to localStorage
  const setSelectedServer = useCallback((serverUrl: string) => {
    setSelectedServerState(serverUrl);
    try {
      localStorage.setItem('selectedServer', serverUrl);
      console.log('[@ServerManager] Server selection saved:', serverUrl);
    } catch (error) {
      console.warn('[@ServerManager] Failed to save selected server to localStorage:', error);
    }
  }, []);

  // ========================================
  // SERVER DATA FETCHING
  // ========================================

  /**
   * Fetch server information and hosts from all configured servers
   * Non-blocking: Shows partial data if some servers fail
   */
  const fetchServerData = useCallback(async (forceRefresh = false) => {
    // Check cache first (unless force refresh)
    if (!forceRefresh) {
      try {
        const cached = localStorage.getItem(STORAGE_KEYS.SERVER_HOSTS_CACHE);
        if (cached) {
          const { data, timestamp }: CachedData = JSON.parse(cached);
          const age = Date.now() - timestamp;
          if (age < CACHE_CONFIG.VERY_SHORT_TTL) {
            console.log(`[@ServerManager] Using cached data (age: ${Math.round(age / 1000)}s)`);
            setServerHostsData(data);
            setIsLoading(false);
            isRequestInProgress.current = false;
            return;
          }
        }
      } catch (error) {
        console.warn('[@ServerManager] Failed to load cached data:', error);
      }
    }

    // Prevent duplicate calls
    if (isRequestInProgress.current) {
      console.log('[@ServerManager] Request already in progress, skipping duplicate call');
      return;
    }

    isRequestInProgress.current = true;
    setIsLoading(true);
    setError(null);
    // Don't reset serverHostsData to empty - keep old data while fetching
    // This prevents triggering hostCount=0 conditions during refresh
    setPendingServers(new Set(availableServers));
    setFailedServers(new Set()); // Reset failed servers

    // Fetch from all servers in parallel
    const promises = availableServers.map(async (serverUrl) => {
      try {
        // Fetch hosts WITH system stats but WITHOUT action schemas
        // System stats (~5-10KB) are needed for Dashboard monitoring
        // Action schemas (~190KB) are only needed when taking control, handled by DeviceDataContext
        const response = await fetch(buildServerUrlForServer(serverUrl, '/server/system/getAllHosts?include_actions=false&include_system_stats=true'), {
          signal: AbortSignal.timeout(10000) // Increased to 10s
        });
        
        if (response.ok) {
          const data = await response.json();
          const urlParts = new URL(serverUrl);
          const cleanUrl = serverUrl.replace(/^https?:\/\//, '').replace(/:\d+$/, '');
          
          const serverData = {
            server_info: {
              server_name: data.server_info?.server_name || 'Unknown Server',
              server_url: serverUrl,
              server_url_display: cleanUrl,
              server_port: urlParts.port || (urlParts.protocol === 'https:' ? '443' : '80'),
              // Include server system stats for Dashboard monitoring
              system_stats: data.server_info?.system_stats || null
            },
            hosts: data.hosts || []
          };

          return { success: true, serverUrl, data: serverData };
        } else {
          console.warn(`[@ServerManager] Failed response from ${serverUrl}: ${response.status}`);
          setFailedServers(prev => new Set(prev).add(serverUrl));
          return { success: false, serverUrl, data: null };
        }
      } catch (error: any) {
        console.warn(`[@ServerManager] Error from ${serverUrl}: ${error.message}`);
        setFailedServers(prev => new Set(prev).add(serverUrl));
        return { success: false, serverUrl, data: null };
      } finally {
        // Remove from pending
        setPendingServers(prev => {
          const newSet = new Set(prev);
          newSet.delete(serverUrl);
          return newSet;
        });
      }
    });

    // Wait for all requests to complete
    const results = await Promise.all(promises);
    
    // Extract successful server data
    const allServerData = results
      .filter(result => result.success && result.data)
      .map(result => result.data!);

    // Update state with new data (replaces old data atomically)
    setServerHostsData(allServerData);

    // Cache the data if we have any
    if (allServerData.length > 0) {
      try {
        const cacheData: CachedData = {
          data: allServerData,
          timestamp: Date.now()
        };
        localStorage.setItem(STORAGE_KEYS.SERVER_HOSTS_CACHE, JSON.stringify(cacheData));
        console.log('[@ServerManager] Data cached successfully');
      } catch (error) {
        console.warn('[@ServerManager] Failed to cache data:', error);
      }
    }

    setIsLoading(false);
    isRequestInProgress.current = false;
  }, [availableServers, selectedServer]);

  /**
   * Manual refresh function - forces a fresh fetch bypassing cache
   */
  const refreshServerData = useCallback(async () => {
    console.log('[@ServerManager] Manual refresh requested - bypassing cache');
    await fetchServerData(true);
  }, [fetchServerData]);

  // ========================================
  // EFFECTS
  // ========================================

  // Initial data fetch on mount only
  // We fetch ALL servers once, then switching servers is just a client-side operation
  useEffect(() => {
    if (availableServers.length > 0) {
      console.log('[@ServerManager] Initial data fetch');
      fetchServerData();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Only run once on mount

  // Auto-switch away from failed server after initial load
  useEffect(() => {
    if (!isLoading && failedServers.has(selectedServer)) {
      // Find first working server
      const workingServer = availableServers.find(s => !failedServers.has(s));
      if (workingServer) {
        console.log(`[@ServerManager] Selected server ${selectedServer} is down, switching to ${workingServer}`);
        setSelectedServer(workingServer);
      }
    }
  }, [isLoading, failedServers, selectedServer, availableServers, setSelectedServer]);

  // ========================================
  // CONTEXT VALUE
  // ========================================

  const contextValue = useMemo(
    () => ({
      // Server selection
      selectedServer,
      availableServers,
      setSelectedServer,

      // Server data
      serverHostsData,
      isLoading,
      error,
      pendingServers,
      failedServers,

      // Actions
      refreshServerData,
    }),
    [selectedServer, availableServers, setSelectedServer, serverHostsData, isLoading, error, refreshServerData, pendingServers, failedServers]
  );

  return (
    <ServerManagerContext.Provider value={contextValue}>
      {children}
    </ServerManagerContext.Provider>
  );
};

ServerManagerProvider.displayName = 'ServerManagerProvider';
