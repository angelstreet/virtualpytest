import React from 'react';
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
  isAtLiveEdge,
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
  videoRef,
  onTogglePlayPause,
  onSliderChange,
  onSeek,
  show,
  currentManifestIndex,
}) => {
  if (!show || duration <= 0) {
    return null;
  }

  // Calculate timeline range
  const min = isLiveMode ? 0 : (continuousStartTime || 0);
  const max = isLiveMode ? 150 : (continuousEndTime || duration);
  
  // For archive mode, we want to show full 24h range but restrict interaction
  const displayMin = isLiveMode ? min : 0;
  const displayMax = isLiveMode ? max : (24 * 3600);

  return (
    <Box
        sx={{
          position: 'absolute',
          bottom: -65,
          left: 0,
          right: 0,
          background: 'linear-gradient(transparent, rgba(0,0,0,0.8))',
          p: 2,
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 0.5 }}>
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
                    : (archiveMetadata ? globalCurrentTime : currentTime);
                  const minValue = isLiveMode ? 0 : (archiveMetadata && availableHours.length > 0 ? availableHours[0] * 3600 : 0);
                  const maxValue = isLiveMode ? 150 : (archiveMetadata && availableHours.length > 0 ? (availableHours[availableHours.length - 1] + 1) * 3600 : duration);
                  
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
                backgroundColor: isLiveMode ? undefined : 'primary.main',
                background: isLiveMode ? `linear-gradient(to right, 
                  rgba(255,255,255,0.15) 0%, 
                  rgba(255,255,255,0.15) ${Math.max(0, ((150 - liveBufferSeconds) / 150) * 100)}%, 
                  rgba(244,67,54,0.8) ${Math.max(0, ((150 - liveBufferSeconds) / 150) * 100)}%,
                  rgba(244,67,54,0.8) 100%
                )` : undefined,
                height: 6,
              },
              '& .MuiSlider-rail': {
                backgroundColor: 'rgba(255,255,255,0.15)',
                height: 6,
                background: !isLiveMode && continuousStartTime > 0 && continuousEndTime > 0 
                  ? `linear-gradient(to right,
                      rgba(100,100,100,0.3) 0%,
                      rgba(100,100,100,0.3) ${(continuousStartTime / max) * 100}%,
                      rgba(255,255,255,0.15) ${(continuousStartTime / max) * 100}%,
                      rgba(255,255,255,0.15) ${(continuousEndTime / max) * 100}%,
                      rgba(100,100,100,0.3) ${(continuousEndTime / max) * 100}%,
                      rgba(100,100,100,0.3) 100%
                    )`
                  : undefined,
              },
              '& .MuiSlider-markLabel': {
                fontSize: '0.7rem',
                color: 'rgba(255,255,255,0.7)'
              }
            }}
          />
        </Box>
      </Box>
      
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', pl: !isLiveMode ? 7 : 0, pr: 2, mt: -1 }}>  
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
            <Box sx={{ minWidth: '60px' }} />
            
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
              {(() => {
                if (archiveMetadata && availableHours.length > 0) {
                  const lastManifest = archiveMetadata.manifests[archiveMetadata.manifests.length - 1];
                  if (lastManifest) {
                    const hour = lastManifest.window_index;
                    const chunk = lastManifest.chunk_index;
                    // Calculate END time of the last chunk (chunk_index + 1) * 10
                    const minutes = (chunk + 1) * 10;
                    return `${hour}h${minutes.toString().padStart(2, '0')}`;
                  }
                }
                return formatTime(duration);
              })()}
            </Typography>
          </>
        )}
      </Box>
    </Box>
  );
};
