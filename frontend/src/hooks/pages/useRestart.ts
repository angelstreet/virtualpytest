import { useState, useEffect, useCallback } from 'react';

import { Host, Device } from '../../types/common/Host_Types';

import { buildServerUrl } from '../../utils/buildUrlUtils';

interface UseRestartParams {
  host: Host;
  device: Device;
}

interface UseRestartReturn {
  videoUrl: string | null;
  isGenerating: boolean;
  isReady: boolean;
  error: string | null;
  processingTime: number | null;
}

export const useRestart = ({ host, device }: UseRestartParams): UseRestartReturn => {
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isReady, setIsReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [processingTime, setProcessingTime] = useState<number | null>(null);

  // Generate video once on mount - no dependencies to prevent re-generation
  useEffect(() => {
    let cancelled = false;

    const generateVideo = async () => {
      if (cancelled) return;
      
      setIsGenerating(true);
      setError(null);
      
      try {
        console.log(`[@hook:useRestart] Generating restart video for ${host.host_name}-${device.device_id}`);

        const response = await fetch(buildServerUrl('/server/av/generateRestartVideo'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            host: host,
            device_id: device.device_id || 'device1',
            duration_seconds: 30,
          }),
        });

        if (!response.ok) {
          throw new Error(`Failed to generate video: ${response.status}`);
        }

        const data = await response.json();
        
        if (cancelled) return;

        if (data.success && data.video_url) {
          setVideoUrl(data.video_url);
          setProcessingTime(data.processing_time_seconds);
          setIsReady(true);
          console.log(`[@hook:useRestart] Video ready in ${data.processing_time_seconds}s`);
        } else {
          throw new Error(data.error || 'Video generation failed');
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Video generation failed');
        }
      } finally {
        if (!cancelled) {
          setIsGenerating(false);
        }
      }
    };

    generateVideo();

    return () => {
      cancelled = true;
    };
  }, []); // No dependencies - generate once only

  return {
    videoUrl,
    isGenerating,
    isReady,
    error,
    processingTime,
  };
};