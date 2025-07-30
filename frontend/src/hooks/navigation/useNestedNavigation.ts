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
      const subTrees = await navigationConfig.loadNodeSubTrees(actualTreeId!, node.id);

      if (subTrees.length > 0) {
        // 4a. Load existing sub-tree
        const primarySubTree = subTrees[0];
        const treeData = await navigationConfig.loadTreeData(primarySubTree.id);

        if (treeData.success) {
          // Convert to frontend format
          const frontendNodes = (treeData.nodes || []).map((node: any) => ({
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

          const frontendEdges = (treeData.edges || []).map((edge: any) => ({
            id: edge.edge_id,
            source: edge.source_node_id,
            target: edge.target_node_id,
            type: 'uiNavigation',
            data: {
              label: edge.label, // Include the auto-generated label from database
              description: edge.description,
              actions: edge.actions,
              retryActions: edge.retry_actions,
              final_wait_time: edge.final_wait_time,
              ...edge.data
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
          }, 10);

          console.log(`[@useNestedNavigation] Loaded existing sub-tree: ${primarySubTree.name}`);
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
        userinterface_id: actualTreeId, // Use same interface
        description: `Sub-navigation for ${parentNode.data.label}`,
      };

      const newTree = await navigationConfig.createSubTree(actualTreeId!, parentNode.id, newTreeData);

      // Create initial entry node for the new subtree
      const entryNodeData = {
        id: 'entry-node',
        node_id: 'entry-node',
        label: 'Entry Point',
        node_type: 'entry',
        position_x: 100,
        position_y: 100,
        parent_node_ids: [],
        is_root: true,
        verifications: [],
        depth: 0,
        priority: 'p3',
        data: {
          description: 'Entry point for nested navigation'
        },
        metadata: {}
      };

      await navigationConfig.saveNode(newTree.id, entryNodeData);

      // Load the new subtree
      const treeData = await navigationConfig.loadTreeData(newTree.id);
      
      if (treeData.success) {
        const frontendNodes = (treeData.nodes || []).map((node: any) => ({
          id: node.node_id,
          type: 'uiScreen',
          position: { x: node.position_x, y: node.position_y },
          data: {
            label: node.label,
            type: node.node_type,
            description: node.data?.description, // Read description from data field
            verifications: node.verifications,
            ...node.data
          }
        }));

        // Push to navigation stack
        pushLevel(newTree.id, parentNode.id, newTree.name, parentNode.data.label, newTree.tree_depth);

        // Load breadcrumb
        await loadBreadcrumb(newTree.id);

        // Set nodes
        setTimeout(() => {
          setNodes(frontendNodes);
          setEdges([]);
        }, 10);

        console.log(`[@useNestedNavigation] Created new sub-tree: ${newTree.name}`);
      }
    } catch (error) {
      console.error('[@useNestedNavigation] Error creating sub-tree:', error);
      throw error;
    }
  }, [actualTreeId, navigationConfig, pushLevel, loadBreadcrumb, setNodes, setEdges]);

  return {
    handleNodeDoubleClick,
    createNewSubTree
  };
};
