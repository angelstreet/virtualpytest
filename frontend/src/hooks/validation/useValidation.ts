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
    if (!scriptResult.success) {
      return null;
    }

    try {
      // Parse the stdout to extract validation results
      const stdout = scriptResult.stdout || '';
      
      // Look for validation summary in stdout with multiple patterns
      let summaryMatch = stdout.match(/Steps: (\d+)\/(\d+) steps successful/);
      
      // Fallback patterns for different output formats
      if (!summaryMatch) {
        // Try alternative patterns
        const successfulMatch = stdout.match(/✅ Successful: (\d+)/);
        const failedMatch = stdout.match(/❌ Failed: (\d+)/);
        const totalMatch = stdout.match(/📊 Steps: (\d+) total/);
        
        if (successfulMatch && (failedMatch || totalMatch)) {
          const successful = parseInt(successfulMatch[1]);
          const failed = failedMatch ? parseInt(failedMatch[1]) : 0;
          const total = totalMatch ? parseInt(totalMatch[1]) : successful + failed;
          summaryMatch = [null, successful.toString(), total.toString()]; // Fake match array
        }
      }
      
      if (!summaryMatch) {
        console.warn('Could not parse validation results from script output');
        console.warn('Script stdout:', stdout);
        return null;
      }

      const timeMatch = stdout.match(/Total Time: ([\d.]+)s/);
      const executionTime = timeMatch ? parseFloat(timeMatch[1]) * 1000 : 0;

      // Parse structured step data from validation output - NO FALLBACK
      const edgeResults: any[] = [];
      const structuredDataMatch = stdout.match(/=== VALIDATION_STEPS_DATA_START ===([\s\S]*?)=== VALIDATION_STEPS_DATA_END ===/);
      
      if (!structuredDataMatch) {
        console.error('[@hook:useValidation] No structured validation data found in stdout');
        console.error('[@hook:useValidation] Full stdout length:', stdout.length);
        console.error('[@hook:useValidation] Script stdout (last 2000 chars):', stdout.substring(Math.max(0, stdout.length - 2000)));
        console.error('[@hook:useValidation] Looking for markers in stdout:', {
          hasStartMarker: stdout.includes('=== VALIDATION_STEPS_DATA_START ==='),
          hasEndMarker: stdout.includes('=== VALIDATION_STEPS_DATA_END ===')
        });
        return null;
      }
      
      console.log('[@hook:useValidation] Found structured validation data, parsing...');
      const stepLines = structuredDataMatch[1].trim().split('\n');
      
      for (const line of stepLines) {
        if (line.startsWith('STEP:')) {
          const parts = line.split('|');
          if (parts.length >= 10) {
            const fromName = parts[1];
            const toName = parts[2];
            const status = parts[3];
            const duration = parseFloat(parts[4]);
            const errorMessage = parts[5] || '';
            const actionsExecuted = parseInt(parts[6]) || 0;
            const totalActions = parseInt(parts[7]) || 0;
            const verificationsExecuted = parseInt(parts[8]) || 0;
            const totalVerifications = parseInt(parts[9]) || 0;
            
            edgeResults.push({
              from: fromName.toLowerCase().replace(/[^a-z0-9]/g, '_'),
              to: toName.toLowerCase().replace(/[^a-z0-9]/g, '_'),
              fromName,
              toName,
              success: status === 'PASS',
              skipped: false,
              retryAttempts: 0,
              errors: errorMessage ? [errorMessage] : [],
              actionsExecuted,
              totalActions,
              verificationsExecuted,
              totalVerifications,
              executionTime: duration * 1000, // Convert to milliseconds
              verificationResults: []
            });
          } else {
            console.warn('[@hook:useValidation] Invalid step data format (expected 10 fields):', line);
            console.warn('[@hook:useValidation] Received:', parts.length, 'fields in line:', line);
          }
        }
      }
      
      if (edgeResults.length === 0) {
        console.error('[@hook:useValidation] No valid step data parsed from structured output');
        return null;
      }
      
      console.log(`[@hook:useValidation] Successfully parsed ${edgeResults.length} validation steps`);

      // Calculate summary from actual parsed step data
      const actualSuccessful = edgeResults.filter(step => step.success).length;
      const actualFailed = edgeResults.filter(step => !step.success).length;
      const actualTotal = edgeResults.length;
      
      // Recalculate health based on actual parsed data
      const actualHealthPercentage = actualTotal > 0 ? (actualSuccessful / actualTotal) * 100 : 0;
      let actualOverallHealth: 'excellent' | 'good' | 'fair' | 'poor';
      
      if (actualHealthPercentage >= 90) {
        actualOverallHealth = 'excellent';
      } else if (actualHealthPercentage >= 75) {
        actualOverallHealth = 'good';
      } else if (actualHealthPercentage >= 50) {
        actualOverallHealth = 'fair';
      } else {
        actualOverallHealth = 'poor';
      }

      console.log(`[@hook:useValidation] Actual results: ${actualSuccessful}/${actualTotal} successful (${actualHealthPercentage.toFixed(1)}%)`);

      return {
        treeId,
        summary: {
          totalNodes: actualSuccessful,
          totalEdges: actualTotal,
          validNodes: actualSuccessful,
          errorNodes: actualFailed,
          skippedEdges: 0,
          overallHealth: actualOverallHealth,
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