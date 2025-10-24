/**
 * TestCase API Service
 * 
 * Handles all API calls related to TestCase Builder operations.
 * Routes: /server/testcase/*
 */

import { apiClient } from './apiClient';
import type { TestCaseGraph } from '../types/testcase/TestCase_Types';

export interface TestCaseDefinition {
  testcase_id: string;
  team_id: string;
  testcase_name: string;
  description?: string;
  userinterface_name?: string;
  graph_json: TestCaseGraph;
  created_at: string;
  updated_at: string;
  created_by?: string;
  is_active: boolean;
  execution_count?: number;
  last_execution_success?: boolean;
}

export interface TestCaseExecutionResult {
  success: boolean;
  execution_time_ms: number;
  step_count: number;
  script_result_id: string;
  error?: string;
  step_results?: any[];
}

export interface TestCaseExecutionHistory {
  script_result_id: string;
  started_at: string;
  completed_at?: string;
  execution_time_ms: number;
  success: boolean;
}

/**
 * Save or update a test case
 */
export async function saveTestCase(
  testcaseName: string,
  graphJson: TestCaseGraph,
  description: string,
  userinterfaceName: string,
  createdBy: string,
  teamId: string
): Promise<{ success: boolean; testcase_id?: string; action?: string; error?: string }> {
  try {
    const response = await apiClient.post<{ success: boolean; testcase_id?: string; action?: string; error?: string }>(
      '/server/testcase/save',
      {
        testcase_name: testcaseName,
        graph_json: graphJson,
        description,
        userinterface_name: userinterfaceName,
        created_by: createdBy,
        team_id: teamId
      }
    );
    
    return response;
  } catch (error) {
    console.error('[testcaseApi] Error saving test case:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

/**
 * List all test cases
 */
export async function listTestCases(teamId: string): Promise<{ success: boolean; testcases: TestCaseDefinition[] }> {
  try {
    const response = await apiClient.get<{ success: boolean; testcases: TestCaseDefinition[] }>(
      '/server/testcase/list',
      { team_id: teamId }
    );
    
    return response;
  } catch (error) {
    console.error('[testcaseApi] Error listing test cases:', error);
    return { success: false, testcases: [] };
  }
}

/**
 * Get a specific test case by ID
 */
export async function getTestCase(testcaseId: string, teamId: string): Promise<{ success: boolean; testcase?: TestCaseDefinition; error?: string }> {
  try {
    const response = await apiClient.get<{ success: boolean; testcase?: TestCaseDefinition; error?: string }>(
      `/server/testcase/${testcaseId}`,
      { team_id: teamId }
    );
    
    return response;
  } catch (error) {
    console.error('[testcaseApi] Error getting test case:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

/**
 * Execute a test case
 */
export async function executeTestCase(testcaseId: string, deviceId: string): Promise<{ success: boolean; result?: TestCaseExecutionResult; error?: string }> {
  try {
    const response = await apiClient.post<{ success: boolean; result?: TestCaseExecutionResult; error?: string }>(
      `/server/testcase/${testcaseId}/execute`,
      { device_id: deviceId }
    );
    
    return response;
  } catch (error) {
    console.error('[testcaseApi] Error executing test case:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

/**
 * Get execution history for a test case
 */
export async function getTestCaseHistory(testcaseId: string, teamId: string): Promise<{ success: boolean; history: TestCaseExecutionHistory[] }> {
  try {
    const response = await apiClient.get<{ success: boolean; history: TestCaseExecutionHistory[] }>(
      `/server/testcase/${testcaseId}/history`,
      { team_id: teamId }
    );
    
    return response;
  } catch (error) {
    console.error('[testcaseApi] Error getting history:', error);
    return { success: false, history: [] };
  }
}

/**
 * Delete a test case
 */
export async function deleteTestCase(testcaseId: string, teamId: string): Promise<{ success: boolean; error?: string }> {
  try {
    const url = `/server/testcase/${testcaseId}?team_id=${encodeURIComponent(teamId)}`;
    const response = await apiClient.delete<{ success: boolean; error?: string }>(url);
    
    return response;
  } catch (error) {
    console.error('[testcaseApi] Error deleting test case:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

/**
 * Generate test case graph from AI prompt
 * Handles disambiguation and feasibility checking
 */
export async function generateTestCaseFromPrompt(
  prompt: string,
  userinterfaceName: string,
  deviceId: string,
  teamId: string
): Promise<{ 
  success: boolean; 
  graph?: TestCaseGraph;
  analysis?: string;
  needs_disambiguation?: boolean;
  ambiguities?: any[];
  available_nodes?: any[];
  error?: string;
}> {
  try {
    const response = await apiClient.post<any>(
      '/server/ai/generatePlan',
      {
        prompt,
        userinterface_name: userinterfaceName,
        device_id: deviceId,
        team_id: teamId
      }
    );
    
    if (response.success) {
      const plan = response.plan || {};
      
      // Check if needs disambiguation
      if (plan.needs_disambiguation) {
        return {
          success: false,
          needs_disambiguation: true,
          ambiguities: plan.ambiguities || [],
          available_nodes: plan.available_nodes || [],
          error: 'Prompt needs disambiguation',
        };
      }
      
      // Check if not feasible
      if (plan.feasible === false) {
        return {
          success: false,
          error: plan.error || 'Task is not feasible with available navigation nodes',
        };
      }
      
      // Success - return graph
      return {
        success: true,
        graph: plan.graph,
        analysis: plan.analysis,
      };
    } else {
      return {
        success: false,
        error: response.error || 'AI generation failed',
      };
    }
  } catch (error) {
    console.error('[testcaseApi] Error generating from prompt:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

/**
 * Save disambiguation choices and regenerate
 */
export async function saveDisambiguationAndRegenerate(
  prompt: string,
  selections: Array<{ phrase: string; resolved: string }>,
  userinterfaceName: string,
  deviceId: string,
  teamId: string
): Promise<{ 
  success: boolean; 
  graph?: TestCaseGraph;
  analysis?: string;
  error?: string;
}> {
  try {
    // First, save disambiguation choices
    await apiClient.post(
      '/server/ai-disambiguation/saveDisambiguation',
      {
        prompt,
        selections,
        userinterface_name: userinterfaceName,
        team_id: teamId
      }
    );
    
    // Then regenerate with saved choices
    return await generateTestCaseFromPrompt(prompt, userinterfaceName, deviceId, teamId);
  } catch (error) {
    console.error('[testcaseApi] Error saving disambiguation:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}
