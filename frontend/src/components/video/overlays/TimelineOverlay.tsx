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

  // STANDARD TIMELINE: Slider value = globalCurrentTime (0 on left = past, 86400 on right = now)
  const sliderValue = !isLiveMode && archiveMetadata
    ? globalCurrentTime
    : globalCurrentTime;

  // Build rail gradient with grey gaps for archive mode (STANDARD: past on left, now on right)
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

    // Collect color stops as array of {percent: number, color: string}
    const colorStops: { percent: number; color: string }[] = [];

    // Iterate from oldest to newest (past to now, left to right)
    for (let hoursAgo = 23; hoursAgo >= 0; hoursAgo--) {
      const actualHour = (currentHour - hoursAgo + 24) % 24;
      const hourStartSeconds = (23 - hoursAgo) * 3600;  // 0 for oldest, increases to 82800 for newest

      for (let chunk = 0; chunk < 6; chunk++) {
        const key = `${actualHour}-${chunk}`;
        const hasChunk = allChunks[key];

        if (actualHour === currentHour || actualHour === 15) {
          console.log(`[@TimelineOverlay] Hour ${actualHour} (${hoursAgo}h ago), chunk ${chunk}: ${hasChunk ? 'AVAILABLE (blue)' : 'missing (grey)'}, key=${key}`);
        }

        const color = hasChunk
          ? 'rgb(104, 177, 255)'  // Bright electric cyan for available
          : 'rgb(207, 207, 207)'; // Light grey for missing

        const startSeconds = hourStartSeconds + chunk * 600;
        const endSeconds = startSeconds + 600;

        // Standard percentages: low on left (past), high on right (now)
        const startPercent = (startSeconds / totalSeconds) * 100;
        const endPercent = (endSeconds / totalSeconds) * 100;

        // For sharp transitions: add color at start, and same at end (solid block)
        colorStops.push({ percent: startPercent, color });
        colorStops.push({ percent: endPercent, color });
      }
    }

    // Sort by percentage ascending (should already be mostly sorted, but ensure)
    colorStops.sort((a, b) => a.percent - b.percent);

    // Remove the entire merging block
    // const mergedStops: { percent: number; color: string }[] = [];
    // colorStops.forEach(stop => {
    //   const last = mergedStops[mergedStops.length - 1];
    //   if (!last || last.color !== stop.color) {
    //     mergedStops.push(stop);
    //   } else {
    //     last.percent = stop.percent;
    //   }
    // });
    // const gradientParts = mergedStops.map(stop => `${stop.color} ${stop.percent.toFixed(2)}%`);

    // Restore simple mapping
    const gradientParts = colorStops.map(stop => `${stop.color} ${stop.percent.toFixed(2)}%`);

    const gradientString = `linear-gradient(to right, ${gradientParts.join(', ')})`;
    console.log(`[@TimelineOverlay] Final gradient: ${gradientString}`);

    return gradientString;
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
                  : (isDraggingSlider ? dragSliderValue : sliderValue);
                const minValue = isLiveMode ? 0 : 0;
                const maxValue = isLiveMode ? 150 : 86400;
                
                const percentage = ((currentValue - minValue) / (maxValue - minValue)) * 100;
                console.log(`[@TimelineOverlay] Tooltip: value=${currentValue.toFixed(0)}s, percentage=${percentage.toFixed(2)}%`); // Debug log
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
                  if (behindSeconds === 0) return 'Live';
                  if (behindSeconds < 60) return `-${behindSeconds}s`;
                  const minutes = Math.floor(behindSeconds / 60);
                  const seconds = behindSeconds % 60;
                  return `-${minutes}:${seconds.toString().padStart(2, '0')}`;
                })()
              ) : (
                // Show actual time directly
                (() => {
                  const tooltipTime = isDraggingSlider ? dragSliderValue : sliderValue;
                  console.log(`[@TimelineOverlay] Tooltip time: ${formatTime(tooltipTime)} (${tooltipTime.toFixed(0)}s)`); // Debug
                  return formatTime(tooltipTime)
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
                const sliderValue = Array.isArray(value) ? value[0] : value;
                // No inversion needed - sliderValue is now actual time
                const seekTime = sliderValue;

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
