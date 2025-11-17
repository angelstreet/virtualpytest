import React, { useCallback } from 'react';
import { useNavigationStack } from '../../contexts/navigation/NavigationStackContext';
import { useNavigationConfig } from '../../contexts/navigation/NavigationConfigContext';
import { useNavigation } from '../../contexts/navigation/NavigationContext';

interface NestedNavigationHookParams {
  setNodes: (nodes: any[]) => void;
  setEdges: (edges: any[]) => void;
  openNodeDialog: (node: any) => void;
}

export const useNestedNavigation = ({
  setNodes,
  setEdges,
  openNodeDialog,
}: NestedNavigationHookParams) => {
  const { pushLevel, stack, loadBreadcrumb } = useNavigationStack();
  const { actualTreeId } = useNavigationConfig();
  const navigationConfig = useNavigationConfig();
  const navigation = useNavigation();

  // Unified tree loading function  
  const loadTreeData = useCallback(async (treeId: string) => {
    const treeData = await navigationConfig.loadTreeData(treeId);
    
    if (!treeData.success) {
      throw new Error(treeData.error || 'Failed to load tree');
    }

    // Convert to frontend format (same logic as NavigationEditor)
    const frontendNodes = (treeData.nodes || []).map((dbNode: any) => ({
      id: dbNode.node_id,
      type: dbNode.node_type || 'screen', // Use top-level node_type column
      position: { x: dbNode.position_x, y: dbNode.position_y },
      data: {
        label: dbNode.label,
        description: dbNode.description,
        verifications: dbNode.verifications,
        has_subtree: dbNode.has_subtree,
        subtree_count: dbNode.subtree_count,
        ...dbNode.data, // ✅ Spread data object which contains verification_pass_condition
      }
    }));

    const frontendEdges = (treeData.edges || []).map((edge: any) => ({
      id: edge.edge_id,
      source: edge.source_node_id,
      target: edge.target_node_id,
      type: 'navigation',
      label: edge.label, // Move label to top-level (ReactFlow standard)
      sourceHandle: edge.data?.sourceHandle,
      targetHandle: edge.data?.targetHandle,
      data: {
        // Remove label from data - now in top-level field
        action_sets: edge.action_sets,
        default_action_set_id: edge.default_action_set_id,
        final_wait_time: edge.final_wait_time,
        ...edge.data
      }
    }));

    return { nodes: frontendNodes, edges: frontendEdges };
  }, [navigationConfig]);

  const handleNodeDoubleClick = useCallback(async (_event: React.MouseEvent, node: any) => {
    // 1. Skip action nodes - they don't have sub-navigation
    if (node.data?.type === 'action') {
      return;
    }

    // 2. Infinite loop protection
    const nodeId = node.id;
    const isAlreadyInThisNode = stack.some((level) => level.parentNodeId === nodeId);

    if (isAlreadyInThisNode) {
      console.warn(
        `[@useNestedNavigation] Prevented infinite loop: Already in sub-tree of node "${node.data.label}" (ID: ${nodeId})`,
      );
      openNodeDialog(node);
      return;
    }

    // 3. Check for existing sub-trees
    try {
      console.log(`[@useNestedNavigation] Checking for existing subtrees for node: ${node.id} in tree: ${actualTreeId}`);
      const subTrees = await navigationConfig.loadNodeSubTrees(actualTreeId!, node.id);
      console.log(`[@useNestedNavigation] Found ${subTrees.length} existing subtrees:`, subTrees);

      if (subTrees.length > 0) {
        // 4a. Load existing sub-tree
        const primarySubTree = subTrees[0];
        console.log(`[@useNestedNavigation] Loading existing subtree:`, primarySubTree);
        // Load nested tree data using unified approach
        const { nodes: frontendNodes, edges: frontendEdges } = await loadTreeData(primarySubTree.id);
        
        // Add parent node context to nested tree
        const parentWithContext = {
          id: node.id, // Use original parent node ID
          type: node.type || 'screen', // Use ReactFlow type field
          position: { x: 200, y: 200 },
          data: {
            label: node.data.label,
            description: node.data.description || `Navigation for ${node.data.label}`,
            verifications: node.data.verifications || [],
            // ADD NESTED TREE CONTEXT
            isParentReference: true,
            originalTreeId: actualTreeId, // Original tree where this node lives
            currentTreeId: primarySubTree.id, // Current nested tree we're viewing
            depth: primarySubTree.tree_depth, // Depth in nested structure
            parentNodeId: node.data.parent?.[node.data.parent.length - 1], // Immediate parent
            parent: node.data.parent || [], // Full parent chain from original tree
            ...node.data
          }
        };
        
        // Ensure parent node is included in nested tree
        const finalNodes = frontendNodes.some((n: any) => n.id === node.id)
          ? frontendNodes.map((n: any) => 
              n.id === node.id 
                ? { ...n, data: { ...n.data, ...parentWithContext.data } }
                : n
            )
          : [parentWithContext, ...frontendNodes];

        // Push to navigation stack with depth and parent tree tracking
        pushLevel(
          primarySubTree.id, 
          node.id, 
          primarySubTree.name, 
          node.data.label,
          primarySubTree.tree_depth,
          actualTreeId || undefined
        );

        // Update actualTreeId to the nested tree ID
        navigationConfig.setActualTreeId(primarySubTree.id);
        console.log(`[@useNestedNavigation] Updated actualTreeId to nested tree: ${primarySubTree.id}`);

        // Load breadcrumb for the new tree
        await loadBreadcrumb(primarySubTree.id);

        navigation.addToParentChain({ 
          treeId: primarySubTree.id, 
          treeName: primarySubTree.name,
          nodes: finalNodes, 
          edges: frontendEdges 
        });
        
        navigation.setInitialState({ nodes: [...finalNodes], edges: [...frontendEdges] });
        navigation.setHasUnsavedChanges(false);
        
        // Focus on the entry node (first node) and fit view
        setTimeout(() => {
          if (finalNodes.length > 0 && navigation.reactFlowInstance) {
            const entryNode = finalNodes[0]; // First node is the entry node
            navigation.reactFlowInstance.setCenter(entryNode.position.x, entryNode.position.y, { zoom: 1 });
            console.log(`[@useNestedNavigation] Focused on entry node: ${entryNode.data.label}`);
          }
        }, 10);

        console.log(`[@useNestedNavigation] Successfully loaded existing sub-tree: ${primarySubTree.name} with ${finalNodes.length} nodes and ${frontendEdges.length} edges`);
      } else {
        // 4b. Create new sub-tree
        await createNewSubTree(node);
      }
    } catch (error) {
      console.error('[@useNestedNavigation] Error handling node double-click:', error);
      // Fallback to node dialog
      openNodeDialog(node);
    }
  }, [stack, actualTreeId, navigationConfig, pushLevel, loadBreadcrumb, setNodes, setEdges, openNodeDialog]);

  const createNewSubTree = useCallback(async (parentNode: any) => {
    try {
      const newTreeData = {
        name: `${parentNode.data.label} - Subtree`,
        userinterface_id: navigationConfig.currentTree?.userinterface_id, // Use the already loaded tree's userinterface_id
        description: `Sub-navigation for ${parentNode.data.label}`,
      };

      const newTree = await navigationConfig.createSubTree(actualTreeId!, parentNode.id, newTreeData);

      // CRITICAL: Save parent node to subtree database (required for pathfinding)
      const parentNodeData = {
        node_id: parentNode.id,
        label: parentNode.data.label,
        position_x: 200, // Default position in subtree
        position_y: 200,
        node_type: parentNode.type || 'screen', // Use ReactFlow type field
        style: {},
        data: {
          description: parentNode.data.description || `Navigation for ${parentNode.data.label}`,
          screenshot: parentNode.data.screenshot,
          isParentReference: true,
          originalTreeId: actualTreeId,
          depth: newTree.tree_depth,
          parent: parentNode.data.parent || [],
          ...parentNode.data
        },
        verifications: parentNode.data.verifications || [],
        has_subtree: true,
        subtree_count: 1
      };
      
      await navigationConfig.saveNode(newTree.id, parentNodeData);
      console.log(`[@useNestedNavigation] Saved parent node to subtree database for pathfinding`);
      
      // Always start new subtree with parent node displayed graphically with context
      const frontendNodes = [{
        id: parentNode.id, // Use original parent node ID
        type: parentNode.type || 'screen', // Use ReactFlow type field
        position: { x: 200, y: 200 },
        data: {
          label: parentNode.data.label,
          description: parentNode.data.description || `Navigation for ${parentNode.data.label}`,
          verifications: parentNode.data.verifications || [],
          // ADD NESTED TREE CONTEXT
          isParentReference: true,
          originalTreeId: actualTreeId, // Original tree where this node lives
          currentTreeId: newTree.id, // Current nested tree we're viewing
          depth: newTree.tree_depth, // Depth in nested structure
          parentNodeId: parentNode.data.parent?.[parentNode.data.parent.length - 1], // Immediate parent
          parent: parentNode.data.parent || [], // Full parent chain from original tree
          ...parentNode.data
        }
      }];

      // Push to navigation stack with parent tree tracking
      pushLevel(newTree.id, parentNode.id, newTree.name, parentNode.data.label, newTree.tree_depth, actualTreeId || undefined);

      // CRITICAL: Update actualTreeId to the new nested tree ID
      navigationConfig.setActualTreeId(newTree.id);
      console.log(`[@useNestedNavigation] Updated actualTreeId to new nested tree: ${newTree.id}`);

      // Load breadcrumb
      await loadBreadcrumb(newTree.id);

      navigation.addToParentChain({ 
        treeId: newTree.id, 
        treeName: newTree.name,
        nodes: frontendNodes, 
        edges: [] 
      });
      
      setTimeout(() => {
        if (navigation.reactFlowInstance) {
          navigation.reactFlowInstance.setCenter(frontendNodes[0].position.x, frontendNodes[0].position.y, { zoom: 1 });
          console.log(`[@useNestedNavigation] Focused on parent node: ${frontendNodes[0].data.label}`);
        }
      }, 10);

      console.log(`[@useNestedNavigation] Created new sub-tree: ${newTree.name} starting with parent node`);
    } catch (error) {
      console.error('[@useNestedNavigation] Error creating sub-tree:', error);
      throw error;
    }
  }, [actualTreeId, navigationConfig, pushLevel, loadBreadcrumb, setNodes, setEdges]);

  // No helper function needed - we just display the parent node graphically

  return {
    handleNodeDoubleClick,
    createNewSubTree
  };
};
