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
  userBufferPosition: number;
  globalCurrentTime: number;
  isDraggingSlider: boolean;
  dragSliderValue: number;
  archiveMetadata: ArchiveMetadata | null;
  availableHours: number[];
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
  userBufferPosition,
  globalCurrentTime,
  isDraggingSlider,
  dragSliderValue,
  archiveMetadata,
  availableHours,
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

  return (
    <Box
      sx={{
        position: 'absolute',
        bottom: -45,
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
                    ? (isDraggingSlider ? dragSliderValue : userBufferPosition)
                    : (isDraggingSlider ? dragSliderValue : (archiveMetadata ? globalCurrentTime : currentTime));
                  const minValue = isLiveMode ? 0 : (archiveMetadata && availableHours.length > 0 ? availableHours[0] * 3600 : 0);
                  const maxValue = isLiveMode ? 1 : (archiveMetadata && availableHours.length > 0 ? (availableHours[availableHours.length - 1] + 1) * 3600 : duration);
                  
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
                    const video = videoRef.current;
                    let totalBufferSeconds = 0;
                    
                    if (video && video.buffered.length > 0) {
                      const buffered = video.buffered;
                      const bufferStart = buffered.start(0);
                      const bufferEnd = buffered.end(buffered.length - 1);
                      totalBufferSeconds = bufferEnd - bufferStart;
                    }
                    
                    const behindSeconds = Math.round((1 - dragSliderValue) * totalBufferSeconds);
                    if (behindSeconds < 5) {
                      return 'LIVE';
                    } else if (behindSeconds < 60) {
                      return `-${behindSeconds}s`;
                    } else {
                      const minutes = Math.floor(behindSeconds / 60);
                      const seconds = behindSeconds % 60;
                      return `-${minutes}:${seconds.toString().padStart(2, '0')}`;
                    }
                  })()
                ) : (
                  formatTime(dragSliderValue)
                )}
              </Typography>
            </Box>
          )}

          <Slider
            value={(() => {
              if (isLiveMode) {
                return isDraggingSlider ? dragSliderValue : userBufferPosition;
              } else {
                return isDraggingSlider ? dragSliderValue : (archiveMetadata ? globalCurrentTime : currentTime);
              }
            })()}
            min={isLiveMode ? 0 : (archiveMetadata && availableHours.length > 0 ? availableHours[0] * 3600 : 0)}
            max={(() => {
              if (isLiveMode) {
                return 1;
              } else {
                return archiveMetadata && availableHours.length > 0 ? (availableHours[availableHours.length - 1] + 1) * 3600 : duration;
              }
            })()}
            step={isLiveMode ? 0.01 : undefined}
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
                backgroundColor: isLiveMode ? 'error.main' : 'primary.main'
              },
              '& .MuiSlider-markLabel': {
                fontSize: '0.7rem',
                color: 'rgba(255,255,255,0.7)'
              }
            }}
          />
        </Box>
      </Box>
      
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', pl: !isLiveMode ? 7 : 0, pr: 2 }}>  
        {isLiveMode ? (
          <>
            <Typography variant="caption" sx={{ color: 'white', minWidth: '60px' }}>
              {(() => {
                const video = videoRef.current;
                if (video && video.buffered.length > 0) {
                  const buffered = video.buffered;
                  const bufferStart = buffered.start(0);
                  const bufferEnd = buffered.end(buffered.length - 1);
                  const totalBufferSeconds = Math.floor(bufferEnd - bufferStart);
                  
                  if (totalBufferSeconds < 60) {
                    return `-${totalBufferSeconds}s`;
                  } else {
                    const minutes = Math.floor(totalBufferSeconds / 60);
                    const seconds = totalBufferSeconds % 60;
                    return `-${minutes}:${seconds.toString().padStart(2, '0')}`;
                  }
                }
                return '-0s';
              })()}
            </Typography>
            
            <Typography variant="caption" sx={{ color: 'white', fontWeight: 600, fontSize: '0.75rem' }}>
              {(() => {
                if (isAtLiveEdge) {
                  return 'LIVE';
                } else {
                  const video = videoRef.current;
                  let totalBufferSeconds = 0;
                  
                  if (video && video.buffered.length > 0) {
                    const buffered = video.buffered;
                    const bufferStart = buffered.start(0);
                    const bufferEnd = buffered.end(buffered.length - 1);
                    totalBufferSeconds = bufferEnd - bufferStart;
                  }
                  
                  const behindSeconds = Math.round((1 - userBufferPosition) * totalBufferSeconds);
                  if (behindSeconds < 60) {
                    return `-${behindSeconds}s`;
                  } else {
                    const minutes = Math.floor(behindSeconds / 60);
                    const seconds = behindSeconds % 60;
                    return `-${minutes}:${seconds.toString().padStart(2, '0')}`;
                  }
                }
              })()}
            </Typography>
            
            <Typography variant="caption" sx={{ color: 'white', minWidth: '60px', textAlign: 'right' }}>
              Now
            </Typography>
          </>
        ) : (
          <>
            <Box sx={{ minWidth: '60px' }} />
            
            {archiveMetadata && (
              <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.6)', textAlign: 'center' }}>
                {availableHours.length > 0 ? `${availableHours.length}h available` : 'No archive available'} • Chunk {currentManifestIndex + 1}/{archiveMetadata.manifests.length}
              </Typography>
            )}
            
            <Typography variant="caption" sx={{ color: 'white', minWidth: '60px', textAlign: 'right' }}>
              {(() => {
                if (archiveMetadata && availableHours.length > 0) {
                  const lastManifest = archiveMetadata.manifests[archiveMetadata.manifests.length - 1];
                  if (lastManifest) {
                    const hour = lastManifest.window_index;
                    const chunk = lastManifest.chunk_index;
                    const minutes = chunk * 10;
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
