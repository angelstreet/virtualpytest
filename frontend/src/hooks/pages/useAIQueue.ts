import { useMemo } from 'react';
import { buildServerUrl } from '../../utils/buildUrlUtils';

export interface QueueItem {
  id: string;
  type: string;
  data: any;
  created_at: string;
}

export interface QueueData {
  name: string;
  length: number;
  processed: number;
  discarded: number;
  validated: number;
  items?: QueueItem[];
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
    () => async (includeItems: boolean = false): Promise<AIQueueStatus> => {
      try {
        // Use backend_server proxy to get queue data from Redis
        const url = buildServerUrl(`/server/ai-queue/status${includeItems ? '?include_items=true' : ''}`);
        const response = await fetch(url);
        
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

  const clearQueues = useMemo(
    () => async (queueType: 'incidents' | 'scripts' | 'all' = 'all'): Promise<void> => {
      try {
        console.log(`[@hook:useAIQueue:clearQueues] Clearing ${queueType} queue(s)`);

        const response = await fetch(buildServerUrl('/server/ai-queue/clear'), {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            queue_type: queueType,
          }),
        });

        if (!response.ok) {
          throw new Error(`Failed to clear queues: ${response.status}`);
        }

        const result = await response.json();
        console.log('[@hook:useAIQueue:clearQueues] Success:', result);
      } catch (error) {
        console.error('[@hook:useAIQueue:clearQueues] Error:', error);
        throw error;
      }
    },
    [],
  );

  return {
    getQueueStatus,
    clearQueues,
  };
};
