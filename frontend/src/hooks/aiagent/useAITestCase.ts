/**
 * AI Test Case Hook - Clean Modern Implementation
 * No fallbacks, no legacy code, no backward compatibility
 */

import { useState, useCallback } from 'react';
import { buildServerUrl } from '../../utils/buildUrlUtils';
import { 
  AITestCaseRequest, 
  AITestCaseResponse, 
  CompatibilityResult,
  AIAnalysisRequest,
  AIAnalysisResponse,
  AIGenerationRequest,
  TestCase
} from '../../types/pages/TestCase_Types';

export const useAITestCase = () => {
  const [isGenerating, setIsGenerating] = useState(false);
  const [isExecuting, setIsExecuting] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [compatibilityResults, setCompatibilityResults] = useState<CompatibilityResult[]>([]);
  const [error, setError] = useState<string | null>(null);

  // Two-step process: Step 1 - Analysis
  const analyzeTestCase = useCallback(async (prompt: string): Promise<AIAnalysisResponse> => {
    setIsAnalyzing(true);
    setError(null);

    try {
      console.log('[@useAITestCase:analyzeTestCase] Starting analysis for prompt:', prompt);

      const response = await fetch(buildServerUrl('/server/aitestcase/analyzeTestCase'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ prompt } as AIAnalysisRequest)
      });

      if (!response.ok) {
        throw new Error(`Analysis failed: ${response.status} ${response.statusText}`);
      }

      const result = await response.json() as AIAnalysisResponse;
      console.log('[@useAITestCase:analyzeTestCase] Analysis completed:', result.compatible_count, 'compatible interfaces');

      return result;

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Analysis failed';
      console.error('[@useAITestCase:analyzeTestCase] Error:', errorMessage);
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setIsAnalyzing(false);
    }
  }, []);

  // Two-step process: Step 2 - Generation
  const generateTestCases = useCallback(async (
    analysisId: string, 
    confirmedInterfaces: string[]
  ): Promise<TestCase[]> => {
    setIsGenerating(true);
    setError(null);

    try {
      console.log('[@useAITestCase:generateTestCases] Generating for interfaces:', confirmedInterfaces);

      const response = await fetch(buildServerUrl('/server/aitestcase/generateTestCases'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          analysis_id: analysisId,
          confirmed_userinterfaces: confirmedInterfaces
        } as AIGenerationRequest)
      });

      if (!response.ok) {
        throw new Error(`Generation failed: ${response.status} ${response.statusText}`);
      }

      const result = await response.json();

      if (!result.success) {
        throw new Error(result.error || 'Generation failed');
      }

      console.log('[@useAITestCase:generateTestCases] Generated', result.total_generated, 'test cases');

      return result.generated_testcases;

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Generation failed';
      console.error('[@useAITestCase:generateTestCases] Error:', errorMessage);
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setIsGenerating(false);
    }
  }, []);

  // Unified AI Agent generation
  const generateTestCase = useCallback(async (request: AITestCaseRequest): Promise<AITestCaseResponse> => {
    setIsGenerating(true);
    setError(null);
    setCompatibilityResults([]);

    try {
      console.log('[@useAITestCase:generateTestCase] Starting unified AI test case generation', request);

      const response = await fetch(buildServerUrl('/server/aitestcase/generateTestCase'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          prompt: request.prompt,
          device_model: request.device_model,
          interface_name: request.interface_name
        })
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

      console.log('[@useAITestCase:generateTestCase] Unified generation completed', result.success);

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

  // Quick feasibility check using unified AI Agent
  const quickFeasibilityCheck = useCallback(async (
    prompt: string, 
    interfaceName?: string
  ): Promise<{ success: boolean; feasible?: boolean; reason?: string; suggestions?: string[] }> => {
    try {
      console.log('[@useAITestCase:quickFeasibilityCheck] Checking feasibility:', prompt);

      const response = await fetch(buildServerUrl('/server/aitestcase/quickFeasibilityCheck'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          prompt,
          interface_name: interfaceName
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      console.log('[@useAITestCase:quickFeasibilityCheck] Feasibility check completed:', result.feasible);

      return result;

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred';
      console.error('[@useAITestCase:quickFeasibilityCheck] Error:', errorMessage);
      
      return {
        success: false,
        feasible: false,
        reason: errorMessage
      };
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

      const response = await fetch(buildServerUrl('/server/aitestcase/executeTestCase'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
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

      const response = await fetch(buildServerUrl('/server/aitestcase/validateCompatibility'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
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
    // Two-step process actions
    analyzeTestCase,
    generateTestCases,
    
    // Unified AI Agent actions
    generateTestCase,
    quickFeasibilityCheck,
    executeTestCase,
    validateCompatibility,
    clearError,
    clearCompatibilityResults,
    
    // State
    isAnalyzing,
    isGenerating,
    isExecuting,
    compatibilityResults,
    error
  };
};
