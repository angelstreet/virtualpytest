import { useState, useEffect, useCallback, useMemo } from 'react';

import {
  MonitoringAnalysis,
  SubtitleAnalysis,
  SubtitleTrendAnalysis,
  LanguageMenuAnalysis,
} from '../../types/pages/Monitoring_Types';

import { buildServerUrl } from '../../utils/buildUrlUtils';
interface FrameRef {
  timestamp: string;
  imageUrl: string;
  jsonUrl: string;
  analysis?: MonitoringAnalysis | null;
  subtitleAnalysis?: SubtitleAnalysis | null;
  languageMenuAnalysis?: LanguageMenuAnalysis | null;
  aiDescription?: string | null;
}

interface BufferedFrame {
  frame: FrameRef;
  aiPromise: Promise<void>;
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
  const [currentImageUrl, setCurrentImageUrl] = useState<string>('');
  const [userSelectedFrame, setUserSelectedFrame] = useState(false);
  const [selectedFrameAnalysis, setSelectedFrameAnalysis] = useState<MonitoringAnalysis | null>(
    null,
  );
  const [isHistoricalFrameLoaded, setIsHistoricalFrameLoaded] = useState(false);
  const [isInitialLoading, setIsInitialLoading] = useState(true);
  const [frameBuffer, setFrameBuffer] = useState<BufferedFrame[]>([]);
  const [_displayQueue, setDisplayQueue] = useState<FrameRef[]>([]);

  // Initial loading buffer - reduced to max 1 second as requested
  useEffect(() => {
    const timer = setTimeout(() => {
      setIsInitialLoading(false);
    }, 1000); // 1 second maximum delay before showing first image
    return () => clearTimeout(timer);
  }, []);



  // AI analysis for buffered frame
  const analyzeFrame = useCallback(async (frameData: {imageUrl: string, jsonUrl: string, timestamp: string}): Promise<FrameRef> => {
    // Load JSON analysis first
    let jsonAnalysis = null;
    let realTimestamp = frameData.timestamp;
    
    try {
      const jsonResponse = await fetch(frameData.jsonUrl);
      if (jsonResponse.ok) {
        jsonAnalysis = await jsonResponse.json();
        realTimestamp = jsonAnalysis.timestamp || frameData.timestamp;
      }
    } catch (error) {
      console.warn('[useMonitoring] Failed to load JSON:', error);
    }

    // Parallel AI analysis
    const [subtitleResult, languageMenuResult, descriptionResult] = await Promise.allSettled([
      fetch(buildServerUrl('/server/verification/video/detectSubtitlesAI'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          host: host,
          device_id: device?.device_id,
          image_source_url: frameData.imageUrl,
          extract_text: true,
        }),
      }).then(r => r.ok ? r.json() : null),

      fetch(buildServerUrl('/server/verification/video/analyzeLanguageMenu'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          host: host,
          device_id: device?.device_id,
          image_source_url: frameData.imageUrl,
        }),
      }).then(r => r.ok ? r.json() : null),

