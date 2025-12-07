import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Box, 
  Paper, 
  InputBase, 
  IconButton, 
  Chip,
  Fade,
  Backdrop,
  Menu,
  MenuItem,
  Typography
} from '@mui/material';
import { 
  AutoAwesome as SparkleIcon,
  KeyboardReturn as EnterIcon,
  KeyboardArrowDown as ArrowDownIcon
} from '@mui/icons-material';
import { useAIContext } from '../../contexts/AIContext';

// Available agents with agent-specific tips
const AVAILABLE_AGENTS = [
  { 
    id: 'ai-assistant', 
    nickname: 'Atlas', 
    description: 'General AI Assistant', 
    color: '#d4af37',
    tips: ['Go to dashboard', 'Show me test reports', 'What can you do?']
  },
  { 
    id: 'qa-web-manager', 
    nickname: 'Sherlock', 
    description: 'Web testing specialist', 
    color: '#4fc3f7',
    tips: ['Run web regression tests', 'Automate login flow', 'Check broken links']
  },
  { 
    id: 'qa-mobile-manager', 
    nickname: 'Scout', 
    description: 'Mobile testing specialist', 
    color: '#81c784',
    tips: ['Run smoke test on Pixel 5', 'Test app on iOS', 'Check device status']
  },
  { 
    id: 'qa-stb-manager', 
    nickname: 'Watcher', 
    description: 'STB testing specialist', 
    color: '#ba68c8',
    tips: ['Run STB zapping test', 'Check EPG loading', 'Test channel switch']
  },
  { 
    id: 'monitoring-manager', 
    nickname: 'Guardian', 
    description: 'Monitoring specialist', 
    color: '#ffb74d',
    tips: ['Show active alerts', 'Check system health', 'Run incident analysis']
  },
];

