import { Box, Typography, CircularProgress, Alert } from '@mui/material';
import React, { useMemo } from 'react';

import { getStreamViewerLayout } from '../../config/layoutConfig';
import { useRestart } from '../../hooks/pages/useRestart';
import { Host, Device } from '../../types/common/Host_Types';
import { HLSVideoPlayer } from '../common/HLSVideoPlayer';

import { RestartOverlay } from './RestartOverlay';

interface RestartPlayerProps {
  host: Host;
  device: Device;
}

export const RestartPlayer: React.FC<RestartPlayerProps> = ({ host, device }) => {
  // Generate 5-minute MP4 restart video
  const {
    videoUrl,
    isGenerating,
    isReady,
    error,
    processingTime,
  } = useRestart({
    host: host,
    device: device,
  });

  // Layout configuration for video player
  const layoutConfig = useMemo(() => {
    return getStreamViewerLayout(device?.device_model);
  }, [device?.device_model]);

  return (
    <Box
      sx={{
        position: 'relative',
        width: '100%',
        height: '100%',
        backgroundColor: '#000000',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        overflow: 'hidden',
        '& .MuiCard-root': {
          height: '100%',
          borderRadius: 0,
          border: 'none',
        },
      }}
    >
      {/* Video generation loading state */}
      {isGenerating && (
        <Box
          sx={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            height: '100%',
            color: 'white',
            gap: 2,
          }}
        >
          <CircularProgress sx={{ color: 'white' }} />
          <Typography>Generating 5-minute restart video...</Typography>
          <Typography variant="caption" sx={{ opacity: 0.7 }}>
            This may take 15-30 seconds
          </Typography>
        </Box>
      )}

      {/* Error state */}
      {error && !isGenerating && (
        <Box
          sx={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            height: '100%',
            color: 'white',
            gap: 2,
            p: 3,
          }}
        >
          <Alert severity="error" sx={{ backgroundColor: 'rgba(211, 47, 47, 0.1)' }}>
            <Typography color="white">Failed to generate restart video</Typography>
            <Typography variant="caption" color="white" sx={{ opacity: 0.8 }}>
              {error}
            </Typography>
          </Alert>
        </Box>
      )}

      {/* Video player - ready state */}
      {isReady && videoUrl && !isGenerating && (
        <Box
          sx={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            backgroundColor: 'transparent',
            zIndex: 1,
            overflow: 'hidden',
          }}
        >
          <HLSVideoPlayer
            streamUrl={videoUrl}
            isStreamActive={true}
            isCapturing={false}
            model={device?.device_model}
            layoutConfig={layoutConfig}
            muted={false} // Enable audio for restart video
            sx={{
              width: '100%',
              height: '100%',
              '& video': {
                width: '100%',
                height: '100%',
                objectFit: layoutConfig.objectFit || 'contain',
                objectPosition: 'top center',
              },
            }}
          />
        </Box>
      )}

      {/* Restart overlay */}
      <Box
        sx={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          zIndex: 1000000,
          pointerEvents: 'none',
        }}
      >
        <RestartOverlay
          timestamp={
            isReady && processingTime
              ? `Generated in ${processingTime}s`
              : undefined
          }
        />
      </Box>

      {/* Processing time indicator */}
      {isReady && processingTime && (
        <Box
          sx={{
            position: 'absolute',
            bottom: 16,
            right: 16,
            zIndex: 1000010,
            backgroundColor: 'rgba(0,0,0,0.7)',
            borderRadius: 1,
            px: 1,
            py: 0.5,
          }}
        >
          <Typography
            variant="caption"
            sx={{
              color: '#ffffff',
              fontSize: '0.7rem',
              textShadow: '1px 1px 2px rgba(0,0,0,0.8)',
            }}
          >
            5-min video • Generated in {processingTime}s
          </Typography>
        </Box>
      )}
    </Box>
  );
};