      fetch(buildServerUrl('/server/verification/video/analyzeImageAI'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          host: host,
          device_id: device?.device_id,
          image_source_url: frameData.imageUrl,
          query: 'Provide a short description of what you see in this image',
        }),
      }).then(r => r.ok ? r.json() : null),
    ]);

    // Process results
    let subtitleAnalysis = null;
    if (subtitleResult.status === 'fulfilled' && subtitleResult.value?.success) {
      const data = subtitleResult.value.results?.[0] || {};
      subtitleAnalysis = {
        subtitles_detected: subtitleResult.value.subtitles_detected || false,
        combined_extracted_text: subtitleResult.value.combined_extracted_text || data.extracted_text || '',
        detected_language: subtitleResult.value.detected_language !== 'unknown' ? subtitleResult.value.detected_language : undefined,
        confidence: data.confidence || (subtitleResult.value.subtitles_detected ? 0.9 : 0.1),
        detection_message: subtitleResult.value.detection_message || '',
      };
    }

    let languageMenuAnalysis = null;
    if (languageMenuResult.status === 'fulfilled' && languageMenuResult.value?.success) {
      languageMenuAnalysis = {
        menu_detected: languageMenuResult.value.menu_detected || false,
        audio_languages: languageMenuResult.value.audio_languages || [],
        subtitle_languages: languageMenuResult.value.subtitle_languages || [],
        selected_audio: languageMenuResult.value.selected_audio ?? -1,
        selected_subtitle: languageMenuResult.value.selected_subtitle ?? -1,
      };
    }

    let aiDescription = null;
    if (descriptionResult.status === 'fulfilled' && descriptionResult.value?.success) {
      aiDescription = descriptionResult.value.response;
    }

    return {
      timestamp: realTimestamp,
      imageUrl: frameData.imageUrl,
      jsonUrl: frameData.jsonUrl,
      analysis: jsonAnalysis,
      subtitleAnalysis,
      languageMenuAnalysis,
      aiDescription,
    };
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
          host: host,
          device_id: device?.device_id || 'device1',
        }),
      });

      if (response.ok) {
        const result = await response.json();
        if (result.success && result.screenshot_url) {
          // Extract base pattern: remove sequence number from capture_NNNN.jpg format
          const basePattern = result.screenshot_url.replace(
            /capture_\d+\.jpg$/,
            'capture_{sequence}.jpg',
          );
          
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
      const response = await fetch(buildServerUrl('/server/av/monitoring/latest-json'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          host: host,
          device_id: device?.device_id || 'device1',
        }),
      });

      if (response.ok) {
        const result = await response.json();
        if (result.success && result.latest_json_url) {
          const jsonUrl = result.latest_json_url;
          const imageUrl = jsonUrl.replace('.json', '.jpg'); // Simple replacement
          const sequenceMatch = jsonUrl.match(/capture_(\d+)/);
          const sequence = sequenceMatch ? sequenceMatch[1] : '';
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

  // Buffer management and display
  useEffect(() => {
    if (isInitialLoading) return;

    const processFrames = async () => {
      // Poll for new frames
      const latestData = await fetchLatestMonitoringData();
      if (!latestData || latestData.imageUrl === currentImageUrl) return;

      setCurrentImageUrl(latestData.imageUrl);

      // Always add new frame, remove oldest if buffer full
      const aiPromise = analyzeFrame(latestData).then(frame => {
        setDisplayQueue(prev => [...prev, frame]);
        setFrameBuffer(prev => prev.slice(1)); // Remove completed frame from buffer
      });
      
      setFrameBuffer(prev => {
        const newBuffer = [...prev, { 
          frame: { 
            timestamp: latestData.timestamp, 
            imageUrl: latestData.imageUrl, 
            jsonUrl: latestData.jsonUrl 
          }, 
          aiPromise 
        }];
        return newBuffer.slice(-3); // Keep only last 3 frames
      });
    };

    // Display frames at 1 FPS
    const displayInterval = setInterval(() => {
      setDisplayQueue(prev => {
        if (prev.length === 0) return prev;
        const [nextFrame, ...rest] = prev;
        
        setFrames(current => {
          const newFrames = [...current, nextFrame].slice(-100);
          setCurrentIndex(newFrames.length - 1);
          return newFrames;
        });
        
        return rest;
      });
    }, 1000);

    // Poll for new frames
    const pollInterval = setInterval(processFrames, 1000);
    processFrames(); // Initial call

    return () => {
      clearInterval(displayInterval);
      clearInterval(pollInterval);
    };
  }, [isInitialLoading, fetchLatestMonitoringData, analyzeFrame, currentImageUrl, frameBuffer.length]);

  // Auto-play functionality
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isPlaying && frames.length > 1 && !userSelectedFrame) {
      interval = setInterval(() => {
        setCurrentIndex((prev) => {
          const next = prev + 1;
          if (next >= frames.length) {
            // Stay on latest frame when we reach the end
            return frames.length - 1;
          }
          return next;
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
        let analysis = null;

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
      // When starting play, reset to follow new images automatically
      setUserSelectedFrame(false);
      setCurrentIndex(frames.length - 1);
    } else {
      // When pausing, mark as user-selected to stop auto-following
      setUserSelectedFrame(true);
    }
    setIsPlaying(!isPlaying);
  }, [isPlaying, frames.length]);

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
