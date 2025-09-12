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

interface UseRestartReturn {
  videoUrl: string | null;
  isGenerating: boolean;
  isReady: boolean;
  error: string | null;
  processingTime: number | null;
  // Analysis results (loaded progressively)
  audioAnalysis: any | null;
  subtitleAnalysis: any | null;
  videoDescription: string | null;
  // Analysis progress tracking
  analysisProgress: {
    audio: 'pending' | 'loading' | 'completed' | 'error';
    subtitles: 'pending' | 'loading' | 'completed' | 'error';
    description: 'pending' | 'loading' | 'completed' | 'error';
  };
  isAnalysisComplete: boolean;
}

export const useRestart = ({ host, device, includeAudioAnalysis }: UseRestartParams): UseRestartReturn => {
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isReady, setIsReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [processingTime, setProcessingTime] = useState<number | null>(null);
  
  // Analysis results (loaded progressively)
  const [audioAnalysis, setAudioAnalysis] = useState<any | null>(null);
  const [subtitleAnalysis, setSubtitleAnalysis] = useState<any | null>(null);
  const [videoDescription, setVideoDescription] = useState<string | null>(null);
  
  // Analysis progress tracking
  const [analysisProgress, setAnalysisProgress] = useState<{
    audio: 'pending' | 'loading' | 'completed' | 'error';
    subtitles: 'pending' | 'loading' | 'completed' | 'error';
    description: 'pending' | 'loading' | 'completed' | 'error';
  }>({
    audio: 'pending',
    subtitles: 'pending',
    description: 'pending',
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
            
            // Start background analysis if requested
            if (includeAudioAnalysis) {
              startBackgroundAnalysis(data.video_url);
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
            include_audio_analysis: false,  // Fast return, no analysis
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
          
          // Start background analysis if requested
          if (includeAudioAnalysis) {
            startBackgroundAnalysis(data.video_url);
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

  // Background analysis function (3 parallel calls)
  const startBackgroundAnalysis = async (videoUrl: string) => {
    console.log('[@hook:useRestart] Starting background analysis...');
    
    // Start all 3 analyses in parallel
    const audioPromise = analyzeAudio(videoUrl);
    const subtitlePromise = analyzeSubtitles(videoUrl);
    const descriptionPromise = analyzeVideoDescription(videoUrl);
    
    // Handle results as they complete
    audioPromise.then(result => {
      setAudioAnalysis(result);
      setAnalysisProgress(prev => ({ ...prev, audio: result ? 'completed' : 'error' }));
    }).catch(() => {
      setAnalysisProgress(prev => ({ ...prev, audio: 'error' }));
    });
    
    subtitlePromise.then(result => {
      setSubtitleAnalysis(result);
      setAnalysisProgress(prev => ({ ...prev, subtitles: result ? 'completed' : 'error' }));
    }).catch(() => {
      setAnalysisProgress(prev => ({ ...prev, subtitles: 'error' }));
    });
    
    descriptionPromise.then(result => {
      setVideoDescription(result);
      setAnalysisProgress(prev => ({ ...prev, description: result ? 'completed' : 'error' }));
    }).catch(() => {
      setAnalysisProgress(prev => ({ ...prev, description: 'error' }));
    });
    
    // Set loading states
    setAnalysisProgress({
      audio: 'loading',
      subtitles: 'loading', 
      description: 'loading'
    });
  };

  // Individual analysis functions
  const analyzeAudio = async (videoUrl: string) => {
    try {
      const response = await fetch(buildServerUrl('/server/verification/audio/analyzeAudio'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          host: host,
          device_id: device.device_id,
          video_url: videoUrl
        }),
      });
      const data = await response.json();
      return data.success ? data : null;
    } catch (error) {
      console.error('Audio analysis failed:', error);
      return null;
    }
  };

  const analyzeSubtitles = async (videoUrl: string) => {
    try {
      const response = await fetch(buildServerUrl('/server/verification/video/detectSubtitlesAI'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          host: host,
          device_id: device.device_id,
          video_url: videoUrl
        }),
      });
      const data = await response.json();
      return data.success ? data : null;
    } catch (error) {
      console.error('Subtitle analysis failed:', error);
      return null;
    }
  };

  const analyzeVideoDescription = async (videoUrl: string) => {
    try {
      const response = await fetch(buildServerUrl('/server/verification/video/analyzeVideoDescription'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          host: host,
          device_id: device.device_id,
          video_url: videoUrl
        }),
      });
      const data = await response.json();
      return data.success ? data.video_summary : null;
    } catch (error) {
      console.error('Video description analysis failed:', error);
      return null;
    }
  };

  const isAnalysisComplete = analysisProgress.audio !== 'pending' && analysisProgress.audio !== 'loading' &&
                            analysisProgress.subtitles !== 'pending' && analysisProgress.subtitles !== 'loading' &&
                            analysisProgress.description !== 'pending' && analysisProgress.description !== 'loading';

  return {
    videoUrl,
    isGenerating,
    isReady,
    error,
    processingTime,
    audioAnalysis,
    subtitleAnalysis,
    videoDescription,
    analysisProgress,
    isAnalysisComplete,
  };
};