import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  TextField,
  Button,
  CircularProgress,
  IconButton,
  Checkbox,
  FormControlLabel,
} from '@mui/material';
import {
  SmartToy as AIIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
} from '@mui/icons-material';

import { Host, Device } from '../../types/common/Host_Types';
import { useAI } from '../../hooks/useAI';
import { getZIndex } from '../../utils/zIndexUtils';

interface AIExecutionPanelProps {
  host: Host;
  device: Device;
  isControlActive: boolean;
  isVisible: boolean;
}

export const AIExecutionPanel: React.FC<AIExecutionPanelProps> = ({
  host,
  device,
  isControlActive,
  isVisible,
}) => {
  // Local state
  const [taskInput, setTaskInput] = useState('');
  const [isAnalysisExpanded, setIsAnalysisExpanded] = useState<boolean>(false);
  const [useCacheEnabled, setUseCacheEnabled] = useState(true);
  const [debugMode, setDebugMode] = useState(false);

  // AI Agent hook
  const {
    isExecuting: isAIExecuting,
    currentPlan: aiPlan,
    taskResult,
    executionSummary,
    executeTask: executeAITask,
    // Direct access to computed values
    currentStep,
    progressPercentage,
    isPlanFeasible,
    // Processed data for UI
    processedSteps
  } = useAI({
    host,
    device,
    mode: 'real-time'
  });

  // Reset local state when new execution starts (simple reset)
  useEffect(() => {
    if (isAIExecuting && !aiPlan) {
      setIsAnalysisExpanded(false);
    }
  }, [isAIExecuting, aiPlan]);

  // Don't render if not visible
  if (!isVisible) return null;

  return (
    <Box
      sx={{
        position: 'absolute',
        top: '50%',
        right: 16,
        transform: 'translateY(-50%)',
        zIndex: getZIndex('MODAL_CONTENT'),
        pointerEvents: 'auto',
        width: '380px',
        backgroundColor: 'rgba(0,0,0,0.85)',
        borderRadius: 1,
        border: '1px solid rgba(255,255,255,0.2)',
        backdropFilter: 'blur(10px)',
      }}
    >
      <Box sx={{ p: 1 }}>
        {/* Header */}
        <Typography
          variant="h6"
          sx={{
            color: '#ffffff',
            mb: 1,
            display: 'flex',
            alignItems: 'center',
            gap: 1,
          }}
        >
          <AIIcon />
          AI Agent
          {isAIExecuting && (
            <Typography variant="caption" sx={{ color: '#2196f3', ml: 1 }}>
              Progress: {progressPercentage}%
            </Typography>
          )}
          {aiPlan && !isPlanFeasible && (
            <Box sx={{ color: '#f44336', display: 'flex', alignItems: 'center', ml: 1 }}>
              ✕
            </Box>
          )}
        </Typography>

        {/* Task Input */}
        <Box sx={{ display: 'flex', gap: 1, alignItems: 'flex-start', mb: 1 }}>
          <TextField
            size="small"
            placeholder="Enter task (e.g., 'go to live and zap 10 times')"
            value={taskInput}
            onChange={(e) => setTaskInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                executeAITask(taskInput, 'horizon_android_mobile', useCacheEnabled, debugMode);
              }
            }}
            disabled={isAIExecuting}
            sx={{
              flex: 1,
              '& .MuiOutlinedInput-root': {
                backgroundColor: 'rgba(0, 0, 0, 0.7)',
                '& fieldset': {
                  borderColor: '#444',
                },
                '&:hover fieldset': {
                  borderColor: '#666',
                },
                '&.Mui-focused fieldset': {
                  borderColor: '#2196f3',
                },
              },
              '& .MuiInputBase-input': {
                color: '#ffffff',
                '&::placeholder': {
                  color: '#888',
                  opacity: 1,
                },
              },
            }}
          />
          <Button
            variant="contained"
            size="small"
            onClick={() => executeAITask(taskInput, 'horizon_android_mobile', useCacheEnabled, debugMode)}
            disabled={!taskInput.trim() || isAIExecuting || !isControlActive}
            startIcon={isAIExecuting ? <CircularProgress size={16} sx={{ color: '#fff' }} /> : undefined}
            sx={{
              backgroundColor: isAIExecuting ? '#1976d2' : '#2196f3',
              color: '#ffffff',
              minWidth: '80px',
              '&:hover': {
                backgroundColor: '#1976d2',
              },
              '&.Mui-disabled': {
                backgroundColor: '#444',
                color: '#888',
              },
            }}
          >
            {isAIExecuting ? 'Executing...' : 'Execute'}
          </Button>
        </Box>

        {/* Cache Controls */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1 }}>
          <FormControlLabel
            control={
              <Checkbox
                checked={useCacheEnabled}
                onChange={(e) => setUseCacheEnabled(e.target.checked)}
                size="small"
                sx={{
                  color: '#888',
                  '&.Mui-checked': {
                    color: '#2196f3',
                  },
                }}
              />
            }
            label={
              <Typography variant="caption" sx={{ color: '#aaa' }}>
                Use Cache
              </Typography>
            }
            sx={{ margin: 0 }}
          />
          <FormControlLabel
            control={
              <Checkbox
                checked={debugMode}
                onChange={(e) => setDebugMode(e.target.checked)}
                size="small"
                sx={{
                  color: '#888',
                  '&.Mui-checked': {
                    color: '#ff9800',
                  },
                }}
              />
            }
            label={
              <Typography variant="caption" sx={{ color: '#aaa' }}>
                Debug Mode
              </Typography>
            }
            sx={{ margin: 0 }}
          />
          {!useCacheEnabled && (
            <Typography variant="caption" sx={{ color: '#ff9800', ml: 1 }}>
              (Fresh generation)
            </Typography>
          )}
          {debugMode && (
            <Typography variant="caption" sx={{ color: '#ff9800', ml: 1 }}>
              (No storage)
            </Typography>
          )}
        </Box>

        {/* AI Plan Display */}
        {(aiPlan || isAIExecuting) && (
          <Box
            key={aiPlan?.id || `executing-${isAIExecuting}`} // Force re-render on plan change
            sx={{
              mt: 1,
              p: 1,
              backgroundColor: 'rgba(0, 0, 0, 0.8)',
              borderRadius: 1,
              border: `1px solid ${isPlanFeasible ? '#444' : '#f44336'}`,
              maxHeight: '400px',
              overflowY: 'auto',
            }}
          >
            {/* Show current step when executing but no plan yet */}
            {isAIExecuting && !aiPlan && (
              <Box sx={{ p: 2, textAlign: 'center' }}>
                <CircularProgress size={20} sx={{ color: '#2196f3', mb: 1 }} />
                <Typography variant="body2" sx={{ color: '#2196f3' }}>
                  {currentStep || 'Starting AI...'}
                </Typography>
              </Box>
            )}

            {/* PHASE 1: Analysis Display (Always show first when available) */}
            {aiPlan && aiPlan.analysis && (
              <Box sx={{ mb: 0.5 }}>
                <Box 
                  sx={{ 
                    display: 'flex', 
                    alignItems: 'center', 
                    cursor: 'pointer',
                    '&:hover': { backgroundColor: 'rgba(255,255,255,0.05)' },
                    borderRadius: 0.5,
                    p: 0.5,
                    mb: 0.5
                  }}
                  onClick={() => setIsAnalysisExpanded(!isAnalysisExpanded)}
                >
                  <Typography variant="subtitle2" sx={{ 
                    color: isPlanFeasible ? '#4caf50' : '#f44336', 
                    flex: 1,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 1
                  }}>
                    {isPlanFeasible ? '✅' : '❌'} Task Analysis
                    {!isPlanFeasible && (
                      <Typography variant="caption" sx={{ color: '#f44336', ml: 0 }}>
                        (Not Feasible)
                      </Typography>
                    )}
                  </Typography>
                  <IconButton 
                    size="small" 
                    sx={{ color: '#aaa', p: 0.25 }}
                    aria-label={isAnalysisExpanded ? 'Collapse analysis' : 'Expand analysis'}
                  >
                    {isAnalysisExpanded ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
                  </IconButton>
                </Box>
                
                {isAnalysisExpanded && (
                  <Box
                    sx={{
                      p: 1,
                      backgroundColor: !isPlanFeasible ? 'rgba(244,67,54,0.1)' : 'rgba(76,175,80,0.1)',
                      borderRadius: 0.5,
                      border: !isPlanFeasible ? '1px solid rgba(244,67,54,0.3)' : '1px solid rgba(76,175,80,0.3)',
                      mb: 1
                    }}
                  >
                    <Typography variant="body2" sx={{ color: !isPlanFeasible ? '#ffffff' : '#cccccc' }}>
                      {aiPlan.analysis}
                    </Typography>
                  </Box>
                )}
              </Box>
            )}

            {/* Non-feasible task message */}
            {aiPlan && !isPlanFeasible && (
              <Box sx={{ mt: 0.5, mb: 1 }}>
                <Typography variant="body2" sx={{ 
                  color: '#f44336',
                  fontWeight: 'bold',
                  textAlign: 'center',
                  p: 1,
                  backgroundColor: 'rgba(244,67,54,0.1)',
                  borderRadius: 0.5,
                  border: '1px solid rgba(244,67,54,0.3)'
                }}>
                  ❌ Task not feasible
                </Typography>
              </Box>
            )}

            {/* Task Execution Status Header - Only for feasible plans */}
            {aiPlan && isPlanFeasible && (
              <Box sx={{ mt: 0.5, mb: 0.5 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <Typography variant="caption" sx={{ color: '#aaa' }}>
                    Task Execution:
                  </Typography>
                  {taskResult && !isAIExecuting && (
                    <Typography variant="caption" sx={{ 
                      color: taskResult.success ? '#4caf50' : '#f44336',
                      fontWeight: 'bold'
                    }}>
                      {taskResult.success ? '🎉 Success' : '⚠️ Failed'}
                    </Typography>
                  )}
                </Box>
              </Box>
            )}

            {/* PHASE 2: Plan Steps Display (Only for feasible plans) */}
            {aiPlan && isPlanFeasible && aiPlan.steps && aiPlan.steps.length > 0 && (
              <>
                <Box sx={{ mt: 0.5 }}>
                  {processedSteps.map((step: any, index: number) => {
                    let statusIcon, bgColor, borderColor;
                    if (step.status === 'completed') {
                      statusIcon = <Box sx={{ width: 12, height: 12, borderRadius: '50%', backgroundColor: '#4caf50' }} />;
                      bgColor = 'rgba(76,175,80,0.1)';
                      borderColor = 'rgba(76,175,80,0.3)';
                    } else if (step.status === 'failed') {
                      statusIcon = <Box sx={{ width: 12, height: 12, borderRadius: '50%', backgroundColor: '#f44336' }} />;
                      bgColor = 'rgba(244,67,54,0.1)';
                      borderColor = 'rgba(244,67,54,0.3)';
                    } else if (step.status === 'current') {
                      statusIcon = <CircularProgress size={12} sx={{ color: '#2196f3' }} />;
                      bgColor = 'rgba(33,150,243,0.1)';
                      borderColor = 'rgba(33,150,243,0.3)';
                    } else {
                      statusIcon = <Box sx={{ width: 12, height: 12, borderRadius: '50%', backgroundColor: '#666', border: '1px solid #888' }} />;
                      bgColor = 'rgba(255,255,255,0.05)';
                      borderColor = 'transparent';
                    }
                    
                    return (
                      <Box
                        key={`${aiPlan?.id || 'current'}-step-${step.stepNumber}-${index}`}
                        sx={{
                          mb: 1,
                          p: 1,
                          backgroundColor: bgColor,
                          borderRadius: 0.5,
                          border: `1px solid ${borderColor}`,
                        }}
                      >
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                          {statusIcon}
                          <Typography variant="caption" sx={{ color: '#fff', fontWeight: 'bold' }}>
                            {step.stepNumber}. {step.description}
                            {step.duration && ` (${step.duration.toFixed(1)}s)`}
                          </Typography>
                        </Box>
                        <Typography variant="caption" sx={{ color: '#aaa', display: 'block', ml: 2 }}>
                          {step.type && `[${step.type}] `}{step.command}
                          {step.params && Object.keys(step.params).length > 0 && ` | ${JSON.stringify(step.params)}`}
                        </Typography>
                      </Box>
                    );
                  })}
                </Box>

                {/* PHASE 3: Execution Summary (Show during/after execution) */}
                {(isAIExecuting || executionSummary || taskResult) && (
                  <Box sx={{ mt: 1, p: 1, backgroundColor: 'rgba(255,255,255,0.05)', borderRadius: 0.5 }}>
                    
                    {/* Progress Bar */}
                    <Box sx={{ mb: 1 }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                        <Typography variant="caption" sx={{ color: '#fff' }}>
                          Progress: {progressPercentage.toFixed(0)}%
                        </Typography>
                        <Typography variant="caption" sx={{ color: '#aaa' }}>
                          {executionSummary ? `${executionSummary.completedSteps}/${executionSummary.totalSteps}` : `${Math.round(progressPercentage / 100 * (aiPlan.steps?.length || 0))}/${aiPlan.steps?.length || 0}`} steps
                        </Typography>
                      </Box>
                      <Box sx={{ 
                        width: '100%', 
                        height: 4, 
                        backgroundColor: 'rgba(255,255,255,0.1)', 
                        borderRadius: 2,
                        overflow: 'hidden'
                      }}>
                        <Box sx={{ 
                          width: `${progressPercentage}%`, 
                          height: '100%', 
                          backgroundColor: taskResult?.success === false ? '#f44336' : '#4caf50',
                          transition: 'width 0.3s ease'
                        }} />
                      </Box>
                    </Box>

                    {/* Current Status */}
                    {isAIExecuting && (
                      <Typography variant="caption" sx={{ color: '#2196f3', display: 'block', mb: 1 }}>
                        🔄 {currentStep}
                      </Typography>
                    )}

                    {/* Execution Summary */}
                    {executionSummary && (
                      <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mt: 1 }}>
                        <Typography variant="caption" sx={{
                          color: '#4caf50',
                          backgroundColor: 'rgba(76,175,80,0.1)',
                          px: 1, py: 0.5, borderRadius: 0.5,
                        }}>
                          ✅ {executionSummary.completedSteps} completed
                        </Typography>
                        {executionSummary.failedSteps > 0 && (
                          <Typography variant="caption" sx={{
                            color: '#f44336',
                            backgroundColor: 'rgba(244,67,54,0.1)',
                            px: 1, py: 0.5, borderRadius: 0.5,
                          }}>
                            ❌ {executionSummary.failedSteps} failed
                          </Typography>
                        )}
                        <Typography variant="caption" sx={{
                          color: '#2196f3',
                          backgroundColor: 'rgba(33,150,243,0.1)',
                          px: 1, py: 0.5, borderRadius: 0.5,
                        }}>
                          ⏱️ {executionSummary.totalDuration.toFixed(1)}s total
                        </Typography>
                      </Box>
                    )}

                  </Box>
                )}

              </>
            )}
          </Box>
        )}
      </Box>
    </Box>
  );
};
