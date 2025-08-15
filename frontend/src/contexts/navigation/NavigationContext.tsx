import React, {
  createContext,
  useState,
  useRef,
  useCallback,
  useMemo,
  useEffect,
  useContext,
} from 'react';
import { useParams } from 'react-router-dom';
import { useNodesState, useEdgesState, ReactFlowInstance } from 'reactflow';

import {
  UINavigationNode,
  UINavigationEdge,
  NodeForm,
  EdgeForm,
} from '../../types/pages/Navigation_Types';
import { useDeviceData } from '../device/DeviceDataContext';
import { useNavigationConfig } from './NavigationConfigContext';

// ========================================
// TYPES
// ========================================

export interface NavigationContextType {
  // Route params
  treeId?: string;
  treeName?: string;
  interfaceId?: string;

  // Navigation state
  currentTreeId: string;
  setCurrentTreeId: (id: string) => void;
  currentTreeName: string;
  setCurrentTreeName: (name: string) => void;
  navigationPath: string[];
  setNavigationPath: (path: string[]) => void;
  navigationNamePath: string[];
  setNavigationNamePath: (path: string[]) => void;

  // Current position tracking
  currentNodeId: string | null;
  setCurrentNodeId: (id: string | null) => void;
  currentNodeLabel: string | null;
  setCurrentNodeLabel: (label: string | null) => void;

  // Tree cache management
  cacheTree: (treeId: string, treeData: { nodes: UINavigationNode[], edges: UINavigationEdge[] }) => void;
  getCachedTree: (treeId: string) => { nodes: UINavigationNode[], edges: UINavigationEdge[] } | null;
  switchToTree: (treeId: string) => void;
  cacheAndSwitchToTree: (treeId: string, treeData: { nodes: UINavigationNode[], edges: UINavigationEdge[] }) => void;
  
  // Root tree tracking for breadcrumb navigation
  rootTreeId: string | null;
  setRootTreeId: (treeId: string | null) => void;
  
  // React Flow state - displays active tree from cache
  nodes: UINavigationNode[];
  setNodes: (nodes: UINavigationNode[]) => void;
  onNodesChange: (changes: any[]) => void;
  edges: UINavigationEdge[];
  setEdges: (edges: UINavigationEdge[]) => void;
  onEdgesChange: (changes: any[]) => void;

  // Selection state
  selectedNode: UINavigationNode | null;
  setSelectedNode: (node: UINavigationNode | null) => void;
  selectedEdge: UINavigationEdge | null;
  setSelectedEdge: (edge: UINavigationEdge | null) => void;

  // Dialog states
  isNodeDialogOpen: boolean;
  setIsNodeDialogOpen: (open: boolean) => void;
  isEdgeDialogOpen: boolean;
  setIsEdgeDialogOpen: (open: boolean) => void;
  isDiscardDialogOpen: boolean;
  setIsDiscardDialogOpen: (open: boolean) => void;

  // Form states
  isNewNode: boolean;
  setIsNewNode: (isNew: boolean) => void;
  nodeForm: NodeForm;
  setNodeForm: (form: NodeForm) => void;
  edgeForm: EdgeForm;
  setEdgeForm: (form: EdgeForm) => void;
  edgeLabels: {fromLabel: string, toLabel: string};
  setEdgeLabels: (labels: {fromLabel: string, toLabel: string}) => void;

  // Loading and error states
  isLoading: boolean;
  setIsLoading: (loading: boolean) => void;
  error: string | null;
  setError: (error: string | null) => void;
  success: string | null;
  setSuccess: (success: string | null) => void;

  // Save states
  isSaving: boolean;
  setIsSaving: (saving: boolean) => void;
  saveError: string | null;
  setSaveError: (error: string | null) => void;
  saveSuccess: boolean;
  setSaveSuccess: (success: boolean) => void;
  hasUnsavedChanges: boolean;
  setHasUnsavedChanges: (hasChanges: boolean) => void;

  // Lock states
  isLocked: boolean;
  setIsLocked: (locked: boolean) => void;
  isCheckingLock: boolean;
  setIsCheckingLock: (checking: boolean) => void;

  // Interface state
  userInterface: any;
  setUserInterface: (ui: any) => void;
  rootTree: any;
  setRootTree: (tree: any) => void;
  isLoadingInterface: boolean;
  setIsLoadingInterface: (loading: boolean) => void;

  // View state
  currentViewRootId: string | null;
  setCurrentViewRootId: (id: string | null) => void;
  viewPath: { id: string; name: string }[];
  setViewPath: (path: { id: string; name: string }[]) => void;

  // Filtering state
  focusNodeId: string | null;
  setFocusNodeId: (id: string | null) => void;
  maxDisplayDepth: number;
  setMaxDisplayDepth: (depth: number) => void;
  availableFocusNodes: { id: string; label: string; depth: number }[];
  setAvailableFocusNodes: (nodes: { id: string; label: string; depth: number }[]) => void;

  // History state
  initialState: { nodes: UINavigationNode[]; edges: UINavigationEdge[] } | null;
  setInitialState: (state: { nodes: UINavigationNode[]; edges: UINavigationEdge[] } | null) => void;

