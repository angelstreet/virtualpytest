import { useState, useEffect, useCallback, useMemo } from 'react';

import {
  MonitoringAnalysis,
  SubtitleAnalysis,
  SubtitleTrendAnalysis,
  LanguageMenuAnalysis,
} from '../../types/pages/Monitoring_Types';

import { buildServerUrl, buildCaptureUrl } from '../../utils/buildUrlUtils';
interface FrameRef {
  timestamp: string;
  imageUrl: string;
  jsonUrl: string;
  analysis?: MonitoringAnalysis | null;
  subtitleAnalysis?: SubtitleAnalysis | null;
  languageMenuAnalysis?: LanguageMenuAnalysis | null;
  aiDescription?: string | null;
}

interface QueuedFrame {
  timestamp: string;
  imageUrl: string;
  jsonUrl: string;
  sequence: string;
  // AI analysis will be added asynchronously after queuing
  analysis?: MonitoringAnalysis | null;
  subtitleAnalysis?: SubtitleAnalysis | null;
  languageMenuAnalysis?: LanguageMenuAnalysis | null;
  aiDescription?: string | null;
}

interface ErrorTrendData {
  blackscreenConsecutive: number;
  freezeConsecutive: number;
  audioLossConsecutive: number;
  macroblocksConsecutive: number;
  hasWarning: boolean;
  hasError: boolean;
}

interface UseMonitoringReturn {
  // Frame management
  frames: FrameRef[];
  currentIndex: number;
  currentFrameUrl: string;
  selectedFrameAnalysis: MonitoringAnalysis | null;
  isHistoricalFrameLoaded: boolean;
  isInitialLoading: boolean;

  // Playback controls
  isPlaying: boolean;
  userSelectedFrame: boolean;

  // Actions
  handlePlayPause: () => void;
  handleSliderChange: (event: Event, newValue: number | number[]) => void;
  handleHistoricalFrameLoad: () => void;


  // Subtitle trend analysis
  subtitleTrendAnalysis: SubtitleTrendAnalysis | null;

  // Error trend analysis
  errorTrendData: ErrorTrendData | null;

  // Current analysis data for overlay display
  currentSubtitleAnalysis: SubtitleAnalysis | null;
  currentLanguageMenuAnalysis: LanguageMenuAnalysis | null;
  currentAIDescription: string | null;

  // Current frame timestamp for analysis tracking
  currentFrameTimestamp: string | null;
}

interface UseMonitoringProps {
  host: any; // Host object for API requests
  device: any; // Device object for API requests
  baseUrlPattern?: string; // Base URL pattern from useRec - optional
}

