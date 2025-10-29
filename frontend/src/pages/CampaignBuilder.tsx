/**
 * Campaign Builder Page
 * 
 * Visual campaign builder with React Flow canvas.
 * Allows users to create campaigns by dragging testcases and scripts onto a canvas,
 * connecting them visually, and linking data between blocks.
 * 
 * NOTE: This uses the EXACT same layout structure as TestCaseBuilder for consistency
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
  Button,
  Typography,
  IconButton,
} from '@mui/material';
import {
  Save as SaveIcon,
  PlayArrow as ExecuteIcon,
  ChevronLeft as ChevronLeftIcon,
  ChevronRight as ChevronRightIcon,
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
  const { mode } = useTheme();
  const actualMode = mode === 'system' ? 'light' : mode;
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
      {/* Header - EXACT same structure as TestCaseBuilderHeader */}
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
        {/* Title */}
        <Box sx={{ display: 'flex', alignItems: 'center', minWidth: 0, flex: '0 0 260px', gap: 1 }}>
          <Typography variant="h6" fontWeight="bold" sx={{ whiteSpace: 'nowrap' }}>
            Campaign Builder
          </Typography>
          {state.campaign_name && (
            <>
              <Typography variant="h6" sx={{ color: 'text.disabled' }}>
                •
              </Typography>
              <Typography 
                variant="h6" 
                sx={{ 
                  fontWeight: 600,
                  color: 'primary.main',
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  maxWidth: 200,
                }}
              >
                {state.campaign_name}
              </Typography>
            </>
          )}
        </Box>
        
        {/* Action Buttons */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <Button 
            size="small" 
            variant="outlined" 
            startIcon={<SaveIcon />} 
            onClick={handleSave}
          >
            Save
          </Button>
          
          <Button
            size="small"
            variant="contained"
            startIcon={<ExecuteIcon />}
            onClick={handleExecute}
            disabled={nodes.length <= 3}
          >
            Execute
          </Button>
        </Box>
      </Box>

      {/* Main Container - EXACT same structure as TestCaseBuilder */}
      <Box sx={{ 
        flex: 1,
        display: 'flex', 
        overflow: 'hidden',
        minHeight: 0,
        position: 'relative',
      }}>
        {/* Sidebar - EXACT same structure as TestCaseBuilderSidebar */}
        <Box
          sx={{
            position: 'absolute',
            left: 0,
            top: 0,
            bottom: 0,
            width: isSidebarOpen ? '280px' : '0px',
            transition: 'width 0.3s ease',
            overflow: 'hidden',
            borderRight: isSidebarOpen ? 1 : 0,
            borderColor: 'divider',
            display: 'flex',
            flexDirection: 'column',
            background: actualMode === 'dark' ? '#0f172a' : '#f8f9fa',
            zIndex: 5,
          }}
        >
          {isSidebarOpen && (
            <>
              {/* Sidebar Header */}
              <Box
                sx={{
                  px: 2,
                  py: 1.5,
                  height: '40px',
                  borderBottom: 1,
                  borderColor: 'divider',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  background: actualMode === 'dark' ? '#1e293b' : '#ffffff',
                }}
              >
                <Typography variant="subtitle1" fontWeight="bold">
                  Toolbox
                </Typography>
                <IconButton
                  size="small"
                  onClick={() => setIsSidebarOpen(false)}
                  sx={{
                    color: 'text.secondary',
                    '&:hover': { color: 'primary.main' },
                  }}
                >
                  <ChevronLeftIcon />
                </IconButton>
              </Box>
              
              {/* Sidebar Content */}
              <Box sx={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
                <CampaignToolbox />
              </Box>
            </>
          )}
        </Box>
        
        {/* Toggle Button (when sidebar is closed) */}
        {!isSidebarOpen && (
          <Box
            sx={{
              position: 'absolute',
              left: 0,
              top: '140px',
              zIndex: 10,
            }}
          >
            <IconButton
              onClick={() => setIsSidebarOpen(true)}
              sx={{
                borderRadius: '0 8px 8px 0',
                background: actualMode === 'dark' ? '#1e293b' : '#ffffff',
                border: 1,
                borderLeft: 0,
                borderColor: 'divider',
                '&:hover': {
                  background: actualMode === 'dark' ? '#334155' : '#f1f5f9',
                },
              }}
            >
              <ChevronRightIcon />
            </IconButton>
          </Box>
        )}

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
                left: isSidebarOpen ? '290px' : '10px',
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
