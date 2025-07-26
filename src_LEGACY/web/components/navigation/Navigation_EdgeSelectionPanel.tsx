import { Close as CloseIcon } from '@mui/icons-material';
import { Box, Typography, Button, IconButton, Paper, LinearProgress } from '@mui/material';
import React, { useEffect, useMemo } from 'react';
import { useReactFlow } from 'reactflow';

import { useEdge } from '../../hooks/navigation/useEdge';
import { Host } from '../../types/common/Host_Types';
import { UINavigationEdge, EdgeForm } from '../../types/pages/Navigation_Types';
import { getZIndex } from '../../utils/zIndexUtils';

interface EdgeSelectionPanelProps {
  selectedEdge: UINavigationEdge;
  onClose: () => void;
  onEdit: () => void;
  onDelete: () => void;
  setEdgeForm: React.Dispatch<React.SetStateAction<EdgeForm>>;
  setIsEdgeDialogOpen: (open: boolean) => void;

  // Device control props
  isControlActive?: boolean;
  selectedHost?: Host; // Make optional to fix regression

  // Positioning for multiple panels
  panelIndex?: number;

  // Add props for passing labels to the edit dialog
  onEditWithLabels?: (fromLabel: string, toLabel: string) => void;
}

export const EdgeSelectionPanel: React.FC<EdgeSelectionPanelProps> = React.memo(
  ({
    selectedEdge,
    onClose,
    onEdit: _onEdit,
    onDelete,
    setEdgeForm,
    setIsEdgeDialogOpen,

    isControlActive = false,
    selectedHost,
    panelIndex = 0,
    onEditWithLabels,
  }) => {
    const { getNodes } = useReactFlow();

    // Get actual node labels for from/to display
    const { fromLabel, toLabel } = useMemo(() => {
      const nodes = getNodes();
      const sourceNode = nodes.find((node) => node.id === selectedEdge.source);
      const targetNode = nodes.find((node) => node.id === selectedEdge.target);

      return {
        fromLabel: sourceNode?.data?.label || selectedEdge.source,
        toLabel: targetNode?.data?.label || selectedEdge.target,
      };
    }, [getNodes, selectedEdge.source, selectedEdge.target]);

    // Use the consolidated edge hook
    const edgeHook = useEdge({
      selectedHost: selectedHost || null,
      isControlActive,
    });

    // Get actions and retry actions using hook functions
    const actions = edgeHook.getActionsFromEdge(selectedEdge);
    const retryActions = edgeHook.getRetryActionsFromEdge(selectedEdge);
    const hasActions = actions.length > 0;
    const hasRetryActions = retryActions.length > 0;
    const canRunActions = edgeHook.canRunActions(selectedEdge);

    // Memoize the clearResults function to avoid recreating it on every render
    const clearResults = useMemo(() => edgeHook.clearResults, [edgeHook.clearResults]);

    // Clear run results when edge selection changes
    useEffect(() => {
      clearResults();
    }, [selectedEdge.id, clearResults]);

    // Check if edge can be deleted using hook function
    const isProtectedEdge = edgeHook.isProtectedEdge(selectedEdge);

    // Get metrics from edge data (loaded once with tree)
    const edgeMetrics = useMemo(() => {
      return selectedEdge.data?.metrics || { volume: 0, success_rate: 0.0, avg_execution_time: 0 };
    }, [selectedEdge.data?.metrics]);

    // Format success rate as percentage
    const successRateText = useMemo(() => {
      if (edgeMetrics.volume === 0) return 'No data';
      return `${Math.round(edgeMetrics.success_rate * 100)}%`;
    }, [edgeMetrics.volume, edgeMetrics.success_rate]);

    // Get success rate color
    const successRateColor = useMemo(() => {
      if (edgeMetrics.volume === 0) return '#666';
      if (edgeMetrics.success_rate >= 0.7) return '#4caf50'; // Green for 70%+
      if (edgeMetrics.success_rate >= 0.5) return '#ff9800'; // Orange for 50-70%
      return '#f44336'; // Red for <50%
    }, [edgeMetrics.volume, edgeMetrics.success_rate]);

    const handleEdit = () => {
      // Create edge form using hook function
      const edgeForm = edgeHook.createEdgeForm(selectedEdge);
      setEdgeForm(edgeForm);
      setIsEdgeDialogOpen(true);
      onClose(); // Close the selection panel when opening the edit dialog
      // Note: Dependency check happens in EdgeEditDialog when saving
      // If no dependencies are found, the edge will be saved directly
      if (onEditWithLabels) {
        onEditWithLabels(fromLabel, toLabel);
      }
    };

    // Execute all edge actions using hook function
    const handleRunActions = async () => {
      await edgeHook.executeEdgeActions(selectedEdge);
    };

    return (
      <Paper
        sx={{
          position: 'absolute',
          top: 16,
          right: 16 + panelIndex * 380, // Position panels side by side horizontally
          width: 360,
          p: 1.5,
          zIndex: getZIndex('NAVIGATION_EDGE_PANEL'),
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <Box>
          <Box
            sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Typography variant="h6" sx={{ margin: 0, fontSize: '1rem' }}>
                Edge Selection
              </Typography>
              {/* Show success rate percentage with color coding */}
              <Typography
                variant="caption"
                sx={{
                  fontSize: '0.75rem',
                  fontWeight: 'bold',
                  color: successRateColor,
                  padding: '2px 6px',
                  borderRadius: '4px',
                  backgroundColor: 'rgba(255,255,255,0.1)',
                }}
              >
                {successRateText}
              </Typography>
              {/* Show average time in seconds */}
              <Typography
                variant="caption"
                sx={{
                  fontSize: '0.75rem',
                  fontWeight: 'bold',
                  color: '#666',
                  padding: '2px 6px',
                  borderRadius: '4px',
                  backgroundColor: 'rgba(255,255,255,0.1)',
                }}
              >
                {edgeMetrics.avg_execution_time > 0
                  ? `${(edgeMetrics.avg_execution_time / 1000).toFixed(1)}s`
                  : '0s'}
              </Typography>
              {/* Show execution count */}
              <Typography
                variant="caption"
                sx={{
                  fontSize: '0.75rem',
                  fontWeight: 'bold',
                  color: '#666',
                  padding: '2px 6px',
                  borderRadius: '4px',
                  backgroundColor: 'rgba(255,255,255,0.1)',
                }}
              >
                #{edgeMetrics.volume}
              </Typography>
            </Box>
            <IconButton
              size="small"
              onClick={(e) => {
                e.stopPropagation(); // Prevent event from bubbling to ReactFlow pane
                onClose();
              }}
              sx={{ p: 0.25 }}
            >
              <CloseIcon fontSize="small" />
            </IconButton>
          </Box>

          {/* Show From/To information with actual node labels */}
          <Box sx={{ mb: 1, display: 'flex', alignItems: 'center', gap: 1 }}>
            <Typography
              variant="body2"
              sx={{ fontSize: '0.8rem', fontWeight: 'bold', color: '#1976d2' }}
            >
              {fromLabel}
            </Typography>
            <Typography variant="body1" sx={{ fontSize: '1rem' }}>
              →
            </Typography>
            <Typography
              variant="body2"
              sx={{ fontSize: '0.8rem', fontWeight: 'bold', color: '#4caf50' }}
            >
              {toLabel}
            </Typography>
          </Box>

          {/* Show main actions list */}
          {actions.length > 0 && (
            <Box sx={{ mb: 1 }}>
              <Typography
                variant="caption"
                sx={{ fontWeight: 'bold', fontSize: '0.7rem', mb: 0.5, display: 'block' }}
              >
                Main Actions:
              </Typography>
              {actions.map((action, index) => {
                const formatActionDisplay = (action: any) => {
                  if (!action.command) return 'No action selected';
                  const commandDisplay = action.command.replace(/_/g, ' ').trim();
                  const params = action.params || {};
                  const paramParts = [];
                  switch (action.command) {
                    case 'press_key':
                      if (params.key) paramParts.push(`"${params.key}"`);
                      break;
                    case 'input_text':
                      if (params.text) paramParts.push(`"${params.text}"`);
                      break;
                    case 'click_element':
                      if (params.element_id) paramParts.push(`"${params.element_id}"`);
                      break;
                    case 'tap_coordinates':
                      if (params.x !== undefined && params.y !== undefined) {
                        paramParts.push(`(${params.x}, ${params.y})`);
                      }
                      break;
                    case 'swipe':
                      if (params.direction) paramParts.push(`"${params.direction}"`);
                      break;
                    case 'launch_app':
                    case 'close_app':
                      if (params.package) paramParts.push(`"${params.package}"`);
                      break;
                    case 'wait':
                      if (params.duration) paramParts.push(`${params.duration}s`);
                      break;
                    case 'scroll':
                      if (params.direction) paramParts.push(`"${params.direction}"`);
                      if (params.amount) paramParts.push(`${params.amount}x`);
                      break;
                  }
                  if (params.wait_time && params.wait_time !== 500) {
                    paramParts.push(`wait: ${params.wait_time}ms`);
                  }
                  const paramDisplay = paramParts.length > 0 ? ` → ${paramParts.join(', ')}` : '';
                  return `${commandDisplay}${paramDisplay}`;
                };

                return (
                  <Typography key={index} variant="body2" sx={{ fontSize: '0.75rem', mb: 0.3 }}>
                    {index + 1}. {formatActionDisplay(action)}
                  </Typography>
                );
              })}
            </Box>
          )}

          {/* Show retry actions list */}
          {hasRetryActions && (
            <Box sx={{ mb: 1 }}>
              <Typography
                variant="caption"
                sx={{
                  fontWeight: 'bold',
                  fontSize: '0.7rem',
                  mb: 0.5,
                  display: 'block',
                  color: 'warning.main',
                }}
              >
                Retry Actions (if main actions fail):
              </Typography>
              {retryActions.map((action, index) => {
                const formatActionDisplay = (action: any) => {
                  if (!action.command) return 'No action selected';
                  const commandDisplay = action.command.replace(/_/g, ' ').trim();
                  const params = action.params || {};
                  const paramParts = [];
                  switch (action.command) {
                    case 'press_key':
                      if (params.key) paramParts.push(`"${params.key}"`);
                      break;
                    case 'input_text':
                      if (params.text) paramParts.push(`"${params.text}"`);
                      break;
                    case 'click_element':
                      if (params.element_id) paramParts.push(`"${params.element_id}"`);
                      break;
                    case 'tap_coordinates':
                      if (params.x !== undefined && params.y !== undefined) {
                        paramParts.push(`(${params.x}, ${params.y})`);
                      }
                      break;
                    case 'swipe':
                      if (params.direction) paramParts.push(`"${params.direction}"`);
                      break;
                    case 'launch_app':
                    case 'close_app':
                      if (params.package) paramParts.push(`"${params.package}"`);
                      break;
                    case 'wait':
                      if (params.duration) paramParts.push(`${params.duration}s`);
                      break;
                    case 'scroll':
                      if (params.direction) paramParts.push(`"${params.direction}"`);
                      if (params.amount) paramParts.push(`${params.amount}x`);
                      break;
                  }
                  if (params.wait_time && params.wait_time !== 500) {
                    paramParts.push(`wait: ${params.wait_time}ms`);
                  }
                  const paramDisplay = paramParts.length > 0 ? ` → ${paramParts.join(', ')}` : '';
                  return `${commandDisplay}${paramDisplay}`;
                };

                return (
                  <Typography
                    key={`retry-${index}`}
                    variant="body2"
                    sx={{ fontSize: '0.75rem', mb: 0.3, color: 'warning.main' }}
                  >
                    R{index + 1}. {formatActionDisplay(action)}
                  </Typography>
                );
              })}
            </Box>
          )}

          <Box sx={{ mt: 0.5, display: 'flex', flexDirection: 'column', gap: 0.5 }}>
            {/* Edit and Delete buttons */}
            <Box sx={{ display: 'flex', gap: 0.5 }}>
              <Button
                size="small"
                variant="outlined"
                sx={{ fontSize: '0.75rem', px: 1, flex: 1 }}
                onClick={handleEdit}
                disabled={!isControlActive || !selectedHost}
                title={
                  !isControlActive || !selectedHost ? 'Device control required to edit edges' : ''
                }
              >
                Edit
              </Button>
              {/* Only show delete button if not a protected edge */}
              {!isProtectedEdge && (
                <Button
                  size="small"
                  variant="outlined"
                  color="error"
                  sx={{ fontSize: '0.75rem', px: 1, flex: 1 }}
                  onClick={onDelete}
                >
                  Delete
                </Button>
              )}
            </Box>

            {/* Run button - only shown when actions exist */}
            {hasActions && (
              <Button
                size="small"
                variant="contained"
                sx={{ fontSize: '0.75rem', px: 1 }}
                onClick={handleRunActions}
                disabled={!canRunActions}
                title={
                  !isControlActive || !selectedHost ? 'Device control required to test actions' : ''
                }
              >
                {edgeHook.actionHook.loading ? 'Running...' : 'Run'}
              </Button>
            )}

            {/* Linear Progress - shown when running */}
            {edgeHook.actionHook.loading && <LinearProgress sx={{ mt: 0.5, borderRadius: 1 }} />}

            {/* Run result display - with scrolling */}
            {edgeHook.runResult && (
              <Box
                sx={{
                  mt: 0.5,
                  p: 0.5,
                  bgcolor: edgeHook.runResult.includes('❌ OVERALL RESULT: FAILED')
                    ? 'error.light'
                    : edgeHook.runResult.includes('✅ OVERALL RESULT: SUCCESS')
                      ? 'success.light'
                      : edgeHook.runResult.includes('❌') && !edgeHook.runResult.includes('✅')
                        ? 'error.light'
                        : edgeHook.runResult.includes('⚠️')
                          ? 'warning.light'
                          : 'success.light',
                  borderRadius: 0.5,
                  maxHeight: '150px', // Limit height to enable scrolling
                  overflow: 'auto', // Enable scrolling
                  border: '1px solid rgba(0, 0, 0, 0.12)', // Add subtle border
                }}
              >
                <Typography
                  variant="caption"
                  sx={{
                    fontFamily: 'monospace',
                    whiteSpace: 'pre-line',
                    fontSize: '0.7rem', // Slightly smaller font for compactness
                    lineHeight: 1.2, // Tighter line spacing
                  }}
                >
                  {edgeHook.formatRunResult(edgeHook.runResult)}
                </Typography>
              </Box>
            )}
          </Box>
        </Box>
      </Paper>
    );
  },
);
