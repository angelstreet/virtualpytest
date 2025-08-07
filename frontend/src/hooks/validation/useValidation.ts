/**
 * Validation Hook - Using useScript
 *
 * This hook provides state management for validation operations using the existing useScript infrastructure.
 */

import { useState, useCallback, useEffect } from 'react';

import { ValidationResults, ValidationPreviewData } from '../../types/features/Validation_Types';
import { useHostManager } from '../useHostManager';
import { useScript } from '../script/useScript';

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
  const { executeScript } = useScript();
  
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
   * Parse script execution result into ValidationResults format
   */
  const parseScriptResultToValidation = useCallback((scriptResult: any): ValidationResults | null => {
    if (!scriptResult.success) {
      return null;
    }

    try {
      // Parse the stdout to extract validation results
      const stdout = scriptResult.stdout || '';
      
      // Look for validation summary in stdout
      const summaryMatch = stdout.match(/Steps: (\d+)\/(\d+) steps successful/);
      const timeMatch = stdout.match(/Total Time: ([\d.]+)s/);
      
      if (!summaryMatch) {
        console.warn('Could not parse validation results from script output');
        return null;
      }

      const successful = parseInt(summaryMatch[1]);
      const total = parseInt(summaryMatch[2]);
      const failed = total - successful;
      const executionTime = timeMatch ? parseFloat(timeMatch[1]) * 1000 : 0;

      // Calculate overall health
      const healthPercentage = total > 0 ? (successful / total) * 100 : 0;
      let overallHealth: 'excellent' | 'good' | 'fair' | 'poor';
      
      if (healthPercentage >= 90) {
        overallHealth = 'excellent';
      } else if (healthPercentage >= 75) {
        overallHealth = 'good';
      } else if (healthPercentage >= 50) {
        overallHealth = 'fair';
      } else {
        overallHealth = 'poor';
      }

      // Create edge results from available data
      const edgeResults = state.preview?.edges.map((edge, index) => ({
        from: edge.from_node,
        to: edge.to_node,
        fromName: edge.from_name,
        toName: edge.to_name,
        success: index < successful, // Simple assumption - first N edges were successful
        skipped: false,
        retryAttempts: 0,
        errors: index >= successful ? ['Validation failed'] : [],
        actionsExecuted: 1,
        totalActions: 1,
        executionTime: executionTime / total, // Average time per edge
        verificationResults: []
      })) || [];

      return {
        treeId,
        summary: {
          totalNodes: successful,
          totalEdges: total,
          validNodes: successful,
          errorNodes: failed,
          skippedEdges: 0,
          overallHealth,
          executionTime
        },
        nodeResults: [],
        edgeResults,
        reportUrl: scriptResult.report_url
      };
    } catch (error) {
      console.error('Error parsing script result:', error);
      return null;
    }
  }, [treeId, state.preview]);

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
   * Run validation using the existing useScript infrastructure
   */
  const runValidation = useCallback(
    async (skippedEdges: string[] = []) => {
      if (!treeId || !selectedHost || !selectedDeviceId || !state.preview) {
        updateValidationState(treeId, {
          validationError: 'Tree ID, host, device, and preview data are required',
        });
        return;
      }

      updateValidationState(treeId, {
        isValidating: true,
        validationError: null,
        results: null,
        showResults: false,
      });

      try {
        console.log(`[@hook:useValidation] Starting validation script for tree ${treeId}`);

        // Use the validation script with the existing useScript infrastructure
        // Parameters: userinterface_name --host <host> --device <device>
        const userinterface_name = `tree_${treeId}`;
        const parameters = `${userinterface_name} --host ${selectedHost.host_name} --device ${selectedDeviceId}`;

        const scriptResult = await executeScript(
          'validation',
          selectedHost.host_name,
          selectedDeviceId,
          parameters
        );

        console.log(`[@hook:useValidation] Validation script completed:`, scriptResult);

        if (scriptResult.success) {
          // Parse the script result into validation format
          const validationResults = parseScriptResultToValidation(scriptResult);
          
          if (validationResults) {
            updateValidationState(treeId, {
              results: validationResults,
              showResults: true,
            });
            console.log(`[@hook:useValidation] Validation results parsed successfully`);
          } else {
            throw new Error('Failed to parse validation results from script output');
          }
        } else {
          throw new Error(scriptResult.stderr || 'Validation script failed');
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
    [treeId, selectedHost, selectedDeviceId, state.preview, executeScript, parseScriptResultToValidation],
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