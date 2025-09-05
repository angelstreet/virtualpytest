import {
  Campaign as CampaignIcon,
  CheckCircle as PassIcon,
  Error as FailIcon,
  Link as LinkIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  PlayArrow as ScriptIcon,
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
  Checkbox,
  IconButton,
} from '@mui/material';
import React, { useState, useEffect } from 'react';

import { useCampaignResults, CampaignResult } from '../hooks/pages/useCampaignResults';

const CampaignReports: React.FC = () => {
  const { getAllCampaignResults } = useCampaignResults();
  const [campaignResults, setCampaignResults] = useState<CampaignResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());

  // Load campaign results on component mount
  useEffect(() => {
    const loadCampaignResults = async () => {
      try {
        setLoading(true);
        setError(null);
        const results = await getAllCampaignResults();
        setCampaignResults(results);
      } catch (err) {
        console.error('[@component:CampaignReports] Error loading campaign results:', err);
        setError(err instanceof Error ? err.message : 'Failed to load campaign results');
      } finally {
        setLoading(false);
      }
    };

    loadCampaignResults();
  }, [getAllCampaignResults]);

  // Calculate stats
  const totalReports = campaignResults.length;
  const passedReports = campaignResults.filter((result) => result.success).length;
  const successRate = totalReports > 0 ? ((passedReports / totalReports) * 100).toFixed(1) : 'N/A';

  // Calculate this week's reports (last 7 days)
  const oneWeekAgo = new Date();
  oneWeekAgo.setDate(oneWeekAgo.getDate() - 7);
  const thisWeekReports = campaignResults.filter(
    (result) => new Date(result.created_at) >= oneWeekAgo,
  ).length;

  // Calculate average duration
  const validDurations = campaignResults.filter((result) => result.execution_time_ms !== null);
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

  // Handle row expansion
  const handleRowExpand = (campaignId: string) => {
    const newExpandedRows = new Set(expandedRows);
    
    if (expandedRows.has(campaignId)) {
      // Collapse row
      newExpandedRows.delete(campaignId);
    } else {
      // Expand row - script results are already included in campaign data
      newExpandedRows.add(campaignId);
    }
    
    setExpandedRows(newExpandedRows);
  };

  // Handle discard toggle
  const handleDiscardToggle = async (resultId: string, discardValue: boolean) => {
    try {
      // TODO: Implement API call to update discard status
      console.log(`Toggling discard for campaign result ${resultId} to ${discardValue}`);

      // Update local state immediately for better UX
      setCampaignResults((prev) =>
        prev.map((result) =>
          result.id === resultId ? { ...result, discard: discardValue } : result,
        ),
      );
    } catch (error) {
      console.error('Error toggling discard status:', error);
      setError('Failed to update discard status');
    }
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
          No campaign results available yet
        </Typography>
      </TableCell>
    </TableRow>
  );

  return (
    <Box>
      <Box sx={{ mb: 0.5 }}>
        <Typography variant="h4" sx={{ mb: 1 }}>
          Campaign Reports
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
                <CampaignIcon color="primary" />
                <Typography variant="h6" sx={{ my: 0 }}>Quick Stats</Typography>
              </Box>

              <Box display="flex" alignItems="center" gap={2}>
                <Box display="flex" alignItems="center" gap={1}>
                  <Typography variant="body2">Total Campaigns</Typography>
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

      {/* Recent Campaign Reports */}
      <Card>
        <CardContent>

          <TableContainer component={Paper} variant="outlined">
            <Table size="small" sx={{ '& .MuiTableRow-root': { height: '40px' } }}>
              <TableHead>
                <TableRow>
                  <TableCell sx={{ py: 1, width: '40px' }}>
                    {/* Expand column */}
                  </TableCell>
                  <TableCell sx={{ py: 1 }}>
                    <strong>Campaign Name</strong>
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
                    <strong>Discard</strong>
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
                ) : campaignResults.length === 0 ? (
                  <EmptyState />
                ) : (
                  campaignResults.map((result) => (
                    <React.Fragment key={result.id}>
                      {/* Main campaign row */}
                      <TableRow
                        sx={{
                          '&:hover': {
                            backgroundColor: 'rgba(0, 0, 0, 0.04) !important',
                          },
                          opacity: result.discard ? 0.5 : 1,
                        }}
                      >
                        <TableCell sx={{ py: 0.5 }}>
                          <IconButton
                            size="small"
                            onClick={() => handleRowExpand(result.id)}
                            disabled={false}
                          >
                            {expandedRows.has(result.id) ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                          </IconButton>
                        </TableCell>
                        <TableCell sx={{ py: 0.5 }}>{result.campaign_name}</TableCell>
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
                              label="View Report"
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
                          <Checkbox
                            size="small"
                            checked={result.discard || false}
                            onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                              handleDiscardToggle(result.id, e.target.checked)
                            }
                            title={result.discard ? 'Discarded' : 'Not discarded'}
                          />
                        </TableCell>
                      </TableRow>

                      {/* Expandable rows for script results - align with main table columns */}
                      {expandedRows.has(result.id) && (
                        <>
                          {result.script_results && result.script_results.length > 0 ? (
                            result.script_results.map((script) => (
                              <TableRow 
                                key={script.id}
                                sx={{
                                  backgroundColor: 'rgba(0, 0, 0, 0.02)',
                                  '&:hover': {
                                    backgroundColor: 'rgba(0, 0, 0, 0.06) !important',
                                  },
                                }}
                              >
                                <TableCell sx={{ py: 0.5, pl: 4 }}>
                                  <ScriptIcon fontSize="small" />
                                </TableCell>
                                <TableCell sx={{ py: 0.5 }}>{script.script_name}</TableCell>
                                <TableCell sx={{ py: 0.5 }}>-</TableCell>
                                <TableCell sx={{ py: 0.5 }}>-</TableCell>
                                <TableCell sx={{ py: 0.5 }}>-</TableCell>
                                <TableCell sx={{ py: 0.5 }}>
                                  <Chip
                                    icon={script.success ? <PassIcon /> : <FailIcon />}
                                    label={script.success ? 'PASS' : 'FAIL'}
                                    color={script.success ? 'success' : 'error'}
                                    size="small"
                                  />
                                </TableCell>
                                <TableCell sx={{ py: 0.5 }}>
                                  {script.execution_time_ms
                                    ? formatDuration(script.execution_time_ms)
                                    : 'N/A'}
                                </TableCell>
                                <TableCell sx={{ py: 0.5 }}>-</TableCell>
                                <TableCell sx={{ py: 0.5 }}>
                                  {script.html_report_r2_url ? (
                                    <Chip
                                      icon={<LinkIcon />}
                                      label="View Report"
                                      size="small"
                                      clickable
                                      onClick={() => window.open(script.html_report_r2_url!, '_blank')}
                                      color="primary"
                                      variant="outlined"
                                    />
                                  ) : (
                                    <Chip label="No Report" size="small" variant="outlined" disabled />
                                  )}
                                </TableCell>
                                <TableCell sx={{ py: 0.5 }}>-</TableCell>
                              </TableRow>
                            ))
                          ) : (
                            <TableRow
                              sx={{
                                backgroundColor: 'rgba(255, 193, 7, 0.1)',
                              }}
                            >
                              <TableCell sx={{ py: 1, pl: 4 }}>
                                <ScriptIcon fontSize="small" color="warning" />
                              </TableCell>
                              <TableCell colSpan={9} sx={{ py: 1, fontStyle: 'italic', color: 'text.secondary' }}>
                                No script results linked to this campaign (backend linking issue)
                              </TableCell>
                            </TableRow>
                          )}
                        </>
                      )}
                    </React.Fragment>
                  ))
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>
    </Box>
  );
};

export default CampaignReports;