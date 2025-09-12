import { Box, Typography, CircularProgress, Alert, IconButton, LinearProgress, Tooltip } from '@mui/material';
import { Settings as SettingsIcon, Assessment as ReportIcon } from '@mui/icons-material';
import React, { useEffect, useRef, useState } from 'react';

import { useRestart } from '../../hooks/pages/useRestart';
import { Host, Device } from '../../types/common/Host_Types';

import { RestartSettingsPanel } from './RestartSettingsPanel';
import { RestartSummaryOverlay } from './RestartSummaryOverlay';
import { RestartSubtitleOverlay } from './RestartSubtitleOverlay';

interface RestartPlayerProps {
  host: Host;
  device: Device;
  includeAudioAnalysis?: boolean;
}

export const RestartPlayer: React.FC<RestartPlayerProps> = ({ host, device, includeAudioAnalysis }) => {
  console.log(`[@component:RestartPlayer] Component mounting for ${host.host_name}-${device.device_id}`);
  
  const videoRef = useRef<HTMLVideoElement>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [showSummaryOverlay, setShowSummaryOverlay] = useState(false);
  const [showSubtitleOverlay, setShowSubtitleOverlay] = useState(false);
  const [summaryLanguage, setSummaryLanguage] = useState('en');
  const [subtitleLanguage, setSubtitleLanguage] = useState('en');
  const [subtitleStyle, setSubtitleStyle] = useState('yellow');
  const [subtitleFontSize, setSubtitleFontSize] = useState('medium');
  
  const { videoUrl, isGenerating, isReady, error, analysisResults, analysisProgress, isAnalysisComplete } = useRestart({ 
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

        {/* Summary overlay - top */}
        {showSummaryOverlay && analysisResults.videoDescription && (
          <RestartSummaryOverlay
            videoRef={videoRef}
            frameDescriptions={analysisResults.videoDescription.frame_descriptions}
            language={summaryLanguage}
          />
        )}

        {/* Subtitle overlay - bottom, covers original */}
        {showSubtitleOverlay && analysisResults.subtitles?.extracted_text && (
          <RestartSubtitleOverlay
            subtitleText={analysisResults.subtitles.extracted_text}
            language={subtitleLanguage}
            style={subtitleStyle}
            fontSize={subtitleFontSize}
          />
        )}
      </Box>

      {/* Analysis Progress Bar (top-right, animated) */}
      {includeAudioAnalysis && !isAnalysisComplete && (
        <Box sx={{ position: 'absolute', top: 16, right: 16, zIndex: 1000030, width: 100 }}>
          <LinearProgress 
            variant="determinate" 
            value={(() => {
              const completed = Object.values(analysisProgress).filter(status => status === 'completed').length;
              const errors = Object.values(analysisProgress).filter(status => status === 'error').length;
              return ((completed + errors) / 3) * 100;
            })()}
            sx={{ 
              height: 6, 
              borderRadius: 3,
              backgroundColor: 'rgba(255,255,255,0.2)',
              '& .MuiLinearProgress-bar': {
                backgroundColor: (() => {
                  const errors = Object.values(analysisProgress).filter(status => status === 'error').length;
                  return errors > 0 ? '#FF6B6B' : '#00AA00';
                })(),
                borderRadius: 3,
                transition: 'transform 0.4s ease-in-out'
              }
            }}
          />
        </Box>
      )}

      {/* Settings and Report Buttons (appears when analysis complete) */}
      {isAnalysisComplete && (
        <Box sx={{ position: 'absolute', top: 16, right: 16, zIndex: 1000030, display: 'flex', flexDirection: 'column', gap: 1 }}>
          <Tooltip title="Link Report" placement="left">
            <IconButton
              onClick={() => {
                // Open report in new tab
                const reportUrl = `/reports/restart/${host.host_name}/${device.device_id}`;
                window.open(reportUrl, '_blank');
              }}
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
        showSummaryOverlay={showSummaryOverlay}
        onToggleSummary={setShowSummaryOverlay}
        showSubtitleOverlay={showSubtitleOverlay}
        onToggleSubtitle={setShowSubtitleOverlay}
        summaryLanguage={summaryLanguage}
        onSummaryLanguageChange={setSummaryLanguage}
        subtitleLanguage={subtitleLanguage}
        onSubtitleLanguageChange={setSubtitleLanguage}
        subtitleStyle={subtitleStyle}
        onSubtitleStyleChange={setSubtitleStyle}
        subtitleFontSize={subtitleFontSize}
        onSubtitleFontSizeChange={setSubtitleFontSize}
        videoDescription={analysisResults.videoDescription?.video_summary}
        audioTranscript={analysisResults.audio?.combined_transcript}
      />
    </Box>
  );
};