/**
 * useTestCaseSave Hook
 * 
 * Handles test case save, load, list, and delete operations.
 * Follows Navigation architecture pattern with buildServerUrl + fetch directly.
 */

import { useCallback } from 'react';
import { buildServerUrl } from '../../utils/buildUrlUtils';
import { getCachedTestCaseList, invalidateTestCaseListCache } from '../../utils/testcaseCache';
import { TestCaseGraph } from '../../types/testcase/TestCase_Types';

export const useTestCaseSave = () => {
  
  /**
   * Save or update a test case
   */
  const saveTestCase = useCallback(async (
    testcaseName: string,
    graphJson: TestCaseGraph,
    description: string,
    userinterfaceName: string,
    createdBy: string,
    environment: string = 'dev',
    overwrite: boolean = false,
    folder?: string,  // NEW: Folder name (user-selected or typed)
    tags?: string[]   // NEW: List of tag names
  ): Promise<{ success: boolean; action?: string; error?: string; testcase?: any }> => {
    try {
      const response = await fetch(buildServerUrl('/server/testcase/save'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          testcase_name: testcaseName,
          graph_json: graphJson,
          description,
          userinterface_name: userinterfaceName,
          created_by: createdBy,
          environment,
          overwrite,
          folder,  // NEW: Folder name
          tags,    // NEW: Tag names array
        }),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP ${response.status}`);
      }
      
      const result = await response.json();
      
      // Invalidate cache after successful save
      if (result.success) {
        invalidateTestCaseListCache();
      }
      
      return result;
    } catch (error) {
      console.error('[useTestCaseSave] Error saving test case:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  }, []);

  /**
   * List all test cases
   */
  const listTestCases = useCallback(async (): Promise<{ success: boolean; testcases: any[] }> => {
    try {
      return await getCachedTestCaseList(buildServerUrl('/server/testcase/list'));
    } catch (error) {
      console.error('[useTestCaseSave] Error listing test cases:', error);
      return { success: false, testcases: [] };
    }
  }, []);

  /**
   * Get a specific test case by ID
   */
  const getTestCase = useCallback(async (testcaseId: string): Promise<{ success: boolean; testcase?: any; error?: string }> => {
    try {
      const response = await fetch(buildServerUrl(`/server/testcase/${testcaseId}`));
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('[useTestCaseSave] Error getting test case:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  }, []);

  /**
   * Delete a test case
   */
  const deleteTestCase = useCallback(async (testcaseId: string): Promise<{ success: boolean; error?: string }> => {
    try {
      const response = await fetch(buildServerUrl(`/server/testcase/${testcaseId}`), {
        method: 'DELETE',
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('[useTestCaseSave] Error deleting test case:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  }, []);

  return {
    saveTestCase,
    listTestCases,
    getTestCase,
    deleteTestCase,
  };
};

