import React, { useState, useRef, useEffect } from 'react';
import {
  Box,
  Switch,
  FormControlLabel,
  Slider,
  Typography,
  IconButton,
  Stack,
} from '@mui/material';
import {
  PlayArrow as PlayIcon,
  Pause as PauseIcon,
  VolumeUp as VolumeIcon,
  Fullscreen as FullscreenIcon,
} from '@mui/icons-material';

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
  hostName,
  width = '100%',
  height = 400,
  autoPlay = true,
  className
}) => {
  // Player state
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isLiveMode, setIsLiveMode] = useState(true);
  const [isPlaying, setIsPlaying] = useState(autoPlay);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [isFullscreen, setIsFullscreen] = useState(false);

  // HLS URLs
  const liveUrl = `/stream/capture${deviceId === 'device1' ? '1' : '2'}/live.m3u8`;
  const archiveUrl = `/stream/capture${deviceId === 'device1' ? '1' : '2'}/output.m3u8`;

  // Current URL based on mode
  const currentUrl = isLiveMode ? liveUrl : archiveUrl;

  // Load HLS stream
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    // For now, use native HLS support or fall back to basic video
    // In production, you'd use hls.js here
    if (video.canPlayType('application/vnd.apple.mpegurl')) {
      video.src = currentUrl;
    } else {
      console.warn('HLS not natively supported, would need hls.js');
      // Fallback or hls.js implementation
    }

    if (autoPlay && isPlaying) {
      video.play().catch(console.error);
    }
  }, [currentUrl, autoPlay, isPlaying]);

  // Video event handlers
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const handleTimeUpdate = () => setCurrentTime(video.currentTime);
    const handleDurationChange = () => setDuration(video.duration);
    const handlePlay = () => setIsPlaying(true);
    const handlePause = () => setIsPlaying(false);

    video.addEventListener('timeupdate', handleTimeUpdate);
    video.addEventListener('durationchange', handleDurationChange);
    video.addEventListener('play', handlePlay);
    video.addEventListener('pause', handlePause);

    return () => {
      video.removeEventListener('timeupdate', handleTimeUpdate);
      video.removeEventListener('durationchange', handleDurationChange);
      video.removeEventListener('play', handlePlay);
      video.removeEventListener('pause', handlePause);
    };
  }, []);

  // Mode toggle handler
  const handleModeToggle = (event: React.ChangeEvent<HTMLInputElement>) => {
    const newIsLiveMode = event.target.checked;
    setIsLiveMode(newIsLiveMode);
    
    console.log(`📺 Switching to ${newIsLiveMode ? 'Live' : '24h Archive'} mode`);
    
    // Reset timeline when switching modes
    setCurrentTime(0);
    setDuration(0);
  };

  // Playback controls
  const togglePlayPause = () => {
    const video = videoRef.current;
    if (!video) return;

    if (isPlaying) {
      video.pause();
    } else {
      video.play().catch(console.error);
    }
  };

  const handleSeek = (event: Event, newValue: number | number[]) => {
    const video = videoRef.current;
    if (!video || isLiveMode) return; // No seeking in live mode

    const seekTime = newValue as number;
    video.currentTime = seekTime;
    setCurrentTime(seekTime);
  };

  const handleVolumeChange = (event: Event, newValue: number | number[]) => {
    const video = videoRef.current;
    if (!video) return;

    const newVolume = (newValue as number) / 100;
    video.volume = newVolume;
    setVolume(newVolume);
  };

  const toggleFullscreen = () => {
    const video = videoRef.current;
    if (!video) return;

    if (!isFullscreen) {
      video.requestFullscreen?.();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen?.();
      setIsFullscreen(false);
    }
  };

  // Format time for display
  const formatTime = (seconds: number) => {
    if (!seconds || !isFinite(seconds)) return '0:00';
    
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <Box className={className} sx={{ width, position: 'relative' }}>
      {/* Mode Toggle */}
      <Box sx={{ mb: 1, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <FormControlLabel
          control={
            <Switch
              checked={isLiveMode}
              onChange={handleModeToggle}
              color="primary"
            />
          }
          label={
            <Typography variant="body2" sx={{ fontWeight: 500 }}>
              {isLiveMode ? '🔴 Live' : '📼 24h Archive'}
            </Typography>
          }
        />
        
        {!isLiveMode && (
          <Typography variant="caption" color="text.secondary">
            Use timeline below to navigate through 24h history
          </Typography>
        )}
      </Box>

      {/* Video Player */}
      <Box sx={{ position: 'relative', backgroundColor: '#000', borderRadius: 1 }}>
        <video
          ref={videoRef}
          width="100%"
          height={height}
          controls={false} // We'll use custom controls
          autoPlay={autoPlay}
          muted={false}
          style={{ display: 'block', borderRadius: 4 }}
        />

        {/* Custom Controls Overlay */}
        <Box
          sx={{
            position: 'absolute',
            bottom: 0,
            left: 0,
            right: 0,
            background: 'linear-gradient(transparent, rgba(0,0,0,0.7))',
            p: 1,
            borderRadius: '0 0 4px 4px',
          }}
        >
          {/* Timeline Scrubber (only in 24h mode) */}
          {!isLiveMode && duration > 0 && (
            <Box sx={{ mb: 1 }}>
              <Slider
                value={currentTime}
                max={duration}
                onChange={handleSeek}
                size="small"
                sx={{
                  color: 'primary.main',
                  '& .MuiSlider-thumb': {
                    width: 12,
                    height: 12,
                  },
                  '& .MuiSlider-track': {
                    height: 3,
                  },
                  '& .MuiSlider-rail': {
                    height: 3,
                    opacity: 0.3,
                  },
                }}
              />
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 0.5 }}>
                <Typography variant="caption" sx={{ color: 'white' }}>
                  {formatTime(currentTime)}
                </Typography>
                <Typography variant="caption" sx={{ color: 'white' }}>
                  {formatTime(duration)}
                </Typography>
              </Box>
            </Box>
          )}

          {/* Control Buttons */}
          <Stack direction="row" spacing={1} alignItems="center">
            {/* Play/Pause */}
            <IconButton
              onClick={togglePlayPause}
              size="small"
              sx={{ color: 'white' }}
            >
              {isPlaying ? <PauseIcon /> : <PlayIcon />}
            </IconButton>

            {/* Volume Control */}
            <Box sx={{ display: 'flex', alignItems: 'center', minWidth: 100 }}>
              <VolumeIcon sx={{ color: 'white', mr: 1, fontSize: 20 }} />
              <Slider
                value={volume * 100}
                onChange={handleVolumeChange}
                size="small"
                sx={{ color: 'white', maxWidth: 60 }}
              />
            </Box>

            {/* Live/Archive Indicator */}
            <Box sx={{ flexGrow: 1, textAlign: 'center' }}>
              <Typography variant="caption" sx={{ color: 'white' }}>
                {isLiveMode ? '🔴 LIVE' : `📼 ARCHIVE (${formatTime(duration)} available)`}
              </Typography>
            </Box>

            {/* Fullscreen */}
            <IconButton
              onClick={toggleFullscreen}
              size="small"
              sx={{ color: 'white' }}
            >
              <FullscreenIcon />
            </IconButton>
          </Stack>
        </Box>
      </Box>

      {/* Mode Info */}
      <Box sx={{ mt: 1 }}>
        <Typography variant="caption" color="text.secondary">
          {isLiveMode 
            ? 'Live stream - showing current feed with minimal delay'
            : '24-hour archive - navigate timeline to view historical footage'
          }
        </Typography>
      </Box>
    </Box>
  );
};
