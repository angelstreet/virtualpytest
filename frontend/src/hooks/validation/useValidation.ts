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
      });

      try {
        console.log(`[@hook:useValidation] Starting validation script for tree ${treeId}`);

        // Use the validation script with the existing useScript infrastructure
        const userinterface_name = treeName || currentTreeName || treeId;
        const parameters = `${userinterface_name} --host ${selectedHost.host_name} --device ${selectedDeviceId}`;

        const scriptResult = await executeScript(
          'validation',
          selectedHost.host_name,
          selectedDeviceId,
          parameters
        );

        console.log(`[@hook:useValidation] Validation script completed:`, scriptResult);

        // Check if we have a report URL and open it
        if (scriptResult.report_url) {
          console.log(`[@hook:useValidation] Opening validation report: ${scriptResult.report_url}`);
          
          // Save report URL for "View Last Results" functionality
          saveReportUrl(treeId, scriptResult.report_url);
          updateValidationState(treeId, { lastReportUrl: scriptResult.report_url });
          
          // Open the report URL in a new tab
          openValidationReport(scriptResult.report_url);
        } else {
          throw new Error('No report URL available from validation script');
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

  return {
    // State
    isValidating: state.isValidating,
    preview: state.preview,
    isLoadingPreview: state.isLoadingPreview,
    validationError: state.validationError,

    // Computed properties for button logic
    canRunValidation: !state.isValidating, // Always enabled when not validating
    hasLastResults: !!state.lastReportUrl, // Check if we have a saved report URL

    // Actions
    loadPreview,
    runValidation,
    viewLastValidationResults,
  };
};