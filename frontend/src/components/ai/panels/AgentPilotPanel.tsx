import React from 'react';
import { Box, Paper, Typography, IconButton, LinearProgress, Divider, Stack } from '@mui/material';
import { 
  Close as CloseIcon, 
  SmartToy as RobotIcon,
  CheckCircleOutline,
  RadioButtonUnchecked
} from '@mui/icons-material';
import { useAIContext } from '../../../contexts/AIContext';
import { motion } from 'framer-motion'; // Ensure framer-motion is installed or use standard CSS transition

export const AgentPilotPanel: React.FC = () => {
  const { activeTask, isProcessing, togglePilot } = useAIContext();

  return (
    <Box
      sx={{
        position: 'fixed',
        top: 64, // Below navbar
        right: 0,
        bottom: 0,
        width: 320,
        bgcolor: 'background.paper',
        borderLeft: '1px solid',
        borderColor: 'divider',
        boxShadow: '-4px 0 20px rgba(0,0,0,0.1)',
        zIndex: 1200,
        display: 'flex',
        flexDirection: 'column'
      }}
    >
      {/* Header */}
      <Box sx={{ p: 2, display: 'flex', alignItems: 'center', borderBottom: '1px solid', borderColor: 'divider', bgcolor: 'action.hover' }}>
        <RobotIcon sx={{ mr: 1, color: 'primary.main' }} />
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
               Thinking...
             </Typography>
          </Box>
        )}
      </Box>

      <Divider />

      {/* Steps / Activity Feed */}
      <Box sx={{ flex: 1, overflowY: 'auto', p: 2 }}>
         <Stack spacing={2}>
            {/* Placeholder Steps for demo */}
            {activeTask && (
                <>
                    <Box sx={{ display: 'flex', gap: 1.5 }}>
                        <CheckCircleOutline color="success" fontSize="small" />
                        <Box>
                            <Typography variant="body2">Interpret Command</Typography>
                            <Typography variant="caption" color="text.secondary">Parsed intent: Navigation</Typography>
                        </Box>
                    </Box>
                     <Box sx={{ display: 'flex', gap: 1.5 }}>
                        <RadioButtonUnchecked color="primary" fontSize="small" />
                        <Box>
                            <Typography variant="body2">Execute Action</Typography>
                            <Typography variant="caption" color="text.secondary">Pending...</Typography>
                        </Box>
                    </Box>
                </>
            )}
         </Stack>
      </Box>
    </Box>
  );
};

