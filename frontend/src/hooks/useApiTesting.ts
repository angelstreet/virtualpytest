import { useState, useCallback } from 'react';
import { buildServerUrl } from '../utils/buildUrlUtils';
import { useToast } from './useToast';

export interface TestResult {
  endpoint: string;
  method: string;
  url: string;
  status: 'pass' | 'fail' | 'skip';
  status_code?: number;
  response_time: number;
  error?: string;
  response_body?: any;
  request_body?: any;
  headers?: any;
}

export interface TestReport {
  id: string;
  timestamp: string;
  git_commit: string;
  total_tests: number;
  passed: number;
  failed: number;
  results: TestResult[];
}

export interface EndpointConfig {
  name: string;
  method: string;
  url: string;
  expected_status: number[];
  body?: any;
  params?: any;
}

export interface ApiTestingState {
  isRunning: boolean;
  currentTest: string | null;
  progress: number;
  lastReport: TestReport | null;
  error: string | null;
  availableEndpoints: EndpointConfig[];
  selectedEndpoints: string[];
  liveResults: TestResult[];
  totalTests: number;
  completedTests: number;
}

export const useApiTesting = () => {
  const [state, setState] = useState<ApiTestingState>({
    isRunning: false,
    currentTest: null,
    progress: 0,
    lastReport: null,
    error: null,
    availableEndpoints: [],
    selectedEndpoints: [],
    liveResults: [],
    totalTests: 0,
    completedTests: 0,
  });

  const toast = useToast();

  const runTestsWithProgress = useCallback(async (endpoints: string[], generateReport: boolean = true) => {
    const selectedTests = state.availableEndpoints.filter(ep => endpoints.includes(ep.name));
    
    setState(prev => ({
      ...prev,
      isRunning: true,
      currentTest: 'Initializing...',
      progress: 0,
      error: null,
      liveResults: [],
      totalTests: selectedTests.length,
      completedTests: 0,
    }));

    try {
      // Simulate running tests one by one with live updates
      for (let i = 0; i < selectedTests.length; i++) {
        const endpoint = selectedTests[i];
        
        setState(prev => ({
          ...prev,
          currentTest: `Testing: ${endpoint.name}`,
          progress: Math.round((i / selectedTests.length) * 100),
        }));

        // Make individual test request
        try {
          const testResponse = await fetch(buildServerUrl('server/api-testing/run'), {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              selected_endpoints: [endpoint.name]
            }),
          });

          const testResult = await testResponse.json();
          
          if (testResponse.ok && testResult.success && testResult.report?.results?.[0]) {
            const result = testResult.report.results[0];
            
            setState(prev => ({
              ...prev,
              liveResults: [...prev.liveResults, result],
              completedTests: prev.completedTests + 1,
            }));
          } else {
            // Add failed result
            const failedResult: TestResult = {
              endpoint: endpoint.name,
              method: endpoint.method,
              url: endpoint.url,
              status: 'fail',
              response_time: 0,
              error: testResult.error || 'Test failed'
            };
            
            setState(prev => ({
              ...prev,
              liveResults: [...prev.liveResults, failedResult],
              completedTests: prev.completedTests + 1,
            }));
          }
        } catch (testError) {
          // Add error result
          const errorResult: TestResult = {
            endpoint: endpoint.name,
            method: endpoint.method,
            url: endpoint.url,
            status: 'fail',
            response_time: 0,
            error: testError instanceof Error ? testError.message : 'Network error'
          };
          
          setState(prev => ({
            ...prev,
            liveResults: [...prev.liveResults, errorResult],
            completedTests: prev.completedTests + 1,
          }));
        }

        // Small delay to show progress
        await new Promise(resolve => setTimeout(resolve, 100));
      }

      // Final state update
      setState(prev => {
        const passed = prev.liveResults.filter(r => r.status === 'pass').length;
        const percentage = Math.round((passed / prev.liveResults.length) * 100);
        
        // Create report only for normal tests, not quick tests
        let finalReport = null;
        if (generateReport) {
          finalReport = {
            id: `test-${Date.now()}`,
            timestamp: new Date().toISOString(),
            git_commit: 'local-test',
            total_tests: prev.liveResults.length,
            passed: passed,
            failed: prev.liveResults.length - passed,
            results: prev.liveResults
          };
        }

        return {
          ...prev,
          isRunning: false,
          currentTest: null,
          progress: 100,
          lastReport: finalReport,
          error: null,
        };
      });

      // Show completion message after a small delay to ensure state is updated
      setTimeout(() => {
        setState(prev => {
          const passed = prev.liveResults.filter(r => r.status === 'pass').length;
          const total = prev.liveResults.length;
          
          if (total > 0) {
            const percentage = Math.round((passed / total) * 100);
            
            if (percentage === 100) {
              toast.showSuccess(`All ${total} tests passed! 🎉`);
            } else {
              toast.showWarning(`${passed}/${total} tests passed (${percentage}%)`);
            }
          }
          
          return prev; // Don't change state, just show message
        });
      }, 100);

    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Unknown error';
      setState(prev => ({
        ...prev,
        isRunning: false,
        currentTest: null,
        progress: 0,
        error: errorMsg,
      }));
      toast.showError(`Test failed: ${errorMsg}`);
    }
  }, [state.availableEndpoints, toast]);

  const runAllTests = useCallback(async () => {
    const selectedEndpoints = state.selectedEndpoints.length > 0 ? state.selectedEndpoints : state.availableEndpoints.map(ep => ep.name);
    await runTestsWithProgress(selectedEndpoints, true); // Generate report for normal tests
  }, [state.selectedEndpoints, state.availableEndpoints, runTestsWithProgress]);

  const runQuickTest = useCallback(async () => {
    // Get critical endpoints for quick test
    const criticalEndpoints = state.availableEndpoints
      .filter(ep => ep.category === 'critical')
      .map(ep => ep.name);
    
    await runTestsWithProgress(criticalEndpoints, false); // Don't generate report for quick tests
  }, [state.availableEndpoints, runTestsWithProgress]);

  const getTestConfig = useCallback(async () => {
    try {
      const response = await fetch(buildServerUrl('server/api-testing/config'));
      const result = await response.json();
      
      if (response.ok && result.success) {
        const endpoints = result.config.endpoints || [];
        setState(prev => ({
          ...prev,
          availableEndpoints: endpoints,
          selectedEndpoints: prev.selectedEndpoints.length === 0 ? endpoints.map((e: EndpointConfig) => e.name) : prev.selectedEndpoints
        }));
        return result.config;
      } else {
        throw new Error(result.error || 'Failed to get test config');
      }
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Unknown error';
      toast.showError(`Failed to get config: ${errorMsg}`);
      return null;
    }
  }, [toast]);

  const toggleEndpoint = useCallback((endpointName: string) => {
    setState(prev => ({
      ...prev,
      selectedEndpoints: prev.selectedEndpoints.includes(endpointName)
        ? prev.selectedEndpoints.filter(name => name !== endpointName)
        : [...prev.selectedEndpoints, endpointName]
    }));
  }, []);

  const selectAllEndpoints = useCallback(() => {
    setState(prev => ({
      ...prev,
      selectedEndpoints: prev.availableEndpoints.map(endpoint => endpoint.name)
    }));
  }, []);

  const deselectAllEndpoints = useCallback(() => {
    setState(prev => ({
      ...prev,
      selectedEndpoints: []
    }));
  }, []);

  const generateHtmlReport = useCallback((report: TestReport) => {
    const passed = report.passed;
    const failed = report.failed;
    const percentage = Math.round((passed / report.total_tests) * 100);
    
    const html = `<!DOCTYPE html>
<html>
<head>
    <title>API Test Report - ${report.timestamp}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .summary { background: #f5f5f5; padding: 20px; border-radius: 5px; margin-bottom: 20px; }
        .pass { color: #4caf50; font-weight: bold; }
        .fail { color: #f44336; font-weight: bold; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #f2f2f2; }
        .status-pass { background-color: #e8f5e8; }
        .status-fail { background-color: #ffeaea; }
    </style>
</head>
<body>
    <div class="summary">
        <h1>API Test Report</h1>
        <p><strong>Git Commit:</strong> ${report.git_commit}</p>
        <p><strong>Timestamp:</strong> ${new Date(report.timestamp).toLocaleString()}</p>
        <p><strong>Results:</strong> <span class="pass">${passed} passed</span>, <span class="fail">${failed} failed</span> (${percentage}%)</p>
    </div>
    
    <table>
        <thead>
            <tr>
                <th>Endpoint</th>
                <th>Method</th>
                <th>Status</th>
                <th>Status Code</th>
                <th>Response Time</th>
                <th>Error</th>
            </tr>
        </thead>
        <tbody>
            ${report.results.map(result => `
                <tr class="status-${result.status}">
                    <td>${result.endpoint}</td>
                    <td>${result.method}</td>
                    <td class="${result.status}">${result.status === 'pass' ? '✅ PASS' : '❌ FAIL'}</td>
                    <td>${result.status_code || 'N/A'}</td>
                    <td>${result.response_time}ms</td>
                    <td>${result.error || ''}</td>
                </tr>
            `).join('')}
        </tbody>
    </table>
</body>
</html>`;

    return html;
  }, []);

  const downloadHtmlReport = useCallback((report: TestReport) => {
    const html = generateHtmlReport(report);
    const blob = new Blob([html], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = `api-test-report-${report.git_commit}-${Date.now()}.html`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    toast.showSuccess('HTML report downloaded');
  }, [generateHtmlReport, toast]);

  const clearResults = useCallback(() => {
    setState(prev => ({
      ...prev,
      lastReport: null,
      error: null,
      progress: 0,
      liveResults: [],
      totalTests: 0,
      completedTests: 0,
    }));
  }, []);

  return {
    ...state,
    runAllTests,
    runQuickTest,
    getTestConfig,
    downloadHtmlReport,
    clearResults,
    toggleEndpoint,
    selectAllEndpoints,
    deselectAllEndpoints,
  };
};
