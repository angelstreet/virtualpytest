import React, { createContext, useContext, useState, useCallback, ReactNode, useEffect, useRef } from 'react';
import { Node, Edge, addEdge, Connection, NodeChange, EdgeChange, applyNodeChanges, applyEdgeChanges } from 'reactflow';
import { BlockType, ExecutionState, TestCaseGraph } from '../../types/testcase/TestCase_Types';
import { 
  useTestCaseSave, 
  useTestCaseExecution,
  useTestCaseBuilder as useTestCaseBuilderHook,
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
  executeCurrentTestCase: () => Promise<void>;
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
  const [userinterfaceName, setUserinterfaceName] = useState<string>('');
  const [currentTestcaseId, setCurrentTestcaseId] = useState<string | null>(null);
  const [testcaseList, setTestcaseList] = useState<any[]>([]);
  
  // Unsaved changes tracking
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  
  // Available options for dropdowns
  const [availableInterfaces, setAvailableInterfaces] = useState<UserInterface[]>([]);
  const [availableNodes, setAvailableNodes] = useState<NavigationNode[]>([]);
  const [availableActions, setAvailableActions] = useState<ActionCommand[]>([]);
  const [availableVerifications, setAvailableVerifications] = useState<any[]>([]);
  const [isLoadingOptions, setIsLoadingOptions] = useState<boolean>(false);

  // ID counter for client-side node/edge generation (only used until save - backend assigns real UUIDs)
  const nodeIdCounter = useRef(1);
  const edgeIdCounter = useRef(1);

  // Add a new block to the canvas
  const addBlock = useCallback((type: BlockType | string, position: { x: number; y: number }, defaultData?: any) => {
    const newNode: Node = {
      id: `node_${nodeIdCounter.current++}`, // Temporary ID - backend assigns real UUID on save
      type,
      position,
      data: defaultData || {},
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
    // Determine edge type and color based on source handle
    // Support: success, failure, true, false, complete, break
    const sourceHandle = connection.sourceHandle || 'success';
    let edgeType = sourceHandle;
    let edgeColor = '#6b7280'; // default gray
    
    // Map handle types to colors
    switch (sourceHandle) {
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
      id: `edge_${edgeIdCounter.current++}`, // Temporary ID - backend assigns real UUID on save
      type: edgeType,
      source: connection.source!,
      target: connection.target!,
      style: { stroke: edgeColor, strokeWidth: 2 },
    };
    
    setEdges((prev) => addEdge(newEdge, prev));
    setHasUnsavedChanges(true);
  }, []);

  // Execute testcase
  const executeCurrentTestCase = useCallback(async () => {
    let testcaseIdToExecute = currentTestcaseId;
    
    // If no test case ID, auto-save first
    if (!testcaseIdToExecute) {
      console.log('No test case ID, auto-saving before execution...');
      const autoSaveName = testcaseName || `unsaved_${Date.now()}`;
      
      // Convert nodes and edges to TestCaseGraph format (same as saveCurrentTestCase)
      const graph: TestCaseGraph = {
        nodes: nodes.map(node => ({
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
      
      const saveResult = await saveTestCase(
        autoSaveName,
        graph,
        description || '',
        userinterfaceName || '',
        'default-user'
      );
      
      if (saveResult.success && saveResult.testcase_id) {
        testcaseIdToExecute = saveResult.testcase_id;
        setCurrentTestcaseId(saveResult.testcase_id);
        setTestcaseName(autoSaveName);
        setHasUnsavedChanges(false);
      } else {
        console.error('Failed to auto-save test case before execution');
        return;
      }
    }
    
    setExecutionState({
      isExecuting: true,
      currentBlockId: 'start',
      result: null,
    });

    try {
      const response = await executeTestCase(testcaseIdToExecute, 'device1');
      
      if (response.success && response.result) {
        setExecutionState({
          isExecuting: false,
          currentBlockId: null,
          result: {
            success: response.result.success,
            current_step: response.result.step_count,
            total_steps: response.result.step_count,
            step_results: response.result.step_results || [],
            execution_time_ms: response.result.execution_time_ms,
            report_url: response.result.script_result_id ? `/script-results/${response.result.script_result_id}` : undefined
          },
        });
      } else {
        setExecutionState({
          isExecuting: false,
          currentBlockId: null,
          result: {
            success: false,
            current_step: 0,
            total_steps: 0,
            step_results: [],
            execution_time_ms: 0,
          },
        });
      }
    } catch (error) {
      console.error('Error executing test case:', error);
      setExecutionState({
        isExecuting: false,
        currentBlockId: null,
        result: {
          success: false,
          current_step: 0,
          total_steps: 0,
          step_results: [],
          execution_time_ms: 0,
        },
      });
    }
  }, [currentTestcaseId, testcaseName, nodes, edges, description, userinterfaceName]);
  
  // Save current test case
  const saveCurrentTestCase = useCallback(async (): Promise<{ success: boolean; error?: string }> => {
    if (!testcaseName) {
      return { success: false, error: 'Test case name is required' };
    }
    
    // Convert nodes and edges to TestCaseGraph format
    const graph: TestCaseGraph = {
      nodes: nodes.map(node => ({
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
    
    try {
      const result = await saveTestCase(
        testcaseName,
        graph,
        description,
        userinterfaceName,
        'default-user'
      );
      
      if (result.success && result.testcase_id) {
        setCurrentTestcaseId(result.testcase_id);
        setHasUnsavedChanges(false); // Reset after successful save
        console.log(`Test case ${result.action}: ${result.testcase_id}`);
        return { success: true };
      }
      
      return { success: false, error: result.error };
    } catch (error: any) {
      return { success: false, error: error.message };
    }
  }, [testcaseName, description, userinterfaceName, nodes, edges]);
  
  // Load test case
  const loadTestCase = useCallback(async (testcase_id: string) => {
    try {
      const result = await getTestCase(testcase_id);
      
      if (result.success && result.testcase) {
        const testcase = result.testcase;
        
        // Set metadata
        setTestcaseName(testcase.testcase_name);
        setDescription(testcase.description || '');
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
        
        setHasUnsavedChanges(false); // Reset after load
        console.log('Test case loaded:', testcase.testcase_name);
      }
    } catch (error) {
      console.error('Error loading test case:', error);
    }
  }, []);
  
  // Fetch test case list
  const fetchTestCaseList = useCallback(async () => {
    try {
      const result = await listTestCases();
      if (result.success && result.testcases) {
        setTestcaseList(result.testcases);
      }
    } catch (error) {
      console.error('Error fetching test case list:', error);
    }
  }, []);
  
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
  }, []);

  // Fetch navigation nodes when userinterface changes
  const fetchNavigationNodes = useCallback(async (interfaceName: string) => {
    if (!interfaceName) return;
    
    setIsLoadingOptions(true);
    try {
      const result = await getNavigationNodesForInterface(interfaceName);
      if (result.success) {
        // Filter out ENTRY nodes (case-insensitive)
        const filteredNodes = result.nodes.filter(node => {
          const nodeType = (node.type || '').toLowerCase();
          return nodeType !== 'entry';
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
    userinterfaceName,
    setUserinterfaceName,
    currentTestcaseId,
    setCurrentTestcaseId,
    hasUnsavedChanges,
    setHasUnsavedChanges,
    testcaseList,
    setTestcaseList,
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
  };

  return (
    <TestCaseBuilderContext.Provider value={value}>
      {children}
    </TestCaseBuilderContext.Provider>
  );
};

