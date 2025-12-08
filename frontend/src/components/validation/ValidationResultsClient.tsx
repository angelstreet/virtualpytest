'use client';

import {
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  Chip,
} from '@mui/material';
import React from 'react';

import { StyledDialog } from '../common/StyledDialog';
import { extractR2Path, getR2Url, isCloudflareR2Url } from '../../utils/infrastructure/cloudflareUtils';

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
  const handleOpenReport = async () => {
    if (!reportUrl) return;

    try {
      const isHttpUrl = /^https?:\/\//i.test(reportUrl);

      // Non-R2 HTTP links can be opened directly
      if (isHttpUrl && !isCloudflareR2Url(reportUrl)) {
        window.open(reportUrl, '_blank');
        return;
      }

      // Normalize to R2 path for signing
      let path = reportUrl;
      if (isCloudflareR2Url(reportUrl)) {
        const extracted = extractR2Path(reportUrl);
        if (extracted) {
          path = extracted;
        }
      }

      const signedUrl = await getR2Url(path);
      window.open(signedUrl, '_blank');
    } catch (error) {
      console.error('[@ValidationResultsClient] Failed to open validation report:', error);
    }
  };

  return (
    <StyledDialog 
      open={open} 
      onClose={onClose} 
      maxWidth="xs" 
      fullWidth
    >
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
                onClick={handleOpenReport}
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
    </StyledDialog>
  );
};

export default ValidationResultsClient;
