import { createContext } from 'react';

import { Host, Device } from '../types/common/Host_Types';

// ========================================
// TYPES
// ========================================

export interface HostManagerContextType {
  // Panel and UI state
  selectedHost: Host | null;
  selectedDeviceId: string | null;
  isControlActive: boolean;
  isRemotePanelOpen: boolean;
  showRemotePanel: boolean;
  showAVPanel: boolean;
  isVerificationActive: boolean;

  // Host data (filtered by interface models)
  availableHosts: Host[];
  getHostByName: (name: string) => Host | null;
  isLoading: boolean;
  error: string | null;

  // NEW: Direct data access functions (Phase 1.1)
  getAllHosts: () => Host[];
  getHostsByModel: (models: string[]) => Host[];
  getAllDevices: () => Device[];
  getDevicesFromHost: (hostName: string) => Device[];
  getDevicesByCapability: (capability: string) => { host: Host; device: Device }[];

  // Device control functions - now device-oriented
  takeControl: (
    host: Host,
    device_id?: string,
    sessionId?: string,
  ) => Promise<{
    success: boolean;
    error?: string;
    errorType?: string;
    details?: any;
  }>;

  releaseControl: (
    host: Host,
    device_id?: string,
    sessionId?: string,
  ) => Promise<{
    success: boolean;
    error?: string;
    errorType?: string;
    details?: any;
  }>;

  // Status checking methods - now device-oriented
  isDeviceLocked: (host: Host | null, deviceId?: string) => boolean;
  canLockDevice: (host: Host | null, deviceId?: string) => boolean;
  hasActiveLock: (deviceKey: string) => boolean; // deviceKey format: "hostname" or "hostname:device_id"

  // Panel and UI handlers
  handleDeviceSelect: (host: Host | null, deviceId: string | null) => void;
  handleControlStateChange: (active: boolean) => void;
  handleToggleRemotePanel: () => void;
  handleConnectionChange: (connected: boolean) => void;
  handleDisconnectComplete: () => void;

  // Panel and control actions
  setSelectedHost: (host: Host | null) => void;
  setSelectedDeviceId: (deviceId: string | null) => void;
  setIsControlActive: (active: boolean) => void;
  setIsRemotePanelOpen: (open: boolean) => void;
  setShowRemotePanel: (show: boolean) => void;
  setShowAVPanel: (show: boolean) => void;
  setIsVerificationActive: (active: boolean) => void;

  // Lock management
  reclaimLocks: () => Promise<boolean>;
}

// ========================================
// CONTEXT
// ========================================

export const HostManagerContext = createContext<HostManagerContextType | undefined>(undefined);
