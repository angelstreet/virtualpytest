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
import { useDeviceControlWithForceUnlock } from '../useDeviceControlWithForceUnlock';
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
  isLoadingTree: boolean; // NEW: Tree loading state
  currentTreeId: string | null; // NEW: Current tree ID
  
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
  testcaseFolder: string; // NEW
  setTestcaseFolder: (folder: string) => void; // NEW
  testcaseTags: string[]; // NEW
  setTestcaseTags: (tags: string[]) => void; // NEW
  currentTestcaseId: string | null;
  testcaseList: any[];
  isLoadingTestCaseList: boolean;
  hasUnsavedChanges: boolean;
  handleSave: () => Promise<{ success: boolean; error?: string }>;
  handleLoad: (testcaseId: string) => Promise<void>;
  handleDelete: (testcaseId: string, testcaseName: string) => Promise<void>;
  handleExecute: () => Promise<void>;
  handleNew: () => void;
  
  // Dialogs
  saveDialogOpen: boolean;
  setSaveDialogOpen: (open: boolean) => void;
  loadDialogOpen: boolean;
  setLoadDialogOpen: (open: boolean) => void;
  isLoadingTestCases: boolean;
  handleLoadClick: () => Promise<void>;
  deleteConfirmOpen: boolean;
  setDeleteConfirmOpen: (open: boolean) => void;
  deleteTargetTestCase: { id: string; name: string } | null;
  setDeleteTargetTestCase: (target: { id: string; name: string } | null) => void;
  newConfirmOpen: boolean;
  setNewConfirmOpen: (open: boolean) => void;
  handleConfirmDelete: () => Promise<void>;
  handleConfirmNew: () => void;
  aiGenerateConfirmOpen: boolean;
  setAiGenerateConfirmOpen: (open: boolean) => void;
  handleConfirmAIGenerate: () => void;
  aiGenerationResult: any | null;
  showAIResultPanel: boolean;
  handleCloseAIResultPanel: () => void;
  handleRegenerateAI: () => void;
  handleShowLastGeneration: () => void;
  
  // AI Disambiguation
  disambiguationData: any | null;
  handleDisambiguationResolve: (selections: Record<string, string>, saveToDb: boolean) => void;
  handleDisambiguationCancel: () => void;
  handleDisambiguationEditPrompt: () => void;
  
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
  
  // ==================== INTERFACE & NAVIGATION (EARLY DECLARATION) ====================
  // Declare currentTreeId early so it can be used by device control hook
  const [currentTreeId, setCurrentTreeId] = useState<string | null>(null);
  const [isLoadingTree, setIsLoadingTree] = useState(false);
  
  // ==================== SNACKBAR (EARLY DECLARATION) ====================
  // Declare snackbar early so it can be used in control error display
  const [snackbar, setSnackbar] = useState<{
    open: boolean;
    message: string;
    severity: 'success' | 'error' | 'info';
  }>({
    open: false,
    message: '',
    severity: 'info',
  });
  
  // Use enhanced device control hook with force unlock and tree_id support
  const {
    isControlLoading,
    handleDeviceControl,
    controlError,
    clearError,
  } = useDeviceControlWithForceUnlock({
    host: selectedHost,
    device_id: selectedDeviceId,
    sessionId: 'testcase-builder-session',
    autoCleanup: true,
    tree_id: currentTreeId || undefined, // Pass tree_id for cache building
    onControlStateChange: handleControlStateChange,
  });
  
  // Show control errors
  useEffect(() => {
    if (controlError) {
      setSnackbar({
        open: true,
        message: controlError,
        severity: 'error',
      });
      clearError();
    }
  }, [controlError, clearError]);
  
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
  const { generateTestCaseFromPrompt, saveDisambiguationAndRegenerate } = useTestCaseAI();
  
  const [compatibleInterfaceNames, setCompatibleInterfaceNames] = useState<string[]>([]);
  const [navNodes, setNavNodes] = useState<any[]>([]);
  // Note: currentTreeId is declared earlier for use in device control hook
  
  const {
    userinterfaceName,
    setUserinterfaceName,
  } = useTestCaseBuilder();
  
  // Load compatible interfaces
  useEffect(() => {
    const loadCompatibleInterfaces = async () => {
      if (!selectedDeviceId || !selectedHost) {
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
  }, [selectedDeviceId, selectedHost, getAllUserInterfaces, userinterfaceName, setUserinterfaceName]);
  
  // Load navigation tree
  useEffect(() => {
    const loadNavigationTree = async () => {
      if (!selectedDeviceId || !userinterfaceName) {
        setNavNodes([]);
        setCurrentTreeId(null);
        setIsLoadingTree(false);
        return;
      }
      
      setIsLoadingTree(true);
      
      try {
        const userInterface = await getUserInterfaceByName(userinterfaceName);
        
        if (userInterface) {
          const result = await loadTreeByUserInterface(userInterface.id);
          setUserInterfaceFromProps(userInterface);
          
          console.log('[@useTestCaseBuilderPage] 🔍 DEBUG result structure:', {
            result_tree_id: result?.tree?.id,
            userInterface_root_tree: userInterface.root_tree,
            full_result: result
          });
          
          const nodes = result?.tree?.metadata?.nodes || result?.nodes || [];
          const treeId = result?.tree?.id || userInterface.root_tree;
          
          setNavNodes(nodes);
          setCurrentTreeId(treeId);
          
          console.log('[@useTestCaseBuilderPage] ✅ Loaded navigation tree:', {
            interface: userinterfaceName,
            treeId: treeId,
            nodeCount: nodes.length
          });
          
          if (!treeId) {
            console.error('[@useTestCaseBuilderPage] ❌ CRITICAL: tree_id is undefined!', {
              userInterface,
              result
            });
          } else {
            console.log('[@useTestCaseBuilderPage] 🗺️ tree_id ready for cache building:', treeId);
          }
        }
      } catch (error) {
        console.error('[@useTestCaseBuilderPage] ❌ Failed to load tree:', error);
        setNavNodes([]);
        setCurrentTreeId(null);
      } finally {
        setIsLoadingTree(false);
      }
    };
    
    loadNavigationTree();
  }, [selectedDeviceId, userinterfaceName, getUserInterfaceByName, loadTreeByUserInterface, setUserInterfaceFromProps]);
  
  // ==================== TOOLBOX ====================
  const dynamicToolboxConfig = useMemo(() => {
    if (!selectedDeviceId || !userinterfaceName || navNodes.length === 0) {
      return null;
    }
    
    // Only show toolbox after taking control, not just on device selection
    return buildToolboxFromNavigationData(navNodes, availableActions, availableVerifications, isControlActive);
  }, [selectedDeviceId, userinterfaceName, navNodes, availableActions, availableVerifications, isControlActive]);
  
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
    testcaseFolder, // NEW
    setTestcaseFolder, // NEW
    testcaseTags, // NEW
    setTestcaseTags, // NEW
    currentTestcaseId,
    testcaseList,
    isLoadingTestCaseList,
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
  const [isLoadingTestCases, setIsLoadingTestCases] = useState(false);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [deleteTargetTestCase, setDeleteTargetTestCase] = useState<{ id: string; name: string } | null>(null);
  const [newConfirmOpen, setNewConfirmOpen] = useState(false);
  const [aiGenerateConfirmOpen, setAiGenerateConfirmOpen] = useState(false);
  
  // AI Generation Result Panel State
  const [aiGenerationResult, setAiGenerationResult] = useState<any | null>(null);
  const [showAIResultPanel, setShowAIResultPanel] = useState(false);
  
  // AI Disambiguation state
  const [disambiguationData, setDisambiguationData] = useState<any | null>(null);
  
  // Handle Load button click - fetch data first, then open dialog
  const handleLoadClick = useCallback(async () => {
    setIsLoadingTestCases(true);
    await fetchTestCaseList();
    setIsLoadingTestCases(false);
    setLoadDialogOpen(true);
  }, [fetchTestCaseList]);
  
  // Remove the useEffect that fetches when dialog opens since we fetch before opening now
  // useEffect(() => {
  //   if (loadDialogOpen) {
  //     fetchTestCaseList();
  //   }
  // }, [loadDialogOpen, fetchTestCaseList]);
  
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
  // Note: snackbar state is declared earlier for use in control error display
  
  // ==================== TEST CASE OPERATIONS ====================
  const handleSave = useCallback(async (): Promise<{ success: boolean; error?: string }> => {
    const result = await saveCurrentTestCase();
    if (result.success) {
      // Don't show toast - success is shown in dialog with green tick
      // Don't close dialog here - let the caller handle it
      return result;
    } else {
      setSnackbar({
        open: true,
        message: `Save failed: ${result.error}`,
        severity: 'error',
      });
      return result;
    }
  }, [saveCurrentTestCase]);
  
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
    
    // Execute without showing toast - ExecutionProgressBar shows the status
    await executeCurrentTestCase(selectedHost.host_name);
  }, [selectedHost, executeCurrentTestCase]);
  
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

    if (!isControlActive) {
      setSnackbar({
        open: true,
        message: 'Please take control of the device first',
        severity: 'error',
      });
      return;
    }

    // Check for unsaved changes or existing nodes
    const hasExistingGraph = nodes.length > 2; // More than START and SUCCESS nodes
    const hasCurrentTestCase = !!currentTestcaseId; // Has a loaded test case
    
    // Only show warning if there's actual content to lose (existing graph OR saved test case with changes)
    if (hasExistingGraph && (hasUnsavedChanges || hasCurrentTestCase)) {
      // Show confirmation dialog
      setAiGenerateConfirmOpen(true);
      return;
    }

    // Proceed with generation
    await performAIGeneration();
  }, [aiPrompt, userinterfaceName, selectedHost, hasUnsavedChanges, nodes.length, currentTestcaseId]);

  const performAIGeneration = useCallback(async () => {
    setIsGenerating(true);
    
    try {
      console.log('[@useTestCaseBuilderPage] Starting AI generation');
      const result = await generateTestCaseFromPrompt(
        aiPrompt, 
        userinterfaceName,
        selectedDeviceId || 'device1',
        selectedHost!.host_name
      );
      
      console.log('[@useTestCaseBuilderPage] AI generation result:', {
        success: result.success,
        needs_disambiguation: result.needs_disambiguation,
        has_graph: !!result.graph
      });
      
      // Handle disambiguation
      if (result.needs_disambiguation) {
        console.log('[@useTestCaseBuilderPage] Disambiguation needed, showing modal');
        setDisambiguationData(result);
        setIsGenerating(false);
        return;
      }
      
      if (result.success && result.graph) {
        // Load graph onto ReactFlow canvas (like loading a test case)
        const loadedNodes = result.graph.nodes.map((node: any) => ({
          id: node.id,
          type: node.type as any,
          position: node.position,
          data: node.data
        }));
        
        const loadedEdges = result.graph.edges.map((edge: any) => ({
          id: edge.id,
          source: edge.source,
          target: edge.target,
          sourceHandle: edge.sourceHandle,
          type: edge.type as any,
          style: { 
            stroke: edge.type === 'success' ? '#10b981' : '#ef4444',
            strokeWidth: 2
          }
        }));
        
        // 🆕 AUTO-LAYOUT: Apply vertical layout immediately after AI generation
        const { getLayoutedElements } = await import('../../components/testcase/ai/autoLayout');
        const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
          loadedNodes,
          loadedEdges,
          { direction: 'TB' } // Force vertical layout
        );
        
        setNodes(layoutedNodes);
        setEdges(layoutedEdges);
        
        // Store the generation result for the result panel
        setAiGenerationResult(result);
        setShowAIResultPanel(true);
        
        // Switch to visual mode to show the graph
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
      setAiGenerateConfirmOpen(false); // Close dialog after generation
    }
  }, [aiPrompt, userinterfaceName, selectedHost, selectedDeviceId, setNodes, setEdges, setTestcaseName, setDescription, generateTestCaseFromPrompt, setCreationMode]);
  
  const handleConfirmAIGenerate = useCallback(() => {
    performAIGeneration();
  }, [performAIGeneration]);
  
  const handleCloseAIResultPanel = useCallback(() => {
    setShowAIResultPanel(false);
    // Keep aiGenerationResult so user can reopen it
  }, []);
  
  const handleShowLastGeneration = useCallback(() => {
    if (aiGenerationResult) {
      setShowAIResultPanel(true);
    }
  }, [aiGenerationResult]);
  
  const handleRegenerateAI = useCallback(() => {
    setShowAIResultPanel(false);
    setAiGenerationResult(null);
    setCreationMode('ai'); // Switch back to AI mode
  }, [setCreationMode]);
  
  // Disambiguation handlers
  const handleDisambiguationResolve = useCallback(async (
    selections: Record<string, string>,
    saveToDb: boolean
  ) => {
    console.log('[@useTestCaseBuilderPage] Resolving disambiguation', { selections, saveToDb });
    setDisambiguationData(null);
    setIsGenerating(true);
    
    try {
      if (saveToDb) {
        // Convert selections to array format expected by API
        const selectionsArray = Object.entries(selections).map(([phrase, resolved]) => ({
          phrase,
          resolved
        }));
        
        // Save disambiguation choices
        await saveDisambiguationAndRegenerate(
          aiPrompt,
          selectionsArray,
          userinterfaceName,
          selectedDeviceId || 'device1',
          selectedHost!.host_name
        );
      }
      
      // Regenerate with resolved selections
      await performAIGeneration();
    } catch (error) {
      console.error('[@useTestCaseBuilderPage] Disambiguation resolve error:', error);
      setSnackbar({
        open: true,
        message: `Failed to apply disambiguation: ${error instanceof Error ? error.message : 'Unknown error'}`,
        severity: 'error',
      });
      setIsGenerating(false);
    }
  }, [aiPrompt, userinterfaceName, selectedDeviceId, selectedHost, performAIGeneration, saveDisambiguationAndRegenerate]);
  
  const handleDisambiguationCancel = useCallback(() => {
    console.log('[@useTestCaseBuilderPage] Disambiguation cancelled');
    setDisambiguationData(null);
    setIsGenerating(false);
  }, []);
  
  const handleDisambiguationEditPrompt = useCallback(() => {
    console.log('[@useTestCaseBuilderPage] Edit prompt requested from disambiguation');
    setDisambiguationData(null);
    setIsGenerating(false);
    setCreationMode('ai'); // Switch to AI mode to edit prompt
  }, [setCreationMode]);
  
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
    isLoadingTree,
    currentTreeId,
    
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
    testcaseFolder, // NEW
    setTestcaseFolder, // NEW
    testcaseTags, // NEW
    setTestcaseTags, // NEW
    currentTestcaseId,
    testcaseList,
    isLoadingTestCaseList,
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
    isLoadingTestCases,
    handleLoadClick,
    deleteConfirmOpen,
    setDeleteConfirmOpen,
    deleteTargetTestCase,
    setDeleteTargetTestCase,
    newConfirmOpen,
    setNewConfirmOpen,
    handleConfirmDelete,
    handleConfirmNew,
    aiGenerateConfirmOpen,
    setAiGenerateConfirmOpen,
    handleConfirmAIGenerate,
    aiGenerationResult,
    showAIResultPanel,
    handleCloseAIResultPanel,
    handleRegenerateAI,
    handleShowLastGeneration,
    
    // AI Disambiguation
    disambiguationData,
    handleDisambiguationResolve,
    handleDisambiguationCancel,
    handleDisambiguationEditPrompt,
    
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

