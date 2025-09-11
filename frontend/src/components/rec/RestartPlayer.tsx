import { Box, Typography, CircularProgress, Alert } from '@mui/material';
import React from 'react';

import { useRestart } from '../../hooks/pages/useRestart';
import { Host, Device } from '../../types/common/Host_Types';

import { RestartOverlay } from './RestartOverlay';

interface RestartPlayerProps {
  host: Host;
  device: Device;
}

export const RestartPlayer: React.FC<RestartPlayerProps> = ({ host, device }) => {
  const { videoUrl, isGenerating, isReady, error, processingTime } = useRestart({ host, device });

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
          <Typography>Generating 30-second restart video...</Typography>
          <Typography variant="caption" sx={{ opacity: 0.7 }}>
            This should take 3-5 seconds
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

      {/* Simple video player - ready state */}
      {isReady && videoUrl && !isGenerating && (
        <Box
          component="video"
          src={videoUrl}
          controls
          autoPlay
          muted={false}
          sx={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            objectFit: 'contain',
            objectPosition: 'top center',
            zIndex: 1,
          }}
        />
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
            30s video • Generated in {processingTime}s
          </Typography>
        </Box>
      )}
    </Box>
  );
};