/**
 * AI Service - Handles AI-related API calls
 * Wraps AI analysis and generation endpoints
 */

import { apiClient } from './apiClient';
import type { TestCaseGraph } from '../types/testcase/TestCase_Types';

const TEAM_ID = '7fdeb4bb-3639-4ec3-959f-b54769a219ce'; // Default team ID

export interface AIAnalysisResponse {
  success: boolean;
  analysis?: {
    prompt: string;
    steps: Array<{
      step_number: number;
      description: string;
      action_type: string;
      target?: string;
      params?: Record<string, any>;
    }>;
    compatible_interfaces: string[];
    reasoning: string;
  };
  error?: string;
}

export interface AIGenerateGraphResponse {
  success: boolean;
  graph?: TestCaseGraph;
  testcase_name?: string;
  description?: string;
  ai_prompt?: string;
  ai_analysis?: string;
  error?: string;
}

/**
 * Analyze a natural language prompt
 * Step 1: Parse the prompt and check compatibility
 */
export async function analyzePrompt(prompt: string, teamId: string = TEAM_ID): Promise<AIAnalysisResponse> {
  try {
    const response = await apiClient.post<AIAnalysisResponse>(
      `/server/ai/analyzePrompt?team_id=${teamId}`,
      { prompt }
    );
    return response;
  } catch (error) {
    console.error('Error analyzing prompt:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Failed to analyze prompt'
    };
  }
}

/**
 * Generate a test case graph from a natural language prompt
 * This is the unified endpoint that:
 * 1. Analyzes the prompt
 * 2. Generates the graph structure
 * 3. Returns React Flow compatible nodes/edges
 */
export async function generateTestCaseFromPrompt(
  prompt: string,
  teamId: string = TEAM_ID
): Promise<AIGenerateGraphResponse> {
  try {
    const response = await apiClient.post<AIGenerateGraphResponse>(
      `/server/testcase/generate-with-ai?team_id=${teamId}`,
      { prompt }
    );
    return response;
  } catch (error) {
    console.error('Error generating test case from prompt:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Failed to generate test case'
    };
  }
}

/**
 * Generate AI execution plan (for Live AI Modal - immediate execution)
 * This is different from test case generation - it's for ephemeral execution
 */
export async function generateExecutionPlan(
  prompt: string,
  deviceId: string,
  teamId: string = TEAM_ID
): Promise<any> {
  try {
    const response = await apiClient.post(
      `/server/ai/generatePlan?team_id=${teamId}`,
      { 
        task_description: prompt,
        device_id: deviceId
      }
    );
    return response;
  } catch (error) {
    console.error('Error generating execution plan:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Failed to generate plan'
    };
  }
}

