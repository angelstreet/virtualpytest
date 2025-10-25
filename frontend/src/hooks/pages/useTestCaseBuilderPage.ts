/**
 * TestCaseBuilder Page Hook
 * 
 * Orchestrates all TestCaseBuilder page logic:
 * - Device control and host management
 * - Interface and navigation tree loading
 * - AI generation
 * - Test case operations (save, load, execute)
 * - Toolbox building
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import { useHostManager } from '../../contexts/index';
import { useDeviceData } from '../../contexts/device/DeviceDataContext';
import { useDeviceControl } from '../useDeviceControl';
import { useNavigationEditor } from '../navigation/useNavigationEditor';
import { useNavigationConfig } from '../../contexts/navigation/NavigationConfigContext';
import { useUserInterface } from './useUserInterface';
import { useTestCaseBuilder } from '../../contexts/testcase/TestCaseBuilderContext';
import { useTestCaseAI } from '../testcase';
import { buildToolboxFromNavigationData } from '../../utils/toolboxBuilder';

export interface UseTestCaseBuilderPageReturn {
  // Device & Host
  selectedHost: any;
  selectedDeviceId: string | null;
  isControlActive: boolean;
  isControlLoading: boolean;
  isRemotePanelOpen: boolean;
  showRemotePanel: boolean;
  showAVPanel: boolean;
  availableHosts: any[];
  handleDeviceSelect: (host: any | null, deviceId: string | null) => void;
  handleDeviceControl: () => Promise<void>;
  handleToggleRemotePanel: () => void;
  handleDisconnectComplete: () => void;
  isDeviceLocked: (deviceKey: string) => boolean;
  
  // Interface & Navigation
  compatibleInterfaceNames: string[];
  userinterfaceName: string;
  setUserinterfaceName: (name: string) => void;
  navNodes: any[];
  
  // Actions & Verifications
  availableActions: any;
  availableVerifications: any;
  areActionsLoaded: boolean;
  
  // Toolbox
  dynamicToolboxConfig: any;
  
  // AI Generation
  creationMode: 'visual' | 'ai';
  setCreationMode: (mode: 'visual' | 'ai') => void;
  aiPrompt: string;
  setAiPrompt: (prompt: string) => void;
  isGenerating: boolean;
  handleGenerateWithAI: () => Promise<void>;
  
  // Test Case Operations
  testcaseName: string;
  setTestcaseName: (name: string) => void;
  description: string;
  setDescription: (desc: string) => void;
  currentTestcaseId: string | null;
  testcaseList: any[];
  hasUnsavedChanges: boolean;
  handleSave: () => Promise<void>;
  handleLoad: (testcaseId: string) => Promise<void>;
  handleDelete: (testcaseId: string, testcaseName: string) => Promise<void>;
  handleExecute: () => Promise<void>;
  handleNew: () => void;
  
  // Dialogs
  saveDialogOpen: boolean;
  setSaveDialogOpen: (open: boolean) => void;
  loadDialogOpen: boolean;
  setLoadDialogOpen: (open: boolean) => void;
  deleteConfirmOpen: boolean;
  setDeleteConfirmOpen: (open: boolean) => void;
  deleteTargetTestCase: { id: string; name: string } | null;
  setDeleteTargetTestCase: (target: { id: string; name: string } | null) => void;
  newConfirmOpen: boolean;
  setNewConfirmOpen: (open: boolean) => void;
  handleConfirmDelete: () => Promise<void>;
  handleConfirmNew: () => void;
  
  // Execution (NEW: Unified execution state)
  unifiedExecution: ReturnType<typeof useTestCaseBuilder>['unifiedExecution'];
  
  // AV Panel
  isAVPanelCollapsed: boolean;
  setIsAVPanelCollapsed: (collapsed: boolean) => void;
  isAVPanelMinimized: boolean;
  setIsAVPanelMinimized: (minimized: boolean) => void;
  captureMode: 'stream' | 'screenshot' | 'video';
  setCaptureMode: (mode: 'stream' | 'screenshot' | 'video') => void;
  isVerificationVisible: boolean;
  handleAVPanelCollapsedChange: (collapsed: boolean) => void;
  handleCaptureModeChange: (mode: 'stream' | 'screenshot' | 'video') => void;
  handleAVPanelMinimizedChange: (minimized: boolean) => void;
  
  // Snackbar
  snackbar: {
    open: boolean;
    message: string;
    severity: 'success' | 'error' | 'info';
  };
  setSnackbar: (snackbar: any) => void;
  
  // TestCase Builder Context
  nodes: any[];
  edges: any[];
  selectedBlock: any;
  setSelectedBlock: (block: any) => void;
  isConfigDialogOpen: boolean;
  setIsConfigDialogOpen: (open: boolean) => void;
  executionState: any;
  isExecutable: boolean;
  addBlock: (type: string, position: any, defaultData?: any) => void;
  updateBlock: (id: string, data: any) => void;
  onNodesChange: (changes: any) => void;
  onEdgesChange: (changes: any) => void;
  onConnect: (connection: any) => void;
  setNodes: (nodes: any) => void;
  setEdges: (edges: any) => void;
}

export function useTestCaseBuilderPage(): UseTestCaseBuilderPageReturn {
  // ==================== HOST & DEVICE ====================
  const {
    selectedHost,
    selectedDeviceId,
    isControlActive,
    isRemotePanelOpen,
    showRemotePanel,
    showAVPanel,
    availableHosts,
    handleDeviceSelect: hostManagerDeviceSelect,
    handleControlStateChange,
    handleToggleRemotePanel,
    handleDisconnectComplete,
    isDeviceLocked: hostManagerIsDeviceLocked,
  } = useHostManager();
  
  // Wrapper for handleDeviceSelect - no need to convert, just pass through
  const handleDeviceSelect = hostManagerDeviceSelect;
  
  // Wrapper for isDeviceLocked to match expected signature
  const isDeviceLocked = useCallback((deviceKey: string) => {
    const [hostName, deviceId] = deviceKey.includes(':')
      ? deviceKey.split(':')
      : [deviceKey, 'device1'];
    
    const host = availableHosts.find((h: any) => h.host_name === hostName);
    return hostManagerIsDeviceLocked(host || null, deviceId);
  }, [availableHosts, hostManagerIsDeviceLocked]);
  
  const {
    isControlLoading,
    handleTakeControl,
    handleReleaseControl,
  } = useDeviceControl({
    host: selectedHost,
    device_id: selectedDeviceId || 'device1',
    sessionId: 'testcase-builder-session',
    autoCleanup: true,
  });
  
  const handleDeviceControl = useCallback(async () => {
    if (isControlActive) {
      await handleReleaseControl();
      handleControlStateChange(false);
    } else {
      const success = await handleTakeControl();
      if (success) {
        handleControlStateChange(true);
      }
    }
  }, [isControlActive, handleTakeControl, handleReleaseControl, handleControlStateChange]);
  
  // ==================== DEVICE DATA ====================
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
  const { setUserInterfaceFromProps } = useNavigationEditor();
  const { loadTreeByUserInterface } = useNavigationConfig();
  const { getAllUserInterfaces, getUserInterfaceByName } = useUserInterface();
  const { generateTestCaseFromPrompt } = useTestCaseAI();
  
  const [compatibleInterfaceNames, setCompatibleInterfaceNames] = useState<string[]>([]);
  const [navNodes, setNavNodes] = useState<any[]>([]);
  
  const {
    userinterfaceName,
    setUserinterfaceName,
  } = useTestCaseBuilder();
  
  // Load compatible interfaces
  useEffect(() => {
    const loadCompatibleInterfaces = async () => {
      if (!selectedDeviceId || !selectedHost || !isControlActive) {
        setCompatibleInterfaceNames([]);
        setUserinterfaceName('');
        return;
      }
      
      try {
        const selectedDevice = selectedHost.devices?.find((d: any) => d.device_id === selectedDeviceId);
        const deviceModel = selectedDevice?.device_model;
        
        const interfaces = await getAllUserInterfaces();
        
        const compatibleInterfaces = interfaces.filter((ui: any) => {
          const hasTree = !!ui.root_tree;
          const isCompatible = ui.models?.includes(deviceModel);
          return hasTree && isCompatible;
        });
        
        const names = compatibleInterfaces.map((ui: any) => ui.name);
        
        setCompatibleInterfaceNames(names);
        
        if (names.length > 0 && !names.includes(userinterfaceName)) {
          setUserinterfaceName(names[0]);
        }
      } catch (error) {
        console.error('[@useTestCaseBuilderPage] Failed to load compatible interfaces:', error);
      }
    };
    
    loadCompatibleInterfaces();
  }, [selectedDeviceId, selectedHost, isControlActive, getAllUserInterfaces, userinterfaceName, setUserinterfaceName]);
  
  // Load navigation tree
  useEffect(() => {
    const loadNavigationTree = async () => {
      if (!selectedDeviceId || !userinterfaceName) {
        setNavNodes([]);
        return;
      }
      
      try {
        const userInterface = await getUserInterfaceByName(userinterfaceName);
        
        if (userInterface) {
          const result = await loadTreeByUserInterface(userInterface.id);
          setUserInterfaceFromProps(userInterface);
          
          const nodes = result?.tree?.metadata?.nodes || result?.nodes || [];
          setNavNodes(nodes);
        }
      } catch (error) {
        console.error('[@useTestCaseBuilderPage] Failed to load tree:', error);
        setNavNodes([]);
      }
    };
    
    loadNavigationTree();
  }, [selectedDeviceId, userinterfaceName, getUserInterfaceByName, loadTreeByUserInterface, setUserInterfaceFromProps]);
  
  // ==================== TOOLBOX ====================
  const dynamicToolboxConfig = useMemo(() => {
    if (!selectedDeviceId || !userinterfaceName || navNodes.length === 0) {
      return null;
    }
    
    return buildToolboxFromNavigationData(navNodes, availableActions, availableVerifications);
  }, [selectedDeviceId, userinterfaceName, navNodes, availableActions, availableVerifications]);
  
  // ==================== TEST CASE CONTEXT ====================
  const {
    nodes,
    edges,
    selectedBlock,
    setSelectedBlock,
    isConfigDialogOpen,
    setIsConfigDialogOpen,
    executionState,
    isExecutable,
    testcaseName,
    setTestcaseName,
    description,
    setDescription,
    currentTestcaseId,
    testcaseList,
    hasUnsavedChanges,
    addBlock,
    updateBlock,
    onNodesChange,
    onEdgesChange,
    onConnect,
    saveCurrentTestCase,
    loadTestCase,
    executeCurrentTestCase,
    fetchTestCaseList,
    deleteTestCaseById,
    resetBuilder,
    setNodes,
    setEdges,
    unifiedExecution, // 🆕 ADD: Extract unifiedExecution from context
  } = useTestCaseBuilder();
  
  // ==================== AI GENERATION ====================
  const [creationMode, setCreationMode] = useState<'visual' | 'ai'>('visual');
  const [aiPrompt, setAiPrompt] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  
  // ==================== DIALOGS ====================
  const [saveDialogOpen, setSaveDialogOpen] = useState(false);
  const [loadDialogOpen, setLoadDialogOpen] = useState(false);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [deleteTargetTestCase, setDeleteTargetTestCase] = useState<{ id: string; name: string } | null>(null);
  const [newConfirmOpen, setNewConfirmOpen] = useState(false);
  
  useEffect(() => {
    if (loadDialogOpen) {
      fetchTestCaseList();
    }
  }, [loadDialogOpen, fetchTestCaseList]);
  
  // ==================== AV PANEL ====================
  const [isAVPanelCollapsed, setIsAVPanelCollapsed] = useState(true);
  const [isAVPanelMinimized, setIsAVPanelMinimized] = useState(false);
  const [captureMode, setCaptureMode] = useState<'stream' | 'screenshot' | 'video'>('stream');
  const isVerificationVisible = captureMode === 'screenshot' || captureMode === 'video';
  
  const handleAVPanelCollapsedChange = useCallback((isCollapsed: boolean) => {
    setIsAVPanelCollapsed(isCollapsed);
  }, []);
  
  const handleCaptureModeChange = useCallback((mode: 'stream' | 'screenshot' | 'video') => {
    setCaptureMode(mode);
  }, []);
  
  const handleAVPanelMinimizedChange = useCallback((isMinimized: boolean) => {
    setIsAVPanelMinimized(isMinimized);
  }, []);
  
  // ==================== SNACKBAR ====================
  const [snackbar, setSnackbar] = useState<{
    open: boolean;
    message: string;
    severity: 'success' | 'error' | 'info';
  }>({
    open: false,
    message: '',
    severity: 'info',
  });
  
  // ==================== TEST CASE OPERATIONS ====================
  const handleSave = useCallback(async () => {
    const result = await saveCurrentTestCase();
    if (result.success) {
      setSnackbar({
        open: true,
        message: `Test case "${testcaseName}" saved successfully`,
        severity: 'success',
      });
      setSaveDialogOpen(false);
    } else {
      setSnackbar({
        open: true,
        message: `Save failed: ${result.error}`,
        severity: 'error',
      });
    }
  }, [saveCurrentTestCase, testcaseName]);
  
  const handleLoad = useCallback(async (testcaseId: string) => {
    await loadTestCase(testcaseId);
    setLoadDialogOpen(false);
    setSnackbar({
      open: true,
      message: `Test case "${testcaseName}" loaded successfully`,
      severity: 'success',
    });
  }, [loadTestCase, testcaseName]);
  
  const handleDelete = useCallback(async (testcaseId: string, testcaseName: string): Promise<void> => {
    setDeleteTargetTestCase({ id: testcaseId, name: testcaseName });
    setDeleteConfirmOpen(true);
  }, []);
  
  const handleConfirmDelete = useCallback(async () => {
    if (deleteTargetTestCase) {
      await deleteTestCaseById(deleteTargetTestCase.id);
      setSnackbar({
        open: true,
        message: `Test case "${deleteTargetTestCase.name}" deleted!`,
        severity: 'info',
      });
      setDeleteConfirmOpen(false);
      setDeleteTargetTestCase(null);
    }
  }, [deleteTargetTestCase, deleteTestCaseById]);
  
  const handleExecute = useCallback(async () => {
    if (!selectedHost?.host_name) {
      setSnackbar({
        open: true,
        message: 'Please select a host first',
        severity: 'error',
      });
      return;
    }
    
    await executeCurrentTestCase(selectedHost.host_name);
    
    if (executionState.result) {
      if (executionState.result.success) {
        setSnackbar({
          open: true,
          message: `Execution completed successfully in ${executionState.result.execution_time_ms}ms`,
          severity: 'success',
        });
      } else {
        setSnackbar({
          open: true,
          message: 'Execution failed',
          severity: 'error',
        });
      }
    }
  }, [selectedHost, executeCurrentTestCase, executionState]);
  
  const handleNew = useCallback(() => {
    setNewConfirmOpen(true);
  }, []);
  
  const handleConfirmNew = useCallback(() => {
    resetBuilder();
    setCreationMode('visual');
    setAiPrompt('');
    setNewConfirmOpen(false);
    setSnackbar({
      open: true,
      message: 'Ready to create new test case',
      severity: 'info',
    });
  }, [resetBuilder, setCreationMode, setAiPrompt]);
  
  // ==================== AI GENERATION ====================
  const handleGenerateWithAI = useCallback(async () => {
    if (!aiPrompt.trim()) {
      setSnackbar({
        open: true,
        message: 'Please enter a prompt',
        severity: 'error',
      });
      return;
    }

    if (!userinterfaceName) {
      setSnackbar({
        open: true,
        message: 'Please select a user interface',
        severity: 'error',
      });
      return;
    }

    if (!selectedHost) {
      setSnackbar({
        open: true,
        message: 'Please select a host device',
        severity: 'error',
      });
      return;
    }

    setIsGenerating(true);
    
    try {
      const result = await generateTestCaseFromPrompt(
        aiPrompt, 
        userinterfaceName,
        selectedDeviceId || 'device1',
        selectedHost.host_name
      );
      
      if (result.success && result.graph) {
        setNodes(result.graph.nodes.map((node: any) => ({
          id: node.id,
          type: node.type as any,
          position: node.position,
          data: node.data
        })));
        
        setEdges(result.graph.edges.map((edge: any) => ({
          id: edge.id,
          source: edge.source,
          target: edge.target,
          sourceHandle: edge.sourceHandle,
          type: edge.type as any,
          style: { 
            stroke: edge.type === 'success' ? '#10b981' : '#ef4444',
            strokeWidth: 2
          }
        })));
        
        setSnackbar({
          open: true,
          message: 'Test case generated! Review and save when ready.',
          severity: 'success',
        });
        
        setCreationMode('visual');
      } else {
        setSnackbar({
          open: true,
          message: `Generation failed: ${result.error || 'Unknown error'}`,
          severity: 'error',
        });
      }
    } catch (error) {
      console.error('AI generation error:', error);
      setSnackbar({
        open: true,
        message: `Generation failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
        severity: 'error',
      });
    } finally {
      setIsGenerating(false);
    }
  }, [aiPrompt, userinterfaceName, selectedHost, selectedDeviceId, setNodes, setEdges, setTestcaseName, setDescription]);
  
  // ==================== RETURN ====================
  return {
    // Device & Host
    selectedHost,
    selectedDeviceId,
    isControlActive,
    isControlLoading,
    isRemotePanelOpen,
    showRemotePanel,
    showAVPanel,
    availableHosts,
    handleDeviceSelect,
    handleDeviceControl,
    handleToggleRemotePanel,
    handleDisconnectComplete,
    isDeviceLocked,
    
    // Interface & Navigation
    compatibleInterfaceNames,
    userinterfaceName,
    setUserinterfaceName,
    navNodes,
    
    // Actions & Verifications
    availableActions,
    availableVerifications,
    areActionsLoaded,
    
    // Toolbox
    dynamicToolboxConfig,
    
    // AI Generation
    creationMode,
    setCreationMode,
    aiPrompt,
    setAiPrompt,
    isGenerating,
    handleGenerateWithAI,
    
    // Test Case Operations
    testcaseName,
    setTestcaseName,
    description,
    setDescription,
    currentTestcaseId,
    testcaseList,
    hasUnsavedChanges,
    handleSave,
    handleLoad,
    handleDelete,
    handleExecute,
    handleNew,
    
    // Dialogs
    saveDialogOpen,
    setSaveDialogOpen,
    loadDialogOpen,
    setLoadDialogOpen,
    deleteConfirmOpen,
    setDeleteConfirmOpen,
    deleteTargetTestCase,
    setDeleteTargetTestCase,
    newConfirmOpen,
    setNewConfirmOpen,
    handleConfirmDelete,
    handleConfirmNew,
    
    // AV Panel
    isAVPanelCollapsed,
    setIsAVPanelCollapsed,
    isAVPanelMinimized,
    setIsAVPanelMinimized,
    captureMode,
    setCaptureMode,
    isVerificationVisible,
    handleAVPanelCollapsedChange,
    handleCaptureModeChange,
    handleAVPanelMinimizedChange,
    
    // Snackbar
    snackbar,
    setSnackbar,
    
    // TestCase Builder Context
    nodes,
    edges,
    selectedBlock,
    setSelectedBlock,
    isConfigDialogOpen,
    setIsConfigDialogOpen,
    executionState,
    isExecutable,
    addBlock,
    updateBlock,
    onNodesChange,
    onEdgesChange,
    onConnect,
    setNodes,
    setEdges,
    
    // 🆕 NEW: Unified execution state
    unifiedExecution,
  };
}

