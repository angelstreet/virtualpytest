import { useState, useEffect, useCallback, useRef } from 'react';

import {
  MonitoringAnalysis,
  SubtitleAnalysis,
  LanguageMenuAnalysis,
} from '../../types/pages/Monitoring_Types';

import { buildServerUrl, buildCaptureUrl } from '../../utils/buildUrlUtils';

interface ErrorTrendData {
  blackscreenConsecutive: number;
  freezeConsecutive: number;
  audioLossConsecutive: number;
  macroblocksConsecutive: number;
  hasWarning: boolean;
  hasError: boolean;
}

interface AnalysisSnapshot {
  timestamp: string;
  analysis: MonitoringAnalysis | null;
  subtitleAnalysis?: SubtitleAnalysis | null;
  languageMenuAnalysis?: LanguageMenuAnalysis | null;
  aiDescription?: string | null;
}

interface UseMonitoringReturn {
  // Latest analysis data
  latestAnalysis: MonitoringAnalysis | null;
  latestSubtitleAnalysis: SubtitleAnalysis | null;
  latestLanguageMenuAnalysis: LanguageMenuAnalysis | null;
  latestAIDescription: string | null;

  // Error trend analysis (based on last 10 samples)
  errorTrendData: ErrorTrendData | null;

  // Loading state
  isLoading: boolean;

  // Current analysis timestamp
  analysisTimestamp: string | null;
}

interface UseMonitoringProps {
  host: any; // Host object for API requests
  device: any; // Device object for API requests
  enabled: boolean; // Only poll when monitoring mode is active
  archiveMode?: boolean; // Archive mode (Last 24h)
  currentVideoTime?: number; // Video currentTime in seconds
}

