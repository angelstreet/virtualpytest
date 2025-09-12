import { Box, Typography, CircularProgress, Alert, IconButton, LinearProgress } from '@mui/material';
import { Description as DescriptionIcon, Subtitles as SubtitlesIcon, VolumeUp as AudioIcon, OpenInNew } from '@mui/icons-material';
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
  
  const { videoUrl, isGenerating, isReady, error, processingTime, audioAnalysis, subtitleAnalysis, videoDescription, analysisProgress, isAnalysisComplete } = useRestart({ 
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

        {/* Subtitle overlay - only show if subtitle analysis is complete */}
        {subtitleAnalysis && subtitleAnalysis.subtitles_detected && (
          <SubtitleOverlay
            transcript={subtitleAnalysis.extracted_text}
            detectedLanguage={subtitleAnalysis.detected_language}
            speechDetected={subtitleAnalysis.subtitles_detected}
            videoRef={videoRef}
            videoDuration={10}
            subtitleSettings={subtitleSettings}
          />
        )}
      </Box>

      {/* Analysis Progress Bar (top-right, like Heatmap) */}
      {includeAudioAnalysis && !isAnalysisComplete && (
        <Box sx={{ position: 'absolute', top: 16, right: 16, zIndex: 1000030, minWidth: 120 }}>
          <LinearProgress 
            variant="determinate" 
            value={(() => {
              const completed = Object.values(analysisProgress).filter(status => status === 'completed').length;
              return (completed / 3) * 100;
            })()}
            sx={{ 
              height: 4, 
              borderRadius: 2,
              backgroundColor: 'rgba(255,255,255,0.3)',
              '& .MuiLinearProgress-bar': {
                backgroundColor: '#00AA00'
              }
            }}
          />
          <Typography variant="caption" sx={{ color: 'white', fontSize: '0.7rem', display: 'block', textAlign: 'center', mt: 0.5 }}>
            Analyzing... {Object.values(analysisProgress).filter(status => status === 'completed').length}/3
          </Typography>
        </Box>
      )}

      {/* Analysis Settings Icons (appear when complete, like Heatmap report icon) */}
      {isAnalysisComplete && (
        <Box sx={{ position: 'absolute', top: 16, right: 16, zIndex: 1000030, display: 'flex', gap: 1 }}>
          {/* Audio Settings */}
          {audioAnalysis && (
            <IconButton
              size="small"
              sx={{
                backgroundColor: 'rgba(0, 0, 0, 0.7)',
                color: '#ffffff',
                '&:hover': { backgroundColor: 'rgba(0, 0, 0, 0.9)' },
              }}
              title="Audio Analysis"
            >
              <AudioIcon fontSize="small" />
            </IconButton>
          )}
          
          {/* Subtitle Settings */}
          {subtitleAnalysis && (
            <IconButton
              onClick={() => setSettingsOpen(true)}
              size="small"
              sx={{
                backgroundColor: 'rgba(0, 0, 0, 0.7)',
                color: '#ffffff',
                '&:hover': { backgroundColor: 'rgba(0, 0, 0, 0.9)' },
              }}
              title="Subtitle Settings"
            >
              <SubtitlesIcon fontSize="small" />
            </IconButton>
          )}
          
          {/* Description Panel */}
          {videoDescription && (
            <IconButton
              size="small"
              sx={{
                backgroundColor: 'rgba(0, 0, 0, 0.7)',
                color: '#ffffff',
                '&:hover': { backgroundColor: 'rgba(0, 0, 0, 0.9)' },
              }}
              title="Video Description"
            >
              <DescriptionIcon fontSize="small" />
            </IconButton>
          )}
          
          {/* Report Link (future feature, like Heatmap) */}
          <IconButton
            size="small"
            sx={{
              backgroundColor: 'rgba(0, 0, 0, 0.7)',
              color: '#ffffff',
              '&:hover': { backgroundColor: 'rgba(0, 0, 0, 0.9)' },
            }}
            title="View Report"
          >
            <OpenInNew fontSize="small" />
          </IconButton>
        </Box>
      )}

      {/* Subtitle Settings Modal */}
      <SubtitleSettings
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        settings={subtitleSettings}
        onSettingsChange={setSubtitleSettings}
        originalLanguage={subtitleAnalysis?.detected_language}
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
        videoDescription={videoDescription || undefined}
        framesAnalyzed={10}
      />
    </Box>
  );
};