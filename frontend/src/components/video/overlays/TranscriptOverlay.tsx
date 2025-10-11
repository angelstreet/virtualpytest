import React, { useState } from 'react';
import { Box, Typography, IconButton, Menu, MenuItem, Chip } from '@mui/material';
import { AutoAwesome, Headphones, Language } from '@mui/icons-material';
import { TranscriptSegment } from '../EnhancedHLSPlayer.types';

interface TranscriptOverlayProps {
  currentTranscript: TranscriptSegment | null;
  transcriptText: string;
  selectedLanguage: string;
  availableLanguages?: string[];
  onLanguageChange?: (language: string) => void;
  isTranslating?: boolean;
  show: boolean;
  hasMp3?: boolean;
  mp3Url?: string | null;
}

export const TranscriptOverlay: React.FC<TranscriptOverlayProps> = ({
  currentTranscript,
  transcriptText,
  selectedLanguage,
  availableLanguages = ['original'],
  onLanguageChange,
  isTranslating = false,
  show,
  hasMp3,
  mp3Url,
}) => {
  const [languageMenuAnchor, setLanguageMenuAnchor] = useState<null | HTMLElement>(null);
  
  if (!show || !currentTranscript || !transcriptText) {
    return null;
  }

  const handleAudioClick = () => {
    if (mp3Url) {
      window.open(mp3Url, '_blank');
    }
  };
  
  const handleLanguageClick = (event: React.MouseEvent<HTMLElement>) => {
    setLanguageMenuAnchor(event.currentTarget);
  };
  
  const handleLanguageClose = () => {
    setLanguageMenuAnchor(null);
  };
  
  const handleLanguageSelect = (language: string) => {
    if (onLanguageChange) {
      onLanguageChange(language);
    }
    handleLanguageClose();
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
      {/* Audio button - top right */}
      {hasMp3 && mp3Url && (
        <IconButton
          onClick={handleAudioClick}
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
      
      {/* Language selector button - top right, below audio button */}
      {availableLanguages.length > 1 && (
        <>
          <IconButton
            onClick={handleLanguageClick}
            disabled={isTranslating}
            sx={{
              position: 'fixed',
              top: hasMp3 && mp3Url ? 72 : 16,
              right: 16,
              backgroundColor: 'rgba(0, 0, 0, 0.7)',
              color: 'white',
              zIndex: 1250,
              '&:hover': { backgroundColor: 'rgba(0, 0, 0, 0.85)' },
              '&.Mui-disabled': { backgroundColor: 'rgba(0, 0, 0, 0.5)', color: 'rgba(255, 255, 255, 0.5)' },
            }}
          >
            <Language />
          </IconButton>
          
          <Menu
            anchorEl={languageMenuAnchor}
            open={Boolean(languageMenuAnchor)}
            onClose={handleLanguageClose}
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
                onClick={() => handleLanguageSelect(lang)}
                selected={lang === selectedLanguage}
                sx={{
                  '&:hover': { backgroundColor: 'rgba(255, 255, 255, 0.1)' },
                  '&.Mui-selected': {
                    backgroundColor: 'rgba(33, 150, 243, 0.3)',
                    '&:hover': { backgroundColor: 'rgba(33, 150, 243, 0.4)' },
                  },
                }}
              >
                {languageNames[lang] || lang.toUpperCase()}
                {lang === selectedLanguage && ' ✓'}
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
              ? `${currentTranscript.language.charAt(0).toUpperCase() + currentTranscript.language.slice(1).toLowerCase()} • ${Math.round(currentTranscript.confidence * 100)}%`
              : `Translated to ${selectedLanguage}`
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
