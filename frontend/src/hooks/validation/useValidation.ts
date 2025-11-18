/**
 * Validation Hook - Using useScript
 *
 * This hook provides state management for validation operations using the existing useScript infrastructure.
 */

import { useState, useCallback, useEffect } from 'react';

import { ValidationPreviewData } from '../../types/features/Validation_Types';
import { useHostManager } from '../useHostManager';
import { useScript } from '../script/useScript';
import { useNavigation } from '../../contexts/navigation/NavigationContext';
import { buildServerUrl } from '../../utils/buildUrlUtils';

// Simplified shared state store for validation - only track report URLs
const validationStore: Record<
  string,
  {
    isValidating: boolean;
    lastReportUrl: string | null; // Store last report URL for "View Last Results"
    preview: ValidationPreviewData | null;
    isLoadingPreview: boolean;
    validationError: string | null;
    validationResult: { success: boolean; duration: number; reportUrl?: string } | null;
    startTime: number | null;
    listeners: Set<() => void>;
  }
> = {};

// Load persisted report URL from localStorage
const loadPersistedReportUrl = (treeId: string): string | null => {
  try {
    const key = `validation_report_url_${treeId}`;
    return localStorage.getItem(key);
  } catch (error) {
    console.warn('Failed to load persisted report URL:', error);
    return null;
  }
};

// Save report URL to localStorage for "View Last Results" functionality
const saveReportUrl = (treeId: string, reportUrl: string) => {
  try {
    const key = `validation_report_url_${treeId}`;
    localStorage.setItem(key, reportUrl);
  } catch (error) {
    console.warn('Failed to save report URL:', error);
  }
};

const getValidationState = (treeId: string) => {
  if (!validationStore[treeId]) {
    const persistedReportUrl = loadPersistedReportUrl(treeId);
    validationStore[treeId] = {
      isValidating: false,
      lastReportUrl: persistedReportUrl,
      preview: null,
      isLoadingPreview: false,
      validationError: null,
      validationResult: null,
      startTime: null,
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
   * Open validation report in new tab
   */
  const openValidationReport = useCallback((reportUrl: string) => {
    console.log(`[@hook:useValidation] Opening validation report: ${reportUrl}`);
    window.open(reportUrl, '_blank');
  }, []);

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
    async (selectedEdgeIds?: string[]) => {
      if (!treeId || !selectedHost || !selectedDeviceId || !state.preview) {
        updateValidationState(treeId, {
          validationError: 'Tree ID, host, device, and preview data are required',
        });
        return;
      }

      updateValidationState(treeId, {
        isValidating: true,
        validationError: null,
        validationResult: null,
        startTime: Date.now(),
      });

      try {
        console.log(`[@hook:useValidation] Starting validation script for tree ${treeId}`);

        // Use the validation script with the existing useScript infrastructure
        const userinterface_name = treeName || currentTreeName || treeId;
        let parameters = `--userinterface ${userinterface_name} --host ${selectedHost.host_name} --device ${selectedDeviceId}`;
        
        // Add selected edges if provided (format: "from-to,from-to,...")
        // Only send --edges parameter if we have selected edges, otherwise validate all
        if (selectedEdgeIds && selectedEdgeIds.length > 0) {
          const edgesParam = selectedEdgeIds.join(',');
          parameters += ` --edges "${edgesParam}"`;
          console.log(`[@hook:useValidation] Running validation with ${selectedEdgeIds.length} selected transitions`);
          console.log(`[@hook:useValidation] DEBUG: Sample edge IDs:`, selectedEdgeIds.slice(0, 3));
          console.log(`[@hook:useValidation] DEBUG: Edges parameter:`, edgesParam.substring(0, 200));
        } else {
          console.log(`[@hook:useValidation] Running validation with ALL transitions (no selection)`);
        }

        const scriptResult = await executeScript(
          'validation',
          selectedHost.host_name,
          selectedDeviceId,
          parameters
        );

        console.log(`[@hook:useValidation] Validation script completed:`, scriptResult);
        console.log(`[@hook:useValidation] DEBUG: script_success=${scriptResult.script_success}, success=${scriptResult.success}, exit_code=${scriptResult.exit_code}`);

        // Calculate duration
        const duration = state.startTime ? (Date.now() - state.startTime) / 1000 : 0;
        
        // CRITICAL: Only use script_success (from SCRIPT_SUCCESS marker in stdout)
        // DO NOT fall back to overall success, as it includes non-validation failures like video capture
        const success = scriptResult.script_success ?? false;
        
        console.log(`[@hook:useValidation] Final success value (script_success only): ${success}`);

        // Save report URL for "View Last Results" functionality
        if (scriptResult.report_url) {
          saveReportUrl(treeId, scriptResult.report_url);
        }

        // Store validation result to show in dialog
        updateValidationState(treeId, {
          lastReportUrl: scriptResult.report_url || null,
          validationResult: {
            success,
            duration,
            reportUrl: scriptResult.report_url,
          },
        });

      } catch (error) {
        console.error('[@hook:useValidation] Validation error:', error);
        updateValidationState(treeId, {
          validationError: error instanceof Error ? error.message : 'Unknown validation error',
        });
      } finally {
        updateValidationState(treeId, {
          isValidating: false,
          startTime: null,
        });
      }
    },
    [treeId, selectedHost, selectedDeviceId, state.preview, executeScript, openValidationReport],
  );

  /**
   * View last validation results by opening the saved report URL
   */
  const viewLastValidationResults = useCallback(() => {
    const state = getValidationState(treeId);
    if (state.lastReportUrl) {
      console.log(`[@hook:useValidation] Opening last validation report for tree ${treeId}: ${state.lastReportUrl}`);
      openValidationReport(state.lastReportUrl);
      return true;
    }
    console.log(`[@hook:useValidation] No last validation report available for tree ${treeId}`);
    return false;
  }, [treeId, openValidationReport]);

  /**
   * Clear validation result (close the results dialog)
   */
  const clearValidationResult = useCallback(() => {
    updateValidationState(treeId, { validationResult: null });
  }, [treeId]);

  return {
    // State
    isValidating: state.isValidating,
    preview: state.preview,
    isLoadingPreview: state.isLoadingPreview,
    validationError: state.validationError,
    validationResult: state.validationResult,

    // Computed properties for button logic
    canRunValidation: !state.isValidating, // Always enabled when not validating
    hasLastResults: !!state.lastReportUrl, // Check if we have a saved report URL

    // Actions
    loadPreview,
    runValidation,
    viewLastValidationResults,
    clearValidationResult,
  };
};