import { useMemo, useCallback, useContext } from 'react';
import { MarkerType, addEdge, Connection } from 'reactflow';

import { useNavigationConfig } from '../../contexts/navigation/NavigationConfigContext';
import NavigationContext from '../../contexts/navigation/NavigationContext';
import { useHostManager } from '../useHostManager';
import { UINavigationEdge } from '../../types/pages/Navigation_Types';

export const useNavigationEditor = () => {
  // Get the navigation config context (save/load functionality)
  const navigationConfig = useNavigationConfig();

  // Get the unified navigation context (state management)
  const navigation = useContext(NavigationContext);
  if (!navigation) {
    throw new Error('useNavigationEditor must be used within a NavigationProvider');
  }

  // Get host manager
  const hostManager = useHostManager();

  // New normalized API functions
  const loadTreeData = useCallback(
    async (treeId: string) => {
      try {
        navigation.setIsLoading(true);
        navigation.setError(null);

        // Load complete tree data using new API
        const treeData = await navigationConfig.loadFullTree(treeId);
        
        // Convert normalized data to frontend format
        const frontendNodes = treeData.nodes.map((node: any) => ({
          id: node.node_id,
          type: 'uiScreen',
          position: { x: node.position_x, y: node.position_y },
          data: {
            label: node.label,
            type: node.node_type,
            description: node.description,
            verifications: node.verifications, // Directly embedded
            ...node.data // Additional data
          }
        }));

        const frontendEdges = treeData.edges.map((edge: any) => ({
          id: edge.edge_id,
          source: edge.source_node_id,
          target: edge.target_node_id,
          type: 'uiNavigation',
          sourceHandle: edge.data?.sourceHandle, // Extract handle info to root level
          targetHandle: edge.data?.targetHandle, // Extract handle info to root level
          data: {
            description: edge.description,
            actions: edge.actions || [], // Use backend structure exactly
            retryActions: edge.retry_actions || [],
            final_wait_time: edge.final_wait_time,
            ...edge.data // Additional data
          }
        }));

        navigation.setNodes(frontendNodes);
        navigation.setEdges(frontendEdges);
        navigation.setInitialState({ nodes: [...frontendNodes], edges: [...frontendEdges] });
        navigation.setHasUnsavedChanges(false);

        console.log(`[@useNavigationEditor:loadTreeData] Loaded ${frontendNodes.length} nodes and ${frontendEdges.length} edges`);
      } catch (error) {
        navigation.setError(`Failed to load tree: ${error instanceof Error ? error.message : 'Unknown error'}`);
      } finally {
        navigation.setIsLoading(false);
      }
    },
    [navigationConfig, navigation],
  );

  const saveTreeData = useCallback(
    async (treeId: string) => {
      try {
        navigation.setIsLoading(true);

        // Convert frontend format to normalized format
        const normalizedNodes = navigation.nodes.map(node => ({
          node_id: node.id,
          label: node.data.label,
          position_x: node.position?.x || 0,
          position_y: node.position?.y || 0,
          node_type: node.data.type || 'default',
          description: node.data.description,
          verifications: node.data.verifications || [],
          data: {
            // Store any additional data
            ...node.data,
            verifications: undefined // Remove from data since it's stored separately
          }
        }));

        const normalizedEdges = navigation.edges.map(edge => ({
          edge_id: edge.id,
          source_node_id: edge.source,
          target_node_id: edge.target,
          description: edge.data?.description,
          actions: edge.data?.actions || [],
          retry_actions: edge.data?.retryActions || [],
          final_wait_time: edge.data?.final_wait_time || 0,
          edge_type: edge.data?.edgeType || 'default',
          data: {
            // Store any additional data
            ...edge.data,
            actions: undefined, // Remove from data since it's stored separately
            retryActions: undefined,
            final_wait_time: undefined
          }
        }));

        await navigationConfig.saveTreeData(treeId, normalizedNodes, normalizedEdges);
        
        navigation.setInitialState({ nodes: [...navigation.nodes], edges: [...navigation.edges] });
        navigation.setHasUnsavedChanges(false);

        console.log(`[@useNavigationEditor:saveTreeData] Saved ${normalizedNodes.length} nodes and ${normalizedEdges.length} edges`);
      } catch (error) {
        navigation.setError(`Failed to save tree: ${error instanceof Error ? error.message : 'Unknown error'}`);
        throw error;
      } finally {
        navigation.setIsLoading(false);
      }
    },
    [navigationConfig, navigation],
  );

  const saveNode = useCallback(
    async (treeId: string, nodeData: any) => {
      try {
        const normalizedNode = {
          node_id: nodeData.id,
          label: nodeData.label,
          position_x: nodeData.position?.x || 0,
          position_y: nodeData.position?.y || 0,
          node_type: nodeData.type || 'default',
          verifications: nodeData.verifications || [],
          data: {
            ...(nodeData.data || {}),
            description: nodeData.description
          }
        };

        await navigationConfig.saveNode(treeId, normalizedNode);
        console.log(`[@useNavigationEditor:saveNode] Saved node: ${nodeData.id}`);
      } catch (error) {
        navigation.setError(`Failed to save node: ${error instanceof Error ? error.message : 'Unknown error'}`);
        throw error;
      }
    },
    [navigationConfig, navigation],
  );

  const saveEdge = useCallback(
    async (treeId: string, edgeData: any) => {
      try {
        const normalizedEdge = {
          edge_id: edgeData.id,
          source_node_id: edgeData.source,
          target_node_id: edgeData.target,
          actions: edgeData.actions || [],
          retry_actions: edgeData.retryActions || [],
          final_wait_time: edgeData.final_wait_time || 0,
          edge_type: edgeData.edgeType || 'default',
          data: {
            ...(edgeData.data || {}),
            description: edgeData.description
          }
        };

        await navigationConfig.saveEdge(treeId, normalizedEdge);
        console.log(`[@useNavigationEditor:saveEdge] Saved edge: ${edgeData.id}`);
      } catch (error) {
        navigation.setError(`Failed to save edge: ${error instanceof Error ? error.message : 'Unknown error'}`);
        throw error;
      }
    },
    [navigationConfig, navigation],
  );



  // Simple event handlers
  const onConnect = useCallback(
    async (connection: Connection) => {
      console.log('Connection attempt:', connection);

      // Validate connection parameters
      if (!connection.source || !connection.target) {
        console.error(
          '[@useNavigationEditor:onConnect] Invalid connection: missing source or target',
        );
        return;
      }

      // Find source and target nodes
      const sourceNode = navigation.nodes.find((n) => n.id === connection.source);
      const targetNode = navigation.nodes.find((n) => n.id === connection.target);

      if (!sourceNode || !targetNode) {
        console.error('[@useNavigationEditor:onConnect] Source or target node not found');
        return;
      }

      // Prevent self-connections
      if (connection.source === connection.target) {
        console.warn('[@useNavigationEditor:onConnect] Cannot connect node to itself');
        return;
      }

      // Create new edge with proper UINavigationEdge structure
      const newEdge: UINavigationEdge = {
        id: `edge-${connection.source}-${connection.target}-${Date.now()}`,
        source: connection.source,
        target: connection.target,
        sourceHandle: connection.sourceHandle || undefined,
        targetHandle: connection.targetHandle || undefined,
        type: 'uiNavigation',
        animated: false,
        style: {
          stroke: '#555',
          strokeWidth: 2,
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: '#555',
        },
        data: {
          edgeType: 'horizontal',
          description: `${sourceNode.data.label} → ${targetNode.data.label}`,
          from: sourceNode.data.label,
          to: targetNode.data.label,
        },
      };

      console.log('[@useNavigationEditor:onConnect] Creating edge:', newEdge);

      // Add edge to current edges using ReactFlow's addEdge utility
      const updatedEdges = addEdge(newEdge, navigation.edges);

      // Update edges in navigation context
      navigation.setEdges(updatedEdges);

      // Mark as having unsaved changes
      navigation.setHasUnsavedChanges(true);

      console.log(
        '[@useNavigationEditor:onConnect] Edge created successfully - manual save required',
      );
    },
    [navigation],
  );

  const onNodeClick = useCallback(
    (_event: React.MouseEvent, node: any) => {
      navigation.setSelectedNode(node);
      navigation.setSelectedEdge(null); // Clear edge selection when node is selected
    },
    [navigation],
  );

  const onEdgeClick = useCallback(
    (_event: React.MouseEvent, edge: any) => {
      // Find bidirectional edge (opposite direction)
      const oppositeEdge = navigation.edges.find(
        (e) => e.source === edge.target && e.target === edge.source && e.id !== edge.id,
      );

      if (oppositeEdge) {
        // If bidirectional edges exist, set both edges for the panel to handle
        navigation.setSelectedEdge({
          ...edge,
          bidirectionalEdge: oppositeEdge,
        });
      } else {
        navigation.setSelectedEdge(edge);
      }

      navigation.setSelectedNode(null); // Clear node selection when edge is selected
    },
    [navigation],
  );

  const onNodeDoubleClick = useCallback(
    (_event: React.MouseEvent, node: any) => {
      // Simple double-click opens edit dialog (nested navigation handled separately)
      navigation.openNodeDialog(node);
    },
    [navigation],
  );

  const onPaneClick = useCallback(() => {
    navigation.resetSelection();
  }, [navigation]);

  // Node and edge action handlers
  const handleNodeFormSubmit = useCallback(
    async (nodeForm: any) => {
      try {
        // Verifications are now embedded directly - no need to save separately
        console.log(
          '[@useNavigationEditor:handleNodeFormSubmit] Using embedded verifications:',
          nodeForm.verifications?.length || 0,
        );

        // Update the node
        let updatedNodeData: any;

        if (navigation.isNewNode) {
          // Create new node
          updatedNodeData = {
            id: nodeForm.id || `node-${Date.now()}`,
            position: { x: 100, y: 100 },
            type: 'uiScreen',
            data: {
              label: nodeForm.label,
              type: nodeForm.type,
              description: nodeForm.description,
              verifications: nodeForm.verifications || [],
            },
          };
          navigation.setNodes([...navigation.nodes, updatedNodeData]);
        } else if (navigation.selectedNode) {
          // Update existing node
          updatedNodeData = {
            ...navigation.selectedNode,
            data: {
              ...navigation.selectedNode.data,
              label: nodeForm.label,
              type: nodeForm.type,
              description: nodeForm.description,
              verifications: nodeForm.verifications || [],
            },
          };
          const updatedNodes = navigation.nodes.map((node) =>
            node.id === navigation.selectedNode?.id ? updatedNodeData : node,
          );
          navigation.setNodes(updatedNodes);
          navigation.setSelectedNode(updatedNodeData);
        }

        // Auto-save to database
        if (updatedNodeData && navigationConfig.actualTreeId) {
          console.log('[@useNavigationEditor:handleNodeFormSubmit] Auto-saving node to database...');
          
          // Use the existing saveNode wrapper function
          await saveNode(navigationConfig.actualTreeId, {
            id: updatedNodeData.id,
            label: updatedNodeData.data.label,
            type: updatedNodeData.type || 'uiScreen',
            position: updatedNodeData.position,
            description: updatedNodeData.data.description,
            verifications: updatedNodeData.data.verifications || [],
            data: updatedNodeData.data,
          });
          console.log('[@useNavigationEditor:handleNodeFormSubmit] Node auto-saved successfully');
        }

        // Close dialog - no need to mark unsaved changes since we auto-saved
        navigation.setIsNodeDialogOpen(false);

        console.log('[@useNavigationEditor:handleNodeFormSubmit] Node saved successfully to database');
      } catch (error) {
        console.error('Error during node save:', error);
        navigation.setError('Failed to save node changes');
      }
    },
    [navigation, navigationConfig.actualTreeId, saveNode],
  );

  const handleEdgeFormSubmit = useCallback(
    async (edgeForm: any) => {
      console.log('[@useNavigationEditor:handleEdgeFormSubmit] Received edge form data:', {
        description: edgeForm?.description,
        actions: edgeForm?.actions?.length || 0,
        retryActions: edgeForm?.retryActions?.length || 0,
        final_wait_time: edgeForm?.final_wait_time,
      });

      try {
        // Get edge ID from form - this is the single source of truth
        if (!edgeForm.edgeId) {
          console.error('[@useNavigationEditor:handleEdgeFormSubmit] No edge ID in form');
          navigation.setError('Edge ID missing from form data');
          return;
        }

        console.log('[@useNavigationEditor:handleEdgeFormSubmit] Processing edge save:', {
          edgeId: edgeForm.edgeId,
          actions: edgeForm.actions?.length || 0,
          retryActions: edgeForm.retryActions?.length || 0,
        });

        // Find the edge to update using the ID from form
        const currentSelectedEdge = navigation.edges.find((edge) => edge.id === edgeForm.edgeId);

        if (!currentSelectedEdge) {
          console.error(
            '[@useNavigationEditor:handleEdgeFormSubmit] Edge not found:',
            edgeForm.edgeId,
          );
          console.error(
            '[@useNavigationEditor:handleEdgeFormSubmit] Available edges:',
            navigation.edges.map((e) => ({ id: e.id, source: e.source, target: e.target })),
          );
          navigation.setError(`Edge ${edgeForm.edgeId} not found in current tree`);
          return;
        }

        console.log(
          '[@useNavigationEditor:handleEdgeFormSubmit] Starting edge save process for edge:',
          currentSelectedEdge.id,
        );

        // Actions are now embedded directly - no need to save separately
        console.log(
          `[@useNavigationEditor:handleEdgeFormSubmit] Using embedded actions: ${edgeForm.actions?.length || 0} actions and ${edgeForm.retryActions?.length || 0} retry actions`,
        );

        // Update edge with embedded actions and retry actions (no more IDs)
        const updatedEdge = {
          ...currentSelectedEdge,
          data: {
            ...(currentSelectedEdge.data || {}),
            description: edgeForm.description || currentSelectedEdge.data?.description || '',
            actions: edgeForm.actions || [],
            retryActions: edgeForm.retryActions || [],
            final_wait_time: edgeForm.final_wait_time || 0,
            priority: edgeForm.priority || 'p3',
            threshold: edgeForm.threshold || 0,
          },
        };

        console.log('[@useNavigationEditor:handleEdgeFormSubmit] Updating edge with new data:', {
          id: updatedEdge.id,
          final_wait_time: updatedEdge.data.final_wait_time,
          actions: updatedEdge.data.actions.length,
          retryActions: updatedEdge.data.retryActions.length,
          description: updatedEdge.data.description,
        });

        const updatedEdges = navigation.edges.map((edge) =>
          edge.id === currentSelectedEdge.id ? updatedEdge : edge,
        );

        navigation.setEdges(updatedEdges);
        navigation.setSelectedEdge(updatedEdge);

        // Auto-save to database
        if (navigationConfig.actualTreeId) {
          console.log('[@useNavigationEditor:handleEdgeFormSubmit] Auto-saving edge to database...');
          
          // Use the existing saveEdge wrapper function
          await saveEdge(navigationConfig.actualTreeId, {
            id: updatedEdge.id,
            source: updatedEdge.source,
            target: updatedEdge.target,
            description: updatedEdge.data.description,
            actions: updatedEdge.data.actions || [],
            retryActions: updatedEdge.data.retryActions || [],
            final_wait_time: updatedEdge.data.final_wait_time || 0,
            edgeType: updatedEdge.type || 'default',
            data: updatedEdge.data,
          });
          console.log('[@useNavigationEditor:handleEdgeFormSubmit] Edge auto-saved successfully');
        }

        navigation.setIsEdgeDialogOpen(false);
        // No need to mark unsaved changes since we auto-saved

        console.log('[@useNavigationEditor:handleEdgeFormSubmit] Edge saved successfully to database');
      } catch (error) {
        console.error('[@useNavigationEditor:handleEdgeFormSubmit] Error during edge save:', error);
        navigation.setError('Failed to save edge actions');
      }
    },
    [navigation, navigationConfig.actualTreeId, saveEdge],
  );

  const addNewNode = useCallback(
    (type: string = 'screen', position: { x: number; y: number } = { x: 250, y: 250 }) => {
      const validType = type as 'screen' | 'dialog' | 'popup' | 'overlay' | 'menu' | 'entry';
      const newNode = {
        id: `node-${Date.now()}`,
        type: 'uiScreen',
        position,
        data: {
          type: validType,
          label: `new_${type}`,
          description: '',
          verifications: [],
        },
      };
      navigation.setNodes([...navigation.nodes, newNode as any]);
      navigation.markUnsavedChanges();
    },
    [navigation],
  );

  const cancelNodeChanges = useCallback(() => {
    navigation.setIsNodeDialogOpen(false);
    navigation.setNodeForm({
      label: '',
      type: 'screen',
      description: '',
      verifications: [],
    });
  }, [navigation]);

  const closeSelectionPanel = useCallback(() => {
    navigation.resetSelection();
  }, [navigation]);

  const deleteSelected = useCallback(() => {
    if (navigation.selectedNode) {
      const filteredNodes = navigation.nodes.filter((n) => n.id !== navigation.selectedNode?.id);
      navigation.setNodes(filteredNodes);
      navigation.setSelectedNode(null);
      navigation.markUnsavedChanges();
    }
    if (navigation.selectedEdge) {
      const filteredEdges = navigation.edges.filter((e) => e.id !== navigation.selectedEdge?.id);
      navigation.setEdges(filteredEdges);
      navigation.setSelectedEdge(null);
      navigation.markUnsavedChanges();
    }
  }, [navigation]);

  const resetNode = useCallback(
    (nodeId: string) => {
      console.log('Reset node:', nodeId);
      navigation.setIsNodeDialogOpen(false);
    },
    [navigation],
  );

  const discardChanges = useCallback(() => {
    navigation.setIsDiscardDialogOpen(true);
  }, [navigation]);

  const performDiscardChanges = useCallback(() => {
    navigation.resetToInitialState();
    navigation.setIsDiscardDialogOpen(false);
  }, [navigation]);

  const fitView = useCallback(() => {
    navigation.fitViewToNodes();
  }, [navigation]);

  const navigateToParent = useCallback(() => {
    // Simple fallback
    console.log('Navigate to parent');
  }, []);

  const setUserInterfaceFromProps = useCallback(
    (userInterface: any) => {
      navigation.setUserInterface(userInterface);
    },
    [navigation],
  );

  // Combine all functionality into the same interface as the original useNavigationEditor
  return useMemo(
    () => ({
      // State (filtered views for ReactFlow display)
      nodes: navigation.nodes,
      edges: navigation.edges,

      // Raw data (single source of truth)
      allNodes: navigation.nodes, // In unified context, nodes are already the source of truth
      allEdges: navigation.edges,

      // Tree and interface state
      treeName: navigation.currentTreeName,
      treeId: navigation.currentTreeId,
      interfaceId: navigation.interfaceId,
      currentTreeId: navigation.currentTreeId,
      currentTreeName: navigation.currentTreeName,
      navigationPath: navigation.navigationPath,
      navigationNamePath: navigation.navigationNamePath,
      userInterface: navigation.userInterface,
      rootTree: navigation.rootTree,
      viewPath: navigation.viewPath,

      // Loading states
      isLoadingInterface: navigation.isLoadingInterface,
      isLoading: navigation.isLoading,

      // Selection state
      selectedNode: navigation.selectedNode,
      selectedEdge: navigation.selectedEdge,

      // Dialog states
      isNodeDialogOpen: navigation.isNodeDialogOpen,
      isEdgeDialogOpen: navigation.isEdgeDialogOpen,
      isDiscardDialogOpen: navigation.isDiscardDialogOpen,

      // Form states
      isNewNode: navigation.isNewNode,
      nodeForm: navigation.nodeForm,
      edgeForm: navigation.edgeForm,

      // Error and success states
      error: navigation.error,
      success: navigation.success,
      hasUnsavedChanges: navigation.hasUnsavedChanges,

      // Focus and filtering
      focusNodeId: navigation.focusNodeId,
      maxDisplayDepth: navigation.maxDisplayDepth,
      availableFocusNodes: navigation.availableFocusNodes,

      // React Flow refs and state
      reactFlowWrapper: navigation.reactFlowWrapper,
      reactFlowInstance: navigation.reactFlowInstance,
      pendingConnection: null, // Not used in unified context

      // Setters (maintain compatibility)
      setNodes: navigation.setNodes,
      setEdges: navigation.setEdges,
      setHasUnsavedChanges: navigation.setHasUnsavedChanges,
      setTreeName: navigation.setCurrentTreeName,
      setIsLoadingInterface: navigation.setIsLoadingInterface,
      setSelectedNode: navigation.setSelectedNode,
      setSelectedEdge: navigation.setSelectedEdge,
      setIsNodeDialogOpen: navigation.setIsNodeDialogOpen,
      setIsEdgeDialogOpen: navigation.setIsEdgeDialogOpen,
      setIsNewNode: navigation.setIsNewNode,
      setNodeForm: navigation.setNodeForm,
      setEdgeForm: navigation.setEdgeForm,
      setIsLoading: navigation.setIsLoading,
      setError: navigation.setError,
      setSuccess: navigation.setSuccess,
      setPendingConnection: () => {}, // Not used
      setReactFlowInstance: navigation.setReactFlowInstance,
      setIsDiscardDialogOpen: navigation.setIsDiscardDialogOpen,

      // Event handlers
      onNodesChange: navigation.onNodesChange,
      onEdgesChange: navigation.onEdgesChange,
      onConnect,
      onNodeClick,
      onEdgeClick,
      onNodeDoubleClick,
      onPaneClick,

      // Focus management
      setFocusNode: navigation.setFocusNodeId,
      setDisplayDepth: navigation.setMaxDisplayDepth,
      resetFocus: () => {
        navigation.setFocusNodeId(null);
        navigation.setMaxDisplayDepth(5);
      },
      isNodeDescendantOf: () => false, // Not implemented in unified context

      // New normalized API operations
      loadTreeData,
      saveTreeData,
      saveNode,
      saveEdge,



      // Interface operations
      listAvailableTrees: navigationConfig.listAvailableUserInterfaces,

      // Lock management - from NavigationConfigContext
      isLocked: navigationConfig.isLocked,
      lockInfo: navigationConfig.lockInfo,
      showReadOnlyOverlay: navigationConfig.showReadOnlyOverlay,
      setCheckingLockState: navigationConfig.setCheckingLockState,
      sessionId: navigationConfig.sessionId,
      lockNavigationTree: navigationConfig.lockNavigationTree,
      unlockNavigationTree: navigationConfig.unlockNavigationTree,
      setupAutoUnlock: navigationConfig.setupAutoUnlock,

      // Node/Edge management actions
      handleNodeFormSubmit,
      handleEdgeFormSubmit,
      handleDeleteNode: deleteSelected,
      handleDeleteEdge: deleteSelected,
      addNewNode,
      cancelNodeChanges,
      closeSelectionPanel,
      deleteSelected,
      resetNode,

      // Additional actions
      discardChanges,
      performDiscardChanges,
      fitView,

      // Navigation actions
      navigateToTreeLevel: () => {}, // Not implemented
      goBackToParent: navigateToParent,
      navigateToParentView: navigateToParent,
      navigateToParent,

      // Configuration
      defaultEdgeOptions: {
        type: 'uiNavigation',
        animated: false,
        style: { strokeWidth: 2, stroke: '#b1b1b7' },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          width: 20,
          height: 20,
          color: '#b1b1b7',
        },
      },

      // Connection rules
      getConnectionRulesSummary: () => 'No specific connection rules defined',

      // User interface management
      setUserInterfaceFromProps,

      // Device control state - from HostManager
      selectedHost: hostManager.selectedHost,
      isControlActive: hostManager.isControlActive,
      isRemotePanelOpen: hostManager.isRemotePanelOpen,
      showRemotePanel: hostManager.showRemotePanel,
      showAVPanel: hostManager.showAVPanel,
      isVerificationActive: false, // Not implemented

      // Device control handlers - from HostManager
      handleDeviceSelect: hostManager.handleDeviceSelect,
      handleControlStateChange: hostManager.handleControlStateChange,
      handleToggleRemotePanel: hostManager.handleToggleRemotePanel,
      handleConnectionChange: () => {}, // Not implemented
      handleDisconnectComplete: hostManager.handleDisconnectComplete,

      // Host data - from HostManager (filtered by userInterface models)
      availableHosts: hostManager.getHostsByModel(navigation.userInterface?.models || []),
      getHostByName: hostManager.getHostByName,
    }),
    [
      navigation,
      navigationConfig,
      hostManager,
      loadTreeData,
      saveTreeData,
      saveNode,
      saveEdge,
      onConnect,
      onNodeClick,
      onEdgeClick,
      onNodeDoubleClick,
      onPaneClick,
      handleNodeFormSubmit,
      handleEdgeFormSubmit,
      addNewNode,
      cancelNodeChanges,
      closeSelectionPanel,
      deleteSelected,
      resetNode,
      discardChanges,
      performDiscardChanges,
      fitView,
      navigateToParent,
      setUserInterfaceFromProps,
    ],
  );
};
