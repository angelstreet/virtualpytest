import { useCallback, useState } from 'react';

import { useNavigation } from '../../contexts/navigation/NavigationContext';
import { Host } from '../../types/common/Host_Types';
import { Actions, Action } from '../../types/controller/Action_Types';
import { UINavigationEdge, EdgeForm, ActionSet } from '../../types/pages/Navigation_Types';
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
  const { updateCurrentPosition } = useNavigation();

  // Validation colors hook for edge styling
  const { getEdgeColors } = useValidationColors([]);

  // State for edge operations
  const [runResult, setRunResult] = useState<string | null>(null);

  /**
   * Convert navigation Action to EdgeAction for action execution
   */
  const convertToControllerAction = useCallback((navAction: Action): any => {
    return {
      command: navAction.command,
      name: navAction.label || navAction.command,
      params: navAction.params,
    };
  }, []);

  /**
   * Get edge colors based on validation status
   */
  const getEdgeColorsForEdge = useCallback(
    (edgeId: string, _isEntryEdge: boolean = false) => {
      return getEdgeColors(edgeId);
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
      (actionSet.retry_actions || []).map(convertToControllerAction)
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
    async (edge: UINavigationEdge, overrideActions?: Action[], overrideRetryActions?: Action[]) => {
      const defaultSet = getDefaultActionSet(edge);
      const actions = overrideActions || defaultSet.actions || [];
      const retryActions = overrideRetryActions || defaultSet.retry_actions || [];

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
        );

        const formattedResult = formatRunResult(actionHook.formatExecutionResults(result));
        setRunResult(formattedResult);

        // Update current position to the target node if execution was successful
        // This follows the same pattern as executeNavigation in useNode.ts
        if (result && result.success !== false && edge.target) {
          updateCurrentPosition(edge.target, null);
          
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
   * Create edge form from edge data - STRICT: Only action_sets structure, NO LEGACY
   */
  const createEdgeForm = useCallback(
    (edge: UINavigationEdge): EdgeForm => {
      const actionSets = getActionSetsFromEdge(edge);
      const defaultActionSetId = edge.data.default_action_set_id;
      
      if (!defaultActionSetId) {
        throw new Error("Edge missing default_action_set_id - no legacy support");
      }

      return {
        edgeId: edge.id, // Include edge ID for tracking
        action_sets: actionSets, // REQUIRED: action sets structure
        default_action_set_id: defaultActionSetId, // REQUIRED: default action set ID
        final_wait_time: edge.data?.final_wait_time ?? 2000,
        priority: edge.data?.priority || 'p3', // Default to p3 if not set
        threshold: edge.data?.threshold ?? 0, // Default to 0 if not set
      };
    },
    [getActionSetsFromEdge],
  );

  /**
   * Clear results when edge changes
   */
  const clearResults = useCallback(() => {
    setRunResult(null);
  }, []);

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

    canRunActions,
    formatRunResult,
    createEdgeForm,

    // Action functions
    executeEdgeActions,
    clearResults,
  };
};
