import React, { createContext, useContext, useCallback, useState, useMemo } from 'react';

import { useUserSession } from '../../hooks/useUserSession';
import { UINavigationNode, UINavigationEdge } from '../../types/pages/Navigation_Types';

// ========================================
// TYPES
// ========================================

interface NavigationConfigContextType {
  // Lock management
  isLocked: boolean;
  lockInfo: any;
  isCheckingLock: boolean;
  showReadOnlyOverlay: boolean;
  setCheckingLockState: (checking: boolean) => void;
  lockNavigationTree: (userInterfaceId: string) => Promise<boolean>;
  unlockNavigationTree: (userInterfaceId: string) => Promise<boolean>;
  checkTreeLockStatus: (userInterfaceId: string) => Promise<void>;
  setupAutoUnlock: (userInterfaceId: string) => () => void;

  // Tree metadata operations
  loadTreeMetadata: (treeId: string) => Promise<any>;
  saveTreeMetadata: (treeId: string, metadata: any) => Promise<void>;
  deleteTree: (treeId: string) => Promise<void>;

  // Node operations
  loadTreeNodes: (treeId: string, page?: number, limit?: number) => Promise<any[]>;
  getNode: (treeId: string, nodeId: string) => Promise<any>;
  saveNode: (treeId: string, node: any) => Promise<void>;
  deleteNode: (treeId: string, nodeId: string) => Promise<void>;

  // Edge operations
  loadTreeEdges: (treeId: string, nodeIds?: string[]) => Promise<any[]>;
  getEdge: (treeId: string, edgeId: string) => Promise<any>;
  saveEdge: (treeId: string, edge: any) => Promise<void>;
  deleteEdge: (treeId: string, edgeId: string) => Promise<void>;

  // Batch operations
  loadFullTree: (treeId: string) => Promise<{tree: any, nodes: any[], edges: any[]}>;
  saveTreeData: (treeId: string, nodes: any[], edges: any[]) => Promise<void>;

  // Interface operations
  listAvailableUserInterfaces: () => Promise<any[]>;

  // Tree data
  actualTreeId: string | null;
  setActualTreeId: (treeId: string | null) => void;

  // User identification
  sessionId: string;
  userId: string;
}

interface NavigationConfigState {
  nodes: UINavigationNode[];
  edges: UINavigationEdge[];
  userInterface: any;
  setNodes: (nodes: UINavigationNode[]) => void;
  setEdges: (edges: UINavigationEdge[]) => void;
  setUserInterface: (ui: any) => void;
  setInitialState: (state: { nodes: UINavigationNode[]; edges: UINavigationEdge[] } | null) => void;
  setHasUnsavedChanges: (hasChanges: boolean) => void;
  setIsLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  setActualTreeId: (treeId: string | null) => void;
}

interface NavigationConfigProviderProps {
  children: React.ReactNode;
}

// ========================================
// CONTEXT
// ========================================

const NavigationConfigContext = createContext<NavigationConfigContextType | null>(null);

