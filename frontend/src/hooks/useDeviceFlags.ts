import { useState, useEffect, useCallback } from 'react';
import { buildServerUrl } from '../utils/buildUrlUtils';

interface DeviceFlag {
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
  refreshFlags: () => Promise<void>;
}

export const useDeviceFlags = (): UseDeviceFlagsReturn => {
  const [deviceFlags, setDeviceFlags] = useState<DeviceFlag[]>([]);
  const [uniqueFlags, setUniqueFlags] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDeviceFlags = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      const response = await fetch(buildServerUrl('/server/device-flags/'));
      if (!response.ok) {
        throw new Error(`Failed to fetch device flags: ${response.statusText}`);
      }

      const result = await response.json();
      if (result.success) {
        setDeviceFlags(result.data || []);
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

  const fetchUniqueFlags = useCallback(async () => {
    try {
      const response = await fetch(buildServerUrl('/server/device-flags/flags'));
      if (!response.ok) {
        throw new Error(`Failed to fetch unique flags: ${response.statusText}`);
      }

      const result = await response.json();
      if (result.success) {
        setUniqueFlags(result.data || []);
      }
    } catch (err) {
      console.error('Error fetching unique flags:', err);
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
        
        // Refresh unique flags
        await fetchUniqueFlags();
        return true;
      } else {
        throw new Error(result.error || 'Failed to update device flags');
      }
    } catch (err) {
      console.error('Error updating device flags:', err);
      setError(err instanceof Error ? err.message : 'Unknown error');
      return false;
    }
  }, [fetchUniqueFlags]);

  const refreshFlags = useCallback(async () => {
    await Promise.all([fetchDeviceFlags(), fetchUniqueFlags()]);
  }, [fetchDeviceFlags, fetchUniqueFlags]);

  useEffect(() => {
    refreshFlags();
  }, [refreshFlags]);

  return {
    deviceFlags,
    uniqueFlags,
    isLoading,
    error,
    updateDeviceFlags,
    refreshFlags,
  };
};
