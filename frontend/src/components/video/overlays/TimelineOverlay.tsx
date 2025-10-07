import React from 'react';
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
  if (!seconds || !isFinite(seconds)) return '0:00';
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);
  return hours > 0 
    ? `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
    : `${minutes}:${secs.toString().padStart(2, '0')}`;
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
  
  // Build rail gradient with grey gaps for archive mode
  const buildArchiveRailGradient = () => {
    if (isLiveMode || !archiveMetadata || archiveMetadata.manifests.length === 0) {
      return 'rgba(255,255,255,0.15)';
    }
    
    // Calculate ALL 144 possible 10-minute chunks in 24h
    const allChunkPositions: { [key: string]: boolean } = {};
    archiveMetadata.manifests.forEach(manifest => {
      const key = `${manifest.window_index}-${manifest.chunk_index}`;
      allChunkPositions[key] = true;
    });
    
    // Build gradient with available (white) and gap (grey) segments
    const gradientParts: string[] = [];
    const totalSeconds = 24 * 3600; // 24 hours
    
    for (let hour = 0; hour < 24; hour++) {
      for (let chunk = 0; chunk < 6; chunk++) {
        const key = `${hour}-${chunk}`;
        const hasChunk = allChunkPositions[key];
        
        const startSeconds = hour * 3600 + chunk * 600;
        const endSeconds = startSeconds + 600;
        const startPercent = (startSeconds / totalSeconds) * 100;
        const endPercent = (endSeconds / totalSeconds) * 100;
        
        const color = hasChunk 
          ? 'rgba(255,255,255,0.15)'  // Available chunk (normal)
          : 'rgba(100,100,100,0.3)';   // Gap (greyed out)
        
        gradientParts.push(`${color} ${startPercent}%`);
        gradientParts.push(`${color} ${endPercent}%`);
      }
    }
    
    return `linear-gradient(to right, ${gradientParts.join(', ')})`;
  };

  // Timeline positioned at bottom of viewport, completely independent of container
  const timelineStyle = {
    position: 'fixed' as const,
    left: 0,
    right: 0,
    bottom: 0,
    width: '100%',
    background: 'linear-gradient(transparent, rgba(0,0,0,0.85))',
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
          {isDraggingSlider && (
            <Box
              sx={{
                position: 'absolute',
                bottom: 25,
                left: (() => {
                  const currentValue = isLiveMode 
                    ? dragSliderValue
                    : dragSliderValue;
                  const minValue = isLiveMode ? 0 : 0;
                  const maxValue = isLiveMode ? 150 : 86400;
                  
                  const percentage = ((currentValue - minValue) / (maxValue - minValue)) * 100;
                  return `calc(${percentage}% - 25px)`;
                })(),
                transform: 'translateX(0)',
                pointerEvents: 'none',
                zIndex: 10,
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
                    const behindSeconds = Math.round(150 - dragSliderValue);
                    if (behindSeconds < 60) return `-${behindSeconds}s`;
                    const minutes = Math.floor(behindSeconds / 60);
                    const seconds = behindSeconds % 60;
                    return `-${minutes}:${seconds.toString().padStart(2, '0')}`;
                  })()
                ) : (
                  formatTime(dragSliderValue)
                )}
              </Typography>
            </Box>
          )}

          <Slider
            value={isLiveMode ? (isDraggingSlider ? dragSliderValue : liveSliderPosition) : (isDraggingSlider ? dragSliderValue : (archiveMetadata ? globalCurrentTime : currentTime))}
            min={min}
            max={max}
            step={isLiveMode ? 1 : undefined}
            disabled={isLiveMode && liveBufferSeconds < 10}
            onChange={onSliderChange}
            onChangeCommitted={onSeek}
            marks={!isLiveMode ? hourMarks : []}
            sx={{ 
              color: isLiveMode ? 'error.main' : 'primary.main',
              flex: 1,
              '& .MuiSlider-thumb': {
                width: 16,
                height: 16,
              },
              '& .MuiSlider-track': {
                backgroundColor: isLiveMode ? 'transparent' : 'primary.main',
                height: 6,
              },
              '& .MuiSlider-rail': {
                backgroundColor: 'rgba(255,255,255,0.15)',
                height: 6,
                background: isLiveMode 
                  ? `linear-gradient(to right, 
                      rgba(255,255,255,0.15) 0%, 
                      rgba(255,255,255,0.15) ${Math.max(0, ((150 - liveBufferSeconds) / 150) * 100)}%, 
                      rgba(244,67,54,0.8) ${Math.max(0, ((150 - liveBufferSeconds) / 150) * 100)}%,
                      rgba(244,67,54,0.8) 100%
                    )`
                  : buildArchiveRailGradient(),
              },
              '& .MuiSlider-markLabel': {
                fontSize: '0.7rem',
                color: 'rgba(255,255,255,0.7)'
              }
            }}
          />
        </Box>
      </Box>
      
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', pl: !isLiveMode ? 7 : 0, pr: 2, mt: -2 }}>  
        {isLiveMode ? (
          <>
            <Typography variant="caption" sx={{ color: 'white', minWidth: '60px', fontSize: '0.7rem' }}>
              -2:30
            </Typography>
            
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
            
            <Typography variant="caption" sx={{ color: 'white', minWidth: '60px', textAlign: 'right' }}>
              Now
            </Typography>
          </>
        ) : (
          <>
            <Typography variant="caption" sx={{ color: 'white', minWidth: '60px', fontSize: '0.7rem' }}>
              0:00
            </Typography>
            
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
            
            <Typography variant="caption" sx={{ color: 'white', minWidth: '60px', textAlign: 'right' }}>
              24:00
            </Typography>
          </>
        )}
      </Box>
    </Box>
  );

  // Render timeline via portal to avoid parent overflow clipping
  return createPortal(timelineContent, document.body);
};
