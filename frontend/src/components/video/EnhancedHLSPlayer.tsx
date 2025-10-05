import React, { useState, useRef, useEffect, useMemo, useCallback } from 'react';
import { Box, Slider, Typography, IconButton, Select, MenuItem, CircularProgress } from '@mui/material';
import { PlayArrow, Pause, Translate, AutoAwesome } from '@mui/icons-material';
import { HLSVideoPlayer } from '../common/HLSVideoPlayer';
import { useStream } from '../../hooks/controller';
import { Host } from '../../types/common/Host_Types';
import { buildStreamUrl } from '../../utils/buildUrlUtils';

interface ArchiveMetadata {
  total_segments: number; // Deprecated (for backward compatibility)
  total_duration_seconds: number;
  window_hours: number;
  segments_per_window: number; // Now represents chunks per hour (6)
  manifests: Array<{
    name: string; // MP4 chunk path: "0/chunk_10min_0.mp4"
    window_index: number; // Hour (0-23)
    chunk_index: number; // Chunk within hour (0-5)
    start_segment: number; // Deprecated (for backward compatibility)
    end_segment: number; // Deprecated (for backward compatibility)
    start_time_seconds: number; // Absolute time from midnight
    end_time_seconds: number; // Absolute time from midnight
    duration_seconds: number; // Always 600 (10 minutes)
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
  shouldPause?: boolean; // Pause player to show last frame (during quality transition)
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
  shouldPause = false, // Default to not paused
  onPlayerReady
}) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [internalIsLiveMode] = useState(true); // Start in live mode
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [isPlaying, setIsPlaying] = useState(true); // Start playing automatically
  const [isTransitioning, setIsTransitioning] = useState(false); // Mode transition state
  const qualityTimestampRef = useRef<number>(Date.now()); // Track timestamp for quality changes
  
  // Archive metadata and manifest switching state
  const [archiveMetadata, setArchiveMetadata] = useState<ArchiveMetadata | null>(null);
  const [currentManifestIndex, setCurrentManifestIndex] = useState(0);
  const [globalCurrentTime, setGlobalCurrentTime] = useState(0); // Time across all manifests
  const [preloadedNextManifest, setPreloadedNextManifest] = useState(false);
  const [isDraggingSlider, setIsDraggingSlider] = useState(false);
  const [dragSliderValue, setDragSliderValue] = useState(0);
  const [isAtLiveEdge, setIsAtLiveEdge] = useState(true); // Start as true for live mode
  const liveEdgeTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  
  // Available hours tracking and caching
  const [availableHours, setAvailableHours] = useState<number[]>([]);
  const [isCheckingAvailability, setIsCheckingAvailability] = useState(false);
  
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
  const prevQuality = useRef(quality);
  
  // Update timestamp ref when quality changes
  useEffect(() => {
    if (prevQuality.current !== quality) {
      console.log(`[@EnhancedHLSPlayer] Quality changed: ${prevQuality.current} -> ${quality}`);
      qualityTimestampRef.current = Date.now();
      prevQuality.current = quality;
    }
  }, [quality]);

  // Generate cache key for available hours
  const getCacheKey = useCallback(() => {
    return `available-hours-${hostName}-${deviceId}`;
  }, [hostName, deviceId]);

  // Check if a specific hour has MP4 files available
  const checkHourAvailability = useCallback(async (hour: number, baseUrl: string): Promise<boolean> => {
    try {
      // Check if first chunk of the hour exists (chunk_10min_0.mp4)
      const testUrl = baseUrl.replace(/\/(segments\/)?(output|archive.*?)\.m3u8$/, `/segments/${hour}/chunk_10min_0.mp4`);
      
      const response = await fetch(testUrl, { method: 'HEAD' });
      return response.ok;
    } catch (error) {
      console.log(`[@EnhancedHLSPlayer] Hour ${hour} not available:`, error);
      return false;
    }
  }, []);

  // Check all hours for availability and cache results
  const checkAvailableHours = useCallback(async (baseUrl: string): Promise<number[]> => {
    const cacheKey = getCacheKey();
    
    // Try to get from cache first
    const cached = localStorage.getItem(cacheKey);
    if (cached) {
      try {
        const cachedHours = JSON.parse(cached);
        const cacheTime = localStorage.getItem(`${cacheKey}-time`);
        const isRecent = cacheTime && (Date.now() - parseInt(cacheTime)) < 5 * 60 * 1000; // 5 minutes
        
        if (isRecent && Array.isArray(cachedHours) && cachedHours.length > 0) {
          console.log(`[@EnhancedHLSPlayer] Using cached available hours:`, cachedHours);
          return cachedHours;
        }
      } catch (e) {
        console.warn('[@EnhancedHLSPlayer] Failed to parse cached hours:', e);
      }
    }

    setIsCheckingAvailability(true);
    console.log('[@EnhancedHLSPlayer] Checking available hours (0-23)...');
    
    const available: number[] = [];
    
    // Check hours 0-23 in parallel for faster loading
    const checks = Array.from({ length: 24 }, (_, hour) => 
      checkHourAvailability(hour, baseUrl).then(isAvailable => ({ hour, isAvailable }))
    );
    
    const results = await Promise.all(checks);
    
    for (const { hour, isAvailable } of results) {
      if (isAvailable) {
        available.push(hour);
      }
    }
    
    // Sort available hours
    available.sort((a, b) => a - b);
    
    console.log(`[@EnhancedHLSPlayer] Available hours found:`, available);
    
    // Cache results
    if (available.length > 0) {
      localStorage.setItem(cacheKey, JSON.stringify(available));
      localStorage.setItem(`${cacheKey}-time`, Date.now().toString());
    }
    
    setIsCheckingAvailability(false);
    return available;
  }, [getCacheKey, checkHourAvailability]);

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
        setAvailableHours([]);
        setIsCheckingAvailability(false);
      }
      
      // Small delay to allow cleanup
      setTimeout(() => {
        setIsTransitioning(false);
      }, 100);
      
      prevIsLiveMode.current = isLiveMode;
    }
  }, [isLiveMode]);

  // Fetch archive metadata when entering archive mode
  // PURE MP4 ARCHITECTURE: No legacy TS segments
  // Each hour has 6× 10-minute MP4 chunks (only for available hours)
  useEffect(() => {
    if (!isLiveMode && !archiveMetadata && !isTransitioning && !isCheckingAvailability) {
      const initializeArchiveMode = async () => {
        const baseUrl = providedStreamUrl || hookStreamUrl || buildStreamUrl(host, deviceId);
        
        // Check which hours have MP4 files available
        const available = await checkAvailableHours(baseUrl);
        setAvailableHours(available);
        
        if (available.length === 0) {
          console.warn('[@EnhancedHLSPlayer] No archive hours available');
          setIsCheckingAvailability(false);
          return;
        }
        
        // Generate metadata only for available hours
        const metadata: ArchiveMetadata = {
          total_segments: available.length * 6, // Available hours × 6 chunks each
          total_duration_seconds: available.length * 3600, // Available hours duration
          window_hours: 1, // 1 hour per folder
          segments_per_window: 6, // 6× 10-minute chunks per hour
          manifests: []
        };
        
        // Generate MP4 chunk references only for available hours
        for (const hour of available) {
          for (let chunk = 0; chunk < 6; chunk++) {
            const globalIndex = metadata.manifests.length; // Sequential index for available chunks
            metadata.manifests.push({
              name: `${hour}/chunk_10min_${chunk}.mp4`, // Direct MP4 chunk path
              window_index: hour, // Original hour (0-23)
              chunk_index: chunk, // Chunk within hour (0-5)
              start_segment: globalIndex, // Sequential global chunk index
              end_segment: globalIndex, // Same (one chunk)
              start_time_seconds: hour * 3600 + chunk * 600, // Absolute time from original hour
              end_time_seconds: hour * 3600 + (chunk + 1) * 600, // Absolute time from original hour
              duration_seconds: 600 // 10 minutes per chunk
            });
          }
        }
        
        console.log('[@EnhancedHLSPlayer] Generated MP4 archive metadata for available hours:', {
          available_hours: available,
          total_chunks: metadata.manifests.length,
          chunks_per_hour: metadata.segments_per_window,
          first_chunk: metadata.manifests[0]?.name,
          last_chunk: metadata.manifests[metadata.manifests.length - 1]?.name
        });
        setArchiveMetadata(metadata);
        
        // Start at first available chunk (first available hour, chunk 0)
        const firstHour = available[0];
        console.log(`[@EnhancedHLSPlayer] Starting at first available hour: ${firstHour}/chunk_10min_0.mp4`);
        setCurrentManifestIndex(0);
      };
      
      initializeArchiveMode();
    }
  }, [isLiveMode, archiveMetadata, isTransitioning, isCheckingAvailability, providedStreamUrl, hookStreamUrl, deviceId, checkAvailableHours]);

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
  // PURE MP4 ARCHITECTURE: Live uses HLS, Archive uses direct MP4 chunks
  const streamUrl = useMemo(() => {
    let url: string;
    
    // Live mode - use segments/output.m3u8 (HLS for low latency)
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
    // Archive mode - use direct MP4 chunks (no HLS manifests)
    else if (archiveMetadata && archiveMetadata.manifests.length > 0) {
      const currentManifest = archiveMetadata.manifests[currentManifestIndex];
      if (currentManifest) {
        const baseUrl = providedStreamUrl || hookStreamUrl || buildStreamUrl(host, deviceId);
        // Direct MP4 chunk path: segments/X/chunk_10min_Y.mp4
        const mp4ChunkPath = currentManifest.name; // Already formatted: "0/chunk_10min_0.mp4"
        url = baseUrl.replace(/\/(segments\/)?(output|archive.*?)\.m3u8$/, `/segments/${mp4ChunkPath}`);
        console.log(`[@EnhancedHLSPlayer] Using MP4 chunk (hour ${currentManifest.window_index}, chunk ${currentManifest.chunk_index}):`, url);
      } else {
        // Fallback when currentManifest doesn't exist - use first chunk
        const baseUrl = providedStreamUrl || hookStreamUrl || buildStreamUrl(host, deviceId);
        url = baseUrl.replace(/\/(segments\/)?(output|archive.*?)\.m3u8$/, '/segments/0/chunk_10min_0.mp4');
      }
    }
    // Fallback to first chunk while metadata is loading
    else {
      const baseUrl = providedStreamUrl || hookStreamUrl || buildStreamUrl(host, deviceId);
      url = baseUrl.replace(/\/(segments\/)?(output|archive.*?)\.m3u8$/, '/segments/0/chunk_10min_0.mp4');
    }
    
    // Append quality and timestamp parameters to force reload when quality changes (without unmounting component)
    // The URL itself doesn't change, but FFmpeg restarts with new quality settings on the backend
    const separator = url.includes('?') ? '&' : '?';
    url = `${url}${separator}q=${quality}&t=${qualityTimestampRef.current}`;
    
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
      
      // Check if we're at live edge in live mode - improved detection
      if (isLiveMode && video.duration && isFinite(video.duration)) {
        const latency = video.duration - video.currentTime;
        const atLiveEdge = latency < 3; // Within 3 seconds of live edge
        
        // Only update if state actually changed to prevent unnecessary re-renders
        if (atLiveEdge !== isAtLiveEdge) {
          setIsAtLiveEdge(atLiveEdge);
          console.log(`[@EnhancedHLSPlayer] Live edge status: ${atLiveEdge ? 'LIVE' : 'BEHIND'} (latency: ${latency.toFixed(2)}s)`);
        }
      } else if (isLiveMode && !isAtLiveEdge) {
        // Default to live edge when in live mode but no duration yet
        setIsAtLiveEdge(true);
      }
      
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
      
      // Cleanup live edge timeout
      if (liveEdgeTimeoutRef.current) {
        clearTimeout(liveEdgeTimeoutRef.current);
      }
    };
  }, [isLiveMode, archiveMetadata, currentManifestIndex, preloadedNextManifest, transcriptData]);

  // Handle mode changes and seeking
  useEffect(() => {
    const timer = setTimeout(() => {
      if (isLiveMode) {
        console.log('[@EnhancedHLSPlayer] Switching to live mode - ensuring live edge status');
        setIsAtLiveEdge(true); // Assume we're at live edge when switching to live
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

  // Handle slider drag (visual feedback only) - respects rolling buffer limits
  const handleSliderChange = useCallback((_event: Event | React.SyntheticEvent, newValue: number | number[]) => {
    const seekTime = Array.isArray(newValue) ? newValue[0] : newValue;
    if (!isFinite(seekTime) || seekTime < 0) return;
    
    // In live mode, allow scrubbing only within the actual buffered content (150 segments rolling)
    if (isLiveMode && videoRef.current) {
      const video = videoRef.current;
      const buffered = video.buffered;
      
      // Check if seek time is within any buffered range
      let canSeek = false;
      for (let i = 0; i < buffered.length; i++) {
        if (seekTime >= buffered.start(i) && seekTime <= buffered.end(i)) {
          canSeek = true;
          break;
        }
      }
      
      // Don't allow seeking beyond buffered content in live mode
      if (!canSeek) {
        console.log(`[@EnhancedHLSPlayer] Live mode: Cannot seek to ${seekTime.toFixed(1)}s (not in rolling buffer)`);
        return;
      }
    }
    
    setIsDraggingSlider(true);
    setDragSliderValue(seekTime);
  }, [isLiveMode]);

  // Timeline seeking - works for both live and archive modes
  const handleSeek = useCallback((_event: Event | React.SyntheticEvent, newValue: number | number[]) => {
    if (!videoRef.current) return;
    
    setIsDraggingSlider(false);
    
    const seekTime = Array.isArray(newValue) ? newValue[0] : newValue;
    if (!isFinite(seekTime) || seekTime < 0) return;
    
    const video = videoRef.current;
    const wasPlaying = !video.paused;
    
    // Live mode seeking - only within buffered content
    if (isLiveMode) {
      const buffered = video.buffered;
      let canSeek = false;
      
      // Check if seek time is within any buffered range
      for (let i = 0; i < buffered.length; i++) {
        if (seekTime >= buffered.start(i) && seekTime <= buffered.end(i)) {
          canSeek = true;
          break;
        }
      }
      
      if (canSeek) {
        console.log(`[@EnhancedHLSPlayer] Live mode seek to ${seekTime.toFixed(1)}s (within buffer)`);
        video.currentTime = seekTime;
        setIsDraggingSlider(false);
        
        // Set up auto-return to live edge after 10 seconds of inactivity
        // REMOVED: Let user stay in the past if they choose to
        
        return;
      } else {
        console.warn(`[@EnhancedHLSPlayer] Live mode: Cannot seek to ${seekTime.toFixed(1)}s (not buffered)`);
        setIsDraggingSlider(false);
        return;
      }
    }
    
    // Archive mode seeking - if using multi-manifest archive, find correct manifest and seek within it
    else if (archiveMetadata && archiveMetadata.manifests.length > 0) {
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
      {/* CSS keyframes for live indicator pulse animation */}
      <style>
        {`
          @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
          }
        `}
      </style>
      
      {/* Reuse HLSVideoPlayer for all streaming logic */}
      <Box sx={{ position: 'relative', height }}>
        {!isTransitioning && (!isCheckingAvailability && (isLiveMode || availableHours.length > 0)) ? (
          <HLSVideoPlayer
            key={`${isLiveMode ? 'live' : 'archive'}`} // Only remount on mode change, not quality change
            streamUrl={streamUrl}
            isStreamActive={true}
            videoElementRef={videoRef}
            muted={muted} // Use the muted prop from parent
            isArchiveMode={!isLiveMode} // Pass archive mode flag
            shouldPause={shouldPause} // Pause to show last frame during quality transition
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
            {isCheckingAvailability ? (
              <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
                <CircularProgress sx={{ color: 'white' }} />
                <Typography>Checking available archive hours...</Typography>
              </Box>
            ) : availableHours.length === 0 && !isLiveMode ? (
              <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
                <Typography>No archive hours available</Typography>
                <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.6)' }}>
                  Switch back to Live mode or check again later
                </Typography>
              </Box>
            ) : (
              <Typography>Switching mode...</Typography>
            )}
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

        {/* Timeline Overlay with integrated Play/Pause button (Live & Archive) */}
        {!isTransitioning && duration > 0 && (
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
              {/* Play/Pause Button - Only show in archive mode */}
              {!isLiveMode && (
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
              )}
              
              {/* Timeline Slider */}
              <Slider
                value={isDraggingSlider ? dragSliderValue : (archiveMetadata ? globalCurrentTime : currentTime)}
                min={(() => {
                  // In live mode, set min to start of buffered content (rolling buffer)
                  if (isLiveMode && videoRef.current) {
                    const buffered = videoRef.current.buffered;
                    return buffered.length > 0 ? buffered.start(0) : 0;
                  }
                  return 0;
                })()}
                max={(() => {
                  // In live mode, set max to end of buffered content (live edge)
                  if (isLiveMode && videoRef.current) {
                    const buffered = videoRef.current.buffered;
                    return buffered.length > 0 ? buffered.end(buffered.length - 1) : duration;
                  }
                  return archiveMetadata ? archiveMetadata.total_duration_seconds : duration;
                })()}
                onChange={handleSliderChange}
                onChangeCommitted={handleSeek}
                marks={!isLiveMode ? hourMarks : []} // Only show hour marks in archive mode
                sx={{ 
                  color: isLiveMode ? 'error.main' : 'primary.main', // Red for live, blue for archive
                  flex: 1,
                  '& .MuiSlider-thumb': {
                    width: 16,
                    height: 16,
                  },
                  '& .MuiSlider-track': {
                    // Different track styling for live vs archive
                    backgroundColor: isLiveMode ? 'error.main' : 'primary.main'
                  },
                  '& .MuiSlider-markLabel': {
                    fontSize: '0.7rem',
                    color: 'rgba(255,255,255,0.7)'
                  }
                }}
              />
            </Box>
            
            {/* Time display row */}
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', pl: 7 }}>  
              <Typography variant="caption" sx={{ color: 'white' }}>
                {formatTime(isDraggingSlider ? dragSliderValue : (archiveMetadata && archiveMetadata.manifests.length > 0 ? globalCurrentTime : currentTime))}
              </Typography>
              
              {/* Live indicator in live mode */}
              {isLiveMode && (
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                  <Box
                    sx={{
                      width: 8,
                      height: 8,
                      borderRadius: '50%',
                      backgroundColor: isAtLiveEdge ? 'error.main' : 'warning.main',
                      animation: isAtLiveEdge ? 'pulse 1.5s ease-in-out infinite' : 'none',
                    }}
                  />
                  <Typography 
                    variant="caption" 
                    sx={{ 
                      color: isAtLiveEdge ? 'error.main' : 'warning.main',
                      fontWeight: 600,
                      fontSize: '0.65rem'
                    }}
                  >
                    {isAtLiveEdge ? 'LIVE' : 'BEHIND'}
                  </Typography>
                </Box>
              )}
              
              {archiveMetadata && (
                <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.6)' }}>
                  Manifest {currentManifestIndex + 1}/{archiveMetadata.manifests.length}
                  {availableHours.length > 0 && ` • Hours: ${availableHours.join(',')}`}
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
