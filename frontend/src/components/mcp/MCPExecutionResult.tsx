import React from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Stack,
  Chip,
  LinearProgress,
  Alert,
  IconButton,
  Collapse,
} from '@mui/material';
import {
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
  Close as CloseIcon,
  Info as InfoIcon,
} from '@mui/icons-material';

interface MCPExecutionResultProps {
  unifiedExecution: any;
  executionResult: any;
  isGenerating?: boolean;  // NEW: for MCP Proxy loading state
}

export const MCPExecutionResult: React.FC<MCPExecutionResultProps> = ({
  unifiedExecution,
  executionResult,
  isGenerating = false,  // NEW: MCP Proxy loading state
}) => {
  
  const [isVisible, setIsVisible] = React.useState(true);
  
  const { isExecuting, blockStates, result } = unifiedExecution.state;
  
  // NEW: Handle MCP Proxy format (executionResult from useMCPProxy)
  const isMCPProxyResult = executionResult && executionResult.tool_calls;
  
  // Don't show if:
  // 1. Still loading (no result yet)
  // 2. No execution has happened
  if (isGenerating && !executionResult) {
    return null;  // Hide while generating
  }
  
  if (!isExecuting && !isGenerating && blockStates.size === 0 && !executionResult) {
    return null;  // Hide if nothing happened
  }
  
  // Calculate progress
  const totalBlocks = blockStates.size;
  const completedBlocks = Array.from(blockStates.values()).filter(
    state => state.status === 'success' || state.status === 'failure'
  ).length;
  const progress = totalBlocks > 0 ? (completedBlocks / totalBlocks) * 100 : 0;
  
  // Determine result type
  let resultIcon = <InfoIcon />;
  let resultColor: 'info' | 'success' | 'error' | 'warning' = 'info';
  let resultText = 'Executing...';
  
  // NEW: Handle MCP Proxy results
  if (isMCPProxyResult && !isGenerating) {
    if (executionResult.success) {
      resultIcon = <SuccessIcon />;
      resultColor = 'success';
      resultText = executionResult.result?.message || 'MCP Tool Executed Successfully';
    } else {
      resultIcon = <ErrorIcon />;
      resultColor = 'error';
      resultText = executionResult.error || 'MCP Tool Execution Failed';
    }
  }
  // OLD: Handle test case execution results
  else if (!isExecuting && result) {
    if (result.result_type === 'success') {
      resultIcon = <SuccessIcon />;
      resultColor = 'success';
      resultText = 'Execution Completed Successfully';
    } else if (result.result_type === 'failure') {
      resultIcon = <WarningIcon />;
      resultColor = 'warning';
      resultText = 'Execution Completed with Failures';
    } else {
      resultIcon = <ErrorIcon />;
      resultColor = 'error';
      resultText = 'Execution Failed';
    }
  }
  
  return (
    <Collapse in={isVisible}>
      <Card
        sx={{
          border: 1,
          borderColor: 'divider',
          boxShadow: 'none',
          bgcolor: isExecuting ? 'action.hover' : 'background.paper',
        }}
      >
        <CardContent sx={{ p: { xs: 2, md: 2.5 }, '&:last-child': { pb: { xs: 2, md: 2.5 } } }}>
          {/* Header */}
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              mb: 2,
            }}
          >
            <Typography variant="h6" sx={{ fontSize: { xs: '1rem', md: '1.1rem' } }}>
              Execution Result
            </Typography>
            {!isExecuting && (
              <IconButton size="small" onClick={() => setIsVisible(false)}>
                <CloseIcon fontSize="small" />
              </IconButton>
            )}
          </Box>
          
          {/* Content */}
          <Stack spacing={2}>
            {/* Test Case Execution: Progress with blocks (only for non-MCP) */}
            {!isMCPProxyResult && isExecuting && blockStates.size > 0 && (
              <Box>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
                  <Typography variant="body2" color="text.secondary">
                    Progress
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {completedBlocks} / {totalBlocks} blocks
                  </Typography>
                </Box>
                <LinearProgress variant="determinate" value={progress} sx={{ height: 8, borderRadius: 1 }} />
              </Box>
            )}
            
            {/* Result Alert */}
            <Alert
              severity={resultColor}
              icon={resultIcon}
              sx={{
                '& .MuiAlert-message': {
                  width: '100%',
                },
              }}
            >
              <Stack spacing={1}>
                <Typography variant="body2" sx={{ fontWeight: 600 }}>
                  {resultText}
                </Typography>
                
                {/* NEW: MCP Tool Calls info */}
                {isMCPProxyResult && executionResult.tool_calls && (
                  <Typography variant="caption" color="text.secondary">
                    Tool used: {executionResult.tool_calls[0]?.tool}
                  </Typography>
                )}
                
                {/* Duration */}
                {result?.execution_time_ms !== undefined && (
                  <Typography variant="caption" color="text.secondary">
                    Duration: {result.execution_time_ms}ms ({(result.execution_time_ms / 1000).toFixed(2)}s)
                  </Typography>
                )}
                
                {/* Error message */}
                {(result?.error || executionResult?.error) && (
                  <Typography variant="body2" sx={{ mt: 1 }}>
                    Error: {result?.error || executionResult?.error}
                  </Typography>
                )}
                
                {/* Step count */}
                {result?.step_count !== undefined && (
                  <Typography variant="caption" color="text.secondary">
                    Steps executed: {result.step_count}
                  </Typography>
                )}
              </Stack>
            </Alert>
            
            {/* Block States (summary) - Only for test case execution */}
            {!isMCPProxyResult && blockStates.size > 0 && (
              <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap', gap: 1 }}>
                {Array.from(blockStates.entries()).map(([blockId, state]) => (
                  <Chip
                    key={blockId}
                    label={`Block ${blockId.substring(0, 8)}`}
                    size="small"
                    color={
                      state.status === 'success'
                        ? 'success'
                        : state.status === 'failure'
                        ? 'error'
                        : state.status === 'running'
                        ? 'primary'
                        : 'default'
                    }
                    variant={state.status === 'pending' ? 'outlined' : 'filled'}
                    sx={{
                      fontSize: { xs: '0.75rem', md: '0.7rem' },
                    }}
                  />
                ))}
              </Stack>
            )}
            
            {/* Report Link */}
            {result?.report_url && (
              <Box>
                <Typography
                  component="a"
                  href={result.report_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  sx={{
                    color: 'primary.main',
                    textDecoration: 'none',
                    fontSize: { xs: '0.9rem', md: '0.85rem' },
                    '&:hover': {
                      textDecoration: 'underline',
                    },
                  }}
                >
                  View Detailed Report →
                </Typography>
              </Box>
            )}
          </Stack>
        </CardContent>
      </Card>
    </Collapse>
  );
};

