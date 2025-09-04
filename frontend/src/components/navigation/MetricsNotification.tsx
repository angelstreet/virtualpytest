/**
 * Minimalist Metrics Notification Component
 * Small toast at bottom right - click to view details
 */

import React from 'react';
import { Snackbar, Alert, Box, IconButton, Tooltip } from '@mui/material';
import { Warning, Error, Close } from '@mui/icons-material';

import { MetricsNotificationData } from '../../types/navigation/Metrics_Types';

export interface MetricsNotificationProps {
  notificationData: MetricsNotificationData;
  onViewDetails: () => void;
  onClose?: () => void;
  onSkip?: () => void; // New: Skip this notification until next refresh
  autoHideDuration?: number;
}

export const MetricsNotification: React.FC<MetricsNotificationProps> = ({
  notificationData,
  onViewDetails,
  onClose,
  onSkip,
  autoHideDuration = 6000, // 6 seconds
}) => {
  if (!notificationData.show) {
    return null;
  }

  const handleClick = (event: React.MouseEvent) => {
    // Prevent event bubbling to avoid closing when clicking the skip button
    if ((event.target as HTMLElement).closest('.skip-button')) {
      return;
    }
    
    // Hide toast immediately when opening modal
    onClose?.();
    // Then open modal
    onViewDetails();
  };

  const handleClose = (_event?: React.SyntheticEvent | Event, reason?: string) => {
    if (reason === 'clickaway') {
      return;
    }
    onClose?.();
  };

  const handleSkip = (event: React.MouseEvent) => {
    event.stopPropagation(); // Prevent triggering the main click handler
    onSkip?.();
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
    const confidenceScore = Math.round(notificationData.global_confidence * 10);
    const successRate = notificationData.global_success_rate 
      ? (notificationData.global_success_rate * 100).toFixed(0)
      : '0';
    const count = notificationData.low_confidence_count;
    
    // Emphasize confidence score (larger, first) then success rate
    if (notificationData.severity === 'error') {
      return `Score: ${confidenceScore}/10 • ${successRate}% success • ${count} items`;
    } else {
      return `Score: ${confidenceScore}/10 • ${successRate}% success • ${count} items`;
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
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flex: 1 }}>
            {/* Confidence Score - Emphasized */}
            <Box sx={{ 
              fontSize: '1rem', 
              fontWeight: 'bold',
              color: notificationData.severity === 'error' ? '#ef4444' : '#f59e0b',
              padding: '2px 6px',
              borderRadius: '4px',
              backgroundColor: 'rgba(255,255,255,0.2)',
              border: '1px solid rgba(255,255,255,0.3)'
            }}>
              {Math.round(notificationData.global_confidence * 10)}/10
            </Box>
            
            {/* Success Rate and Count - Secondary */}
            <Box sx={{ fontSize: '0.75rem', fontWeight: 400, opacity: 0.9 }}>
              {notificationData.global_success_rate 
                ? `${(notificationData.global_success_rate * 100).toFixed(0)}% success`
                : '0% success'
              } • {notificationData.low_confidence_count} items
            </Box>
          </Box>
          
          {/* Skip button */}
          {onSkip && (
            <Tooltip title="Skip until next refresh" placement="top">
              <IconButton
                className="skip-button"
                size="small"
                onClick={handleSkip}
                sx={{
                  padding: '2px',
                  marginLeft: '8px',
                  opacity: 0.7,
                  '&:hover': {
                    opacity: 1,
                    backgroundColor: 'rgba(255, 255, 255, 0.1)',
                  },
                }}
              >
                <Close fontSize="small" />
              </IconButton>
            </Tooltip>
          )}
        </Box>
      </Alert>
    </Snackbar>
  );
};
