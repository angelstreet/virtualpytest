import { useState, useEffect } from 'react';
import { useNavigation } from '../../contexts/navigation/NavigationContext';
import { buildServerUrl } from '../../utils/buildUrlUtils';
import { APP_CONFIG } from '../../config/constants';

interface UseAIGenerationModalProps {
  isOpen: boolean;
  treeId: string;
  selectedHost: any;
  selectedDeviceId: string;
  onClose: () => void;
  onCleanupTemp?: () => void;
  startExploration: () => Promise<void>;
  explorationId?: string;
}

export const useAIGenerationModal = ({
  isOpen,
  treeId,
  selectedHost,
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
        
        setHasTempNodes(false);
        
        // Keep modal open - user decides when to close (tree will refresh naturally)
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
        
        onCleanupTemp?.();
        setHasTempNodes(false);
        
        // Keep modal open - user decides when to close (tree will refresh naturally)
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
      
      // Count non-essential nodes (exclude entry-node, home, and subtree root)
      const nonEssentialNodes = nodesData.success && nodesData.nodes 
        ? nodesData.nodes.filter((n: any) => 
            n.node_id !== 'entry-node' && 
            n.node_id !== 'home' &&
            n.data?.isParentReference !== true  // ✅ PROTECT: Subtree root node
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

  const handleConfirmClean = async () => {
    setShowCleanConfirm(false);
    setIsCheckingTree(true);
    
    try {
      console.log('[@useAIGenerationModal] User confirmed - batch deleting all non-home nodes/edges...');
      
      // Get nodes and edges again
      const [nodesResponse, edgesResponse] = await Promise.all([
        fetch(buildServerUrl(`/server/navigationTrees/${treeId}/nodes?team_id=${APP_CONFIG.DEFAULT_TEAM_ID}`)),
        fetch(buildServerUrl(`/server/navigationTrees/${treeId}/edges?team_id=${APP_CONFIG.DEFAULT_TEAM_ID}`))
      ]);
      
      const nodesData = await nodesResponse.json();
      const edgesData = await edgesResponse.json();
      
      // Filter nodes: Keep 'entry-node', 'home', and subtree root
      const nodeIdsToDelete = nodesData.success && nodesData.nodes 
        ? nodesData.nodes
            .filter((n: any) => 
              n.node_id !== 'entry-node' && 
              n.node_id !== 'home' &&
              n.data?.isParentReference !== true  // ✅ PROTECT: Subtree root node
            )
            .map((n: any) => n.node_id)
        : [];
      
      // Filter edges: Keep 'edge-entry-node-to-home'
      const edgeIdsToDelete = edgesData.success && edgesData.edges
        ? edgesData.edges
            .filter((e: any) => e.edge_id !== 'edge-entry-node-to-home')
            .map((e: any) => e.edge_id)
        : [];
      
      console.log(`[@useAIGenerationModal] Batch deleting ${edgeIdsToDelete.length} edges and ${nodeIdsToDelete.length} nodes...`);
      
      // ✅ Use batch endpoint - ONE API call instead of N calls
      const batchResponse = await fetch(
        buildServerUrl(`/server/navigationTrees/${treeId}/batch?team_id=${APP_CONFIG.DEFAULT_TEAM_ID}`),
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            nodes: [], // Not updating any nodes
            edges: [], // Not updating any edges
            deleted_node_ids: nodeIdsToDelete,
            deleted_edge_ids: edgeIdsToDelete
          })
        }
      );
      
      if (!batchResponse.ok) {
        throw new Error(`Batch delete failed: ${batchResponse.status}`);
      }
      
      const batchResult = await batchResponse.json();
      if (!batchResult.success) {
        throw new Error(batchResult.error || 'Batch delete failed');
      }
      
      console.log('[@useAIGenerationModal] ✅ Tree cleaned successfully via batch delete');
      
      // Wait 1s for database updates to complete
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // Start AI generation (tree will refresh naturally)
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

