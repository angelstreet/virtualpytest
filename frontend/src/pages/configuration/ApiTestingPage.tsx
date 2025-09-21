import {
  Api as ApiIcon,
  PlayArrow as RunIcon,
  Speed as QuickIcon,
  Download as DownloadIcon,
  Clear as ClearIcon,
  SelectAll as SelectAllIcon,
  DeselectOutlined as DeselectIcon,
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
  Paper,
  Chip,
  Checkbox,
  FormControlLabel,
  Divider,
} from '@mui/material';
import React, { useEffect } from 'react';

import { useApiTesting, TestResult } from '../../hooks/useApiTesting';

const ApiTestingPage: React.FC = () => {
  const {
    isRunning,
    currentTest,
    progress,
    lastReport,
    error,
    availableEndpoints,
    selectedEndpoints,
    runAllTests,
    runQuickTest,
    downloadHtmlReport,
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
          <Typography variant="h6" sx={{ mb: 2 }}>
            Test Controls
          </Typography>

          <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
            <Button
              variant="contained"
              startIcon={isRunning ? <CircularProgress size={20} /> : <RunIcon />}
              onClick={runAllTests}
              disabled={isRunning || selectedEndpoints.length === 0}
              sx={{ minWidth: 140 }}
            >
              {isRunning ? 'Running...' : selectedEndpoints.length === availableEndpoints.length ? 'Run All Tests' : `Run ${selectedEndpoints.length} Tests`}
            </Button>

            <Button
              variant="outlined"
              startIcon={<QuickIcon />}
              onClick={runQuickTest}
              disabled={isRunning}
            >
              Quick Test
            </Button>

            {lastReport && (
              <Button
                variant="outlined"
                startIcon={<DownloadIcon />}
                onClick={() => downloadHtmlReport(lastReport)}
                disabled={isRunning}
              >
                Download HTML
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
            <Box sx={{ mb: 2 }}>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                {currentTest}
              </Typography>
              <LinearProgress variant="indeterminate" />
            </Box>
          )}

          {/* Error Display */}
          {error && (
            <Box sx={{ p: 2, backgroundColor: '#ffebee', borderRadius: 1, mb: 2 }}>
              <Typography color="error" variant="body2">
                <strong>Error:</strong> {error}
              </Typography>
            </Box>
          )}
        </CardContent>
      </Card>

      {/* Endpoint Selection */}
      {availableEndpoints.length > 0 && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="h6" sx={{ mb: 2 }}>
              Select Endpoints to Test ({selectedEndpoints.length}/{availableEndpoints.length} selected)
            </Typography>

            {/* Select All/None Controls */}
            <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
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

            <Divider sx={{ mb: 2 }} />

            {/* Endpoint Checkboxes */}
            <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 1 }}>
              {availableEndpoints.map((endpoint) => (
                <FormControlLabel
                  key={endpoint.name}
                  control={
                    <Checkbox
                      checked={selectedEndpoints.includes(endpoint.name)}
                      onChange={() => toggleEndpoint(endpoint.name)}
                      disabled={isRunning}
                    />
                  }
                  label={
                    <Box>
                      <Typography variant="body2" fontWeight="medium">
                        {endpoint.name}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {endpoint.method} {endpoint.url}
                      </Typography>
                    </Box>
                  }
                />
              ))}
            </Box>

            {selectedEndpoints.length === 0 && (
              <Box sx={{ p: 2, backgroundColor: '#fff3e0', borderRadius: 1, mt: 2 }}>
                <Typography color="warning.main" variant="body2">
                  <strong>Warning:</strong> No endpoints selected. Please select at least one endpoint to test.
                </Typography>
              </Box>
            )}
          </CardContent>
        </Card>
      )}

      {/* Results Summary */}
      {lastReport && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="h6" sx={{ mb: 2 }}>
              Test Results Summary
            </Typography>

            <Box sx={{ display: 'flex', gap: 3, mb: 2 }}>
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

      {/* Detailed Results */}
      {lastReport && lastReport.results.length > 0 && (
        <Card>
          <CardContent>
            <Typography variant="h6" sx={{ mb: 2 }}>
              Detailed Results ({lastReport.results.length} endpoints)
            </Typography>

            <TableContainer component={Paper} variant="outlined">
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Endpoint</TableCell>
                    <TableCell>Method</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Code</TableCell>
                    <TableCell>Time</TableCell>
                    <TableCell>Error</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {lastReport.results.map((result: TestResult, index: number) => (
                    <TableRow
                      key={index}
                      sx={{
                        backgroundColor: result.status === 'pass' ? '#e8f5e8' : '#ffeaea',
                      }}
                    >
                      <TableCell>
                        <Typography variant="body2" fontWeight="medium">
                          {result.endpoint}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {result.url}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={result.method}
                          size="small"
                          variant="outlined"
                        />
                      </TableCell>
                      <TableCell>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <span>{getStatusIcon(result.status)}</span>
                          <Chip
                            label={result.status.toUpperCase()}
                            color={getStatusColor(result.status)}
                            size="small"
                          />
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" fontFamily="monospace">
                          {result.status_code || 'N/A'}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">
                          {result.response_time}ms
                        </Typography>
                      </TableCell>
                      <TableCell>
                        {result.error && (
                          <Typography
                            variant="body2"
                            color="error"
                            sx={{ maxWidth: 200, wordBreak: 'break-word' }}
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

      {/* Empty State */}
      {!lastReport && !isRunning && (
        <Card>
          <CardContent sx={{ textAlign: 'center', py: 6 }}>
            <ApiIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
            <Typography variant="h6" color="text.secondary" sx={{ mb: 1 }}>
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
