/**
 * Validation Hook - Simplified
 *
 * This hook provides state management for validation operations.
 */

import { useState, useCallback, useEffect } from 'react';

import { ValidationResults, ValidationPreviewData } from '../../types/features/Validation_Types';
import { useHostManager } from '../useHostManager';

// Simplified shared state store for validation
const validationStore: Record<
  string,
  {
    isValidating: boolean;
    results: ValidationResults | null;
    showResults: boolean;
    preview: ValidationPreviewData | null;
    isLoadingPreview: boolean;
    validationError: string | null;
    listeners: Set<() => void>;
  }
> = {};

const getValidationState = (treeId: string) => {
  if (!validationStore[treeId]) {
    validationStore[treeId] = {
      isValidating: false,
      results: null,
      showResults: false,
      preview: null,
      isLoadingPreview: false,
      validationError: null,
      listeners: new Set(),
    };
  }
  return validationStore[treeId];
};

const updateValidationState = (
  treeId: string,
  updates: Partial<(typeof validationStore)[string]>,
) => {
  const state = getValidationState(treeId);
  Object.assign(state, updates);
  // Notify all listeners
  state.listeners.forEach((listener) => listener());
};

export const useValidation = (treeId: string, providedHost?: any, providedDeviceId?: string | null) => {
  const { selectedHost: contextHost, selectedDeviceId: contextDeviceId } = useHostManager();
  
  // Use provided values if available, otherwise fall back to context
  const selectedHost = providedHost || contextHost;
  const selectedDeviceId = providedDeviceId || contextDeviceId;
  const [, forceUpdate] = useState({});

  // Force re-render when state changes
  const rerender = useCallback(() => {
    forceUpdate({});
  }, []);

  // Subscribe to state changes
  useEffect(() => {
    const state = getValidationState(treeId);
    state.listeners.add(rerender);

    return () => {
      state.listeners.delete(rerender);
    };
  }, [treeId, rerender]);

  const state = getValidationState(treeId);

  /**
   * Load validation preview
   */
  const loadPreview = useCallback(async () => {
    if (!treeId) return;

    updateValidationState(treeId, { isLoadingPreview: true });

    try {
      const response = await fetch(`/server/validation/preview/${treeId}`);
      const result = await response.json();

      if (result.success) {
        updateValidationState(treeId, { preview: result });
      } else {
        updateValidationState(treeId, { validationError: result.error || 'Failed to load preview' });
      }
    } catch (error) {
      updateValidationState(treeId, {
        validationError: error instanceof Error ? error.message : 'Failed to load preview',
      });
    } finally {
      updateValidationState(treeId, { isLoadingPreview: false });
    }
  }, [treeId]);

  /**
   * Run validation with simple loading state
   */
  const runValidation = useCallback(
    async (skippedEdges: string[] = []) => {
      if (!treeId || !selectedHost || !state.preview) {
        updateValidationState(treeId, {
          validationError: 'Tree ID, host, and preview data are required',
        });
        return;
      }

      // Filter out skipped edges to get edges to validate
      const edgesToValidate = state.preview.edges.filter(
        (edge) => !skippedEdges.includes(`${edge.from_node}-${edge.to_node}`),
      );

      updateValidationState(treeId, {
        isValidating: true,
        validationError: null,
        results: null,
        showResults: false,
      });

      try {
        console.log(`[@hook:useValidation] Starting validation for tree ${treeId}`);

        // Start async validation
        const response = await fetch(`/server/validation/run/${treeId}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            host: selectedHost,
            device_id: selectedDeviceId,
            edges_to_validate: edgesToValidate,
          }),
        });

        const initialResult = await response.json();

        if (response.status === 202 && initialResult.task_id) {
          console.log(`[@hook:useValidation] Validation started with task_id: ${initialResult.task_id}`);

          // Simple polling for completion (no progress updates)
          const taskId = initialResult.task_id;
          const pollInterval = 3000; // 3 seconds
          const maxWaitTime = 600000; // 10 minutes
          const startTime = Date.now();

          while (Date.now() - startTime < maxWaitTime) {
            await new Promise((resolve) => setTimeout(resolve, pollInterval));

            const statusResponse = await fetch(`/server/validation/status/${taskId}`);
            const statusResult = await statusResponse.json();

            if (statusResult.success && statusResult.task) {
              const task = statusResult.task;

              if (task.status === 'completed') {
                console.log(`[@hook:useValidation] Validation completed successfully`);

                // Use the results directly from ScriptExecutor format
                updateValidationState(treeId, {
                  results: task.result, // ScriptExecutor result already in correct format
                  showResults: true,
                });
                return;
              } else if (task.status === 'failed') {
                throw new Error(task.error || 'Validation execution failed');
              }
            }
          }

          throw new Error('Validation execution timed out');
        } else {
          throw new Error(initialResult.error || 'Validation failed to start');
        }
      } catch (error) {
        console.error('[@hook:useValidation] Validation error:', error);
        updateValidationState(treeId, {
          validationError: error instanceof Error ? error.message : 'Unknown validation error',
        });
      } finally {
        updateValidationState(treeId, {
          isValidating: false,
        });
      }
    },
    [treeId, selectedHost, selectedDeviceId, state.preview],
  );

  /**
   * Set results visibility
   */
  const setShowResults = useCallback(
    (show: boolean) => {
      updateValidationState(treeId, { showResults: show });
    },
    [treeId],
  );

  return {
    // State
    isValidating: state.isValidating,
    validationResults: state.results,
    showResults: state.showResults,
    preview: state.preview,
    isLoadingPreview: state.isLoadingPreview,
    validationError: state.validationError,

    // Computed properties for button logic
    canRunValidation: !state.isValidating, // Always enabled when not validating
    hasResults: !!state.results,

    // Actions
    loadPreview,
    runValidation,
    setShowResults,
  };
};