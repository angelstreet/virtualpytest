import { useState, useCallback, useEffect, useMemo } from 'react';
import { TranscriptData, TranscriptDataLegacy, TranscriptData10Min, TranscriptSegment, ArchiveMetadata, TimedSegment } from '../EnhancedHLSPlayer.types';
import { Host } from '../../../types/common/Host_Types';
import { 
  buildHostUrl, 
  buildAudioMp3Url,
  buildDubbedAudioUrl,
  buildDubbedAudio1MinUrl,
  buildTranscriptChunkUrl,
  buildTranscriptManifestUrl
} from '../../../utils/buildUrlUtils';

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
  const [currentTimedSegment, setCurrentTimedSegment] = useState<TimedSegment | null>(null);
  
  // Separate language selection for audio and transcript
  const [selectedAudioLanguage, setSelectedAudioLanguage] = useState<string>('original');
  const [selectedTranscriptLanguage, setSelectedTranscriptLanguage] = useState<string>('original');
  
  const [availableLanguages, setAvailableLanguages] = useState<string[]>(['original']);
  const [availableDubbedLanguages, setAvailableDubbedLanguages] = useState<string[]>([]);
  const [isTranslating, setIsTranslating] = useState(false);
  const [hasMp3, setHasMp3] = useState(false);
  const [mp3Url, setMp3Url] = useState<string | null>(null);
  const [dubbedAudioUrl, setDubbedAudioUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!isLiveMode && archiveMetadata && archiveMetadata.manifests.length > 0) {
      const currentManifest = archiveMetadata.manifests[currentManifestIndex];
      if (currentManifest) {
        const hour = currentManifest.window_index;
        const chunkIndex = currentManifest.chunk_index;
        
        // Check transcript manifest first to avoid 404s
        const manifestUrl = buildTranscriptManifestUrl(host, deviceId);
        
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
              const mp3Path = buildAudioMp3Url(host, deviceId, hour, chunkIndex);
              setMp3Url(mp3Path);
            } else {
              setMp3Url(null);
            }
            
            // Extract available languages from manifest
            const languages = chunkInfo.available_languages || ['original'];
            const dubbedLanguages = chunkInfo.available_dubbed_languages || [];
            setAvailableLanguages(languages);
            setAvailableDubbedLanguages(dubbedLanguages);
            console.log(`[@useTranscriptPlayer] Available languages:`, languages);
            console.log(`[@useTranscriptPlayer] Available dubbed audio:`, dubbedLanguages);
            
            // Manifest has metadata only - load actual chunk JSON for segments
            console.log(`[@useTranscriptPlayer] Loading transcript chunk with segments (hour ${hour}, chunk ${chunkIndex})`);
            const transcriptUrl = buildTranscriptChunkUrl(host, deviceId, hour, chunkIndex, 'original');
            
            fetch(transcriptUrl)
              .then(res => {
                if (!res.ok) throw new Error(`Transcript chunk not found`);
                return res.json();
              })
              .then((data) => {
                const transcript: TranscriptData10Min = {
                  ...data,
                  hour: hour,
                  chunk_index: chunkIndex,
                };
                
                if (!transcript.transcript) {
                  console.log(`[@useTranscriptPlayer] No transcript text in chunk ${chunkIndex}`);
                  setTranscriptData(null);
                  setRawTranscriptData(null);
                  return;
                }
                
                // Store raw 10-min data for timed segment access
                setRawTranscriptData(transcript);
                
                // Show segment summary
                const segmentCount = transcript.segments?.length || 0;
                if (segmentCount > 0 && transcript.segments) {
                  const firstSeg = transcript.segments[0];
                  const lastSeg = transcript.segments[segmentCount - 1];
                  console.log(`📚 Loaded ${segmentCount} segments: ${firstSeg.start.toFixed(1)}s-${lastSeg.end.toFixed(1)}s | First: "${firstSeg.text.substring(0, 30)}..."`);
                } else {
                  console.log(`[@useTranscriptPlayer] ⚠️ Chunk has no timed segments`);
                }
                
                const normalizedData = normalizeTranscriptData(transcript);
                
                console.log(`[@useTranscriptPlayer] ✅ Transcript loaded:`, {
                  language: transcript.language,
                  confidence: transcript.confidence,
                  textLength: transcript.transcript.length,
                  segmentCount: segmentCount,
                  preview: transcript.transcript.substring(0, 100)
                });
                
                setTranscriptData(normalizedData);
              })
              .catch((error) => {
                console.error(`[@useTranscriptPlayer] Failed to load transcript:`, error.message);
                setTranscriptData(null);
                setRawTranscriptData(null);
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
        const closestSegment = transcriptData.segments.reduce((closest: TranscriptSegment, segment: TranscriptSegment) => {
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
    
    // Find active segment at current time (no per-minute filtering for incomplete chunks)
    const activeSegment = rawTranscriptData.segments.find(
      seg => localTime >= seg.start && localTime < seg.end
    );
    
    if (activeSegment) {
      setCurrentTimedSegment(activeSegment);
      console.log(`📝 ${localTime.toFixed(1)}s | seg[${activeSegment.start.toFixed(1)}-${activeSegment.end.toFixed(1)}] | "${activeSegment.text.substring(0, 40)}..."`);
    } else {
      setCurrentTimedSegment(null);
      
      // Log if no segment found (useful for debugging incomplete chunks)
      const segmentRange = rawTranscriptData.segments.length > 0 
        ? `${rawTranscriptData.segments[0].start.toFixed(1)}-${rawTranscriptData.segments[rawTranscriptData.segments.length - 1].end.toFixed(1)}s`
        : 'none';
      if (rawTranscriptData.segments.length === 0 || localTime < rawTranscriptData.segments[0].start || localTime > rawTranscriptData.segments[rawTranscriptData.segments.length - 1].end) {
        console.log(`⏹️ ${localTime.toFixed(1)}s | Outside segment range: ${segmentRange} (${rawTranscriptData.segments.length} segments)`);
      }
    }
  }, [rawTranscriptData, globalCurrentTime, archiveMetadata, currentManifestIndex]);

  // Translation progress removed - we now translate the full transcript as ONE block (fast!)
  
  // Helper: Load transcript for a specific language (original or pre-translated)
  const loadTranscriptForLanguage = useCallback(async (hour: number, chunkIndex: number, language: string) => {
    const transcriptUrl = buildTranscriptChunkUrl(host, deviceId, hour, chunkIndex, language);
    
    try {
      const response = await fetch(transcriptUrl);
      if (!response.ok) throw new Error(`Failed to load ${language} transcript`);
      
      const data = await response.json();
      const transcript: TranscriptData10Min = { ...data, hour, chunk_index: chunkIndex };
      
      setRawTranscriptData(transcript);
      setTranscriptData(normalizeTranscriptData(transcript));
      console.log(`[@useTranscriptPlayer] ✅ Loaded ${language} transcript`);
    } catch (error) {
      console.error(`[@useTranscriptPlayer] Error loading ${language}:`, error);
    }
  }, [deviceId, host]);
  
  // Helper: Reload transcript data from manifest
  const reloadTranscriptData = useCallback(async () => {
    if (!rawTranscriptData) return;
    
    const manifestUrl = buildTranscriptManifestUrl(host, deviceId);
    
    try {
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
            segments: chunkInfo.segments || [],
            minute_metadata: chunkInfo.minute_metadata || []
          };
          
          setRawTranscriptData(updatedTranscript);
          setTranscriptData(normalizeTranscriptData(updatedTranscript));
        }
      }
    } catch (error) {
      console.error('[@useTranscriptPlayer] Failed to reload transcript:', error);
    }
  }, [rawTranscriptData, deviceId, host]);

  // Unified language change handler (handles both transcript and audio)
  const handleLanguageChange = useCallback(async (language: string) => {
    setSelectedTranscriptLanguage(language);
    setSelectedAudioLanguage(language);
    
    if (language === 'original') {
      await reloadTranscriptData();
    } else {
      if (!archiveMetadata?.manifests.length) return;
      const currentManifest = archiveMetadata.manifests[currentManifestIndex];
      if (!currentManifest) return;

      const hour = currentManifest.window_index;
      const chunkIndex = currentManifest.chunk_index;

      if (availableLanguages.includes(language)) {
        setIsTranslating(true);
        await loadTranscriptForLanguage(hour, chunkIndex, language);
        setIsTranslating(false);
      } else {
        setIsTranslating(true);
        
        try {
          if (!host) {
            console.error(`[@useTranscriptPlayer] Host information required for API call`);
            setIsTranslating(false);
            return;
          }
          
          const transcriptUrl = buildTranscriptChunkUrl(host, deviceId, hour, chunkIndex, 'original');

          const apiUrl = buildHostUrl(host, 'host/transcript/translate-chunk');
          const response = await fetch(apiUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              chunk_url: transcriptUrl,
              language
            })
          });
          
          const result = await response.json();
          
          if (result.success) {
            await loadTranscriptForLanguage(hour, chunkIndex, language);
          } else {
            console.error(`[@useTranscriptPlayer] Translation failed:`, result.error);
          }
        } catch (error) {
          console.error(`[@useTranscriptPlayer] Translation error:`, error);
        } finally {
          setIsTranslating(false);
        }
      }
    }
    
    if (!archiveMetadata?.manifests.length) return;
    const currentManifest = archiveMetadata.manifests[currentManifestIndex];
    if (!currentManifest) return;

    const hour = currentManifest.window_index;
    const chunkIndex = currentManifest.chunk_index;

    if (language === 'original') {
      setDubbedAudioUrl(null);
    } else if (availableDubbedLanguages.includes(language)) {
      const currentMinute = Math.floor(globalCurrentTime / 60) % 10;
      const url1min = buildDubbedAudio1MinUrl(host, deviceId, currentMinute, language);
      const url10min = buildDubbedAudioUrl(host, deviceId, hour, chunkIndex, language);
      
      try {
        const response = await fetch(url1min, { method: 'HEAD' });
        if (response.ok) {
          setDubbedAudioUrl(url1min);
          return;
        }
      } catch (e) {
        // Fallback to 10min
      }
      
      try {
        const response10 = await fetch(url10min, { method: 'HEAD' });
        if (response10.ok) {
          setDubbedAudioUrl(url10min);
          return;
        }
      } catch (e) {
        // Generate on-demand
      }
      
      setIsTranslating(true);
      try {
        if (!host) {
          setDubbedAudioUrl(null);
          setIsTranslating(false);
          return;
        }
        
        const apiUrl = buildHostUrl(host, 'host/transcript/generate-dubbed-audio');
        const response = await fetch(apiUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ 
            device_id: deviceId, 
            hour, 
            chunk_index: chunkIndex, 
            language 
          })
        });
        
        const result = await response.json();
        
        if (result.success && result.url) {
          // Result URL is a relative path, use buildHostUrl to construct full URL
          // Remove leading slash if present since buildHostUrl handles it
          const cleanUrl = result.url.startsWith('/') ? result.url.slice(1) : result.url;
          const fullUrl = buildHostUrl(host, cleanUrl);
          setDubbedAudioUrl(fullUrl);
        } else {
          setDubbedAudioUrl(null);
        }
      } catch (error) {
        setDubbedAudioUrl(null);
      } finally {
        setIsTranslating(false);
      }
    } else {
      setDubbedAudioUrl(null);
    }
  }, [availableLanguages, availableDubbedLanguages, archiveMetadata, currentManifestIndex, globalCurrentTime, 
      loadTranscriptForLanguage, reloadTranscriptData, host, deviceId]);

  // Auto-update 1-minute dubbed audio as video progresses through minutes
  useEffect(() => {
    if (selectedAudioLanguage === 'original' || !availableDubbedLanguages.includes(selectedAudioLanguage)) {
      return;
    }

    if (!archiveMetadata?.manifests.length) return;
    const currentManifest = archiveMetadata.manifests[currentManifestIndex];
    if (!currentManifest) return;

    const currentMinute = Math.floor(globalCurrentTime / 60) % 10;
    const hour = currentManifest.window_index;
    const chunkIndex = currentManifest.chunk_index;

    const url1min = buildDubbedAudio1MinUrl(host, deviceId, currentMinute, selectedAudioLanguage);
    const url10min = buildDubbedAudioUrl(host, deviceId, hour, chunkIndex, selectedAudioLanguage);

    fetch(url1min, { method: 'HEAD' })
      .then(response => {
        if (response.ok && dubbedAudioUrl !== url1min) {
          setDubbedAudioUrl(url1min);
        } else if (!response.ok && dubbedAudioUrl !== url10min) {
          setDubbedAudioUrl(url10min);
        }
      })
      .catch(() => {
        if (dubbedAudioUrl !== url10min) {
          setDubbedAudioUrl(url10min);
        }
      });
  }, [globalCurrentTime, selectedAudioLanguage, availableDubbedLanguages, archiveMetadata, currentManifestIndex, host, deviceId, dubbedAudioUrl]);

  const getCurrentTranscriptText = useCallback(() => {
    if (rawTranscriptData?.segments && rawTranscriptData.segments.length > 0) {
      if (!currentTimedSegment) return '';
      
      if (selectedTranscriptLanguage !== 'original' && currentTimedSegment.translations?.[selectedTranscriptLanguage]) {
        return currentTimedSegment.translations[selectedTranscriptLanguage];
      }
      return currentTimedSegment.text;
    }
    
    if (!currentTranscript) return '';
    
    if (selectedTranscriptLanguage === 'original') {
      return currentTranscript.enhanced_transcript || currentTranscript.transcript;
    }
    
    const translation = currentTranscript.translations?.[selectedTranscriptLanguage];
    return translation || currentTranscript.enhanced_transcript || currentTranscript.transcript;
  }, [rawTranscriptData, currentTranscript, currentTimedSegment, selectedTranscriptLanguage]);

  const clearTranscriptData = useCallback(() => {
    setTranscriptData(null);
    setCurrentTranscript(null);
  }, []);

  return useMemo(() => ({
    transcriptData,
    currentTranscript,
    selectedLanguage: selectedTranscriptLanguage, // Unified language (same for both transcript and audio)
    availableLanguages,
    availableDubbedLanguages,
    isTranslating,
    handleLanguageChange, // Unified handler for both transcript and audio
    getCurrentTranscriptText,
    clearTranscriptData,
    hasMp3,
    mp3Url,
    dubbedAudioUrl,
  }), [
    transcriptData,
    currentTranscript,
    selectedTranscriptLanguage,
    availableLanguages,
    availableDubbedLanguages,
    isTranslating,
    handleLanguageChange,
    getCurrentTranscriptText,
    clearTranscriptData,
    hasMp3,
    mp3Url,
    dubbedAudioUrl,
  ]);
};
