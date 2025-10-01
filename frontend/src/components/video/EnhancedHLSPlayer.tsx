import React, { useState, useRef, useEffect, useMemo, useCallback } from 'react';
import { Box, Slider, Typography, IconButton } from '@mui/material';
import { PlayArrow, Pause } from '@mui/icons-material';
import { HLSVideoPlayer } from '../common/HLSVideoPlayer';
import { useStream } from '../../hooks/controller';
import { Host } from '../../types/common/Host_Types';

interface ArchiveMetadata {
  total_segments: number;
  total_duration_seconds: number;
  window_hours: number;
  segments_per_window: number;
  manifests: Array<{
    name: string;
    window_index: number;
    start_segment: number;
    end_segment: number;
    start_time_seconds: number;
    end_time_seconds: number;
    duration_seconds: number;
  }>;
}

interface EnhancedHLSPlayerProps {
  deviceId: string;
  hostName: string;
  host?: Host; // Host object for useStream hook
  streamUrl?: string; // Server-provided stream URL
  width?: string | number;
  height?: string | number;
  muted?: boolean; // Add muted prop for audio control
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
  muted = true, // Default to muted for autoplay compliance
  className,
  isLiveMode: externalIsLiveMode
}) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [internalIsLiveMode] = useState(true); // Start in live mode
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [isPlaying, setIsPlaying] = useState(true); // Start playing automatically
  const [isTransitioning, setIsTransitioning] = useState(false); // Mode transition state
  
  // Archive metadata and manifest switching state
  const [archiveMetadata, setArchiveMetadata] = useState<ArchiveMetadata | null>(null);
  const [currentManifestIndex, setCurrentManifestIndex] = useState(0);
  const [globalCurrentTime, setGlobalCurrentTime] = useState(0); // Time across all manifests
  const [preloadedNextManifest, setPreloadedNextManifest] = useState(false);
  
  // Use external control if provided, otherwise use internal state
  const isLiveMode = externalIsLiveMode !== undefined ? externalIsLiveMode : internalIsLiveMode;
  
  // Track previous mode to detect changes
  const prevIsLiveMode = useRef(isLiveMode);

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

  // Detect mode changes and trigger transition
  useEffect(() => {
    if (prevIsLiveMode.current !== isLiveMode) {
      console.log(`[@EnhancedHLSPlayer] Mode change detected: ${prevIsLiveMode.current ? 'Live' : 'Archive'} -> ${isLiveMode ? 'Live' : 'Archive'}`);
      setIsTransitioning(true);
      
      // When switching back to live, clear archive metadata
      if (isLiveMode) {
        console.log('[@EnhancedHLSPlayer] Clearing archive metadata (switching to live)');
        setArchiveMetadata(null);
        setCurrentManifestIndex(0);
      }
      
      // Small delay to allow cleanup
      setTimeout(() => {
        setIsTransitioning(false);
      }, 100);
      
      prevIsLiveMode.current = isLiveMode;
    }
  }, [isLiveMode]);

  // Fetch archive metadata when entering archive mode
  useEffect(() => {
    if (!isLiveMode && !archiveMetadata && !isTransitioning) {
      const baseUrl = providedStreamUrl || hookStreamUrl || `/host/stream/capture${deviceId === 'device1' ? '1' : '2'}/output.m3u8`;
      const metadataUrl = baseUrl.replace(/\/(output|archive.*?)\.m3u8$/, '/archive_metadata.json');
      
      console.log('[@EnhancedHLSPlayer] Fetching archive metadata:', metadataUrl);
      
      fetch(metadataUrl)
        .then(res => res.json())
        .then(data => {
          console.log('[@EnhancedHLSPlayer] Archive metadata loaded:', data);
          setArchiveMetadata(data);
          
          // Start at the first manifest (oldest, beginning of 24h archive)
          if (data.manifests && data.manifests.length > 0) {
            console.log(`[@EnhancedHLSPlayer] Starting at first manifest (archive1): 1/${data.manifests.length}`);
            setCurrentManifestIndex(0); // Start at archive1 (oldest)
          }
        })
        .catch(err => {
          console.warn('[@EnhancedHLSPlayer] Failed to load archive metadata, falling back to single manifest:', err);
          // Fallback to single manifest if metadata not available
          setArchiveMetadata(null);
        });
    }
  }, [isLiveMode, archiveMetadata, isTransitioning, providedStreamUrl, hookStreamUrl, deviceId]);

  // Build the appropriate stream URL based on mode and current manifest
  const streamUrl = useMemo(() => {
    // Live mode - use output.m3u8
    if (isLiveMode) {
      if (providedStreamUrl) {
        return providedStreamUrl.replace(/\/(output|archive.*?)\.m3u8$/, '/output.m3u8');
      }
      if (hookStreamUrl) {
        return hookStreamUrl.replace(/\/(output|archive.*?)\.m3u8$/, '/output.m3u8');
      }
      return `/host/stream/capture${deviceId === 'device1' ? '1' : '2'}/output.m3u8`;
    }
    
    // Archive mode - use dynamic manifests if metadata available
    if (archiveMetadata && archiveMetadata.manifests.length > 0) {
      const currentManifest = archiveMetadata.manifests[currentManifestIndex];
      if (currentManifest) {
        const baseUrl = providedStreamUrl || hookStreamUrl || `/host/stream/capture${deviceId === 'device1' ? '1' : '2'}/output.m3u8`;
        // Replace both output.m3u8 and archive*.m3u8 patterns
        const manifestUrl = baseUrl.replace(/\/(output|archive.*?)\.m3u8$/, `/${currentManifest.name}`);
        console.log(`[@EnhancedHLSPlayer] Using manifest ${currentManifest.name} (window ${currentManifest.window_index}), URL: ${manifestUrl}`);
        return manifestUrl;
      }
    }
    
    // Fallback to archive.m3u8 (single manifest mode)
    if (providedStreamUrl) {
      return providedStreamUrl.replace(/\/(output|archive.*?)\.m3u8$/, '/archive.m3u8');
    }
    if (hookStreamUrl) {
      return hookStreamUrl.replace(/\/(output|archive.*?)\.m3u8$/, '/archive.m3u8');
    }
    return `/host/stream/capture${deviceId === 'device1' ? '1' : '2'}/archive.m3u8`;
  }, [providedStreamUrl, hookStreamUrl, isLiveMode, deviceId, archiveMetadata, currentManifestIndex]);

  // Seek to live edge when switching to live mode
  const seekToLive = () => {
    if (videoRef.current) {
      const video = videoRef.current;
      if (video.duration && !isNaN(video.duration) && isFinite(video.duration)) {
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

  // Video event handlers for timeline and play state with manifest switching
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const handleTimeUpdate = () => {
      setCurrentTime(video.currentTime);
      
      // Calculate global time if using multi-manifest archive
      if (!isLiveMode && archiveMetadata && archiveMetadata.manifests.length > 0) {
        const currentManifest = archiveMetadata.manifests[currentManifestIndex];
        if (currentManifest) {
          const globalTime = currentManifest.start_time_seconds + video.currentTime;
          setGlobalCurrentTime(globalTime);
          
          // Check if we need to switch to next manifest
          // Pre-load when 90% through current manifest
          const progressRatio = video.currentTime / video.duration;
          if (progressRatio > 0.9 && !preloadedNextManifest) {
            const nextIndex = currentManifestIndex + 1;
            if (nextIndex < archiveMetadata.manifests.length) {
              console.log(`[@EnhancedHLSPlayer] Pre-loading next manifest (${nextIndex + 1}/${archiveMetadata.manifests.length})`);
              setPreloadedNextManifest(true);
            }
          }
          
          // Switch to next manifest when reaching the end
          if (video.currentTime >= video.duration - 1) {
            const nextIndex = currentManifestIndex + 1;
            if (nextIndex < archiveMetadata.manifests.length) {
              console.log(`[@EnhancedHLSPlayer] Switching to manifest ${nextIndex + 1}`);
              setCurrentManifestIndex(nextIndex);
              setPreloadedNextManifest(false);
              // Video will restart at beginning of next manifest
            }
          }
        }
      } else {
        // For live mode or single manifest, use video.currentTime directly
        setGlobalCurrentTime(video.currentTime);
      }
    };
    
    const handleDurationChange = () => {
      setDuration(video.duration);
      
      // When archive mode loads and we get duration, seek to beginning
      if (!isLiveMode && video.duration && !isNaN(video.duration)) {
        console.log(`[@EnhancedHLSPlayer] Archive mode loaded, seeking to beginning (0:00)`);
        video.currentTime = 0; // Start at beginning of archive
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
  }, [isLiveMode, archiveMetadata, currentManifestIndex, preloadedNextManifest]);

  // Handle mode changes and seeking
  useEffect(() => {
    const timer = setTimeout(() => {
      if (isLiveMode) {
        seekToLive();
      } else {
        // For archive mode, seek to beginning
        if (videoRef.current && videoRef.current.duration) {
          console.log(`[@EnhancedHLSPlayer] Mode change to archive, seeking to beginning (0:00)`);
          videoRef.current.currentTime = 0;
        }
      }
    }, 500); // Small delay to allow HLS player to initialize with new manifest
    
    return () => clearTimeout(timer);
  }, [isLiveMode]);

  // Archive timeline controls with multi-manifest seeking
  const handleSeek = useCallback((_event: Event, newValue: number | number[]) => {
    if (!videoRef.current || isLiveMode) return;
    
    const seekTime = Array.isArray(newValue) ? newValue[0] : newValue;
    if (!isFinite(seekTime) || seekTime < 0) return;
    
    const video = videoRef.current;
    const wasPlaying = !video.paused;
    
    // If using multi-manifest archive, find correct manifest and seek within it
    if (archiveMetadata && archiveMetadata.manifests.length > 0) {
      // Find which manifest contains this time
      let targetManifestIndex = -1;
      let targetLocalTime = 0;
      
      for (let i = 0; i < archiveMetadata.manifests.length; i++) {
        const manifest = archiveMetadata.manifests[i];
        // Handle seek to exact end of manifest (boundary case)
        const isAtEnd = seekTime >= manifest.end_time_seconds && i === archiveMetadata.manifests.length - 1;
        const isInRange = seekTime >= manifest.start_time_seconds && seekTime < manifest.end_time_seconds;
        
        if (isInRange || isAtEnd) {
          targetManifestIndex = i;
          targetLocalTime = seekTime - manifest.start_time_seconds;
          
          // Clamp to manifest duration to avoid seeking beyond
          const manifestDuration = manifest.duration_seconds;
          targetLocalTime = Math.min(targetLocalTime, manifestDuration - 0.1);
          
          console.log(`[@EnhancedHLSPlayer] User seek: global ${seekTime.toFixed(1)}s -> manifest ${manifest.window_index} at ${targetLocalTime.toFixed(1)}s`);
          break;
        }
      }
      
      if (targetManifestIndex === -1) {
        console.warn(`[@EnhancedHLSPlayer] Seek time ${seekTime}s not found in any manifest`);
        return;
      }
      
      // Switch manifest if needed
      if (targetManifestIndex !== currentManifestIndex) {
        console.log(`[@EnhancedHLSPlayer] Switching from manifest ${currentManifestIndex + 1} to ${targetManifestIndex + 1}`);
        
        // Pause video during manifest switch to prevent playback issues
        video.pause();
        
        setCurrentManifestIndex(targetManifestIndex);
        setPreloadedNextManifest(false);
        
        // Wait for new manifest to load, then seek and resume playback
        setTimeout(() => {
          if (videoRef.current) {
            videoRef.current.currentTime = targetLocalTime;
            
            // Resume playback if it was playing before seek
            if (wasPlaying) {
              videoRef.current.play().catch(err => {
                console.warn('[@EnhancedHLSPlayer] Failed to resume playback after manifest switch:', err);
              });
            }
          }
        }, 800); // Give HLS.js time to load new manifest
      } else {
        // Same manifest, just seek
        video.currentTime = targetLocalTime;
        
        // Video element automatically resumes if it was playing
      }
    } else {
      // Single manifest mode - simple seek
      video.currentTime = seekTime;
    }
  }, [isLiveMode, archiveMetadata, currentManifestIndex]);

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
        {!isTransitioning ? (
          <HLSVideoPlayer
            key={`${isLiveMode ? 'live' : 'archive'}-${streamUrl}`} // Force remount on mode OR URL change
            streamUrl={streamUrl}
            isStreamActive={true}
            videoElementRef={videoRef}
            muted={muted} // Use the muted prop from parent
            isArchiveMode={!isLiveMode} // Pass archive mode flag
            sx={{ width: '100%', height: '100%' }}
          />
        ) : (
          <Box
            sx={{
              width: '100%',
              height: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: 'black',
              color: 'white',
            }}
          >
            <Typography>Switching mode...</Typography>
          </Box>
        )}

        {/* Archive Timeline Overlay with integrated Play/Pause button */}
        {!isLiveMode && !isTransitioning && duration > 0 && (
          <Box
            sx={{
              position: 'absolute',
              bottom: -20, // Compensate for modal's 20px margin from window height
              left: 0,
              right: 0,
              background: 'linear-gradient(transparent, rgba(0,0,0,0.8))',
              p: 2,
            }}
          >
            {/* Timeline controls row */}
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1 }}>
              {/* Play/Pause Button */}
              <IconButton
                onClick={togglePlayPause}
                sx={{
                  backgroundColor: 'rgba(0, 0, 0, 0.6)',
                  color: 'white',
                  border: '2px solid rgba(255, 255, 255, 0.7)',
                  '&:hover': {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    border: '2px solid rgba(255, 255, 255, 1)',
                  },
                  minWidth: 40,
                  height: 40,
                }}
                size="small"
              >
                {isPlaying ? <Pause /> : <PlayArrow />}
              </IconButton>
              
              {/* Timeline Slider */}
              <Slider
                value={archiveMetadata ? globalCurrentTime : currentTime}
                max={archiveMetadata ? archiveMetadata.total_duration_seconds : duration}
                onChange={handleSeek}
                sx={{ 
                  color: 'primary.main', 
                  flex: 1,
                  '& .MuiSlider-thumb': {
                    width: 16,
                    height: 16,
                  }
                }}
              />
            </Box>
            
            {/* Time display row */}
            <Box sx={{ display: 'flex', justifyContent: 'space-between', pl: 7 }}>  
              <Typography variant="caption" sx={{ color: 'white' }}>
                {formatTime(archiveMetadata && archiveMetadata.manifests.length > 0 ? globalCurrentTime : currentTime)}
              </Typography>
              {archiveMetadata && (
                <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.6)' }}>
                  Manifest {currentManifestIndex + 1}/{archiveMetadata.manifests.length}
                </Typography>
              )}
              <Typography variant="caption" sx={{ color: 'white' }}>
                {formatTime(archiveMetadata ? archiveMetadata.total_duration_seconds : duration)}
              </Typography>
            </Box>
          </Box>
        )}
      </Box>
    </Box>
  );
};
