import React, { createContext, useContext, useState } from 'react';

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

// Action Set interface for new edge structure
export interface ActionSet {
  id: string;
  label: string;
  actions: any[];
  retry_actions?: any[];
  priority: number;
  conditions?: any;
  timer?: number; // Timer action support
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
  edge_type: string;
  priority: string;
  threshold: number;
  metadata: any;
}

interface NavigationConfigContextType {
  // Tree metadata operations
  currentTree: NavigationTree | null;
  isLoading: boolean;
  error: string | null;
  actualTreeId: string | null;

  // Load operations
  loadTreeMetadata: (treeId: string) => Promise<NavigationTree>;
  loadTreeData: (treeId: string) => Promise<any>;
  loadTreeNodes: (treeId: string, page?: number, limit?: number) => Promise<NavigationNode[]>;
  loadTreeEdges: (treeId: string, nodeIds?: string[]) => Promise<NavigationEdge[]>;

  // Save operations
  saveNode: (treeId: string, nodeData: NavigationNode) => Promise<void>;
  saveEdge: (treeId: string, edgeData: NavigationEdge) => Promise<void>;
  
  // Batch operations
  saveTreeData: (treeId: string, nodes: any[], edges: any[], deletedNodeIds?: string[], deletedEdgeIds?: string[]) => Promise<void>;
  
  // Nested tree operations
  loadNodeSubTrees: (treeId: string, nodeId: string) => Promise<any[]>;
  createSubTree: (parentTreeId: string, parentNodeId: string, treeData: any) => Promise<any>;
  moveSubTree: (subtreeId: string, newParentTreeId: string, newParentNodeId: string) => Promise<void>;

  setActualTreeId: (treeId: string | null) => void;
}

const NavigationConfigContext = createContext<NavigationConfigContextType | null>(null);

export const NavigationConfigProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [currentTree, setCurrentTree] = useState<NavigationTree | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actualTreeId, setActualTreeId] = useState<string | null>(null);

  const loadTreeMetadata = async (treeId: string): Promise<NavigationTree> => {
    setIsLoading(true);
    try {
      const response = await fetch(`/server/navigationTrees/${treeId}`);
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
      const response = await fetch(`/server/navigationTrees/${treeId}/full`);
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

  const loadTreeNodes = async (treeId: string, page = 0, limit = 100): Promise<NavigationNode[]> => {
    const response = await fetch(`/server/navigationTrees/${treeId}/nodes?page=${page}&limit=${limit}`);
    const result = await response.json();
    
    if (result.success) {
      return result.nodes;
    } else {
      throw new Error(result.error);
    }
  };

  const loadTreeEdges = async (treeId: string, nodeIds?: string[]): Promise<NavigationEdge[]> => {
    const url = new URL(`/server/navigationTrees/${treeId}/edges`, window.location.origin);
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
    const response = await fetch(`/server/navigationTrees/${treeId}/nodes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(node)
    });
    
    const result = await response.json();
    if (!result.success) {
      throw new Error(result.error);
    }
  };

  const saveEdge = async (treeId: string, edge: NavigationEdge): Promise<void> => {
    const response = await fetch(`/server/navigationTrees/${treeId}/edges`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(edge)
    });
    
    const result = await response.json();
    if (!result.success) {
      throw new Error(result.error);
    }
  };



  // Nested tree operations
  const loadNodeSubTrees = async (treeId: string, nodeId: string): Promise<NavigationTree[]> => {
    const response = await fetch(`/server/navigationTrees/getNodeSubTrees/${treeId}/${nodeId}`);
    const result = await response.json();
    
    if (result.success) {
      return result.sub_trees;
    } else {
      throw new Error(result.error);
    }
  };

  const createSubTree = async (parentTreeId: string, parentNodeId: string, treeData: any): Promise<NavigationTree> => {
    const response = await fetch(`/server/navigationTrees/${parentTreeId}/nodes/${parentNodeId}/subtrees`, {
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
    const response = await fetch(`/server/navigationTrees/${subtreeId}/move`, {
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

  const saveTreeData = async (treeId: string, nodes: any[], edges: any[], deletedNodeIds?: string[], deletedEdgeIds?: string[]): Promise<void> => {
    const response = await fetch(`/server/navigationTrees/${treeId}/batch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        nodes: nodes,
        edges: edges,
        deleted_node_ids: deletedNodeIds || [],
        deleted_edge_ids: deletedEdgeIds || []
      })
    });
    
    const result = await response.json();
    if (!result.success) {
      throw new Error(result.error);
    }
  };

  return (
    <NavigationConfigContext.Provider value={{
      loadTreeMetadata,
      loadTreeData,
      loadTreeNodes,
      loadTreeEdges,
      saveNode,
      saveEdge,
      loadNodeSubTrees,
      createSubTree,
      moveSubTree: moveSubtree,
      saveTreeData,
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
