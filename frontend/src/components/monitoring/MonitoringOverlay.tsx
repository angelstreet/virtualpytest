import { Box, Typography } from '@mui/material';
import React from 'react';

import { MonitoringAnalysis, SubtitleAnalysis, LanguageMenuAnalysis } from '../../types/pages/Monitoring_Types';

interface ConsecutiveErrorCounts {
  blackscreenConsecutive: number;
  freezeConsecutive: number;
  audioLossConsecutive: number;
  hasWarning: boolean;
  hasError: boolean;
}

interface MonitoringOverlayProps {
  sx?: any;
  monitoringAnalysis?: MonitoringAnalysis; // Core audio/video monitoring data from backend
  subtitleAnalysis?: SubtitleAnalysis | null; // Subtitle analysis from frontend detection
  languageMenuAnalysis?: LanguageMenuAnalysis | null; // Language menu analysis from AI detection
  consecutiveErrorCounts?: ConsecutiveErrorCounts | null; // Consecutive error counts for trend indicators
  showSubtitles?: boolean; // Whether to show subtitle information in overlay
  showLanguageMenu?: boolean; // Whether to show language menu information in overlay
  analysisTimestamp?: string; // Timestamp of the JSON file being analyzed
}

export const MonitoringOverlay: React.FC<MonitoringOverlayProps> = ({
  sx,
  monitoringAnalysis,
  subtitleAnalysis,
  languageMenuAnalysis,
  consecutiveErrorCounts,
  showSubtitles = false,
  showLanguageMenu = false,
  analysisTimestamp,
}) => {
  // Use separate data sources
  const analysis = monitoringAnalysis;
  const subtitles = subtitleAnalysis;
  const languageMenu = languageMenuAnalysis;

  // Format timestamp for display (YYYYMMDDHHMMSS -> HH:MM:SS.000)
  const formatTimestamp = (timestamp?: string): string => {
    if (!timestamp || timestamp.length !== 14) return 'Unknown';
    
    const hour = timestamp.substring(8, 10);
    const minute = timestamp.substring(10, 12);
    const second = timestamp.substring(12, 14);
    
    // Add milliseconds (always .000 since we don't have sub-second precision)
    return `${hour}:${minute}:${second}.000`;
  };

  // Always render overlay with empty state when no analysis

  return (
    <>
      {/* Main analysis overlay - left aligned */}
      <Box
        sx={{
          position: 'absolute',
          top: 16,
          left: 16,
          zIndex: 20,
          p: 2,
          backgroundColor: 'rgba(0, 0, 0, 0.7)',
          borderRadius: 1,
          pointerEvents: 'none', // Don't interfere with clicks
          minWidth: 200,
          ...sx,
        }}
      >
        {/* Analysis Timestamp */}
        {analysisTimestamp && (
          <Typography variant="body2" sx={{ color: '#ffffff', mb: 0.5 }}>
            {formatTimestamp(analysisTimestamp)}
          </Typography>
        )}

        {/* Blackscreen */}
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 0.5 }}>
          <Typography variant="body2" sx={{ color: '#ffffff', mr: 1 }}>
            Blackscreen:
          </Typography>
          <Typography
            variant="body2"
            sx={{
              color: analysis?.blackscreen ? '#ff4444' : '#00ff00',
              fontWeight: analysis?.blackscreen ? 'bold' : 'normal',
            }}
          >
            {analysis?.blackscreen ? 'Yes' : 'No'}
            {analysis?.blackscreen && consecutiveErrorCounts && (
              <Typography component="span" variant="body2" sx={{ color: '#cccccc', ml: 1 }}>
                ({consecutiveErrorCounts.blackscreenConsecutive})
              </Typography>
            )}
          </Typography>
        </Box>

        {/* Freeze */}
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 0.5 }}>
          <Typography variant="body2" sx={{ color: '#ffffff', mr: 1 }}>
            Freeze:
          </Typography>
          <Typography
            variant="body2"
            sx={{
              color: analysis?.freeze ? '#ff4444' : '#00ff00',
              fontWeight: analysis?.freeze ? 'bold' : 'normal',
            }}
          >
            {analysis?.freeze ? 'Yes' : 'No'}
            {analysis?.freeze && consecutiveErrorCounts && (
              <Typography component="span" variant="body2" sx={{ color: '#cccccc', ml: 1 }}>
                ({consecutiveErrorCounts.freezeConsecutive})
              </Typography>
            )}
          </Typography>
        </Box>

        {/* Audio */}
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 0.5 }}>
          <Typography variant="body2" sx={{ color: '#ffffff', mr: 1 }}>
            Audio:
          </Typography>
          <Typography
            variant="body2"
            sx={{
              color: analysis?.audio ? '#00ff00' : '#ff4444',
              fontWeight: analysis?.audio ? 'bold' : 'normal',
            }}
          >
            {analysis?.audio ? 'Yes' : 'No'}
            {!analysis?.audio && consecutiveErrorCounts && (
              <Typography component="span" variant="body2" sx={{ color: '#cccccc', ml: 1 }}>
                ({consecutiveErrorCounts.audioLossConsecutive})
              </Typography>
            )}
          </Typography>
        </Box>

        {/* Subtitles - only shown when explicitly requested */}
        {showSubtitles && (
          <Box sx={{ mb: 0.5 }}>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <Typography variant="body2" sx={{ color: '#ffffff', mr: 1 }}>
                Subtitles:
              </Typography>
              <Typography
                variant="body2"
                sx={{
                  color: subtitles?.subtitles_detected ? '#00ff00' : '#ffffff',
                  fontWeight: subtitles?.subtitles_detected ? 'bold' : 'normal',
                }}
              >
                {subtitles?.subtitles_detected ? 'Yes' : 'No'}
                {subtitles?.subtitles_detected && subtitles?.detected_language && (
                  <Typography component="span" variant="body2" sx={{ color: '#cccccc', ml: 1 }}>
                    ({subtitles.detected_language})
                  </Typography>
                )}
              </Typography>
            </Box>
            {subtitles?.subtitles_detected && subtitles?.combined_extracted_text && (
              <Typography variant="body2" sx={{ color: '#ffffff', ml: 0, mt: 0.5 }}>
                Text:{' '}
                <Typography component="span" sx={{ color: '#cccccc' }}>
                  {subtitles.combined_extracted_text}
                </Typography>
              </Typography>
            )}
          </Box>
        )}

        {/* Language Menu - only shown when explicitly requested */}
        {showLanguageMenu && languageMenu?.menu_detected && (
          <Box sx={{ mb: 0.5 }}>
            {/* Audio Languages */}
            {languageMenu.audio_languages.length > 0 && (
              <Box sx={{ mb: 0.5 }}>
                <Typography variant="body2" sx={{ color: '#ffffff', mb: 0.3 }}>
                  Audio:
                </Typography>
                {languageMenu.audio_languages.map((lang, index) => (
                  <Typography
                    key={index}
                    variant="body2"
                    sx={{
                      color: index === languageMenu.selected_audio ? '#00ff00' : '#cccccc',
                      fontWeight: index === languageMenu.selected_audio ? 'bold' : 'normal',
                      ml: 1,
                      fontSize: '0.75rem',
                    }}
                  >
                    {index}: {lang}
                    {index === languageMenu.selected_audio && ' ✓'}
                  </Typography>
                ))}
              </Box>
            )}

            {/* Subtitle Languages */}
            {languageMenu.subtitle_languages.length > 0 && (
              <Box>
                <Typography variant="body2" sx={{ color: '#ffffff', mb: 0.3 }}>
                  Subtitles:
                </Typography>
                {languageMenu.subtitle_languages.map((lang, index) => (
                  <Typography
                    key={index}
                    variant="body2"
                    sx={{
                      color: index === languageMenu.selected_subtitle ? '#00ff00' : '#cccccc',
                      fontWeight: index === languageMenu.selected_subtitle ? 'bold' : 'normal',
                      ml: 1,
                      fontSize: '0.75rem',
                    }}
                  >
                    {index}: {lang}
                    {index === languageMenu.selected_subtitle && ' ✓'}
                  </Typography>
                ))}
              </Box>
            )}
          </Box>
        )}
      </Box>

      {/* Warning indicator - top right for 1-2 consecutive errors */}
      {consecutiveErrorCounts?.hasWarning && !consecutiveErrorCounts?.hasError && (
        <Box
          sx={{
            position: 'absolute',
            top: 16,
            right: 66, // 50px more from right edge to avoid online status
            zIndex: 20,
            p: 1,
            backgroundColor: 'rgba(255, 165, 0, 0.8)', // Orange
            borderRadius: 1,
            pointerEvents: 'none',
          }}
        >
          <Typography variant="caption" sx={{ color: '#ffffff', fontWeight: 'bold' }}>
            WARNING
          </Typography>
        </Box>
      )}

      {/* Error indicator - top right for 3+ consecutive errors */}
      {consecutiveErrorCounts?.hasError && (
        <Box
          sx={{
            position: 'absolute',
            top: 16,
            right: 66, // 50px more from right edge to avoid online status
            zIndex: 20,
            p: 1,
            backgroundColor: 'rgba(255, 68, 68, 0.8)', // Red
            borderRadius: 1,
            pointerEvents: 'none',
          }}
        >
          <Typography variant="caption" sx={{ color: '#ffffff', fontWeight: 'bold' }}>
            ERROR
          </Typography>
        </Box>
      )}
    </>
  );
};
