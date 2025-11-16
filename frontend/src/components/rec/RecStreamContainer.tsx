import { Box, Typography, CircularProgress } from '@mui/material';
import React from 'react';

import { Host, Device } from '../../types/common/Host_Types';
import { MonitoringAnalysis, SubtitleAnalysis, LanguageMenuAnalysis } from '../../types/pages/Monitoring_Types';
import { EnhancedHLSPlayer } from '../video/EnhancedHLSPlayer';
import { MonitoringOverlay } from '../monitoring/MonitoringOverlay';
import { buildStreamUrl } from '../../utils/buildUrlUtils';
import { RestartPlayer } from './RestartPlayer';

interface ErrorTrendData {
  blackscreenConsecutive: number;
  freezeConsecutive: number;
  audioLossConsecutive: number;
  macroblocksConsecutive: number;
  hasWarning: boolean;
  hasError: boolean;
}

interface RecStreamContainerProps {
  host: Host;
  device?: Device;
  
  // Stream state
  streamUrl?: string;
  isLoadingUrl: boolean;
  urlError: string | null;
  
  // Mode states
  monitoringMode: boolean;
  restartMode: boolean;
  isLiveMode: boolean;
  
  // Control state
  isControlActive: boolean;
  
  // Quality state
  currentQuality: 'low' | 'sd' | 'hd';
  isQualitySwitching: boolean;
  shouldPausePlayer: boolean;
  
  // Audio state
  isMuted: boolean;
  
  // Layout
  isMobileModel: boolean;
  showRemote: boolean;
  showWeb: boolean;
  finalStreamContainerDimensions: {
    width: number;
    height: number;
    x: number;
    y: number;
  };
  
  // VNC scaling function
  calculateVncScaling: (dimensions: { width: number; height: number }) => any;
  
  // Callbacks
  onPlayerReady: () => void;
  onVideoTimeUpdate: (time: number) => void;
  onVideoPause?: () => void;
  onCurrentSegmentChange?: (segmentUrl: string) => void;
  
  // Monitoring data props (for overlay on live video)
  monitoringAnalysis?: MonitoringAnalysis;
  subtitleAnalysis?: SubtitleAnalysis;
  languageMenuAnalysis?: LanguageMenuAnalysis;
  aiDescription?: string;
  errorTrendData?: ErrorTrendData;
  analysisTimestamp?: string;
  isAIAnalyzing?: boolean;
}

