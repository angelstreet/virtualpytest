import React from 'react';
import { Box, Typography, TextField, Button } from '@mui/material';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';

interface AIModePanel Props {
  aiPrompt?: string;
  setAiPrompt?: (prompt: string) => void;
  isGenerating?: boolean;
  handleGenerateWithAI?: () => void;
}

export const AIModePanel: React.FC<AIModePanel Props> = ({
  aiPrompt = '',
  setAiPrompt = () => {},
  isGenerating = false,
  handleGenerateWithAI = () => {},
}) => {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, p: 1.5, flex: 1, overflowY: 'auto' }}>
      <Typography variant="subtitle2" fontWeight="bold">
        AI Test Generator
      </Typography>
      <TextField
        multiline
        rows={6}
        placeholder="e.g., Go to live TV and verify audio is playing"
        value={aiPrompt}
        onChange={(e) => setAiPrompt(e.target.value)}
        size="small"
        fullWidth
      />
      <Button
        variant="contained"
        startIcon={<AutoAwesomeIcon />}
        onClick={handleGenerateWithAI}
        disabled={isGenerating || !aiPrompt.trim()}
        fullWidth
        size="small"
      >
        {isGenerating ? 'Generating...' : 'Generate'}
      </Button>
      
      {/* Sample prompts */}
      <Box sx={{ mt: 1 }}>
        <Typography variant="caption" fontWeight="bold" color="text.secondary">
          Examples:
        </Typography>
        {[
          'Go to live TV and check audio',
          'Navigate to settings',
          'Play first recording'
        ].map((example, idx) => (
          <Typography
            key={idx}
            variant="caption"
            sx={{
              display: 'block',
              mt: 0.5,
              cursor: 'pointer',
              color: 'primary.main',
              '&:hover': { textDecoration: 'underline' }
            }}
            onClick={() => setAiPrompt(example)}
          >
            • {example}
          </Typography>
        ))}
      </Box>
    </Box>
  );
};

