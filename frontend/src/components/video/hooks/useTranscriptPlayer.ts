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
            
            // Extract available languages from manifest
            const languages = chunkInfo.available_languages || ['original'];
            const dubbedLanguages = chunkInfo.available_dubbed_languages || [];
            setAvailableLanguages(languages);
            setAvailableDubbedLanguages(dubbedLanguages);
            console.log(`[@useTranscriptPlayer] Available languages:`, languages);
            console.log(`[@useTranscriptPlayer] Available dubbed audio:`, dubbedLanguages);
            
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
            
            // Show segment summary
            const segmentCount = transcript.segments?.length || 0;
            if (segmentCount > 0 && transcript.segments) {
              const firstSeg = transcript.segments[0];
              const lastSeg = transcript.segments[segmentCount - 1];
              console.log(`📚 Loaded ${segmentCount} segments: ${firstSeg.start.toFixed(1)}s-${lastSeg.end.toFixed(1)}s | First: "${firstSeg.text.substring(0, 30)}..."`);
            } else {
              console.log(`[@useTranscriptPlayer] 10-min transcript with ${segmentCount} timed segments`);
            }
            
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
    
    // Count segments in current minute
    const segmentsInMinute = rawTranscriptData.segments.filter(
      seg => seg.start >= minuteStart && seg.start < minuteEnd
    );
    
    // Find active segment within current minute
    const activeSegment = rawTranscriptData.segments.find(
      seg => seg.start >= minuteStart && seg.start < minuteEnd && localTime >= seg.start && localTime < seg.end
    );
    
    if (activeSegment) {
      setCurrentTimedSegment(activeSegment);
      console.log(`📝 Minute ${currentMinute} | Time ${localTime.toFixed(1)}s | Showing: "${activeSegment.text.substring(0, 40)}..."`);
    } else {
      setCurrentTimedSegment(null);
      console.log(`⏸️ Minute ${currentMinute} | Time ${localTime.toFixed(1)}s | ${segmentsInMinute.length} segments but none active (between segments)`);
    }
  }, [rawTranscriptData, globalCurrentTime, archiveMetadata, currentManifestIndex]);

  // Translation progress removed - we now translate the full transcript as ONE block (fast!)
  
  // Helper: Load transcript for a specific language (original or pre-translated)
  const loadTranscriptForLanguage = useCallback(async (hour: number, chunkIndex: number, language: string) => {
    const baseUrl = providedStreamUrl || hookStreamUrl || buildStreamUrl(host, deviceId);
    const langSuffix = language === 'original' ? '' : `_${language}`;
    const transcriptUrl = baseUrl.replace(/\/(segments\/)?(output|archive.*?)\.m3u8$/, `/transcript/${hour}/chunk_10min_${chunkIndex}${langSuffix}.json`);
    
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
  }, [providedStreamUrl, hookStreamUrl, deviceId, host]);
  
  // Helper: Reload transcript data from manifest
  const reloadTranscriptData = useCallback(async () => {
    if (!rawTranscriptData) return;
    
    const baseUrl = providedStreamUrl || hookStreamUrl || buildStreamUrl(host, deviceId);
    const manifestUrl = baseUrl.replace(/\/(segments\/)?(output|archive.*?)\.m3u8$/, `/transcript/transcript_manifest.json`);
    
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
  }, [rawTranscriptData, providedStreamUrl, hookStreamUrl, deviceId, host]);

  // Handle audio language change (dubbed audio only)
  const handleAudioLanguageChange = useCallback(async (language: string) => {
    setSelectedAudioLanguage(language);
    
    if (!archiveMetadata?.manifests.length) return;
    const currentManifest = archiveMetadata.manifests[currentManifestIndex];
    if (!currentManifest) return;

    const hour = currentManifest.window_index;
    const chunkIndex = currentManifest.chunk_index;
    const baseUrl = providedStreamUrl || hookStreamUrl || buildStreamUrl(host, deviceId);

    if (language === 'original') {
      setDubbedAudioUrl(null);
      console.log(`[@useTranscriptPlayer] Switched to original audio`);
    } else if (availableDubbedLanguages.includes(language)) {
      // Try 1-minute dubbed audio first (fast!), fallback to 10-minute
      const currentMinute = Math.floor(globalCurrentTime / 60) % 10; // 0-9
      const url1min = baseUrl.replace(/\/(segments\/)?(output|archive.*?)\.m3u8$/, `/audio/temp/1min_${currentMinute}_${language}.mp3`);
      const url10min = baseUrl.replace(/\/(segments\/)?(output|archive.*?)\.m3u8$/, `/audio/${hour}/chunk_10min_${chunkIndex}_${language}.mp3`);
      
      // Check if 1-minute dubbed audio exists (HEAD request for speed)
      try {
        const response = await fetch(url1min, { method: 'HEAD' });
        if (response.ok) {
          setDubbedAudioUrl(url1min);
          console.log(`[@useTranscriptPlayer] 🎤 Using 1min dubbed audio (${language}):`, url1min);
          return;
        }
      } catch (e) {
        console.debug(`[@useTranscriptPlayer] 1min dubbed audio not available, trying 10min...`);
      }
      
      // Check if 10-minute dubbed audio exists
      try {
        const response10 = await fetch(url10min, { method: 'HEAD' });
        if (response10.ok) {
          setDubbedAudioUrl(url10min);
          console.log(`[@useTranscriptPlayer] 🎤 Using 10min dubbed audio (${language}):`, url10min);
          return;
        }
      } catch (e) {
        console.debug(`[@useTranscriptPlayer] 10min dubbed audio not found, generating on-demand...`);
      }
      
      // Generate on-demand
      setIsTranslating(true);
      try {
        const response = await fetch(`${host}/host/transcript/generate-dubbed-audio`, {
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
          const fullUrl = baseUrl.replace(/\/(segments\/)?(output|archive.*?)\.m3u8$/, result.url);
          setDubbedAudioUrl(fullUrl);
          console.log(`[@useTranscriptPlayer] ✅ Generated dubbed audio (${language}):`, fullUrl);
        } else {
          console.error(`[@useTranscriptPlayer] Failed to generate dubbed audio:`, result.error);
          setDubbedAudioUrl(null);
        }
      } catch (error) {
        console.error(`[@useTranscriptPlayer] Error generating dubbed audio:`, error);
        setDubbedAudioUrl(null);
      } finally {
        setIsTranslating(false);
      }
    } else {
      setDubbedAudioUrl(null);
    }
  }, [availableDubbedLanguages, archiveMetadata, currentManifestIndex, globalCurrentTime, providedStreamUrl, hookStreamUrl, host, deviceId]);

  // Handle transcript/subtitle language change (text only)
  const handleTranscriptLanguageChange = useCallback(async (language: string) => {
    setSelectedTranscriptLanguage(language);
    
    if (language === 'original') {
      // Just reload original
      await reloadTranscriptData();
      return;
    }
    
    if (!archiveMetadata?.manifests.length) return;
    const currentManifest = archiveMetadata.manifests[currentManifestIndex];
    if (!currentManifest) return;

    const hour = currentManifest.window_index;
    const chunkIndex = currentManifest.chunk_index;

    if (availableLanguages.includes(language)) {
      // Translation already exists, just load it
      setIsTranslating(true);
      await loadTranscriptForLanguage(hour, chunkIndex, language);
      setIsTranslating(false);
    } else {
      // On-demand translation via AI
      setIsTranslating(true);
      console.log(`[@useTranscriptPlayer] 🤖 Requesting AI translation to ${language}...`);
      
      try {
        const response = await fetch(`${host}/host/transcript/translate-chunk`, {
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
        
        if (result.success) {
          console.log(`[@useTranscriptPlayer] ✅ Translation complete (${result.cached ? 'cached' : 'fresh'}, ${result.processing_time?.toFixed(1) || '?'}s)`);
          // Load the new translation
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
  }, [availableLanguages, archiveMetadata, currentManifestIndex, loadTranscriptForLanguage, reloadTranscriptData, host, deviceId]);

  // Auto-update 1-minute dubbed audio as video progresses through minutes
  useEffect(() => {
    if (selectedAudioLanguage === 'original' || !availableDubbedLanguages.includes(selectedAudioLanguage)) {
      return;
    }

    if (!archiveMetadata?.manifests.length) return;
    const currentManifest = archiveMetadata.manifests[currentManifestIndex];
    if (!currentManifest) return;

    const currentMinute = Math.floor(globalCurrentTime / 60) % 10;
    const baseUrl = providedStreamUrl || hookStreamUrl || buildStreamUrl(host, deviceId);
    const hour = currentManifest.window_index;
    const chunkIndex = currentManifest.chunk_index;

    // Try 1-minute dubbed audio for current minute
    const url1min = baseUrl.replace(/\/(segments\/)?(output|archive.*?)\.m3u8$/, `/audio/temp/1min_${currentMinute}_${selectedAudioLanguage}.mp3`);
    const url10min = baseUrl.replace(/\/(segments\/)?(output|archive.*?)\.m3u8$/, `/audio/${hour}/chunk_10min_${chunkIndex}_${selectedAudioLanguage}.mp3`);

    // Quick HEAD check (async, don't block)
    fetch(url1min, { method: 'HEAD' })
      .then(response => {
        if (response.ok && dubbedAudioUrl !== url1min) {
          setDubbedAudioUrl(url1min);
          console.log(`[@useTranscriptPlayer] 🔄 Auto-switched to 1min dubbed audio for minute ${currentMinute}`);
        } else if (!response.ok && dubbedAudioUrl !== url10min) {
          setDubbedAudioUrl(url10min);
        }
      })
      .catch(() => {
        if (dubbedAudioUrl !== url10min) {
          setDubbedAudioUrl(url10min);
        }
      });
  }, [globalCurrentTime, selectedAudioLanguage, availableDubbedLanguages, archiveMetadata, currentManifestIndex, providedStreamUrl, hookStreamUrl, host, deviceId, dubbedAudioUrl]);

  const getCurrentTranscriptText = useCallback(() => {
    // For new 10-min format with timed segments, ONLY use timed segments (no fallback)
    if (rawTranscriptData?.segments && rawTranscriptData.segments.length > 0) {
      if (!currentTimedSegment) return '';  // Show nothing between segments - no fallback to full transcript
      
      // Check for translation in timed segment
      if (selectedTranscriptLanguage !== 'original' && currentTimedSegment.translations?.[selectedTranscriptLanguage]) {
        return currentTimedSegment.translations[selectedTranscriptLanguage];
      }
      return currentTimedSegment.text;
    }
    
    // Legacy format (6-second segments) - use currentTranscript
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
    selectedAudioLanguage,
    selectedTranscriptLanguage,
    availableLanguages,
    availableDubbedLanguages,
    isTranslating,
    handleAudioLanguageChange,
    handleTranscriptLanguageChange,
    getCurrentTranscriptText,
    clearTranscriptData,
    hasMp3,
    mp3Url,
    dubbedAudioUrl,
  }), [
    transcriptData,
    currentTranscript,
    selectedAudioLanguage,
    selectedTranscriptLanguage,
    availableLanguages,
    availableDubbedLanguages,
    isTranslating,
    handleAudioLanguageChange,
    handleTranscriptLanguageChange,
    getCurrentTranscriptText,
    clearTranscriptData,
    hasMp3,
    mp3Url,
    dubbedAudioUrl,
  ]);
};