export const useMonitoring = ({
  host,
  device,
  enabled,
  archiveMode = false,
  currentVideoTime,
}: UseMonitoringProps): UseMonitoringReturn => {
  // Store last 10 analysis snapshots for error trend tracking
  const [analysisHistory, setAnalysisHistory] = useState<AnalysisSnapshot[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [lastProcessedSequence, setLastProcessedSequence] = useState<string>('');
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const fetchTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Helper: Load JSON analysis from capture URL
  const loadJsonAnalysis = useCallback(async (jsonUrl: string): Promise<MonitoringAnalysis | null> => {
    try {
      const response = await fetch(jsonUrl);
      if (response.ok) {
        const data = await response.json();
        return {
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
      } else if (response.status === 404) {
        console.log('[useMonitoring] JSON not found (404) - capture not yet available');
      }
    } catch (error) {
      console.warn('[useMonitoring] Failed to load JSON:', error);
    }
    return null;
  }, []);

  // Background AI analysis (runs separately, non-blocking)
  const analyzeFrameAIAsync = useCallback(async (imageUrl: string, sequence: string): Promise<{
    subtitleAnalysis: SubtitleAnalysis | null;
    languageMenuAnalysis: LanguageMenuAnalysis | null;
    aiDescription: string | null;
  }> => {
    console.log('[useMonitoring] 🤖 Background AI analysis for sequence:', sequence);

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
    let subtitleAnalysis: SubtitleAnalysis | null = null;
    let languageMenuAnalysis: LanguageMenuAnalysis | null = null;
    let aiDescription: string | null = null;
    
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

    console.log(`[useMonitoring] ✅ Background AI completed for sequence:`, sequence);

    return { subtitleAnalysis, languageMenuAnalysis, aiDescription };
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
          
          return { imageUrl, jsonUrl, sequence, timestamp };
        }
      }
      return null;
    } catch (error) {
      console.error('[useMonitoring] Failed to fetch latest JSON:', error);
      return null;
    }
  }, [host, device?.device_id]);

  // Fetch archive JSON by timestamp
  const fetchArchiveData = useCallback(async (timestampSeconds: number) => {
    try {
      const response = await fetch(buildServerUrl('/server/monitoring/json-by-time'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          host_name: host.host_name,
          device_id: device?.device_id || 'device1',
          timestamp_seconds: Math.floor(timestampSeconds),
          fps: 5
        })
      });

      if (response.ok) {
        const result = await response.json();
        if (result.success && result.json_data) {
          const snapshot: AnalysisSnapshot = {
            timestamp: result.json_data.timestamp || new Date().toISOString(),
            analysis: result.json_data,
            subtitleAnalysis: null,
            languageMenuAnalysis: null,
            aiDescription: null,
          };
          setAnalysisHistory([snapshot]);
          if (isLoading) setIsLoading(false);
        }
      }
    } catch (error) {
      console.error('[useMonitoring] Archive fetch error:', error);
    }
  }, [host, device?.device_id, isLoading]);

  // Poll live data OR fetch archive data based on mode
  useEffect(() => {
    if (!enabled) {
      setAnalysisHistory([]);
      setIsLoading(true);
      setLastProcessedSequence('');
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
      if (fetchTimeoutRef.current) {
        clearTimeout(fetchTimeoutRef.current);
        fetchTimeoutRef.current = null;
      }
      return;
    }

    // Archive mode: debounced fetch on video time change
    if (archiveMode && currentVideoTime !== undefined) {
      if (fetchTimeoutRef.current) {
        clearTimeout(fetchTimeoutRef.current);
      }
      fetchTimeoutRef.current = setTimeout(() => {
        fetchArchiveData(currentVideoTime);
      }, 300);
      
      return () => {
        if (fetchTimeoutRef.current) {
          clearTimeout(fetchTimeoutRef.current);
          fetchTimeoutRef.current = null;
        }
      };
    }

    // Live mode: 500ms polling
    let isMounted = true;
    
    const pollLatestData = async () => {
      try {
        const latestData = await fetchLatestMonitoringData();
        if (!isMounted || !latestData) return;
        if (latestData.sequence === lastProcessedSequence) return;

        const analysis = await loadJsonAnalysis(latestData.jsonUrl);
        if (!analysis) return;

        const snapshot: AnalysisSnapshot = {
          timestamp: latestData.timestamp,
          analysis,
          subtitleAnalysis: null,
          languageMenuAnalysis: null,
          aiDescription: null,
        };

        setAnalysisHistory(prev => [...prev, snapshot].slice(-10));
        setLastProcessedSequence(latestData.sequence);
        if (isLoading) setIsLoading(false);

        analyzeFrameAIAsync(latestData.imageUrl, latestData.sequence).then(aiResults => {
          if (!isMounted) return;
          setAnalysisHistory(prev => 
            prev.map(s => 
              s.timestamp === latestData.timestamp 
                ? { ...s, ...aiResults }
                : s
            )
          );
        }).catch(error => {
          console.warn('[useMonitoring] Background AI failed:', error);
        });
      } catch (error) {
        console.error('[useMonitoring] Polling error:', error);
      }
    };

    pollLatestData();
    pollingIntervalRef.current = setInterval(pollLatestData, 500);

    return () => {
      isMounted = false;
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
    };
  }, [enabled, archiveMode, currentVideoTime, fetchLatestMonitoringData, loadJsonAnalysis, analyzeFrameAIAsync, fetchArchiveData, lastProcessedSequence, isLoading]);

  // Compute error trend data from analysis history
  const computeErrorTrends = useCallback((): ErrorTrendData | null => {
    if (analysisHistory.length === 0) return null;

    let blackscreenConsecutive = 0;
    let freezeConsecutive = 0;
    let audioLossConsecutive = 0;

    // Count consecutive errors from the end (most recent snapshots)
    for (let i = analysisHistory.length - 1; i >= 0; i--) {
      const analysis = analysisHistory[i].analysis;
      if (!analysis) break;

      const hasBlackscreen = analysis.blackscreen;
      const hasFreeze = analysis.freeze;
      const hasAudioLoss = !analysis.audio;

      // Count consecutive errors
      if (hasBlackscreen) {
        blackscreenConsecutive++;
      } else if (blackscreenConsecutive > 0) {
        break;
      }

      if (hasFreeze) {
        freezeConsecutive++;
      } else if (freezeConsecutive > 0) {
        break;
      }

      if (hasAudioLoss) {
        audioLossConsecutive++;
      } else if (audioLossConsecutive > 0) {
        break;
      }

      // Stop if no errors
      if (!hasBlackscreen && !hasFreeze && !hasAudioLoss) {
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

    return {
      blackscreenConsecutive,
      freezeConsecutive,
      audioLossConsecutive,
      macroblocksConsecutive: 0,
      hasWarning,
      hasError,
    };
  }, [analysisHistory]);

  // Get latest snapshot (most recent)
  const latestSnapshot = analysisHistory.length > 0 ? analysisHistory[analysisHistory.length - 1] : null;

  return {
    // Latest analysis data
    latestAnalysis: latestSnapshot?.analysis || null,
    latestSubtitleAnalysis: latestSnapshot?.subtitleAnalysis || null,
    latestLanguageMenuAnalysis: latestSnapshot?.languageMenuAnalysis || null,
    latestAIDescription: latestSnapshot?.aiDescription || null,

    // Error trend analysis
    errorTrendData: computeErrorTrends(),

    // Loading state
    isLoading,

    // Current analysis timestamp
    analysisTimestamp: latestSnapshot?.timestamp || null,
  };
};
