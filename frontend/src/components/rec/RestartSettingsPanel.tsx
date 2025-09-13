import { Box, Typography, IconButton, Slide, Paper, Checkbox, Select, MenuItem, Collapse, CircularProgress } from '@mui/material';
import { Close as CloseIcon, ExpandMore as ExpandMoreIcon, ExpandLess as ExpandLessIcon } from '@mui/icons-material';
import React, { useState, useEffect } from 'react';
import { buildServerUrl } from '../../utils/buildUrlUtils';

interface RestartSettingsPanelProps {
  open: boolean;
  onClose: () => void;
  showSubtitleOverlay: boolean;
  onToggleSubtitle: (show: boolean) => void;
  showAudioTranscriptOverlay: boolean;
  onToggleAudioTranscript: (show: boolean) => void;
  summaryLanguage: string;
  onSummaryLanguageChange: (lang: string) => void;
  subtitleLanguage: string;
  onSubtitleLanguageChange: (lang: string) => void;
  audioTranscriptLanguage: string;
  onAudioTranscriptLanguageChange: (lang: string) => void;
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
  audioAnalysis?: {
    success: boolean;
    combined_transcript: string;
    detected_language: string;
    speech_detected: boolean;
    confidence: number;
    execution_time_ms: number;
  };
  subtitleData?: {
    success: boolean;
    subtitles_detected: boolean;
    extracted_text: string;
    detected_language?: string;
    execution_time_ms: number;
    frame_subtitles?: string[];
  };
}

