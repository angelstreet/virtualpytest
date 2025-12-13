/**
 * Navigation Tree Viewer - Embedded ReactFlow viewer for navigation trees
 * 
 * A simplified version of NavigationEditor for embedding in ContentViewer.
 * Shows the navigation tree without headers, panels, or full-page layout.
 */

import React, { useEffect, useMemo, useCallback } from 'react';
import { Box, Typography, CircularProgress } from '@mui/material';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  ReactFlowProvider,
  BackgroundVariant,
  MarkerType,
  ConnectionLineType,
} from 'reactflow';
import 'reactflow/dist/style.css';

import { useTheme } from '@mui/material/styles';
import { AGENT_CHAT_PALETTE as PALETTE } from '../../constants/agentChatTheme';

// Import navigation components and contexts
import { NavigationConfigProvider, useNavigationConfig } from '../../contexts/navigation/NavigationConfigContext';
import { NavigationEditorProvider } from '../../contexts/navigation/NavigationEditorProvider';
import { NavigationStackProvider } from '../../contexts/navigation/NavigationStackContext';
import { NavigationPreviewCacheProvider } from '../../contexts/navigation/NavigationPreviewCacheContext';
import { useNavigationEditor } from '../../hooks/navigation/useNavigationEditor';
import { useUserInterface } from '../../hooks/pages/useUserInterface';

// Import node/edge components from NavigationEditor
import { UINavigationNode } from '../navigation/Navigation_NavigationNode';
import { UIActionNode } from '../navigation/Navigation_ActionNode';
import { NavigationEdgeComponent } from '../navigation/Navigation_NavigationEdge';

// Node types for React Flow
const nodeTypes = {
  screen: UINavigationNode,
  menu: UINavigationNode,
  action: UIActionNode,
  entry: UINavigationNode,
};

const edgeTypes = {
  navigation: NavigationEdgeComponent,
  smoothstep: NavigationEdgeComponent,
};

const defaultEdgeOptions = {
  type: 'navigation',
  animated: false,
  style: { strokeWidth: 2, stroke: '#b1b1b7' },
  markerEnd: {
    type: MarkerType.ArrowClosed,
    width: 20,
    height: 20,
    color: '#b1b1b7',
  },
};

const proOptions = { hideAttribution: true };

interface NavigationTreeViewerProps {
  userInterfaceName: string;
  treeId?: string;
  nodeId?: string;
  readOnly?: boolean;
}

// Inner content component that uses the hooks
const NavigationTreeViewerContent: React.FC<NavigationTreeViewerProps> = ({
  userInterfaceName,
  treeId,
  nodeId,
  readOnly = true,
}) => {
  const theme = useTheme();
  const isDarkMode = theme.palette.mode === 'dark';
  
  const { setActualTreeId } = useNavigationConfig();
  const { getUserInterfaceByName } = useUserInterface();
  
  const {
    nodes,
    edges,
    isLoadingInterface,
    error,
    loadTreeByUserInterface,
    setUserInterfaceFromProps,
    setReactFlowInstance,
  } = useNavigationEditor();

  // Load tree by userinterface name
  useEffect(() => {
    const loadTree = async () => {
      if (!userInterfaceName) return;
      
      try {
        console.log(`[NavigationTreeViewer] Loading tree for: ${userInterfaceName}`);
        const resolvedInterface = await getUserInterfaceByName(userInterfaceName);
        setUserInterfaceFromProps(resolvedInterface);
        
        const result = await loadTreeByUserInterface(resolvedInterface.id);
        if (result?.tree?.id) {
          setActualTreeId(result.tree.id);
        }
      } catch (err) {
        console.error('[NavigationTreeViewer] Failed to load tree:', err);
      }
    };
    
    loadTree();
  }, [userInterfaceName]);

  // MiniMap node color
  const miniMapNodeColor = useCallback((node: any) => {
    switch (node.data?.type) {
      case 'screen': return '#3b82f6';
      case 'dialog': return '#8b5cf6';
      case 'popup': return '#f59e0b';
      case 'overlay': return '#10b981';
      case 'menu': return '#ffc107';
      case 'entry': return '#ef4444';
      default: return '#6b7280';
    }
  }, []);

  const miniMapStyle = useMemo(() => ({
    backgroundColor: isDarkMode ? '#1f2937' : '#ffffff',
    border: `1px solid ${isDarkMode ? '#374151' : '#e5e7eb'}`,
    borderRadius: '4px',
  }), [isDarkMode]);

  if (isLoadingInterface) {
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
          Loading navigation tree...
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
          No navigation tree found
        </Typography>
        <Typography variant="caption" color="text.disabled">
          {userInterfaceName}
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ flex: 1, width: '100%', height: '100%' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        defaultEdgeOptions={defaultEdgeOptions}
        connectionLineType={ConnectionLineType.SmoothStep}
        onInit={(instance) => {
          setReactFlowInstance(instance);
          // Fit view on init
          setTimeout(() => instance.fitView({ padding: 0.2 }), 100);
        }}
        nodesDraggable={!readOnly}
        nodesConnectable={!readOnly}
        elementsSelectable={true}
        panOnDrag={true}
        zoomOnScroll={true}
        zoomOnPinch={true}
        proOptions={proOptions}
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
export const NavigationTreeViewer: React.FC<NavigationTreeViewerProps> = (props) => {
  if (!props.userInterfaceName) {
    return (
      <Box sx={{ 
        flex: 1, 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center',
        p: 4,
      }}>
        <Typography color="text.secondary">
          No user interface specified
        </Typography>
      </Box>
    );
  }

  return (
    <ReactFlowProvider>
      <NavigationConfigProvider>
        <NavigationPreviewCacheProvider>
          <NavigationEditorProvider>
            <NavigationStackProvider>
              <NavigationTreeViewerContent {...props} />
            </NavigationStackProvider>
          </NavigationEditorProvider>
        </NavigationPreviewCacheProvider>
      </NavigationConfigProvider>
    </ReactFlowProvider>
  );
};

export default NavigationTreeViewer;

