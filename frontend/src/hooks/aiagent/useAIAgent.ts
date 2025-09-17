import { useState, useCallback } from 'react';

import { Host, Device } from '../../types/common/Host_Types';

import { buildServerUrl } from '../../utils/buildUrlUtils';
import { useToast } from '../useToast';
interface ExecutionLogEntry {
  timestamp: string;
  type: string;
  action_type: string;
  value: any;
  description: string;
}

interface UseAIAgentProps {
  host: Host;
  device: Device;
  enabled?: boolean;
}

interface UseAIAgentReturn {
  // State
  isExecuting: boolean;
  currentStep: string;
  executionLog: ExecutionLogEntry[];
  taskInput: string;
  errorMessage: string | null;
  taskResult: { success: boolean; message: string } | null;

  // AI plan from backend
  aiPlan: any;
  isPlanFeasible: boolean;

  // Actions
  setTaskInput: (input: string) => void;
  executeTask: () => Promise<void>;
  stopExecution: () => Promise<void>;
  clearLog: () => void;
}

export const useAIAgent = ({ host, device, enabled = true }: UseAIAgentProps): UseAIAgentReturn => {
  const [isExecuting, setIsExecuting] = useState(false);
  const [currentStep, setCurrentStep] = useState('');
  const [executionLog, setExecutionLog] = useState<ExecutionLogEntry[]>([]);
  const [taskInput, setTaskInput] = useState('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [taskResult, setTaskResult] = useState<{ success: boolean; message: string } | null>(null);
  
  // Toast notifications
  const toast = useToast();

  // AI plan response
  const [aiPlan, setAiPlan] = useState<any>(null);
  const [isPlanFeasible, setIsPlanFeasible] = useState<boolean>(true);

  // Helper function to enhance error messages for specific error types
  const enhanceErrorMessage = useCallback((error: string) => {
    if (error.includes('429') || error.includes('rate limit')) {
      return '🤖 AI service is temporarily busy. Please wait a moment and try again.';
    }
    if (error.includes('No path found to')) {
      const nodeMatch = error.match(/No path found to '([^']+)'/);
      const nodeName = nodeMatch ? nodeMatch[1] : 'target location';
      return `🧭 Cannot navigate to "${nodeName}" - screen not found in navigation tree.`;
    }
    return error; // Return original error for other cases
  }, []);

  const executeTask = useCallback(async () => {
    if (!enabled || !taskInput.trim() || isExecuting) return;

    try {
      setIsExecuting(true);
      setErrorMessage(null);
      setTaskResult(null);
      setCurrentStep('Asking AI for execution plan...');
      setExecutionLog([]);
      setAiPlan(null);
      setIsPlanFeasible(true);

      // Show task start notification
      toast.showInfo(`🤖 Starting AI task`, { duration: 3000 });

      console.log('[useAIAgent] Executing task:', taskInput);

      const response = await fetch(buildServerUrl('/server/aiagent/executeTask'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          host: host,
          device_id: device?.device_id,
          task_description: taskInput.trim(),
        }),
      });

      const result = await response.json();
      console.log('[useAIAgent] Task execution result:', result);

      if (response.ok && result.success) {
        // Update initial state from the response
        setCurrentStep(result.current_step || 'Plan generated');
        setExecutionLog(result.execution_log || []);

        // Extract AI plan from execution_log
        const executionLog = result.execution_log || [];
        const planEntry = executionLog.find(
          (entry: ExecutionLogEntry) =>
            entry.action_type === 'plan_generated' && entry.type === 'ai_plan',
        );

        if (planEntry && planEntry.value) {
          setAiPlan(planEntry.value);
          setIsPlanFeasible(planEntry.value.feasible !== false);
        }

        // Start polling for status updates (following useValidation pattern)
        const pollInterval = 1000; // 1 second - more frequent than validation since AI tasks are usually shorter
        const maxWaitTime = 300000; // 5 minutes max wait time
        const startTime = Date.now();

        console.log('[useAIAgent] Starting status polling for real-time updates');

        const pollStatus = async () => {
          while (Date.now() - startTime < maxWaitTime) {
            await new Promise((resolve) => setTimeout(resolve, pollInterval));

            try {
              const statusResponse = await fetch(buildServerUrl('/server/aiagent/getStatus'), {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                  host: host,
                  device_id: device?.device_id,
                }),
              });

              const statusResult = await statusResponse.json();
              console.log('[useAIAgent] Status poll result:', statusResult);

              if (statusResult.success) {
                // Update current step and execution log with latest data
                const prevLogLength = executionLog.length;
                const newLog = statusResult.execution_log || [];
                setCurrentStep(statusResult.current_step || 'Processing...');
                setExecutionLog(newLog);

                // Check for new log entries and show toast notifications
                if (newLog.length > prevLogLength) {
                  const newEntries = newLog.slice(prevLogLength);
                  console.log('[useAIAgent] Processing new log entries:', newEntries);
                  for (const entry of newEntries) {
                    console.log('[useAIAgent] Processing entry:', entry.action_type, entry);
                    if (entry.action_type === 'plan_ready') {
                      const stepData = entry.value;
                      console.log('[useAIAgent] Showing plan ready toast');
                      toast.showInfo(`📋 Plan ready: ${stepData.total_steps} steps`, { duration: 2000 });
                    } else if (entry.action_type === 'step_start') {
                      const stepData = entry.value;
                      console.log('[useAIAgent] Showing step start toast');
                      toast.showInfo(`⚡ Step ${stepData.step}/${stepData.total_steps}`, { duration: 2000 });
                    } else if (entry.action_type === 'step_success') {
                      const stepData = entry.value;
                      console.log('[useAIAgent] Showing step success toast');
                      toast.showSuccess(`✅ Step ${stepData.step} done in ${stepData.duration.toFixed(1)}s`, { duration: 2000 });
                    } else if (entry.action_type === 'step_failed') {
                      const stepData = entry.value;
                      console.log('[useAIAgent] Showing step failed toast');
                      toast.showError(`❌ Step ${stepData.step} failed in ${stepData.duration.toFixed(1)}s`, { duration: 2000 });
                    } else if (entry.action_type === 'task_completed') {
                      const taskData = entry.value;
                      console.log('[useAIAgent] Showing task completed toast');
                      toast.showSuccess(`🎉 Task completed in ${taskData.duration.toFixed(1)}s`, { duration: 4000 });
                    } else if (entry.action_type === 'task_failed') {
                      const taskData = entry.value;
                      console.log('[useAIAgent] Showing task failed toast');
                      toast.showError(`⚠️ Task failed in ${taskData.duration.toFixed(1)}s`, { duration: 4000 });
                    }
                  }
                }

                // Check if execution is still running
                if (!statusResult.is_executing) {
                  console.log('[useAIAgent] Task execution completed');

                  // Extract final AI plan if not already set
                  if (!aiPlan && statusResult.execution_log) {
                    const finalPlanEntry = statusResult.execution_log.find(
                      (entry: ExecutionLogEntry) =>
                        entry.action_type === 'plan_generated' && entry.type === 'ai_plan',
                    );

                    if (finalPlanEntry && finalPlanEntry.value) {
                      setAiPlan(finalPlanEntry.value);
                      setIsPlanFeasible(finalPlanEntry.value.feasible !== false);
                    }
                  }

                  // Extract task result from execution log
                  const summaryEntry = statusResult.execution_log.find(
                    (entry: ExecutionLogEntry) => entry.action_type === 'result_summary' && entry.type === 'summary',
                  );

                  if (summaryEntry && summaryEntry.value) {
                    const summary = summaryEntry.value;
                    const success = summary.success === true;
                    const message = success ? 'Task Completed' : 'Task Failed';
                    setTaskResult({ success, message });
                  } else {
                    // Fallback if no summary found
                    setTaskResult({ success: true, message: 'Task Completed' });
                  }

                  // Task completed, stop polling
                  setIsExecuting(false);
                  return;
                }
                // Continue polling if still executing
              } else {
                console.warn('[useAIAgent] Status poll failed:', statusResult.error);
                // Continue polling despite errors - might be temporary
              }
            } catch (pollError) {
              console.warn('[useAIAgent] Error polling status:', pollError);
              // Continue polling despite error - network issues might be temporary
            }
          }

          // Timeout reached
          console.warn('[useAIAgent] Polling timeout reached');
          setErrorMessage('Task execution timeout - status polling stopped');
          setIsExecuting(false);
        };

        // Start polling in background
        pollStatus();
      } else {
        // Handle both HTTP errors and execution failures
        const rawErrorMessage = !response.ok 
          ? (result.error || `HTTP ${response.status}: ${response.statusText}`)
          : (result.error || 'Failed to start task execution');
        
        setErrorMessage(enhanceErrorMessage(rawErrorMessage));
        setCurrentStep('Task execution failed');
        setExecutionLog(result.execution_log || []);
        setIsPlanFeasible(false);
        setIsExecuting(false);
      }
    } catch (error) {
      console.error('[useAIAgent] Task execution error:', error);
      setErrorMessage(enhanceErrorMessage('Network error during task execution'));
      setCurrentStep('Error');
      setIsPlanFeasible(false);
      setIsExecuting(false);
    }
  }, [enabled, taskInput, isExecuting, host, device?.device_id, aiPlan, enhanceErrorMessage]);

  const stopExecution = useCallback(async () => {
    if (!enabled || !isExecuting) return;

    try {
      console.log('[useAIAgent] Stopping task execution');

      const response = await fetch(buildServerUrl('/server/aiagent/stopExecution'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          host: host,
          device_id: device?.device_id,
        }),
      });

      const result = await response.json();
      console.log('[useAIAgent] Stop execution result:', result);

      if (response.ok && result.success) {
        setCurrentStep('Stopped by user');
        setExecutionLog(result.execution_log || []);
      } else if (!response.ok) {
        console.error('[useAIAgent] Stop execution HTTP error:', response.status, result.error);
        const rawErrorMessage = result.error || `HTTP ${response.status}: Failed to stop execution`;
        setErrorMessage(enhanceErrorMessage(rawErrorMessage));
      }
    } catch (error) {
      console.error('[useAIAgent] Stop execution error:', error);
    } finally {
      setIsExecuting(false);
    }
  }, [enabled, isExecuting, host, device?.device_id, enhanceErrorMessage]);

  const clearLog = useCallback(() => {
    setExecutionLog([]);
    setErrorMessage(null);
    setTaskResult(null);
    setCurrentStep('');
    setAiPlan(null);
    setIsPlanFeasible(true);
  }, []);

  return {
    // State
    isExecuting,
    currentStep,
    executionLog,
    taskInput,
    errorMessage,
    taskResult,
    aiPlan,
    isPlanFeasible,

    // Actions
    setTaskInput,
    executeTask,
    stopExecution,
    clearLog,
  };
};
