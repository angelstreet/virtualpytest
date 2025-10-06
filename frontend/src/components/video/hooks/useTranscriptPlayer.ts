import { useState, useCallback, useEffect, useMemo } from 'react';
import { TranscriptData, TranscriptSegment, ArchiveMetadata } from '../EnhancedHLSPlayer.types';
import { Host } from '../../../types/common/Host_Types';
import { buildStreamUrl } from '../../../utils/buildUrlUtils';

interface UseTranscriptPlayerProps {
  isLiveMode: boolean;
  archiveMetadata: ArchiveMetadata | null;
  currentManifestIndex: number;
  globalCurrentTime: number;
  providedStreamUrl?: string;
  hookStreamUrl?: string;
  host?: Host;
  deviceId: string;
  hostName: string;
}

export const useTranscriptPlayer = ({
  isLiveMode,
  archiveMetadata,
  currentManifestIndex,
  globalCurrentTime,
  providedStreamUrl,
  hookStreamUrl,
  host,
  deviceId,
  hostName,
}: UseTranscriptPlayerProps) => {
  const [transcriptData, setTranscriptData] = useState<TranscriptData | null>(null);
  const [currentTranscript, setCurrentTranscript] = useState<TranscriptSegment | null>(null);
  const [selectedLanguage, setSelectedLanguage] = useState<string>('original');
  const [isTranslating, setIsTranslating] = useState(false);

  useEffect(() => {
    if (!isLiveMode && archiveMetadata && archiveMetadata.manifests.length > 0) {
      const currentManifest = archiveMetadata.manifests[currentManifestIndex];
      if (currentManifest) {
        const hour = currentManifest.window_index;
        const chunkIndex = currentManifest.chunk_index;
        const baseUrl = providedStreamUrl || hookStreamUrl || buildStreamUrl(host, deviceId);
        
        const transcriptUrl = baseUrl.replace(/\/(segments\/)?(output|archive.*?)\.m3u8$/, `/transcript/${hour}/chunk_10min_${chunkIndex}.json`);
        
        console.log(`[@EnhancedHLSPlayer] Loading transcript chunk (hour ${hour}, chunk ${chunkIndex}):`, transcriptUrl);
        
        fetch(transcriptUrl)
          .then(res => res.json())
          .then(transcript => {
            if (transcript && transcript.segments) {
              console.log(`[@EnhancedHLSPlayer] Transcript chunk loaded: ${transcript.segments.length} samples`);
              setTranscriptData(transcript);
            } else {
              console.log(`[@EnhancedHLSPlayer] No transcript data for chunk ${chunkIndex}`);
              setTranscriptData(null);
            }
          })
          .catch(() => {
            console.log(`[@EnhancedHLSPlayer] No transcript available for hour ${hour}, chunk ${chunkIndex}`);
            setTranscriptData(null);
          });
      }
    }
  }, [isLiveMode, archiveMetadata, currentManifestIndex, providedStreamUrl, hookStreamUrl, deviceId, host]);

  useEffect(() => {
    if (transcriptData && transcriptData.segments.length > 0) {
      const closestSegment = transcriptData.segments.reduce((closest, segment) => {
        const timeDiff = Math.abs(segment.relative_seconds - globalCurrentTime);
        const closestDiff = closest ? Math.abs(closest.relative_seconds - globalCurrentTime) : Infinity;
        return timeDiff < closestDiff ? segment : closest;
      }, transcriptData.segments[0]);
      
      if (Math.abs(closestSegment.relative_seconds - globalCurrentTime) < 6) {
        setCurrentTranscript(closestSegment);
      } else {
        setCurrentTranscript(null);
      }
    } else {
      setCurrentTranscript(null);
    }
  }, [transcriptData, globalCurrentTime]);

  const handleLanguageChange = useCallback(async (language: string) => {
    setSelectedLanguage(language);
    
    if (language === 'original') {
      console.log('[@EnhancedHLSPlayer] Switched to original language');
      return;
    }

    const hasTranslations = transcriptData?.segments.some(
      seg => seg.translations && seg.translations[language]
    );
    
    if (hasTranslations) {
      console.log(`[@EnhancedHLSPlayer] Using cached translations for ${language}`);
      return;
    }

    setIsTranslating(true);
    console.log(`[@EnhancedHLSPlayer] Translating transcripts to ${language}...`);
    
    try {
      const baseUrl = providedStreamUrl || hookStreamUrl || buildStreamUrl(host, deviceId);
      const captureMatch = baseUrl.match(/\/stream\/(\w+)\//);
      const captureFolder = captureMatch ? captureMatch[1] : transcriptData?.capture_folder;
      
      const currentManifest = archiveMetadata?.manifests[currentManifestIndex];
      const hourWindow = currentManifest?.window_index || 1;
      
      const response = await fetch(`/host/${captureFolder}/translate-transcripts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          target_language: language,
          hour_window: hourWindow
        })
      });

      const data = await response.json();
      
      if (data.success) {
        console.log(`[@EnhancedHLSPlayer] Translation complete: ${data.translated_count} segments translated`);
        
        const transcriptUrl = baseUrl.replace(/\/(output|archive.*?)\.m3u8$/, `/transcript_hour${hourWindow}.json`);
        const updatedData = await fetch(transcriptUrl).then(res => res.json());
        setTranscriptData(updatedData);
      }
    } catch (error) {
      console.error('[@EnhancedHLSPlayer] Translation failed:', error);
    } finally {
      setIsTranslating(false);
    }
  }, [transcriptData, archiveMetadata, currentManifestIndex, providedStreamUrl, hookStreamUrl, deviceId, hostName, host]);

  const getCurrentTranscriptText = useCallback(() => {
    if (!currentTranscript) return '';
    
    if (selectedLanguage === 'original') {
      return currentTranscript.enhanced_transcript || currentTranscript.transcript;
    }
    
    const translation = currentTranscript.translations?.[selectedLanguage];
    return translation || currentTranscript.enhanced_transcript || currentTranscript.transcript;
  }, [currentTranscript, selectedLanguage]);

  const clearTranscriptData = useCallback(() => {
    setTranscriptData(null);
    setCurrentTranscript(null);
  }, []);

  return useMemo(() => ({
    transcriptData,
    currentTranscript,
    selectedLanguage,
    isTranslating,
    handleLanguageChange,
    getCurrentTranscriptText,
    clearTranscriptData,
  }), [
    transcriptData,
    currentTranscript,
    selectedLanguage,
    isTranslating,
    handleLanguageChange,
    getCurrentTranscriptText,
    clearTranscriptData,
  ]);
};
