import {
  Api as ApiIcon,
  PlayArrow as RunIcon,
  Speed as QuickIcon,
  OpenInNew as OpenInNewIcon,
  Clear as ClearIcon,
  SelectAll as SelectAllIcon,
  DeselectOutlined as DeselectIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  KeyboardArrowDown as ArrowDownIcon,
  KeyboardArrowRight as ArrowRightIcon,
} from '@mui/icons-material';
import {
  Box,
  Button,
  Card,
  CardContent,
  Typography,
  CircularProgress,
  LinearProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Checkbox,
  FormControlLabel,
  Divider,
  Collapse,
  IconButton,
} from '@mui/material';
import React, { useEffect, useState } from 'react';

import { useApiTesting, TestResult, TestReport } from '../hooks/useApiTesting';

const ApiTestingPage: React.FC = () => {
  const [isRoutesExpanded, setIsRoutesExpanded] = useState(true);
  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set());
  
  const {
    isRunning,
    currentTest,
    lastReport,
    error,
    availableEndpoints,
    selectedEndpoints,
    liveResults,
    totalTests,
    completedTests,
    runAllTests,
    runQuickTest,
    clearResults,
    getTestConfig,
    toggleEndpoint,
    selectAllEndpoints,
    deselectAllEndpoints,
  } = useApiTesting();

  // Load test configuration on component mount
  useEffect(() => {
    getTestConfig();
  }, [getTestConfig]);

  // Auto-collapse routes when tests start running
  useEffect(() => {
    if (isRunning) {
      setIsRoutesExpanded(false);
    }
  }, [isRunning]);

  // Clear expanded rows when new tests start
  useEffect(() => {
    if (isRunning) {
      setExpandedRows(new Set());
    }
  }, [isRunning]);

  const toggleRowExpansion = (index: number) => {
    setExpandedRows(prev => {
      const newSet = new Set(prev);
      if (newSet.has(index)) {
        newSet.delete(index);
      } else {
        newSet.add(index);
      }
      return newSet;
    });
  };

  const handleRunAllTests = async () => {
    setIsRoutesExpanded(false); // Collapse before running
    await runAllTests();
  };

  const handleRunQuickTest = async () => {
    setIsRoutesExpanded(false); // Collapse before running
    await runQuickTest();
  };

  const openReportInNewTab = (report: TestReport) => {
    // Generate HTML content
    const htmlContent = generateHtmlReport(report);
    
    // Create blob and URL
    const blob = new Blob([htmlContent], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    
    // Open in new tab
    window.open(url, '_blank');
    
    // Clean up URL after a delay
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };

  const generateHtmlReport = (report: TestReport) => {
    const passed = report.passed;
    const failed = report.failed;
    const percentage = Math.round((passed / report.total_tests) * 100);
    
    return `<!DOCTYPE html>
<html>
<head>
    <title>API Test Report - ${report.timestamp}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .summary { background: #f8f9fa; padding: 20px; border-radius: 5px; margin-bottom: 20px; border-left: 4px solid #007bff; }
        .pass { color: #28a745; font-weight: bold; }
        .fail { color: #dc3545; font-weight: bold; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #dee2e6; }
        th { background-color: #f8f9fa; font-weight: 600; }
        .status-pass { background-color: #d4edda; }
        .status-fail { background-color: #f8d7da; }
        .badge { padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }
        .badge-grey { background: #6c757d; color: white; }
        .badge-success { background: #28a745; color: white; }
        .badge-danger { background: #dc3545; color: white; }
        h1 { color: #333; margin-bottom: 10px; }
        .meta { color: #666; font-size: 14px; }
        .expandable-row { cursor: pointer; }
        .expandable-row:hover { background-color: #f8f9fa; }
        .expand-icon { display: inline-block; width: 20px; text-align: center; transition: transform 0.2s; }
        .expand-icon.expanded { transform: rotate(90deg); }
        .response-details { display: none; background: #f8f9fa; padding: 15px; border-left: 4px solid #007bff; }
        .response-details.show { display: block; }
        .response-body { background: #fff; border: 1px solid #dee2e6; border-radius: 4px; padding: 10px; font-family: monospace; font-size: 12px; white-space: pre-wrap; word-break: break-all; max-height: 300px; overflow-y: auto; }
    </style>
    <script>
        function toggleResponse(index) {
            const icon = document.getElementById('icon-' + index);
            const details = document.getElementById('details-' + index);
            
            if (details.classList.contains('show')) {
                details.classList.remove('show');
                icon.classList.remove('expanded');
                icon.textContent = '▶';
            } else {
                details.classList.add('show');
                icon.classList.add('expanded');
                icon.textContent = '▼';
            }
        }
    </script>
</head>
<body>
    <div class="container">
        <div class="summary">
            <h1>API Test Report</h1>
            <div class="meta">
                <p><strong>Git Commit:</strong> <code>${report.git_commit}</code></p>
                <p><strong>Timestamp:</strong> ${new Date(report.timestamp).toLocaleString()}</p>
                <p><strong>Test Type:</strong> ${(report as any).quick_test ? 'Quick Test (Critical Routes)' : 'Full Test (All Routes)'}</p>
                <p><strong>Results:</strong> 
                    <span class="pass">${passed} passed</span>, 
                    <span class="fail">${failed} failed</span> 
                    <strong>(${percentage}% success rate)</strong>
                </p>
            </div>
        </div>
        
        <table>
            <thead>
                <tr>
                    <th style="width: 30px;"></th>
                    <th>Route</th>
                    <th>Method</th>
                    <th>Status</th>
                    <th>Status Code</th>
                    <th>Response Time</th>
                    <th>Error</th>
                </tr>
            </thead>
            <tbody>
                ${report.results.map((result: TestResult, index: number) => `
                    <tr class="expandable-row status-${result.status}" onclick="toggleResponse(${index})">
                        <td><span id="icon-${index}" class="expand-icon">▶</span></td>
                        <td><strong>${result.endpoint}</strong><br><small style="color: #666;">${result.url}</small></td>
                        <td><span class="badge badge-grey">${result.method}</span></td>
                        <td>
                            <span class="badge ${result.status === 'pass' ? 'badge-success' : 'badge-danger'}">
                                ${result.status === 'pass' ? 'PASS' : 'FAIL'}
                            </span>
                        </td>
                        <td><code>${result.status_code || 'N/A'}</code></td>
                        <td>${result.response_time}ms</td>
                        <td style="max-width: 300px; word-break: break-word;">${result.error || ''}</td>
                    </tr>
                    <tr>
                        <td colspan="7" style="padding: 0;">
                            <div id="details-${index}" class="response-details">
                                <h4 style="margin-top: 0;">Response Details</h4>
                                <p><strong>Status Code:</strong> ${result.status_code || 'N/A'}</p>
                                <p><strong>Response Time:</strong> ${result.response_time}ms</p>
                                ${result.error ? `<p><strong>Error:</strong> <span style="color: #dc3545;">${result.error}</span></p>` : ''}
                                <div>
                                    <strong>Response Body:</strong>
                                    <div class="response-body">${
                                        result.response_body 
                                            ? (typeof result.response_body === 'string' 
                                                ? result.response_body 
                                                : JSON.stringify(result.response_body, null, 2))
                                            : 'No response data available'
                                    }</div>
                                </div>
                            </div>
                        </td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
        
        <div style="margin-top: 30px; padding: 15px; background: #e9ecef; border-radius: 5px; text-align: center;">
            <small>Generated by VirtualPyTest API Testing System</small>
        </div>
    </div>
</body>
</html>`;
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pass': return 'success';
      case 'fail': return 'error';
      default: return 'default';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'pass': return '✅';
      case 'fail': return '❌';
      default: return '⏸️';
    }
  };

  return (
    <Box sx={{ p: 3, maxWidth: 1200, mx: 'auto' }}>
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <ApiIcon sx={{ mr: 2, fontSize: 32, color: 'primary.main' }} />
        <Typography variant="h4" component="h1">
          API Testing
        </Typography>
      </Box>

      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        Test all server API endpoints systematically and generate detailed reports.
      </Typography>

      {/* Control Panel */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" sx={{ mb: 0.5 }}>
            Test Controls
          </Typography>

          <Box sx={{ display: 'flex', gap: 2, mb: 0.5 }}>
            <Button
              variant="contained"
              startIcon={isRunning ? <CircularProgress size={20} /> : <RunIcon />}
              onClick={handleRunAllTests}
              disabled={isRunning || selectedEndpoints.length === 0}
              sx={{ minWidth: 140 }}
            >
              {isRunning ? 'Running...' : selectedEndpoints.length === availableEndpoints.length ? 'Run All Tests' : `Run ${selectedEndpoints.length} Tests`}
            </Button>

            <Button
              variant="outlined"
              startIcon={<QuickIcon />}
              onClick={handleRunQuickTest}
              disabled={isRunning}
            >
              Quick Test
            </Button>

            {lastReport && (
              <Button
                variant="outlined"
                startIcon={<OpenInNewIcon />}
                onClick={() => openReportInNewTab(lastReport)}
                disabled={isRunning}
              >
                Open Report
              </Button>
            )}

            <Button
              variant="outlined"
              startIcon={<ClearIcon />}
              onClick={clearResults}
              disabled={isRunning}
            >
              Clear
            </Button>
          </Box>

          {/* Progress */}
          {isRunning && (
            <Box sx={{ mb: 0.5 }}>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 0.5 }}>
                {currentTest} ({completedTests}/{totalTests})
              </Typography>
              <LinearProgress 
                variant="determinate" 
                value={totalTests > 0 ? (completedTests / totalTests) * 100 : 0}
                sx={{ mb: 0.5 }}
              />
              <Typography variant="caption" color="text.secondary">
                {Math.round(totalTests > 0 ? (completedTests / totalTests) * 100 : 0)}% complete
              </Typography>
            </Box>
          )}

          {/* Error Display */}
          {error && (
            <Box sx={{ p: 2, backgroundColor: '#ffebee', borderRadius: 1, mb: 0.5 }}>
              <Typography color="error" variant="body2">
                <strong>Error:</strong> {error}
              </Typography>
            </Box>
          )}
        </CardContent>
      </Card>

      {/* Route Selection - Always in same position, just collapses */}
      {availableEndpoints.length > 0 && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 0.5 }}>
              <Typography variant="h6">
                Select Routes ({selectedEndpoints.length}/{availableEndpoints.length} selected)
              </Typography>
              <IconButton
                onClick={() => setIsRoutesExpanded(!isRoutesExpanded)}
                sx={{ ml: 1 }}
              >
                {isRoutesExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
              </IconButton>
            </Box>

            <Collapse in={isRoutesExpanded}>
              {/* Select All/None Controls */}
              <Box sx={{ display: 'flex', gap: 2, mb: 0.5 }}>
                <Button
                  variant="outlined"
                  size="small"
                  startIcon={<SelectAllIcon />}
                  onClick={selectAllEndpoints}
                  disabled={isRunning || selectedEndpoints.length === availableEndpoints.length}
                >
                  Select All
                </Button>
                <Button
                  variant="outlined"
                  size="small"
                  startIcon={<DeselectIcon />}
                  onClick={deselectAllEndpoints}
                  disabled={isRunning || selectedEndpoints.length === 0}
                >
                  Deselect All
                </Button>
              </Box>

              <Divider sx={{ mb: 0.5 }} />

              {/* Route Checkboxes - Compact 2-column layout */}
              <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 1 }}>
                {availableEndpoints.map((endpoint) => (
                  <FormControlLabel
                    key={endpoint.name}
                    control={
                      <Checkbox
                        checked={selectedEndpoints.includes(endpoint.name)}
                        onChange={() => toggleEndpoint(endpoint.name)}
                        disabled={isRunning}
                        size="small"
                      />
                    }
                    label={
                        <Typography 
                          variant="caption" 
                          sx={{ 
                            fontSize: '0.75rem',
                            lineHeight: 1.3,
                            display: 'block',
                            wordBreak: 'break-word',
                            maxWidth: '100%'
                          }}
                        >
                        <Box component="span" sx={{ fontWeight: 'medium' }}>
                          {endpoint.name}
                        </Box>
                        <Box component="span" sx={{ color: 'text.secondary', ml: 1 }}>
                          - {endpoint.method} {endpoint.url}
                        </Box>
                      </Typography>
                    }
                    sx={{ 
                      margin: 0,
                      alignItems: 'center',
                      '& .MuiCheckbox-root': {
                        padding: '4px',
                        alignSelf: 'flex-start',
                        marginTop: '1px'
                      },
                      '& .MuiFormControlLabel-label': {
                        paddingLeft: '4px',
                        marginTop: 0
                      }
                    }}
                  />
                ))}
              </Box>

              {selectedEndpoints.length === 0 && (
                <Box sx={{ p: 2, backgroundColor: '#fff3e0', borderRadius: 1, mt: 0.5 }}>
                  <Typography color="warning.main" variant="body2">
                    <strong>Warning:</strong> No routes selected. Please select at least one route to test.
                  </Typography>
                </Box>
              )}
            </Collapse>
          </CardContent>
        </Card>
      )}

      {/* Live Results - Show during and after testing */}
      {(isRunning || liveResults.length > 0) && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="h6" sx={{ mb: 0.5 }}>
              {isRunning ? 'Test Progress' : 'Test Results'} ({liveResults.length} {liveResults.length === 1 ? 'route' : 'routes'})
            </Typography>

            <TableContainer sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 1, maxHeight: 400, overflow: 'auto' }}>
              <Table size="small" stickyHeader>
                <TableHead>
                  <TableRow sx={{ '&:hover': { backgroundColor: 'transparent !important' }, '&:hover td': { backgroundColor: 'transparent !important' } }}>
                    <TableCell sx={{ backgroundColor: 'transparent !important', border: 'none', borderBottom: '1px solid', borderColor: 'divider', py: 1, width: '40px' }}>
                      <Typography variant="caption" sx={{ fontSize: '0.75rem', fontWeight: 'bold' }}></Typography>
                    </TableCell>
                    <TableCell sx={{ backgroundColor: 'transparent !important', border: 'none', borderBottom: '1px solid', borderColor: 'divider', py: 1 }}>
                      <Typography variant="caption" sx={{ fontSize: '0.75rem', fontWeight: 'bold' }}>Route</Typography>
                    </TableCell>
                    <TableCell sx={{ backgroundColor: 'transparent !important', border: 'none', borderBottom: '1px solid', borderColor: 'divider', py: 1 }}>
                      <Typography variant="caption" sx={{ fontSize: '0.75rem', fontWeight: 'bold' }}>Method</Typography>
                    </TableCell>
                    <TableCell sx={{ backgroundColor: 'transparent !important', border: 'none', borderBottom: '1px solid', borderColor: 'divider', py: 1 }}>
                      <Typography variant="caption" sx={{ fontSize: '0.75rem', fontWeight: 'bold' }}>Status</Typography>
                    </TableCell>
                    <TableCell sx={{ backgroundColor: 'transparent !important', border: 'none', borderBottom: '1px solid', borderColor: 'divider', py: 1 }}>
                      <Typography variant="caption" sx={{ fontSize: '0.75rem', fontWeight: 'bold' }}>Time</Typography>
                    </TableCell>
                    <TableCell sx={{ backgroundColor: 'transparent !important', border: 'none', borderBottom: '1px solid', borderColor: 'divider', py: 1 }}>
                      <Typography variant="caption" sx={{ fontSize: '0.75rem', fontWeight: 'bold' }}>Error</Typography>
                    </TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {liveResults.map((result: TestResult, index: number) => (
                    <React.Fragment key={index}>
                      <TableRow
                        sx={{
                          backgroundColor: 'transparent !important',
                          '&:hover': {
                            backgroundColor: 'transparent !important',
                          },
                          '&:hover td': {
                            backgroundColor: 'transparent !important',
                          },
                          cursor: 'pointer'
                        }}
                        onClick={() => toggleRowExpansion(index)}
                      >
                        <TableCell sx={{ backgroundColor: 'transparent !important', border: 'none', borderBottom: '1px solid', borderColor: 'divider', py: 0.5 }}>
                          <IconButton size="small" sx={{ p: 0 }}>
                            {expandedRows.has(index) ? <ArrowDownIcon fontSize="small" /> : <ArrowRightIcon fontSize="small" />}
                          </IconButton>
                        </TableCell>
                        <TableCell sx={{ backgroundColor: 'transparent !important', border: 'none', borderBottom: '1px solid', borderColor: 'divider', py: 0.5 }}>
                          <Typography 
                            variant="caption" 
                            sx={{ 
                              fontSize: '0.75rem',
                              lineHeight: 1.2,
                              display: 'block',
                              whiteSpace: 'nowrap',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              maxWidth: '300px'
                            }}
                          >
                            <Box component="span" sx={{ fontWeight: 'medium' }}>
                              {result.endpoint}
                            </Box>
                            <Box component="span" sx={{ color: 'text.secondary', ml: 1 }}>
                              - {result.url}
                            </Box>
                          </Typography>
                        </TableCell>
                        <TableCell sx={{ backgroundColor: 'transparent !important', border: 'none', borderBottom: '1px solid', borderColor: 'divider', py: 0.5 }}>
                          <Chip
                            label={result.method}
                            size="small"
                            variant="outlined"
                            sx={{ 
                              backgroundColor: 'transparent !important',
                              fontSize: '0.7rem',
                              height: '20px'
                            }}
                          />
                        </TableCell>
                        <TableCell sx={{ backgroundColor: 'transparent !important', border: 'none', borderBottom: '1px solid', borderColor: 'divider', py: 0.5 }}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                            <span style={{ fontSize: '0.8rem' }}>{getStatusIcon(result.status)}</span>
                            <Chip
                              label={result.status.toUpperCase()}
                              color={getStatusColor(result.status)}
                              size="small"
                              sx={{ 
                                backgroundColor: 'transparent !important',
                                fontSize: '0.7rem',
                                height: '20px'
                              }}
                            />
                          </Box>
                        </TableCell>
                        <TableCell sx={{ backgroundColor: 'transparent !important', border: 'none', borderBottom: '1px solid', borderColor: 'divider', py: 0.5 }}>
                          <Typography variant="caption" sx={{ fontSize: '0.75rem' }}>
                            {result.response_time}ms
                          </Typography>
                        </TableCell>
                        <TableCell sx={{ backgroundColor: 'transparent !important', border: 'none', borderBottom: '1px solid', borderColor: 'divider', py: 0.5 }}>
                          {result.error && (
                            <Typography
                              variant="caption"
                              color="error"
                              sx={{ 
                                maxWidth: 150, 
                                wordBreak: 'break-word',
                                fontSize: '0.75rem',
                                lineHeight: 1.2
                              }}
                            >
                              {result.error}
                            </Typography>
                          )}
                        </TableCell>
                      </TableRow>
                      
                      {/* Expanded Row Content */}
                      {expandedRows.has(index) && (
                        <TableRow
                          sx={{
                            backgroundColor: 'transparent !important',
                            '&:hover': {
                              backgroundColor: 'transparent !important',
                            },
                            '&:hover td': {
                              backgroundColor: 'background.default !important',
                            },
                          }}
                        >
                          <TableCell sx={{ backgroundColor: 'transparent !important', border: 'none', py: 0 }} />
                          <TableCell 
                            colSpan={5} 
                            sx={{ 
                              backgroundColor: 'background.default !important', 
                              border: 'none', 
                              borderBottom: '1px solid', 
                              borderColor: 'divider',
                              py: 2
                            }}
                          >
                            <Box sx={{ maxWidth: '100%', overflow: 'auto' }}>
                              {/* Status Code */}
                              <Box sx={{ mb: 1 }}>
                                <Typography variant="caption" sx={{ fontSize: '0.7rem', fontWeight: 'medium' }}>
                                  Status Code: <Box component="span" sx={{ fontFamily: 'monospace' }}>{result.status_code || 'N/A'}</Box>
                                </Typography>
                              </Box>
                              
                              {/* Raw Response */}
                              {result.response_body ? (
                                <Box 
                                  sx={{ 
                                    backgroundColor: 'background.paper', 
                                    p: 1, 
                                    borderRadius: 1, 
                                    border: '1px solid', 
                                    borderColor: 'divider',
                                    maxHeight: '200px',
                                    overflow: 'auto'
                                  }}
                                >
                                  <Typography 
                                    variant="caption" 
                                    sx={{ 
                                      fontSize: '0.65rem', 
                                      fontFamily: 'monospace',
                                      whiteSpace: 'pre-wrap',
                                      wordBreak: 'break-all'
                                    }}
                                  >
                                    {typeof result.response_body === 'string' ? result.response_body : JSON.stringify(result.response_body, null, 2)}
                                  </Typography>
                                </Box>
                              ) : (
                                <Typography variant="caption" sx={{ fontSize: '0.7rem', color: 'text.secondary', fontStyle: 'italic' }}>
                                  No response data available
                                </Typography>
                              )}
                            </Box>
                          </TableCell>
                        </TableRow>
                      )}
                    </React.Fragment>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>

            {/* Summary for completed tests */}
            {!isRunning && liveResults.length > 0 && (
              <Box sx={{ mt: 0.5, p: 2, backgroundColor: 'background.default', borderRadius: 1 }}>
                <Typography variant="body2">
                  <strong>Summary:</strong> {(() => {
                    const passed = liveResults.filter(r => r.status === 'pass').length;
                    const failed = liveResults.filter(r => r.status === 'fail').length;
                    const total = liveResults.length;
                    const percentage = total > 0 ? Math.round((passed / total) * 100) : 0;
                    return `${passed} passed, ${failed} failed (${percentage}% success rate)`;
                  })()}
                </Typography>
              </Box>
            )}
          </CardContent>
        </Card>
      )}

      {/* Results Summary - Only show if there's a report (normal tests) and no live results */}
      {lastReport && !liveResults.length && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="h6" sx={{ mb: 0.5 }}>
              Test Results Summary
            </Typography>

            <Box sx={{ display: 'flex', gap: 3, mb: 0.5 }}>
              <Box>
                <Typography variant="body2" color="text.secondary">
                  Git Commit
                </Typography>
                <Typography variant="body1" fontFamily="monospace">
                  {lastReport.git_commit}
                </Typography>
              </Box>
              <Box>
                <Typography variant="body2" color="text.secondary">
                  Timestamp
                </Typography>
                <Typography variant="body1">
                  {new Date(lastReport.timestamp).toLocaleString()}
                </Typography>
              </Box>
              <Box>
                <Typography variant="body2" color="text.secondary">
                  Success Rate
                </Typography>
                <Typography variant="body1">
                  {lastReport.passed}/{lastReport.total_tests} ({Math.round((lastReport.passed / lastReport.total_tests) * 100)}%)
                </Typography>
              </Box>
            </Box>

            <Box sx={{ display: 'flex', gap: 1 }}>
              <Chip
                label={`${lastReport.passed} Passed`}
                color="success"
                size="small"
              />
              <Chip
                label={`${lastReport.failed} Failed`}
                color="error"
                size="small"
              />
            </Box>
          </CardContent>
        </Card>
      )}

      {/* Detailed Results - Only show if there's a report (normal tests) and no live results */}
      {lastReport && lastReport.results.length > 0 && !liveResults.length && (
        <Card>
          <CardContent>
            <Typography variant="h6" sx={{ mb: 0.5 }}>
              Detailed Results ({lastReport.results.length} routes)
            </Typography>

            <TableContainer sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 1 }}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ backgroundColor: 'transparent', border: 'none', borderBottom: '1px solid', borderColor: 'divider', py: 1 }}>
                      <Typography variant="caption" sx={{ fontSize: '0.75rem', fontWeight: 'bold' }}>Route</Typography>
                    </TableCell>
                    <TableCell sx={{ backgroundColor: 'transparent', border: 'none', borderBottom: '1px solid', borderColor: 'divider', py: 1 }}>
                      <Typography variant="caption" sx={{ fontSize: '0.75rem', fontWeight: 'bold' }}>Method</Typography>
                    </TableCell>
                    <TableCell sx={{ backgroundColor: 'transparent', border: 'none', borderBottom: '1px solid', borderColor: 'divider', py: 1 }}>
                      <Typography variant="caption" sx={{ fontSize: '0.75rem', fontWeight: 'bold' }}>Status</Typography>
                    </TableCell>
                    <TableCell sx={{ backgroundColor: 'transparent', border: 'none', borderBottom: '1px solid', borderColor: 'divider', py: 1 }}>
                      <Typography variant="caption" sx={{ fontSize: '0.75rem', fontWeight: 'bold' }}>Code</Typography>
                    </TableCell>
                    <TableCell sx={{ backgroundColor: 'transparent', border: 'none', borderBottom: '1px solid', borderColor: 'divider', py: 1 }}>
                      <Typography variant="caption" sx={{ fontSize: '0.75rem', fontWeight: 'bold' }}>Time</Typography>
                    </TableCell>
                    <TableCell sx={{ backgroundColor: 'transparent', border: 'none', borderBottom: '1px solid', borderColor: 'divider', py: 1 }}>
                      <Typography variant="caption" sx={{ fontSize: '0.75rem', fontWeight: 'bold' }}>Error</Typography>
                    </TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {lastReport.results.map((result: TestResult, index: number) => (
                    <TableRow
                      key={index}
                      sx={{
                        backgroundColor: 'transparent',
                        '&:hover': {
                          backgroundColor: 'transparent',
                        },
                      }}
                    >
                      <TableCell sx={{ backgroundColor: 'transparent', border: 'none', borderBottom: '1px solid', borderColor: 'divider', py: 0.5 }}>
                        <Typography 
                          variant="caption" 
                          sx={{ 
                            fontSize: '0.75rem',
                            lineHeight: 1.2,
                            display: 'block',
                            whiteSpace: 'nowrap',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            maxWidth: '300px'
                          }}
                        >
                          <Box component="span" sx={{ fontWeight: 'medium' }}>
                            {result.endpoint}
                          </Box>
                          <Box component="span" sx={{ color: 'text.secondary', ml: 1 }}>
                            - {result.url}
                          </Box>
                        </Typography>
                      </TableCell>
                      <TableCell sx={{ backgroundColor: 'transparent', border: 'none', borderBottom: '1px solid', borderColor: 'divider', py: 0.5 }}>
                        <Chip
                          label={result.method}
                          size="small"
                          variant="outlined"
                          sx={{ 
                            backgroundColor: 'transparent',
                            fontSize: '0.7rem',
                            height: '20px'
                          }}
                        />
                      </TableCell>
                      <TableCell sx={{ backgroundColor: 'transparent', border: 'none', borderBottom: '1px solid', borderColor: 'divider', py: 0.5 }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                          <span style={{ fontSize: '0.8rem' }}>{getStatusIcon(result.status)}</span>
                          <Chip
                            label={result.status.toUpperCase()}
                            color={getStatusColor(result.status)}
                            size="small"
                            sx={{ 
                              backgroundColor: 'transparent',
                              fontSize: '0.7rem',
                              height: '20px'
                            }}
                          />
                        </Box>
                      </TableCell>
                      <TableCell sx={{ backgroundColor: 'transparent', border: 'none', borderBottom: '1px solid', borderColor: 'divider', py: 0.5 }}>
                        <Typography variant="caption" fontFamily="monospace" sx={{ fontSize: '0.75rem' }}>
                          {result.status_code || 'N/A'}
                        </Typography>
                      </TableCell>
                      <TableCell sx={{ backgroundColor: 'transparent', border: 'none', borderBottom: '1px solid', borderColor: 'divider', py: 0.5 }}>
                        <Typography variant="caption" sx={{ fontSize: '0.75rem' }}>
                          {result.response_time}ms
                        </Typography>
                      </TableCell>
                      <TableCell sx={{ backgroundColor: 'transparent', border: 'none', borderBottom: '1px solid', borderColor: 'divider', py: 0.5 }}>
                        {result.error && (
                          <Typography
                            variant="caption"
                            color="error"
                            sx={{ 
                              maxWidth: 200, 
                              wordBreak: 'break-word',
                              fontSize: '0.75rem',
                              lineHeight: 1.2
                            }}
                          >
                            {result.error}
                          </Typography>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      )}

      {/* Empty State - Only show if no results at all */}
      {!lastReport && !isRunning && liveResults.length === 0 && (
        <Card>
          <CardContent sx={{ textAlign: 'center', py: 6 }}>
            <ApiIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 0.5 }} />
            <Typography variant="h6" color="text.secondary" sx={{ mb: 0.5 }}>
              No test results yet
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Run tests to see detailed API endpoint status and performance metrics
            </Typography>
          </CardContent>
        </Card>
      )}
    </Box>
  );
};

export default ApiTestingPage;
