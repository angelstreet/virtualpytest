/**
 * Validation Hook - Using useScript
 *
 * This hook provides state management for validation operations using the existing useScript infrastructure.
 */

import { useState, useCallback, useEffect } from 'react';

import { ValidationResults, ValidationPreviewData } from '../../types/features/Validation_Types';
import { useHostManager } from '../useHostManager';
import { useScript } from '../script/useScript';
import { useNavigation } from '../../contexts/navigation/NavigationContext';
import { buildServerUrl } from '../../utils/buildUrlUtils';

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
  const { treeName, currentTreeName } = useNavigation();
  
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
    try {
      const stdout = scriptResult.stdout || '';
      
      // Parse current validation script output format
      const failedMatch = stdout.match(/❌ Failed: (\d+)/);
      const stepsMatch = stdout.match(/📊 Steps: (\d+)\/(\d+) steps successful/);
      const timeMatch = stdout.match(/⏱️  Total Time: ([\d.]+)s/);
      
      if (!stepsMatch) {
        console.error('Could not parse total steps from validation output');
        return null;
      }

      const successful = stepsMatch ? parseInt(stepsMatch[1]) : 0;
      const total = stepsMatch ? parseInt(stepsMatch[2]) : 0;
      const failed = failedMatch ? parseInt(failedMatch[1]) : total - successful;
      const executionTime = timeMatch ? parseFloat(timeMatch[1]) : 0;

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

      // Create edge results for each step
      const edgeResults: any[] = [];
      for (let i = 1; i <= total; i++) {
        const isSuccess = i <= successful;
        edgeResults.push({
          from: `step_${i}_start`,
          to: `step_${i}_end`,
          fromName: `Step ${i} Start`,
          toName: `Step ${i} End`,
          success: isSuccess,
          skipped: false,
          retryAttempts: 0,
          errors: isSuccess ? [] : ['Step execution failed'],
          actionsExecuted: isSuccess ? 1 : 0,
          totalActions: 1,
          verificationsExecuted: isSuccess ? 1 : 0,
          totalVerifications: 1,
          executionTime: executionTime / total,
          verificationResults: []
        });
      }

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
    if (!treeId || !selectedHost) return;

    updateValidationState(treeId, { isLoadingPreview: true });

    try {
      // Add host_name parameter like navigation preview does
      const baseUrl = buildServerUrl(`/server/validation/preview/${treeId}`);
      const url = new URL(baseUrl);
      url.searchParams.append('host_name', selectedHost.host_name);
      
      const response = await fetch(url.toString());
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
    async () => {
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
        // Use actual tree name from navigation context, not constructed ID
        const userinterface_name = treeName || currentTreeName || treeId;
        console.log(`[@hook:useValidation] Using userinterface_name: '${userinterface_name}' (treeName: '${treeName}', currentTreeName: '${currentTreeName}', treeId: '${treeId}')`);
        const parameters = `${userinterface_name} --host ${selectedHost.host_name} --device ${selectedDeviceId}`;

        const scriptResult = await executeScript(
          'validation',
          selectedHost.host_name,
          selectedDeviceId,
          parameters
        );

        console.log(`[@hook:useValidation] Validation script completed:`, scriptResult);
        console.log(`[@hook:useValidation] Script stdout excerpt:`, scriptResult.stdout?.substring(0, 500) + '...');

        // Always try to parse validation results, regardless of script success status
        // Validation scripts can complete but report validation failures (which is normal)
        const validationResults = parseScriptResultToValidation(scriptResult);
        
        if (validationResults) {
          updateValidationState(treeId, {
            results: validationResults,
            showResults: true,
          });
          console.log(`[@hook:useValidation] Validation results parsed successfully`);
        } else {
          // If we can't parse results, check if the script actually failed to execute
          if (!scriptResult.success && scriptResult.stderr) {
            throw new Error(scriptResult.stderr || 'Validation script execution failed');
          } else {
            throw new Error('Failed to parse validation results from script output');
          }
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