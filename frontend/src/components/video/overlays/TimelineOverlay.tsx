import React, { useMemo } from 'react';
import { createPortal } from 'react-dom';
import { Box, Slider, Typography, IconButton } from '@mui/material';
import { PlayArrow, Pause } from '@mui/icons-material';
import { ArchiveMetadata } from '../EnhancedHLSPlayer.types';

interface TimelineOverlayProps {
  isLiveMode: boolean;
  isPlaying: boolean;
  currentTime: number;
  duration: number;
  isAtLiveEdge: boolean;
  liveBufferSeconds: number;
  liveSliderPosition: number;
  globalCurrentTime: number;
  isDraggingSlider: boolean;
  dragSliderValue: number;
  archiveMetadata: ArchiveMetadata | null;
  availableHours: number[];
  continuousStartTime: number;
  continuousEndTime: number;
  hourMarks: Array<{ value: number; label: string; style?: React.CSSProperties }>;
  videoRef: React.RefObject<HTMLVideoElement>;
  onTogglePlayPause: () => void;
  onSliderChange: (_event: Event | React.SyntheticEvent, newValue: number | number[]) => void;
  onSeek: (_event: Event | React.SyntheticEvent, newValue: number | number[]) => void;
  show: boolean;
  currentManifestIndex: number;
  containerRef: React.RefObject<HTMLDivElement>; // Reference to the video container for positioning
}

const formatTime = (seconds: number) => {
  if (!seconds || !isFinite(seconds)) return '0h00';
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  return `${hours}h${minutes.toString().padStart(2, '0')}`;
};

