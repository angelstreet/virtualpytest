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
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [overlayPositions, setOverlayPositions] = useState<Array<{
    left: number;
    top: number;
    width: number;
    height: number;
  }>>([]);
  
  const currentItem = timeline[currentIndex];
  const mosaicSrc = getMosaicUrl ? getMosaicUrl(currentItem, filter) : currentItem?.mosaicUrl || '';
  
  // Reset loading state when filter or index changes
  useEffect(() => {
    setImageLoading(true);
    setImageError(false);
  }, [filter, currentIndex]);

  // Calculate overlay positions based on actual image dimensions
  useEffect(() => {
    const calculatePositions = () => {
      if (!currentImageRef.current || !containerRef.current || !analysisData?.devices) return;

      const img = currentImageRef.current;
      const container = containerRef.current;

      // Get container dimensions
      const containerRect = container.getBoundingClientRect();
      const containerWidth = containerRect.width;
      const containerHeight = containerRect.height;

      // Get actual image dimensions (natural size)
      const imageNaturalWidth = img.naturalWidth;
      const imageNaturalHeight = img.naturalHeight;

      if (imageNaturalWidth === 0 || imageNaturalHeight === 0) return;

      // Calculate how the image is displayed with object-fit: contain
      const containerAspectRatio = containerWidth / containerHeight;
      const imageAspectRatio = imageNaturalWidth / imageNaturalHeight;

      let displayedImageWidth: number;
      let displayedImageHeight: number;
      let offsetX: number;
      let offsetY: number;

      if (imageAspectRatio > containerAspectRatio) {
        // Image is wider - constrained by width
        displayedImageWidth = containerWidth;
        displayedImageHeight = containerWidth / imageAspectRatio;
        offsetX = 0;
        offsetY = (containerHeight - displayedImageHeight) / 2;
      } else {
        // Image is taller - constrained by height
        displayedImageWidth = containerHeight * imageAspectRatio;
        displayedImageHeight = containerHeight;
        offsetX = (containerWidth - displayedImageWidth) / 2;
        offsetY = 0;
      }

      // Calculate grid layout (same as backend)
      const deviceCount = analysisData.devices.length;
      let cols: number, rows: number;
      if (deviceCount <= 1) {
        cols = 1; rows = 1;
      } else if (deviceCount === 2) {
        cols = 2; rows = 1;
      } else if (deviceCount <= 4) {
        cols = 2; rows = 2;
      } else if (deviceCount <= 6) {
        cols = 3; rows = 2;
      } else if (deviceCount <= 9) {
        cols = 3; rows = 3;
      } else {
        cols = Math.ceil(Math.sqrt(deviceCount));
        rows = Math.ceil(deviceCount / cols);
      }

      // Calculate cell dimensions within the displayed image
      const cellWidth = displayedImageWidth / cols;
      const cellHeight = displayedImageHeight / rows;

      // Calculate positions for each device
      const positions = analysisData.devices.map((_: any, index: number) => {
        const col = index % cols;
        const row = Math.floor(index / cols);

        return {
          left: offsetX + (col * cellWidth),
          top: offsetY + (row * cellHeight),
          width: cellWidth,
          height: cellHeight
        };
      });

      setOverlayPositions(positions);
    };

    // Calculate on image load and when analysis data changes
    if (currentImageRef.current) {
      const img = currentImageRef.current;
      if (img.complete && !imageLoading) {
        calculatePositions();
      } else {
        img.addEventListener('load', calculatePositions);
      }
    }

    // Recalculate on window resize
    window.addEventListener('resize', calculatePositions);

    return () => {
      if (currentImageRef.current) {
        currentImageRef.current.removeEventListener('load', calculatePositions);
      }
      window.removeEventListener('resize', calculatePositions);
    };
  }, [analysisData, imageLoading, mosaicSrc]);
  
  // Preload and cache image
  useEffect(() => {
    if (!mosaicSrc || mosaicSrc === '') {
      setImageLoading(false);
      setImageError(true);
      return;
    }
    
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
      {/* Header with time */}
      <Box sx={{ mb: 2, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Box>
          <Typography variant="h6">
            {formatDisplayTime(currentItem)}
          </Typography>
        </Box>
        
      </Box>
      
      {/* Loading indicator */}
      {isLoading && (
        <LinearProgress sx={{ mb: 1 }} />
      )}
      
      {/* Mosaic Display */}
      <Box 
        ref={containerRef}
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
              ref={currentImageRef}
              src={mosaicSrc}
              alt={`Heatmap ${currentItem.timeKey} - ${filter}`}
              style={{
                width: '100%',
                height: '100%',
                objectFit: 'contain'
              }}
            />
            
            {/* Device Overlays */}
            {!imageLoading && analysisData?.devices && overlayPositions.length > 0 && (
              <Box sx={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%' }}>
                {analysisData.devices.map((device: any, index: number) => {
                  const position = overlayPositions[index];
                  if (!position) return null;

                  const analysis = device.analysis_json || {};
                  const deviceName = device.device_name || device.device_id || 'Unknown';
                  
                  const tooltipText = `${device.host_name}-${deviceName}
Audio: ${analysis.audio ? 'Yes' : 'No'}
Video: ${!analysis.blackscreen && !analysis.freeze ? 'Yes' : 'No'}
${analysis.volume_percentage !== undefined ? `Volume: ${analysis.volume_percentage}%` : ''}
${analysis.freeze ? `Freeze: ${(analysis.freeze_diffs || []).length} diffs` : ''}`;

                  return (
                    <Tooltip key={`${device.host_name}-${device.device_id}`} title={tooltipText} arrow>
                      <Box
                        sx={{
                          position: 'absolute',
                          left: `${position.left}px`,
                          top: `${position.top}px`,
                          width: `${position.width}px`,
                          height: `${position.height}px`,
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
        <Box sx={{ position: 'relative', pb: 5 }}>
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
          
          
          {/* Hour Marks with Date/Time Display */}
          <Box sx={{ position: 'absolute', top: 35, left: 0, right: 0, height: 40 }}>
            {Array.from({ length: 24 }, (_, i) => {
              const hourIndex = i * 60; // Every hour (60 minutes)
              const position = (hourIndex / Math.max(1, timeline.length - 1)) * 100;
              const timelineItem = timeline[hourIndex];
              
              return (
                <Tooltip 
                  key={i}
                  title={timelineItem ? formatDisplayTime(timelineItem) : ''}
                  arrow
                >
                  <Box
                    sx={{
                      position: 'absolute',
                      left: `${position}%`,
                      transform: 'translateX(-50%)',
                      fontSize: '10px',
                      cursor: 'pointer',
                      textAlign: 'center',
                      '&:hover': { fontWeight: 'bold' }
                    }}
                    onClick={() => onIndexChange(hourIndex)}
                  >
                    <Typography variant="caption" sx={{ fontSize: '10px', display: 'block' }}>
                      {String(23 - i).padStart(2, '0')}h
                    </Typography>
                    {timelineItem && (
                      <Typography variant="caption" sx={{ fontSize: '8px', color: 'text.secondary', display: 'block' }}>
                        {timelineItem.isToday ? 'Today' : 'Yesterday'}
                      </Typography>
                    )}
                  </Box>
                </Tooltip>
              );
            })}
          </Box>
        </Box>
      </Box>
    </Box>
  );
};
