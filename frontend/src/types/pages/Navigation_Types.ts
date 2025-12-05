import { EdgeAction } from '../controller/Action_Types';

// Simple action interface for database storage (only command + params)
export interface Action {
  command: string;
  params: any;
  device_model?: string; // Optional device targeting
  action_type?: 'remote' | 'av' | 'power' | 'desktop' | 'web' | 'network' | 'timer' | 'verification'; // Optional: type of action (needed for verification UI)
  verification_type?: 'text' | 'image' | 'adb' | 'appium' | 'audio' | 'video'; // Optional: verification type for verification actions
  iterator?: number; // Optional: number of times to repeat this action (1-100, default: 1) - NOT used for verification actions
  continue_on_fail?: boolean; // Optional: continue execution even if this action fails (for non-mandatory actions like cookie popups)
}

// Action Set interface for bidirectional edge structure
export interface ActionSet {
  id: string; // Format: nodeA_to_nodeB
  label: string; // Format: nodeA → nodeB
  actions: Action[];
  retry_actions?: Action[];
  failure_actions?: Action[];
  priority?: number; // Priority for action set execution
  conditions?: Record<string, any>; // Conditions for action set execution
  timer?: number; // Timer in milliseconds
  
  // KPI Measurement fields (action_set-level)
  use_verifications_for_kpi?: boolean; // Use target node verifications for KPI
  kpi_references?: Verification[]; // OR separate KPI references
}
import { Verification } from '../verification/Verification_Types';

// Re-export EdgeAction for convenience
export type { EdgeAction };

// Navigation types are centralized in this file
// NavigationConfig_Types and NavigationContext_Types are imported where needed

// =====================================================
// CORE NAVIGATION TYPES
// =====================================================

// Define the data type for navigation nodes
export interface UINavigationNodeData {
  label: string;
  type: 'screen' | 'action' | 'menu' | 'entry';
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

  // Verification support (embedded directly - no ID resolution needed)
  verifications?: Verification[]; // Array of embedded verification objects
  verification_pass_condition?: 'all' | 'any'; // Condition for passing verifications: 'all' = all must pass (default), 'any' = any can pass

  // Nested tree properties
  has_subtree?: boolean; // True if this node has associated subtrees
  subtree_count?: number; // Number of subtrees linked to this node

  // Execution metrics
  metrics?: {
    volume: number;
    success_rate: number;
    avg_execution_time: number;
  };

  // Nested tree context (for parent node references)
  isParentReference?: boolean; // True if this node is a reference to a parent tree
  originalTreeId?: string; // Tree ID where this node actually lives
  currentTreeId?: string; // Tree ID where we're currently viewing it
  parentNodeId?: string; // Immediate parent node ID
}

// Define the data type for navigation edges - BIDIRECTIONAL STRUCTURE
export interface UINavigationEdgeData {
  label?: string; // Auto-generated label in format "source_label→target_label"
  action_sets: ActionSet[]; // REQUIRED: Always exactly 2 action sets (enforced by convention)
  default_action_set_id: string; // REQUIRED: Always source_to_target
  final_wait_time: number;
  priority?: 'p1' | 'p2' | 'p3'; // Priority level
  threshold?: number; // Threshold in milliseconds
  sourceHandle?: string; // ReactFlow source handle
  targetHandle?: string; // ReactFlow target handle
  is_conditional?: boolean; // Whether this edge is part of a conditional group (multiple edges sharing same FORWARD action)
  is_conditional_primary?: boolean; // Whether this edge is the PRIMARY edge in a conditional group (owns the actions, fully editable)
  // NOTE: Conditional edges only share FORWARD actions (action_sets[0]). Reverse actions (action_sets[1]) are independent.
  enable_sibling_shortcuts?: boolean; // Allow this edge to create sibling shortcuts for web/mobile DOM sharing (default: false)
  metrics?: {
    volume: number;
    success_rate: number;
    avg_execution_time: number;
  };
}

// =====================================================
// NESTED TREE TYPES
// =====================================================

export interface NavigationTree {
  id: string;
  name: string;
  userinterface_id: string;
  team_id: string;
  description?: string;
  parent_tree_id?: string;
  parent_node_id?: string;
  tree_depth: number;
  is_root_tree: boolean;
  root_node_id?: string;
  created_at: string;
  updated_at: string;
}

export interface TreeHierarchy {
  tree_id: string;
  tree_name: string;
  depth: number;
  parent_tree_id?: string;
  parent_node_id?: string;
}

export interface BreadcrumbItem {
  tree_id: string;
  tree_name: string;
  depth: number;
  node_id?: string;
}

export interface NavigationNode {
  node_id: string;
  label: string;
  node_type: string;
  position_x: number;
  position_y: number;
  verifications: Verification[]; // Embedded verifications
  verification_pass_condition?: 'all' | 'any'; // Condition for passing verifications
  data: any; // description goes in data.description
  
  // Optional fields
  screenshot?: string;
  menu_type?: string;
  has_subtree?: boolean; // Nested tree properties
  subtree_count?: number;
}

export interface NavigationEdge {
  edge_id: string;
  source_node_id: string;
  target_node_id: string;
  label?: string;
  data?: any;
  // NEW: Action sets structure - NO LEGACY FIELDS
  action_sets: ActionSet[]; // REQUIRED
  default_action_set_id: string; // REQUIRED
  final_wait_time: number;
}

