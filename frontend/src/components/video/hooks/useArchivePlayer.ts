import { useState, useCallback, useMemo, useEffect } from 'react';
import { ArchiveMetadata } from '../EnhancedHLSPlayer.types';
import { Host } from '../../../types/common/Host_Types';
import { buildStreamUrl } from '../../../utils/buildUrlUtils';

interface UseArchivePlayerProps {
  isLiveMode: boolean;
  providedStreamUrl?: string;
  hookStreamUrl?: string;
  host?: Host;
  deviceId: string;
  isTransitioning: boolean;
  videoRef: React.RefObject<HTMLVideoElement>;
  onVideoTimeUpdate?: (time: number) => void;
}

export const useArchivePlayer = ({
  isLiveMode,
  providedStreamUrl,
  hookStreamUrl,
  host,
  deviceId,
  isTransitioning,
  videoRef,
  onVideoTimeUpdate,
}: UseArchivePlayerProps) => {
  const [archiveMetadata, setArchiveMetadata] = useState<ArchiveMetadata | null>(null);
  const [currentManifestIndex, setCurrentManifestIndex] = useState(0);
  const [globalCurrentTime, setGlobalCurrentTime] = useState(0);
  const [preloadedNextManifest, setPreloadedNextManifest] = useState(false);
  const [isDraggingSlider, setIsDraggingSlider] = useState(false);
  const [dragSliderValue, setDragSliderValue] = useState(0);
  const [availableHours, setAvailableHours] = useState<number[]>([]);
  const [isCheckingAvailability, setIsCheckingAvailability] = useState(false);
  const [continuousStartTime, setContinuousStartTime] = useState<number>(0);
  const [continuousEndTime, setContinuousEndTime] = useState<number>(0);
  const [hasAttemptedLoad, setHasAttemptedLoad] = useState(false);

  const loadArchiveManifest = useCallback(async (baseUrl: string): Promise<ArchiveMetadata | null> => {
    setIsCheckingAvailability(true);
    
    try {
      const manifestUrl = baseUrl.replace(/\/(segments\/)?(output|archive.*?)\.m3u8$/, '/segments/archive_manifest.json');
      const response = await fetch(manifestUrl);
      
      if (!response.ok) {
        console.warn('[@EnhancedHLSPlayer] No archive manifest found');
        return null;
      }
      
      const manifest = await response.json();
      console.log(`[@EnhancedHLSPlayer] Loaded manifest: ${manifest.total_chunks} chunks across ${manifest.available_hours.length} hours`);
      console.log(`[@EnhancedHLSPlayer] Continuous range: ${manifest.continuous_from ? `hour ${manifest.continuous_from.hour}, chunk ${manifest.continuous_from.chunk_index}` : 'unknown'} to ${manifest.chunks.length > 0 ? `hour ${manifest.chunks[manifest.chunks.length - 1].hour}, chunk ${manifest.chunks[manifest.chunks.length - 1].chunk_index}` : 'unknown'}`);
      
      setAvailableHours(manifest.available_hours);
      
      // Sort chunks by time (oldest first) for proper playback order
      const sortedChunks = [...manifest.chunks].sort((a: any, b: any) => {
        const aTime = a.hour * 3600 + a.chunk_index * 600;
        const bTime = b.hour * 3600 + b.chunk_index * 600;
        return aTime - bTime;
      });
      
      const metadata: ArchiveMetadata = {
        total_segments: manifest.total_chunks,
        total_duration_seconds: manifest.total_chunks * 600,
        window_hours: 1,
        segments_per_window: 6,
        manifests: sortedChunks.map((chunk: any, index: number) => ({
          name: `${chunk.hour}/chunk_10min_${chunk.chunk_index}.mp4`,
          window_index: chunk.hour,
          chunk_index: chunk.chunk_index,
          start_segment: index,
          end_segment: index,
          start_time_seconds: chunk.hour * 3600 + chunk.chunk_index * 600,
          end_time_seconds: chunk.hour * 3600 + (chunk.chunk_index + 1) * 600,
          duration_seconds: 600
        }))
      };
      
      // Calculate continuous time range
      if (metadata.manifests.length > 0) {
        const firstChunk = metadata.manifests[0];
        const lastChunk = metadata.manifests[metadata.manifests.length - 1];
        setContinuousStartTime(firstChunk.start_time_seconds);
        setContinuousEndTime(lastChunk.end_time_seconds);
      }
      
      return metadata;
    } catch (error) {
      console.error('[@EnhancedHLSPlayer] Failed to load archive manifest:', error);
      return null;
    } finally {
      setIsCheckingAvailability(false);
    }
  }, []);

  useEffect(() => {
    if (!isLiveMode && !archiveMetadata && !isTransitioning && !isCheckingAvailability && !hasAttemptedLoad) {
      const initializeArchiveMode = async () => {
        const baseUrl = providedStreamUrl || hookStreamUrl || buildStreamUrl(host, deviceId);
        const metadata = await loadArchiveManifest(baseUrl);
        
        setHasAttemptedLoad(true);
        
        if (!metadata || metadata.manifests.length === 0) {
          console.warn('[@EnhancedHLSPlayer] No archive data available');
          return;
        }
        
        // Start from the NEWEST available chunk (last in sorted array, closest to now)
        const newestIndex = metadata.manifests.length - 1;
        const newestChunk = metadata.manifests[newestIndex];
        
        // Position at the start of the newest chunk (which might be the current building chunk)
        const now = new Date();
        const currentHour = now.getHours();
        const currentChunkIndex = Math.floor(now.getMinutes() / 10);
        const isCurrentBuildingChunk = newestChunk.window_index === currentHour && newestChunk.chunk_index === currentChunkIndex;
        
        console.log(`[@EnhancedHLSPlayer] Archive initialized: ${metadata.manifests.length} chunks`);
        console.log(`[@EnhancedHLSPlayer] Starting from NEWEST chunk: hour ${newestChunk.window_index}, chunk ${newestChunk.chunk_index}${isCurrentBuildingChunk ? ' (building)' : ''}`);
        
        setArchiveMetadata(metadata);
        setCurrentManifestIndex(newestIndex);
        setGlobalCurrentTime(newestChunk.start_time_seconds);
      };
      
      initializeArchiveMode();
    }
  }, [isLiveMode, archiveMetadata, isTransitioning, isCheckingAvailability, hasAttemptedLoad, providedStreamUrl, hookStreamUrl, deviceId, host, loadArchiveManifest]);

  const hourMarks = useMemo(() => {
    if (!archiveMetadata) return [];
    
    const marks = [];
    const now = new Date();
    const currentHour = now.getHours();
    const currentMinute = now.getMinutes();
    const currentSecond = now.getSeconds();
    
    // Generate marks for the last 24 hours in INVERTED order (now at right)
    // Timeline goes from 24h ago (left, 0 seconds) to now (right, 86400 seconds)
    for (let hoursAgo = 0; hoursAgo <= 24; hoursAgo++) {
      // Calculate the actual hour for this position
      const actualHour = (currentHour - hoursAgo + 24) % 24;
      
      // Position in seconds: hoursAgo=0 (now) = 86400s, hoursAgo=24 = 0s
      const timeValue = (24 - hoursAgo) * 3600;
      
      // Check if this hour is available
      const isAvailable = availableHours.includes(actualHour);
      
      // Generate label
      let label = '';
      if (hoursAgo === 0) {
        label = 'Now';
      } else if (hoursAgo === 24) {
        label = '24h ago';
      } else {
        // Show hour with indicator if it's yesterday
        const hourLabel = `${actualHour}h`;
        if (hoursAgo > currentHour) {
          // This is yesterday
          label = `${hourLabel}`;
        } else {
          label = hourLabel;
        }
      }
      
      marks.push({
        value: timeValue,
        label: label,
        style: isAvailable ? {} : {
          color: 'rgba(255, 255, 255, 0.3)',
          opacity: 0.5
        }
      });
    }
    
    // Add current hour start mark ONLY if we're past the hour AND it's not already in the marks
    // This ensures "16h" shows before "Now" when it's 16:30, but avoids duplicates
    if (currentMinute > 0 || currentSecond > 0) {
      const currentHourStartPosition = 86400 - (currentMinute * 60 + currentSecond);
      
      // Check if this position already has a mark (avoid duplicates)
      const hasExistingMark = marks.some(mark => Math.abs(mark.value - currentHourStartPosition) < 60);
      
      if (!hasExistingMark) {
        const isAvailable = availableHours.includes(currentHour);
        marks.push({
          value: currentHourStartPosition,
          label: `${currentHour}h`,
          style: isAvailable ? {} : {
            color: 'rgba(255, 255, 255, 0.3)',
            opacity: 0.5
          }
        });
      }
    }
    
    // Sort marks by value for proper display
    marks.sort((a, b) => a.value - b.value);
    
    return marks;
  }, [archiveMetadata, availableHours]);

  const handleVideoError = useCallback(() => {
    if (!videoRef.current || isLiveMode) return;
    
    const video = videoRef.current;
    const error = video.error;
    
    if (error && archiveMetadata && archiveMetadata.manifests.length > 0) {
      console.warn(`[@EnhancedHLSPlayer] Video error (${error.code}): ${error.message}`);
      
      const nextIndex = currentManifestIndex + 1;
      if (nextIndex < archiveMetadata.manifests.length) {
        console.log(`[@EnhancedHLSPlayer] Skipping to next available chunk (${nextIndex + 1}/${archiveMetadata.manifests.length})`);
        setCurrentManifestIndex(nextIndex);
        setPreloadedNextManifest(false);
      } else {
        console.warn('[@EnhancedHLSPlayer] No more chunks available');
      }
    }
  }, [isLiveMode, archiveMetadata, currentManifestIndex, videoRef]);

  const handleSliderChange = useCallback((_event: Event | React.SyntheticEvent, newValue: number | number[]) => {
    const sliderValue = Array.isArray(newValue) ? newValue[0] : newValue;
    if (!isFinite(sliderValue) || sliderValue < 0) return;
    
    // Store the inverted slider value for display (timeline shows inverted positions)
    setIsDraggingSlider(true);
    setDragSliderValue(sliderValue);
  }, []);

  const handleSeek = useCallback((_event: Event | React.SyntheticEvent, newValue: number | number[]) => {
    if (!videoRef.current) return;
    
    setIsDraggingSlider(false);
    const video = videoRef.current;
    // newValue is already the actual time (converted from inverted in TimelineOverlay)
    const seekTime = Array.isArray(newValue) ? newValue[0] : newValue;
    if (!isFinite(seekTime) || seekTime < 0) return;
    
    const wasPlaying = !video.paused;
    
    if (archiveMetadata && archiveMetadata.manifests.length > 0) {
      let targetManifestIndex = -1;
      let targetLocalTime = 0;
      
      // Find the manifest that contains this seek time
      for (let i = 0; i < archiveMetadata.manifests.length; i++) {
        const manifest = archiveMetadata.manifests[i];
        const isAtEnd = seekTime >= manifest.end_time_seconds && i === archiveMetadata.manifests.length - 1;
        const isInRange = seekTime >= manifest.start_time_seconds && seekTime < manifest.end_time_seconds;
        
        if (isInRange || isAtEnd) {
          targetManifestIndex = i;
          targetLocalTime = seekTime - manifest.start_time_seconds;
          
          const manifestDuration = manifest.duration_seconds;
          targetLocalTime = Math.min(targetLocalTime, manifestDuration - 0.1);
          
          console.log(`[@EnhancedHLSPlayer] User seek: global ${seekTime.toFixed(1)}s -> manifest ${manifest.window_index} at ${targetLocalTime.toFixed(1)}s`);
          break;
        }
      }
      
      if (targetManifestIndex === -1) {
        console.warn(`[@EnhancedHLSPlayer] Seek time ${seekTime}s is in a gap (no chunk available) - finding nearest available chunk`);
        
        // Find nearest available chunk (forward first, then backward)
        let nearestIndex = -1;
        let minDistance = Infinity;
        
        for (let i = 0; i < archiveMetadata.manifests.length; i++) {
          const manifest = archiveMetadata.manifests[i];
          const distance = Math.abs(seekTime - manifest.start_time_seconds);
          if (distance < minDistance) {
            minDistance = distance;
            nearestIndex = i;
          }
        }
        
        if (nearestIndex !== -1) {
          targetManifestIndex = nearestIndex;
          const nearestManifest = archiveMetadata.manifests[nearestIndex];
          targetLocalTime = 0; // Start of nearest chunk
          console.log(`[@EnhancedHLSPlayer] Jumping to nearest chunk: manifest ${nearestManifest.window_index}`);
        } else {
          console.error('[@EnhancedHLSPlayer] No available chunks found');
          return;
        }
      }
      
      if (targetManifestIndex !== currentManifestIndex) {
        console.log(`[@EnhancedHLSPlayer] Switching from manifest ${currentManifestIndex + 1} to ${targetManifestIndex + 1}`);
        
        video.pause();
        
        setCurrentManifestIndex(targetManifestIndex);
        setPreloadedNextManifest(false);
        
        setTimeout(() => {
          if (videoRef.current) {
            videoRef.current.currentTime = targetLocalTime;
            
            if (wasPlaying) {
              videoRef.current.play().catch(err => {
                console.warn('[@EnhancedHLSPlayer] Failed to resume playback after manifest switch:', err);
              });
            }
          }
        }, 1000);
      } else {
        video.currentTime = targetLocalTime;
      }
    } else {
      video.currentTime = seekTime;
    }
  }, [archiveMetadata, currentManifestIndex, videoRef]);

  const updateTimeTracking = useCallback((video: HTMLVideoElement) => {
    if (archiveMetadata && archiveMetadata.manifests.length > 0) {
      const currentManifest = archiveMetadata.manifests[currentManifestIndex];
      if (currentManifest) {
        const globalTime = currentManifest.start_time_seconds + video.currentTime;
        setGlobalCurrentTime(globalTime);
        
        if (onVideoTimeUpdate) {
          // Pass global clock time (seconds in day) to consumers for consistent archive lookups
          onVideoTimeUpdate(globalTime);
        }
        
        const progressRatio = video.currentTime / video.duration;
        if (progressRatio > 0.9 && !preloadedNextManifest) {
          const nextIndex = currentManifestIndex + 1;
          if (nextIndex < archiveMetadata.manifests.length) {
            console.log(`[@EnhancedHLSPlayer] Pre-loading next manifest (${nextIndex + 1}/${archiveMetadata.manifests.length})`);
            setPreloadedNextManifest(true);
          }
        }
        
        if (video.currentTime >= video.duration - 1) {
          const nextIndex = currentManifestIndex + 1;
          if (nextIndex < archiveMetadata.manifests.length) {
            console.log(`[@EnhancedHLSPlayer] Switching to manifest ${nextIndex + 1}`);
            setCurrentManifestIndex(nextIndex);
            setPreloadedNextManifest(false);
          }
        }
      }
    } else {
      setGlobalCurrentTime(video.currentTime);
    }
  }, [archiveMetadata, currentManifestIndex, preloadedNextManifest, onVideoTimeUpdate]);

  const clearArchiveData = useCallback(() => {
    console.log('[@EnhancedHLSPlayer] Clearing archive metadata (switching to live)');
    setArchiveMetadata(null);
    setCurrentManifestIndex(0);
    setAvailableHours([]);
    setIsCheckingAvailability(false);
    setContinuousStartTime(0);
    setContinuousEndTime(0);
    setHasAttemptedLoad(false);
  }, []);

  return useMemo(() => ({
    archiveMetadata,
    currentManifestIndex,
    globalCurrentTime,
    preloadedNextManifest,
    isDraggingSlider,
    dragSliderValue,
    availableHours,
    isCheckingAvailability,
    continuousStartTime,
    continuousEndTime,
    hourMarks,
    handleVideoError,
    handleSliderChange,
    handleSeek,
    updateTimeTracking,
    clearArchiveData,
    setCurrentManifestIndex,
    setPreloadedNextManifest,
  }), [
    archiveMetadata,
    currentManifestIndex,
    globalCurrentTime,
    preloadedNextManifest,
    isDraggingSlider,
    dragSliderValue,
    availableHours,
    isCheckingAvailability,
    continuousStartTime,
    continuousEndTime,
    hourMarks,
    handleVideoError,
    handleSliderChange,
    handleSeek,
    updateTimeTracking,
    clearArchiveData,
  ]);
};
