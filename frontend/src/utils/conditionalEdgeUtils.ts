/**
 * Utilities for handling conditional edges
 * Conditional edges share the same action_set_id (forward actions only)
 */

import { Edge } from 'reactflow';

/**
 * Find sibling edge that has the actual actions for a conditional edge
 * @param edgeId - Current edge ID
 * @param sourceNodeId - Source node ID
 * @param actionSetId - The shared action_set_id
 * @param allEdges - All edges in the graph
 * @returns The sibling edge with actions, or null if not found
 */
export function findSiblingWithActions(
  edgeId: string,
  sourceNodeId: string,
  actionSetId: string,
  allEdges: Edge[]
): Edge | null {
  for (const edge of allEdges) {
    // Skip self
    if (edge.id === edgeId) continue;
    
    // Only check edges from same source
    if (edge.source !== sourceNodeId) continue;
    
    // Check if this edge shares the same action_set_id AND has actions
    const edgeActionSets = edge.data?.action_sets || [];
    if (edgeActionSets.length > 0) {
      const forwardActionSet = edgeActionSets[0]; // Forward is always index 0
      if (forwardActionSet?.id === actionSetId && forwardActionSet.actions?.length > 0) {
        return edge;
      }
    }
  }
  
  return null;
}

