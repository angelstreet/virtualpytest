import React, { useCallback, useRef, DragEvent, useState, useEffect } from 'react';
import { 
  Box, 
  Button, 
  Typography, 
  Dialog, 
  DialogTitle, 
  DialogContent, 
  DialogActions,
  TextField,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  IconButton,
  Alert,
  Snackbar
} from '@mui/material';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  BackgroundVariant,
  ReactFlowProvider,
  MarkerType,
} from 'reactflow';
import 'reactflow/dist/style.css';

// Hide React Flow attribution
const styles = `
  .react-flow__panel.react-flow__attribution {
    display: none !important;
  }
`;

// Icons
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import SaveIcon from '@mui/icons-material/Save';
import FolderOpenIcon from '@mui/icons-material/FolderOpen';
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';

// Components
import { TestCaseToolbox } from '../components/testcase/builder/TestCaseToolbox';
import { StartBlock } from '../components/testcase/blocks/StartBlock';
import { SuccessBlock } from '../components/testcase/blocks/SuccessBlock';
import { FailureBlock } from '../components/testcase/blocks/FailureBlock';
import { UniversalBlock } from '../components/testcase/blocks/UniversalBlock';
import { SuccessEdge } from '../components/testcase/edges/SuccessEdge';
import { FailureEdge } from '../components/testcase/edges/FailureEdge';
import { UserinterfaceSelector } from '../components/common/UserinterfaceSelector';

// Device Control Components (REUSE from NavigationEditor)
import { RemotePanel } from '../components/controller/remote/RemotePanel';
import { DesktopPanel } from '../components/controller/desktop/DesktopPanel';
import { WebPanel } from '../components/controller/web/WebPanel';
import { VNCStream } from '../components/controller/av/VNCStream';
import { HDMIStream } from '../components/controller/av/HDMIStream';
import { DEFAULT_DEVICE_RESOLUTION } from '../config/deviceResolutions';
import { NavigationEditorDeviceControls } from '../components/navigation/Navigation_NavigationEditor_DeviceControls';

// Dialogs
import { ActionConfigDialog } from '../components/testcase/dialogs/ActionConfigDialog';
import { VerificationConfigDialog } from '../components/testcase/dialogs/VerificationConfigDialog';
import { NavigationConfigDialog } from '../components/testcase/dialogs/NavigationConfigDialog';
import { LoopConfigDialog } from '../components/testcase/dialogs/LoopConfigDialog';

// Context
import { TestCaseBuilderProvider, useTestCaseBuilder } from '../contexts/testcase/TestCaseBuilderContext';
import { NavigationEditorProvider } from '../contexts/navigation/NavigationEditorProvider';
import { NavigationConfigProvider } from '../contexts/navigation/NavigationConfigContext';
import { useNavigationEditor } from '../hooks/navigation/useNavigationEditor';
import { useDeviceData } from '../contexts/device/DeviceDataContext';
import { useHostManager } from '../contexts/index';
import { useDeviceControl } from '../hooks/useDeviceControl';
import { useTheme } from '../contexts/ThemeContext';
import { useNavigationConfig } from '../contexts/navigation/NavigationConfigContext';
import { useUserInterface } from '../hooks/pages/useUserInterface';
import { generateTestCaseFromPrompt } from '../services/aiService';
import { buildToolboxFromNavigationData } from '../utils/toolboxBuilder';

// Node types for React Flow
const nodeTypes = {
  start: StartBlock,
  success: SuccessBlock,
  failure: FailureBlock,
  // Generic types from toolboxBuilder
  action: UniversalBlock,
  verification: UniversalBlock,
  navigation: UniversalBlock,
  // Specific command types use UniversalBlock
  press_key: UniversalBlock,
  press_sequence: UniversalBlock,
  tap: UniversalBlock,
  swipe: UniversalBlock,
  type_text: UniversalBlock,
  verify_image: UniversalBlock,
  verify_ocr: UniversalBlock,
  verify_audio: UniversalBlock,
  verify_element: UniversalBlock,
  condition: UniversalBlock,
  container: UniversalBlock,
  set_variable: UniversalBlock,
  sleep: UniversalBlock,
  get_current_time: UniversalBlock,
  generate_random: UniversalBlock,
  http_request: UniversalBlock,
  loop: UniversalBlock,
};

// Edge types for React Flow
const edgeTypes = {
  success: SuccessEdge,
  failure: FailureEdge,
  true: SuccessEdge,
  false: FailureEdge,
  complete: SuccessEdge,
  break: FailureEdge,
};

// Default edge options
const defaultEdgeOptions = {
  type: 'success',
  animated: false,
  markerEnd: {
    type: MarkerType.ArrowClosed,
    width: 20,
    height: 20,
  },
};

