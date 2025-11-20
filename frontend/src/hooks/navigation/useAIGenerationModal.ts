import { useState, useEffect } from 'react';
import { useNavigation } from '../../contexts/navigation/NavigationContext';
import { buildServerUrl } from '../../utils/buildUrlUtils';
import { APP_CONFIG } from '../../config/constants';

interface UseAIGenerationModalProps {
  isOpen: boolean;
  treeId: string;
  selectedHost: any;
  selectedDeviceId: string;
  onGenerated: () => void;
  onClose: () => void;
  onCleanupTemp?: () => void;
  startExploration: () => Promise<void>;
  explorationId?: string;
}

export const useAIGenerationModal = ({
  isOpen,
  treeId,
  selectedHost,
  onGenerated,
  onClose,
  onCleanupTemp,
  startExploration
}: UseAIGenerationModalProps) => {
  const [hasTempNodes, setHasTempNodes] = useState(false);
  const [isValidating, setIsValidating] = useState(false);
  const [isAborting, setIsAborting] = useState(false);
  const [showCleanConfirm, setShowCleanConfirm] = useState(false);
  const [existingNodesCount, setExistingNodesCount] = useState(0);
  const [existingEdgesCount, setExistingEdgesCount] = useState(0);
  const [isCheckingTree, setIsCheckingTree] = useState(false);
  
  const { nodes } = useNavigation();

  // Check for _temp nodes when modal opens (check labels, not IDs)
  useEffect(() => {
    if (isOpen) {
      const tempNodesExist = nodes.some(n => n.data?.label?.endsWith('_temp'));
      setHasTempNodes(tempNodesExist);
      if (tempNodesExist) {
        const tempCount = nodes.filter(n => n.data?.label?.endsWith('_temp')).length;
        console.log(`[@useAIGenerationModal] Found ${tempCount} _temp nodes in tree`);
      }
    }
  }, [isOpen, nodes]);

  const handleValidatePrevious = async () => {
    console.log('[@useAIGenerationModal] Validating previous _temp nodes...');
    setIsValidating(true);
    
    try {
      const response = await fetch(buildServerUrl('/server/ai-generation/finalize-structure'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tree_id: treeId,
          host_name: selectedHost?.host_name
        })
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      if (data.success) {
        console.log('[@useAIGenerationModal] ✅ Validated:', data.nodes_renamed, 'nodes,', data.edges_renamed, 'edges');
2.        
        // CRITICAL: Rebuild unified cache after validation
        // This ensures navigation commands like "go to" work immediately
        await rebuildNavigationCache();
        
        // Refresh tree to show renamed nodes
        onGenerated();
        setHasTempNodes(false);
        
        // Keep modal open - user decides when to close
      } else {
        console.error('[@useAIGenerationModal] ❌ Validation failed:', data.error);
        alert(`Failed to validate: ${data.error || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('[@useAIGenerationModal] ❌ Validation error:', error);
      alert(`Error during validation: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsValidating(false);
    }
  };

  const handleAbortPrevious = async () => {
    console.log('[@useAIGenerationModal] Aborting previous _temp nodes...');
    setIsAborting(true);
    
    try {
      const response = await fetch(buildServerUrl('/server/ai-generation/cleanup-temp'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tree_id: treeId,
          host_name: selectedHost?.host_name
        })
      });
      
      const data = await response.json();
      
      if (data.success) {
        console.log('[@useAIGenerationModal] ✅ Aborted:', data.nodes_deleted, 'nodes,', data.edges_deleted, 'edges');
        
        // Wait a moment for cache to clear
        await new Promise(resolve => setTimeout(resolve, 500));
        
        // Refresh tree to remove deleted nodes
        onGenerated();
        onCleanupTemp?.();
        setHasTempNodes(false);
        
        // Keep modal open - user decides when to close
      } else {
        console.error('[@useAIGenerationModal] ❌ Abort failed:', data.error);
      }
    } catch (error) {
      console.error('[@useAIGenerationModal] ❌ Abort error:', error);
    } finally {
      setIsAborting(false);
    }
  };

  const startExplorationFlow = async () => {
    // Auto-abort any existing temp nodes before starting new exploration
    if (hasTempNodes) {
      console.log('[@useAIGenerationModal] Auto-aborting existing _temp nodes before new exploration');
      await handleAbortPrevious();
    }
    
    await startExploration();
  };

  const handleStart = async () => {
    setIsCheckingTree(true);
    
    try {
      console.log('[@useAIGenerationModal] Checking tree state...');
      
      const [nodesResponse, edgesResponse] = await Promise.all([
        fetch(buildServerUrl(`/server/navigationTrees/${treeId}/nodes?team_id=${APP_CONFIG.DEFAULT_TEAM_ID}`)),
        fetch(buildServerUrl(`/server/navigationTrees/${treeId}/edges?team_id=${APP_CONFIG.DEFAULT_TEAM_ID}`))
      ]);
      
      const nodesData = await nodesResponse.json();
      const edgesData = await edgesResponse.json();
      
      // Count non-essential nodes (exclude entry-node and home)
      const nonEssentialNodes = nodesData.success && nodesData.nodes 
        ? nodesData.nodes.filter((n: any) => 
            n.node_id !== 'entry-node' && n.node_id !== 'home'
          )
        : [];
      
      // Count deletable edges (exclude edge-entry-node-to-home)
      const allEdges = edgesData.success && edgesData.edges ? edgesData.edges : [];
      const deletableEdges = allEdges.filter((e: any) => 
        e.edge_id !== 'edge-entry-node-to-home'
      );
      
      console.log(`[@useAIGenerationModal] Found ${nonEssentialNodes.length} deletable nodes, ${deletableEdges.length} deletable edges`);
      
      // If tree has existing data, ask user to confirm deletion
      if (nonEssentialNodes.length > 0 || deletableEdges.length > 0) {
        setExistingNodesCount(nonEssentialNodes.length);
        setExistingEdgesCount(deletableEdges.length);
        setShowCleanConfirm(true);
        return;
      }
      
      // No existing data - proceed directly
      await startExplorationFlow();
      
    } catch (error) {
      console.error('[@useAIGenerationModal] Error checking tree state:', error);
      // On error, proceed anyway (fallback)
      await startExplorationFlow();
    } finally {
      setIsCheckingTree(false);
    }
  };

  const rebuildNavigationCache = async () => {
    try {
      console.log('[@useAIGenerationModal] Rebuilding unified navigation cache...');
      
      // STEP 1: Load tree hierarchy from database
      const hierarchyResponse = await fetch(
        buildServerUrl(`/server/navigationTrees/${treeId}/hierarchy?team_id=${APP_CONFIG.DEFAULT_TEAM_ID}`)
      );
      const hierarchyData = await hierarchyResponse.json();
      
      if (!hierarchyData.success) {
        console.error('[@useAIGenerationModal] Failed to load tree hierarchy:', hierarchyData.error);
        return false;
      }
      
      const all_trees_data = hierarchyData.all_trees_data || [];
      console.log(`[@useAIGenerationModal] Loaded hierarchy: ${all_trees_data.length} trees`);
      
      // STEP 2: Populate cache on HOST using same endpoint as take-control
      const populateResponse = await fetch(
        buildServerUrl(`/host/navigation/cache/populate/${treeId}?team_id=${APP_CONFIG.DEFAULT_TEAM_ID}`),
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            all_trees_data: all_trees_data,
            force_repopulate: true  // Force rebuild (same as take-control)
          })
        }
      );
      
      const populateData = await populateResponse.json();
      
      if (populateData.success) {
        console.log('[@useAIGenerationModal] ✅ Unified cache rebuilt successfully');
        return true;
      } else {
        console.error('[@useAIGenerationModal] ❌ Cache rebuild failed:', populateData.error);
        return false;
      }
    } catch (error) {
      console.error('[@useAIGenerationModal] Error rebuilding cache:', error);
      return false;
    }
  };

  const handleConfirmClean = async () => {
    setShowCleanConfirm(false);
    setIsCheckingTree(true);
    
    try {
      console.log('[@useAIGenerationModal] User confirmed - deleting all non-home nodes/edges...');
      
      // Get nodes and edges again
      const [nodesResponse, edgesResponse] = await Promise.all([
        fetch(buildServerUrl(`/server/navigationTrees/${treeId}/nodes?team_id=${APP_CONFIG.DEFAULT_TEAM_ID}`)),
        fetch(buildServerUrl(`/server/navigationTrees/${treeId}/edges?team_id=${APP_CONFIG.DEFAULT_TEAM_ID}`))
      ]);
      
      const nodesData = await nodesResponse.json();
      const edgesData = await edgesResponse.json();
      
      // Filter nodes: Keep 'entry-node' and 'home'
      const nonEssentialNodes = nodesData.success && nodesData.nodes 
        ? nodesData.nodes.filter((n: any) => 
            n.node_id !== 'entry-node' && n.node_id !== 'home'
          )
        : [];
      
      // Filter edges: Keep 'edge-entry-node-to-home'
      const allEdges = edgesData.success && edgesData.edges ? edgesData.edges : [];
      const edgesToDelete = allEdges.filter((e: any) => 
        e.edge_id !== 'edge-entry-node-to-home'
      );
      
      // Delete all edges EXCEPT 'edge-entry-node-to-home'
      console.log(`[@useAIGenerationModal] Deleting ${edgesToDelete.length} edges (keeping edge-entry-node-to-home)...`);
      for (const edge of edgesToDelete) {
        try {
          await fetch(
            buildServerUrl(`/server/navigationTrees/${treeId}/edges/${edge.edge_id}?team_id=${APP_CONFIG.DEFAULT_TEAM_ID}`),
            { method: 'DELETE' }
          );
        } catch (err) {
          console.warn(`[@useAIGenerationModal] Failed to delete edge ${edge.edge_id}:`, err);
        }
      }
      
      // Delete all non-essential nodes
      console.log(`[@useAIGenerationModal] Deleting ${nonEssentialNodes.length} nodes (keeping entry-node and home)...`);
      for (const node of nonEssentialNodes) {
        try {
          await fetch(
            buildServerUrl(`/server/navigationTrees/${treeId}/nodes/${node.node_id}?team_id=${APP_CONFIG.DEFAULT_TEAM_ID}`),
            { method: 'DELETE' }
          );
        } catch (err) {
          console.warn(`[@useAIGenerationModal] Failed to delete node ${node.node_id}:`, err);
        }
      }
      
      console.log('[@useAIGenerationModal] Tree cleaned successfully');
      
      // CRITICAL: Rebuild unified cache after deletion (same as take-control)
      // This ensures "go to home" and other navigation actions will work
      await rebuildNavigationCache();
      
      // Refresh ReactFlow to show clean tree
      onGenerated();
      
      // Wait 3s for cache to rebuild fully
      await new Promise(resolve => setTimeout(resolve, 3000));
      
      // Start AI generation
      await startExplorationFlow();
      
    } catch (error) {
      console.error('[@useAIGenerationModal] Error cleaning tree:', error);
    } finally {
      setIsCheckingTree(false);
    }
  };

  const handleCancelClean = () => {
    setShowCleanConfirm(false);
  };

  return {
    // State
    hasTempNodes,
    isValidating,
    isAborting,
    showCleanConfirm,
    existingNodesCount,
    existingEdgesCount,
    isCheckingTree,
    
    // Handlers
    handleValidatePrevious,
    handleAbortPrevious,
    handleStart,
    handleConfirmClean,
    handleCancelClean
  };
};

