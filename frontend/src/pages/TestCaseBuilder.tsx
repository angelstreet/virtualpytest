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
  addEdge,
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
import { ApiCallBlock } from '../components/testcase/blocks/ApiCallBlock';
import { SuccessEdge } from '../components/testcase/edges/SuccessEdge';
import { FailureEdge } from '../components/testcase/edges/FailureEdge';
import { DataEdge } from '../components/testcase/edges/DataEdge';
// 🆕 NEW: Execution components
import { ExecutionProgressBar } from '../components/testcase/builder/ExecutionProgressBar';

// Dialogs
import { ActionConfigDialog } from '../components/testcase/dialogs/ActionConfigDialog';
import { VerificationConfigDialog } from '../components/testcase/dialogs/VerificationConfigDialog';
import { LoopConfigDialog } from '../components/testcase/dialogs/LoopConfigDialog';
import { StandardBlockConfigDialog } from '../components/testcase/dialogs/StandardBlockConfigDialog';
import { ApiCallConfigModal } from '../components/testcase/dialogs/ApiCallConfigModal';
import { TestCaseBuilderDialogs } from '../components/testcase/builder/TestCaseBuilderDialogs';
import { AIGenerationResultPanel } from '../components/testcase/builder/AIGenerationResultPanel';
import { PromptDisambiguation } from '../components/ai/PromptDisambiguation';

// Shared Container Components
import {
  BuilderPageLayout,
  BuilderSidebarContainer,
  BuilderMainContainer,
  BuilderStatsBarContainer,
} from '../components/common/builder';

// Context
import { TestCaseBuilderProvider } from '../contexts/testcase/TestCaseBuilderContext';
import { NavigationEditorProvider } from '../contexts/navigation/NavigationEditorProvider';
import { NavigationConfigProvider } from '../contexts/navigation/NavigationConfigContext';
import { useTheme } from '../contexts/ThemeContext';

// Hook
import { useTestCaseBuilderPage } from '../hooks/pages/useTestCaseBuilderPage';
import { useTestCaseBuilder } from '../contexts/testcase/TestCaseBuilderContext';

// Constants
import { TOAST_POSITION } from '../constants/toastConfig';

// Node types for React Flow - memoized to prevent recreation warnings
const NODE_TYPES = {
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
  set_variable_io: UniversalBlock,
  set_metadata: UniversalBlock,
  getMenuInfo: UniversalBlock,
  sleep: UniversalBlock,
  get_current_time: UniversalBlock,
  generate_random: UniversalBlock,
  http_request: UniversalBlock,
  loop: UniversalBlock,
  // Standard blocks
  custom_code: UniversalBlock,
  common_operation: UniversalBlock,
  evaluate_condition: UniversalBlock,
  // API blocks
  api_call: ApiCallBlock,
};

