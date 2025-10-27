import { buildServerUrl } from './buildUrlUtils';

/**
 * Navigation execution result
 */
export interface NavigationExecuteResponse {
  success: boolean;
  error?: string;
  final_position_node_id?: string;
  verification_results?: Array<{ success: boolean }>;
  transitions?: any[];
}

/**
 * Execute navigation with async polling - REUSABLE UTILITY
 * Extracted from useNode.ts to avoid code duplication
 * 
 * @param params Navigation execution parameters
 * @returns Navigation execution result
 */
export async function executeNavigationAsync(params: {
  treeId: string;
  targetNodeLabel: string;
  hostName: string;
  deviceId: string;
  userinterfaceName: string;
  currentNodeId?: string;
  onProgress?: (message: string) => void;
}): Promise<NavigationExecuteResponse> {
  const {
    treeId,
    targetNodeLabel,
    hostName,
    deviceId,
    userinterfaceName,
    currentNodeId,
    onProgress
  } = params;

  // Start async execution
  const executionUrl = buildServerUrl(`/server/navigation/execute/${treeId}/${targetNodeLabel}`);
  
  const startResult = await fetch(executionUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      host_name: hostName,
      device_id: deviceId,
      current_node_id: currentNodeId,
      userinterface_name: userinterfaceName,
      async_execution: true, // Enable async execution
    }),
  });

  const startResponse = await startResult.json();

  if (!startResponse.success) {
    throw new Error(startResponse.error || 'Failed to start navigation');
  }

  const executionId = startResponse.execution_id;
  console.log('[@navigationExecutionUtils] ✅ Async execution started:', executionId);
  
  if (onProgress) {
    onProgress(`Navigating to ${targetNodeLabel}...`);
  }

  // Poll for completion
  const statusUrl = buildServerUrl(
    `/server/navigation/execution/${executionId}/status?host_name=${hostName}&device_id=${deviceId}`
  );

  let attempts = 0;
  const maxAttempts = 60; // 60 * 1000ms = 60 seconds max

  while (attempts < maxAttempts) {
    await new Promise((resolve) => setTimeout(resolve, 1000)); // Poll every 1s
    attempts++;

    const statusResult = await fetch(statusUrl);
    const statusResponse = await statusResult.json();

    if (!statusResponse.success) {
      throw new Error(statusResponse.error || 'Failed to get execution status');
    }

    if (statusResponse.status === 'completed') {
      const response: NavigationExecuteResponse = statusResponse.result;

      if (!response.success) {
        throw new Error(response.error || 'Navigation execution failed');
      }

      if (onProgress) {
        onProgress(`Navigation to ${targetNodeLabel} completed successfully`);
      }

      return response;
    } else if (statusResponse.status === 'error') {
      throw new Error(statusResponse.error || 'Navigation execution failed');
    }

    // Update progress message
    if (statusResponse.message && onProgress) {
      onProgress(statusResponse.message);
    }
  }

  throw new Error('Navigation timeout - execution took too long');
}

