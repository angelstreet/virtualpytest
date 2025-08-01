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

  // Device data hook (no longer needed for individual resolution)

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
   * LEGACY: Get actions from edge data (for backward compatibility during transition)
   */
  const getActionsFromEdge = useCallback((edge: UINavigationEdge): Action[] => {
    // Try new structure first
    try {
      const defaultSet = getDefaultActionSet(edge);
      return defaultSet.actions;
    } catch {
      // Fallback to legacy structure if it exists
      return edge.data?.actions || [];
    }
  }, [getDefaultActionSet]);

  /**
   * LEGACY: Get retry actions from edge data (for backward compatibility during transition)
   */
  const getRetryActionsFromEdge = useCallback((edge: UINavigationEdge): Action[] => {
    // Try new structure first
    try {
      const defaultSet = getDefaultActionSet(edge);
      return defaultSet.retry_actions || [];
    } catch {
      // Fallback to legacy structure if it exists
      return edge.data?.retryActions || [];
    }
  }, [getDefaultActionSet]);

  /**
   * Check if edge can run actions
   */
  const canRunActions = useCallback(
    (edge: UINavigationEdge): boolean => {
      const actions = getActionsFromEdge(edge);
      
      // Debug the canRunActions conditions
      console.log('canRunActions conditions:', {
        isControlActive: props?.isControlActive === true,
        hasSelectedHost: props?.selectedHost !== null,
        hasActions: actions.length > 0,
        isNotLoading: !actionHook.loading,
        edge: edge.id
      });
      
      return (
        props?.isControlActive === true &&
        props?.selectedHost !== null &&
        actions.length > 0 &&
        !actionHook.loading
      );
    },
    [props?.isControlActive, props?.selectedHost, actionHook.loading, getActionsFromEdge],
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
      const actions = overrideActions || getActionsFromEdge(edge);
      const retryActions = overrideRetryActions || getRetryActionsFromEdge(edge);

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
      getActionsFromEdge,
      getRetryActionsFromEdge,
      convertToControllerAction,
      formatRunResult,
      props?.isControlActive,
      props?.selectedHost,
      updateCurrentPosition,
    ],
  );

  /**
   * Create edge form from edge data - NEW: Uses action_sets structure
   */
  const createEdgeForm = useCallback(
    (edge: UINavigationEdge): EdgeForm => {
      try {
        // Try new action_sets structure
        const actionSets = getActionSetsFromEdge(edge);
        const defaultActionSetId = edge.data.default_action_set_id || 'default';

        return {
          edgeId: edge.id, // Include edge ID for tracking
          description: edge.data?.description || '',
          action_sets: actionSets, // NEW: action sets structure
          default_action_set_id: defaultActionSetId, // NEW: default action set ID
          final_wait_time: edge.data?.final_wait_time ?? 2000,
          priority: edge.data?.priority || 'p3', // Default to p3 if not set
          threshold: edge.data?.threshold ?? 0, // Default to 0 if not set
        };
      } catch {
        // Fallback for legacy structure during transition
        const actions = edge.data?.actions || [];
        const retryActions = edge.data?.retryActions || [];

        // Convert legacy to new structure
        const defaultActionSet: ActionSet = {
          id: 'default',
          label: 'Default Actions',
          actions: actions,
          retry_actions: retryActions,
          priority: 1,
          conditions: {},
          timer: 0
        };

        return {
          edgeId: edge.id,
          description: edge.data?.description || '',
          action_sets: [defaultActionSet],
          default_action_set_id: 'default',
          final_wait_time: edge.data?.final_wait_time ?? 2000,
          priority: edge.data?.priority || 'p3',
          threshold: edge.data?.threshold ?? 0,
        };
      }
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

    // NEW: Action sets methods
    getActionSetsFromEdge,
    getDefaultActionSet,
    executeActionSet,

    // Utility functions
    getEdgeColorsForEdge,
    isProtectedEdge,
    getActionsFromEdge, // Legacy compatibility
    getRetryActionsFromEdge, // Legacy compatibility
    canRunActions,
    formatRunResult,
    createEdgeForm,

    // Action functions
    executeEdgeActions,
    clearResults,
  };
};
