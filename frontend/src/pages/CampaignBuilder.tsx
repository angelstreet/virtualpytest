/**
 * Campaign Builder Page
 * 
 * Visual campaign builder with React Flow canvas.
 * Allows users to create campaigns by dragging testcases and scripts onto a canvas,
 * connecting them visually, and linking data between blocks.
 */

import React, { useCallback, DragEvent, useState } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  BackgroundVariant,
  ConnectionMode,
} from 'reactflow';
import 'reactflow/dist/style.css';
import {
  Box,
  Typography,
  Button,
  AppBar,
  Toolbar,
} from '@mui/material';
import {
  Save as SaveIcon,
  PlayArrow as ExecuteIcon,
} from '@mui/icons-material';
import { CampaignBuilderProvider, useCampaignBuilder } from '../contexts/campaign/CampaignBuilderContext';
import { CampaignBlock } from '../components/campaign/blocks/CampaignBlock';
import { CampaignToolbox } from '../components/campaign/builder/CampaignToolbox';
import { CampaignNode, CampaignDragData } from '../types/pages/CampaignGraph_Types';
import { useTheme } from '../contexts/ThemeContext';

// Define node types for React Flow
const nodeTypes = {
  start: CampaignBlock,
  success: CampaignBlock,
  failure: CampaignBlock,
  testcase: CampaignBlock,
  script: CampaignBlock,
};

const CampaignBuilderContent: React.FC = () => {
  const { mode: actualMode } = useTheme();
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
        x: event.clientX - reactFlowBounds.left - 140, // Center horizontally (block width ~280)
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
          // TODO: Fetch testcase scriptConfig to populate inputs/outputs
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

  // Handle save
  const handleSave = async () => {
    const success = await saveCampaign();
    if (success) {
      console.log('[@CampaignBuilder] Campaign saved successfully');
      // TODO: Show success toast
    } else {
      console.error('[@CampaignBuilder] Failed to save campaign');
      // TODO: Show error toast
    }
  };

  // Handle execute (TODO)
  const handleExecute = () => {
    console.log('[@CampaignBuilder] Execute campaign:', state);
    // TODO: Convert graph to linear campaign config and execute
  };

  return (
    <Box sx={{ height: '100vh', display: 'flex', flexDirection: 'column', background: actualMode === 'dark' ? '#0f172a' : '#f8f9fa' }}>
      {/* Top App Bar */}
      <AppBar position="static" color="default" elevation={0} sx={{ 
        borderBottom: 1, 
        borderColor: 'divider',
        background: actualMode === 'dark' ? '#1e293b' : '#ffffff',
      }}>
        <Toolbar variant="dense" sx={{ minHeight: '40px', px: 2 }}>
          <Typography variant="h6" sx={{ flex: 1, fontWeight: 600 }}>
            Campaign Builder
            {state.campaign_name && `: ${state.campaign_name}`}
          </Typography>

          <Button
            startIcon={<SaveIcon />}
            onClick={handleSave}
            sx={{ mr: 1 }}
          >
            Save
          </Button>

          <Button
            variant="contained"
            startIcon={<ExecuteIcon />}
            onClick={handleExecute}
            disabled={nodes.length <= 3} // Only START, SUCCESS, FAILURE
          >
            Execute
          </Button>
        </Toolbar>
      </AppBar>

      {/* Main Content Area */}
      <Box sx={{ 
        flex: 1,
        display: 'flex', 
        overflow: 'hidden',
        minHeight: 0,
        position: 'relative',
      }}>
        {/* Left Toolbox */}
        <CampaignToolbox isSidebarOpen={isSidebarOpen} toggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)} actualMode={actualMode} />

        {/* React Flow Canvas */}
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
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            nodeTypes={nodeTypes}
            connectionMode={ConnectionMode.Loose}
            fitView
            attributionPosition="bottom-left"
            style={{ background: actualMode === 'dark' ? '#0f172a' : '#f8f9fa' }}
          >
            <Background 
              variant={BackgroundVariant.Dots} 
              gap={15} 
              size={1}
              color={actualMode === 'dark' ? '#334155' : '#cbd5e1'}
            />
            <Controls
              showInteractive={false}
              position="top-left"
              style={{
                background: actualMode === 'dark' ? '#1e293b' : '#ffffff',
                border: `1px solid ${actualMode === 'dark' ? '#334155' : '#e2e8f0'}`,
                borderRadius: '8px',
                left: isSidebarOpen ? '390px' : '10px',
                transition: 'left 0.3s ease',
              }}
            />
            <MiniMap
              nodeColor={(node) => {
                if (node.id === 'start') return '#2196f3';
                if (node.id === 'success') return '#4caf50';
                if (node.id === 'failure') return '#f44336';
                if (node.type === 'testcase') return '#9c27b0';
                if (node.type === 'script') return '#ff9800';
                return '#9e9e9e';
              }}
              style={{
                background: actualMode === 'dark' ? '#1e293b' : '#ffffff',
                border: `1px solid ${actualMode === 'dark' ? '#334155' : '#ddd'}`,
              }}
              position="bottom-right"
            />
          </ReactFlow>
        </Box>
      </Box>
    </Box>
  );
};

// Main component wrapped in provider
const CampaignBuilder: React.FC = () => {
  return (
    <CampaignBuilderProvider>
      <CampaignBuilderContent />
    </CampaignBuilderProvider>
  );
};

export default CampaignBuilder;

