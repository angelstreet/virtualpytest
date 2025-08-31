import {
  Assessment as ReportsIcon,
  CheckCircle as PassIcon,
  Error as FailIcon,
  HourglassEmpty as RunningIcon,
  Link as LinkIcon,
  SmartToy as AiIcon,
  Person as ManualIcon,
  Help as UnknownIcon,
  Comment as CommentIcon,
  Check as ValidIcon,
  Warning as DiscardedIcon,
  Visibility as DetailsIcon,
  VisibilityOff as HideDetailsIcon,
  CheckCircle as CheckedIcon,
} from '@mui/icons-material';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  CircularProgress,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Tooltip,
  IconButton,
  Switch,
  FormControlLabel,
} from '@mui/material';
import React, { useState, useEffect } from 'react';

import { useScriptResults, ScriptResult } from '../hooks/pages/useScriptResults';

const TestReports: React.FC = () => {
  const { getAllScriptResults } = useScriptResults();
  const [scriptResults, setScriptResults] = useState<ScriptResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [discardModalOpen, setDiscardModalOpen] = useState(false);
  const [selectedDiscardComment, setSelectedDiscardComment] = useState<{
    comment: string;
    result: ScriptResult;
  } | null>(null);
  const [showDetailedColumns, setShowDetailedColumns] = useState(false);

  // Load script results on component mount
  useEffect(() => {
    const loadScriptResults = async () => {
      try {
        setLoading(true);
        setError(null);
        const results = await getAllScriptResults();
        setScriptResults(results);
      } catch (err) {
        console.error('[@component:TestReports] Error loading script results:', err);
        setError(err instanceof Error ? err.message : 'Failed to load script results');
      } finally {
        setLoading(false);
      }
    };

    loadScriptResults();
  }, [getAllScriptResults]);

  // Auto-refresh when there are running scripts
  useEffect(() => {
    const hasRunningScripts = scriptResults.some(result => getExecutionStatus(result) === 'running');
    
    if (hasRunningScripts) {
      const intervalId = setInterval(async () => {
        try {
          const results = await getAllScriptResults();
          setScriptResults(results);
        } catch (err) {
          console.error('[@component:TestReports] Error refreshing script results:', err);
        }
      }, 5000); // Refresh every 5 seconds

      return () => clearInterval(intervalId);
    }
  }, [scriptResults, getAllScriptResults]);

  // Calculate stats
  const totalReports = scriptResults.length;
  const passedReports = scriptResults.filter((result) => result.success).length;
  const successRate = totalReports > 0 ? ((passedReports / totalReports) * 100).toFixed(1) : 'N/A';

  // Calculate this week's reports (last 7 days)
  const oneWeekAgo = new Date();
  oneWeekAgo.setDate(oneWeekAgo.getDate() - 7);
  const thisWeekReports = scriptResults.filter(
    (result) => new Date(result.created_at) >= oneWeekAgo,
  ).length;

  // Calculate average duration
  const validDurations = scriptResults.filter((result) => result.execution_time_ms !== null);
  const avgDuration =
    validDurations.length > 0
      ? formatDuration(
          validDurations.reduce((sum, result) => sum + (result.execution_time_ms || 0), 0) /
            validDurations.length,
        )
      : 'N/A';

  // Format duration helper
  function formatDuration(ms: number): string {
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    const minutes = Math.floor(ms / 60000);
    const seconds = ((ms % 60000) / 1000).toFixed(1);
    return `${minutes}m ${seconds}s`;
  }

  // Format date helper
  function formatDate(dateString: string): string {
    return new Date(dateString).toLocaleString();
  }

  // Convert report URL to logs URL helper
  function getLogsUrl(reportUrl: string): string {
    return reportUrl.replace('script-reports', 'script-logs').replace('report.html', 'execution.txt');
  }

  // Determine execution status helper
  function getExecutionStatus(result: ScriptResult): 'running' | 'passed' | 'failed' {
    // If success is true, it's definitely passed
    if (result.success) {
      return 'passed';
    }
    
    // If success is false, check if it's still running or actually failed
    // Logic: If started_at and completed_at are very close (< 5 seconds), it's likely still running
    // because update_script_execution_result hasn't been called yet
    const startTime = new Date(result.started_at).getTime();
    const completedTime = new Date(result.completed_at).getTime();
    const timeDiff = Math.abs(completedTime - startTime);
    
    // If less than 5 seconds difference AND no execution time recorded, likely still running
    if (timeDiff < 5000 && !result.execution_time_ms) {
      return 'running';
    }
    
    // Otherwise, it's actually failed
    return 'failed';
  }

  // Note: handleDiscardToggle removed - discard status is now managed by AI analysis
  // Users can view AI analysis results but cannot manually toggle discard status

  // Handle discard comment modal
  const handleDiscardCommentClick = (result: ScriptResult) => {
    if (result.discard_comment) {
      setSelectedDiscardComment({
        comment: result.discard_comment,
        result: result,
      });
      setDiscardModalOpen(true);
    }
  };

  const handleCloseDiscardModal = () => {
    setDiscardModalOpen(false);
    setSelectedDiscardComment(null);
  };

  // Note: toggleRowExpansion removed - not needed for this implementation

  // Get individual discard analysis components
  const getCheckedStatus = (result: ScriptResult) => {
    if (result.checked === undefined || result.checked === null) {
      return (
        <Chip
          icon={<UnknownIcon />}
          label="Pending"
          color="default"
          size="small"
          variant="outlined"
        />
      );
    }
    return (
      <Chip
        icon={<CheckedIcon />}
        label={result.checked ? 'Checked' : 'Unchecked'}
        color={result.checked ? 'success' : 'default'}
        size="small"
      />
    );
  };

  const getDiscardStatus = (result: ScriptResult) => {
    if (!result.checked) {
      return (
        <Typography variant="body2" color="text.disabled">
          -
        </Typography>
      );
    }
    return (
      <Chip
        icon={result.discard ? <DiscardedIcon /> : <ValidIcon />}
        label={result.discard ? 'Discarded' : 'Valid'}
        color={result.discard ? 'warning' : 'success'}
        size="small"
      />
    );
  };

  const getCheckType = (result: ScriptResult) => {
    if (!result.check_type) {
      return (
        <Typography variant="body2" color="text.disabled">
          -
        </Typography>
      );
    }
    const isAI = result.check_type === 'ai';
    return (
      <Chip
        icon={isAI ? <AiIcon /> : <ManualIcon />}
        label={isAI ? 'AI' : 'Manual'}
        color="primary"
        size="small"
        variant="outlined"
      />
    );
  };


  const getDiscardComment = (result: ScriptResult) => {
    if (!result.discard_comment) {
      return (
        <Typography variant="body2" color="text.disabled">
          -
        </Typography>
      );
    }
    return (
      <Tooltip title="View full comment">
        <IconButton
          size="small"
          onClick={() => handleDiscardCommentClick(result)}
          sx={{ p: 0.25 }}
        >
          <CommentIcon fontSize="small" />
        </IconButton>
      </Tooltip>
    );
  };

  // Loading state component
  const LoadingState = () => (
    <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
      <CircularProgress />
    </Box>
  );

  // Note: EmptyState component removed - now handled inline with dynamic colspan

  return (
    <Box>
      <Box sx={{ mb: 1 }}>
        <Typography variant="h4" gutterBottom>
          Test Reports
        </Typography>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 1 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Quick Stats */}
      <Box sx={{ mb: 0.5 }}>
        <Card>
          <CardContent sx={{ py: 0.5 }}>
            <Box display="flex" alignItems="center" justifyContent="space-between">
              <Box display="flex" alignItems="center" gap={1}>
                <ReportsIcon color="primary" />
                <Typography variant="h6">Quick Stats</Typography>
              </Box>

              <Box display="flex" alignItems="center" gap={4}>
                <Box display="flex" alignItems="center" gap={1}>
                  <Typography variant="body2">Total Reports</Typography>
                  <Typography variant="body2" fontWeight="bold">
                    {totalReports}
                  </Typography>
                </Box>
                <Box display="flex" alignItems="center" gap={1}>
                  <Typography variant="body2">This Week</Typography>
                  <Typography variant="body2" fontWeight="bold">
                    {thisWeekReports}
                  </Typography>
                </Box>
                <Box display="flex" alignItems="center" gap={1}>
                  <Typography variant="body2">Success Rate</Typography>
                  <Typography variant="body2" fontWeight="bold">
                    {successRate}%
                  </Typography>
                </Box>
                <Box display="flex" alignItems="center" gap={1}>
                  <Typography variant="body2">Avg Duration</Typography>
                  <Typography variant="body2" fontWeight="bold">
                    {avgDuration}
                  </Typography>
                </Box>
              </Box>
            </Box>
          </CardContent>
        </Card>
      </Box>

      {/* Recent Test Reports */}
      <Card>
        <CardContent>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h6">
              Recent Test Reports
            </Typography>
            <FormControlLabel
              control={
                <Switch
                  checked={showDetailedColumns}
                  onChange={(e) => setShowDetailedColumns(e.target.checked)}
                  size="small"
                />
              }
              label={
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  {showDetailedColumns ? <HideDetailsIcon /> : <DetailsIcon />}
                  <Typography variant="body2">
                    {showDetailedColumns ? 'Hide' : 'Show'} Discard Analysis Details
                  </Typography>
                </Box>
              }
            />
          </Box>

          <TableContainer component={Paper} variant="outlined">
            <Table size="small" sx={{ '& .MuiTableRow-root': { height: '40px' }, minWidth: '1400px' }}>
              <TableHead>
                <TableRow>
                  <TableCell sx={{ py: 1 }}>
                    <strong>Script Name</strong>
                  </TableCell>
                  <TableCell sx={{ py: 1 }}>
                    <strong>UI Name</strong>
                  </TableCell>
                  <TableCell sx={{ py: 1 }}>
                    <strong>Host</strong>
                  </TableCell>
                  <TableCell sx={{ py: 1 }}>
                    <strong>Device</strong>
                  </TableCell>
                  <TableCell sx={{ py: 1 }}>
                    <strong>Status</strong>
                  </TableCell>
                  <TableCell sx={{ py: 1 }}>
                    <strong>Duration</strong>
                  </TableCell>
                  <TableCell sx={{ py: 1 }}>
                    <strong>Started</strong>
                  </TableCell>
                  <TableCell sx={{ py: 1 }}>
                    <strong>Report</strong>
                  </TableCell>
                  <TableCell sx={{ py: 1 }}>
                    <strong>Logs</strong>
                  </TableCell>
                  {showDetailedColumns && (
                    <>
                      <TableCell sx={{ py: 1 }}>
                        <strong>Checked</strong>
                      </TableCell>
                      <TableCell sx={{ py: 1 }}>
                        <strong>Discard</strong>
                      </TableCell>
                      <TableCell sx={{ py: 1 }}>
                        <strong>Checked By</strong>
                      </TableCell>
                      <TableCell sx={{ py: 1 }}>
                        <strong>Comment</strong>
                      </TableCell>
                    </>
                  )}
                </TableRow>
              </TableHead>
              <TableBody>
                {loading ? (
                  <TableRow>
                    <TableCell colSpan={showDetailedColumns ? 13 : 9}>
                      <LoadingState />
                    </TableCell>
                  </TableRow>
                ) : scriptResults.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={showDetailedColumns ? 13 : 9} sx={{ textAlign: 'center', py: 4 }}>
                      <Typography variant="body2" color="textSecondary">
                        No script results available yet
                      </Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  scriptResults.map((result) => (
                    <TableRow
                      key={result.id}
                      sx={{
                        '&:hover': {
                          backgroundColor: 'rgba(0, 0, 0, 0.04) !important',
                        },
                        opacity: result.discard ? 0.5 : 1,
                      }}
                    >
                      <TableCell sx={{ py: 0.5 }}>{result.script_name}</TableCell>
                      <TableCell sx={{ py: 0.5 }}>{result.userinterface_name || 'N/A'}</TableCell>
                      <TableCell sx={{ py: 0.5 }}>{result.host_name}</TableCell>
                      <TableCell sx={{ py: 0.5 }}>{result.device_name}</TableCell>
                      <TableCell sx={{ py: 0.5 }}>
                        {(() => {
                          const status = getExecutionStatus(result);
                          switch (status) {
                            case 'running':
                              return (
                                <Chip
                                  icon={<RunningIcon />}
                                  label="RUNNING"
                                  color="warning"
                                  size="small"
                                />
                              );
                            case 'passed':
                              return (
                                <Chip
                                  icon={<PassIcon />}
                                  label="PASS"
                                  color="success"
                                  size="small"
                                />
                              );
                            case 'failed':
                              return (
                                <Chip
                                  icon={<FailIcon />}
                                  label="FAIL"
                                  color="error"
                                  size="small"
                                />
                              );
                            default:
                              return (
                                <Chip
                                  icon={<UnknownIcon />}
                                  label="UNKNOWN"
                                  color="default"
                                  size="small"
                                />
                              );
                          }
                        })()}
                      </TableCell>
                      <TableCell sx={{ py: 0.5 }}>
                        {result.execution_time_ms
                          ? formatDuration(result.execution_time_ms)
                          : 'N/A'}
                      </TableCell>
                      <TableCell sx={{ py: 0.5 }}>{formatDate(result.started_at)}</TableCell>
                      <TableCell sx={{ py: 0.5 }}>
                        {result.html_report_r2_url ? (
                          <Chip
                            icon={<LinkIcon />}
                            label="Report"
                            size="small"
                            clickable
                            onClick={() => window.open(result.html_report_r2_url!, '_blank')}
                            color="primary"
                            variant="outlined"
                          />
                        ) : (
                          <Chip label="No Report" size="small" variant="outlined" disabled />
                        )}
                      </TableCell>
                      <TableCell sx={{ py: 0.5 }}>
                        {result.html_report_r2_url ? (
                          <Chip
                            icon={<LinkIcon />}
                            label="Logs"
                            size="small"
                            clickable
                            onClick={() => window.open(getLogsUrl(result.html_report_r2_url!), '_blank')}
                            color="secondary"
                            variant="outlined"
                          />
                        ) : (
                          <Chip label="No Logs" size="small" variant="outlined" disabled />
                        )}
                      </TableCell>
                      {showDetailedColumns && (
                        <>
                          <TableCell sx={{ py: 0.5 }}>
                            {getCheckedStatus(result)}
                          </TableCell>
                          <TableCell sx={{ py: 0.5 }}>
                            {getDiscardStatus(result)}
                          </TableCell>
                          <TableCell sx={{ py: 0.5 }}>
                            {getCheckType(result)}
                          </TableCell>
                          <TableCell sx={{ py: 0.5 }}>
                            {getDiscardComment(result)}
                          </TableCell>
                        </>
                      )}
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>

      {/* Discard Comment Modal */}
      <Dialog 
        open={discardModalOpen} 
        onClose={handleCloseDiscardModal}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <CommentIcon />
            AI Analysis Comment
          </Box>
        </DialogTitle>
        <DialogContent>
          {selectedDiscardComment && (
            <Box>
              <Typography variant="subtitle2" sx={{ mb: 1, color: 'text.secondary' }}>
                Script: {selectedDiscardComment.result.script_name}
              </Typography>
              <Typography variant="subtitle2" sx={{ mb: 2, color: 'text.secondary' }}>
                Analysis Type: {selectedDiscardComment.result.check_type === 'ai' ? 'AI Analysis' : 'Manual Review'}
                {selectedDiscardComment.result.discard_type && ` • Category: ${selectedDiscardComment.result.discard_type}`}
              </Typography>
              <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>
                {selectedDiscardComment.comment}
              </Typography>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDiscardModal} color="primary">
            Close
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default TestReports;
