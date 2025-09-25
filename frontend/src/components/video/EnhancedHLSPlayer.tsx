import React, { useState, useRef, useEffect } from 'react';
import { Box, Slider, Typography, IconButton } from '@mui/material';
import { PlayArrow, Pause } from '@mui/icons-material';
import { HLSVideoPlayer } from '../common/HLSVideoPlayer';
import { useStream } from '../../hooks/controller';
import { Host } from '../../types/common/Host_Types';

interface EnhancedHLSPlayerProps {
  deviceId: string;
  hostName: string;
  host?: Host; // Host object for useStream hook
  streamUrl?: string; // Server-provided stream URL
  width?: string | number;
  height?: string | number;
  autoPlay?: boolean;
  className?: string;
  isLiveMode?: boolean;
}

export const EnhancedHLSPlayer: React.FC<EnhancedHLSPlayerProps> = ({
  deviceId,
  hostName,
  host,
  streamUrl: providedStreamUrl,
  width = '100%',
  height = 400,
  className,
  isLiveMode: externalIsLiveMode
}) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [internalIsLiveMode] = useState(true); // Start in live mode
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [isPlaying, setIsPlaying] = useState(true); // Start playing automatically
  
  // Use external control if provided, otherwise use internal state
  const isLiveMode = externalIsLiveMode !== undefined ? externalIsLiveMode : internalIsLiveMode;

  // Use useStream hook when host is provided and no streamUrl is given (same as RecHostPreview)
  const { streamUrl: hookStreamUrl } = useStream({
    host: host || {
      host_name: hostName,
      host_url: `http://${hostName}:6109`,
      host_port: 6109,
      devices: [],
      device_count: 0,
      status: 'online',
      last_seen: Date.now(),
      registered_at: new Date().toISOString(),
      system_stats: {
        cpu_percent: 0,
        memory_percent: 0,
        disk_percent: 0,
        platform: 'linux',
        architecture: 'x86_64',
        python_version: '3.9'
      },
      isLocked: false
    },
    device_id: deviceId,
  });

  // Use provided stream URL, then hook URL, then fallback to dynamic URL based on mode
  const streamUrl = providedStreamUrl || hookStreamUrl || (isLiveMode 
    ? `/host/stream/capture${deviceId === 'device1' ? '1' : '2'}/output.m3u8`
    : `/host/stream/capture${deviceId === 'device1' ? '1' : '2'}/archive.m3u8`);

  // Seek to live edge when switching to live mode
  const seekToLive = () => {
    if (videoRef.current) {
      const video = videoRef.current;
      if (video.duration && !isNaN(video.duration)) {
        video.currentTime = video.duration;
      }
    }
  };

  // Play/pause control
  const togglePlayPause = () => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause();
      } else {
        videoRef.current.play();
      }
      setIsPlaying(!isPlaying);
    }
  };

  // Video event handlers for timeline and play state
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const handleTimeUpdate = () => setCurrentTime(video.currentTime);
    const handleDurationChange = () => {
      setDuration(video.duration);
      
      // When archive mode loads and we get duration, seek to beginning (leftmost position)
      if (!isLiveMode && video.duration && !isNaN(video.duration)) {
        console.log('[@EnhancedHLSPlayer] Archive mode loaded, seeking to beginning');
        video.currentTime = 0; // Start at beginning for 24h mode
      }
    };

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
  }, [isLiveMode]);

  // Handle mode changes and seeking
  useEffect(() => {
    const timer = setTimeout(() => {
      if (isLiveMode) {
        seekToLive();
      } else {
        // For 24h mode, start at beginning
        if (videoRef.current) {
          videoRef.current.currentTime = 0;
        }
      }
    }, 500); // Small delay to allow HLS player to initialize with new manifest
    
    return () => clearTimeout(timer);
  }, [isLiveMode]);

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
      {/* Reuse HLSVideoPlayer for all streaming logic */}
      <Box sx={{ position: 'relative', height }}>
        <HLSVideoPlayer
          key={streamUrl} // Force remount when URL changes
          streamUrl={streamUrl}
          isStreamActive={true}
          videoElementRef={videoRef}
          muted={false}
          isArchiveMode={!isLiveMode} // Pass archive mode flag
          sx={{ width: '100%', height: '100%' }}
        />

        {/* Play/Pause Control Overlay - Always visible */}
        <Box
          sx={{
            position: 'absolute',
            bottom: !isLiveMode && duration > 0 ? 80 : 16, // Align with timeline when present
            left: 16,
            zIndex: 10,
          }}
        >
          <IconButton
            onClick={togglePlayPause}
            sx={{
              backgroundColor: 'rgba(0, 0, 0, 0.6)',
              color: 'white',
              '&:hover': {
                backgroundColor: 'rgba(0, 0, 0, 0.8)',
              },
            }}
            size="small"
          >
            {isPlaying ? <PlayArrow /> : <Pause />}
          </IconButton>
        </Box>

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
