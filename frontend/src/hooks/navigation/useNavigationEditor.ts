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
        const treeData = await navigationConfig.loadTreeData(treeId);
        
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
            label: edge.label, // Include the auto-generated label from database
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
        console.log('[@useNavigationEditor:loadTreeData] Set initialState with node IDs:', frontendNodes.map((n: any) => n.id));
      } catch (error) {
        navigation.setError(`Failed to load tree: ${error instanceof Error ? error.message : 'Unknown error'}`);
      } finally {
        navigation.setIsLoading(false);
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
          label: `${sourceNode.data.label}→${targetNode.data.label}`,
          description: `Edge from ${sourceNode.data.label} to ${targetNode.data.label}`,
          action_sets: [],
          default_action_set_id: '',
        },
      };

      console.log('[@useNavigationEditor:onConnect] Creating edge:', newEdge);

      // Add edge to current edges using ReactFlow's addEdge utility
      const updatedEdges = addEdge(newEdge, navigation.edges);

      // Update edges in navigation context
      navigation.setEdges(updatedEdges as UINavigationEdge[]);

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
      await navigation.saveNodeWithStateUpdate(nodeForm);
    },
    [navigation],
  );

  const handleEdgeFormSubmit = useCallback(
    async (edgeForm: any) => {
      await navigation.saveEdgeWithStateUpdate(edgeForm);
    },
    [navigation],
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

  const deleteSelected = useCallback(async () => {
    console.log('[@useNavigationEditor:deleteSelected] Starting deletion process', {
      selectedNode: navigation.selectedNode?.id,
      selectedEdge: navigation.selectedEdge?.id,
      currentNodeCount: navigation.nodes.length,
      currentEdgeCount: navigation.edges.length
    });

    if (navigation.selectedNode) {
      const nodeId = navigation.selectedNode.id;
      const node = navigation.selectedNode;
      
      // Check if node has nested trees and warn user
      if (node.data?.has_subtree && (node.data?.subtree_count || 0) > 0) {
        const subtreeCount = node.data?.subtree_count || 0;
        const confirmMessage = `This node has ${subtreeCount} nested tree(s). Deleting it will also delete all nested navigation trees. Are you sure?`;
        if (!window.confirm(confirmMessage)) {
          return; // User cancelled
        }
        console.log(`[@useNavigationEditor:deleteSelected] User confirmed deletion of node with ${subtreeCount} nested trees`);
      }
      
      const filteredNodes = navigation.nodes.filter((n) => n.id !== nodeId);
      console.log('[@useNavigationEditor:deleteSelected] Deleting node:', nodeId, 
        'Nodes before:', navigation.nodes.length, 'Nodes after:', filteredNodes.length);
      navigation.setNodes(filteredNodes);
      navigation.setSelectedNode(null);
      navigation.markUnsavedChanges();
    }
    if (navigation.selectedEdge) {
      const edgeId = navigation.selectedEdge.id;
      const filteredEdges = navigation.edges.filter((e) => e.id !== edgeId);
      console.log('[@useNavigationEditor:deleteSelected] Deleting edge:', edgeId,
        'Edges before:', navigation.edges.length, 'Edges after:', filteredEdges.length);
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
      
      // Centralized save methods from NavigationContext
      saveNodeWithStateUpdate: navigation.saveNodeWithStateUpdate,
      saveEdgeWithStateUpdate: navigation.saveEdgeWithStateUpdate,
      saveTreeWithStateUpdate: navigation.saveTreeWithStateUpdate,



      // Interface operations
      listAvailableTrees: async () => {
        try {
          const response = await fetch('/server/userinterface/getAllUserInterfaces');
          if (!response.ok) {
            throw new Error(`Failed to fetch user interfaces: ${response.status}`);
          }
          return await response.json();
        } catch (error) {
          console.error('Error fetching user interfaces:', error);
          return [];
        }
      },

      // Lock management - from NavigationContext
      isLocked: navigation.isLocked,
      lockNavigationTree: navigation.lockNavigationTree,
      unlockNavigationTree: navigation.unlockNavigationTree,

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
