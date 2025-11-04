/**
 * MCP Playground Page Hook
 * 
 * REUSES TestCaseBuilder infrastructure:
 * - useHostManager (device selection)
 * - useDeviceControlWithForceUnlock (take/release control)
 * - useDeviceData (available actions/verifications)
 * - useNavigationEditor + useNavigationConfig (tree loading)
 * - useTestCaseAI (AI generation)
 * - useTestCaseExecution (execution)
 */

import { useState, useEffect, useCallback } from 'react';
import { useHostManager } from '../../contexts/index';
import { useDeviceData } from '../../contexts/device/DeviceDataContext';
import { useDeviceControlWithForceUnlock } from '../useDeviceControlWithForceUnlock';
import { useNavigationEditor } from '../navigation/useNavigationEditor';
import { useNavigationConfig } from '../../contexts/navigation/NavigationConfigContext';
import { useUserInterface } from './useUserInterface';
import { useTestCaseAI } from '../testcase';
import { useTestCaseExecution } from '../testcase/useTestCaseExecution';
import { useExecutionState } from '../testcase/useExecutionState';
import { filterCompatibleInterfaces } from '../../utils/userinterface/deviceCompatibilityUtils';
import { TestCaseGraph, ScriptInput, Variable } from '../../types/testcase/TestCase_Types';

export interface UseMCPPlaygroundPageReturn {
  // Device & Control
  selectedHost: any;
  selectedDeviceId: string | null;
  isControlActive: boolean;
  isControlLoading: boolean;
  availableHosts: any[];
  handleDeviceSelect: (host: any | null, deviceId: string | null) => void;
  handleDeviceControl: () => Promise<void>;
  
  // Interface & Navigation
  compatibleInterfaceNames: string[];
  userinterfaceName: string;
  setUserinterfaceName: (name: string) => void;
  navNodes: any[];
  currentTreeId: string | null;
  isLoadingTree: boolean;
  
  // Available Options
  availableActions: any;
  availableVerifications: any;
  areActionsLoaded: boolean;
  
  // Prompt & AI
  prompt: string;
  setPrompt: (prompt: string) => void;
  isGenerating: boolean;
  handleGenerate: () => Promise<void>;
  
