/**
 * MCP Playground Page Hook
 * 
 * REUSES TestCaseBuilder infrastructure:
 * - useHostManager (device selection)
 * - useDeviceControlWithForceUnlock (take/release control)
 * - useDeviceData (available actions/verifications)
 * - Direct API call for navigation nodes (same as MCP backend)
 * - useTestCaseAI (AI generation)
 * - useTestCaseExecution (execution)
 */

import { useState, useEffect, useCallback } from 'react';
import { useHostManager } from '../../contexts/index';
import { useDeviceData } from '../../contexts/device/DeviceDataContext';
import { useDeviceControlWithForceUnlock } from '../useDeviceControlWithForceUnlock';
import { useUserInterface } from './useUserInterface';
import { useTestCaseAI } from '../testcase';
import { useTestCaseExecution } from '../testcase/useTestCaseExecution';
import { useExecutionState } from '../testcase/useExecutionState';
import { useMCPProxy } from '../useMCPProxy';  // NEW: MCP Proxy hook
import { filterCompatibleInterfaces } from '../../utils/userinterface/deviceCompatibilityUtils';
import { buildServerUrl } from '../../utils/buildUrlUtils';
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
    requireTreeId: false, // MCP Playground doesn't require tree_id (optional navigation)
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
  
  // ==================== INTERFACE & NAVIGATION ====================
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
        
        // Use shared compatibility utility
        const compatibleInterfaces = filterCompatibleInterfaces(interfaces, selectedDevice);
        
        const names = compatibleInterfaces.map((ui: any) => ui.name);
        
        setCompatibleInterfaceNames(names);
        
        // Auto-select first interface if current selection is not in the list
        if (names.length > 0 && !names.includes(userinterfaceName)) {
          setUserinterfaceName(names[0]);
        }
      } catch (error) {
        console.error('[@useMCPPlaygroundPage] Failed to load compatible interfaces:', error);
      }
    };
    
    loadCompatibleInterfaces();
  }, [selectedDeviceId, selectedHost, getAllUserInterfaces, userinterfaceName, setUserinterfaceName]);
  
  // Load navigation nodes when interface changes (REUSE SAME API AS TESTCASEBUILDER)
  useEffect(() => {
    const loadNodesForInterface = async () => {
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
          setIsLoadingTree(false);
          return;
        }
        
        // REUSE EXACT SAME API AS TESTCASEBUILDER (NavigationConfigContext.tsx line 284)
        // GET /server/navigationTrees/getTreeByUserInterfaceId/{userInterfaceId}?include_nested=true
        console.log(`[@useMCPPlaygroundPage] Loading nodes from /server/navigationTrees/getTreeByUserInterfaceId/${interfaceData.id}`);
        
        const response = await fetch(
          buildServerUrl(`/server/navigationTrees/getTreeByUserInterfaceId/${interfaceData.id}?include_nested=true`)
        );
        
        if (!response.ok) {
          throw new Error(`Failed to load navigation nodes: ${response.statusText}`);
        }
        
        const result = await response.json();
        
        if (!result.success || !result.tree) {
          console.warn(`[@useMCPPlaygroundPage] No tree returned for interface ${userinterfaceName}`);
          setNavNodes([]);
          setCurrentTreeId(null);
          setIsLoadingTree(false);
          return;
        }
        
        // Extract nodes from tree metadata (SAME AS TESTCASEBUILDER)
        const nodes = result.tree.metadata?.nodes || [];
        const tree_id = result.tree.id;
        
        setCurrentTreeId(tree_id);
        
        // Filter out ENTRY nodes (same as TestCaseBuilder does)
        const filteredNodes = nodes.filter((node: any) => 
          node.id !== 'ENTRY' && 
          node.type !== 'entry' &&
          node.label?.toLowerCase() !== 'entry'
        );
        
        setNavNodes(filteredNodes);
        console.log(`[@useMCPPlaygroundPage] ✅ Loaded ${filteredNodes.length} nodes from API (total: ${nodes.length}, tree_id: ${tree_id})`);
        
      } catch (error) {
        console.error('[@useMCPPlaygroundPage] Error loading nodes:', error);
        setNavNodes([]);
        setCurrentTreeId(null);
      } finally {
        setIsLoadingTree(false);
      }
    };
    
    loadNodesForInterface();
  }, [userinterfaceName, getUserInterfaceByName]);
  
  // ==================== AI GENERATION (REUSE FROM TESTCASEBUILDER) ====================
  const { generateTestCaseFromPrompt } = useTestCaseAI();
  const { executeTestCase } = useTestCaseExecution();
  const unifiedExecution = useExecutionState();
  const { executePrompt: executeMCPPrompt, isExecuting: isMCPExecuting } = useMCPProxy();  // NEW: MCP Proxy
  
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
    
    if (!selectedDeviceId || !selectedHost) {
      console.error('[@useMCPPlaygroundPage] No device selected');
      addToHistory(prompt, false, { error: 'No device selected' });
      return;
    }
    
    setIsGenerating(true);
    setDisambiguationData(null);
    
    try {
      console.log('[@useMCPPlaygroundPage] Sending prompt to MCP Proxy (OpenRouter + Function Calling):', prompt);
      
      // Get selected device to extract device_model
      const selectedDevice = selectedHost.devices?.find((d: any) => d.device_id === selectedDeviceId);
      
      // NEW: Use MCP Proxy with OpenRouter function calling
      const result = await executeMCPPrompt(
        prompt,
        selectedDeviceId,
        selectedHost.host_name,
        userinterfaceName,
        undefined, // team_id (optional)
        currentTreeId || undefined,  // tree_id (optional, for navigation)
        selectedDevice?.device_model || 'android_mobile'  // device_model
      );
      
      console.log('[@useMCPPlaygroundPage] MCP Proxy result:', result);
      console.log('[@useMCPPlaygroundPage] Tool calls made:', result.tool_calls);
      
      // Add to history
      addToHistory(prompt, true, result);
      setExecutionResult(result);
      
    } catch (error) {
      console.error('[@useMCPPlaygroundPage] Error generating:', error);
      addToHistory(prompt, false, { error: error instanceof Error ? error.message : 'Unknown error' });
    } finally {
      setIsGenerating(false);
    }
  }, [prompt, userinterfaceName, selectedDeviceId, selectedHost, currentTreeId, executeMCPPrompt, addToHistory]);
  
  const handleDisambiguationResolve = useCallback(async (resolutions: Record<string, string>) => {
    if (!disambiguationData) return;
    
    if (!selectedDeviceId || !selectedHost) {
      console.error('[@useMCPPlaygroundPage] No device selected');
      return;
    }
    
    setIsGenerating(true);
    setDisambiguationData(null);
    
    try {
      const result = await generateTestCaseFromPrompt(
        disambiguationData.originalPrompt,
        userinterfaceName,
        selectedDeviceId,
        selectedHost.host_name
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
  }, [disambiguationData, userinterfaceName, selectedDeviceId, selectedHost, generateTestCaseFromPrompt, executeGraph, addToHistory]);
  
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

