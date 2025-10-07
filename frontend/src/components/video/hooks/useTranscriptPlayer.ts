import { useState, useCallback, useEffect, useMemo } from 'react';
import { TranscriptData, TranscriptDataLegacy, TranscriptData10Min, TranscriptSegment, ArchiveMetadata, TimedSegment } from '../EnhancedHLSPlayer.types';
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

// Type guard to check if transcript is new 10-minute format
const isTranscriptData10Min = (data: TranscriptData): data is TranscriptData10Min => {
  return 'chunk_duration_minutes' in data && 'mp3_file' in data;
};

// Helper to normalize transcript data to legacy format for backward compatibility
const normalizeTranscriptData = (data: TranscriptData): TranscriptDataLegacy => {
  if (isTranscriptData10Min(data)) {
    // Convert new 10-min format to legacy segments format
    // Create a single segment representing the entire 10-minute chunk
    const chunkStartSeconds = (data.hour * 3600) + (data.chunk_index * 600);
    
    const segment: TranscriptSegment = {
      segment_num: data.chunk_index,
      relative_seconds: chunkStartSeconds,
      language: data.language,
      transcript: data.transcript,
      confidence: data.confidence,
      manifest_window: data.hour,
      translations: data.translations,
    };
    
    return {
      capture_folder: data.capture_folder,
      sample_interval_seconds: 600, // 10 minutes
      total_duration_seconds: 600,
      segments: [segment],
      last_update: data.timestamp,
      total_samples: 1,
    };
  }
  
  // Already in legacy format
  return data as TranscriptDataLegacy;
};

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
  const [rawTranscriptData, setRawTranscriptData] = useState<TranscriptData10Min | null>(null);  // Keep raw 10-min data
  const [currentTranscript, setCurrentTranscript] = useState<TranscriptSegment | null>(null);
  const [currentTimedSegment, setCurrentTimedSegment] = useState<TimedSegment | null>(null);  // Track current timed segment
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
        
        // Check transcript manifest first to avoid 404s
        const manifestUrl = baseUrl.replace(/\/(segments\/)?(output|archive.*?)\.m3u8$/, `/transcript/transcript_manifest.json`);
        
        console.log(`[@useTranscriptPlayer] Checking transcript availability from manifest...`);
        
        fetch(manifestUrl)
          .then(res => {
            if (!res.ok) {
              console.log(`[@useTranscriptPlayer] No transcript manifest available`);
              setTranscriptData(null);
              return null;
            }
            return res.json();
          })
          .then((manifest) => {
            if (!manifest || !manifest.chunks) {
              setTranscriptData(null);
              return;
            }
            
            // Check if transcript exists for this hour/chunk
            const transcriptExists = manifest.chunks.some(
              (chunk: any) => chunk.hour === hour && chunk.chunk_index === chunkIndex && chunk.has_transcript
            );
            
            if (!transcriptExists) {
              console.log(`[@useTranscriptPlayer] No transcript available for hour ${hour}, chunk ${chunkIndex} (checked manifest)`);
              setTranscriptData(null);
              return;
            }
            
            console.log(`[@useTranscriptPlayer] Loading transcript chunk (hour ${hour}, chunk ${chunkIndex}):`, transcriptUrl);
            
            // Transcript exists in manifest, fetch it
            return fetch(transcriptUrl)
              .then(res => res.json())
              .then((transcript: TranscriptData) => {
                if (!transcript) {
                  console.log(`[@useTranscriptPlayer] No transcript data for chunk ${chunkIndex}`);
                  setTranscriptData(null);
                  setRawTranscriptData(null);
                  return;
                }
                
                // Detect format and normalize
                const is10Min = isTranscriptData10Min(transcript);
                console.log(`[@useTranscriptPlayer] Transcript format: ${is10Min ? '10-minute (NEW)' : '6-second segments (LEGACY)'}`);
                
                // Store raw 10-min data for timed segment access
                if (is10Min) {
                  setRawTranscriptData(transcript as TranscriptData10Min);
                  console.log(`[@useTranscriptPlayer] 10-min transcript with ${(transcript as TranscriptData10Min).segments?.length || 0} timed segments`);
                } else {
                  setRawTranscriptData(null);
                }
                
                const normalizedData = normalizeTranscriptData(transcript);
                
                if (is10Min) {
                  console.log(`[@useTranscriptPlayer] 10-min transcript loaded:`, {
                    language: (transcript as TranscriptData10Min).language,
                    confidence: (transcript as TranscriptData10Min).confidence,
                    textLength: (transcript as TranscriptData10Min).transcript.length,
                    preview: (transcript as TranscriptData10Min).transcript.substring(0, 100)
                  });
                } else {
                  console.log(`[@useTranscriptPlayer] Transcript chunk loaded: ${normalizedData.segments.length} segments`);
                }
                
                setTranscriptData(normalizedData);
              });
          })
          .catch((error) => {
            console.log(`[@useTranscriptPlayer] Error loading transcript:`, error.message);
            setTranscriptData(null);
            setRawTranscriptData(null);
          });
      }
    }
  }, [isLiveMode, archiveMetadata, currentManifestIndex, providedStreamUrl, hookStreamUrl, deviceId, host]);

  useEffect(() => {
    if (transcriptData && transcriptData.segments.length > 0) {
      // For 10-minute chunks (1 segment), show transcript for entire chunk duration
      // For legacy 6-second segments, find closest segment
      const isLongChunk = transcriptData.sample_interval_seconds >= 600; // 10 minutes
      
      if (isLongChunk && transcriptData.segments.length === 1) {
        // NEW format: Show transcript for entire 10-minute chunk
        // Since we're playing a single 10-min chunk, transcript is always visible during playback
        const segment = transcriptData.segments[0];
        const chunkStartTime = segment.relative_seconds;
        const chunkEndTime = chunkStartTime + 600; // 10 minutes
        
        // Check if current time is within this chunk
        if (globalCurrentTime >= chunkStartTime && globalCurrentTime < chunkEndTime) {
          setCurrentTranscript(segment);
        } else {
          console.log(`[@useTranscriptPlayer] Time mismatch: globalCurrentTime=${globalCurrentTime.toFixed(1)}s, chunk range=${chunkStartTime}-${chunkEndTime}`);
          setCurrentTranscript(null);
        }
      } else {
        // LEGACY format: Find closest 6-second segment
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
      }
    } else {
      setCurrentTranscript(null);
    }
  }, [transcriptData, globalCurrentTime]);
  
  // NEW: Find current timed segment based on video playback time (for subtitle-style display)
  useEffect(() => {
    if (!rawTranscriptData || !rawTranscriptData.segments || rawTranscriptData.segments.length === 0) {
      setCurrentTimedSegment(null);
      return;
    }
    
    // Calculate local time within the chunk (video.currentTime)
    if (!archiveMetadata || archiveMetadata.manifests.length === 0) {
      setCurrentTimedSegment(null);
      return;
    }
    
    const currentManifest = archiveMetadata.manifests[currentManifestIndex];
    if (!currentManifest) {
      setCurrentTimedSegment(null);
      return;
    }
    
    // Local time within the 10-minute chunk (0-600 seconds)
    const localTime = globalCurrentTime - currentManifest.start_time_seconds;
    
    // Find the timed segment that contains this local time
    const activeSegment = rawTranscriptData.segments.find(
      seg => localTime >= seg.start && localTime < seg.end
    );
    
    if (activeSegment) {
      setCurrentTimedSegment(activeSegment);
      console.log(`[@useTranscriptPlayer] Current timed segment: ${localTime.toFixed(1)}s -> "${activeSegment.text.substring(0, 50)}..."`);
    } else {
      setCurrentTimedSegment(null);
    }
  }, [rawTranscriptData, globalCurrentTime, archiveMetadata, currentManifestIndex]);

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
    // Prioritize timed segment for subtitle-style display (NEW format)
    if (currentTimedSegment) {
      return currentTimedSegment.text;
    }
    
    // Fallback to full transcript segment (OLD format or no timed segments)
    if (!currentTranscript) return '';
    
    if (selectedLanguage === 'original') {
      return currentTranscript.enhanced_transcript || currentTranscript.transcript;
    }
    
    const translation = currentTranscript.translations?.[selectedLanguage];
    return translation || currentTranscript.enhanced_transcript || currentTranscript.transcript;
  }, [currentTranscript, currentTimedSegment, selectedLanguage]);

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
