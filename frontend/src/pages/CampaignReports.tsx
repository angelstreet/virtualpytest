import {
  Campaign as CampaignIcon,
} from '@mui/icons-material';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Paper,
  Alert,
} from '@mui/material';
import React, { useState, useEffect } from 'react';

// Reuse CampaignResultsList component
import { CampaignResultsList } from '../components/campaigns/CampaignResultsList';
import { useCampaignResults } from '../hooks/pages/useCampaignResults';

const CampaignReports: React.FC = () => {
  const { getAllCampaignResults } = useCampaignResults();
  const [campaignResults, setCampaignResults] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);

  // Load campaign results for stats calculation
  useEffect(() => {
    const loadCampaignResults = async () => {
      try {
        setError(null);
        const results = await getAllCampaignResults();
        setCampaignResults(results);
      } catch (err) {
        console.error('[@component:CampaignReports] Error loading campaign results:', err);
        setError(err instanceof Error ? err.message : 'Failed to load campaign results');
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

  // Handle discard toggle
  const handleDiscardToggle = async (resultId: string, discardValue: boolean) => {
    try {
      // TODO: Implement API call to update discard status
      console.log(`Toggling discard for campaign result ${resultId} to ${discardValue}`);
      
      // Update local state for stats
      setCampaignResults(prev => prev.map(r => 
        r.id === resultId ? { ...r, discard: discardValue } : r
      ));
    } catch (error) {
      console.error('Error toggling discard status:', error);
      setError('Failed to update discard status');
    }
  };

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
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

      {/* Reuse CampaignResultsList component */}
      <Paper sx={{ p: 2, flex: 1, display: 'flex', flexDirection: 'column' }}>
        <CampaignResultsList onDiscardToggle={handleDiscardToggle} />
      </Paper>
    </Box>
  );
};

export default CampaignReports;