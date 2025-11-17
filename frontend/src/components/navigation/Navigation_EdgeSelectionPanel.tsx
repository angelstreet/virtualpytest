import { Close as CloseIcon } from '@mui/icons-material';
import { Box, Typography, Button, IconButton, Paper, LinearProgress, Alert } from '@mui/material';
import React, { useEffect, useMemo } from 'react';
import { useReactFlow } from 'reactflow';

import { useEdge } from '../../hooks/navigation/useEdge';
import { useValidationColors } from '../../hooks/validation/useValidationColors';
import { Host } from '../../types/common/Host_Types';
import { UINavigationEdge, EdgeForm } from '../../types/pages/Navigation_Types';
import { MetricData } from '../../types/navigation/Metrics_Types';
import { getZIndex } from '../../utils/zIndexUtils';
import { findSiblingWithActions } from '../../utils/conditionalEdgeUtils';

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
  selectedDeviceId?: string; // Add selectedDeviceId prop

  // Positioning for multiple panels
  panelIndex?: number;

  // Add props for passing labels to the edit dialog
  onEditWithLabels?: (fromLabel: string, toLabel: string) => void;
  
  // Current edge form state (for running updated actions)
  currentEdgeForm?: EdgeForm | null;

  // NEW: Specific action set to display (if provided, use this instead of extracting from edge)
  actionSet?: any;
  // Metrics props - passed from NavigationEditor
  edgeMetrics?: MetricData | null;
  // Tree ID for navigation context
  treeId?: string | null;
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
    selectedDeviceId,
    panelIndex = 0,
    onEditWithLabels,
    actionSet, // NEW: specific action set to display
    edgeMetrics,
    treeId,
  }) => {
    const { getNodes, getEdges } = useReactFlow();

    // Simple hardcoded direction lookup based on action set ID
    const { fromLabel, toLabel } = useMemo(() => {
      const nodes = getNodes();
      const sourceNode = nodes.find((node) => node.id === selectedEdge.source);
      const targetNode = nodes.find((node) => node.id === selectedEdge.target);
      
      const sourceLabel = sourceNode?.data?.label || selectedEdge.source;
      const targetLabel = targetNode?.data?.label || selectedEdge.target;

      if (!actionSet?.id) {
        return { fromLabel: sourceLabel, toLabel: targetLabel };
      }

      // Simple parsing: action set ID is always "from_to_to"
      if (actionSet.id.includes('_to_')) {
        const [fromLabel, toLabel] = actionSet.id.split('_to_');
        return { fromLabel, toLabel };
      }

      return { fromLabel: sourceLabel, toLabel: targetLabel };
    }, [getNodes, selectedEdge.source, selectedEdge.target, actionSet]);

    // Check if this specific actionSet is shared with other edges (conditional edge)
    // IMPORTANT: Only FORWARD action sets (index 0) can be conditional - REVERSE action sets (index 1) are always independent
    const isCurrentActionSetShared = useMemo(() => {
      if (!actionSet?.id) return false;
      
      // Check if this is a reverse action set (index 1) - reverse action sets are NEVER conditional
      const edgeActionSets = selectedEdge.data?.action_sets || [];
      if (edgeActionSets.length >= 2) {
        const reverseActionSet = edgeActionSets[1];
        if (reverseActionSet?.id === actionSet.id) {
          // This is a reverse action set - NEVER conditional
          return false;
        }
      }
      
      // From here, we know it's a forward action set (index 0) - check if conditional
      
      // First check if edge has conditional flag (same as edge component line 25)
      if (selectedEdge.data?.is_conditional || selectedEdge.data?.is_conditional_primary) {
        return true;
      }
      
      // Auto-detect by counting edges (same as edge component lines 28-43)
      const edges = getEdges();
      let shareCount = 0;
      
      edges.forEach((edge: any) => {
        // Only count edges from the SAME SOURCE node
        if (edge.source === selectedEdge.source) {
          const edgeActionSetId = edge.data?.default_action_set_id;
          if (edgeActionSetId === actionSet.id) {
            shareCount++;
          }
        }
      });
      
      // If more than 1 edge from same source has this action_set_id as DEFAULT, it's conditional
      return shareCount > 1;
    }, [actionSet?.id, selectedEdge.source, selectedEdge.data?.is_conditional, selectedEdge.data?.is_conditional_primary, selectedEdge.data?.action_sets, getEdges]);
    
    // Check if this is the primary conditional edge (fully editable without warning)
    const isConditionalPrimary = selectedEdge.data?.is_conditional_primary || false;

    // Use edge hook only for action execution - initialize lazily
    const edgeHook = useEdge({
      selectedHost: selectedHost || null,
      selectedDeviceId: selectedDeviceId || null,
      isControlActive,
      treeId: treeId || null,
    });
    
    // Get validation colors for confidence-based styling
    const { getEdgeColors } = useValidationColors([]);

    // Get actions from actionSet, or from sibling if conditional edge with empty actions
    const { actions, retryActions, failureActions } = useMemo(() => {
      const baseActions = actionSet?.actions || [];
      const baseRetry = actionSet?.retry_actions || [];
      const baseFailure = actionSet?.failure_actions || [];
      
      // If we have actions, use them
      if (baseActions.length > 0) {
        return { actions: baseActions, retryActions: baseRetry, failureActions: baseFailure };
      }
      
      // Empty actions + conditional = look up sibling
      if (isCurrentActionSetShared && actionSet?.id) {
        const sibling = findSiblingWithActions(selectedEdge.id, selectedEdge.source, actionSet.id, getEdges());
        if (sibling?.data?.action_sets?.[0]) {
          const siblingForward = sibling.data.action_sets[0];
          return {
            actions: siblingForward.actions || [],
            retryActions: siblingForward.retry_actions || [],
            failureActions: siblingForward.failure_actions || []
          };
        }
      }
      
      return { actions: baseActions, retryActions: baseRetry, failureActions: baseFailure };
    }, [actionSet, isCurrentActionSetShared, selectedEdge.id, selectedEdge.source, getEdges]);
    
    const hasActions = actions.length > 0;
    const hasRetryActions = retryActions.length > 0;
    const hasFailureActions = failureActions.length > 0;
    
    // Simple canRunActions check using props only
    const canRunActions = isControlActive === true && 
                         selectedHost !== null && 
                         hasActions && 
                         !edgeHook.actionHook.loading;

    // Memoize the clearResults function to avoid recreating it on every render
    const clearResults = useMemo(() => edgeHook.clearResults, [edgeHook.clearResults]);

    // Clear run results when edge selection changes
    useEffect(() => {
      clearResults();
    }, [selectedEdge.id, clearResults]);

    // Check if edge can be deleted using hook function
    const isProtectedEdge = edgeHook.isProtectedEdge(selectedEdge);

    // Get confidence-based colors for the edge
    const edgeColors = useMemo(() => {
      return getEdgeColors(selectedEdge.id, edgeMetrics);
    }, [getEdgeColors, selectedEdge.id, edgeMetrics]);

    // Format metrics display
    const metricsDisplay = useMemo(() => {
      if (!edgeMetrics) {
        return {
          successRateText: 'No data',
          successRateColor: '#666',
          confidenceScore: 0,
          confidenceColor: '#666',
          volumeText: '0',
          timeText: '0s'
        };
      }

      // Success rate should be 0% or 100% for single executions, or actual percentage for multiple
      const successRatePercent = Math.round(edgeMetrics.success_rate * 100);
      
      // Confidence is 0-1, convert to 0-10 scale for display
      const confidenceScore = Math.round(edgeMetrics.confidence * 10); // Round to whole number
      
      return {
        successRateText: `${successRatePercent}%`,
        successRateColor: edgeMetrics.volume === 0 ? '#666' : (successRatePercent >= 90 ? '#22c55e' : successRatePercent >= 70 ? '#f59e0b' : '#ef4444'),
        confidenceScore: confidenceScore,
        confidenceColor: edgeColors.stroke, // Use confidence-based stroke color
        volumeText: `${edgeMetrics.volume}`,
        timeText: edgeMetrics.avg_execution_time > 0 
          ? `${(edgeMetrics.avg_execution_time / 1000).toFixed(1)}s` 
          : '0s'
      };
    }, [edgeMetrics, edgeColors]);

    const handleEdit = () => {
      // Simple edge form creation
      const edgeForm = edgeHook.createEdgeForm(selectedEdge);
      
      // Direction detection based on edge type:
      // - Unidirectional edges (entry/action): always forward (only 1 action set)
      // - Bidirectional edges (screen/menu): detect from action set ID (index 0 = forward, index 1 = reverse)
      if (edgeForm.action_sets?.length === 1) {
        // Unidirectional edge - always forward
        edgeForm.direction = 'forward';
      } else if (actionSet?.id && edgeForm.action_sets?.length >= 2) {
        // Bidirectional edge - detect from action set ID
        edgeForm.direction = actionSet.id === edgeForm.action_sets[0].id ? 'forward' : 'reverse';
      }
      
      setEdgeForm(edgeForm);
      setIsEdgeDialogOpen(true);
      onClose(); // Close the selection panel when opening the edit dialog
      
      if (onEditWithLabels) {
        onEditWithLabels(fromLabel, toLabel);
      }
    };

    // Execute actions using actionSet data
    const handleRunActions = async () => {
      await edgeHook.executeEdgeActions(
        selectedEdge,
        actions,
        retryActions,
        failureActions,
        actionSet?.id
      );
    };

    return (
      <Paper
        sx={{
          position: 'absolute',
          top: 16,
          right: 16 + panelIndex * 380, // Stack panels to the left (higher index = further left)
          width: 360,
          p: 1.5,
          zIndex: getZIndex('NAVIGATION_EDGE_PANEL'),
          borderLeft: `4px solid ${edgeColors.stroke}`, // Show confidence color as border
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <Box>
          <Box
            sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flex: 1 }}>
              <Typography variant="h6" sx={{ margin: 0, fontSize: '1rem' }}>
                Edge Selection
              </Typography>
              
              {/* Success Rate */}
              <Typography
                variant="caption"
                sx={{
                  fontSize: '0.75rem',
                  fontWeight: 'bold',
                  color: metricsDisplay.successRateColor,
                  padding: '2px 6px',
                  borderRadius: '4px',
                  backgroundColor: 'rgba(255,255,255,0.1)',
                }}
              >
                {metricsDisplay.successRateText}
              </Typography>
              
              {/* Duration */}
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
                {metricsDisplay.timeText}
              </Typography>
              
              {/* Volume */}
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
                #{metricsDisplay.volumeText}
              </Typography>
            </Box>
            
            {/* Confidence Score - Larger, on the right */}
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Typography
                variant="h6"
                sx={{
                  fontSize: '1.2rem',
                  fontWeight: 'bold',
                  color: metricsDisplay.confidenceColor,
                  padding: '4px 8px',
                  borderRadius: '6px',
                  backgroundColor: 'rgba(255,255,255,0.1)',
                  border: `1px solid ${metricsDisplay.confidenceColor}`,
                  minWidth: '50px',
                  textAlign: 'center'
                }}
              >
                {metricsDisplay.confidenceScore}
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

          {/* Conditional Edge Warning - Only show for shared action sets (not primary) */}
          {isCurrentActionSetShared && !isConditionalPrimary && (
            <Alert severity="info" icon={false} sx={{ mb: 1, py: 0.5, fontSize: '0.75rem' }}>
              <Typography variant="caption" sx={{ fontSize: '0.7rem', fontWeight: 'bold' }}>
                🔷 Conditional Edge - Editing actions will unlink this edge and make it independent.
              </Typography>
            </Alert>
          )}

          {/* Show main actions list */}
          {(actions?.length || 0) > 0 && (
            <Box sx={{ mb: 1 }}>
              <Typography
                variant="caption"
                sx={{ fontWeight: 'bold', fontSize: '0.7rem', mb: 0.5, display: 'block' }}
              >
                Main Actions:
              </Typography>
              {actions?.map((action: any, index: number) => {
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
                      // Backend uses single parameter: selector (web) or element_id (remote)
                      if (params.selector) paramParts.push(`"${params.selector}"`);
                      if (params.element_id) paramParts.push(`"${params.element_id}"`);
                      break;
                    case 'click_element_by_id':
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
                  if (params.wait_time) {
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
              {retryActions?.map((action: any, index: number) => {
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
                      // Backend uses single parameter: selector (web) or element_id (remote)
                      if (params.selector) paramParts.push(`"${params.selector}"`);
                      if (params.element_id) paramParts.push(`"${params.element_id}"`);
                      break;
                    case 'click_element_by_id':
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
                  if (params.wait_time) {
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

          {/* Show failure actions list */}
          {hasFailureActions && (
            <Box sx={{ mb: 1 }}>
              <Typography
                variant="caption"
                sx={{
                  fontWeight: 'bold',
                  fontSize: '0.7rem',
                  mb: 0.5,
                  display: 'block',
                  color: 'error.main',
                }}
              >
                Failure Actions (if retry actions fail):
              </Typography>
              {failureActions?.map((action: any, index: number) => {
                const formatActionDisplay = (action: any) => {
                  if (!action.command) return 'No action selected';
                  const commandDisplay = action.command.replace(/_/g, ' ').trim();
                  const params = action.params || {};
                  const paramParts = [];
                  switch (action.command) {
                    case 'click_element':
                      // Backend uses single parameter: selector (web) or element_id (remote)
                      if (params.selector) paramParts.push(`"${params.selector}"`);
                      if (params.element_id) paramParts.push(`"${params.element_id}"`);
                      break;
                    case 'input_text':
                      paramParts.push(`text: "${params.text || 'undefined'}"`);
                      break;
                    case 'tap_coordinates':
                      paramParts.push(`x: ${params.x || 0}, y: ${params.y || 0}`);
                      break;
                    case 'launch_app':
                    case 'close_app':
                      paramParts.push(`package: ${params.package || 'undefined'}`);
                      break;
                    case 'remote_key':
                      paramParts.push(`key: ${params.key || 'undefined'}`);
                      break;
                    case 'wait':
                      paramParts.push(`duration: ${params.duration || params.wait_time || 0}ms`);
                      break;
                    default:
                      break;
                  }
                  
                  return paramParts.length > 0 
                    ? `${commandDisplay} (${paramParts.join(', ')})`
                    : commandDisplay;
                };

                return (
                  <Typography
                    key={`failure-${index}`}
                    variant="body2"
                    sx={{ fontSize: '0.75rem', mb: 0.3, color: 'error.main' }}
                  >
                    F{index + 1}. {formatActionDisplay(action)}
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
                  bgcolor: edgeHook.runResult.includes('❌ FAILED')
                    ? 'error.light'
                    : edgeHook.runResult.includes('✅ SUCCESS')
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
