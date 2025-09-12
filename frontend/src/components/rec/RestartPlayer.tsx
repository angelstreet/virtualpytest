import { Box, Typography, CircularProgress, Alert, IconButton } from '@mui/material';
import { Settings as SettingsIcon } from '@mui/icons-material';
import React, { useEffect, useRef, useState } from 'react';

import { useRestart } from '../../hooks/pages/useRestart';
import { Host, Device } from '../../types/common/Host_Types';

import { RestartOverlay } from './RestartOverlay';
import { SubtitleOverlay } from './SubtitleOverlay';
import { SubtitleSettings, SubtitleStyle } from './SubtitleSettings';
import { VideoDescriptionPanel } from './VideoDescriptionPanel';

interface RestartPlayerProps {
  host: Host;
  device: Device;
  includeAudioAnalysis?: boolean;
}

export const RestartPlayer: React.FC<RestartPlayerProps> = ({ host, device, includeAudioAnalysis }) => {
  console.log(`[@component:RestartPlayer] Component mounting for ${host.host_name}-${device.device_id}`);
  
  const videoRef = useRef<HTMLVideoElement>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [subtitleSettings, setSubtitleSettings] = useState<SubtitleStyle>({
    fontSize: 'medium',
    fontFamily: 'default',
    textStyle: 'white',
    opacity: 1.0,
    showOriginal: true,
    showTranslation: false,
    targetLanguage: 'en'
  });
  
  const { videoUrl, isGenerating, isReady, error, processingTime, transcript, detectedLanguage, speechDetected, videoDescription, framesAnalyzed } = useRestart({ 
    host, 
    device, 
    includeAudioAnalysis 
  });

  useEffect(() => {
    return () => {
      console.log(`[@component:RestartPlayer] Component unmounting for ${host.host_name}-${device.device_id}`);
    };
  }, [host.host_name, device.device_id]);

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
          <Typography>Generating restart video...</Typography>
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
          ref={videoRef}
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

        {/* Subtitle overlay */}
        <SubtitleOverlay
          transcript={transcript}
          detectedLanguage={detectedLanguage}
          speechDetected={speechDetected}
          videoRef={videoRef}
          videoDuration={30}
          subtitleSettings={subtitleSettings}
        />
      </Box>

      {/* Subtitle Settings Button */}
      {speechDetected && transcript && (
        <IconButton
          onClick={() => setSettingsOpen(true)}
          sx={{
            position: 'absolute',
            top: 16,
            right: 16,
            zIndex: 1000030,
            backgroundColor: 'rgba(0, 0, 0, 0.7)',
            color: 'white',
            '&:hover': {
              backgroundColor: 'rgba(0, 0, 0, 0.9)',
            },
          }}
        >
          <SettingsIcon />
        </IconButton>
      )}

      {/* Subtitle Settings Modal */}
      <SubtitleSettings
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        settings={subtitleSettings}
        onSettingsChange={setSubtitleSettings}
        originalLanguage={detectedLanguage}
      />

      {/* Processing time indicator - top */}
      {isReady && processingTime && (
        <Box
          sx={{
            position: 'absolute',
            top: 16,
            left: 16,
            zIndex: 1000010,
            backgroundColor: 'rgba(0,0,0,0.7)',
            borderRadius: 1,
            px: 2,
            py: 1,
          }}
        >
        </Box>
      )}

      {/* Video Description Panel */}
      <VideoDescriptionPanel
        videoDescription={videoDescription}
        framesAnalyzed={framesAnalyzed}
      />
    </Box>
  );
};