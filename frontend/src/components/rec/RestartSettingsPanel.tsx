import { Box, Typography, IconButton, Slide, Paper, Checkbox, FormControlLabel, Select, MenuItem, Divider, FormControl, InputLabel, Collapse } from '@mui/material';
import { Close as CloseIcon, ExpandMore as ExpandMoreIcon, ExpandLess as ExpandLessIcon } from '@mui/icons-material';
import React, { useState } from 'react';

interface RestartSettingsPanelProps {
  open: boolean;
  onClose: () => void;
  showSummaryOverlay: boolean;
  onToggleSummary: (show: boolean) => void;
  showSubtitleOverlay: boolean;
  onToggleSubtitle: (show: boolean) => void;
  showAudioTranscriptOverlay: boolean;
  onToggleAudioTranscript: (show: boolean) => void;
  summaryLanguage: string;
  onSummaryLanguageChange: (lang: string) => void;
  subtitleLanguage: string;
  onSubtitleLanguageChange: (lang: string) => void;
  subtitleStyle: string;
  onSubtitleStyleChange: (style: string) => void;
  subtitleFontSize: string;
  onSubtitleFontSizeChange: (size: string) => void;
  videoDescription?: {
    frame_descriptions: string[];
    video_summary: string;
    frames_analyzed: number;
    execution_time_ms: number;
  };
  audioTranscript?: string;
}