export const TimelineOverlay: React.FC<TimelineOverlayProps> = ({
  isLiveMode,
  isPlaying,
  currentTime,
  duration,
  isAtLiveEdge: _isAtLiveEdge, // Unused but kept for future use
  liveBufferSeconds,
  liveSliderPosition,
  globalCurrentTime,
  isDraggingSlider,
  dragSliderValue,
  archiveMetadata,
  availableHours,
  continuousStartTime,
  continuousEndTime,
  hourMarks,
  videoRef: _videoRef, // Unused but kept for future use
  onTogglePlayPause,
  onSliderChange,
  onSeek,
  show,
  currentManifestIndex,
  containerRef,
}) => {
  if (!show || duration <= 0) {
    return null;
  }

  // Calculate timeline range - always full 24h for archive mode
  const min = isLiveMode ? 0 : 0;           // Always start at 0 (midnight)
  const max = isLiveMode ? 150 : 86400;     // 24h = 86400 seconds
  
  // INVERTED TIMELINE: Convert globalCurrentTime (0-86400) to inverted slider value
  // globalCurrentTime=0 (hour 0/midnight) -> slider=86400 (right side)
  // globalCurrentTime=86400 (24h later) -> slider=0 (left side)
  const invertedSliderValue = !isLiveMode && archiveMetadata 
    ? 86400 - globalCurrentTime 
    : globalCurrentTime;
  
  // Build rail gradient with grey gaps for archive mode (INVERTED: now on right, past on left)
  // Memoized to prevent infinite render loop
  const archiveRailGradient = useMemo(() => {
    if (isLiveMode || !archiveMetadata || archiveMetadata.manifests.length === 0) {
      return 'rgba(255,255,255,0.15)';
    }
    
    const totalSeconds = 86400;
    const now = new Date();
    const currentHour = now.getHours();
    
    const allChunks: { [key: string]: boolean } = {};
    archiveMetadata.manifests.forEach(manifest => {
      const key = `${manifest.window_index}-${manifest.chunk_index}`;
      allChunks[key] = true;
    });
    
    console.log(`[@TimelineOverlay] Building gradient with ${Object.keys(allChunks).length} chunks:`, Object.keys(allChunks));
    console.log(`[@TimelineOverlay] Current hour: ${currentHour}`);
    
    // Build gradient with hard edges (no smooth transitions)
    const gradientParts: string[] = [];
    
    // Iterate over the last 24 hours, matching the hour marks logic
    for (let hoursAgo = 23; hoursAgo >= 0; hoursAgo--) {
      // Calculate the actual hour for this position (matching hour marks logic)
      const actualHour = (currentHour - hoursAgo + 24) % 24;
      
      // Position in seconds: hoursAgo=0 (now) starts at 82800s (last hour), hoursAgo=23 starts at 0s (first hour)
      const hourStartSeconds = (23 - hoursAgo) * 3600;
      
      for (let chunk = 0; chunk < 6; chunk++) {
        const key = `${actualHour}-${chunk}`;
        const hasChunk = allChunks[key];
        
        // Debug logging for the current hour and hour 15
        if (actualHour === currentHour || actualHour === 15) {
          console.log(`[@TimelineOverlay] Hour ${actualHour} (${hoursAgo}h ago), chunk ${chunk}: ${hasChunk ? 'AVAILABLE (blue)' : 'missing (grey)'}, key=${key}`);
        }
        
        // Only 2 colors: available (bright cyan) or missing (light grey) - both fully opaque
        const color = hasChunk
          ? 'rgb(104, 177, 255)'  // Bright electric cyan for available chunks - fully opaque
          : 'rgb(207, 207, 207)';    // Light grey for missing chunks - fully opaque, no transparency
        
        const startSeconds = hourStartSeconds + chunk * 600;
        const endSeconds = startSeconds + 600;
        
        // Calculate percentages (inverted: past on left, now on right)
        const startPercent = (100 - (startSeconds / totalSeconds) * 100).toFixed(2);
        const endPercent = (100 - (endSeconds / totalSeconds) * 100).toFixed(2);
        
        // Create HARD EDGES by putting both color stops at same position
        // Format: "color start%, color end%"
        gradientParts.push(`${color} ${endPercent}%`);
        gradientParts.push(`${color} ${startPercent}%`);
      }
    }
    
    return `linear-gradient(to right, ${gradientParts.join(', ')})`;
  }, [isLiveMode, archiveMetadata]);

  // Check if a given time (in seconds from midnight) has an available chunk
  const isTimeAvailable = (timeSeconds: number): boolean => {
    if (!archiveMetadata || archiveMetadata.manifests.length === 0) return false;
    
    const hour = Math.floor(timeSeconds / 3600);
    const chunk = Math.floor((timeSeconds % 3600) / 600);
    const key = `${hour}-${chunk}`;
    
    return archiveMetadata.manifests.some(
      manifest => `${manifest.window_index}-${manifest.chunk_index}` === key
    );
  };

  // Timeline positioned at bottom of viewport, completely independent of container
  const timelineStyle = {
    position: 'fixed' as const,
    left: 0,
    right: 0,
    bottom: 0,
    width: '100%',
    background: 'rgba(0,0,0,1)', // Solid dark background, no gradient
    padding: '8px 16px 8px 16px', // Reduced vertical padding
    zIndex: 1300, // High z-index to be above everything
    pointerEvents: 'auto' as const,
  };

  const timelineContent = (
    <Box
        sx={timelineStyle}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 0 }}>
        {!isLiveMode && (
          <IconButton
            onClick={onTogglePlayPause}
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
        )}
        
        <Box
          sx={{
            position: 'relative',
            flex: 1,
          }}
        >
          {/* Always show tooltip on top of thumb */}
          <Box
            sx={{
              position: 'absolute',
              top: -40,  // Position above the slider/thumb
              left: (() => {
                const currentValue = isLiveMode 
                  ? (isDraggingSlider ? dragSliderValue : liveSliderPosition)
                  : (isDraggingSlider ? dragSliderValue : invertedSliderValue);
                const minValue = isLiveMode ? 0 : 0;
                const maxValue = isLiveMode ? 150 : 86400;
                
                const percentage = ((currentValue - minValue) / (maxValue - minValue)) * 100;
                return `calc(${percentage}% - 40px)`;  // Subtract ~half the tooltip width for centering
              })(),
              transform: 'translateX(0)',
              pointerEvents: 'none',
              zIndex: 10,  // High z-index to ensure it's above everything
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
            }}
          >
            <Typography
              variant="caption"
              sx={{
                backgroundColor: 'rgba(0, 0, 0, 0.9)',
                color: 'white',
                px: 1,
                py: 0.5,
                borderRadius: 1,
                fontWeight: 600,
                fontSize: '0.7rem',
                whiteSpace: 'nowrap',
              }}
            >
              {isLiveMode ? (
                (() => {
                  if (liveBufferSeconds === 0) return 'Buffering...';
                  const behindSeconds = Math.round(150 - (isDraggingSlider ? dragSliderValue : liveSliderPosition));
                  if (behindSeconds < 60) return `-${behindSeconds}s`;
                  const minutes = Math.floor(behindSeconds / 60);
                  const seconds = behindSeconds % 60;
                  return `-${minutes}:${seconds.toString().padStart(2, '0')}`;
                })()
              ) : (
                // Show actual time (convert from inverted slider value)
                formatTime(86400 - (isDraggingSlider ? dragSliderValue : invertedSliderValue))
              )}
            </Typography>
            {/* Downward arrow to point at the thumb */}
            <Box
              sx={{
                width: 0,
                height: 0,
                borderLeft: '6px solid transparent',
                borderRight: '6px solid transparent',
                borderTop: '6px solid rgba(0, 0, 0, 0.9)',  // Matches tooltip background
                mt: -1,  // Pull it up to connect seamlessly
              }}
            />
          </Box>

          <Slider
            value={isLiveMode 
              ? (isDraggingSlider ? dragSliderValue : liveSliderPosition) 
              : (isDraggingSlider ? dragSliderValue : invertedSliderValue)
            }
            min={min}
            max={max}
            step={isLiveMode ? 1 : undefined}
            disabled={isLiveMode && liveBufferSeconds < 10}
            track={isLiveMode ? false : false}  // No progress track - only rail with availability gradient
            onChange={onSliderChange}
            onChangeCommitted={(event, value) => {
              if (!isLiveMode) {
                const sliderValue = Array.isArray(value) ? value[0] : value;
                // Convert inverted slider value back to actual time
                const seekTime = 86400 - sliderValue;

                if (isTimeAvailable(seekTime)) {
                  // If available, seek normally
                  onSeek(event, seekTime);
                  return;
                }

                // If unavailable, find nearest available chunk
                let nearestTime = null;
                let minDiff = Infinity;

                if (archiveMetadata && archiveMetadata.manifests) {
                  archiveMetadata.manifests.forEach(manifest => {
                    const chunkStartTime = manifest.window_index * 3600 + manifest.chunk_index * 600;
                    const diff = Math.abs(chunkStartTime - seekTime);
                    if (diff < minDiff) {
                      minDiff = diff;
                      nearestTime = chunkStartTime;
                    }
                  });
                }

                if (nearestTime !== null) {
                  console.log(`[@TimelineOverlay] Snapping to nearest available: ${nearestTime}s`);
                  onSeek(event, nearestTime);
                } else {
                  console.warn('[@TimelineOverlay] No available chunks to snap to');
                  // Optional: Reset to current position or earliest available
                }
                return;
              }
              onSeek(event, value);
            }}
            marks={!isLiveMode ? hourMarks : []}
            sx={{ 
              color: isLiveMode ? 'error.main' : 'primary.main',
              flex: 1,
              '& .MuiSlider-thumb': {
                width: 16,
                height: 16,
                zIndex: 3,  // Increase from 2 to 3 (or higher if still obscured)
                boxShadow: '0 0 4px rgba(0,0,0,0.5)',  // Add subtle shadow for visibility
                border: '1px solid white',  // Optional: Add a border to make it stand out more
              },
              '& .MuiSlider-track': {
                // Hide track completely - we only want the rail to show availability
                display: 'none',
              },
              '& .MuiSlider-rail': {
                height: 8,
                zIndex: 1,  // Explicitly set lower than thumb to ensure layering
                borderRadius: '4px',
                border: '1px solid rgba(255, 255, 255, 0.3)',  // Slightly more visible border
                opacity: 1,  // Force full opacity
                background: isLiveMode 
                  ? (() => {
                      const bufferPercent = Math.max(0, ((150 - liveBufferSeconds) / 150) * 100);
                      return `linear-gradient(to right, 
                        rgba(255,255,255,0.15) 0%, 
                        rgba(255,255,255,0.15) ${bufferPercent}%, 
                        rgba(244,67,54,1) ${bufferPercent}%,
                        rgba(244,67,54,1) 100%
                      )`;
                    })()
                  : archiveRailGradient,
              },
              '& .MuiSlider-markLabel': {
                fontSize: '0.7rem',
                color: 'rgba(255,255,255,0.7)'
              }
            }}
          />
        </Box>
      </Box>
      
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', mt: -2 }}>  
        {isLiveMode ? (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            {liveBufferSeconds > 0 && liveBufferSeconds < 150 && (
              <Typography variant="caption" sx={{ color: 'rgba(255, 255, 255, 0.7)', fontSize: '0.7rem' }}>
                Buffer: {Math.floor(liveBufferSeconds)}s
              </Typography>
            )}
            <Typography variant="caption" sx={{ color: 'white', fontWeight: 600, fontSize: '0.75rem' }}>
              {(() => {
                const behindSeconds = Math.round(150 - liveSliderPosition);
                if (behindSeconds === 0) return 'LIVE';
                if (behindSeconds < 60) return `-${behindSeconds}s`;
                const minutes = Math.floor(behindSeconds / 60);
                const seconds = behindSeconds % 60;
                return `-${minutes}:${seconds.toString().padStart(2, '0')}`;
              })()}
            </Typography>
          </Box>
        ) : (
          <>
            {archiveMetadata && (
              <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.6)', textAlign: 'center' }}>
                {(() => {
                  if (archiveMetadata.manifests.length === 0) return 'No archive available';
                  const totalMinutes = archiveMetadata.manifests.length * 10;
                  const hours = Math.floor(totalMinutes / 60);
                  const minutes = totalMinutes % 60;
                  let durationStr = '';
                  if (hours > 0) durationStr += `${hours}h`;
                  if (minutes > 0) durationStr += `${minutes}min`;
                  return `${durationStr} available`;
                })()} • Chunk {currentManifestIndex + 1}/{archiveMetadata.manifests.length}
              </Typography>
            )}
          </>
        )}
      </Box>
    </Box>
  );

  // Render timeline via portal to avoid parent overflow clipping
  return createPortal(timelineContent, document.body);
};
