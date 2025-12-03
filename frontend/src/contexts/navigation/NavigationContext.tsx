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
import { useNodesState, useEdgesState, ReactFlowInstance, Edge } from 'reactflow';

import {
  UINavigationNode,
  UINavigationEdge,
  NodeForm,
  EdgeForm,
} from '../../types/pages/Navigation_Types';
import { useDeviceData } from '../device/DeviceDataContext';
import { useNavigationConfig } from './NavigationConfigContext';
import { useNavigationPreviewCache } from './NavigationPreviewCacheContext';

import { buildServerUrl } from '../../utils/buildUrlUtils';
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

  parentChain: Array<{ treeId: string; treeName: string; nodes: UINavigationNode[]; edges: UINavigationEdge[] }>;
  setParentChain: (chain: Array<{ treeId: string; treeName: string; nodes: UINavigationNode[]; edges: UINavigationEdge[] }>) => void;
  addToParentChain: (treeData: { treeId: string; treeName: string; nodes: UINavigationNode[]; edges: UINavigationEdge[] }) => void;
  popFromParentChain: () => void;
  resetToRoot: () => void;
  
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
  edgeForm: EdgeForm | null;
  setEdgeForm: (form: EdgeForm | null) => void;
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
  
  // Undo/Redo methods
  undo: () => void;
  redo: () => void;
  canUndo: boolean;
  canRedo: boolean;
  pushHistory: () => void;
  
  // Copy/Paste methods
  copyNode: () => void;
  pasteNode: () => void;
  canPaste: boolean;

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
  
  // Edge deletion methods
  deleteEdgeDirection: (edgeId: string, actionSetId: string) => Promise<void>;
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
  const { invalidateTree } = useNavigationPreviewCache();

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

  const [parentChain, setParentChain] = useState<Array<{ treeId: string; treeName: string; nodes: UINavigationNode[]; edges: UINavigationEdge[] }>>([]);
  
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, _onEdgesChange] = useEdgesState([]);  // Rename to _onEdgesChange

  // Wrap onEdgesChange to handle conditional edge auto-ungroup
  const onEdgesChange = useCallback(async (changes: any[]) => {
    // First apply the changes using the original handler
    _onEdgesChange(changes);
    
    // Check if any edges were removed
    const removeChanges = changes.filter((c) => c.type === 'remove');
    if (removeChanges.length === 0) return;
    
    // For each removed edge, check if it was part of a conditional group
    for (const removeChange of removeChanges) {
      const removedEdgeId = removeChange.id;
      const removedEdge = edges.find((e) => e.id === removedEdgeId);
      
      if (!removedEdge || !removedEdge.data?.is_conditional) continue;
      
      // Find remaining sibling edges (same source + sourceHandle, different target)
      const remainingSiblings = edges.filter(
        (e) => 
          e.id !== removedEdgeId &&
          e.source === removedEdge.source && 
          e.sourceHandle === removedEdge.sourceHandle &&
          e.data?.action_sets?.[0]?.id === removedEdge.data?.action_sets?.[0]?.id
      );
      
      // If only 1 sibling remains, unlink it
      if (remainingSiblings.length === 1) {
        const lastSibling = remainingSiblings[0];
        console.log(`[@NavigationContext:onEdgesChange] 🔓 UNLINK: Last sibling ${lastSibling.id} becoming independent`);
        
        // Save to database with cleared conditional flag
        try {
          const siblingNormalized = {
            edge_id: lastSibling.id,
            source_node_id: lastSibling.source,
            target_node_id: lastSibling.target,
            label: lastSibling.label,
            data: {
              priority: lastSibling.data?.priority || 'p3',
              sourceHandle: lastSibling.sourceHandle,
              targetHandle: lastSibling.targetHandle,
              // Clear conditional flags
              is_conditional: false,
              is_conditional_primary: false,
            },
            action_sets: lastSibling.data.action_sets,
            default_action_set_id: lastSibling.data.default_action_set_id,
            final_wait_time: lastSibling.data.final_wait_time || 2000,
          };
          
          await navigationConfig?.saveEdge(navigationConfig?.actualTreeId || 'unknown', siblingNormalized as any);
          console.log(`[@NavigationContext:onEdgesChange] 🔓 Unlinked sibling saved to database: ${lastSibling.id}`);
        } catch (err) {
          console.error(`[@NavigationContext:onEdgesChange] ⚠️ Failed to save unlinked sibling:`, err);
        }
        
        // Update frontend state
        setEdges((currentEdges) => 
          currentEdges.map((edge): Edge => {
            if (edge.id === lastSibling.id) {
              return {
                ...edge,
                data: {
                  ...edge.data,
                  is_conditional: false,
                  is_conditional_primary: false,
                },
              };
            }
            return edge;
          })
        );
      }
    }
  }, [_onEdgesChange, edges, setEdges, navigationConfig]);

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
  const [edgeForm, setEdgeForm] = useState<EdgeForm | null>(null);
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
  
  // Undo/Redo state
  const [history, setHistory] = useState<Array<{ nodes: UINavigationNode[]; edges: UINavigationEdge[] }>>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);
  
  // Copy/Paste state
  const [copiedNode, setCopiedNode] = useState<UINavigationNode | null>(null);

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
  const addToParentChain = useCallback((treeData: { treeId: string; treeName: string; nodes: UINavigationNode[]; edges: UINavigationEdge[] }) => {
    setParentChain(prev => [...prev, treeData]);
    setNodes(treeData.nodes);
    setEdges(treeData.edges);
  }, [setNodes, setEdges]);

  const popFromParentChain = useCallback(() => {
    setParentChain(prev => {
      if (prev.length <= 1) return prev;
      const newChain = prev.slice(0, -1);
      const parent = newChain[newChain.length - 1];
      setNodes(parent.nodes);
      setEdges(parent.edges);
      return newChain;
    });
  }, [setNodes, setEdges]);

  const resetToRoot = useCallback(() => {
    if (parentChain.length > 0) {
      const root = parentChain[0];
      setParentChain([root]);
      setNodes(root.nodes);
      setEdges(root.edges);
    }
  }, [parentChain, setNodes, setEdges]);

  const validateNavigationPath = useCallback((path: string[]): boolean => {
    console.log('[@context:NavigationProvider] Validating navigation path:', path);
    return path.length > 0 && path.every((id) => typeof id === 'string' && id.length > 0);
  }, []);

  // Undo/Redo methods
  const pushHistory = useCallback(() => {
    const snapshot = { nodes: nodes as UINavigationNode[], edges: edges as UINavigationEdge[] };
    setHistory(prev => [...prev.slice(0, historyIndex + 1), snapshot]);
    setHistoryIndex(prev => prev + 1);
  }, [nodes, edges, historyIndex]);

  const undo = useCallback(() => {
    if (historyIndex > 0) {
      const prevState = history[historyIndex - 1];
      setNodes(prevState.nodes);
      setEdges(prevState.edges);
      setHistoryIndex(prev => prev - 1);
      setHasUnsavedChanges(true);
    }
  }, [history, historyIndex, setNodes, setEdges]);

  const redo = useCallback(() => {
    if (historyIndex < history.length - 1) {
      const nextState = history[historyIndex + 1];
      setNodes(nextState.nodes);
      setEdges(nextState.edges);
      setHistoryIndex(prev => prev + 1);
      setHasUnsavedChanges(true);
    }
  }, [history, historyIndex, setNodes, setEdges]);

  const canUndo = historyIndex > 0;
  const canRedo = historyIndex < history.length - 1;

  // Copy/Paste methods
  const copyNode = useCallback(() => {
    if (selectedNode) {
      setCopiedNode(selectedNode);
      console.log('[@NavigationContext] Node copied:', selectedNode.id);
    }
  }, [selectedNode]);

  const pasteNode = useCallback(() => {
    if (copiedNode) {
      const newNode: UINavigationNode = {
        ...copiedNode,
        id: `node-${Date.now()}`,
        position: {
          x: copiedNode.position.x + 50,
          y: copiedNode.position.y + 50,
        },
        data: {
          ...copiedNode.data,
          label: `${copiedNode.data.label}_copy`,
        },
      };
      setNodes([...nodes, newNode]);
      setHasUnsavedChanges(true);
      console.log('[@NavigationContext] Node pasted:', newNode.id);
    }
  }, [copiedNode, nodes, setNodes]);

  const canPaste = copiedNode !== null;

  // Auto-push history when nodes/edges change
  const prevNodesRef = useRef<UINavigationNode[]>(nodes as UINavigationNode[]);
  const prevEdgesRef = useRef<UINavigationEdge[]>(edges as UINavigationEdge[]);
  useEffect(() => {
    if (nodes !== prevNodesRef.current || edges !== prevEdgesRef.current) {
      prevNodesRef.current = nodes as UINavigationNode[];
      prevEdgesRef.current = edges as UINavigationEdge[];
      if (nodes.length > 0) pushHistory();
    }
  }, [nodes, edges, pushHistory]);

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
  // EFFECTS
  // ========================================

  // Update availableFocusNodes when nodes change - filter out entry nodes
  useEffect(() => {
    const focusNodes = nodes
      .filter(node => {
        // Filter out entry nodes (case-insensitive) - check type, label, and id
        const nodeType = (node.type || '').toLowerCase();
        const nodeLabel = (node.data?.label || '').toLowerCase();
        const nodeId = (node.id || '').toLowerCase();
        
        // Filter out if type, label, or id is "entry" or contains "entry"
        if (nodeType === 'entry' || nodeLabel === 'entry' || nodeId === 'entry' || nodeId.includes('entry')) {
          return false;
        }
        
        return true;
      })
      .map(node => ({
        id: node.id,
        label: node.data?.label || node.id,
        depth: node.data?.depth || 0
      }));
    
    setAvailableFocusNodes(focusNodes);
  }, [nodes]);

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

      parentChain,
      setParentChain,
      addToParentChain,
      popFromParentChain,
      resetToRoot,
      
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
      
      // Undo/Redo
      undo,
      redo,
      canUndo,
      canRedo,
      pushHistory,
      
      // Copy/Paste
      copyNode,
      pasteNode,
      canPaste,

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
            // Create new node - use ReactFlow type field only
            updatedNodeData = {
              id: nodeForm.id || `node-${Date.now()}`,
              position: { x: 100, y: 100 },
              type: nodeForm.type, // ReactFlow type field (screen, menu, action, entry)
              data: {
                label: nodeForm.label,
                description: nodeForm.description,
                verifications: nodeForm.verifications || [],
                verification_pass_condition: nodeForm.verification_pass_condition || 'all', // ✅ FIX: Include verification pass condition from form
                priority: nodeForm.priority || 'p3', // ✅ Also include priority to be consistent
              },
            };
            setNodes([...nodes, updatedNodeData]);
          } else if (selectedNode) {
            // Update existing node - update ReactFlow type field only
            updatedNodeData = {
              ...selectedNode,
              type: nodeForm.type, // ReactFlow type field
              data: {
                ...selectedNode.data,
                label: nodeForm.label,
                description: nodeForm.description,
                verifications: nodeForm.verifications || [],
                verification_pass_condition: nodeForm.verification_pass_condition || 'all', // ✅ FIX: Include verification pass condition from form
                priority: nodeForm.priority || 'p3', // ✅ Also include priority to be consistent
              },
            };
             const updatedNodes = nodes.map((node) =>
               node.id === selectedNode?.id ? updatedNodeData : node,
             );
             setNodes(updatedNodes);
             setSelectedNode(updatedNodeData);
           }

                       // Save to database via NavigationConfigContext with smart routing
            if (updatedNodeData && navigationConfig?.actualTreeId) {
             // SMART SAVE ROUTING: Determine which tree to save to
             const isParentReference = updatedNodeData.data.isParentReference;
             const targetTreeId = isParentReference 
               ? updatedNodeData.data.originalTreeId || navigationConfig.actualTreeId
               : navigationConfig.actualTreeId;
               
             console.log(`[@NavigationContext] SMART ROUTING - Node save details:`, {
               nodeId: updatedNodeData.id,
               nodeLabel: updatedNodeData.data.label,
               isParentReference,
               originalTreeId: updatedNodeData.data.originalTreeId,
               actualTreeId: navigationConfig.actualTreeId,
               targetTreeId,
               hasScreenshot: !!updatedNodeData.data.screenshot,
               screenshotUrl: updatedNodeData.data.screenshot
             });
                         
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
              node_type: updatedNodeData.type || 'screen',  // Use top-level node_type column only
              verifications: updatedNodeData.data.verifications || [],
              data: {
                // Only include non-verification data to avoid duplication
                // NOTE: node_type is saved at top-level, NOT in data object
                description: updatedNodeData.data.description || '',
                screenshot: updatedNodeData.data.screenshot || '',
                depth: updatedNodeData.data.depth ?? 0,
                parent: updatedNodeData.data.parent || [],
                menu_type: updatedNodeData.data.menu_type || '',
                priority: updatedNodeData.data.priority || 'p3',
                verification_pass_condition: updatedNodeData.data.verification_pass_condition || 'all',  // ✅ FIX: Store in data object
                is_root: updatedNodeData.data.is_root || false,
                isParentReference: updatedNodeData.data.isParentReference || false,
                originalTreeId: updatedNodeData.data.originalTreeId || '',
                // DO NOT include verifications here - they're already at top level
              },
            };

            console.log(`[@NavigationContext] Normalized node structure:`, {
              verifications: normalizedNode.verifications,
              dataHasVerifications: 'verifications' in normalizedNode.data
            });

            await navigationConfig?.saveNode(targetTreeId, normalizedNode as any);

            // UPDATE TREE CACHE: Keep cache synchronized with current state
            // For parent references, update the original tree cache
            // For regular nodes, update the current tree cache
            if (isParentReference && updatedNodeData.data.originalTreeId) {
              const originalChainIndex = parentChain.findIndex(t => t.treeId === updatedNodeData.data.originalTreeId);
              if (originalChainIndex !== -1) {
                const updatedOriginalNodes = parentChain[originalChainIndex].nodes.map((node: UINavigationNode) =>
                  node.id === updatedNodeData.id ? updatedNodeData : node
                );
                const newChain = [...parentChain];
                newChain[originalChainIndex] = {
                  ...newChain[originalChainIndex],
                  nodes: updatedOriginalNodes
                };
                setParentChain(newChain);
              }
            }
            
            const currentChainIndex = parentChain.findIndex(t => t.treeId === navigationConfig.actualTreeId);
            if (currentChainIndex !== -1) {
              const newChain = [...parentChain];
              newChain[currentChainIndex] = {
                ...newChain[currentChainIndex],
                nodes: nodes as UINavigationNode[],
                edges: edges as UINavigationEdge[]
              };
              setParentChain(newChain);
            }
            
            // ✅ UPDATE CACHE: Call server to update node cache on all hosts
            try {
              const nodeDataForCache = {
                id: updatedNodeData.id,
                node_id: updatedNodeData.id,
                label: updatedNodeData.data.label,
                node_type: updatedNodeData.type,
                description: updatedNodeData.data.description,
                screenshot: updatedNodeData.data.screenshot,
                verifications: updatedNodeData.data.verifications,
                position_x: currentPosition.x,
                position_y: currentPosition.y,
              };
              
              console.log('[@NavigationContext:saveNode] 🔄 Updating cache on all hosts...');
              console.log('[@NavigationContext:saveNode]   → Tree ID:', targetTreeId);
              console.log('[@NavigationContext:saveNode]   → Node ID:', updatedNodeData.id);
              
              const cacheResponse = await fetch(buildServerUrl(`/server/navigation/cache/update-node`), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  node: nodeDataForCache,
                  tree_id: targetTreeId
                })
              });
              
              if (cacheResponse.ok) {
                const cacheResult = await cacheResponse.json();
                console.log('[@NavigationContext:saveNode] ✅ Cache updated:', cacheResult.summary);
              } else {
                console.warn('[@NavigationContext:saveNode] ⚠️ Cache update failed (non-critical):', cacheResponse.statusText);
              }
            } catch (cacheError) {
              console.warn('[@NavigationContext:saveNode] ⚠️ Cache update error (non-critical):', cacheError);
            }
           }

          setIsNodeDialogOpen(false);
          setNodeForm({ label: '', type: 'screen', description: '', verifications: [] }); // Reset to initial empty form
          setSuccess('Node saved successfully');
          
          // Auto-clear success message after 3 seconds
          setTimeout(() => setSuccess(null), 3000);
         } catch (error) {
           console.error('Error saving node:', error);
           setError('Failed to save node changes');
           
           // Auto-clear error message after 5 seconds
           setTimeout(() => setError(null), 5000);
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

          // ✅ CONDITIONAL EDGE UNLINK: Only when editing FORWARD direction
          // Reverse direction (action_sets[1]) is ALWAYS independent - never triggers unlink
          const isConditionalEdge = currentSelectedEdge.data?.is_conditional || currentSelectedEdge.data?.is_conditional_primary;
          const isEditingForwardDirection = edgeForm.direction === 'forward' || !edgeForm.direction; // Default to forward if not specified
          
          if (isConditionalEdge && isEditingForwardDirection) {
            const sharedActionSetId = edgeForm.default_action_set_id;
            const siblingEdges = edges.filter(e => 
              e.source === currentSelectedEdge.source &&
              e.data?.default_action_set_id === sharedActionSetId &&
              e.id !== currentSelectedEdge.id
            );
            
            if (siblingEdges.length > 0) {
              console.log(`[@NavigationContext:saveEdge] 🔓 UNLINKING ${siblingEdges.length + 1} conditional edges (editing FORWARD direction)`);
              
              // UNLINK: Clear conditional flags for ALL siblings
              const unlinkedSiblings = siblingEdges.map(sibling => ({
                ...sibling,
                data: {
                  ...sibling.data,
                  is_conditional: false,
                  is_conditional_primary: false,
                }
              }));
              
              // Save each sibling to database with cleared flags
              for (const sibling of unlinkedSiblings) {
                const siblingNormalized = {
                  edge_id: sibling.id,
                  source_node_id: sibling.source,
                  target_node_id: sibling.target,
                  label: sibling.label,
                  data: {
                    priority: sibling.data?.priority || 'p3',
                    sourceHandle: sibling.sourceHandle,
                    targetHandle: sibling.targetHandle,
                    // Clear conditional flags
                    is_conditional: false,
                    is_conditional_primary: false,
                  },
                  action_sets: sibling.data.action_sets,
                  default_action_set_id: sibling.data.default_action_set_id,
                  final_wait_time: sibling.data.final_wait_time || 2000,
                };
                
                await navigationConfig?.saveEdge(navigationConfig?.actualTreeId || 'unknown', siblingNormalized as any);
                console.log(`[@NavigationContext:saveEdge] 🔓 Unlinked sibling: ${sibling.id}`);
              }
              
              // Update frontend state with unlinked siblings
              const updatedEdges = edges.map(e => {
                const unlinkedSibling = unlinkedSiblings.find(s => s.id === e.id);
                return unlinkedSibling || e;
              });
              setEdges(updatedEdges);
              
              // Generate new action_set_id for the edited edge to make it independent
              const newActionSetId = `${currentSelectedEdge.source}_to_${currentSelectedEdge.target}_${Date.now()}`;
              edgeForm.action_sets[0].id = newActionSetId;
              edgeForm.default_action_set_id = newActionSetId;
              console.log(`[@NavigationContext:saveEdge] 🔓 Created new action_set_id for edited edge: ${newActionSetId}`);
            }
          } else if (isConditionalEdge && !isEditingForwardDirection) {
            console.log(`[@NavigationContext:saveEdge] 📝 Editing REVERSE direction - no unlink needed (reverse is always independent)`);
          }

          // Update edge with form data
          const updatedEdge = {
            ...currentSelectedEdge,
            data: {
              ...(currentSelectedEdge.data || {}),
              action_sets: edgeForm.action_sets || [],
              default_action_set_id: edgeForm.default_action_set_id || 'default',
              final_wait_time: edgeForm.final_wait_time || 0,
              priority: edgeForm.priority || 'p3',
              threshold: edgeForm.threshold || 0,
            },
          };

                       // DATABASE FIRST: Save to database, then update frontend with server response
            if (navigationConfig?.actualTreeId) {
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
                // Clear conditional flags when editing (unlinking)
                is_conditional: false,
                is_conditional_primary: false,
              },
              // NEW: action_sets structure - NO LEGACY FIELDS
              action_sets: updatedEdge.data.action_sets || [],
              default_action_set_id: updatedEdge.data.default_action_set_id || 'default',
              final_wait_time: updatedEdge.data.final_wait_time || 0,
            };

             const saveResponse = await navigationConfig?.saveEdge(navigationConfig?.actualTreeId || 'unknown', normalizedEdge as any);
             
                           // Update frontend state with server response (source of truth)
              if (saveResponse && 'edge' in saveResponse) {
                const serverEdge = (saveResponse as any).edge;
                
                // Check if edge is conditional (preserve from server data)
                const isConditional = serverEdge.data?.is_conditional || serverEdge.data?.is_conditional_primary;
                
                const updatedEdgeFromServer: UINavigationEdge = {
                ...currentSelectedEdge,
                data: {
                  // Map server response to frontend data structure
                  action_sets: serverEdge.action_sets || [],
                  default_action_set_id: serverEdge.default_action_set_id || '',
                  final_wait_time: serverEdge.final_wait_time || 2000,
                  priority: serverEdge.data?.priority || 'p3',
                  // Preserve ReactFlow properties
                  sourceHandle: currentSourceHandle || undefined,
                  targetHandle: currentTargetHandle || undefined,
                  // Preserve conditional flags
                  ...(serverEdge.data?.is_conditional !== undefined && { is_conditional: serverEdge.data.is_conditional }),
                  ...(serverEdge.data?.is_conditional_primary !== undefined && { is_conditional_primary: serverEdge.data.is_conditional_primary }),
                },
                type: currentSelectedEdge.type || 'smoothstep', // Ensure type is never undefined
                label: typeof currentSelectedEdge.label === 'string' ? currentSelectedEdge.label : undefined,
                sourceHandle: currentSourceHandle || undefined,
                targetHandle: currentTargetHandle || undefined,
                // Apply conditional styling based on server data
                style: isConditional ? { stroke: '#2196f3', strokeWidth: 2 } : (currentSelectedEdge.style || { stroke: '#555', strokeWidth: 2 }),
                markerEnd: isConditional ? { type: 'arrowclosed' as const, color: '#2196f3' } : currentSelectedEdge.markerEnd,
              };
              
              // Update edges list with server data
              const updatedEdges = edges.map((edge) =>
                edge.id === currentSelectedEdge.id ? updatedEdgeFromServer : edge,
              );
              setEdges(updatedEdges);
              
              // Update selected edge with server data
              setSelectedEdge(updatedEdgeFromServer);
               
               // RELOAD EDGE FORM: Update edgeForm state with fresh data from server
               if (edgeForm && edgeForm.edgeId === currentSelectedEdge.id) {
                               const refreshedEdgeForm: EdgeForm = {
                edgeId: updatedEdgeFromServer.id,
                action_sets: updatedEdgeFromServer.data.action_sets,
                default_action_set_id: updatedEdgeFromServer.data.default_action_set_id,
                final_wait_time: updatedEdgeFromServer.data.final_wait_time || 2000,
                direction: edgeForm.direction, // Preserve current direction
              };
                 setEdgeForm(refreshedEdgeForm);
                 console.log('[@NavigationContext] Reloaded edge form with server data');
               }
               
               console.log('[@NavigationContext] Updated frontend state with server response');
               
              if (navigationConfig?.actualTreeId) {
                const currentChainIndex = parentChain.findIndex(t => t.treeId === navigationConfig.actualTreeId);
                if (currentChainIndex !== -1) {
                  const newChain = [...parentChain];
                  newChain[currentChainIndex] = {
                    ...newChain[currentChainIndex],
                    nodes: nodes as UINavigationNode[],
                    edges: updatedEdges as UINavigationEdge[]
                  };
                  setParentChain(newChain);
                }
                
                invalidateTree(navigationConfig.actualTreeId);
              }
             }

                          // ✅ UPDATE CACHE: Call server to update edge cache on all hosts
              try {
                const edgeDataForCache = {
                  id: updatedEdge.id,
                  edge_id: updatedEdge.id,
                  source_node_id: updatedEdge.source,
                  target_node_id: updatedEdge.target,
                  action_sets: updatedEdge.data.action_sets,
                  default_action_set_id: updatedEdge.data.default_action_set_id,
                  final_wait_time: updatedEdge.data.final_wait_time,
                };
                
                console.log('[@NavigationContext:saveEdge] 🔄 Updating cache on all hosts...');
                console.log('[@NavigationContext:saveEdge]   → Tree ID:', navigationConfig.actualTreeId);
                console.log('[@NavigationContext:saveEdge]   → Edge ID:', updatedEdge.id);
                
                const cacheResponse = await fetch(buildServerUrl(`/server/navigation/cache/update-edge`), {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({
                    edge: edgeDataForCache,
                    tree_id: navigationConfig.actualTreeId
                  })
                });
                
                if (cacheResponse.ok) {
                  const cacheResult = await cacheResponse.json();
                  console.log('[@NavigationContext:saveEdge] ✅ Cache updated:', cacheResult.summary);
                } else {
                  console.warn('[@NavigationContext:saveEdge] ⚠️ Cache update failed (non-critical):', cacheResponse.statusText);
                }
              } catch (cacheError) {
                console.warn('[@NavigationContext:saveEdge] ⚠️ Cache update error (non-critical):', cacheError);
              }
           }

           setIsEdgeDialogOpen(false);
           setSuccess('Edge saved successfully');
           
           // Auto-clear success message after 3 seconds
           setTimeout(() => setSuccess(null), 3000);
         } catch (error) {
           console.error('Error saving edge:', error);
           setError('Failed to save edge changes');
           
           // Auto-clear error message after 5 seconds
           setTimeout(() => setError(null), 5000);
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
          // DO NOT filter parent references - they are real nodes in the subtree with their own positions
          const nodesToSave = nodes; // Save all nodes including parent references
          
          console.log(`[@NavigationContext] Bulk saving tree with ${nodesToSave.length} nodes (all nodes including parent references)`);
          
          // Helper to compare if node has changed
          const hasNodeChanged = (node: any, initialNode: any) => {
            if (!initialNode) {
              console.log(`[@NavigationContext:hasNodeChanged] Node ${node.id} is NEW (not in initial state)`);
              return true; // New node
            }
            const posChanged = node.position?.x !== initialNode.position?.x || node.position?.y !== initialNode.position?.y;
            const labelChanged = node.data.label !== initialNode.data.label;
            const descChanged = node.data.description !== initialNode.data.description;
            const typeChanged = node.type !== initialNode.type;
            const screenshotChanged = node.data.screenshot !== initialNode.data.screenshot;
            const verificationsChanged = JSON.stringify(node.data.verifications) !== JSON.stringify(initialNode.data.verifications);
            
            // DETAILED LOGGING for debugging
            console.log(`[@NavigationContext:hasNodeChanged] Comparing node ${node.id} (${node.data.label}):`, {
              currentPos: `(${node.position?.x}, ${node.position?.y})`,
              initialPos: `(${initialNode.position?.x}, ${initialNode.position?.y})`,
              posChanged,
              labelChanged,
              descChanged,
              typeChanged,
              screenshotChanged,
              verificationsChanged
            });
            
            if (posChanged || labelChanged || descChanged || typeChanged || screenshotChanged || verificationsChanged) {
              return true;
            }
            return false;
          };
          
          // Helper to compare if edge has changed
          const hasEdgeChanged = (edge: any, initialEdge: any) => {
            if (!initialEdge) return true; // New edge
            return (
              edge.label !== initialEdge.label ||
              edge.source !== initialEdge.source ||
              edge.target !== initialEdge.target ||
              edge.sourceHandle !== initialEdge.sourceHandle ||
              edge.targetHandle !== initialEdge.targetHandle ||
              JSON.stringify(edge.data?.action_sets) !== JSON.stringify(initialEdge.data?.action_sets)
            );
          };
          
          // Create lookup maps for initial state - include all nodes (parent references are real nodes)
          const initialNodesMap = new Map(initialState?.nodes?.map(n => [n.id, n]) || []);
          const initialEdgesMap = new Map(initialState?.edges?.map(e => [e.id, e]) || []);
          
          console.log(`[@NavigationContext] Initial state has ${initialNodesMap.size} nodes and ${initialEdgesMap.size} edges`);
          console.log(`[@NavigationContext] Current state has ${nodesToSave.length} nodes and ${edges.length} edges`);
          
          // Filter to only changed nodes
          const changedNodes = nodesToSave.filter(node => {
            const initialNode = initialNodesMap.get(node.id);
            const changed = hasNodeChanged(node, initialNode);
            // Log every node comparison for debugging
            if (!changed) {
              console.log(`[@NavigationContext] Node ${node.id} (${node.data.label}) unchanged - pos: (${node.position?.x}, ${node.position?.y})`);
            }
            return changed;
          });
          console.log(`[@NavigationContext] Only saving ${changedNodes.length}/${nodesToSave.length} changed nodes`);
          
          const normalizedNodes = changedNodes.map(node => {
            const normalized = {
              node_id: node.id,
              label: node.data.label,
              position_x: node.position?.x || 0,
              position_y: node.position?.y || 0,
              node_type: node.type || 'screen', // Use ReactFlow type field
              verifications: node.data.verifications || [],
              data: {
                // Only include non-verification data to avoid duplication
                description: node.data.description,
                screenshot: node.data.screenshot,
                depth: node.data.depth,
                parent: node.data.parent,
                menu_type: node.data.menu_type,
                priority: node.data.priority,
                verification_pass_condition: node.data.verification_pass_condition || 'all', // ✅ FIX: Store in data object
                is_root: node.data.is_root,
                // CRITICAL: Preserve parent reference metadata (for blue primary sibling indicator in nested trees)
                isParentReference: node.data.isParentReference,
                originalTreeId: node.data.originalTreeId,
                // DO NOT include verifications here - they're already at top level
              }
            };
            console.log(`[@NavigationContext] Saving node ${node.id} (${node.data.label}) at position:`, { x: normalized.position_x, y: normalized.position_y });
            return normalized;
          });

          // Filter to only changed edges
          const changedEdges = edges.filter(edge => hasEdgeChanged(edge, initialEdgesMap.get(edge.id)));
          console.log(`[@NavigationContext] Only saving ${changedEdges.length}/${edges.length} changed edges`);
          
                    const normalizedEdges = changedEdges.map(edge => ({
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
              // Include conditional properties for persistence
              ...(edge.data?.is_conditional !== undefined && { is_conditional: edge.data.is_conditional }),
              ...(edge.data?.is_conditional_primary !== undefined && { is_conditional_primary: edge.data.is_conditional_primary }),
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
          await navigationConfig?.saveTreeData(treeId, normalizedNodes, normalizedEdges, deletedNodeIds, deletedEdgeIds, viewport);
           
          // CRITICAL: Invalidate frontend localStorage cache so refresh loads latest data
          navigationConfig?.invalidateAllTreeCache();
          
          // Invalidate preview cache (tree structure changed)
          invalidateTree(treeId);
          
          setInitialState({ 
            nodes: nodes as UINavigationNode[], 
            edges: edges as UINavigationEdge[] 
          });
          setHasUnsavedChanges(false);
           
          const currentChainIndex = parentChain.findIndex(t => t.treeId === treeId);
          if (currentChainIndex !== -1) {
            const newChain = [...parentChain];
            newChain[currentChainIndex] = {
              ...newChain[currentChainIndex],
              nodes: nodes as UINavigationNode[],
              edges: edges as UINavigationEdge[]
            };
            setParentChain(newChain);
          }
           
          setSuccess('Tree saved successfully');
          
          // Auto-clear success message after 3 seconds
          setTimeout(() => setSuccess(null), 3000);
         } catch (error) {
           console.error('Error saving tree:', error);
           setError('Failed to save tree');
           
           // Auto-clear error message after 5 seconds
           setTimeout(() => setError(null), 5000);
           throw error;
         } finally {
           setIsLoading(false);
         }
       },

       // NEW: Direction-specific deletion for edge panels
       deleteEdgeDirection: async (edgeId: string, actionSetId: string) => {
         try {
           setIsLoading(true);
           setError(null);

           console.log('[@NavigationContext] Deleting edge direction:', { edgeId, actionSetId });

           const edge = edges.find(e => e.id === edgeId);
           if (!edge) {
             throw new Error(`Edge ${edgeId} not found`);
           }

           // Inline direction deletion logic (from useEdge pattern)
           const actionSets = edge.data?.action_sets || [];
           
           // Determine direction from action set ID
           const forwardActionSetId = actionSets[0]?.id;
           const direction = actionSetId === forwardActionSetId ? 'forward' : 'reverse';
           const targetIndex = direction === 'forward' ? 0 : 1;

           // Clear actions but keep structure
           const updatedActionSets = [...actionSets];
           updatedActionSets[targetIndex] = {
             ...updatedActionSets[targetIndex],
             actions: [],
             retry_actions: [],
             failure_actions: []
           };

           // Create updated edge
           const updatedEdge = {
             ...edge,
             data: {
               ...edge.data,
               action_sets: updatedActionSets
             }
           };

           // Check if both directions are now empty
           const bothDirectionsEmpty = updatedActionSets.every(as => 
             (!as.actions || as.actions.length === 0) &&
             (!as.retry_actions || as.retry_actions.length === 0) &&
             (!as.failure_actions || as.failure_actions.length === 0)
           );

          if (bothDirectionsEmpty) {
            const filteredEdges = edges.filter(e => e.id !== edgeId);
            setEdges(filteredEdges);
            setSelectedEdge(null);
            setHasUnsavedChanges(true);
            
            if (navigationConfig?.actualTreeId) {
              const currentChainIndex = parentChain.findIndex(t => t.treeId === navigationConfig.actualTreeId);
              if (currentChainIndex !== -1) {
                const newChain = [...parentChain];
                newChain[currentChainIndex] = {
                  ...newChain[currentChainIndex],
                  nodes: nodes as UINavigationNode[],
                  edges: filteredEdges as UINavigationEdge[]
                };
                setParentChain(newChain);
              }
            }
          } else {
             // Update edge and save to database
             const edgeForm = {
               edgeId: updatedEdge.id,
               action_sets: updatedEdge.data.action_sets,
               default_action_set_id: updatedEdge.data.default_action_set_id,
               final_wait_time: updatedEdge.data.final_wait_time || 2000,
             };

             // Save to database and update frontend state
             console.log('[@NavigationContext] Saving updated edge to database');
             
             // Save to database
             const normalizedEdge = {
               edge_id: edgeForm.edgeId,
               source_node_id: edge.source,
               target_node_id: edge.target,
               label: edge.label,
               data: {
                 priority: edge.data?.priority || 'p3',
                 sourceHandle: edge.sourceHandle,
                 targetHandle: edge.targetHandle,
               },
               action_sets: edgeForm.action_sets,
               default_action_set_id: edgeForm.default_action_set_id,
               final_wait_time: edgeForm.final_wait_time,
             };

             const saveResponse = await navigationConfig?.saveEdge(navigationConfig?.actualTreeId || 'unknown', normalizedEdge as any);
             
                         // Update frontend state with server response
            if (saveResponse && 'edge' in saveResponse) {
              const serverEdge = (saveResponse as any).edge;
                             const updatedEdgeFromServer: UINavigationEdge = {
                ...edge,
                data: {
                  action_sets: serverEdge.action_sets || [],
                  default_action_set_id: serverEdge.default_action_set_id || '',
                  final_wait_time: serverEdge.final_wait_time || 2000,
                  priority: serverEdge.data?.priority || 'p3',
                  sourceHandle: edge.sourceHandle || undefined,
                  targetHandle: edge.targetHandle || undefined,
                },
                type: edge.type || 'smoothstep', // Ensure type is never undefined
                label: typeof edge.label === 'string' ? edge.label : undefined,
                sourceHandle: edge.sourceHandle || undefined,
                targetHandle: edge.targetHandle || undefined,
              };
              
              const updatedEdges = edges.map((e) =>
                e.id === edge.id ? updatedEdgeFromServer : e,
              );
              setEdges(updatedEdges);
              setSelectedEdge(updatedEdgeFromServer);
               
                             // RELOAD EDGE FORM: Update edgeForm state if it's currently editing this edge
              if (edgeForm && edgeForm.edgeId === edge.id) {
                const refreshedEdgeForm: EdgeForm = {
                  edgeId: updatedEdgeFromServer.id,
                  action_sets: updatedEdgeFromServer.data.action_sets,
                  default_action_set_id: updatedEdgeFromServer.data.default_action_set_id,
                  final_wait_time: updatedEdgeFromServer.data.final_wait_time || 2000,
                  direction: (edgeForm as any).direction, // Preserve current direction
                };
                setEdgeForm(refreshedEdgeForm);
              }
              
              if (navigationConfig?.actualTreeId) {
                const currentChainIndex = parentChain.findIndex(t => t.treeId === navigationConfig.actualTreeId);
                if (currentChainIndex !== -1) {
                  const newChain = [...parentChain];
                  newChain[currentChainIndex] = {
                    ...newChain[currentChainIndex],
                    nodes: nodes as UINavigationNode[],
                    edges: updatedEdges as UINavigationEdge[]
                  };
                  setParentChain(newChain);
                }
              }
             }

            console.log('[@NavigationContext] Updated edge direction and saved to database');
          }

         } catch (error) {
           console.error('[@NavigationContext] Error deleting edge direction:', error);
           setError(`Failed to delete edge direction: ${error instanceof Error ? error.message : 'Unknown error'}`);
           
           // Auto-clear error message after 5 seconds
           setTimeout(() => setError(null), 5000);
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
           const result = await fetch(buildServerUrl('/server/action/execute'), {
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
           
           // Auto-clear success message after 3 seconds
           setTimeout(() => setSuccess(null), 3000);
           return response;
         } catch (error) {
           console.error('Error executing actions:', error);
           setError('Failed to execute actions');
           
           // Auto-clear error message after 5 seconds
           setTimeout(() => setError(null), 5000);
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
