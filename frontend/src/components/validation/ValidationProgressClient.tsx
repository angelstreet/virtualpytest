'use client';

import {
  Dialog,
  DialogTitle,
  DialogContent,
  Typography,
  Box,
  CircularProgress,
  Chip,
} from '@mui/material';
import React, { useEffect } from 'react';

import { useValidation } from '../../hooks/validation';

interface ValidationProgressClientProps {
  treeId: string;
  selectedHost?: any;
  selectedDeviceId?: string | null;
}

export const ValidationProgressClient: React.FC<ValidationProgressClientProps> = ({
  treeId,
  selectedHost,
  selectedDeviceId,
}) => {
  const validation = useValidation(treeId, selectedHost, selectedDeviceId);

  // Only show progress dialog when validation is running
  if (!validation.isValidating) {
    return null;
  }

  return (
    <Dialog open={validation.isValidating} disableEscapeKeyDown maxWidth="sm" fullWidth>
      <DialogTitle>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Typography variant="h6">Running Validation</Typography>
          <Chip
            label="In Progress"
            color="primary"
            size="small"
            variant="outlined"
          />
        </Box>
      </DialogTitle>

      <DialogContent>
        <Box sx={{ py: 2 }}>
          {/* Simple loading display - no complex progress tracking */}
          <Box
            sx={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: 2,
              p: 2,
              borderRadius: 1,
              border: '1px solid',
              borderColor: 'grey.200',
            }}
          >
            <CircularProgress size={40} />
            <Typography variant="body1" color="text.primary" textAlign="center">
              Validation is running...
            </Typography>
            <Typography variant="body2" color="text.secondary" textAlign="center">
              Please wait while the validation executes. This may take several minutes.
              The system is capturing screenshots and generating a detailed report.
            </Typography>
          </Box>
        </Box>
      </DialogContent>
    </Dialog>
  );
};

export default ValidationProgressClient;