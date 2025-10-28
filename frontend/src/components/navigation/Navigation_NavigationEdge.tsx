import React from 'react';
import { EdgeProps, getSmoothStepPath, getBezierPath, useReactFlow } from 'reactflow';

import { useMetrics } from '../../hooks/navigation/useMetrics';
import { useValidationColors } from '../../hooks/validation';
import { UINavigationEdge as UINavigationEdgeType } from '../../types/pages/Navigation_Types';

export const NavigationEdgeComponent: React.FC<EdgeProps<UINavigationEdgeType['data']>> = (
  props,
) => {
  const { id, source, target, sourceX, sourceY, targetX, targetY, selected, data } = props;
  const { getNodes, getEdges } = useReactFlow();

  // Get metrics for this edge
  const metricsHook = useMetrics();
  const edgeMetrics = metricsHook.getEdgeMetrics(id);

  // Get edge colors based on validation status with metrics (direct call)
  const { getEdgeColors } = useValidationColors([]);
  let edgeColors = getEdgeColors(id, edgeMetrics);

  // 🎨 AUTOMATIC CONDITIONAL EDGE DETECTION
  // Check if this edge's action set is shared by multiple edges from the same source
  const defaultActionSetId = data?.default_action_set_id;
  let isConditionalEdge = data?.is_conditional || data?.is_conditional_primary || false;
  
  if (!isConditionalEdge && defaultActionSetId) {
    // Auto-detect: count how many edges from the same source use this action_set_id
    const edges = getEdges();
    let shareCount = 0;
    
    edges.forEach((edge: any) => {
      // Only count edges from the SAME SOURCE node
      if (edge.source === source) {
        const edgeActionSetId = edge.data?.default_action_set_id;
        if (edgeActionSetId === defaultActionSetId) {
          shareCount++;
        }
      }
    });
    
    // If multiple edges from same source share this action_set_id, it's conditional
    isConditionalEdge = shareCount > 1;
  }

  // 🎨 OVERRIDE: Conditional edges are always BLUE
  if (isConditionalEdge) {
    edgeColors = {
      stroke: '#2196f3',
      strokeWidth: 3,
      strokeDasharray: '',
      opacity: 1,
    };
  }

  // Get current nodes to check types
  const nodes = getNodes();
  const sourceNode = nodes.find((node) => node.id === source);
  const targetNode = nodes.find((node) => node.id === target);

  // Check if this is an entry-to-home connection
  const isEntryToHome =
    sourceNode?.data?.type === 'entry' &&
    (targetNode?.data?.is_root === true || targetNode?.data?.label?.toLowerCase() === 'home');

  // Normalize coordinates for bidirectional edges to ensure same path (for non-entry edges)
  // Always use the lexicographically smaller node ID as "source" for path calculation
  const normalizedSource = source < target ? source : target;

  // Determine if we need to swap coordinates based on normalization
  const shouldSwapCoordinates = source !== normalizedSource;

  // Use normalized coordinates for consistent path (only for non-entry edges)
  const pathSourceX =
    isEntryToHome || shouldSwapCoordinates ? (isEntryToHome ? sourceX : targetX) : sourceX;
  const pathSourceY =
    isEntryToHome || shouldSwapCoordinates ? (isEntryToHome ? sourceY : targetY) : sourceY;
  const pathTargetX =
    isEntryToHome || shouldSwapCoordinates ? (isEntryToHome ? targetX : sourceX) : targetX;
  const pathTargetY =
    isEntryToHome || shouldSwapCoordinates ? (isEntryToHome ? targetY : sourceY) : targetY;

  // Choose path type based on edge type
  let edgePath: string;

  if (isEntryToHome) {
    // Use bezier path for entry-to-home connections
    [edgePath] = getBezierPath({
      sourceX: pathSourceX,
      sourceY: pathSourceY,
      targetX: pathTargetX,
      targetY: pathTargetY,
    });
  } else {
    // Use smooth step path for all other connections
    [edgePath] = getSmoothStepPath({
      sourceX: pathSourceX,
      sourceY: pathSourceY,
      targetX: pathTargetX,
      targetY: pathTargetY,
    });
  }

  return (
    <g className={edgeColors.className}>
      {/* Invisible thick overlay for better selectability */}
      <path
        id={`${id}-selectable`}
        style={{
          ...edgeColors,
          strokeWidth: 15,
          fill: 'none',
          stroke: 'transparent',
          cursor: 'pointer',
        }}
        className="react-flow__edge-interaction"
        d={edgePath}
      />

      {/* Visible edge path without arrow */}
      <path
        id={id}
        style={{
          ...edgeColors,
          fill: 'none',
          strokeWidth: edgeColors.strokeWidth || 2,
          cursor: 'pointer',
        }}
        className="react-flow__edge-path"
        d={edgePath}
      />

      {/* Selection indicator */}
      {selected && (
        <path
          style={{
            ...edgeColors,
            stroke: '#555',
            strokeWidth: (edgeColors.strokeWidth || 2) + 2,
            fill: 'none',
            strokeDasharray: '5,5',
            opacity: 0.8,
          }}
          className="react-flow__edge-path"
          d={edgePath}
        />
      )}
    </g>
  );
};
