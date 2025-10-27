import React, { useCallback, useRef, DragEvent, useState } from 'react';
import { 
  Box, 
  Button, 
  Typography, 
  Dialog, 
  DialogTitle, 
  DialogContent, 
  DialogActions,
  Alert,
  Snackbar
} from '@mui/material';
import ReactFlow, {
  ReactFlowProvider,
  MarkerType,
} from 'reactflow';
import 'reactflow/dist/style.css';

// Auto-layout utility
import { getLayoutedElements } from '../components/testcase/ai/autoLayout';

// Hide React Flow attribution
const styles = `
  .react-flow__panel.react-flow__attribution {
    display: none !important;
  }
`;

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
// 🆕 NEW: Execution components
import { ExecutionProgressBar } from '../components/testcase/builder/ExecutionProgressBar';

// Dialogs
import { ActionConfigDialog } from '../components/testcase/dialogs/ActionConfigDialog';
import { VerificationConfigDialog } from '../components/testcase/dialogs/VerificationConfigDialog';
import { LoopConfigDialog } from '../components/testcase/dialogs/LoopConfigDialog';
import { TestCaseBuilderDialogs } from '../components/testcase/builder/TestCaseBuilderDialogs';
import { AIGenerationResultPanel } from '../components/testcase/builder/AIGenerationResultPanel';
import { PromptDisambiguation } from '../components/ai/PromptDisambiguation';

// Context
import { TestCaseBuilderProvider } from '../contexts/testcase/TestCaseBuilderContext';
import { NavigationEditorProvider } from '../contexts/navigation/NavigationEditorProvider';
import { NavigationConfigProvider } from '../contexts/navigation/NavigationConfigContext';
import { useTheme } from '../contexts/ThemeContext';

// Hook
import { useTestCaseBuilderPage } from '../hooks/pages/useTestCaseBuilderPage';

