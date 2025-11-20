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
      console.log('[@useEdgeEdit] Loaded actions detail from edgeForm:', JSON.stringify(actionSet.actions, null, 2));
      
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
      console.log('[@useEdgeEdit:handleActionsChange] Actions detail:', JSON.stringify(newActions, null, 2));
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
      
      console.log('[@useEdgeEdit:handleActionsChange] Updated action_sets:', JSON.stringify(updatedActionSets, null, 2));
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

  // Handle save operation - INCREMENTAL CACHE UPDATE (no rebuild)
  const handleSave = useCallback(async () => {
    if (!edgeForm) {
      console.error('[useEdgeEdit] Cannot save: edgeForm is null');
      return;
    }
    
    try {
      // 🛡️ VALIDATION: Filter out empty actions from all action sets before saving
      const validatedActionSets = (edgeForm.action_sets || []).map((actionSet: ActionSet) => {
        return {
          ...actionSet,
          actions: (actionSet.actions || []).filter((action: Action) => {
            // Must have a command
            if (!action.command || action.command.trim() === '') {
              console.warn('[useEdgeEdit] 🛡️ Filtered out action with missing command:', action);
              return false;
            }
            return true;
          }),
          retry_actions: (actionSet.retry_actions || []).filter((action: Action) => {
            if (!action.command || action.command.trim() === '') {
              console.warn('[useEdgeEdit] 🛡️ Filtered out retry action with missing command:', action);
              return false;
            }
            return true;
          }),
          failure_actions: (actionSet.failure_actions || []).filter((action: Action) => {
            if (!action.command || action.command.trim() === '') {
              console.warn('[useEdgeEdit] 🛡️ Filtered out failure action with missing command:', action);
              return false;
            }
            return true;
          })
        };
      });
      
      // Update edgeForm with validated action sets
      const validatedEdgeForm = {
        ...edgeForm,
        action_sets: validatedActionSets
      };
      
      const totalBefore = (edgeForm.action_sets || []).reduce((sum, as) => 
        sum + (as.actions?.length || 0) + (as.retry_actions?.length || 0) + (as.failure_actions?.length || 0), 0);
      const totalAfter = validatedActionSets.reduce((sum, as) => 
        sum + (as.actions?.length || 0) + (as.retry_actions?.length || 0) + (as.failure_actions?.length || 0), 0);
      
      console.log(`[useEdgeEdit] 🛡️ Validation: ${totalBefore} → ${totalAfter} actions across all sets`);
      
      // 1. Save to database via context
      console.log('[useEdgeEdit] 💾 Saving edge to database:', validatedEdgeForm.edgeId);
      await saveEdgeWithStateUpdate(validatedEdgeForm);
      console.log('[useEdgeEdit] ✅ Edge saved to database');
      
      // 2. Update cache incrementally on all hosts (no rebuild)
      if (treeId && selectedEdge) {
        console.log('\n[useEdgeEdit] 🔄 Updating cache on all hosts...');
        console.log('[useEdgeEdit]   → Tree ID:', treeId);
        console.log('[useEdgeEdit]   → Edge ID:', edgeForm.edgeId);
        console.log('[useEdgeEdit]   → Source:', selectedEdge.source);
        console.log('[useEdgeEdit]   → Target:', selectedEdge.target);
        
        const { buildServerUrl } = await import('../../utils/buildUrlUtils');
        
        // Build proper edge data structure for cache update
        const edgeDataForCache = {
          id: validatedEdgeForm.edgeId,
          source_node_id: selectedEdge.source,
          target_node_id: selectedEdge.target,
          action_sets: validatedEdgeForm.action_sets,
          default_action_set_id: validatedEdgeForm.default_action_set_id,
          final_wait_time: validatedEdgeForm.final_wait_time,
          priority: validatedEdgeForm.priority,
          threshold: validatedEdgeForm.threshold
        };
        
        console.log('[useEdgeEdit]   → Action sets:', edgeDataForCache.action_sets?.length || 0);
        console.log('[useEdgeEdit]   → Default set:', edgeDataForCache.default_action_set_id);
        
        // Call server to update edge in cache on all hosts (buildServerUrl adds team_id automatically)
        const url = buildServerUrl(`/server/navigation/cache/update-edge`);
        console.log('[useEdgeEdit]   → Calling:', url);
        
        const startTime = Date.now();
        const response = await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            edge: edgeDataForCache,
            tree_id: treeId
          })
        });
        const duration = Date.now() - startTime;
        
        if (!response.ok) {
          const errorText = await response.text();
          console.error('[useEdgeEdit] ❌ Cache update failed:', {
            status: response.status,
            statusText: response.statusText,
            error: errorText,
            duration: `${duration}ms`
          });
        } else {
          const result = await response.json();
          console.log('[useEdgeEdit] ✅ Cache update completed:', {
            duration: `${duration}ms`,
            summary: result.summary,
            message: result.message
          });
          
          // Log per-host results
          if (result.results && result.results.length > 0) {
            console.log('[useEdgeEdit] 📊 Per-host results:');
            result.results.forEach((hostResult: any) => {
              const status = hostResult.cache_exists ? '✅ Updated' : 
                            hostResult.success ? 'ℹ️  Skipped (no cache)' : 
                            '❌ Failed';
              console.log(`[useEdgeEdit]   ${status} - ${hostResult.host}${hostResult.error ? ': ' + hostResult.error : ''}`);
            });
          }
        }
      } else {
        console.log('[useEdgeEdit] ℹ️  Cache update skipped - missing treeId or selectedEdge');
      }
    } catch (error) {
      console.error('[useEdgeEdit] ❌ Failed to save edge or update cache:', error);
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
