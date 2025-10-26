/**
 * useTestCaseExecution Hook
 * 
 * Handles test case execution operations with async polling support.
 * Follows Navigation architecture pattern with buildServerUrl + fetch directly.
 */

import { useCallback } from 'react';
import { buildServerUrl } from '../../utils/buildUrlUtils';

export interface TestCaseExecutionResult {
  success: boolean;
  result_type?: 'success' | 'failure' | 'error';
  execution_time_ms: number;
  step_count: number;
  script_result_id: string;
  error?: string;
  step_results?: any[];
}

export interface TestCaseExecutionResponse {
  success: boolean;
  execution_id?: string;  // For async execution
  result_type?: 'success' | 'failure' | 'error';
  execution_time_ms?: number;
  step_count?: number;
  script_result_id?: string;
  error?: string;
  step_results?: any[];
  message?: string;
}

export interface ExecutionStatus {
  execution_id: string;
  status: 'running' | 'completed' | 'failed';
  current_block_id: string | null;
  block_states: {
    [blockId: string]: {
      status: 'success' | 'failure';
      duration: number;
      error?: string;
      message?: string;
    };
  };
  result: TestCaseExecutionResult | null;
  error: string | null;
  elapsed_time_ms: number;
}

export const useTestCaseExecution = () => {
  
  /**
   * Execute a test case directly from graph with async polling
   */
  const executeTestCase = useCallback(async (
    graph: any,  // TestCaseGraph
    deviceId: string,
    hostName: string,
    userinterfaceName?: string,
    onProgress?: (status: ExecutionStatus) => void  // Real-time progress callback
  ): Promise<TestCaseExecutionResponse> => {
    try {
      // Step 1: Start async execution
      const response = await fetch(buildServerUrl(`/server/testcase/execute`), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          graph_json: graph,
          device_id: deviceId,
          host_name: hostName,
          userinterface_name: userinterfaceName || '',
          async_execution: true  // Always use async to prevent timeouts
        }),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP ${response.status}`);
      }
      
      const startData = await response.json();
      
      if (!startData.success) {
        throw new Error(startData.error || 'Failed to start execution');
      }
      
      const executionId = startData.execution_id;
      
      if (!executionId) {
        throw new Error('No execution_id returned');
      }
      
      console.log(`[useTestCaseExecution] Started async execution: ${executionId}`);
      
      // Step 2: Poll for status until completion
      return await pollExecutionStatus(executionId, onProgress);
      
    } catch (error) {
      console.error('[useTestCaseExecution] Error executing test case:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  }, []);

  /**
   * Poll execution status until completion
   */
  const pollExecutionStatus = async (
    executionId: string,
    onProgress?: (status: ExecutionStatus) => void
  ): Promise<TestCaseExecutionResponse> => {
    const maxAttempts = 300;  // 5 minutes max (300 * 1000ms)
    const pollInterval = 1000;  // Poll every 1 second
    
    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      try {
        const statusResponse = await fetch(buildServerUrl(`/server/testcase/execution/${executionId}/status`));
        
        // If execution not found or already cleaned up, stop polling
        if (statusResponse.status === 400 || statusResponse.status === 404) {
          console.log(`[useTestCaseExecution] Execution ${executionId} not found (${statusResponse.status}) - stopping poll`);
          return {
            success: false,
            error: 'Execution not found - it may have already completed'
          };
        }
        
        if (!statusResponse.ok) {
          throw new Error(`HTTP ${statusResponse.status}`);
        }
        
        const statusData = await statusResponse.json();
        
        if (!statusData.success) {
          // If backend explicitly says execution is done/failed, stop polling
          console.log(`[useTestCaseExecution] Backend returned success=false - stopping poll`);
          return {
            success: false,
            error: statusData.error || 'Execution failed'
          };
        }
        
        const status: ExecutionStatus = statusData.status;
        
        // Call progress callback with current status
        if (onProgress) {
          onProgress(status);
        }
        
        // Check if execution is complete
        if (status.status === 'completed' || status.status === 'failed') {
          console.log(`[useTestCaseExecution] Execution ${executionId} ${status.status}`);
          
          if (status.result) {
            // Return final result
            return {
              success: status.result.success,
              result_type: status.result.result_type,
              execution_time_ms: status.result.execution_time_ms,
              step_count: status.result.step_count,
              script_result_id: status.result.script_result_id,
              error: status.result.error,
              step_results: status.result.step_results
            };
          } else {
            // Execution failed before producing result
            return {
              success: false,
              error: status.error || 'Execution failed'
            };
          }
        }
        
        // Still running - wait before next poll
        await new Promise(resolve => setTimeout(resolve, pollInterval));
        
      } catch (error) {
        console.error('[useTestCaseExecution] Error polling status:', error);
        // Only continue polling for network errors, not for "not found" errors
        // If we've hit max attempts, give up
        if (attempt >= maxAttempts - 1) {
          return {
            success: false,
            error: 'Polling timeout: execution status unavailable'
          };
        }
        await new Promise(resolve => setTimeout(resolve, pollInterval));
      }
    }
    
    return {
      success: false,
      error: 'Execution timeout: maximum polling attempts reached'
    };
  };

  /**
   * Get execution status (single poll)
   */
  const getExecutionStatus = useCallback(async (executionId: string): Promise<{ success: boolean; status?: ExecutionStatus; error?: string }> => {
    try {
      const response = await fetch(buildServerUrl(`/server/testcase/execution/${executionId}/status`));
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('[useTestCaseExecution] Error getting status:', error);
      return { success: false, error: error instanceof Error ? error.message : 'Unknown error' };
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
    getExecutionStatus,
    getTestCaseHistory,
  };
};
