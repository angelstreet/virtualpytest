import { Box, Typography, IconButton, Slide, Paper, Select, MenuItem, Collapse } from '@mui/material';
import { Close as CloseIcon, ExpandMore as ExpandMoreIcon, ExpandLess as ExpandLessIcon } from '@mui/icons-material';
import React, { useState, useEffect } from 'react';
import { buildServerUrl } from '../../utils/buildUrlUtils';

interface RestartSettingsPanelProps {
  open: boolean;
  onClose: () => void;
  language: string;
  onLanguageChange: (lang: string) => void;
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
  language,
  onLanguageChange,
  videoDescription,
  audioTranscript,
  audioAnalysis,
  subtitleData,
}) => {
  const [isVideoSummaryExpanded, setIsVideoSummaryExpanded] = useState(false);
  const [isTranscriptExpanded, setIsTranscriptExpanded] = useState(false);
  const [isFrameAnalysisExpanded, setIsFrameAnalysisExpanded] = useState(false);
  const [translatedTranscript, setTranslatedTranscript] = useState<string>('');
  const [translatedSummary, setTranslatedSummary] = useState<string>('');

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
  // Old translation logic removed - using unified translation system

  // Effect to handle subtitle translation when language changes
  // Unified translation effect - translates all content when language changes
  useEffect(() => {
    const translateAllContent = async () => {
      if (language === 'en') {
        // Reset to original content for English
        setTranslatedTranscript('');
        setTranslatedSummary('');
        return;
      }

      try {
        // Translate audio transcript (only the content, not the metadata)
        if (audioTranscript && audioAnalysis?.detected_language) {
          const translatedAudio = await translateText(
            audioTranscript,
            language,
            audioAnalysis.detected_language.toLowerCase()
          );
          setTranslatedTranscript(translatedAudio);
        }

        // Translate video summary
        if (videoDescription?.video_summary) {
          const translatedSum = await translateText(
            videoDescription.video_summary,
            language,
            'en' // Assume summary is in English
          );
          setTranslatedSummary(translatedSum);
        }
      } catch (error) {
        console.error('Translation error:', error);
      }
    };

    translateAllContent();
  }, [language, audioTranscript, subtitleData, videoDescription, audioAnalysis]);

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

        {/* Global Language Selector */}
        <Box sx={{ 
          pb: 1.5, 
          mb: 1.5, 
          borderBottom: '1px solid rgba(255,255,255,0.2)' 
        }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Typography 
              variant="subtitle2" 
              sx={{ 
                fontSize: '0.85rem', 
                fontWeight: 600,
                minWidth: 'fit-content'
              }}
            >
              Language:
            </Typography>
            <Select
              value={language}
              onChange={(e) => onLanguageChange(e.target.value)}
              size="small"
              sx={{ 
                minWidth: 120, 
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
          </Box>
        </Box>

        {/* 1. Video Summary Section */}
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
              onClick={() => setIsVideoSummaryExpanded(!isVideoSummaryExpanded)}
            >
              Video Summary
            </Typography>
            {videoDescription && videoDescription.video_summary && (
              <IconButton
                onClick={() => setIsVideoSummaryExpanded(!isVideoSummaryExpanded)}
                sx={{ color: '#ffffff', p: 0.25 }}
                size="small"
              >
                {isVideoSummaryExpanded ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
              </IconButton>
            )}
          </Box>
          
          {videoDescription && videoDescription.video_summary && (
            <Collapse in={isVideoSummaryExpanded}>
              <Box sx={{ mt: 1 }}>
                <Typography variant="body2" sx={{ 
                  p: 1.5, 
                  fontSize: '0.75rem',
                  backgroundColor: 'rgba(255,255,255,0.15)', 
                  borderRadius: 1,
                  lineHeight: 1.3,
                  borderLeft: '3px solid #4CAF50'
                }}>
                  <strong>{language === 'en' ? 'Original Summary:' : `Translated Summary (${getLanguageName(language)}):`}</strong><br />
                  {language === 'en' ? videoDescription.video_summary : (translatedSummary || videoDescription.video_summary || 'Translating...')}
                </Typography>
              </Box>
            </Collapse>
          )}
        </Box>

        {/* 2. Audio Transcript Section */}
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
              onClick={() => setIsTranscriptExpanded(!isTranscriptExpanded)}
            >
              Audio Transcript
            </Typography>
            {(audioTranscript || (audioAnalysis && audioAnalysis.speech_detected)) && (
              <IconButton
                onClick={() => setIsTranscriptExpanded(!isTranscriptExpanded)}
                sx={{ color: '#ffffff', p: 0.25 }}
                size="small"
              >
                {isTranscriptExpanded ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
              </IconButton>
            )}
          </Box>
          
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
                <strong>
                  {language === 'en' ? 'Original' : `Translated to ${getLanguageName(language)}`} 
                  ({getLanguageName(audioAnalysis?.detected_language || 'Unknown')}, {Math.round((audioAnalysis?.confidence || 0) * 100)}% confidence):
                </strong><br />
                {language === 'en' ? (audioTranscript || 'No transcript available') : (translatedTranscript || audioTranscript || 'Translating...')}
              </Typography>
            </Box>
          </Collapse>
        </Box>

        {/* 3. Frame Analysis Section */}
        <Box>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 0.8 }}>
            <Typography 
              variant="subtitle2" 
              sx={{ 
                fontSize: '0.85rem', 
                fontWeight: 600,
                flex: 1,
                cursor: 'pointer'
              }}
              onClick={() => setIsFrameAnalysisExpanded(!isFrameAnalysisExpanded)}
            >
              Frame Analysis
            </Typography>
            {videoDescription && videoDescription.frame_descriptions && videoDescription.frame_descriptions.length > 0 && (
              <IconButton
                onClick={() => setIsFrameAnalysisExpanded(!isFrameAnalysisExpanded)}
                sx={{ color: '#ffffff', p: 0.25 }}
                size="small"
              >
                {isFrameAnalysisExpanded ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
              </IconButton>
            )}
          </Box>
          
          
          {/* Frame Analysis Content */}
          <Collapse in={isFrameAnalysisExpanded}>
            <Box sx={{ mt: 1 }}>
              {/* Frame-by-frame analysis */}
              {videoDescription && videoDescription.frame_descriptions && videoDescription.frame_descriptions.length > 0 && (
                <Box sx={{ mb: 1.5 }}>
                  {videoDescription.frame_descriptions.map((description, index) => {
                    // Parse frame description to extract frame number and content
                    const frameMatch = description.match(/^Frame (\d+):\s*(.+)$/);
                    const frameNumber = frameMatch ? frameMatch[1] : (index + 1).toString();
                    const frameContent = frameMatch ? frameMatch[2] : description;
                    
                    // Get corresponding subtitle for this frame
                    const frameSubtitle = subtitleData?.frame_subtitles?.[index];
                    const subtitleMatch = frameSubtitle?.match(/^Frame \d+:\s*(.+)$/);
                    const subtitleContent = subtitleMatch ? subtitleMatch[1] : frameSubtitle;
                    
                    return (
                      <Box 
                        key={index}
                        sx={{ 
                          mb: 1,
                          p: 1,
                          backgroundColor: 'rgba(255,255,255,0.08)', 
                          borderRadius: 0.5,
                          borderLeft: '2px solid #2196F3'
                        }}
                      >
                        <Typography variant="body2" sx={{ 
                          fontSize: '0.7rem',
                          fontWeight: 600,
                          color: '#2196F3',
                          mb: 0.5
                        }}>
                          Frame {frameNumber}:
                        </Typography>
                        
                        {subtitleContent && subtitleContent !== 'No subtitles detected' && (
                          <Typography variant="body2" sx={{ 
                            fontSize: '0.65rem',
                            color: '#FF9800',
                            fontStyle: 'italic',
                            mb: 0.5,
                            lineHeight: 1.2
                          }}>
                            Subtitles ({getLanguageName(subtitleData?.detected_language || 'Unknown')}): {subtitleContent}
                          </Typography>
                        )}
                        
                        <Typography variant="body2" sx={{ 
                          fontSize: '0.65rem',
                          lineHeight: 1.3,
                          color: 'rgba(255,255,255,0.9)'
                        }}>
                          {frameContent}
                        </Typography>
                      </Box>
                    );
                  })}
                </Box>
              )}
              
            </Box>
          </Collapse>
        </Box>
      </Paper>
    </Slide>
  );
};
