/**
 * Script Execution Hook
 *
 * This hook handles script execution operations with progress tracking and API calls.
 * Follows the same patterns as useValidation and other hooks.
 */

import { useState, useCallback } from 'react';
import { buildServerUrl } from '../../utils/buildUrlUtils';

interface ScriptExecutionResult {
  success: boolean;
  stdout: string;
  stderr: string;
  exit_code: number;
  host?: string;
  report_url?: string;
  script_success?: boolean; // Extracted from SCRIPT_SUCCESS marker
}

interface UseScriptReturn {
  executeScript: (
    scriptName: string,
    hostName: string,
    deviceId: string,
    parameters?: string,
  ) => Promise<ScriptExecutionResult>;
  executeMultipleScripts: (
    executions: Array<{
      id: string;
      scriptName: string;
      hostName: string;
      deviceId: string;
      parameters?: string;
    }>,
    onExecutionComplete?: (executionId: string, result: ScriptExecutionResult) => void
  ) => Promise<{ [executionId: string]: ScriptExecutionResult }>;
  isExecuting: boolean;
  executingIds: string[];
  lastResult: ScriptExecutionResult | null;
  error: string | null;
}

// Build script API URLs properly - don't append paths to URLs with query params

export const useScript = (): UseScriptReturn => {
  const [isExecuting, setIsExecuting] = useState(false);
  const [executingIds, setExecutingIds] = useState<string[]>([]);
  const [lastResult, setLastResult] = useState<ScriptExecutionResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const executeScript = useCallback(
    async (
      scriptName: string,
      hostName: string,
      deviceId: string,
      parameters?: string,
    ): Promise<ScriptExecutionResult> => {
      console.log(
        `[@hook:useScript:executeScript] Executing script: ${scriptName} on ${hostName}:${deviceId}${parameters ? ` with parameters: ${parameters}` : ''}`,
      );

      setIsExecuting(true);
      setError(null);

      try {
        const requestBody: any = {
          script_name: scriptName,
          host_name: hostName,
          device_id: deviceId,
        };

        // Add parameters if provided
        if (parameters && parameters.trim()) {
          requestBody.parameters = parameters.trim();
        }

        // Start async script execution
        const response = await fetch(buildServerUrl('/server/script/execute'), {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(requestBody),
        });

        const initialResult = await response.json();

        // Handle async task response (202 status code)
        if (response.status === 202 && initialResult.task_id) {
          console.log(
            `[@hook:useScript:executeScript] Script started async with task_id: ${initialResult.task_id}`,
          );

          // Poll for task completion
          const taskId = initialResult.task_id;
          const pollInterval = 10000; // 10 seconds - less frequent polling for long scripts
          const maxWaitTime = 7200000; // 2 hours - validation scripts can take very long
          const startTime = Date.now();

          while (Date.now() - startTime < maxWaitTime) {
            await new Promise((resolve) => setTimeout(resolve, pollInterval));

            try {
              const statusResponse = await fetch(buildServerUrl(`/server/script/status/${taskId}`));
              const statusResult = await statusResponse.json();

              if (statusResult.success && statusResult.task) {
                const task = statusResult.task;

                if (task.status === 'completed') {
                  console.log(`[@hook:useScript:executeScript] Script completed successfully`);
                  const result: ScriptExecutionResult = {
                    success: task.result?.success || false,
                    stdout: task.result?.stdout || '',
                    stderr: task.result?.stderr || '',
                    exit_code: task.result?.exit_code || 0,
                    host: hostName,
                    report_url: task.result?.report_url,
                  };
                  setLastResult(result);
                  return result;
                } else if (task.status === 'failed') {
                  console.log(`[@hook:useScript:executeScript] Script failed:`, task.error);
                  throw new Error(task.error || 'Script execution failed');
                }
                // Continue polling if status is still 'started'
              }
            } catch (pollError) {
              console.warn(`[@hook:useScript:executeScript] Error polling task status:`, pollError);
              // Continue polling despite error
            }
          }

          throw new Error('Script execution timed out');
        } else {
          // Handle synchronous response or error
          if (!response.ok) {
            throw new Error(
              initialResult.stderr || initialResult.error || 'Script execution failed',
            );
          }

          console.log(`[@hook:useScript:executeScript] Script completed:`, initialResult);
          setLastResult(initialResult);
          return initialResult;
        }
      } catch (error) {
        console.error(`[@hook:useScript:executeScript] Error executing script:`, error);
        const errorMessage = error instanceof Error ? error.message : 'Unknown error';
        setError(errorMessage);
        throw error;
      } finally {
        setIsExecuting(false);
      }
    },
    [],
  );

  // Helper function for polling individual tasks with completion callback
  const pollTaskCompletion = useCallback(async (
    taskId: string, 
    hostName: string,
    onComplete: (result: ScriptExecutionResult) => void
  ): Promise<ScriptExecutionResult> => {
    const pollInterval = 10000; // 10 seconds - less frequent polling for long scripts
    const maxWaitTime = 7200000; // 2 hours - validation scripts can take very long
    const startTime = Date.now();

    while (Date.now() - startTime < maxWaitTime) {
      await new Promise((resolve) => setTimeout(resolve, pollInterval));

      try {
        const statusResponse = await fetch(buildServerUrl(`/server/script/status/${taskId}`));
        const statusResult = await statusResponse.json();

        if (statusResult.success && statusResult.task) {
          const task = statusResult.task;

          if (task.status === 'completed') {
            const result: ScriptExecutionResult = {
              success: task.result?.success || false,
              stdout: task.result?.stdout || '',
              stderr: task.result?.stderr || '',
              exit_code: task.result?.exit_code || 0,
              host: hostName,
              report_url: task.result?.report_url,
              script_success: task.result?.script_success, // Use field directly from host
            };
            
            // IMMEDIATE CALLBACK: Notify completion right away
            onComplete(result);
            return result;
          } else if (task.status === 'failed') {
            const errorResult: ScriptExecutionResult = {
              success: false,
              stdout: '',
              stderr: task.error || 'Script execution failed',
              exit_code: 1,
              host: hostName,
            };
            
            onComplete(errorResult);
            return errorResult;
          }
        }
      } catch (pollError) {
        console.warn(`[@hook:useScript] Error polling task ${taskId}:`, pollError);
      }
    }

    const timeoutResult: ScriptExecutionResult = {
      success: false,
      stdout: '',
      stderr: `Script execution timed out for task ${taskId}`,
      exit_code: 1,
      host: hostName,
    };
    
    onComplete(timeoutResult);
    return timeoutResult;
  }, []);

  const executeMultipleScripts = useCallback(async (
    executions: Array<{
      id: string;
      scriptName: string;
      hostName: string;
      deviceId: string;
      parameters?: string;
    }>,
    onExecutionComplete?: (executionId: string, result: ScriptExecutionResult) => void
  ) => {
    console.log(`[@hook:useScript:executeMultipleScripts] Starting ${executions.length} concurrent executions`);
    
    setIsExecuting(true);
    setExecutingIds(executions.map(e => e.id));
    setError(null);

    const results: { [executionId: string]: ScriptExecutionResult } = {};

    // Start all executions in parallel with live callback
    const promises = executions.map(async (execution) => {
      try {
        console.log(`[@hook:useScript] Starting execution ${execution.id} on ${execution.hostName}:${execution.deviceId}`);
        
        const requestBody: any = {
          script_name: execution.scriptName,
          host_name: execution.hostName,
          device_id: execution.deviceId,
        };

        if (execution.parameters && execution.parameters.trim()) {
          requestBody.parameters = execution.parameters.trim();
        }

        const response = await fetch(buildServerUrl('/server/script/execute'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(requestBody),
        });

        const initialResult = await response.json();

        if (response.status === 202 && initialResult.task_id) {
          console.log(`[@hook:useScript] Execution ${execution.id} started with task_id: ${initialResult.task_id}`);

          // Poll with live callback
          const result = await pollTaskCompletion(
            initialResult.task_id, 
            execution.hostName,
            (result) => {
              // LIVE UPDATE: Call callback immediately when this execution completes
              results[execution.id] = result;
              setExecutingIds(prev => prev.filter(id => id !== execution.id));
              onExecutionComplete?.(execution.id, result);
              console.log(`[@hook:useScript] Execution ${execution.id} completed with exit_code: ${result.exit_code}`);
            }
          );
          
          return result;
        } else {
          if (!response.ok) {
            throw new Error(initialResult.stderr || initialResult.error || 'Script execution failed');
          }
          
          // Extract SCRIPT_SUCCESS marker for immediate completion
          if (initialResult.stdout && initialResult.stdout.includes('SCRIPT_SUCCESS:')) {
            const successMatch = initialResult.stdout.match(/SCRIPT_SUCCESS:(true|false)/);
            if (successMatch) {
              initialResult.script_success = successMatch[1] === 'true';
            }
          }
          
          // Immediate completion for synchronous response
          results[execution.id] = initialResult;
          setExecutingIds(prev => prev.filter(id => id !== execution.id));
          onExecutionComplete?.(execution.id, initialResult);
          
          return initialResult;
        }
      } catch (error) {
        console.error(`[@hook:useScript] Error in execution ${execution.id}:`, error);
        const errorResult: ScriptExecutionResult = {
          success: false,
          stdout: '',
          stderr: error instanceof Error ? error.message : 'Unknown error',
          exit_code: 1,
          host: execution.hostName,
        };
        
        results[execution.id] = errorResult;
        setExecutingIds(prev => prev.filter(id => id !== execution.id));
        onExecutionComplete?.(execution.id, errorResult);
        
        return errorResult;
      }
    });

    // Wait for ALL executions to complete before allowing new ones
    await Promise.allSettled(promises);
    
    setIsExecuting(false);
    setExecutingIds([]);
    
    console.log(`[@hook:useScript:executeMultipleScripts] All ${executions.length} executions completed`);
    return results;
  }, [pollTaskCompletion]);

  return {
    executeScript,
    executeMultipleScripts,
    isExecuting,
    executingIds,
    lastResult,
    error,
  };
};
