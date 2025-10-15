import React, { useState, useCallback, useEffect, useMemo, useRef } from 'react';
import { ServerManagerContext } from './ServerManagerContext';
import { ServerHostData } from '../types/common/Server_Types';
import { getAllServerUrls, buildServerUrlForServer } from '../utils/buildUrlUtils';

interface ServerManagerProviderProps {
  children: React.ReactNode;
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

  // Server data state
  const [serverHostsData, setServerHostsData] = useState<ServerHostData[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
  const fetchServerData = useCallback(async () => {
    // Prevent duplicate calls
    if (isRequestInProgress.current) {
      console.log('[@ServerManager] Request already in progress, skipping duplicate call');
      return;
    }

    try {
      isRequestInProgress.current = true;
      setIsLoading(true);
      setError(null);

      console.log('[@ServerManager] Fetching data from all servers:', availableServers);

      // Fetch from all servers with timeout to prevent blocking
      const serverDataPromises = availableServers.map(async (serverUrl) => {
        try {
          // Race between fetch and timeout to prevent blocking
          const fetchPromise = fetch(buildServerUrlForServer(serverUrl, '/server/system/getAllHosts'), {
            signal: AbortSignal.timeout(5000) // 5 second timeout per server
          });
          
          const response = await fetchPromise;
          
          if (response.ok) {
            const data = await response.json();
            
            // Use backend's SERVER_NAME and keep full URL for functionality
            const urlParts = new URL(serverUrl);
            const cleanUrl = serverUrl.replace(/^https?:\/\//, '').replace(/:\d+$/, '');
            
            console.log('[@ServerManager] Server data received:', {
              serverUrl,
              serverName: data.server_info?.server_name,
              hostsCount: data.hosts?.length || 0
            });

            return {
              server_info: {
                server_name: data.server_info?.server_name || 'Unknown Server',
                server_url: serverUrl, // Keep full URL for localStorage/API calls
                server_url_display: cleanUrl, // Clean URL for display only
                server_port: urlParts.port || (urlParts.protocol === 'https:' ? '443' : '80')
              },
              hosts: data.hosts || []
            };
          } else {
            console.warn('[@ServerManager] Failed to fetch from server:', serverUrl, response.status);
          }
        } catch (error: any) {
          if (error.name === 'TimeoutError') {
            console.warn(`[@ServerManager] Timeout fetching from ${serverUrl} - continuing with other servers`);
          } else {
            console.warn(`[@ServerManager] Error fetching from ${serverUrl}:`, error.message, '- continuing with other servers');
          }
        }
        return null;
      });

      const results = (await Promise.all(serverDataPromises)).filter(Boolean) as ServerHostData[];
      
      // Batch state updates to prevent multiple re-renders
      const totalHosts = results.reduce((sum, s) => sum + s.hosts.length, 0);
      console.log('[@ServerManager] Server data fetched successfully:', {
        serverCount: results.length,
        totalHosts
      });
      
      // Single state update with both values
      setServerHostsData(results);
      setIsLoading(false);

    } catch (err) {
      const errorMessage = 'Failed to fetch server data';
      setError(errorMessage);
      setIsLoading(false);
      console.error('[@ServerManager]', errorMessage, err);
    } finally {
      isRequestInProgress.current = false;
    }
  }, [availableServers]);

  /**
   * Manual refresh function
   */
  const refreshServerData = useCallback(async () => {
    await fetchServerData();
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

      // Actions
      refreshServerData,
    }),
    [selectedServer, availableServers, setSelectedServer, serverHostsData, isLoading, error, refreshServerData]
  );

  return (
    <ServerManagerContext.Provider value={contextValue}>
      {children}
    </ServerManagerContext.Provider>
  );
};

ServerManagerProvider.displayName = 'ServerManagerProvider';
