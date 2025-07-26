/**
 * Validation Hook
 *
 * This hook provides state management for validation operations.
 */

import { useState, useCallback, useEffect } from 'react';

import { ValidationResults, ValidationPreviewData } from '../../types/features/Validation_Types';
import { useHostManager } from '../useHostManager';

// Progress tracking types
interface ValidationStep {
  stepNumber: number;
  totalSteps: number;
  fromNode: string;
  toNode: string;
  fromName: string;
  toName: string;
  status: 'pending' | 'running' | 'success' | 'failed' | 'skipped';
  error?: string;
  executionTime?: number;
}

interface ValidationProgress {
  currentStep: number;
  totalSteps: number;
  steps: ValidationStep[];
  isRunning: boolean;
}

// Shared state store for validation
const validationStore: Record<
  string,
  {
    isValidating: boolean;
    results: ValidationResults | null;
    showResults: boolean;
    preview: ValidationPreviewData | null;
    isLoadingPreview: boolean;
    validationError: string | null;
    progress: ValidationProgress | null;
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
      progress: null,
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

export const useValidation = (treeId: string) => {
  const { selectedHost, selectedDeviceId } = useHostManager();
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
      const data: ValidationPreviewData = await response.json();

      if (data.success) {
        updateValidationState(treeId, { preview: data });
      } else {
        console.error('Failed to load validation preview:', data.error);
        updateValidationState(treeId, {
          validationError: data.error || 'Failed to load validation preview',
        });
      }
    } catch (error) {
      console.error('Error loading validation preview:', error);
      updateValidationState(treeId, {
        validationError: error instanceof Error ? error.message : 'Unknown error',
      });
    } finally {
      updateValidationState(treeId, { isLoadingPreview: false });
    }
  }, [treeId]);

  /**
   * Run validation with step-by-step progress tracking
   */
  const runValidation = useCallback(
    async (skippedEdges: string[] = []) => {
      if (!treeId || !selectedHost || !state.preview) {
        updateValidationState(treeId, {
          validationError: 'Tree ID, host, and preview data are required',
        });
        return;
      }

      console.log('[@hook:useValidation] Setting isValidating to true');

      // Filter out skipped edges to get edges to validate
      const edgesToValidate = state.preview.edges.filter(
        (edge) => !skippedEdges.includes(`${edge.from_node}-${edge.to_node}`),
      );

      // Initialize progress tracking
      const initialSteps: ValidationStep[] = edgesToValidate.map((edge, index) => ({
        stepNumber: index + 1,
        totalSteps: edgesToValidate.length,
        fromNode: edge.from_node,
        toNode: edge.to_node,
        fromName: edge.from_name,
        toName: edge.to_name,
        status: 'pending' as const,
      }));

      updateValidationState(treeId, {
        isValidating: true,
        validationError: null,
        results: null,
        showResults: false,
        progress: {
          currentStep: 0,
          totalSteps: edgesToValidate.length,
          steps: initialSteps,
          isRunning: true,
        },
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

        // Handle async task response (202 status code)
        if (response.status === 202 && initialResult.task_id) {
          console.log(
            `[@hook:useValidation] Validation started async with task_id: ${initialResult.task_id}`,
          );

          // Poll for task completion with progress updates
          const taskId = initialResult.task_id;
          const pollInterval = 2000; // 2 seconds
          const maxWaitTime = 600000; // 10 minutes for validation
          const startTime = Date.now();

          while (Date.now() - startTime < maxWaitTime) {
            await new Promise((resolve) => setTimeout(resolve, pollInterval));

            try {
              const statusResponse = await fetch(`/server/validation/status/${taskId}`);
              const statusResult = await statusResponse.json();

              if (statusResult.success && statusResult.task) {
                const task = statusResult.task;

                // Update progress if available
                if (task.progress) {
                  const progressSteps: ValidationStep[] = task.progress.steps.map((step: any) => ({
                    stepNumber: step.stepNumber,
                    totalSteps: task.progress.totalSteps,
                    fromNode: '', // Not used in current progress display
                    toNode: '', // Not used in current progress display
                    fromName: step.fromName,
                    toName: step.toName,
                    status: step.status,
                    executionTime: step.executionTime,
                  }));

                  updateValidationState(treeId, {
                    progress: {
                      currentStep: task.progress.currentStep,
                      totalSteps: task.progress.totalSteps,
                      steps: progressSteps,
                      isRunning: task.status === 'started',
                    },
                  });
                }

                if (task.status === 'completed') {
                  console.log(`[@hook:useValidation] Validation completed successfully`);

                  const { summary, results, report_url } = task.result;

                  // Convert API response to ValidationResults format
                  const validationResults: ValidationResults = {
                    treeId,
                    summary: {
                      totalNodes: summary.totalTested,
                      totalEdges: summary.totalTested,
                      validNodes: summary.successful,
                      errorNodes: summary.failed,
                      skippedEdges: summary.skipped,
                      overallHealth: summary.overallHealth,
                      executionTime: results.reduce(
                        (sum: number, r: any) => sum + r.execution_time,
                        0,
                      ),
                    },
                    nodeResults: [],
                    edgeResults: results.map((result: any) => ({
                      from: result.from_node,
                      to: result.to_node,
                      fromName: result.from_name,
                      toName: result.to_name,
                      success: result.success,
                      skipped: result.skipped,
                      retryAttempts: 0,
                      errors: result.error_message ? [result.error_message] : [],
                      actionsExecuted: result.actions_executed,
                      totalActions: result.total_actions,
                      executionTime: result.execution_time,
                    })),
                    reportUrl: report_url, // Include report URL from API response
                  };

                  console.log('[@hook:useValidation] Setting results and showResults to true');
                  updateValidationState(treeId, {
                    results: validationResults,
                    showResults: true,
                    progress: null, // Clear progress when showing results
                  });

                  console.log(
                    `[@hook:useValidation] Validation completed: ${summary.successful}/${summary.totalTested} successful`,
                  );
                  return;
                } else if (task.status === 'failed') {
                  console.log(`[@hook:useValidation] Validation failed:`, task.error);
                  throw new Error(task.error || 'Validation execution failed');
                }
                // Continue polling if status is still 'started'
              }
            } catch (pollError) {
              console.warn(`[@hook:useValidation] Error polling task status:`, pollError);
              // Continue polling despite error
            }
          }

          throw new Error('Validation execution timed out');
        } else {
          // Handle synchronous response or error (backward compatibility)
          if (!response.ok) {
            throw new Error(initialResult.error || 'Validation failed');
          }

          console.log(`[@hook:useValidation] Validation completed synchronously:`, initialResult);

          const { summary, results, report_url } = initialResult;

          const validationResults: ValidationResults = {
            treeId,
            summary: {
              totalNodes: summary.totalTested,
              totalEdges: summary.totalTested,
              validNodes: summary.successful,
              errorNodes: summary.failed,
              skippedEdges: summary.skipped,
              overallHealth: summary.overallHealth,
              executionTime: results.reduce((sum: number, r: any) => sum + r.execution_time, 0),
            },
            nodeResults: [],
            edgeResults: results.map((result: any) => ({
              from: result.from_node,
              to: result.to_node,
              fromName: result.from_name,
              toName: result.to_name,
              success: result.success,
              skipped: result.skipped,
              retryAttempts: 0,
              errors: result.error_message ? [result.error_message] : [],
              actionsExecuted: result.actions_executed,
              totalActions: result.total_actions,
              executionTime: result.execution_time,
            })),
            reportUrl: report_url,
          };

          updateValidationState(treeId, {
            results: validationResults,
            showResults: true,
            progress: null,
          });
        }
      } catch (error) {
        console.error('[@hook:useValidation] Error running validation:', error);
        updateValidationState(treeId, {
          validationError: error instanceof Error ? error.message : 'Unknown error',
          progress: null,
        });
      } finally {
        console.log('[@hook:useValidation] Setting isValidating to false');
        updateValidationState(treeId, { isValidating: false });
      }
    },
    [treeId, selectedHost, selectedDeviceId, state.preview],
  );

  /**
   * Clear validation state
   */
  const clearValidation = useCallback(() => {
    updateValidationState(treeId, {
      results: null,
      showResults: false,
      preview: null,
      validationError: null,
      progress: null,
    });
  }, [treeId]);

  /**
   * Set show results
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
    validationError: state.validationError,
    preview: state.preview,
    isLoadingPreview: state.isLoadingPreview,
    showResults: state.showResults,
    progress: state.progress,

    // Actions
    loadPreview,
    runValidation,
    clearValidation,
    setShowResults,

    // Computed
    hasResults: !!state.results,
    canRunValidation: !state.isValidating && !!selectedHost && !!treeId,
  };
};
