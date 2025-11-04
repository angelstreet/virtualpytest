import React, { createContext, useContext, useState, useCallback, ReactNode, useEffect } from 'react';
import { useDeviceData } from '../device/DeviceDataContext';
import { useControl } from '../../hooks/device/useControl';
import { useTestCaseBuilder as useTestCaseBuilderHook, type NavigationNode, type ActionCommand } from '../../hooks/testcase';
import { useTestCaseAI } from '../../hooks/testcase/useTestCaseAI';
import { useTestCaseExecution } from '../../hooks/testcase/useTestCaseExecution';
import { useExecutionState } from '../../hooks/testcase/useExecutionState';
import { TestCaseGraph, ScriptInput, Variable } from '../../types/testcase/TestCase_Types';

interface MCPPlaygroundContextType {
  // Device & Control
  selectedHost: string;
  setSelectedHost: React.Dispatch<React.SetStateAction<string>>;
  selectedDeviceId: string;
  setSelectedDeviceId: React.Dispatch<React.SetStateAction<string>>;
  userinterfaceName: string;
  setUserinterfaceName: React.Dispatch<React.SetStateAction<string>>;
  availableHosts: string[];
  isControlActive: boolean;
  isControlLoading: boolean;
  handleDeviceControl: () => Promise<void>;
  
  // Available Options
  availableInterfaces: any[];
  availableNodes: NavigationNode[];
  availableActions: ActionCommand[];
  availableVerifications: any[];
  isLoadingOptions: boolean;
  
  // Prompt & AI
  prompt: string;
  setPrompt: React.Dispatch<React.SetStateAction<string>>;
  isGenerating: boolean;
  handleGenerate: () => Promise<void>;
  
  // Execution
  unifiedExecution: ReturnType<typeof useExecutionState>;
  isExecuting: boolean;
  executionResult: any;
  
  // History
  commandHistory: Array<{ timestamp: Date; prompt: string; success: boolean; result?: any }>;
  addToHistory: (prompt: string, success: boolean, result?: any) => void;
  clearHistory: () => void;
  
  // Disambiguation
  disambiguationData: any;
  handleDisambiguationResolve: (resolutions: Record<string, string>) => void;
  handleDisambiguationCancel: () => void;
}

const MCPPlaygroundContext = createContext<MCPPlaygroundContextType | undefined>(undefined);

export const useMCPPlayground = () => {
  const context = useContext(MCPPlaygroundContext);
  if (!context) {
    throw new Error('useMCPPlayground must be used within MCPPlaygroundProvider');
  }
  return context;
};

interface MCPPlaygroundProviderProps {
  children: ReactNode;
}

