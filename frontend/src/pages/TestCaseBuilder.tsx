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
import { toolboxConfig } from '../components/testcase/builder/toolboxConfig';
import { StartBlock } from '../components/testcase/blocks/StartBlock';
import { SuccessBlock } from '../components/testcase/blocks/SuccessBlock';
import { FailureBlock } from '../components/testcase/blocks/FailureBlock';
import { UniversalBlock } from '../components/testcase/blocks/UniversalBlock';
import { SuccessEdge } from '../components/testcase/edges/SuccessEdge';
import { FailureEdge } from '../components/testcase/edges/FailureEdge';
import { UserinterfaceSelector } from '../components/common/UserinterfaceSelector';

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
import { useTheme } from '../contexts/ThemeContext';
import { generateTestCaseFromPrompt } from '../services/aiService';
import { buildToolboxFromNavigationData } from '../utils/toolboxBuilder';
import { buildServerUrl } from '../utils/buildUrlUtils';

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
  
  // Get available actions from DeviceDataContext (same as Navigation Editor)
  const { getAvailableActions } = useDeviceData();
  const availableActions = getAvailableActions();
  
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
  const [activeToolboxTab, setActiveToolboxTab] = useState('standard');

  // Dialogs
  const [saveDialogOpen, setSaveDialogOpen] = useState(false);
  const [loadDialogOpen, setLoadDialogOpen] = useState(false);
  
  // Load all interfaces WITH tree data for selector (load once, instant switching)
  const [allInterfaceNames, setAllInterfaceNames] = useState<string[]>([]);
  const [allInterfacesTreeData, setAllInterfacesTreeData] = useState<Map<string, any>>(new Map());
  const [isLoadingAllData, setIsLoadingAllData] = useState(true);
  
  // Frontend cache with 5 min TTL
  const FRONTEND_CACHE_KEY = 'testcasebuilder_all_interfaces_trees';
  const FRONTEND_CACHE_TTL = 5 * 60 * 1000; // 5 minutes in ms
  
  useEffect(() => {
    console.log('[@TestCaseBuilder] Loading ALL interfaces with tree data...');
    const loadAllInterfacesWithTrees = async () => {
      try {
        setIsLoadingAllData(true);
        
        // Check frontend cache first (localStorage)
        const cachedData = localStorage.getItem(FRONTEND_CACHE_KEY);
        if (cachedData) {
          try {
            const parsed = JSON.parse(cachedData);
            const age = Date.now() - parsed.timestamp;
            if (age < FRONTEND_CACHE_TTL) {
              console.log(`[@TestCaseBuilder] ⚡ CACHE HIT: Using cached data (age: ${(age/1000).toFixed(0)}s / ${FRONTEND_CACHE_TTL/1000}s TTL)`);
              
              const interfaceNames: string[] = [];
              const treeDataMap = new Map();
              
              parsed.data.interfaces.forEach((item: any) => {
                const interfaceName = item.interface.name;
                interfaceNames.push(interfaceName);
                treeDataMap.set(interfaceName, {
                  interface: item.interface,
                  tree: item.tree_data.tree,
                  nodes: item.tree_data.nodes,
                  edges: item.tree_data.edges
                });
              });
              
              setAllInterfaceNames(interfaceNames);
              setAllInterfacesTreeData(treeDataMap);
              setIsLoadingAllData(false);
              
              console.log(`[@TestCaseBuilder] ✅ Loaded ${interfaceNames.length} interfaces from CACHE`);
              return;
            } else {
              console.log(`[@TestCaseBuilder] ❌ CACHE EXPIRED: (age: ${(age/1000).toFixed(0)}s > ${FRONTEND_CACHE_TTL/1000}s TTL)`);
              localStorage.removeItem(FRONTEND_CACHE_KEY);
            }
          } catch (e) {
            console.error('[@TestCaseBuilder] Error parsing cache:', e);
            localStorage.removeItem(FRONTEND_CACHE_KEY);
          }
        }
        
        // Call new optimized endpoint that loads everything at once
        console.log('[@TestCaseBuilder] CACHE MISS - Fetching from server...');
        const response = await fetch(buildServerUrl('/server/userinterface/getAllInterfacesWithTrees'));
        const result = await response.json();
        
        if (result.success) {
          const interfaceNames: string[] = [];
          const treeDataMap = new Map();
          
          result.interfaces.forEach((item: any) => {
            const interfaceName = item.interface.name;
            interfaceNames.push(interfaceName);
            treeDataMap.set(interfaceName, {
              interface: item.interface,
              tree: item.tree_data.tree,
              nodes: item.tree_data.nodes,
              edges: item.tree_data.edges
            });
          });
          
          setAllInterfaceNames(interfaceNames);
          setAllInterfacesTreeData(treeDataMap);
          
          // Store in frontend cache (localStorage)
          try {
            localStorage.setItem(FRONTEND_CACHE_KEY, JSON.stringify({
              data: result,
              timestamp: Date.now()
            }));
            console.log(`[@TestCaseBuilder] 💾 CACHED: Stored data in localStorage (TTL: 5min)`);
          } catch (e) {
            console.warn('[@TestCaseBuilder] Failed to cache data in localStorage:', e);
          }
          
          console.log(`[@TestCaseBuilder] ✅ Loaded ${interfaceNames.length} interfaces with ${result.total_nodes} nodes in ONE call`);
          console.log(`[@TestCaseBuilder] Interfaces:`, interfaceNames);
        } else {
          console.error('[@TestCaseBuilder] Failed to load interfaces:', result.error);
        }
      } catch (error) {
        console.error('[@TestCaseBuilder] Error loading interfaces:', error);
      } finally {
        setIsLoadingAllData(false);
      }
    };
    
    loadAllInterfacesWithTrees();
  }, []); // Load once on mount
  
  // Debug: Log userinterfaceName changes
  useEffect(() => {
    console.log('[@TestCaseBuilder] userinterfaceName changed to:', userinterfaceName);
  }, [userinterfaceName]);
  
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

  // Load navigation tree when interface changes - NOW INSTANT (uses pre-loaded data)
  useEffect(() => {
    const loadNavigationTree = async () => {
      if (!userinterfaceName) return;
      
      try {
        console.log(`[@TestCaseBuilder] Switching to interface: ${userinterfaceName}`);
        
        // Get pre-loaded data from memory (INSTANT!)
        const treeData = allInterfacesTreeData.get(userinterfaceName);
        
        if (treeData) {
          // Data already loaded - just use it!
          console.log(`[@TestCaseBuilder] ⚡ INSTANT: Using pre-loaded data for ${userinterfaceName}`);
          
          // Set interface for NavigationEditor infrastructure compatibility
          setUserInterfaceFromProps(treeData.interface);
          
          // Tree data is already available - no loading needed!
          console.log(`[@TestCaseBuilder] ✅ Interface switched instantly (${treeData.nodes.length} nodes, ${treeData.edges.length} edges)`);
        } else {
          console.warn(`[@TestCaseBuilder] ⚠️ Tree data not found for ${userinterfaceName} - shouldn't happen`);
        }
      } catch (error) {
        console.error(`[@TestCaseBuilder] Failed to switch interface:`, error);
      }
    };
    
    loadNavigationTree();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userinterfaceName]); // Only re-run when interface NAME changes

  // Build dynamic toolbox from pre-loaded navigation data (INSTANT!)
  const dynamicToolboxConfig = React.useMemo(() => {
    if (!userinterfaceName) return null;
    
    const treeData = allInterfacesTreeData.get(userinterfaceName);
    if (!treeData) return null;
    
    // Convert backend format to frontend format for toolbox builder
    const frontendNodes = treeData.nodes.map((node: any) => ({
      id: node.node_id,
      type: node.node_type || 'screen',
      position: { x: node.position_x, y: node.position_y },
      data: {
        label: node.label,
        type: node.node_type || 'screen',
        verifications: node.verifications,
        ...node.data
      }
    }));
    
    console.log(`[@TestCaseBuilder] Building toolbox - nodes: ${frontendNodes.length}, actions from controllers: ${Object.values(availableActions).flat().length}, interface: ${userinterfaceName}`);
    return buildToolboxFromNavigationData(frontendNodes, availableActions, treeData.interface);
  }, [userinterfaceName, allInterfacesTreeData, availableActions]);

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
        <Box sx={{ display: 'flex', alignItems: 'center', minWidth: 0, flex: '0 0 240px' }}>
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
        
        {/* SECTION 3: Interface Selector + Toolbox Tabs */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, flex: '1 1 auto', ml: 2, justifyContent: 'center' }}>
          {/* Userinterface Selector */}
          <UserinterfaceSelector
            compatibleInterfaces={allInterfaceNames}
            value={userinterfaceName}
            onChange={setUserinterfaceName}
            label="Interface"
            size="small"
            fullWidth={false}
            sx={{ minWidth: 200 }}
          />
          
          {/* Toolbox Tab Navigation (only in visual mode) */}
          {creationMode === 'visual' && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              {Object.keys(dynamicToolboxConfig || toolboxConfig).map((key) => {
                const config = dynamicToolboxConfig || toolboxConfig;
                const tabName = (config as any)[key]?.tabName || key;
                
                // Define tab colors
                const tabColors: Record<string, string> = {
                  'standard': '#3b82f6',    // blue
                  'navigation': '#8b5cf6',  // purple
                  'actions': '#ef4444',     // red
                  'verifications': '#10b981' // green
                };
                
                const tabColor = tabColors[key] || '#6b7280';
                const isActive = activeToolboxTab === key;
                
                return (
                  <Button
                    key={key}
                    size="small"
                    variant={isActive ? 'contained' : 'outlined'}
                    onClick={() => setActiveToolboxTab(key)}
                    sx={{ 
                      fontSize: 10, 
                      py: 0.5, 
                      px: 1.5,
                      minWidth: 'auto',
                      // Active: colored background
                      ...(isActive && {
                        backgroundColor: tabColor,
                        borderColor: tabColor,
                        color: '#ffffff',
                        '&:hover': {
                          backgroundColor: tabColor,
                          opacity: 0.9
                        }
                      }),
                      // Inactive: colored border and text
                      ...(!isActive && {
                        borderColor: tabColor,
                        color: tabColor,
                        '&:hover': {
                          borderColor: tabColor,
                          backgroundColor: `${tabColor}15` // 15% opacity
                        }
                      })
                    }}
                  >
                    {tabName.toUpperCase()}
                  </Button>
                );
              })}
            </Box>
          )}
        </Box>
        
        {/* SECTION 4: TestCase Info + Action Buttons */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, minWidth: 0, flex: '0 0 auto', ml: 2 }}>
          {testcaseName && (
            <Typography variant="caption" color="text.secondary" sx={{ whiteSpace: 'nowrap' }}>
              {testcaseName} {currentTestcaseId ? '(saved)' : '(unsaved)'}
            </Typography>
          )}
          
          <Box sx={{ display: 'flex', gap: 0.75 }}>
            <Button size="small" variant="outlined" startIcon={<AddIcon />} onClick={handleNew}>
              New
            </Button>
            <Button size="small" variant="outlined" startIcon={<FolderOpenIcon />} onClick={() => setLoadDialogOpen(true)}>
              Load
            </Button>
            <Button size="small" variant="outlined" startIcon={<SaveIcon />} onClick={() => setSaveDialogOpen(true)}>
              Save
            </Button>
            <Button
              size="small"
              variant="contained"
              startIcon={<PlayArrowIcon />}
              onClick={handleExecute}
              disabled={executionState.isExecuting || !currentTestcaseId}
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
            isLoadingAllData ? (
              <Box sx={{ p: 2, textAlign: 'center' }}>
                <Typography variant="caption" color="text.secondary">
                  Loading all navigation data...
                </Typography>
              </Box>
            ) : dynamicToolboxConfig ? (
              <TestCaseToolbox 
                activeTab={activeToolboxTab}
                toolboxConfig={dynamicToolboxConfig}
              />
            ) : (
              <Box sx={{ p: 2, textAlign: 'center' }}>
                <Typography variant="caption" color="text.secondary">
                  Select an interface to load toolbox
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
            <Controls />
            <MiniMap style={miniMapStyle} nodeColor={(node) => {
              if (node.type === 'success') return '#10b981';
              if (node.type === 'failure') return '#ef4444';
              if (node.type === 'start') return '#3b82f6';
              if (node.type === 'action') return '#3b82f6';
              if (node.type === 'verification') return '#8b5cf6';
              if (node.type === 'navigation') return '#10b981';
              if (node.type === 'loop') return '#f59e0b';
              return '#6b7280';
            }} />
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

