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
    <Box
      sx={{
        position: 'absolute',
        bottom: 100,
        left: '50%',
        transform: 'translateX(-50%)',
        backgroundColor: 'rgba(0, 0, 0, 0.85)',
        color: 'white',
        px: 3,
        py: 1.5,
        borderRadius: 2,
        maxWidth: '80%',
        textAlign: 'center',
        border: currentTranscript.enhanced_transcript && selectedLanguage === 'original'
          ? '2px solid rgba(33, 150, 243, 0.8)'
          : '1px solid rgba(255, 255, 255, 0.3)',
        boxShadow: currentTranscript.enhanced_transcript && selectedLanguage === 'original'
          ? '0 4px 12px rgba(33, 150, 243, 0.4)'
          : '0 4px 12px rgba(0,0,0,0.5)',
      }}
    >
      {currentTranscript.enhanced_transcript && selectedLanguage === 'original' && (
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', mb: 0.5 }}>
          <AutoAwesome sx={{ fontSize: 16, color: '#2196f3', mr: 0.5 }} />
          <Typography variant="caption" sx={{ color: '#2196f3', fontWeight: 600 }}>
            AI Enhanced
          </Typography>
        </Box>
      )}
      
      <Typography variant="body2" sx={{ fontWeight: 500, lineHeight: 1.4 }}>
        {transcriptText}
      </Typography>
      <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.6)', mt: 0.5, display: 'block' }}>
        {selectedLanguage === 'original' 
          ? `${currentTranscript.language} • ${Math.round(currentTranscript.confidence * 100)}%`
          : `Translated to ${selectedLanguage}`
        }
      </Typography>
    </Box>
  );
};
