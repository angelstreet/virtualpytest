import React from 'react';
import { Box, Select, MenuItem, CircularProgress } from '@mui/material';
import { Translate } from '@mui/icons-material';
import { TranscriptDataLegacy } from '../EnhancedHLSPlayer.types';

interface LanguageSelectorProps {
  transcriptData: TranscriptDataLegacy | null;
  selectedLanguage: string;
  isTranslating: boolean;
  onLanguageChange: (language: string) => void;
  show: boolean;
  detectedLanguage?: string;
}

export const LanguageSelector: React.FC<LanguageSelectorProps> = ({
  transcriptData,
  selectedLanguage,
  isTranslating,
  onLanguageChange,
  show,
  detectedLanguage,
}) => {
  if (!show || !transcriptData || !transcriptData.segments || transcriptData.segments.length === 0) {
    return null;
  }

  // Format detected language name for display
  const formatLanguageName = (lang?: string): string => {
    if (!lang) return 'Original';
    // Capitalize first letter
    return lang.charAt(0).toUpperCase() + lang.slice(1).toLowerCase();
  };

  const originalLabel = detectedLanguage ? formatLanguageName(detectedLanguage) : 'Original';

  return (
    <Box
      sx={{
        position: 'absolute',
        top: 10,
        right: 10,
        display: 'flex',
        flexDirection: 'column',
        gap: 0.5,
      }}
    >
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 1,
          backgroundColor: 'rgba(0, 0, 0, 0.7)',
          borderRadius: 1,
          p: 1,
        }}
      >
        <Translate sx={{ color: 'white', fontSize: 20 }} />
        <Select
          value={selectedLanguage}
          onChange={(e) => onLanguageChange(e.target.value)}
          size="small"
          disabled={isTranslating}
          sx={{
            color: 'white',
            minWidth: 120,
            '& .MuiOutlinedInput-notchedOutline': {
              borderColor: 'rgba(255, 255, 255, 0.3)',
            },
            '&:hover .MuiOutlinedInput-notchedOutline': {
              borderColor: 'rgba(255, 255, 255, 0.5)',
            },
            '& .MuiSvgIcon-root': {
              color: 'white',
            },
          }}
        >
          <MenuItem value="original">{originalLabel}</MenuItem>
          <MenuItem value="French">French</MenuItem>
          <MenuItem value="Spanish">Spanish</MenuItem>
          <MenuItem value="German">German</MenuItem>
          <MenuItem value="Italian">Italian</MenuItem>
          <MenuItem value="Portuguese">Portuguese</MenuItem>
        </Select>
        {isTranslating && <CircularProgress size={20} sx={{ color: 'white' }} />}
      </Box>
    </Box>
  );
};
