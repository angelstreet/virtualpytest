import React, { createContext, useContext, useState, useRef, useCallback, useEffect } from 'react';

import { buildServerUrl } from '../../utils/buildUrlUtils';
import { CACHE_CONFIG, STORAGE_KEYS } from '../../config/constants';

// Types for nested tree operations
export interface NavigationTree {
  id: string;
  name: string;
  userinterface_id: string;
  team_id: string;
  description?: string;
  parent_tree_id?: string;
  parent_node_id?: string;
  tree_depth: number;
  is_root_tree: boolean;
  root_node_id?: string;
  created_at: string;
  updated_at: string;
}

export interface TreeHierarchy {
  tree_id: string;
  tree_name: string;
  depth: number;
  parent_tree_id?: string;
  parent_node_id?: string;
}

export interface BreadcrumbItem {
  tree_id: string;
  tree_name: string;
  depth: number;
  node_id?: string;
}

export interface NavigationNode {
  node_id: string;
  label: string;
  node_type: string;
  position_x: number;
  position_y: number;
  verifications: any[];
  data: any; // description should be stored in data.description
  
  // Optional fields
  screenshot?: string;
  menu_type?: string;
  has_subtree?: boolean;
  subtree_count?: number;
}

// Action Set interface for bidirectional edge structure
export interface ActionSet {
  id: string; // Format: nodeA_to_nodeB
  label: string; // Format: nodeA → nodeB
  actions: any[];
  retry_actions?: any[];
  // REMOVED: priority, conditions, timer for simplicity
}

export interface NavigationEdge {
  id: string;
  edge_id: string;
  source_node_id: string;
  target_node_id: string;
  label?: string;
  description?: string;
  // NEW: Action sets structure - NO LEGACY FIELDS
  action_sets: ActionSet[]; // REQUIRED
  default_action_set_id: string; // REQUIRED
  final_wait_time: number;
  priority: string;
  threshold: number;
  metadata: any;
}

// ========================================
// TREE CACHE TYPES
// ========================================

interface TreeCacheEntry {
  data: any; // Full tree data including metrics
  timestamp: number;
}

const TREE_CACHE_STORAGE_KEY = STORAGE_KEYS.NAVIGATION_TREE_CACHE_PREFIX + 'data';

// Load tree cache from localStorage
const loadTreeCacheFromStorage = (): Map<string, TreeCacheEntry> => {
  try {
    const stored = localStorage.getItem(TREE_CACHE_STORAGE_KEY);
    if (stored) {
      const parsed = JSON.parse(stored);
      const now = Date.now();
      const cache = new Map<string, TreeCacheEntry>();
      
      // Filter out expired entries
      let validCount = 0;
      let expiredCount = 0;
      
      Object.entries(parsed).forEach(([key, entry]: [string, any]) => {
        const age = now - entry.timestamp;
        if (age < CACHE_CONFIG.VERY_SHORT_TTL) {
          cache.set(key, entry as TreeCacheEntry);
          validCount++;
        } else {
          expiredCount++;
        }
      });
      
      console.log(`[@TreeCache] Loaded ${validCount} valid tree entries from localStorage (${expiredCount} expired entries removed)`);
      return cache;
    }
  } catch (error) {
    console.warn('[@TreeCache] Failed to load tree cache from localStorage:', error);
  }
  return new Map();
};

// Save tree cache to localStorage
const saveTreeCacheToStorage = (cache: Map<string, TreeCacheEntry>): void => {
  try {
    const obj: Record<string, TreeCacheEntry> = {};
    cache.forEach((value, key) => {
      obj[key] = value;
    });
    localStorage.setItem(TREE_CACHE_STORAGE_KEY, JSON.stringify(obj));
  } catch (error) {
    console.warn('[@TreeCache] Failed to save tree cache to localStorage:', error);
  }
};

// ========================================
// CONTEXT TYPES
// ========================================

interface NavigationConfigContextType {
  // Tree metadata operations
  currentTree: NavigationTree | null;
  isLoading: boolean;
  error: string | null;
  actualTreeId: string | null;

  // Load operations
  loadTreeMetadata: (treeId: string) => Promise<NavigationTree>;
  loadTreeData: (treeId: string) => Promise<any>;
  loadTreeByUserInterface: (userInterfaceId: string, options?: { includeMetrics?: boolean; includeNested?: boolean }) => Promise<any>;
  loadTreeNodes: (treeId: string, page?: number, limit?: number) => Promise<NavigationNode[]>;
  loadTreeEdges: (treeId: string, nodeIds?: string[]) => Promise<NavigationEdge[]>;

