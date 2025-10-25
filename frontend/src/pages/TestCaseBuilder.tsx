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
import DeleteIcon from '@mui/icons-material/Delete';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';

// Components
import { TestCaseBuilderHeader } from '../components/testcase/builder/TestCaseBuilderHeader';
import { TestCaseBuilderSidebar } from '../components/testcase/builder/TestCaseBuilderSidebar';
import { TestCaseBuilderCanvas } from '../components/testcase/builder/TestCaseBuilderCanvas';
import { TestCaseBuilderPanels } from '../components/testcase/builder/TestCaseBuilderPanels';
import { StartBlock } from '../components/testcase/blocks/StartBlock';
import { SuccessBlock } from '../components/testcase/blocks/SuccessBlock';
import { FailureBlock } from '../components/testcase/blocks/FailureBlock';
import { UniversalBlock } from '../components/testcase/blocks/UniversalBlock';
import { SuccessEdge } from '../components/testcase/edges/SuccessEdge';
import { FailureEdge } from '../components/testcase/edges/FailureEdge';
import { ExecutionOverlay } from '../components/testcase/ExecutionOverlay';

// Dialogs
import { ActionConfigDialog } from '../components/testcase/dialogs/ActionConfigDialog';
import { VerificationConfigDialog } from '../components/testcase/dialogs/VerificationConfigDialog';
import { NavigationConfigDialog } from '../components/testcase/dialogs/NavigationConfigDialog';
import { LoopConfigDialog } from '../components/testcase/dialogs/LoopConfigDialog';

// Context
import { TestCaseBuilderProvider } from '../contexts/testcase/TestCaseBuilderContext';
import { NavigationEditorProvider } from '../contexts/navigation/NavigationEditorProvider';
import { NavigationConfigProvider } from '../contexts/navigation/NavigationConfigContext';
import { useTheme } from '../contexts/ThemeContext';

