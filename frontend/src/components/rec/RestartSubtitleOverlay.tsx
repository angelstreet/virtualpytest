import { Box, Typography } from '@mui/material';
import React, { useState, useEffect } from 'react';

interface RestartSubtitleOverlayProps {
  videoRef?: React.RefObject<HTMLVideoElement>;
  frameSubtitles?: string[];
  style: string;
  fontSize: string;
}

export const RestartSubtitleOverlay: React.FC<RestartSubtitleOverlayProps> = ({
  videoRef,
  frameSubtitles,
  style,
  fontSize,
}) => {
  const [currentSubtitle, setCurrentSubtitle] = useState<string>('');

  useEffect(() => {
    if (!videoRef?.current || !frameSubtitles?.length) return;

    const video = videoRef.current;
    
    const updateSubtitle = () => {
      const currentTime = Math.floor(video.currentTime);
      const subtitle = frameSubtitles[currentTime] || '';
      // Remove "Frame X: " prefix and show only the subtitle text
      const cleanSubtitle = subtitle.replace(/^Frame \d+: /, '');
      setCurrentSubtitle(cleanSubtitle === 'No subtitles detected' ? '' : cleanSubtitle);
    };

    video.addEventListener('timeupdate', updateSubtitle);
    return () => video.removeEventListener('timeupdate', updateSubtitle);
  }, [videoRef, frameSubtitles]);

  if (!currentSubtitle) return null;

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
        {currentSubtitle}
      </Typography>
    </Box>
  );
};
