import { Node, Edge } from 'reactflow';

import { EdgeAction } from '../controller/Action_Types';
import { Verification } from '../verification/Verification_Types';

// Re-export EdgeAction for use in navigation components
export type { EdgeAction };

// Navigation types are centralized in this file
// NavigationConfig_Types and NavigationContext_Types are imported where needed

// =====================================================
// CORE NAVIGATION TYPES
// =====================================================

// Define the data type for navigation nodes
export interface UINavigationNodeData {
  label: string;
  type: 'screen' | 'dialog' | 'popup' | 'overlay' | 'menu' | 'entry';
  screenshot?: string;
  screenshot_timestamp?: number; // Timestamp for forcing image refresh after screenshot updates
  description?: string;
  is_root?: boolean; // True only for the first entry node
  tree_id?: string; // For menu nodes, references the associated tree
  tree_name?: string; // For menu nodes, the name of the associated tree

  // Simple parent chain approach
  parent?: string[]; // ["home", "tvguide"] - array of parent node IDs
  depth?: number; // parent?.length || 0

  is_loaded?: boolean; // Whether this node's children have been loaded
  has_children?: boolean; // Whether this node has child nodes
  child_count?: number; // Number of direct children
  menu_type?: 'main' | 'submenu' | 'leaf'; // Type of menu node

  // Priority field
  priority?: 'p1' | 'p2' | 'p3'; // Priority level (default: p3)

  // Verification support
  verifications?: Verification[]; // Array of full verification objects for UI display (loaded from DB via verification_ids)
  verification_ids?: string[]; // Array of verification database IDs for persistence (saved to tree)

  // Execution metrics
  metrics?: {
    volume: number;
    success_rate: number;
    avg_execution_time: number;
  };
}

// Define the navigation node type using ReactFlow's Node with our data type
export type UINavigationNode = Node<UINavigationNodeData>;

// =====================================================
// NAVIGATION EDGE ACTION TYPES
// =====================================================

// EdgeAction is now imported from Action_Types.ts to avoid duplication

// Define the data type for navigation edges
export interface UINavigationEdgeData {
  actions?: EdgeAction[]; // Array of actions for UI display (loaded from DB via action_ids)
  action_ids?: string[]; // Array of action database IDs for persistence (saved to tree)
  retryActions?: EdgeAction[]; // Array of retry actions for UI display (loaded from DB via retry_action_ids)
  retry_action_ids?: string[]; // Array of retry action database IDs for persistence (saved to tree)
  finalWaitTime?: number; // Wait time after all actions
  description?: string;
  from?: string; // Source node label
  to?: string; // Target node label
  edgeType?: 'horizontal' | 'vertical'; // For edge coloring: horizontal=siblings, vertical=parent-child

  // Priority and threshold fields
  priority?: 'p1' | 'p2' | 'p3'; // Priority level (default: p3)
  threshold?: number; // Threshold in milliseconds (default: 0)

  // Execution metrics
  metrics?: {
    volume: number;
    success_rate: number;
    avg_execution_time: number;
  };
}

// Use ReactFlow's Edge type with our custom data
export type UINavigationEdge = Edge<UINavigationEdgeData>;

export interface NavigationTreeData {
  nodes: UINavigationNode[];
  edges: UINavigationEdge[];

  root_node_id?: string; // ID of the root node
  metadata?: {
    tv_interface_type?: 'android_tv' | 'fire_tv' | 'apple_tv' | 'generic';
    remote_type?: string;
  };
}

// =====================================================
// FORM TYPES
// =====================================================

export interface NodeForm {
  id?: string; // Node identification
  label: string;
  type: 'screen' | 'dialog' | 'popup' | 'overlay' | 'menu' | 'entry';
  description: string;
  screenshot?: string; // Preserve during editing

  // Form fields for TV menus
  depth?: number;
  parent?: string[];
  menu_type?: 'main' | 'submenu' | 'leaf';

  // Priority field
  priority?: 'p1' | 'p2' | 'p3'; // Priority level (default: p3)

  // Verifications field to preserve during editing
  verifications?: Verification[];
  verification_ids?: string[]; // Database IDs for persistence
}

// Updated EdgeForm interface for multiple actions
export interface EdgeForm {
  edgeId: string; // Required edge ID to track which edge is being edited
  actions: EdgeAction[];
  retryActions: EdgeAction[];
  finalWaitTime: number;
  description: string;

  // Priority and threshold fields
  priority?: 'p1' | 'p2' | 'p3'; // Priority level (default: p3)
  threshold?: number; // Threshold in milliseconds (default: 0)
}

// =====================================================
// NAVIGATION EXECUTION TYPES
// =====================================================

export interface NavigationStep {
  transition_number: number;
  from_node_id: string;
  to_node_id: string;
  from_node_label: string;
  to_node_label: string;
  actions: EdgeAction[];
  retryActions?: EdgeAction[];
  total_actions: number;
  total_retry_actions?: number;
  finalWaitTime?: number;
  description: string;
}

