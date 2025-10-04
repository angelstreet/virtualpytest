import React, { useState, useRef, useEffect, useMemo, useCallback } from 'react';
import { Box, Slider, Typography, IconButton, Select, MenuItem, CircularProgress } from '@mui/material';
import { PlayArrow, Pause, Translate, AutoAwesome } from '@mui/icons-material';
import { HLSVideoPlayer } from '../common/HLSVideoPlayer';
import { useStream } from '../../hooks/controller';
import { Host } from '../../types/common/Host_Types';
import { buildStreamUrl } from '../../utils/buildUrlUtils';

interface ArchiveMetadata {
  total_segments: number;
  total_duration_seconds: number;
  window_hours: number;
  segments_per_window: number;
  manifests: Array<{
    name: string;
    window_index: number;
    start_segment: number;
    end_segment: number;
    start_time_seconds: number;
    end_time_seconds: number;
    duration_seconds: number;
  }>;
}

interface TranscriptSegment {
  segment_num: number;
  relative_seconds: number;
  language: string;
  transcript: string;
  enhanced_transcript?: string; // AI-enhanced transcript (preferred if available)
  confidence: number;
  manifest_window: number;
  translations?: Record<string, string>; // On-demand translations
}

interface TranscriptData {
  capture_folder: string;
  sample_interval_seconds: number;
  total_duration_seconds: number;
  segments: TranscriptSegment[];
  last_update: string;
  total_samples: number;
}

interface EnhancedHLSPlayerProps {
  deviceId: string;
  hostName: string;
  host?: Host; // Host object for useStream hook
  streamUrl?: string; // Server-provided stream URL
  width?: string | number;
  height?: string | number;
  muted?: boolean; // Add muted prop for audio control
  className?: string;
  isLiveMode?: boolean;
  quality?: 'low' | 'sd' | 'hd'; // Stream quality - forces reload when changed
  onPlayerReady?: () => void; // Callback when player loads successfully
}

