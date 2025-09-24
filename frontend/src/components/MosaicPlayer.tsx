/**
 * Mosaic Player Component
 * 
 * Displays heatmap mosaics with timeline scrubber for 24h circular buffer.
 * Shows mosaic images and provides timeline navigation controls.
 */

import React, { useState, useRef, useCallback } from 'react';
import {
  Box,
  Slider,
  Typography,
  Alert,
  IconButton,
  Chip,
  LinearProgress
} from '@mui/material';
import {
  PlayArrow,
  Pause,
  SkipNext,
  SkipPrevious,
  Refresh
} from '@mui/icons-material';

import { TimelineItem } from '../hooks/useHeatmap';

interface MosaicPlayerProps {
  timeline: TimelineItem[];
  currentIndex: number;
  onIndexChange: (index: number) => void;
  onCellClick?: (deviceData: any) => void;
  hasIncidents?: boolean;
  isLoading?: boolean;
}

export const MosaicPlayer: React.FC<MosaicPlayerProps> = ({
  timeline,
  currentIndex,
  onIndexChange,
  onCellClick,
  hasIncidents = false,
  isLoading = false
}) => {
  const [imageError, setImageError] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [imageLoading, setImageLoading] = useState(true);
  
  const playInterval = useRef<NodeJS.Timeout | null>(null);
  
  const currentItem = timeline[currentIndex];
  
  /**
   * Auto-play functionality
   */
  const startPlaying = useCallback(() => {
    if (playInterval.current) return;
    
    setIsPlaying(true);
    playInterval.current = setInterval(() => {
      onIndexChange(prev => {
        const next = prev + 1;
        if (next >= timeline.length) {
          setIsPlaying(false);
          return timeline.length - 1;
        }
        return next;
      });
    }, 1000); // 1 second per frame
  }, [onIndexChange, timeline.length]);
  
  const stopPlaying = useCallback(() => {
    if (playInterval.current) {
      clearInterval(playInterval.current);
      playInterval.current = null;
    }
    setIsPlaying(false);
  }, []);
  
  const togglePlayPause = () => {
    if (isPlaying) {
      stopPlaying();
    } else {
      startPlaying();
    }
  };
  
  /**
   * Navigation controls
   */
  const goToPrevious = () => {
    if (currentIndex > 0) {
      onIndexChange(currentIndex - 1);
    }
  };
  
  const goToNext = () => {
    if (currentIndex < timeline.length - 1) {
      onIndexChange(currentIndex + 1);
    }
  };
  
  
  /**
   * Timeline slider change handler
   */
  const handleSliderChange = (_event: Event, newValue: number | number[]) => {
    const index = newValue as number;
    onIndexChange(index);
  };
  
  /**
   * Format time for display
   */
  const formatDisplayTime = (item: TimelineItem): string => {
    const time = item.displayTime;
    const timeStr = time.toLocaleTimeString('en-US', { 
      hour12: false, 
      hour: '2-digit', 
      minute: '2-digit' 
    });
    
    if (item.isToday) {
      return `Today ${timeStr}`;
    } else {
      return `Yesterday ${timeStr}`;
    }
  };
  
  /**
   * Get timeline tick colors for incidents
   */
  const getTimelineTicks = () => {
    // For now, we'll just show basic ticks
    // In the future, we could load incident data for all timeline items
    return timeline.map((_, index) => ({
      value: index,
      hasIncident: false // We'd need to load this data
    }));
  };
  
  // Cleanup interval on unmount
  React.useEffect(() => {
    return () => {
      if (playInterval.current) {
        clearInterval(playInterval.current);
      }
    };
  }, []);
  
  if (!currentItem) {
    return (
      <Alert severity="warning">
        No timeline data available
      </Alert>
    );
  }
  
  return (
    <Box>
      {/* Header with time and status */}
      <Box sx={{ mb: 2, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Box>
          <Typography variant="h6">
            {formatDisplayTime(currentItem)}
          </Typography>
          <Box sx={{ display: 'flex', gap: 1, mt: 0.5 }}>
            <Chip 
              label={`Frame ${currentIndex + 1} / ${timeline.length}`}
              size="small"
              variant="outlined"
            />
            {hasIncidents && (
              <Chip 
                label="Incidents Detected"
                size="small"
                color="error"
              />
            )}
            {isLoading && (
              <Chip 
                label="Loading..."
                size="small"
                color="info"
              />
            )}
          </Box>
        </Box>
        
      </Box>
      
      {/* Loading indicator */}
      {isLoading && (
        <LinearProgress sx={{ mb: 1 }} />
      )}
      
      {/* Mosaic Display */}
      <Box 
        sx={{ 
          width: '100%', 
          height: '50vh',
          backgroundColor: 'black',
          borderRadius: 1,
          overflow: 'hidden',
          position: 'relative',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center'
        }}
      >
        {imageError ? (
          <Alert 
            severity="warning" 
            sx={{ 
              backgroundColor: 'rgba(255, 193, 7, 0.1)',
              color: 'white'
            }}
          >
            No mosaic available for {currentItem.timeKey}
          </Alert>
        ) : (
          <img
            src={currentItem.mosaicUrl}
            alt={`Heatmap ${currentItem.timeKey}`}
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'contain'
            }}
            onLoad={() => {
              setImageLoading(false);
              setImageError(false);
            }}
            onError={() => {
              setImageLoading(false);
              setImageError(true);
            }}
            onClick={() => {
              // Open image in new tab
              window.open(currentItem.mosaicUrl, '_blank');
            }}
          />
        )}
        
        {imageLoading && (
          <Box 
            sx={{ 
              position: 'absolute',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              color: 'white'
            }}
          >
            <Typography>Loading mosaic...</Typography>
          </Box>
        )}
      </Box>
      
      {/* Timeline Controls */}
      <Box 
        sx={{ 
          mt: 1,
          p: 1,
          backgroundColor: 'rgba(0,0,0,0.05)',
          borderRadius: 1
        }}
      >
        {/* Time Display */}
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
          <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
            {currentItem ? formatTime(currentItem.displayTime) : '--:--'}
          </Typography>
          <Chip
            label={hasIncidents ? 'INCIDENTS' : 'ALL GOOD'}
            size="small"
            sx={{
              backgroundColor: hasIncidents ? '#ff4444' : '#4CAF50',
              color: 'white',
              fontWeight: 'bold'
            }}
          />
        </Box>
        
        {/* Timeline Scrubber */}
        <Box sx={{ position: 'relative' }}>
          <Slider
            value={currentIndex}
            min={0}
            max={Math.max(0, timeline.length - 1)}
            onChange={handleSliderChange}
            sx={{
              color: hasIncidents ? '#FF0000' : '#00AA00',
              '& .MuiSlider-thumb': {
                width: 16,
                height: 16,
                backgroundColor: hasIncidents ? '#FF0000' : '#00AA00',
              },
              '& .MuiSlider-track': {
                backgroundColor: hasIncidents ? '#FF0000' : '#00AA00',
              },
              '& .MuiSlider-rail': {
                backgroundColor: '#CCCCCC',
              }
            }}
          />
          
          {/* Hour Marks */}
          <Box sx={{ position: 'absolute', top: -25, left: 0, right: 0, height: 20 }}>
            {Array.from({ length: 24 }, (_, i) => {
              const hourIndex = i * 60; // Every hour (60 minutes)
              const position = (hourIndex / Math.max(1, timeline.length - 1)) * 100;
              return (
                <Box
                  key={i}
                  sx={{
                    position: 'absolute',
                    left: `${position}%`,
                    transform: 'translateX(-50%)',
                    fontSize: '10px',
                    cursor: 'pointer',
                    '&:hover': { fontWeight: 'bold' }
                  }}
                  onClick={() => onIndexChange(hourIndex)}
                >
                  {String(23 - i).padStart(2, '0')}h
                </Box>
              );
            })}
          </Box>
        </Box>
      </Box>
    </Box>
  );
};
