/**
 * Metrics Notification Component
 * Toast notification for confidence warnings with click-to-view-details
 */

import React from 'react';
import { Snackbar, Alert, AlertTitle, Box, Chip } from '@mui/material';
import { Warning, Error, Info } from '@mui/icons-material';

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
  autoHideDuration = 8000, // 8 seconds for important metrics info
}) => {
  if (!notificationData.show) {
    return null;
  }

  const handleClick = () => {
    onViewDetails();
  };

  const handleClose = (_event?: React.SyntheticEvent | Event, reason?: string) => {
    // Don't auto-close on clickaway for important metrics notifications
    if (reason === 'clickaway') {
      return;
    }
    onClose?.();
  };

  const getIcon = () => {
    switch (notificationData.severity) {
      case 'error':
        return <Error />;
      case 'warning':
        return <Warning />;
      default:
        return <Info />;
    }
  };

  const getAlertTitle = () => {
    switch (notificationData.severity) {
      case 'error':
        return 'Navigation Confidence Alert';
      case 'warning':
        return 'Navigation Confidence Warning';
      default:
        return 'Navigation Metrics';
    }
  };

  return (
    <Snackbar
      open={notificationData.show}
      autoHideDuration={autoHideDuration}
      onClose={handleClose}
      anchorOrigin={{ 
        vertical: 'top', 
        horizontal: 'right' 
      }}
      sx={{
        marginTop: '80px', // Below navigation header
        zIndex: 1400, // Above most UI elements but below modals
      }}
    >
      <Alert
        severity={notificationData.severity}
        onClick={handleClick}
        onClose={onClose ? handleClose : undefined}
        icon={getIcon()}
        sx={{
          cursor: 'pointer',
          minWidth: '320px',
          maxWidth: '480px',
          '&:hover': {
            backgroundColor: (theme) => 
              notificationData.severity === 'error' 
                ? theme.palette.error.light
                : notificationData.severity === 'warning'
                ? theme.palette.warning.light
                : theme.palette.info.light,
            opacity: 0.9,
          },
          transition: 'all 0.2s ease-in-out',
        }}
      >
        <AlertTitle sx={{ fontWeight: 'bold', marginBottom: 1 }}>
          {getAlertTitle()}
        </AlertTitle>
        
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
          {/* Main message */}
          <Box sx={{ fontSize: '0.875rem' }}>
            {notificationData.message}
          </Box>
          
          {/* Metrics chips */}
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            <Chip
              size="small"
              label={`Global: ${(notificationData.global_confidence * 100).toFixed(1)}%`}
              color={notificationData.severity === 'error' ? 'error' : 'warning'}
              variant="outlined"
            />
            
            {notificationData.low_confidence_count > 0 && (
              <Chip
                size="small"
                label={`${notificationData.low_confidence_count} items need attention`}
                color="default"
                variant="outlined"
              />
            )}
          </Box>
          
          {/* Click hint */}
          <Box 
            sx={{ 
              fontSize: '0.75rem', 
              fontStyle: 'italic',
              opacity: 0.8,
              marginTop: 0.5,
            }}
          >
            Click to view detailed metrics
          </Box>
        </Box>
      </Alert>
    </Snackbar>
  );
};