  // React Flow refs
  reactFlowWrapper: React.RefObject<HTMLDivElement>;
  reactFlowInstance: ReactFlowInstance | null;
  setReactFlowInstance: (instance: ReactFlowInstance | null) => void;
  pendingViewport: { x: number; y: number; zoom: number } | null;
  setPendingViewport: (viewport: { x: number; y: number; zoom: number } | null) => void;

  // Action methods
  resetAll: () => void;
  resetSelection: () => void;
  resetToInitialState: () => void;
  resetForms: () => void;
  resetDialogs: () => void;
  openNodeDialog: (node?: UINavigationNode) => void;
  openEdgeDialog: (edge?: UINavigationEdge) => void;
  closeAllDialogs: () => void;
  markUnsavedChanges: () => void;
  clearUnsavedChanges: () => void;
  resetToHome: () => void;
  fitViewToNodes: () => void;
  validateNavigationPath: (path: string[]) => boolean;
  updateNavigationPath: (newPath: string[], newNamePath: string[]) => void;
  updateCurrentPosition: (nodeId: string | null, nodeLabel?: string | null) => void;
  updateNodesWithMinimapIndicators: (navigationSteps?: any[]) => void;

  // Lock methods
  lockNavigationTree: (treeId: string) => Promise<boolean>;
  unlockNavigationTree: (treeId: string) => Promise<boolean>;

  // Centralized save methods
  saveNodeWithStateUpdate: (nodeForm: any) => Promise<void>;
  saveEdgeWithStateUpdate: (edgeForm: any) => Promise<void>;
  saveTreeWithStateUpdate: (treeId: string) => Promise<void>;
  executeActionsWithPositionUpdate: (actions: any[], retryActions: any[], failureActions?: any[], targetNodeId?: string) => Promise<any>;
}

interface NavigationProviderProps {
  children: React.ReactNode;
}

// ========================================
// CONTEXT
// ========================================

const NavigationContext = createContext<NavigationContextType | null>(null);

