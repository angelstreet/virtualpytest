/**
 * Campaign Flow Viewer - Embedded ReactFlow viewer for campaigns
 *
 * A simplified version of CampaignBuilder for embedding in ContentViewer.
 * Shows the campaign flow without headers, sidebars, or full-page layout.
 */

import React, { useEffect, useMemo, useCallback, useRef, useState } from 'react';
import { Box, Typography, CircularProgress } from '@mui/material';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  ReactFlowProvider,
  BackgroundVariant,
  MarkerType,
  ConnectionMode,
} from 'reactflow';
import 'reactflow/dist/style.css';

import { useTheme } from '@mui/material/styles';
import { AGENT_CHAT_PALETTE as PALETTE } from '../../constants/agentChatTheme';

// Import campaign contexts and hooks
import { CampaignBuilderProvider, useCampaignBuilder } from '../../contexts/campaign/CampaignBuilderContext';
import { NavigationEditorProvider } from '../../contexts/navigation/NavigationEditorProvider';
import { NavigationConfigProvider } from '../../contexts/navigation/NavigationConfigContext';

// Import campaign block components
import { StartBlock } from '../testcase/blocks/StartBlock';
import { SuccessBlock } from '../testcase/blocks/SuccessBlock';
import { FailureBlock } from '../testcase/blocks/FailureBlock';
import { CampaignBlock } from '../campaign/blocks/CampaignBlock';
import { SuccessEdge } from '../testcase/edges/SuccessEdge';
import { FailureEdge } from '../testcase/edges/FailureEdge';

// Node types for React Flow
const nodeTypes = {
  start: StartBlock,
  success: SuccessBlock,
  failure: FailureBlock,
  testcase: CampaignBlock,
  script: CampaignBlock,
};

// Edge types for React Flow
const edgeTypes = {
  success: SuccessEdge,
  failure: FailureEdge,
  control: SuccessEdge, // Campaign uses 'control' type for flow edges
};

// Default edge options - matching CampaignBuilder
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

// Hide attribution style
const hideAttributionStyle = `
  .react-flow__panel.react-flow__attribution {
    display: none !important;
  }
`;

interface CampaignFlowViewerProps {
  campaignId?: string;
  readOnly?: boolean;
}

// Inner content component that uses the hooks
const CampaignFlowViewerContent: React.FC<CampaignFlowViewerProps> = ({
  campaignId,
  readOnly = true,
}) => {
  const theme = useTheme();
  const isDarkMode = theme.palette.mode === 'dark';
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const [reactFlowInstance, setReactFlowInstance] = useState<any>(null);

  // Inject styles to hide React Flow attribution
  useEffect(() => {
    const styleTag = document.createElement('style');
    styleTag.innerHTML = hideAttributionStyle;
    document.head.appendChild(styleTag);
    return () => {
      document.head.removeChild(styleTag);
    };
  }, []);

  // Use the campaign builder hook
  const {
    nodes,
    edges,
    state,
    loadCampaign,
  } = useCampaignBuilder();

  // Load campaign by ID
  useEffect(() => {
    const loadCampaignData = async () => {
      if (!campaignId) {
        setIsLoading(false);
        return;
      }

      try {
        console.log(`[CampaignFlowViewer] Loading campaign: ${campaignId}`);
        setIsLoading(true);
        setError(null);
        await loadCampaign(campaignId);
        setIsLoading(false);
      } catch (err) {
        console.error('[CampaignFlowViewer] Failed to load campaign:', err);
        setError(err instanceof Error ? err.message : 'Failed to load campaign');
        setIsLoading(false);
      }
    };

    loadCampaignData();
  }, [campaignId, loadCampaign]);

  // Fit view when instance is ready and nodes change
  useEffect(() => {
    if (reactFlowInstance && nodes.length > 0) {
      setTimeout(() => {
        reactFlowInstance.fitView({ padding: 0.2, duration: 300 });
      }, 100);
    }
  }, [reactFlowInstance, nodes.length]);

  // MiniMap node color
  const miniMapNodeColor = useCallback((node: any) => {
    switch (node.type) {
      case 'start': return '#22c55e';
      case 'success': return '#22c55e';
      case 'failure': return '#ef4444';
      case 'testcase': return '#3b82f6';
      case 'script': return '#8b5cf6';
      default: return '#6b7280';
    }
  }, []);

  const miniMapStyle = useMemo(() => ({
    backgroundColor: isDarkMode ? '#1f2937' : '#ffffff',
    border: `1px solid ${isDarkMode ? '#374151' : '#e5e7eb'}`,
    borderRadius: '4px',
  }), [isDarkMode]);

  if (isLoading) {
    return (
      <Box sx={{
        flex: 1,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexDirection: 'column',
        gap: 2,
      }}>
        <CircularProgress size={40} sx={{ color: PALETTE.accent }} />
        <Typography variant="body2" color="text.secondary">
          Loading campaign...
        </Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{
        flex: 1,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        p: 4,
      }}>
        <Typography color="error">{error}</Typography>
      </Box>
    );
  }

  if (nodes.length === 0) {
    return (
      <Box sx={{
        flex: 1,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexDirection: 'column',
        gap: 1,
        p: 4,
      }}>
        <Typography variant="body1" color="text.secondary">
          No campaign loaded
        </Typography>
        {campaignId && (
          <Typography variant="caption" color="text.disabled">
            ID: {campaignId}
          </Typography>
        )}
        {state.campaign_name && (
          <Typography variant="caption" color="text.disabled">
            Name: {state.campaign_name}
          </Typography>
        )}
      </Box>
    );
  }

  return (
    <Box
      ref={reactFlowWrapper}
      sx={{ flex: 1, width: '100%', height: '100%' }}
    >
      <ReactFlow
        nodes={nodes}
        edges={edges as any}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        defaultEdgeOptions={defaultEdgeOptions}
        onInit={setReactFlowInstance}
        nodesDraggable={!readOnly}
        nodesConnectable={!readOnly}
        elementsSelectable={true}
        panOnDrag={true}
        zoomOnScroll={true}
        zoomOnPinch={true}
        connectionMode={ConnectionMode.Loose}
        fitView
      >
        <Background variant={BackgroundVariant.Dots} gap={15} size={1} />
        <Controls position="top-left" showInteractive={!readOnly} />
        <MiniMap
          style={miniMapStyle}
          nodeColor={miniMapNodeColor}
          maskColor="rgba(255, 255, 255, 0.2)"
          pannable
          zoomable
          position="bottom-right"
        />
      </ReactFlow>
    </Box>
  );
};

// Main component with providers
export const CampaignFlowViewer: React.FC<CampaignFlowViewerProps> = (props) => {
  return (
    <ReactFlowProvider>
      <NavigationConfigProvider>
        <NavigationEditorProvider>
          <CampaignBuilderProvider>
            <CampaignFlowViewerContent {...props} />
          </CampaignBuilderProvider>
        </NavigationEditorProvider>
      </NavigationConfigProvider>
    </ReactFlowProvider>
  );
};

export default CampaignFlowViewer;

