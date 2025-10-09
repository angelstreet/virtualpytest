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
}: UseTranscriptPlayerProps) => {
  const [transcriptData, setTranscriptData] = useState<TranscriptDataLegacy | null>(null);
  const [rawTranscriptData, setRawTranscriptData] = useState<TranscriptData10Min | null>(null);  // Keep raw 10-min data
  const [currentTranscript, setCurrentTranscript] = useState<TranscriptSegment | null>(null);
  const [currentTimedSegment, setCurrentTimedSegment] = useState<TimedSegment | null>(null);  // Track current timed segment
  const [selectedLanguage, setSelectedLanguage] = useState<string>('original');
  const [isTranslating, setIsTranslating] = useState(false);
  const [hasMp3, setHasMp3] = useState(false);
  const [mp3Url, setMp3Url] = useState<string | null>(null);

  useEffect(() => {
    if (!isLiveMode && archiveMetadata && archiveMetadata.manifests.length > 0) {
      const currentManifest = archiveMetadata.manifests[currentManifestIndex];
      if (currentManifest) {
        const hour = currentManifest.window_index;
        const chunkIndex = currentManifest.chunk_index;
        const baseUrl = providedStreamUrl || hookStreamUrl || buildStreamUrl(host, deviceId);
        
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
            const chunkInfo = manifest.chunks.find(
              (chunk: any) => chunk.hour === hour && chunk.chunk_index === chunkIndex
            );
            
            if (!chunkInfo || !chunkInfo.has_transcript) {
              console.log(`[@useTranscriptPlayer] No transcript available for hour ${hour}, chunk ${chunkIndex} (checked manifest)`);
              setTranscriptData(null);
              setHasMp3(false);
              setMp3Url(null);
              return;
            }
            
            // Extract has_mp3 and build mp3Url if available
            const hasMp3Flag = chunkInfo.has_mp3 === true;
            setHasMp3(hasMp3Flag);
            if (hasMp3Flag) {
              const mp3Path = baseUrl.replace(/\/(segments\/)?(output|archive.*?)\.m3u8$/, `/audio/${hour}/chunk_10min_${chunkIndex}.mp3`);
              setMp3Url(mp3Path);
            } else {
              setMp3Url(null);
            }
            
            // OPTIMIZATION: Transcript data is now included directly in manifest (1 API call instead of 2)
            console.log(`[@useTranscriptPlayer] ⚡ Reading transcript directly from manifest (hour ${hour}, chunk ${chunkIndex})`);
            
            // Build transcript object from manifest data
            const transcript: TranscriptData10Min = {
              capture_folder: chunkInfo.capture_folder || deviceId,
              hour: hour,
              chunk_index: chunkIndex,
              chunk_duration_minutes: 10,
              language: chunkInfo.language || 'unknown',
              transcript: chunkInfo.transcript || '',
              confidence: chunkInfo.confidence || 0.0,
              transcription_time_seconds: chunkInfo.transcription_time_seconds || 0,
              timestamp: chunkInfo.timestamp || new Date().toISOString(),
              mp3_file: chunkInfo.mp3_file || `chunk_10min_${chunkIndex}.mp3`,
              segments: chunkInfo.segments || [],
              minute_metadata: chunkInfo.minute_metadata || []
            };
            
            if (!transcript.transcript) {
              console.log(`[@useTranscriptPlayer] No transcript text in manifest for chunk ${chunkIndex}`);
              setTranscriptData(null);
              setRawTranscriptData(null);
              return;
            }
            
            // Store raw 10-min data for timed segment access
            setRawTranscriptData(transcript);
            console.log(`[@useTranscriptPlayer] 10-min transcript with ${transcript.segments?.length || 0} timed segments`);
            
            const normalizedData = normalizeTranscriptData(transcript);
            
            console.log(`[@useTranscriptPlayer] 10-min transcript loaded from manifest:`, {
              language: transcript.language,
              confidence: transcript.confidence,
              textLength: transcript.transcript.length,
              segmentCount: transcript.segments?.length || 0,
              preview: transcript.transcript.substring(0, 100)
            });
            
            setTranscriptData(normalizedData);
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
    if (transcriptData && transcriptData.segments && transcriptData.segments.length > 0) {
      // For 10-minute chunks (1 segment), show transcript for entire chunk duration
      // For legacy 6-second segments, find closest segment
      const isLongChunk = (transcriptData.sample_interval_seconds ?? 0) >= 600; // 10 minutes
      
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
  
  // Find current timed segment based on video playback time (per-minute granularity)
  useEffect(() => {
    if (!rawTranscriptData || !rawTranscriptData.segments || rawTranscriptData.segments.length === 0) {
      setCurrentTimedSegment(null);
      return;
    }
    
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
    
    // Find current minute (0-9)
    const currentMinute = Math.floor(localTime / 60);
    
    // Filter segments for current minute only (60s window)
    const minuteStart = currentMinute * 60;
    const minuteEnd = minuteStart + 60;
    
    // Find active segment within current minute
    const activeSegment = rawTranscriptData.segments.find(
      seg => seg.start >= minuteStart && seg.start < minuteEnd && localTime >= seg.start && localTime < seg.end
    );
    
    if (activeSegment) {
      setCurrentTimedSegment(activeSegment);
      console.log(`[@useTranscriptPlayer] Minute ${currentMinute} | ${localTime.toFixed(1)}s -> "${activeSegment.text.substring(0, 50)}..."`);
    } else {
      setCurrentTimedSegment(null);
    }
  }, [rawTranscriptData, globalCurrentTime, archiveMetadata, currentManifestIndex]);

  const handleLanguageChange = useCallback(async (language: string) => {
    setSelectedLanguage(language);
    
    if (language === 'original') {
      console.log('[@useTranscriptPlayer] Switched to original language');
      return;
    }

    // Check if translations already cached
    const hasTranslations = rawTranscriptData?.segments?.some(
      seg => seg.translations && seg.translations[language]
    );
    
    if (hasTranslations) {
      console.log(`[@useTranscriptPlayer] Using cached translations for ${language}`);
      return;
    }

    // Need to translate - use what's already loaded
    if (!rawTranscriptData?.segments) {
      console.log('[@useTranscriptPlayer] No segments to translate');
      return;
    }

    setIsTranslating(true);
    console.log(`[@useTranscriptPlayer] Translating ${rawTranscriptData.segments.length} segments to ${language}...`);
    
    try {
      const baseUrl = providedStreamUrl || hookStreamUrl || buildStreamUrl(host, deviceId);
      const captureMatch = baseUrl.match(/\/stream\/(\w+)\//);
      const captureFolder = captureMatch ? captureMatch[1] : 'capture1';
      
      // Extract texts from loaded segments (what's already displayed)
      const segmentTexts = rawTranscriptData.segments.map(seg => seg.text);
      
      // Call backend to translate and cache
      const response = await fetch(`/host/${captureFolder}/translate-segments`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          hour: rawTranscriptData.hour,
          chunk_index: rawTranscriptData.chunk_index,
          segments: segmentTexts,
          target_language: language,
          source_language: rawTranscriptData.language
        })
      });

      const data = await response.json();
      
      if (data.success) {
        console.log(`[@useTranscriptPlayer] ✅ Translation complete and cached`);
        
        // Reload transcript from manifest to get updated data with cached translations
        const manifestUrl = baseUrl.replace(/\/(segments\/)?(output|archive.*?)\.m3u8$/, `/transcript/transcript_manifest.json`);
        const manifest = await fetch(manifestUrl).then(res => res.json());
        
        if (manifest && manifest.chunks) {
          const chunkInfo = manifest.chunks.find(
            (chunk: any) => chunk.hour === rawTranscriptData.hour && chunk.chunk_index === rawTranscriptData.chunk_index
          );
          
          if (chunkInfo && chunkInfo.transcript) {
            const updatedTranscript: TranscriptData10Min = {
              capture_folder: chunkInfo.capture_folder || deviceId,
              hour: rawTranscriptData.hour,
              chunk_index: rawTranscriptData.chunk_index,
              chunk_duration_minutes: 10,
              language: chunkInfo.language || 'unknown',
              transcript: chunkInfo.transcript || '',
              confidence: chunkInfo.confidence || 0.0,
              transcription_time_seconds: chunkInfo.transcription_time_seconds || 0,
              timestamp: chunkInfo.timestamp || new Date().toISOString(),
              mp3_file: chunkInfo.mp3_file || '',
              segments: chunkInfo.segments || []
            };
            
            setRawTranscriptData(updatedTranscript);
            setTranscriptData(normalizeTranscriptData(updatedTranscript));
          }
        }
      }
    } catch (error) {
      console.error('[@useTranscriptPlayer] Translation failed:', error);
    } finally {
      setIsTranslating(false);
    }
  }, [rawTranscriptData, archiveMetadata, currentManifestIndex, providedStreamUrl, hookStreamUrl, deviceId, host]);

  const getCurrentTranscriptText = useCallback(() => {
    // For new 10-min format with timed segments, ONLY use timed segments (no fallback)
    if (rawTranscriptData?.segments && rawTranscriptData.segments.length > 0) {
      if (!currentTimedSegment) return '';  // Show nothing between segments - no fallback to full transcript
      
      // Check for translation in timed segment
      if (selectedLanguage !== 'original' && currentTimedSegment.translations?.[selectedLanguage]) {
        return currentTimedSegment.translations[selectedLanguage];
      }
      return currentTimedSegment.text;
    }
    
    // Legacy format (6-second segments) - use currentTranscript
    if (!currentTranscript) return '';
    
    if (selectedLanguage === 'original') {
      return currentTranscript.enhanced_transcript || currentTranscript.transcript;
    }
    
    const translation = currentTranscript.translations?.[selectedLanguage];
    return translation || currentTranscript.enhanced_transcript || currentTranscript.transcript;
  }, [rawTranscriptData, currentTranscript, currentTimedSegment, selectedLanguage]);

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
    hasMp3,
    mp3Url,
  }), [
    transcriptData,
    currentTranscript,
    selectedLanguage,
    isTranslating,
    handleLanguageChange,
    getCurrentTranscriptText,
    clearTranscriptData,
    hasMp3,
    mp3Url,
  ]);
};
