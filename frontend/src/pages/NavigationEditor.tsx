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

// Auto-layout utility
import { getLayoutedElements } from '../components/testcase/ai/autoLayout';

// Import extracted components and hooks
import { RemotePanel } from '../components/controller/remote/RemotePanel';
import { DesktopPanel } from '../components/controller/desktop/DesktopPanel';
import { WebPanel } from '../components/controller/web/WebPanel';
import { VNCStream } from '../components/controller/av/VNCStream';
import { HDMIStream } from '../components/controller/av/HDMIStream';
import { ConfirmDialog } from '../components/common/ConfirmDialog';
import { NavigationBreadcrumbCompact } from '../components/navigation/NavigationBreadcrumbCompact';
import { EdgeEditDialog } from '../components/navigation/Navigation_EdgeEditDialog';
import { AIGenerationModal } from '../components/navigation/AIGenerationModal';
import { ValidationReadyPrompt } from '../components/navigation/ValidationReadyPrompt';
import { ValidationModal } from '../components/navigation/ValidationModal';
import { EdgeSelectionPanel } from '../components/navigation/Navigation_EdgeSelectionPanel';
import { MetricsNotification } from '../components/navigation/MetricsNotification';
import { MetricsModal } from '../components/navigation/MetricsModal';
import { NavigationEditorHeader } from '../components/navigation/Navigation_EditorHeader';
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
import { NavigationPreviewCacheProvider } from '../contexts/navigation/NavigationPreviewCacheContext';
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
import { useDeviceCompatibilityGuard } from '../hooks/navigation/useDeviceCompatibilityGuard';
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
  menu: UINavigationNode,
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
      loadTreeData,

      // Confirmation dialog state and handlers
      confirmDialogState,
      confirmDialogHandleConfirm,
      confirmDialogHandleCancel,
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

    // Mobile orientation state for coordinating video aspect ratio
    const [isMobileOrientationLandscape, setIsMobileOrientationLandscape] = useState(false);

    // Calculate verification editor visibility based on capture mode (same logic as AV components)
    const isVerificationVisible = captureMode === 'screenshot' || captureMode === 'video';

    // Goto panel state
    const [showGotoPanel, setShowGotoPanel] = useState(false);
    const [selectedNodeForGoto, setSelectedNodeForGoto] = useState<UINavigationNodeType | null>(
      null,
    );

    // AI Generation modal state
    const [isAIGenerationOpen, setIsAIGenerationOpen] = useState(false);
    
    // Validation Ready Prompt state
    const [showValidationPrompt, setShowValidationPrompt] = useState(false);
    const [validationNodesCount, setValidationNodesCount] = useState(0);
    const [validationEdgesCount, setValidationEdgesCount] = useState(0);
    const [explorationId, setExplorationId] = useState<string | null>(null);
    const [explorationHostName, setExplorationHostName] = useState<string | null>(null);
    
    // Validation Modal state
    const [isValidationModalOpen, setIsValidationModalOpen] = useState(false);
    const [applyAutoLayoutFlag, setApplyAutoLayoutFlag] = useState(false);

    // Metrics state
    const [showMetricsModal, setShowMetricsModal] = useState(false);

    // Modifier key state for conditional edge creation
    const [isShiftHeld, setIsShiftHeld] = useState(false);

    // Keyboard event listeners for modifier keys
    useEffect(() => {
      const handleKeyDown = (e: KeyboardEvent) => {
        // Check if user is focused on an input field (TextField, textarea, contenteditable)
        const target = e.target as HTMLElement;
        const isInputField = 
          target.tagName === 'INPUT' || 
          target.tagName === 'TEXTAREA' || 
          target.isContentEditable ||
          target.closest('input') !== null ||
          target.closest('textarea') !== null;
        
        if (e.shiftKey) {
          setIsShiftHeld(true);
        }
        
        // DELETE/BACKSPACE key - delete selected node/edge with protection
        if ((e.key === 'Delete' || e.key === 'Backspace') && !isInputField) {
          e.preventDefault();
          deleteSelected();
        }
        
        // Undo/Redo shortcuts - only when NOT in input fields
        if ((e.ctrlKey || e.metaKey) && !e.shiftKey && e.key === 'z' && !isInputField) {
          e.preventDefault();
          navigation.undo();
        }
        if ((e.ctrlKey || e.metaKey) && (e.shiftKey && e.key === 'z' || e.key === 'y') && !isInputField) {
          e.preventDefault();
          navigation.redo();
        }
        
        // Copy/Paste shortcuts - only when NOT in input fields (allow normal text copy/paste)
        if ((e.ctrlKey || e.metaKey) && e.key === 'c' && !isInputField) {
          e.preventDefault();
          navigation.copyNode();
        }
        if ((e.ctrlKey || e.metaKey) && e.key === 'v' && !isInputField) {
          e.preventDefault();
          navigation.pasteNode();
        }
      };

      const handleKeyUp = (e: KeyboardEvent) => {
        if (!e.shiftKey) {
          setIsShiftHeld(false);
        }
      };

      window.addEventListener('keydown', handleKeyDown);
      window.addEventListener('keyup', handleKeyUp);

      return () => {
        window.removeEventListener('keydown', handleKeyDown);
        window.removeEventListener('keyup', handleKeyUp);
      };
    }, [deleteSelected, navigation]);

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
            // CRITICAL: Invalidate cache FIRST to force fresh fetch from DB
            // This ensures we see the newly created _temp nodes immediately
            console.log('[@NavigationEditor:handleAIGenerated] 🗑️ Invalidating cache for interface:', userInterface.id);
            navigationConfig.invalidateTreeCache(userInterface.id);
            
            // Re-fetch tree data after AI generation using navigation hook
            console.log('[@NavigationEditor:handleAIGenerated] 🔄 Force-refreshing tree after AI structure creation');
            console.log('[@NavigationEditor:handleAIGenerated] Current tree ID:', actualTreeId);
            console.log('[@NavigationEditor:handleAIGenerated] Is subtree:', navigation.parentChain.length > 0);
            
            try {
              // ✅ FIX: If in subtree, stay in subtree instead of jumping to root!
              if (navigation.parentChain.length > 0 && actualTreeId) {
                // We're in a subtree - reload the root tree BUT stay in the current subtree context
                console.log('[@NavigationEditor:handleAIGenerated] Reloading tree while preserving SUBTREE context');
                console.log('[@NavigationEditor:handleAIGenerated] Current subtree:', actualTreeId);
                console.log('[@NavigationEditor:handleAIGenerated] Parent chain length:', navigation.parentChain.length);
                
                // Reload the root tree (to get updated data) but don't navigate away from subtree
                const result = await loadTreeByUserInterface(userInterface.id);
                
                if (result?.metrics) {
                  console.log('[@NavigationEditor] Capturing preloaded metrics from tree load');
                  setPreloadedMetrics(result.metrics);
                }
                
                // Parent chain is preserved by NavigationContext - we won't be redirected
                console.log('[@NavigationEditor:handleAIGenerated] ✅ Tree reloaded, staying in subtree');
              } else {
                // We're in root tree - reload by userInterface as usual
                console.log('[@NavigationEditor:handleAIGenerated] Reloading ROOT tree by userInterface');
                const result = await loadTreeByUserInterface(userInterface.id);
                
                if (result?.metrics) {
                  console.log('[@NavigationEditor] Capturing preloaded metrics from tree load');
                  setPreloadedMetrics(result.metrics);
                }
              }
              
              // ✅ Apply auto-layout after nodes are loaded
              // Note: We'll trigger this via a flag instead of calling handleAutoLayout directly
              // to avoid circular dependency issues
              setApplyAutoLayoutFlag(true);
              
            } catch (error) {
              console.error('Failed to refresh tree data after AI generation:', error);
            }
          }
        } catch (error) {
          console.error('[@NavigationEditor:handleAIGenerated] Failed to refresh tree data:', error);
        }
      };
      refreshData();
    }, [userInterface?.id, loadTreeByUserInterface, navigationConfig]);

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

    // Wrap onConnect to pass modifier key state for conditional edges
    const wrappedOnConnect = useCallback(
      (connection: any) => {
        // Pass isConditional flag based on Shift key state
        const enhancedConnection = {
          ...connection,
          isConditional: isShiftHeld, // Hold Shift to create conditional edge (BLUE, shared actions)
        };
        
        if (isShiftHeld) {
          console.log('[@NavigationEditor] 🔷 Creating CONDITIONAL edge (Shift held) - will share actions with siblings');
        } else {
          console.log('[@NavigationEditor] ⚪ Creating REGULAR edge - unique action sets');
        }
        
        onConnect(enhancedConnection);
      },
      [onConnect, isShiftHeld]
    );

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

    // Handle mobile orientation changes
    const handleMobileOrientationChange = useCallback((isLandscape: boolean) => {
      setIsMobileOrientationLandscape(isLandscape);
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
    const handleNavigateBack = useCallback(async () => {
      if (navigation.parentChain.length <= 1) {
        console.log('[@NavigationEditor] Already at root, cannot go back');
        return;
      }
      
      // Auto-save before navigating if there are unsaved changes
      if (hasUnsavedChanges && actualTreeId) {
        console.log('[@NavigationEditor] Auto-saving before navigating back to parent tree');
        try {
          await saveTreeWithStateUpdate(actualTreeId);
          console.log('[@NavigationEditor] Auto-save successful');
        } catch (error) {
          console.error('[@NavigationEditor] Auto-save failed:', error);
          // Continue navigation even if save fails - user can manually save later
        }
      }
      
      navigation.popFromParentChain();
      popLevel();
      
      const parent = navigation.parentChain[navigation.parentChain.length - 2];
      if (parent) {
        setActualTreeId(parent.treeId);
      }
    }, [navigation, popLevel, setActualTreeId, hasUnsavedChanges, saveTreeWithStateUpdate, actualTreeId]);

    // Handle navigation to specific level in breadcrumb
    const handleNavigateToLevel = useCallback(
      async (levelIndex: number) => {
        if (levelIndex >= navigation.parentChain.length) {
          console.log('[@NavigationEditor] Invalid level index');
          return;
        }
        
        // Auto-save before navigating if there are unsaved changes
        if (hasUnsavedChanges && actualTreeId) {
          console.log('[@NavigationEditor] Auto-saving before navigating to level', levelIndex);
          try {
            await saveTreeWithStateUpdate(actualTreeId);
            console.log('[@NavigationEditor] Auto-save successful');
          } catch (error) {
            console.error('[@NavigationEditor] Auto-save failed:', error);
            // Continue navigation even if save fails - user can manually save later
          }
        }
        
        const newChain = navigation.parentChain.slice(0, levelIndex + 1);
        const target = newChain[newChain.length - 1];
        
        navigation.setNodes(target.nodes);
        navigation.setEdges(target.edges);
        navigation.setParentChain(newChain);
        
        jumpToLevel(levelIndex);
        setActualTreeId(target.treeId);
      },
      [navigation, jumpToLevel, setActualTreeId, hasUnsavedChanges, saveTreeWithStateUpdate, actualTreeId],
    );

    // Handle navigation to root
    const handleNavigateToRoot = useCallback(async () => {
      if (navigation.parentChain.length === 0) {
        console.log('[@NavigationEditor] No root tree in parent chain');
        return;
      }
      
      // Auto-save before navigating if there are unsaved changes
      if (hasUnsavedChanges && actualTreeId) {
        console.log('[@NavigationEditor] Auto-saving before navigating to root');
        try {
          await saveTreeWithStateUpdate(actualTreeId);
          console.log('[@NavigationEditor] Auto-save successful');
        } catch (error) {
          console.error('[@NavigationEditor] Auto-save failed:', error);
          // Continue navigation even if save fails - user can manually save later
        }
      }
      
      navigation.resetToRoot();
      jumpToRoot();
      
      const root = navigation.parentChain[0];
      setActualTreeId(root.treeId);
    }, [navigation, jumpToRoot, setActualTreeId, hasUnsavedChanges, saveTreeWithStateUpdate, actualTreeId]);

    // Memoize the selectedHost to prevent unnecessary re-renders
    const stableSelectedHost = useMemo(() => selectedHost, [selectedHost]);

    // Centralized reference management - both verification references and actions
    const { setControlState, setUserinterfaceName } = useDeviceData();

    // Set control state in device data context when it changes
    useEffect(() => {
      setControlState(stableSelectedHost, selectedDeviceId, isControlActive);
    }, [stableSelectedHost, selectedDeviceId, isControlActive, setControlState]);

    // Set userinterface name for optimal reference filtering
    useEffect(() => {
      if (userInterface?.name) {
        console.log('[@NavigationEditor] Setting userinterface name for optimal filtering:', userInterface.name);
        setUserinterfaceName(userInterface.name);
      }
      return () => {
        // Clear on unmount
        setUserinterfaceName(null);
      };
    }, [userInterface?.name, setUserinterfaceName]);

    // Auto-guard against incompatible device selections when userInterface changes
    useDeviceCompatibilityGuard({
      userInterface,
      selectedHost,
      selectedDeviceId,
      isControlActive,
      onReleaseControl: handleDisconnectComplete,
      onClearSelection: () => handleDeviceSelect(null, null),
    });

    // Focus node view handler - pan/zoom to focused node when selected
    useEffect(() => {
      if (focusNodeId && nodes.length > 0 && navigation.reactFlowInstance) {
        // Find the focused node in the current nodes array
        const focusedNode = nodes.find((node) => node.id === focusNodeId);
        
        if (focusedNode) {
          console.log(`[@NavigationEditor] Focusing view on node: ${focusedNode.data.label || focusNodeId}`);
          
          // Center the view on the focused node with smooth animation
          // Calculate center position (React Flow nodes may have width/height as optional properties)
          const nodeWidth = (focusedNode as any).width || 200;
          const nodeHeight = (focusedNode as any).height || 100;
          
          setTimeout(() => {
            navigation.reactFlowInstance?.setCenter(
              focusedNode.position.x + nodeWidth / 2,
              focusedNode.position.y + nodeHeight / 2,
              { zoom: 1.2, duration: 800 }
            );
          }, 100);
        } else {
          console.warn(`[@NavigationEditor] Focused node ${focusNodeId} not found in current nodes`);
        }
      }
    }, [focusNodeId, nodes, navigation.reactFlowInstance]);

    // ========================================
    // 1. INITIALIZATION & REFERENCES
    // ========================================

    // Unified save function - works for both root and nested trees
    const handleSaveToConfig = useCallback(
      async () => {
        try {
          const treeType = isNested && currentLevel ? 'nested' : 'root';
          const contextInfo = navigation.parentChain.length > 0 
            ? `(subtree depth: ${navigation.parentChain.length})` 
            : '(root level)';
          
          console.log(`[@NavigationEditor] 💾 Saving ${treeType} tree: ${actualTreeId} ${contextInfo}`);
          console.log(`[@NavigationEditor] 💾 Tree contains: ${nodes.length} nodes, ${edges.length} edges`);
          
          // All tree saves now use the same unified batch API - saves to actualTreeId (current tree context)
          await saveTreeWithStateUpdate(actualTreeId!);
          
          console.log(`[@NavigationEditor] ✅ ${treeType} tree saved successfully: ${actualTreeId}`);
        } catch (error) {
          console.error('Error saving tree:', error);
          throw error;
        }
      },
      [isNested, currentLevel, actualTreeId, nodes.length, edges.length, saveTreeWithStateUpdate, navigation.parentChain.length],
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
        
        if (isNested && navigation.parentChain.some(t => t.treeId === userInterface.id)) {
          console.log(`[@component:NavigationEditor] Tree already in parent chain: ${userInterface.id}`);
          lastLoadedTreeId.current = userInterface.id;
          return;
        }
        
        lastLoadedTreeId.current = userInterface.id;

        console.log(`[@component:NavigationEditor] Loading tree for userInterface: ${userInterface.id}`);
        loadTreeForUserInterface(userInterface.id).then((result: any) => {
          if (result?.tree?.id && !isNested && stack.length === 0) {
            const actualTreeUuid = result.tree.id;
            setActualTreeId(actualTreeUuid);
          }
        }).catch((error: any) => {
          console.error(`[@component:NavigationEditor] Failed to load tree:`, error);
        });

        // No auto-unlock for navigation tree - keep it locked for editing session
      }
    }, [userInterface?.id, isLoadingInterface, loadTreeForUserInterface, navigation, isNested, stack.length, setActualTreeId]);

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

    // Auto-layout handler - vertical layout (top to bottom)
    const handleAutoLayout = useCallback(() => {
      const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
        nodes as any,
        edges as any,
        { direction: 'TB' } // Top to Bottom
      );
      setNodes(layoutedNodes as any);
      setEdges(layoutedEdges as any);
      setHasUnsavedChanges(true);
      
      // Fit view after layout
      if (navigation.reactFlowInstance) {
        setTimeout(() => {
          navigation.reactFlowInstance?.fitView({ padding: 0.2, duration: 300 });
        }, 100);
      }
    }, [nodes, edges, setNodes, setEdges, setHasUnsavedChanges, navigation.reactFlowInstance]);

    // Effect to trigger auto-layout after AI generation
    useEffect(() => {
      if (applyAutoLayoutFlag && nodes.length > 0 && actualTreeId) {
        const treeType = navigation.parentChain.length > 0 ? 'subtree' : 'root tree';
        const treeInfo = navigation.parentChain.length > 0 
          ? `subtree (${actualTreeId}, depth: ${navigation.parentChain.length})` 
          : `root tree (${actualTreeId})`;
        
        console.log(`[@NavigationEditor] 🎨 Triggering auto-layout after AI generation for ${treeInfo}`);
        console.log(`[@NavigationEditor] 🎨 Layout will be applied to ${nodes.length} nodes and ${edges.length} edges`);
        
        setTimeout(() => {
          handleAutoLayout();
          setApplyAutoLayoutFlag(false); // Reset flag
          
          // Auto-save after layout is applied to the CURRENT tree (root or subtree)
          console.log(`[@NavigationEditor] 💾 Auto-saving ${treeType} after layout to tree: ${actualTreeId}`);
          setTimeout(() => {
            if (!actualTreeId) {
              console.error(`[@NavigationEditor] ❌ Cannot save - actualTreeId is undefined!`);
              return;
            }
            
            handleSaveToConfig()
              .then(() => {
                console.log(`[@NavigationEditor] ✅ Auto-save completed for ${treeType}: ${actualTreeId}`);
              })
              .catch((error) => {
                console.error(`[@NavigationEditor] ❌ Auto-save failed for ${treeType}:`, error);
              });
          }, 2000); // Wait 2s to ensure layout positions are fully applied to ReactFlow
        }, 1000); // Small delay to ensure nodes are rendered
      } else if (applyAutoLayoutFlag && !actualTreeId) {
        console.error('[@NavigationEditor] ❌ Cannot apply auto-layout - actualTreeId is undefined!');
        setApplyAutoLayoutFlag(false);
      }
    }, [applyAutoLayoutFlag, nodes.length, edges.length, handleAutoLayout, handleSaveToConfig, actualTreeId, navigation.parentChain.length]);

    // Wrap onNodesChange to track position changes as unsaved changes
    const wrappedOnNodesChange = useCallback(
      (changes: any) => {
        onNodesChange(changes);
        // Check if any change is a position change
        const hasPositionChange = changes.some((change: any) => change.type === 'position' && change.dragging === false);
        if (hasPositionChange) {
          console.log('[@NavigationEditor] Node position changed:', changes.filter((c: any) => c.type === 'position'));
          setHasUnsavedChanges(true);
        }
      },
      [onNodesChange, setHasUnsavedChanges]
    );

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
          position: 'fixed',
          top: 64,
          left: 0,
          right: 0,
          bottom: 32, // Leave space for shared Footer (minHeight 24 + py 8 = 32px)
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
            overflow: 'hidden',
          }}
        >
          {/* Main Editor Area */}
          <Box
            sx={{
              flex: 1,
              position: 'relative',
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
                  onNodesChange={wrappedOnNodesChange}
                  onEdgesChange={onEdgesChange}
                  onConnect={wrappedOnConnect}
                  onNodeClick={wrappedOnNodeClick}
                  onEdgeClick={wrappedOnEdgeClick}
                  onNodeDoubleClick={nestedNavigation.handleNodeDoubleClick}
                  onPaneClick={wrappedOnPaneClick}
                  deleteKeyCode={null}
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
                  connectionRadius={50}
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
                  
                  {/* Auto Layout Button - matching TestCaseBuilder positioning */}
                  <button
                    onClick={handleAutoLayout}
                    title="Auto Layout"
                    style={{
                      position: 'absolute',
                      top: '124px',
                      left: '15px',
                      width: '26px',
                      height: '26px',
                      padding: '0',
                      background: '#ffffff',
                      border: `0px solid ${actualMode === 'dark' ? '#334155' : '#e2e8f0'}`,
                      borderRadius: '0',
                      cursor: 'pointer',
                      fontSize: '16px',
                      color: '#000000',
                      zIndex: 5,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      boxShadow: 'rgba(0, 0, 0, 0.1) 0px 0px 0px 1px',
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.background = '#f1f5f9';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = '#ffffff';
                    }}
                  >
                    <svg 
                      width="16" 
                      height="16" 
                      viewBox="0 0 24 24" 
                      fill="none" 
                      stroke="currentColor" 
                      strokeWidth="2"
                      strokeLinecap="round" 
                      strokeLinejoin="round"
                    >
                      {/* Grid layout icon */}
                      <rect x="3" y="3" width="7" height="7" />
                      <rect x="14" y="3" width="7" height="7" />
                      <rect x="14" y="14" width="7" height="7" />
                      <rect x="3" y="14" width="7" height="7" />
                    </svg>
                  </button>
                  
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
                                  key={`${edge.id}-${actionSet.id}-${panelIndexOffset + actionSetIndex}`}
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
                onOrientationChange={handleMobileOrientationChange}
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
                userinterfaceName={treeName} // Use treeName directly from URL (always available, no race condition)
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
                userinterfaceName={treeName} // Use treeName directly from URL (always available, no race condition)
                onCollapsedChange={handleAVPanelCollapsedChange}
                onMinimizedChange={handleAVPanelMinimizedChange}
                onCaptureModeChange={handleCaptureModeChange}
                deviceResolution={DEFAULT_DEVICE_RESOLUTION}
                isLandscape={isMobileOrientationLandscape}
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
            onUpdateNode={handleUpdateNode}
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
            selectedDeviceId={selectedDeviceId}
            fromLabel={edgeLabels.fromLabel}
            toLabel={edgeLabels.toLabel}
            model={userInterface?.models?.[0] || 'android_mobile'}
          />
        )}

        {/* AI Generation Modal - Only mount when user opens it or validation prompt is active */}
        {(isAIGenerationOpen || showValidationPrompt) && isControlActive && selectedHost && selectedDeviceId && actualTreeId && (
          <AIGenerationModal
            isOpen={isAIGenerationOpen}
            onClose={() => setIsAIGenerationOpen(false)}
            treeId={actualTreeId}
            selectedHost={selectedHost}
            selectedDeviceId={selectedDeviceId}
            userinterfaceName={userInterface?.name}
            onStructureCreated={async (nodesCount, edgesCount, explId, explHostName) => {
              // Show ValidationReadyPrompt after structure creation
              setValidationNodesCount(nodesCount);
              setValidationEdgesCount(edgesCount);
              setExplorationId(explId);
              setExplorationHostName(explHostName);
              setShowValidationPrompt(true);
              
              // ✅ CRITICAL: Reload tree data BEFORE triggering auto-layout
              // This ensures the newly created nodes/edges are fetched and displayed
              const treeType = navigation.parentChain.length > 0 ? 'subtree' : 'root tree';
              const treeContext = navigation.parentChain.length > 0 
                ? `(subtree: ${actualTreeId}, depth: ${navigation.parentChain.length})` 
                : `(root tree: ${actualTreeId})`;
              
              console.log(`[@NavigationEditor] 🔄 Reloading ${treeType} data after structure creation ${treeContext}`);
              
              if (actualTreeId) {
                try {
                  // Invalidate cache to force fresh fetch
                  if (userInterface?.id) {
                    navigationConfig.invalidateTreeCache(userInterface.id);
                  }
                  
                  // ✅ Reload CURRENT tree (preserves subtree context if in subtree)
                  console.log(`[@NavigationEditor] 🔄 Loading tree: ${actualTreeId}`);
                  await loadTreeData(actualTreeId);
                  
                  console.log(`[@NavigationEditor] ✅ Tree data reloaded for ${treeType} - triggering auto-layout`);
                  
                  // Small delay to ensure React state has updated before triggering auto-layout
                  setTimeout(() => {
                    setApplyAutoLayoutFlag(true);
                  }, 100);
                } catch (error) {
                  console.error(`[@NavigationEditor] ❌ Failed to reload ${treeType} data:`, error);
                }
              } else {
                console.error('[@NavigationEditor] ❌ Cannot reload tree - actualTreeId is undefined!');
              }
            }}
            onFinalized={async () => {
              // ✅ Reload tree after finalize to show updated labels (removed _temp suffix)
              const treeType = navigation.parentChain.length > 0 ? 'subtree' : 'root tree';
              const treeContext = navigation.parentChain.length > 0 
                ? `(subtree: ${actualTreeId}, depth: ${navigation.parentChain.length})` 
                : `(root tree: ${actualTreeId})`;
              
              console.log(`[@NavigationEditor] 🔄 Reloading ${treeType} data after finalize ${treeContext}`);
              
              if (actualTreeId && userInterface?.id) {
                try {
                  navigationConfig.invalidateTreeCache(userInterface.id);
                  
                  // ✅ Reload CURRENT tree (preserves subtree context if in subtree)
                  await loadTreeData(actualTreeId);
                  
                  console.log(`[@NavigationEditor] ✅ Tree data reloaded for ${treeType} after finalize`);
                } catch (error) {
                  console.error(`[@NavigationEditor] ❌ Failed to reload ${treeType} after finalize:`, error);
                }
              }
            }}
            onCleanupTemp={() => {
              // Clean up _temp nodes from frontend state (match by label, not ID)
              const tempNodes = nodes.filter(node => node.data?.label?.endsWith('_temp'));
              const tempNodeIds = new Set(tempNodes.map(n => n.id));
              
              // Clean up edges connected to _temp nodes
              const tempEdges = edges.filter(edge => 
                tempNodeIds.has(edge.source) || tempNodeIds.has(edge.target)
              );
              
              if (tempNodes.length > 0 || tempEdges.length > 0) {
                console.log(`[@NavigationEditor] Cleaning up ${tempNodes.length} _temp nodes and ${tempEdges.length} edges from React Flow...`);
                
                // Remove edges first (to avoid orphaned edges)
                const remainingEdges = edges.filter(edge => 
                  !tempNodeIds.has(edge.source) && !tempNodeIds.has(edge.target)
                );
                setEdges(remainingEdges);
                
                // Remove nodes
                const remainingNodes = nodes.filter(node => !node.data?.label?.endsWith('_temp'));
                setNodes(remainingNodes);
                
                console.log(`[@NavigationEditor] ✅ Cleaned up ${tempNodes.length} _temp nodes and ${tempEdges.length} _temp edges from React Flow`);
              } else {
                console.log('[@NavigationEditor] No _temp nodes found to clean up');
              }
            }}
          />
        )}

        {/* Validation Ready Prompt - Show after structure creation */}
        {showValidationPrompt && (
          <ValidationReadyPrompt
            nodesCreated={validationNodesCount}
            edgesCreated={validationEdgesCount}
            onStartValidation={() => {
              console.log('[@NavigationEditor] Start validation clicked - opening ValidationModal');
              setShowValidationPrompt(false);
              setIsValidationModalOpen(true);
            }}
            onCancel={async () => {
              // Delete all _temp nodes/edges using frontend state
              console.log('[@NavigationEditor] Cancel validation - cleaning up _temp nodes');
              
              // Find all _temp nodes in current ReactFlow state
              const tempNodes = nodes.filter(node => node.id.endsWith('_temp'));
              const tempEdges = edges.filter(edge => edge.id.includes('_temp'));
              
              console.log(`[@NavigationEditor] Found ${tempNodes.length} _temp nodes and ${tempEdges.length} _temp edges to delete`);
              
              if (tempNodes.length > 0 || tempEdges.length > 0) {
                // Delete edges first
                const remainingEdges = edges.filter(edge => !edge.id.includes('_temp'));
                setEdges(remainingEdges);
                
                // Then delete nodes
                const remainingNodes = nodes.filter(node => !node.id.endsWith('_temp'));
                setNodes(remainingNodes);
                
                setHasUnsavedChanges(true);
                
                console.log(`[@NavigationEditor] Deleted ${tempNodes.length} nodes and ${tempEdges.length} edges from frontend state`);
                
                // Refresh to sync with backend
                handleAIGenerated();
              }
              
              setShowValidationPrompt(false);
            }}
          />
        )}

        {/* Validation Modal - Phase 2b: Validation */}
        {isValidationModalOpen && explorationId && explorationHostName && actualTreeId && selectedDeviceId && (
          <ValidationModal
            isOpen={isValidationModalOpen}
            onClose={() => {
              // Cancel button clicked - delete _temp nodes/edges
              console.log('[@NavigationEditor] User cancelled - deleting _temp nodes/edges');
              setIsValidationModalOpen(false);
              
              // Clean up _temp nodes from frontend state
              const tempNodes = nodes.filter(node => node.id.endsWith('_temp'));
              const tempEdges = edges.filter(edge => edge.id.includes('_temp'));
              
              if (tempNodes.length > 0 || tempEdges.length > 0) {
                const remainingEdges = edges.filter(edge => !edge.id.includes('_temp'));
                setEdges(remainingEdges);
                
                const remainingNodes = nodes.filter(node => !node.id.endsWith('_temp'));
                setNodes(remainingNodes);
                
                setHasUnsavedChanges(true);
                console.log(`[@NavigationEditor] Deleted ${tempNodes.length} _temp nodes and ${tempEdges.length} _temp edges`);
              }
              
              // Reset exploration state
              setExplorationId(null);
              setExplorationHostName(null);
              
              // Refresh to sync with backend
              handleAIGenerated();
            }}
            explorationId={explorationId}
            explorationHostName={explorationHostName}
            treeId={actualTreeId}
            selectedDeviceId={selectedDeviceId}
            onValidationStarted={() => {
              console.log('[@NavigationEditor] Validation started');
            }}
            onValidationComplete={async () => {
              // Confirm button clicked - rename _temp to permanent
              console.log('[@NavigationEditor] User confirmed - renaming _temp nodes/edges');
              
              // Call backend to rename _temp nodes/edges
              try {
                const response = await fetch(
                  buildServerUrl(`/server/ai-generation/finalize-structure`),
                  {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                      exploration_id: explorationId,
                      host_name: explorationHostName,
                      tree_id: actualTreeId
                    })
                  }
                );
                
                if (response.ok) {
                  console.log('[@NavigationEditor] Structure finalized - _temp suffix removed');
                } else {
                  console.error('[@NavigationEditor] Failed to finalize structure');
                }
              } catch (err) {
                console.error('[@NavigationEditor] Error finalizing structure:', err);
              }
              
              // ✅ FIX: Don't reload tree unnecessarily - just refresh cache
              // The nodes/edges were already renamed by backend, just invalidate cache
              console.log('[@NavigationEditor] Invalidating cache after finalization');
              navigationConfig.invalidateTreeCache(userInterface?.id);
              
              // Close modal
              setIsValidationModalOpen(false);
              
              // Reset exploration state
              setExplorationId(null);
              setExplorationHostName(null);
              
              // ✅ Show success message
              console.log('[@NavigationEditor] ✅ Validation complete - structure finalized');
            }}
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

        {/* Confirmation Dialog - replaces window.confirm */}
        <ConfirmDialog
          open={confirmDialogState.open}
          title={confirmDialogState.title}
          message={confirmDialogState.message}
          confirmText={confirmDialogState.confirmText}
          cancelText={confirmDialogState.cancelText}
          confirmColor={confirmDialogState.confirmColor}
          onConfirm={confirmDialogHandleConfirm}
          onCancel={confirmDialogHandleCancel}
        />
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
        <NavigationPreviewCacheProvider>
          <NavigationEditorProvider>
            <NavigationStackProvider>
              <NavigationEditorContent treeName={treeName} />
            </NavigationStackProvider>
          </NavigationEditorProvider>
        </NavigationPreviewCacheProvider>
      </NavigationConfigProvider>
    </ReactFlowProvider>
  );
};

export default NavigationEditor;
