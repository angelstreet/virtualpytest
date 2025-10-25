import React, { useEffect, useState } from 'react';
import { Box, Typography, CircularProgress, LinearProgress } from '@mui/material';
import { keyframes } from '@mui/system';

interface ExecutionOverlayProps {
  isExecuting: boolean;
  command?: string;
  params?: Record<string, any>;
}

const pulseAnimation = keyframes`
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.6;
  }
`;

export const ExecutionOverlay: React.FC<ExecutionOverlayProps> = ({
  isExecuting,
  command,
  params,
}) => {
  const [elapsedTime, setElapsedTime] = useState(0);

  useEffect(() => {
    if (!isExecuting) {
      setElapsedTime(0);
      return;
    }

    const startTime = Date.now();
    const interval = setInterval(() => {
      setElapsedTime((Date.now() - startTime) / 1000);
    }, 100);

    return () => clearInterval(interval);
  }, [isExecuting]);

  if (!isExecuting) return null;

  return (
    <Box
      sx={{
        position: 'absolute',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.6)',
        backdropFilter: 'blur(2px)',
        zIndex: 1000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        pointerEvents: 'all', // Block all interactions
        cursor: 'wait',
      }}
    >
      <Box
        sx={{
          backgroundColor: (theme) => theme.palette.mode === 'dark' ? '#1f2937' : '#ffffff',
          borderRadius: 3,
          padding: 4,
          minWidth: 320,
          maxWidth: 400,
          boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.3), 0 10px 10px -5px rgba(0, 0, 0, 0.2)',
          border: '2px solid',
          borderColor: (theme) => theme.palette.mode === 'dark' ? '#374151' : '#e5e7eb',
        }}
      >
        {/* Header */}
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            gap: 2,
            mb: 3,
          }}
        >
          <Box
            sx={{
              animation: `${pulseAnimation} 1.5s ease-in-out infinite`,
            }}
          >
            <CircularProgress size={32} thickness={4} />
          </Box>
          <Typography
            variant="h6"
            fontWeight="bold"
            sx={{
              color: (theme) => theme.palette.mode === 'dark' ? '#f3f4f6' : '#111827',
            }}
          >
            ⚡ EXECUTING
          </Typography>
        </Box>

        {/* Divider */}
        <Box
          sx={{
            height: 2,
            backgroundColor: (theme) => theme.palette.mode === 'dark' ? '#374151' : '#e5e7eb',
            mb: 3,
          }}
        />

        {/* Command Details */}
        {command && (
          <Box sx={{ mb: 3 }}>
            <Typography
              variant="caption"
              sx={{
                color: (theme) => theme.palette.mode === 'dark' ? '#9ca3af' : '#6b7280',
                textTransform: 'uppercase',
                letterSpacing: 1,
                fontWeight: 600,
                fontSize: 10,
              }}
            >
              Command
            </Typography>
            <Typography
              variant="body1"
              fontWeight="medium"
              sx={{
                mt: 0.5,
                color: (theme) => theme.palette.mode === 'dark' ? '#f3f4f6' : '#111827',
                fontFamily: 'monospace',
              }}
            >
              {command}
            </Typography>
          </Box>
        )}

        {/* Parameters */}
        {params && Object.keys(params).length > 0 && (
          <Box sx={{ mb: 3 }}>
            <Typography
              variant="caption"
              sx={{
                color: (theme) => theme.palette.mode === 'dark' ? '#9ca3af' : '#6b7280',
                textTransform: 'uppercase',
                letterSpacing: 1,
                fontWeight: 600,
                fontSize: 10,
              }}
            >
              Parameters
            </Typography>
            <Box
              sx={{
                mt: 0.5,
                display: 'flex',
                flexWrap: 'wrap',
                gap: 0.5,
              }}
            >
              {Object.entries(params).slice(0, 3).map(([key, value]) => (
                <Typography
                  key={key}
                  variant="caption"
                  sx={{
                    backgroundColor: (theme) => theme.palette.mode === 'dark' ? '#374151' : '#f3f4f6',
                    color: (theme) => theme.palette.mode === 'dark' ? '#d1d5db' : '#4b5563',
                    px: 1,
                    py: 0.5,
                    borderRadius: 1,
                    fontFamily: 'monospace',
                    fontSize: 11,
                  }}
                >
                  {key}: {String(value).substring(0, 20)}
                  {String(value).length > 20 ? '...' : ''}
                </Typography>
              ))}
            </Box>
          </Box>
        )}

        {/* Progress Bar */}
        <Box sx={{ mb: 2 }}>
          <LinearProgress
            sx={{
              height: 6,
              borderRadius: 3,
              backgroundColor: (theme) => theme.palette.mode === 'dark' ? '#374151' : '#e5e7eb',
              '& .MuiLinearProgress-bar': {
                borderRadius: 3,
                backgroundColor: '#3b82f6',
              },
            }}
          />
        </Box>

        {/* Elapsed Time */}
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 1,
          }}
        >
          <Typography
            variant="body2"
            sx={{
              color: (theme) => theme.palette.mode === 'dark' ? '#9ca3af' : '#6b7280',
              fontFamily: 'monospace',
              fontSize: 13,
            }}
          >
            ⏱️ {elapsedTime.toFixed(2)}s
          </Typography>
        </Box>
      </Box>
    </Box>
  );
};