// Constants
import { TOAST_POSITION } from '../constants/toastConfig';

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
  
  // 🗑️ REMOVED: Local execution overlay state - now using unifiedExecution from context
  
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

  // Handle block single click - just select
  const onNodeClick = useCallback(
    (_event: React.MouseEvent, node: any) => {
      hookData.setSelectedBlock(node);
    },
    [hookData.setSelectedBlock]
  );

  // Handle block double click - open configuration dialog
  const onNodeDoubleClick = useCallback(
    (_event: React.MouseEvent, node: any) => {
      // Don't open dialog for terminal blocks or navigation blocks
      if (node.type === 'start' || node.type === 'success' || node.type === 'failure' || node.type === 'navigation') {
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

  // Auto-layout handler - ALWAYS vertical (top to bottom)
  const handleAutoLayout = useCallback(() => {
    const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
      hookData.nodes,
      hookData.edges,
      { direction: 'TB' } // Force vertical layout
    );
    hookData.setNodes(layoutedNodes);
    hookData.setEdges(layoutedEdges);
    
    // Fit view after layout with a small delay
    if (reactFlowInstance) {
      setTimeout(() => {
        reactFlowInstance.fitView({ padding: 0.2, duration: 300 });
      }, 50);
    }
  }, [hookData.nodes, hookData.edges, hookData.setNodes, hookData.setEdges, reactFlowInstance]);

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
      bottom: 32, // Leave space for shared Footer (minHeight 24 + py 8 = 32px)
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
        handleNew={hookData.handleNew}
        handleLoadClick={hookData.handleLoadClick}
        isLoadingTestCases={hookData.isLoadingTestCases}
        setSaveDialogOpen={hookData.setSaveDialogOpen}
        handleExecute={hookData.handleExecute}
        isExecuting={hookData.executionState.isExecuting}
        isExecutable={hookData.isExecutable}
        onCloseProgressBar={() => hookData.unifiedExecution.resetExecution()}
      />

      {/* Main Container */}
      <Box sx={{ 
        flex: 1,
        display: 'flex', 
        overflow: 'hidden',
        minHeight: 0,
        position: 'relative',
      }}>
        {/* 🆕 NEW: Execution Progress Bar (floating, non-blocking) */}
        {(hookData.unifiedExecution.state.isExecuting || hookData.unifiedExecution.state.blockStates.size > 0) && (
          <ExecutionProgressBar
            currentBlockId={hookData.unifiedExecution.state.currentBlockId}
            blockStates={hookData.unifiedExecution.state.blockStates}
            isExecuting={hookData.unifiedExecution.state.isExecuting}
            nodes={hookData.nodes}
            executionResult={hookData.unifiedExecution.state.result}
            onStop={() => {
              // TODO: Implement stop execution
              console.log('Stop execution requested');
            }}
            onClose={() => {
              // User manually closes the progress bar
              hookData.unifiedExecution.resetExecution();
            }}
          />
        )}
        
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
          onCloseProgressBar={() => hookData.unifiedExecution.resetExecution()}
          aiPrompt={hookData.aiPrompt}
          setAiPrompt={hookData.setAiPrompt}
          isGenerating={hookData.isGenerating}
          handleGenerateWithAI={hookData.handleGenerateWithAI}
          hasLastGeneration={!!hookData.aiGenerationResult}
          handleShowLastGeneration={hookData.handleShowLastGeneration}
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
            nodes={hookData.nodes.map(node => ({
              ...node,
              // 🆕 ADD: Pass execution state to each node
              data: {
                ...node.data,
                executionState: hookData.unifiedExecution.state.blockStates.get(node.id),
              },
            }))}
            edges={hookData.edges.map(edge => {
              // 🆕 ADD: Calculate edge execution state based on source/target blocks
              const sourceNode = hookData.nodes.find(n => n.id === edge.source);
              const targetNode = hookData.nodes.find(n => n.id === edge.target);
              const sourceBlockState = hookData.unifiedExecution.state.blockStates.get(edge.source);
              const targetBlockState = hookData.unifiedExecution.state.blockStates.get(edge.target);
              const currentBlockId = hookData.unifiedExecution.state.currentBlockId;
              const previousBlockId = hookData.unifiedExecution.state.previousBlockId;
              const isExecuting = hookData.unifiedExecution.state.isExecuting;
              
              // Determine edge execution state
              let edgeExecutionState: 'idle' | 'active' | 'success' | 'failure' = 'idle';
              
              // 🆕 SPECIAL: START node - edge is active when execution begins or target is executing
              if (sourceNode?.type === 'start' && isExecuting) {
                if (currentBlockId === edge.target || previousBlockId === edge.source) {
                  edgeExecutionState = 'active';
                } else if (targetBlockState && targetBlockState.status !== 'pending') {
                  edgeExecutionState = 'success';
                }
              }
              // 🆕 SPECIAL: Terminal nodes (SUCCESS/FAILURE) - show result when reached
              else if (targetNode?.type === 'success' || targetNode?.type === 'failure') {
                if (targetBlockState && targetBlockState.status !== 'pending') {
                  // Edge to SUCCESS terminal = green, edge to FAILURE terminal = red
                  edgeExecutionState = targetNode.type === 'success' ? 'success' : 'failure';
                } else if (currentBlockId === edge.target) {
                  edgeExecutionState = 'active';
                }
              }
              // Active: Edge is currently being traversed (from previous to current block)
              else if (isExecuting && 
                       previousBlockId === edge.source && 
                       currentBlockId === edge.target) {
                edgeExecutionState = 'active';
              }
              // Success/Failure: Edge was traversed after source block completed
              else if (sourceBlockState && 
                       (sourceBlockState.status === 'success' || sourceBlockState.status === 'failure') &&
                       targetBlockState &&
                       targetBlockState.status !== 'pending') {
                // Check if this edge was actually taken based on the handle type
                const handleType = edge.sourceHandle || 'success';
                const blockSucceeded = sourceBlockState.status === 'success';
                
                if ((blockSucceeded && handleType === 'success') || 
                    (!blockSucceeded && handleType === 'failure')) {
                  edgeExecutionState = sourceBlockState.status;
                }
              }
              
              return {
                ...edge,
                data: {
                  ...edge.data,
                  executionState: edgeExecutionState,
                },
              };
            })}
            onNodesChange={hookData.onNodesChange}
            onEdgesChange={hookData.onEdgesChange}
            onConnect={hookData.onConnect}
            onNodeClick={onNodeClick}
            onNodeDoubleClick={onNodeDoubleClick}
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
              onAutoLayout={handleAutoLayout}
              // 🗑️ REMOVED: isExecuting, executionDetails - no longer needed
            />
          </ReactFlow>
        </Box>
      </Box>

      {/* Stats Bar - Page-specific info above shared footer */}
      <Box
        sx={{
          height: '32px',
          borderTop: 1,
          borderColor: 'divider',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          px: 2,
          background: actualMode === 'dark' ? '#1e293b' : '#f1f5f9',
          flexShrink: 0,
        }}
      >
        <Typography variant="caption" color="text.secondary">
          {hookData.nodes.filter(n => !['start', 'success', 'failure'].includes(n.type)).length} blocks • {hookData.edges.length} connections
        </Typography>
        <Typography variant="caption" color="text.secondary">
          {hookData.executionState.isExecuting && 'Executing...'}
          {hookData.executionState.result && !hookData.executionState.isExecuting && (() => {
            const result = hookData.executionState.result;
            const resultType = result.result_type || (result.success ? 'success' : 'error');
            
            if (resultType === 'success') {
              return `✓ Last run: SUCCESS (${result.execution_time_ms}ms)`;
            } else if (resultType === 'failure') {
              return `✗ Last run: FAILURE (${result.execution_time_ms}ms)`;
            } else {
              return `⚠ Last run: ERROR - ${result.error || 'Unknown error'}`;
            }
          })()}
        </Typography>
      </Box>

      {/* Configuration Dialogs */}
      {hookData.selectedBlock?.type === 'action' && (
        <ActionConfigDialog
          open={hookData.isConfigDialogOpen}
          initialData={hookData.selectedBlock.data}
          onSave={handleConfigSave}
          onCancel={() => hookData.setIsConfigDialogOpen(false)}
        />
      )}

      {hookData.selectedBlock?.type === 'verification' && (
        <VerificationConfigDialog
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
      
      {/* All Dialogs - using TestCaseBuilderDialogs component */}
      <TestCaseBuilderDialogs
        saveDialogOpen={hookData.saveDialogOpen}
        setSaveDialogOpen={hookData.setSaveDialogOpen}
        testcaseName={hookData.testcaseName}
        setTestcaseName={hookData.setTestcaseName}
        testcaseDescription={hookData.description}
        setTestcaseDescription={hookData.setDescription}
        testcaseEnvironment="dev"
        setTestcaseEnvironment={() => {}}
        currentTestcaseId={hookData.currentTestcaseId}
        currentVersion={
          hookData.currentTestcaseId 
            ? hookData.testcaseList.find(tc => tc.testcase_id === hookData.currentTestcaseId)?.current_version 
            : null
        }
        handleSave={hookData.handleSave}
        loadDialogOpen={hookData.loadDialogOpen}
        setLoadDialogOpen={hookData.setLoadDialogOpen}
        availableTestcases={hookData.testcaseList}
        handleLoad={hookData.handleLoad}
        handleDelete={hookData.handleDelete}
        editDialogOpen={false}
        setEditDialogOpen={() => {}}
        editingNode={null}
        editFormData={{}}
        setEditFormData={() => {}}
        handleSaveEdit={() => {}}
        aiGenerateConfirmOpen={hookData.aiGenerateConfirmOpen}
        setAiGenerateConfirmOpen={hookData.setAiGenerateConfirmOpen}
        handleConfirmAIGenerate={hookData.handleConfirmAIGenerate}
      />
      
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
      
      {/* Snackbar for notifications - using centralized positioning */}
      <Snackbar
        open={hookData.snackbar.open}
        autoHideDuration={4000}
        onClose={() => hookData.setSnackbar({ ...hookData.snackbar, open: false })}
        anchorOrigin={TOAST_POSITION.anchorOrigin}
        sx={TOAST_POSITION.sx}
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
      
      {/* AI Generation Result Panel */}
      {hookData.showAIResultPanel && hookData.aiGenerationResult && (
        <AIGenerationResultPanel
          result={hookData.aiGenerationResult}
          onClose={hookData.handleCloseAIResultPanel}
          onRegenerate={hookData.handleRegenerateAI}
          originalPrompt={hookData.aiPrompt}
        />
      )}
      
      {/* AI Disambiguation Modal - Rendered at top level with proper z-index */}
      {hookData.disambiguationData && (
        <>
          {console.log('[@TestCaseBuilder] Rendering PromptDisambiguation modal')}
          {console.log('[@TestCaseBuilder] Modal data:', {
            hasAmbiguities: !!hookData.disambiguationData.ambiguities,
            ambiguitiesLength: hookData.disambiguationData.ambiguities?.length,
            hasAutoCorrections: !!hookData.disambiguationData.auto_corrections,
            hasAvailableNodes: !!hookData.disambiguationData.available_nodes
          })}
          <PromptDisambiguation
            ambiguities={hookData.disambiguationData.ambiguities}
            autoCorrections={hookData.disambiguationData.auto_corrections}
            availableNodes={hookData.disambiguationData.available_nodes}
            onResolve={hookData.handleDisambiguationResolve}
            onCancel={hookData.handleDisambiguationCancel}
            onEditPrompt={hookData.handleDisambiguationEditPrompt}
          />
        </>
      )}
      
      {/* 🗑️ REMOVED: ExecutionOverlay - replaced by ExecutionProgressBar + ExecutionLog */}
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

