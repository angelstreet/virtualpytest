/**
 * useTestCaseExecution Hook
 * 
 * Handles test case execution operations with async polling support.
 * Follows Navigation architecture pattern with buildServerUrl + fetch directly.
 */

import { useCallback } from 'react';
import { buildServerUrl } from '../../utils/buildUrlUtils';
import { resolveGraphVariables } from '../../utils/variableResolutionUtils';

export interface TestCaseExecutionResult {
  success: boolean;
  result_type?: 'success' | 'failure' | 'error';
  execution_time_ms: number;
  step_count: number;
  script_result_id: string;
  error?: string;
  step_results?: any[];
  report_url?: string;  // 🆕 Report URL from R2
  logs_url?: string;    // 🆕 Logs URL from R2
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
  report_url?: string;  // 🆕 Report URL from R2
  logs_url?: string;    // 🆕 Logs URL from R2
  script_outputs?: Record<string, any>;  // Script output values
  block_outputs?: Record<string, any>;   // Block output values
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
  variables?: Record<string, any>;  // 🆕 NEW: Runtime variable values
  metadata?: Record<string, any>;   // 🆕 NEW: Runtime metadata values
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
    scriptInputs?: any[],  // NEW: Script inputs for variable resolution
    scriptVariables?: any[],  // NEW: Script variables for variable resolution
    testcaseName?: string,  // 🆕 NEW: Test case name for execution tracking
    onProgress?: (status: ExecutionStatus) => void  // Real-time progress callback
  ): Promise<TestCaseExecutionResponse> => {
    try {
      // ✅ NEW: Resolve all {variable} references BEFORE sending to backend
      console.log('[useTestCaseExecution] Resolving graph variables before execution...');
      const resolvedGraph = resolveGraphVariables(graph, scriptInputs, scriptVariables);
      
      // Step 1: Start async execution with RESOLVED graph
      const response = await fetch(buildServerUrl(`/server/testcase/execute`), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          graph_json: resolvedGraph,  // ✅ Send resolved graph (not raw graph)
          device_id: deviceId,
          host_name: hostName,
          userinterface_name: userinterfaceName || '',
          testcase_name: testcaseName || 'unsaved_testcase',  // 🆕 NEW: Send test case name
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
      
      // Step 2: Poll for status until completion (pass hostName for routing)
      return await pollExecutionStatus(executionId, hostName, onProgress);
      
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
    hostName: string,  // Include host_name for proxy routing
    onProgress?: (status: ExecutionStatus) => void
  ): Promise<TestCaseExecutionResponse> => {
    const maxAttempts = 300;  // 5 minutes max (300 * 1000ms)
    const pollInterval = 1000;  // Poll every 1 second
    let consecutiveErrors = 0;
    const maxConsecutiveErrors = 3;  // Stop after 3 consecutive errors
    
    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      try {
        // Include host_name as query param so proxy can route correctly
        const statusResponse = await fetch(
          buildServerUrl(`/server/testcase/execution/${executionId}/status?host_name=${encodeURIComponent(hostName)}`)
        );
        
        if (!statusResponse.ok) {
          // If 404, execution was removed from memory - stop polling
          if (statusResponse.status === 404) {
            console.log(`[useTestCaseExecution] Execution ${executionId} not found (404) - stopping poll`);
            return {
              success: false,
              error: 'Execution not found'
            };
          }
          
          // If 400, might be a proxy/session issue - count consecutive errors
          if (statusResponse.status === 400) {
            consecutiveErrors++;
            console.warn(`[useTestCaseExecution] HTTP 400 error (${consecutiveErrors}/${maxConsecutiveErrors})`);
            
            if (consecutiveErrors >= maxConsecutiveErrors) {
              console.log(`[useTestCaseExecution] Too many consecutive 400 errors - execution completed but status unavailable`);
              return {
                success: false,
                result_type: 'error',
                execution_time_ms: 0,
                step_count: 0,
                script_result_id: '',
                error: 'Execution completed but final status unavailable (host connection lost)'
              };
            }
            
            // Wait and retry
            await new Promise(resolve => setTimeout(resolve, pollInterval));
            continue;
          }
          
          throw new Error(`HTTP ${statusResponse.status}`);
        }
        
        // Reset error counter on successful response
        consecutiveErrors = 0;
        
        const statusData = await statusResponse.json();
        
        if (!statusData.success) {
          throw new Error(statusData.error || 'Failed to get status');
        }
        
        const status: ExecutionStatus = statusData.status;
        
        // Call progress callback with current status
        if (onProgress) {
          onProgress(status);
        }
        
        // Check if execution is complete
        if (status.status === 'completed' || status.status === 'failed') {
          console.log(`[useTestCaseExecution] Execution ${executionId} ${status.status} - STOPPING POLL`);
          
          if (status.result) {
            // Return final result with ALL fields including report/logs URLs
            return {
              success: status.result.success,
              result_type: status.result.result_type,
              execution_time_ms: status.result.execution_time_ms,
              step_count: status.result.step_count,
              script_result_id: status.result.script_result_id,
              error: status.result.error,
              step_results: status.result.step_results,
              report_url: status.result.report_url,  // ✅ Include report URL
              logs_url: status.result.logs_url        // ✅ Include logs URL
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
        consecutiveErrors++;
        
        // Stop if too many consecutive errors
        if (consecutiveErrors >= maxConsecutiveErrors) {
          return {
            success: false,
            error: 'Too many polling errors - execution status unavailable'
          };
        }
        
        // Continue polling unless we've hit max attempts
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