export const RestartSettingsPanel: React.FC<RestartSettingsPanelProps> = ({
  open,
  onClose,
  showSubtitleOverlay,
  onToggleSubtitle,
  showAudioTranscriptOverlay,
  onToggleAudioTranscript,
  summaryLanguage: _summaryLanguage,
  onSummaryLanguageChange: _onSummaryLanguageChange,
  subtitleLanguage,
  onSubtitleLanguageChange,
  audioTranscriptLanguage,
  onAudioTranscriptLanguageChange,
  subtitleStyle,
  onSubtitleStyleChange,
  subtitleFontSize,
  onSubtitleFontSizeChange,
  videoDescription,
  audioTranscript,
  audioAnalysis,
  subtitleData,
}) => {
  const [isTranscriptExpanded, setIsTranscriptExpanded] = useState(false);
  const [isSubtitleExpanded, setIsSubtitleExpanded] = useState(false);
  const [translatedTranscript, setTranslatedTranscript] = useState<string>('');
  const [translatedSubtitle, setTranslatedSubtitle] = useState<string>('');
  const [isTranslatingAudio, setIsTranslatingAudio] = useState(false);

  // Language code to name mapping
  const getLanguageName = (code: string): string => {
    const languageNames: Record<string, string> = {
      'en': 'English',
      'es': 'Spanish', 
      'fr': 'French',
      'de': 'German',
      'it': 'Italian',
      'pt': 'Portuguese',
      'ru': 'Russian',
      'ja': 'Japanese',
      'ko': 'Korean',
      'zh': 'Chinese'
    };
    return languageNames[code.toLowerCase()] || code.toUpperCase();
  };

  // Translation cache to avoid re-translating same content
  const [translationCache, setTranslationCache] = useState<Record<string, string>>({});

  // Dynamic translation function with caching and backend API calls
  const translateText = async (text: string, targetLang: string, originalLang: string = 'en'): Promise<string> => {
    if (!text || targetLang === originalLang) return text;
    
    // Create cache key
    const cacheKey = `${originalLang}-${targetLang}-${text.substring(0, 50)}`;
    
    // Check cache first
    if (translationCache[cacheKey]) {
      return translationCache[cacheKey];
    }
    
    try {
      console.log(`[@component:RestartSettingsPanel] Translating text from ${originalLang} to ${targetLang}`);
      
      // Call backend translation API
      const response = await fetch(buildServerUrl('/server/translate/text'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: text,
          source_language: originalLang,
          target_language: targetLang
        }),
      });

      if (!response.ok) {
        throw new Error(`Translation API failed: ${response.status} ${response.statusText}`);
      }

      const result = await response.json();
      
      if (result.success) {
        const translatedText = result.translated_text || text;
        
        // Cache the result
        setTranslationCache(prev => ({
          ...prev,
          [cacheKey]: translatedText
        }));
        
        console.log(`[@component:RestartSettingsPanel] Translation successful: ${text.substring(0, 50)}... -> ${translatedText.substring(0, 50)}...`);
        return translatedText;
      } else {
        throw new Error(result.error || 'Translation failed');
      }
      
    } catch (error) {
      console.error('[@component:RestartSettingsPanel] Translation error:', error);
      // Return original text on error
      return text;
    }
  };

  // Effect to handle dynamic translation when language changes
  useEffect(() => {
    const handleTranslation = async () => {
      if (audioTranscript && audioTranscriptLanguage !== (audioAnalysis?.detected_language?.toLowerCase() || 'en')) {
        try {
          setIsTranslatingAudio(true);
          const translated = await translateText(
            audioTranscript, 
            audioTranscriptLanguage, 
            audioAnalysis?.detected_language?.toLowerCase() || 'en'
          );
          setTranslatedTranscript(translated);
        } catch (error) {
          console.error('Translation error:', error);
          setTranslatedTranscript(audioTranscript); // Fallback to original
        } finally {
          setIsTranslatingAudio(false);
        }
      } else {
        setTranslatedTranscript('');
        setIsTranslatingAudio(false);
      }
    };

    handleTranslation();
  }, [audioTranscript, audioTranscriptLanguage, audioAnalysis?.detected_language]);

  // Effect to handle subtitle translation when language changes
  useEffect(() => {
    const handleSubtitleTranslation = async () => {
      if (subtitleData?.extracted_text && subtitleLanguage !== (subtitleData?.detected_language?.toLowerCase() || 'en')) {
        try {
          const translated = await translateText(
            subtitleData.extracted_text, 
            subtitleLanguage, 
            subtitleData.detected_language?.toLowerCase() || 'en'
          );
          setTranslatedSubtitle(translated);
        } catch (error) {
          console.error('Subtitle translation error:', error);
          setTranslatedSubtitle(subtitleData.extracted_text); // Fallback to original
        }
      } else {
        setTranslatedSubtitle('');
      }
    };

    handleSubtitleTranslation();
  }, [subtitleData?.extracted_text, subtitleLanguage, subtitleData?.detected_language]);

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

        <Box sx={{ 
          pb: 1.5, 
          mb: 1.5, 
          borderBottom: '1px solid rgba(255,255,255,0.2)' 
        }}>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 0.8 }}>
            <Typography 
              variant="subtitle2" 
              sx={{ 
                fontSize: '0.85rem', 
                fontWeight: 600,
                flex: 1,
                cursor: 'pointer'
              }}
            >
              Video Summary
            </Typography>
            {videoDescription && (
              <IconButton
                sx={{ color: '#ffffff', p: 0.25 }}
                size="small"
              >
                <ExpandMoreIcon fontSize="small" />
              </IconButton>
            )}
          </Box>
          
          {videoDescription && (
            <Box>
              <Box sx={{ mt: 1 }}>
                {/* Frame Descriptions */}
                {videoDescription.frame_descriptions && videoDescription.frame_descriptions.length > 0 && (
                  <Box sx={{ mb: 1.5 }}>
                    {videoDescription.frame_descriptions.map((description, index) => {
                      // Parse frame description to extract frame number and content
                      const frameMatch = description.match(/^Frame (\d+):\s*(.+)$/);
                      const frameNumber = frameMatch ? frameMatch[1] : (index + 1).toString();
                      const frameContent = frameMatch ? frameMatch[2] : description;
                      
                      return (
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
                            borderLeft: '2px solid #2196F3'
                          }}
                        >
                          <strong>Frame {frameNumber}:</strong> {frameContent}
                        </Typography>
                      );
                    })}
                  </Box>
                )}
                
                {/* Final Summary */}
                {videoDescription.video_summary && (
                  <Box>
                    <Typography variant="body2" sx={{ 
                      p: 1.5, 
                      fontSize: '0.75rem',
                      backgroundColor: 'rgba(255,255,255,0.15)', 
                      borderRadius: 1,
                      lineHeight: 1.3,
                      borderLeft: '3px solid #4CAF50'
                    }}>
                      <strong>Summary:</strong> {videoDescription.video_summary}
                    </Typography>
                  </Box>
                )}
              </Box>
            </Box>
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
            <Typography 
              variant="subtitle2" 
              sx={{ 
                fontSize: '0.85rem', 
                fontWeight: 600,
                flex: 1,
                cursor: 'pointer'
              }}
              onClick={() => setIsSubtitleExpanded(!isSubtitleExpanded)}
            >
              Subtitles
            </Typography>
            {subtitleData && subtitleData.subtitles_detected && (
              <IconButton
                onClick={() => setIsSubtitleExpanded(!isSubtitleExpanded)}
                sx={{ color: '#ffffff', p: 0.25 }}
                size="small"
              >
                {isSubtitleExpanded ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
              </IconButton>
            )}
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
          
          {/* Subtitle Content */}
          {subtitleData && subtitleData.subtitles_detected && (
            <Collapse in={isSubtitleExpanded}>
              <Box sx={{ mt: 1 }}>
                {/* Frame-by-frame subtitles */}
                {subtitleData.frame_subtitles && subtitleData.frame_subtitles.length > 0 && (
                  <Typography variant="body2" sx={{ 
                    p: 1.5, 
                    fontSize: '0.75rem',
                    lineHeight: 1.4,
                    backgroundColor: 'rgba(255,255,255,0.1)', 
                    borderRadius: 1,
                    borderLeft: '3px solid #2196F3',
                    mb: 1
                  }}>
                    <strong>Frame-by-Frame Subtitles ({getLanguageName(subtitleData.detected_language || 'Unknown')}):</strong><br />
                    {subtitleData.frame_subtitles.map((frameSubtitle, index) => (
                      <span key={index}>
                        {frameSubtitle}
                        {index < subtitleData.frame_subtitles!.length - 1 && <br />}
                      </span>
                    ))}
                  </Typography>
                )}
                
                
                {subtitleLanguage !== (subtitleData.detected_language || 'en') && (
                  <Typography variant="body2" sx={{ 
                    p: 1.5, 
                    mt: 1,
                    fontSize: '0.75rem',
                    lineHeight: 1.4,
                    backgroundColor: 'rgba(255,255,255,0.15)', 
                    borderRadius: 1,
                    borderLeft: '3px solid #4CAF50'
                  }}>
                    <strong>Translated ({getLanguageName(subtitleLanguage)}):</strong><br />
                    {translatedSubtitle || 'Translating...'}
                  </Typography>
                )}
              </Box>
            </Collapse>
          )}
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
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: 1
              }}
              onClick={() => setIsTranscriptExpanded(!isTranscriptExpanded)}
            >
              Audio Transcript
              {isTranslatingAudio && (
                <CircularProgress 
                  size={12} 
                  sx={{ 
                    color: '#ffffff',
                    ml: 0.5
                  }} 
                />
              )}
            </Typography>
            {audioAnalysis && audioAnalysis.speech_detected && (
              <IconButton
                onClick={() => setIsTranscriptExpanded(!isTranscriptExpanded)}
                sx={{ color: '#ffffff', p: 0.25 }}
                size="small"
              >
                {isTranscriptExpanded ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
              </IconButton>
            )}
          </Box>
          
          {/* Language Dropdown for Audio Transcript */}
          <Select
            value={audioTranscriptLanguage}
            onChange={(e) => onAudioTranscriptLanguageChange(e.target.value)}
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
            <MenuItem value="de" sx={{ fontSize: '0.75rem' }}>German</MenuItem>
            <MenuItem value="it" sx={{ fontSize: '0.75rem' }}>Italian</MenuItem>
            <MenuItem value="pt" sx={{ fontSize: '0.75rem' }}>Portuguese</MenuItem>
          </Select>
          
          <Collapse in={isTranscriptExpanded}>
            <Box sx={{ mt: 1 }}>
              <Typography variant="body2" sx={{ 
                p: 1.5, 
                fontSize: '0.75rem',
                lineHeight: 1.4,
                backgroundColor: 'rgba(255,255,255,0.1)', 
                borderRadius: 1,
                borderLeft: '3px solid #FF9800'
              }}>
                <strong>Original ({getLanguageName(audioAnalysis?.detected_language || 'Unknown')}, {Math.round((audioAnalysis?.confidence || 0) * 100)}% confidence):</strong><br />
                {audioTranscript || 'No transcript available'}
              </Typography>
              
              {audioTranscriptLanguage !== (audioAnalysis?.detected_language?.toLowerCase() || 'en') && audioTranscript && (
                <Typography variant="body2" sx={{ 
                  p: 1.5, 
                  mt: 1,
                  fontSize: '0.75rem',
                  lineHeight: 1.4,
                  backgroundColor: 'rgba(255,255,255,0.15)', 
                  borderRadius: 1,
                  borderLeft: '3px solid #4CAF50'
                }}>
                  <strong>Translated ({getLanguageName(audioTranscriptLanguage)}):</strong><br />
                  {translatedTranscript || 'Translating...'}
                </Typography>
              )}
            </Box>
          </Collapse>
        </Box>
      </Paper>
    </Slide>
  );
};
