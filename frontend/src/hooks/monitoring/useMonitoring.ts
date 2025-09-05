import { useState, useEffect, useCallback, useMemo } from 'react';

import {
  MonitoringAnalysis,
  SubtitleAnalysis,
  SubtitleTrendAnalysis,
  LanguageMenuAnalysis,
} from '../../types/pages/Monitoring_Types';

import { useMonitoringAI } from './useMonitoringAI';
import { useMonitoringSubtitles } from './useMonitoringSubtitles';
import { useMonitoringLanguageMenu } from './useMonitoringLanguageMenu';

interface FrameRef {
  timestamp: string;
  imageUrl: string;
  jsonUrl: string;
  analysis?: MonitoringAnalysis | null;
  subtitleDetectionPerformed?: boolean; // Flag to track if manual subtitle detection was done
}

interface ErrorTrendData {
  blackscreenConsecutive: number;
  freezeConsecutive: number;
  audioLossConsecutive: number;
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

  // Subtitle detection
  detectSubtitles: () => Promise<void>;
  detectSubtitlesAI: () => Promise<void>;
  isDetectingSubtitles: boolean;
  isDetectingSubtitlesAI: boolean;
  hasSubtitleDetectionResults: boolean; // Whether current frame has subtitle detection results

  // AI Query functionality
  isAIQueryVisible: boolean;
  aiQuery: string;
  aiResponse: string;
  isProcessingAIQuery: boolean;
  toggleAIPanel: () => void;
  submitAIQuery: () => Promise<void>;
  clearAIQuery: () => void;
  handleAIQueryChange: (query: string) => void;

  // Subtitle trend analysis
  subtitleTrendAnalysis: SubtitleTrendAnalysis | null;

  // Error trend analysis
  errorTrendData: ErrorTrendData | null;

  // Current subtitle analysis for components that need subtitle data
  currentSubtitleAnalysis: SubtitleAnalysis | null;

  // Language menu detection
  analyzeLanguageMenu: () => Promise<void>;
  isAnalyzingLanguageMenu: boolean;
  hasLanguageMenuResults: boolean;
  currentLanguageMenuAnalysis: LanguageMenuAnalysis | null;

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

  // Initial loading buffer - reduced since we fetch latest available JSON
  useEffect(() => {
    const timer = setTimeout(() => {
      setIsInitialLoading(false);
    }, 3000); // 3 seconds - just enough for latest JSON to be available
    return () => clearTimeout(timer);
  }, []);



  // Use dedicated hooks for subtitle detection
  const subtitleHook = useMonitoringSubtitles({
    frames,
    currentIndex,
    setFrames,
    setIsPlaying,
    setUserSelectedFrame,
    host,
    device,
  });

  // Use dedicated hook for AI functionality
  const aiHook = useMonitoringAI({
    frames,
    currentIndex,
    setIsPlaying,
    setUserSelectedFrame,
    host,
    device,
  });

