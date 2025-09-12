import { Box, Typography } from '@mui/material';
import React, { useState, useEffect } from 'react';

interface RestartSummaryOverlayProps {
  videoRef?: React.RefObject<HTMLVideoElement>;
  frameDescriptions?: string[];
}

export const RestartSummaryOverlay: React.FC<RestartSummaryOverlayProps> = ({
  videoRef,
  frameDescriptions,
}) => {
  const [currentSummary, setCurrentSummary] = useState<string>('');

  useEffect(() => {
    if (!videoRef?.current || !frameDescriptions?.length) return;

    const video = videoRef.current;
    
    const updateSummary = () => {
      const currentTime = Math.floor(video.currentTime);
      const summary = frameDescriptions[currentTime] || '';
      setCurrentSummary(summary.replace(/^Second \d+: /, ''));
    };

    video.addEventListener('timeupdate', updateSummary);
    return () => video.removeEventListener('timeupdate', updateSummary);
  }, [videoRef, frameDescriptions]);

  if (!currentSummary) return null;

  return (
    <Box
      sx={{
        position: 'absolute',
        top: 20,
        left: '50%',
        transform: 'translateX(-50%)',
        zIndex: 1000020,
        maxWidth: '80%',
        textAlign: 'center',
      }}
    >
      <Typography
        variant="body2"
        sx={{
          backgroundColor: 'rgba(0, 0, 0, 0.8)',
          color: '#ffffff',
          p: 1,
          borderRadius: 1,
          fontSize: '0.9rem',
        }}
      >
        {currentSummary}
      </Typography>
    </Box>
  );
};
