/**
 * ExecutionProgressBar Component
 * 
 * Floating progress bar shown during test case execution.
 * Displays current block, progress, elapsed time, and stop button.
 * Non-blocking - ReactFlow remains visible and interactive below.
 */

import React, { useEffect, useState } from 'react';
import { Box, Typography, LinearProgress, IconButton, Tooltip } from '@mui/material';
import StopIcon from '@mui/icons-material/Stop';
import CloseIcon from '@mui/icons-material/Close';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import { BlockExecutionState } from '../../../hooks/testcase/useExecutionState';
import { useTheme } from '../../../contexts/ThemeContext';

interface ExecutionProgressBarProps {
  currentBlockId: string | null;
  blockStates: Map<string, BlockExecutionState>;
  isExecuting: boolean; // NEW: Know when execution is complete
  onStop: () => void;
  onClose: () => void; // NEW: Manual close
  nodes: any[]; // NEW: Pass nodes to get block labels
  executionResult?: { // NEW: Pass backend execution result
    success: boolean;
    execution_time_ms: number;
    error?: string;
  } | null;
}

export const ExecutionProgressBar: React.FC<ExecutionProgressBarProps> = ({
  currentBlockId,
  blockStates,
  isExecuting,
  onStop,
  onClose,
  nodes,
  executionResult,
}) => {
  const { actualMode } = useTheme();
  const [elapsedTime, setElapsedTime] = useState(0);
  const [startTime] = useState(Date.now());
  const [finalTime, setFinalTime] = useState<number | null>(null);
  const [lastBlockLabel, setLastBlockLabel] = useState<string | null>(null);

  // Get block label from node data
  const getCurrentBlockLabel = () => {
    if (!currentBlockId) return null;
    const node = nodes.find(n => n.id === currentBlockId);
    return node?.data?.label || node?.data?.command || node?.type || currentBlockId;
  };

  const currentBlockLabel = getCurrentBlockLabel();

  // Update last block label whenever current block changes
  useEffect(() => {
    if (currentBlockLabel) {
      setLastBlockLabel(currentBlockLabel);
    }
  }, [currentBlockLabel]);

  // Stop timer when execution completes and capture the final time
  useEffect(() => {
    if (!isExecuting && finalTime === null) {
      // Prefer backend execution time over client timer
      if (executionResult?.execution_time_ms) {
        setFinalTime(executionResult.execution_time_ms / 1000); // Convert ms to seconds
      } else if (elapsedTime > 0) {
        setFinalTime(elapsedTime);
      }
    }
  }, [isExecuting, elapsedTime, finalTime, executionResult]);

  // Update elapsed time
  useEffect(() => {
    if (isExecuting) {
      const interval = setInterval(() => {
        setElapsedTime((Date.now() - startTime) / 1000);
      }, 100);

      return () => clearInterval(interval);
    }
  }, [startTime, isExecuting]);

  // Calculate progress
  const total = blockStates.size;
  const completed = Array.from(blockStates.values()).filter(
    s => ['success', 'failure', 'error'].includes(s.status)
  ).length;
  const progress = total > 0 ? (completed / total) * 100 : 0;

  // Count results
  const successCount = Array.from(blockStates.values()).filter(s => s.status === 'success').length;
  const failureCount = Array.from(blockStates.values()).filter(s => s.status === 'failure').length;
  const errorCount = Array.from(blockStates.values()).filter(s => s.status === 'error').length;

  return (
    <Box
      sx={{
        position: 'fixed',
        top: 120, // Below header (64px + 16px margin)
        right: '24px',
        transform: 'translateX(-50%)',
        zIndex: 1100,
        minWidth: 400,
        maxWidth: 600,
        backgroundColor: actualMode === 'dark' ? '#1f2937' : '#ffffff',
        borderRadius: 2,
        boxShadow: '0 8px 16px rgba(0, 0, 0, 0.3)',
        border: '2px solid',
        borderColor: '#3b82f6',
        p: 2,
        animation: 'slideDown 0.3s ease-out',
        '@keyframes slideDown': {
          from: {
            opacity: 0,
            transform: 'translateX(-50%) translateY(-20px)',
          },
          to: {
            opacity: 1,
            transform: 'translateX(-50%) translateY(0)',
          },
        },
      }}
    >
      {/* Header */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          mb: 1.5,
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          {isExecuting ? (
            <>
              <Box
                sx={{
                  width: 10,
                  height: 10,
                  borderRadius: '50%',
                  backgroundColor: '#3b82f6',
                  animation: 'pulse 1.5s ease-in-out infinite',
                  '@keyframes pulse': {
                    '0%, 100%': { opacity: 1, transform: 'scale(1)' },
                    '50%': { opacity: 0.5, transform: 'scale(1.3)' },
                  },
                }}
              />
              <Typography variant="subtitle2" fontWeight="bold" color="#3b82f6">
                ⚡ EXECUTING TEST CASE
              </Typography>
            </>
          ) : (
            <>
              {successCount > 0 && failureCount === 0 && errorCount === 0 ? (
                <>
                  <CheckCircleIcon sx={{ color: '#10b981', fontSize: 20 }} />
                  <Typography variant="subtitle2" fontWeight="bold" color="#10b981">
                    ✓ EXECUTION COMPLETE
                  </Typography>
                </>
              ) : (
                <>
                  <ErrorIcon sx={{ color: '#ef4444', fontSize: 20 }} />
                  <Typography variant="subtitle2" fontWeight="bold" color="#ef4444">
                    ✗ EXECUTION FAILED
                  </Typography>
                </>
              )}
            </>
          )}
        </Box>
        
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          {/* Stats */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            {successCount > 0 && (
              <Typography variant="caption" sx={{ color: '#10b981', fontWeight: 'bold' }}>
                ✓ {successCount}
              </Typography>
            )}
            {failureCount > 0 && (
              <Typography variant="caption" sx={{ color: '#ef4444', fontWeight: 'bold' }}>
                ✗ {failureCount}
              </Typography>
            )}
            {errorCount > 0 && (
              <Typography variant="caption" sx={{ color: '#f59e0b', fontWeight: 'bold' }}>
                ⚠ {errorCount}
              </Typography>
            )}
          </Box>

          {/* Timer */}
          <Typography
            variant="caption"
            sx={{
              fontFamily: 'monospace',
              color: 'text.secondary',
              fontWeight: 'bold',
            }}
          >
            ⏱ {(finalTime ?? elapsedTime).toFixed(1)}s
          </Typography>

          {/* Stop/Close Button */}
          {isExecuting ? (
            <Tooltip title="Stop Execution">
              <IconButton
                size="small"
                onClick={onStop}
                sx={{
                  color: '#ef4444',
                  '&:hover': {
                    backgroundColor: 'rgba(239, 68, 68, 0.1)',
                  },
                }}
              >
                <StopIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          ) : (
            <Tooltip title="Close">
              <IconButton
                size="small"
                onClick={onClose}
                sx={{
                  color: 'text.secondary',
                  '&:hover': {
                    backgroundColor: 'rgba(0, 0, 0, 0.1)',
                  },
                }}
              >
                <CloseIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          )}
        </Box>
      </Box>

      {/* Progress Bar */}
      <Box sx={{ mb: 1 }}>
        <LinearProgress
          variant="determinate"
          value={progress}
          sx={{
            height: 8,
            borderRadius: 4,
            backgroundColor: actualMode === 'dark' ? '#374151' : '#e5e7eb',
            '& .MuiLinearProgress-bar': {
              borderRadius: 4,
              backgroundColor: '#3b82f6',
              transition: 'transform 0.3s ease',
            },
          }}
        />
      </Box>

      {/* Status Text */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <Typography variant="caption" color="text.secondary">
          Step {completed}/{total} {(currentBlockLabel || lastBlockLabel) && `• ${currentBlockLabel || lastBlockLabel}`}
        </Typography>
        <Typography variant="caption" color="text.secondary" fontWeight="bold">
          {Math.round(progress)}%
        </Typography>
      </Box>
    </Box>
  );
};

