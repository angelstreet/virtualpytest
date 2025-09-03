/**
 * Minimalist Metrics Notification Component
 * Small toast at bottom right - click to view details
 */

import React from 'react';
import { Snackbar, Alert, Box } from '@mui/material';
import { Warning, Error } from '@mui/icons-material';

import { MetricsNotificationData } from '../../types/navigation/Metrics_Types';

export interface MetricsNotificationProps {
  notificationData: MetricsNotificationData;
  onViewDetails: () => void;
  onClose?: () => void;
  autoHideDuration?: number;
}

export const MetricsNotification: React.FC<MetricsNotificationProps> = ({
  notificationData,
  onViewDetails,
  onClose,
  autoHideDuration = 6000, // 6 seconds
}) => {
  if (!notificationData.show) {
    return null;
  }

  const handleClick = () => {
    onViewDetails();
  };

  const handleClose = (_event?: React.SyntheticEvent | Event, reason?: string) => {
    if (reason === 'clickaway') {
      return;
    }
    onClose?.();
  };

  const getIcon = () => {
    switch (notificationData.severity) {
      case 'error':
        return <Error fontSize="small" />;
      case 'warning':
        return <Warning fontSize="small" />;
      default:
        return null;
    }
  };

  const getShortMessage = () => {
    const confidence = (notificationData.global_confidence * 100).toFixed(0);
    const count = notificationData.low_confidence_count;
    
    if (notificationData.severity === 'error') {
      return `Low confidence ${confidence}% • ${count} items`;
    } else {
      return `Medium confidence ${confidence}% • ${count} items`;
    }
  };

  return (
    <Snackbar
      open={notificationData.show}
      autoHideDuration={autoHideDuration}
      onClose={handleClose}
      anchorOrigin={{ 
        vertical: 'bottom', 
        horizontal: 'right' 
      }}
      sx={{
        marginBottom: '20px',
        marginRight: '20px',
        zIndex: 1400,
      }}
    >
      <Alert
        severity={notificationData.severity}
        onClick={handleClick}
        onClose={onClose ? handleClose : undefined}
        icon={getIcon()}
        sx={{
          cursor: 'pointer',
          minWidth: '200px',
          maxWidth: '280px',
          fontSize: '0.8rem',
          padding: '4px 12px',
          '& .MuiAlert-message': {
            padding: '4px 0',
            fontSize: '0.8rem',
          },
          '& .MuiAlert-icon': {
            padding: '4px 0',
            marginRight: '8px',
          },
          '& .MuiAlert-action': {
            padding: '0',
            marginRight: '0',
          },
          '&:hover': {
            transform: 'scale(1.02)',
            boxShadow: (theme) => theme.shadows[4],
          },
          transition: 'all 0.2s ease-in-out',
          borderRadius: '8px',
        }}
      >
        <Box sx={{ 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'space-between',
          width: '100%'
        }}>
          <Box sx={{ fontSize: '0.8rem', fontWeight: 500 }}>
            {getShortMessage()}
          </Box>
        </Box>
      </Alert>
    </Snackbar>
  );
};
