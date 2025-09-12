import { useState, useEffect, useCallback, useMemo } from 'react';

import { Host, Device } from '../../types/common/Host_Types';
import { buildServerUrl } from '../../utils/buildUrlUtils';

// =====================================================
// TYPES & INTERFACES
// =====================================================

interface UseRestartParams {
  host: Host;
  device: Device;
  includeAudioAnalysis?: boolean;
}

interface AudioAnalysis {
  success: boolean;
  combined_transcript: string;
  detected_language: string;
  speech_detected: boolean;
  confidence: number;
  execution_time_ms: number;
}

interface SubtitleAnalysis {
  success: boolean;
  subtitles_detected: boolean;
  extracted_text: string;
  detected_language?: string;
  execution_time_ms: number;
}

interface VideoDescriptionAnalysis {
  frame_descriptions: string[];
  video_summary: string;
  frames_analyzed: number;
  execution_time_ms: number;
}

interface AnalysisResults {
  audio: AudioAnalysis | null;
  subtitles: SubtitleAnalysis | null;
  videoDescription: VideoDescriptionAnalysis | null;
}

type AnalysisState = 'idle' | 'loading' | 'completed' | 'error';

interface AnalysisProgress {
  audio: AnalysisState;
  subtitles: AnalysisState;
  videoDescription: AnalysisState;
}

interface BackendAnalysisData {
  audio_analysis?: {
    success: boolean;
    combined_transcript: string;
    detected_language: string;
    speech_detected: boolean;
    confidence: number;
    segments_analyzed: number;
  };
  subtitle_analysis?: {
    success: boolean;
    subtitles_detected: boolean;
    extracted_text: string;
    detected_language: string;
    confidence: number;
    frames_analyzed: number;
  };
  video_analysis?: {
    success: boolean;
    frame_descriptions: string[];
    video_summary: string;
    frames_analyzed: number;
  };
  screenshot_urls?: string[];
  video_id?: string;
  analysis_complete?: boolean;
}

interface BackendResponse {
  success: boolean;
  video_url?: string;
  processing_time_seconds?: number;
  analysis_data?: BackendAnalysisData;
  error?: string;
}

interface UseRestartReturn {
  // Core video state
  videoUrl: string | null;
  isGenerating: boolean;
  isReady: boolean;
  error: string | null;
  processingTime: number | null;
  
  // Analysis state
  analysisResults: AnalysisResults;
  analysisProgress: AnalysisProgress;
  isAnalysisComplete: boolean;
  
  // Manual analysis triggers
  analyzeAudio: (videoUrl: string) => Promise<any>;
  analyzeSubtitles: (videoUrl: string) => Promise<any>;
  analyzeVideoDescription: (videoUrl: string) => Promise<any>;
  
  // Utility functions
  regenerateVideo: () => Promise<void>;
}

// =====================================================
// CACHE MANAGEMENT
// =====================================================

interface CacheEntry {
  promise: Promise<BackendResponse>;
  timestamp: number;
}

class VideoGenerationCache {
  private cache = new Map<string, CacheEntry>();
  private readonly CACHE_TTL = 30000; // 30 seconds

  private generateKey(host: Host, device: Device): string {
    return `${host.host_name}-${device.device_id}`;
  }

  private isExpired(entry: CacheEntry): boolean {
    return Date.now() - entry.timestamp > this.CACHE_TTL;
  }

  get(host: Host, device: Device): Promise<BackendResponse> | null {
    const key = this.generateKey(host, device);
    const entry = this.cache.get(key);
    
    if (!entry || this.isExpired(entry)) {
      this.cache.delete(key);
      return null;
    }
    
    return entry.promise;
  }

  set(host: Host, device: Device, promise: Promise<BackendResponse>): void {
    const key = this.generateKey(host, device);
    this.cache.set(key, {
      promise,
      timestamp: Date.now()
    });
  }

  delete(host: Host, device: Device): void {
    const key = this.generateKey(host, device);
    this.cache.delete(key);
  }

  clear(): void {
    this.cache.clear();
  }
}

// Global cache instance
const videoCache = new VideoGenerationCache();

// =====================================================
// MAIN HOOK IMPLEMENTATION
// =====================================================

