/**
 * Campaign Builder Page
 * 
 * Visual campaign builder with React Flow canvas.
 * Allows users to create campaigns by dragging testcases and scripts onto a canvas,
 * connecting them visually, and linking data between blocks.
 * 
 * NOTE: Uses shared container components and TestCase terminal blocks for consistency
 */

import React, { useCallback, DragEvent, useState } from 'react';
import ReactFlow, {
  ReactFlowProvider,
  ConnectionMode,
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
import {
  Box,
  Typography,
} from '@mui/material';

// Shared Container Components
import {
  BuilderPageLayout,
  BuilderSidebarContainer,
  BuilderMainContainer,
  BuilderStatsBarContainer,
} from '../components/common/builder';

// Reuse TestCase terminal blocks and canvas for consistency
import { StartBlock } from '../components/testcase/blocks/StartBlock';
import { SuccessBlock } from '../components/testcase/blocks/SuccessBlock';
import { FailureBlock } from '../components/testcase/blocks/FailureBlock';
import { SuccessEdge } from '../components/testcase/edges/SuccessEdge';
import { FailureEdge } from '../components/testcase/edges/FailureEdge';
import { TestCaseBuilderCanvas } from '../components/testcase/builder/TestCaseBuilderCanvas';
import { TestCaseBuilderHeader } from '../components/testcase/builder/TestCaseBuilderHeader';

// Campaign-specific components
import { CampaignBuilderProvider, useCampaignBuilder } from '../contexts/campaign/CampaignBuilderContext';
import { CampaignBlock } from '../components/campaign/blocks/CampaignBlock';
import { CampaignToolbox } from '../components/campaign/builder/CampaignToolbox';
import { CampaignNode, CampaignDragData } from '../types/pages/CampaignGraph_Types';
import { useTheme } from '../contexts/ThemeContext';

// Define node types for React Flow - reuse TestCase terminal blocks
const nodeTypes = {
  start: StartBlock,
  success: SuccessBlock,
  failure: FailureBlock,
  testcase: CampaignBlock,
  script: CampaignBlock,
};

// Reuse TestCase edge types for consistent styling
const edgeTypes = {
  success: SuccessEdge,
  failure: FailureEdge,
  control: SuccessEdge, // Campaign uses 'control' type for flow edges
};

// Default edge options - matching TestCaseBuilder
const defaultEdgeOptions = {
  type: 'success',
  animated: false,
  style: {
    stroke: '#94a3b8',
    strokeWidth: 2,
  },
  markerEnd: {
    type: MarkerType.ArrowClosed,
    width: 20,
    height: 20,
    color: '#94a3b8',
  },
};

const CampaignBuilderContent: React.FC = () => {
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
    onNodesChange,
    onEdgesChange,
    onConnect,
    addNode,
    saveCampaign,
    state,
  } = useCampaignBuilder();
  
  // Sidebar state
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [reactFlowInstance, setReactFlowInstance] = React.useState<any>(null);

  // Handle save
  const handleSave = async () => {
    const success = await saveCampaign();
    if (success) {
      console.log('[@CampaignBuilder] Campaign saved successfully');
    } else {
      console.error('[@CampaignBuilder] Failed to save campaign');
    }
  };

  // Handle execute
  const handleExecute = () => {
    console.log('[@CampaignBuilder] Execute campaign:', state);
  };

  // Placeholder props for header (will be fully implemented when campaign execution is added)
  const [creationMode, setCreationMode] = useState<'visual' | 'ai'>('visual');
  
  // TODO: These will come from a proper hook when device control is implemented for campaigns
  const headerProps = {
    actualMode,
    builderType: 'Campaign' as const,
    creationMode,
    setCreationMode,
    selectedHost: null,
    selectedDeviceId: null,
    isControlActive: false,
    isControlLoading: false,
    isRemotePanelOpen: false,
    availableHosts: [],
    isDeviceLocked: () => false,
    handleDeviceSelect: () => {},
    handleDeviceControl: () => {},
    handleToggleRemotePanel: () => {},
    compatibleInterfaceNames: [],
    userinterfaceName: '',
    setUserinterfaceName: () => {},
    isLoadingTree: false,
    currentTreeId: null,
    testcaseName: state.campaign_name || 'Untitled',
    hasUnsavedChanges: false, // TODO: Track changes
    handleNew: () => { console.log('New campaign'); },
    handleLoadClick: async () => { console.log('Load campaign'); },
    isLoadingTestCases: false,
    setSaveDialogOpen: (open: boolean) => { if (open) handleSave(); },
    handleExecute,
    isExecuting: false, // TODO: Track execution state
    isExecutable: nodes.length > 3,
    onCloseProgressBar: () => {},
    // Undo/Redo/Copy/Paste - Campaign builder will implement these
    undo: () => { console.log('Undo - TODO: implement for campaigns'); },
    redo: () => { console.log('Redo - TODO: implement for campaigns'); },
    canUndo: false, // TODO: Track undo stack
    canRedo: false, // TODO: Track redo stack
    resetBuilder: () => { console.log('Reset - TODO: implement for campaigns'); },
    copyBlock: () => { console.log('Copy - TODO: implement for campaigns'); },
    pasteBlock: () => { console.log('Paste - TODO: implement for campaigns'); },
  };

  // Auto-layout handler - ALWAYS vertical (top to bottom)
  const handleAutoLayout = useCallback(() => {
    const { nodes: layoutedNodes } = getLayoutedElements(
      nodes,
      edges as any,
      { direction: 'TB' } // Force vertical layout
    );
    
    // Update nodes positions via React Flow's handlers
    const nodeChanges = layoutedNodes.map((node) => ({
      id: node.id,
      type: 'position',
      position: node.position,
    }));
    
    onNodesChange(nodeChanges as any);
    
    // Fit view after layout with a small delay
    if (reactFlowInstance) {
      setTimeout(() => {
        reactFlowInstance.fitView({ padding: 0.2, duration: 300 });
      }, 50);
    }
  }, [nodes, edges, onNodesChange, reactFlowInstance]);

  // Handle drop from toolbox onto canvas
  const handleDrop = useCallback((event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();

    try {
      const dragData: CampaignDragData = JSON.parse(event.dataTransfer.getData('application/json'));
      
      if (dragData.type !== 'toolbox-item' || !dragData.toolboxItem) {
        return;
      }

      // Get the drop position
      const reactFlowBounds = event.currentTarget.getBoundingClientRect();
      const position = {
        x: event.clientX - reactFlowBounds.left - 140,
        y: event.clientY - reactFlowBounds.top,
      };

      // Create new node
      const item = dragData.toolboxItem;
      const newNode: CampaignNode = {
        id: `node-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        type: item.type,
        position,
        data: {
          label: item.label,
          description: item.description,
          executableId: item.executableId,
          executableType: item.executableType,
          executableName: item.executableName,
          parameters: {},
          inputs: item.executableType === 'testcase' ? [] : undefined,
          outputs: item.executableType === 'testcase' ? [] : undefined,
        },
      };

      addNode(newNode);
      
      console.log('[@CampaignBuilder] Added node:', newNode);
    } catch (error) {
      console.error('[@CampaignBuilder] Error handling drop:', error);
    }
  }, [addNode]);

  const handleDragOver = useCallback((event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'copy';
  }, []);

  return (
    <BuilderPageLayout>
      {/* Header - Using EXACT same TestCaseBuilderHeader */}
      <TestCaseBuilderHeader {...headerProps} />

      {/* Main Container - Using shared container */}
      <BuilderMainContainer>
        {/* Sidebar - Using shared container */}
        <BuilderSidebarContainer
          actualMode={actualMode}
          isOpen={isSidebarOpen}
          onToggle={() => setIsSidebarOpen(!isSidebarOpen)}
        >
          <CampaignToolbox
            actualMode={actualMode}
            toggleSidebar={() => setIsSidebarOpen(false)}
          />
        </BuilderSidebarContainer>

        {/* Canvas - EXACT same structure as TestCaseBuilder */}
        <Box 
          sx={{ 
            flex: 1, 
            height: '100%',
            minWidth: 0,
            overflow: 'hidden',
          }} 
          onDrop={handleDrop} 
          onDragOver={handleDragOver}
        >
          <ReactFlow
            nodes={nodes}
            edges={edges as any}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
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
            connectionMode={ConnectionMode.Loose}
            fitView
          >
            {/* Reuse TestCaseBuilderCanvas for consistent controls and minimap */}
            <TestCaseBuilderCanvas
              actualMode={actualMode}
              isSidebarOpen={isSidebarOpen}
              onAutoLayout={handleAutoLayout}
            />
          </ReactFlow>
        </Box>
      </BuilderMainContainer>

      {/* Stats Bar - Using shared container */}
      <BuilderStatsBarContainer actualMode={actualMode}>
        <Typography variant="caption" color="text.secondary">
          {nodes.filter(n => !['start', 'success', 'failure'].includes(n.type || '')).length} blocks • {edges.length} connections
        </Typography>
        <Typography variant="caption" color="text.secondary">
          {state.campaign_name ? `Campaign: ${state.campaign_name}` : 'Unsaved Campaign'}
        </Typography>
      </BuilderStatsBarContainer>
    </BuilderPageLayout>
  );
};

// Main component wrapped in provider
const CampaignBuilder: React.FC = () => {
  return (
    <ReactFlowProvider>
      <CampaignBuilderProvider>
        <CampaignBuilderContent />
      </CampaignBuilderProvider>
    </ReactFlowProvider>
  );
};

export default CampaignBuilder;
