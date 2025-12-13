/**
 * Test Case Flow Viewer - Embedded ReactFlow viewer for test cases
 * 
 * A simplified version of TestCaseBuilder for embedding in ContentViewer.
 * Shows the test case flow without headers, sidebars, or full-page layout.
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
} from 'reactflow';
import 'reactflow/dist/style.css';

import { useTheme } from '@mui/material/styles';
import { AGENT_CHAT_PALETTE as PALETTE } from '../../constants/agentChatTheme';

// Import test case contexts and hooks
import { TestCaseBuilderProvider, useTestCaseBuilder } from '../../contexts/testcase/TestCaseBuilderContext';
import { NavigationEditorProvider } from '../../contexts/navigation/NavigationEditorProvider';
import { NavigationConfigProvider } from '../../contexts/navigation/NavigationConfigContext';
import { useTestCaseBuilderPage } from '../../hooks/pages/useTestCaseBuilderPage';

// Import block components from TestCaseBuilder
import { StartBlock } from '../testcase/blocks/StartBlock';
import { SuccessBlock } from '../testcase/blocks/SuccessBlock';
import { FailureBlock } from '../testcase/blocks/FailureBlock';
import { UniversalBlock } from '../testcase/blocks/UniversalBlock';
import { ApiCallBlock } from '../testcase/blocks/ApiCallBlock';
import { SuccessEdge } from '../testcase/edges/SuccessEdge';
import { FailureEdge } from '../testcase/edges/FailureEdge';
import { DataEdge } from '../testcase/edges/DataEdge';

// Node types for React Flow
const NODE_TYPES = {
  start: StartBlock,
  success: SuccessBlock,
  failure: FailureBlock,
  action: UniversalBlock,
  verification: UniversalBlock,
  navigation: UniversalBlock,
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
  custom_code: UniversalBlock,
  common_operation: UniversalBlock,
  evaluate_condition: UniversalBlock,
  api_call: ApiCallBlock,
};

// Edge types for React Flow
const EDGE_TYPES = {
  success: SuccessEdge,
  failure: FailureEdge,
  true: SuccessEdge,
  false: FailureEdge,
  complete: SuccessEdge,
  break: FailureEdge,
  data: DataEdge,
};

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

interface TestCaseFlowViewerProps {
  testcaseId?: string;
  readOnly?: boolean;
}

// Inner content component that uses the hooks
const TestCaseFlowViewerContent: React.FC<TestCaseFlowViewerProps> = ({
  testcaseId,
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

  // Use the test case builder hook
  const hookData = useTestCaseBuilderPage();
  const { nodes, edges, handleLoad, testcaseName } = hookData;

  // Load test case by ID
  useEffect(() => {
    const loadTestCase = async () => {
      if (!testcaseId) {
        setIsLoading(false);
        return;
      }

      try {
        console.log(`[TestCaseFlowViewer] Loading test case: ${testcaseId}`);
        setIsLoading(true);
        setError(null);
        await handleLoad(testcaseId);
        setIsLoading(false);
      } catch (err) {
        console.error('[TestCaseFlowViewer] Failed to load test case:', err);
        setError(err instanceof Error ? err.message : 'Failed to load test case');
        setIsLoading(false);
      }
    };

    loadTestCase();
  }, [testcaseId, handleLoad]);

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
      case 'action': return '#3b82f6';
      case 'verification': return '#8b5cf6';
      case 'navigation': return '#f59e0b';
      case 'condition': return '#ec4899';
      case 'loop': return '#06b6d4';
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
          Loading test case...
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
          No test case loaded
        </Typography>
        {testcaseId && (
          <Typography variant="caption" color="text.disabled">
            ID: {testcaseId}
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
        edges={edges}
        nodeTypes={NODE_TYPES}
        edgeTypes={EDGE_TYPES}
        defaultEdgeOptions={defaultEdgeOptions}
        onInit={setReactFlowInstance}
        nodesDraggable={!readOnly}
        nodesConnectable={!readOnly}
        elementsSelectable={true}
        panOnDrag={true}
        zoomOnScroll={true}
        zoomOnPinch={true}
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
export const TestCaseFlowViewer: React.FC<TestCaseFlowViewerProps> = (props) => {
  return (
    <ReactFlowProvider>
      <NavigationConfigProvider>
        <NavigationEditorProvider>
          <TestCaseBuilderProvider>
            <TestCaseFlowViewerContent {...props} />
          </TestCaseBuilderProvider>
        </NavigationEditorProvider>
      </NavigationConfigProvider>
    </ReactFlowProvider>
  );
};

export default TestCaseFlowViewer;

