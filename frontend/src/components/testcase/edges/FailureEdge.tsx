import React from 'react';
import {
  BaseEdge,
  EdgeProps,
  getBezierPath,
} from 'reactflow';

/**
 * Failure Edge - Grey connection with optional animated flow
 * Shows animated dots flowing when edge is part of execution path
 */
export const FailureEdge: React.FC<EdgeProps & { 
  animated?: boolean; // For execution flow visualization
  executionState?: 'active' | 'traversed' | 'idle';
}> = ({
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  style = {},
  markerEnd,
  selected,
  animated,
  executionState = 'idle',
}) => {
  const [edgePath] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  // Determine edge color based on execution state
  const getEdgeColor = () => {
    if (executionState === 'active') return '#3b82f6'; // Blue for active execution
    if (executionState === 'traversed') return '#ef4444'; // Red for failure path traversed
    if (selected) return '#64748b';
    return '#94a3b8'; // Default grey
  };

  const edgeColor = getEdgeColor();
  const strokeWidth = executionState !== 'idle' ? 3 : (selected ? 3 : 2);

  return (
    <>
      <BaseEdge
        path={edgePath}
        markerEnd={markerEnd}
        style={{
          ...style,
          stroke: edgeColor,
          strokeWidth,
          strokeDasharray: animated || executionState === 'active' ? '5, 5' : undefined,
          animation: animated || executionState === 'active' ? 'flowDots 1s linear infinite' : undefined,
        }}
      />
      
      {/* Add keyframes for flow animation */}
      <style>{`
        @keyframes flowDots {
          to {
            stroke-dashoffset: -10;
          }
        }
      `}</style>
    </>
  );
};
