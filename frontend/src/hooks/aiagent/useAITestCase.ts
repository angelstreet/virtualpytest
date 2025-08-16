/**
 * AI Test Case Hook - Clean Modern Implementation
 * No fallbacks, no legacy code, no backward compatibility
 */

import { useState, useCallback } from 'react';
import { 
  AITestCaseRequest, 
  AITestCaseResponse, 
  CompatibilityResult, 
  TestCase 
} from '../../types/pages/TestCase_Types';

export const useAITestCase = () => {
  const [isGenerating, setIsGenerating] = useState(false);
  const [isExecuting, setIsExecuting] = useState(false);
  const [compatibilityResults, setCompatibilityResults] = useState<CompatibilityResult[]>([]);
  const [error, setError] = useState<string | null>(null);

  const generateTestCase = useCallback(async (request: AITestCaseRequest): Promise<AITestCaseResponse> => {
    setIsGenerating(true);
    setError(null);
    setCompatibilityResults([]);

    try {
      console.log('[@useAITestCase:generateTestCase] Starting AI test case generation', request);

      const response = await fetch('/server/aitestcase/generateTestCase', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Team-ID': localStorage.getItem('team_id') || '',
          'X-User-ID': localStorage.getItem('user_id') || ''
        },
        body: JSON.stringify(request)
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json() as AITestCaseResponse;

      if (result.compatibility_results) {
        setCompatibilityResults(result.compatibility_results);
      }

      if (!result.success && result.error) {
        setError(result.error);
      }

      console.log('[@useAITestCase:generateTestCase] Generation completed', result.success);

      return result;

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred';
      console.error('[@useAITestCase:generateTestCase] Error:', errorMessage);
      setError(errorMessage);
      
      return {
        success: false,
        error: errorMessage
      };
    } finally {
      setIsGenerating(false);
    }
  }, []);

  const executeTestCase = useCallback(async (
    testCaseId: string, 
    deviceId: string, 
    interfaceName?: string
  ): Promise<{ success: boolean; error?: string; execution_result?: any }> => {
    setIsExecuting(true);
    setError(null);

    try {
      console.log('[@useAITestCase:executeTestCase] Starting test case execution', { testCaseId, deviceId });

      const response = await fetch('/server/aitestcase/executeTestCase', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Team-ID': localStorage.getItem('team_id') || '',
          'X-User-ID': localStorage.getItem('user_id') || ''
        },
        body: JSON.stringify({
          test_case_id: testCaseId,
          device_id: deviceId,
          interface_name: interfaceName
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();

      if (!result.success && result.error) {
        setError(result.error);
      }

      console.log('[@useAITestCase:executeTestCase] Execution completed', result.success);

      return result;

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred';
      console.error('[@useAITestCase:executeTestCase] Error:', errorMessage);
      setError(errorMessage);
      
      return {
        success: false,
        error: errorMessage
      };
    } finally {
      setIsExecuting(false);
    }
  }, []);

  const validateCompatibility = useCallback(async (
    testCaseId: string, 
    interfaceName: string
  ): Promise<{ success: boolean; compatible?: boolean; reasoning?: string; error?: string }> => {
    try {
      console.log('[@useAITestCase:validateCompatibility] Validating compatibility', { testCaseId, interfaceName });

      const response = await fetch('/server/aitestcase/validateCompatibility', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Team-ID': localStorage.getItem('team_id') || '',
          'X-User-ID': localStorage.getItem('user_id') || ''
        },
        body: JSON.stringify({
          test_case_id: testCaseId,
          interface_name: interfaceName
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      
      console.log('[@useAITestCase:validateCompatibility] Validation completed', result);

      return result;

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred';
      console.error('[@useAITestCase:validateCompatibility] Error:', errorMessage);
      
      return {
        success: false,
        error: errorMessage
      };
    }
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const clearCompatibilityResults = useCallback(() => {
    setCompatibilityResults([]);
  }, []);

  return {
    // Actions
    generateTestCase,
    executeTestCase,
    validateCompatibility,
    clearError,
    clearCompatibilityResults,
    
    // State
    isGenerating,
    isExecuting,
    compatibilityResults,
    error
  };
};
