import React from 'react';
import { Box, Fab, Tooltip } from '@mui/material';
import { AutoAwesome } from '@mui/icons-material';
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

      {/* Ask AI Button (Bottom Left) */}
      <Box 
        sx={{ 
          position: 'fixed', 
          bottom: 24, 
          left: 24, 
          pointerEvents: 'auto',
          zIndex: 1000 
        }}
      >
        <Tooltip title="Ask AI (Cmd+K)" placement="right">
            <Fab 
                size="medium"
                onClick={openCommand}
                sx={{ 
                    bgcolor: 'rgba(212, 175, 55, 0.95)',
                    backdropFilter: 'blur(8px)',
                    boxShadow: '0 4px 24px rgba(212, 175, 55, 0.35)',
                    transition: 'all 0.2s ease',
                    '&:hover': { 
                      bgcolor: '#B8860B',
                      boxShadow: '0 6px 28px rgba(212, 175, 55, 0.5)',
                      transform: 'scale(1.05)'
                    }
                }}
            >
                <AutoAwesome sx={{ color: '#1a1a1a', fontSize: 24 }} />
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