export interface NavigationPreviewResponse {
  success: boolean;
  error?: string;
  tree_id: string;
  target_node_id: string;
  current_node_id: string;
  navigation_type: string;
  transitions: NavigationStep[]; // Server uses 'transitions' - keep consistent
  total_transitions: number;
  total_actions: number;
}

export interface NavigationExecuteResponse {
  success: boolean;
  error?: string;
  message?: string;
  tree_id: string;
  target_node_id: string;
  current_node_id?: string;
  final_position_node_id?: string; // Where we actually ended up after navigation
  transitions_executed: number;
  total_transitions: number;
  actions_executed: number;
  total_actions: number;
  execution_time: number;
  verification_results?: any[];
  navigation_path?: string[];
}

export interface ActionExecutionResult {
  results: string[];
  executionStopped: boolean;
  updatedActions: any[];
  updatedRetryActions?: any[];
}

// =====================================================
// CONTROLLER & ACTION TYPES
// =====================================================

export interface ControllerAction {
  id: string;
  label: string;
  command: string;
  params: any;
  description: string;
  requiresInput?: boolean;
  inputLabel?: string;
  inputPlaceholder?: string;
}

export interface ControllerActions {
  [controllerType: string]: ControllerAction[];
}

// =====================================================
// CONNECTION & HOOK TYPES
// =====================================================

export interface ConnectionResult {
  isAllowed: boolean;
  reason?: string;
  edgeType: 'horizontal' | 'vertical';
  sourceNodeUpdates?: Partial<UINavigationNodeData>;
  targetNodeUpdates?: Partial<UINavigationNodeData>;
}

export interface NodeEdgeManagementProps {
  nodes: UINavigationNode[];
  edges: UINavigationEdge[];
  selectedNode: UINavigationNode | null;
  selectedEdge: UINavigationEdge | null;
  nodeForm: any;
  edgeForm: any;
  isNewNode: boolean;
  setNodes: (nodes: any) => void;
  setEdges: (edges: any) => void;
  setSelectedNode: (node: UINavigationNode | null) => void;
  setSelectedEdge: (edge: UINavigationEdge | null) => void;
  setNodeForm: (form: any) => void;
  setEdgeForm: (form: any) => void;
  setIsNodeDialogOpen: (isOpen: boolean) => void;
  setIsEdgeDialogOpen: (isOpen: boolean) => void;
  setIsNewNode: (isNew: boolean) => void;
  setHasUnsavedChanges: (hasChanges: boolean) => void;
}

// =====================================================
// COMPONENT PROPS TYPES
// =====================================================

export interface NavigationEditorHeaderProps {
  // Navigation state
  navigationPath: string[];
  navigationNamePath: string[];
  viewPath: { id: string; name: string }[];
  hasUnsavedChanges: boolean;

  // Tree filtering props
  focusNodeId: string | null;
  availableFocusNodes: { id: string; label: string; depth: number }[];
  maxDisplayDepth: number;
  totalNodes: number;
  visibleNodes: number;

  // Loading and error states
  isLoading: boolean;
  error: string | null;

  // Lock management props
  isLocked?: boolean;
  lockInfo?: any;
  sessionId?: string;

  // Remote control props
  isRemotePanelOpen: boolean;
  selectedDevice: string | null;
  isControlActive: boolean;

  // User interface props
  userInterface: any;

  // Device props
  devicesLoading?: boolean;

  // Validation props
  treeId: string;

  // Action handlers
  onNavigateToParent: () => void;
  onNavigateToTreeLevel: (index: number) => void;
  onNavigateToParentView: (index: number) => void;
  onAddNewNode: (nodeType: string, position: { x: number; y: number }) => void;
  onFitView: () => void;
  onSaveToConfig?: (treeName: string) => void;
  onLockTree?: (treeName: string) => void;
  onUnlockTree?: (treeName: string) => void;
  onDiscardChanges: () => void;

  // Tree filtering handlers
  onFocusNodeChange: (nodeId: string | null) => void;
  onDepthChange: (depth: number) => void;
  onResetFocus: () => void;

  // Remote control handlers
  onToggleRemotePanel: () => void;
  onDeviceSelect: (device: string | null) => void;
  onTakeControl: () => void;

  // Update handlers for validation confidence tracking
  onUpdateNode?: (nodeId: string, updatedData: any) => void;
  onUpdateEdge?: (edgeId: string, updatedData: any) => void;
}

export interface NodeEditDialogProps {
  isOpen: boolean;
  nodeForm: NodeForm | null;
  nodes: UINavigationNode[];
  setNodeForm: (form: NodeForm | null) => void;
  onSubmit: () => void;
  onClose: () => void;
  onResetNode?: () => void;
  selectedHost?: any; // Host object for verification/navigation
  selectedDeviceId?: string; // Device ID for getting model references
  isControlActive?: boolean;
  model?: string;
}

