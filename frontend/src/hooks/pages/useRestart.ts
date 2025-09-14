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
  frame_subtitles?: string[];
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
  video: AnalysisState;
  audio: AnalysisState;
  subtitles: AnalysisState;
  summary: AnalysisState;
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
    frame_subtitles?: string[];
  };
  video_analysis?: {
    success: boolean;
    frame_descriptions: string[];
    video_summary: string;
    frames_analyzed: number;
  };
  screenshot_urls?: string[];
  video_id?: string;
  segment_count?: number;
  analysis_complete?: boolean;
}

interface BackendResponse {
  success: boolean;
  video_url?: string;
  processing_time_seconds?: number;
  analysis_data?: BackendAnalysisData;
  report_url?: string;
  error?: string;
}

interface UseRestartReturn {
  // Core video state
  videoUrl: string | null;
  isGenerating: boolean;
  isReady: boolean;
  error: string | null;
  processingTime: number | null;
  reportUrl: string | null;
  
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
  const [processingTime] = useState<number | null>(null);
  const [reportUrl] = useState<string | null>(null);
  
  const [analysisResults, setAnalysisResults] = useState<AnalysisResults>({
    audio: null,
    subtitles: null,
    videoDescription: null,
  });
  
  const [analysisProgress, setAnalysisProgress] = useState<AnalysisProgress>({
    video: 'idle',
    audio: 'idle',
    subtitles: 'idle',
    summary: 'idle',
  });

  // =====================================================
  // CORE FUNCTIONS
  // =====================================================


  const executeVideoGeneration = useCallback(async () => {
    console.log(`[@hook:useRestart] Starting 4-stage video generation for ${host.host_name}-${device.device_id}`);
    
    setIsGenerating(true);
    setError(null);
    setIsReady(false);
    setAnalysisProgress({ video: 'loading', audio: 'idle', subtitles: 'idle', summary: 'idle' });

    try {
      // Stage 1: Generate video only (fast)
      const videoResponse = await fetch(buildServerUrl('/server/av/generateRestartVideo'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          host,
          device_id: device.device_id || 'device1',
          duration_seconds: 10,
        }),
      });

      if (!videoResponse.ok) throw new Error(`Video generation failed: ${videoResponse.status}`);
      const videoData = await videoResponse.json();
      
      if (!videoData.success) throw new Error(videoData.error || 'Video generation failed');

      // Video ready - show immediately
      setVideoUrl(videoData.video_url);
      setIsReady(true);
      setIsGenerating(false);
      setAnalysisProgress(prev => ({ ...prev, video: 'completed' }));

      if (!includeAudioAnalysis) return;

      // Stage 2-4: Run analysis sequentially (no race conditions)
      console.log(`[@hook:useRestart] Starting sequential analysis for video_id: ${videoData.video_id}`);
      
      try {
        // Step 2: Audio Analysis
        console.log(`[@hook:useRestart] Step 2: Starting audio analysis`);
        setAnalysisProgress(prev => ({ ...prev, audio: 'loading' }));
        
        const audioResponse = await fetch(buildServerUrl('/server/av/analyzeRestartAudio'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            host,
            device_id: device.device_id || 'device1',
            video_id: videoData.video_id,
          }),
        });
        
        const audioData = await audioResponse.json();
        if (audioData.success && audioData.audio_analysis) {
          setAnalysisResults(prev => ({ ...prev, audio: {
            success: audioData.audio_analysis.success,
            combined_transcript: audioData.audio_analysis.combined_transcript || '',
            detected_language: audioData.audio_analysis.detected_language || 'unknown',
            speech_detected: audioData.audio_analysis.speech_detected || false,
            confidence: audioData.audio_analysis.confidence || 0,
            execution_time_ms: 0,
          }}));
        }
        setAnalysisProgress(prev => ({ ...prev, audio: audioData.success ? 'completed' : 'error' }));
        console.log(`[@hook:useRestart] Step 2: Audio analysis ${audioData.success ? 'completed' : 'failed'}`);
        
        // Step 3: Subtitle Analysis
        console.log(`[@hook:useRestart] Step 3: Starting subtitle analysis`);
        setAnalysisProgress(prev => ({ ...prev, subtitles: 'loading' }));
        
        const subtitleResponse = await fetch(buildServerUrl('/server/av/analyzeRestartSubtitles'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            host,
            device_id: device.device_id || 'device1',
            video_id: videoData.video_id,
            screenshot_urls: videoData.screenshot_urls || [],
          }),
        });
        
        const subtitleData = await subtitleResponse.json();
        if (subtitleData.success && subtitleData.subtitle_analysis) {
          setAnalysisResults(prev => ({ ...prev, subtitles: {
            success: subtitleData.subtitle_analysis.success,
            subtitles_detected: subtitleData.subtitle_analysis.subtitles_detected || false,
            extracted_text: subtitleData.subtitle_analysis.extracted_text || '',
            detected_language: subtitleData.subtitle_analysis.detected_language || 'unknown',
            execution_time_ms: 0,
            frame_subtitles: subtitleData.subtitle_analysis.frame_subtitles || [],
          }}));
        }
        setAnalysisProgress(prev => ({ ...prev, subtitles: subtitleData.success ? 'completed' : 'error' }));
        console.log(`[@hook:useRestart] Step 3: Subtitle analysis ${subtitleData.success ? 'completed' : 'failed'}`);
        
        // Step 4: Summary Analysis
        console.log(`[@hook:useRestart] Step 4: Starting summary analysis`);
        setAnalysisProgress(prev => ({ ...prev, summary: 'loading' }));
        
        const summaryResponse = await fetch(buildServerUrl('/server/av/analyzeRestartSummary'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            host,
            device_id: device.device_id || 'device1',
            video_id: videoData.video_id,
            screenshot_urls: videoData.screenshot_urls || [],
          }),
        });
        
        const summaryData = await summaryResponse.json();
        if (summaryData.success && summaryData.video_analysis) {
          setAnalysisResults(prev => ({ ...prev, videoDescription: {
            frame_descriptions: summaryData.video_analysis.frame_descriptions || [],
            video_summary: summaryData.video_analysis.video_summary || '',
            frames_analyzed: summaryData.video_analysis.frames_analyzed || 0,
            execution_time_ms: 0,
          }}));
        }
        setAnalysisProgress(prev => ({ ...prev, summary: summaryData.success ? 'completed' : 'error' }));
        console.log(`[@hook:useRestart] Step 4: Summary analysis ${summaryData.success ? 'completed' : 'failed'}`);
        
        console.log(`[@hook:useRestart] All analysis steps completed`);
        
      } catch (analysisError) {
        console.error(`[@hook:useRestart] Analysis error:`, analysisError);
        // Don't fail the entire process if analysis fails - video is still playable
        setAnalysisProgress(prev => ({
          ...prev,
          audio: prev.audio === 'loading' ? 'error' : prev.audio,
          subtitles: prev.subtitles === 'loading' ? 'error' : prev.subtitles,
          summary: prev.summary === 'loading' ? 'error' : prev.summary,
        }));
      }

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Video generation failed';
      console.error('[@hook:useRestart] Video generation error:', errorMessage);
      setError(errorMessage);
      setIsGenerating(false);
      setAnalysisProgress({ video: 'error', audio: 'idle', subtitles: 'idle', summary: 'idle' });
    }
  }, [host, device, includeAudioAnalysis]);

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
           analysisProgress.summary !== 'idle' && analysisProgress.summary !== 'loading';
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
    reportUrl,
    
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