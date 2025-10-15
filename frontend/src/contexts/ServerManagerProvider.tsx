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
  const fetchServerData = useCallback(async () => {
    // Prevent duplicate calls
    if (isRequestInProgress.current) {
      console.log('[@ServerManager] Request already in progress, skipping duplicate call');
      return;
    }

    isRequestInProgress.current = true;
    setIsLoading(true);
    setError(null);
    setServerHostsData([]); // Reset to empty
    setPendingServers(new Set(availableServers));
    setFailedServers(new Set()); // Reset failed servers
    
    availableServers.forEach(async (serverUrl) => {
      try {
        const response = await fetch(buildServerUrlForServer(serverUrl, '/server/system/getAllHosts'), {
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
              server_port: urlParts.port || (urlParts.protocol === 'https:' ? '443' : '80')
            },
            hosts: data.hosts || []
          };
          
          // Append this server's data
          setServerHostsData(prev => [...prev, serverData]);
          
          // If this is the selected server, stop loading
          if (serverUrl === selectedServer) {
            setIsLoading(false);
          }
        } else {
          console.warn(`[@ServerManager] Failed response from ${serverUrl}: ${response.status}`);
          // Mark as failed
          setFailedServers(prev => new Set(prev).add(serverUrl));
        }
      } catch (error: any) {
        console.warn(`[@ServerManager] Error from ${serverUrl}: ${error.message}`);
        // Mark as failed
        setFailedServers(prev => new Set(prev).add(serverUrl));
      } finally {
        // Remove from pending
        setPendingServers(prev => {
          const newSet = new Set(prev);
          newSet.delete(serverUrl);
          if (newSet.size === 0) {
            setIsLoading(false); // All done
          }
          return newSet;
        });
      }
    });
  }, [availableServers, selectedServer]);

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