  // Use dedicated hook for language menu analysis
  const languageMenuHook = useMonitoringLanguageMenu({
    frames,
    currentIndex,
    setFrames,
    setIsPlaying,
    setUserSelectedFrame,
    host,
    device,
  });

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
      const response = await fetch('/server/av/takeScreenshot', {
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
          // Extract base pattern: remove timestamp from capture_YYYYMMDDHHMMSS.jpg format
          const basePattern = result.screenshot_url.replace(
            /capture_\d{14}\.jpg$/,
            'capture_{timestamp}.jpg',
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
  const fetchLatestMonitoringData = useCallback(async (): Promise<{imageUrl: string, jsonUrl: string, timestamp: string} | null> => {
    try {
      // Get latest JSON file from the capture directory
      const response = await fetch('/server/av/monitoring/latest-json', {
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
          const timestampMatch = jsonUrl.match(/capture_(\d{14})/);
          const timestamp = timestampMatch ? timestampMatch[1] : '';
          
          console.log(`[useMonitoring] Latest JSON: ${jsonUrl} -> Image: ${imageUrl}`);
          return { imageUrl, jsonUrl, timestamp };
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

  // Fetch latest monitoring data (only after initial loading)
  useEffect(() => {
    if (isInitialLoading) return; // Skip during initial loading

    const fetchLatestFrame = async () => {
      const latestData = await fetchLatestMonitoringData();

      if (latestData) {
        // Check if this is actually new data (different timestamp)
        const isDifferentFrame = latestData.imageUrl !== currentImageUrl;
        
        if (isDifferentFrame) {
          setCurrentImageUrl(latestData.imageUrl);

          console.log('[useMonitoring] New frame detected:', latestData.timestamp);

          // Add new frame and handle navigation in a single state update
          setFrames((prev) => {
            // Check if we already have this timestamp to avoid duplicates
            const existingFrame = prev.find(frame => frame.timestamp === latestData.timestamp);
            if (existingFrame) {
              console.log('[useMonitoring] Frame already exists, skipping:', latestData.timestamp);
              return prev;
            }

            const newFrames = [...prev, { 
              timestamp: latestData.timestamp, 
              imageUrl: latestData.imageUrl, 
              jsonUrl: latestData.jsonUrl 
            }];
            const updatedFrames = newFrames.slice(-100); // Always keep last 100 frames

            // Update current index based on current playing state
            // This happens in the same render cycle, avoiding stale closures
            setCurrentIndex((currentIdx) => {
              // ONLY auto-follow when actively playing AND not user-selected
              if (isPlaying && !userSelectedFrame) {
                return updatedFrames.length - 1;
              }
              // ONLY move user if their selected frame was deleted from buffer
              else if (userSelectedFrame && currentIdx >= updatedFrames.length) {
                // Frame was deleted, move to newest but DON'T resume playing
                // Keep the user in control - they paused for a reason
                console.log('[useMonitoring] User selected frame was deleted, moving to latest but staying paused');
                return updatedFrames.length - 1;
              }
              // Otherwise: DO NOTHING - stay on current frame
              return currentIdx;
            });

            return updatedFrames;
          });
        } else {
          console.log('[useMonitoring] Same frame, no update needed');
        }
      }
    };

    // Fetch initial frame immediately
    fetchLatestFrame();

    // Set up interval for continuous monitoring
    const interval = setInterval(fetchLatestFrame, 3000); // Fetch every 3 seconds
    return () => clearInterval(interval);
  }, [
    fetchLatestMonitoringData,
    isInitialLoading,
    isPlaying,
    userSelectedFrame,
    currentImageUrl,
  ]);

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
      hasWarning,
      hasError,
    };
  }, [frames]);

  // Subtitle trend analysis moved to useMonitoringSubtitles
  const subtitleTrendAnalysis = subtitleHook.subtitleTrendAnalysis;

  // Get current subtitle analysis from the subtitle hook
  const currentSubtitleAnalysis = subtitleHook.currentSubtitleAnalysis;

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

    // Subtitle detection (from dedicated hook)
    detectSubtitles: subtitleHook.detectSubtitles,
    detectSubtitlesAI: subtitleHook.detectSubtitlesAI,
    isDetectingSubtitles: subtitleHook.isDetectingSubtitles,
    isDetectingSubtitlesAI: subtitleHook.isDetectingSubtitlesAI,
    hasSubtitleDetectionResults: subtitleHook.hasSubtitleDetectionResults,

    // AI Query functionality (from dedicated hook)
    isAIQueryVisible: aiHook.isAIQueryVisible,
    aiQuery: aiHook.aiQuery,
    aiResponse: aiHook.aiResponse,
    isProcessingAIQuery: aiHook.isProcessingAIQuery,
    toggleAIPanel: aiHook.toggleAIPanel,
    submitAIQuery: aiHook.submitAIQuery,
    clearAIQuery: aiHook.clearAIQuery,
    handleAIQueryChange: aiHook.handleAIQueryChange,

    // Subtitle trend analysis
    subtitleTrendAnalysis,

    // Error trend analysis
    errorTrendData,

    // Current subtitle analysis for components that need subtitle data
    currentSubtitleAnalysis,

    // Language menu detection (from dedicated hook)
    analyzeLanguageMenu: languageMenuHook.analyzeLanguageMenu,
    isAnalyzingLanguageMenu: languageMenuHook.isAnalyzingLanguageMenu,
    hasLanguageMenuResults: languageMenuHook.hasLanguageMenuResults,
    currentLanguageMenuAnalysis: languageMenuHook.currentLanguageMenuAnalysis,

    // Current frame timestamp for analysis tracking
    currentFrameTimestamp: frames[currentIndex]?.timestamp || null,
  };
};