  // Execution
  unifiedExecution: ReturnType<typeof useExecutionState>;
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

export function useMCPPlaygroundPage(): UseMCPPlaygroundPageReturn {
  // ==================== HOST & DEVICE (REUSE FROM TESTCASEBUILDER) ====================
  const {
    selectedHost,
    selectedDeviceId,
    isControlActive,
    availableHosts,
    handleDeviceSelect: hostManagerDeviceSelect,
    handleControlStateChange,
  } = useHostManager();
  
  const handleDeviceSelect = hostManagerDeviceSelect;
  
  // ==================== INTERFACE & NAVIGATION (EARLY DECLARATION) ====================
  const [currentTreeId, setCurrentTreeId] = useState<string | null>(null);
  const [isLoadingTree, setIsLoadingTree] = useState(false);
  const [userinterfaceName, setUserinterfaceName] = useState<string>('');
  
  // ==================== DEVICE CONTROL (REUSE FROM TESTCASEBUILDER) ====================
  const {
    isControlLoading,
    handleDeviceControl,
    controlError,
    clearError,
  } = useDeviceControlWithForceUnlock({
    host: selectedHost,
    device_id: selectedDeviceId,
    sessionId: 'mcp-playground-session',
    autoCleanup: true,
    tree_id: currentTreeId || undefined,
    onControlStateChange: handleControlStateChange,
  });
  
  // ==================== DEVICE DATA (REUSE FROM TESTCASEBUILDER) ====================
  const { 
    setControlState, 
    getAvailableActions,
    getAvailableVerificationTypes,
    availableActionsLoading,
    fetchAvailableActions,
  } = useDeviceData();
  
  useEffect(() => {
    setControlState(selectedHost, selectedDeviceId, isControlActive);
  }, [selectedHost, selectedDeviceId, isControlActive, setControlState]);
  
  useEffect(() => {
    if (!isControlActive || !selectedHost || !selectedDeviceId) return;
    
    const timer = setTimeout(async () => {
      await fetchAvailableActions(true);
    }, 1000);

    return () => clearTimeout(timer);
  }, [isControlActive, selectedHost, selectedDeviceId, fetchAvailableActions]);
  
  const availableActions = getAvailableActions();
  const availableVerifications = getAvailableVerificationTypes();
  const areActionsLoaded = isControlActive && !availableActionsLoading && Object.values(availableActions || {}).flat().length > 0;
  
  // ==================== INTERFACE & NAVIGATION (REUSE FROM TESTCASEBUILDER) ====================
  const { setUserInterfaceFromProps } = useNavigationEditor();
  const { loadTreeByUserInterface, getNodeById } = useNavigationConfig();
  const { getAllUserInterfaces, getUserInterfaceByName } = useUserInterface();
  
  const [compatibleInterfaceNames, setCompatibleInterfaceNames] = useState<string[]>([]);
  const [navNodes, setNavNodes] = useState<any[]>([]);
  
  // Load compatible interfaces (SAME AS TESTCASEBUILDER)
  useEffect(() => {
    const loadCompatibleInterfaces = async () => {
      if (!selectedDeviceId || !selectedHost) {
        setCompatibleInterfaceNames([]);
        setUserinterfaceName('');
        return;
      }
      
      try {
        const selectedDevice = selectedHost.devices?.find((d: any) => d.device_id === selectedDeviceId);
        
        if (!selectedDevice) {
          console.warn('[@useMCPPlaygroundPage] Selected device not found');
          return;
        }
        
        const interfaces = await getAllUserInterfaces();
        const compatibleInterfaces = filterCompatibleInterfaces(interfaces, selectedDevice);
        
        const names = compatibleInterfaces.map((iface: any) => iface.userinterface_name);
        setCompatibleInterfaceNames(names);
        
        // Auto-select first compatible interface
        if (names.length > 0 && !userinterfaceName) {
          setUserinterfaceName(names[0]);
        }
      } catch (error) {
        console.error('[@useMCPPlaygroundPage] Error loading compatible interfaces:', error);
      }
    };
    
    loadCompatibleInterfaces();
  }, [selectedDeviceId, selectedHost, getAllUserInterfaces, userinterfaceName]);
  
  // Load navigation tree when interface changes (SAME AS TESTCASEBUILDER)
  useEffect(() => {
    const loadTreeForInterface = async () => {
      if (!userinterfaceName) {
        setNavNodes([]);
        setCurrentTreeId(null);
        return;
      }
      
      try {
        setIsLoadingTree(true);
        const interfaceData = await getUserInterfaceByName(userinterfaceName);
        
        if (!interfaceData) {
          console.warn(`[@useMCPPlaygroundPage] Interface not found: ${userinterfaceName}`);
          return;
        }
        
        const tree_id = interfaceData.tree_id;
        if (!tree_id) {
          console.warn(`[@useMCPPlaygroundPage] No tree_id for interface: ${userinterfaceName}`);
          return;
        }
        
        setCurrentTreeId(tree_id);
        await loadTreeByUserInterface(userinterfaceName);
        await setUserInterfaceFromProps(userinterfaceName);
        
        // Extract nodes from loaded tree
        const allNodes: any[] = [];
        const collectNodes = (nodeId: string, visited = new Set<string>()) => {
          if (visited.has(nodeId)) return;
          visited.add(nodeId);
          
          const node = getNodeById(nodeId);
          if (node) {
            allNodes.push(node);
            node.edges?.forEach((edge: any) => {
              if (edge.target) collectNodes(edge.target, visited);
            });
          }
        };
        
        const entryNode = getNodeById('ENTRY');
        if (entryNode) {
          collectNodes('ENTRY');
        }
        
        // Filter out ENTRY nodes
        const filteredNodes = allNodes.filter(node => 
          node.id !== 'ENTRY' && 
          node.type !== 'entry' &&
          node.label?.toLowerCase() !== 'entry'
        );
        
        setNavNodes(filteredNodes);
        console.log(`[@useMCPPlaygroundPage] Loaded ${filteredNodes.length} nodes for ${userinterfaceName}`);
      } catch (error) {
        console.error('[@useMCPPlaygroundPage] Error loading tree:', error);
      } finally {
        setIsLoadingTree(false);
      }
    };
    
    loadTreeForInterface();
  }, [userinterfaceName, getUserInterfaceByName, loadTreeByUserInterface, setUserInterfaceFromProps, getNodeById]);
  
  // ==================== AI GENERATION (REUSE FROM TESTCASEBUILDER) ====================
  const { generateTestCaseFromPrompt } = useTestCaseAI();
  const { executeTestCase } = useTestCaseExecution();
  const unifiedExecution = useExecutionState();
  
  const [prompt, setPrompt] = useState<string>('');
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [disambiguationData, setDisambiguationData] = useState<any>(null);
  const [executionResult, setExecutionResult] = useState<any>(null);
  
  // ==================== COMMAND HISTORY ====================
  const [commandHistory, setCommandHistory] = useState<Array<{ timestamp: Date; prompt: string; success: boolean; result?: any }>>([]);
  
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
  
  useEffect(() => {
    localStorage.setItem('mcp-playground-history', JSON.stringify(commandHistory));
  }, [commandHistory]);
  
  const addToHistory = useCallback((prompt: string, success: boolean, result?: any) => {
    setCommandHistory(prev => [
      { timestamp: new Date(), prompt, success, result },
      ...prev.slice(0, 49)
    ]);
  }, []);
  
  const clearHistory = useCallback(() => {
    setCommandHistory([]);
    localStorage.removeItem('mcp-playground-history');
  }, []);
  
  // ==================== GENERATE & EXECUTE ====================
  const executeGraph = useCallback(async (graph: TestCaseGraph) => {
    if (!selectedDeviceId || !selectedHost) {
      console.error('[@useMCPPlaygroundPage] No device selected');
      return;
    }
    
    const blockIds = graph.nodes
      .filter(n => !['start', 'success', 'failure'].includes(n.type || ''))
      .map(n => n.id);
    
    unifiedExecution.startExecution('mcp_command', blockIds);
    
    try {
      const response = await executeTestCase(
        graph,
        selectedDeviceId,
        selectedHost.host_name,
        userinterfaceName,
        [] as ScriptInput[],
        [] as Variable[],
        `MCP: ${prompt.substring(0, 50)}`,
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
      console.error('[@useMCPPlaygroundPage] Execution error:', error);
      unifiedExecution.completeExecution({
        success: false,
        result_type: 'error',
        execution_time_ms: 0,
        error: error instanceof Error ? error.message : 'Unknown error',
      });
      
      addToHistory(prompt, false, { error: error instanceof Error ? error.message : 'Unknown error' });
    }
  }, [selectedDeviceId, selectedHost, userinterfaceName, prompt, unifiedExecution, executeTestCase, addToHistory]);
  
  const handleGenerate = useCallback(async () => {
    if (!prompt.trim()) {
      console.log('[@useMCPPlaygroundPage] Empty prompt');
      return;
    }
    
    if (!userinterfaceName) {
      console.error('[@useMCPPlaygroundPage] No interface selected');
      addToHistory(prompt, false, { error: 'No interface selected' });
      return;
    }
    
    setIsGenerating(true);
    setDisambiguationData(null);
    
    try {
      console.log('[@useMCPPlaygroundPage] Generating from prompt:', prompt);
      
      const result = await generateTestCaseFromPrompt(prompt, userinterfaceName);
      
      if (result.requires_disambiguation) {
        console.log('[@useMCPPlaygroundPage] Disambiguation required');
        setDisambiguationData({
          ambiguities: result.ambiguities || [],
          auto_corrections: result.auto_corrections || [],
          available_nodes: result.available_nodes || navNodes,
          originalPrompt: prompt
        });
        setIsGenerating(false);
        return;
      }
      
      if (!result.success || !result.graph) {
        console.error('[@useMCPPlaygroundPage] Generation failed:', result.error);
        addToHistory(prompt, false, { error: result.error });
        setIsGenerating(false);
        return;
      }
      
      console.log('[@useMCPPlaygroundPage] Executing generated graph');
      await executeGraph(result.graph);
      
    } catch (error) {
      console.error('[@useMCPPlaygroundPage] Error generating:', error);
      addToHistory(prompt, false, { error: error instanceof Error ? error.message : 'Unknown error' });
    } finally {
      setIsGenerating(false);
    }
  }, [prompt, userinterfaceName, generateTestCaseFromPrompt, navNodes, executeGraph, addToHistory]);
  
  const handleDisambiguationResolve = useCallback(async (resolutions: Record<string, string>) => {
    if (!disambiguationData) return;
    
    setIsGenerating(true);
    setDisambiguationData(null);
    
    try {
      const result = await generateTestCaseFromPrompt(
        disambiguationData.originalPrompt,
        userinterfaceName,
        resolutions
      );
      
      if (result.success && result.graph) {
        await executeGraph(result.graph);
      } else {
        console.error('[@useMCPPlaygroundPage] Generation failed after disambiguation:', result.error);
        addToHistory(disambiguationData.originalPrompt, false, { error: result.error });
      }
    } catch (error) {
      console.error('[@useMCPPlaygroundPage] Error after disambiguation:', error);
      addToHistory(disambiguationData.originalPrompt, false, { error: error instanceof Error ? error.message : 'Unknown error' });
    } finally {
      setIsGenerating(false);
    }
  }, [disambiguationData, userinterfaceName, generateTestCaseFromPrompt, executeGraph, addToHistory]);
  
  const handleDisambiguationCancel = useCallback(() => {
    setDisambiguationData(null);
    setIsGenerating(false);
  }, []);
  
  // ==================== RETURN ====================
  return {
    // Device & Control
    selectedHost,
    selectedDeviceId,
    isControlActive,
    isControlLoading,
    availableHosts,
    handleDeviceSelect,
    handleDeviceControl,
    
    // Interface & Navigation
    compatibleInterfaceNames,
    userinterfaceName,
    setUserinterfaceName,
    navNodes,
    currentTreeId,
    isLoadingTree,
    
    // Available Options
    availableActions,
    availableVerifications,
    areActionsLoaded,
    
    // Prompt & AI
    prompt,
    setPrompt,
    isGenerating,
    handleGenerate,
    
    // Execution
    unifiedExecution,
    executionResult,
    
    // History
    commandHistory,
    addToHistory,
    clearHistory,
    
    // Disambiguation
    disambiguationData,
    handleDisambiguationResolve,
    handleDisambiguationCancel,
  };
}

