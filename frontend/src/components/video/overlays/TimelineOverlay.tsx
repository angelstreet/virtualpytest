import React, { useMemo } from 'react';
import { createPortal } from 'react-dom';
import { Box, Slider, Typography, IconButton } from '@mui/material';
import { PlayArrow, Pause } from '@mui/icons-material';
import { ArchiveMetadata } from '../EnhancedHLSPlayer.types';
import { getZIndex } from '../../../utils/zIndexUtils';

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
  if (!seconds || !isFinite(seconds)) return '0h00:00';
  const hours = Math.floor(seconds / 3600) % 24;
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);
  return `${hours}h${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
};

const getRoundedNow = () => {
  const now = new Date();
  const currentHour = now.getHours();
  const currentMinute = now.getMinutes();
  const roundedMinute = Math.floor(currentMinute / 10) * 10;
  return currentHour * 3600 + roundedMinute * 60;
};

const positionToClockTime = (position: number, roundedNow: number) => {
  return ((roundedNow - 86400) + position + 86400) % 86400;
};

const clockTimeToPosition = (clockTime: number, roundedNow: number) => {
  return (clockTime - (roundedNow - 86400) + 86400) % 86400;
};

export const TimelineOverlay: React.FC<TimelineOverlayProps> = ({
  isLiveMode,
  isPlaying,
  currentTime: _currentTime,
  duration,
  isAtLiveEdge: _isAtLiveEdge,
  liveBufferSeconds,
  liveSliderPosition,
  globalCurrentTime,
  isDraggingSlider,
  dragSliderValue,
  archiveMetadata,
  availableHours: _availableHours,
  continuousStartTime: _continuousStartTime,
  continuousEndTime: _continuousEndTime,
  hourMarks,
  videoRef: _videoRef,
  onTogglePlayPause,
  onSliderChange,
  onSeek,
  show,
  currentManifestIndex,
  containerRef: _containerRef,
}) => {
  if (!show || duration <= 0) {
    return null;
  }

  const min = isLiveMode ? 0 : 0;
  const max = isLiveMode ? 150 : 86400;

  const sliderValue = useMemo(() => {
    if (isLiveMode || !archiveMetadata) {
      return globalCurrentTime;
    }
    const roundedNow = getRoundedNow();
    return clockTimeToPosition(globalCurrentTime, roundedNow);
  }, [isLiveMode, archiveMetadata, globalCurrentTime]);

  const archiveRailGradient = useMemo(() => {
    if (isLiveMode || !archiveMetadata || archiveMetadata.manifests.length === 0) {
      return 'rgba(255,255,255,0.15)';
    }

    const roundedNow = getRoundedNow();
    const allChunks: { [key: string]: boolean } = {};
    archiveMetadata.manifests.forEach(manifest => {
      const key = `${manifest.window_index}-${manifest.chunk_index}`;
      allChunks[key] = true;
    });

    // Mark current building chunk as available (progressive build)
    const now = new Date();
    const currentHour = now.getHours();
    const currentChunkIndex = Math.floor(now.getMinutes() / 10);
    const currentKey = `${currentHour}-${currentChunkIndex}`;
    allChunks[currentKey] = true;

    const colorStops: { percent: number; color: string }[] = [];

    for (let i = 0; i < 144; i++) {
      const chunkStartPosition = i * 600;
      const chunkEndPosition = (i + 1) * 600;
      
      const chunkClockTime = positionToClockTime(chunkStartPosition, roundedNow);
      const hour = Math.floor(chunkClockTime / 3600);
      const chunk = Math.floor((chunkClockTime % 3600) / 600);
      const key = `${hour}-${chunk}`;
      
      const color = allChunks[key] ? 'rgb(104, 177, 255)' : 'rgb(207, 207, 207)';
      const startPercent = (chunkStartPosition / 86400) * 100;
      const endPercent = (chunkEndPosition / 86400) * 100;
      
      colorStops.push({ percent: startPercent, color });
      colorStops.push({ percent: endPercent, color });
    }

    const gradientParts = colorStops.map(stop => `${stop.color} ${stop.percent.toFixed(2)}%`);
    return `linear-gradient(to right, ${gradientParts.join(', ')})`;
  }, [isLiveMode, archiveMetadata]);

  const isTimeAvailable = (timeSeconds: number): boolean => {
    if (!archiveMetadata || archiveMetadata.manifests.length === 0) return false;
    const hour = Math.floor(timeSeconds / 3600);
    const chunk = Math.floor((timeSeconds % 3600) / 600);
    const key = `${hour}-${chunk}`;
    
    // Check if it's the current building chunk
    const now = new Date();
    const currentHour = now.getHours();
    const currentChunkIndex = Math.floor(now.getMinutes() / 10);
    const isCurrentChunk = hour === currentHour && chunk === currentChunkIndex;
    
    return isCurrentChunk || archiveMetadata.manifests.some(
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
    background: 'transparent',
    padding: '8px 16px 8px 16px', // Reduced vertical padding
    zIndex: getZIndex('TIMELINE_OVERLAY'), // Above modals but below interactive overlays
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
              top: -20,  // Position above the slider/thumb
              left: (() => {
                const currentValue = isLiveMode 
                  ? (isDraggingSlider ? dragSliderValue : liveSliderPosition)
                  : (isDraggingSlider ? dragSliderValue : sliderValue);
                const minValue = isLiveMode ? 0 : 0;
                const maxValue = isLiveMode ? 150 : 82800;  // Match the slider max
                
                // Calculate percentage (0-100)
                const percentage = ((currentValue - minValue) / (maxValue - minValue)) * 100;
                
                // Clamp percentage to prevent tooltip from going off-screen
                // Leave some margin (5% on each side = ~40-50px depending on screen width)
                const clampedPercentage = Math.max(5, Math.min(95, percentage));
                
                return `${clampedPercentage}%`;
              })(),
              transform: 'translateX(-50%)',  // Center the tooltip on its position
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
                  if (behindSeconds === 0) return 'Live';
                  if (behindSeconds < 60) return `-${behindSeconds}s`;
                  const minutes = Math.floor(behindSeconds / 60);
                  const seconds = behindSeconds % 60;
                  return `-${minutes}:${seconds.toString().padStart(2, '0')}`;
                })()
              ) : (
                (() => {
                  const roundedNow = getRoundedNow();
                  const displayTime = isDraggingSlider 
                    ? positionToClockTime(dragSliderValue, roundedNow)
                    : globalCurrentTime;
                  return formatTime(displayTime);
                })()
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
              : (isDraggingSlider ? dragSliderValue : sliderValue)
            }
            min={min}
            max={max}
            step={isLiveMode ? 1 : undefined}
            disabled={isLiveMode && liveBufferSeconds < 10}
            track={isLiveMode ? false : false}  // No progress track - only rail with availability gradient
            onChange={onSliderChange}
            onChangeCommitted={(event, value) => {
              if (!isLiveMode) {
                const positionValue = Array.isArray(value) ? value[0] : value;
                const roundedNow = getRoundedNow();
                const seekTime = positionToClockTime(positionValue, roundedNow);

                // Check if seeking to current building chunk (last 10min window)
                const now = new Date();
                const currentHour = now.getHours();
                const currentMinute = now.getMinutes();
                const currentChunkIndex = Math.floor(currentMinute / 10);
                const currentChunkStartTime = currentHour * 3600 + currentChunkIndex * 600;
                const isCurrentChunk = seekTime >= currentChunkStartTime && seekTime < currentChunkStartTime + 600;

                // Allow seeking to current building chunk (even if incomplete)
                if (isCurrentChunk) {
                  onSeek(event, seekTime);
                  return;
                }

                if (isTimeAvailable(seekTime)) {
                  onSeek(event, seekTime);
                  return;
                }

                // Find nearest available chunk (but prefer recent chunks over yesterday)
                let nearestTime = null;
                let minDiff = Infinity;

                if (archiveMetadata && archiveMetadata.manifests) {
                  archiveMetadata.manifests.forEach(manifest => {
                    const chunkStartTime = manifest.window_index * 3600 + manifest.chunk_index * 600;
                    const diff = Math.abs(chunkStartTime - seekTime);
                    
                    // Prefer chunks within 1 hour over wrapping to yesterday
                    const timeDiff = seekTime - chunkStartTime;
                    const isRecent = timeDiff >= -3600 && timeDiff <= 3600;
                    const adjustedDiff = isRecent ? diff : diff + 86400;
                    
                    if (adjustedDiff < minDiff) {
                      minDiff = adjustedDiff;
                      nearestTime = chunkStartTime;
                    }
                  });
                }

                if (nearestTime !== null) {
                  onSeek(event, nearestTime);
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
