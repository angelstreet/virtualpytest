import React, { useState } from 'react';
import { Box, Typography, IconButton, Menu, MenuItem, CircularProgress } from '@mui/material';
import { AutoAwesome, Headphones, Language } from '@mui/icons-material';
import { TranscriptSegment } from '../EnhancedHLSPlayer.types';

interface TranscriptOverlayProps {
  currentTranscript: TranscriptSegment | null;
  transcriptText: string;
  
  // Separate language controls for audio and transcript
  selectedAudioLanguage?: string;
  selectedTranscriptLanguage?: string;
  availableLanguages?: string[];
  availableDubbedLanguages?: string[];
  onAudioLanguageChange?: (language: string) => void;
  onTranscriptLanguageChange?: (language: string) => void;
  
  isTranslating?: boolean;
  show: boolean;
  hasMp3?: boolean;
  mp3Url?: string | null;
}

export const TranscriptOverlay: React.FC<TranscriptOverlayProps> = ({
  currentTranscript,
  transcriptText,
  selectedAudioLanguage = 'original',
  selectedTranscriptLanguage = 'original',
  availableLanguages = ['original'],
  availableDubbedLanguages = [],
  onAudioLanguageChange,
  onTranscriptLanguageChange,
  isTranslating = false,
  show,
  hasMp3,
  mp3Url,
}) => {
  const [audioMenuAnchor, setAudioMenuAnchor] = useState<null | HTMLElement>(null);
  const [transcriptMenuAnchor, setTranscriptMenuAnchor] = useState<null | HTMLElement>(null);
  
  if (!show || !currentTranscript || !transcriptText) {
    return null;
  }

  const handleMp3Click = () => {
    if (mp3Url) {
      window.open(mp3Url, '_blank');
    }
  };
  
  // Audio language menu handlers
  const handleAudioClick = (event: React.MouseEvent<HTMLElement>) => {
    setAudioMenuAnchor(event.currentTarget);
  };

  const handleAudioClose = () => {
    setAudioMenuAnchor(null);
  };

  const handleAudioSelect = (language: string) => {
    if (onAudioLanguageChange) {
      onAudioLanguageChange(language);
    }
    setAudioMenuAnchor(null);
  };

  // Transcript language menu handlers
  const handleTranscriptClick = (event: React.MouseEvent<HTMLElement>) => {
    setTranscriptMenuAnchor(event.currentTarget);
  };

  const handleTranscriptClose = () => {
    setTranscriptMenuAnchor(null);
  };

  const handleTranscriptSelect = (language: string) => {
    if (onTranscriptLanguageChange) {
      onTranscriptLanguageChange(language);
    }
    setTranscriptMenuAnchor(null);
  };
  
  // Language display names
  const languageNames: { [key: string]: string } = {
    'original': 'Original',
    'en': 'English',
    'fr': 'Français',
    'es': 'Español',
    'de': 'Deutsch',
    'it': 'Italiano'
  };

  return (
    <>
      {/* Loading indicator for dubbed audio generation */}
      {isTranslating && (
        <Box
          sx={{
            position: 'fixed',
            top: 200,
            right: 16,
            zIndex: 1250,
            backgroundColor: 'rgba(0, 0, 0, 0.85)',
            color: 'white',
            padding: '12px 16px',
            borderRadius: '8px',
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
          }}
        >
          <CircularProgress size={20} sx={{ color: '#2196f3' }} />
          <Typography variant="caption" sx={{ fontSize: '13px', fontWeight: 500 }}>
            Generating dubbed audio...
          </Typography>
        </Box>
      )}
      
      {/* Audio MP3 download button - top right */}
      {hasMp3 && mp3Url && (
        <IconButton
          onClick={handleMp3Click}
          title="Download MP3"
          sx={{
            position: 'fixed',
            top: 16,
            right: 16,
            backgroundColor: 'rgba(0, 0, 0, 0.7)',
            color: 'white',
            zIndex: 1250,
            '&:hover': { backgroundColor: 'rgba(0, 0, 0, 0.85)' },
          }}
        >
          <Headphones />
        </IconButton>
      )}

      {/* Audio language selector (dubbed audio) */}
      {availableDubbedLanguages.length > 0 && (
        <>
          <IconButton
            onClick={handleAudioClick}
            disabled={isTranslating}
            title="Audio Language"
            sx={{
              position: 'fixed',
              top: hasMp3 && mp3Url ? 72 : 16,
              right: 16,
              backgroundColor: 'rgba(156, 39, 176, 0.8)',
              color: 'white',
              zIndex: 1250,
              '&:hover': { backgroundColor: 'rgba(156, 39, 176, 0.95)' },
              '&.Mui-disabled': { backgroundColor: 'rgba(156, 39, 176, 0.5)', color: 'rgba(255, 255, 255, 0.5)' },
            }}
          >
            <Headphones />
          </IconButton>
          
          <Menu
            anchorEl={audioMenuAnchor}
            open={Boolean(audioMenuAnchor)}
            onClose={handleAudioClose}
            sx={{
              '& .MuiPaper-root': {
                backgroundColor: 'rgba(0, 0, 0, 0.9)',
                color: 'white',
              },
            }}
          >
            <MenuItem
              onClick={() => handleAudioSelect('original')}
              selected={selectedAudioLanguage === 'original'}
              sx={{
                '&:hover': { backgroundColor: 'rgba(255, 255, 255, 0.1)' },
                '&.Mui-selected': {
                  backgroundColor: 'rgba(156, 39, 176, 0.3)',
                  '&:hover': { backgroundColor: 'rgba(156, 39, 176, 0.4)' },
                },
              }}
            >
              Original Audio {selectedAudioLanguage === 'original' && ' ✓'}
            </MenuItem>
            {availableDubbedLanguages.map((lang) => (
              <MenuItem
                key={lang}
                onClick={() => handleAudioSelect(lang)}
                selected={lang === selectedAudioLanguage}
                sx={{
                  '&:hover': { backgroundColor: 'rgba(255, 255, 255, 0.1)' },
                  '&.Mui-selected': {
                    backgroundColor: 'rgba(156, 39, 176, 0.3)',
                    '&:hover': { backgroundColor: 'rgba(156, 39, 176, 0.4)' },
                  },
                }}
              >
                {languageNames[lang] || lang.toUpperCase()}
                {lang === selectedAudioLanguage && ' ✓'}
              </MenuItem>
            ))}
          </Menu>
        </>
      )}

      {/* Transcript/Subtitle language selector */}
      {availableLanguages.length > 1 && (
        <>
          <IconButton
            onClick={handleTranscriptClick}
            disabled={isTranslating}
            title="Subtitle Language"
            sx={{
              position: 'fixed',
              top: hasMp3 && mp3Url ? (availableDubbedLanguages.length > 0 ? 128 : 72) : (availableDubbedLanguages.length > 0 ? 72 : 16),
              right: 16,
              backgroundColor: 'rgba(33, 150, 243, 0.8)',
              color: 'white',
              zIndex: 1250,
              '&:hover': { backgroundColor: 'rgba(33, 150, 243, 0.95)' },
              '&.Mui-disabled': { backgroundColor: 'rgba(33, 150, 243, 0.5)', color: 'rgba(255, 255, 255, 0.5)' },
            }}
          >
            <Language />
          </IconButton>
          
          <Menu
            anchorEl={transcriptMenuAnchor}
            open={Boolean(transcriptMenuAnchor)}
            onClose={handleTranscriptClose}
            sx={{
              '& .MuiPaper-root': {
                backgroundColor: 'rgba(0, 0, 0, 0.9)',
                color: 'white',
              },
            }}
          >
            {availableLanguages.map((lang) => (
              <MenuItem
                key={lang}
                onClick={() => handleTranscriptSelect(lang)}
                selected={lang === selectedTranscriptLanguage}
                sx={{
                  '&:hover': { backgroundColor: 'rgba(255, 255, 255, 0.1)' },
                  '&.Mui-selected': {
                    backgroundColor: 'rgba(33, 150, 243, 0.3)',
                    '&:hover': { backgroundColor: 'rgba(33, 150, 243, 0.4)' },
                  },
                }}
              >
                {languageNames[lang] || lang.toUpperCase()}
                {lang === selectedTranscriptLanguage && ' ✓'}
              </MenuItem>
            ))}
          </Menu>
        </>
      )}

      {/* Language and confidence info - positioned above transcript box */}
      <Box
        sx={{
          position: 'fixed',
          bottom: 115,  // Position above the transcript box
          left: '40px',  // Left aligned
          display: 'flex',
          alignItems: 'center',
          gap: 1,
          zIndex: 1250,
        }}
      >
        {currentTranscript.enhanced_transcript && selectedTranscriptLanguage === 'original' && (
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
            {selectedTranscriptLanguage === 'original' 
              ? `${currentTranscript.language.charAt(0).toUpperCase() + currentTranscript.language.slice(1).toLowerCase()} • ${Math.round(currentTranscript.confidence * 100)}%`
              : `Translated to ${languageNames[selectedTranscriptLanguage] || selectedTranscriptLanguage}`
            }
          </Typography>
        </Box>
      </Box>

      {/* Transcript box - only 2 lines */}
      <Box
        sx={{
          position: 'fixed',
          bottom: 80,  // Much closer to timeline (timeline takes ~80px from bottom)
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
          border: currentTranscript.enhanced_transcript && selectedTranscriptLanguage === 'original'
            ? '2px solid rgba(33, 150, 243, 0.8)'
            : '1px solid rgba(255, 255, 255, 0.3)',
          boxShadow: currentTranscript.enhanced_transcript && selectedTranscriptLanguage === 'original'
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
      
      {/* Status indicators */}
      <Box sx={{ position: 'fixed', bottom: 16, left: 16, zIndex: 1250, display: 'flex', flexDirection: 'column', gap: 1 }}>
        {selectedAudioLanguage !== 'original' && (
          <Box
            sx={{
              padding: '6px 12px',
              backgroundColor: 'rgba(156, 39, 176, 0.8)',
              color: 'white',
              borderRadius: '4px',
              fontSize: '12px',
              fontWeight: 500,
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            🎤 Audio: {languageNames[selectedAudioLanguage] || selectedAudioLanguage.toUpperCase()}
          </Box>
        )}
        {selectedTranscriptLanguage !== 'original' && (
          <Box
            sx={{
              padding: '6px 12px',
              backgroundColor: 'rgba(33, 150, 243, 0.8)',
              color: 'white',
              borderRadius: '4px',
              fontSize: '12px',
              fontWeight: 500,
            }}
          >
            💬 Subtitles: {languageNames[selectedTranscriptLanguage] || selectedTranscriptLanguage.toUpperCase()}
          </Box>
        )}
      </Box>
    </>
  );
};
