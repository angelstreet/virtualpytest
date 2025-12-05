import React from 'react';
import { Box, Typography, IconButton, LinearProgress, Divider, Stack } from '@mui/material';
import { 
  Close as CloseIcon, 
  SmartToy as RobotIcon,
  CheckCircleOutline,
  RadioButtonUnchecked,
  ErrorOutline
} from '@mui/icons-material';
import { useAIContext } from '../../../contexts/AIContext';

export const AgentPilotPanel: React.FC = () => {
  const { activeTask, isProcessing, executionSteps, togglePilot, isConnected } = useAIContext();

  const getStepIcon = (status: string) => {
    switch (status) {
      case 'done':
        return <CheckCircleOutline color="success" fontSize="small" />;
      case 'active':
        return <RadioButtonUnchecked color="primary" fontSize="small" sx={{ animation: 'pulse 1s infinite' }} />;
      case 'error':
        return <ErrorOutline color="error" fontSize="small" />;
      default:
        return <RadioButtonUnchecked color="disabled" fontSize="small" />;
    }
  };

  return (
    <Box
      sx={{
        position: 'fixed',
        top: 64,
        right: 0,
        bottom: 0,
        width: 320,
        bgcolor: 'background.paper',
        borderLeft: '1px solid',
        borderColor: 'divider',
        boxShadow: '-4px 0 20px rgba(0,0,0,0.1)',
        zIndex: 1200,
        display: 'flex',
        flexDirection: 'column',
        '@keyframes pulse': {
          '0%, 100%': { opacity: 1 },
          '50%': { opacity: 0.5 },
        },
      }}
    >
      {/* Header */}
      <Box sx={{ p: 2, display: 'flex', alignItems: 'center', borderBottom: '1px solid', borderColor: 'divider', bgcolor: 'action.hover' }}>
        <RobotIcon sx={{ mr: 1, color: isConnected ? 'success.main' : 'text.disabled' }} />
        <Typography variant="subtitle1" fontWeight="bold" sx={{ flex: 1 }}>
          Agent Pilot
        </Typography>
        <IconButton size="small" onClick={togglePilot}>
          <CloseIcon fontSize="small" />
        </IconButton>
      </Box>

      {/* Active Task Status */}
      <Box sx={{ p: 2 }}>
        <Typography variant="caption" color="text.secondary" fontWeight="bold" sx={{ textTransform: 'uppercase' }}>
          Current Mission
        </Typography>
        <Typography variant="body2" sx={{ mt: 0.5, mb: 2, fontWeight: 500 }}>
          {activeTask || "Waiting for instructions..."}
        </Typography>
        
        {isProcessing && (
          <Box sx={{ mb: 2 }}>
             <LinearProgress sx={{ borderRadius: 1, height: 6 }} />
             <Typography variant="caption" sx={{ mt: 0.5, display: 'block', textAlign: 'right', color: 'primary.main' }}>
               Processing...
             </Typography>
          </Box>
        )}
      </Box>

      <Divider />

      {/* Execution Steps - Now Dynamic */}
      <Box sx={{ flex: 1, overflowY: 'auto', p: 2 }}>
         <Stack spacing={2}>
            {executionSteps.length === 0 && !activeTask && (
              <Typography variant="caption" color="text.secondary" sx={{ textAlign: 'center', py: 4 }}>
                Use Cmd+K to start a task
              </Typography>
            )}
            
            {executionSteps.map((step) => (
              <Box key={step.id} sx={{ display: 'flex', gap: 1.5 }}>
                {getStepIcon(step.status)}
                <Box>
                  <Typography variant="body2">{step.label}</Typography>
                  {step.detail && (
                    <Typography variant="caption" color="text.secondary">
                      {step.detail}
                    </Typography>
                  )}
                </Box>
              </Box>
            ))}
         </Stack>
      </Box>
    </Box>
  );
};
