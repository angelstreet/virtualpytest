/**
 * ExecutionProgressBar Component
 * 
 * Enhanced progress bar with:
 * - Optional AI reasoning section
 * - Scrollable step history (most recent first)
 * - Detailed execution log
 * - Collapsible sections
 */

import React, { useEffect, useState } from 'react';
import { Box, Typography, LinearProgress, IconButton, Tooltip, Collapse } from '@mui/material';
import StopIcon from '@mui/icons-material/Stop';
import CloseIcon from '@mui/icons-material/Close';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import { BlockExecutionState } from '../../../hooks/testcase/useExecutionState';
import { useTheme } from '../../../contexts/ThemeContext';

interface AIReasoning {
  plan?: string;
  analysis?: string;
  suggestions?: string[];
  insights?: string[];
  troubleshooting?: string[];
}

interface StepDetail {
  block_id: string;
  step_number: number;
  label: string;
  type: string;
  command?: string;
  success: boolean;
  execution_time_ms: number;
  error?: string;
  message?: string;
  timestamp: number;
}

interface ExecutionProgressBarProps {
  currentBlockId: string | null;
  blockStates: Map<string, BlockExecutionState>;
  isExecuting: boolean;
  onStop: () => void;
  onClose: () => void;
  nodes: any[];
  executionResult?: {
    success: boolean;
    result_type?: 'success' | 'failure' | 'error';
    execution_time_ms: number;
    error?: string;
    step_count?: number;
  } | null;
  aiReasoning?: AIReasoning | null; // 🆕 Optional AI reasoning
  stepDetails?: StepDetail[]; // 🆕 Detailed step information
}

