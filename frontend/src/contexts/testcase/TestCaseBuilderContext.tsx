import React, { createContext, useContext, useState, useCallback, ReactNode, useEffect, useRef, useMemo } from 'react';
import { Node, Edge, addEdge, Connection, NodeChange, EdgeChange, applyNodeChanges, applyEdgeChanges } from 'reactflow';
import { BlockType, ExecutionState, TestCaseGraph } from '../../types/testcase/TestCase_Types';
import { 
  useTestCaseSave, 
  useTestCaseExecution,
  useTestCaseBuilder as useTestCaseBuilderHook,
  useExecutionState, // 🆕 ADD
  type NavigationNode,
  type UserInterface,
  type ActionCommand
} from '../../hooks/testcase';

interface TestCaseBuilderContextType {
  // Graph state
  nodes: Node[];
  edges: Edge[];
  setNodes: React.Dispatch<React.SetStateAction<Node[]>>;
  setEdges: React.Dispatch<React.SetStateAction<Edge[]>>;
  
  // Test case metadata
  testcaseName: string;
  setTestcaseName: React.Dispatch<React.SetStateAction<string>>;
  description: string;
  setDescription: React.Dispatch<React.SetStateAction<string>>;
  testcaseEnvironment: string;
  setTestcaseEnvironment: React.Dispatch<React.SetStateAction<string>>;
  userinterfaceName: string;
  setUserinterfaceName: React.Dispatch<React.SetStateAction<string>>;
  currentTestcaseId: string | null;
  setCurrentTestcaseId: React.Dispatch<React.SetStateAction<string | null>>;
  
  // Unsaved changes tracking
  hasUnsavedChanges: boolean;
  setHasUnsavedChanges: React.Dispatch<React.SetStateAction<boolean>>;
  
  // Test case list
  testcaseList: any[];
  setTestcaseList: React.Dispatch<React.SetStateAction<any[]>>;
  isLoadingTestCaseList: boolean;
  
  // Available options
  availableInterfaces: UserInterface[];
  availableNodes: NavigationNode[];
  availableActions: ActionCommand[];
  availableVerifications: any[];
  isLoadingOptions: boolean;
  
  // Selected elements
  selectedBlock: Node | null;
  setSelectedBlock: React.Dispatch<React.SetStateAction<Node | null>>;
  
  // Dialogs
  isConfigDialogOpen: boolean;
  setIsConfigDialogOpen: React.Dispatch<React.SetStateAction<boolean>>;
  
  // Execution state
  executionState: ExecutionState;
  setExecutionState: React.Dispatch<React.SetStateAction<ExecutionState>>;
  
  // 🆕 ADD: Unified execution state
  unifiedExecution: ReturnType<typeof useExecutionState>;
  
  // Validation
  isExecutable: boolean;
  
  // Actions
  addBlock: (type: BlockType | string, position: { x: number; y: number }, defaultData?: any) => void;
  updateBlock: (blockId: string, data: any) => void;
  deleteBlock: (blockId: string) => void;
  onNodesChange: (changes: NodeChange[]) => void;
  onEdgesChange: (changes: EdgeChange[]) => void;
  onConnect: (connection: Connection) => void;
  
  // API Actions
  saveCurrentTestCase: () => Promise<{ success: boolean; error?: string }>;
  loadTestCase: (testcase_id: string) => Promise<void>;
  executeCurrentTestCase: (hostName: string) => Promise<void>;
  fetchTestCaseList: () => Promise<void>;
  deleteTestCaseById: (testcase_id: string) => Promise<void>;
  resetBuilder: () => void;
  fetchNavigationNodes: (interfaceName: string) => Promise<void>;
}

const TestCaseBuilderContext = createContext<TestCaseBuilderContextType | undefined>(undefined);

export const useTestCaseBuilder = () => {
  const context = useContext(TestCaseBuilderContext);
  if (!context) {
    throw new Error('useTestCaseBuilder must be used within TestCaseBuilderProvider');
  }
  return context;
};

interface TestCaseBuilderProviderProps {
  children: ReactNode;
}

