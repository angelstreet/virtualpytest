import {
  KeyboardArrowDown as ExpandMoreIcon,
  KeyboardArrowRight as ExpandLessIcon,
  Error as IncidentIcon,
  Assessment as ScriptIcon,
  Clear as ClearIcon,
  DeleteSweep as ClearAllIcon,
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
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
} from '@mui/material';
import React, { useState, useEffect } from 'react';

import { useAIQueue, AIQueueStatus } from '../hooks/pages/useAIQueue';

const AIQueueMonitor: React.FC = () => {
  const { getQueueStatus, clearQueues } = useAIQueue();
  const [queueStatus, setQueueStatus] = useState<AIQueueStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set());
  const [clearDialog, setClearDialog] = useState<{
    open: boolean;
    queueType: 'incidents' | 'scripts' | 'all';
    queueName: string;
  }>({ open: false, queueType: 'all', queueName: '' });

  const fetchStatus = async (includeItems: boolean = false) => {
    try {
      setError(null);
      const status = await getQueueStatus(includeItems);
      setQueueStatus(status);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch queue status');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 5000); // Refresh every 5s
    return () => clearInterval(interval);
  }, [getQueueStatus]);

  const toggleSection = async (section: string) => {
    const isCurrentlyExpanded = expandedSections.has(section);
    
    setExpandedSections(prev => {
      const newSet = new Set(prev);
      if (newSet.has(section)) {
        newSet.delete(section);
      } else {
        newSet.add(section);
      }
      return newSet;
    });

    // If expanding and we don't have items yet, fetch them
    if (!isCurrentlyExpanded && queueStatus && 
        (!queueStatus.queues[section as keyof typeof queueStatus.queues]?.items || 
         queueStatus.queues[section as keyof typeof queueStatus.queues]?.items?.length === 0)) {
      await fetchStatus(true);
    }
  };

  const handleClearQueue = (queueType: 'incidents' | 'scripts' | 'all', queueName: string) => {
    setClearDialog({ open: true, queueType, queueName });
  };

  const confirmClearQueue = async () => {
    try {
      await clearQueues(clearDialog.queueType);
      setClearDialog({ open: false, queueType: 'all', queueName: '' });
      // Refresh queue status
      fetchStatus();
    } catch (error) {
      console.error('Failed to clear queue:', error);
    }
  };

  const cancelClearQueue = () => {
    setClearDialog({ open: false, queueType: 'all', queueName: '' });
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
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
        <Typography variant="h5">
          AI Queue Monitor
        </Typography>
        {queueStatus && (
          <Button
            variant="outlined"
            color="error"
            size="small"
            startIcon={<ClearAllIcon />}
            onClick={() => handleClearQueue('all', 'All Queues')}
            disabled={queueStatus.queues.incidents.length === 0 && queueStatus.queues.scripts.length === 0}
          >
            Clear All
          </Button>
        )}
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 1 }} onClose={() => setError(null)}>
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
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <IconButton
                      size="small"
                      onClick={() => handleClearQueue('incidents', 'Incidents')}
                      disabled={queueStatus.queues.incidents.length === 0}
                      title="Clear incidents queue"
                    >
                      <ClearIcon />
                    </IconButton>
                    <IconButton
                      size="small"
                      onClick={() => toggleSection('incidents')}
                    >
                      {expandedSections.has('incidents') ? <ExpandMoreIcon /> : <ExpandLessIcon />}
                    </IconButton>
                  </Box>
                </Box>

                <Collapse in={expandedSections.has('incidents')}>
                  <Box sx={{ mt: 1, p: 2, bgcolor: 'rgba(0,0,0,0.02)', borderRadius: 1 }}>
                    {queueStatus.queues.incidents.items && queueStatus.queues.incidents.items.length > 0 ? (
                      <Box>
                        <Typography variant="body2" sx={{ mb: 1, fontWeight: 'bold' }}>
                          Last {Math.min(50, queueStatus.queues.incidents.items.length)} pending items:
                        </Typography>
                        <Box sx={{ maxHeight: 200, overflowY: 'auto' }}>
                          {queueStatus.queues.incidents.items.slice(0, 50).map((item, index) => (
                            <Box key={index} sx={{ mb: 1, p: 1, bgcolor: 'white', borderRadius: 0.5, fontSize: '0.75rem' }}>
                              <Typography variant="caption" sx={{ fontWeight: 'bold' }}>
                                ID: {item.id}
                              </Typography>
                              <Typography variant="caption" sx={{ ml: 2, color: 'text.secondary' }}>
                                {new Date(item.created_at).toLocaleString()}
                              </Typography>
                            </Box>
                          ))}
                        </Box>
                      </Box>
                    ) : (
                      <Typography variant="body2" color="text.secondary">
                        {queueStatus.queues.incidents.length === 0 ? 'No items in queue' : 'Loading items...'}
                      </Typography>
                    )}
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
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <IconButton
                      size="small"
                      onClick={() => handleClearQueue('scripts', 'Scripts')}
                      disabled={queueStatus.queues.scripts.length === 0}
                      title="Clear scripts queue"
                    >
                      <ClearIcon />
                    </IconButton>
                    <IconButton
                      size="small"
                      onClick={() => toggleSection('scripts')}
                    >
                      {expandedSections.has('scripts') ? <ExpandMoreIcon /> : <ExpandLessIcon />}
                    </IconButton>
                  </Box>
                </Box>

                <Collapse in={expandedSections.has('scripts')}>
                  <Box sx={{ mt: 1, p: 2, bgcolor: 'rgba(0,0,0,0.02)', borderRadius: 1 }}>
                    {queueStatus.queues.scripts.items && queueStatus.queues.scripts.items.length > 0 ? (
                      <Box>
                        <Typography variant="body2" sx={{ mb: 1, fontWeight: 'bold' }}>
                          Last {Math.min(50, queueStatus.queues.scripts.items.length)} pending items:
                        </Typography>
                        <Box sx={{ maxHeight: 200, overflowY: 'auto' }}>
                          {queueStatus.queues.scripts.items.slice(0, 50).map((item, index) => (
                            <Box key={index} sx={{ mb: 1, p: 1, bgcolor: 'white', borderRadius: 0.5, fontSize: '0.75rem' }}>
                              <Typography variant="caption" sx={{ fontWeight: 'bold' }}>
                                ID: {item.id}
                              </Typography>
                              <Typography variant="caption" sx={{ ml: 2, color: 'text.secondary' }}>
                                {new Date(item.created_at).toLocaleString()}
                              </Typography>
                            </Box>
                          ))}
                        </Box>
                      </Box>
                    ) : (
                      <Typography variant="body2" color="text.secondary">
                        {queueStatus.queues.scripts.length === 0 ? 'No items in queue' : 'Loading items...'}
                      </Typography>
                    )}
                  </Box>
                </Collapse>
              </CardContent>
            </Card>
          </Grid>

        </Grid>
      )}

      {/* Clear Queue Confirmation Dialog */}
      <Dialog
        open={clearDialog.open}
        onClose={cancelClearQueue}
        aria-labelledby="clear-queue-dialog-title"
        aria-describedby="clear-queue-dialog-description"
      >
        <DialogTitle id="clear-queue-dialog-title">
          Clear {clearDialog.queueName}?
        </DialogTitle>
        <DialogContent>
          <DialogContentText id="clear-queue-dialog-description">
            Are you sure you want to clear the {clearDialog.queueName.toLowerCase()}? 
            This will permanently remove all pending tasks from the queue and cannot be undone.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={cancelClearQueue} color="primary">
            Cancel
          </Button>
          <Button onClick={confirmClearQueue} color="error" variant="contained">
            Clear Queue
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default AIQueueMonitor;
