import { useState, useCallback, useMemo, useRef } from 'react';

import { Host, Device } from '../../types/common/Host_Types';
import { 
  AIExecutionLogEntry, 
  AIPlan, 
  AIExecutionSummary,
  AI_CONSTANTS 
} from '../../types/aiagent/AIAgent_Types';

import { buildServerUrl } from '../../utils/buildUrlUtils';
import { useToast } from '../useToast';

interface UseAIAgentProps {
  host: Host;
  device: Device;
  enabled?: boolean;
}

interface UseAIAgentReturn {
  // State
  isExecuting: boolean;
  currentStep: string;
  executionLog: AIExecutionLogEntry[];
  taskInput: string;
  errorMessage: string | null;
  taskResult: { success: boolean; message: string } | null;

  // AI plan from backend
  aiPlan: AIPlan | null;
  isPlanFeasible: boolean;

  // Progress tracking
  progressPercentage: number;
  executionSummary: AIExecutionSummary | null;

  // Actions
  setTaskInput: (input: string) => void;
  executeTask: () => Promise<void>;
  stopExecution: () => Promise<void>;
  clearLog: () => void;
}

export const useAIAgent = ({ host, device, enabled = true }: UseAIAgentProps): UseAIAgentReturn => {
  const [isExecuting, setIsExecuting] = useState(false);
  const [currentStep, setCurrentStep] = useState('');
  const [executionLog, setExecutionLog] = useState<AIExecutionLogEntry[]>([]);
  const [taskInput, setTaskInput] = useState('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [taskResult, setTaskResult] = useState<{ success: boolean; message: string } | null>(null);
  
  // Toast notifications
  const toast = useToast();

  // AI plan response
  const [aiPlan, setAiPlan] = useState<AIPlan | null>(null);
  const [isPlanFeasible, setIsPlanFeasible] = useState<boolean>(true);

  // Request deduplication
  const isRequestInProgress = useRef(false);
  const currentTaskId = useRef<string | null>(null);

  // Progress percentage calculation
  const progressPercentage = useMemo(() => {
    if (!aiPlan?.plan || aiPlan.plan.length === 0) return 0;
    
    const completedSteps = executionLog.filter(entry => 
      entry.action_type === 'step_success' || entry.action_type === 'step_failed'
    ).length;
    
    return Math.round((completedSteps / aiPlan.plan.length) * 100);
  }, [executionLog, aiPlan]);

  // Execution summary calculation
  const executionSummary = useMemo((): AIExecutionSummary | null => {
    if (!aiPlan?.plan || executionLog.length === 0) return null;

    const completedSteps = executionLog.filter(entry => entry.action_type === 'step_success');
    const failedSteps = executionLog.filter(entry => entry.action_type === 'step_failed');
    const taskCompleted = executionLog.some(entry => entry.action_type === 'task_completed');
    const taskFailed = executionLog.some(entry => entry.action_type === 'task_failed');

    if (!taskCompleted && !taskFailed) return null;

    // Calculate total duration and average step duration
    const stepDurations = executionLog
      .filter(entry => entry.action_type === 'step_success' || entry.action_type === 'step_failed')
      .map(entry => entry.value?.duration || 0);
    
    const totalDuration = executionLog.find(entry => 
      entry.action_type === 'task_completed' || entry.action_type === 'task_failed'
    )?.value?.duration || 0;

    const averageStepDuration = stepDurations.length > 0 
      ? stepDurations.reduce((sum, duration) => sum + duration, 0) / stepDurations.length 
      : 0;

    const success = taskCompleted && failedSteps.length === 0;
    
    return {
      totalSteps: aiPlan.plan.length,
      completedSteps: completedSteps.length,
      failedSteps: failedSteps.length,
      totalDuration,
      averageStepDuration,
      success,
      message: success 
        ? `All ${completedSteps.length} steps completed successfully`
        : `${completedSteps.length}/${aiPlan.plan.length} steps completed, ${failedSteps.length} failed`
    };
  }, [executionLog, aiPlan]);

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
    
    // Clear all previous state for new task
    setAiPlan(null);
    setExecutionLog([]);
    setErrorMessage(null);
    setTaskResult(null);
    setIsPlanFeasible(true);

    // Request deduplication - prevent duplicate calls
    const taskId = `${host.host_name}-${device.device_id}-${taskInput.trim()}-${Date.now()}`;
    if (isRequestInProgress.current && currentTaskId.current === taskId) {
      console.log('[useAIAgent] Task already in progress, ignoring duplicate request');
      return;
    }

    // Mark request as in progress
    isRequestInProgress.current = true;
    currentTaskId.current = taskId;

    try {
      console.log('[useAIAgent] 🚀 Starting task execution - setting isExecuting to true');
      setIsExecuting(true);
      setCurrentStep('Starting AI...');

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
        console.log('[useAIAgent] ✅ Task execution started successfully');
        const initialLog = result.execution_log || [];
        setExecutionLog(initialLog);

        // Extract AI plan from execution_log immediately
        console.log('[useAIAgent] 🔍 Looking for AI plan in execution log:', initialLog);
        const planEntry = initialLog.find(
          (entry: AIExecutionLogEntry) =>
            entry.action_type === 'plan_generated' && entry.type === 'ai_plan',
        );

        if (planEntry && planEntry.value) {
          console.log('[useAIAgent] 📋 Found AI plan, setting it immediately:', planEntry.value);
          setAiPlan(planEntry.value);
          setIsPlanFeasible(planEntry.value.feasible !== false);
          setCurrentStep('Plan ready');
        } else {
          console.log('[useAIAgent] ⚠️ No AI plan found in initial execution log - will wait for polling');
          setCurrentStep('Generating plan...');
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
                console.log('[useAIAgent] 📊 Status poll success:', statusResult);
                const newLog = statusResult.execution_log || [];
                setExecutionLog(newLog);

                // Extract AI plan if not already set
                if (!aiPlan && newLog.length > 0) {
                  const planEntry = newLog.find(
                    (entry: AIExecutionLogEntry) =>
                      entry.action_type === 'plan_generated' && entry.type === 'ai_plan',
                  );
                  if (planEntry && planEntry.value) {
                    console.log('[useAIAgent] 📋 Found AI plan in status update:', planEntry.value);
                    setAiPlan(planEntry.value);
                    setIsPlanFeasible(planEntry.value.feasible !== false);
                    setCurrentStep('Plan ready');
                  }
                }

                // Only update current step if we have a plan (execution started)
                if (aiPlan || (newLog.length > 0 && newLog.some((e: AIExecutionLogEntry) => e.action_type === 'plan_generated'))) {
                  setCurrentStep(statusResult.current_step || 'Processing...');
                }

                const prevLogLength = executionLog.length;

                if (newLog.length > prevLogLength) {
                  const newEntries = newLog.slice(prevLogLength);
                  for (const entry of newEntries) {
                    if (entry.action_type === 'step_success') {
                      const stepData = entry.value;
                      toast.showSuccess(`✅ Step ${stepData.step} completed (${stepData.duration.toFixed(1)}s)`, { duration: 2000 });
                    } else if (entry.action_type === 'step_failed') {
                      const stepData = entry.value;
                      toast.showError(`❌ Step ${stepData.step} failed (${stepData.duration.toFixed(1)}s)`, { duration: 2000 });
                    } else if (entry.action_type === 'task_completed') {
                      const taskData = entry.value;
                      toast.showSuccess(`🎉 Task completed in ${taskData.duration.toFixed(1)}s`, { duration: AI_CONSTANTS.TOAST_DURATION.SUCCESS });
                    } else if (entry.action_type === 'task_failed') {
                      const taskData = entry.value;
                      toast.showError(`⚠️ Task failed in ${taskData.duration.toFixed(1)}s`, { duration: AI_CONSTANTS.TOAST_DURATION.ERROR });
                    }
                  }
                }

                // Check if execution is truly completed (not just async started)
                const hasTaskCompletion = statusResult.execution_log?.some((entry: AIExecutionLogEntry) => 
                  entry.action_type === 'task_completed' || entry.action_type === 'task_failed'
                );

                if (!statusResult.is_executing && hasTaskCompletion) {
                  console.log('[useAIAgent] 🏁 Task execution truly completed - setting isExecuting to false');

                  // Extract final AI plan if not already set
                  if (!aiPlan && statusResult.execution_log) {
                    const finalPlanEntry = statusResult.execution_log.find(
                      (entry: AIExecutionLogEntry) =>
                        entry.action_type === 'plan_generated' && entry.type === 'ai_plan',
                    );

                    if (finalPlanEntry && finalPlanEntry.value) {
                      setAiPlan(finalPlanEntry.value);
                      setIsPlanFeasible(finalPlanEntry.value.feasible !== false);
                    }
                  }

                  // Extract task result from execution log
                  const summaryEntry = statusResult.execution_log.find(
                    (entry: AIExecutionLogEntry) => entry.action_type === 'task_completed' || entry.action_type === 'task_failed',
                  );

                  if (summaryEntry) {
                    const success = summaryEntry.action_type === 'task_completed';
                    const message = success ? 'Task Completed' : 'Task Failed';
                    setTaskResult({ success, message });
                  } else {
                    // Fallback if no completion found
                    setTaskResult({ success: true, message: 'Task Completed' });
                  }

                  // Task completed, stop polling
                  setIsExecuting(false);
                  return;
                } else if (!statusResult.is_executing) {
                  console.log('[useAIAgent] ⏳ Backend says not executing but no completion markers - continuing to poll');
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
      const errorMsg = enhanceErrorMessage('Network error during task execution');
      setErrorMessage(errorMsg);
      setCurrentStep('Error');
      setIsPlanFeasible(false);
      setIsExecuting(false);
      toast.showError(`❌ AI task failed: ${errorMsg}`, { duration: AI_CONSTANTS.TOAST_DURATION.ERROR });
    } finally {
      // Clear deduplication flags
      isRequestInProgress.current = false;
      currentTaskId.current = null;
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

    // Progress tracking
    progressPercentage,
    executionSummary,

    // Actions
    setTaskInput,
    executeTask,
    stopExecution,
    clearLog,
  };
};
