import { Box, Typography } from '@mui/material';
import React from 'react';

interface RestartSubtitleOverlayProps {
  subtitleText?: string;
  style: string;
  fontSize: string;
}

export const RestartSubtitleOverlay: React.FC<RestartSubtitleOverlayProps> = ({
  subtitleText,
  style,
  fontSize,
}) => {
  if (!subtitleText) return null;

  // Style configurations
  const getSubtitleStyle = () => {
    switch (style) {
      case 'yellow':
        return {
          color: '#ffff00',
          backgroundColor: 'rgba(0, 0, 0, 0.8)',
          textShadow: '2px 2px 4px rgba(0,0,0,0.8)',
        };
      case 'white':
        return {
          color: '#ffffff',
          backgroundColor: 'rgba(0, 0, 0, 0.8)',
          textShadow: '2px 2px 4px rgba(0,0,0,0.8)',
        };
      case 'white-border':
        return {
          color: '#ffffff',
          backgroundColor: 'transparent',
          textShadow: '2px 2px 0px #000000, -2px -2px 0px #000000, 2px -2px 0px #000000, -2px 2px 0px #000000',
        };
      case 'black-bg':
        return {
          color: '#ffffff',
          backgroundColor: 'rgba(0, 0, 0, 0.9)',
          textShadow: 'none',
        };
      default:
        return {
          color: '#ffff00',
          backgroundColor: 'rgba(0, 0, 0, 0.8)',
          textShadow: '2px 2px 4px rgba(0,0,0,0.8)',
        };
    }
  };

  const getFontSize = () => {
    switch (fontSize) {
      case 'small': return '0.9rem';
      case 'medium': return '1.1rem';
      case 'large': return '1.3rem';
      default: return '1.1rem';
    }
  };

  const subtitleStyle = getSubtitleStyle();

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
          backgroundColor: subtitleStyle.backgroundColor,
          color: subtitleStyle.color,
          p: 1.5,
          borderRadius: style === 'white-border' ? 0 : 1,
          fontSize: getFontSize(),
          fontWeight: 500,
          textShadow: subtitleStyle.textShadow,
        }}
      >
        {subtitleText}
      </Typography>
    </Box>
  );
};