export const NavigationConfigProvider: React.FC<NavigationConfigProviderProps> = ({ children }) => {
  const { userId, sessionId } = useUserSession();

  // ========================================
  // STATE
  // ========================================

  const [isLocked, setIsLocked] = useState(false);
  const [lockInfo, setLockInfo] = useState<any>(null);
  const [isCheckingLock, setIsCheckingLock] = useState(false);
  const [showReadOnlyOverlay, setShowReadOnlyOverlay] = useState(false);
  const [actualTreeId, setActualTreeId] = useState<string | null>(null);

  // ========================================
  // LOCK MANAGEMENT
  // ========================================

  // Set checking lock state immediately (fixes race condition)
  const setCheckingLockState = useCallback((checking: boolean) => {
    setIsCheckingLock(checking);
  }, []);

  // Check lock status for a tree
  const checkTreeLockStatus = useCallback(
    async (userInterfaceId: string) => {
      try {
        setIsCheckingLock(true);

        const response = await fetch(
          `/server/navigationTrees/lockStatus?userinterface_id=${userInterfaceId}`,
          {
            headers: {
              'Content-Type': 'application/json',
            },
          },
        );

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (data.success) {
          const lockData = data.lock || null;

          if (lockData) {
            // Tree is locked by someone
            const isOurLock = lockData.session_id === sessionId;

            setIsLocked(isOurLock);
            setLockInfo(lockData);
            setShowReadOnlyOverlay(!isOurLock);
          } else {
            // Tree is not locked - user still needs to take control
            setIsLocked(false);
            setLockInfo(null);
            setShowReadOnlyOverlay(true);
          }
        } else {
          console.error(
            `[@context:NavigationConfigProvider:checkTreeLockStatus] Error:`,
            data.error,
          );
          setIsLocked(false);
          setLockInfo(null);
          setShowReadOnlyOverlay(true);
        }
      } catch (error) {
        console.error(`[@context:NavigationConfigProvider:checkTreeLockStatus] Error:`, error);
        setIsLocked(false);
        setLockInfo(null);
        setShowReadOnlyOverlay(true);
      } finally {
        setIsCheckingLock(false);
      }
    },
    [sessionId],
  );

  // Try to lock a tree
  const lockNavigationTree = useCallback(
    async (userInterfaceId: string): Promise<boolean> => {
      try {
        setIsCheckingLock(true);

        const response = await fetch(`/server/navigationTrees/lockAcquire`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            userinterface_id: userInterfaceId,
            session_id: sessionId,
            user_id: userId,
          }),
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (data.success) {
          setIsLocked(true);
          setLockInfo(data.lock);
          setShowReadOnlyOverlay(false);
          return true;
        } else {
          // Lock failed, check if it's locked by someone else
          await checkTreeLockStatus(userInterfaceId);
          return false;
        }
      } catch (error) {
        console.error(`[@context:NavigationConfigProvider:lockNavigationTree] Error:`, error);
        setIsLocked(false);
        setLockInfo(null);
        setShowReadOnlyOverlay(true);
        return false;
      } finally {
        setIsCheckingLock(false);
      }
    },
    [sessionId, userId, checkTreeLockStatus],
  );

  // Unlock a tree
  const unlockNavigationTree = useCallback(
    async (userInterfaceId: string): Promise<boolean> => {
      try {
        setIsCheckingLock(true);

        const response = await fetch(`/server/navigationTrees/lockRelease`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            userinterface_id: userInterfaceId,
            session_id: sessionId,
            user_id: userId,
          }),
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (data.success) {
          setIsLocked(false);
          setLockInfo(null);
          setShowReadOnlyOverlay(true);
          return true;
        } else {
          console.error(
            `[@context:NavigationConfigProvider:unlockNavigationTree] Error:`,
            data.error,
          );
          return false;
        }
      } catch (error) {
        console.error(`[@context:NavigationConfigProvider:unlockNavigationTree] Error:`, error);
        // On error, assume we don't have control
        setIsLocked(false);
        setLockInfo(null);
        setShowReadOnlyOverlay(true);
        return false;
      } finally {
        setIsCheckingLock(false);
      }
    },
    [sessionId, userId],
  );

  // Setup auto-unlock on page unload
  const setupAutoUnlock = useCallback(
    (userInterfaceId: string) => {
      console.log(
        `[@context:NavigationConfigProvider:setupAutoUnlock] Setting up auto-unlock for userInterface: ${userInterfaceId}`,
      );

      // Return cleanup function
      return () => {
        console.log(
          `[@context:NavigationConfigProvider:setupAutoUnlock] Cleaning up and unlocking userInterface: ${userInterfaceId}`,
        );
        // Always try to unlock - the server will handle checking if we have the lock
        unlockNavigationTree(userInterfaceId).catch((error) => {
          console.error(
            `[@context:NavigationConfigProvider:setupAutoUnlock] Error during auto-unlock:`,
            error,
          );
        });
      };
    },
    [unlockNavigationTree],
  );

  // ========================================
  // NEW NORMALIZED API OPERATIONS
  // ========================================

  // Tree metadata operations
  const loadTreeMetadata = useCallback(async (treeId: string) => {
    const response = await fetch(`/server/navigationTrees/${treeId}/metadata`);
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    const data = await response.json();
    if (!data.success) throw new Error(data.message);
    return data.tree;
  }, []);

  const saveTreeMetadata = useCallback(async (treeId: string, metadata: any) => {
    const response = await fetch(`/server/navigationTrees/${treeId}/metadata`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(metadata)
    });
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    const data = await response.json();
    if (!data.success) throw new Error(data.message);
  }, []);

  const deleteTree = useCallback(async (treeId: string) => {
    const response = await fetch(`/server/navigationTrees/${treeId}`, {
      method: 'DELETE'
    });
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    const data = await response.json();
    if (!data.success) throw new Error(data.message);
  }, []);

  // Node operations
  const loadTreeNodes = useCallback(async (treeId: string, page = 0, limit = 100) => {
    const response = await fetch(`/server/navigationTrees/${treeId}/nodes?page=${page}&limit=${limit}`);
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    const data = await response.json();
    if (!data.success) throw new Error(data.message);
    return data.nodes;
  }, []);

  const getNode = useCallback(async (treeId: string, nodeId: string) => {
    const response = await fetch(`/server/navigationTrees/${treeId}/nodes/${nodeId}`);
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    const data = await response.json();
    if (!data.success) throw new Error(data.message);
    return data.node;
  }, []);

  const saveNode = useCallback(async (treeId: string, node: any) => {
    const method = node.id ? 'PUT' : 'POST';
    const url = node.id 
      ? `/server/navigationTrees/${treeId}/nodes/${node.node_id}`
      : `/server/navigationTrees/${treeId}/nodes`;
    
    const response = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(node)
    });
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    const data = await response.json();
    if (!data.success) throw new Error(data.message);
  }, []);

  const deleteNode = useCallback(async (treeId: string, nodeId: string) => {
    const response = await fetch(`/server/navigationTrees/${treeId}/nodes/${nodeId}`, {
      method: 'DELETE'
    });
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    const data = await response.json();
    if (!data.success) throw new Error(data.message);
  }, []);

  // Edge operations
  const loadTreeEdges = useCallback(async (treeId: string, nodeIds?: string[]) => {
    const url = new URL(`/server/navigationTrees/${treeId}/edges`, window.location.origin);
    if (nodeIds) {
      nodeIds.forEach(id => url.searchParams.append('node_ids', id));
    }
    
    const response = await fetch(url.toString());
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    const data = await response.json();
    if (!data.success) throw new Error(data.message);
    return data.edges;
  }, []);

  const getEdge = useCallback(async (treeId: string, edgeId: string) => {
    const response = await fetch(`/server/navigationTrees/${treeId}/edges/${edgeId}`);
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    const data = await response.json();
    if (!data.success) throw new Error(data.message);
    return data.edge;
  }, []);

  const saveEdge = useCallback(async (treeId: string, edge: any) => {
    const method = edge.id ? 'PUT' : 'POST';
    const url = edge.id 
      ? `/server/navigationTrees/${treeId}/edges/${edge.edge_id}`
      : `/server/navigationTrees/${treeId}/edges`;
    
    const response = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(edge)
    });
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    const data = await response.json();
    if (!data.success) throw new Error(data.message);
  }, []);

  const deleteEdge = useCallback(async (treeId: string, edgeId: string) => {
    const response = await fetch(`/server/navigationTrees/${treeId}/edges/${edgeId}`, {
      method: 'DELETE'
    });
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    const data = await response.json();
    if (!data.success) throw new Error(data.message);
  }, []);

  // Batch operations
  const loadFullTree = useCallback(async (treeId: string) => {
    const response = await fetch(`/server/navigationTrees/${treeId}/full`);
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    const data = await response.json();
    if (!data.success) throw new Error(data.message);
    return data;
  }, []);

  const saveTreeData = useCallback(async (treeId: string, nodes: any[], edges: any[]) => {
    const response = await fetch(`/server/navigationTrees/${treeId}/batch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ nodes, edges })
    });
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    const data = await response.json();
    if (!data.success) throw new Error(data.message);
  }, []);

  // ========================================
  // INTERFACE OPERATIONS
  // ========================================

  // List available user interfaces
  const listAvailableUserInterfaces = useCallback(async (): Promise<any[]> => {
    try {
      const response = await fetch('/server/navigationTrees/userinterfaces');

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();

      // The navigationTrees endpoint returns wrapped in success object
      return data.success && Array.isArray(data.userinterfaces) ? data.userinterfaces : [];
    } catch (error) {
      console.error(
        `[@context:NavigationConfigProvider:listAvailableUserInterfaces] Error:`,
        error,
      );
      return [];
    }
  }, []);

  // Save tree to database using normalized API
  const saveToConfig = useCallback(
    async (userInterfaceId: string, state: NavigationConfigState) => {
      try {
        state.setIsLoading(true);
        state.setError(null);

        console.log(
          '[@context:NavigationConfigProvider:saveToConfig] Saving tree for userInterface:',
          userInterfaceId,
        );
        console.log('[@context:NavigationConfigProvider:saveToConfig] Tree data:', {
          nodes: state.nodes.length,
          edges: state.edges.length,
        });

        // Use the new normalized API to save nodes and edges
        if (actualTreeId) {
          await saveTreeData(actualTreeId, state.nodes, state.edges);
          
          console.log('[@context:NavigationConfigProvider:saveToConfig] Tree saved successfully');
          // Update initial state to reflect saved state
          state.setInitialState({ nodes: [...state.nodes], edges: [...state.edges] });
          state.setHasUnsavedChanges(false);
        } else {
          throw new Error('No tree ID available for saving');
        }
      } catch (error) {
        console.error(`[@context:NavigationConfigProvider:saveToConfig] Error saving tree:`, error);
        state.setError(error instanceof Error ? error.message : 'Unknown error occurred');
        throw error; // Re-throw to allow caller to handle
      } finally {
        state.setIsLoading(false);
      }
    },
    [actualTreeId, saveTreeData],
  );

  // List available user interfaces
  const listAvailableUserInterfaces = useCallback(async (): Promise<any[]> => {
    try {
      const response = await fetch('/server/navigationTrees/userinterfaces');

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();

      // The navigationTrees endpoint returns wrapped in success object
      return data.success && Array.isArray(data.userinterfaces) ? data.userinterfaces : [];
    } catch (error) {
      console.error(
        `[@context:NavigationConfigProvider:listAvailableUserInterfaces] Error:`,
        error,
      );
      return [];
    }
  }, []);

  // TODO: Create empty tree functionality needs to be implemented with normalized API
  // This function is currently not used but may be needed in the future
  // const createEmptyTree = useCallback(
  //   async (userInterfaceId: string, state: NavigationConfigState) => {
  //     // Implementation needed: Create tree metadata first, then add empty nodes/edges
  //     throw new Error('createEmptyTree not implemented for normalized API');
  //   },
  //   [],
  // );

  // ========================================
  // CONTEXT VALUE
  // ========================================

  const contextValue: NavigationConfigContextType = useMemo(
    () => ({
      // Lock management
      isLocked,
      lockInfo,
      isCheckingLock,
      showReadOnlyOverlay,
      setCheckingLockState,
      lockNavigationTree,
      unlockNavigationTree,
      checkTreeLockStatus,
      setupAutoUnlock,

      // Tree metadata operations
      loadTreeMetadata,
      saveTreeMetadata,
      deleteTree,

      // Node operations
      loadTreeNodes,
      getNode,
      saveNode,
      deleteNode,

      // Edge operations
      loadTreeEdges,
      getEdge,
      saveEdge,
      deleteEdge,

      // Batch operations
      loadFullTree,
      saveTreeData,

      // Interface operations
      listAvailableUserInterfaces,

      // Tree data
      actualTreeId,
      setActualTreeId,

      // User identification
      sessionId,
      userId,
    }),
    [
      isLocked,
      lockInfo,
      isCheckingLock,
      showReadOnlyOverlay,
      sessionId,
      userId,
      setCheckingLockState,
      lockNavigationTree,
      unlockNavigationTree,
      checkTreeLockStatus,
      setupAutoUnlock,
      loadTreeMetadata,
      saveTreeMetadata,
      deleteTree,
      loadTreeNodes,
      getNode,
      saveNode,
      deleteNode,
      loadTreeEdges,
      getEdge,
      saveEdge,
      deleteEdge,
      loadFullTree,
      saveTreeData,
      listAvailableUserInterfaces,
      actualTreeId,
      setActualTreeId,
    ],
  );

  return (
    <NavigationConfigContext.Provider value={contextValue}>
      {children}
    </NavigationConfigContext.Provider>
  );
};

NavigationConfigProvider.displayName = 'NavigationConfigProvider';

// ========================================
// HOOK
// ========================================

export const useNavigationConfig = (): NavigationConfigContextType => {
  const context = useContext(NavigationConfigContext);
  if (!context) {
    throw new Error('useNavigationConfig must be used within a NavigationConfigProvider');
  }
  return context;
};

// Export the type for use in other files
export type { NavigationConfigState };
