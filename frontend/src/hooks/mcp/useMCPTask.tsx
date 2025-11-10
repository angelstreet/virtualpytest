import { useState, useCallback } from 'react';

import { buildServerUrl } from '../../utils/buildUrlUtils';

interface MCPTaskProps {
  device_id?: string;
  host_name?: string;
  userinterface_name?: string;
  device_model?: string;
  team_id?: string;
}

interface MCPTaskResponse {
  success: boolean;
  result?: string;
  tool_executed?: string;
  tool_result?: any;
  ai_analysis?: string;
  ai_response?: string;
  execution_log?: any[];
  tool_calls?: Array<{
    tool: string;
    arguments: any;
    result: any;
  }>;
  iterations?: number;
  error?: string;
}

interface UseMCPTaskReturn {
  // Panel state
  isPanelVisible: boolean;
  togglePanel: () => void;
  closePanel: () => void;

  // Task state
  currentTask: string;
  setCurrentTask: (task: string) => void;

  // Execution state
  isExecuting: boolean;
  lastResponse: MCPTaskResponse | null;

  // Actions
  executeTask: () => Promise<void>;
  clearResponse: () => void;
}

export const useMCPTask = (props?: MCPTaskProps): UseMCPTaskReturn => {
  // Device context - use props or defaults
  const device_id = props?.device_id || 'device1';
  const host_name = props?.host_name || 'sunri-pi1';
  const userinterface_name = props?.userinterface_name || 'mobile_test';
  const device_model = props?.device_model || 'android_mobile';
  const team_id = props?.team_id || 'team_1';

  // Panel visibility state
  const [isPanelVisible, setIsPanelVisible] = useState(false);

  // Task input state
  const [currentTask, setCurrentTask] = useState('');

  // Execution state
  const [isExecuting, setIsExecuting] = useState(false);
  const [lastResponse, setLastResponse] = useState<MCPTaskResponse | null>(null);

  // Toggle panel visibility
  const togglePanel = useCallback(() => {
    setIsPanelVisible((prev) => !prev);
    // Clear response when opening panel
    if (!isPanelVisible) {
      setLastResponse(null);
    }
  }, [isPanelVisible]);

  // Close panel
  const closePanel = useCallback(() => {
    setIsPanelVisible(false);
    setLastResponse(null);
  }, []);

  // Execute MCP task
  const executeTask = useCallback(async () => {
    if (!currentTask.trim() || isExecuting) {
      return;
    }

    setIsExecuting(true);
    setLastResponse(null);

    try {
      const response = await fetch(buildServerUrl('/server/mcp-proxy/execute-prompt'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          prompt: currentTask.trim(),
          device_id,
          host_name,
          userinterface_name,
          device_model,
          team_id,
        }),
      });

      const data: MCPTaskResponse = await response.json();

      if (response.ok) {
        // Map the MCP proxy response to our expected format
        const mappedResponse: MCPTaskResponse = {
          success: data.success,
          result: data.result ? JSON.stringify(data.result, null, 2) : 'Task completed',
          tool_executed: data.tool_calls?.[0]?.tool || 'MCP Tool',
          tool_result: data.result,
          ai_analysis: data.ai_response || `Completed in ${data.iterations || 1} iteration(s)`,
          ai_response: data.ai_response,
          execution_log: data.tool_calls || [],  // Pass tool_calls as execution_log
          tool_calls: data.tool_calls || [],
          iterations: data.iterations,
          error: data.error,
        };
        
        setLastResponse(mappedResponse);
        // Clear task input on success
        if (data.success) {
          setCurrentTask('');
        }
      } else {
        setLastResponse({
          success: false,
          error: data.error || `HTTP ${response.status}: ${response.statusText}`,
        });
      }
    } catch (error) {
      console.error('[useMCPTask] Execute task error:', error);
      setLastResponse({
        success: false,
        error: `Network error: ${error instanceof Error ? error.message : 'Unknown error'}`,
      });
    } finally {
      setIsExecuting(false);
    }
  }, [currentTask, isExecuting, device_id, host_name, userinterface_name, device_model, team_id]);

  // Clear response
  const clearResponse = useCallback(() => {
    setLastResponse(null);
  }, []);

  return {
    // Panel state
    isPanelVisible,
    togglePanel,
    closePanel,

    // Task state
    currentTask,
    setCurrentTask,

    // Execution state
    isExecuting,
    lastResponse,

    // Actions
    executeTask,
    clearResponse,
  };
};
