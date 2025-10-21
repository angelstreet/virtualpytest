import { useCallback, useState, useEffect, useRef, useMemo } from 'react';

import { Host } from '../../types/common/Host_Types';
import { EdgeForm, UINavigationEdge } from '../../types/pages/Navigation_Types';
import { Action } from '../../types/pages/Navigation_Types';

import { useEdge } from './useEdge';
import { useNavigation } from '../../contexts/navigation/NavigationContext';
import { useDeviceData } from '../../contexts/device/DeviceDataContext';
import { useVerification } from '../verification/useVerification';

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

  // Get navigation context for save and treeId
  const { saveEdgeWithStateUpdate, treeId, userInterface } = useNavigation();

  // Get device data context for model references
  const { getModelReferences, referencesLoading, references } = useDeviceData();
  
  // Use userinterface name for reference lookup
  const referenceKey = userInterface?.name;

  // Get model references using the userinterface name
  const modelReferences = useMemo(() => {
    if (!referenceKey) return {};
    return getModelReferences(referenceKey);
  }, [getModelReferences, referenceKey, references]);

  // Verification hook for managing verifications (for KPI references)
  const verification = useVerification({
    captureSourcePath: undefined,
    userinterfaceName: referenceKey,  // Pass userinterface name for reference resolution
  });

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
  
  // Track if we're currently updating from user edits to prevent reload loop
  const isUserEditRef = useRef(false);
  
  // Track the edge ID to detect when we switch to a different edge
  const prevEdgeIdRef = useRef<string | null>(null);

  // Initialize actions when dialog opens - FIXED: Support both unidirectional (1 action set) and bidirectional (2 action sets)
  useEffect(() => {
    console.log('[@useEdgeEdit] useEffect triggered:', { 
      isOpen, 
      isUserEdit: isUserEditRef.current,
      edgeId: edgeForm?.edgeId,
      prevEdgeId: prevEdgeIdRef.current,
      direction: edgeForm?.direction,
      actionSetsLength: edgeForm?.action_sets?.length
    });
    
    // Skip reload if this is a user edit (not a new edge or direction change)
    if (isUserEditRef.current) {
      console.log('[@useEdgeEdit] Skipping reload - user edit in progress');
      isUserEditRef.current = false;
      return;
    }
    
    // Detect edge change
    const currentEdgeId = edgeForm?.edgeId;
    if (currentEdgeId && prevEdgeIdRef.current !== currentEdgeId) {
      console.log('[@useEdgeEdit] Edge changed:', { from: prevEdgeIdRef.current, to: currentEdgeId });
      prevEdgeIdRef.current = currentEdgeId;
      // Continue to load - new edge selected
    }
    if (isOpen && edgeForm?.action_sets && edgeForm.action_sets.length >= 1) {
      // Direction-based action set selection
      const direction = edgeForm.direction || 'forward';
      
      // For unidirectional edges (entry/action): always use first action set
      // For bidirectional edges: use direction to select forward (index 0) or reverse (index 1)
      const actionSetIndex = edgeForm.action_sets.length === 1 ? 0 : (direction === 'forward' ? 0 : 1);
      const actionSet = edgeForm.action_sets[actionSetIndex];
      
      console.log('[@useEdgeEdit] Loading action set for direction:', direction, actionSet.id, { 
        isUnidirectional: edgeForm.action_sets.length === 1,
        actionSetIndex,
        actions: actionSet.actions?.length || 0, 
        retry_actions: actionSet.retry_actions?.length || 0,
        failure_actions: actionSet.failure_actions?.length || 0
      });
      
      setLocalActions(actionSet.actions || []);
      setLocalRetryActions(actionSet.retry_actions || []);
      setLocalFailureActions(actionSet.failure_actions || []);
    } else if (isOpen && selectedEdge?.data?.action_sets?.[0]) {
      // Fallback: Load actions from selectedEdge if form doesn't have them
      const actionSet = selectedEdge.data.action_sets[0];
      console.log('[@useEdgeEdit] Loading from selectedEdge (fallback):', { 
        actions: actionSet.actions?.length || 0, 
        retry_actions: actionSet.retry_actions?.length || 0,
        failure_actions: actionSet.failure_actions?.length || 0
      });
      setLocalActions(actionSet.actions || []);
      setLocalRetryActions(actionSet.retry_actions || []);
      setLocalFailureActions(actionSet.failure_actions || []);

      // Update the form with the loaded actions
      if (edgeForm && edgeForm.action_sets) {
        const updatedActionSets = [...edgeForm.action_sets];
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
  }, [isOpen, edgeForm?.direction, edgeForm?.action_sets, edgeForm?.edgeId]);

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

  // Handle actions change - SIMPLIFIED DIRECTION-BASED
  const handleActionsChange = useCallback(
    (newActions: Action[]) => {
      console.log('[@useEdgeEdit:handleActionsChange] Called with actions:', newActions.length);
      if (!edgeForm) return;

      setLocalActions(newActions);
      
      // Mark as user edit to prevent reload loop
      console.log('[@useEdgeEdit:handleActionsChange] Setting isUserEditRef = true');
      isUserEditRef.current = true;
      
      // Simple direction-based index selection
      const direction = edgeForm.direction || 'forward';
      const targetIndex = direction === 'forward' ? 0 : 1;
      
      const updatedActionSets = [...(edgeForm.action_sets || [])];
      if (updatedActionSets[targetIndex]) {
        updatedActionSets[targetIndex] = { 
          ...updatedActionSets[targetIndex], 
          actions: newActions 
        };
      }
      
      console.log('[@useEdgeEdit:handleActionsChange] Updating edgeForm, isUserEditRef =', isUserEditRef.current);
      setEdgeForm({
        ...edgeForm,
        action_sets: updatedActionSets,
      });
    },
    [edgeForm, setEdgeForm],
  );

  // Handle retry actions change - SIMPLIFIED DIRECTION-BASED
  const handleRetryActionsChange = useCallback(
    (newRetryActions: Action[]) => {
      if (!edgeForm) return;

      setLocalRetryActions(newRetryActions);
      
      // Mark as user edit to prevent reload loop
      isUserEditRef.current = true;
      
      // Simple direction-based index selection
      const direction = edgeForm.direction || 'forward';
      const targetIndex = direction === 'forward' ? 0 : 1;
      
      const updatedActionSets = [...(edgeForm.action_sets || [])];
      if (updatedActionSets[targetIndex]) {
        updatedActionSets[targetIndex] = { 
          ...updatedActionSets[targetIndex], 
          retry_actions: newRetryActions 
        };
      }
      
      setEdgeForm({
        ...edgeForm,
        action_sets: updatedActionSets,
      });
    },
    [edgeForm, setEdgeForm],
  );

  // Handle failure actions change - SIMPLIFIED DIRECTION-BASED
  const handleFailureActionsChange = useCallback(
    (newFailureActions: Action[]) => {
      if (!edgeForm) return;

      setLocalFailureActions(newFailureActions);
      
      // Mark as user edit to prevent reload loop
      isUserEditRef.current = true;
      
      // Simple direction-based index selection
      const direction = edgeForm.direction || 'forward';
      const targetIndex = direction === 'forward' ? 0 : 1;
      
      const updatedActionSets = [...(edgeForm.action_sets || [])];
      if (updatedActionSets[targetIndex]) {
        updatedActionSets[targetIndex] = { 
          ...updatedActionSets[targetIndex], 
          failure_actions: newFailureActions 
        };
      }
      
      setEdgeForm({
        ...edgeForm,
        action_sets: updatedActionSets,
      });
    },
    [edgeForm, setEdgeForm],
  );

  // Handle KPI reference change for specific action set
  const handleKpiReferencesChange = useCallback(
    (actionSetIndex: number, newKpiReferences: any[]) => {
      if (!edgeForm) return;

      // Mark as user edit to prevent reload loop
      isUserEditRef.current = true;

      const updatedActionSets = [...(edgeForm.action_sets || [])];
      if (updatedActionSets[actionSetIndex]) {
        updatedActionSets[actionSetIndex] = {
          ...updatedActionSets[actionSetIndex],
          kpi_references: newKpiReferences
        };
      }

      setEdgeForm({
        ...edgeForm,
        action_sets: updatedActionSets,
      });
    },
    [edgeForm, setEdgeForm],
  );

  // Handle use_verifications_for_kpi flag change for specific action set
  const handleUseVerificationsForKpiChange = useCallback(
    (actionSetIndex: number, useVerifications: boolean) => {
      if (!edgeForm) return;

      // Mark as user edit to prevent reload loop
      isUserEditRef.current = true;

      const updatedActionSets = [...(edgeForm.action_sets || [])];
      if (updatedActionSets[actionSetIndex]) {
        updatedActionSets[actionSetIndex] = {
          ...updatedActionSets[actionSetIndex],
          use_verifications_for_kpi: useVerifications
        };
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

  // Handle save operation - SELF-CONTAINED (Option 1)
  const handleSave = useCallback(async () => {
    if (!edgeForm) {
      console.error('[useEdgeEdit] Cannot save: edgeForm is null');
      return;
    }
    
    try {
      // Save to database via context
      await saveEdgeWithStateUpdate(edgeForm);
      
      // Invalidate navigation cache on all hosts after edge update
      if (treeId) {
        console.log('[useEdgeEdit] Invalidating navigation cache for tree:', treeId);
        const { buildServerUrl } = await import('../../utils/buildUrlUtils');
        
        // Call server to invalidate cache on all hosts (buildServerUrl adds team_id automatically)
        await fetch(buildServerUrl(`/server/navigation/cache/invalidate/${treeId}`), {
          method: 'POST',
        });
        console.log('[useEdgeEdit] Cache invalidated successfully');
      }
    } catch (error) {
      console.error('[useEdgeEdit] Failed to save edge or invalidate cache:', error);
      throw error;
    }
  }, [edgeForm, saveEdgeWithStateUpdate, treeId]);

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
    handleKpiReferencesChange,
    handleUseVerificationsForKpiChange,

    // Verification (for KPI references)
    verification,
    modelReferences,
    referencesLoading,

    // Validation & Save (aligned with useNodeEdit)
    isFormValid,
    handleSave,
  };
};
