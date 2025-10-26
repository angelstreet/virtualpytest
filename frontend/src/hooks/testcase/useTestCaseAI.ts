/**
 * useTestCaseAI Hook
 * 
 * Handles AI-powered test case generation.
 * Follows Navigation architecture pattern with buildServerUrl + fetch directly.
 */

import { useCallback } from 'react';
import { buildServerUrl } from '../../utils/buildUrlUtils';
import { TestCaseGraph } from '../../types/testcase/TestCase_Types';

export const useTestCaseAI = () => {
  
  /**
   * Generate test case graph from AI prompt
   */
  const generateTestCaseFromPrompt = useCallback(async (
    prompt: string,
    userinterfaceName: string,
    deviceId: string,
    hostName: string
  ): Promise<{ 
    success: boolean; 
    graph?: TestCaseGraph;
    analysis?: string;
    needs_disambiguation?: boolean;
    ambiguities?: any[];
    available_nodes?: any[];
    error?: string;
    generation_stats?: {
      prompt_tokens?: number;
      completion_tokens?: number;
      block_counts?: {
        navigation: number;
        action: number;
        verification: number;
        other: number;
        total: number;
      };
    };
    execution_time?: number;
    message?: string;
  }> => {
    try {
      const response = await fetch(buildServerUrl('/server/ai/generatePlan'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt,
          userinterface_name: userinterfaceName,
          device_id: deviceId,
          host_name: hostName
        }),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        return {
          success: false,
          error: errorData.error || `HTTP ${response.status}`,
        };
      }
      
      const result = await response.json();
      
      if (result.success) {
        // Backend now returns data directly (not wrapped in 'plan')
        
        // Check if needs disambiguation
        if (result.needs_disambiguation) {
          return {
            success: false,
            needs_disambiguation: true,
            ambiguities: result.ambiguities || [],
            available_nodes: result.available_nodes || [],
            error: 'Prompt needs disambiguation',
          };
        }
        
        // Check if not feasible
        if (result.feasible === false) {
          return {
            success: false,
            error: result.error || 'Task is not feasible with available navigation nodes',
          };
        }
        
        // Success - return graph with generation stats
        return {
          success: true,
          graph: result.graph,
          analysis: result.analysis,
          generation_stats: result.generation_stats,
          execution_time: result.execution_time,
          message: result.message,
        };
      } else {
        return {
          success: false,
          error: result.error || 'AI generation failed',
        };
      }
    } catch (error) {
      console.error('[useTestCaseAI] Error generating from prompt:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  }, []);

  /**
   * Save disambiguation choices and regenerate
   */
  const saveDisambiguationAndRegenerate = useCallback(async (
    prompt: string,
    selections: Array<{ phrase: string; resolved: string }>,
    userinterfaceName: string,
    deviceId: string,
    hostName: string
  ): Promise<{ 
    success: boolean; 
    graph?: TestCaseGraph;
    analysis?: string;
    error?: string;
  }> => {
    try {
      // First, save disambiguation choices
      await fetch(buildServerUrl('/server/ai-disambiguation/saveDisambiguation'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt,
          selections,
          userinterface_name: userinterfaceName,
          host_name: hostName
        }),
      });
      
      // Then regenerate with saved choices
      return await generateTestCaseFromPrompt(prompt, userinterfaceName, deviceId, hostName);
    } catch (error) {
      console.error('[useTestCaseAI] Error saving disambiguation:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  }, [generateTestCaseFromPrompt]);

  return {
    generateTestCaseFromPrompt,
    saveDisambiguationAndRegenerate,
  };
};

