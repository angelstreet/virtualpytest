import React, { useState, useRef, useEffect } from 'react';
import { 
  Box, 
  Paper, 
  InputBase, 
  IconButton, 
  Typography, 
  Fade,
  Backdrop
} from '@mui/material';
import { 
  Search as SearchIcon, 
  AutoAwesome as SparkleIcon,
  KeyboardReturn as EnterIcon
} from '@mui/icons-material';
import { useAIContext } from '../../contexts/AIContext';

export const AICommandBar: React.FC = () => {
  const { isCommandOpen, closeCommand, setTask, setProcessing } = useAIContext();
  const [input, setInput] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  // Focus input when opened
  useEffect(() => {
    if (isCommandOpen && inputRef.current) {
      // Small delay to ensure render
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isCommandOpen]);

  const handleSubmit = (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!input.trim()) return;

    // 1. Set the task in global context
    setTask(input);
    
    // 2. Start processing (this triggers the Right Panel to open)
    setProcessing(true);
    
    // 3. Clear and close the command bar
    setInput('');
    closeCommand();
  };

  if (!isCommandOpen) return null;

  return (
    <>
      {/* Dimmed Background */}
      <Backdrop 
        open={isCommandOpen} 
        onClick={closeCommand}
        sx={{ zIndex: 9998, bgcolor: 'rgba(0,0,0,0.4)' }} 
      />

      {/* Floating Command Input */}
      <Fade in={isCommandOpen}>
        <Box
          sx={{
            position: 'fixed',
            top: '20%',
            left: '50%',
            transform: 'translateX(-50%)',
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
              borderColor: 'primary.main',
              boxShadow: '0 8px 32px rgba(0,0,0,0.2)',
              overflow: 'hidden'
            }}
          >
            <Box sx={{ p: 1.5, display: 'flex', alignItems: 'center', color: 'primary.main' }}>
              <SparkleIcon fontSize="medium" />
            </Box>
            
            <InputBase
              inputRef={inputRef}
              sx={{ ml: 1, flex: 1, fontSize: '1.1rem' }}
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
          
          {/* Quick Hints */}
          <Box sx={{ mt: 1, display: 'flex', justifyContent: 'center', gap: 2 }}>
             <Typography variant="caption" sx={{ color: 'white', textShadow: '0 1px 2px rgba(0,0,0,0.8)' }}>
               Try: "Go to dashboard"
             </Typography>
             <Typography variant="caption" sx={{ color: 'white', textShadow: '0 1px 2px rgba(0,0,0,0.8)' }}>
               Try: "Run smoke test on Pixel 5"
             </Typography>
          </Box>
        </Box>
      </Fade>
    </>
  );
};

