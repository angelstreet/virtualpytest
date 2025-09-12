import { Box, Typography } from '@mui/material';
import React from 'react';

interface RestartSubtitleOverlayProps {
  subtitleText?: string;
  language: string;
}

export const RestartSubtitleOverlay: React.FC<RestartSubtitleOverlayProps> = ({
  subtitleText,
  language,
}) => {
  if (!subtitleText) return null;

  return (
    <Box
      sx={{
        position: 'absolute',
        bottom: 60,
        left: '50%',
        transform: 'translateX(-50%)',
        zIndex: 1000020,
        maxWidth: '90%',
        textAlign: 'center',
      }}
    >
      <Typography
        variant="body1"
        sx={{
          backgroundColor: 'rgba(0, 0, 0, 0.9)',
          color: '#ffffff',
          p: 1.5,
          borderRadius: 1,
          fontSize: '1rem',
          fontWeight: 500,
          textShadow: '1px 1px 2px rgba(0,0,0,0.8)',
        }}
      >
        {subtitleText}
      </Typography>
    </Box>
  );
};
