import { Box, Typography, IconButton, Slide, Paper, Select, MenuItem, Collapse, CircularProgress } from '@mui/material';
import { Close as CloseIcon, ExpandMore as ExpandMoreIcon, ExpandLess as ExpandLessIcon } from '@mui/icons-material';
import React, { useState, useEffect } from 'react';
import { buildServerUrl } from '../../utils/buildUrlUtils';
import { useToast } from '../../hooks/useToast';

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
  generateDubbedVersion?: (language: string, transcript: string, videoId: string) => Promise<void>;
  isDubbing?: boolean;
  videoId?: string;
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
  generateDubbedVersion,
  isDubbing,
  videoId,
}) => {
  const toast = useToast();
  const [isVideoSummaryExpanded, setIsVideoSummaryExpanded] = useState(false);
  const [isTranscriptExpanded, setIsTranscriptExpanded] = useState(false);
  const [isFrameAnalysisExpanded, setIsFrameAnalysisExpanded] = useState(false);
  const [translatedTranscript, setTranslatedTranscript] = useState<string>('');
  const [translatedSummary, setTranslatedSummary] = useState<string>('');
  const [translatedFrameDescriptions, setTranslatedFrameDescriptions] = useState<string[]>([]);
  const [translatedFrameSubtitles, setTranslatedFrameSubtitles] = useState<string[]>([]);
  
  // Translation loading state
  const [isTranslating, setIsTranslating] = useState(false);

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

  // Translation cache removed - using single batch translation instead

  // Single batch translation effect - translates all content in one AI request
  useEffect(() => {
    const translateAllContentBatch = async () => {
      if (language === 'en') {
        // Reset to original content for English
        setTranslatedTranscript('');
        setTranslatedSummary('');
        setTranslatedFrameDescriptions([]);
        setTranslatedFrameSubtitles([]);
        return;
      }

      setIsTranslating(true);
      
      try {
        toast.showInfo('🌐 Starting translation...', { duration: 3000 });

        // Prepare all content for single batch translation
        const contentBlocks = {
          video_summary: {
            text: videoDescription?.video_summary || '',
            source_language: 'en'
          },
          audio_transcript: {
            text: audioTranscript || '',
            source_language: audioAnalysis?.detected_language?.toLowerCase() || 'en'
          },
          frame_descriptions: {
            texts: videoDescription?.frame_descriptions?.map(desc => {
              const descText = desc.includes(': ') ? desc.split(': ').slice(1).join(': ') : desc;
              return descText === 'No description available' ? '' : descText;
            }).filter(text => text) || [],
            source_language: 'en'
          },
          frame_subtitles: {
            texts: subtitleData?.frame_subtitles?.map(sub => {
              const subText = sub.includes(': ') ? sub.split(': ').slice(1).join(': ') : sub;
              return subText === 'No subtitles detected' ? '' : subText;
            }).filter(text => text) || [],
            source_language: subtitleData?.detected_language?.toLowerCase() || 'en'
          }
        };

        // Single API call for all translations
        const response = await fetch(buildServerUrl('/server/translate/restart-batch'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            content_blocks: contentBlocks,
            target_language: language
          })
        });

        if (!response.ok) {
          throw new Error(`Batch translation API failed: ${response.status} ${response.statusText}`);
        }

        const data = await response.json();
        
        if (data.success && data.translations) {
          // Apply all translations at once
          if (data.translations.video_summary) {
            setTranslatedSummary(data.translations.video_summary);
          }
          
          if (data.translations.audio_transcript) {
            setTranslatedTranscript(data.translations.audio_transcript);
          }
          
          if (data.translations.frame_descriptions?.length > 0) {
            // Reconstruct with frame prefixes
            const translatedDescs = videoDescription?.frame_descriptions?.map((originalDesc, index) => {
              const prefix = originalDesc.split(': ')[0];
              const translatedText = data.translations.frame_descriptions[index] || 'No description available';
              return `${prefix}: ${translatedText}`;
            }) || [];
            setTranslatedFrameDescriptions(translatedDescs);
          }
          
          if (data.translations.frame_subtitles?.length > 0) {
            // Reconstruct with frame prefixes
            const translatedSubs = subtitleData?.frame_subtitles?.map((originalSub, index) => {
              const prefix = originalSub.split(': ')[0];
              const translatedText = data.translations.frame_subtitles[index] || 'No subtitles detected';
              return `${prefix}: ${translatedText}`;
            }) || [];
            setTranslatedFrameSubtitles(translatedSubs);
          }
          
          toast.showSuccess('✅ All translations complete!', { duration: 4000 });
          
          // Start dubbing after translation completes
          if (generateDubbedVersion && audioTranscript && videoId) {
            toast.showInfo('🎤 Starting dubbing...', { duration: 3000 });
            await generateDubbedVersion(language, audioTranscript, videoId);
            toast.showSuccess('🎬 Dubbing complete!', { duration: 4000 });
          }
          
        } else {
          throw new Error(data.error || 'Batch translation failed');
        }
        
      } catch (error) {
        console.error('Batch translation error:', error);
        const errorMessage = error instanceof Error ? error.message : 'Unknown error';
        toast.showError(`❌ Translation failed: ${errorMessage}`, { duration: 5000 });
      } finally {
        setIsTranslating(false);
      }
    };
    
    translateAllContentBatch();
  }, [language, videoDescription, audioTranscript, subtitleData, audioAnalysis, toast]);

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
              disabled={isTranslating}
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
            {isTranslating && (
              <CircularProgress 
                size={16} 
                sx={{ 
                  color: '#ffffff',
                  ml: 1
                }} 
              />
            )}
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
                  {language === 'en' 
                    ? `Original (${getLanguageName(audioAnalysis?.detected_language || 'Unknown')})` 
                    : `Translated to ${getLanguageName(language)}`}:
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
                    // Use translated content if available, otherwise use original
                    const displayDescription = translatedFrameDescriptions[index] || description;
                    const displaySubtitle = translatedFrameSubtitles[index] || subtitleData?.frame_subtitles?.[index];
                    
                    // Parse frame description to extract frame number and content
                    const frameMatch = displayDescription.match(/^Frame (\d+):\s*(.+)$/);
                    const frameNumber = frameMatch ? frameMatch[1] : (index + 1).toString();
                    const frameContent = frameMatch ? frameMatch[2] : displayDescription;
                    
                    // Get corresponding subtitle for this frame
                    const subtitleMatch = displaySubtitle?.match(/^Frame \d+:\s*(.+)$/);
                    const subtitleContent = subtitleMatch ? subtitleMatch[1] : displaySubtitle;
                    
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
                            Subtitles ({
                              language !== 'en' && translatedFrameSubtitles.length > 0 
                                ? `Translated to ${getLanguageName(language)}`
                                : (subtitleData?.detected_language || 'Unknown').toUpperCase()
                            }): {subtitleContent}
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
