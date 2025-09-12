import { Box, Typography } from '@mui/material';
import React, { useState, useEffect } from 'react';

interface SubtitleSegment {
  startTime: number; // seconds
  endTime: number;   // seconds
  text: string;
}

interface SubtitleOverlayProps {
  transcript?: string;
  detectedLanguage?: string;
  speechDetected?: boolean;
  videoRef?: React.RefObject<HTMLVideoElement>;
  videoDuration?: number; // Total video duration in seconds
}

export const SubtitleOverlay: React.FC<SubtitleOverlayProps> = ({
  transcript,
  detectedLanguage,
  speechDetected,
  videoRef,
  videoDuration = 30
}) => {
  const [currentSubtitle, setCurrentSubtitle] = useState<string>('');
  const [subtitleSegments, setSubtitleSegments] = useState<SubtitleSegment[]>([]);

  // Parse transcript into time-synchronized segments
  useEffect(() => {
    if (!transcript || !speechDetected) {
      setSubtitleSegments([]);
      return;
    }

    // Split transcript into segments (roughly 3-5 words per segment for readability)
    const words = transcript.split(' ');
    const segments: SubtitleSegment[] = [];
    const wordsPerSegment = 4;
    const segmentDuration = videoDuration / Math.ceil(words.length / wordsPerSegment);

    for (let i = 0; i < words.length; i += wordsPerSegment) {
      const segmentWords = words.slice(i, i + wordsPerSegment);
      const startTime = (i / wordsPerSegment) * segmentDuration;
      const endTime = Math.min(startTime + segmentDuration, videoDuration);
      
      segments.push({
        startTime,
        endTime,
        text: segmentWords.join(' ')
      });
    }

    setSubtitleSegments(segments);
  }, [transcript, speechDetected, videoDuration]);

  // Sync with video timeline
  useEffect(() => {
    if (!videoRef?.current || subtitleSegments.length === 0) return;

    const video = videoRef.current;
    
    const updateSubtitle = () => {
      const currentTime = video.currentTime;
      const activeSegment = subtitleSegments.find(
        segment => currentTime >= segment.startTime && currentTime <= segment.endTime
      );
      
      setCurrentSubtitle(activeSegment?.text || '');
    };

    // Update on time change
    video.addEventListener('timeupdate', updateSubtitle);
    
    return () => {
      video.removeEventListener('timeupdate', updateSubtitle);
    };
  }, [videoRef, subtitleSegments]);

  if (!speechDetected || !transcript) return null;

  return (
    <Box
      sx={{
        position: 'absolute',
        bottom: 80, // Above video controls
        left: '50%',
        transform: 'translateX(-50%)',
        zIndex: 1000020,
        maxWidth: '80%',
        textAlign: 'center',
        pointerEvents: 'none',
      }}
    >
      {/* Language indicator */}
      {detectedLanguage && detectedLanguage !== 'unknown' && (
        <Box
          sx={{
            mb: 1,
            px: 1,
            py: 0.5,
            backgroundColor: 'rgba(0, 0, 0, 0.6)',
            borderRadius: 1,
            display: 'inline-block',
          }}
        >
          <Typography
            variant="caption"
            sx={{
              color: '#ffffff',
              fontSize: '0.7rem',
              textTransform: 'uppercase',
              letterSpacing: '0.5px',
            }}
          >
            {detectedLanguage}
          </Typography>
        </Box>
      )}

      {/* Subtitle text */}
      {currentSubtitle && (
        <Box
          sx={{
            px: 2,
            py: 1,
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            borderRadius: 1,
            border: '1px solid rgba(255, 255, 255, 0.1)',
          }}
        >
          <Typography
            variant="body1"
            sx={{
              color: '#ffffff',
              fontSize: '1rem',
              fontWeight: 500,
              textShadow: '2px 2px 4px rgba(0,0,0,0.9)',
              lineHeight: 1.3,
            }}
          >
            {currentSubtitle}
          </Typography>
        </Box>
      )}
    </Box>
  );
};
