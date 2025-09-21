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
  });

  const toast = useToast();

  const runAllTests = useCallback(async () => {
    setState(prev => ({
      ...prev,
      isRunning: true,
      currentTest: 'Initializing...',
      progress: 0,
      error: null,
    }));

    try {
      const response = await fetch(buildServerUrl('server/api-testing/run'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          selected_endpoints: state.selectedEndpoints.length > 0 ? state.selectedEndpoints : undefined
        }),
      });

      const result = await response.json();

      if (response.ok && result.success) {
        setState(prev => ({
          ...prev,
          isRunning: false,
          currentTest: null,
          progress: 100,
          lastReport: result.report,
          error: null,
        }));

        const { passed, total_tests } = result.report;
        const percentage = Math.round((passed / total_tests) * 100);
        
        if (percentage === 100) {
          toast.showSuccess(`All ${total_tests} tests passed! 🎉`);
        } else {
          toast.showWarning(`${passed}/${total_tests} tests passed (${percentage}%)`);
        }
      } else {
        throw new Error(result.error || 'Test execution failed');
      }
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
  }, [toast]);

  const runQuickTest = useCallback(async () => {
    setState(prev => ({
      ...prev,
      isRunning: true,
      currentTest: 'Running quick test...',
      progress: 0,
      error: null,
    }));

    try {
      const response = await fetch(buildServerUrl('server/api-testing/quick'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      const result = await response.json();

      if (response.ok && result.success) {
        setState(prev => ({
          ...prev,
          isRunning: false,
          currentTest: null,
          progress: 100,
          error: null,
        }));

        const { passed, total } = result;
        const percentage = Math.round((passed / total) * 100);
        
        if (percentage === 100) {
          toast.showSuccess(`Quick test passed! ${passed}/${total} critical endpoints working`);
        } else {
          toast.showWarning(`Quick test: ${passed}/${total} critical endpoints working (${percentage}%)`);
        }
      } else {
        throw new Error(result.error || 'Quick test failed');
      }
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Unknown error';
      setState(prev => ({
        ...prev,
        isRunning: false,
        currentTest: null,
        progress: 0,
        error: errorMsg,
      }));
      toast.showError(`Quick test failed: ${errorMsg}`);
    }
  }, [toast]);

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