export const useMonitoring = ({
  host,
  device,
  baseUrlPattern,
}: UseMonitoringProps): UseMonitoringReturn => {
  const [frames, setFrames] = useState<FrameRef[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(true);
  const [, setCurrentImageUrl] = useState<string>('');
  const [userSelectedFrame, setUserSelectedFrame] = useState(false);
  const [selectedFrameAnalysis, setSelectedFrameAnalysis] = useState<MonitoringAnalysis | null>(
    null,
  );
  const [isHistoricalFrameLoaded, setIsHistoricalFrameLoaded] = useState(false);
  const [isInitialLoading, setIsInitialLoading] = useState(true);
  const [, setDisplayQueue] = useState<QueuedFrame[]>([]);
  const [lastProcessedSequence, setLastProcessedSequence] = useState<string>('');
  const [initialFramesLoaded, setInitialFramesLoaded] = useState(0);

  // Initial loading: Wait for 3 frames with JSON only (fast display)
  useEffect(() => {
    if (initialFramesLoaded >= 3) {
      console.log('[useMonitoring] 🎯 Initial buffer complete: 3 frames loaded, starting display');
      setIsInitialLoading(false);
    }
  }, [initialFramesLoaded]);



  // Fast JSON loading for immediate display
  const loadFrameJsonAsync = useCallback(async (queuedFrame: QueuedFrame): Promise<void> => {
    const startTime = performance.now();
    console.log('[useMonitoring] ⚡ Fast JSON loading for:', queuedFrame.imageUrl);
    
    // Load JSON analysis only (fast) - handle 404s gracefully
    let jsonAnalysis: any = null;
    try {
      const jsonResponse = await fetch(queuedFrame.jsonUrl);
      if (jsonResponse.ok) {
        jsonAnalysis = await jsonResponse.json();
      } else if (jsonResponse.status === 404) {
        console.log('[useMonitoring] JSON not found (404) - will display image without analysis');
        jsonAnalysis = null; // Explicitly set to null for 404
      } else {
        console.warn('[useMonitoring] JSON fetch failed:', jsonResponse.status, jsonResponse.statusText);
      }
    } catch (error) {
      console.warn('[useMonitoring] Failed to load JSON:', error);
    }
    
    const totalTime = performance.now() - startTime;
    console.log(`[useMonitoring] ✅ JSON loaded in ${totalTime.toFixed(0)}ms for:`, queuedFrame.imageUrl);

    // Update frame with JSON only (ready for display)
    queuedFrame.analysis = jsonAnalysis;
    queuedFrame.subtitleAnalysis = null; // Will be filled by background AI
    queuedFrame.languageMenuAnalysis = null; // Removed for performance
    queuedFrame.aiDescription = null; // Will be filled by background AI

    // Count as complete for initial buffer (frame ready for display regardless of JSON)
    if (initialFramesLoaded < 3) {
      setInitialFramesLoaded(count => {
        const newCount = count + 1;
        console.log(`[useMonitoring] 📊 Initial frame ${newCount}/3 ready for display (JSON: ${jsonAnalysis ? 'loaded' : 'missing'})`);
        return newCount;
      });
    }
  }, [initialFramesLoaded]);

  // Background AI analysis for caching (runs separately)
  const analyzeFrameAIAsync = useCallback(async (queuedFrame: QueuedFrame): Promise<void> => {
    const startTime = performance.now();
    console.log('[useMonitoring] 🤖 Background AI analysis for:', queuedFrame.imageUrl);

    // Combined AI analysis in background (single call for both subtitle + description)
    const combinedResult = await fetch(buildServerUrl('/server/verification/video/analyzeImageComplete'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        host_name: host.host_name,
        device_id: device?.device_id,
        image_source_url: queuedFrame.imageUrl,
        extract_text: true,
        include_description: true,
      }),
    }).then(r => r.ok ? r.json() : null).catch(() => null);

    // Process combined AI results
    let subtitleAnalysis: any = null;
    let aiDescription: any = null;
    
    if (combinedResult?.success && combinedResult.subtitle_analysis) {
      const data = combinedResult.subtitle_analysis;
      subtitleAnalysis = {
        subtitles_detected: data.subtitles_detected || false,
        combined_extracted_text: data.combined_extracted_text || '',
        detected_language: data.detected_language !== 'unknown' ? data.detected_language : undefined,
        confidence: data.confidence || (data.subtitles_detected ? 0.9 : 0.1),
        detection_message: data.detection_message || '',
      };
    }

    if (combinedResult?.success && combinedResult.description_analysis?.success) {
      aiDescription = combinedResult.description_analysis.response;
    }

    const totalTime = performance.now() - startTime;
    console.log(`[useMonitoring] ✅ Background AI completed in ${totalTime.toFixed(0)}ms for:`, queuedFrame.imageUrl);

    // Update frame with AI results (cached for when user revisits)
    queuedFrame.subtitleAnalysis = subtitleAnalysis;
    queuedFrame.aiDescription = aiDescription;

    // Update both queue and frames array with cached AI results
    setDisplayQueue(prev => prev.map(frame => 
      frame.imageUrl === queuedFrame.imageUrl ? { ...frame, subtitleAnalysis, aiDescription } : frame
    ));
    setFrames(prev => prev.map(frame => 
      frame.imageUrl === queuedFrame.imageUrl ? { ...frame, subtitleAnalysis, aiDescription } : frame
    ));
  }, [host, device?.device_id]);

  // State for autonomous base URL pattern (discovered via takeScreenshot API)
  const [autonomousBaseUrlPattern, setAutonomousBaseUrlPattern] = useState<string | null>(null);
  const [isInitializingBaseUrl, setIsInitializingBaseUrl] = useState(false);

  // Initialize base URL pattern autonomously using takeScreenshot API (like the original useRec implementation)
  const initializeAutonomousBaseUrl = useCallback(async (): Promise<void> => {
    if (autonomousBaseUrlPattern || isInitializingBaseUrl) {
      return; // Already have pattern or currently initializing
    }

    setIsInitializingBaseUrl(true);
    try {
      console.log('[useMonitoring] Initializing autonomous base URL pattern...');
      const response = await fetch(buildServerUrl('/server/av/takeScreenshot'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          host_name: host.host_name,
          device_id: device?.device_id || 'device1',
        }),
      });

      if (response.ok) {
        const result = await response.json();
        if (result.success && result.screenshot_url) {
          const basePattern = buildCaptureUrl(host, '{sequence}', device?.device_id);
          
          setAutonomousBaseUrlPattern(basePattern);
          console.log(`[useMonitoring] Autonomous base URL pattern initialized: ${basePattern}`);
        } else {
          console.warn('[useMonitoring] takeScreenshot API returned no screenshot_url');
        }
      } else {
        console.warn('[useMonitoring] takeScreenshot API failed:', response.status);
      }
    } catch (error) {
      console.error('[useMonitoring] Failed to initialize autonomous base URL pattern:', error);
    } finally {
      setIsInitializingBaseUrl(false);
    }
  }, [host, device, autonomousBaseUrlPattern, isInitializingBaseUrl]);

  // Fetch latest JSON file and derive image URL
  const fetchLatestMonitoringData = useCallback(async (): Promise<{imageUrl: string, jsonUrl: string, timestamp: string, sequence: string} | null> => {
    try {
      // Get latest JSON file from the capture directory
      const response = await fetch(buildServerUrl('/server/monitoring/latest-json'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          host_name: host.host_name,
          device_id: device?.device_id || 'device1',
        }),
      });

      if (response.ok) {
        const result = await response.json();
        if (result.success && result.latest_json_url) {
          // Extract filename from the raw URL
          const rawJsonUrl = result.latest_json_url;
          const sequenceMatch = rawJsonUrl.match(/capture_(\d+)/);
          const sequence = sequenceMatch ? sequenceMatch[1] : '';
          
          const imageUrl = buildCaptureUrl(host, sequence, device?.device_id);
          const jsonUrl = imageUrl.replace('.jpg', '.json');
          const timestamp = result.timestamp || new Date().toISOString();
          
          console.log(`[useMonitoring] Latest JSON: ${jsonUrl} -> Image: ${imageUrl}`);
          return { imageUrl, jsonUrl, sequence, timestamp };
        }
      }
      return null;
    } catch (error) {
      console.error('[useMonitoring] Failed to fetch latest JSON:', error);
      return null;
    }
  }, [host?.host_name, host?.host_url, device?.device_id]);

  // Initialize autonomous base URL pattern on mount
  useEffect(() => {
    if (!baseUrlPattern && !autonomousBaseUrlPattern && !isInitializingBaseUrl) {
      initializeAutonomousBaseUrl();
    }
  }, [baseUrlPattern, autonomousBaseUrlPattern, isInitializingBaseUrl, initializeAutonomousBaseUrl]);

  // Process 1: Queue Feeder - Sequential frame processing with complete AI analysis
  useEffect(() => {
    // Start immediately, don't wait for initial loading to complete

    let isRunning = true;
    let frameSequence = 0;

    const queueFeederLoop = async () => {
      // Wait a moment for autonomous base URL initialization
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      console.log('[useMonitoring] 🔄 Starting fast initial buffer (3 frames)...');
      
      // Phase 1: Fast initial buffer - exactly 3 frames for immediate display
      for (let i = 0; i < 3 && isRunning; i++) {
        try {
          const latestData = await fetchLatestMonitoringData();
          
          if (latestData && latestData.sequence !== lastProcessedSequence) {
            frameSequence++;
            const timestamp = new Date().toISOString();
            console.log(`[useMonitoring] ⚡ [${timestamp}] Fast loading frame ${frameSequence}/3: seq=${latestData.sequence}`);
            
            const queuedFrame: QueuedFrame = {
              timestamp: latestData.timestamp,
              imageUrl: latestData.imageUrl,
              jsonUrl: latestData.jsonUrl,
              sequence: latestData.sequence,
            };

            // Fast JSON loading only
            await loadFrameJsonAsync(queuedFrame);
            
            // Queue immediately
            setDisplayQueue(prev => [...prev, queuedFrame]);
            setLastProcessedSequence(latestData.sequence);
            setCurrentImageUrl(latestData.imageUrl);

            // Start background AI (non-blocking)
            analyzeFrameAIAsync(queuedFrame).catch(error => {
              console.warn('[useMonitoring] Background AI failed:', error);
            });
          }
          
          // Small delay between initial frames
          if (i < 2) await new Promise(resolve => setTimeout(resolve, 100));
        } catch (error) {
          console.error('[useMonitoring] Initial buffer error:', error);
        }
      }
      
      console.log('[useMonitoring] ✅ Fast initial buffer complete - player should be visible');
      
      // Phase 2: Normal operation - continue feeding queue
      while (isRunning) {
        try {
          const latestData = await fetchLatestMonitoringData();
          
          if (latestData && latestData.sequence !== lastProcessedSequence) {
            frameSequence++;
            const timestamp = new Date().toISOString();
            console.log(`[useMonitoring] 📦 [${timestamp}] Normal frame ${frameSequence}: seq=${latestData.sequence}`);
            
            const queuedFrame: QueuedFrame = {
              timestamp: latestData.timestamp,
              imageUrl: latestData.imageUrl,
              jsonUrl: latestData.jsonUrl,
              sequence: latestData.sequence,
            };

            await loadFrameJsonAsync(queuedFrame);
            
            setDisplayQueue(prev => [...prev, queuedFrame].slice(-10));
            setLastProcessedSequence(latestData.sequence);
            setCurrentImageUrl(latestData.imageUrl);

            // Background AI caching
            analyzeFrameAIAsync(queuedFrame).catch(error => {
              console.warn('[useMonitoring] Background AI failed:', error);
            });
          }
          
          // Normal polling rate
          await new Promise(resolve => setTimeout(resolve, 500));
        } catch (error) {
          console.error('[useMonitoring] Queue feeder error:', error);
          await new Promise(resolve => setTimeout(resolve, 1000));
        }
      }
    };

    queueFeederLoop();

    return () => {
      isRunning = false;
    };
  }, [fetchLatestMonitoringData, loadFrameJsonAsync, analyzeFrameAIAsync, lastProcessedSequence, initialFramesLoaded]);

  // Process 2: Display Consumer - Simple 1 FPS display from complete frames
  useEffect(() => {
    if (isInitialLoading) return;

    const displayInterval = setInterval(() => {
      const timestamp = new Date().toISOString();
      
      setDisplayQueue(prev => {
        console.log(`[useMonitoring] 📊 [${timestamp}] Display consumer: Queue length=${prev.length}`);
        
        if (prev.length === 0) {
          console.log(`[useMonitoring] ⚠️ [${timestamp}] Queue empty - no frames to display`);
          return prev;
        }

        // Take first frame (all frames in queue are complete)
        const [nextFrame, ...remainingFrames] = prev;
        
        console.log(`[useMonitoring] 🎬 [${timestamp}] Displaying frame: seq=${nextFrame.sequence}, url=${nextFrame.imageUrl}`);
        console.log(`[useMonitoring] 📊 [${timestamp}] Remaining queue: ${remainingFrames.length} frames`);
        
        // Convert QueuedFrame to FrameRef and add to frames array
        const frameRef: FrameRef = {
          timestamp: nextFrame.timestamp,
          imageUrl: nextFrame.imageUrl,
          jsonUrl: nextFrame.jsonUrl,
          analysis: nextFrame.analysis,
          subtitleAnalysis: nextFrame.subtitleAnalysis,
          languageMenuAnalysis: nextFrame.languageMenuAnalysis,
          aiDescription: nextFrame.aiDescription,
        };

        setFrames(current => {
          const newFrames = [...current, frameRef].slice(-100);
          // Only auto-advance to latest if user is not manually browsing
          if (!userSelectedFrame && isPlaying) {
            setCurrentIndex(newFrames.length - 1);
          }
          return newFrames;
        });

        return remainingFrames;
      });
    }, 2000); // 0.5 FPS (2-second intervals)

    return () => clearInterval(displayInterval);
  }, [isInitialLoading, userSelectedFrame, isPlaying]);

  // Auto-play functionality - only advances when at the latest frame
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isPlaying && frames.length > 1 && !userSelectedFrame) {
      interval = setInterval(() => {
        setCurrentIndex((prev) => {
          // Only auto-advance if we're already at the latest frame
          if (prev === frames.length - 1) {
            // Stay at latest frame (will advance when new frames are added)
            return frames.length - 1;
          }
          // If user is viewing historical frames, don't auto-advance
          return prev;
        });
      }, 2000); // 2 seconds per frame
    }
    return () => clearInterval(interval);
  }, [isPlaying, frames.length, userSelectedFrame]);

  // Load analysis for selected frame
  useEffect(() => {
    const loadSelectedFrameAnalysis = async () => {
      if (frames.length === 0 || currentIndex >= frames.length) {
        setSelectedFrameAnalysis(null);
        return;
      }

      const selectedFrame = frames[currentIndex];
      if (!selectedFrame) {
        setSelectedFrameAnalysis(null);
        return;
      }

      // If we already have analysis data (including null from failed load), use it
      if (selectedFrame.hasOwnProperty('analysis')) {
        setSelectedFrameAnalysis(selectedFrame.analysis || null);
        return;
      }

      // No delay needed - JSON is guaranteed to exist since we fetched it from latest API
      try {
        console.log('[useMonitoring] Loading analysis:', selectedFrame.jsonUrl);
        const response = await fetch(selectedFrame.jsonUrl);
        let analysis: any = null;

        if (response.ok) {
            const data = await response.json();

            analysis = {
              timestamp: data.timestamp || '',
              filename: data.filename || '',
              thumbnail: data.thumbnail || '',
              blackscreen: data.blackscreen || false,
              blackscreen_percentage: data.blackscreen_percentage || 0,
              freeze: data.freeze || false,
              freeze_diffs: data.freeze_diffs || [],
              last_3_filenames: data.last_3_filenames || [],
              last_3_thumbnails: data.last_3_thumbnails || [],
              audio: data.audio || false,
              volume_percentage: data.volume_percentage || 0,
              mean_volume_db: data.mean_volume_db || -100,
              macroblocks: data.macroblocks || false,
              quality_score: data.quality_score || 0,
              has_incidents: data.has_incidents || false,
            };

            console.log('[useMonitoring] Analysis loaded:', analysis);
          } else {
            console.log('[useMonitoring] Analysis failed:', response.status, response.statusText);
            
            // Skip entirely - don't update any state when JSON is missing
            return;
          }

          // Cache the analysis in the frame reference
          setFrames((prev) =>
            prev.map((frame, index) => (index === currentIndex ? { ...frame, analysis } : frame)),
          );

          setSelectedFrameAnalysis(analysis);
        } catch {
          // Skip entirely - don't update any state when JSON loading fails
          console.log('[useMonitoring] Analysis loading failed with exception');
          return;
        }
    };

    loadSelectedFrameAnalysis();
  }, [currentIndex, frames]);

  // Error trend analysis - track consecutive blackscreen and freeze errors
  const errorTrendData = useMemo((): ErrorTrendData | null => {
    if (frames.length === 0) return null;

    // Get frames with successfully loaded analysis data (not null, not undefined)
    // This excludes frames where JSON was missing (404) or failed to load
    const framesWithValidAnalysis = frames.filter((frame) => frame.analysis !== undefined && frame.analysis !== null);

    if (framesWithValidAnalysis.length === 0) return null;

    // Analyze up to the last 10 frames for error trends
    const recentFrames = framesWithValidAnalysis.slice(-10);

    let blackscreenConsecutive = 0;
    let freezeConsecutive = 0;
    let audioLossConsecutive = 0;

    // Count consecutive errors from the end (most recent frames)
    // Only count frames with valid analysis data to avoid false trends from missing JSON files
    for (let i = recentFrames.length - 1; i >= 0; i--) {
      const analysis = recentFrames[i].analysis;
      if (!analysis) break; // This shouldn't happen due to our filtering, but safety check

      // Track whether we found any errors in this frame
      let hasBlackscreenError = analysis.blackscreen;
      let hasFreezeError = analysis.freeze;
      let hasAudioLossError = !analysis.audio;

      // Count consecutive blackscreen errors
      if (hasBlackscreenError) {
        blackscreenConsecutive++;
      } else {
        // Reset blackscreen count if no error in this frame
        if (blackscreenConsecutive > 0) break;
      }

      // Count consecutive freeze errors
      if (hasFreezeError) {
        freezeConsecutive++;
      } else {
        // Reset freeze count if no error in this frame
        if (freezeConsecutive > 0) break;
      }

      // Count consecutive audio loss errors
      if (hasAudioLossError) {
        audioLossConsecutive++;
      } else {
        // Reset audio loss count if no error in this frame
        if (audioLossConsecutive > 0) break;
      }

      // If no errors are present in this frame, stop all consecutive counts
      if (!hasBlackscreenError && !hasFreezeError && !hasAudioLossError) {
        break;
      }
    }

    // Determine warning/error states
    const maxConsecutive = Math.max(
      blackscreenConsecutive,
      freezeConsecutive,
      audioLossConsecutive,
    );
    const hasWarning = maxConsecutive >= 1 && maxConsecutive < 3;
    const hasError = maxConsecutive >= 3;

    console.log('[useMonitoring] Error trend analysis:', {
      blackscreenConsecutive,
      freezeConsecutive,
      audioLossConsecutive,
      maxConsecutive,
      hasWarning,
      hasError,
      framesAnalyzed: recentFrames.length,
      totalFrames: frames.length,
      validAnalysisFrames: framesWithValidAnalysis.length,
    });

    return {
      blackscreenConsecutive,
      freezeConsecutive,
      audioLossConsecutive,
      macroblocksConsecutive: 0, // TODO: Implement macroblock consecutive tracking
      hasWarning,
      hasError,
    };
  }, [frames]);

  // Subtitle trend analysis - computed from autonomous analysis results
  const subtitleTrendAnalysis = useMemo((): SubtitleTrendAnalysis | null => {
    if (frames.length === 0) return null;

    // Get frames with subtitle data from autonomous analysis
    const framesWithSubtitles = frames.filter(
      (frame) => frame.subtitleAnalysis !== undefined,
    );

    if (framesWithSubtitles.length === 0) return null;

    // Use up to 3 frames for subtitle trend analysis
    const targetFrameCount = Math.min(3, framesWithSubtitles.length);
    const recentFrames = framesWithSubtitles.slice(-targetFrameCount);

    // Check for subtitle presence across frames
    let noSubtitlesCount = 0;
    let currentHasSubtitles = false;

    recentFrames.forEach((frame, index) => {
      const subtitleData = frame.subtitleAnalysis;
      if (!subtitleData) return;

      // Check current frame (most recent)
      if (index === recentFrames.length - 1) {
        currentHasSubtitles = subtitleData.subtitles_detected || false;
      }

      // Count frames without subtitles
      if (!subtitleData.subtitles_detected) {
        noSubtitlesCount++;
      }
    });

    // Red indicator logic:
    // - Show red if ALL analyzed frames have no subtitles
    // - AND we have analyzed at least the target number of frames
    const showRedIndicator =
      noSubtitlesCount === recentFrames.length && recentFrames.length >= targetFrameCount;

    return {
      showRedIndicator,
      currentHasSubtitles,
      framesAnalyzed: recentFrames.length,
      noSubtitlesStreak: noSubtitlesCount,
    };
  }, [frames]);

  // Get current analysis data for overlay display
  const currentSubtitleAnalysis = useMemo(() => {
    if (frames.length === 0 || currentIndex >= frames.length) return null;
    const currentFrame = frames[currentIndex];
    return currentFrame?.subtitleAnalysis || null;
  }, [frames, currentIndex]);

  const currentLanguageMenuAnalysis = useMemo(() => {
    if (frames.length === 0 || currentIndex >= frames.length) return null;
    const currentFrame = frames[currentIndex];
    return currentFrame?.languageMenuAnalysis || null;
  }, [frames, currentIndex]);

  const currentAIDescription = useMemo(() => {
    if (frames.length === 0 || currentIndex >= frames.length) return null;
    const currentFrame = frames[currentIndex];
    return currentFrame?.aiDescription || null;
  }, [frames, currentIndex]);

  // Handlers
  const handlePlayPause = useCallback(() => {
    if (!isPlaying) {
      // When starting play, only reset to latest if user wants to follow live
      // Don't force them to latest frame if they're browsing history
      setUserSelectedFrame(false);
      // Only jump to latest if they're close to it (within 2 frames)
      if (frames.length > 0 && currentIndex >= frames.length - 3) {
        setCurrentIndex(frames.length - 1);
      }
    } else {
      // When pausing, mark as user-selected to stop auto-following
      setUserSelectedFrame(true);
    }
    setIsPlaying(!isPlaying);
  }, [isPlaying, frames.length, currentIndex]);

  const handleSliderChange = useCallback((_event: Event, newValue: number | number[]) => {
    const index = newValue as number;
    setCurrentIndex(index);
    setIsPlaying(false);
    setUserSelectedFrame(true); // Mark as manually selected
    setIsHistoricalFrameLoaded(false); // Reset loading state when changing frames
  }, []);

  const handleHistoricalFrameLoad = useCallback(() => {
    setIsHistoricalFrameLoaded(true);
  }, []);

  // Reset loading state when current frame changes
  useEffect(() => {
    setIsHistoricalFrameLoaded(false);
  }, [currentIndex]);

  // Get current frame URL for display
  const currentFrameUrl = frames[currentIndex]?.imageUrl || '';

  return {
    // Frame management
    frames,
    currentIndex,
    currentFrameUrl,
    selectedFrameAnalysis,
    isHistoricalFrameLoaded,
    isInitialLoading,

    // Playback controls
    isPlaying,
    userSelectedFrame,

    // Actions
    handlePlayPause,
    handleSliderChange,
    handleHistoricalFrameLoad,


    // Subtitle trend analysis
    subtitleTrendAnalysis,

    // Error trend analysis
    errorTrendData,

    // Current analysis data for overlay display
    currentSubtitleAnalysis,
    currentLanguageMenuAnalysis,
    currentAIDescription,

    // Current frame timestamp for analysis tracking
    currentFrameTimestamp: frames[currentIndex]?.timestamp || null,
  };
};
