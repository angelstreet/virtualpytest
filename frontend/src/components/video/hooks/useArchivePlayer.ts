import { useState, useRef, useCallback, useMemo, useEffect } from 'react';
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
      
      const metadata: ArchiveMetadata = {
        total_segments: manifest.total_chunks,
        total_duration_seconds: manifest.total_chunks * 600,
        window_hours: 1,
        segments_per_window: 6,
        manifests: manifest.chunks.map((chunk: any, index: number) => ({
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
        
        console.log(`[@EnhancedHLSPlayer] Archive initialized: ${metadata.manifests.length} chunks, starting at ${metadata.manifests[0].name}`);
        setArchiveMetadata(metadata);
        setCurrentManifestIndex(0);
      };
      
      initializeArchiveMode();
    }
  }, [isLiveMode, archiveMetadata, isTransitioning, isCheckingAvailability, hasAttemptedLoad, providedStreamUrl, hookStreamUrl, deviceId, host, loadArchiveManifest]);

  const hourMarks = useMemo(() => {
    if (!archiveMetadata) return [];
    
    const marks = [];
    const allHoursSet = new Set(availableHours);
    
    if (availableHours.length > 0) {
      const minHour = Math.min(...availableHours);
      const maxHour = Math.max(...availableHours);
      
      for (let hour = minHour; hour <= maxHour; hour++) {
        const isAvailable = allHoursSet.has(hour);
        marks.push({
          value: hour * 3600,
          label: `${hour}h`,
          style: isAvailable ? {} : {
            color: 'rgba(255, 255, 255, 0.3)',
            opacity: 0.5
          }
        });
      }
    }
    
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
    const seekTime = Array.isArray(newValue) ? newValue[0] : newValue;
    if (!isFinite(seekTime) || seekTime < 0) return;
    
    // Restrict to continuous time range
    if (continuousStartTime > 0 && continuousEndTime > 0) {
      if (seekTime < continuousStartTime || seekTime > continuousEndTime) {
        console.log(`[@EnhancedHLSPlayer] Cannot drag to ${seekTime}s - outside continuous range (${continuousStartTime}s - ${continuousEndTime}s)`);
        return;
      }
    }
    
    setIsDraggingSlider(true);
    setDragSliderValue(seekTime);
  }, [continuousStartTime, continuousEndTime]);

  const handleSeek = useCallback((_event: Event | React.SyntheticEvent, newValue: number | number[]) => {
    if (!videoRef.current) return;
    
    setIsDraggingSlider(false);
    const video = videoRef.current;
    const seekTime = Array.isArray(newValue) ? newValue[0] : newValue;
    if (!isFinite(seekTime) || seekTime < 0) return;
    
    // Restrict to continuous time range
    if (continuousStartTime > 0 && continuousEndTime > 0) {
      if (seekTime < continuousStartTime || seekTime > continuousEndTime) {
        console.warn(`[@EnhancedHLSPlayer] Cannot seek to ${seekTime}s - outside continuous range (${continuousStartTime}s - ${continuousEndTime}s)`);
        return;
      }
    }
    
    const wasPlaying = !video.paused;
    
    if (archiveMetadata && archiveMetadata.manifests.length > 0) {
      let targetManifestIndex = -1;
      let targetLocalTime = 0;
      
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
        console.warn(`[@EnhancedHLSPlayer] Seek time ${seekTime}s not found in any manifest`);
        return;
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
  }, [archiveMetadata, currentManifestIndex, continuousStartTime, continuousEndTime, videoRef]);

  const updateTimeTracking = useCallback((video: HTMLVideoElement) => {
    if (archiveMetadata && archiveMetadata.manifests.length > 0) {
      const currentManifest = archiveMetadata.manifests[currentManifestIndex];
      if (currentManifest) {
        const globalTime = currentManifest.start_time_seconds + video.currentTime;
        setGlobalCurrentTime(globalTime);
        
        if (onVideoTimeUpdate) {
          onVideoTimeUpdate(video.currentTime);
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
