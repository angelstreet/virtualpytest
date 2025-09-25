/**
 * Mosaic Player Component
 * 
 * Displays heatmap mosaics with timeline scrubber for 24h circular buffer.
 * Shows mosaic images and provides timeline navigation controls.
 */

import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  Slider,
  Typography,
  Alert,
  Chip,
  LinearProgress,
  Tooltip
} from '@mui/material';

import { TimelineItem } from '../hooks/useHeatmap';

// Add type alias for filter
type FilterType = 'ALL' | 'OK' | 'KO';

interface MosaicPlayerProps {
  timeline: TimelineItem[];
  currentIndex: number;
  onIndexChange: (index: number) => void;
  onCellClick?: (deviceData: any) => void;
  hasIncidents?: boolean;
  isLoading?: boolean;
  hasDataError?: boolean;
  analysisData?: any; // Device analysis data for overlays
  filter?: FilterType;
  getMosaicUrl?: (item: TimelineItem, filter: FilterType) => string;
}

export const MosaicPlayer: React.FC<MosaicPlayerProps> = ({
  timeline,
  currentIndex,
  onIndexChange,
  onCellClick,
  hasIncidents = false,
  isLoading = false,
  hasDataError = false,
  analysisData,
  filter = 'ALL',
  getMosaicUrl
}) => {
  const [imageError, setImageError] = useState(false);
  const [imageLoading, setImageLoading] = useState(true);
  const imageCache = useRef<Map<string, HTMLImageElement>>(new Map());
  const currentImageRef = useRef<HTMLImageElement | null>(null);
  
  const currentItem = timeline[currentIndex];
  const mosaicSrc = getMosaicUrl ? getMosaicUrl(currentItem, filter) : currentItem.mosaicUrl;
  
  // Reset loading state when filter or index changes
  useEffect(() => {
    setImageLoading(true);
    setImageError(false);
  }, [filter, currentIndex]);
  
  // Preload and cache image
  useEffect(() => {
    if (!mosaicSrc) return;
    
    // Check if image is already cached
    if (imageCache.current.has(mosaicSrc)) {
      setImageLoading(false);
      setImageError(false);
      return;
    }
    
    // Preload image
    const img = new Image();
    img.onload = () => {
      imageCache.current.set(mosaicSrc, img);
      setImageLoading(false);
      setImageError(false);
    };
    img.onerror = () => {
      setImageLoading(false);
      setImageError(true);
    };
    img.src = mosaicSrc;
    currentImageRef.current = img;
    
    return () => {
      if (currentImageRef.current) {
        currentImageRef.current.onload = null;
        currentImageRef.current.onerror = null;
      }
    };
  }, [mosaicSrc]);
  
  
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
          <>
            <img
              src={mosaicSrc}
              alt={`Heatmap ${currentItem.timeKey} - ${filter}`}
              style={{
                width: '100%',
                height: '100%',
                objectFit: 'contain'
              }}
            />
            
            {/* Device Overlays */}
            {!imageLoading && analysisData?.devices && (
              <Box sx={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%' }}>
                {analysisData.devices.map((device: any, index: number) => {
                  const deviceCount = analysisData.devices.length;
                  const cols = deviceCount <= 4 ? Math.ceil(Math.sqrt(deviceCount)) : 3;
                  const rows = Math.ceil(deviceCount / cols);
                  const col = index % cols;
                  const row = Math.floor(index / cols);
                  
                  const cellWidth = 100 / cols;
                  const cellHeight = 100 / rows;
                  
                  const analysis = device.analysis_json || {};
                  
                  const tooltipText = `${device.host_name}-${device.device_name}
Audio: ${analysis.audio ? 'Yes' : 'No'}
Video: ${!analysis.blackscreen && !analysis.freeze ? 'Yes' : 'No'}
${analysis.volume_percentage !== undefined ? `Volume: ${analysis.volume_percentage}%` : ''}
${analysis.freeze ? `Freeze: ${(analysis.freeze_diffs || []).length} diffs` : ''}`;

                  return (
                    <Tooltip key={`${device.host_name}-${device.device_id}`} title={tooltipText} arrow>
                      <Box
                        sx={{
                          position: 'absolute',
                          left: `${col * cellWidth}%`,
                          top: `${row * cellHeight}%`,
                          width: `${cellWidth}%`,
                          height: `${cellHeight}%`,
                          cursor: 'pointer',
                          '&:hover': {
                            backgroundColor: 'rgba(255, 255, 255, 0.1)',
                            border: '2px solid #fff'
                          }
                        }}
                        onClick={(e) => {
                          e.stopPropagation();
                          onCellClick?.(device);
                        }}
                      />
                    </Tooltip>
                  );
                })}
              </Box>
            )}
          </>
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
        
        {/* Timeline Scrubber */}
        <Box sx={{ position: 'relative' }}>
          <Slider
            value={currentIndex}
            min={0}
            max={Math.max(0, timeline.length - 1)}
            onChange={handleSliderChange}
            sx={{
              color: (!currentItem || hasDataError) ? '#888888' : (hasIncidents ? '#FF0000' : '#00AA00'),
              '& .MuiSlider-thumb': {
                width: 16,
                height: 16,
                backgroundColor: (!currentItem || hasDataError) ? '#888888' : (hasIncidents ? '#FF0000' : '#00AA00'),
              },
              '& .MuiSlider-track': {
                backgroundColor: (!currentItem || hasDataError) ? '#888888' : (hasIncidents ? '#FF0000' : '#00AA00'),
              },
              '& .MuiSlider-rail': {
                backgroundColor: '#CCCCCC',
              }
            }}
          />
          
          {/* Hour Marks */}
          <Box sx={{ position: 'absolute', top: 35, left: 0, right: 0, height: 20 }}>
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
