import React from 'react';
import { Box, Typography } from '@mui/material';
import { AutoAwesome } from '@mui/icons-material';
import { TranscriptSegment } from '../EnhancedHLSPlayer.types';

interface TranscriptOverlayProps {
  currentTranscript: TranscriptSegment | null;
  transcriptText: string;
  selectedLanguage: string;
  show: boolean;
}

export const TranscriptOverlay: React.FC<TranscriptOverlayProps> = ({
  currentTranscript,
  transcriptText,
  selectedLanguage,
  show,
}) => {
  if (!show || !currentTranscript || !transcriptText) {
    return null;
  }

  return (
    <>
      {/* Language and confidence info - positioned above transcript box */}
      <Box
        sx={{
          position: 'fixed',
          bottom: 135,  // Position above the transcript box
          left: '50%',
          transform: 'translateX(-50%)',
          display: 'flex',
          alignItems: 'center',
          gap: 1,
          zIndex: 1250,
        }}
      >
        {currentTranscript.enhanced_transcript && selectedLanguage === 'original' && (
          <Box sx={{ display: 'flex', alignItems: 'center', backgroundColor: 'rgba(0, 0, 0, 0.7)', px: 1, py: 0.5, borderRadius: 1 }}>
            <AutoAwesome sx={{ fontSize: 14, color: '#2196f3', mr: 0.5 }} />
            <Typography variant="caption" sx={{ color: '#2196f3', fontWeight: 600, fontSize: '0.7rem' }}>
              AI Enhanced
            </Typography>
          </Box>
        )}
        
        <Box sx={{ backgroundColor: 'rgba(0, 0, 0, 0.7)', px: 1.5, py: 0.5, borderRadius: 1 }}>
          <Typography 
            variant="caption" 
            sx={{ 
              color: 'rgba(255,255,255,0.8)', 
              fontSize: '0.7rem',
              fontWeight: 500,
            }}
          >
            {selectedLanguage === 'original' 
              ? `${currentTranscript.language} • ${Math.round(currentTranscript.confidence * 100)}%`
              : `Translated to ${selectedLanguage}`
            }
          </Typography>
        </Box>
      </Box>

      {/* Transcript box - only 2 lines */}
      <Box
        sx={{
          position: 'fixed',
          bottom: 85,  // Much closer to timeline (timeline takes ~80px from bottom)
          left: '50%',
          transform: 'translateX(-50%)',
          backgroundColor: 'rgba(0, 0, 0, 0.85)',
          color: 'white',
          px: 2,
          py: 1,
          borderRadius: 1,
          maxWidth: 'calc(100% - 80px)',  // Window width minus 80px
          width: 'calc(100% - 80px)',      // Use full available width
          textAlign: 'center',
          border: currentTranscript.enhanced_transcript && selectedLanguage === 'original'
            ? '2px solid rgba(33, 150, 243, 0.8)'
            : '1px solid rgba(255, 255, 255, 0.3)',
          boxShadow: currentTranscript.enhanced_transcript && selectedLanguage === 'original'
            ? '0 4px 12px rgba(33, 150, 243, 0.4)'
            : '0 4px 12px rgba(0,0,0,0.5)',
          zIndex: 1250,  // Below timeline (which is 1300) but above video
        }}
      >
        <Typography 
          variant="body1" 
          sx={{ 
            fontWeight: 500, 
            lineHeight: 1.3,
            fontSize: '0.95rem',
            // Limit to 2 lines with ellipsis
            display: '-webkit-box',
            WebkitLineClamp: 2,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            // Add text shadow for better readability
            textShadow: '1px 1px 2px rgba(0, 0, 0, 0.8)',
          }}
        >
          {transcriptText}
        </Typography>
      </Box>
    </>
  );
};