export const TestCaseBuilderProvider: React.FC<TestCaseBuilderProviderProps> = ({ children }) => {
  // Use testcase hooks (following Navigation pattern)
  const { saveTestCase, listTestCases, getTestCase, deleteTestCase } = useTestCaseSave();
  const { executeTestCase } = useTestCaseExecution();
  const { 
    getUserInterfaces, 
    getNavigationNodesForInterface, 
    getAvailableActions, 
    getAvailableVerifications 
  } = useTestCaseBuilderHook();
  
  // 🆕 ADD: Unified execution state management
  const unifiedExecution = useExecutionState();
  
  // Initialize with start, success, and failure blocks
  // START at top center, SUCCESS at bottom-left, FAILURE at bottom-right
  const [nodes, setNodes] = useState<Node[]>([
    {
      id: 'start',
      type: 'start',
      position: { x: 400, y: 50 },  // Top center
      data: {},
      deletable: false,  // Cannot be deleted
    },
    {
      id: 'success',
      type: 'success',
      position: { x: 250, y: 550 },  // Bottom left (shifted 50px right)
      data: {},
      deletable: false,  // Cannot be deleted
    },
    {
      id: 'failure',
      type: 'failure',
      position: { x: 550, y: 550 },  // Bottom right (shifted 50px left)
      data: {},
      deletable: false,  // Cannot be deleted
    },
  ]);
  
  const [edges, setEdges] = useState<Edge[]>([]);
  const [selectedBlock, setSelectedBlock] = useState<Node | null>(null);
  const [isConfigDialogOpen, setIsConfigDialogOpen] = useState(false);
  const [executionState, setExecutionState] = useState<ExecutionState>({
    isExecuting: false,
    currentBlockId: null,
    result: null,
  });
  
  // Test case metadata
  const [testcaseName, setTestcaseName] = useState<string>('');
  const [description, setDescription] = useState<string>('');
  const [testcaseEnvironment, setTestcaseEnvironment] = useState<string>('dev');
  const [userinterfaceName, setUserinterfaceName] = useState<string>('');
  const [currentTestcaseId, setCurrentTestcaseId] = useState<string | null>(null);
  const [testcaseList, setTestcaseList] = useState<any[]>([]);
  const [isLoadingTestCaseList, setIsLoadingTestCaseList] = useState(false);
  
  // Unsaved changes tracking
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  
  // Available options for dropdowns
  const [availableInterfaces, setAvailableInterfaces] = useState<UserInterface[]>([]);
  const [availableNodes, setAvailableNodes] = useState<NavigationNode[]>([]);
  const [availableActions, setAvailableActions] = useState<ActionCommand[]>([]);
  const [availableVerifications, setAvailableVerifications] = useState<any[]>([]);
  const [isLoadingOptions, setIsLoadingOptions] = useState<boolean>(false);

  // Validation: Check if START is connected to any executable blocks
  const isExecutable = useMemo(() => {
    // Find the START node
    const startNode = nodes.find(n => n.type === 'start');
    if (!startNode) return false;
    
    // Check if START has any outgoing edges
    const startEdges = edges.filter(e => e.source === startNode.id);
    if (startEdges.length === 0) return false;
    
    // Check if any edge connects to an executable block (not SUCCESS/FAILURE)
    const hasExecutableConnection = startEdges.some(edge => {
      const targetNode = nodes.find(n => n.id === edge.target);
      return targetNode && !['success', 'failure', 'start'].includes(targetNode.type || '');
    });
    
    return hasExecutableConnection;
  }, [nodes, edges]);

  // ID generation now uses crypto.randomUUID for nodes and edges
  
  // Block counters for auto-labeling (tracks count per type)
  const blockCounters = useRef<Record<string, number>>({});

  // Add a new block to the canvas
  const addBlock = useCallback((type: BlockType | string, position: { x: number; y: number }, defaultData?: any) => {
    // Determine the group/category for labeling
    let labelGroup = type;
    
    // Map specific types to their category for consistent labeling
    if (['press_key', 'press_sequence', 'tap', 'swipe', 'type_text'].includes(type)) {
      labelGroup = 'action';
    } else if (['verify_image', 'verify_ocr', 'verify_audio', 'verify_element'].includes(type)) {
      labelGroup = 'verification';
    } else if (type === 'navigation') {
      labelGroup = 'navigation';
    } else if (['sleep', 'get_current_time', 'condition', 'set_variable', 'loop'].includes(type)) {
      labelGroup = 'standard';
    }
    
    // Increment counter for this group
    if (!blockCounters.current[labelGroup]) {
      blockCounters.current[labelGroup] = 0;
    }
    blockCounters.current[labelGroup]++;
    
    // Extract first 3 words from command/type for the label
    // For navigation blocks, use target_node_label if available
    const commandName = (type === 'navigation' && defaultData?.target_node_label) 
      ? defaultData.target_node_label 
      : (defaultData?.command || type);
    const words = commandName
      .split(/[_\s]+/) // Split by underscore or space
      .filter(Boolean) // Remove empty strings
      .slice(0, 3) // Take first 3 words
      .join('_'); // Join with underscore
    
    // Generate auto-label (e.g., "action_1:swipe_up", "navigation_1:home")
    const autoLabel = words 
      ? `${labelGroup}_${blockCounters.current[labelGroup]}:${words}`
      : `${labelGroup}_${blockCounters.current[labelGroup]}`;
    
    const newNode: Node = {
      id: crypto.randomUUID(),
      type,
      position,
      data: {
        ...defaultData,
        // For navigation blocks, use block_label to avoid overwriting target_node_label
        // For all other blocks, use label as expected
        ...(type === 'navigation' ? { block_label: autoLabel } : { label: autoLabel }),
      },
    };
    setNodes((prev) => [...prev, newNode]);
    setHasUnsavedChanges(true);
  }, []);

  // Update block data
  const updateBlock = useCallback((blockId: string, data: any) => {
    setNodes((prev) =>
      prev.map((node) =>
        node.id === blockId ? { ...node, data: { ...node.data, ...data } } : node
      )
    );
    setHasUnsavedChanges(true);
  }, []);

  // Delete a block
  const deleteBlock = useCallback((blockId: string) => {
    setNodes((prev) => prev.filter((node) => node.id !== blockId));
    setEdges((prev) => prev.filter((edge) => edge.source !== blockId && edge.target !== blockId));
    setHasUnsavedChanges(true);
  }, []);

  // Handle node changes (drag, select, etc.)
  const onNodesChange = useCallback((changes: NodeChange[]) => {
    setNodes((prev) => applyNodeChanges(changes, prev));
    
    // Track position changes as unsaved changes (when drag completes)
    const hasPositionChange = changes.some((change: any) => 
      change.type === 'position' && change.dragging === false
    );
    if (hasPositionChange) {
      setHasUnsavedChanges(true);
    }
  }, []);

  // Handle edge changes
  const onEdgesChange = useCallback((changes: EdgeChange[]) => {
    setEdges((prev) => applyEdgeChanges(changes, prev));
    
    // Track edge removal as unsaved changes
    const hasRemoval = changes.some((change: any) => change.type === 'remove');
    if (hasRemoval) {
      setHasUnsavedChanges(true);
    }
  }, []);

  // Handle connections
  const onConnect = useCallback((connection: Connection) => {
    // RULE: Each source handle can only have ONE outgoing connection
    // If a connection from the same source handle exists, remove it first
    const sourceNodeId = connection.source;
    const sourceHandleId = connection.sourceHandle || 'success';
    
    // Remove any existing edge from the same source handle
    setEdges((prev) => {
      const filteredEdges = prev.filter(edge => 
        !(edge.source === sourceNodeId && edge.sourceHandle === sourceHandleId)
      );
      
      // Determine edge type and color based on source handle
      // Support: success, failure, true, false, complete, break
      // Strip "-hitarea" suffix if present (hitarea handles should use same type as their visible counterpart)
      let edgeType = sourceHandleId.replace(/-hitarea$/, '');
      let edgeColor = '#6b7280'; // default gray
      
      // Map handle types to colors
      switch (edgeType) {
        case 'success':
        case 'true':
        case 'complete':
          edgeColor = '#10b981'; // green
          break;
        case 'failure':
        case 'false':
          edgeColor = '#ef4444'; // red
          break;
        case 'break':
          edgeColor = '#f59e0b'; // orange/yellow
          break;
      }
      
      const newEdge: Edge = {
        ...connection,
        id: crypto.randomUUID(),
        type: edgeType,
        source: connection.source!,
        target: connection.target!,
        sourceHandle: sourceHandleId,
        style: { stroke: edgeColor, strokeWidth: 2 },
      };
      
      return addEdge(newEdge, filteredEdges);
    });
    
    setHasUnsavedChanges(true);
  }, []);

  // Execute testcase
  const executeCurrentTestCase = useCallback(async (hostName: string) => {
    // DEBUG: Check nodes state before execution
    console.log('[@TestCaseBuilder] Pre-execution nodes check:', {
      nodesCount: nodes.length,
      nodeIds: nodes.map(n => n.id),
      duplicates: nodes.map(n => n.id).filter((id, index, arr) => arr.indexOf(id) !== index)
    });
    
    // 🛡️ SAFEGUARD: Rename duplicate nodes with new UUIDs
    const seenIds = new Set<string>();
    const uniqueNodes = nodes.map(node => 
      seenIds.has(node.id) ? { ...node, id: crypto.randomUUID() } : (seenIds.add(node.id), node)
    );
    
    // Build graph from current state - NO SAVE REQUIRED
    const graph: TestCaseGraph = {
      nodes: uniqueNodes.map(node => ({
        id: node.id,
        type: node.type as BlockType,
        position: node.position,
        data: node.data || {}
      })),
      edges: edges.map(edge => ({
        id: edge.id!,
        source: edge.source,
        target: edge.target,
        sourceHandle: edge.sourceHandle as 'success' | 'failure',
        type: (edge.type === 'success' || edge.type === 'failure') ? edge.type : 'success' as any
      }))
    };
    
    // DEBUG: Log execution graph
    console.log('[@TestCaseBuilder] Executing with graph:', {
      nodes: graph.nodes.length,
      edges: graph.edges.length,
      nodeIds: graph.nodes.map(n => n.id),
      edgeDetails: graph.edges
    });
    
    // 🆕 ADD: Initialize unified execution state
    const blockIds = nodes.filter(n => !['start', 'success', 'failure'].includes(n.type || '')).map(n => n.id);
    unifiedExecution.startExecution('test_case', blockIds);
    
    // ✅ KEEP: Legacy execution state (for backwards compatibility)
    setExecutionState({
      isExecuting: true,
      currentBlockId: 'start',
      result: null,
    });

    try {
      // Execute with async polling and real-time progress updates
      const response = await executeTestCase(
        graph,
        'device1',
        hostName,
        userinterfaceName,
        // Real-time progress callback
        (status) => {
          // Update current block ID
          if (status.current_block_id) {
            setExecutionState(prev => ({
              ...prev,
              currentBlockId: status.current_block_id
            }));
          }
          
          // Update block states in real-time
          Object.entries(status.block_states).forEach(([blockId, blockState]) => {
            unifiedExecution.updateBlockState(blockId, {
              status: blockState.status,
              duration: blockState.duration,
              error: blockState.error,
              result: blockState
            });
          });
          
          console.log(`[TestCaseBuilder] Progress: ${status.status}, block: ${status.current_block_id}, elapsed: ${status.elapsed_time_ms}ms`);
        }
      );
      
      // 🆕 PROCESS step_results to update blockStates (final update)
      // Each step has { block_id, success, error, execution_time_ms }
      if (response.step_results && Array.isArray(response.step_results)) {
        response.step_results.forEach((step: any) => {
          if (step.block_id) {
            // Set the duration from backend execution_time_ms
            unifiedExecution.updateBlockState(step.block_id, {
              status: step.success ? 'success' : 'failure',
              duration: step.execution_time_ms || 0,
              error: step.error,
              result: step
            });
          }
        });
      }
      
      // 🆕 ADD: Complete unified execution with final result
      // IMPORTANT: success is based on result_type ('success' = reached SUCCESS terminal)
      // NOT on whether individual blocks succeeded
      unifiedExecution.completeExecution({
        success: response.success,
        result_type: response.result_type || (response.success ? 'success' : 'error'),
        execution_time_ms: response.execution_time_ms || 0,
        error: response.error,
        step_count: response.step_count,
      });
      
      // ✅ KEEP: Legacy state updates
      if (response.success) {
        setExecutionState({
          isExecuting: false,
          currentBlockId: null,
          result: {
            success: response.success,
            result_type: response.result_type || 'success',
            current_step: response.step_count || 0,
            total_steps: response.step_count || 0,
            step_results: response.step_results || [],
            execution_time_ms: response.execution_time_ms || 0,
            error: response.error,
            report_url: response.script_result_id ? `/script-results/${response.script_result_id}` : undefined
          },
        });
      } else {
        setExecutionState({
          isExecuting: false,
          currentBlockId: null,
          result: {
            success: false,
            result_type: response.result_type || 'error',
            current_step: response.step_count || 0,
            total_steps: response.step_count || 0,
            step_results: response.step_results || [],
            execution_time_ms: response.execution_time_ms || 0,
            error: response.error,
          },
        });
      }
    } catch (error) {
      console.error('Error executing test case:', error);
      
      // 🆕 ADD: Update unified execution on error
      unifiedExecution.completeExecution({
        success: false,
        result_type: 'error',
        execution_time_ms: 0,
        error: error instanceof Error ? error.message : 'Unknown error',
      });
      
      // ✅ KEEP: Legacy error handling
      setExecutionState({
        isExecuting: false,
        currentBlockId: null,
        result: {
          success: false,
          result_type: 'error',
          current_step: 0,
          total_steps: 0,
          step_results: [],
          execution_time_ms: 0,
          error: error instanceof Error ? error.message : 'Unknown error',
        },
      });
    }
  }, [currentTestcaseId, testcaseName, nodes, edges, description, userinterfaceName, unifiedExecution, saveTestCase, executeTestCase]);
  
  // Save current test case
  const saveCurrentTestCase = useCallback(async (): Promise<{ success: boolean; error?: string }> => {
    if (!testcaseName || testcaseName.trim() === '') {
      return { success: false, error: 'Test case name is required' };
    }
    
    if (!userinterfaceName) {
      return { success: false, error: 'User interface is required' };
    }
    
    // 🛡️ SAFEGUARD: Rename duplicate nodes with new UUIDs
    const seenIds = new Set<string>();
    const uniqueNodes = nodes.map(node => 
      seenIds.has(node.id) ? { ...node, id: crypto.randomUUID() } : (seenIds.add(node.id), node)
    );
    
    // Convert nodes and edges to TestCaseGraph format
    const graph: TestCaseGraph = {
      nodes: uniqueNodes.map(node => ({
        id: node.id,
        type: node.type as BlockType,
        position: node.position,
        data: node.data || {}
      })),
      edges: edges.map(edge => ({
        id: edge.id!,
        source: edge.source,
        target: edge.target,
        sourceHandle: edge.sourceHandle as 'success' | 'failure',
        type: (edge.type === 'success' || edge.type === 'failure') ? edge.type : 'success' as any
      }))
    };
    
    // DEBUG: Log what we're saving
    console.log('[@TestCaseBuilder] Manual save with graph:', {
      nodes: graph.nodes.length,
      edges: graph.edges.length,
      nodeIds: graph.nodes.map(n => n.id),
      edgeDetails: graph.edges
    });
    
    try {
      const result = await saveTestCase(
        testcaseName,
        graph,
        description,
        userinterfaceName,
        'default-user',
        testcaseEnvironment,
        true  // Always overwrite - maintains history automatically via trigger
      );
      
      if (result.success && (result as any).testcase?.testcase_id) {
        const savedId = (result as any).testcase.testcase_id as string;
        setCurrentTestcaseId(savedId);
        setHasUnsavedChanges(false); // Reset after successful save
        console.log(`Test case ${result.action}: ${savedId}`);
        return { success: true };
      }
      
      return { success: false, error: result.error };
    } catch (error: any) {
      return { success: false, error: error.message };
    }
  }, [testcaseName, description, testcaseEnvironment, userinterfaceName, nodes, edges, saveTestCase]);
  
  // Load test case
  const loadTestCase = useCallback(async (testcase_id: string) => {
    try {
      const result = await getTestCase(testcase_id);
      
      if (result.success && result.testcase) {
        const testcase = result.testcase;
        
        // Set metadata
        setTestcaseName(testcase.testcase_name);
        setDescription(testcase.description || '');
        setTestcaseEnvironment(testcase.environment || 'dev');
        setUserinterfaceName(testcase.userinterface_name || '');
        setCurrentTestcaseId(testcase.testcase_id);
        
        // Load graph
        const graph = testcase.graph_json;
        setNodes(graph.nodes.map((node: any) => ({
          id: node.id,
          type: node.type,
          position: node.position,
          data: node.data,
          // Ensure START, SUCCESS, and FAILURE blocks are not deletable
          deletable: !['start', 'success', 'failure'].includes(node.type)
        })));
        setEdges(graph.edges.map((edge: any) => ({
          id: edge.id,
          source: edge.source,
          target: edge.target,
          sourceHandle: edge.sourceHandle,
          type: edge.type,
          style: { 
            stroke: edge.type === 'success' ? '#10b981' : '#ef4444',
            strokeWidth: 2
          }
        })));
        
        // Recalculate block counters from loaded nodes
        blockCounters.current = {};
        graph.nodes.forEach((node: any) => {
          if (node.data?.label && !['start', 'success', 'failure'].includes(node.type)) {
            // Extract group and count from label (e.g., "action_5_swipe_up" -> group "action", count 5)
            const match = node.data.label.match(/^([a-zA-Z_]+)_(\d+)/);
            if (match) {
              const [, group, count] = match;
              blockCounters.current[group] = Math.max(
                blockCounters.current[group] || 0,
                parseInt(count, 10)
              );
            }
          }
        });
        
        setHasUnsavedChanges(false); // Reset after load
        console.log('Test case loaded:', testcase.testcase_name);
      }
    } catch (error) {
      console.error('Error loading test case:', error);
    }
  }, []);
  
  // Fetch test case list
  const fetchTestCaseList = useCallback(async () => {
    setIsLoadingTestCaseList(true);
    try {
      const result = await listTestCases();
      if (result.success && result.testcases) {
        setTestcaseList(result.testcases);
      }
    } catch (error) {
      console.error('Error fetching test case list:', error);
    } finally {
      setIsLoadingTestCaseList(false);
    }
  }, [listTestCases]);
  
  // Delete test case
  const deleteTestCaseById = useCallback(async (testcase_id: string) => {
    try {
      const result = await deleteTestCase(testcase_id);
      if (result.success) {
        // Refresh list
        await fetchTestCaseList();
        
        // If deleting current test case, reset builder
        if (testcase_id === currentTestcaseId) {
          resetBuilder();
        }
      }
    } catch (error) {
      console.error('Error deleting test case:', error);
    }
  }, [currentTestcaseId]);
  
  // Reset builder to initial state
  const resetBuilder = useCallback(() => {
    setNodes([
      {
        id: 'start',
        type: 'start',
        position: { x: 400, y: 50 },  // Top center
        data: {},
        deletable: false,  // Cannot be deleted
      },
      {
        id: 'success',
        type: 'success',
        position: { x: 200, y: 550 },  // Bottom left (shifted 50px right)
        data: {},
        deletable: false,  // Cannot be deleted
      },
      {
        id: 'failure',
        type: 'failure',
        position: { x: 600, y: 550 },  // Bottom right (shifted 50px left)
        data: {},
        deletable: false,  // Cannot be deleted
      },
    ]);
    setEdges([]);
    setTestcaseName('');
    setDescription('');
    setUserinterfaceName('');
    setCurrentTestcaseId(null);
    setSelectedBlock(null);
    setHasUnsavedChanges(false); // Reset on new test case
    blockCounters.current = {}; // Reset block counters
  }, []);

  // Fetch navigation nodes when userinterface changes
  const fetchNavigationNodes = useCallback(async (interfaceName: string) => {
    if (!interfaceName) return;
    
    setIsLoadingOptions(true);
    try {
      const result = await getNavigationNodesForInterface(interfaceName);
      if (result.success) {
        // Filter out ENTRY nodes (case-insensitive) - check type, label, and id
        const filteredNodes = result.nodes.filter(node => {
          const nodeType = (node.type || '').toLowerCase();
          const nodeLabel = (node.label || '').toLowerCase();
          const nodeId = ((node as any).node_id || node.id || '').toLowerCase();
          
          // Filter out if type, label, or id is "entry" or contains "entry"
          if (nodeType === 'entry' || nodeLabel === 'entry' || nodeId === 'entry' || nodeId.includes('entry')) {
            return false;
          }
          
          return true;
        });
        setAvailableNodes(filteredNodes);
      }
    } catch (error) {
      console.error('Error fetching navigation nodes:', error);
    } finally {
      setIsLoadingOptions(false);
    }
  }, [getNavigationNodesForInterface]);
  
  // Fetch user interfaces on mount
  useEffect(() => {
    const fetchInitialData = async () => {
      try {
        const [interfacesRes, actionsRes, verificationsRes] = await Promise.all([
          getUserInterfaces(),
          getAvailableActions(),
          getAvailableVerifications(),
        ]);
        
        if (interfacesRes.success) {
          setAvailableInterfaces(interfacesRes.userinterfaces);
        }
        if (actionsRes.success) {
          setAvailableActions(actionsRes.actions);
        }
        if (verificationsRes.success) {
          setAvailableVerifications(verificationsRes.verifications);
        }
      } catch (error) {
        console.error('Error fetching initial data:', error);
      }
    };
    
    fetchInitialData();
  }, []);
  
  // Fetch navigation nodes when userinterface changes
  // NOTE: Disabled - TestCaseBuilder already loads navigation tree via NavigationEditor infrastructure
  // The toolbox builder extracts nodes from the loaded tree, making this redundant
  useEffect(() => {
    // Commenting out to prevent duplicate API calls and warnings
    // if (userinterfaceName) {
    //   fetchNavigationNodes(userinterfaceName);
    // }
  }, [userinterfaceName, fetchNavigationNodes]);
  
  const value: TestCaseBuilderContextType = {
    nodes,
    edges,
    setNodes,
    setEdges,
    testcaseName,
    setTestcaseName,
    description,
    setDescription,
    testcaseEnvironment,
    setTestcaseEnvironment,
    userinterfaceName,
    setUserinterfaceName,
    currentTestcaseId,
    setCurrentTestcaseId,
    hasUnsavedChanges,
    setHasUnsavedChanges,
    testcaseList,
    setTestcaseList,
    isLoadingTestCaseList,
    availableInterfaces,
    availableNodes,
    availableActions,
    availableVerifications,
    isLoadingOptions,
    selectedBlock,
    setSelectedBlock,
    isConfigDialogOpen,
    setIsConfigDialogOpen,
    executionState,
    setExecutionState,
    isExecutable,
    addBlock,
    updateBlock,
    deleteBlock,
    onNodesChange,
    onEdgesChange,
    onConnect,
    saveCurrentTestCase,
    loadTestCase,
    executeCurrentTestCase,
    fetchTestCaseList,
    deleteTestCaseById,
    resetBuilder,
    fetchNavigationNodes,
    // 🆕 ADD: Unified execution state
    unifiedExecution,
  };

  return (
    <TestCaseBuilderContext.Provider value={value}>
      {children}
    </TestCaseBuilderContext.Provider>
  );
};

