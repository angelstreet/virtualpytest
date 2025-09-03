import { useCallback, useState } from 'react';

import { useNavigation } from '../../contexts/navigation/NavigationContext';
import { Host } from '../../types/common/Host_Types';
import { Actions } from '../../types/controller/Action_Types';
import { UINavigationEdge, EdgeForm, ActionSet, Action } from '../../types/pages/Navigation_Types';
import { useAction } from '../actions';
import { useValidationColors } from '../validation';

export interface UseEdgeProps {
  selectedHost?: Host | null;
  selectedDeviceId?: string | null;
  isControlActive?: boolean;
  availableActions?: Actions;
}

export const useEdge = (props?: UseEdgeProps) => {
  // Action hook for edge operations
  const actionHook = useAction();

  // Navigation context for current position updates
  const { updateCurrentPosition, nodes } = useNavigation();

  // Validation colors hook for edge styling
  const { getEdgeColors } = useValidationColors([]);

  // State for edge operations
  const [runResult, setRunResult] = useState<string | null>(null);

  /**
   * Convert navigation Action to EdgeAction for action execution
   */
  const convertToControllerAction = useCallback((navAction: Action): any => {
    console.log('🔍 [DEBUG] convertToControllerAction input:', navAction);
    
    const converted: any = {
      command: navAction.command,
      name: navAction.command, // Use command as name since action.name was removed
      params: navAction.params,
      action_type: navAction.action_type, // Include action_type for routing
      verification_type: navAction.verification_type, // Include verification_type for verification actions
    };
    
    // Only include iterator for non-verification actions
    if (navAction.action_type !== 'verification') {
      converted.iterator = navAction.iterator || 1;
    }
    
    console.log('🔍 [DEBUG] convertToControllerAction output:', converted);
    return converted;
  }, []);

  /**
   * Get edge colors based on validation status
   */
  const getEdgeColorsForEdge = useCallback(
    (edgeId: string, _isEntryEdge: boolean = false, metrics?: any) => {
      return getEdgeColors(edgeId, metrics);
    },
    [getEdgeColors],
  );

  /**
   * Check if an edge is a protected edge (cannot be deleted)
   */
  const isProtectedEdge = useCallback((edge: UINavigationEdge): boolean => {
    return (
      edge.source === 'entry-node' ||
      edge.source?.toLowerCase().includes('entry') ||
      edge.source?.toLowerCase().includes('home')
    );
  }, []);

  /**
   * NEW: Get action sets from edge data
   */
  const getActionSetsFromEdge = useCallback((edge: UINavigationEdge): ActionSet[] => {
    if (!edge.data?.action_sets) {
      throw new Error("Edge missing action_sets - no legacy support");
    }
    return edge.data.action_sets;
  }, []);

  /**
   * NEW: Get default action set from edge
   */
  const getDefaultActionSet = useCallback((edge: UINavigationEdge): ActionSet => {
    const actionSets = getActionSetsFromEdge(edge);
    const defaultId = edge.data.default_action_set_id;
    if (!defaultId) { 
      throw new Error("Edge missing default_action_set_id"); 
    }
    const defaultSet = actionSets.find(set => set.id === defaultId);
    if (!defaultSet) { 
      throw new Error(`Default action set '${defaultId}' not found`); 
    }
    return defaultSet;
  }, [getActionSetsFromEdge]);

  /**
   * NEW: Execute specific action set
   */
  const executeActionSet = useCallback(async (
    edge: UINavigationEdge,
    actionSetId: string
  ) => {
    const actionSets = getActionSetsFromEdge(edge);
    const actionSet = actionSets.find(set => set.id === actionSetId);
    if (!actionSet) { 
      throw new Error(`Action set ${actionSetId} not found`); 
    }
    return await actionHook.executeActions(
      actionSet.actions.map(convertToControllerAction),
      (actionSet.retry_actions || []).map(convertToControllerAction),
      (actionSet.failure_actions || []).map(convertToControllerAction)
    );
  }, [getActionSetsFromEdge, actionHook, convertToControllerAction]);



  /**
   * Check if edge can run actions
   */
  const canRunActions = useCallback(
    (edge: UINavigationEdge): boolean => {
      const defaultSet = getDefaultActionSet(edge);
      const actions = defaultSet.actions || [];
      
      return (
        props?.isControlActive === true &&
        props?.selectedHost !== null &&
        actions.length > 0 &&
        !actionHook.loading
      );
    },
    [props?.isControlActive, props?.selectedHost, actionHook.loading, getDefaultActionSet],
  );

  /**
   * Format run result for compact display
   */
  const formatRunResult = useCallback((result: string): string => {
    if (!result) return '';

    const lines = result.split('\n');
    const formattedLines: string[] = [];

    for (const line of lines) {
      if (
        line.includes('⏹️ Execution stopped due to failed action') ||
        line.includes('📋 Processing') ||
        line.includes('⏳ Starting execution') ||
        line.includes('🔄 Executing action') ||
        line.includes('✅ Action completed') ||
        line.includes('❌ Action failed') ||
        line.includes('🎯 Final result')
      ) {
        continue;
      }

      if (line.trim()) {
        formattedLines.push(line);
      }
    }

    return formattedLines.join('\n');
  }, []);

  /**
   * Execute edge actions using centralized method
   */
  const executeEdgeActions = useCallback(
    async (edge: UINavigationEdge, overrideActions?: Action[], overrideRetryActions?: Action[], overrideFailureActions?: Action[]) => {
      const defaultSet = getDefaultActionSet(edge);
      const actions = overrideActions || defaultSet.actions || [];
      const retryActions = overrideRetryActions || defaultSet.retry_actions || [];
      const failureActions = overrideFailureActions || defaultSet.failure_actions || [];

      if (actions.length === 0) {
        setRunResult('❌ No actions to execute');
        return;
      }

      if (!props?.isControlActive || !props?.selectedHost) {
        setRunResult('❌ Device control not active or host not available');
        return;
      }

      setRunResult(null);

      try {
        const result = await actionHook.executeActions(
          actions.map(convertToControllerAction),
          retryActions.map(convertToControllerAction),
          failureActions.map(convertToControllerAction),
        );

        const formattedResult = formatRunResult(actionHook.formatExecutionResults(result));
        setRunResult(formattedResult);

        // Update current position to the target node if execution was successful
        // BUT: If target is an action node, stay at the source node since actions are operations, not destinations
        if (result && result.success !== false && edge.target) {
          const targetNode = nodes.find(n => n.id === edge.target);
          
          if (targetNode?.data.type === 'action') {
            // For action nodes, position remains at source (where the action was triggered from)
            // Do not update current position since actions are transient operations
            console.log(`[@useEdge] Action node '${targetNode.data.label}' executed, position remains at source`);
          } else {
            // For screen/menu nodes, update position to target
            updateCurrentPosition(edge.target, null);
          }
          
          // Note: Timer actions should be handled by a dedicated timer actions hook
          // in components that specifically need auto-return functionality
        }

        return result;
      } catch (err: any) {
        const errorResult = `❌ Network error: ${err.message}`;
        setRunResult(errorResult);
        throw err;
      }
    },
    [
      actionHook,
      getDefaultActionSet,
      convertToControllerAction,
      formatRunResult,
      props?.isControlActive,
      props?.selectedHost,
      updateCurrentPosition,
    ],
  );

  /**
   * Create edge form from edge data - CLEAN BIDIRECTIONAL STRUCTURE ONLY
   */
  const createEdgeForm = useCallback(
    (edge: UINavigationEdge): EdgeForm => {
      // Ensure edge has exactly 2 action sets
      const actionSets = getActionSetsFromEdge(edge);
      if (actionSets.length !== 2) {
        throw new Error(`Edge must have exactly 2 action sets, found ${actionSets.length}`);
      }
      
      const defaultActionSetId = edge.data.default_action_set_id;
      if (!defaultActionSetId) {
        throw new Error("Edge missing default_action_set_id");
      }

      return {
        edgeId: edge.id,
        action_sets: actionSets,
        default_action_set_id: defaultActionSetId,
        final_wait_time: edge.data?.final_wait_time ?? 2000,
      };
    },
    [getActionSetsFromEdge],
  );

  /**
   * Check if an action set is null or empty (no actions in any category)
   */
  const isActionSetEmpty = useCallback((actionSet: ActionSet): boolean => {
    if (!actionSet) return true;
    
    const hasActions = (actionSet.actions && actionSet.actions.length > 0);
    const hasRetryActions = (actionSet.retry_actions && actionSet.retry_actions.length > 0);
    const hasFailureActions = (actionSet.failure_actions && actionSet.failure_actions.length > 0);
    
    return !hasActions && !hasRetryActions && !hasFailureActions;
  }, []);

  /**
   * Check if an edge should be deleted based on directional action set rules:
   * - If both directions (action sets) are empty: delete the edge
   * - If one direction has actions and other is empty: update (clear empty direction)
   * - If both directions have actions: keep as is (no deletion)
   * - If only one direction exists and has actions: keep as is (no deletion)
   */
  const shouldDeleteEdge = useCallback((edge: UINavigationEdge): { shouldDelete: boolean, shouldUpdate: boolean } => {
    const actionSets = getActionSetsFromEdge(edge);
    
    if (actionSets.length === 0) {
      // No action sets - delete the edge
      return { shouldDelete: true, shouldUpdate: false };
    }
    
    const emptyActionSets = actionSets.filter(set => isActionSetEmpty(set));
    const nonEmptyActionSets = actionSets.filter(set => !isActionSetEmpty(set));
    
    if (emptyActionSets.length === actionSets.length) {
      // All directions are empty - delete the edge
      return { shouldDelete: true, shouldUpdate: false };
    }
    
    if (nonEmptyActionSets.length === actionSets.length) {
      // All directions have actions - keep the edge as is
      return { shouldDelete: false, shouldUpdate: false };
    }
    
    // Mixed: some directions have actions, others are empty - update (clear empty directions)
    return { shouldDelete: false, shouldUpdate: true };
  }, [getActionSetsFromEdge, isActionSetEmpty]);

  /**
   * Clear only the empty action sets (directional cleanup)
   * Returns the updated edge data structure
   */
  const clearEdgeActionSets = useCallback((edge: UINavigationEdge): any => {
    const actionSets = getActionSetsFromEdge(edge);
    
    // Only clear action sets that are already empty (this is for cleanup)
    // Keep non-empty action sets as they represent active directions
    const updatedActionSets = actionSets.map(actionSet => {
      if (isActionSetEmpty(actionSet)) {
        // Clear empty action sets completely
        return {
          ...actionSet,
          actions: [],
          retry_actions: [],
          failure_actions: []
        };
      }
      // Keep non-empty action sets unchanged
      return actionSet;
    });
    
    return {
      ...edge,
      data: {
        ...edge.data,
        action_sets: updatedActionSets
      }
    };
  }, [getActionSetsFromEdge, isActionSetEmpty]);

  /**
   * Delete actions from specific direction only
   */
  const deleteActionSetDirection = useCallback(async (edgeId: string, actionSetId: string) => {
    console.log('[@useEdge:deleteActionSetDirection] Deleting direction:', { edgeId, actionSetId });
    
    const edge = nodes.find(n => n.id === edgeId); // This should be edges, will fix in navigation context
    if (!edge) {
      throw new Error(`Edge ${edgeId} not found`);
    }
    
    // This function will be called by NavigationContext with proper edge parameter
    throw new Error('deleteActionSetDirection should be called through NavigationContext');
  }, [nodes]);

  /**
   * Delete entire edge (when both directions empty)
   */
  const deleteEntireEdge = useCallback(async (edgeId: string) => {
    console.log('[@useEdge:deleteEntireEdge] Deleting entire edge:', edgeId);
    
    // This function will be called by NavigationContext with proper edge management
    throw new Error('deleteEntireEdge should be called through NavigationContext');
  }, []);

  /**
   * Complete edge deletion workflow - MAIN ENTRY POINT
   */
  const handleEdgeDeletion = useCallback(async (edge: UINavigationEdge) => {
    console.log('[@useEdge:handleEdgeDeletion] Starting edge deletion workflow:', edge.id);
    
    // Check deletion rules based on directional action sets
    const edgeDecision = shouldDeleteEdge(edge);
    
    console.log('[@useEdge:handleEdgeDeletion] Edge deletion analysis:', {
      edgeId: edge.id,
      edgeDecision
    });
    
    if (edgeDecision.shouldDelete) {
      // Delete the edge completely (all directions are empty)
      console.log('[@useEdge:handleEdgeDeletion] All directions empty, deleting entire edge');
      return { action: 'delete_entire_edge', edgeId: edge.id };
    } else if (edgeDecision.shouldUpdate) {
      // Update edge (clear empty directions, keep active directions)
      console.log('[@useEdge:handleEdgeDeletion] Clearing empty directions only');
      const updatedEdge = clearEdgeActionSets(edge);
      return { action: 'update_edge', edge: updatedEdge };
    } else {
      // Keep the edge as is (all directions have actions)
      console.log('[@useEdge:handleEdgeDeletion] Edge has active directions - no deletion');
      return { action: 'no_change', message: 'Edge has active directions - no deletion' };
    }
  }, [shouldDeleteEdge, clearEdgeActionSets]);

  /**
   * Handle direction-specific deletion (for panel delete buttons)
   */
  const handleDirectionDeletion = useCallback(async (edge: UINavigationEdge, actionSetId: string) => {
    console.log('[@useEdge:handleDirectionDeletion] Deleting direction:', { edgeId: edge.id, actionSetId });
    
    const actionSets = getActionSetsFromEdge(edge);
    
    // Determine direction from action set ID
    const forwardActionSetId = actionSets[0]?.id;
    const direction = actionSetId === forwardActionSetId ? 'forward' : 'reverse';
    const targetIndex = direction === 'forward' ? 0 : 1;

    // Clear actions but keep structure
    const updatedActionSets = [...actionSets];
    updatedActionSets[targetIndex] = {
      ...updatedActionSets[targetIndex],
      actions: [],
      retry_actions: [],
      failure_actions: []
    };

    // Create updated edge
    const updatedEdge = {
      ...edge,
      data: {
        ...edge.data,
        action_sets: updatedActionSets
      }
    };

    // Check if both directions are now empty
    const bothDirectionsEmpty = updatedActionSets.every(as => 
      (!as.actions || as.actions.length === 0) &&
      (!as.retry_actions || as.retry_actions.length === 0) &&
      (!as.failure_actions || as.failure_actions.length === 0)
    );

    if (bothDirectionsEmpty) {
      // Return action to delete entire edge
      console.log('[@useEdge:handleDirectionDeletion] Both directions empty after clearing, delete entire edge');
      return { action: 'delete_entire_edge', edgeId: edge.id };
    } else {
      // Return action to update edge with cleared direction
      console.log('[@useEdge:handleDirectionDeletion] Clearing direction only:', direction);
      return { action: 'update_edge', edge: updatedEdge, needsSave: true };
    }
  }, [getActionSetsFromEdge]);

  /**
   * Clear results when edge changes
   */
  const clearResults = useCallback(() => {
    setRunResult(null);
  }, []);

  /**
   * Check if an edge involves an action node or entry node (source or target is action/entry type)
   * Both action and entry nodes should only show forward edges (unidirectional)
   */
  const isActionEdge = useCallback((edge: UINavigationEdge): boolean => {
    const sourceNode = nodes.find((n) => n.id === edge.source);
    const targetNode = nodes.find((n) => n.id === edge.target);
    return (
      sourceNode?.data.type === 'action' || 
      targetNode?.data.type === 'action' ||
      sourceNode?.data.type === 'entry' || 
      targetNode?.data.type === 'entry'
    );
  }, [nodes]);

  /**
   * Get action sets for display - filter to only forward direction for action/entry edges
   */
  const getDisplayActionSets = useCallback((edge: UINavigationEdge): ActionSet[] => {
    const actionSets = getActionSetsFromEdge(edge);
    
    // For action/entry edges, only show the first action set (forward direction)
    // since actions and entry nodes are unidirectional operations
    if (isActionEdge(edge)) {
      return actionSets.length > 0 ? [actionSets[0]] : [];
    }
    
    // For regular edges, show all action sets (bidirectional)
    return actionSets;
  }, [getActionSetsFromEdge, isActionEdge]);

  return {
    // Action hook
    actionHook,

    // State
    runResult,

    // Action sets methods - STRICT: NO LEGACY SUPPORT
    getActionSetsFromEdge,
    getDefaultActionSet,
    executeActionSet,

    // Utility functions
    getEdgeColorsForEdge,
    isProtectedEdge,
    isActionEdge,
    getDisplayActionSets,

    canRunActions,
    formatRunResult,
    createEdgeForm,

    // Action functions
    executeEdgeActions,
    clearResults,

    // NEW: Edge deletion logic helpers
    isActionSetEmpty,
    shouldDeleteEdge,
    clearEdgeActionSets,

    // NEW: Edge deletion workflow functions
    deleteActionSetDirection,
    deleteEntireEdge,
    handleEdgeDeletion,
    handleDirectionDeletion,
  };
};