  // Save operations
  saveNode: (treeId: string, nodeData: NavigationNode) => Promise<void>;
  saveEdge: (treeId: string, edgeData: NavigationEdge, options?: { skipCacheUpdate?: boolean }) => Promise<any>;
  
  // Batch operations
  saveTreeData: (treeId: string, nodes: any[], edges: any[], deletedNodeIds?: string[], deletedEdgeIds?: string[], viewport?: any) => Promise<void>;
  
  // Nested tree operations
  loadNodeSubTrees: (treeId: string, nodeId: string) => Promise<any[]>;
  createSubTree: (parentTreeId: string, parentNodeId: string, treeData: any) => Promise<any>;
  moveSubTree: (subtreeId: string, newParentTreeId: string, newParentNodeId: string) => Promise<void>;

  // Cache operations
  invalidateTreeCache: (userInterfaceId: string) => void;
  invalidateAllTreeCache: () => void;
  
  setActualTreeId: (treeId: string | null) => void;
}

const NavigationConfigContext = createContext<NavigationConfigContextType | null>(null);

export const NavigationConfigProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [currentTree, setCurrentTree] = useState<NavigationTree | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actualTreeId, setActualTreeId] = useState<string | null>(null);

  // Initialize tree cache from localStorage
  const treeCache = useRef<Map<string, TreeCacheEntry>>(loadTreeCacheFromStorage());
  const saveCacheTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Debounced save to localStorage
  const scheduleCacheSave = useCallback(() => {
    if (saveCacheTimeoutRef.current) {
      clearTimeout(saveCacheTimeoutRef.current);
    }
    saveCacheTimeoutRef.current = setTimeout(() => {
      saveTreeCacheToStorage(treeCache.current);
    }, 500); // Save 500ms after last update
  }, []);

  // Clean up timeout on unmount
  useEffect(() => {
    return () => {
      if (saveCacheTimeoutRef.current) {
        clearTimeout(saveCacheTimeoutRef.current);
        saveTreeCacheToStorage(treeCache.current); // Save immediately on unmount
      }
    };
  }, []);

  const loadTreeMetadata = async (treeId: string): Promise<NavigationTree> => {
    setIsLoading(true);
    try {
      const response = await fetch(buildServerUrl(`/server/navigationTrees/${treeId}`));
      const result = await response.json();
      
      if (result.success) {
        setCurrentTree(result.tree);
        setActualTreeId(treeId);
        return result.tree;
      } else {
        throw new Error(result.error);
      }
    } catch (err: any) {
      setError(err.message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const loadTreeData = async (treeId: string): Promise<any> => {
    setIsLoading(true);
    try {
      const response = await fetch(buildServerUrl(`/server/navigationTrees/${treeId}/full`));
      const result = await response.json();
      
      if (result.success) {
        setActualTreeId(treeId);
        return result;
      } else {
        throw new Error(result.error);
      }
    } catch (err: any) {
      setError(err.message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const loadTreeByUserInterface = async (userInterfaceId: string, options?: { includeMetrics?: boolean; includeNested?: boolean }): Promise<any> => {
    const includeMetrics = options?.includeMetrics || false;
    const includeNested = options?.includeNested || false;
    
    // Include server URL in cache key to prevent cross-server cache pollution
    // When user switches servers, cache from different server should not be used
    const selectedServer = localStorage.getItem('selectedServer') || 'default';
    const cacheKey = `${selectedServer}|${userInterfaceId}|metrics:${includeMetrics}|nested:${includeNested}`;
    
    // Check cache first
    const cached = treeCache.current.get(cacheKey);
    if (cached) {
      const age = Date.now() - cached.timestamp;
      if (age < CACHE_CONFIG.VERY_SHORT_TTL) {
        const ageSeconds = Math.floor(age / 1000);
        console.log(`[@TreeCache] ✅ HIT: interface ${userInterfaceId} from ${selectedServer} (age: ${ageSeconds}s, metrics: ${includeMetrics}, nested: ${includeNested})`);
        
        // Still set the tree ID from cache
        if (cached.data.tree) {
          setActualTreeId(cached.data.tree.id);
        }
        
        return cached.data;
      } else {
        // Entry expired, remove it
        treeCache.current.delete(cacheKey);
        scheduleCacheSave();
        console.log(`[@TreeCache] ⏰ EXPIRED: interface ${userInterfaceId} from ${selectedServer} (removing, will fetch fresh)`);
      }
    }
    
    // Cache miss or expired - fetch from server
    setIsLoading(true);
    try {
      // Build query parameters
      const params = new URLSearchParams();
      if (includeMetrics) params.append('include_metrics', 'true');
      if (includeNested) params.append('include_nested', 'true');
      const queryString = params.toString() ? `?${params.toString()}` : '';
      
      const url = buildServerUrl(`/server/navigationTrees/getTreeByUserInterfaceId/${userInterfaceId}${queryString}`);
      
      console.log(`[@TreeCache] 🌐 FETCH: interface ${userInterfaceId} from ${selectedServer} (metrics: ${includeMetrics}, nested: ${includeNested})`);
      
      const response = await fetch(url);
      const result = await response.json();
      
      if (result.success && result.tree) {
        setActualTreeId(result.tree.id);
        
        // Cache the result with server-aware key
        treeCache.current.set(cacheKey, {
          data: result,
          timestamp: Date.now(),
        });
        scheduleCacheSave();
        
        if (includeNested && result.nested_trees_count) {
          console.log(`[@TreeCache] 💾 Cached interface ${userInterfaceId} from ${selectedServer} with ${result.nested_trees_count} trees, ${result.tree.metadata.nodes.length} total nodes (TTL: 30s)`);
        } else if (result.metrics) {
          console.log(`[@TreeCache] 💾 Cached interface ${userInterfaceId} from ${selectedServer} with metrics (nodes: ${Object.keys(result.metrics.nodes || {}).length}, edges: ${Object.keys(result.metrics.edges || {}).length}, TTL: 30s)`);
        } else {
          console.log(`[@TreeCache] 💾 Cached interface ${userInterfaceId} from ${selectedServer} (total: ${treeCache.current.size}, TTL: 30s)`);
        }
        
        return result;
      } else {
        throw new Error(result.error || 'Failed to load tree for user interface');
      }
    } catch (err: any) {
      setError(err.message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const loadTreeNodes = async (treeId: string, page = 0, limit = 100): Promise<NavigationNode[]> => {
    const response = await fetch(buildServerUrl(`/server/navigationTrees/${treeId}/nodes?page=${page}&limit=${limit}`));
    const result = await response.json();
    
    if (result.success) {
      return result.nodes;
    } else {
      throw new Error(result.error);
    }
  };

  const loadTreeEdges = async (treeId: string, nodeIds?: string[]): Promise<NavigationEdge[]> => {
    const url = new URL(buildServerUrl(`/server/navigationTrees/${treeId}/edges`), window.location.origin);
    if (nodeIds) {
      nodeIds.forEach(id => url.searchParams.append('node_ids', id));
    }
    
    const response = await fetch(url.toString());
    const result = await response.json();
    
    if (result.success) {
      return result.edges;
    } else {
      throw new Error(result.error);
    }
  };

  const saveNode = async (treeId: string, node: NavigationNode): Promise<void> => {
    const response = await fetch(buildServerUrl(`/server/navigationTrees/${treeId}/nodes`), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(node)
    });
    
    const result = await response.json();
    if (!result.success) {
      throw new Error(result.error);
    }
    
    // Update backend unified cache for live editing (memory-only, but needs updates)
    try {
      const cacheUpdateResponse = await fetch(buildServerUrl(`/server/navigation/cache/update-node`), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tree_id: treeId,
          node: result.node // Use node data from server response
        })
      });
      const cacheResult = await cacheUpdateResponse.json();
      if (cacheResult.success) {
        console.log(`[@NavigationConfigContext:saveNode] ✅ Backend cache updated for node ${node.node_id}`);
      } else {
        console.warn(`[@NavigationConfigContext:saveNode] ⚠️ Backend cache update failed: ${cacheResult.error}`);
      }
    } catch (err) {
      console.warn(`[@NavigationConfigContext:saveNode] ⚠️ Backend cache update error:`, err);
      // Don't fail the save if cache update fails
    }
  };

  const saveEdge = async (treeId: string, edge: NavigationEdge, options?: { skipCacheUpdate?: boolean }): Promise<any> => {
    const response = await fetch(buildServerUrl(`/server/navigationTrees/${treeId}/edges`), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(edge)
    });
    
    const result = await response.json();
    if (!result.success) {
      throw new Error(result.error);
    }
    
    // Update backend unified cache for live editing (memory-only, but needs updates)
    // Skip if explicitly requested (e.g., during batch unlink operations)
    if (!options?.skipCacheUpdate) {
      try {
        const cacheUpdateResponse = await fetch(buildServerUrl(`/server/navigation/cache/update-edge`), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            tree_id: treeId,
            edge: result.edge // Use edge data from server response
          })
        });
        const cacheResult = await cacheUpdateResponse.json();
        if (cacheResult.success) {
          console.log(`[@NavigationConfigContext:saveEdge] ✅ Backend cache updated for edge ${edge.id}`);
        } else {
          console.warn(`[@NavigationConfigContext:saveEdge] ⚠️ Backend cache update failed: ${cacheResult.error}`);
        }
      } catch (err) {
        console.warn(`[@NavigationConfigContext:saveEdge] ⚠️ Backend cache update error:`, err);
        // Don't fail the save if cache update fails
      }
    } else {
      console.log(`[@NavigationConfigContext:saveEdge] ⏭️ Skipping cache update for edge ${edge.id} (batch operation)`);
    }
    
    return result;
  };



  // Nested tree operations
  const loadNodeSubTrees = async (treeId: string, nodeId: string): Promise<NavigationTree[]> => {
    const response = await fetch(buildServerUrl(`/server/navigationTrees/getNodeSubTrees/${treeId}/${nodeId}`));
    const result = await response.json();
    
    if (result.success) {
      return result.sub_trees;
    } else {
      throw new Error(result.error);
    }
  };

  const createSubTree = async (parentTreeId: string, parentNodeId: string, treeData: any): Promise<NavigationTree> => {
    const response = await fetch(buildServerUrl(`/server/navigationTrees/${parentTreeId}/nodes/${parentNodeId}/subtrees`), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(treeData)
    });
    
    const result = await response.json();
    if (result.success) {
      return result.tree;
    } else {
      throw new Error(result.error);
    }
  };



  const moveSubtree = async (subtreeId: string, newParentTreeId: string, newParentNodeId: string): Promise<void> => {
    const response = await fetch(buildServerUrl(`/server/navigationTrees/${subtreeId}/move`), {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        new_parent_tree_id: newParentTreeId,
        new_parent_node_id: newParentNodeId
      })
    });
    
    const result = await response.json();
    if (!result.success) {
      throw new Error(result.error);
    }
  };

  const saveTreeData = async (treeId: string, nodes: any[], edges: any[], deletedNodeIds?: string[], deletedEdgeIds?: string[], viewport?: any): Promise<void> => {
    const payload: any = {
      nodes: nodes,
      edges: edges,
      deleted_node_ids: deletedNodeIds || [],
      deleted_edge_ids: deletedEdgeIds || []
    };
    if (viewport) payload.viewport = viewport;
    
    const response = await fetch(buildServerUrl(`/server/navigationTrees/${treeId}/batch`), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    
    const result = await response.json();
    if (!result.success) {
      throw new Error(result.error);
    }
  };

  // Cache invalidation function - invalidates cache entries across all servers for the given interface
  const invalidateTreeCache = useCallback((userInterfaceId: string) => {
    // Find all cache keys containing this userInterfaceId (across all servers)
    const keysToDelete = Array.from(treeCache.current.keys()).filter(k => k.includes(`|${userInterfaceId}|`));
    keysToDelete.forEach(k => treeCache.current.delete(k));
    scheduleCacheSave();
    console.log(`[@TreeCache] 🗑️ Invalidated ${keysToDelete.length} cache entries for interface ${userInterfaceId} (across all servers)`);
  }, [scheduleCacheSave]);

  // Cache invalidation by tree ID - clears all cache entries (used after tree save)
  const invalidateAllTreeCache = useCallback(() => {
    const cacheSize = treeCache.current.size;
    treeCache.current.clear();
    scheduleCacheSave();
    console.log(`[@TreeCache] 🗑️ CLEARED ALL: Invalidated ${cacheSize} cache entries after tree save`);
  }, [scheduleCacheSave]);

  return (
    <NavigationConfigContext.Provider value={{
      loadTreeMetadata,
      loadTreeData,
      loadTreeByUserInterface,
      loadTreeNodes,
      loadTreeEdges,
      saveNode,
      saveEdge,
      loadNodeSubTrees,
      createSubTree,
      moveSubTree: moveSubtree,
      saveTreeData,
      invalidateTreeCache,
      invalidateAllTreeCache,
      currentTree,
      isLoading,
      error,
      actualTreeId,
      setActualTreeId
    }}>
      {children}
    </NavigationConfigContext.Provider>
  );
};

export const useNavigationConfig = (): NavigationConfigContextType => {
  const context = useContext(NavigationConfigContext);
  if (!context) {
    throw new Error('useNavigationConfig must be used within a NavigationConfigProvider');
  }
  return context;
};
