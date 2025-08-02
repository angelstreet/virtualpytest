import {
  Box,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Snackbar,
  Alert,
  Typography,
  Button,
} from '@mui/material';
import React, { useEffect, useCallback, useRef, useState, useMemo } from 'react';
import { useParams } from 'react-router-dom';
import ReactFlow, {
  Background,
  Controls,
  ReactFlowProvider,
  MiniMap,
  ConnectionLineType,
  BackgroundVariant,
  MarkerType,

} from 'reactflow';
import 'reactflow/dist/style.css';

// Import extracted components and hooks
import { HDMIStream } from '../components/controller/av/HDMIStream';
import { RemotePanel } from '../components/controller/remote/RemotePanel';
import { NavigationBreadcrumbCompact } from '../components/navigation/NavigationBreadcrumbCompact';
import { EdgeEditDialog } from '../components/navigation/Navigation_EdgeEditDialog';
import { EdgeSelectionPanel } from '../components/navigation/Navigation_EdgeSelectionPanel';
import { NavigationEditorHeader } from '../components/navigation/Navigation_EditorHeader';
import { UIMenuNode } from '../components/navigation/Navigation_MenuNode';
import { NavigationEdgeComponent } from '../components/navigation/Navigation_NavigationEdge';
import { UINavigationNode } from '../components/navigation/Navigation_NavigationNode';
import { NodeEditDialog } from '../components/navigation/Navigation_NodeEditDialog';
import { NodeGotoPanel } from '../components/navigation/Navigation_NodeGotoPanel';
import { NodeSelectionPanel } from '../components/navigation/Navigation_NodeSelectionPanel';
import { useTheme } from '../contexts/ThemeContext';
import { useDeviceData } from '../contexts/device/DeviceDataContext';
import { useHostManager } from '../contexts/index';
import {
  NavigationConfigProvider,
  useNavigationConfig,
} from '../contexts/navigation/NavigationConfigContext';
import { useNavigation } from '../contexts/navigation/NavigationContext';
import { NavigationEditorProvider } from '../contexts/navigation/NavigationEditorProvider';
import {
  NavigationStackProvider,
  useNavigationStack,
} from '../contexts/navigation/NavigationStackContext';
import { useNavigationEditor } from '../hooks/navigation/useNavigationEditor';
import { useNestedNavigation } from '../hooks/navigation/useNestedNavigation';
import { useUserInterface } from '../hooks/pages/useUserInterface';
import {
  NodeForm,
  EdgeForm,
  UINavigationNode as UINavigationNodeType,
} from '../types/pages/Navigation_Types';
import { getZIndex } from '../utils/zIndexUtils';

// Node types for React Flow - defined outside component to prevent recreation on every render
const nodeTypes = {
  uiScreen: UINavigationNode,
  uiMenu: UIMenuNode,
};

const edgeTypes = {
  uiNavigation: NavigationEdgeComponent,
  smoothstep: NavigationEdgeComponent,
};

// Default options - defined outside component to prevent recreation
const defaultEdgeOptions = {
  type: 'uiNavigation',
  animated: false,
  style: { strokeWidth: 2, stroke: '#b1b1b7' },
  markerEnd: {
    type: MarkerType.ArrowClosed,
    width: 20,
    height: 20,
    color: '#b1b1b7',
  },
};

const defaultViewport = { x: 0, y: 0, zoom: 1 };

const translateExtent: [[number, number], [number, number]] = [
  [-5000, -5000],
  [10000, 10000],
];
const nodeExtent: [[number, number], [number, number]] = [
  [-5000, -5000],
  [10000, 10000],
];

const snapGrid: [number, number] = [15, 15];

const reactFlowStyle = { width: '100%', height: '100%' };

const nodeOrigin: [number, number] = [0, 0];

// miniMapStyle moved inside component to use theme context

const proOptions = { hideAttribution: true };

// MiniMap nodeColor function - defined outside component to prevent recreation
const miniMapNodeColor = (node: any) => {
  // Check if this is the current position node
  const isCurrentPosition = node.data?.isCurrentPosition;

  // Check if this is part of navigation route
  const isOnNavigationRoute = node.data?.isOnNavigationRoute;

  // Current position gets bright purple
  if (isCurrentPosition) {
    return '#9c27b0'; // Bright purple for current position
  }

  // Navigation route nodes get orange/amber
  if (isOnNavigationRoute) {
    return '#ff9800'; // Orange for navigation route
  }

  // Default colors based on node type
  switch (node.data?.type) {
    case 'screen':
      return '#3b82f6';
    case 'dialog':
      return '#8b5cf6';
    case 'popup':
      return '#f59e0b';
    case 'overlay':
      return '#10b981';
    case 'menu':
      return '#ffc107';
    case 'entry':
      return '#ef4444'; // Red for entry points
    default:
      return '#6b7280';
  }
};

// Helper function removed - was unused

