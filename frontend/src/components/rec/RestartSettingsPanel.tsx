import { Box, Typography, IconButton, Slide, Paper, Checkbox, FormControlLabel, Select, MenuItem } from '@mui/material';
import { Close as CloseIcon } from '@mui/icons-material';
import React from 'react';

interface RestartSettingsPanelProps {
  open: boolean;
  onClose: () => void;
  showSummaryOverlay: boolean;
  onToggleSummary: (show: boolean) => void;
  showSubtitleOverlay: boolean;
  onToggleSubtitle: (show: boolean) => void;
  summaryLanguage: string;
  onSummaryLanguageChange: (lang: string) => void;
  subtitleLanguage: string;
  onSubtitleLanguageChange: (lang: string) => void;
  videoDescription?: string;
  audioTranscript?: string;
}

export const RestartSettingsPanel: React.FC<RestartSettingsPanelProps> = ({
  open,
  onClose,
  showSummaryOverlay,
  onToggleSummary,
  showSubtitleOverlay,
  onToggleSubtitle,
  summaryLanguage,
  onSummaryLanguageChange,
  subtitleLanguage,
  onSubtitleLanguageChange,
  videoDescription,
  audioTranscript,
}) => {
  return (
    <Slide direction="left" in={open} mountOnEnter unmountOnExit>
      <Paper
        sx={{
          position: 'absolute',
          top: 0,
          right: 0,
          width: 350,
          height: '100%',
          zIndex: 1000040,
          backgroundColor: 'rgba(0, 0, 0, 0.95)',
          color: '#ffffff',
          p: 3,
          overflowY: 'auto',
        }}
      >
        {/* Header */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Typography variant="h6">Settings</Typography>
          <IconButton onClick={onClose} sx={{ color: '#ffffff' }}>
            <CloseIcon />
          </IconButton>
        </Box>

        {/* Video Summary */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="subtitle1" sx={{ mb: 2 }}>Video Summary</Typography>
          <FormControlLabel
            control={
              <Checkbox
                checked={showSummaryOverlay}
                onChange={(e) => onToggleSummary(e.target.checked)}
                sx={{ color: '#ffffff' }}
              />
            }
            label="Show Per-Second Summary"
          />
          <Select
            value={summaryLanguage}
            onChange={(e) => onSummaryLanguageChange(e.target.value)}
            size="small"
            sx={{ ml: 2, color: '#ffffff', '& .MuiOutlinedInput-notchedOutline': { borderColor: '#ffffff' } }}
          >
            <MenuItem value="en">English</MenuItem>
            <MenuItem value="es">Spanish</MenuItem>
            <MenuItem value="fr">French</MenuItem>
          </Select>
          
          {videoDescription && (
            <Typography variant="body2" sx={{ mt: 2, p: 2, backgroundColor: 'rgba(255,255,255,0.1)', borderRadius: 1 }}>
              {videoDescription}
            </Typography>
          )}
        </Box>

        {/* Subtitles */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="subtitle1" sx={{ mb: 2 }}>Subtitles</Typography>
          <FormControlLabel
            control={
              <Checkbox
                checked={showSubtitleOverlay}
                onChange={(e) => onToggleSubtitle(e.target.checked)}
                sx={{ color: '#ffffff' }}
              />
            }
            label="Show Subtitle Overlay"
          />
          <Select
            value={subtitleLanguage}
            onChange={(e) => onSubtitleLanguageChange(e.target.value)}
            size="small"
            sx={{ ml: 2, color: '#ffffff', '& .MuiOutlinedInput-notchedOutline': { borderColor: '#ffffff' } }}
          >
            <MenuItem value="en">English</MenuItem>
            <MenuItem value="es">Spanish</MenuItem>
            <MenuItem value="fr">French</MenuItem>
          </Select>
        </Box>

        {/* Audio Transcript */}
        <Box>
          <Typography variant="subtitle1" sx={{ mb: 2 }}>Audio Transcript</Typography>
          <Typography variant="body2" sx={{ p: 2, backgroundColor: 'rgba(255,255,255,0.1)', borderRadius: 1, maxHeight: 150, overflow: 'auto' }}>
            {audioTranscript || 'No transcript available'}
          </Typography>
        </Box>
      </Paper>
    </Slide>
  );
};
