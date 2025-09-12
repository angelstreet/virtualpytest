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
  transcript?: string;
  detectedLanguage?: string;
  speechDetected?: boolean;
  videoDescription?: string;
  framesAnalyzed?: number;
}

export const useRestart = ({ host, device, includeAudioAnalysis }: UseRestartParams): UseRestartReturn => {
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isReady, setIsReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [processingTime, setProcessingTime] = useState<number | null>(null);
  const [transcript, setTranscript] = useState<string | undefined>(undefined);
  const [detectedLanguage, setDetectedLanguage] = useState<string | undefined>(undefined);
  const [speechDetected, setSpeechDetected] = useState<boolean | undefined>(undefined);
  const [videoDescription, setVideoDescription] = useState<string | undefined>(undefined);
  const [framesAnalyzed, setFramesAnalyzed] = useState<number | undefined>(undefined);

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
          console.log(`[@hook:useRestart] Cached request completed for ${cacheKey}:`, data);
          if (data.success && data.video_url) {
            setVideoUrl(data.video_url);
            setProcessingTime(data.processing_time_seconds);
            setTranscript(data.transcript);
            setDetectedLanguage(data.detected_language);
            setSpeechDetected(data.speech_detected);
            setVideoDescription(data.video_description);
            setFramesAnalyzed(data.frames_analyzed);
            setIsReady(true);
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
            duration_seconds: 30,
            include_audio_analysis: includeAudioAnalysis || false,
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
          setTranscript(data.transcript);
          setDetectedLanguage(data.detected_language);
          setSpeechDetected(data.speech_detected);
          setVideoDescription(data.video_description);
          setFramesAnalyzed(data.frames_analyzed);
          setIsReady(true);
          console.log(`[@hook:useRestart] Video ready in ${data.processing_time_seconds}s`);
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

  return {
    videoUrl,
    isGenerating,
    isReady,
    error,
    processingTime,
    transcript,
    detectedLanguage,
    speechDetected,
    videoDescription,
    framesAnalyzed,
  };
};