// Edge types for React Flow - memoized to prevent recreation warnings
const EDGE_TYPES = {
  success: SuccessEdge,
  failure: FailureEdge,
  true: SuccessEdge,
  false: FailureEdge,
  complete: SuccessEdge,
  break: FailureEdge,
  data: DataEdge, // NEW: Data flow edges
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
  
  // 🆕 NEW: Data linking state for click-to-link I/O
  const [dataLinkingState, setDataLinkingState] = useState<{
    active: boolean;
    sourceBlockId: string;
    sourceHandle: string;
    sourceType: 'input' | 'output';
  } | null>(null);
  
  // Use the consolidated hook for all business logic
  const hookData = useTestCaseBuilderPage();

  // Get undo/redo/copy/paste from context
  const { undo, redo, canUndo, canRedo, resetBuilder, copyBlock, pasteBlock } = useTestCaseBuilder();

  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const [reactFlowInstance, setReactFlowInstance] = React.useState<any>(null);

  // ✅ Listen for block config requests from InputDisplay chips
  React.useEffect(() => {
    const handleOpenBlockConfig = (event: CustomEvent) => {
      const blockId = event.detail?.blockId;
      if (blockId) {
        const node = hookData.nodes.find(n => n.id === blockId);
        if (node) {
          hookData.setSelectedBlock(node);
          hookData.setIsConfigDialogOpen(true);
        }
      }
    };
    
    window.addEventListener('openBlockConfig' as any, handleOpenBlockConfig);
    return () => window.removeEventListener('openBlockConfig' as any, handleOpenBlockConfig);
  }, [hookData.nodes, hookData.setSelectedBlock, hookData.setIsConfigDialogOpen]);

  // ✅ API Block Config Modal State
  const [apiConfigModalOpen, setApiConfigModalOpen] = React.useState(false);
  const [selectedApiBlock, setSelectedApiBlock] = React.useState<any>(null);

  // ✅ Listen for API block config requests
  React.useEffect(() => {
    const handleOpenApiBlockConfig = (event: CustomEvent) => {
      const blockId = event.detail?.blockId;
      if (blockId) {
        const node = hookData.nodes.find(n => n.id === blockId);
        if (node) {
          setSelectedApiBlock(node);
          setApiConfigModalOpen(true);
        }
      }
    };
    
    window.addEventListener('openApiBlockConfig' as any, handleOpenApiBlockConfig);
    return () => window.removeEventListener('openApiBlockConfig' as any, handleOpenApiBlockConfig);
  }, [hookData.nodes]);

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

        const position = reactFlowInstance.screenToFlowPosition({
          x: event.clientX,
          y: event.clientY,
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

  // 🆕 NEW: Handle I/O handle clicks for data linking
  const handleDataHandleClick = useCallback((blockId: string, handleId: string, handleType: 'input' | 'output') => {
    if (handleType === 'output') {
      // Start linking mode from OUTPUT
      setDataLinkingState({
        active: true,
        sourceBlockId: blockId,
        sourceHandle: handleId,
        sourceType: 'output',
      });
      console.log('[@TestCaseBuilder] Data linking started from OUTPUT:', { blockId, handleId });
    } else if (handleType === 'input') {
      if (dataLinkingState?.active) {
        // Completing link: OUTPUT → INPUT
        
        // Prevent self-linking (same block)
        if (dataLinkingState.sourceBlockId === blockId) {
          console.log('[@TestCaseBuilder] Cannot link block to itself');
          setDataLinkingState(null);
          return;
        }
        
        // Create DATA edge
        console.log('[@TestCaseBuilder] Creating data edge (OUT → IN):', {
          source: dataLinkingState.sourceBlockId,
          target: blockId,
        });
        
        const newEdge = {
          id: `data-${dataLinkingState.sourceBlockId}-${blockId}-${Date.now()}`,
          source: dataLinkingState.sourceBlockId,
          sourceHandle: dataLinkingState.sourceHandle,
          target: blockId,
          targetHandle: handleId,
          type: 'data',
        };
        
        hookData.setEdges((eds: any) => addEdge(newEdge, eds));
        setDataLinkingState(null);
      } else {
        // IN clicked when NOT in linking mode → Open dialog to set static value
        console.log('[@TestCaseBuilder] Opening dialog to set static value for block:', blockId);
        // TODO: Open dialog to set static input value
        // For now, just log - dialog implementation will come later
      }
    }
  }, [dataLinkingState, hookData.setEdges]);

  // Cancel linking on Escape key
  React.useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && dataLinkingState?.active) {
        setDataLinkingState(null);
        console.log('[@TestCaseBuilder] Data linking cancelled');
      }
    };
    
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [dataLinkingState]);

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
      // Standard blocks: Open StandardBlockConfigDialog
      const standardBlockTypes = ['evaluate_condition', 'custom_code', 'common_operation', 'set_variable', 'set_variable_io', 'get_current_time', 'sleep'];
      if (standardBlockTypes.includes(node.type)) {
        hookData.setSelectedBlock(node);
        hookData.setIsConfigDialogOpen(true);
      }
      // Other blocks use inline InputDisplay/OutputDisplay
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

  // Fit view when test case is loaded (when currentTestcaseId changes)
  React.useEffect(() => {
    if (reactFlowInstance && hookData.currentTestcaseId) {
      // Small delay to ensure nodes are rendered
      setTimeout(() => {
        reactFlowInstance.fitView({ padding: 0.2, duration: 300 });
      }, 150);
    }
  }, [reactFlowInstance, hookData.currentTestcaseId]);

  // Wrap handleNew to trigger fitView after reset
  const wrappedHandleNew = useCallback(() => {
    hookData.handleNew();
    // Fit view after new test case is created
    if (reactFlowInstance) {
      setTimeout(() => {
        reactFlowInstance.fitView({ padding: 0.2, duration: 300 });
      }, 200);
    }
  }, [hookData.handleNew, reactFlowInstance]);

  return (
    <BuilderPageLayout>
      {/* Header */}
      <TestCaseBuilderHeader
        actualMode={actualMode}
        builderType="TestCase"
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
        isLoadingTree={hookData.isLoadingTree}
        testcaseName={hookData.testcaseName}
        hasUnsavedChanges={hookData.hasUnsavedChanges}
        handleNew={wrappedHandleNew}
        handleLoadClick={hookData.handleLoadClick}
        isLoadingTestCases={hookData.isLoadingTestCases}
        setSaveDialogOpen={hookData.setSaveDialogOpen}
        handleExecute={hookData.handleExecute}
        isExecuting={hookData.executionState.isExecuting}
        isExecutable={hookData.isExecutable}
        onCloseProgressBar={() => hookData.unifiedExecution.resetExecution()}
        undo={undo}
        redo={redo}
        canUndo={canUndo}
        canRedo={canRedo}
        resetBuilder={resetBuilder}
        copyBlock={copyBlock}
        pasteBlock={pasteBlock}
      />

      {/* Main Container - Using shared container */}
      <BuilderMainContainer>
        {/* Execution Progress Bar (floating, non-blocking) */}
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
        
        {/* Sidebar - Using shared container */}
        <BuilderSidebarContainer
          actualMode={actualMode}
          isOpen={isSidebarOpen}
          onToggle={() => setIsSidebarOpen(!isSidebarOpen)}
        >
          <TestCaseBuilderSidebar
          actualMode={actualMode}
          creationMode={hookData.creationMode}
          isSidebarOpen={isSidebarOpen}
          toggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
          toolboxConfig={hookData.dynamicToolboxConfig}
          selectedHost={hookData.selectedHost}
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
        </BuilderSidebarContainer>

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
                onDataHandleClick: handleDataHandleClick, // 🆕 NEW: Pass handler to blocks
                dataLinkingState: dataLinkingState, // 🆕 NEW: Pass linking state
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
            nodeTypes={NODE_TYPES}
            edgeTypes={EDGE_TYPES}
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
      </BuilderMainContainer>

      {/* Stats Bar - Using shared container */}
      <BuilderStatsBarContainer actualMode={actualMode}>
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
      </BuilderStatsBarContainer>

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

      {/* Standard Blocks Config Dialog */}
      {hookData.selectedBlock && ['evaluate_condition', 'custom_code', 'common_operation', 'set_variable', 'set_variable_io', 'get_current_time', 'sleep'].includes(hookData.selectedBlock.type) && (
        <StandardBlockConfigDialog
          open={hookData.isConfigDialogOpen}
          blockCommand={hookData.selectedBlock.data.command || hookData.selectedBlock.type}
          blockLabel={hookData.selectedBlock.data.label || hookData.selectedBlock.type}
          params={hookData.selectedBlock.data.paramSchema || {}}
          initialData={hookData.selectedBlock.data.params || {}}
          availableVariables={(() => {
            // Get script I/O from context
            const { scriptInputs, scriptOutputs, scriptVariables, executionOutputValues } = useTestCaseBuilder();
            
            const variables: any[] = [];
            
            // Add script inputs with their default values
            scriptInputs.forEach((input: any) => {
              variables.push({
                name: input.name,
                type: input.type,
                source: 'input',
                value: input.default, // Show default value
              });
            });
            
            // Add script outputs with execution values if available
            scriptOutputs.forEach((output: any) => {
              variables.push({
                name: output.name,
                type: output.type,
                source: 'output',
                value: executionOutputValues[output.name], // Show runtime value
              });
            });
            
            // Add script variables
            scriptVariables.forEach((variable: any) => {
              variables.push({
                name: variable.name,
                type: variable.type,
                source: 'variable',
                value: variable.value, // Show variable value
              });
            });
            
            // Add block outputs from nodes
            hookData.nodes.forEach((node: any) => {
              if (node.data?.outputSchema && node.id !== hookData.selectedBlock?.id) {
                Object.entries(node.data.outputSchema).forEach(([outputName, outputType]) => {
                  variables.push({
                    name: outputName,
                    type: outputType as string,
                    source: 'block_output',
                    blockId: node.data.label || node.id,
                    // Could add execution values here if available
                  });
                });
              }
            });
            
            return variables;
          })()}
          onSave={(newParams) => {
            if (hookData.selectedBlock) {
              hookData.updateBlock(hookData.selectedBlock.id, { params: newParams });
            }
            hookData.setIsConfigDialogOpen(false);
          }}
          onCancel={() => hookData.setIsConfigDialogOpen(false)}
        />
      )}

      {/* API Call Config Modal */}
      <ApiCallConfigModal
        open={apiConfigModalOpen}
        onClose={() => {
          setApiConfigModalOpen(false);
          setSelectedApiBlock(null);
        }}
        initialConfig={selectedApiBlock?.data?.params}
        onSave={(config) => {
          if (selectedApiBlock) {
            // Update block with API configuration
            hookData.updateBlock(selectedApiBlock.id, {
              params: config,
              label: config.request_name,
              // Define block outputs for API calls
              blockOutputs: [
                { name: 'response', type: 'object', value: null },
                { name: 'status_code', type: 'number', value: null },
                { name: 'headers', type: 'object', value: null },
              ],
            });
          }
          setApiConfigModalOpen(false);
          setSelectedApiBlock(null);
        }}
      />
      
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
        testcaseFolder={hookData.testcaseFolder}
        setTestcaseFolder={hookData.setTestcaseFolder}
        testcaseTags={hookData.testcaseTags}
        setTestcaseTags={hookData.setTestcaseTags}
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
            onClick={hookData.handleCancelDelete}
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
        isMobileOrientationLandscape={hookData.isMobileOrientationLandscape}
        handleMobileOrientationChange={hookData.handleMobileOrientationChange}
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
    </BuilderPageLayout>
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

