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
  Visibility as DetailsIcon,
  VisibilityOff as HideDetailsIcon,
  CheckCircle as CheckedIcon,
  OpenInNew,
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
  CircularProgress,
  Alert,
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
import { formatToLocalTime } from '../utils/dateUtils';
import { getR2Url, extractR2Path, isCloudflareR2Url } from '../utils/infrastructure/cloudflareUtils';
import { StyledDialog } from '../components/common/StyledDialog';

const TestReports: React.FC = () => {
  // Get Grafana URL from environment variable
  const grafanaUrl = (import.meta as any).env?.VITE_GRAFANA_URL || 'http://localhost/grafana';
  
  const { getAllScriptResults, updateCheckedStatus, updateDiscardStatus } = useScriptResults();
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
  }, []); // Only run on component mount

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
    return formatToLocalTime(dateString);
  }

  // Convert report URL to logs URL helper
  function getLogsUrl(reportUrl: string): string {
    return reportUrl.replace('script-reports', 'script-logs').replace('report.html', 'execution.txt');
  }

  // Open R2 URL with automatic signed URL generation (handles both public and private modes)
  const handleOpenR2Url = async (url: string) => {
    try {
      // Extract path from full URL if needed (database stores full public URLs)
      let path = url;
      if (isCloudflareR2Url(url)) {
        const extracted = extractR2Path(url);
        if (extracted) {
          path = extracted;
        }
      }
      
      // getR2Url handles both public and private modes automatically
      const signedUrl = await getR2Url(path);
      window.open(signedUrl, '_blank');
    } catch (error) {
      console.error('[@TestReports] Failed to open R2 URL:', error);
      setError('Failed to open file. Please try again.');
    }
  };

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

  // Handle checked status toggle
  const handleCheckedToggle = async (result: ScriptResult) => {
    try {
      const newChecked = !result.checked;
      await updateCheckedStatus(result.id, newChecked);
      
      // Update local state
      setScriptResults(prev => 
        prev.map(r => r.id === result.id ? { ...r, checked: newChecked, check_type: 'manual' } : r)
      );
    } catch (error) {
      console.error('Failed to update checked status:', error);
      setError('Failed to update checked status');
    }
  };

  // Handle discard status toggle
  const handleDiscardToggle = async (result: ScriptResult) => {
    try {
      const newDiscard = !result.discard;
      const checkType = result.check_type === 'ai' ? 'ai_and_human' : 'manual';
      
      await updateDiscardStatus(result.id, newDiscard, undefined, checkType);
      
      // Update local state
      setScriptResults(prev => 
        prev.map(r => r.id === result.id ? { ...r, discard: newDiscard, check_type: checkType } : r)
      );
    } catch (error) {
      console.error('Failed to update discard status:', error);
      setError('Failed to update discard status');
    }
  };

  // Get individual discard analysis components
  const getCheckedStatus = (result: ScriptResult) => {
    if (result.checked === undefined || result.checked === null) {
      return (
        <Tooltip title="Mark as checked">
          <IconButton
            size="small"
            onClick={() => handleCheckedToggle(result)}
            sx={{ p: 0.5 }}
          >
            <UnknownIcon fontSize="small" color="disabled" />
          </IconButton>
        </Tooltip>
      );
    }
    return (
      <Tooltip title={result.checked ? 'Checked' : 'Not checked'}>
        <IconButton
          size="small"
          onClick={() => handleCheckedToggle(result)}
          sx={{ p: 0.5 }}
        >
          <CheckedIcon fontSize="small" color={result.checked ? 'success' : 'disabled'} />
        </IconButton>
      </Tooltip>
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
      <Tooltip title={result.discard ? 'Discarded (Invalid/False Positive)' : 'Valid (Legitimate Result)'}>
        <Typography
          variant="body2"
          onClick={() => handleDiscardToggle(result)}
          sx={{
            fontWeight: 'bold',
            color: result.discard ? 'error.main' : 'success.main',
            cursor: 'pointer',
            '&:hover': {
              opacity: 0.7,
            },
          }}
        >
          {result.discard ? 'YES' : 'NO'}
        </Typography>
      </Tooltip>
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
    const isAI = result.check_type === 'ai' || result.check_type === 'ai_agent' || result.check_type === 'ai_and_human';
    const isHuman = result.check_type === 'ai_and_human';
    return (
      <Tooltip title={isHuman ? 'AI & Human' : isAI ? 'AI Agent' : 'Manual'}>
        <Box sx={{ display: 'flex', gap: 0.5, alignItems: 'center' }}>
          {isAI && <AiIcon fontSize="small" color="primary" />}
          {(result.check_type === 'manual' || isHuman) && <ManualIcon fontSize="small" color="primary" />}
        </Box>
      </Tooltip>
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
      <Box sx={{ mb: 0.5 }}>
        <Typography variant="h4" sx={{ mb: 1 }}>
          Test Reports
        </Typography>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 1 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Quick Stats */}
      <Box sx={{ mb: 1 }}>
        <Card>
          <CardContent sx={{ py: 0.5 }}>
            <Box display="flex" alignItems="center" justifyContent="space-between">
              <Box display="flex" alignItems="center" gap={1}>
                <ReportsIcon color="primary" />
                <Typography variant="h6" sx={{ my: 0 }}>Quick Stats</Typography>
                <Tooltip title="Open Script Results Dashboard">
                  <IconButton
                    onClick={() => window.open(`${grafanaUrl}/d/2a3b060a-7820-4a6e-aa2a-adcbf5408bd3/script-results?orgId=1&from=now-30d&to=now&timezone=browser&var-user_interface=$__all&var-host=$__all&var-device_name=$__all&var-script_name=$__all`, '_blank')}
                    color="primary"
                    size="small"
                  >
                    <OpenInNew fontSize="small" />
                  </IconButton>
                </Tooltip>
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
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
            <Typography variant="h6" sx={{ my: 0 }}>
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
            <Table size="small" sx={{ 
              '& .MuiTableRow-root': { height: '40px' },
              '& .MuiTableCell-root': { 
                px: 1, 
                py: 0.5,
                fontSize: '0.875rem',
                whiteSpace: 'nowrap',
              }
            }}>
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
                        <strong>Analyzed By</strong>
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
                                <Tooltip title="Running">
                                  <RunningIcon color="warning" fontSize="small" />
                                </Tooltip>
                              );
                            case 'passed':
                              return (
                                <Tooltip title="Pass">
                                  <PassIcon color="success" fontSize="small" />
                                </Tooltip>
                              );
                            case 'failed':
                              return (
                                <Tooltip title="Fail">
                                  <FailIcon color="error" fontSize="small" />
                                </Tooltip>
                              );
                            default:
                              return (
                                <Tooltip title="Unknown">
                                  <UnknownIcon color="disabled" fontSize="small" />
                                </Tooltip>
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
                          <Tooltip title="Open Report">
                            <IconButton
                              size="small"
                              onClick={() => handleOpenR2Url(result.html_report_r2_url!)}
                              color="primary"
                              sx={{ p: 0.5 }}
                            >
                              <LinkIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        ) : (
                          <Typography variant="body2" color="text.disabled">-</Typography>
                        )}
                      </TableCell>
                      <TableCell sx={{ py: 0.5 }}>
                        {result.html_report_r2_url ? (
                          <Tooltip title="Open Logs">
                            <IconButton
                              size="small"
                              onClick={() => handleOpenR2Url(getLogsUrl(result.html_report_r2_url!))}
                              color="secondary"
                              sx={{ p: 0.5 }}
                            >
                              <LinkIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        ) : (
                          <Typography variant="body2" color="text.disabled">-</Typography>
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
      <StyledDialog 
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
                Analysis Type: {(selectedDiscardComment.result.check_type === 'ai' || selectedDiscardComment.result.check_type === 'ai_agent') ? 'AI Agent Analysis' : selectedDiscardComment.result.check_type === 'ai_and_human' ? 'AI & Human Review' : 'Manual Review'}
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
      </StyledDialog>
    </Box>
  );
};

export default TestReports;
