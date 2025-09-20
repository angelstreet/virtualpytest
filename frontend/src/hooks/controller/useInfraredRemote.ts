import { useState, useCallback, useEffect } from 'react';

import { infraredRemoteConfig } from '../../config/remote/infraredRemote';
import { getInfraredRemoteConfig } from '../../config/remote/infraredRemoteFactory';
import { InfraredRemoteConfig } from '../../config/remote/infraredRemoteBase';
import { Host } from '../../types/common/Host_Types';

import { buildServerUrl } from '../../utils/buildUrlUtils';
interface InfraredRemoteSession {
  connected: boolean;
  connecting: boolean;
  error: string | null;
}

interface UseInfraredRemoteReturn {
  session: InfraredRemoteSession;
  isLoading: boolean;
  lastAction: string;
  layoutConfig: InfraredRemoteConfig;
  handleConnect: () => Promise<void>;
  handleDisconnect: () => Promise<void>;
  handleRemoteCommand: (command: string, params?: any) => Promise<void>;
}

export const useInfraredRemote = (
  host: Host,
  deviceId?: string,
  isConnected?: boolean,
): UseInfraredRemoteReturn => {
  // Get IR type from device configuration
  const device = host?.devices?.find(d => d.device_id === deviceId);
  const irType = device?.ir_type;

  // Get the appropriate config based on IR type
  const layoutConfig = irType ? getInfraredRemoteConfig(irType) : infraredRemoteConfig;
  
  const [session, setSession] = useState<InfraredRemoteSession>({
    connected: false,
    connecting: false,
    error: null,
  });
  const [isLoading, setIsLoading] = useState(false);
  const [lastAction, setLastAction] = useState('');

  console.log(`[@hook:useInfraredRemote] IR Type: ${irType || 'none'}, Config: ${layoutConfig.remote_info.name}`);

  // Update session based on external connection status
  useEffect(() => {
    if (isConnected) {
      setSession({
        connected: true,
        connecting: false,
        error: null,
      });
      setLastAction('Connected via external control');
      console.log(
        `[@hook:useInfraredRemote] Connected via external control: ${host.host_name}, deviceId: ${deviceId}`,
      );
    } else {
      setSession({
        connected: false,
        connecting: false,
        error: null,
      });
      setLastAction('Disconnected via external control');
      console.log(
        `[@hook:useInfraredRemote] Disconnected via external control: ${host.host_name}, deviceId: ${deviceId}`,
      );
    }
  }, [isConnected, host.host_name, deviceId]);

  const handleConnect = useCallback(async () => {
    setSession((prev) => ({ ...prev, connecting: true, error: null }));
    setIsLoading(true);

    try {
      console.log(`[@hook:useInfraredRemote] Attempting to connect to IR remote: ${host.host_name}`);

      // For IR remote, we assume it's always available since it's hardware-based
      // In a real implementation, this might check if the IR device is accessible
      await new Promise((resolve) => setTimeout(resolve, 1000)); // Simulate connection delay

      setSession({
        connected: true,
        connecting: false,
        error: null,
      });
      setLastAction('Connected to IR remote');

      console.log(`[@hook:useInfraredRemote] Successfully connected to IR remote: ${host.host_name}`);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Connection failed';
      setSession({
        connected: false,
        connecting: false,
        error: errorMessage,
      });
      setLastAction(`Connection failed: ${errorMessage}`);
      console.error(`[@hook:useInfraredRemote] Connection failed: ${errorMessage}`);
    } finally {
      setIsLoading(false);
    }
  }, [host.host_name]);

  const handleDisconnect = useCallback(async () => {
    setIsLoading(true);

    try {
      console.log(`[@hook:useInfraredRemote] Disconnecting from IR remote: ${host.host_name}`);

      setSession({
        connected: false,
        connecting: false,
        error: null,
      });
      setLastAction('Disconnected from IR remote');

      console.log(`[@hook:useInfraredRemote] Successfully disconnected from IR remote: ${host.host_name}`);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Disconnect failed';
      console.error(`[@hook:useInfraredRemote] Disconnect failed: ${errorMessage}`);
    } finally {
      setIsLoading(false);
    }
  }, [host.host_name]);

  const handleRemoteCommand = useCallback(
    async (command: string, params?: any) => {
      if (!session.connected) {
        console.warn(`[@hook:useInfraredRemote] Cannot send command - not connected`);
        return;
      }

      setIsLoading(true);

      try {
        console.log(`[@hook:useInfraredRemote] Sending IR command: ${command}`, params);

        // Use the same server proxy pattern as Android TV remote
        const requestBody: any = {
          host_name: host.host_name,
          command: 'press_key',
          params: { key: command, ...params },
          remote_type: 'ir_remote', // Specify IR remote controller
        };

        // Add deviceId if provided
        if (deviceId) {
          requestBody.device_id = deviceId;
        }

        const response = await fetch(buildServerUrl('/server/remote/executeCommand'), {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(requestBody),
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const result = await response.json();
        
        if (!result.success) {
          throw new Error(result.error || 'Command failed');
        }

        setLastAction(`Sent IR command: ${command}`);
        console.log(`[@hook:useInfraredRemote] Successfully sent IR command: ${command}`, result);
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Command failed';
        setLastAction(`Command failed: ${errorMessage}`);
        console.error(`[@hook:useInfraredRemote] Command failed: ${errorMessage}`);
        
        // Don't disconnect on command failure for IR remote
        // IR commands might fail due to hardware issues but connection should remain
      } finally {
        setIsLoading(false);
      }
    },
    [session.connected, host.host_name, deviceId],
  );

  return {
    session,
    isLoading,
    lastAction,
    layoutConfig,
    handleConnect,
    handleDisconnect,
    handleRemoteCommand,
  };
};
