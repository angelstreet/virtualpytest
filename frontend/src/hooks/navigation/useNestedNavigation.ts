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

  const handleNodeDoubleClick = useCallback(async (_event: React.MouseEvent, node: any) => {
    // 1. Skip entry type nodes
    if (node.data?.type === 'entry') {
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
        const treeData = await navigationConfig.loadTreeData(primarySubTree.id);
        console.log(`[@useNestedNavigation] Loaded tree data for existing subtree:`, treeData);

        if (treeData.success) {
          console.log(`[@useNestedNavigation] Converting ${treeData.nodes?.length || 0} nodes and ${treeData.edges?.length || 0} edges to frontend format`);
          
          // No need to create database entries - just ensure we show the parent node graphically
          
          // Convert to frontend format
          let frontendNodes = (treeData.nodes || []).map((node: any) => ({
            id: node.node_id,
            type: 'uiScreen',
            position: { x: node.position_x, y: node.position_y },
            data: {
              label: node.label,
              type: node.node_type,
              description: node.description,
              verifications: node.verifications,
              has_subtree: node.has_subtree,
              subtree_count: node.subtree_count,
              ...node.data
            }
          }));
          
          // Always ensure we show at least the parent node graphically
          if (frontendNodes.length === 0) {
            console.log(`[@useNestedNavigation] Empty subtree, showing parent node graphically`);
            frontendNodes = [{
              id: node.id, // Use original parent node ID
              type: 'uiScreen',
              position: { x: 200, y: 200 },
              data: {
                label: node.data.label,
                type: node.data.type || 'screen',
                description: node.data.description || `Navigation for ${node.data.label}`,
                verifications: node.data.verifications || [],
                ...node.data
              }
            }];
          }

          const frontendEdges = (treeData.edges || []).map((edge: any) => ({
            id: edge.edge_id,
            source: edge.source_node_id,
            target: edge.target_node_id,
            type: 'uiNavigation',
            data: {
              label: edge.label, // Include the auto-generated label from database
              description: edge.description,
              action_sets: edge.action_sets, // NEW: action sets structure - REQUIRED
              default_action_set_id: edge.default_action_set_id, // NEW: default action set ID - REQUIRED
              final_wait_time: edge.final_wait_time,
              ...edge.data
              // NO LEGACY FIELDS: actions, retryActions removed
            }
          }));

          // 5. Push to navigation stack with depth
          pushLevel(
            primarySubTree.id, 
            node.id, 
            primarySubTree.name, 
            node.data.label,
            primarySubTree.tree_depth
          );

          // Load breadcrumb for the new tree
          await loadBreadcrumb(primarySubTree.id);

          // Set nodes and edges
          setTimeout(() => {
            setNodes(frontendNodes);
            setEdges(frontendEdges);
            // Set initial state for deletion detection
            navigation.setInitialState({ nodes: [...frontendNodes], edges: [...frontendEdges] });
            navigation.setHasUnsavedChanges(false);
            
            // Focus on the entry node (first node) and fit view
            if (frontendNodes.length > 0 && navigation.reactFlowInstance) {
              const entryNode = frontendNodes[0]; // First node is the entry node
              navigation.reactFlowInstance.setCenter(entryNode.position.x, entryNode.position.y, { zoom: 1 });
              console.log(`[@useNestedNavigation] Focused on entry node: ${entryNode.data.label}`);
            }
          }, 10);

          console.log(`[@useNestedNavigation] Successfully loaded existing sub-tree: ${primarySubTree.name} with ${frontendNodes.length} nodes and ${frontendEdges.length} edges`);
        } else {
          console.error(`[@useNestedNavigation] Failed to load tree data for existing subtree:`, treeData.error);
        }
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

      // No need to create database entry - just show parent node graphically
      console.log(`[@useNestedNavigation] New subtree created, will show parent node graphically`);
      
      // Always start new subtree with parent node displayed graphically
      const frontendNodes = [{
        id: parentNode.id, // Use original parent node ID
        type: 'uiScreen',
        position: { x: 200, y: 200 },
        data: {
          label: parentNode.data.label,
          type: parentNode.data.type || 'screen',
          description: parentNode.data.description || `Navigation for ${parentNode.data.label}`,
          verifications: parentNode.data.verifications || [],
          ...parentNode.data
        }
      }];

      // Push to navigation stack
      pushLevel(newTree.id, parentNode.id, newTree.name, parentNode.data.label, newTree.tree_depth);

      // Load breadcrumb
      await loadBreadcrumb(newTree.id);

      // Set nodes with parent node displayed
      setTimeout(() => {
        setNodes(frontendNodes);
        setEdges([]);
        
        // Focus on the parent node and fit view
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
