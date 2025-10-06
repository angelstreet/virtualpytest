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

  const getCacheKey = useCallback(() => {
    return `available-hours-${host?.host_name || 'unknown'}-${deviceId}`;
  }, [host?.host_name, deviceId]);

  const checkHourAvailability = useCallback(async (hour: number, baseUrl: string): Promise<boolean> => {
    try {
      const testUrl = baseUrl.replace(/\/(segments\/)?(output|archive.*?)\.m3u8$/, `/segments/${hour}/chunk_10min_0.mp4`);
      const response = await fetch(testUrl, { method: 'HEAD' });
      return response.ok;
    } catch (error) {
      console.log(`[@EnhancedHLSPlayer] Hour ${hour} not available:`, error);
      return false;
    }
  }, []);

  const checkAvailableHours = useCallback(async (baseUrl: string): Promise<number[]> => {
    const cacheKey = getCacheKey();
    
    const cached = localStorage.getItem(cacheKey);
    if (cached) {
      try {
        const cachedHours = JSON.parse(cached);
        const cacheTime = localStorage.getItem(`${cacheKey}-time`);
        const isRecent = cacheTime && (Date.now() - parseInt(cacheTime)) < 5 * 60 * 1000;
        
        if (isRecent && Array.isArray(cachedHours) && cachedHours.length > 0) {
          console.log(`[@EnhancedHLSPlayer] Using cached available hours:`, cachedHours);
          return cachedHours;
        }
      } catch (e) {
        console.warn('[@EnhancedHLSPlayer] Failed to parse cached hours:', e);
      }
    }

    setIsCheckingAvailability(true);
    console.log('[@EnhancedHLSPlayer] Checking available hours (all 24 hours)...');
    
    const available: number[] = [];
    const currentHour = new Date().getHours();
    
    const hoursToCheck = [];
    for (let i = 0; i < 24; i++) {
      const hourToCheck = (currentHour - i + 24) % 24;
      hoursToCheck.push(hourToCheck);
    }
    
    const checks = hoursToCheck.map(hour => 
      checkHourAvailability(hour, baseUrl).then(isAvailable => ({ hour, isAvailable }))
    );
    
    const results = await Promise.all(checks);
    
    for (const { hour, isAvailable } of results) {
      if (isAvailable) {
        available.push(hour);
      }
    }
    
    available.sort((a, b) => a - b);
    
    console.log(`[@EnhancedHLSPlayer] Available hours found (24h rolling):`, available);
    
    if (available.length > 0) {
      localStorage.setItem(cacheKey, JSON.stringify(available));
      localStorage.setItem(`${cacheKey}-time`, Date.now().toString());
    }
    
    setIsCheckingAvailability(false);
    return available;
  }, [getCacheKey, checkHourAvailability]);

  useEffect(() => {
    if (!isLiveMode && !archiveMetadata && !isTransitioning && !isCheckingAvailability) {
      const initializeArchiveMode = async () => {
        const baseUrl = providedStreamUrl || hookStreamUrl || buildStreamUrl(host, deviceId);
        
        const available = await checkAvailableHours(baseUrl);
        setAvailableHours(available);
        
        if (available.length === 0) {
          console.warn('[@EnhancedHLSPlayer] No archive hours available');
          setIsCheckingAvailability(false);
          return;
        }
        
        console.log('[@EnhancedHLSPlayer] Checking chunk-level availability...');
        const chunkChecks: Promise<{ path: string; exists: boolean }>[] = [];
        
        for (const hour of available) {
          for (let chunk = 0; chunk < 6; chunk++) {
            const chunkPath = `${hour}/chunk_10min_${chunk}.mp4`;
            const testUrl = baseUrl.replace(/\/(segments\/)?(output|archive.*?)\.m3u8$/, `/segments/${chunkPath}`);
            
            chunkChecks.push(
              fetch(testUrl, { method: 'HEAD' })
                .then(res => ({ path: chunkPath, exists: res.ok }))
                .catch(() => ({ path: chunkPath, exists: false }))
            );
          }
        }
        
        const chunkResults = await Promise.all(chunkChecks);
        const availableChunkSet = new Set<string>();
        
        for (const { path, exists } of chunkResults) {
          if (exists) {
            availableChunkSet.add(path);
          }
        }
        
        console.log(`[@EnhancedHLSPlayer] Available chunks: ${availableChunkSet.size}/${chunkChecks.length}`, Array.from(availableChunkSet));
        
        const metadata: ArchiveMetadata = {
          total_segments: availableChunkSet.size,
          total_duration_seconds: availableChunkSet.size * 600,
          window_hours: 1,
          segments_per_window: 6,
          manifests: []
        };
        
        let globalIndex = 0;
        for (const hour of available) {
          for (let chunk = 0; chunk < 6; chunk++) {
            const chunkPath = `${hour}/chunk_10min_${chunk}.mp4`;
            
            if (availableChunkSet.has(chunkPath)) {
              metadata.manifests.push({
                name: chunkPath,
                window_index: hour,
                chunk_index: chunk,
                start_segment: globalIndex,
                end_segment: globalIndex,
                start_time_seconds: hour * 3600 + chunk * 600,
                end_time_seconds: hour * 3600 + (chunk + 1) * 600,
                duration_seconds: 600
              });
              globalIndex++;
            }
          }
        }
        
        console.log('[@EnhancedHLSPlayer] Generated MP4 archive metadata (available chunks only):', {
          available_hours: available,
          available_chunks: metadata.manifests.length,
          first_chunk: metadata.manifests[0]?.name,
          last_chunk: metadata.manifests[metadata.manifests.length - 1]?.name
        });
        setArchiveMetadata(metadata);
        
        if (metadata.manifests.length > 0) {
          console.log(`[@EnhancedHLSPlayer] Starting at first available chunk: ${metadata.manifests[0].name}`);
          setCurrentManifestIndex(0);
        }
      };
      
      initializeArchiveMode();
    }
  }, [isLiveMode, archiveMetadata, isTransitioning, isCheckingAvailability, providedStreamUrl, hookStreamUrl, deviceId, checkAvailableHours, host]);

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
    
    if (availableHours.length > 0) {
      const seekHour = Math.floor(seekTime / 3600);
      if (!availableHours.includes(seekHour)) {
        console.log(`[@EnhancedHLSPlayer] Cannot drag to hour ${seekHour} - not available`);
        return;
      }
    }
    
    setIsDraggingSlider(true);
    setDragSliderValue(seekTime);
  }, [availableHours]);

  const handleSeek = useCallback((_event: Event | React.SyntheticEvent, newValue: number | number[]) => {
    if (!videoRef.current) return;
    
    setIsDraggingSlider(false);
    const video = videoRef.current;
    const seekTime = Array.isArray(newValue) ? newValue[0] : newValue;
    if (!isFinite(seekTime) || seekTime < 0) return;
    
    if (availableHours.length > 0) {
      const seekHour = Math.floor(seekTime / 3600);
      if (!availableHours.includes(seekHour)) {
        console.warn(`[@EnhancedHLSPlayer] Cannot seek to hour ${seekHour} - not available. Available hours: ${availableHours.join(',')}`);
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
  }, [archiveMetadata, currentManifestIndex, availableHours, videoRef]);

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
  }, []);

  return {
    archiveMetadata,
    currentManifestIndex,
    globalCurrentTime,
    preloadedNextManifest,
    isDraggingSlider,
    dragSliderValue,
    availableHours,
    isCheckingAvailability,
    hourMarks,
    handleVideoError,
    handleSliderChange,
    handleSeek,
    updateTimeTracking,
    clearArchiveData,
    setCurrentManifestIndex,
    setPreloadedNextManifest,
  };
};