export const EnhancedHLSPlayer: React.FC<EnhancedHLSPlayerProps> = ({
  deviceId,
  hostName,
  host,
  streamUrl: providedStreamUrl,
  width = '100%',
  height = 400,
  muted = true, // Default to muted for autoplay compliance
  className,
  isLiveMode: externalIsLiveMode,
  quality = 'sd', // Default to SD quality
  onPlayerReady
}) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [internalIsLiveMode] = useState(true); // Start in live mode
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [isPlaying, setIsPlaying] = useState(true); // Start playing automatically
  const [isTransitioning, setIsTransitioning] = useState(false); // Mode transition state
  
  // Archive metadata and manifest switching state
  const [archiveMetadata, setArchiveMetadata] = useState<ArchiveMetadata | null>(null);
  const [currentManifestIndex, setCurrentManifestIndex] = useState(0);
  const [globalCurrentTime, setGlobalCurrentTime] = useState(0); // Time across all manifests
  const [preloadedNextManifest, setPreloadedNextManifest] = useState(false);
  const [isDraggingSlider, setIsDraggingSlider] = useState(false);
  const [dragSliderValue, setDragSliderValue] = useState(0);
  
  // Transcript overlay state
  const [transcriptData, setTranscriptData] = useState<TranscriptData | null>(null);
  const [currentTranscript, setCurrentTranscript] = useState<TranscriptSegment | null>(null);
  
  // Translation state
  const [selectedLanguage, setSelectedLanguage] = useState<string>('original');
  const [isTranslating, setIsTranslating] = useState(false);
  
  // Use external control if provided, otherwise use internal state
  const isLiveMode = externalIsLiveMode !== undefined ? externalIsLiveMode : internalIsLiveMode;
  
  // Track previous mode to detect changes
  const prevIsLiveMode = useRef(isLiveMode);

  // Use useStream hook when host is provided and no streamUrl is given (same as RecHostPreview)
  const { streamUrl: hookStreamUrl } = useStream({
    host: host || {
      host_name: hostName,
      host_url: `http://${hostName}:6109`,
      host_port: 6109,
      devices: [],
      device_count: 0,
      status: 'online',
      last_seen: Date.now(),
      registered_at: new Date().toISOString(),
      system_stats: {
        cpu_percent: 0,
        memory_percent: 0,
        disk_percent: 0,
        platform: 'linux',
        architecture: 'x86_64',
        python_version: '3.9'
      },
      isLocked: false
    },
    device_id: deviceId,
  });

  // Detect mode changes and trigger transition
  useEffect(() => {
    if (prevIsLiveMode.current !== isLiveMode) {
      console.log(`[@EnhancedHLSPlayer] Mode change detected: ${prevIsLiveMode.current ? 'Live' : 'Archive'} -> ${isLiveMode ? 'Live' : 'Archive'}`);
      setIsTransitioning(true);
      
      // When switching back to live, clear archive metadata and transcripts
      if (isLiveMode) {
        console.log('[@EnhancedHLSPlayer] Clearing archive metadata (switching to live)');
        setArchiveMetadata(null);
        setCurrentManifestIndex(0);
        setTranscriptData(null);
        setCurrentTranscript(null);
      }
      
      // Small delay to allow cleanup
      setTimeout(() => {
        setIsTransitioning(false);
      }, 100);
      
      prevIsLiveMode.current = isLiveMode;
    }
  }, [isLiveMode]);

  // Fetch archive metadata when entering archive mode
  // NEW: Archive metadata no longer needed with hot/cold architecture
  // Each hour folder (0-23) has its own archive.m3u8 manifest
  useEffect(() => {
    if (!isLiveMode && !archiveMetadata && !isTransitioning) {
      // Hot/cold architecture: Build simple metadata with 24 hour manifests
      const metadata: ArchiveMetadata = {
        total_segments: 0, // Not calculated upfront
        total_duration_seconds: 24 * 3600, // 24 hours
        window_hours: 1, // 1 hour per folder
        segments_per_window: 3600, // 1 segment per second
        manifests: []
      };
      
      // Generate manifests for all 24 hours (0-23)
      for (let hour = 0; hour < 24; hour++) {
        metadata.manifests.push({
          name: `${hour}/archive.m3u8`, // Relative path from segments/
          window_index: hour,
          start_segment: hour * 3600,
          end_segment: (hour + 1) * 3600 - 1,
          start_time_seconds: hour * 3600,
          end_time_seconds: (hour + 1) * 3600,
          duration_seconds: 3600
        });
      }
      
      console.log('[@EnhancedHLSPlayer] Generated hour-based archive metadata (hot/cold):', metadata);
      setArchiveMetadata(metadata);
      
      // Start at hour 0 (beginning of 24h archive)
      console.log('[@EnhancedHLSPlayer] Starting at hour 0');
      setCurrentManifestIndex(0);
    }
  }, [isLiveMode, archiveMetadata, isTransitioning]);

  // Load hourly transcript file when manifest changes (aligned with archive windows)
  useEffect(() => {
    if (!isLiveMode && archiveMetadata && archiveMetadata.manifests.length > 0) {
      const currentManifest = archiveMetadata.manifests[currentManifestIndex];
      if (currentManifest) {
        const hourWindow = currentManifest.window_index;
        const baseUrl = providedStreamUrl || hookStreamUrl || buildStreamUrl(host, deviceId);
        const transcriptUrl = baseUrl.replace(/\/segments\/(output|archive.*?)\.m3u8$/, `/transcript_hour${hourWindow}.json`);
        
        console.log(`[@EnhancedHLSPlayer] Loading transcript for hour window ${hourWindow}...`);
        
        fetch(transcriptUrl)
          .then(res => res.json())
          .then(transcript => {
            if (transcript && transcript.segments) {
              console.log(`[@EnhancedHLSPlayer] Transcript hour${hourWindow} loaded: ${transcript.segments.length} samples`);
              setTranscriptData(transcript);
            } else {
              console.log(`[@EnhancedHLSPlayer] No transcript data for hour ${hourWindow}`);
              setTranscriptData(null);
            }
          })
          .catch(() => {
            console.log(`[@EnhancedHLSPlayer] No transcript available for hour ${hourWindow}`);
            setTranscriptData(null);
          });
      }
    }
  }, [isLiveMode, archiveMetadata, currentManifestIndex, providedStreamUrl, hookStreamUrl, deviceId]);

  // Generate hour marks for archive timeline (tick every 1h, label every 3h)
  const hourMarks = useMemo(() => {
    if (!archiveMetadata) return [];
    const totalHours = Math.floor(archiveMetadata.total_duration_seconds / 3600);
    const marks = [];
    for (let h = 0; h <= totalHours; h++) {
      marks.push({
        value: h * 3600,
        label: h % 3 === 0 ? `${h}h` : ''
      });
    }
    return marks;
  }, [archiveMetadata]);

  // Build the appropriate stream URL based on mode and current manifest
  // NEW: Hot/cold architecture - segments/ subfolder for all manifests
  const streamUrl = useMemo(() => {
    let url: string;
    
    // Live mode - use segments/output.m3u8
    if (isLiveMode) {
      if (providedStreamUrl) {
        // Replace old paths with new segments/ structure
        url = providedStreamUrl.replace(/\/(segments\/)?(output|archive.*?)\.m3u8$/, '/segments/output.m3u8');
      } else if (hookStreamUrl) {
        url = hookStreamUrl.replace(/\/(segments\/)?(output|archive.*?)\.m3u8$/, '/segments/output.m3u8');
      } else {
        url = buildStreamUrl(host, deviceId);
      }
    }
    // Archive mode - use hour-based manifests: segments/X/archive.m3u8
    else if (archiveMetadata && archiveMetadata.manifests.length > 0) {
      const currentManifest = archiveMetadata.manifests[currentManifestIndex];
      if (currentManifest) {
        const baseUrl = providedStreamUrl || hookStreamUrl || buildStreamUrl(host, deviceId);
        // Extract hour from manifest window_index and build path: segments/X/archive.m3u8
        const hour = currentManifest.window_index; // 0-23
        url = baseUrl.replace(/\/(segments\/)?(output|archive.*?)\.m3u8$/, `/segments/${hour}/archive.m3u8`);
        console.log(`[@EnhancedHLSPlayer] Using hour ${hour} manifest, URL: ${url}`);
      } else {
        url = providedStreamUrl?.replace(/\/(segments\/)?(output|archive.*?)\.m3u8$/, '/segments/0/archive.m3u8') 
          || hookStreamUrl?.replace(/\/(segments\/)?(output|archive.*?)\.m3u8$/, '/segments/0/archive.m3u8')
          || `/host/stream/capture${deviceId === 'device1' ? '1' : '2'}/segments/0/archive.m3u8`;
      }
    }
    // Fallback to first hour (0) while metadata is loading
    else {
      url = providedStreamUrl?.replace(/\/(segments\/)?(output|archive.*?)\.m3u8$/, '/segments/0/archive.m3u8')
        || hookStreamUrl?.replace(/\/(segments\/)?(output|archive.*?)\.m3u8$/, '/segments/0/archive.m3u8')
        || `/host/stream/capture${deviceId === 'device1' ? '1' : '2'}/segments/0/archive.m3u8`;
    }
    
    // Append quality parameter to force reload when quality changes (without unmounting component)
    if (quality) {
      const separator = url.includes('?') ? '&' : '?';
      url = `${url}${separator}q=${quality}`;
    }
    
    return url;
  }, [providedStreamUrl, hookStreamUrl, isLiveMode, deviceId, archiveMetadata, currentManifestIndex, quality]);

  // Seek to live edge when switching to live mode
  const seekToLive = () => {
    if (videoRef.current) {
      const video = videoRef.current;
      if (video.duration && !isNaN(video.duration) && isFinite(video.duration)) {
        video.currentTime = video.duration;
      }
    }
  };

  // Play/pause control
  const togglePlayPause = () => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause();
      } else {
        videoRef.current.play();
      }
      setIsPlaying(!isPlaying);
    }
  };

  // Video event handlers for timeline and play state with manifest switching
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const handleTimeUpdate = () => {
      setCurrentTime(video.currentTime);
      
      // Calculate global time if using multi-manifest archive
      if (!isLiveMode && archiveMetadata && archiveMetadata.manifests.length > 0) {
        const currentManifest = archiveMetadata.manifests[currentManifestIndex];
        if (currentManifest) {
          const globalTime = currentManifest.start_time_seconds + video.currentTime;
          setGlobalCurrentTime(globalTime);
          
          // Find matching transcript for current time (within this hour's segments)
          if (transcriptData && transcriptData.segments.length > 0) {
            const closestSegment = transcriptData.segments.reduce((closest, segment) => {
              const timeDiff = Math.abs(segment.relative_seconds - globalTime);
              const closestDiff = closest ? Math.abs(closest.relative_seconds - globalTime) : Infinity;
              return timeDiff < closestDiff ? segment : closest;
            }, transcriptData.segments[0]);
            
            // Show transcript if within 6s window (sample interval)
            if (Math.abs(closestSegment.relative_seconds - globalTime) < 6) {
              setCurrentTranscript(closestSegment);
            } else {
              setCurrentTranscript(null);
            }
          } else {
            setCurrentTranscript(null);
          }
          
          // Check if we need to switch to next manifest
          // Pre-load when 90% through current manifest
          const progressRatio = video.currentTime / video.duration;
          if (progressRatio > 0.9 && !preloadedNextManifest) {
            const nextIndex = currentManifestIndex + 1;
            if (nextIndex < archiveMetadata.manifests.length) {
              console.log(`[@EnhancedHLSPlayer] Pre-loading next manifest (${nextIndex + 1}/${archiveMetadata.manifests.length})`);
              setPreloadedNextManifest(true);
            }
          }
          
          // Switch to next manifest when reaching the end
          if (video.currentTime >= video.duration - 1) {
            const nextIndex = currentManifestIndex + 1;
            if (nextIndex < archiveMetadata.manifests.length) {
              console.log(`[@EnhancedHLSPlayer] Switching to manifest ${nextIndex + 1}`);
              setCurrentManifestIndex(nextIndex);
              setPreloadedNextManifest(false);
              // Video will restart at beginning of next manifest
            }
          }
        }
      } else {
        // For live mode or single manifest, use video.currentTime directly
        setGlobalCurrentTime(video.currentTime);
      }
    };
    
    const handleDurationChange = () => {
      setDuration(video.duration);
    };

    const handlePlay = () => setIsPlaying(true);
    const handlePause = () => setIsPlaying(false);

    video.addEventListener('timeupdate', handleTimeUpdate);
    video.addEventListener('durationchange', handleDurationChange);
    video.addEventListener('play', handlePlay);
    video.addEventListener('pause', handlePause);

    return () => {
      video.removeEventListener('timeupdate', handleTimeUpdate);
      video.removeEventListener('durationchange', handleDurationChange);
      video.removeEventListener('play', handlePlay);
      video.removeEventListener('pause', handlePause);
    };
  }, [isLiveMode, archiveMetadata, currentManifestIndex, preloadedNextManifest, transcriptData]);

  // Handle mode changes and seeking
  useEffect(() => {
    const timer = setTimeout(() => {
      if (isLiveMode) {
        seekToLive();
      } else {
        // For archive mode, seek to beginning
        if (videoRef.current && videoRef.current.duration) {
          console.log(`[@EnhancedHLSPlayer] Mode change to archive, seeking to beginning (0:00)`);
          videoRef.current.currentTime = 0;
        }
      }
    }, 500); // Small delay to allow HLS player to initialize with new manifest
    
    return () => clearTimeout(timer);
  }, [isLiveMode]);

  // Handle slider drag (visual feedback only)
  const handleSliderChange = useCallback((_event: Event | React.SyntheticEvent, newValue: number | number[]) => {
    if (isLiveMode) return;
    
    const seekTime = Array.isArray(newValue) ? newValue[0] : newValue;
    if (!isFinite(seekTime) || seekTime < 0) return;
    
    setIsDraggingSlider(true);
    setDragSliderValue(seekTime);
  }, [isLiveMode]);

  // Archive timeline controls with multi-manifest seeking (actual seek on release)
  const handleSeek = useCallback((_event: Event | React.SyntheticEvent, newValue: number | number[]) => {
    if (!videoRef.current || isLiveMode) return;
    
    setIsDraggingSlider(false);
    
    const seekTime = Array.isArray(newValue) ? newValue[0] : newValue;
    if (!isFinite(seekTime) || seekTime < 0) return;
    
    const video = videoRef.current;
    const wasPlaying = !video.paused;
    
    // If using multi-manifest archive, find correct manifest and seek within it
    if (archiveMetadata && archiveMetadata.manifests.length > 0) {
      // Find which manifest contains this time
      let targetManifestIndex = -1;
      let targetLocalTime = 0;
      
      for (let i = 0; i < archiveMetadata.manifests.length; i++) {
        const manifest = archiveMetadata.manifests[i];
        // Handle seek to exact end of manifest (boundary case)
        const isAtEnd = seekTime >= manifest.end_time_seconds && i === archiveMetadata.manifests.length - 1;
        const isInRange = seekTime >= manifest.start_time_seconds && seekTime < manifest.end_time_seconds;
        
        if (isInRange || isAtEnd) {
          targetManifestIndex = i;
          targetLocalTime = seekTime - manifest.start_time_seconds;
          
          // Clamp to manifest duration to avoid seeking beyond
          const manifestDuration = manifest.duration_seconds;
          targetLocalTime = Math.min(targetLocalTime, manifestDuration - 0.1);
          
          console.log(`[@EnhancedHLSPlayer] User seek: global ${seekTime.toFixed(1)}s -> manifest ${manifest.window_index} at ${targetLocalTime.toFixed(1)}s`);
          break;
        }
      }
      
      if (targetManifestIndex === -1) {
        console.warn(`[@EnhancedHLSPlayer] Seek time ${seekTime}s not found in any manifest`);
        return;
      }
      
      // Switch manifest if needed
      if (targetManifestIndex !== currentManifestIndex) {
        console.log(`[@EnhancedHLSPlayer] Switching from manifest ${currentManifestIndex + 1} to ${targetManifestIndex + 1}`);
        
        // Pause video during manifest switch to prevent playback issues
        video.pause();
        
        setCurrentManifestIndex(targetManifestIndex);
        setPreloadedNextManifest(false);
        
        // Wait for new manifest to load, then seek and resume playback
        setTimeout(() => {
          if (videoRef.current) {
            videoRef.current.currentTime = targetLocalTime;
            
            // Resume playback if it was playing before seek
            if (wasPlaying) {
              videoRef.current.play().catch(err => {
                console.warn('[@EnhancedHLSPlayer] Failed to resume playback after manifest switch:', err);
              });
            }
          }
        }, 1000); // Increased from 800ms
      } else {
        // Same manifest, just seek
        video.currentTime = targetLocalTime;
        
        // Video element automatically resumes if it was playing
      }
    } else {
      // Single manifest mode - simple seek
      video.currentTime = seekTime;
    }
  }, [isLiveMode, archiveMetadata, currentManifestIndex]);

  const formatTime = (seconds: number) => {
    if (!seconds || !isFinite(seconds)) return '0:00';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    return hours > 0 
      ? `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
      : `${minutes}:${secs.toString().padStart(2, '0')}`;
  };

  // Translation handler (minimal pattern from useRestart.ts)
  const handleLanguageChange = useCallback(async (language: string) => {
    setSelectedLanguage(language);
    
    // Original = instant switch (no API call)
    if (language === 'original') {
      console.log('[@EnhancedHLSPlayer] Switched to original language');
      return;
    }

    // Check if translations already exist in transcript data
    const hasTranslations = transcriptData?.segments.some(
      seg => seg.translations && seg.translations[language]
    );
    
    if (hasTranslations) {
      console.log(`[@EnhancedHLSPlayer] Using cached translations for ${language}`);
      return;
    }

    // Not cached - translate via backend
    setIsTranslating(true);
    console.log(`[@EnhancedHLSPlayer] Translating transcripts to ${language}...`);
    
    try {
      const baseUrl = providedStreamUrl || hookStreamUrl || buildStreamUrl(host, deviceId);
      // Extract capture folder from stream URL (e.g., capture1, capture2)
      const captureMatch = baseUrl.match(/\/stream\/(\w+)\//);
      const captureFolder = captureMatch ? captureMatch[1] : transcriptData?.capture_folder;
      
      // Get current hour window for hourly transcript files
      const currentManifest = archiveMetadata?.manifests[currentManifestIndex];
      const hourWindow = currentManifest?.window_index || 1;
      
      const response = await fetch(`/host/${captureFolder}/translate-transcripts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          target_language: language,
          hour_window: hourWindow  // Tell backend which hourly file to translate
        })
      });

      const data = await response.json();
      
      if (data.success) {
        console.log(`[@EnhancedHLSPlayer] Translation complete: ${data.translated_count} segments translated`);
        
        // Reload current hourly transcript data with new translations
        const transcriptUrl = baseUrl.replace(/\/(output|archive.*?)\.m3u8$/, `/transcript_hour${hourWindow}.json`);
        const updatedData = await fetch(transcriptUrl).then(res => res.json());
        setTranscriptData(updatedData);
      }
    } catch (error) {
      console.error('[@EnhancedHLSPlayer] Translation failed:', error);
    } finally {
      setIsTranslating(false);
    }
  }, [transcriptData, archiveMetadata, currentManifestIndex, providedStreamUrl, hookStreamUrl, deviceId, hostName]);

  // Get current transcript text (with AI enhancement and translation support)
  const getCurrentTranscriptText = useCallback(() => {
    if (!currentTranscript) return '';
    
    if (selectedLanguage === 'original') {
      // Prefer AI-enhanced transcript if available, otherwise use original Whisper transcript
      return currentTranscript.enhanced_transcript || currentTranscript.transcript;
    }
    
    // Use translated version if available
    const translation = currentTranscript.translations?.[selectedLanguage];
    return translation || currentTranscript.enhanced_transcript || currentTranscript.transcript;
  }, [currentTranscript, selectedLanguage]);

  return (
    <Box className={className} sx={{ width, position: 'relative' }}>
      {/* Reuse HLSVideoPlayer for all streaming logic */}
      <Box sx={{ position: 'relative', height }}>
        {!isTransitioning ? (
          <HLSVideoPlayer
            key={`${isLiveMode ? 'live' : 'archive'}`} // Only remount on mode change, not quality change
            streamUrl={streamUrl}
            isStreamActive={true}
            videoElementRef={videoRef}
            muted={muted} // Use the muted prop from parent
            isArchiveMode={!isLiveMode} // Pass archive mode flag
            sx={{ width: '100%', height: '100%' }}
            onPlayerReady={onPlayerReady} // Pass callback to notify when player loads successfully
          />
        ) : (
          <Box
            sx={{
              width: '100%',
              height: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: 'black',
              color: 'white',
            }}
          >
            <Typography>Switching mode...</Typography>
          </Box>
        )}

        {/* Language Selector */}
        {!isLiveMode && transcriptData && transcriptData.segments.length > 0 && (
          <Box
            sx={{
              position: 'absolute',
              top: 10,
              right: 10,
              display: 'flex',
              alignItems: 'center',
              gap: 1,
              backgroundColor: 'rgba(0, 0, 0, 0.7)',
              borderRadius: 1,
              p: 1,
            }}
          >
            <Translate sx={{ color: 'white', fontSize: 20 }} />
            <Select
              value={selectedLanguage}
              onChange={(e) => handleLanguageChange(e.target.value)}
              size="small"
              disabled={isTranslating}
              sx={{
                color: 'white',
                minWidth: 120,
                '& .MuiOutlinedInput-notchedOutline': {
                  borderColor: 'rgba(255, 255, 255, 0.3)',
                },
                '&:hover .MuiOutlinedInput-notchedOutline': {
                  borderColor: 'rgba(255, 255, 255, 0.5)',
                },
                '& .MuiSvgIcon-root': {
                  color: 'white',
                },
              }}
            >
              <MenuItem value="original">Original</MenuItem>
              <MenuItem value="French">French</MenuItem>
              <MenuItem value="Spanish">Spanish</MenuItem>
              <MenuItem value="German">German</MenuItem>
              <MenuItem value="Italian">Italian</MenuItem>
              <MenuItem value="Portuguese">Portuguese</MenuItem>
            </Select>
            {isTranslating && <CircularProgress size={20} sx={{ color: 'white' }} />}
          </Box>
        )}

        {/* Transcript Overlay */}
        {!isLiveMode && currentTranscript && getCurrentTranscriptText() && (
          <Box
            sx={{
              position: 'absolute',
              bottom: 100,
              left: '50%',
              transform: 'translateX(-50%)',
              backgroundColor: 'rgba(0, 0, 0, 0.85)',
              color: 'white',
              px: 3,
              py: 1.5,
              borderRadius: 2,
              maxWidth: '80%',
              textAlign: 'center',
              // Blue border for AI-enhanced, white for original
              border: currentTranscript.enhanced_transcript && selectedLanguage === 'original'
                ? '2px solid rgba(33, 150, 243, 0.8)' // Blue for enhanced
                : '1px solid rgba(255, 255, 255, 0.3)', // White for original
              boxShadow: currentTranscript.enhanced_transcript && selectedLanguage === 'original'
                ? '0 4px 12px rgba(33, 150, 243, 0.4)' // Blue glow for enhanced
                : '0 4px 12px rgba(0,0,0,0.5)',
            }}
          >
            {/* AI Enhanced Icon */}
            {currentTranscript.enhanced_transcript && selectedLanguage === 'original' && (
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', mb: 0.5 }}>
                <AutoAwesome sx={{ fontSize: 16, color: '#2196f3', mr: 0.5 }} />
                <Typography variant="caption" sx={{ color: '#2196f3', fontWeight: 600 }}>
                  AI Enhanced
                </Typography>
              </Box>
            )}
            
            <Typography variant="body2" sx={{ fontWeight: 500, lineHeight: 1.4 }}>
              {getCurrentTranscriptText()}
            </Typography>
            <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.6)', mt: 0.5, display: 'block' }}>
              {selectedLanguage === 'original' 
                ? `${currentTranscript.language} • ${Math.round(currentTranscript.confidence * 100)}%`
                : `Translated to ${selectedLanguage}`
              }
            </Typography>
          </Box>
        )}

        {/* Archive Timeline Overlay with integrated Play/Pause button */}
        {!isLiveMode && !isTransitioning && duration > 0 && (
          <Box
            sx={{
              position: 'absolute',
              bottom: -20, // Compensate for modal's 20px margin from window height
              left: 0,
              right: 0,
              background: 'linear-gradient(transparent, rgba(0,0,0,0.8))',
              p: 2,
            }}
          >
            {/* Timeline controls row */}
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1 }}>
              {/* Play/Pause Button */}
              <IconButton
                onClick={togglePlayPause}
                sx={{
                  backgroundColor: 'rgba(0, 0, 0, 0.6)',
                  color: 'white',
                  border: '2px solid rgba(255, 255, 255, 0.7)',
                  '&:hover': {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    border: '2px solid rgba(255, 255, 255, 1)',
                  },
                  minWidth: 40,
                  height: 40,
                }}
                size="small"
              >
                {isPlaying ? <Pause /> : <PlayArrow />}
              </IconButton>
              
              {/* Timeline Slider */}
              <Slider
                value={isDraggingSlider ? dragSliderValue : (archiveMetadata ? globalCurrentTime : currentTime)}
                max={archiveMetadata ? archiveMetadata.total_duration_seconds : duration}
                onChange={handleSliderChange}
                onChangeCommitted={handleSeek}
                marks={hourMarks}
                sx={{ 
                  color: 'primary.main', 
                  flex: 1,
                  '& .MuiSlider-thumb': {
                    width: 16,
                    height: 16,
                  },
                  '& .MuiSlider-markLabel': {
                    fontSize: '0.7rem',
                    color: 'rgba(255,255,255,0.7)'
                  }
                }}
              />
            </Box>
            
            {/* Time display row */}
            <Box sx={{ display: 'flex', justifyContent: 'space-between', pl: 7 }}>  
              <Typography variant="caption" sx={{ color: 'white' }}>
                {formatTime(isDraggingSlider ? dragSliderValue : (archiveMetadata && archiveMetadata.manifests.length > 0 ? globalCurrentTime : currentTime))}
              </Typography>
              {archiveMetadata && (
                <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.6)' }}>
                  Manifest {currentManifestIndex + 1}/{archiveMetadata.manifests.length}
                </Typography>
              )}
              <Typography variant="caption" sx={{ color: 'white' }}>
                {formatTime(archiveMetadata ? archiveMetadata.total_duration_seconds : duration)}
              </Typography>
            </Box>
          </Box>
        )}
      </Box>
    </Box>
  );
};
