import React, { useState } from 'react';
import { Box, Typography, IconButton, Menu, MenuItem, CircularProgress } from '@mui/material';
import { Headphones, Language } from '@mui/icons-material';

interface TranscriptOverlayProps {
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
  
  // Show only if we have transcript text
  if (!show || !transcriptText) {
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
  
  // All supported transcript languages (always available on-demand)
  const allTranscriptLanguages = ['original', 'fr', 'en', 'es', 'de', 'it'];

  return (
    <>
      {/* Loading indicator for translation/dubbing */}
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
            🤖 AI translating...
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
            top: 80,
            right: 36,
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
              top: 80,
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

      {/* Transcript/Subtitle language selector - always show (on-demand translation) */}
      <IconButton
        onClick={handleTranscriptClick}
        disabled={isTranslating}
        title="Subtitle Language"
        sx={{
          position: 'fixed',
          top: availableDubbedLanguages.length > 0 ? 136 : 80,
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
        {allTranscriptLanguages.map((lang) => {
          const isCached = availableLanguages.includes(lang);
          return (
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
              {!isCached && lang !== 'original' && ' 🤖'}
            </MenuItem>
          );
        })}
      </Menu>


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
          border: '1px solid rgba(255, 255, 255, 0.3)',
          boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
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