const TestCaseBuilderContent: React.FC = () => {
  // Inject styles to hide React Flow attribution
  React.useEffect(() => {
    const styleTag = document.createElement('style');
    styleTag.innerHTML = styles;
    document.head.appendChild(styleTag);
    return () => {
      document.head.removeChild(styleTag);
    };
  }, []);

  const { actualMode } = useTheme();
  
  // Get host manager for device control (REUSE from NavigationEditor)
  const {
    selectedHost,
    selectedDeviceId,
    isControlActive,
    isRemotePanelOpen,
    showRemotePanel,
    showAVPanel,
    availableHosts,
    handleDeviceSelect,
    handleControlStateChange,
    handleToggleRemotePanel,
    handleDisconnectComplete,
    isDeviceLocked, // For device locking functionality
  } = useHostManager();
  
  // Get device control hook for control state (REUSE from NavigationEditor lines 86-99)
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
  
  // Device control handler (REUSE pattern from NavigationEditor lines 115-125)
  const handleDeviceControl = useCallback(async () => {
    if (isControlActive) {
      console.log('[@TestCaseBuilder] Releasing device control');
      await handleReleaseControl();
      handleControlStateChange(false);
    } else {
      console.log('[@TestCaseBuilder] Taking device control');
      const success = await handleTakeControl();
      if (success) {
        handleControlStateChange(true);
      }
    }
  }, [isControlActive, handleTakeControl, handleReleaseControl, handleControlStateChange]);
  
  // Get DeviceDataContext and initialize it with control state (REUSE from NavigationEditor line 530-535)
  const { 
    setControlState, 
    getAvailableActions, // ← Use getter function like NavigationEditor does
    availableActionsLoading,
  } = useDeviceData();
  
  // Initialize device data context when control state changes (COPIED from NavigationEditor)
  useEffect(() => {
    console.log(`[@TestCaseBuilder] setControlState called - host: ${selectedHost?.host_name}, device: ${selectedDeviceId}, active: ${isControlActive}`);
    setControlState(selectedHost, selectedDeviceId, isControlActive);
  }, [selectedHost, selectedDeviceId, isControlActive, setControlState]);
  
  // Get latest actions on-demand (like NavigationEditor does)
  const availableActions = getAvailableActions();
  
  // Track when actions are loaded (not loading and has actions)
  const areActionsLoaded = isControlActive && !availableActionsLoading && Object.values(availableActions).flat().length > 0;
  
  // Debug log - simplified
  useEffect(() => {
    const actionCount = Object.values(availableActions).flat().length;
    const categories = Object.keys(availableActions);
    
    console.log(`[@TestCaseBuilder] Actions loaded - device: ${selectedDeviceId}, control: ${isControlActive}, loading: ${availableActionsLoading}, count: ${actionCount}, categories: [${categories.join(', ')}]`);
    
    if (actionCount > 0) {
      console.log(`[@TestCaseBuilder] ✅ Actions by category:`, Object.keys(availableActions).map(k => `${k}: ${availableActions[k].length}`));
    }
  }, [selectedDeviceId, isControlActive, availableActionsLoading, availableActions]);
  
  // Get navigation infrastructure (for compatibility, but we use pre-loaded data)
  const {
    setUserInterfaceFromProps,
  } = useNavigationEditor();
  
  const {
    nodes,
    edges,
    selectedBlock,
    setSelectedBlock,
    isConfigDialogOpen,
    setIsConfigDialogOpen,
    executionState,
    testcaseName,
    setTestcaseName,
    description,
    setDescription,
    userinterfaceName,
    setUserinterfaceName,
    currentTestcaseId,
    testcaseList,
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
  } = useTestCaseBuilder();

  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const [reactFlowInstance, setReactFlowInstance] = React.useState<any>(null);

  // Mode selection
  const [creationMode, setCreationMode] = useState<'visual' | 'ai'>('visual');
  const [aiPrompt, setAiPrompt] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);

  // Dialogs
  const [saveDialogOpen, setSaveDialogOpen] = useState(false);
  const [loadDialogOpen, setLoadDialogOpen] = useState(false);
  
  // AV Panel coordination (REUSE from NavigationEditor lines 316-325)
  const [isAVPanelCollapsed, setIsAVPanelCollapsed] = useState(true);
  const [isAVPanelMinimized, setIsAVPanelMinimized] = useState(false);
  const [captureMode, setCaptureMode] = useState<'stream' | 'screenshot' | 'video'>('stream');
  const isVerificationVisible = captureMode === 'screenshot' || captureMode === 'video';
  
  // Load compatible interfaces based on selected device
  const [compatibleInterfaceNames, setCompatibleInterfaceNames] = useState<string[]>([]);
  const { getAllUserInterfaces, getUserInterfaceByName } = useUserInterface();
  
  // Load compatible interfaces when device is selected AND control is taken
  useEffect(() => {
    const loadCompatibleInterfaces = async () => {
      if (!selectedDeviceId || !selectedHost || !isControlActive) {
        setCompatibleInterfaceNames([]);
        setUserinterfaceName(''); // Clear interface when device changes
        return;
      }
      
      try {
        console.log('[@TestCaseBuilder] Loading compatible interfaces for device...');
        
        const selectedDevice = selectedHost.devices?.find((d) => d.device_id === selectedDeviceId);
        const deviceModel = selectedDevice?.device_model;
        
        const interfaces = await getAllUserInterfaces();
        
        // Filter interfaces that:
        // 1. Have navigation trees (root_tree property exists)
        // 2. Are compatible with the selected device model
        const compatibleInterfaces = interfaces.filter((ui: any) => {
          const hasTree = !!ui.root_tree;
          const isCompatible = ui.models?.includes(deviceModel);
          return hasTree && isCompatible;
        });
        
        const names = compatibleInterfaces.map((ui: any) => ui.name);
        
        setCompatibleInterfaceNames(names);
        console.log(`[@TestCaseBuilder] Loaded ${names.length} compatible interfaces for ${deviceModel}`);
        
        // Auto-select first compatible interface if available
        if (names.length > 0 && !names.includes(userinterfaceName)) {
          setUserinterfaceName(names[0]);
        }
      } catch (error) {
        console.error('[@TestCaseBuilder] Failed to load compatible interfaces:', error);
      }
    };
    
    loadCompatibleInterfaces();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedDeviceId, selectedHost, isControlActive]); // Re-load when device or control state changes
  
  // Debug: Log userinterfaceName changes
  useEffect(() => {
    console.log('[@TestCaseBuilder] userinterfaceName changed to:', userinterfaceName);
  }, [userinterfaceName]);
  
  // AV Panel handlers (REUSE from NavigationEditor lines 409-423)
  const handleAVPanelCollapsedChange = useCallback((isCollapsed: boolean) => {
    setIsAVPanelCollapsed(isCollapsed);
  }, []);
  
  const handleCaptureModeChange = useCallback((mode: 'stream' | 'screenshot' | 'video') => {
    setCaptureMode(mode);
    console.log('[@TestCaseBuilder] Capture mode changed to:', mode);
  }, []);
  
  const handleAVPanelMinimizedChange = useCallback((isMinimized: boolean) => {
    setIsAVPanelMinimized(isMinimized);
    console.log('[@TestCaseBuilder] AV panel minimized changed to:', isMinimized);
  }, []);
  
  // Snackbar state
  const [snackbar, setSnackbar] = useState<{
    open: boolean;
    message: string;
    severity: 'success' | 'error' | 'info';
  }>({
    open: false,
    message: '',
    severity: 'info',
  });

  // Load navigation tree when interface changes - Load from NavigationConfig
  const { loadTreeByUserInterface } = useNavigationConfig();
  const [navNodes, setNavNodes] = useState<any[]>([]);
  
  useEffect(() => {
    const loadNavigationTree = async () => {
      // Only load tree if BOTH device and interface are selected
      if (!selectedDeviceId || !userinterfaceName) {
        console.log(`[@TestCaseBuilder] Skipping tree load - device: ${selectedDeviceId}, interface: ${userinterfaceName}`);
        setNavNodes([]); // Clear nodes if either is missing
        return;
      }
      
      try {
        console.log(`[@TestCaseBuilder] Loading tree for interface: ${userinterfaceName} (device: ${selectedDeviceId})`);
        
        const userInterface = await getUserInterfaceByName(userinterfaceName);
        console.log(`[@TestCaseBuilder] Got userInterface:`, userInterface);
        
        if (userInterface) {
          // Load tree data through NavigationConfig (uses cache automatically)
          const result = await loadTreeByUserInterface(userInterface.id);
          console.log(`[@TestCaseBuilder] Tree load result:`, result);
          setUserInterfaceFromProps(userInterface);
          
          // Extract nodes from result (API structure: result.tree.metadata.nodes)
          const nodes = result?.tree?.metadata?.nodes || result?.nodes || [];
          console.log(`[@TestCaseBuilder] 🔍 Raw nodes sample:`, nodes[0]); // DEBUG: See node structure
          setNavNodes(nodes);
          
          if (nodes.length > 0) {
            console.log(`[@TestCaseBuilder] ✅ Loaded tree for ${userinterfaceName} with ${nodes.length} nodes`);
          } else {
            console.warn(`[@TestCaseBuilder] ⚠️ Tree result has no nodes!`, result);
          }
        } else {
          console.warn(`[@TestCaseBuilder] ⚠️ No userInterface found for: ${userinterfaceName}`);
        }
      } catch (error) {
        console.error(`[@TestCaseBuilder] Failed to load tree:`, error);
        setNavNodes([]); // Clear nodes on error
      }
    };
    
    loadNavigationTree();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedDeviceId, userinterfaceName]); // Re-load when device OR interface changes

  // Build dynamic toolbox from navigation data - only if device and interface are selected
  const dynamicToolboxConfig = React.useMemo(() => {
    console.log(`[@TestCaseBuilder] Building toolbox - device: ${selectedDeviceId}, interface: ${userinterfaceName}, nodes: ${navNodes.length}, actions: ${Object.values(availableActions).flat().length}`);
    
    if (!selectedDeviceId || !userinterfaceName || navNodes.length === 0) {
      console.log(`[@TestCaseBuilder] ⚠️ Cannot build toolbox - missing requirements`);
      return null;
    }
    
    console.log(`[@TestCaseBuilder] ✅ Building toolbox with ${navNodes.length} nodes and ${Object.values(availableActions).flat().length} actions`);
    const config = buildToolboxFromNavigationData(navNodes, availableActions, null);
    console.log(`[@TestCaseBuilder] Toolbox config built:`, config);
    return config;
  }, [selectedDeviceId, userinterfaceName, navNodes, availableActions]);

  // Load test case list when load dialog opens
  useEffect(() => {
    if (loadDialogOpen) {
      fetchTestCaseList();
    }
  }, [loadDialogOpen, fetchTestCaseList]);

  // Handle drop from toolbox
  const onDrop = useCallback(
    (event: DragEvent) => {
      event.preventDefault();

      const dragDataStr = event.dataTransfer.getData('application/reactflow');
      
      if (!dragDataStr) {
        return;
      }

      try {
        const dragData = JSON.parse(dragDataStr);
        const { type, defaultData } = dragData;

        if (typeof type === 'undefined' || !type) {
          return;
        }

        const reactFlowBounds = reactFlowWrapper.current?.getBoundingClientRect();
        const position = reactFlowInstance.project({
          x: event.clientX - (reactFlowBounds?.left || 0),
          y: event.clientY - (reactFlowBounds?.top || 0),
        });

        addBlock(type, position, defaultData);
      } catch (error) {
        console.error('Invalid drag data format:', error);
      }
    },
    [reactFlowInstance, addBlock]
  );

  const onDragOver = useCallback((event: DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  // Handle block click
  const onNodeClick = useCallback(
    (_event: React.MouseEvent, node: any) => {
      // Don't open dialog for terminal blocks
      if (node.type === 'start' || node.type === 'success' || node.type === 'failure') {
        setSelectedBlock(node);
        return;
      }

      setSelectedBlock(node);
      setIsConfigDialogOpen(true);
    },
    [setSelectedBlock, setIsConfigDialogOpen]
  );

  // Handle config save
  const handleConfigSave = useCallback(
    (data: any) => {
      if (selectedBlock) {
        updateBlock(selectedBlock.id, data);
      }
      setIsConfigDialogOpen(false);
    },
    [selectedBlock, updateBlock, setIsConfigDialogOpen]
  );
  
  // Handle save
  const handleSave = useCallback(async () => {
    const result = await saveCurrentTestCase();
    if (result.success) {
      setSnackbar({
        open: true,
        message: `Test case "${testcaseName}" saved successfully!`,
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
  
  // Handle load
  const handleLoad = useCallback(async (testcaseId: string) => {
    await loadTestCase(testcaseId);
    setLoadDialogOpen(false);
    setSnackbar({
      open: true,
      message: 'Test case loaded successfully!',
      severity: 'success',
    });
  }, [loadTestCase]);
  
  // Handle delete
  const handleDelete = useCallback(async (testcaseId: string, testcaseName: string) => {
    if (window.confirm(`Are you sure you want to delete "${testcaseName}"?`)) {
      await deleteTestCaseById(testcaseId);
      setSnackbar({
        open: true,
        message: `Test case "${testcaseName}" deleted!`,
        severity: 'info',
      });
    }
  }, [deleteTestCaseById]);
  
  // Handle execute
  const handleExecute = useCallback(async () => {
    if (!currentTestcaseId) {
      setSnackbar({
        open: true,
        message: 'Please save the test case before executing',
        severity: 'error',
      });
      return;
    }
    
    await executeCurrentTestCase();
    
    // Show result after execution
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
  }, [currentTestcaseId, executeCurrentTestCase, executionState]);
  
  // Handle new test case
  const handleNew = useCallback(() => {
    if (window.confirm('Create new test case? Unsaved changes will be lost.')) {
      resetBuilder();
      setCreationMode('visual');
      setAiPrompt('');
      setSnackbar({
        open: true,
        message: 'Ready to create new test case',
        severity: 'info',
      });
    }
  }, [resetBuilder]);

  // Handle AI generation
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

    setIsGenerating(true);
    
    try {
      const result = await generateTestCaseFromPrompt(
        aiPrompt, 
        userinterfaceName,  // Use interface from store
        'device1'  // Default device
      );
      
      if (result.success && result.graph) {
        // Load the generated graph into the builder
        setNodes(result.graph.nodes.map(node => ({
          id: node.id,
          type: node.type as any,
          position: node.position,
          data: node.data
        })));
        
        setEdges(result.graph.edges.map(edge => ({
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
        
        // Pre-fill metadata
        if (result.testcase_name) {
          setTestcaseName(result.testcase_name);
        }
        if (result.description) {
          setDescription(result.description);
        }
        
        setSnackbar({
          open: true,
          message: 'Test case generated! Review and save when ready.',
          severity: 'success',
        });
        
        // Switch back to visual mode so user can see the graph
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
  }, [aiPrompt, userinterfaceName, setNodes, setEdges, setTestcaseName, setDescription, setCreationMode]);

  // MiniMap style
  const miniMapStyle = React.useMemo(
    () => ({
      backgroundColor: actualMode === 'dark' ? '#1f2937' : '#ffffff',
      border: `1px solid ${actualMode === 'dark' ? '#374151' : '#e5e7eb'}`,
    }),
    [actualMode]
  );

  return (
    <Box sx={{ 
      position: 'fixed',
      top: 64,
      left: 0,
      right: 0,
      bottom: 32,
      display: 'flex', 
      flexDirection: 'column', 
      overflow: 'hidden',
      zIndex: 1,
    }}>
      {/* Header - Fixed 46px with 4 Sections */}
      <Box
        sx={{
          px: 2,
          py: 0,
          borderBottom: 1,
          borderColor: 'divider',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: actualMode === 'dark' ? '#111827' : '#ffffff',
          height: '46px',
          flexShrink: 0,
        }}
      >
        {/* SECTION 1: Title */}
        <Box sx={{ display: 'flex', alignItems: 'center', minWidth: 0, flex: '0 0 190px' }}>
          <Typography variant="h6" fontWeight="bold" sx={{ whiteSpace: 'nowrap' }}>
            TestCase Builder
          </Typography>
        </Box>
        
        {/* SECTION 2: Visual/AI Mode Toggle */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, flex: '0 0 auto', ml: 2 }}>
          <Button
            size="small"
            variant={creationMode === 'visual' ? 'contained' : 'outlined'}
            onClick={() => setCreationMode('visual')}
            sx={{ fontSize: 11, py: 0.5, px: 1.5 }}
          >
            Visual
          </Button>
          <Button
            size="small"
            variant={creationMode === 'ai' ? 'contained' : 'outlined'}
            onClick={() => setCreationMode('ai')}
            startIcon={<AutoAwesomeIcon fontSize="small" />}
            sx={{ fontSize: 11, py: 0.5, px: 1.5 }}
          >
            AI
          </Button>
        </Box>
        
        {/* SECTION 2.5: Device Control (REUSE exact same component as NavigationEditor) */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flex: '0 0 auto', ml: 2, borderLeft: 1, borderColor: 'divider', pl: 2 }}>
          <NavigationEditorDeviceControls
            selectedHost={selectedHost}
            selectedDeviceId={selectedDeviceId || null}
            isControlActive={isControlActive}
            isControlLoading={isControlLoading}
            isRemotePanelOpen={isRemotePanelOpen}
            availableHosts={availableHosts}
            isDeviceLocked={(deviceKey: string) => {
              // Parse deviceKey format: "hostname:device_id"
              const [hostName, deviceId] = deviceKey.includes(':')
                ? deviceKey.split(':')
                : [deviceKey, 'device1'];
              
              const host = availableHosts.find((h) => h.host_name === hostName);
              return isDeviceLocked(host || null, deviceId);
            }}
            onDeviceSelect={handleDeviceSelect}
            onTakeControl={handleDeviceControl}
            onToggleRemotePanel={handleToggleRemotePanel}
          />
        </Box>
        
        {/* SECTION 3: Interface Selector */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, flex: '1 1 auto', ml: 2, justifyContent: 'center' }}>
          {/* Userinterface Selector - enabled when device + control */}
          <UserinterfaceSelector
            compatibleInterfaces={compatibleInterfaceNames}
            value={userinterfaceName}
            onChange={setUserinterfaceName}
            label="Interface"
            size="small"
            fullWidth={false}
            sx={{ minWidth: 200 }}
            disabled={!selectedDeviceId || !isControlActive}
          />
        </Box>
        
        {/* SECTION 4: TestCase Info + Action Buttons */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, minWidth: 0, flex: '0 0 auto', ml: 2 }}>
          {testcaseName && (
            <Typography variant="caption" color="text.secondary" sx={{ whiteSpace: 'nowrap' }}>
              {testcaseName} {currentTestcaseId ? '(saved)' : '(unsaved)'}
            </Typography>
          )}
          
          <Box sx={{ display: 'flex', gap: 0.75 }}>
            <Button 
              size="small" 
              variant="outlined" 
              startIcon={<AddIcon />} 
              onClick={handleNew}
              disabled={!userinterfaceName}
              title={!userinterfaceName ? 'Select a userinterface first' : 'Create new test case'}
            >
              New
            </Button>
            <Button 
              size="small" 
              variant="outlined" 
              startIcon={<FolderOpenIcon />} 
              onClick={() => setLoadDialogOpen(true)}
            >
              Load
            </Button>
            <Button 
              size="small" 
              variant="outlined" 
              startIcon={<SaveIcon />} 
              onClick={() => setSaveDialogOpen(true)}
              disabled={!userinterfaceName}
              title={!userinterfaceName ? 'Select a userinterface first' : 'Save test case'}
            >
              Save
            </Button>
            <Button
              size="small"
              variant="contained"
              startIcon={<PlayArrowIcon />}
              onClick={handleExecute}
              disabled={
                executionState.isExecuting || 
                !currentTestcaseId || 
                !selectedDeviceId || 
                !isControlActive || 
                !userinterfaceName
              }
              title={
                !userinterfaceName ? 'Select a userinterface first' :
                !selectedDeviceId ? 'Select a device first' :
                !isControlActive ? 'Take control of device first' :
                !currentTestcaseId ? 'Save test case first' :
                executionState.isExecuting ? 'Test is running' :
                'Run test case on device'
              }
            >
              {executionState.isExecuting ? 'Running...' : 'Run'}
            </Button>
          </Box>
        </Box>
      </Box>

      {/* Container - Fills remaining space after header and footer */}
      <Box sx={{ 
        flex: 1,
        display: 'flex', 
        overflow: 'hidden',
        minHeight: 0,
      }}>
        {/* Toolbox/AI Panel */}
        <Box sx={{ 
          width: 220, 
          height: '100%',
          borderRight: 1, 
          borderColor: 'divider',
          display: 'flex',
          flexDirection: 'column',
          background: actualMode === 'dark' ? '#111827' : '#f9fafb',
          overflow: 'hidden',
          flexShrink: 0,
        }}>
          {/* Visual Mode: Toolbox */}
          {creationMode === 'visual' && (
            dynamicToolboxConfig ? (
              <TestCaseToolbox 
                toolboxConfig={dynamicToolboxConfig}
              />
            ) : (
              <Box sx={{ p: 2, textAlign: 'center' }}>
                <Typography variant="caption" color="text.secondary">
                  {!selectedDeviceId 
                    ? '1. Select a device first' 
                    : !isControlActive
                    ? '2. Take control of device'
                    : !areActionsLoaded
                    ? '3. Loading device capabilities...'
                    : !userinterfaceName 
                    ? '4. Select an interface'
                    : 'Loading toolbox...'}
                </Typography>
              </Box>
            )
          )}

          {/* AI Mode: Prompt Input */}
          {creationMode === 'ai' && (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, p: 1.5, flex: 1, overflowY: 'auto' }}>
                <Typography variant="subtitle2" fontWeight="bold">
                  AI Test Generator
                </Typography>
                <TextField
                  multiline
                  rows={6}
                  placeholder="e.g., Go to live TV and verify audio is playing"
                  value={aiPrompt}
                  onChange={(e) => setAiPrompt(e.target.value)}
                  size="small"
                  fullWidth
                />
                <Button
                  variant="contained"
                  startIcon={<AutoAwesomeIcon />}
                  onClick={handleGenerateWithAI}
                  disabled={isGenerating || !aiPrompt.trim()}
                  fullWidth
                  size="small"
                >
                  {isGenerating ? 'Generating...' : 'Generate'}
                </Button>
                
                {/* Sample prompts */}
                <Box sx={{ mt: 1 }}>
                  <Typography variant="caption" fontWeight="bold" color="text.secondary">
                    Examples:
                  </Typography>
                  {[
                    'Go to live TV and check audio',
                    'Navigate to settings',
                    'Play first recording'
                  ].map((example, idx) => (
                    <Typography
                      key={idx}
                      variant="caption"
                      sx={{
                        display: 'block',
                        mt: 0.5,
                        cursor: 'pointer',
                        color: 'primary.main',
                        '&:hover': { textDecoration: 'underline' }
                      }}
                      onClick={() => setAiPrompt(example)}
                    >
                      • {example}
                    </Typography>
                  ))}
                </Box>
            </Box>
          )}
        </Box>

        {/* Canvas */}
        <Box 
          ref={reactFlowWrapper} 
          sx={{ 
            flex: 1, 
            height: '100%',
            minWidth: 0,
            overflow: 'hidden',
          }} 
          onDrop={onDrop} 
          onDragOver={onDragOver}
        >
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeClick={onNodeClick}
            onInit={setReactFlowInstance}
            nodeTypes={nodeTypes}
            edgeTypes={edgeTypes}
            defaultEdgeOptions={defaultEdgeOptions}
            fitView
          >
            <Background variant={BackgroundVariant.Dots} gap={15} size={1} />
            <Controls position="top-left" />
            <MiniMap 
              style={miniMapStyle} 
              position="top-right"
              nodeColor={(node) => {
                if (node.type === 'success') return '#10b981';
                if (node.type === 'failure') return '#ef4444';
                if (node.type === 'start') return '#3b82f6';
                if (node.type === 'action') return '#3b82f6';
                if (node.type === 'verification') return '#8b5cf6';
                if (node.type === 'navigation') return '#10b981';
                if (node.type === 'loop') return '#f59e0b';
                return '#6b7280';
              }} 
            />
          </ReactFlow>
        </Box>
      </Box>

      {/* Footer - Fixed 40px */}
      <Box
        sx={{
          height: '40px',
          borderTop: 1,
          borderColor: 'divider',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          px: 2,
          background: actualMode === 'dark' ? '#111827' : '#f9fafb',
          flexShrink: 0,
        }}
      >
        <Typography variant="caption" color="text.secondary">
          {nodes.length} blocks • {edges.length} connections
        </Typography>
        <Typography variant="caption" color="text.secondary">
          {executionState.isExecuting && 'Executing...'}
          {executionState.result && !executionState.isExecuting && (
            executionState.result.success 
              ? `✓ Last run: ${executionState.result.execution_time_ms}ms` 
              : '✗ Last run: Failed'
          )}
        </Typography>
      </Box>

      {/* Configuration Dialogs */}
      {selectedBlock?.type === 'press_key' && (
        <ActionConfigDialog
          open={isConfigDialogOpen}
          initialData={selectedBlock.data}
          onSave={handleConfigSave}
          onCancel={() => setIsConfigDialogOpen(false)}
        />
      )}

      {selectedBlock?.type === 'verify_image' && (
        <VerificationConfigDialog
          open={isConfigDialogOpen}
          initialData={selectedBlock.data}
          onSave={handleConfigSave}
          onCancel={() => setIsConfigDialogOpen(false)}
        />
      )}

      {selectedBlock?.type === 'navigation' && (
        <NavigationConfigDialog
          open={isConfigDialogOpen}
          initialData={selectedBlock.data}
          onSave={handleConfigSave}
          onCancel={() => setIsConfigDialogOpen(false)}
        />
      )}

      {selectedBlock?.type === 'loop' && (
        <LoopConfigDialog
          open={isConfigDialogOpen}
          initialData={selectedBlock.data}
          onSave={handleConfigSave}
          onCancel={() => setIsConfigDialogOpen(false)}
        />
      )}
      
      {/* Save Dialog */}
      <Dialog open={saveDialogOpen} onClose={() => setSaveDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Save Test Case</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Test Case Name"
            type="text"
            fullWidth
            required
            value={testcaseName}
            onChange={(e) => setTestcaseName(e.target.value)}
            placeholder="e.g., login_test"
          />
          <TextField
            margin="dense"
            label="Description"
            type="text"
            fullWidth
            multiline
            rows={3}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Describe what this test case does"
          />
          <TextField
            margin="dense"
            label="Navigation Tree (UI Name)"
            type="text"
            fullWidth
            value={userinterfaceName}
            onChange={(e) => setUserinterfaceName(e.target.value)}
            placeholder="e.g., horizon_android_mobile"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSaveDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleSave} variant="contained" disabled={!testcaseName}>
            Save
          </Button>
        </DialogActions>
      </Dialog>
      
      {/* Load Dialog */}
      <Dialog open={loadDialogOpen} onClose={() => setLoadDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Load Test Case</DialogTitle>
        <DialogContent>
          {testcaseList.length === 0 ? (
            <Alert severity="info">No test cases found. Create one first!</Alert>
          ) : (
            <List>
              {testcaseList.map((tc) => (
                <ListItem
                  key={tc.testcase_id}
                  secondaryAction={
                    <IconButton edge="end" onClick={() => handleDelete(tc.testcase_id, tc.testcase_name)}>
                      <DeleteIcon />
                    </IconButton>
                  }
                  disablePadding
                >
                  <ListItemButton onClick={() => handleLoad(tc.testcase_id)}>
                    <ListItemText
                      primary={tc.testcase_name}
                      secondary={
                        <>
                          {tc.description && <span>{tc.description}<br /></span>}
                          {tc.userinterface_name && <span>UI: {tc.userinterface_name}<br /></span>}
                          {tc.last_execution_success !== undefined && (
                            <span>
                              Last run: {tc.last_execution_success ? 
                                <CheckCircleIcon fontSize="small" style={{ color: '#10b981', verticalAlign: 'middle' }} /> : 
                                <ErrorIcon fontSize="small" style={{ color: '#ef4444', verticalAlign: 'middle' }} />
                              } ({tc.execution_count || 0} executions)
                            </span>
                          )}
                        </>
                      }
                    />
                  </ListItemButton>
                </ListItem>
              ))}
            </List>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setLoadDialogOpen(false)}>Cancel</Button>
        </DialogActions>
      </Dialog>
      
      {/* Snackbar for notifications */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert
          onClose={() => setSnackbar({ ...snackbar, open: false })}
          severity={snackbar.severity}
          sx={{ width: '100%' }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
      
      {/* Remote/Desktop Panel - REUSE from NavigationEditor lines 996-1121 */}
      {showRemotePanel && selectedHost && selectedDeviceId && isControlActive && (() => {
        const selectedDevice = selectedHost.devices?.find((d) => d.device_id === selectedDeviceId);
        const isDesktopDevice = selectedDevice?.device_model === 'host_vnc';
        const remoteCapability = selectedDevice?.device_capabilities?.remote;
        const hasMultipleRemotes = Array.isArray(remoteCapability) || selectedDevice?.device_model === 'fire_tv';
        
        if (isDesktopDevice) {
          // For desktop devices, render both DesktopPanel and WebPanel together
          return (
            <>
              <DesktopPanel
                host={selectedHost}
                deviceId={selectedDeviceId}
                deviceModel={selectedDevice?.device_model || 'host_vnc'}
                isConnected={isControlActive}
                onReleaseControl={handleDisconnectComplete}
                initialCollapsed={true}
              />
              <WebPanel
                host={selectedHost}
                deviceId={selectedDeviceId}
                deviceModel={selectedDevice?.device_model || 'host_vnc'}
                isConnected={isControlActive}
                onReleaseControl={handleDisconnectComplete}
                initialCollapsed={true}
              />
            </>
          );
        } else if (hasMultipleRemotes && selectedDevice?.device_model === 'fire_tv') {
          // For Fire TV devices, render both AndroidTvRemote and InfraredRemote side by side
          return (
            <Box
              sx={{
                display: 'flex',
                flexDirection: 'row',
                gap: 2,
                position: 'absolute',
                right: 10,
                bottom: 20,
                zIndex: 1000,
                height: 'auto',
              }}
            >
              <RemotePanel
                host={selectedHost}
                deviceId={selectedDeviceId}
                deviceModel={selectedDevice?.device_model || 'fire_tv'}
                remoteType="android_tv"
                isConnected={isControlActive}
                onReleaseControl={handleDisconnectComplete}
                deviceResolution={DEFAULT_DEVICE_RESOLUTION}
                streamCollapsed={isAVPanelCollapsed}
                streamMinimized={isAVPanelMinimized}
                streamHidden={showAVPanel}
                captureMode={captureMode}
                initialCollapsed={true}
              />
              <RemotePanel
                host={selectedHost}
                deviceId={selectedDeviceId}
                deviceModel={selectedDevice?.device_model || 'fire_tv'}
                remoteType="ir_remote"
                isConnected={isControlActive}
                onReleaseControl={handleDisconnectComplete}
                deviceResolution={DEFAULT_DEVICE_RESOLUTION}
                streamCollapsed={isAVPanelCollapsed}
                streamMinimized={isAVPanelMinimized}
                streamHidden={showAVPanel}
                captureMode={captureMode}
                initialCollapsed={true}
              />
            </Box>
          );
        } else if (hasMultipleRemotes) {
          // For other devices with multiple remote controllers - render side by side
          const remoteTypes = Array.isArray(remoteCapability) ? remoteCapability : [remoteCapability];
          return (
            <Box
              sx={{
                display: 'flex',
                flexDirection: 'row',
                gap: 2,
                position: 'absolute',
                right: 10,
                bottom: 20,
                zIndex: 1000,
                height: 'auto',
              }}
            >
              {remoteTypes.filter(Boolean).map((remoteType: string, index: number) => (
                <RemotePanel
                  key={`${selectedDeviceId}-${remoteType}`}
                  host={selectedHost}
                  deviceId={selectedDeviceId}
                  deviceModel={selectedDevice?.device_model || 'unknown'}
                  remoteType={remoteType}
                  isConnected={isControlActive}
                  onReleaseControl={handleDisconnectComplete}
                  deviceResolution={DEFAULT_DEVICE_RESOLUTION}
                  streamCollapsed={isAVPanelCollapsed}
                  streamMinimized={isAVPanelMinimized}
                  captureMode={captureMode}
                  initialCollapsed={index > 0}
                />
              ))}
            </Box>
          );
        } else {
          // For single remote devices, render only one RemotePanel
          return (
            <RemotePanel
              host={selectedHost}
              deviceId={selectedDeviceId}
              deviceModel={selectedDevice?.device_model || 'unknown'}
              isConnected={isControlActive}
              onReleaseControl={handleDisconnectComplete}
              deviceResolution={DEFAULT_DEVICE_RESOLUTION}
              streamCollapsed={isAVPanelCollapsed}
              streamMinimized={isAVPanelMinimized}
              captureMode={captureMode}
              isVerificationVisible={isVerificationVisible}
              isNavigationEditorContext={false}
            />
          );
        }
      })()}

      {/* AV Panel - REUSE from NavigationEditor lines 1124-1156 */}
      {showAVPanel && selectedHost && selectedDeviceId && (() => {
        const selectedDevice = selectedHost.devices?.find((d) => d.device_id === selectedDeviceId);
        const deviceModel = selectedDevice?.device_model;
        
        return (
          <Box
            sx={{
              position: 'absolute',
              left: 240,
              bottom: 20,
              zIndex: 999,
            }}
          >
            {deviceModel === 'host_vnc' ? (
              <VNCStream
                host={selectedHost}
                deviceId={selectedDeviceId}
                deviceModel={deviceModel}
                isControlActive={isControlActive}
                userinterfaceName={userinterfaceName}
                onCollapsedChange={handleAVPanelCollapsedChange}
                onMinimizedChange={handleAVPanelMinimizedChange}
                onCaptureModeChange={handleCaptureModeChange}
              />
            ) : (
              <HDMIStream
                host={selectedHost}
                deviceId={selectedDeviceId}
                deviceModel={deviceModel}
                isControlActive={isControlActive}
                userinterfaceName={userinterfaceName}
                onCollapsedChange={handleAVPanelCollapsedChange}
                onMinimizedChange={handleAVPanelMinimizedChange}
                onCaptureModeChange={handleCaptureModeChange}
                deviceResolution={DEFAULT_DEVICE_RESOLUTION}
              />
            )}
          </Box>
        );
      })()}
    </Box>
  );
};

const TestCaseBuilder: React.FC = () => {
  return (
    <ReactFlowProvider>
      <NavigationConfigProvider>
        <NavigationEditorProvider>
          <TestCaseBuilderProvider>
            <TestCaseBuilderContent />
          </TestCaseBuilderProvider>
        </NavigationEditorProvider>
      </NavigationConfigProvider>
    </ReactFlowProvider>
  );
};

export default TestCaseBuilder;

