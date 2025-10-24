/**
 * TestCase Builder Types
 * 
 * Defines the structure for visual testcase building with React Flow
 */

export enum BlockType {
  START = 'start',
  SUCCESS = 'success',
  FAILURE = 'failure',
  ACTION = 'action',
  VERIFICATION = 'verification',
  NAVIGATION = 'navigation',
  LOOP = 'loop'
}

export enum ConnectionType {
  SUCCESS = 'success',
  FAILURE = 'failure'
}

// Block data interfaces for each type
export interface ActionBlockData {
  command?: string;
  action_type?: string;
  params?: Record<string, any>;
  retry_actions?: any[];
  failure_actions?: any[];
  iterator?: number;
}

export interface VerificationBlockData {
  command?: string;
  verification_type?: string;
  reference?: string;
  threshold?: number;
  params?: Record<string, any>;
}

export interface NavigationBlockData {
  target_node_label?: string;
  target_node_id?: string;
}

export interface LoopBlockData {
  iterations: number;
  nested_graph?: TestCaseGraph; // Contains its own nodes/edges
}

// Base block interface
export interface TestCaseBlock {
  id: string;
  type: BlockType;
  position: { x: number; y: number };
  data: ActionBlockData | VerificationBlockData | NavigationBlockData | LoopBlockData | {};
}

// Connection between blocks
export interface TestCaseConnection {
  id: string;
  source: string;
  target: string;
  sourceHandle: 'success' | 'failure';
  targetHandle?: string;
  type: ConnectionType;
  style?: {
    stroke?: string;
    strokeWidth?: number;
  };
}

// Complete testcase graph
export interface TestCaseGraph {
  nodes: TestCaseBlock[];
  edges: TestCaseConnection[];
}

// Saved testcase (with metadata)
export interface SavedTestCase {
  id: string;
  name: string;
  description?: string;
  userinterface_name: string;
  graph: TestCaseGraph;
  created_at: string;
  updated_at: string;
  team_id: string;
}

// Execution-related types
export interface StepResult {
  step_number: number;
  block_id: string;
  block_type: BlockType;
  success: boolean;
  message?: string;
  error?: string;
  execution_time_ms: number;
  screenshot_path?: string;
  timestamp: number;
}

export interface ExecutionResult {
  success: boolean;
  current_step: number;
  total_steps: number;
  step_results: StepResult[];
  execution_time_ms: number;
  report_url?: string;
  error?: string;
}

export interface ExecutionState {
  isExecuting: boolean;
  currentBlockId: string | null;
  result: ExecutionResult | null;
}

// Form data for block configuration
export interface ActionForm extends ActionBlockData {
  isValid: boolean;
}

export interface VerificationForm extends VerificationBlockData {
  isValid: boolean;
}

export interface NavigationForm extends NavigationBlockData {
  isValid: boolean;
}

export interface LoopForm extends LoopBlockData {
  isValid: boolean;
}

