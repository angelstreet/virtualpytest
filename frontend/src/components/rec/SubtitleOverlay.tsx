import { Box, Typography } from '@mui/material';
import React, { useState, useEffect } from 'react';
import { buildServerUrl } from '../../utils/buildUrlUtils';
import { SubtitleStyle } from './SubtitleSettings';

interface SubtitleSegment {
  startTime: number; // seconds
  endTime: number;   // seconds
  text: string;
  translatedText?: string;
}

interface SubtitleOverlayProps {
  transcript?: string;
  detectedLanguage?: string;
  speechDetected?: boolean;
  videoRef?: React.RefObject<HTMLVideoElement>;
  videoDuration?: number; // Total video duration in seconds
  subtitleSettings: SubtitleStyle;
}

export const SubtitleOverlay: React.FC<SubtitleOverlayProps> = ({
  transcript,
  detectedLanguage,
  speechDetected,
  videoRef,
  videoDuration = 30,
  subtitleSettings
}) => {
  const [currentSubtitle, setCurrentSubtitle] = useState<string>('');
  const [currentTranslatedSubtitle, setCurrentTranslatedSubtitle] = useState<string>('');
  const [subtitleSegments, setSubtitleSegments] = useState<SubtitleSegment[]>([]);
  const [isTranslating, setIsTranslating] = useState(false);

  // Parse transcript into time-synchronized segments
  useEffect(() => {
    if (!transcript || !speechDetected) {
      setSubtitleSegments([]);
      return;
    }

    // Split transcript into segments (roughly 3-5 words per segment for readability)
    const words = transcript.split(' ');
    const segments: SubtitleSegment[] = [];
    const wordsPerSegment = 4;
    const segmentDuration = videoDuration / Math.ceil(words.length / wordsPerSegment);

    for (let i = 0; i < words.length; i += wordsPerSegment) {
      const segmentWords = words.slice(i, i + wordsPerSegment);
      const startTime = (i / wordsPerSegment) * segmentDuration;
      const endTime = Math.min(startTime + segmentDuration, videoDuration);
      
      segments.push({
        startTime,
        endTime,
        text: segmentWords.join(' ')
      });
    }

    setSubtitleSegments(segments);
  }, [transcript, speechDetected, videoDuration]);

  // Translate segments when settings change
  useEffect(() => {
    if (!subtitleSettings.showTranslation || !detectedLanguage || !subtitleSegments.length) {
      return;
    }

    if (detectedLanguage === subtitleSettings.targetLanguage) {
      // Same language, no translation needed
      return;
    }

    const translateSegments = async () => {
      setIsTranslating(true);
      try {
        const segmentTexts = subtitleSegments.map(s => s.text);
        
        const response = await fetch(buildServerUrl('/server/translate/batch'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            segments: segmentTexts,
            source_language: detectedLanguage,
            target_language: subtitleSettings.targetLanguage
          })
        });

        if (response.ok) {
          const result = await response.json();
          if (result.success) {
            const updatedSegments = subtitleSegments.map((segment, index) => ({
              ...segment,
              translatedText: result.translated_segments[index] || segment.text
            }));
            setSubtitleSegments(updatedSegments);
          }
        }
      } catch (error) {
        console.error('Translation failed:', error);
      } finally {
        setIsTranslating(false);
      }
    };

    translateSegments();
  }, [subtitleSettings.showTranslation, subtitleSettings.targetLanguage, detectedLanguage, subtitleSegments.length]);

  // Sync with video timeline
  useEffect(() => {
    if (!videoRef?.current || subtitleSegments.length === 0) return;

    const video = videoRef.current;
    
    const updateSubtitle = () => {
      const currentTime = video.currentTime;
      const activeSegment = subtitleSegments.find(
        segment => currentTime >= segment.startTime && currentTime <= segment.endTime
      );
      
      setCurrentSubtitle(activeSegment?.text || '');
      setCurrentTranslatedSubtitle(activeSegment?.translatedText || '');
    };

    // Update on time change
    video.addEventListener('timeupdate', updateSubtitle);
    
    return () => {
      video.removeEventListener('timeupdate', updateSubtitle);
    };
  }, [videoRef, subtitleSegments]);

  if (!speechDetected || !transcript) return null;

  // Get style settings
  const getFontSize = () => {
    switch (subtitleSettings.fontSize) {
      case 'small': return '0.8rem';
      case 'large': return '1.2rem';
      default: return '1rem';
    }
  };

  const getFontFamily = () => {
    switch (subtitleSettings.fontFamily) {
      case 'serif': return 'Georgia, serif';
      case 'monospace': return 'Courier New, monospace';
      default: return 'Roboto, Arial, sans-serif';
    }
  };

  const getTextStyle = () => {
    const baseStyle = {
      fontSize: getFontSize(),
      fontFamily: getFontFamily(),
      opacity: subtitleSettings.opacity,
      lineHeight: 1.3,
      fontWeight: 500,
    };

    switch (subtitleSettings.textStyle) {
      case 'yellow':
        return { ...baseStyle, color: '#ffff00', textShadow: '2px 2px 4px rgba(0,0,0,0.9)' };
      case 'white-border':
        return { 
          ...baseStyle, 
          color: '#ffffff', 
          textShadow: '0 0 2px #000000, 0 0 2px #000000, 0 0 2px #000000, 0 0 2px #000000' 
        };
      case 'black-background':
        return { 
          ...baseStyle, 
          color: '#ffffff', 
          backgroundColor: 'rgba(0,0,0,0.9)', 
          padding: '2px 6px', 
          borderRadius: '2px',
          display: 'inline-block'
        };
      default: // white
        return { ...baseStyle, color: '#ffffff', textShadow: '2px 2px 4px rgba(0,0,0,0.9)' };
    }
  };

  const showOriginal = subtitleSettings.showOriginal && currentSubtitle;
  const showTranslation = subtitleSettings.showTranslation && currentTranslatedSubtitle && 
                          detectedLanguage !== subtitleSettings.targetLanguage;

  if (!showOriginal && !showTranslation) return null;

  return (
    <Box
      sx={{
        position: 'absolute',
        bottom: 80, // Above video controls
        left: '50%',
        transform: 'translateX(-50%)',
        zIndex: 1000020,
        maxWidth: '80%',
        textAlign: 'center',
        pointerEvents: 'none',
      }}
    >
      {/* Language indicators */}
      {(showOriginal || showTranslation) && detectedLanguage && detectedLanguage !== 'unknown' && (
        <Box sx={{ mb: 1, display: 'flex', justifyContent: 'center', gap: 1 }}>
          {showOriginal && (
            <Box
              sx={{
                px: 1,
                py: 0.5,
                backgroundColor: 'rgba(0, 0, 0, 0.6)',
                borderRadius: 1,
                display: 'inline-block',
              }}
            >
              <Typography
                variant="caption"
                sx={{
                  color: '#ffffff',
                  fontSize: '0.7rem',
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px',
                }}
              >
                {detectedLanguage}
              </Typography>
            </Box>
          )}
          {showTranslation && (
            <Box
              sx={{
                px: 1,
                py: 0.5,
                backgroundColor: 'rgba(0, 100, 200, 0.6)',
                borderRadius: 1,
                display: 'inline-block',
              }}
            >
              <Typography
                variant="caption"
                sx={{
                  color: '#ffffff',
                  fontSize: '0.7rem',
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px',
                }}
              >
                {subtitleSettings.targetLanguage}
              </Typography>
            </Box>
          )}
        </Box>
      )}

      {/* Original subtitle */}
      {showOriginal && (
        <Box
          sx={{
            px: 2,
            py: 1,
            backgroundColor: subtitleSettings.textStyle === 'black-background' ? 'transparent' : 'rgba(0, 0, 0, 0.8)',
            borderRadius: 1,
            border: subtitleSettings.textStyle === 'black-background' ? 'none' : '1px solid rgba(255, 255, 255, 0.1)',
            mb: showTranslation ? 1 : 0,
          }}
        >
          <Typography style={getTextStyle()}>
            {currentSubtitle}
          </Typography>
        </Box>
      )}

      {/* Translated subtitle */}
      {showTranslation && (
        <Box
          sx={{
            px: 2,
            py: 1,
            backgroundColor: subtitleSettings.textStyle === 'black-background' ? 'transparent' : 'rgba(0, 0, 0, 0.8)',
            borderRadius: 1,
            border: subtitleSettings.textStyle === 'black-background' ? 'none' : '1px solid rgba(255, 255, 255, 0.1)',
          }}
        >
          <Typography 
            style={{
              ...getTextStyle(),
              fontSize: `calc(${getFontSize()} * 0.9)`, // Slightly smaller for translation
              opacity: subtitleSettings.opacity * 0.9, // Slightly more transparent
            }}
          >
            {isTranslating ? '...' : currentTranslatedSubtitle}
          </Typography>
        </Box>
      )}
    </Box>
  );
};