const NavigationEditorContent: React.FC<{ treeName: string }> = React.memo(
  ({ treeName }) => {

    // Get theme context for dynamic styling
    const { actualMode } = useTheme();

    // Get navigation stack for nested navigation
    const { popLevel, jumpToLevel, jumpToRoot, currentLevel, isNested, stack } = useNavigationStack();

    // Get current node ID from NavigationContext
    const { currentNodeId } = useNavigation();

      // Get the actual tree ID from NavigationConfigContext
  const navigationConfig = useNavigationConfig();
  const { actualTreeId, setActualTreeId } = navigationConfig;

    // Get navigation context for nested navigation
    const navigation = useNavigation();

    // Dynamic miniMapStyle based on theme - black background in dark mode, white in light mode
    const miniMapStyle = useMemo(
      () => ({
        backgroundColor: actualMode === 'dark' ? '#1f2937' : '#ffffff',
        border: `1px solid ${actualMode === 'dark' ? '#374151' : '#e5e7eb'}`,
        borderRadius: '8px',
        boxShadow:
          actualMode === 'dark'
            ? '0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -1px rgba(0, 0, 0, 0.2)'
            : '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
      }),
      [actualMode],
    );

    // Use the restored navigation editor hook
    const {
      // State
      nodes,
      edges,
      isLoadingInterface,
      selectedNode,
      selectedEdge,
      isNodeDialogOpen,
      isEdgeDialogOpen,
      nodeForm,
      edgeForm,
      success,
      reactFlowWrapper,

      hasUnsavedChanges,
      isDiscardDialogOpen,
      userInterface,

      // View state for single-level navigation

      // Tree filtering state
      focusNodeId,
      maxDisplayDepth,
      availableFocusNodes,
      allNodes,
      setFocusNode,
      setDisplayDepth,
      resetFocus,

      // Setters
      setIsNodeDialogOpen,
      setIsEdgeDialogOpen,
      setNodeForm,
      setEdgeForm,
      setIsDiscardDialogOpen,

      // Event handlers
      onNodesChange,
      onEdgesChange,
      onConnect,
      onNodeClick,
      onEdgeClick,
      onPaneClick,

      // New normalized API
      saveTreeWithStateUpdate,
      isLocked,
      saveNodeWithStateUpdate,
      saveEdgeWithStateUpdate,
      addNewNode,
      cancelNodeChanges,
      discardChanges,
      performDiscardChanges,
      closeSelectionPanel,
      fitView,
      deleteSelected,
      resetNode,
      setUserInterfaceFromProps,

      // Additional setters we need
      setNodes,
      setSelectedNode,
      setReactFlowInstance,
      setHasUnsavedChanges,
      setEdges,
      // setSelectedEdge, // Removed - not used without handleUpdateEdge

      // Error state
      error,

      // Host data (filtered by userInterface models)
      availableHosts,
    } = useNavigationEditor();

    // Clean approach: Use treeName directly, no fallbacks needed
    const actualUserInterfaceId = treeName;

    // Initialize nested navigation hook for unified double-click handling
    const nestedNavigation = useNestedNavigation({
      setNodes,
      setEdges,
      openNodeDialog: navigation.openNodeDialog,
    });

    // Get host manager from context (excluding availableHosts - we get that from useNavigationEditor)
    const {
      selectedHost,
      selectedDeviceId,
      isControlActive,
      isRemotePanelOpen,
      showRemotePanel,
      showAVPanel,
      handleDeviceSelect,
      handleControlStateChange,
      handleToggleRemotePanel,
      handleDisconnectComplete,
    } = useHostManager();

    // Track the last loaded tree ID to prevent unnecessary reloads
    const lastLoadedTreeId = useRef<string | null>(null);

    // Track AV panel collapsed state
    const [isAVPanelCollapsed, setIsAVPanelCollapsed] = useState(true);
    const [isAVPanelMinimized, setIsAVPanelMinimized] = useState(false);
    const [captureMode, setCaptureMode] = useState<'stream' | 'screenshot' | 'video'>('stream');

    // Goto panel state
    const [showGotoPanel, setShowGotoPanel] = useState(false);
    const [selectedNodeForGoto, setSelectedNodeForGoto] = useState<UINavigationNodeType | null>(
      null,
    );

    // Wrap the original click handlers to close goto panel
    const wrappedOnNodeClick = useCallback(
      (event: React.MouseEvent, node: any) => {
        // Close goto panel if it's open
        if (showGotoPanel) {
          setShowGotoPanel(false);
          setSelectedNodeForGoto(null);
        }
        // Call the original handler
        onNodeClick(event, node);
      },
      [onNodeClick, showGotoPanel],
    );

    const wrappedOnEdgeClick = useCallback(
      (event: React.MouseEvent, edge: any) => {
        // Close goto panel if it's open
        if (showGotoPanel) {
          setShowGotoPanel(false);
          setSelectedNodeForGoto(null);
        }
        // Call the original handler
        onEdgeClick(event, edge);
      },
      [onEdgeClick, showGotoPanel],
    );

    // Wrap the pane click handler to also close goto panel
    const wrappedOnPaneClick = useCallback(() => {
      // Close goto panel if it's open
      if (showGotoPanel) {
        setShowGotoPanel(false);
        setSelectedNodeForGoto(null);
      }
      // Call the original handler
      onPaneClick();
    }, [onPaneClick, showGotoPanel]);

    // Memoize the AV panel collapsed change handler to prevent infinite loops
    const handleAVPanelCollapsedChange = useCallback((isCollapsed: boolean) => {
      setIsAVPanelCollapsed(isCollapsed);
    }, []);

    // Handle minimized state changes from HDMIStream
    const handleAVPanelMinimizedChange = useCallback((isMinimized: boolean) => {
      setIsAVPanelMinimized(isMinimized);
    }, []);

    // Handle capture mode changes from HDMIStream
    const handleCaptureModeChange = useCallback((mode: 'stream' | 'screenshot' | 'video') => {
      setCaptureMode(mode);
    }, []);

    // Handle opening goto panel
    const handleOpenGotoPanel = useCallback((node: UINavigationNodeType) => {
      setSelectedNodeForGoto(node);
      setShowGotoPanel(true);
    }, []);

    // Handle closing goto panel
    const handleCloseGotoPanel = useCallback(() => {
      setShowGotoPanel(false);
      setSelectedNodeForGoto(null);
    }, []);

    // Helper functions using new normalized API
    const loadTreeForUserInterface = useCallback(
      async (userInterfaceId: string) => {
        try {
          // Get the tree directly by user interface ID using the original endpoint
          const response = await fetch(
            `/server/navigationTrees/getTreeByUserInterfaceId/${userInterfaceId}`,
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

          if (data.success && data.tree) {
            // Get the tree data
            const tree = data.tree;
            const treeData = tree.metadata || {};
            const rawNodes = treeData.nodes || [];
            const rawEdges = treeData.edges || [];
            const treeId = tree.id || null;

            // Convert normalized data to frontend format (same as useNavigationEditor)
            const frontendNodes = rawNodes.map((node: any) => ({
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

            const frontendEdges = rawEdges.map((edge: any) => ({
              id: edge.edge_id,
              source: edge.source_node_id,
              target: edge.target_node_id,
              type: 'uiNavigation',
              sourceHandle: edge.data?.sourceHandle, // Extract handle info to root level
              targetHandle: edge.data?.targetHandle, // Extract handle info to root level
              data: {
                label: edge.label, // Include the auto-generated label from database
                action_sets: edge.action_sets, // NEW: action sets structure - REQUIRED
                default_action_set_id: edge.default_action_set_id, // NEW: default action set ID - REQUIRED
                final_wait_time: edge.final_wait_time,
                ...edge.data // Additional data
                // NO LEGACY FIELDS: actions, retryActions removed
              }
            }));

            console.log(
              `[@NavigationEditor:loadTreeForUserInterface] Loaded tree for userInterface: ${userInterfaceId} with ${frontendNodes.length} nodes and ${frontendEdges.length} edges`,
            );

            // Cache tree data and display it
            if (treeId) {
              navigation.cacheAndSwitchToTree(treeId, { nodes: frontendNodes, edges: frontendEdges });
              setActualTreeId(treeId);
              console.log(`[@NavigationEditor:loadTreeForUserInterface] Cached and switched to tree: ${treeId}`);
            }
            
            // Set initial state for deletion detection
            navigation.setInitialState({ nodes: [...frontendNodes], edges: [...frontendEdges] });
            setHasUnsavedChanges(false);
            console.log('[@NavigationEditor:loadTreeForUserInterface] Set initialState with node IDs:', frontendNodes.map((n: any) => n.id));

            console.log(
              `[@NavigationEditor:loadTreeForUserInterface] Set tree data with ${frontendNodes.length} nodes and ${frontendEdges.length} edges`,
            );
          } else {
            console.error('Failed to load tree:', data.error || 'Unknown error');
          }
        } catch (error) {
          console.error('Failed to load tree for user interface:', error);
        }
      },
      [setNodes, setEdges],
    );





    // Handle navigation back to parent tree
    const handleNavigateBack = useCallback(() => {
      // Get target tree before popping the level
      const newCurrentLevel = stack.length > 1 ? stack[stack.length - 2] : null;
      const targetTreeId = newCurrentLevel ? newCurrentLevel.treeId : actualUserInterfaceId;
      
      console.log(`[@NavigationEditor] Navigation back - target tree: ${targetTreeId}, current nested: ${isNested}`);
      
      // Check if target tree is cached
      const cachedTree = navigation.getCachedTree(targetTreeId);
      if (cachedTree) {
        console.log(`[@NavigationEditor] Using cached tree for navigation back: ${targetTreeId}`);
        
        // Update navigation stack first
        popLevel();
        
        // Switch to cached parent tree data
        navigation.switchToTree(targetTreeId);
        
        // Update actualTreeId to reflect current tree
        setActualTreeId(targetTreeId);
        
        console.log(`[@NavigationEditor] Navigation back completed - switched to cached tree: ${targetTreeId}`);
      } else {
        console.warn(`[@NavigationEditor] Tree ${targetTreeId} not found in cache, cannot navigate back`);
      }
    }, [popLevel, actualUserInterfaceId, stack, setActualTreeId, navigation, isNested]);

    // Handle navigation to specific level in breadcrumb
    const handleNavigateToLevel = useCallback(
      (levelIndex: number) => {
        // Get target tree before jumping to level
        const targetLevel = stack[levelIndex];
        const targetTreeId = targetLevel ? targetLevel.treeId : actualUserInterfaceId;
        
        console.log(`[@NavigationEditor] Navigation to level ${levelIndex} - target tree: ${targetTreeId}`);
        
        // Check if target tree is cached
        const cachedTree = navigation.getCachedTree(targetTreeId);
        if (cachedTree) {
          console.log(`[@NavigationEditor] Using cached tree for level navigation: ${targetTreeId}`);
          
          // Update navigation stack first
          jumpToLevel(levelIndex);
          
          // Switch to cached tree data
          navigation.switchToTree(targetTreeId);
          
          // Update actualTreeId to reflect current tree
          setActualTreeId(targetTreeId);
          
          console.log(`[@NavigationEditor] Navigation to level ${levelIndex} completed - switched to cached tree: ${targetTreeId}`);
        } else {
          console.warn(`[@NavigationEditor] Tree ${targetTreeId} not found in cache, cannot navigate to level ${levelIndex}`);
        }
      },
      [jumpToLevel, actualUserInterfaceId, stack, setActualTreeId, navigation],
    );

    // Handle navigation to root
    const handleNavigateToRoot = useCallback(() => {
      console.log(`[@NavigationEditor] Navigation to root - target tree: ${actualUserInterfaceId}`);
      
      // Check if root tree is cached
      const cachedTree = navigation.getCachedTree(actualUserInterfaceId);
      if (cachedTree) {
        console.log(`[@NavigationEditor] Using cached tree for root navigation: ${actualUserInterfaceId}`);
        
        // Update navigation stack first
        jumpToRoot();
        
        // Switch to cached root tree data
        navigation.switchToTree(actualUserInterfaceId);
        
        // Update actualTreeId to reflect root tree
        setActualTreeId(actualUserInterfaceId);
        
        console.log(`[@NavigationEditor] Navigation to root completed - switched to cached tree: ${actualUserInterfaceId}`);
      } else {
        console.warn(`[@NavigationEditor] Root tree ${actualUserInterfaceId} not found in cache, cannot navigate to root`);
      }
    }, [jumpToRoot, actualUserInterfaceId, setActualTreeId, navigation]);

    // Memoize the selectedHost to prevent unnecessary re-renders
    const stableSelectedHost = useMemo(() => selectedHost, [selectedHost]);

    // Centralized reference management - both verification references and actions
    const { setControlState } = useDeviceData();

    // Set control state in device data context when it changes
    useEffect(() => {
      setControlState(stableSelectedHost, selectedDeviceId, isControlActive);
    }, [stableSelectedHost, selectedDeviceId, isControlActive, setControlState]);

    // ========================================
    // 1. INITIALIZATION & REFERENCES
    // ========================================

    // Create a unified save function that handles both root and subtree saves
    const handleSaveToConfig = useCallback(
      async (saveTarget: 'root' | 'subtree' | 'auto' = 'auto') => {
        try {
          // Auto-determine save target if not specified
          const shouldSaveAsSubtree =
            saveTarget === 'subtree' || (saveTarget === 'auto' && isNested && currentLevel);

          if (shouldSaveAsSubtree && currentLevel) {
            // Save as subtree - check if subtree already exists
            console.log(
              `[@NavigationEditor] Saving as subtree for: ${currentLevel.parentNodeLabel}`,
            );

            // First, check if a subtree already exists for this node in the parent tree
            const parentTreeId = currentLevel.parentTreeId || actualTreeId;
            
            console.log(`[@NavigationEditor] Saving nested tree with ${nodes.length} nodes at current canvas positions:`, 
              nodes.map(n => ({ id: n.id, position: n.position })));
            const checkResponse = await fetch(
              `/server/navigationTrees/getNodeSubTrees/${parentTreeId}/${currentLevel.parentNodeId}`,
            );
            const checkResult = await checkResponse.json();

            if (checkResult.success && checkResult.sub_trees && checkResult.sub_trees.length > 0) {
              // Update existing subtree
              const existingSubTree = checkResult.sub_trees[0]; // Use the first subtree
              console.log(`[@NavigationEditor] Updating existing subtree: ${existingSubTree.id}`);

              const updateResponse = await fetch(
                `/server/navigationTrees/updateTree/${existingSubTree.id}`,
                {
                  method: 'PUT',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({
                    tree_data: { 
                      nodes: nodes.map(node => ({
                        node_id: node.id,
                        label: node.data.label,
                        position_x: node.position?.x || 0, // ✅ Proper position normalization
                        position_y: node.position?.y || 0, // ✅ Proper position normalization
                        node_type: node.data.type || 'default',
                        verifications: node.data.verifications || [],
                        data: {
                          ...node.data,
                          description: node.data.description,
                        }
                      })), 
                      edges: edges.map(edge => ({
                        edge_id: edge.id,
                        source_node_id: edge.source,
                        target_node_id: edge.target,
                        label: edge.data?.label,
                        data: {
                          ...(edge.data?.priority && { priority: edge.data.priority }),
                          ...(edge.data?.threshold && { threshold: edge.data.threshold }),
                          ...(edge.sourceHandle && { sourceHandle: edge.sourceHandle }),
                          ...(edge.targetHandle && { targetHandle: edge.targetHandle }),
                        },
                        action_sets: edge.data?.action_sets || [],
                        default_action_set_id: edge.data?.default_action_set_id || 'default',
                        final_wait_time: edge.data?.final_wait_time || 0,
                      }))
                    },
                    description: `Updated actions for ${currentLevel.parentNodeLabel}`,
                    modification_type: 'update',
                    changes_summary: 'Updated subtree from nested navigation editor',
                  }),
                },
              );
              const updateResult = await updateResponse.json();

              if (updateResult.success) {
                console.log('Sub-tree updated successfully');
                setHasUnsavedChanges(false);
              } else {
                console.error('Failed to update sub-tree:', updateResult.message);
                throw new Error(updateResult.message);
              }
            } else {
              // Create new subtree
              console.log(`[@NavigationEditor] Creating new subtree`);
              const response = await fetch(`/server/navigationTrees/${parentTreeId}/nodes/${currentLevel.parentNodeId}/subtrees`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  name: currentLevel.treeName,
                  tree_data: { 
                    nodes: nodes.map(node => ({
                      node_id: node.id,
                      label: node.data.label,
                      position_x: node.position?.x || 0, // ✅ Proper position normalization
                      position_y: node.position?.y || 0, // ✅ Proper position normalization
                      node_type: node.data.type || 'default',
                      verifications: node.data.verifications || [],
                      data: {
                        ...node.data,
                        description: node.data.description,
                      }
                    })), 
                    edges: edges.map(edge => ({
                      edge_id: edge.id,
                      source_node_id: edge.source,
                      target_node_id: edge.target,
                      label: edge.data?.label,
                      data: {
                        ...(edge.data?.priority && { priority: edge.data.priority }),
                        ...(edge.data?.threshold && { threshold: edge.data.threshold }),
                        ...(edge.sourceHandle && { sourceHandle: edge.sourceHandle }),
                        ...(edge.targetHandle && { targetHandle: edge.targetHandle }),
                      },
                      action_sets: edge.data?.action_sets || [],
                      default_action_set_id: edge.data?.default_action_set_id || 'default',
                      final_wait_time: edge.data?.final_wait_time || 0,
                    }))
                  },
                  description: `Actions for ${currentLevel.parentNodeLabel}`,
                }),
              });
              const result = await response.json();

              if (result.success) {
                console.log('Sub-tree created successfully');
                setHasUnsavedChanges(false);
              } else {
                console.error('Failed to create sub-tree:', result.message);
                throw new Error(result.message);
              }
            }
          } else {
            // Save as root tree using centralized tree ID
            console.log(`[@NavigationEditor] Saving tree: ${actualTreeId}`);
            await saveTreeWithStateUpdate(actualTreeId!);
          }
        } catch (error) {
          console.error('Error saving tree:', error);
          // Re-throw to let the UI handle the error
          throw error;
        }
      },
      [
        isNested,
        currentLevel,
        actualTreeId,
        nodes,
        edges,
        actualUserInterfaceId,
        saveTreeWithStateUpdate,
        setHasUnsavedChanges,
      ],
    );

    // Wrapper for the header component (matches expected signature)
    const handleSaveForHeader = useCallback(() => {
      handleSaveToConfig('auto');
    }, [handleSaveToConfig]);



    // Lifecycle refs to prevent unnecessary re-renders

    // Clean approach: Resolve userInterface by name from treeName
    const { getUserInterfaceByName } = useUserInterface();
    
    useEffect(() => {
      const resolveUserInterface = async () => {
        if (!treeName) return;
        
        // If we already have the correct userInterface, skip
        if (userInterface?.name === treeName) return;
        
        try {
          console.log(`[@component:NavigationEditor] Resolving userInterface for treeName: ${treeName}`);
          
          const resolvedInterface = await getUserInterfaceByName(treeName);
          setUserInterfaceFromProps(resolvedInterface);
          
          console.log(`[@component:NavigationEditor] Successfully resolved userInterface: ${resolvedInterface.name} (ID: ${resolvedInterface.id})`);
        } catch (error) {
          console.error(`[@component:NavigationEditor] Failed to resolve userInterface for treeName ${treeName}:`, error);
        }
      };
      
      resolveUserInterface();
    }, [treeName, userInterface, setUserInterfaceFromProps, getUserInterfaceByName]);

    // Clean approach: treeName is guaranteed to exist from NavigationEditor

    // Effect to load tree when tree name changes
    useEffect(() => {
      // Only load if we have a tree name and userInterface is loaded
      if (userInterface?.id && !isLoadingInterface) {
        // Check if we already loaded this userInterface to prevent infinite loops
        if (lastLoadedTreeId.current === userInterface.id) {
          return;
        }
        
        // CRITICAL: Don't reload if we're navigating back and the tree is already cached
        const cachedTree = navigation.getCachedTree(userInterface.id);
        if (cachedTree && isNested) {
          console.log(`[@component:NavigationEditor] Skipping tree reload - using cached tree for navigation back: ${userInterface.id}`);
          navigation.switchToTree(userInterface.id);
          lastLoadedTreeId.current = userInterface.id;
          return;
        }
        
        lastLoadedTreeId.current = userInterface.id;

        // STEP 1: Load tree data directly (simplified approach)
        console.log(`[@component:NavigationEditor] Loading tree for userInterface: ${userInterface.id}`);
        loadTreeForUserInterface(userInterface.id);

        // No auto-unlock for navigation tree - keep it locked for editing session
      }
    }, [userInterface?.id, isLoadingInterface, loadTreeForUserInterface, navigation, isNested]);

    // Simple update handlers - complex validation logic moved to device control component
    const handleUpdateNode = useCallback(
      (nodeId: string, updatedData: any) => {
        const updatedNodes = nodes.map((node) =>
          node.id === nodeId ? { ...node, data: { ...node.data, ...updatedData } } : node,
        );
        setNodes(updatedNodes);
        if (selectedNode?.id === nodeId) {
          setSelectedNode({ ...selectedNode, data: { ...selectedNode.data, ...updatedData } });
        }
        setHasUnsavedChanges(true);
      },
      [nodes, setNodes, setSelectedNode, setHasUnsavedChanges, selectedNode],
    );

    // Wrapper for node form submission to handle the form data
    const handleNodeFormSubmitWrapper = useCallback(() => {
      if (nodeForm) {
        console.log(
          '[@component:NavigationEditor] Submitting node form with verifications:',
          nodeForm.verifications?.length || 0,
        );
        saveNodeWithStateUpdate(nodeForm);
        console.log('[@component:NavigationEditor] Node form submitted successfully');
      }
    }, [nodeForm, saveNodeWithStateUpdate]);

    // Wrapper for add new node to provide default parameters
    const handleAddNewNodeWrapper = useCallback(() => {
      addNewNode('screen', { x: 250, y: 250 });
    }, [addNewNode]);



    // ========================================
    // 7. RENDER
    // ========================================

    // State for edge labels
    const [edgeLabels, setEdgeLabels] = useState<{ fromLabel: string; toLabel: string }>({
      fromLabel: '',
      toLabel: '',
    });

    return (
      <Box
        sx={{
          width: '100%',
          height: 'calc(100vh - 100px)',
          minHeight: '500px',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
      >
        {/* Header with NavigationEditorHeader component */}
        <NavigationEditorHeader
          hasUnsavedChanges={hasUnsavedChanges}
          focusNodeId={focusNodeId}
          availableFocusNodes={availableFocusNodes}
          maxDisplayDepth={maxDisplayDepth}
          totalNodes={allNodes.length}
          visibleNodes={nodes.length}
          isLoading={isLoadingInterface}
          error={error}
          isLocked={isLocked ?? false}
          treeId={actualTreeId || ''}
          selectedHost={selectedHost}
          selectedDeviceId={selectedDeviceId}
          isRemotePanelOpen={isRemotePanelOpen}
          availableHosts={availableHosts}
          onAddNewNode={handleAddNewNodeWrapper}
          onFitView={fitView}
          onSaveToConfig={handleSaveForHeader}
          onDiscardChanges={discardChanges}
          onDepthChange={setDisplayDepth}
          onResetFocus={resetFocus}
          onFocusNodeChange={setFocusNode}
          onToggleRemotePanel={handleToggleRemotePanel}
          onControlStateChange={handleControlStateChange}
          onDeviceSelect={handleDeviceSelect}
        />

        {/* Compact Breadcrumb - positioned below header, aligned left */}
        <NavigationBreadcrumbCompact
          onNavigateBack={handleNavigateBack}
          onNavigateToLevel={handleNavigateToLevel}
          onNavigateToRoot={handleNavigateToRoot}
        />

        {/* Main Container with side-by-side layout */}
        <Box
          sx={{
            flex: 1,
            display: 'flex',
            minHeight: '500px',
            overflow: 'hidden',
          }}
        >
          {/* Main Editor Area */}
          <Box
            sx={{
              flex: 1,
              position: 'relative',
              minHeight: '500px',
              overflow: 'hidden',
              transition: 'margin-right',
              marginRight: '0px', // Remote panel managed by header
            }}
          >
            <>
              <div
                ref={reactFlowWrapper}
                style={{
                  width: '100%',
                  height: '100%',
                  minHeight: '500px',
                  position: 'relative',
                }}
              >
                {/* Read-Only Overlay - only when definitively locked by someone else */}
                {isLocked && (
                  <Box
                    sx={{
                      position: 'absolute',
                      top: 10,
                      right: 10,
                      zIndex: getZIndex('READ_ONLY_INDICATOR'),
                      backgroundColor: 'warning.light',
                      color: 'warning.contrastText',
                      px: 1,
                      py: 0.5,
                      borderRadius: 1,
                      boxShadow: 2,
                      display: 'flex',
                      alignItems: 'center',
                      gap: 1,
                      fontSize: '0.675rem',
                      fontWeight: 'medium',
                    }}
                  >
                    🔒 READ-ONLY MODE
                    <Typography variant="caption" sx={{ opacity: 0.8 }}>
                      Tree locked by another user
                    </Typography>
                  </Box>
                )}

                <ReactFlow
                  nodes={nodes}
                  edges={edges}
                  onNodesChange={onNodesChange}
                  onEdgesChange={onEdgesChange}
                  onConnect={onConnect}
                  onNodeClick={wrappedOnNodeClick}
                  onEdgeClick={wrappedOnEdgeClick}
                  onNodeDoubleClick={nestedNavigation.handleNodeDoubleClick}
                  onPaneClick={wrappedOnPaneClick}
                  onInit={setReactFlowInstance}
                  nodeTypes={nodeTypes}
                  edgeTypes={edgeTypes}
                  defaultEdgeOptions={defaultEdgeOptions}
                  connectionLineType={ConnectionLineType.SmoothStep}
                  defaultViewport={defaultViewport}
                  translateExtent={translateExtent}
                  nodeExtent={nodeExtent}
                  snapToGrid={true}
                  snapGrid={snapGrid}
                  style={reactFlowStyle}
                  nodeOrigin={nodeOrigin}
                  proOptions={proOptions}
                >
                  <Background variant={BackgroundVariant.Dots} gap={15} size={1} />
                  <Controls />
                  <MiniMap
                    style={miniMapStyle}
                    nodeColor={miniMapNodeColor}
                    maskColor="rgba(255, 255, 255, 0.2)"
                    pannable
                    zoomable
                    position="top-right"
                  />
                </ReactFlow>
              </div>

              {/* Side Panels */}
              {selectedNode || selectedEdge ? (
                <>
                  {selectedNode && selectedNode.data.type !== 'entry' ? (
                    <>
                      {/* Node Selection Panel */}
                      <NodeSelectionPanel
                        selectedNode={selectedNode}
                        nodes={nodes}
                        onClose={closeSelectionPanel}
                        onDelete={deleteSelected}
                        setNodeForm={setNodeForm as React.Dispatch<React.SetStateAction<NodeForm>>}
                        setIsNodeDialogOpen={setIsNodeDialogOpen}
                        onReset={resetNode}
                        onUpdateNode={handleUpdateNode}
                        isControlActive={isControlActive}
                        selectedHost={selectedHost || undefined}
                        selectedDeviceId={selectedDeviceId || undefined}
                        treeId={actualTreeId || ''}
                        currentNodeId={currentNodeId || undefined}
                        onOpenGotoPanel={handleOpenGotoPanel}
                      />
                    </>
                  ) : selectedEdge ? (
                    <>
                      {/* Edge Selection Panels - handled by useEdge hook */}
                      {(selectedEdge.data?.action_sets?.length > 0) ? (
                        selectedEdge.data.action_sets.map((actionSet: any, index: number) => (
                          <EdgeSelectionPanel
                            key={`${selectedEdge.id}-${actionSet.id}-${index}`}
                            selectedEdge={selectedEdge}
                            actionSet={actionSet}
                            panelIndex={index}
                            onClose={closeSelectionPanel}
                            onEdit={() => {}}
                            onDelete={deleteSelected}
                            setEdgeForm={setEdgeForm as React.Dispatch<React.SetStateAction<EdgeForm>>}
                            setIsEdgeDialogOpen={setIsEdgeDialogOpen}
                            isControlActive={isControlActive}
                            selectedHost={selectedHost || undefined}
                            selectedDeviceId={selectedDeviceId || undefined}
                            onEditWithLabels={(fromLabel, toLabel) =>
                              setEdgeLabels({ fromLabel, toLabel })
                            }
                            currentEdgeForm={edgeForm}
                          />
                        ))
                      ) : (
                        // Fallback for edges with empty or missing action_sets
                        <EdgeSelectionPanel
                          selectedEdge={selectedEdge}
                          panelIndex={0}
                          onClose={closeSelectionPanel}
                          onEdit={() => {}}
                          onDelete={deleteSelected}
                          setEdgeForm={setEdgeForm as React.Dispatch<React.SetStateAction<EdgeForm>>}
                          setIsEdgeDialogOpen={setIsEdgeDialogOpen}
                          isControlActive={isControlActive}
                          selectedHost={selectedHost || undefined}
                          selectedDeviceId={selectedDeviceId || undefined}
                          onEditWithLabels={(fromLabel, toLabel) =>
                            setEdgeLabels({ fromLabel, toLabel })
                          }
                          currentEdgeForm={edgeForm}
                        />
                      )}
                    </>
                  ) : null}
                </>
              ) : null}
            </>
          </Box>

          {/* Remote Control Panel is now handled by NavigationEditorDeviceControl component */}
        </Box>

        {/* Autonomous Panels - Now self-positioning with configurable layouts */}
        {showRemotePanel && selectedHost && selectedDeviceId && (
          <RemotePanel
            host={selectedHost}
            deviceId={selectedDeviceId}
            deviceModel={
              selectedHost.devices?.find((d) => d.device_id === selectedDeviceId)?.device_model ||
              'unknown'
            }
            isConnected={isControlActive}
            onReleaseControl={handleDisconnectComplete}
            deviceResolution={{ width: 1920, height: 1080 }}
            streamCollapsed={isAVPanelCollapsed}
            streamMinimized={isAVPanelMinimized}
            captureMode={captureMode}
          />
        )}

        {showAVPanel && selectedHost && selectedDeviceId && (
          <HDMIStream
            host={selectedHost}
            deviceId={selectedDeviceId}
            deviceModel={
              selectedHost.devices?.find((d) => d.device_id === selectedDeviceId)?.device_model
            }
            isControlActive={isControlActive}
            onCollapsedChange={handleAVPanelCollapsedChange}
            onMinimizedChange={handleAVPanelMinimizedChange}
            onCaptureModeChange={handleCaptureModeChange}
          />
        )}

        {/* Node Goto Panel */}
        {showGotoPanel && selectedNodeForGoto && actualTreeId && (
          <NodeGotoPanel
            selectedNode={selectedNodeForGoto}
            nodes={nodes}
            treeId={actualTreeId || ''}
            onClose={handleCloseGotoPanel}
            currentNodeId={currentNodeId || undefined}
            selectedHost={selectedHost || undefined}
            selectedDeviceId={selectedDeviceId || undefined}
            isControlActive={isControlActive}
          />
        )}

        {/* Node Edit Dialog */}
        {isNodeDialogOpen && (
          <NodeEditDialog
            isOpen={isNodeDialogOpen}
            nodeForm={nodeForm}
            nodes={nodes}
            setNodeForm={setNodeForm as (form: NodeForm | null) => void}
            onSubmit={handleNodeFormSubmitWrapper}
            onClose={cancelNodeChanges}
            onResetNode={() => selectedNode && resetNode(selectedNode.id)}
            model={userInterface?.models?.[0] || 'android_mobile'}
            isControlActive={isControlActive}
            selectedHost={selectedHost}
            selectedDeviceId={selectedDeviceId || undefined}
          />
        )}

        {/* Edge Edit Dialog */}
        {isEdgeDialogOpen && selectedHost && (
          <EdgeEditDialog
            isOpen={isEdgeDialogOpen}
            edgeForm={edgeForm}
            setEdgeForm={setEdgeForm as React.Dispatch<React.SetStateAction<EdgeForm>>}
                            onSubmit={saveEdgeWithStateUpdate}
            onClose={() => setIsEdgeDialogOpen(false)}
            selectedEdge={selectedEdge}
            isControlActive={isControlActive}
            selectedHost={selectedHost}
            fromLabel={edgeLabels.fromLabel}
            toLabel={edgeLabels.toLabel}
          />
        )}

        {/* Discard Changes Confirmation Dialog */}
        <Dialog
          open={isDiscardDialogOpen}
          onClose={() => setIsDiscardDialogOpen(false)}
          sx={{ zIndex: getZIndex('NAVIGATION_CONFIRMATION') }}
        >
          <DialogTitle>Discard Changes?</DialogTitle>
          <DialogContent>
            <Typography>
              You have unsaved changes. Are you sure you want to discard them and revert to the last
              saved state?
            </Typography>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setIsDiscardDialogOpen(false)}>Cancel</Button>
            <Button onClick={performDiscardChanges} color="warning" variant="contained">
              Discard Changes
            </Button>
          </DialogActions>
        </Dialog>

        {/* Success/Error Messages */}
        {success && (
          <Snackbar
            open={!!success}
            autoHideDuration={3000}
            onClose={() => {}}
            anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
          >
            <Alert severity="success" sx={{ width: '100%' }}>
              {success}
            </Alert>
          </Snackbar>
        )}
      </Box>
    );
  },
  () => {
    // Custom comparison function - since this component has no props,
    // it should only re-render when its internal hooks change
    // Return true to prevent re-render, false to allow re-render
    return false; // Always allow re-render since we depend on context hooks
  },
);

const NavigationEditor: React.FC = () => {
  // Clean approach: Get treeName from URL parameters only
  const { treeName } = useParams<{ treeName: string }>();

  if (!treeName) {
    return (
      <Box sx={{ p: 2 }}>
        <Typography variant="h6" color="error">
          Invalid URL: Missing tree name
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Expected format: /navigation-editor/[treeName]
        </Typography>
      </Box>
    );
  }

  // Always render with full providers - no conditionals
  return (
    <ReactFlowProvider>
      <NavigationConfigProvider>
        <NavigationEditorProvider>
          <NavigationStackProvider>
            <NavigationEditorContent treeName={treeName} />
          </NavigationStackProvider>
        </NavigationEditorProvider>
      </NavigationConfigProvider>
    </ReactFlowProvider>
  );
};

export default NavigationEditor;
