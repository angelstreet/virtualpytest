import { useCallback, useState, useEffect } from 'react';

import { Host } from '../../types/common/Host_Types';
import { EdgeForm, UINavigationEdge } from '../../types/pages/Navigation_Types';
import { Action } from '../../types/pages/Navigation_Types';

import { useEdge } from './useEdge';

export interface UseEdgeEditProps {
  isOpen: boolean;
  edgeForm: EdgeForm | null;
  setEdgeForm: (form: EdgeForm) => void;
  selectedEdge?: UINavigationEdge | null;
  selectedHost?: Host | null;
  isControlActive?: boolean;
}

export const useEdgeEdit = ({
  isOpen,
  edgeForm,
  setEdgeForm,
  selectedEdge,
  selectedHost,
  isControlActive = false,
}: UseEdgeEditProps) => {

  // Edge hook for loading actions from IDs
  const edgeHook = useEdge({
    selectedHost,
    isControlActive,
  });

  // Local state for dialog-specific concerns
  const [localActions, setLocalActions] = useState<Action[]>([]);
  const [localRetryActions, setLocalRetryActions] = useState<Action[]>([]);
  const [localFailureActions, setLocalFailureActions] = useState<Action[]>([]);
  const [dependencyCheckResult, setDependencyCheckResult] = useState<any>(null);

  // Initialize actions when dialog opens or edgeForm/selectedEdge changes
  useEffect(() => {
    if (isOpen && edgeForm?.action_sets?.length > 0) {
      // Find the target action set to edit (based on targetActionSetId or default to first)
      const targetActionSetId = edgeForm.targetActionSetId;
      let actionSet = edgeForm.action_sets[0]; // Default to first
      
      if (targetActionSetId) {
        const foundActionSet = edgeForm.action_sets.find(as => as.id === targetActionSetId);
        if (foundActionSet) {
          actionSet = foundActionSet;
        }
      }
      
      console.log('[@useEdgeEdit] Loading from form action set:', actionSet.id, { 
        actions: actionSet.actions?.length || 0, 
        retry_actions: actionSet.retry_actions?.length || 0,
        failure_actions: actionSet.failure_actions?.length || 0
      });
      setLocalActions(actionSet.actions || []);
      setLocalRetryActions(actionSet.retry_actions || []);
      setLocalFailureActions(actionSet.failure_actions || []);
    } else if (isOpen && selectedEdge?.data?.action_sets?.[0]) {
      // Load actions from selectedEdge if form doesn't have them
      const actionSet = selectedEdge.data.action_sets[0];
      console.log('[@useEdgeEdit] Loading from selectedEdge:', { 
        actions: actionSet.actions?.length || 0, 
        retry_actions: actionSet.retry_actions?.length || 0,
        failure_actions: actionSet.failure_actions?.length || 0
      });
      setLocalActions(actionSet.actions || []);
      setLocalRetryActions(actionSet.retry_actions || []);
      setLocalFailureActions(actionSet.failure_actions || []);

      // Update the form with the loaded actions
      if (edgeForm) {
        const updatedActionSets = [...(edgeForm.action_sets || [])];
        if (updatedActionSets[0]) {
          updatedActionSets[0] = {
            ...updatedActionSets[0],
            actions: actionSet.actions || [],
            retry_actions: actionSet.retry_actions || [],
            failure_actions: actionSet.failure_actions || []
          };
        }
        // Remove setEdgeForm call to prevent infinite loop
        // The form will be updated when saving, not during initialization
      }
    }
  }, [isOpen, edgeForm?.targetActionSetId, selectedEdge]);

  // Reset state when dialog closes
  useEffect(() => {
    if (!isOpen) {
      setLocalActions([]);
      setLocalRetryActions([]);
      setDependencyCheckResult(null);
    }
  }, [isOpen]);

  // Check dependencies for actions - SIMPLIFIED: Legacy action_ids removed, actions are now embedded in action_sets
  const checkDependencies = useCallback(async (_actions: Action[]): Promise<any> => {
    // Since actions are now embedded within action_sets in each edge, there are no shared dependencies
    console.log('[@hook:useEdgeEdit] Dependency check skipped - actions are embedded in action_sets');
    return { success: true, has_shared_actions: false, edges: [], count: 0 };
  }, []);

  // Handle actions change
  const handleActionsChange = useCallback(
    (newActions: Action[]) => {
      if (!edgeForm) return;

      setLocalActions(newActions);
      const updatedActionSets = [...(edgeForm.action_sets || [])];
      if (updatedActionSets[0]) {
        updatedActionSets[0] = { ...updatedActionSets[0], actions: newActions };
      }
      setEdgeForm({
        ...edgeForm,
        action_sets: updatedActionSets,
      });
    },
    [edgeForm, setEdgeForm],
  );

  // Handle retry actions change
  const handleRetryActionsChange = useCallback(
    (newRetryActions: Action[]) => {
      if (!edgeForm) return;

      setLocalRetryActions(newRetryActions);
      const updatedActionSets = [...(edgeForm.action_sets || [])];
      if (updatedActionSets[0]) {
        updatedActionSets[0] = { ...updatedActionSets[0], retry_actions: newRetryActions };
      }
      setEdgeForm({
        ...edgeForm,
        action_sets: updatedActionSets,
      });
    },
    [edgeForm, setEdgeForm],
  );

  // Handle failure actions change
  const handleFailureActionsChange = useCallback(
    (newFailureActions: Action[]) => {
      if (!edgeForm) return;

      setLocalFailureActions(newFailureActions);
      const updatedActionSets = [...(edgeForm.action_sets || [])];
      if (updatedActionSets[0]) {
        updatedActionSets[0] = { ...updatedActionSets[0], failure_actions: newFailureActions };
      }
      setEdgeForm({
        ...edgeForm,
        action_sets: updatedActionSets,
      });
    },
    [edgeForm, setEdgeForm],
  );

  // Execute local actions - simple wrapper around edge hook
  const executeLocalActions = useCallback(async () => {
    if (!selectedEdge) return;
    return await edgeHook.executeEdgeActions(selectedEdge, localActions, localRetryActions, localFailureActions);
  }, [edgeHook, selectedEdge, localActions, localRetryActions, localFailureActions]);

  // Validate form
  const isFormValid = useCallback((): boolean => {
    return localActions.every((action) => {
      if (!action.command || action.command.trim() === '') {
        return false;
      }

      // Check required parameters based on command using type assertion
      const params = action.params as any;

      if (action.command === 'input_text' && (!params?.text || params.text.trim() === '')) {
        return false;
      }
      if (
        action.command === 'click_element' &&
        (!params?.element_id || params.element_id.trim() === '')
      ) {
        return false;
      }
      if (
        (action.command === 'launch_app' || action.command === 'close_app') &&
        (!params?.package || params.package.trim() === '')
      ) {
        return false;
      }
      if (
        action.command === 'tap_coordinates' &&
        (params?.x === undefined || params?.y === undefined)
      ) {
        return false;
      }

      return true;
    });
  }, [localActions]);

  // Use edgeHook.canRunActions directly instead of duplicating logic

  return {
    // Action execution
    executeLocalActions,
    checkDependencies,

    // Local state
    localActions,
    localRetryActions,
    localFailureActions,
    dependencyCheckResult,

    // Handlers
    handleActionsChange,
    handleRetryActionsChange,
    handleFailureActionsChange,

    // Validation
    isFormValid,
  };
};