export const useRestart = ({ host, device, includeAudioAnalysis }: UseRestartParams): UseRestartReturn => {
  // =====================================================
  // STATE MANAGEMENT
  // =====================================================
  
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isReady, setIsReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [processingTime, setProcessingTime] = useState<number | null>(null);
  
  const [analysisResults, setAnalysisResults] = useState<AnalysisResults>({
    audio: null,
    subtitles: null,
    videoDescription: null,
  });
  
  const [analysisProgress, setAnalysisProgress] = useState<AnalysisProgress>({
    audio: 'idle',
    subtitles: 'idle',
    videoDescription: 'idle',
  });

  // =====================================================
  // CORE FUNCTIONS
  // =====================================================

  const processBackendAnalysis = useCallback((analysisData: BackendAnalysisData) => {
    console.log('[@hook:useRestart] Processing backend analysis data:', analysisData);
    
    // Process audio analysis from backend
    if (analysisData.audio_analysis) {
      const audioData = analysisData.audio_analysis;
      setAnalysisResults(prev => ({
        ...prev,
        audio: {
          success: audioData.success,
          combined_transcript: audioData.combined_transcript || '',
          detected_language: audioData.detected_language || 'unknown',
          speech_detected: audioData.speech_detected || false,
          confidence: audioData.confidence || 0,
          execution_time_ms: 0, // Backend processing time not tracked
        }
      }));
      setAnalysisProgress(prev => ({ ...prev, audio: 'completed' }));
    }
    
    // Process subtitle analysis from backend
    if (analysisData.subtitle_analysis) {
      const subtitleData = analysisData.subtitle_analysis;
      setAnalysisResults(prev => ({
        ...prev,
        subtitles: {
          success: subtitleData.success,
          subtitles_detected: subtitleData.subtitles_detected || false,
          extracted_text: subtitleData.extracted_text || '',
          detected_language: subtitleData.detected_language || 'unknown',
          execution_time_ms: 0,
        }
      }));
      setAnalysisProgress(prev => ({ ...prev, subtitles: 'completed' }));
    }
    
    // Process video description analysis from backend
    if (analysisData.video_analysis) {
      const videoData = analysisData.video_analysis;
      setAnalysisResults(prev => ({
        ...prev,
        videoDescription: {
          frame_descriptions: videoData.frame_descriptions || [],
          video_summary: videoData.video_summary || '',
          frames_analyzed: videoData.frames_analyzed || 0,
          execution_time_ms: 0,
        }
      }));
      setAnalysisProgress(prev => ({ ...prev, videoDescription: 'completed' }));
    }
    
    // If no subtitle or video analysis provided, mark as completed anyway
    if (!analysisData.subtitle_analysis) {
      setAnalysisProgress(prev => ({ ...prev, subtitles: 'completed' }));
    }
    if (!analysisData.video_analysis) {
      setAnalysisProgress(prev => ({ ...prev, videoDescription: 'completed' }));
    }
    
    console.log('[@hook:useRestart] All analysis processing complete');
  }, []);

  const triggerAsyncAnalysis = useCallback(async (videoId: string, screenshotUrls: string[]) => {
    console.log('[@hook:useRestart] Triggering async analysis for video ID:', videoId);
    
    try {
      setAnalysisProgress(prev => ({
        ...prev,
        subtitles: 'loading',
        videoDescription: 'loading'
      }));

      const response = await fetch(buildServerUrl('/server/av/analyzeRestartVideo'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          host,
          device_id: device.device_id || 'device1',
          video_id: videoId,
          screenshot_urls: screenshotUrls,
        }),
      });

      if (!response.ok) {
        throw new Error(`Async analysis failed: ${response.status} ${response.statusText}`);
      }

      const asyncData = await response.json();
      
      if (asyncData.success && asyncData.analysis_data) {
        console.log('[@hook:useRestart] Async analysis completed:', asyncData.analysis_data);
        processBackendAnalysis(asyncData.analysis_data);
      } else {
        throw new Error(asyncData.error || 'Async analysis failed');
      }

    } catch (error) {
      console.error('[@hook:useRestart] Async analysis error:', error);
      // Mark as completed even on error to avoid infinite loading
      setAnalysisProgress(prev => ({
        ...prev,
        subtitles: 'error',
        videoDescription: 'error'
      }));
    }
  }, [host, device.device_id, processBackendAnalysis]);

  const generateVideoRequest = useCallback(async (): Promise<BackendResponse> => {
    const response = await fetch(buildServerUrl('/server/av/generateRestartVideo'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        host,
        device_id: device.device_id || 'device1',
        duration_seconds: 10,
        include_audio_analysis: includeAudioAnalysis || false,
      }),
    });

    if (!response.ok) {
      throw new Error(`Video generation failed: ${response.status} ${response.statusText}`);
    }

    const data: BackendResponse = await response.json();
    
    // Handle different response formats from backend
    if (typeof data === 'object' && data.success === true) {
      return data;
    } else if (typeof data === 'string') {
      // Legacy format: just video URL
      return {
        success: true,
        video_url: data,
        processing_time_seconds: 0
      };
    } else {
      throw new Error(data.error || 'Video generation failed');
    }
  }, [host, device.device_id, includeAudioAnalysis]);

  const executeVideoGeneration = useCallback(async () => {
    console.log(`[@hook:useRestart] Starting video generation for ${host.host_name}-${device.device_id}`);
    
    setIsGenerating(true);
    setError(null);
    setIsReady(false);

    try {
      // Check cache first
      const cachedPromise = videoCache.get(host, device);
      let responsePromise: Promise<BackendResponse>;

      if (cachedPromise) {
        console.log('[@hook:useRestart] Using cached request');
        responsePromise = cachedPromise;
      } else {
        console.log('[@hook:useRestart] Starting new request');
        responsePromise = generateVideoRequest();
        videoCache.set(host, device, responsePromise);
      }

      const data = await responsePromise;
      
      console.log('[@hook:useRestart] Video generation completed:', data);

      // Set video data
      setVideoUrl(data.video_url || null);
      setProcessingTime(data.processing_time_seconds || null);
      setIsReady(true);

      // Process analysis data if available
      if (includeAudioAnalysis && data.analysis_data) {
        processBackendAnalysis(data.analysis_data);
        
        // Trigger async analysis if video_id and screenshot_urls are available
        if (data.analysis_data.video_id && data.analysis_data.screenshot_urls) {
          triggerAsyncAnalysis(data.analysis_data.video_id, data.analysis_data.screenshot_urls);
        }
      }

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Video generation failed';
      console.error('[@hook:useRestart] Video generation error:', errorMessage);
      setError(errorMessage);
    } finally {
      setIsGenerating(false);
      // Clean up cache after a delay
      setTimeout(() => {
        videoCache.delete(host, device);
      }, 5000);
    }
  }, [host, device, includeAudioAnalysis, generateVideoRequest, processBackendAnalysis]);

  // =====================================================
  // EFFECTS
  // =====================================================

  useEffect(() => {
    executeVideoGeneration();
  }, [executeVideoGeneration]);

  // =====================================================
  // ANALYSIS FUNCTIONS
  // =====================================================

  // Screenshot analysis functions removed - backend provides comprehensive analysis

  // =====================================================
  // PUBLIC API FUNCTIONS
  // =====================================================

  const analyzeAudio = useCallback(async (_videoUrl: string) => {
    console.log('[@hook:useRestart] Audio analysis is handled by backend during video generation');
    return null;
  }, []);

  const analyzeSubtitles = useCallback(async (_imageUrl: string) => {
    console.log('[@hook:useRestart] Subtitle analysis is handled by backend during video generation');
    return null;
  }, []);

  const analyzeVideoDescription = useCallback(async (_imageUrl: string) => {
    console.log('[@hook:useRestart] Video description analysis is handled by backend during video generation');
    return null;
  }, []);

  const regenerateVideo = useCallback(async () => {
    videoCache.delete(host, device);
    await executeVideoGeneration();
  }, [host, device, executeVideoGeneration]);

  // =====================================================
  // COMPUTED VALUES
  // =====================================================

  const isAnalysisComplete = useMemo(() => {
    if (!includeAudioAnalysis) return true;
    
    return analysisProgress.audio !== 'idle' && analysisProgress.audio !== 'loading' &&
           analysisProgress.subtitles !== 'idle' && analysisProgress.subtitles !== 'loading' &&
           analysisProgress.videoDescription !== 'idle' && analysisProgress.videoDescription !== 'loading';
  }, [analysisProgress, includeAudioAnalysis]);

  // =====================================================
  // RETURN API
  // =====================================================

  return {
    // Core video state
    videoUrl,
    isGenerating,
    isReady,
    error,
    processingTime,
    
    // Analysis state
    analysisResults,
    analysisProgress,
    isAnalysisComplete,
    
    // Manual analysis triggers
    analyzeAudio,
    analyzeSubtitles,
    analyzeVideoDescription,
    
    // Utility functions
    regenerateVideo,
  };
};