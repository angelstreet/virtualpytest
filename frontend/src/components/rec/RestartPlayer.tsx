import { Box, Typography, CircularProgress, Alert, IconButton, Tooltip, keyframes } from '@mui/material';
import { Settings as SettingsIcon, Assessment as ReportIcon } from '@mui/icons-material';
import React, { useEffect, useRef, useState } from 'react';

import { useRestart } from '../../hooks/pages/useRestart';
import { Host, Device } from '../../types/common/Host_Types';

import { RestartSettingsPanel } from './RestartSettingsPanel';
import { RestartSubtitleOverlay } from './RestartSubtitleOverlay';

// Pulsing animation for the loading indicator
const pulseAnimation = keyframes`
  0% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.1);
    opacity: 0.7;
  }
  100% {
    transform: scale(1);
    opacity: 1;
  }
`;

// AI Analysis Loader Component
const AIAnalysisLoader: React.FC = () => {
  const [elapsedTime, setElapsedTime] = useState(0);

  useEffect(() => {
    const startTime = Date.now();
    const interval = setInterval(() => {
      const elapsed = Math.floor((Date.now() - startTime) / 1000);
      setElapsedTime(elapsed);
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <Box
      sx={{
        position: 'absolute',
        top: 16,
        right: 16,
        zIndex: 1000030,
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        borderRadius: 2,
        padding: 2,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 1,
        minWidth: 140,
        border: '1px solid rgba(255, 255, 255, 0.2)',
      }}
    >
      {/* Pulsing Circle and Timer */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <CircularProgress
          size={20}
          sx={{
            color: 'white',
            animation: `${pulseAnimation} 2s ease-in-out infinite`,
          }}
        />
        <Typography
          variant="body2"
          sx={{
            color: 'white',
            fontFamily: 'monospace',
            fontSize: '14px',
            fontWeight: 600,
          }}
        >
          {formatTime(elapsedTime)}
        </Typography>
      </Box>

      {/* Status Text */}
      <Typography
        variant="caption"
        sx={{
          color: 'white',
          fontSize: '11px',
          textAlign: 'center',
          lineHeight: 1.2,
        }}
      >
        AI Analyzing
      </Typography>

      {/* Expected Duration */}
      <Typography
        variant="caption"
        sx={{
          color: 'rgba(255, 255, 255, 0.7)',
          fontSize: '10px',
          textAlign: 'center',
        }}
      >
        (~2-3 minutes)
      </Typography>
    </Box>
  );
};

interface RestartPlayerProps {
  host: Host;
  device: Device;
  includeAudioAnalysis?: boolean;
}

export const RestartPlayer: React.FC<RestartPlayerProps> = ({ host, device, includeAudioAnalysis }) => {
  console.log(`[@component:RestartPlayer] Component mounting for ${host.host_name}-${device.device_id}`);
  
  const videoRef = useRef<HTMLVideoElement>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [showSubtitleOverlay, setShowSubtitleOverlay] = useState(false);
  const [showAudioTranscriptOverlay, setShowAudioTranscriptOverlay] = useState(false);
  const [summaryLanguage, setSummaryLanguage] = useState('en');
  const [subtitleLanguage, setSubtitleLanguage] = useState('en');
  const [audioTranscriptLanguage, setAudioTranscriptLanguage] = useState('en');
  const [subtitleStyle, setSubtitleStyle] = useState('yellow');
  const [subtitleFontSize, setSubtitleFontSize] = useState('medium');
  
  const { videoUrl, isGenerating, isReady, error, analysisResults, isAnalysisComplete, reportUrl } = useRestart({ 
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


        {/* Subtitle overlay - bottom, covers original */}
        {showSubtitleOverlay && analysisResults.subtitles?.frame_subtitles && (
          <RestartSubtitleOverlay
            videoRef={videoRef}
            frameSubtitles={analysisResults.subtitles.frame_subtitles}
            style={subtitleStyle}
            fontSize={subtitleFontSize}
          />
        )}
      </Box>

      {/* AI Analysis Loading Indicator (shows after video appears, until analysis complete) */}
      {isReady && includeAudioAnalysis && !isAnalysisComplete && (
        <AIAnalysisLoader />
      )}

      {/* Settings and Report Buttons (appears when everything is complete) */}
      {isReady && !isGenerating && (!includeAudioAnalysis || isAnalysisComplete) && (
        <Box sx={{ position: 'absolute', top: 16, right: 16, zIndex: 1000030, display: 'flex', flexDirection: 'column', gap: 1 }}>
          <Tooltip title="Link Report" placement="left">
            <IconButton
              onClick={() => {
                // Open report in new tab using dynamic URL from backend
                if (reportUrl) {
                  window.open(reportUrl, '_blank');
                } else {
                  console.warn('Report URL not available yet - analysis may still be in progress');
                }
              }}
              disabled={!reportUrl}
              sx={{
                backgroundColor: 'rgba(0, 0, 0, 0.7)',
                color: '#ffffff',
                '&:hover': { backgroundColor: 'rgba(0, 0, 0, 0.9)' },
              }}
            >
              <ReportIcon />
            </IconButton>
          </Tooltip>
          
          <Tooltip title="Settings" placement="left">
            <IconButton
              onClick={() => setSettingsOpen(true)}
              sx={{
                backgroundColor: 'rgba(0, 0, 0, 0.7)',
                color: '#ffffff',
                '&:hover': { backgroundColor: 'rgba(0, 0, 0, 0.9)' },
              }}
            >
              <SettingsIcon />
            </IconButton>
          </Tooltip>
        </Box>
      )}

      {/* Settings Panel */}
      <RestartSettingsPanel
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        showSubtitleOverlay={showSubtitleOverlay}
        onToggleSubtitle={setShowSubtitleOverlay}
        showAudioTranscriptOverlay={showAudioTranscriptOverlay}
        onToggleAudioTranscript={setShowAudioTranscriptOverlay}
        summaryLanguage={summaryLanguage}
        onSummaryLanguageChange={setSummaryLanguage}
        subtitleLanguage={subtitleLanguage}
        onSubtitleLanguageChange={setSubtitleLanguage}
        audioTranscriptLanguage={audioTranscriptLanguage}
        onAudioTranscriptLanguageChange={setAudioTranscriptLanguage}
        subtitleStyle={subtitleStyle}
        onSubtitleStyleChange={setSubtitleStyle}
        subtitleFontSize={subtitleFontSize}
        onSubtitleFontSizeChange={setSubtitleFontSize}
        videoDescription={analysisResults.videoDescription || undefined}
        audioTranscript={analysisResults.audio?.combined_transcript}
        audioAnalysis={analysisResults.audio || undefined}
        subtitleData={analysisResults.subtitles || undefined}
      />
    </Box>
  );
};