export const MCPPlaygroundProvider: React.FC<MCPPlaygroundProviderProps> = ({ children }) => {
  // Device data from global context
  const { currentDeviceId, currentHostName, availableHosts } = useDeviceData();
  
  // Local state for device selection
  const [selectedHost, setSelectedHost] = useState<string>(currentHostName || 'sunri-pi1');
  const [selectedDeviceId, setSelectedDeviceId] = useState<string>(currentDeviceId || 'device1');
  const [userinterfaceName, setUserinterfaceName] = useState<string>('');
  
  // Device control
  const { takeControl, releaseControl, isControlActive, isLoading: isControlLoading } = useControl();
  
  // Available options
  const { 
    getUserInterfaces, 
    getNavigationNodesForInterface, 
    getAvailableActions, 
    getAvailableVerifications 
  } = useTestCaseBuilderHook();
  
  const [availableInterfaces, setAvailableInterfaces] = useState<any[]>([]);
  const [availableNodes, setAvailableNodes] = useState<NavigationNode[]>([]);
  const [availableActions, setAvailableActions] = useState<ActionCommand[]>([]);
  const [availableVerifications, setAvailableVerifications] = useState<any[]>([]);
  const [isLoadingOptions, setIsLoadingOptions] = useState<boolean>(false);
  
  // Prompt & AI
  const [prompt, setPrompt] = useState<string>('');
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [disambiguationData, setDisambiguationData] = useState<any>(null);
  const { generateTestGraph } = useTestCaseAI();
  const { executeTestCase } = useTestCaseExecution();
  
  // Execution state
  const unifiedExecution = useExecutionState();
  const [executionResult, setExecutionResult] = useState<any>(null);
  
  // Command history (local storage)
  const [commandHistory, setCommandHistory] = useState<Array<{ timestamp: Date; prompt: string; success: boolean; result?: any }>>([]);
  
  // Load history from localStorage on mount
  useEffect(() => {
    const savedHistory = localStorage.getItem('mcp-playground-history');
    if (savedHistory) {
      try {
        const parsed = JSON.parse(savedHistory);
        setCommandHistory(parsed.map((item: any) => ({
          ...item,
          timestamp: new Date(item.timestamp)
        })));
      } catch (error) {
        console.error('Failed to parse command history:', error);
      }
    }
  }, []);
  
  // Save history to localStorage whenever it changes
  useEffect(() => {
    localStorage.setItem('mcp-playground-history', JSON.stringify(commandHistory));
  }, [commandHistory]);
  
  // Add to history
  const addToHistory = useCallback((prompt: string, success: boolean, result?: any) => {
    setCommandHistory(prev => [
      { timestamp: new Date(), prompt, success, result },
      ...prev.slice(0, 49) // Keep last 50 commands
    ]);
  }, []);
  
  // Clear history
  const clearHistory = useCallback(() => {
    setCommandHistory([]);
    localStorage.removeItem('mcp-playground-history');
  }, []);
  
  // Device control handler
  const handleDeviceControl = useCallback(async () => {
    if (isControlActive) {
      await releaseControl(selectedDeviceId, selectedHost);
    } else {
      // Get current tree ID from selected interface
      const currentTreeId = availableInterfaces.find(
        (iface) => iface.userinterface_name === userinterfaceName
      )?.tree_id;
      
      await takeControl(selectedDeviceId, selectedHost, currentTreeId);
    }
  }, [isControlActive, selectedDeviceId, selectedHost, userinterfaceName, availableInterfaces, takeControl, releaseControl]);
  
  // Fetch available options
  useEffect(() => {
    const fetchInitialData = async () => {
      setIsLoadingOptions(true);
      try {
        const [interfacesRes, actionsRes, verificationsRes] = await Promise.all([
          getUserInterfaces(),
          getAvailableActions(),
          getAvailableVerifications(),
        ]);
        
        if (interfacesRes.success) {
          setAvailableInterfaces(interfacesRes.userinterfaces);
          // Auto-select first interface if none selected
          if (!userinterfaceName && interfacesRes.userinterfaces.length > 0) {
            setUserinterfaceName(interfacesRes.userinterfaces[0].userinterface_name);
          }
        }
        if (actionsRes.success) {
          setAvailableActions(actionsRes.actions);
        }
        if (verificationsRes.success) {
          setAvailableVerifications(verificationsRes.verifications);
        }
      } catch (error) {
        console.error('Error fetching initial data:', error);
      } finally {
        setIsLoadingOptions(false);
      }
    };
    
    fetchInitialData();
  }, []);
  
  // Fetch navigation nodes when interface changes
  useEffect(() => {
    if (!userinterfaceName) return;
    
    const fetchNodes = async () => {
      try {
        const result = await getNavigationNodesForInterface(userinterfaceName);
        if (result.success) {
          // Filter out ENTRY nodes
          const filteredNodes = result.nodes.filter((node: NavigationNode) => {
            const nodeType = (node.type || '').toLowerCase();
            const nodeLabel = (node.label || '').toLowerCase();
            const nodeId = ((node as any).node_id || node.id || '').toLowerCase();
            
            return !(nodeType === 'entry' || nodeLabel === 'entry' || nodeId === 'entry' || nodeId.includes('entry'));
          });
          setAvailableNodes(filteredNodes);
        }
      } catch (error) {
        console.error('Error fetching navigation nodes:', error);
      }
    };
    
    fetchNodes();
  }, [userinterfaceName, getNavigationNodesForInterface]);
  
  // Generate and execute with AI
  const handleGenerate = useCallback(async () => {
    if (!prompt.trim()) {
      console.log('[@MCPPlayground] Empty prompt, skipping generation');
      return;
    }
    
    if (!userinterfaceName) {
      console.error('[@MCPPlayground] No interface selected');
      addToHistory(prompt, false, { error: 'No interface selected' });
      return;
    }
    
    setIsGenerating(true);
    setDisambiguationData(null);
    
    try {
      console.log('[@MCPPlayground] Generating test graph from prompt:', prompt);
      
      const result = await generateTestGraph(prompt, userinterfaceName, selectedDeviceId, selectedHost);
      
      // Check for disambiguation
      if (result.requires_disambiguation) {
        console.log('[@MCPPlayground] Disambiguation required');
        setDisambiguationData({
          ambiguities: result.ambiguities || [],
          auto_corrections: result.auto_corrections || [],
          available_nodes: result.available_nodes || availableNodes,
          originalPrompt: prompt
        });
        setIsGenerating(false);
        return;
      }
      
      // Check for error
      if (!result.success || !result.graph) {
        console.error('[@MCPPlayground] Generation failed:', result.error);
        addToHistory(prompt, false, { error: result.error });
        setIsGenerating(false);
        return;
      }
      
      // Execute the generated graph
      console.log('[@MCPPlayground] Executing generated graph');
      await executeGraph(result.graph);
      
    } catch (error) {
      console.error('[@MCPPlayground] Error generating test graph:', error);
      addToHistory(prompt, false, { error: error instanceof Error ? error.message : 'Unknown error' });
    } finally {
      setIsGenerating(false);
    }
  }, [prompt, userinterfaceName, selectedDeviceId, selectedHost, generateTestGraph, availableNodes, addToHistory]);
  
  // Execute graph
  const executeGraph = useCallback(async (graph: TestCaseGraph) => {
    // Initialize execution state
    const blockIds = graph.nodes
      .filter(n => !['start', 'success', 'failure'].includes(n.type || ''))
      .map(n => n.id);
    
    unifiedExecution.startExecution('mcp_command', blockIds);
    
    try {
      const response = await executeTestCase(
        graph,
        selectedDeviceId,
        selectedHost,
        userinterfaceName,
        [] as ScriptInput[], // No script inputs for MCP
        [] as Variable[], // No variables for MCP
        `MCP: ${prompt.substring(0, 50)}`, // Testcase name
        // Progress callback
        (status) => {
          if (status.current_block_id) {
            unifiedExecution.startBlockExecution(status.current_block_id);
          }
          
          Object.entries(status.block_states).forEach(([blockId, blockState]) => {
            unifiedExecution.updateBlockState(blockId, {
              status: blockState.status,
              duration: blockState.duration,
              error: blockState.error,
              result: blockState
            });
          });
        }
      );
      
      // Complete execution
      unifiedExecution.completeExecution({
        success: response.success,
        result_type: response.result_type || (response.success ? 'success' : 'error'),
        execution_time_ms: response.execution_time_ms || 0,
        error: response.error,
        step_count: response.step_count,
      });
      
      setExecutionResult(response);
      addToHistory(prompt, response.success, response);
      
    } catch (error) {
      console.error('[@MCPPlayground] Execution error:', error);
      unifiedExecution.completeExecution({
        success: false,
        result_type: 'error',
        execution_time_ms: 0,
        error: error instanceof Error ? error.message : 'Unknown error',
      });
      
      addToHistory(prompt, false, { error: error instanceof Error ? error.message : 'Unknown error' });
    }
  }, [selectedDeviceId, selectedHost, userinterfaceName, prompt, unifiedExecution, executeTestCase, addToHistory]);
  
  // Handle disambiguation resolve
  const handleDisambiguationResolve = useCallback(async (resolutions: Record<string, string>) => {
    if (!disambiguationData) return;
    
    setIsGenerating(true);
    setDisambiguationData(null);
    
    try {
      // Regenerate with resolutions
      const result = await generateTestGraph(
        disambiguationData.originalPrompt,
        userinterfaceName,
        selectedDeviceId,
        selectedHost,
        resolutions
      );
      
      if (result.success && result.graph) {
        await executeGraph(result.graph);
      } else {
        console.error('[@MCPPlayground] Generation failed after disambiguation:', result.error);
        addToHistory(disambiguationData.originalPrompt, false, { error: result.error });
      }
    } catch (error) {
      console.error('[@MCPPlayground] Error after disambiguation:', error);
      addToHistory(disambiguationData.originalPrompt, false, { error: error instanceof Error ? error.message : 'Unknown error' });
    } finally {
      setIsGenerating(false);
    }
  }, [disambiguationData, userinterfaceName, selectedDeviceId, selectedHost, generateTestGraph, executeGraph, addToHistory]);
  
  // Handle disambiguation cancel
  const handleDisambiguationCancel = useCallback(() => {
    setDisambiguationData(null);
    setIsGenerating(false);
  }, []);
  
  const value: MCPPlaygroundContextType = {
    selectedHost,
    setSelectedHost,
    selectedDeviceId,
    setSelectedDeviceId,
    userinterfaceName,
    setUserinterfaceName,
    availableHosts,
    isControlActive,
    isControlLoading,
    handleDeviceControl,
    availableInterfaces,
    availableNodes,
    availableActions,
    availableVerifications,
    isLoadingOptions,
    prompt,
    setPrompt,
    isGenerating,
    handleGenerate,
    unifiedExecution,
    isExecuting: unifiedExecution.state.isExecuting,
    executionResult,
    commandHistory,
    addToHistory,
    clearHistory,
    disambiguationData,
    handleDisambiguationResolve,
    handleDisambiguationCancel,
  };
  
  return (
    <MCPPlaygroundContext.Provider value={value}>
      {children}
    </MCPPlaygroundContext.Provider>
  );
};