export const NavigationProvider: React.FC<NavigationProviderProps> = ({ children }) => {
  const { treeId, interfaceId } = useParams<{ treeId: string; interfaceId: string }>();
  const {
    currentHost,
    currentDeviceId,
    getDevicePosition,
    setDevicePosition,
    initializeDevicePosition,
  } = useDeviceData();
  const navigationConfig = useNavigationConfig();

  // console.log('[@context:NavigationProvider] Initializing unified navigation context');

  // ========================================
  // ROUTE PARAMS
  // ========================================

  const routeParams = useParams<{
    treeId?: string;
    treeName: string;
    interfaceId?: string;
  }>();

  const { treeName } = useMemo(() => routeParams, [routeParams]);

  // ========================================
  // STATE
  // ========================================

  // Navigation state
  const [currentTreeId, setCurrentTreeId] = useState<string>(treeName || treeId || 'home');
  const [currentTreeName, setCurrentTreeName] = useState<string>(treeName || 'home');
  const [navigationPath, setNavigationPath] = useState<string[]>([treeName || treeId || 'home']);
  const [navigationNamePath, setNavigationNamePath] = useState<string[]>([treeName || 'home']);

  // Current position tracking
  const [currentNodeId, setCurrentNodeId] = useState<string | null>(null);
  const [currentNodeLabel, setCurrentNodeLabel] = useState<string | null>(null);

  // Tree cache - stores multiple trees by treeId
  const [treeCache, setTreeCache] = useState<Map<string, { nodes: UINavigationNode[], edges: UINavigationEdge[] }>>(new Map());
  
  // Root tree tracking for breadcrumb navigation
  const [rootTreeId, setRootTreeId] = useState<string | null>(null);
  
  // React Flow state - displays active tree from cache
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  // Selection state
  const [selectedNode, setSelectedNode] = useState<UINavigationNode | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<UINavigationEdge | null>(null);

  // Dialog states
  const [isNodeDialogOpen, setIsNodeDialogOpen] = useState(false);
  const [isEdgeDialogOpen, setIsEdgeDialogOpen] = useState(false);
  const [isDiscardDialogOpen, setIsDiscardDialogOpen] = useState(false);

  // Form states
  const [isNewNode, setIsNewNode] = useState(false);
  const [nodeForm, setNodeForm] = useState<NodeForm>({
    label: '',
    type: 'screen',
    description: '',
    verifications: [],
  });
  const [edgeForm, setEdgeForm] = useState<any | null>(null);
  const [edgeLabels, setEdgeLabels] = useState<{fromLabel: string, toLabel: string}>({fromLabel: '', toLabel: ''});

  // Loading and error states
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Save states
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  // Lock states
  const [isLocked, setIsLocked] = useState(false);
  const [isCheckingLock, setIsCheckingLock] = useState(false);

  // Interface state
  const [userInterface, setUserInterface] = useState<any>(null);

  const updateCurrentPosition = useCallback(
    (nodeId: string | null, nodeLabel?: string | null) => {
      console.log('[@context:NavigationProvider] Updating current position');
      setCurrentNodeId(nodeId);
      setCurrentNodeLabel(nodeLabel || null);

      // Update device position if we have the required context
      if (nodeId && nodeLabel && currentHost && currentDeviceId && treeId && setDevicePosition) {
        setDevicePosition(currentHost, currentDeviceId, treeId, nodeId, nodeLabel);
      }
    },
    [currentHost, currentDeviceId, treeId, setDevicePosition],
  );

  // Update nodes with minimap indicators
  const updateNodesWithMinimapIndicators = useCallback(
    (navigationSteps?: any[]) => {
      console.log('[@context:NavigationProvider] Updating nodes with minimap indicators');

      setNodes((currentNodes) => {
        return currentNodes.map((node) => {
          const isCurrentPosition = node.id === currentNodeId;

          // Check if node is part of navigation route
          const isOnNavigationRoute =
            navigationSteps?.some(
              (step: any) => step.from_node_id === node.id || step.to_node_id === node.id,
            ) || false;

          return {
            ...node,
            data: {
              ...node.data,
              isCurrentPosition,
              isOnNavigationRoute,
            },
          };
        });
      });
    },
    [currentNodeId, setNodes],
  );

  // ========================================
  // EFFECTS
  // ========================================

  // Debug logging for userInterface changes
  useEffect(() => {
    console.log('[@context:NavigationProvider] userInterface changed:', userInterface);
  }, [userInterface]);

  // Separate effects to prevent infinite loops
  const prevCurrentNodeIdRef = useRef<string | null>(null);
  const initializationKeyRef = useRef<string>('');

  // Effect 1: Initialize device position when context first loads
  useEffect(() => {
    const currentKey = `${JSON.stringify(currentHost) || ''}-${currentDeviceId || ''}-${treeId || ''}`;

    if (
      nodes.length > 0 &&
      currentHost &&
      currentDeviceId &&
      treeId &&
      getDevicePosition &&
      initializeDevicePosition &&
      initializationKeyRef.current !== currentKey
    ) {
      initializationKeyRef.current = currentKey;

      // Check if we already have a position for this device/tree combination
      const existingPosition = getDevicePosition(currentHost, currentDeviceId, treeId);

      if (existingPosition) {
        // Use existing position
        console.log(
          '[@context:NavigationProvider] Using existing device position:',
          existingPosition,
        );
        setCurrentNodeId(existingPosition.nodeId);
        setCurrentNodeLabel(existingPosition.nodeLabel);
      } else {
        // Initialize to root node
        const homeNode = nodes.find((node: any) => node.data?.is_root === true);
        if (homeNode) {
          console.log(
            '[@context:NavigationProvider] Initializing device position to root node:',
            homeNode.id,
          );
          const position = initializeDevicePosition(
            currentHost,
            currentDeviceId,
            treeId,
            homeNode.id,
            homeNode.data?.label || 'Root',
          );
          setCurrentNodeId(position.nodeId);
          setCurrentNodeLabel(position.nodeLabel);
        }
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    nodes.length, // Only trigger when nodes are first loaded (not on every node change)
    currentHost,
    currentDeviceId,
    treeId,
    getDevicePosition,
    initializeDevicePosition,
  ]);

  // Effect 2: Update minimap indicators when currentNodeId changes (but not when nodes change)
  useEffect(() => {
    if (prevCurrentNodeIdRef.current !== currentNodeId) {
      console.log('[@context:NavigationProvider] Updating nodes with minimap indicators');
      prevCurrentNodeIdRef.current = currentNodeId;

      setNodes((currentNodes) => {
        // Check if any node actually needs updating to prevent unnecessary re-renders
        const needsUpdate = currentNodes.some((node) => {
          const isCurrentPosition = node.id === currentNodeId;
          const isOnNavigationRoute = false;
          return (
            node.data.isCurrentPosition !== isCurrentPosition ||
            node.data.isOnNavigationRoute !== isOnNavigationRoute
          );
        });

        if (!needsUpdate) {
          return currentNodes; // Return same reference if no changes needed
        }

        return currentNodes.map((node) => {
          const isCurrentPosition = node.id === currentNodeId;
          const isOnNavigationRoute = false;

          // Only update if the flags actually changed
          if (
            node.data.isCurrentPosition !== isCurrentPosition ||
            node.data.isOnNavigationRoute !== isOnNavigationRoute
          ) {
            return {
              ...node,
              data: {
                ...node.data,
                isCurrentPosition,
                isOnNavigationRoute,
              },
            };
          }
          return node;
        });
      });
    }
  }, [currentNodeId, setNodes]); // Only depend on currentNodeId, NOT on nodes

  const [rootTree, setRootTree] = useState<any>(null);
  const [isLoadingInterface, setIsLoadingInterface] = useState<boolean>(!!interfaceId);

  // View state
  const [currentViewRootId, setCurrentViewRootId] = useState<string | null>(null);
  const [viewPath, setViewPath] = useState<{ id: string; name: string }[]>([]);

  // Filtering state
  const [focusNodeId, setFocusNodeId] = useState<string | null>(null);
  const [maxDisplayDepth, setMaxDisplayDepth] = useState<number>(5);
  const [availableFocusNodes, setAvailableFocusNodes] = useState<
    { id: string; label: string; depth: number }[]
  >([]);

  // History state
  const [initialState, setInitialState] = useState<{
    nodes: UINavigationNode[];
    edges: UINavigationEdge[];
  } | null>(null);

  // React Flow refs
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const [reactFlowInstance, setReactFlowInstance] = useState<ReactFlowInstance | null>(null);
  const [pendingViewport, setPendingViewport] = useState<{ x: number; y: number; zoom: number } | null>(null);

  // ========================================
  // LOCK METHODS
  // ========================================

  const lockNavigationTree = useCallback(async (treeId: string): Promise<boolean> => {
    setIsCheckingLock(true);
    try {
      // Mock implementation - replace with actual API call
      console.log('[@context:NavigationProvider] Locking navigation tree:', treeId);
      await new Promise((resolve) => setTimeout(resolve, 500)); // Simulate API call
      setIsLocked(true);
      return true;
    } catch (error) {
      console.error('[@context:NavigationProvider] Failed to lock navigation tree:', error);
      return false;
    } finally {
      setIsCheckingLock(false);
    }
  }, []);

  const unlockNavigationTree = useCallback(async (treeId: string): Promise<boolean> => {
    setIsCheckingLock(true);
    try {
      // Mock implementation - replace with actual API call
      console.log('[@context:NavigationProvider] Unlocking navigation tree:', treeId);
      await new Promise((resolve) => setTimeout(resolve, 500)); // Simulate API call
      setIsLocked(false);
      return true;
    } catch (error) {
      console.error('[@context:NavigationProvider] Failed to unlock navigation tree:', error);
      return false;
    } finally {
      setIsCheckingLock(false);
    }
  }, []);

  // ========================================
  // ACTION METHODS
  // ========================================

  const resetAll = useCallback(() => {
    // console.log('[@context:NavigationProvider] Resetting all state');
    setSelectedNode(null);
    setSelectedEdge(null);
    if (initialState) {
      setNodes(initialState.nodes);
      setEdges(initialState.edges);
    }
    setIsNodeDialogOpen(false);
    setIsEdgeDialogOpen(false);
    setIsDiscardDialogOpen(false);
    setNodeForm({
      label: '',
      type: 'screen',
      description: '',
      verifications: [],
    });
    setEdgeForm({
      edgeId: '',
      action_sets: [],
      default_action_set_id: '',
      final_wait_time: 2000,
    });
    setIsNewNode(false);
    setHasUnsavedChanges(false);
    setError(null);
    setSuccess(null);
  }, [initialState, setNodes, setEdges]);

  const resetSelection = useCallback(() => {
    // console.log('[@context:NavigationProvider] Resetting selection');
    setSelectedNode(null);
    setSelectedEdge(null);
  }, []);

  const resetToInitialState = useCallback(() => {
    console.log('[@context:NavigationProvider] Resetting to initial state');
    if (initialState) {
      setNodes(initialState.nodes);
      setEdges(initialState.edges);
      setHasUnsavedChanges(false);
    }
  }, [initialState, setNodes, setEdges]);

  const resetForms = useCallback(() => {
    console.log('[@context:NavigationProvider] Resetting forms');
    setNodeForm({
      label: '',
      type: 'screen',
      description: '',
      verifications: [],
    });
    setEdgeForm({
      edgeId: '',
      action_sets: [],
      default_action_set_id: '',
      final_wait_time: 2000,
    });
    setIsNewNode(false);
  }, []);

  const resetDialogs = useCallback(() => {
    console.log('[@context:NavigationProvider] Resetting dialogs');
    setIsNodeDialogOpen(false);
    setIsEdgeDialogOpen(false);
    setIsDiscardDialogOpen(false);
  }, []);

  const openNodeDialog = useCallback((node?: UINavigationNode) => {
    console.log('[@context:NavigationProvider] Opening node dialog');
    if (node) {
      setSelectedNode(node);
      setNodeForm({
        label: node.data?.label || '',
        type: node.data?.type || 'screen',
        description: node.data?.description || '',
        verifications: node.data?.verifications || [],
      });
      setIsNewNode(false);
    } else {
      setIsNewNode(true);
    }
    setIsNodeDialogOpen(true);
  }, []);

  const openEdgeDialog = useCallback((edge?: UINavigationEdge) => {
    console.log('[@context:NavigationProvider] Opening edge dialog');
    if (edge) {
      setSelectedEdge(edge);
      setEdgeForm({
        edgeId: edge.id,
        action_sets: edge.data?.action_sets || [],
        default_action_set_id: edge.data?.default_action_set_id || '',
        final_wait_time: edge.data?.final_wait_time || 2000,
      });
    }
    setIsEdgeDialogOpen(true);
  }, []);

  const closeAllDialogs = useCallback(() => {
    console.log('[@context:NavigationProvider] Closing all dialogs');
    setIsNodeDialogOpen(false);
    setIsEdgeDialogOpen(false);
    setIsDiscardDialogOpen(false);
  }, []);

  const markUnsavedChanges = useCallback(() => {
    console.log('[@context:NavigationProvider] Marking unsaved changes');
    setHasUnsavedChanges(true);
  }, []);

  const clearUnsavedChanges = useCallback(() => {
    console.log('[@context:NavigationProvider] Clearing unsaved changes');
    setHasUnsavedChanges(false);
  }, []);

  const resetToHome = useCallback(() => {
    console.log('[@context:NavigationProvider] Resetting to home');
    setCurrentTreeId('home');
    setCurrentTreeName('home');
    setNavigationPath(['home']);
    setNavigationNamePath(['home']);
    setCurrentViewRootId(null);
    setViewPath([]);
  }, []);

  const fitViewToNodes = useCallback(() => {
    console.log('[@context:NavigationProvider] Fitting view to nodes');
    if (reactFlowInstance) {
      reactFlowInstance.fitView();
    }
  }, [reactFlowInstance]);

  // Tree cache management functions
  const cacheTree = useCallback((treeId: string, treeData: { nodes: UINavigationNode[], edges: UINavigationEdge[] }) => {
    console.log(`[@context:NavigationProvider] Caching tree ${treeId} with ${treeData.nodes.length} nodes and ${treeData.edges.length} edges`);
    setTreeCache(prev => new Map(prev).set(treeId, treeData));
  }, []);

  const getCachedTree = useCallback((treeId: string) => {
    const cached = treeCache.get(treeId);
    console.log(`[@context:NavigationProvider] Getting cached tree ${treeId}:`, cached ? 'found' : 'not found');
    return cached || null;
  }, [treeCache]);

  const switchToTree = useCallback((treeId: string) => {
    console.log(`[@context:NavigationProvider] Switching to tree ${treeId}`);
    const cachedTree = treeCache.get(treeId);
    if (cachedTree) {
      setNodes(cachedTree.nodes);
      setEdges(cachedTree.edges);
      console.log(`[@context:NavigationProvider] Switched to cached tree ${treeId} with ${cachedTree.nodes.length} nodes`);
    } else {
      console.warn(`[@context:NavigationProvider] Tree ${treeId} not found in cache`);
    }
  }, [treeCache, setNodes, setEdges]);

  const cacheAndSwitchToTree = useCallback((treeId: string, treeData: { nodes: UINavigationNode[], edges: UINavigationEdge[] }) => {
    console.log(`[@context:NavigationProvider] Caching and switching to tree ${treeId} with ${treeData.nodes.length} nodes and ${treeData.edges.length} edges`);
    
    // Update cache first
    setTreeCache(prev => new Map(prev).set(treeId, treeData));
    
    // Immediately display the tree data (no cache dependency)
    setNodes(treeData.nodes);
    setEdges(treeData.edges);
    
    console.log(`[@context:NavigationProvider] Cached and displayed tree ${treeId} with ${treeData.nodes.length} nodes`);
  }, [setNodes, setEdges]);

  const validateNavigationPath = useCallback((path: string[]): boolean => {
    console.log('[@context:NavigationProvider] Validating navigation path:', path);
    return path.length > 0 && path.every((id) => typeof id === 'string' && id.length > 0);
  }, []);

  const updateNavigationPath = useCallback(
    (newPath: string[], newNamePath: string[]) => {
      console.log('[@context:NavigationProvider] Updating navigation path:', {
        newPath,
        newNamePath,
      });
      if (validateNavigationPath(newPath)) {
        setNavigationPath(newPath);
        setNavigationNamePath(newNamePath);
        if (newPath.length > 0) {
          const currentId = newPath[newPath.length - 1];
          const currentName = newNamePath[newNamePath.length - 1] || currentId;
          setCurrentTreeId(currentId);
          setCurrentTreeName(currentName);
        }
      }
    },
    [validateNavigationPath],
  );

  // ========================================
  // MEMOIZED VALUES
  // ========================================

  const stableNodes = useMemo(() => nodes, [nodes]);
  const stableEdges = useMemo(() => edges, [edges]);
  const stableNodeForm = useMemo(() => nodeForm, [nodeForm]);
  const stableEdgeForm = useMemo(() => edgeForm, [edgeForm]);
  const stableNavigationPath = useMemo(() => navigationPath, [navigationPath]);
  const stableNavigationNamePath = useMemo(() => navigationNamePath, [navigationNamePath]);
  const stableViewPath = useMemo(() => viewPath, [viewPath]);
  const stableAvailableFocusNodes = useMemo(() => availableFocusNodes, [availableFocusNodes]);

  // ========================================
  // CONTEXT VALUE
  // ========================================

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const contextValue: NavigationContextType = useMemo(() => {
    // console.log('[@context:NavigationProvider] Creating context value');
    return {
      // Route params
      treeId,
      treeName,
      interfaceId,

      // Navigation state
      currentTreeId,
      setCurrentTreeId,
      currentTreeName,
      setCurrentTreeName,
      navigationPath: stableNavigationPath,
      setNavigationPath,
      navigationNamePath: stableNavigationNamePath,
      setNavigationNamePath,

      // Current position tracking
      currentNodeId,
      setCurrentNodeId,
      currentNodeLabel,
      setCurrentNodeLabel,

      // Tree cache management
      cacheTree,
      getCachedTree,
      switchToTree,
      cacheAndSwitchToTree,
      
      // Root tree tracking
      rootTreeId,
      setRootTreeId,
      
      // React Flow state - displays active tree from cache
      nodes: stableNodes as UINavigationNode[],
      setNodes,
      onNodesChange,
      edges: stableEdges as UINavigationEdge[],
      setEdges,
      onEdgesChange,

      // Selection state
      selectedNode,
      setSelectedNode,
      selectedEdge,
      setSelectedEdge,

      // Dialog states
      isNodeDialogOpen,
      setIsNodeDialogOpen,
      isEdgeDialogOpen,
      setIsEdgeDialogOpen,
      isDiscardDialogOpen,
      setIsDiscardDialogOpen,

      // Form states
      isNewNode,
      setIsNewNode,
      nodeForm,
      setNodeForm,
      edgeForm,
      setEdgeForm,
      edgeLabels,
      setEdgeLabels,

      // Loading and error states
      isLoading,
      setIsLoading,
      error,
      setError,
      success,
      setSuccess,

      // Save states
      isSaving,
      setIsSaving,
      saveError,
      setSaveError,
      saveSuccess,
      setSaveSuccess,
      hasUnsavedChanges,
      setHasUnsavedChanges,

      // Lock states
      isLocked,
      setIsLocked,
      isCheckingLock,
      setIsCheckingLock,

      // Interface state
      userInterface,
      setUserInterface,
      rootTree,
      setRootTree,
      isLoadingInterface,
      setIsLoadingInterface,

      // View state
      currentViewRootId,
      setCurrentViewRootId,
      viewPath: stableViewPath,
      setViewPath,

      // Filtering state
      focusNodeId,
      setFocusNodeId,
      maxDisplayDepth,
      setMaxDisplayDepth,
      availableFocusNodes: stableAvailableFocusNodes,
      setAvailableFocusNodes,

      // History state
      initialState,
      setInitialState,

      // React Flow refs
          reactFlowWrapper,
    reactFlowInstance,
    setReactFlowInstance,
    pendingViewport,
    setPendingViewport,

      // Action methods
      resetAll,
      resetSelection,
      resetToInitialState,
      resetForms,
      resetDialogs,
      openNodeDialog,
      openEdgeDialog,
      closeAllDialogs,
      markUnsavedChanges,
      clearUnsavedChanges,
      resetToHome,
      fitViewToNodes,
      validateNavigationPath,
      updateNavigationPath,
      updateCurrentPosition,
      updateNodesWithMinimapIndicators,

      // Lock methods
      lockNavigationTree,
      unlockNavigationTree,

             // Centralized save methods
       saveNodeWithStateUpdate: async (nodeForm: any) => {
         try {
           setIsLoading(true);
           setError(null);

           let updatedNodeData: any;

           if (isNewNode) {
             // Create new node - use data.type directly as ReactFlow type
             updatedNodeData = {
               id: nodeForm.id || `node-${Date.now()}`,
               position: { x: 100, y: 100 },
               type: nodeForm.type, // Use data.type directly (screen, menu, action)
               data: {
                 label: nodeForm.label,
                 type: nodeForm.type,
                 description: nodeForm.description,
                 verifications: nodeForm.verifications || [],
               },
             };
             setNodes([...nodes, updatedNodeData]);
           } else if (selectedNode) {
             // Update existing node - update ReactFlow type if data.type changed
             updatedNodeData = {
               ...selectedNode,
               type: nodeForm.type, // Update ReactFlow type to match data.type
               data: {
                 ...selectedNode.data,
                 label: nodeForm.label,
                 type: nodeForm.type,
                 description: nodeForm.description,
                 verifications: nodeForm.verifications || [],
               },
             };
             const updatedNodes = nodes.map((node) =>
               node.id === selectedNode?.id ? updatedNodeData : node,
             );
             setNodes(updatedNodes);
             setSelectedNode(updatedNodeData);
           }

           // Save to database via NavigationConfigContext with smart routing
           if (updatedNodeData && navigationConfig.actualTreeId) {
             // SMART SAVE ROUTING: Determine which tree to save to
             const isParentReference = updatedNodeData.data.isParentReference;
             const targetTreeId = isParentReference 
               ? updatedNodeData.data.originalTreeId || navigationConfig.actualTreeId
               : navigationConfig.actualTreeId;
               
             console.log(`[@NavigationContext] Saving node to ${isParentReference ? 'original' : 'current'} tree: ${targetTreeId}`);
                         
             // Get current position from ReactFlow canvas (nodes state)
            const currentNode = nodes.find(node => node.id === updatedNodeData.id);
            const currentPosition = currentNode?.position || updatedNodeData.position || { x: 0, y: 0 };
            
            console.log(`[@NavigationContext] Saving node ${updatedNodeData.id} with canvas position:`, currentPosition);
            console.log(`[@NavigationContext] Node verifications count:`, updatedNodeData.data.verifications?.length || 0);

            const normalizedNode = {
              node_id: updatedNodeData.id,
              label: updatedNodeData.data.label,
              position_x: currentPosition.x,
              position_y: currentPosition.y,
              node_type: updatedNodeData.type || 'screen',
              verifications: updatedNodeData.data.verifications || [],
              data: {
                // Only include non-verification data to avoid duplication
                description: updatedNodeData.data.description,
                screenshot: updatedNodeData.data.screenshot,
                depth: updatedNodeData.data.depth,
                parent: updatedNodeData.data.parent,
                menu_type: updatedNodeData.data.menu_type,
                priority: updatedNodeData.data.priority,
                is_root: updatedNodeData.data.is_root,
                isParentReference: updatedNodeData.data.isParentReference,
                originalTreeId: updatedNodeData.data.originalTreeId,
                // DO NOT include verifications here - they're already at top level
              },
            };

            console.log(`[@NavigationContext] Normalized node structure:`, {
              verifications: normalizedNode.verifications,
              dataHasVerifications: 'verifications' in normalizedNode.data
            });

            await navigationConfig.saveNode(targetTreeId, normalizedNode as any);

            // Note: Cache refresh removed to prevent tree reload that breaks selectedNode reference
            // The cache will be refreshed on next navigation operation if needed
           }

           setIsNodeDialogOpen(false);
           setNodeForm({ label: '', type: 'screen', description: '', verifications: [] }); // Reset to initial empty form
           setSuccess('Node saved successfully');
         } catch (error) {
           console.error('Error saving node:', error);
           setError('Failed to save node changes');
           throw error;
         } finally {
           setIsLoading(false);
         }
       },

       saveEdgeWithStateUpdate: async (edgeForm: any) => {
         try {
           setIsLoading(true);
           setError(null);

           if (!edgeForm.edgeId) {
             throw new Error('Edge ID missing from form data');
           }

           const currentSelectedEdge = edges.find((edge) => edge.id === edgeForm.edgeId);
           if (!currentSelectedEdge) {
             throw new Error(`Edge ${edgeForm.edgeId} not found in current tree`);
           }

                     // Update edge with new data
          const updatedEdge = {
            ...currentSelectedEdge,
            data: {
              ...(currentSelectedEdge.data || {}),
              // Include all form data including action_sets
              action_sets: edgeForm.action_sets || [],
              default_action_set_id: edgeForm.default_action_set_id || 'default',
              final_wait_time: edgeForm.final_wait_time || 0,
              priority: edgeForm.priority || 'p3',
              threshold: edgeForm.threshold || 0,
            },
          };

           // DATABASE FIRST: Save to database, then update frontend with server response
           if (navigationConfig.actualTreeId) {
             // Get current edge from ReactFlow canvas (edges state) to capture current handle positions
             const currentEdge = edges.find(edge => edge.id === updatedEdge.id);
             const currentSourceHandle = currentEdge?.sourceHandle || updatedEdge.sourceHandle;
             const currentTargetHandle = currentEdge?.targetHandle || updatedEdge.targetHandle;
             
             console.log(`[@NavigationContext] Saving edge ${updatedEdge.id} with canvas handles:`, { 
               sourceHandle: currentSourceHandle, 
               targetHandle: currentTargetHandle 
             });

             const normalizedEdge = {
              edge_id: updatedEdge.id,
              source_node_id: updatedEdge.source,
              target_node_id: updatedEdge.target,
              label: updatedEdge.label, // Use ReactFlow edge label, not data.label

              data: {
                // Only include UI-specific data, not navigation logic data
                ...(updatedEdge.data?.priority && { priority: updatedEdge.data.priority }),
                ...(updatedEdge.data?.threshold && { threshold: updatedEdge.data.threshold }),
                // Include ReactFlow handle information for persistence (use current canvas state)
                ...(currentSourceHandle && { sourceHandle: currentSourceHandle }),
                ...(currentTargetHandle && { targetHandle: currentTargetHandle }),
                // IMPORTANT: Do NOT include label in data - use top-level label field only
              },
              // NEW: action_sets structure - NO LEGACY FIELDS
              action_sets: updatedEdge.data.action_sets || [],
              default_action_set_id: updatedEdge.data.default_action_set_id || 'default',
              final_wait_time: updatedEdge.data.final_wait_time || 0,
            };

             const saveResponse = await navigationConfig.saveEdge(navigationConfig.actualTreeId, normalizedEdge as any);
             
             // Update frontend state with server response (source of truth)
             if (saveResponse?.edge) {
               const serverEdge = saveResponse.edge;
               const updatedEdgeFromServer = {
                 ...currentSelectedEdge,
                 data: {
                   ...serverEdge,
                   // Preserve ReactFlow properties
                   sourceHandle: currentSourceHandle,
                   targetHandle: currentTargetHandle,
                 },
               };
               
               // Update edges list with server data
               const updatedEdges = edges.map((edge) =>
                 edge.id === currentSelectedEdge.id ? updatedEdgeFromServer : edge,
               );
               setEdges(updatedEdges);
               
               // Update selected edge with server data
               setSelectedEdge(updatedEdgeFromServer);
               
               console.log('[@NavigationContext] Updated frontend state with server response');
             }

            // Refresh navigation cache (non-blocking)
            try {
              await fetch('/server/pathfinding/cache/refresh', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                  tree_id: navigationConfig.actualTreeId,
                  team_id: 'default' 
                })
              });
            } catch (cacheError) {
              console.warn('Cache refresh failed:', cacheError);
            }
           }

           setIsEdgeDialogOpen(false);
           setSuccess('Edge saved successfully');
         } catch (error) {
           console.error('Error saving edge:', error);
           setError('Failed to save edge changes');
           throw error;
         } finally {
           setIsLoading(false);
         }
       },

       saveTreeWithStateUpdate: async (treeId: string) => {
         try {
           setIsLoading(true);
           setError(null);

           // Convert frontend format to normalized format with current canvas positions
           console.log(`[@NavigationContext] Bulk saving tree with ${nodes.length} nodes at their current canvas positions`);
           const normalizedNodes = nodes.map(node => ({
             node_id: node.id,
             label: node.data.label,
             position_x: node.position?.x || 0,
             position_y: node.position?.y || 0,
             node_type: node.data.type || 'default',
             verifications: node.data.verifications || [],
             data: {
               // Only include non-verification data to avoid duplication
               description: node.data.description,
               screenshot: node.data.screenshot,
               depth: node.data.depth,
               parent: node.data.parent,
               menu_type: node.data.menu_type,
               priority: node.data.priority,
               is_root: node.data.is_root,
               isParentReference: node.data.isParentReference,
               originalTreeId: node.data.originalTreeId,
               // DO NOT include verifications here - they're already at top level
             }
           }));

                     const normalizedEdges = edges.map(edge => ({
            edge_id: edge.id,
            source_node_id: edge.source,
            target_node_id: edge.target,
            label: edge.label, // Use ReactFlow edge label, not data.label

            data: {
              // Only include UI-specific data, not navigation logic data
              ...(edge.data?.priority && { priority: edge.data.priority }),
              ...(edge.data?.threshold && { threshold: edge.data.threshold }),
              // Include ReactFlow handle information for persistence
              ...(edge.sourceHandle && { sourceHandle: edge.sourceHandle }),
              ...(edge.targetHandle && { targetHandle: edge.targetHandle }),
              // IMPORTANT: Do NOT include label in data - use top-level label field only
            },
            // STRICT: action_sets required - NO LEGACY CONVERSION
            action_sets: edge.data?.action_sets || [],
            default_action_set_id: edge.data?.default_action_set_id || 'default',
            final_wait_time: edge.data?.final_wait_time || 0,
          }));

           // Compare with initial state to find deletions
           const currentNodeIds = new Set(nodes.map(n => n.id));
           const currentEdgeIds = new Set(edges.map(e => e.id));
           const initialNodeIds = initialState ? initialState.nodes.map(n => n.id) : [];
           const initialEdgeIds = initialState ? initialState.edges.map(e => e.id) : [];
           
           const deletedNodeIds = initialNodeIds.filter(id => !currentNodeIds.has(id));
           const deletedEdgeIds = initialEdgeIds.filter(id => !currentEdgeIds.has(id));

           // Capture viewport and save
           const viewport = reactFlowInstance?.getViewport();
           await navigationConfig.saveTreeData(treeId, normalizedNodes, normalizedEdges, deletedNodeIds, deletedEdgeIds, viewport);
           
           setInitialState({ 
             nodes: nodes as UINavigationNode[], 
             edges: edges as UINavigationEdge[] 
           });
           setHasUnsavedChanges(false);
           setSuccess('Tree saved successfully');
         } catch (error) {
           console.error('Error saving tree:', error);
           setError('Failed to save tree');
           throw error;
         } finally {
           setIsLoading(false);
         }
       },

       executeActionsWithPositionUpdate: async (actions: any[], retryActions: any[], failureActions?: any[], targetNodeId?: string) => {
         try {
           setIsLoading(true);
           setError(null);

           // Mock action execution - replace with actual API call
           const result = await fetch('/server/action/execute', {
             method: 'POST',
             headers: { 'Content-Type': 'application/json' },
             body: JSON.stringify({
               actions: actions,
               retry_actions: retryActions,
               failure_actions: failureActions || [],
               target_node_id: targetNodeId
             })
           });

           const response = await result.json();

           if (response.success && targetNodeId) {
             setCurrentNodeId(targetNodeId);
             setCurrentNodeLabel(targetNodeId);
           }

           setSuccess('Actions executed successfully');
           return response;
         } catch (error) {
           console.error('Error executing actions:', error);
           setError('Failed to execute actions');
           throw error;
         } finally {
           setIsLoading(false);
         }
       },
    };
  }, [
    // Only include values that should trigger context recreation
    treeId,
    treeName,
    interfaceId,
    currentTreeId,
    currentTreeName,
    stableNavigationPath,
    stableNavigationNamePath,
    stableNodes,
    stableEdges,
    selectedNode,
    selectedEdge,
    isNodeDialogOpen,
    isEdgeDialogOpen,
    isDiscardDialogOpen,
    isNewNode,
    stableNodeForm,
    stableEdgeForm,
    isLoading,
    error,
    success,
    isSaving,
    saveError,
    saveSuccess,
    hasUnsavedChanges,
    isLocked,
    isCheckingLock,
    userInterface,
    rootTree,
    isLoadingInterface,
    currentViewRootId,
    stableViewPath,
    focusNodeId,
    maxDisplayDepth,
    stableAvailableFocusNodes,
    initialState,
    reactFlowInstance,
    currentNodeId,
    currentNodeLabel,
    updateNodesWithMinimapIndicators,
  ]);

  return <NavigationContext.Provider value={contextValue}>{children}</NavigationContext.Provider>;
};

NavigationProvider.displayName = 'NavigationProvider';

export default NavigationContext;

// ========================================
// HOOK
// ========================================

export const useNavigation = (): NavigationContextType => {
  const context = useContext(NavigationContext);
  if (!context) {
    throw new Error('useNavigation must be used within a NavigationProvider');
  }
  return context;
};
