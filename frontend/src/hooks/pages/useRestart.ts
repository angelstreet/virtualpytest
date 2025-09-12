import { useState, useEffect } from 'react';

import { Host, Device } from '../../types/common/Host_Types';

import { buildServerUrl } from '../../utils/buildUrlUtils';

// Global cache to prevent duplicate requests across component remounts
const videoGenerationCache = new Map<string, Promise<any>>();

interface UseRestartParams {
  host: Host;
  device: Device;
  includeAudioAnalysis?: boolean;
}

interface AnalysisResults {
  audio: {
    success: boolean;
    combined_transcript: string;
    detected_language: string;
    speech_detected: boolean;
    confidence: number;
    execution_time_ms: number;
  } | null;
  subtitles: {
    success: boolean;
    subtitles_detected: boolean;
    extracted_text: string;
    detected_language?: string;
    execution_time_ms: number;
  } | null;
  videoDescription: {
    frame_descriptions: string[];
    video_summary: string;
    frames_analyzed: number;
    execution_time_ms: number;
  } | null;
}

interface AnalysisProgress {
  audio: 'idle' | 'loading' | 'completed' | 'error';
  subtitles: 'idle' | 'loading' | 'completed' | 'error';
  videoDescription: 'idle' | 'loading' | 'completed' | 'error';
}

interface UseRestartReturn {
  videoUrl: string | null;
  isGenerating: boolean;
  isReady: boolean;
  error: string | null;
  processingTime: number | null;
  // Analysis results using existing routes
  analysisResults: AnalysisResults;
  analysisProgress: AnalysisProgress;
  isAnalysisComplete: boolean;
  // Manual analysis triggers
  analyzeAudio: (videoUrl: string) => Promise<any>;
  analyzeSubtitles: (videoUrl: string) => Promise<any>;
  analyzeVideoDescription: (videoUrl: string) => Promise<any>;
}

