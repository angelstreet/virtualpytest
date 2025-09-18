import { useState, useCallback, useMemo, useRef } from 'react';
import { Host, Device } from '../types/common/Host_Types';
import { buildServerUrl } from '../utils/buildUrlUtils';
import { useToast } from './useToast';

interface UseAIProps {
  host: Host;
  device: Device;
  mode: 'real-time' | 'test-case';
}

interface AIPlan {
  id: string;
  prompt: string;
  analysis: string;
  feasible: boolean;
  steps: Array<{
    step: number;
    type: string;
    command: string;
    params: Record<string, any>;
    description: string;
  }>;
}

interface ExecutionStatus {
  success: boolean;
  is_executing: boolean;
  current_step: string;
  execution_log: Array<{
    timestamp: number;
    log_type: string;
    action_type: string;
    data: Record<string, any>;
    description: string;
  }>;
  progress_percentage: number;
}

export const useAI = ({ host, device, mode: _mode }: UseAIProps) => {
  const [isExecuting, setIsExecuting] = useState(false);
  const [currentPlan, setCurrentPlan] = useState<AIPlan | null>(null);
  const [executionStatus, setExecutionStatus] = useState<ExecutionStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  
  // Toast notifications
  const toast = useToast();
  
  // Track completion toast to prevent duplicates
  const completionToastShown = useRef(false);

  const analyzeCompatibility = useCallback(async (prompt: string) => {
    try {
      const response = await fetch(buildServerUrl('/server/ai/analyzeCompatibility'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt })
      });

      const result = await response.json();
      if (!response.ok) throw new Error(result.error);
      
      return result;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Analysis failed';
      setError(errorMessage);
      throw new Error(errorMessage);
    }
  }, []);

  const generatePlan = useCallback(async (prompt: string, userinterface_name: string) => {
    try {
      const response = await fetch(buildServerUrl('/server/ai/generatePlan'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt, userinterface_name })
      });

      const result = await response.json();
      if (!response.ok) throw new Error(result.error);
      
      setCurrentPlan(result.plan);
      return result.plan;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Plan generation failed';
      setError(errorMessage);
      throw new Error(errorMessage);
    }
  }, []);

  const executeTask = useCallback(async (prompt: string, userinterface_name: string) => {
    if (isExecuting) return;

    // Clear previous state
    setCurrentPlan(null);
    setExecutionStatus(null);
    setError(null);
    completionToastShown.current = false;

    setIsExecuting(true);

    try {
      // Show start notification
      toast.showInfo(`🤖 Starting AI task`, { duration: 3000 });

      const response = await fetch(buildServerUrl('/server/ai/executeTask'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt,
          userinterface_name,
          host,
          device_id: device.device_id
        })
      });

      const result = await response.json();
      if (!response.ok) throw new Error(result.error);

      const executionId = result.execution_id;

      // Poll for status with rich updates
      const pollStatus = async () => {
        let previousLogLength = 0;
        
        while (true) {
          const statusResponse = await fetch(buildServerUrl(`/server/ai/status/${executionId}`));
          const status = await statusResponse.json();

          setExecutionStatus(status);

          // Extract and set plan if available
          if (!currentPlan && status.execution_log) {
            const planEntry = status.execution_log.find((entry: any) => 
              entry.action_type === 'plan_generated'
            );
            if (planEntry && planEntry.value) {
              setCurrentPlan(planEntry.value);
              toast.showSuccess(`📋 AI plan generated with ${planEntry.value.steps?.length || 0} steps`, { duration: 3000 });
            }
          }

          // Show step progress toasts
          if (status.execution_log && status.execution_log.length > previousLogLength) {
            const newEntries = status.execution_log.slice(previousLogLength);
            for (const entry of newEntries) {
              if (entry.action_type === 'step_success') {
                const stepData = entry.data || entry.value;
                toast.showSuccess(`✅ Step ${stepData.step} completed`, { duration: 2000 });
              } else if (entry.action_type === 'step_failed') {
                const stepData = entry.data || entry.value;
                toast.showError(`❌ Step ${stepData.step} failed`, { duration: 2000 });
              }
            }
            previousLogLength = status.execution_log.length;
          }

          if (!status.is_executing) {
            setIsExecuting(false);
            
            // Show completion toast
            if (!completionToastShown.current) {
              completionToastShown.current = true;
              const success = status.success !== false;
              if (success) {
                toast.showSuccess(`🎉 Task completed successfully`, { duration: 4000 });
              } else {
                toast.showError(`⚠️ Task failed`, { duration: 4000 });
              }
            }
            break;
          }

          await new Promise(resolve => setTimeout(resolve, 1000));
        }
      };

      pollStatus();

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Execution failed';
      setError(errorMessage);
      setIsExecuting(false);
      toast.showError(`❌ AI task failed: ${errorMessage}`, { duration: 4000 });
    }
  }, [host, device, isExecuting, currentPlan, toast]);

  const executeTestCase = useCallback(async (testCaseId: string) => {
    try {
      const response = await fetch(buildServerUrl('/server/ai/executeTestCase'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          test_case_id: testCaseId,
          device_id: device.device_id,
          host
        })
      });

      const result = await response.json();
      if (!response.ok) throw new Error(result.error);
      
      return result;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Test case execution failed';
      setError(errorMessage);
      throw new Error(errorMessage);
    }
  }, [host, device]);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return {
    // State
    isExecuting,
    currentPlan,
    executionStatus,
    error,

    // Actions
    analyzeCompatibility,
    generatePlan,
    executeTask,
    executeTestCase,
    clearError
  };
};
