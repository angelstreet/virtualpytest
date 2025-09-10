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

  // Generate 5-minute MP4 video from HLS segments
  const generateRestartVideo = useCallback(async () => {
    try {
      setIsGenerating(true);
      setError(null);
      setVideoUrl(null);
      setIsReady(false);
      
      console.log(
        `[@hook:useRestart] Generating 5-minute restart video for ${host.host_name}-${device.device_id}`,
      );

      const response = await fetch(buildServerUrl('/server/av/generateRestartVideo'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          host: host,
          device_id: device.device_id || 'device1',
          duration_minutes: 5,
        }),
      });

      if (!response.ok) {
        throw new Error(`Failed to generate video: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();

      if (data.success && data.video_url) {
        console.log(
          `[@hook:useRestart] Successfully generated restart video in ${data.processing_time_seconds}s`,
        );

        setVideoUrl(data.video_url);
        setProcessingTime(data.processing_time_seconds);
        setIsReady(true);
      } else {
        throw new Error(data.error || 'Failed to generate restart video');
      }
    } catch (error) {
      console.error(`[@hook:useRestart] Error generating video:`, error);
      setError(error instanceof Error ? error.message : 'Failed to generate restart video');
    } finally {
      setIsGenerating(false);
    }
  }, [host, device.device_id]);

  // Generate video on mount
  useEffect(() => {
    generateRestartVideo();
  }, [generateRestartVideo]);

  return {
    videoUrl,
    isGenerating,
    isReady,
    error,
    processingTime,
  };
};