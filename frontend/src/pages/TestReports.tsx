import {
  Assessment as ReportsIcon,
  CheckCircle as PassIcon,
  Error as FailIcon,
  Link as LinkIcon,
  SmartToy as AiIcon,
  Person as ManualIcon,
  Help as UnknownIcon,
  Comment as CommentIcon,
  Check as ValidIcon,
  Warning as DiscardedIcon,
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

  // Get AI analysis status display
  const getAIAnalysisDisplay = (result: ScriptResult) => {
    if (!result.checked) {
      return (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Chip
            icon={<UnknownIcon />}
            label="Pending"
            color="default"
            size="small"
            variant="outlined"
          />
        </Box>
      );
    }

    const isAI = result.check_type === 'ai';
    const isDiscarded = result.discard;
    
    return (
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        {/* Check type indicator */}
        <Chip
          icon={isAI ? <AiIcon /> : <ManualIcon />}
          label={isAI ? 'AI' : 'Manual'}
          color="primary"
          size="small"
          variant="outlined"
        />
        
        {/* Discard status */}
        {isDiscarded ? (
          <Chip
            icon={<DiscardedIcon />}
            label={result.discard_type || 'Discarded'}
            color="warning"
            size="small"
          />
        ) : (
          <Chip
            icon={<ValidIcon />}
            label="Valid"
            color="success"
            size="small"
          />
        )}
        
        {/* Comment icon if available */}
        {result.discard_comment && (
          <Tooltip title="View AI analysis comment">
            <IconButton
              size="small"
              onClick={() => handleDiscardCommentClick(result)}
              sx={{ p: 0.25 }}
            >
              <CommentIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        )}
      </Box>
    );
  };

  // Loading state component
  const LoadingState = () => (
    <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
      <CircularProgress />
    </Box>
  );

  // Empty state component
  const EmptyState = () => (
    <TableRow>
      <TableCell colSpan={10} sx={{ textAlign: 'center', py: 4 }}>
        <Typography variant="body2" color="textSecondary">
          No script results available yet
        </Typography>
      </TableCell>
    </TableRow>
  );

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
          <Typography variant="h6" sx={{ mb: 2 }}>
            Recent Test Reports
          </Typography>

          <TableContainer component={Paper} variant="outlined">
            <Table size="small" sx={{ '& .MuiTableRow-root': { height: '40px' } }}>
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
                  <TableCell sx={{ py: 1 }}>
                    <strong>AI Analysis</strong>
                  </TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {loading ? (
                  <TableRow>
                    <TableCell colSpan={10}>
                      <LoadingState />
                    </TableCell>
                  </TableRow>
                ) : scriptResults.length === 0 ? (
                  <EmptyState />
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
                        <Chip
                          icon={result.success ? <PassIcon /> : <FailIcon />}
                          label={result.success ? 'PASS' : 'FAIL'}
                          color={result.success ? 'success' : 'error'}
                          size="small"
                        />
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
                        {result.logs_r2_url ? (
                          <Chip
                            icon={<LinkIcon />}
                            label="Logs"
                            size="small"
                            clickable
                            onClick={() => window.open(result.logs_r2_url!, '_blank')}
                            color="secondary"
                            variant="outlined"
                          />
                        ) : (
                          <Chip label="No Logs" size="small" variant="outlined" disabled />
                        )}
                      </TableCell>
                      <TableCell sx={{ py: 0.5 }}>
                        {getAIAnalysisDisplay(result)}
                      </TableCell>
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
