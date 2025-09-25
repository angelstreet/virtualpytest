import React, { useState, useRef, useEffect } from 'react';
import { Box, Switch, FormControlLabel, Slider, Typography } from '@mui/material';
import { HLSVideoPlayer } from '../common/HLSVideoPlayer';

interface EnhancedHLSPlayerProps {
  deviceId: string;
  hostName: string;
  width?: string | number;
  height?: string | number;
  autoPlay?: boolean;
  className?: string;
}

export const EnhancedHLSPlayer: React.FC<EnhancedHLSPlayerProps> = ({
  deviceId,
  width = '100%',
  height = 400,
  className
}) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isLiveMode, setIsLiveMode] = useState(true);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);

  // Same stream URL for both modes - nginx provides 24h rolling playlist
  const streamUrl = `/host/stream/capture${deviceId === 'device1' ? '1' : '2'}/output.m3u8`;

  // Seek to live edge when switching to live mode
  const seekToLive = () => {
    if (videoRef.current) {
      const video = videoRef.current;
      if (video.duration && !isNaN(video.duration)) {
        video.currentTime = video.duration;
      }
    }
  };

  // Video event handlers for timeline
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const handleTimeUpdate = () => setCurrentTime(video.currentTime);
    const handleDurationChange = () => setDuration(video.duration);

    video.addEventListener('timeupdate', handleTimeUpdate);
    video.addEventListener('durationchange', handleDurationChange);

    return () => {
      video.removeEventListener('timeupdate', handleTimeUpdate);
      video.removeEventListener('durationchange', handleDurationChange);
    };
  }, []);

  // Mode toggle handler
  const handleModeToggle = (event: React.ChangeEvent<HTMLInputElement>) => {
    const newIsLiveMode = event.target.checked;
    setIsLiveMode(newIsLiveMode);
    
    if (newIsLiveMode) {
      seekToLive();
    }
  };

  // Archive timeline controls
  const handleSeek = (_event: Event, newValue: number | number[]) => {
    if (videoRef.current && !isLiveMode) {
      videoRef.current.currentTime = newValue as number;
    }
  };

  const formatTime = (seconds: number) => {
    if (!seconds || !isFinite(seconds)) return '0:00';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    return hours > 0 
      ? `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
      : `${minutes}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <Box className={className} sx={{ width, position: 'relative' }}>
      {/* Mode Toggle */}
      <FormControlLabel
        control={<Switch checked={isLiveMode} onChange={handleModeToggle} />}
        label={isLiveMode ? '🔴 Live' : '📼 24h Archive'}
        sx={{ mb: 1 }}
      />

      {/* Reuse HLSVideoPlayer for all streaming logic */}
      <Box sx={{ position: 'relative', height }}>
        <HLSVideoPlayer
          streamUrl={streamUrl}
          isStreamActive={true}
          videoElementRef={videoRef}
          muted={false}
          sx={{ width: '100%', height: '100%' }}
        />

        {/* Archive Timeline Overlay */}
        {!isLiveMode && duration > 0 && (
          <Box
            sx={{
              position: 'absolute',
              bottom: 0,
              left: 0,
              right: 0,
              background: 'linear-gradient(transparent, rgba(0,0,0,0.8))',
              p: 2,
            }}
          >
            <Slider
              value={currentTime}
              max={duration}
              onChange={handleSeek}
              sx={{ color: 'primary.main', mb: 1 }}
            />
            <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
              <Typography variant="caption" sx={{ color: 'white' }}>
                {formatTime(currentTime)}
              </Typography>
              <Typography variant="caption" sx={{ color: 'white' }}>
                {formatTime(duration)}
              </Typography>
            </Box>
          </Box>
        )}
      </Box>
    </Box>
  );
};