export const RecStreamContainer: React.FC<RecStreamContainerProps> = ({
  host,
  device,
  streamUrl,
  isLoadingUrl,
  urlError,
  monitoringMode,
  restartMode,
  isLiveMode,
  isControlActive,
  currentQuality,
  isQualitySwitching,
  shouldPausePlayer,
  isMuted,
  isMobileModel,
  showRemote,
  showWeb,
  finalStreamContainerDimensions,
  calculateVncScaling,
  onPlayerReady,
  onVideoTimeUpdate,
  onVideoPause,
  onCurrentSegmentChange,
  // Monitoring props
  monitoringAnalysis,
  subtitleAnalysis,
  languageMenuAnalysis,
  aiDescription,
  errorTrendData,
  analysisTimestamp,
  isAIAnalyzing,
}) => {
  // VNC archive mode: override streamUrl to use HLS (same as screenshot logic)
  const isVncDevice = device?.device_model === 'host_vnc';
  const effectiveStreamUrl = (isVncDevice && !isLiveMode) 
    ? buildStreamUrl(host, device?.device_id || 'device1') 
    : streamUrl;

  return (
    <Box
      sx={{
        width: (() => {
          if (!isControlActive) return '100%';
          const panelCount = (showRemote ? 1 : 0) + (showWeb ? 1 : 0);
          if (panelCount === 0) return '100%';
          if (panelCount === 1) return '80%'; // Changed from 75% to 80% (100% - 20%)
          return '60%'; // Changed from 50% to 60% (100% - 40% for two 20% panels)
        })(),
        height: '100%', // Use full available height (already excluding header)
        position: 'relative',
        overflow: 'hidden',
        display: 'flex',
        alignItems: isMobileModel ? 'flex-start' : 'center', // Top-align mobile to avoid bottom black bars
        justifyContent: 'center',
        backgroundColor: 'black',
      }}
    >
      {/* Quality transition overlay - solid black to hide corrupted frames during FFmpeg restart */}
      {isQualitySwitching && (() => {
        console.log(`[@component:RecStreamContainer] 🎬 RENDERING LOADING OVERLAY - isQualitySwitching=${isQualitySwitching}, currentQuality=${currentQuality}`);
        return (
          <Box
            sx={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              backgroundColor: 'black', // Solid black to completely hide any corruption
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 1000,
            }}
          >
            <CircularProgress size={60} sx={{ color: 'warning.main' }} />
            <Typography variant="h6" sx={{ color: 'white', mt: 2 }}>
              Loading {currentQuality.toUpperCase()} quality stream...
            </Typography>
            <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.7)', mt: 1 }}>
              Waiting for stable stream
            </Typography>
          </Box>
        );
      })()}
      
      {/* Content based on mode */}
      {restartMode && isControlActive ? (
        <RestartPlayer host={host} device={device!} includeAudioAnalysis={true} />
      ) : effectiveStreamUrl ? (
        // VNC device in LIVE mode: use iframe for live desktop stream
        // VNC device in ARCHIVE mode: use HLS player for recorded video
        // Non-VNC devices: always use HLS player
        device?.device_model === 'host_vnc' && isLiveMode ? (
          (() => {
            const panelCount = (showRemote ? 1 : 0) + (showWeb ? 1 : 0);
            const hasPanel = panelCount > 0 && isControlActive;
            
            // Calculate target size based on current modal stream area
            const targetWidth = hasPanel 
              ? finalStreamContainerDimensions.width * 0.80  // 80% when panels shown (changed from 75%)
              : finalStreamContainerDimensions.width;        // 100% when no panels
            const targetHeight = finalStreamContainerDimensions.height;
            
            const vncScaling = calculateVncScaling({ 
              width: targetWidth, 
              height: targetHeight 
            });

            return (
              <Box
                sx={{
                  position: 'relative',
                  width: '100%',
                  height: '100%',
                  backgroundColor: 'black',
                  overflow: 'hidden',
                }}
              >
                <iframe
                  src={effectiveStreamUrl}
                  style={{
                    border: 'none',
                    backgroundColor: '#000',
                    display: 'block',
                    margin: '0 auto', // Center horizontally
                    ...vncScaling, // Apply calculated scaling
                  }}
                  title="VNC Desktop Stream"
                  allow="fullscreen"
                />
                
                {/* Monitoring overlay for VNC - same as HLS */}
                {monitoringMode && (
                  <Box
                    sx={{
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      right: 0,
                      bottom: 0,
                      pointerEvents: 'none',
                      zIndex: 100,
                    }}
                  >
                    <MonitoringOverlay
                      monitoringAnalysis={monitoringAnalysis || undefined}
                      subtitleAnalysis={subtitleAnalysis}
                      languageMenuAnalysis={languageMenuAnalysis}
                      consecutiveErrorCounts={errorTrendData || undefined}
                      showSubtitles={!!subtitleAnalysis}
                      showLanguageMenu={!!languageMenuAnalysis}
                      analysisTimestamp={analysisTimestamp || undefined}
                      isAIAnalyzing={isAIAnalyzing}
                    />
                  </Box>
                )}
              </Box>
            );
          })()
        ) : (
          <EnhancedHLSPlayer
            deviceId={device?.device_id || 'device1'}
            hostName={host.host_name}
            host={host}
            streamUrl={effectiveStreamUrl}
            width="100%"
            height={finalStreamContainerDimensions.height}
            muted={isMuted}
            isLiveMode={isLiveMode}
            quality={currentQuality}
            shouldPause={shouldPausePlayer}
            onPlayerReady={onPlayerReady}
            onVideoTimeUpdate={onVideoTimeUpdate}
            onVideoPause={onVideoPause}
            onCurrentSegmentChange={onCurrentSegmentChange}
            // Monitoring overlay props
            monitoringMode={monitoringMode}
            monitoringAnalysis={monitoringAnalysis}
            subtitleAnalysis={subtitleAnalysis}
            languageMenuAnalysis={languageMenuAnalysis}
            aiDescription={aiDescription}
            errorTrendData={errorTrendData}
            analysisTimestamp={analysisTimestamp}
            isAIAnalyzing={isAIAnalyzing}
          />
        )
      ) : (
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            height: '100%',
            color: 'white',
          }}
        >
          <Typography>
            {isLoadingUrl
              ? 'Loading stream...'
              : urlError
                ? 'Stream error'
                : 'No stream available'}
          </Typography>
        </Box>
      )}
    </Box>
  );
};
