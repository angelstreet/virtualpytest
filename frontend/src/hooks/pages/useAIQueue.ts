import { useMemo } from 'react';
import { buildServerUrl } from '../../utils/buildUrlUtils';

export interface QueueData {
  name: string;
  length: number;
  processed: number;
  discarded: number;
  validated: number;
}

export interface AIQueueStatus {
  status: string;
  service: string;
  timestamp: string;
  stats: Record<string, any>;
  queues: {
    incidents: QueueData;
    scripts: QueueData;
  };
}

export const useAIQueue = () => {
  const getQueueStatus = useMemo(
    () => async (): Promise<AIQueueStatus> => {
      try {
        // Use backend_server proxy to get queue data from Redis
        const response = await fetch(buildServerUrl('/server/ai-queue/status'));
        
        if (!response.ok) {
          throw new Error(`Failed to fetch queue status: ${response.status}`);
        }
        
        return response.json();
      } catch (error) {
        console.error('[@hook:useAIQueue] Error fetching queue status:', error);
        throw error;
      }
    },
    [],
  );

  return {
    getQueueStatus,
  };
};
