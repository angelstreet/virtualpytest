/**
 * useTestCaseExecution Hook
 * 
 * Handles test case execution operations.
 * Follows Navigation architecture pattern with buildServerUrl + fetch directly.
 */

import { useCallback } from 'react';
import { buildServerUrl } from '../../utils/buildUrlUtils';

export interface TestCaseExecutionResult {
  success: boolean;
  execution_time_ms: number;
  step_count: number;
  script_result_id: string;
  error?: string;
  step_results?: any[];
}

export const useTestCaseExecution = () => {
  
  /**
   * Execute a test case
   */
  const executeTestCase = useCallback(async (
    testcaseId: string, 
    deviceId: string
  ): Promise<{ success: boolean; result?: TestCaseExecutionResult; error?: string }> => {
    try {
      const response = await fetch(buildServerUrl(`/server/testcase/${testcaseId}/execute`), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ device_id: deviceId }),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('[useTestCaseExecution] Error executing test case:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  }, []);

  /**
   * Get execution history for a test case
   */
  const getTestCaseHistory = useCallback(async (testcaseId: string): Promise<{ success: boolean; history: any[] }> => {
    try {
      const response = await fetch(buildServerUrl(`/server/testcase/${testcaseId}/history`));
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('[useTestCaseExecution] Error getting history:', error);
      return { success: false, history: [] };
    }
  }, []);

  return {
    executeTestCase,
    getTestCaseHistory,
  };
};