export const ExecutionProgressBar: React.FC<ExecutionProgressBarProps> = ({
  currentBlockId,
  blockStates,
  isExecuting,
  onStop,
  onClose,
  nodes,
  executionResult,
  aiReasoning,
}) => {
  const { actualMode } = useTheme();
  const [elapsedTime, setElapsedTime] = useState(0);
  const [startTime] = useState(Date.now());
  const [finalTime, setFinalTime] = useState<number | null>(null);
  const [lastBlockLabel, setLastBlockLabel] = useState<string | null>(null);
  const [isAIReasoningExpanded, setIsAIReasoningExpanded] = useState(true);

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

  // Build step history from blockStates (most recent first)
  const stepHistory = Array.from(blockStates.entries())
    .map(([blockId, state]) => {
      const node = nodes.find(n => n.id === blockId);
      return {
        blockId,
        label: node?.data?.label || node?.data?.command || node?.type || blockId,
        type: node?.type || 'unknown',
        command: node?.data?.command,
        state,
      };
    })
    .filter(step => step.state.status !== 'pending')
    .reverse(); // Most recent first

  return (
    <Box
      sx={{
        position: 'fixed',
        top: 120,
        right: '24px',
        transform: 'translateX(-50%)',
        zIndex: 1100,
        minWidth: 450,
        maxWidth: 650,
        backgroundColor: actualMode === 'dark' ? '#1f2937' : '#ffffff',
        borderRadius: 2,
        boxShadow: '0 8px 16px rgba(0, 0, 0, 0.3)',
        border: '2px solid',
        borderColor: '#3b82f6',
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
          p: 2,
          pb: 1.5,
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
              {executionResult?.success ? (
                <>
                  <CheckCircleIcon sx={{ color: '#10b981', fontSize: 20 }} />
                  <Typography variant="subtitle2" fontWeight="bold" color="#10b981">
                    ✓ TEST PASSED
                  </Typography>
                </>
              ) : executionResult?.result_type === 'failure' ? (
                <>
                  <ErrorIcon sx={{ color: '#ef4444', fontSize: 20 }} />
                  <Typography variant="subtitle2" fontWeight="bold" color="#ef4444">
                    ✗ TEST FAILED
                  </Typography>
                </>
              ) : (
                <>
                  <ErrorIcon sx={{ color: '#f59e0b', fontSize: 20 }} />
                  <Typography variant="subtitle2" fontWeight="bold" color="#f59e0b">
                    ⚠ EXECUTION ERROR
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
      <Box sx={{ px: 2, pb: 1.5 }}>
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
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            mt: 0.5,
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

      {/* AI Reasoning Section (Optional) */}
      {aiReasoning && (
        <Box sx={{ borderTop: 1, borderColor: 'divider' }}>
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              px: 2,
              py: 1,
              cursor: 'pointer',
              '&:hover': {
                backgroundColor: actualMode === 'dark' ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.02)',
              },
            }}
            onClick={() => setIsAIReasoningExpanded(!isAIReasoningExpanded)}
          >
            <Typography variant="caption" fontWeight="bold" color="text.secondary">
              🤖 AI REASONING
            </Typography>
            <IconButton size="small">
              {isAIReasoningExpanded ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
            </IconButton>
          </Box>
          
          <Collapse in={isAIReasoningExpanded}>
            <Box
              sx={{
                px: 2,
                pb: 2,
                maxHeight: 200,
                overflowY: 'auto',
                fontSize: '0.8125rem',
              }}
            >
              {/* Test Plan */}
              {aiReasoning.plan && (
                <Box sx={{ mb: 1.5 }}>
                  <Typography variant="caption" sx={{ color: 'text.secondary', lineHeight: 1.6 }}>
                    {aiReasoning.plan}
                  </Typography>
                </Box>
              )}

              {/* AI Analysis (for failures) */}
              {aiReasoning.analysis && !isExecuting && (
                <Box sx={{ mb: 1.5 }}>
                  <Typography variant="caption" fontWeight="bold" sx={{ color: '#f59e0b', display: 'block', mb: 0.5 }}>
                    💡 AI ANALYSIS
                  </Typography>
                  <Typography variant="caption" sx={{ color: 'text.secondary', lineHeight: 1.6 }}>
                    {aiReasoning.analysis}
                  </Typography>
                </Box>
              )}

              {/* Suggestions */}
              {aiReasoning.suggestions && aiReasoning.suggestions.length > 0 && (
                <Box sx={{ mb: 1.5 }}>
                  <Typography variant="caption" fontWeight="bold" sx={{ color: '#10b981', display: 'block', mb: 0.5 }}>
                    🔧 SUGGESTED FIXES
                  </Typography>
                  {aiReasoning.suggestions.map((suggestion, idx) => (
                    <Typography key={idx} variant="caption" sx={{ color: 'text.secondary', display: 'block', lineHeight: 1.6, ml: 1 }}>
                      • {suggestion}
                    </Typography>
                  ))}
                </Box>
              )}

              {/* Insights (for success) */}
              {aiReasoning.insights && aiReasoning.insights.length > 0 && (
                <Box sx={{ mb: 1.5 }}>
                  <Typography variant="caption" fontWeight="bold" sx={{ color: '#3b82f6', display: 'block', mb: 0.5 }}>
                    📊 INSIGHTS
                  </Typography>
                  {aiReasoning.insights.map((insight, idx) => (
                    <Typography key={idx} variant="caption" sx={{ color: 'text.secondary', display: 'block', lineHeight: 1.6, ml: 1 }}>
                      • {insight}
                    </Typography>
                  ))}
                </Box>
              )}

              {/* Troubleshooting (for errors) */}
              {aiReasoning.troubleshooting && aiReasoning.troubleshooting.length > 0 && (
                <Box>
                  <Typography variant="caption" fontWeight="bold" sx={{ color: '#ef4444', display: 'block', mb: 0.5 }}>
                    🔍 TROUBLESHOOTING
                  </Typography>
                  {aiReasoning.troubleshooting.map((step, idx) => (
                    <Typography key={idx} variant="caption" sx={{ color: 'text.secondary', display: 'block', lineHeight: 1.6, ml: 1 }}>
                      {idx + 1}. {step}
                    </Typography>
                  ))}
                </Box>
              )}
            </Box>
          </Collapse>
        </Box>
      )}

      {/* Step History Section */}
      {stepHistory.length > 0 && (
        <Box sx={{ borderTop: 1, borderColor: 'divider' }}>
          <Box
            sx={{
              px: 2,
              py: 2,
              maxHeight: 400,
              overflowY: 'auto',
              '&::-webkit-scrollbar': {
                width: '6px',
              },
              '&::-webkit-scrollbar-track': {
                background: actualMode === 'dark' ? '#374151' : '#e5e7eb',
                borderRadius: '3px',
              },
              '&::-webkit-scrollbar-thumb': {
                background: actualMode === 'dark' ? '#6b7280' : '#9ca3af',
                borderRadius: '3px',
                '&:hover': {
                  background: actualMode === 'dark' ? '#9ca3af' : '#6b7280',
                },
              },
            }}
          >
            {stepHistory.map((step, index) => {
              const isCurrentStep = step.blockId === currentBlockId && isExecuting;
              const statusIcon = step.state.status === 'executing' || isCurrentStep ? '🔵' :
                                step.state.status === 'success' ? '✅' :
                                step.state.status === 'failure' ? '❌' : '⚠️';
              const statusColor = step.state.status === 'executing' || isCurrentStep ? '#3b82f6' :
                                 step.state.status === 'success' ? '#10b981' :
                                 step.state.status === 'failure' ? '#ef4444' : '#f59e0b';
              const statusText = step.state.status === 'executing' || isCurrentStep ? 'EXECUTING' :
                                step.state.status === 'success' ? 'SUCCESS' :
                                step.state.status === 'failure' ? 'FAILED' : 'ERROR';
              
              return (
                <Box
                  key={step.blockId}
                  sx={{
                    mb: index < stepHistory.length - 1 ? 1.5 : 0,
                    p: 1.5,
                    borderRadius: 1,
                    backgroundColor: actualMode === 'dark' ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)',
                    border: '1px solid',
                    borderColor: isCurrentStep ? statusColor : (actualMode === 'dark' ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)'),
                    animation: isCurrentStep ? 'stepPulse 2s ease-in-out infinite' : undefined,
                    '@keyframes stepPulse': {
                      '0%, 100%': {
                        borderColor: statusColor,
                        boxShadow: `0 0 0 rgba(59, 130, 246, 0)`,
                      },
                      '50%': {
                        borderColor: statusColor,
                        boxShadow: `0 0 8px rgba(59, 130, 246, 0.4)`,
                      },
                    },
                  }}
                >
                  {/* Step Header */}
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 0.5 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Typography variant="caption" sx={{ fontSize: '0.875rem' }}>
                        {statusIcon}
                      </Typography>
                      <Typography variant="caption" fontWeight="bold" sx={{ color: statusColor }}>
                        {statusText}
                      </Typography>
                    </Box>
                    <Typography variant="caption" sx={{ fontFamily: 'monospace', color: 'text.secondary' }}>
                      {isCurrentStep ? 'Running...' : `⏱ ${((step.state.duration || 0) / 1000).toFixed(2)}s`}
                    </Typography>
                  </Box>

                  {/* Step Details */}
                  <Typography variant="caption" sx={{ display: 'block', color: 'text.primary', mb: 0.5 }}>
                    {step.label}
                  </Typography>
                  
                  {step.command && (
                    <Typography variant="caption" sx={{ display: 'block', color: 'text.secondary', fontSize: '0.75rem' }}>
                      Command: {step.command}
                    </Typography>
                  )}

                  {/* Error Message */}
                  {step.state.error && (
                    <Box
                      sx={{
                        mt: 1,
                        p: 1,
                        borderRadius: 0.5,
                        backgroundColor: 'rgba(239, 68, 68, 0.1)',
                        borderLeft: '3px solid #ef4444',
                      }}
                    >
                      <Typography variant="caption" sx={{ display: 'block', color: '#ef4444', fontWeight: 'bold', mb: 0.5 }}>
                        ⚠️ Error
                      </Typography>
                      <Typography variant="caption" sx={{ display: 'block', color: 'text.secondary', fontSize: '0.75rem' }}>
                        {step.state.error}
                      </Typography>
                    </Box>
                  )}
                </Box>
              );
            })}
          </Box>
        </Box>
      )}
    </Box>
  );
};

