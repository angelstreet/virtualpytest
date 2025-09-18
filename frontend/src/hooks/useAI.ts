import { useState, useCallback } from 'react';
import { Host, Device } from '../types/common/Host_Types';
import { buildServerUrl } from '../utils/buildUrlUtils';

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

    setIsExecuting(true);
    setError(null);
    setExecutionStatus(null);

    try {
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

      // Poll for status
      const pollStatus = async () => {
        while (true) {
          const statusResponse = await fetch(buildServerUrl(`/server/ai/status/${executionId}`));
          const status = await statusResponse.json();

          setExecutionStatus(status);

          if (!status.is_executing) {
            setIsExecuting(false);
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
    }
  }, [host, device, isExecuting]);

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
