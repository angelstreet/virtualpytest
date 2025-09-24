import { useState, useEffect, useCallback } from 'react';
import { buildServerUrl } from '../utils/buildUrlUtils';

export interface DeviceFlag {
  id: string;
  host_name: string;
  device_id: string;
  device_name: string;
  flags: string[];
  created_at: string;
  updated_at: string;
}

interface UseDeviceFlagsReturn {
  deviceFlags: DeviceFlag[];
  uniqueFlags: string[];
  isLoading: boolean;
  error: string | null;
  updateDeviceFlags: (hostName: string, deviceId: string, flags: string[]) => Promise<boolean>;
  batchUpdateDeviceFlags: (updates: Array<{ hostName: string; deviceId: string; flags: string[] }>) => Promise<boolean>;
  refreshFlags: () => Promise<void>;
}

export const useDeviceFlags = (): UseDeviceFlagsReturn => {
  const [deviceFlags, setDeviceFlags] = useState<DeviceFlag[]>([]);
  const [uniqueFlags, setUniqueFlags] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchBatchFlags = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      // Use the new batch endpoint to get both device flags and unique flags in one request
      const response = await fetch(buildServerUrl('/server/device-flags/batch'));
      if (!response.ok) {
        throw new Error(`Failed to fetch device flags: ${response.statusText}`);
      }

      const result = await response.json();
      if (result.success) {
        setDeviceFlags(result.data.device_flags || []);
        setUniqueFlags(result.data.unique_flags || []);
      } else {
        throw new Error(result.error || 'Failed to fetch device flags');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      console.error('Error fetching device flags:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const updateDeviceFlags = useCallback(async (hostName: string, deviceId: string, flags: string[]): Promise<boolean> => {
    try {
      const response = await fetch(buildServerUrl(`/server/device-flags/${hostName}/${deviceId}`), {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ flags }),
      });

      if (!response.ok) {
        throw new Error(`Failed to update device flags: ${response.statusText}`);
      }

      const result = await response.json();
      if (result.success) {
        // Update local state
        setDeviceFlags(prev => 
          prev.map(df => 
            df.host_name === hostName && df.device_id === deviceId 
              ? { ...df, flags, updated_at: new Date().toISOString() }
              : df
          )
        );
        
        // Recalculate unique flags from updated device flags
        const allFlags = new Set<string>();
        deviceFlags.forEach(df => {
          if (df.host_name === hostName && df.device_id === deviceId) {
            flags.forEach(flag => allFlags.add(flag));
          } else {
            df.flags.forEach(flag => allFlags.add(flag));
          }
        });
        setUniqueFlags(Array.from(allFlags).sort());
        
        return true;
      } else {
        throw new Error(result.error || 'Failed to update device flags');
      }
    } catch (err) {
      console.error('Error updating device flags:', err);
      setError(err instanceof Error ? err.message : 'Unknown error');
      return false;
    }
  }, [deviceFlags]);

  const batchUpdateDeviceFlags = useCallback(async (updates: Array<{ hostName: string; deviceId: string; flags: string[] }>): Promise<boolean> => {
    try {
      const promises = updates.map(({ hostName, deviceId, flags }) =>
        fetch(buildServerUrl(`/server/device-flags/${hostName}/${deviceId}`), {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ flags }),
        })
      );

      const responses = await Promise.all(promises);
      
      // Check if all requests succeeded
      const allSuccessful = responses.every(response => response.ok);
      
      if (allSuccessful) {
        // Parse all results
        const results = await Promise.all(responses.map(response => response.json()));
        const allResultsSuccessful = results.every(result => result.success);
        
        if (allResultsSuccessful) {
          // Update local state for all changes
          setDeviceFlags(prev => {
            const updated = [...prev];
            updates.forEach(({ hostName, deviceId, flags }) => {
              const index = updated.findIndex(df => df.host_name === hostName && df.device_id === deviceId);
              if (index >= 0) {
                updated[index] = { ...updated[index], flags, updated_at: new Date().toISOString() };
              }
            });
            return updated;
          });
          
          // Recalculate unique flags
          const allFlags = new Set<string>();
          deviceFlags.forEach(df => {
            const update = updates.find(u => u.hostName === df.host_name && u.deviceId === df.device_id);
            const flagsToUse = update ? update.flags : df.flags;
            flagsToUse.forEach(flag => allFlags.add(flag));
          });
          setUniqueFlags(Array.from(allFlags).sort());
          
          return true;
        } else {
          throw new Error('Some flag updates failed');
        }
      } else {
        throw new Error('Some requests failed');
      }
    } catch (err) {
      console.error('Error batch updating device flags:', err);
      setError(err instanceof Error ? err.message : 'Unknown error');
      return false;
    }
  }, [deviceFlags]);

  const refreshFlags = useCallback(async () => {
    await fetchBatchFlags();
  }, [fetchBatchFlags]);

  useEffect(() => {
    fetchBatchFlags();
  }, [fetchBatchFlags]);

  return {
    deviceFlags,
    uniqueFlags,
    isLoading,
    error,
    updateDeviceFlags,
    batchUpdateDeviceFlags,
    refreshFlags,
  };
};