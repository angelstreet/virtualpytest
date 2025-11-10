import React, { useEffect, useState } from 'react';
import { 
  Box, 
  IconButton, 
  TextField, 
  Button, 
  Typography, 
  CircularProgress,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Paper,
  Divider,
  Stack,
  Chip,
} from '@mui/material';
import { 
  SmartToy, 
  Send, 
  CheckCircle, 
  Error,
  ExpandMore as ExpandMoreIcon,
  Build as ToolIcon,
  Psychology as ReasoningIcon,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';

import { useMCPTask } from '../../hooks/mcp/useMCPTask';
import { useHostManager } from '../../hooks/useHostManager';
import { Device } from '../../types/common/Host_Types';

export const MCPTaskInput: React.FC = () => {
  const navigate = useNavigate();
  const { selectedHost, selectedDeviceId } = useHostManager();

  // State for expandable sections - COLLAPSED BY DEFAULT
  const [toolsExpanded, setToolsExpanded] = useState(false);
  const [reasoningExpanded, setReasoningExpanded] = useState(false);

  // Get the device_model from the selected device
  const selectedDevice = selectedHost?.devices?.find((d: Device) => d.device_id === selectedDeviceId);
  const device_model = selectedDevice?.device_model || 'android_mobile';

  const {
    // Panel state
    isPanelVisible,
    togglePanel,

    // Task state
    currentTask,
    setCurrentTask,

    // Execution state
    isExecuting,
    lastResponse,

    // Actions
    executeTask,
    clearResponse,
  } = useMCPTask({
    device_id: selectedDeviceId || 'device1',
    host_name: selectedHost?.host_name || 'sunri-pi1',
    userinterface_name: 'mobile_test', // You can make this dynamic if needed
    device_model,
    team_id: 'team_1',
  });

  // Handle navigation based on response
  useEffect(() => {
    if (lastResponse?.success && lastResponse.tool_result?.redirect_url) {
      const redirectUrl = lastResponse.tool_result.redirect_url;
      console.log(`[MCPTaskInput] Navigating to: ${redirectUrl}`);

      // Navigate after a short delay to show the success message
      setTimeout(() => {
        navigate(redirectUrl);
      }, 1000);
    }
  }, [lastResponse, navigate]);

  // Handle Enter key press
  const handleKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === 'Enter' && !event.shiftKey && !isExecuting) {
      event.preventDefault();
      executeTask();
    }
  };

  return (
    <Box
      sx={{
        position: 'fixed',
        top: '50%',
        left: 0,
        transform: 'translateY(-50%)',
        zIndex: 1000020, // Higher than timeline controls
        pointerEvents: 'auto',
        display: 'flex',
        flexDirection: 'row',
        alignItems: 'center',
      }}
    >
      {/* MCP Robot Icon - always visible on left edge */}
      <IconButton
        size="medium"
        onClick={togglePanel}
        sx={{
          color: '#ffffff',
          backgroundColor: 'rgba(76, 175, 80, 0.2)',
          border: '1px solid rgba(76, 175, 80, 0.3)',
          borderRadius: '0 8px 8px 0',
          borderLeft: 'none',
          ml: 0,
          mr: isPanelVisible ? 1 : 0,
          '&:hover': {
            backgroundColor: 'rgba(76, 175, 80, 0.3)',
            borderColor: 'rgba(76, 175, 80, 0.5)',
          },
        }}
        title="MCP Task Assistant"
      >
        <SmartToy />
      </IconButton>

      {/* Sliding Task Panel - WIDER */}
      <Box
        sx={{
          width: isPanelVisible ? '600px' : '0px',
          height: isPanelVisible ? 'auto' : '0px',
          maxHeight: isPanelVisible ? '85vh' : '0px',
          overflow: isPanelVisible ? 'auto' : 'hidden',
          transition: 'width 300ms ease-in-out, height 300ms ease-in-out',
          backgroundColor: isPanelVisible ? 'rgba(0,0,0,0.85)' : 'transparent',
          borderRadius: isPanelVisible ? 1 : 0,
          border: isPanelVisible ? '1px solid rgba(76, 175, 80, 0.3)' : 'none',
        }}
      >
        {isPanelVisible && (
          <Box sx={{ p: 2, width: '600px' }}>
            {/* Header */}
            <Typography
              variant="subtitle2"
              sx={{
                color: '#4caf50',
                mb: 1,
                fontWeight: 'bold',
                fontSize: '0.9rem',
              }}
            >
              MCP Task Assistant
            </Typography>

            {/* Input field and send button */}
            <Box sx={{ display: 'flex', gap: 1, alignItems: 'flex-start', mb: 1 }}>
              <TextField
                size="small"
                placeholder="Enter task (e.g., 'list userinterface')"
                value={currentTask}
                onChange={(e) => setCurrentTask(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={isExecuting}
                inputProps={{
                  maxLength: 200,
                  autoComplete: 'off',
                  autoCorrect: 'off',
                  autoCapitalize: 'off',
                  spellCheck: false,
                }}
                sx={{
                  flex: 1,
                  '& .MuiOutlinedInput-root': {
                    backgroundColor: 'rgba(0, 0, 0, 0.7)',
                    '& fieldset': {
                      borderColor: '#4caf50',
                    },
                    '&:hover fieldset': {
                      borderColor: '#66bb6a',
                    },
                    '&.Mui-focused fieldset': {
                      borderColor: '#4caf50',
                    },
                  },
                  '& .MuiInputBase-input': {
                    color: '#ffffff',
                    fontSize: '0.875rem',
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
                onClick={executeTask}
                disabled={!currentTask.trim() || isExecuting}
                sx={{
                  backgroundColor: '#4caf50',
                  color: '#ffffff',
                  minWidth: '60px',
                  '&:hover': {
                    backgroundColor: '#388e3c',
                  },
                  '&.Mui-disabled': {
                    backgroundColor: '#444',
                    color: '#888',
                  },
                }}
              >
                {isExecuting ? (
                  <CircularProgress size={16} sx={{ color: '#888' }} />
                ) : (
                  <Send sx={{ fontSize: 16 }} />
                )}
              </Button>
            </Box>

            {/* Response Display - NEW: Useful Result First, Then Expandable Boxes */}
            {lastResponse && (
              <Box
                sx={{
                  mt: 1,
                  p: 1.5,
                  backgroundColor: 'rgba(0, 0, 0, 0.8)',
                  borderRadius: 1,
                  border: `1px solid ${lastResponse.success ? '#4caf50' : '#f44336'}`,
                }}
              >
                {/* Response Header */}
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  {lastResponse.success ? (
                    <CheckCircle sx={{ color: '#4caf50', fontSize: 16, mr: 1 }} />
                  ) : (
                    <Error sx={{ color: '#f44336', fontSize: 16, mr: 1 }} />
                  )}
                  <Typography
                    variant="caption"
                    sx={{
                      color: lastResponse.success ? '#4caf50' : '#f44336',
                      fontWeight: 'bold',
                      fontSize: '0.75rem',
                    }}
                  >
                    {lastResponse.success ? 'SUCCESS' : 'ERROR'}
                  </Typography>
                </Box>

                {/* Error Message (if failed) */}
                {!lastResponse.success && (
                  <Typography
                    variant="body2"
                    sx={{
                      color: '#ffffff',
                      fontSize: '0.75rem',
                      lineHeight: 1.3,
                      mb: 1,
                      wordWrap: 'break-word',
                      overflowWrap: 'break-word',
                    }}
                  >
                    {lastResponse.error || 'Unknown error occurred'}
                  </Typography>
                )}

                {/* SUCCESS: Show Useful Result First */}
                {lastResponse.success && (
                  <Box
                    sx={{
                      mb: 2,
                      p: 1.5,
                      bgcolor: 'rgba(76, 175, 80, 0.1)',
                      borderRadius: 1,
                      border: '1px solid rgba(76, 175, 80, 0.3)',
                    }}
                  >
                    <Typography
                      sx={{
                        fontSize: '0.75rem',
                        lineHeight: 1.6,
                        color: '#e0e0e0',
                        whiteSpace: 'pre-wrap',
                        wordWrap: 'break-word',
                        overflowWrap: 'break-word',
                        overflowX: 'hidden',
                      }}
                    >
                      {lastResponse.result || 'Task completed'}
                    </Typography>
                  </Box>
                )}

                {/* Tools Section - COLLAPSED BY DEFAULT */}
                {lastResponse.success && lastResponse.execution_log && lastResponse.execution_log.length > 0 && (
                  <Accordion 
                    expanded={toolsExpanded} 
                    onChange={() => setToolsExpanded(!toolsExpanded)}
                    sx={{
                      mt: 1,
                      border: 1,
                      borderColor: 'divider',
                      boxShadow: 'none',
                      bgcolor: 'transparent',
                      '&:before': { display: 'none' },
                    }}
                  >
                    <AccordionSummary
                      expandIcon={<ExpandMoreIcon sx={{ color: '#4caf50' }} />}
                      sx={{
                        bgcolor: 'rgba(76, 175, 80, 0.1)',
                        minHeight: '36px',
                        '&.Mui-expanded': {
                          minHeight: '36px',
                        },
                        '& .MuiAccordionSummary-content': {
                          my: 0.5,
                        },
                        '&:hover': {
                          bgcolor: 'rgba(76, 175, 80, 0.2)',
                        },
                      }}
                    >
                      <Stack direction="row" spacing={1} alignItems="center">
                        <ToolIcon sx={{ color: '#4caf50', fontSize: 16 }} />
                        <Typography sx={{ fontSize: '0.8rem', fontWeight: 600, color: '#4caf50' }}>
                          Tools Used
                        </Typography>
                        <Chip 
                          label={lastResponse.execution_log.length} 
                          size="small" 
                          sx={{ 
                            height: 18,
                            fontSize: '0.65rem',
                            bgcolor: '#4caf50',
                            color: '#000',
                          }}
                        />
                      </Stack>
                    </AccordionSummary>
                    <AccordionDetails sx={{ p: 1 }}>
                      <Stack spacing={1}>
                        {lastResponse.execution_log.map((toolCall: any, index: number) => (
                          <Paper
                            key={index}
                            elevation={0}
                            sx={{
                              p: 1.5,
                              border: 1,
                              borderColor: 'rgba(76, 175, 80, 0.3)',
                              borderRadius: 1,
                              bgcolor: 'rgba(0, 0, 0, 0.5)',
                            }}
                          >
                            <Stack spacing={1}>
                              {/* Tool Name */}
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                <Typography sx={{ 
                                  fontSize: '0.75rem', 
                                  fontWeight: 600, 
                                  color: '#4caf50',
                                  wordWrap: 'break-word',
                                  overflowWrap: 'break-word',
                                }}>
                                  {index + 1}. {toolCall.tool}
                                </Typography>
                              </Box>

                              <Divider sx={{ borderColor: 'rgba(76, 175, 80, 0.2)' }} />

                              {/* Arguments */}
                              {toolCall.arguments && Object.keys(toolCall.arguments).length > 0 && (
                                <Box>
                                  <Typography sx={{ fontSize: '0.7rem', fontWeight: 600, color: '#888', mb: 0.5 }}>
                                    Arguments:
                                  </Typography>
                                  <Paper
                                    elevation={0}
                                    sx={{
                                      p: 1,
                                      bgcolor: 'rgba(0, 0, 0, 0.7)',
                                      border: 1,
                                      borderColor: 'rgba(76, 175, 80, 0.2)',
                                      borderRadius: 1,
                                      fontFamily: 'monospace',
                                      fontSize: '0.65rem',
                                      maxHeight: '150px',
                                      overflowY: 'auto',
                                      overflowX: 'hidden',
                                      wordWrap: 'break-word',
                                    }}
                                  >
                                    <pre style={{ 
                                      margin: 0, 
                                      whiteSpace: 'pre-wrap', 
                                      wordBreak: 'break-word', 
                                      color: '#e0e0e0',
                                      overflowWrap: 'break-word',
                                    }}>
                                      {JSON.stringify(toolCall.arguments, null, 2)}
                                    </pre>
                                  </Paper>
                                </Box>
                              )}

                              {/* Result */}
                              {toolCall.result && (
                                <Box>
                                  <Typography sx={{ fontSize: '0.7rem', fontWeight: 600, color: '#888', mb: 0.5 }}>
                                    Result:
                                  </Typography>
                                  <Paper
                                    elevation={0}
                                    sx={{
                                      p: 1,
                                      bgcolor: 'rgba(0, 0, 0, 0.7)',
                                      border: 1,
                                      borderColor: 'rgba(76, 175, 80, 0.2)',
                                      borderRadius: 1,
                                      fontFamily: 'monospace',
                                      fontSize: '0.65rem',
                                      maxHeight: '150px',
                                      overflowY: 'auto',
                                      overflowX: 'hidden',
                                      wordWrap: 'break-word',
                                    }}
                                  >
                                    <pre style={{ 
                                      margin: 0, 
                                      whiteSpace: 'pre-wrap', 
                                      wordBreak: 'break-word', 
                                      color: '#e0e0e0',
                                      overflowWrap: 'break-word',
                                    }}>
                                      {typeof toolCall.result === 'string' 
                                        ? toolCall.result 
                                        : JSON.stringify(toolCall.result, null, 2)}
                                    </pre>
                                  </Paper>
                                </Box>
                              )}
                            </Stack>
                          </Paper>
                        ))}
                      </Stack>
                    </AccordionDetails>
                  </Accordion>
                )}

                {/* Reasoning Section - COLLAPSED BY DEFAULT */}
                {lastResponse.success && lastResponse.ai_analysis && (
                  <Accordion 
                    expanded={reasoningExpanded} 
                    onChange={() => setReasoningExpanded(!reasoningExpanded)}
                    sx={{
                      mt: 1,
                      border: 1,
                      borderColor: 'divider',
                      boxShadow: 'none',
                      bgcolor: 'transparent',
                      '&:before': { display: 'none' },
                    }}
                  >
                    <AccordionSummary
                      expandIcon={<ExpandMoreIcon sx={{ color: '#66bb6a' }} />}
                      sx={{
                        bgcolor: 'rgba(102, 187, 106, 0.1)',
                        minHeight: '36px',
                        '&.Mui-expanded': {
                          minHeight: '36px',
                        },
                        '& .MuiAccordionSummary-content': {
                          my: 0.5,
                        },
                        '&:hover': {
                          bgcolor: 'rgba(102, 187, 106, 0.2)',
                        },
                      }}
                    >
                      <Stack direction="row" spacing={1} alignItems="center">
                        <ReasoningIcon sx={{ color: '#66bb6a', fontSize: 16 }} />
                        <Typography sx={{ fontSize: '0.8rem', fontWeight: 600, color: '#66bb6a' }}>
                          AI Reasoning
                        </Typography>
                      </Stack>
                    </AccordionSummary>
                    <AccordionDetails sx={{ p: 1 }}>
                      <Paper
                        elevation={0}
                        sx={{
                          p: 1.5,
                          border: 1,
                          borderColor: 'rgba(102, 187, 106, 0.3)',
                          borderRadius: 1,
                          bgcolor: 'rgba(0, 0, 0, 0.5)',
                        }}
                      >
                        <Typography 
                          sx={{ 
                            whiteSpace: 'pre-wrap',
                            fontFamily: 'monospace',
                            fontSize: '0.7rem',
                            lineHeight: 1.6,
                            color: '#e0e0e0',
                            wordWrap: 'break-word',
                            overflowWrap: 'break-word',
                            overflowX: 'hidden',
                          }}
                        >
                          {lastResponse.ai_analysis}
                        </Typography>
                      </Paper>
                    </AccordionDetails>
                  </Accordion>
                )}

                {/* Clear button */}
                <Button
                  size="small"
                  onClick={clearResponse}
                  sx={{
                    mt: 1,
                    color: '#888',
                    fontSize: '0.7rem',
                    minHeight: 'auto',
                    padding: '2px 8px',
                    '&:hover': {
                      color: '#fff',
                      backgroundColor: 'rgba(255,255,255,0.1)',
                    },
                  }}
                >
                  Clear
                </Button>
              </Box>
            )}

            {/* Quick Examples */}
            {!lastResponse && !isExecuting && (
              <Box sx={{ mt: 1 }}>
                <Typography
                  variant="caption"
                  sx={{
                    color: '#888',
                    fontSize: '0.7rem',
                    display: 'block',
                    mb: 0.5,
                  }}
                >
                  Quick examples:
                </Typography>
                {['Go to rec page', 'Go to dashboard', 'Execute remote command'].map((example) => (
                  <Button
                    key={example}
                    size="small"
                    onClick={() => setCurrentTask(example)}
                    sx={{
                      color: '#4caf50',
                      fontSize: '0.7rem',
                      minHeight: 'auto',
                      padding: '2px 4px',
                      mr: 0.5,
                      mb: 0.5,
                      textTransform: 'none',
                      '&:hover': {
                        backgroundColor: 'rgba(76, 175, 80, 0.1)',
                      },
                    }}
                  >
                    {example}
                  </Button>
                ))}
              </Box>
            )}
          </Box>
        )}
      </Box>
    </Box>
  );
};
