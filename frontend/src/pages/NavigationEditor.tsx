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

import { DEFAULT_DEVICE_RESOLUTION } from '../config/deviceResolutions';
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
import { RemotePanel } from '../components/controller/remote/RemotePanel';
import { DesktopPanel } from '../components/controller/desktop/DesktopPanel';
import { WebPanel } from '../components/controller/web/WebPanel';
import { VNCStream } from '../components/controller/av/VNCStream';
import { HDMIStream } from '../components/controller/av/HDMIStream';
import { NavigationBreadcrumbCompact } from '../components/navigation/NavigationBreadcrumbCompact';
import { EdgeEditDialog } from '../components/navigation/Navigation_EdgeEditDialog';
import { AIGenerationModal } from '../components/navigation/AIGenerationModal';
import { EdgeSelectionPanel } from '../components/navigation/Navigation_EdgeSelectionPanel';
import { MetricsNotification } from '../components/navigation/MetricsNotification';
import { MetricsModal } from '../components/navigation/MetricsModal';
import { NavigationEditorHeader } from '../components/navigation/Navigation_EditorHeader';
import { UIMenuNode } from '../components/navigation/Navigation_MenuNode';
import { NavigationEdgeComponent } from '../components/navigation/Navigation_NavigationEdge';
import { UINavigationNode } from '../components/navigation/Navigation_NavigationNode';
import { UIActionNode } from '../components/navigation/Navigation_ActionNode';
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
import { useEdge } from '../hooks/navigation/useEdge';
import { useMetrics } from '../hooks/navigation/useMetrics';
import { useUserInterface } from '../hooks/pages/useUserInterface';
import {
  NodeForm,
  EdgeForm,
  UINavigationNode as UINavigationNodeType,
} from '../types/pages/Navigation_Types';
import { getZIndex } from '../utils/zIndexUtils';
import { buildServerUrl } from '../utils/buildUrlUtils';

// Node types for React Flow - defined outside component to prevent recreation on every render
const nodeTypes = {
  screen: UINavigationNode,
  menu: UIMenuNode,
  action: UIActionNode,
  entry: UINavigationNode, // Entry nodes use the same component as screen nodes but with different styling
};

const edgeTypes = {
  navigation: NavigationEdgeComponent,
  smoothstep: NavigationEdgeComponent,
};

