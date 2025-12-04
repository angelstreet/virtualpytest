/**
 * Campaign Builder Page
 * 
 * Visual campaign builder with React Flow canvas.
 * Allows users to create campaigns by dragging testcases and scripts onto a canvas,
 * connecting them visually, and linking data between blocks.
 * 
 * NOTE: Uses shared container components and TestCase terminal blocks for consistency
 */

import React, { useCallback, DragEvent, useState, useEffect } from 'react';
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
import { useHostManager } from '../contexts/index';
import { useUserInterface } from '../hooks/pages/useUserInterface';
import { useBuilder } from '../contexts/builder/useBuilder';
import { useDeviceControlWithForceUnlock } from '../hooks/useDeviceControlWithForceUnlock';
import { useNavigationConfig, NavigationConfigProvider } from '../contexts/navigation/NavigationConfigContext';
import { NavigationEditorProvider } from '../contexts/navigation/NavigationEditorProvider';
import { useDeviceData } from '../contexts/device/DeviceDataContext';

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
  
  // 🆕 Get standard blocks from BuilderContext (same as TestCase builder)
  const { standardBlocks, fetchStandardBlocks } = useBuilder();
  
  // 🆕 Get device control from HostManager (same as TestCase builder)
  const {
    selectedHost,
    selectedDeviceId,
    isControlActive,
    isRemotePanelOpen,
    availableHosts,
    handleDeviceSelect,
    handleToggleRemotePanel,
    handleControlStateChange,
    isDeviceLocked: hostManagerIsDeviceLocked,
  } = useHostManager();
  
  // 🆕 Get userinterface management (same as TestCase builder)
  const { getAllUserInterfaces, getUserInterfaceByName } = useUserInterface();
  const { loadTreeByUserInterface } = useNavigationConfig();
  
  // 🆕 Interface state (same as TestCase builder workflow)
  const [compatibleInterfaceNames, setCompatibleInterfaceNames] = useState<string[]>([]);
  const [userinterfaceName, setUserinterfaceName] = useState<string>('');
  const [currentTreeId, setCurrentTreeId] = useState<string | null>(null);
  const [isLoadingTree, setIsLoadingTree] = useState(false);
  
  // 🆕 Device control hook (EXACT same as TestCase builder)
  const {
    isControlLoading,
    handleDeviceControl,
  } = useDeviceControlWithForceUnlock({
    host: selectedHost,
    device_id: selectedDeviceId,
    sessionId: 'campaign-builder-session',
    autoCleanup: true,
    tree_id: currentTreeId || undefined,
    onControlStateChange: handleControlStateChange,
  });
  
  // 🆕 Device data (EXACT same as TestCase builder)
  const { 
    setControlState, 
    fetchAvailableActions,
  } = useDeviceData();
  
  useEffect(() => {
    setControlState(selectedHost, selectedDeviceId, isControlActive);
  }, [selectedHost, selectedDeviceId, isControlActive, setControlState]);
  
  // 🆕 Fetch actions and standard blocks after control (EXACT same as TestCase builder)
  useEffect(() => {
    if (!isControlActive || !selectedHost || !selectedDeviceId) return;
    
    const timer = setTimeout(async () => {
      await fetchAvailableActions(true);
      // Fetch standard blocks after control with host_name
      if (selectedHost?.host_name) {
        await fetchStandardBlocks(selectedHost.host_name, true);
      }
    }, 1000);

    return () => clearTimeout(timer);
  }, [isControlActive, selectedHost, selectedDeviceId, fetchAvailableActions, fetchStandardBlocks]);
  
  // 🆕 Load compatible interfaces (EXACT same as TestCase builder)
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
        
        // Auto-select first compatible interface
        if (names.length > 0 && !names.includes(userinterfaceName)) {
          setUserinterfaceName(names[0]);
          console.log('[@CampaignBuilder] Auto-selected interface:', names[0]);
        }
      } catch (error) {
        console.error('[@CampaignBuilder] Failed to load compatible interfaces:', error);
      }
    };
    
    loadCompatibleInterfaces();
  }, [selectedDeviceId, selectedHost, getAllUserInterfaces, userinterfaceName]);
  
  // 🆕 Load navigation tree (EXACT same as TestCase builder)
  useEffect(() => {
    const loadNavigationTree = async () => {
      if (!selectedDeviceId || !userinterfaceName) {
        setCurrentTreeId(null);
        setIsLoadingTree(false);
        return;
      }
      
      setIsLoadingTree(true);
      
      try {
        const userInterface = await getUserInterfaceByName(userinterfaceName);
        
        if (userInterface) {
          const result = await loadTreeByUserInterface(userInterface.id);
          const treeId = result?.tree?.id || userInterface.root_tree;
          
          setCurrentTreeId(treeId);
          
          console.log('[@CampaignBuilder] ✅ Loaded navigation tree:', {
            interface: userinterfaceName,
            treeId: treeId,
          });
        }
      } catch (error) {
        console.error('[@CampaignBuilder] ❌ Failed to load tree:', error);
        setCurrentTreeId(null);
      } finally {
        setIsLoadingTree(false);
      }
    };
    
    loadNavigationTree();
  }, [selectedDeviceId, userinterfaceName, getUserInterfaceByName, loadTreeByUserInterface]);
  
  // Wrapper for isDeviceLocked to match expected signature
  const isDeviceLocked = useCallback((deviceKey: string) => {
    const [hostName, deviceId] = deviceKey.includes(':')
      ? deviceKey.split(':')
      : [deviceKey, 'device1'];
    
    const host = availableHosts.find((h: any) => h.host_name === hostName);
    return hostManagerIsDeviceLocked(host || null, deviceId);
  }, [availableHosts, hostManagerIsDeviceLocked]);
  
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

  // Header props - now with REAL device control AND userinterface (same workflow as TestCase builder)
  const [creationMode, setCreationMode] = useState<'visual' | 'ai'>('visual');
  
  const headerProps = {
    actualMode,
    builderType: 'Campaign' as const,
    creationMode,
    setCreationMode,
    // EXACT same as TestCase builder
    selectedHost,
    selectedDeviceId,
    isControlActive,
    isControlLoading,
    isRemotePanelOpen,
    availableHosts,
    isDeviceLocked,
    handleDeviceSelect,
    handleDeviceControl,
    handleToggleRemotePanel,
    // EXACT same as TestCase builder
    compatibleInterfaceNames,
    userinterfaceName,
    setUserinterfaceName,
    isLoadingTree,
    currentTreeId,
    // Campaign operations
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
            standardBlocks={standardBlocks}
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

// Main component wrapped in provider (EXACT same as TestCase builder)
const CampaignBuilder: React.FC = () => {
  return (
    <ReactFlowProvider>
      <NavigationConfigProvider>
        <NavigationEditorProvider>
          <CampaignBuilderProvider>
            <CampaignBuilderContent />
          </CampaignBuilderProvider>
        </NavigationEditorProvider>
      </NavigationConfigProvider>
    </ReactFlowProvider>
  );
};

export default CampaignBuilder;
