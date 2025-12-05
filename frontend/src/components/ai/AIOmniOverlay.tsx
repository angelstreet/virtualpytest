import React from 'react';
import { Box, Fab, Tooltip } from '@mui/material';
import { SmartToy as RobotIcon } from '@mui/icons-material';
import { AICommandBar } from './AICommandBar';
import { AgentPilotPanel } from './panels/AgentPilotPanel';
import { LogTerminalPanel } from './panels/LogTerminalPanel';
import { useAIContext } from '../../contexts/AIContext';

export const AIOmniOverlay: React.FC = () => {
  const { isPilotOpen, isLogsOpen, openCommand } = useAIContext();

  return (
    <Box sx={{ position: 'fixed', inset: 0, zIndex: 9999, pointerEvents: 'none' }}>
      
      {/* 1. Floating Command Bar (Always mounted, visible via internal state) */}
      <Box sx={{ pointerEvents: 'auto' }}>
        <AICommandBar />
      </Box>

      {/* Trigger Button (Bottom Left - Discreet) */}
      <Box 
        sx={{ 
          position: 'fixed', 
          bottom: 24, 
          left: 24, 
          pointerEvents: 'auto',
          zIndex: 1000 
        }}
      >
        <Tooltip title="Ask AI Agent (Cmd+K)" placement="right">
            <Fab 
                color="primary" 
                size="medium"
                onClick={openCommand}
                sx={{ 
                    bgcolor: 'rgba(25, 118, 210, 0.9)',
                    backdropFilter: 'blur(4px)',
                    boxShadow: '0 4px 20px rgba(0,0,0,0.3)'
                }}
            >
                <RobotIcon />
            </Fab>
        </Tooltip>
      </Box>

      {/* 2. Right Panel (Agent Pilot) */}
      {isPilotOpen && (
        <Box sx={{ pointerEvents: 'auto' }}>
          <AgentPilotPanel />
        </Box>
      )}

      {/* 3. Bottom Panel (Logs) */}
      {isLogsOpen && (
        <Box sx={{ pointerEvents: 'auto' }}>
          <LogTerminalPanel />
        </Box>
      )}
      
    </Box>
  );
};

