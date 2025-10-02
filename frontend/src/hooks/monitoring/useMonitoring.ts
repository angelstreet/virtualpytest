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
  // Timeline indicator flags
  hasAIAnalysis?: boolean; // True when subtitle + summary are loaded
  hasError?: boolean; // True when JSON shows blackscreen, freeze, or audio loss
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
}

export const useMonitoring = ({
  host,
  device,
}: UseMonitoringProps): UseMonitoringReturn => {
  const [frames, setFrames] = useState<FrameRef[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(true);
  const [userSelectedFrame, setUserSelectedFrame] = useState(false);
  const [selectedFrameAnalysis, setSelectedFrameAnalysis] = useState<MonitoringAnalysis | null>(
    null,
  );
  const [isHistoricalFrameLoaded, setIsHistoricalFrameLoaded] = useState(false);
  const [isInitialLoading, setIsInitialLoading] = useState(true);
  const [lastProcessedSequence, setLastProcessedSequence] = useState<string>('');

  // Helper: Load JSON analysis and determine error status
  const loadFrameJsonAsync = useCallback(async (jsonUrl: string): Promise<{analysis: any, hasError: boolean}> => {
    let jsonAnalysis: any = null;
    let hasError = false;
    
    try {
      const jsonResponse = await fetch(jsonUrl);
      if (jsonResponse.ok) {
        jsonAnalysis = await jsonResponse.json();
        
        // Determine if frame has errors (for timeline red/green indicator)
        hasError = !!(
          jsonAnalysis?.blackscreen || 
          jsonAnalysis?.freeze || 
          !jsonAnalysis?.audio
        );
      } else if (jsonResponse.status === 404) {
        console.log('[useMonitoring] JSON not found (404) - will display image without analysis');
      }
    } catch (error) {
      console.warn('[useMonitoring] Failed to load JSON:', error);
    }
    
    return { analysis: jsonAnalysis, hasError };
  }, []);

  // Background AI analysis for caching (runs separately, non-blocking)
  const analyzeFrameAIAsync = useCallback(async (imageUrl: string): Promise<void> => {
    console.log('[useMonitoring] 🤖 Background AI analysis for:', imageUrl);

    // Combined AI analysis in background (single call for both subtitle + description)
    const combinedResult = await fetch(buildServerUrl('/server/verification/video/analyzeImageComplete'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        host_name: host.host_name,
        device_id: device?.device_id,
        image_source_url: imageUrl,
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

    console.log(`[useMonitoring] ✅ Background AI completed for:`, imageUrl);

    // Update frames array with AI results and set hasAIAnalysis flag
    setFrames(prev => prev.map(frame => 
      frame.imageUrl === imageUrl ? { 
        ...frame, 
        subtitleAnalysis, 
        aiDescription,
        hasAIAnalysis: true // Mark that AI analysis is available
      } : frame
    ));
  }, [host, device?.device_id]);


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

  // Simple 1s polling: Fetch latest frame, load JSON immediately, display instantly
  useEffect(() => {
    let isMounted = true;
    
    const pollLatestFrame = async () => {
      try {
        const latestData = await fetchLatestMonitoringData();
        if (!isMounted || !latestData) return;
        if (latestData.sequence === lastProcessedSequence) return; // Skip if already processed

        console.log(`[useMonitoring] 📸 New frame detected: seq=${latestData.sequence}`);

        // Load JSON immediately (fast, ~100-200ms)
        const { analysis, hasError } = await loadFrameJsonAsync(latestData.jsonUrl);

        // Create frame and add to frames array immediately
        const frameRef: FrameRef = {
          timestamp: latestData.timestamp,
          imageUrl: latestData.imageUrl,
          jsonUrl: latestData.jsonUrl,
          analysis,
          hasError, // Red/green timeline indicator
          hasAIAnalysis: false, // Will be set to true when AI completes
        };

        setFrames(current => {
          const newFrames = [...current, frameRef].slice(-100);
          // Auto-advance to latest if user is following live
          if (!userSelectedFrame && isPlaying) {
            setCurrentIndex(newFrames.length - 1);
          }
          return newFrames;
        });

        setLastProcessedSequence(latestData.sequence);
        if (isInitialLoading) setIsInitialLoading(false);

        // Start background AI analysis (non-blocking, will update hasAIAnalysis when done)
        analyzeFrameAIAsync(latestData.imageUrl).catch(error => {
          console.warn('[useMonitoring] Background AI failed:', error);
        });
      } catch (error) {
        console.error('[useMonitoring] Polling error:', error);
      }
    };

    // Poll immediately on mount, then every 1s
    pollLatestFrame();
    const interval = setInterval(pollLatestFrame, 1000);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [fetchLatestMonitoringData, loadFrameJsonAsync, analyzeFrameAIAsync, lastProcessedSequence, userSelectedFrame, isPlaying, isInitialLoading]);

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
