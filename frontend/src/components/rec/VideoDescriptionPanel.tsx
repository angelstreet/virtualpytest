import { Box, Typography, IconButton, Slide, Paper } from '@mui/material';
import { Description as DescriptionIcon, Close as CloseIcon } from '@mui/icons-material';
import React, { useState } from 'react';

interface VideoDescriptionPanelProps {
  videoDescription?: string;
  framesAnalyzed?: number;
}

export const VideoDescriptionPanel: React.FC<VideoDescriptionPanelProps> = ({
  videoDescription,
  framesAnalyzed
}) => {
  const [isOpen, setIsOpen] = useState(false);

  if (!videoDescription) return null;

  return (
    <>
      {/* Toggle Button */}
      <IconButton
        onClick={() => setIsOpen(!isOpen)}
        sx={{
          position: 'absolute',
          top: 16,
          right: 60, // Next to subtitle settings
          zIndex: 1000030,
          backgroundColor: 'rgba(0, 0, 0, 0.7)',
          color: '#ffffff',
          '&:hover': {
            backgroundColor: 'rgba(0, 0, 0, 0.9)',
          },
        }}
      >
        <DescriptionIcon />
      </IconButton>

      {/* Sliding Panel */}
      <Slide direction="left" in={isOpen} mountOnEnter unmountOnExit>
        <Paper
          sx={{
            position: 'absolute',
            top: 0,
            right: 0,
            width: 400,
            height: '100%',
            zIndex: 1000040,
            backgroundColor: 'rgba(0, 0, 0, 0.95)',
            color: '#ffffff',
            p: 3,
            overflowY: 'auto',
            borderRadius: 0,
          }}
        >
          {/* Header */}
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              Video Description
            </Typography>
            <IconButton
              onClick={() => setIsOpen(false)}
              sx={{ color: '#ffffff', p: 0.5 }}
            >
              <CloseIcon />
            </IconButton>
          </Box>

          {/* Frames Info */}
          {framesAnalyzed && (
            <Typography variant="caption" sx={{ color: '#cccccc', mb: 2, display: 'block' }}>
              Analyzed {framesAnalyzed} frames (1 per second)
            </Typography>
          )}

          {/* Description Content */}
          <Typography
            variant="body2"
            sx={{
              lineHeight: 1.6,
              whiteSpace: 'pre-line',
              fontSize: '0.9rem',
            }}
          >
            {videoDescription}
          </Typography>
        </Paper>
      </Slide>
    </>
  );
};
