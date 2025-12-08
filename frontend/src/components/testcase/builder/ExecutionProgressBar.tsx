/**
 * ExecutionProgressBar Component
 * 
 * Enhanced progress bar with:
 * - Optional AI reasoning section
 * - Scrollable step history (most recent first)
 * - Detailed execution log
 * - Collapsible sections
 */

import React, { useEffect, useState, useRef } from 'react';
import { Box, Typography, LinearProgress, IconButton, Tooltip, Collapse, Accordion, AccordionSummary, AccordionDetails } from '@mui/material';
import StopIcon from '@mui/icons-material/Stop';
import CloseIcon from '@mui/icons-material/Close';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import DragIndicatorIcon from '@mui/icons-material/DragIndicator';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
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
    report_url?: string;  // 🆕 R2 report URL
    logs_url?: string;    // 🆕 R2 logs URL
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
  const [copiedLogId, setCopiedLogId] = useState<string | null>(null);
  const [isAIReasoningExpanded, setIsAIReasoningExpanded] = useState(true);
  
  // Draggable state
  const [position, setPosition] = useState({ x: 0, y: 120 });
  const [isDragging, setIsDragging] = useState(false);
  const dragRef = useRef<{ startX: number; startY: number; initialX: number; initialY: number } | null>(null);

  // Copy logs to clipboard
  const handleCopyLogs = (logs: any, logId: string, event: React.MouseEvent) => {
    event.stopPropagation(); // Prevent accordion toggle
    const logsText = typeof logs === 'string' ? logs : JSON.stringify(logs, null, 2);
    navigator.clipboard.writeText(logsText).then(() => {
      setCopiedLogId(logId);
      setTimeout(() => setCopiedLogId(null), 2000);
    }).catch((err) => {
      console.error('Failed to copy logs:', err);
    });
  };

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

  // Calculate progress - only count blocks that actually executed
  const completed = Array.from(blockStates.values()).filter(
    s => ['success', 'failure', 'error'].includes(s.status)
  ).length;
  // Total = completed blocks + currently executing (if any)
  const total = isExecuting && currentBlockId ? completed + 1 : completed;
  const progress = total > 0 ? (completed / total) * 100 : 0;

  // Count results
  const successCount = Array.from(blockStates.values()).filter(s => s.status === 'success').length;
  const failureCount = Array.from(blockStates.values()).filter(s => s.status === 'failure').length;
  const errorCount = Array.from(blockStates.values()).filter(s => s.status === 'error').length;

  // 🆕 Calculate current step NUMBER based on completed steps
  const currentStepNumber = isExecuting && currentBlockId 
    ? completed + 1  // Currently executing = completed + 1
    : total;         // When done, show total

  // Helper function to get full block label (same logic as UniversalBlock)
  const getFullBlockLabel = (node: any) => {
    if (!node) return 'Unknown';
    
    const data = node.data;
    const type = node.type;
    
    // If custom label exists, use it
    if (data?.label) {
      return data.label;
    }
    
    // Otherwise construct based on block type (same as UniversalBlock headerLabel logic)
    if (type === 'navigation' && data?.target_node_label) {
      if (data.block_label) {
        return data.block_label;
      } else {
        return `navigation:${data.target_node_label}`;
      }
    } else if (['sleep', 'get_current_time', 'condition', 'set_variable', 'loop'].includes(type as string)) {
      return 'STANDARD';
    } else if (type === 'action' || ['press_key', 'press_sequence', 'tap', 'swipe', 'type_text'].includes(type as string)) {
      return 'ACTION';
    } else if (type === 'verification' || ['verify_image', 'verify_ocr', 'verify_audio', 'verify_element'].includes(type as string)) {
      return 'VERIFICATION';
    }
    
    // Fallback
    return data?.command || type || 'Unknown';
  };

  // 🆕 Separate current executing step from completed history (exclude terminal blocks)
  const currentExecutingStep = currentBlockId && isExecuting ? (() => {
    const node = nodes.find(n => n.id === currentBlockId);
    const state = blockStates.get(currentBlockId);
    
    // Skip terminal blocks (success/failure) - they're not executable steps
    if (!state || !node || ['success', 'failure'].includes(node.type || '')) return null;
    
    return {
      blockId: currentBlockId,
      label: getFullBlockLabel(node),
      type: node?.type || 'unknown',
      command: node?.data?.command,
      state,
    };
  })() : null;

  // Build completed step history (exclude current executing)
  const completedSteps = Array.from(blockStates.entries())
    .map(([blockId, state]) => {
      const node = nodes.find(n => n.id === blockId);
      return {
        blockId,
        label: getFullBlockLabel(node),
        type: node?.type || 'unknown',
        command: node?.data?.command,
        state,
      };
    })
    .filter(step => ['success', 'failure', 'error'].includes(step.state.status))
    .reverse(); // Most recent first

  // Draggable handlers
  const handleMouseDown = (e: React.MouseEvent) => {
    if ((e.target as HTMLElement).closest('.drag-handle')) {
      setIsDragging(true);
      dragRef.current = {
        startX: e.clientX,
        startY: e.clientY,
        initialX: position.x,
        initialY: position.y,
      };
      e.preventDefault();
    }
  };

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (isDragging && dragRef.current) {
        const deltaX = e.clientX - dragRef.current.startX;
        const deltaY = e.clientY - dragRef.current.startY;
        setPosition({
          x: dragRef.current.initialX + deltaX,
          y: dragRef.current.initialY + deltaY,
        });
      }
    };

    const handleMouseUp = () => {
      setIsDragging(false);
      dragRef.current = null;
    };

    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging]);

  return (
    <Box
      onMouseDown={handleMouseDown}
      sx={{
        position: 'fixed',
        top: `${position.y}px`,
        right: position.x === 0 ? '24px' : 'auto',
        left: position.x !== 0 ? `${position.x}px` : 'auto',
        zIndex: 1100,
        minWidth: 450,
        maxWidth: 650,
        backgroundColor: actualMode === 'dark' ? '#1f2937' : '#ffffff',
        borderRadius: 2,
        boxShadow: isDragging ? '0 12px 24px rgba(0, 0, 0, 0.4)' : '0 8px 16px rgba(0, 0, 0, 0.3)',
        borderWidth: '2px',
        borderStyle: 'solid',
        borderColor: '#3b82f6',
        cursor: isDragging ? 'grabbing' : 'default',
        userSelect: isDragging ? 'none' : 'auto',
        transition: isDragging ? 'none' : 'box-shadow 0.2s ease',
        animation: position.x === 0 && position.y === 120 ? 'slideDown 0.3s ease-out' : 'none',
        '@keyframes slideDown': {
          from: {
            opacity: 0,
            transform: 'translateY(-20px)',
          },
          to: {
            opacity: 1,
            transform: 'translateY(0)',
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
          {/* Drag Handle */}
          <Box
            className="drag-handle"
            sx={{
              cursor: 'grab',
              display: 'flex',
              alignItems: 'center',
              color: 'text.secondary',
              '&:hover': {
                color: 'text.primary',
              },
              '&:active': {
                cursor: 'grabbing',
              },
            }}
          >
            <DragIndicatorIcon fontSize="small" />
          </Box>
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
                ⚡ EXECUTING
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
              
              {/* Report and Logs Links (inline with status) */}
              {executionResult && (executionResult.report_url || executionResult.logs_url) && (
                <Box sx={{ display: 'flex', gap: 1.5, ml: 2 }}>
                  {executionResult.report_url && (
                    <Typography
                      variant="caption"
                      component="a"
                      href={executionResult.report_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      sx={{
                        color: '#3b82f6',
                        textDecoration: 'none',
                        fontWeight: 'bold',
                        '&:hover': {
                          textDecoration: 'underline',
                        },
                      }}
                    >
                      📊 Report
                    </Typography>
                  )}
                  {executionResult.logs_url && (
                    <Typography
                      variant="caption"
                      component="a"
                      href={executionResult.logs_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      sx={{
                        color: '#10b981',
                        textDecoration: 'none',
                        fontWeight: 'bold',
                        '&:hover': {
                          textDecoration: 'underline',
                        },
                      }}
                    >
                      📝 Logs
                    </Typography>
                  )}
                </Box>
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
            ⏱ {(finalTime ?? elapsedTime).toFixed(2)}s
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
            {/* Hide total during execution, show only at the end */}
            {isExecuting 
              ? `Step ${currentStepNumber}${currentExecutingStep?.label ? ` • ${currentExecutingStep.label}` : ''}`
              : `Step ${currentStepNumber}/${total}${completedSteps.length > 0 && completedSteps[0]?.label ? ` • ${completedSteps[0].label}` : ''}`
            }
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
      {(currentExecutingStep || completedSteps.length > 0) && (
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
            {/* 🆕 Current Executing Step (always at top) */}
            {currentExecutingStep && (() => {
              // Calculate step number by counting completed steps + 1 (current)
              const executingStepNumber = completedSteps.length + 1;
              
              return (
                <Box
                  sx={{
                    mb: completedSteps.length > 0 ? 1.5 : 0,
                    p: 1.5,
                    borderRadius: 1,
                    backgroundColor: actualMode === 'dark' ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)',
                    borderWidth: '1px',
                    borderStyle: 'solid',
                    borderColor: '#3b82f6',
                    animation: 'stepPulse 2s ease-in-out infinite',
                    '@keyframes stepPulse': {
                      '0%, 100%': {
                        borderColor: '#3b82f6',
                        boxShadow: `0 0 0 rgba(59, 130, 246, 0)`,
                      },
                      '50%': {
                        borderColor: '#3b82f6',
                        boxShadow: `0 0 8px rgba(59, 130, 246, 0.4)`,
                      },
                    },
                  }}
                >
                  {/* Step Header */}
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Typography variant="caption" sx={{ fontSize: '0.875rem' }}>
                        🔵
                      </Typography>
                      <Typography variant="caption" fontWeight="bold" sx={{ color: '#3b82f6' }}>
                        STEP {executingStepNumber}: {currentExecutingStep.label} EXECUTING...
                      </Typography>
                    </Box>
                  
                  </Box>
                </Box>
              );
            })()}

            {/* Completed Steps History */}
            {completedSteps.map((step, index) => {
              // Calculate step number for completed steps incrementally
              // completedSteps is in reverse order (most recent first), so stepNumber = total completed - index
              const stepNumber = completedSteps.length - index;
              
              const statusIcon = step.state.status === 'success' ? '✅' :
                                step.state.status === 'failure' ? '❌' : '⚠️';
              const statusColor = step.state.status === 'success' ? '#10b981' :
                                 step.state.status === 'failure' ? '#ef4444' : '#f59e0b';
              const statusText = step.state.status === 'success' ? 'SUCCESS' :
                                step.state.status === 'failure' ? 'FAILED' : 'ERROR';
              
              return (
                <Box
                  key={step.blockId}
                  sx={{
                    mb: index < completedSteps.length - 1 ? 1.5 : 0,
                    p: 1.5,
                    borderRadius: 1,
                    backgroundColor: actualMode === 'dark' ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)',
                    borderWidth: '1px',
                    borderStyle: 'solid',
                    borderColor: actualMode === 'dark' ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)',
                  }}
                >
                {/* Step Header */}
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: (step.state.error || step.state.result?.logs) ? 1 : 0 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Typography variant="caption" sx={{ fontSize: '0.875rem' }}>
                      {statusIcon}
                    </Typography>
                    <Typography variant="caption" fontWeight="bold" sx={{ color: statusColor }}>
                      STEP {stepNumber}: {step.label} {statusText}
                    </Typography>
                  </Box>
                  <Typography variant="caption" sx={{ fontFamily: 'monospace', color: 'text.secondary' }}>
                    ⏱ {((step.state.duration || 0) / 1000).toFixed(2)}s
                  </Typography>
                </Box>

                  {/* Error Message with Collapsible Logs */}
                  {step.state.error && (
                    <Box sx={{ mt: 1 }}>
                      <Accordion 
                        defaultExpanded={false}
                        sx={{
                          backgroundColor: 'rgba(239, 68, 68, 0.1)',
                          borderLeft: '3px solid #ef4444',
                          boxShadow: 'none',
                          '&:before': { display: 'none' },
                        }}
                      >
                        <AccordionSummary
                          expandIcon={<ExpandMoreIcon sx={{ color: '#ef4444', fontSize: 16 }} />}
                          sx={{
                            minHeight: '30px !important',
                            padding: '2px 12px !important',
                            '& .MuiAccordionSummary-content': {
                              margin: '0 !important',
                            },
                          }}
                        >
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flex: 1 }}>
                            <Typography variant="caption" sx={{ color: '#ef4444', fontWeight: 'bold', whiteSpace: 'nowrap' }}>
                              ⚠️ Error
                            </Typography>
                            <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.75rem', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                              {step.state.error.length > 120 ? `${step.state.error.substring(0, 120)}...` : step.state.error}
                            </Typography>
                            {step.state.result?.logs && (
                              <Tooltip title={copiedLogId === `error-${step.blockId}` ? "Copied!" : "Copy logs"}>
                                <IconButton
                                  size="small"
                                  onClick={(e) => handleCopyLogs(step.state.result.logs, `error-${step.blockId}`, e)}
                                  sx={{
                                    color: copiedLogId === `error-${step.blockId}` ? '#10b981' : '#ef4444',
                                    padding: '2px',
                                    '&:hover': {
                                      backgroundColor: 'rgba(239, 68, 68, 0.1)',
                                    },
                                  }}
                                >
                                  <ContentCopyIcon sx={{ fontSize: 14 }} />
                                </IconButton>
                              </Tooltip>
                            )}
                          </Box>
                        </AccordionSummary>
                        <AccordionDetails sx={{ padding: '0px 12px !important' }}>
                          <Typography
                            variant="caption"
                            sx={{
                              display: 'block',
                              color: 'text.secondary',
                              fontSize: '0.75rem',
                              mb: step.state.result?.logs ? 1 : 0,
                              whiteSpace: 'pre-wrap',
                            }}
                          >
                            {step.state.error}
                          </Typography>
                          {/* Execution Logs */}
                          {step.state.result?.logs && (
                            <Box
                              sx={{
                                backgroundColor: actualMode === 'dark' ? 'rgba(0,0,0,0.3)' : 'rgba(0,0,0,0.05)',
                                borderRadius: 0.5,
                                maxHeight: 200,
                                overflowY: 'auto',
                                fontFamily: 'monospace',
                                fontSize: '0.7rem',
                                '&::-webkit-scrollbar': {
                                  width: '4px',
                                },
                                '&::-webkit-scrollbar-track': {
                                  background: actualMode === 'dark' ? '#374151' : '#e5e7eb',
                                },
                                '&::-webkit-scrollbar-thumb': {
                                  background: actualMode === 'dark' ? '#6b7280' : '#9ca3af',
                                  borderRadius: '2px',
                                },
                              }}
                            >
                              <pre style={{ margin: 0, padding: '4px', whiteSpace: 'pre-wrap', color: actualMode === 'dark' ? '#d1d5db' : '#374151' }}>
                                {typeof step.state.result.logs === 'string' 
                                  ? step.state.result.logs 
                                  : JSON.stringify(step.state.result.logs, null, 2)}
                              </pre>
                            </Box>
                          )}
                        </AccordionDetails>
                      </Accordion>
                    </Box>
                  )}
                  
                  {/* Success Logs - Show logs even when there's no error */}
                  {!step.state.error && step.state.result?.logs && (
                    <Box>
                      <Accordion 
                        defaultExpanded={false}
                        sx={{
                          backgroundColor: 'rgba(16, 185, 129, 0.1)',
                          borderLeft: '3px solid #10b981',
                          boxShadow: 'none',
                          '&:before': { display: 'none' },
                        }}
                      >
                        <AccordionSummary
                          expandIcon={<ExpandMoreIcon sx={{ color: '#10b981', fontSize: 16 }} />}
                          sx={{
                            minHeight: '30px !important',
                            padding: '2px 12px !important',
                            '& .MuiAccordionSummary-content': {
                              margin: '0 !important',
                            },
                          }}
                        >
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flex: 1 }}>
                            <Typography variant="caption" sx={{ color: '#10b981', fontWeight: 'bold', whiteSpace: 'nowrap' }}>
                              📋 Execution Logs
                            </Typography>
                            <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.75rem', flex: 1 }}>
                              Click to view execution logs
                            </Typography>
                            <Tooltip title={copiedLogId === `success-${step.blockId}` ? "Copied!" : "Copy logs"}>
                              <IconButton
                                size="small"
                                onClick={(e) => handleCopyLogs(step.state.result.logs, `success-${step.blockId}`, e)}
                                sx={{
                                  color: copiedLogId === `success-${step.blockId}` ? '#3b82f6' : '#10b981',
                                  padding: '2px',
                                  '&:hover': {
                                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                                  },
                                }}
                              >
                                <ContentCopyIcon sx={{ fontSize: 14 }} />
                              </IconButton>
                            </Tooltip>
                          </Box>
                        </AccordionSummary>
                        <AccordionDetails sx={{ padding: '0px 12px !important' }}>
                          {/* Execution Logs */}
                          {step.state.result?.logs && (
                            <Box
                              sx={{
                                backgroundColor: actualMode === 'dark' ? 'rgba(0,0,0,0.3)' : 'rgba(0,0,0,0.05)',
                                borderRadius: 0.5,
                                maxHeight: 200,
                                overflowY: 'auto',
                                fontFamily: 'monospace',
                                fontSize: '0.7rem',
                                '&::-webkit-scrollbar': {
                                  width: '4px',
                                },
                                '&::-webkit-scrollbar-track': {
                                  background: actualMode === 'dark' ? '#374151' : '#e5e7eb',
                                },
                                '&::-webkit-scrollbar-thumb': {
                                  background: actualMode === 'dark' ? '#6b7280' : '#9ca3af',
                                  borderRadius: '2px',
                                },
                              }}
                            >
                              <pre style={{ margin: 0, padding: '4px', whiteSpace: 'pre-wrap', color: actualMode === 'dark' ? '#d1d5db' : '#374151' }}>
                                {typeof step.state.result.logs === 'string' 
                                  ? step.state.result.logs 
                                  : JSON.stringify(step.state.result.logs, null, 2)}
                              </pre>
                            </Box>
                          )}
                        </AccordionDetails>
                      </Accordion>
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