export const useRestart = ({ host, device, includeAudioAnalysis }: UseRestartParams): UseRestartReturn => {
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isReady, setIsReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [processingTime, setProcessingTime] = useState<number | null>(null);
  
  // Analysis results using new data structure
  const [analysisResults, setAnalysisResults] = useState<AnalysisResults>({
    audio: null,
    subtitles: null,
    videoDescription: null,
  });
  
  // Analysis progress tracking
  const [analysisProgress, setAnalysisProgress] = useState<AnalysisProgress>({
    audio: 'idle',
    subtitles: 'idle',
    videoDescription: 'idle',
  });

  // Generate video once on mount - use global cache to prevent duplicate requests
  useEffect(() => {
    const cacheKey = `${host.host_name}-${device.device_id}`;
    console.log(`[@hook:useRestart] Effect starting for ${cacheKey}`);

    // Check if request is already in progress
    if (videoGenerationCache.has(cacheKey)) {
      console.log(`[@hook:useRestart] Using cached request for ${cacheKey}`);
      setIsGenerating(true);
      videoGenerationCache.get(cacheKey)!
        .then((data) => {
          console.log(`[@hook:useRestart] Video ready for ${cacheKey}:`, data);
          if (data.success && data.video_url) {
            setVideoUrl(data.video_url);
            setProcessingTime(data.processing_time_seconds);
            setIsReady(true);
            
            // Process analysis data if available
            if (includeAudioAnalysis && data.analysis_data) {
              processAnalysisData(data.analysis_data);
            }
          } else {
            setError(data.error || 'Video generation failed');
          }
        })
        .catch((err) => {
          console.log(`[@hook:useRestart] Cached request failed for ${cacheKey}:`, err);
          setError(err instanceof Error ? err.message : 'Video generation failed');
        })
        .finally(() => {
          setIsGenerating(false);
        });
      return;
    }

    // Start new request
    setIsGenerating(true);
    setError(null);

    const generateVideo = async () => {
      try {
        console.log(`[@hook:useRestart] Starting new request for ${cacheKey}`);

        const response = await fetch(buildServerUrl('/server/av/generateRestartVideo'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            host: host,
            device_id: device.device_id || 'device1',
            duration_seconds: 10,  // Fixed 10 seconds
            include_audio_analysis: includeAudioAnalysis || false,  // Enable background analysis
          }),
        });

        console.log(`[@hook:useRestart] Response received: ${response.status}`);

        if (!response.ok) {
          throw new Error(`Failed to generate video: ${response.status}`);
        }

        const data = await response.json();
        console.log(`[@hook:useRestart] Response data:`, data);
        
        return data;
      } catch (err) {
        console.log(`[@hook:useRestart] Request failed:`, err);
        throw err;
      }
    };

    // Cache the promise
    const requestPromise = generateVideo();
    videoGenerationCache.set(cacheKey, requestPromise);

    // Handle the response
    requestPromise
      .then((data) => {
        if (data.success && data.video_url) {
          setVideoUrl(data.video_url);
          setProcessingTime(data.processing_time_seconds);
          setIsReady(true);
          console.log(`[@hook:useRestart] Video ready in ${data.processing_time_seconds}s`);
          
          // Process analysis data if available
          if (includeAudioAnalysis && data.analysis_data) {
            processAnalysisData(data.analysis_data);
          }
        } else {
          throw new Error(data.error || 'Video generation failed');
        }
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : 'Video generation failed');
      })
      .finally(() => {
        setIsGenerating(false);
        // Clean up cache after completion
        setTimeout(() => {
          videoGenerationCache.delete(cacheKey);
        }, 1000);
      });

    return () => {
      console.log(`[@hook:useRestart] Effect cleanup for ${cacheKey}`);
      // Don't cancel the request, let it complete for other instances
    };
  }, []); // No dependencies - generate once only

  // Process analysis data from backend response
  const processAnalysisData = (data: any) => {
    try {
      console.log('[@hook:useRestart] Processing analysis data from backend:', data);
      
      // Extract audio analysis if available
      if (data.audio_analysis) {
        setAnalysisResults(prev => ({
          ...prev,
          audio: {
            success: data.audio_analysis.success,
            combined_transcript: data.audio_analysis.combined_transcript || '',
            detected_language: data.audio_analysis.detected_language || 'unknown',
            speech_detected: data.audio_analysis.speech_detected || false,
            confidence: data.audio_analysis.confidence || 0,
            execution_time_ms: data.audio_analysis.execution_time_ms || 0,
          }
        }));
        setAnalysisProgress(prev => ({ ...prev, audio: 'completed' }));
      }
      
      // Use screenshot URLs for frontend analysis if available
      if (data.screenshot_urls && data.screenshot_urls.length > 0) {
        // Trigger frontend analysis using existing routes
        analyzeScreenshotsForSubtitles(data.screenshot_urls);
        analyzeScreenshotsForDescription(data.screenshot_urls);
      }
      
    } catch (error) {
      console.error('[@hook:useRestart] Error processing analysis data:', error);
    }
  };

  // Analyze screenshots for subtitles using existing route
  const analyzeScreenshotsForSubtitles = async (screenshotUrls: string[]) => {
    try {
      setAnalysisProgress(prev => ({ ...prev, subtitles: 'loading' }));
      
      // Use middle screenshot (same as backend logic)
      const middleIndex = Math.floor(screenshotUrls.length / 2);
      const middleScreenshot = screenshotUrls[middleIndex];
      
      const startTime = Date.now();
      const result = await analyzeSubtitles(middleScreenshot);
      const executionTime = Date.now() - startTime;
      
      if (result) {
        setAnalysisResults(prev => ({
          ...prev,
          subtitles: {
            success: result.success,
            subtitles_detected: result.subtitles_detected || false,
            extracted_text: result.extracted_text || '',
            detected_language: result.detected_language,
            execution_time_ms: executionTime,
          }
        }));
        setAnalysisProgress(prev => ({ ...prev, subtitles: 'completed' }));
      } else {
        setAnalysisProgress(prev => ({ ...prev, subtitles: 'error' }));
      }
    } catch (error) {
      console.error('[@hook:useRestart] Subtitle analysis error:', error);
      setAnalysisProgress(prev => ({ ...prev, subtitles: 'error' }));
    }
  };

  // Analyze screenshots for description using existing route
  const analyzeScreenshotsForDescription = async (screenshotUrls: string[]) => {
    try {
      setAnalysisProgress(prev => ({ ...prev, videoDescription: 'loading' }));
      
      // Take every 2nd screenshot for analysis (up to 10 frames)
      const selectedScreenshots = screenshotUrls.filter((_, index) => index % 2 === 0).slice(0, 10);
      
      const startTime = Date.now();
      const frameDescriptions: string[] = [];
      
      // Analyze each screenshot using existing analyzeImageAI route
      for (let i = 0; i < selectedScreenshots.length; i++) {
        try {
          const result = await analyzeVideoDescription(selectedScreenshots[i]);
          if (result) {
            frameDescriptions.push(`Second ${i + 1}: ${result}`);
          }
        } catch (error) {
          console.error(`[@hook:useRestart] Frame ${i + 1} analysis failed:`, error);
          frameDescriptions.push(`Second ${i + 1}: Analysis failed`);
        }
      }
      
      // Generate summary from frame descriptions
      const videoSummary = frameDescriptions.length > 0 
        ? `Video contains ${frameDescriptions.length} analyzed frames with various activities.`
        : 'No frame descriptions available';
      
      const executionTime = Date.now() - startTime;
      
      setAnalysisResults(prev => ({
        ...prev,
        videoDescription: {
          frame_descriptions: frameDescriptions,
          video_summary: videoSummary,
          frames_analyzed: frameDescriptions.length,
          execution_time_ms: executionTime,
        }
      }));
      setAnalysisProgress(prev => ({ ...prev, videoDescription: 'completed' }));
      
    } catch (error) {
      console.error('[@hook:useRestart] Video description analysis error:', error);
      setAnalysisProgress(prev => ({ ...prev, videoDescription: 'error' }));
    }
  };

  // Individual analysis functions using existing routes
  const analyzeAudio = async (_videoUrl: string) => {
    // Audio analysis is handled by backend, this is just for manual triggers
    console.log('[@hook:useRestart] Audio analysis handled by backend');
    return null;
  };

  const analyzeSubtitles = async (imageUrl: string) => {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 15000); // 15 second timeout
      
      const response = await fetch(buildServerUrl('/server/verification/video/detectSubtitlesAI'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          host: host,
          device_id: device.device_id,
          image_source_url: imageUrl,  // Use existing image-based parameter
          extract_text: true,
        }),
        signal: controller.signal
      });
      
      clearTimeout(timeoutId);
      const data = await response.json();
      return data.success ? data : null;
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        console.error('[@hook:useRestart] Subtitle analysis timed out after 15 seconds');
      } else {
        console.error('[@hook:useRestart] Subtitle analysis failed:', error);
      }
      return null;
    }
  };

  const analyzeVideoDescription = async (imageUrl: string) => {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 20000); // 20 second timeout
      
      const response = await fetch(buildServerUrl('/server/verification/video/analyzeImageAI'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          host: host,
          device_id: device.device_id,
          image_source_url: imageUrl,  // Use existing image-based parameter
          prompt: 'Describe what you see in this frame in 1-2 sentences',
        }),
        signal: controller.signal
      });
      
      clearTimeout(timeoutId);
      const data = await response.json();
      return data.success ? data.response : null;
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        console.error('[@hook:useRestart] Video description analysis timed out after 20 seconds');
      } else {
        console.error('[@hook:useRestart] Video description analysis failed:', error);
      }
      return null;
    }
  };

  const isAnalysisComplete = analysisProgress.audio !== 'idle' && analysisProgress.audio !== 'loading' &&
                            analysisProgress.subtitles !== 'idle' && analysisProgress.subtitles !== 'loading' &&
                            analysisProgress.videoDescription !== 'idle' && analysisProgress.videoDescription !== 'loading';

  return {
    videoUrl,
    isGenerating,
    isReady,
    error,
    processingTime,
    analysisResults,
    analysisProgress,
    isAnalysisComplete,
    analyzeAudio,
    analyzeSubtitles,
    analyzeVideoDescription,
  };
};