export const AICommandBar: React.FC = () => {
  const { isCommandOpen, closeCommand, selectedAgentId, setSelectedAgentId, sendMessage } = useAIContext();
  const [input, setInput] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);
  const chipRef = useRef<HTMLDivElement>(null);
  const [agentMenuOpen, setAgentMenuOpen] = useState(false);
  
  const selectedAgent = AVAILABLE_AGENTS.find(a => a.id === selectedAgentId) || AVAILABLE_AGENTS[0];

  // Focus input when opened
  useEffect(() => {
    if (isCommandOpen && inputRef.current) {
      setTimeout(() => inputRef.current?.focus(), 50);
    }
    // Close menu when command bar closes
    if (!isCommandOpen) {
      setAgentMenuOpen(false);
    }
  }, [isCommandOpen]);

  const handleSubmit = (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!input.trim()) return;

    const message = input.trim();
    
    // Send message directly via AIContext - executes in place without navigation
    sendMessage(message, selectedAgentId);
    
    // Clear input and close command bar
    setInput('');
    setAgentMenuOpen(false);
    closeCommand();
  };

  if (!isCommandOpen) return null;

  return (
    <>
      {/* Dimmed Background */}
      <Backdrop 
        open={isCommandOpen} 
        onClick={closeCommand}
        sx={{ zIndex: 9998, bgcolor: 'rgba(0,0,0,0.88)' }} 
      />

      {/* Floating Command Input */}
      <Fade in={isCommandOpen}>
        <Box
          sx={{
            position: 'fixed',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            width: '100%',
            maxWidth: '600px',
            zIndex: 9999,
            pointerEvents: 'auto'
          }}
        >
          <Paper
            elevation={24}
            component="form"
            onSubmit={handleSubmit}
            sx={{
              p: '2px 4px',
              display: 'flex',
              alignItems: 'center',
              width: '100%',
              bgcolor: 'background.paper',
              borderRadius: 3,
              border: '1px solid',
              borderColor: '#d4af37',
              boxShadow: '0 8px 32px rgba(0,0,0,0.2)',
              overflow: 'hidden'
            }}
          >
            <Box sx={{ p: 1.5, display: 'flex', alignItems: 'center', color: '#d4af37' }}>
              <SparkleIcon fontSize="medium" />
            </Box>
            
            {/* Agent Selector Chip */}
            <Chip
              ref={chipRef}
              label={selectedAgent.nickname}
              size="small"
              onClick={() => setAgentMenuOpen(true)}
              onDelete={() => setAgentMenuOpen(true)}
              deleteIcon={<ArrowDownIcon sx={{ fontSize: 16 }} />}
              sx={{
                height: 28,
                bgcolor: `${selectedAgent.color}20`,
                color: selectedAgent.color,
                border: `1px solid ${selectedAgent.color}40`,
                fontWeight: 600,
                fontSize: '0.8rem',
                cursor: 'pointer',
                transition: 'all 0.15s',
                '& .MuiChip-deleteIcon': {
                  color: selectedAgent.color,
                  '&:hover': { color: selectedAgent.color }
                },
                '&:hover': {
                  bgcolor: `${selectedAgent.color}30`,
                  borderColor: `${selectedAgent.color}60`,
                }
              }}
            />
            
            <InputBase
              inputRef={inputRef}
              sx={{ ml: 1.5, flex: 1, fontSize: '1.1rem' }}
              placeholder="Ask AI Agent to do something..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Escape') closeCommand();
              }}
            />
            
            <Box sx={{ display: 'flex', alignItems: 'center', pr: 1 }}>
              <IconButton type="submit" sx={{ p: 1 }} aria-label="search">
                <EnterIcon />
              </IconButton>
            </Box>
          </Paper>
          
          {/* Agent-specific suggestions */}
          <Box sx={{ mt: 1.5, display: 'flex', justifyContent: 'center', gap: 1, flexWrap: 'wrap' }}>
            {selectedAgent.tips.map((tip) => (
              <Chip
                key={tip}
                label={tip}
                size="small"
                onClick={() => setInput(tip)}
                sx={{
                  bgcolor: 'rgba(60, 60, 60, 0.9)',
                  color: '#b0b0b0',
                  fontSize: '0.75rem',
                  height: 26,
                  border: '1px solid rgba(100, 100, 100, 0.3)',
                  backdropFilter: 'blur(4px)',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                  '&:hover': { 
                    bgcolor: 'rgba(80, 80, 80, 0.95)',
                    color: '#e0e0e0',
                    borderColor: 'rgba(150, 150, 150, 0.4)'
                  }
                }}
              />
            ))}
          </Box>
        </Box>
      </Fade>
      
      {/* Agent Selection Menu */}
      <Menu
        anchorEl={chipRef.current}
        open={agentMenuOpen && isCommandOpen}
        onClose={() => setAgentMenuOpen(false)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'left' }}
        transformOrigin={{ vertical: 'top', horizontal: 'left' }}
        sx={{ zIndex: 10000 }}
        PaperProps={{
          sx: {
            bgcolor: '#2a2a2a',
            border: '1px solid #444',
            borderRadius: 2,
            mt: 0.5,
            minWidth: 220,
            boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
            py: 0.5,
          }
        }}
      >
        {AVAILABLE_AGENTS.map((agent) => (
          <MenuItem
            key={agent.id}
            onClick={() => {
              setSelectedAgentId(agent.id);
              setAgentMenuOpen(false);
              inputRef.current?.focus();
            }}
            selected={agent.id === selectedAgentId}
            sx={{
              py: 0.75,
              px: 1.5,
              minHeight: 'auto',
              '&:hover': { bgcolor: 'rgba(255,255,255,0.06)' },
              '&.Mui-selected': { 
                bgcolor: 'rgba(255,255,255,0.08)',
                '&:hover': { bgcolor: 'rgba(255,255,255,0.1)' }
              },
            }}
          >
            <Box sx={{ 
              width: 8, 
              height: 8, 
              borderRadius: '50%', 
              bgcolor: agent.color,
              flexShrink: 0
            }} />
            <Typography sx={{ fontWeight: 600, color: '#f0f0f0', fontSize: '0.85rem', ml: 1.5 }}>
              {agent.nickname}
            </Typography>
            <Typography sx={{ color: '#999', fontSize: '0.75rem', ml: 'auto', pl: 2 }}>
              {agent.description}
            </Typography>
          </MenuItem>
        ))}
      </Menu>
    </>
  );
};

