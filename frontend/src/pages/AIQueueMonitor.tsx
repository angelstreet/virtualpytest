import {
  KeyboardArrowDown as ExpandMoreIcon,
  KeyboardArrowRight as ExpandLessIcon,
  SmartToy as AIIcon,
  Error as IncidentIcon,
  Assessment as ScriptIcon,
} from '@mui/icons-material';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Alert,
  IconButton,
  Collapse,
  Grid,
} from '@mui/material';
import React, { useState, useEffect } from 'react';

import { useAIQueue, AIQueueStatus } from '../hooks/pages/useAIQueue';

const AIQueueMonitor: React.FC = () => {
  const { getQueueStatus } = useAIQueue();
  const [queueStatus, setQueueStatus] = useState<AIQueueStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set());

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        setError(null);
        const status = await getQueueStatus();
        setQueueStatus(status);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch queue status');
      } finally {
        setLoading(false);
      }
    };

    fetchStatus();
    const interval = setInterval(fetchStatus, 5000); // Refresh every 5s
    return () => clearInterval(interval);
  }, [getQueueStatus]);

  const toggleSection = (section: string) => {
    setExpandedSections(prev => {
      const newSet = new Set(prev);
      if (newSet.has(section)) {
        newSet.delete(section);
      } else {
        newSet.add(section);
      }
      return newSet;
    });
  };

  const getDiscardRate = (discarded: number, total: number) => {
    return total > 0 ? `${((discarded / total) * 100).toFixed(1)}%` : '0%';
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h4" sx={{ mb: 2 }}>
        AI Queue Monitor
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {queueStatus && (
        <Grid container spacing={2}>
          {/* Incidents Queue */}
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent sx={{ py: 1 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <IncidentIcon color="error" />
                    <Typography variant="h6" sx={{ my: 0 }}>
                      Incidents Queue
                    </Typography>
                    <Chip 
                      label={`${queueStatus.queues.incidents.length} pending`}
                      color={queueStatus.queues.incidents.length > 0 ? 'warning' : 'default'}
                      size="small"
                    />
                  </Box>
                  <IconButton
                    size="small"
                    onClick={() => toggleSection('incidents')}
                  >
                    {expandedSections.has('incidents') ? <ExpandMoreIcon /> : <ExpandLessIcon />}
                  </IconButton>
                </Box>

                <Collapse in={expandedSections.has('incidents')}>
                  <Box sx={{ mt: 2, p: 2, bgcolor: 'rgba(0,0,0,0.02)', borderRadius: 1 }}>
                    <Typography variant="body2" sx={{ mb: 1 }}>
                      <strong>Queue:</strong> {queueStatus.queues.incidents.name}
                    </Typography>
                    <Typography variant="body2" sx={{ mb: 1 }}>
                      <strong>Processed:</strong> {queueStatus.queues.incidents.processed}
                    </Typography>
                    <Typography variant="body2" sx={{ mb: 1 }}>
                      <strong>Discarded:</strong> {queueStatus.queues.incidents.discarded} 
                      ({getDiscardRate(queueStatus.queues.incidents.discarded, queueStatus.queues.incidents.processed)})
                    </Typography>
                    <Typography variant="body2">
                      <strong>Validated:</strong> {queueStatus.queues.incidents.validated}
                    </Typography>
                  </Box>
                </Collapse>
              </CardContent>
            </Card>
          </Grid>

          {/* Scripts Queue */}
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent sx={{ py: 1 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <ScriptIcon color="primary" />
                    <Typography variant="h6" sx={{ my: 0 }}>
                      Scripts Queue
                    </Typography>
                    <Chip 
                      label={`${queueStatus.queues.scripts.length} pending`}
                      color={queueStatus.queues.scripts.length > 0 ? 'warning' : 'default'}
                      size="small"
                    />
                  </Box>
                  <IconButton
                    size="small"
                    onClick={() => toggleSection('scripts')}
                  >
                    {expandedSections.has('scripts') ? <ExpandMoreIcon /> : <ExpandLessIcon />}
                  </IconButton>
                </Box>

                <Collapse in={expandedSections.has('scripts')}>
                  <Box sx={{ mt: 2, p: 2, bgcolor: 'rgba(0,0,0,0.02)', borderRadius: 1 }}>
                    <Typography variant="body2" sx={{ mb: 1 }}>
                      <strong>Queue:</strong> {queueStatus.queues.scripts.name}
                    </Typography>
                    <Typography variant="body2" sx={{ mb: 1 }}>
                      <strong>Processed:</strong> {queueStatus.queues.scripts.processed}
                    </Typography>
                    <Typography variant="body2" sx={{ mb: 1 }}>
                      <strong>Discarded:</strong> {queueStatus.queues.scripts.discarded} 
                      ({getDiscardRate(queueStatus.queues.scripts.discarded, queueStatus.queues.scripts.processed)})
                    </Typography>
                    <Typography variant="body2">
                      <strong>Validated:</strong> {queueStatus.queues.scripts.validated}
                    </Typography>
                  </Box>
                </Collapse>
              </CardContent>
            </Card>
          </Grid>

          {/* Service Status */}
          <Grid item xs={12}>
            <Card>
              <CardContent sx={{ py: 1 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                  <AIIcon color="success" />
                  <Typography variant="h6" sx={{ my: 0 }}>
                    AI Service Status
                  </Typography>
                  <Chip 
                    label={queueStatus.status}
                    color={queueStatus.status === 'healthy' ? 'success' : 'error'}
                    size="small"
                  />
                  <Typography variant="body2" color="text.secondary">
                    Total Processed: {queueStatus.stats.tasks_processed || 0}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    AI Success: {queueStatus.stats.ai_successes || 0}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    AI Failures: {queueStatus.stats.ai_failures || 0}
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}
    </Box>
  );
};

export default AIQueueMonitor;
