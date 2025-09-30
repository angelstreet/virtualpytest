'use client';

import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  Chip,
} from '@mui/material';
import React from 'react';

interface ValidationResultsClientProps {
  open: boolean;
  onClose: () => void;
  success: boolean;
  duration: number; // in seconds
  reportUrl?: string;
}

const formatDuration = (seconds: number): string => {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
};

export const ValidationResultsClient: React.FC<ValidationResultsClientProps> = ({
  open,
  onClose,
  success,
  duration,
  reportUrl,
}) => {
  return (
    <Dialog open={open} onClose={onClose} maxWidth="xs" fullWidth>
      <DialogTitle>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Typography variant="h6">Validation Complete</Typography>
          <Chip
            label={success ? 'Success' : 'Failed'}
            color={success ? 'success' : 'error'}
            size="small"
          />
        </Box>
      </DialogTitle>

      <DialogContent>
        <Box sx={{ py: 1 }}>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            Duration: <strong>{formatDuration(duration)}</strong>
          </Typography>
          
          {reportUrl && (
            <Box sx={{ mt: 2 }}>
              <Button
                variant="outlined"
                color="primary"
                fullWidth
                onClick={() => window.open(reportUrl, '_blank')}
              >
                View Detailed Report ↗
              </Button>
            </Box>
          )}
        </Box>
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose} variant="contained">
          Close
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default ValidationResultsClient;