// Default options - defined outside component to prevent recreation
const defaultEdgeOptions = {
  type: 'navigation',
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

const NavigationEditorContent: React.FC<{ treeName: string }> = ({ treeName }) => {

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
      
      // API methods
      loadTreeByUserInterface,
    } = useNavigationEditor();

    // treeName is available from useParams and used for userInterface resolution

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

    // Initialize edge hook - always call but with proper parameters
    const edgeHook = useEdge({
      selectedHost: selectedEdge ? (selectedHost || null) : null,
      selectedDeviceId: selectedEdge ? (selectedDeviceId || null) : null,
      isControlActive: selectedEdge ? isControlActive : false,
      treeId: actualTreeId, // Always pass actualTreeId for proper navigation context
    });

    // Initialize metrics hook
    const [preloadedMetrics, setPreloadedMetrics] = useState<any>(null);
    const metricsHook = useMetrics({
      treeId: actualTreeId,
      nodes,
      edges,
      enabled: true, // Always enabled for confidence tracking
      preloadedMetrics, // Pass metrics from combined endpoint
    });

    // Track the last loaded tree ID to prevent unnecessary reloads
    const lastLoadedTreeId = useRef<string | null>(null);
    
    // Track the last resolved treeName to prevent duplicate userInterface resolution
    const lastResolvedTreeName = useRef<string | null>(null);

    // AV panel collapsed state for other UI elements (keeping for backwards compatibility)
    const [isAVPanelCollapsed, setIsAVPanelCollapsed] = useState(true);

    // AV panel minimized state for overlay coordination
    const [isAVPanelMinimized, setIsAVPanelMinimized] = useState(false);

    // Capture mode state for coordinating between AV and Remote panels
    const [captureMode, setCaptureMode] = useState<'stream' | 'screenshot' | 'video'>('stream');

    // Calculate verification editor visibility based on capture mode (same logic as AV components)
    const isVerificationVisible = captureMode === 'screenshot' || captureMode === 'video';

    // Goto panel state
    const [showGotoPanel, setShowGotoPanel] = useState(false);
    const [selectedNodeForGoto, setSelectedNodeForGoto] = useState<UINavigationNodeType | null>(
      null,
    );

    // AI Generation modal state
    const [isAIGenerationOpen, setIsAIGenerationOpen] = useState(false);

    // Metrics state
    const [showMetricsModal, setShowMetricsModal] = useState(false);

    // AI Generation handler
    const handleToggleAIGeneration = useCallback(() => {
      setIsAIGenerationOpen(true);
    }, []);

    // Handle AI generation completion
    const handleAIGenerated = useCallback(() => {
      // Refresh the navigation tree after AI generation
      const refreshData = async () => {
        try {
          if (userInterface?.id) {
            // Re-fetch tree data after AI generation using navigation hook
            try {
              const result = await loadTreeByUserInterface(userInterface.id);
              // Tree data is automatically updated in the navigation context
              // If metrics were included, store them for useMetrics hook
              if (result?.metrics) {
                console.log('[@NavigationEditor] Capturing preloaded metrics from tree load');
                setPreloadedMetrics(result.metrics);
              }
            } catch (error) {
              console.error('Failed to refresh tree data after AI generation:', error);
            }
          }
        } catch (error) {
          console.error('[@NavigationEditor:handleAIGenerated] Failed to refresh tree data:', error);
        }
      };
      refreshData();
    }, [userInterface?.id]);

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

    // Handle capture mode changes from AV components
    const handleCaptureModeChange = useCallback((mode: 'stream' | 'screenshot' | 'video') => {
      setCaptureMode(mode);
      console.log('[@NavigationEditor] Capture mode changed to:', mode);
    }, []);

    // Handle AV panel minimized changes
    const handleAVPanelMinimizedChange = useCallback((isMinimized: boolean) => {
      setIsAVPanelMinimized(isMinimized);
      console.log('[@NavigationEditor] AV panel minimized changed to:', isMinimized);
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

    // Handle metrics modal
    const handleOpenMetricsModal = useCallback(() => {
      setShowMetricsModal(true);
    }, []);

    const handleCloseMetricsModal = useCallback(() => {
      setShowMetricsModal(false);
    }, []);

    // Handle metrics notification actions
    const handleCloseMetricsNotification = useCallback(() => {
      // This will be called when the toast is minimized
      // No action needed - the toast component handles minimization internally
    }, []);

    // Helper functions using new normalized API
    const loadTreeForUserInterface = useCallback(
      async (userInterfaceId: string) => {
        try {
          // Use the hook's loadTreeByUserInterface which includes metrics
          const result = await loadTreeByUserInterface(userInterfaceId);
          
          // If metrics were included, store them for useMetrics hook
          if (result?.metrics) {
            console.log('[@NavigationEditor:loadTreeForUserInterface] ✅ Capturing metrics from combined endpoint');
            setPreloadedMetrics(result.metrics);
          }
        } catch (error) {
          console.error('[@NavigationEditor:loadTreeForUserInterface] Error loading tree:', error);
        }
      },
      [loadTreeByUserInterface, setPreloadedMetrics],
    );

    // Handle navigation back to parent tree
    const handleNavigateBack = useCallback(() => {
      // Get target tree from navigation stack or fall back to root
      const newCurrentLevel = stack.length > 1 ? stack[stack.length - 2] : null;
      const targetTreeId = newCurrentLevel ? newCurrentLevel.treeId : navigation.rootTreeId;
      
      console.log(`[@NavigationEditor] Navigation back - target tree: ${targetTreeId}, stack length: ${stack.length}, rootTreeId: ${navigation.rootTreeId}`);
      
      if (!targetTreeId) {
        console.error(`[@NavigationEditor] Cannot navigate back - no target tree ID found. Stack:`, stack, 'RootTreeId:', navigation.rootTreeId);
        return;
      }
      
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
    }, [popLevel, stack, setActualTreeId, navigation]);

    // Handle navigation to specific level in breadcrumb
    const handleNavigateToLevel = useCallback(
      (levelIndex: number) => {
        // Get target tree from navigation stack or fall back to root
        const targetLevel = stack[levelIndex];
        const targetTreeId = targetLevel ? targetLevel.treeId : navigation.rootTreeId;
        
        console.log(`[@NavigationEditor] Navigation to level ${levelIndex} - target tree: ${targetTreeId}, stack length: ${stack.length}`);
        
        if (!targetTreeId) {
          console.error(`[@NavigationEditor] Cannot navigate to level ${levelIndex} - no target tree ID found. Stack:`, stack, 'RootTreeId:', navigation.rootTreeId);
          return;
        }
        
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
      [jumpToLevel, stack, setActualTreeId, navigation],
    );

    // Handle navigation to root
    const handleNavigateToRoot = useCallback(() => {
      const rootTreeId = navigation.rootTreeId;
      console.log(`[@NavigationEditor] Navigation to root - target tree: ${rootTreeId}`);
      
      if (!rootTreeId) {
        console.error(`[@NavigationEditor] Cannot navigate to root - no root tree ID found. RootTreeId:`, navigation.rootTreeId);
        return;
      }
      
      // Check if root tree is cached
      const cachedTree = navigation.getCachedTree(rootTreeId);
      if (cachedTree) {
        console.log(`[@NavigationEditor] Using cached tree for root navigation: ${rootTreeId}`);
        
        // Update navigation stack first
        jumpToRoot();
        
        // Switch to cached root tree data
        navigation.switchToTree(rootTreeId);
        
        // Update actualTreeId to reflect root tree
        setActualTreeId(rootTreeId);
        
        console.log(`[@NavigationEditor] Navigation to root completed - switched to cached tree: ${rootTreeId}`);
      } else {
        console.warn(`[@NavigationEditor] Root tree ${rootTreeId} not found in cache, cannot navigate to root`);
      }
    }, [jumpToRoot, setActualTreeId, navigation]);

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

    // Unified save function - works for both root and nested trees
    const handleSaveToConfig = useCallback(
      async () => {
        try {
          const treeType = isNested && currentLevel ? 'nested' : 'root';
          console.log(`[@NavigationEditor] Saving ${treeType} tree: ${actualTreeId} with ${nodes.length} nodes`);
          
          // All tree saves now use the same unified batch API
          await saveTreeWithStateUpdate(actualTreeId!);
          
          console.log(`[@NavigationEditor] ${treeType} tree saved successfully`);
        } catch (error) {
          console.error('Error saving tree:', error);
          throw error;
        }
      },
      [isNested, currentLevel, actualTreeId, nodes.length, saveTreeWithStateUpdate],
    );

    // Wrapper for the header component (matches expected signature)
    const handleSaveForHeader = useCallback(() => {
      handleSaveToConfig();
    }, [handleSaveToConfig]);



    // Lifecycle refs to prevent unnecessary re-renders

    // Clean approach: Resolve userInterface by name from treeName
    const { getUserInterfaceByName } = useUserInterface();
    
    useEffect(() => {
      const resolveUserInterface = async () => {
        if (!treeName) return;
        
        // Prevent duplicate resolution for the same treeName
        if (lastResolvedTreeName.current === treeName) return;
        
        // If we already have the correct userInterface, skip
        if (userInterface?.name === treeName) return;
        
        try {
          console.log(`[@component:NavigationEditor] Resolving userInterface for treeName: ${treeName}`);
          
          // Mark as being resolved to prevent duplicates
          lastResolvedTreeName.current = treeName;
          
          const resolvedInterface = await getUserInterfaceByName(treeName);
          setUserInterfaceFromProps(resolvedInterface);
          
          console.log(`[@component:NavigationEditor] Successfully resolved userInterface: ${resolvedInterface.name} (ID: ${resolvedInterface.id})`);
        } catch (error) {
          console.error(`[@component:NavigationEditor] Failed to resolve userInterface for treeName ${treeName}:`, error);
          // Reset on error so we can retry
          lastResolvedTreeName.current = null;
        }
      };
      
      resolveUserInterface();
    }, [treeName, userInterface?.name, setUserInterfaceFromProps]);

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
          nodeForm.verifications,
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
          onToggleAIGeneration={handleToggleAIGeneration}
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
                  onInit={(instance) => {
                    console.log(`[@NavigationEditor] ReactFlow onInit called`);
                    setReactFlowInstance(instance);
                    // Restore viewport if pending
                    const pendingViewport = navigation.pendingViewport;
                    console.log(`[@NavigationEditor] Checking pendingViewport:`, pendingViewport);
                    if (pendingViewport) {
                      console.log(`[@NavigationEditor] Restoring viewport on ReactFlow init:`, pendingViewport);
                      instance.setViewport(pendingViewport);
                      navigation.setPendingViewport(null); // Clear after restoration
                    } else {
                      console.log(`[@NavigationEditor] No pending viewport to restore`);
                    }
                  }}
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
                  <Controls position="top-left" />
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
              {selectedNode ? (
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
                        nodeMetrics={metricsHook.getNodeMetrics(selectedNode.id)}
                      />
                    </>
              ) : null}
              
              {selectedEdge ? (
                    <>
                      {/* Edge Selection Panels - show panels for both edges if bidirectional */}
                      {(() => {
                        console.log('[@NavigationEditor] Rendering edge panels for selectedEdge:', selectedEdge);
                        console.log('[@NavigationEditor] selectedEdge.bidirectionalEdge:', selectedEdge.bidirectionalEdge);
                        
                        // Edge hook is now conditionally initialized at component level
                        
                        // Post-migration: Only show the selected edge, no bidirectional logic
                        const edgesToShow = [selectedEdge];

                        console.log('[@NavigationEditor] Total edges to show:', edgesToShow.length);
                        console.log('[@NavigationEditor] Edges to show:', edgesToShow);

                        let panelIndexOffset = 0;

                        return edgesToShow.map((edge) => {
                          console.log('[@NavigationEditor] Creating panels for edge:', edge.id, 'with action_sets:', edge.data?.action_sets);
                          const panels = [];
                          
                          // Use filtered action sets for display - only forward direction for action edges
                          const displayActionSets = edgeHook?.getDisplayActionSets(edge) || [];
                          
                          if (displayActionSets.length > 0) {
                            console.log('[@NavigationEditor] Edge has', displayActionSets.length, 'display action sets (filtered for action type)');
                            console.log('[@NavigationEditor] Is action edge:', edgeHook?.isActionEdge(edge));
                            // Render panels for each display action set in this edge
                            displayActionSets.forEach((actionSet: any, actionSetIndex: number) => {
                              console.log('[@NavigationEditor] Creating panel for action set:', actionSet.id, 'at index:', panelIndexOffset + actionSetIndex);
                              const edgeMetrics = metricsHook.getEdgeDirectionMetrics(edge.id, actionSet.id);
                              console.log('[@NavigationEditor] Edge metrics for', edge.id, 'actionSet', actionSet.id, ':', edgeMetrics);
                              panels.push(
                                <EdgeSelectionPanel
                                  key={`${edge.id}-${actionSet.id}-${actionSet.actions?.length || 0}`}
                                  selectedEdge={edge}
                                  actionSet={actionSet}
                                  panelIndex={panelIndexOffset + actionSetIndex}
                                  onClose={closeSelectionPanel}
                                  onEdit={() => {}}
                                  onDelete={() => navigation.deleteEdgeDirection(edge.id, actionSet.id)}
                                  setEdgeForm={setEdgeForm as React.Dispatch<React.SetStateAction<EdgeForm>>}
                                  setIsEdgeDialogOpen={setIsEdgeDialogOpen}
                                  isControlActive={isControlActive}
                                  selectedHost={selectedHost || undefined}
                                  selectedDeviceId={selectedDeviceId || undefined}
                                  onEditWithLabels={(fromLabel, toLabel) =>
                                    setEdgeLabels({ fromLabel, toLabel })
                                  }
                                  currentEdgeForm={edgeForm}
                                  edgeMetrics={edgeMetrics}
                                  treeId={actualTreeId}
                                />
                              );
                            });
                            
                            // Add fallback panel only for non-action edges that have less than 2 action sets
                            // Action edges should only show forward direction - no fallback for missing reverse
                            const isActionEdge = edgeHook?.isActionEdge(edge) || false;
                            if (!isActionEdge && edge.data.action_sets.length < 2) {
                              console.log('[@NavigationEditor] Adding fallback panel for missing direction at index:', panelIndexOffset + displayActionSets.length);
                              panels.push(
                                <EdgeSelectionPanel
                                  key={`${edge.id}-fallback`}
                                  selectedEdge={edge}
                                  actionSet={null}
                                  panelIndex={panelIndexOffset + displayActionSets.length}
                                  onClose={closeSelectionPanel}
                                  onEdit={() => {}}
                                  onDelete={() => navigation.deleteEdgeDirection(edge.id, 'fallback')}
                                  setEdgeForm={setEdgeForm as React.Dispatch<React.SetStateAction<EdgeForm>>}
                                  setIsEdgeDialogOpen={setIsEdgeDialogOpen}
                                  isControlActive={isControlActive}
                                  selectedHost={selectedHost || undefined}
                                  selectedDeviceId={selectedDeviceId || undefined}
                                  onEditWithLabels={(fromLabel, toLabel) =>
                                    setEdgeLabels({ fromLabel, toLabel })
                                  }
                                  currentEdgeForm={edgeForm}
                                  edgeMetrics={metricsHook.getEdgeMetrics(edge.id)}
                                  treeId={actualTreeId}
                                />
                              );
                              panelIndexOffset += 2; // Always reserve space for 2 panels (defined + fallback)
                            } else {
                              panelIndexOffset += displayActionSets.length; // Use filtered count
                            }
                          } else {
                            console.log('[@NavigationEditor] Edge has no action sets, using fallback panel at index:', panelIndexOffset);
                            // Fallback for edges with empty or missing action_sets
                            panels.push(
                              <EdgeSelectionPanel
                                key={`${edge.id}-fallback`}
                                selectedEdge={edge}
                                actionSet={null}
                                panelIndex={panelIndexOffset}
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
                                edgeMetrics={metricsHook.getEdgeMetrics(edge.id)}
                                treeId={actualTreeId}
                              />
                            );
                            panelIndexOffset += 1;
                          }
                          
                          console.log('[@NavigationEditor] Created', panels.length, 'panels for edge:', edge.id);
                          return panels;
                        }).flat();
                      })()}
                    </>
              ) : null}
            </>
          </Box>

          {/* Remote Control Panel is now handled by NavigationEditorDeviceControl component */}
        </Box>

        {/* Autonomous Panels - Now self-positioning with configurable layouts */}
        {/* Remote/Desktop Panel - follows RecHostStreamModal pattern */}
        {showRemotePanel && selectedHost && selectedDeviceId && isControlActive && (() => {
          const selectedDevice = selectedHost.devices?.find((d) => d.device_id === selectedDeviceId);
          const isDesktopDevice = selectedDevice?.device_model === 'host_vnc';
          const remoteCapability = selectedDevice?.device_capabilities?.remote;
          const hasMultipleRemotes = Array.isArray(remoteCapability) || selectedDevice?.device_model === 'fire_tv';
          
          if (isDesktopDevice) {
            // For desktop devices, render both DesktopPanel and WebPanel together
            return (
              <>
                <DesktopPanel
                  host={selectedHost}
                  deviceId={selectedDeviceId}
                  deviceModel={selectedDevice?.device_model || 'host_vnc'}
                  isConnected={isControlActive}
                  onReleaseControl={handleDisconnectComplete}
                  initialCollapsed={true}
                />
                <WebPanel
                  host={selectedHost}
                  deviceId={selectedDeviceId}
                  deviceModel={selectedDevice?.device_model || 'host_vnc'}
                  isConnected={isControlActive}
                  onReleaseControl={handleDisconnectComplete}
                  initialCollapsed={true}
                />
              </>
            );
          } else if (hasMultipleRemotes && selectedDevice?.device_model === 'fire_tv') {
            // For Fire TV devices, render both AndroidTvRemote and InfraredRemote side by side
            return (
              <Box
                sx={{
                  display: 'flex',
                  flexDirection: 'row',
                  gap: 2,
                  position: 'absolute',
                  right: 20,
                  top: 100,
                  zIndex: 1000,
                  height: 'auto',
                }}
              >
                <RemotePanel
                  host={selectedHost}
                  deviceId={selectedDeviceId}
                  deviceModel={selectedDevice?.device_model || 'fire_tv'}
                  remoteType="android_tv"
                  isConnected={isControlActive}
                  onReleaseControl={handleDisconnectComplete}
                  deviceResolution={DEFAULT_DEVICE_RESOLUTION}
                  streamCollapsed={isAVPanelCollapsed}
                  streamMinimized={false}
                  streamHidden={showAVPanel} // Hide overlay when AV panel is active (screenshot/video mode)
                  captureMode="stream"
                  initialCollapsed={true}
                />
                <RemotePanel
                  host={selectedHost}
                  deviceId={selectedDeviceId}
                  deviceModel={selectedDevice?.device_model || 'fire_tv'}
                  remoteType="ir_remote"
                  isConnected={isControlActive}
                  onReleaseControl={handleDisconnectComplete}
                  deviceResolution={DEFAULT_DEVICE_RESOLUTION}
                  streamCollapsed={isAVPanelCollapsed}
                  streamMinimized={false}
                  streamHidden={showAVPanel} // Hide overlay when AV panel is active (screenshot/video mode)
                  captureMode="stream"
                  initialCollapsed={true}
                />
              </Box>
            );
          } else if (hasMultipleRemotes) {
            // For other devices with multiple remote controllers - render side by side
            const remoteTypes = Array.isArray(remoteCapability) ? remoteCapability : [remoteCapability];
            return (
              <Box
                sx={{
                  display: 'flex',
                  flexDirection: 'row',
                  gap: 2,
                  position: 'absolute',
                  right: 20,
                  top: 100,
                  zIndex: 1000,
                  height: 'auto',
                }}
              >
                {remoteTypes.filter(Boolean).map((remoteType: string, index: number) => (
                  <RemotePanel
                    key={`${selectedDeviceId}-${remoteType}`}
                    host={selectedHost}
                    deviceId={selectedDeviceId}
                    deviceModel={selectedDevice?.device_model || 'unknown'}
                    remoteType={remoteType}
                    isConnected={isControlActive}
                    onReleaseControl={handleDisconnectComplete}
                    deviceResolution={DEFAULT_DEVICE_RESOLUTION}
                    streamCollapsed={isAVPanelCollapsed}
                    streamMinimized={false}
                    captureMode="stream"
                    initialCollapsed={index > 0}
                  />
                ))}
              </Box>
            );
          } else {
            // For single remote devices, render only one RemotePanel
            return (
              <RemotePanel
                host={selectedHost}
                deviceId={selectedDeviceId}
                deviceModel={selectedDevice?.device_model || 'unknown'}
                isConnected={isControlActive}
                onReleaseControl={handleDisconnectComplete}
                deviceResolution={DEFAULT_DEVICE_RESOLUTION}
                streamCollapsed={isAVPanelCollapsed}
                streamMinimized={isAVPanelMinimized}
                captureMode={captureMode}
                isVerificationVisible={isVerificationVisible}
                isNavigationEditorContext={true}
              />
            );
          }
        })()}

        {/* AV Panel - device-specific stream rendering */}
        {showAVPanel && selectedHost && selectedDeviceId && (() => {
          const selectedDevice = selectedHost.devices?.find((d) => d.device_id === selectedDeviceId);
          const deviceModel = selectedDevice?.device_model;
          
          if (deviceModel === 'host_vnc') {
            return (
              <VNCStream
                host={selectedHost}
                deviceId={selectedDeviceId}
                deviceModel={deviceModel}
                isControlActive={isControlActive}
                onCollapsedChange={handleAVPanelCollapsedChange}
                onMinimizedChange={handleAVPanelMinimizedChange}
                onCaptureModeChange={handleCaptureModeChange}
              />
            );
          } else {
            return (
              <HDMIStream
                host={selectedHost}
                deviceId={selectedDeviceId}
                deviceModel={deviceModel}
                isControlActive={isControlActive}
                onCollapsedChange={handleAVPanelCollapsedChange}
                onMinimizedChange={handleAVPanelMinimizedChange}
                onCaptureModeChange={handleCaptureModeChange}
                deviceResolution={DEFAULT_DEVICE_RESOLUTION}
              />
            );
          }
        })()}

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
            setEdgeForm={setEdgeForm as any}
                            onSubmit={saveEdgeWithStateUpdate}
            onClose={() => setIsEdgeDialogOpen(false)}
            selectedEdge={selectedEdge}
            isControlActive={isControlActive}
            selectedHost={selectedHost}
            fromLabel={edgeLabels.fromLabel}
            toLabel={edgeLabels.toLabel}
          />
        )}

        {/* AI Generation Modal - Only when control active */}
        {isAIGenerationOpen && isControlActive && selectedHost && selectedDeviceId && actualTreeId && (
          <AIGenerationModal
            isOpen={isAIGenerationOpen}
            onClose={() => setIsAIGenerationOpen(false)}
            treeId={actualTreeId}
            selectedHost={selectedHost}
            selectedDeviceId={selectedDeviceId}
            onGenerated={handleAIGenerated}
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

        {/* Metrics Notification */}
        <MetricsNotification
          notificationData={metricsHook.notificationData}
          onViewDetails={handleOpenMetricsModal}
          onClose={handleCloseMetricsNotification}
        />

        {/* Metrics Modal */}
        <MetricsModal
          open={showMetricsModal}
          onClose={handleCloseMetricsModal}
          lowConfidenceItems={metricsHook.lowConfidenceItems}
          globalConfidence={metricsHook.globalConfidence}
          onRefreshMetrics={metricsHook.refreshMetrics}
          isLoading={metricsHook.isLoading}
        />

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
};

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
