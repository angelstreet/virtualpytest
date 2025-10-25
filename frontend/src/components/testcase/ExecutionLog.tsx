/**
 * ExecutionLog Component
 * 
 * Collapsible execution log showing step-by-step execution history.
 * Displays block execution results with timing and status.
 */

import React, { useState, useEffect } from 'react';
import { Box, Typography, IconButton, Collapse, Chip } from '@mui/material';
import ChevronLeftIcon from '@mui/icons-material/ChevronLeft';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import CloseIcon from '@mui/icons-material/Close';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import CancelIcon from '@mui/icons-material/Cancel';
import ErrorIcon from '@mui/icons-material/Error';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import { BlockExecutionState } from '../../hooks/testcase/useExecutionState';
import { useTheme } from '../../contexts/ThemeContext';
import { Node } from 'reactflow';

interface ExecutionLogProps {
  blockStates: Map<string, BlockExecutionState>;
  nodes: Node[];
  onClose: () => void; // NEW: Manual close
}

export const ExecutionLog: React.FC<ExecutionLogProps> = ({
  blockStates,
  nodes,
  onClose,
}) => {
  const { actualMode } = useTheme();
  const [isCollapsed, setIsCollapsed] = useState(true);
  
  // Auto-open when execution starts
  useEffect(() => {
    if (blockStates.size > 0) {
      setIsCollapsed(false);
    }
  }, [blockStates.size]);

  // Get block label from node
  const getBlockLabel = (blockId: string): string => {
    const node = nodes.find(n => n.id === blockId);
    if (!node) return blockId;

    // Get label based on node type and data
    if (node.type === 'start') return 'START';
    if (node.type === 'success') return 'PASS';
    if (node.type === 'failure') return 'FAIL';
    
    return node.data?.command || node.data?.target_node_label || node.data?.label || node.type || blockId;
  };

  // Get status icon
  const getStatusIcon = (state: BlockExecutionState) => {
    switch (state.status) {
      case 'success':
        return <CheckCircleIcon fontSize="small" sx={{ color: '#10b981' }} />;
      case 'failure':
        return <CancelIcon fontSize="small" sx={{ color: '#ef4444' }} />;
      case 'error':
        return <ErrorIcon fontSize="small" sx={{ color: '#f59e0b' }} />;
      case 'executing':
        return <PlayArrowIcon fontSize="small" sx={{ color: '#3b82f6' }} />;
      default:
        return <Box sx={{ width: 20, height: 20, borderRadius: '50%', backgroundColor: '#6b7280' }} />;
    }
  };

  // Convert blockStates to array and sort by execution order (startTime)
  const logEntries = Array.from(blockStates.entries())
    .filter(([_, state]) => state.status !== 'idle' && state.status !== 'pending')
    .sort((a, b) => (a[1].startTime || 0) - (b[1].startTime || 0));

  // Don't show if no execution has ever occurred
  if (logEntries.length === 0) {
    return null;
  }

  return (
    <Box
      sx={{
        position: 'fixed',
        right: isCollapsed ? 0 : 0,
        top: 64, // Below header
        bottom: 32, // Above footer
        width: isCollapsed ? 40 : 320,
        backgroundColor: actualMode === 'dark' ? '#1f2937' : '#ffffff',
        borderLeft: '1px solid',
        borderColor: actualMode === 'dark' ? '#374151' : '#e5e7eb',
        boxShadow: '-2px 0 8px rgba(0, 0, 0, 0.1)',
        transition: 'width 0.3s ease',
        zIndex: 900,
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {/* Toggle Button */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          p: 1,
          borderBottom: '1px solid',
          borderColor: actualMode === 'dark' ? '#374151' : '#e5e7eb',
        }}
      >
        {!isCollapsed && (
          <Typography variant="subtitle2" fontWeight="bold" sx={{ fontSize: 12 }}>
            EXECUTION LOG
          </Typography>
        )}
        <Box sx={{ display: 'flex', gap: 0.5 }}>
          {!isCollapsed && (
            <IconButton
              size="small"
              onClick={onClose}
              sx={{
                color: 'text.secondary',
              }}
            >
              <CloseIcon fontSize="small" />
            </IconButton>
          )}
          <IconButton
            size="small"
            onClick={() => setIsCollapsed(!isCollapsed)}
            sx={{
              color: 'text.secondary',
            }}
          >
            {isCollapsed ? <ChevronLeftIcon /> : <ChevronRightIcon />}
          </IconButton>
        </Box>
      </Box>

      {/* Log Content */}
      <Collapse in={!isCollapsed} orientation="horizontal">
        <Box
          sx={{
            width: 280,
            height: '100%',
            overflowY: 'auto',
            p: 1.5,
          }}
        >
          {logEntries.length === 0 ? (
            <Typography variant="caption" color="text.secondary">
              No execution history
            </Typography>
          ) : (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              {logEntries.map(([blockId, state], index) => (
                <Box
                  key={blockId}
                  sx={{
                    p: 1.5,
                    borderRadius: 1,
                    border: '1px solid',
                    borderColor: actualMode === 'dark' ? '#374151' : '#e5e7eb',
                    backgroundColor: state.status === 'executing' 
                      ? 'rgba(59, 130, 246, 0.05)'
                      : 'transparent',
                    animation: state.status === 'executing' ? 'pulse 1.5s ease-in-out infinite' : 'none',
                    '@keyframes pulse': {
                      '0%, 100%': { opacity: 1 },
                      '50%': { opacity: 0.7 },
                    },
                  }}
                >
                  {/* Header */}
                  <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1, mb: 0.5 }}>
                    <Box sx={{ mt: 0.25 }}>
                      {getStatusIcon(state)}
                    </Box>
                    <Box sx={{ flex: 1, minWidth: 0 }}>
                      <Typography
                        variant="caption"
                        fontWeight="bold"
                        sx={{
                          display: 'block',
                          color: state.status === 'executing' ? '#3b82f6' : 'text.primary',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                        }}
                      >
                        {index + 1}. {getBlockLabel(blockId)}
                      </Typography>
                      
                      {/* Duration */}
                      {state.duration && (
                        <Typography variant="caption" color="text.secondary" sx={{ fontSize: 10 }}>
                          ⏱ {(state.duration / 1000).toFixed(2)}s
                        </Typography>
                      )}
                      
                      {/* Error message */}
                      {state.error && (
                        <Typography
                          variant="caption"
                          sx={{
                            display: 'block',
                            color: '#ef4444',
                            fontSize: 10,
                            mt: 0.5,
                            wordBreak: 'break-word',
                          }}
                        >
                          {state.error}
                        </Typography>
                      )}
                    </Box>
                  </Box>

                  {/* Status Chip */}
                  <Chip
                    label={state.status.toUpperCase()}
                    size="small"
                    sx={{
                      height: 18,
                      fontSize: 9,
                      fontWeight: 'bold',
                      backgroundColor:
                        state.status === 'success' ? '#10b981' :
                        state.status === 'failure' ? '#ef4444' :
                        state.status === 'error' ? '#f59e0b' :
                        state.status === 'executing' ? '#3b82f6' : '#6b7280',
                      color: 'white',
                    }}
                  />
                </Box>
              ))}
            </Box>
          )}
        </Box>
      </Collapse>
    </Box>
  );
};