// Nested tree operations interface
export interface NestedTreeOperations {
  loadNodeSubTrees: (treeId: string, nodeId: string) => Promise<NavigationTree[]>;
  createSubTree: (parentTreeId: string, parentNodeId: string, treeData: any) => Promise<NavigationTree>;
  getTreeHierarchy: (treeId: string) => Promise<TreeHierarchy[]>;
  getTreeBreadcrumb: (treeId: string) => Promise<BreadcrumbItem[]>;
  deleteTreeCascade: (treeId: string) => Promise<void>;
  moveSubtree: (subtreeId: string, newParentTreeId: string, newParentNodeId: string) => Promise<void>;
}

// =====================================================
// REACTFLOW TYPES
// =====================================================

// ReactFlow node type
export interface UINavigationNode {
  id: string;
  type: string;
  position: { x: number; y: number };
  data: UINavigationNodeData;
}

// ReactFlow edge type
export interface UINavigationEdge {
  id: string;
  source: string;
  target: string;
  type: string;
  label?: string; // Edge label - aligned with database column (not data.label)
  data: UINavigationEdgeData;
  sourceHandle?: string; // ReactFlow sourceHandle property
  targetHandle?: string; // ReactFlow targetHandle property
  animated?: boolean; // ReactFlow animated property
  style?: any; // ReactFlow style property
  markerEnd?: any; // ReactFlow marker property
  bidirectionalEdge?: UINavigationEdge; // Optional bidirectional edge (added by onEdgeClick)
}

// =====================================================
// NO LEGACY TYPES - ALL REMOVED
// =====================================================

// =====================================================
// ACTION AND VERIFICATION TYPES (embedded)
// =====================================================

// Action and Verification types are imported from their respective modules
// to avoid duplication and maintain consistency across the application

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
  type: 'screen' | 'menu' | 'entry' | 'action';
  description: string;
  screenshot?: string; // Preserve during editing

  // Form fields for TV menus
  depth?: number;
  parent?: string[];
  menu_type?: 'main' | 'submenu' | 'leaf';

  // Priority field
  priority?: 'p1' | 'p2' | 'p3'; // Priority level (default: p3)

  // Verifications field (embedded directly)
  verifications?: Verification[];
  verification_pass_condition?: 'all' | 'any'; // Condition for passing verifications: 'all' = all must pass (default), 'any' = any can pass
}

// EdgeForm interface for bidirectional edge structure
export interface EdgeForm {
  edgeId: string; // Required edge ID to track which edge is being edited
  action_sets: ActionSet[]; // REQUIRED: Always exactly 2 action sets (enforced by convention)
  default_action_set_id: string; // REQUIRED: Always source_to_target
  final_wait_time: number;
  direction?: 'forward' | 'reverse'; // Simple direction indicator for editing
  priority?: 'p1' | 'p2' | 'p3'; // Priority level
  threshold?: number; // Threshold in milliseconds
  enable_sibling_shortcuts?: boolean; // Allow this edge to create sibling shortcuts for web/mobile DOM sharing (default: false)
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
  actions: Action[];
  retryActions?: Action[];
  total_actions: number;
  total_retry_actions?: number;
  final_wait_time?: number;
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
  onUpdateNode?: (nodeId: string, updatedData: any) => void;
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
  actions: Action[];
  retryActions: Action[];
  finalWaitTime: number;
  onActionsChange: (actions: Action[]) => void;
  onRetryActionsChange: (retryActions: Action[]) => void;
  onFinalWaitTimeChange: (waitTime: number) => void;
  controllerTypes: string[];
  isControlActive?: boolean;
  selectedDevice?: string | null;
  selectedHost?: any;
}

export interface EdgeActionItemProps {
  action: Action;
  onUpdate: (updatedAction: Action) => void;
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
  external?: boolean; // If true, opens in new tab
  href?: string; // External URL (used when external is true)
}

export interface NavigationDropdownProps {
  label: string;
  items: NavigationItem[];
}

export interface NavigationGroupedItem {
  sectionLabel: string;
  items: NavigationItem[];
}

export interface NavigationGroupedDropdownProps {
  label: string;
  groups: NavigationGroupedItem[];
}

// =====================================================
// RE-EXPORT CONTEXT TYPES FROM SEPARATE FILES
// =====================================================

// Import and re-export NavigationConfig context types
export type {
  NavigationConfigContextType,
  NavigationConfigState,
  NavigationConfigProviderProps,
  TreeLockInfo,
  LockStatusResponse,
  TreeSaveRequest,
  TreeLoadResponse,
} from './NavigationConfig_Types';

// Import and re-export NavigationContext context types
export type {
  NavigationActionsContextType,
  NavigationActionsProviderProps,
  NavigationUIContextType,
  NavigationUIProviderProps,
  NavigationNodesContextType,
  NavigationNodesProviderProps,
  NavigationFlowContextType,
  NavigationFlowProviderProps,
  NavigationEditorProviderProps,
  NodeEdgeManagementContextType,
  NodeEdgeManagementProviderProps,
} from './NavigationContext_Types';