export const RestartSettingsPanel: React.FC<RestartSettingsPanelProps> = ({
  open,
  onClose,
  showSummaryOverlay,
  onToggleSummary,
  showSubtitleOverlay,
  onToggleSubtitle,
  showAudioTranscriptOverlay,
  onToggleAudioTranscript,
  summaryLanguage,
  onSummaryLanguageChange,
  subtitleLanguage,
  onSubtitleLanguageChange,
  subtitleStyle,
  onSubtitleStyleChange,
  subtitleFontSize,
  onSubtitleFontSizeChange,
  videoDescription,
  audioTranscript,
}) => {
  const [isTranscriptExpanded, setIsTranscriptExpanded] = useState(false);
  const [isVideoDescriptionExpanded, setIsVideoDescriptionExpanded] = useState(false);
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
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1.5 }}>
          <Typography variant="h6" sx={{ fontSize: '1.1rem' }}>Settings</Typography>
          <IconButton onClick={onClose} sx={{ color: '#ffffff', p: 0.5 }}>
            <CloseIcon fontSize="small" />
          </IconButton>
        </Box>

        {/* Video Summary */}
        <Box sx={{ 
          pb: 1.5, 
          mb: 1.5, 
          borderBottom: '1px solid rgba(255,255,255,0.2)' 
        }}>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 0.8 }}>
            <Checkbox
              checked={showSummaryOverlay}
              onChange={(e) => onToggleSummary(e.target.checked)}
              sx={{ color: '#ffffff', p: 0.5, mr: 0.5 }}
              size="small"
            />
            <Typography 
              variant="subtitle2" 
              sx={{ 
                fontSize: '0.85rem', 
                fontWeight: 600,
                flex: 1,
                cursor: 'pointer'
              }}
              onClick={() => setIsVideoDescriptionExpanded(!isVideoDescriptionExpanded)}
            >
              Video Summary
            </Typography>
            {videoDescription && (
              <IconButton
                onClick={() => setIsVideoDescriptionExpanded(!isVideoDescriptionExpanded)}
                sx={{ color: '#ffffff', p: 0.25 }}
                size="small"
              >
                {isVideoDescriptionExpanded ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
              </IconButton>
            )}
          </Box>
          <Select
            value={summaryLanguage}
            onChange={(e) => onSummaryLanguageChange(e.target.value)}
            size="small"
            sx={{ 
              ml: 1, 
              minHeight: 28,
              fontSize: '0.75rem',
              color: '#ffffff', 
              '& .MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(255,255,255,0.3)' },
              '& .MuiSelect-select': { py: 0.5 }
            }}
          >
            <MenuItem value="en" sx={{ fontSize: '0.75rem' }}>English</MenuItem>
            <MenuItem value="es" sx={{ fontSize: '0.75rem' }}>Spanish</MenuItem>
            <MenuItem value="fr" sx={{ fontSize: '0.75rem' }}>French</MenuItem>
          </Select>
          
          {videoDescription && (
            <Collapse in={isVideoDescriptionExpanded}>
              <Box sx={{ mt: 1 }}>
                {/* Frame Descriptions */}
                {videoDescription.frame_descriptions && videoDescription.frame_descriptions.length > 0 && (
                  <Box sx={{ mb: 1.5 }}>
                    {videoDescription.frame_descriptions.map((description, index) => (
                      <Typography 
                        key={index}
                        variant="body2" 
                        sx={{ 
                          mb: 0.8,
                          p: 1,
                          fontSize: '0.7rem',
                          backgroundColor: 'rgba(255,255,255,0.08)', 
                          borderRadius: 0.5,
                          lineHeight: 1.3,
                          borderLeft: '2px solid rgba(255,255,255,0.3)'
                        }}
                      >
                        <strong>Frame {index + 1}:</strong> {description}
                      </Typography>
                    ))}
                  </Box>
                )}
                
                {/* Final Summary */}
                {videoDescription.video_summary && (
                  <Typography variant="body2" sx={{ 
                    p: 1.5, 
                    fontSize: '0.75rem',
                    backgroundColor: 'rgba(255,255,255,0.15)', 
                    borderRadius: 1,
                    lineHeight: 1.3,
                    borderLeft: '3px solid #4CAF50'
                  }}>
                    <strong>Final Summary:</strong> {videoDescription.video_summary}
                  </Typography>
                )}
              </Box>
            </Collapse>
          )}
        </Box>

        {/* Subtitles */}
        <Box sx={{ 
          pb: 1.5, 
          mb: 1.5, 
          borderBottom: '1px solid rgba(255,255,255,0.2)' 
        }}>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 0.8 }}>
            <Checkbox
              checked={showSubtitleOverlay}
              onChange={(e) => onToggleSubtitle(e.target.checked)}
              sx={{ color: '#ffffff', p: 0.5, mr: 0.5 }}
              size="small"
            />
            <Typography variant="subtitle2" sx={{ fontSize: '0.85rem', fontWeight: 600 }}>
              Subtitles
            </Typography>
          </Box>
          
          <Box sx={{ display: 'flex', gap: 0.8, flexWrap: 'wrap' }}>
            <Select
              value={subtitleLanguage}
              onChange={(e) => onSubtitleLanguageChange(e.target.value)}
              size="small"
              sx={{ 
                minWidth: 85, 
                minHeight: 28,
                fontSize: '0.75rem',
                color: '#ffffff', 
                '& .MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(255,255,255,0.3)' },
                '& .MuiSelect-select': { py: 0.5 }
              }}
            >
              <MenuItem value="en" sx={{ fontSize: '0.75rem' }}>English</MenuItem>
              <MenuItem value="es" sx={{ fontSize: '0.75rem' }}>Spanish</MenuItem>
              <MenuItem value="fr" sx={{ fontSize: '0.75rem' }}>French</MenuItem>
            </Select>
            
            <Select
              value={subtitleStyle}
              onChange={(e) => onSubtitleStyleChange(e.target.value)}
              size="small"
              sx={{ 
                minWidth: 100, 
                minHeight: 28,
                fontSize: '0.75rem',
                color: '#ffffff', 
                '& .MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(255,255,255,0.3)' },
                '& .MuiSelect-select': { py: 0.5 }
              }}
            >
              <MenuItem value="yellow" sx={{ fontSize: '0.75rem' }}>Yellow</MenuItem>
              <MenuItem value="white" sx={{ fontSize: '0.75rem' }}>White</MenuItem>
              <MenuItem value="white-border" sx={{ fontSize: '0.75rem' }}>White Border</MenuItem>
              <MenuItem value="black-bg" sx={{ fontSize: '0.75rem' }}>Black Background</MenuItem>
            </Select>
            
            <Select
              value={subtitleFontSize}
              onChange={(e) => onSubtitleFontSizeChange(e.target.value)}
              size="small"
              sx={{ 
                minWidth: 70, 
                minHeight: 28,
                fontSize: '0.75rem',
                color: '#ffffff', 
                '& .MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(255,255,255,0.3)' },
                '& .MuiSelect-select': { py: 0.5 }
              }}
            >
              <MenuItem value="small" sx={{ fontSize: '0.75rem' }}>Small</MenuItem>
              <MenuItem value="medium" sx={{ fontSize: '0.75rem' }}>Medium</MenuItem>
              <MenuItem value="large" sx={{ fontSize: '0.75rem' }}>Large</MenuItem>
            </Select>
          </Box>
        </Box>

        {/* Audio Transcript */}
        <Box>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 0.8 }}>
            <Checkbox
              checked={showAudioTranscriptOverlay}
              onChange={(e) => onToggleAudioTranscript(e.target.checked)}
              sx={{ color: '#ffffff', p: 0.5, mr: 0.5 }}
              size="small"
            />
            <Typography 
              variant="subtitle2" 
              sx={{ 
                fontSize: '0.85rem', 
                fontWeight: 600,
                flex: 1,
                cursor: 'pointer'
              }}
              onClick={() => setIsTranscriptExpanded(!isTranscriptExpanded)}
            >
              Audio Transcript
            </Typography>
            <IconButton
              onClick={() => setIsTranscriptExpanded(!isTranscriptExpanded)}
              sx={{ color: '#ffffff', p: 0.25 }}
              size="small"
            >
              {isTranscriptExpanded ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
            </IconButton>
          </Box>
          <Collapse in={isTranscriptExpanded}>
            <Typography variant="body2" sx={{ 
              p: 1.5, 
              fontSize: '0.75rem',
              lineHeight: 1.4,
              backgroundColor: 'rgba(255,255,255,0.1)', 
              borderRadius: 1, 
              maxHeight: 120, 
              overflow: 'auto' 
            }}>
              {audioTranscript || 'No transcript available'}
            </Typography>
          </Collapse>
        </Box>
      </Paper>
    </Slide>
  );
};