// Hook
import { useTestCaseBuilderPage } from '../hooks/pages/useTestCaseBuilderPage';

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
  style: {
    stroke: '#94a3b8', // grey
    strokeWidth: 2,
  },
  markerEnd: {
    type: MarkerType.ArrowClosed,
    width: 20,
    height: 20,
    color: '#94a3b8', // grey to match edge
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
  
  // Execution overlay state
  const [isExecuting, setIsExecuting] = useState(false);
  const [executionDetails, setExecutionDetails] = useState<{ command?: string; params?: Record<string, any> }>({});

  // Listen for execution events
  useEffect(() => {
    const handleExecutionStart = (event: CustomEvent) => {
      setIsExecuting(true);
      setExecutionDetails(event.detail);
    };

    const handleExecutionEnd = () => {
      setIsExecuting(false);
      setExecutionDetails({});
    };

    window.addEventListener('blockExecutionStart' as any, handleExecutionStart);
    window.addEventListener('blockExecutionEnd' as any, handleExecutionEnd);

    return () => {
      window.removeEventListener('blockExecutionStart' as any, handleExecutionStart);
      window.removeEventListener('blockExecutionEnd' as any, handleExecutionEnd);
    };
  }, []);
  
  // Use the consolidated hook for all business logic
  const hookData = useTestCaseBuilderPage();

  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const [reactFlowInstance, setReactFlowInstance] = React.useState<any>(null);

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

        hookData.addBlock(type, position, defaultData);
      } catch (error) {
        console.error('Invalid drag data format:', error);
      }
    },
    [reactFlowInstance, hookData.addBlock]
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
        hookData.setSelectedBlock(node);
        return;
      }

      hookData.setSelectedBlock(node);
      hookData.setIsConfigDialogOpen(true);
    },
    [hookData.setSelectedBlock, hookData.setIsConfigDialogOpen]
  );

  // Handle config save
  const handleConfigSave = useCallback(
    (data: any) => {
      if (hookData.selectedBlock) {
        hookData.updateBlock(hookData.selectedBlock.id, data);
      }
      hookData.setIsConfigDialogOpen(false);
    },
    [hookData.selectedBlock, hookData.updateBlock, hookData.setIsConfigDialogOpen]
  );
  
  // Sidebar state
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  // Fit view when ReactFlow instance is ready
  React.useEffect(() => {
    if (reactFlowInstance) {
      // Small delay to ensure canvas is fully rendered
      setTimeout(() => {
        reactFlowInstance.fitView({ padding: 0.2, duration: 200 });
      }, 100);
    }
  }, [reactFlowInstance]);

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
      {/* Header */}
      <TestCaseBuilderHeader
        actualMode={actualMode}
        creationMode={hookData.creationMode}
        setCreationMode={hookData.setCreationMode}
        selectedHost={hookData.selectedHost}
        selectedDeviceId={hookData.selectedDeviceId}
        isControlActive={hookData.isControlActive}
        isControlLoading={hookData.isControlLoading}
        isRemotePanelOpen={hookData.isRemotePanelOpen}
        availableHosts={hookData.availableHosts}
        isDeviceLocked={hookData.isDeviceLocked}
        handleDeviceSelect={hookData.handleDeviceSelect}
        handleDeviceControl={hookData.handleDeviceControl}
        handleToggleRemotePanel={hookData.handleToggleRemotePanel}
        compatibleInterfaceNames={hookData.compatibleInterfaceNames}
        userinterfaceName={hookData.userinterfaceName}
        setUserinterfaceName={hookData.setUserinterfaceName}
        testcaseName={hookData.testcaseName}
        hasUnsavedChanges={hookData.hasUnsavedChanges}
        currentTestcaseId={hookData.currentTestcaseId}
        handleNew={hookData.handleNew}
        setLoadDialogOpen={hookData.setLoadDialogOpen}
        setSaveDialogOpen={hookData.setSaveDialogOpen}
        handleExecute={hookData.handleExecute}
        isExecuting={hookData.executionState.isExecuting}
      />

      {/* Main Container */}
      <Box sx={{ 
        flex: 1,
        display: 'flex', 
        overflow: 'hidden',
        minHeight: 0,
        position: 'relative',
      }}>
        {/* Sidebar */}
        <TestCaseBuilderSidebar
          actualMode={actualMode}
          creationMode={hookData.creationMode}
          isSidebarOpen={isSidebarOpen}
          toggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
          toolboxConfig={hookData.dynamicToolboxConfig}
          selectedDeviceId={hookData.selectedDeviceId}
          isControlActive={hookData.isControlActive}
          areActionsLoaded={hookData.areActionsLoaded}
          userinterfaceName={hookData.userinterfaceName}
        />

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
            nodes={hookData.nodes}
            edges={hookData.edges}
            onNodesChange={hookData.onNodesChange}
            onEdgesChange={hookData.onEdgesChange}
            onConnect={hookData.onConnect}
            onNodeClick={onNodeClick}
            onInit={setReactFlowInstance}
            nodeTypes={nodeTypes}
            edgeTypes={edgeTypes}
            defaultEdgeOptions={defaultEdgeOptions}
            nodesDraggable={true}
            nodesConnectable={true}
            elementsSelectable={true}
            panOnDrag={true}
            zoomOnScroll={true}
            zoomOnPinch={true}
            fitView
          >
            <TestCaseBuilderCanvas
              actualMode={actualMode}
              isSidebarOpen={isSidebarOpen}
              isExecuting={isExecuting}
              executionDetails={executionDetails}
            />
          </ReactFlow>
        </Box>
      </Box>

      {/* Footer */}
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
          {hookData.nodes.length} blocks • {hookData.edges.length} connections
        </Typography>
        <Typography variant="caption" color="text.secondary">
          {hookData.executionState.isExecuting && 'Executing...'}
          {hookData.executionState.result && !hookData.executionState.isExecuting && (
            hookData.executionState.result.success 
              ? `✓ Last run: ${hookData.executionState.result.execution_time_ms}ms` 
              : '✗ Last run: Failed'
          )}
        </Typography>
      </Box>

      {/* Configuration Dialogs */}
      {hookData.selectedBlock?.type === 'press_key' && (
        <ActionConfigDialog
          open={hookData.isConfigDialogOpen}
          initialData={hookData.selectedBlock.data}
          onSave={handleConfigSave}
          onCancel={() => hookData.setIsConfigDialogOpen(false)}
        />
      )}

      {hookData.selectedBlock?.type === 'verify_image' && (
        <VerificationConfigDialog
          open={hookData.isConfigDialogOpen}
          initialData={hookData.selectedBlock.data}
          onSave={handleConfigSave}
          onCancel={() => hookData.setIsConfigDialogOpen(false)}
        />
      )}

      {hookData.selectedBlock?.type === 'navigation' && (
        <NavigationConfigDialog
          open={hookData.isConfigDialogOpen}
          initialData={hookData.selectedBlock.data}
          onSave={handleConfigSave}
          onCancel={() => hookData.setIsConfigDialogOpen(false)}
        />
      )}

      {hookData.selectedBlock?.type === 'loop' && (
        <LoopConfigDialog
          open={hookData.isConfigDialogOpen}
          initialData={hookData.selectedBlock.data}
          onSave={handleConfigSave}
          onCancel={() => hookData.setIsConfigDialogOpen(false)}
        />
      )}
      
      {/* Save Dialog */}
      <Dialog 
        open={hookData.saveDialogOpen} 
        onClose={() => hookData.setSaveDialogOpen(false)} 
        maxWidth="sm" 
        fullWidth
        PaperProps={{
          sx: {
            border: 2,
            borderColor: 'divider',
          }
        }}
      >
        <DialogTitle sx={{ borderBottom: 1, borderColor: 'divider', pb: 2 }}>
          Save Test Case
        </DialogTitle>
        <DialogContent sx={{ pt: 3 }}>
          <TextField
            autoFocus
            margin="dense"
            label="Test Case Name"
            type="text"
            fullWidth
            required
            value={hookData.testcaseName}
            onChange={(e) => hookData.setTestcaseName(e.target.value)}
            placeholder="e.g., login_test"
          />
          <TextField
            margin="dense"
            label="Description"
            type="text"
            fullWidth
            multiline
            rows={3}
            value={hookData.description}
            onChange={(e) => hookData.setDescription(e.target.value)}
            placeholder="Describe what this test case does"
          />
          <TextField
            margin="dense"
            label="User Interface"
            type="text"
            fullWidth
            value={hookData.userinterfaceName}
            onChange={(e) => hookData.setUserinterfaceName(e.target.value)}
            placeholder="e.g., horizon_android_mobile"
          />
        </DialogContent>
        <DialogActions sx={{ borderTop: 1, borderColor: 'divider', pt: 2, pb: 2, px: 3 }}>
          <Button onClick={() => hookData.setSaveDialogOpen(false)} variant="outlined">
            Cancel
          </Button>
          <Button onClick={hookData.handleSave} variant="contained" disabled={!hookData.testcaseName}>
            Save
          </Button>
        </DialogActions>
      </Dialog>
      
      {/* Load Dialog */}
      <Dialog 
        open={hookData.loadDialogOpen} 
        onClose={() => hookData.setLoadDialogOpen(false)} 
        maxWidth="md" 
        fullWidth
        PaperProps={{
          sx: {
            border: 2,
            borderColor: 'divider',
          }
        }}
      >
        <DialogTitle sx={{ borderBottom: 1, borderColor: 'divider', pb: 2 }}>
          Load Test Case
        </DialogTitle>
        <DialogContent sx={{ pt: 3 }}>
          {hookData.testcaseList.length === 0 ? (
            <Alert severity="info">No test cases found. Create one first!</Alert>
          ) : (
            <List>
              {hookData.testcaseList.map((tc) => (
                <ListItem
                  key={tc.testcase_id}
                  secondaryAction={
                    <IconButton edge="end" onClick={() => hookData.handleDelete(tc.testcase_id, tc.testcase_name)}>
                      <DeleteIcon />
                    </IconButton>
                  }
                  disablePadding
                >
                  <ListItemButton onClick={() => hookData.handleLoad(tc.testcase_id)}>
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
        <DialogActions sx={{ borderTop: 1, borderColor: 'divider', pt: 2, pb: 2, px: 3 }}>
          <Button onClick={() => hookData.setLoadDialogOpen(false)} variant="outlined">
            Cancel
          </Button>
        </DialogActions>
      </Dialog>
      
      {/* Delete Confirmation Dialog */}
      <Dialog 
        open={hookData.deleteConfirmOpen} 
        onClose={() => hookData.setDeleteConfirmOpen(false)}
        maxWidth="sm"
        fullWidth
        PaperProps={{
          sx: {
            border: 2,
            borderColor: 'divider',
          }
        }}
      >
        <DialogTitle sx={{ borderBottom: 1, borderColor: 'divider', pb: 2 }}>
          Delete Test Case
        </DialogTitle>
        <DialogContent sx={{ pt: 3, pb: 3 }}>
          <Typography sx={{ mt: 1 }}>
            Are you sure you want to delete "{hookData.deleteTargetTestCase?.name}"?
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            This action cannot be undone.
          </Typography>
        </DialogContent>
        <DialogActions sx={{ borderTop: 1, borderColor: 'divider', pt: 2, pb: 2, px: 3 }}>
          <Button 
            onClick={() => hookData.setDeleteConfirmOpen(false)}
            variant="outlined"
          >
            Cancel
          </Button>
          <Button 
            onClick={hookData.handleConfirmDelete} 
            color="error" 
            variant="contained"
          >
            Delete
          </Button>
        </DialogActions>
      </Dialog>
      
      {/* New Test Case Confirmation Dialog */}
      <Dialog 
        open={hookData.newConfirmOpen} 
        onClose={() => hookData.setNewConfirmOpen(false)}
        maxWidth="sm"
        fullWidth
        PaperProps={{
          sx: {
            border: 2,
            borderColor: 'divider',
          }
        }}
      >
        <DialogTitle sx={{ borderBottom: 1, borderColor: 'divider', pb: 2 }}>
          Create New Test Case
        </DialogTitle>
        <DialogContent sx={{ pt: 3, pb: 3 }}>
          <Typography sx={{ mt: 1 }}>
            Create new test case? {hookData.hasUnsavedChanges ? 'Unsaved changes will be lost.' : 'Current test case will be cleared.'}
          </Typography>
        </DialogContent>
        <DialogActions sx={{ borderTop: 1, borderColor: 'divider', pt: 2, pb: 2, px: 3 }}>
          <Button 
            onClick={() => hookData.setNewConfirmOpen(false)}
            variant="outlined"
          >
            Cancel
          </Button>
          <Button 
            onClick={hookData.handleConfirmNew} 
            variant="contained"
          >
            OK
          </Button>
        </DialogActions>
      </Dialog>
      
      {/* Snackbar for notifications */}
      <Snackbar
        open={hookData.snackbar.open}
        autoHideDuration={4000}
        onClose={() => hookData.setSnackbar({ ...hookData.snackbar, open: false })}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert
          onClose={() => hookData.setSnackbar({ ...hookData.snackbar, open: false })}
          severity={hookData.snackbar.severity}
          sx={{ width: '100%' }}
        >
          {hookData.snackbar.message}
        </Alert>
      </Snackbar>
      
      {/* Remote/Desktop/AV Panels */}
      <TestCaseBuilderPanels
        showRemotePanel={hookData.showRemotePanel}
        showAVPanel={hookData.showAVPanel}
        selectedHost={hookData.selectedHost}
        selectedDeviceId={hookData.selectedDeviceId}
        isControlActive={hookData.isControlActive}
        userinterfaceName={hookData.userinterfaceName}
        isAVPanelCollapsed={hookData.isAVPanelCollapsed}
        isAVPanelMinimized={hookData.isAVPanelMinimized}
        captureMode={hookData.captureMode}
        isVerificationVisible={hookData.isVerificationVisible}
        isSidebarOpen={isSidebarOpen}
        footerHeight={40}
        handleDisconnectComplete={hookData.handleDisconnectComplete}
        handleAVPanelCollapsedChange={hookData.handleAVPanelCollapsedChange}
        handleAVPanelMinimizedChange={hookData.handleAVPanelMinimizedChange}
        handleCaptureModeChange={hookData.handleCaptureModeChange}
      />
      
      {/* Execution Overlay */}
      <ExecutionOverlay
        isExecuting={isExecuting}
        command={executionDetails.command}
        params={executionDetails.params}
      />
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

