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

// Dialogs
import { ActionConfigDialog } from '../components/testcase/dialogs/ActionConfigDialog';
import { VerificationConfigDialog } from '../components/testcase/dialogs/VerificationConfigDialog';
import { NavigationConfigDialog } from '../components/testcase/dialogs/NavigationConfigDialog';
import { LoopConfigDialog } from '../components/testcase/dialogs/LoopConfigDialog';

// Context
import { TestCaseBuilderProvider, useTestCaseBuilder } from '../contexts/testcase/TestCaseBuilderContext';
import { useTheme } from '../contexts/ThemeContext';
import { generateTestCaseFromPrompt } from '../services/aiService';

// Node types for React Flow
const nodeTypes = {
  start: StartBlock,
  success: SuccessBlock,
  failure: FailureBlock,
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
  navigation: UniversalBlock,
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
      {/* Header - Fixed 46px */}
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
          position: 'relative',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Typography variant="h6" fontWeight="bold">
            TestCase Builder
          </Typography>
          
          {/* Visual/AI Mode Toggle */}
          <Box sx={{ display: 'flex', gap: 0.5, ml: 2 }}>
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
        </Box>
        
        {/* Toolbox Tab Navigation - centered - only show in visual mode */}
        {creationMode === 'visual' && (
          <Box sx={{ 
            position: 'absolute',
            left: '50%',
            transform: 'translateX(-50%)',
            display: 'flex', 
            gap: 0.5
          }}>
            {Object.keys(toolboxConfig).map((key) => (
              <Button
                key={key}
                size="small"
                variant={activeToolboxTab === key ? 'contained' : 'outlined'}
                onClick={() => setActiveToolboxTab(key)}
                sx={{ 
                  fontSize: 10, 
                  py: 0.5, 
                  px: 1.5,
                  minWidth: 'auto'
                }}
              >
                {toolboxConfig[key].tabName.toUpperCase()}
              </Button>
            ))}
          </Box>
        )}
        
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          {testcaseName && (
            <Typography variant="caption" color="text.secondary">
              {testcaseName} {currentTestcaseId ? '(saved)' : '(unsaved)'}
            </Typography>
          )}
        </Box>
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
          {creationMode === 'visual' && <TestCaseToolbox activeTab={activeToolboxTab} />}

          {/* AI Mode: Prompt Input */}
          {creationMode === 'ai' && (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, p: 1.5, flex: 1, overflowY: 'auto' }}>
                <Typography variant="subtitle2" fontWeight="bold">
                  AI Test Generator
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Describe your test in plain English
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

                {/* Instructions */}
                <Box sx={{ 
                  mt: 'auto', 
                  p: 1, 
                  background: actualMode === 'dark' ? '#1f2937' : '#ffffff', 
                  borderRadius: 1 
                }}>
                  <Typography fontSize={10} color="text.secondary">
                    <strong>Note:</strong> After AI generates the test, you can edit it visually.
                </Typography>
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
      <TestCaseBuilderProvider>
        <TestCaseBuilderContent />
      </TestCaseBuilderProvider>
    </ReactFlowProvider>
  );
};

export default TestCaseBuilder;

