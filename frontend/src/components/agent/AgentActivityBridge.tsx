/**
 * Agent Activity Bridge
 * 
 * Connects AIContext (chat events) to AgentActivityContext (badges).
 * Listens for chat events and triggers badge updates.
 */

import { useEffect, useRef } from 'react';
import { useAIContext } from '../../contexts/AIContext';
import { useAgentActivity } from '../../contexts/AgentActivityContext';

export const AgentActivityBridge: React.FC = () => {
  const { isProcessing, activeTask, executionSteps, status } = useAIContext();
  const { startTask, updateTaskStep, completeTask, failTask } = useAgentActivity();
  
  const currentTaskIdRef = useRef<string | null>(null);
  const lastAgentIdRef = useRef<string>('ai-assistant');
  const wasProcessingRef = useRef(false);

  // Track processing state changes
  useEffect(() => {
    // Detect when processing starts
    if (isProcessing && !wasProcessingRef.current && activeTask) {
      // Extract agent ID from task context if available
      const agentId = lastAgentIdRef.current || 'ai-assistant';
      
      // Start a new task in the badge system
      const taskId = startTask(agentId, activeTask, 'manual');
      currentTaskIdRef.current = taskId;
      console.log(`🎯 Bridge: Started badge task ${taskId} for ${agentId}`);
    }
    
    // Detect when processing stops
    if (!isProcessing && wasProcessingRef.current && currentTaskIdRef.current) {
      const agentId = lastAgentIdRef.current || 'ai-assistant';
      const lastStep = executionSteps[executionSteps.length - 1];
      
      if (lastStep?.status === 'error') {
        failTask(agentId, currentTaskIdRef.current, lastStep.detail || 'Task failed');
      } else {
        // Build summary from execution steps
        const toolCalls = executionSteps.filter(s => s.label !== 'Parse Command' && s.label !== 'Thinking');
        const summary = toolCalls.length > 0 ? {
          title: 'Task Complete',
          data: {
            'Steps completed': toolCalls.length,
            'Last action': toolCalls[toolCalls.length - 1]?.label || 'Processing',
          }
        } : undefined;
        
        completeTask(agentId, currentTaskIdRef.current, 'Task completed successfully', summary);
      }
      
      console.log(`🎯 Bridge: Completed badge task ${currentTaskIdRef.current}`);
      currentTaskIdRef.current = null;
    }
    
    wasProcessingRef.current = isProcessing;
  }, [isProcessing, activeTask, executionSteps, startTask, completeTask, failTask]);

  // Update steps as they progress
  useEffect(() => {
    if (!currentTaskIdRef.current || !isProcessing) return;
    
    const lastStep = executionSteps[executionSteps.length - 1];
    if (lastStep) {
      const agentId = lastAgentIdRef.current || 'ai-assistant';
      updateTaskStep(agentId, currentTaskIdRef.current, {
        id: lastStep.id,
        label: lastStep.label,
        status: lastStep.status,
        detail: lastStep.detail,
        timestamp: new Date().toISOString(),
      });
    }
  }, [executionSteps, isProcessing, updateTaskStep]);

  // This component doesn't render anything
  return null;
};

export default AgentActivityBridge;