export interface EdgeEditDialogProps {
  isOpen: boolean;
  edgeForm: EdgeForm | null;
  setEdgeForm: (form: EdgeForm | null) => void;
  onSubmit: () => void;
  onClose: () => void;
  controllerTypes?: string[];
  selectedEdge?: UINavigationEdge | null;
  isControlActive?: boolean;
  selectedDevice?: string | null;
  selectedHost?: any;
}

export interface NodeSelectionPanelProps {
  selectedNode: UINavigationNode;
  nodes: UINavigationNode[];
  onClose: () => void;
  onEdit: () => void;
  onDelete: () => void;
  onAddChildren: () => void;
  setNodeForm: React.Dispatch<React.SetStateAction<NodeForm>>;
  setIsNodeDialogOpen: (open: boolean) => void;
  onReset?: (id: string) => void;
  onUpdateNode?: (nodeId: string, updatedData: any) => void;
  // Device control props
  isControlActive?: boolean;
  selectedHost?: any; // Full host object for API calls
  onSaveScreenshot?: () => void;
  // Navigation props
  treeId?: string;
  currentNodeId?: string;
}

export interface EdgeSelectionPanelProps {
  selectedEdge: UINavigationEdge;
  onClose: () => void;
  onEdit: () => void;
  onDelete: () => void;
  setEdgeForm: (form: EdgeForm | null) => void;
  setIsEdgeDialogOpen: (open: boolean) => void;
  isControlActive?: boolean;
  selectedDevice?: string | null;
  controllerTypes?: string[];
  onUpdateEdge?: (edgeId: string, updatedData: any) => void;
}

export interface NodeGotoPanelProps {
  selectedNode: UINavigationNode;
  treeId: string;
  currentNodeId?: string;
  onClose: () => void;
  isControlActive?: boolean;
  selectedDevice?: string | null;
}

export interface TreeFilterControlsProps {
  focusNodeId: string | null;
  availableFocusNodes: { id: string; label: string; depth: number }[];
  maxDisplayDepth: number;
  totalNodes: number;
  visibleNodes: number;
  onFocusNodeChange: (nodeId: string | null) => void;
  onDepthChange: (depth: number) => void;
  onResetFocus: () => void;
}

export interface StatusMessagesProps {
  isLoading: boolean;
  error: string | null;
}

export interface NavigationToolbarProps {
  onAddNewNode: (nodeType: string, position: { x: number; y: number }) => void;
  onFitView: () => void;
  onSave: () => void;
  onUndo?: () => void;
  onRedo?: () => void;
  canUndo?: boolean;
  canRedo?: boolean;
  hasUnsavedChanges: boolean;
  isLocked?: boolean;
}

// =====================================================
// LIST COMPONENT PROPS TYPES
// =====================================================

export interface EdgeActionsListProps {
  actions: EdgeAction[];
  retryActions: EdgeAction[];
  finalWaitTime: number;
  onActionsChange: (actions: EdgeAction[]) => void;
  onRetryActionsChange: (retryActions: EdgeAction[]) => void;
  onFinalWaitTimeChange: (waitTime: number) => void;
  controllerTypes: string[];
  isControlActive?: boolean;
  selectedDevice?: string | null;
  selectedHost?: any;
}

export interface EdgeActionItemProps {
  action: EdgeAction;
  onUpdate: (updatedAction: EdgeAction) => void;
  onDelete: () => void;
  controllerTypes: string[];
  isControlActive?: boolean;
  selectedDevice?: string | null;
  selectedHost?: any;
}

export interface VerificationsListProps {
  verifications: Verification[];
  availableVerifications: import('../verification/Verification_Types').Verifications;
  onVerificationsChange: (verifications: Verification[]) => void;
  loading?: boolean;
  error?: string | null;
  model?: string;
  onTest?: () => void;
  testResults?: Verification[];
  reloadTrigger?: number;
  onReferenceSelected?: (referenceName: string, referenceData: any) => void;
  selectedHost: import('../common/Host_Types').Host | null;
  modelReferences: import('../verification/Verification_Types').ModelReferences;
  referencesLoading: boolean;
}

export interface NodeVerificationsListProps {
  verifications: Verification[];
  availableVerifications: import('../verification/Verification_Types').Verifications;
  onVerificationsChange: (verifications: Verification[]) => void;
  loading?: boolean;
  error?: string | null;
  model?: string;
  onTest?: () => void;
  testResults?: Verification[];
  reloadTrigger?: number;
  onReferenceSelected?: (referenceName: string, referenceData: any) => void;
  selectedHost: import('../common/Host_Types').Host | null;
  modelReferences: import('../verification/Verification_Types').ModelReferences;
  referencesLoading: boolean;
}

// =====================================================
// NAVIGATION UI COMPONENT TYPES
// =====================================================

export interface NavigationItem {
  label: string;
  path: string;
  icon?: React.ReactNode;
}

export interface NavigationDropdownProps {
  label: string;
  items: NavigationItem[];
}
