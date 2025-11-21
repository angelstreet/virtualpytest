import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useRef,
  useMemo,
} from 'react';

import { Host } from '../../types/common/Host_Types';
import type { Actions } from '../../types/controller/Action_Types';
import { ModelReferences } from '../../types/verification/Verification_Types';

import { buildServerUrl } from '../../utils/buildUrlUtils';
// ========================================
// TYPES
// ========================================

interface DeviceDataState {
  // References data
  references: { [deviceModel: string]: ModelReferences };
  referencesLoading: boolean;
  referencesError: string | null;

  // Available actions data (controller capabilities)
  availableActions: Actions;
  availableActionsLoading: boolean;
  availableActionsError: string | null;

  // Available verification types data (controller capabilities)
  availableVerificationTypes: Record<string, any>;
  availableVerificationTypesLoading: boolean;
  availableVerificationTypesError: string | null;

  // Host tracking
  currentHost: Host | null;
  currentDeviceId: string | null;
  isControlActive: boolean;

  // Device position tracking
  devicePositions: {
    [deviceKey: string]: { nodeId: string; nodeLabel: string; treeId: string; timestamp: number };
  };
}

interface DeviceDataActions {
  // Data fetching
  fetchReferences: (force?: boolean) => Promise<void>;
  fetchAvailableActions: (force?: boolean) => Promise<void>;
  fetchAvailableVerifications: (force?: boolean) => Promise<void>;
  fetchAllData: (force?: boolean) => Promise<void>;

  // Data access helpers
  getModelReferences: (model: string) => ModelReferences;
  getAvailableActions: () => Actions;
  getAvailableVerificationTypes: () => Record<string, any>;

  // State management
  setControlState: (host: Host | null, deviceId: string | null, isActive: boolean) => void;
  clearData: () => void;
  reloadData: () => Promise<void>;
  reloadReferences: () => Promise<void>;

  // Reference cache management
  addReferenceToCache: (deviceModel: string, reference: {
    name: string;
    type: 'image' | 'text';
    url: string;
    area: { x: number; y: number; width: number; height: number };
    text?: string;
    font_size?: number;
    confidence?: number;
  }) => void;

  // Device position management
  getDevicePosition: (
    host: Host,
    deviceId: string,
    treeId: string,
  ) => { nodeId: string; nodeLabel: string } | null;
  setDevicePosition: (
    host: Host,
    deviceId: string,
    treeId: string,
    nodeId: string,
    nodeLabel: string,
  ) => void;
  initializeDevicePosition: (
    host: Host,
    deviceId: string,
    treeId: string,
    rootNodeId: string,
    rootNodeLabel: string,
  ) => { nodeId: string; nodeLabel: string };
}

type DeviceDataContextType = DeviceDataState & DeviceDataActions;

// ========================================
// CONTEXT
// ========================================

const DeviceDataContext = createContext<DeviceDataContextType | undefined>(undefined);

export const useDeviceData = (): DeviceDataContextType => {
  const context = useContext(DeviceDataContext);
  if (context === undefined) {
    throw new Error('useDeviceData must be used within a DeviceDataProvider');
  }
  return context;
};

// ========================================
// PROVIDER
// ========================================

interface DeviceDataProviderProps {
  children: React.ReactNode;
}

export const DeviceDataProvider: React.FC<DeviceDataProviderProps> = ({ children }) => {
  // ========================================
  // STATE
  // ========================================

  const [state, setState] = useState<DeviceDataState>({
    references: {},
    referencesLoading: false,
    referencesError: null,
    availableActions: {},
    availableActionsLoading: false,
    availableActionsError: null,
    availableVerificationTypes: {},
    availableVerificationTypesLoading: false,
    availableVerificationTypesError: null,
    currentHost: null,
    currentDeviceId: null,
    isControlActive: false,
    devicePositions: {},
  });

  // Track what's been loaded to prevent duplicate fetches
  const loadedDataRef = useRef<{
    hostId: string | null;
    referencesLoaded: boolean;
    availableActionsLoaded: boolean;
    availableVerificationTypesLoaded: boolean;
  }>({
    hostId: null,
    referencesLoaded: false,
    availableActionsLoaded: false,
    availableVerificationTypesLoaded: false,
  });

  // Create stable host identifier
  const hostId = useMemo(() => {
    return state.currentHost
      ? `${state.currentHost.host_name}_${state.currentHost.host_url}`
      : null;
  }, [state.currentHost]);

  // ========================================
  // DATA FETCHING FUNCTIONS
  // ========================================

  const fetchReferences = useCallback(
    async (force: boolean = false) => {
      if (!state.isControlActive || !state.currentHost) {
        console.log('[DeviceDataContext] Cannot fetch references - control not active or no host');
        return;
      }

      // Check if already loaded (unless forced)
      if (
        !force &&
        loadedDataRef.current.hostId === hostId &&
        loadedDataRef.current.referencesLoaded
      ) {
        console.log('[DeviceDataContext] References already loaded for host:', hostId);
        return;
      }

      setState((prev) => ({ ...prev, referencesLoading: true, referencesError: null }));

      try {
        // Get current device to filter references by device_model
        const currentDevice = state.currentHost.devices?.find(
          (d) => d.device_id === state.currentDeviceId
        );
        const deviceModel = currentDevice?.device_model;

        // Build URL with device_model for backend filtering
        const params = new URLSearchParams();
        if (deviceModel) {
          params.append('device_model', deviceModel);
          console.log('[DeviceDataContext] Fetching references for device_model:', deviceModel);
        }

        const url = buildServerUrl(
          `/server/verification/getAllReferences${params.toString() ? `?${params.toString()}` : ''}`
        );

        const response = await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ host: state.currentHost }),
        });

        if (response.ok) {
          const result = await response.json();

          if (result.success && result.references && Array.isArray(result.references)) {
            const references: { [deviceModel: string]: ModelReferences } = {};

            result.references.forEach((ref: any) => {
              // Use userinterface_name (primary), fallback to device_model for migration
              const userinterfaceName = ref.userinterface_name || ref.device_model || 'unknown';
              const baseName = ref.name || ref.filename || 'unknown';
              const refType = ref.reference_type === 'reference_text' ? 'text' : 'image';

              // Initialize userinterface references if not exists
              if (!references[userinterfaceName]) {
                references[userinterfaceName] = {};
              }

              // Create internal key with type suffix to avoid conflicts
              // But preserve original name for display in UI
              const internalKey = `${baseName}_${refType}`;

              references[userinterfaceName][internalKey] = {
                name: baseName, // Store original name for display
                type: refType,
                url: ref.r2_url || ref.url,
                area: ref.area || { x: 0, y: 0, width: 0, height: 0 },
                created_at: ref.created_at,
                updated_at: ref.updated_at,
                ...(refType === 'text' &&
                  ref.area && {
                    text: ref.area.text,
                    font_size: ref.area.font_size,
                    confidence: ref.area.confidence,
                  }),
              };
            });

            // References loaded successfully
            setState((prev) => ({ ...prev, references, referencesLoading: false }));
            loadedDataRef.current.referencesLoaded = true;
          } else {
            setState((prev) => ({ ...prev, references: {}, referencesLoading: false }));
          }
        } else {
          throw new Error(`HTTP ${response.status}`);
        }
      } catch (error) {
        console.error('[DeviceDataContext] Error fetching references:', error);
        setState((prev) => ({
          ...prev,
          referencesLoading: false,
          referencesError: error instanceof Error ? error.message : 'Unknown error',
        }));
      }
    },
    [state.currentHost, state.currentDeviceId, state.isControlActive, hostId],
  );

  const fetchAvailableActions = useCallback(
    async (force: boolean = false) => {
      if (!state.isControlActive || !state.currentHost || !state.currentDeviceId) {
        return;
      }

      // Check if already loaded (unless forced)
      if (
        !force &&
        loadedDataRef.current.hostId === hostId &&
        loadedDataRef.current.availableActionsLoaded
      ) {
        return;
      }

      setState((prev) => ({ ...prev, availableActionsLoading: true, availableActionsError: null }));

      try {
        // Get available actions from the currently selected device only
        const categorizedActions: Actions = {};

        // Find the currently selected device
        const currentDevice = state.currentHost.devices?.find(
          (device: any) => device.device_id === state.currentDeviceId
        );

        if (!currentDevice) {
          console.warn('[DeviceDataContext] Current device not found in host devices');
          setState((prev) => ({
            ...prev,
            availableActions: {},
            availableActionsLoading: false,
          }));
          return;
        }

        // Check if device has action types (they might be stripped for performance)
        const deviceActionTypes = currentDevice.device_action_types;
        
        // STEP 2: Check what DeviceDataContext sees
        console.log('[DeviceDataContext:fetchAvailableActions] STEP 2 - Current device data:', {
          currentDevice_id: currentDevice?.device_id,
          hasActionTypes: !!deviceActionTypes,
          actionTypesKeys: deviceActionTypes ? Object.keys(deviceActionTypes) : [],
          state_currentHost_name: state.currentHost?.host_name,
          state_currentDeviceId: state.currentDeviceId,
          deviceActionTypes_sample: deviceActionTypes ? Object.entries(deviceActionTypes).slice(0, 2) : []
        });
        
        if (!deviceActionTypes || Object.keys(deviceActionTypes).length === 0) {
          // Schemas not loaded (performance optimization) - this is expected behavior
          setState((prev) => ({
            ...prev,
            availableActions: {},
            availableActionsLoading: false,
          }));
          return;
        }

        // Process each action category (remote, av, power, desktop, web, etc.)
        Object.keys(deviceActionTypes).forEach((category) => {
          const actions = deviceActionTypes[category];
          if (Array.isArray(actions)) {
            if (!categorizedActions[category]) {
              categorizedActions[category] = [];
            }

            actions.forEach((action: any) => {
              const processedAction = {
                id: action.id || `${action.command}_${category}`,
                label: action.label || action.command,
                command: action.command,
                description: action.description || `${action.command} action`,
                action_type: action.action_type || category,
                params: action.params || {},
                requiresInput: action.requiresInput || false,
                inputLabel: action.inputLabel,
                inputPlaceholder: action.inputPlaceholder,
                verification_type: action.verification_type,
                options: action.options, // Include options array for combobox support
              };
              
              categorizedActions[category].push(processedAction);
            });
          }
        });

        // Available actions loaded successfully

        setState((prev) => ({
          ...prev,
          availableActions: categorizedActions,
          availableActionsLoading: false,
        }));
        loadedDataRef.current.availableActionsLoaded = true;
      } catch (error) {
        console.error(
          '[DeviceDataContext] Error loading available actions from device data:',
          error,
        );
        setState((prev) => ({
          ...prev,
          availableActionsLoading: false,
          availableActionsError: error instanceof Error ? error.message : 'Unknown error',
        }));
      }
    },
    [state.currentHost, state.currentDeviceId, state.isControlActive, hostId],
  );

  const fetchAvailableVerifications = useCallback(
    async (force: boolean = false) => {
      if (!state.isControlActive || !state.currentHost || !state.currentDeviceId) {
        return;
      }

      // Check if already loaded (unless forced)
      if (
        !force &&
        loadedDataRef.current.hostId === hostId &&
        loadedDataRef.current.availableVerificationTypesLoaded
      ) {
        return;
      }

      setState((prev) => ({
        ...prev,
        availableVerificationTypesLoading: true,
        availableVerificationTypesError: null,
      }));

      try {
        // Get available verifications from the currently selected device only
        const allVerificationTypes: Record<string, any> = {};

        // Find the currently selected device
        const currentDevice = state.currentHost.devices?.find(
          (device: any) => device.device_id === state.currentDeviceId
        );

        if (!currentDevice) {
          console.warn('[DeviceDataContext] Current device not found in host devices');
          setState((prev) => ({
            ...prev,
            availableVerificationTypes: {},
            availableVerificationTypesLoading: false,
          }));
          return;
        }

        // Check if device has verification types (they might be stripped for performance)
        const deviceVerificationTypes = currentDevice.device_verification_types;
        
        if (!deviceVerificationTypes || Object.keys(deviceVerificationTypes).length === 0) {
          // Schemas not loaded (performance optimization) - this is expected behavior
          setState((prev) => ({
            ...prev,
            availableVerificationTypes: {},
            availableVerificationTypesLoading: false,
          }));
          return;
        }

        // Process only the current device's verification types
        Object.keys(deviceVerificationTypes).forEach((category) => {
          const verifications = deviceVerificationTypes[category];
          if (Array.isArray(verifications)) {
            allVerificationTypes[category] = verifications;
          }
        });

        // Available verifications loaded successfully

        setState((prev) => ({
          ...prev,
          availableVerificationTypes: allVerificationTypes,
          availableVerificationTypesLoading: false,
        }));
        loadedDataRef.current.availableVerificationTypesLoaded = true;
      } catch (error) {
        console.error(
          '[DeviceDataContext] Error loading available verifications from device data:',
          error,
        );
        setState((prev) => ({
          ...prev,
          availableVerificationTypesLoading: false,
          availableVerificationTypesError: error instanceof Error ? error.message : 'Unknown error',
        }));
      }
    },
    [state.currentHost, state.currentDeviceId, state.isControlActive, hostId],
  );

  const fetchAllData = useCallback(
    async (force: boolean = false) => {
      await Promise.all([
        fetchReferences(force),
        fetchAvailableActions(force),
        fetchAvailableVerifications(force),
      ]);
    },
    [
      fetchReferences,
      fetchAvailableActions,
      fetchAvailableVerifications,
    ],
  );

  // ========================================
  // DATA ACCESS HELPERS
  // ========================================

  const getModelReferences = useCallback(
    (model: string): ModelReferences => {
      if (!model || !state.references[model]) {
        return {};
      }
      return state.references[model];
    },
    [state.references],
  );

  const getAvailableActions = useCallback((): Actions => {
    return state.availableActions;
  }, [state.availableActions]);

  const getAvailableVerificationTypes = useCallback((): Record<string, any> => {
    return state.availableVerificationTypes;
  }, [state.availableVerificationTypes]);

  // ========================================
  // STATE MANAGEMENT
  // ========================================

  const setControlState = useCallback(
    (host: Host | null, deviceId: string | null, isActive: boolean) => {
      const newHostId = host ? `${host.host_name}_${host.host_url}` : null;
      const hostChanged = newHostId !== loadedDataRef.current.hostId;

      if (hostChanged) {
        // Reset loaded state for new host
        loadedDataRef.current = {
          hostId: newHostId,
          referencesLoaded: false,
          availableActionsLoaded: false,
          availableVerificationTypesLoaded: false,
        };

        // Clear existing data
        setState((prev) => ({
          ...prev,
          currentHost: host,
          currentDeviceId: deviceId,
          isControlActive: isActive,
          references: {},
          availableActions: {},
          availableVerificationTypes: {},
          referencesError: null,
          availableActionsError: null,
          availableVerificationTypesError: null,
          devicePositions: {},
        }));
      } else {
        // Same host - update control state and refresh host object
        // (host object may have been updated with action schemas after takeControl)
        const wasControlInactive = !state.isControlActive;
        
        setState((prev) => ({
          ...prev,
          currentHost: host, // Update with potentially refreshed host object
          currentDeviceId: deviceId,
          isControlActive: isActive,
        }));
        
        // Force reload actions/verifications when taking control (host may have been refreshed with schemas)
        if (isActive && wasControlInactive) {
          loadedDataRef.current.availableActionsLoaded = false;
          loadedDataRef.current.availableVerificationTypesLoaded = false;
        }
      }
    },
    [],
  );

  const clearData = useCallback(() => {
    setState((prev) => ({
      ...prev,
      references: {},
      availableActions: {},
      availableVerificationTypes: {},
      referencesError: null,
      availableActionsError: null,
      availableVerificationTypesError: null,
      devicePositions: {},
    }));

    loadedDataRef.current = {
      hostId: null,
      referencesLoaded: false,
      availableActionsLoaded: false,
      availableVerificationTypesLoaded: false,
    };
  }, []);

  const reloadData = useCallback(async () => {
    await fetchAllData(true);
  }, [fetchAllData]);

  const reloadReferences = useCallback(async () => {
    console.log('[DeviceDataContext] Reloading references after save...');
    await fetchReferences(true); // Force reload from server
  }, [fetchReferences]);

  // ========================================
  // REFERENCE CACHE MANAGEMENT
  // ========================================

  const addReferenceToCache = useCallback(
    (deviceModel: string, reference: {
      name: string;
      type: 'image' | 'text';
      url: string;
      area: { x: number; y: number; width: number; height: number };
      text?: string;
      font_size?: number;
      confidence?: number;
    }) => {
      console.log('[DeviceDataContext] Adding reference to cache:', { deviceModel, reference });

      setState((prev) => {
        // Initialize model references if not exists
        if (!prev.references[deviceModel]) {
          prev.references[deviceModel] = {};
        }

        // Create internal key with type suffix to avoid conflicts (same as fetchReferences)
        const internalKey = `${reference.name}_${reference.type}`;

        // Add reference to cache with same structure as fetchReferences
        const newReferences = {
          ...prev.references,
          [deviceModel]: {
            ...prev.references[deviceModel],
            [internalKey]: {
              name: reference.name, // Store original name for display
              type: reference.type,
              url: reference.url,
              area: reference.area,
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
              ...(reference.type === 'text' && {
                text: reference.text,
                font_size: reference.font_size,
                confidence: reference.confidence,
              }),
            },
          },
        };

        console.log('[DeviceDataContext] Updated references cache:', newReferences[deviceModel]);
        
        return {
          ...prev,
          references: newReferences,
        };
      });
    },
    [],
  );

  // ========================================
  // DEVICE POSITION MANAGEMENT
  // ========================================

  const getDevicePosition = useCallback(
    (host: Host, deviceId: string, treeId: string) => {
      const deviceKey = `${host.host_name}_${host.host_url}_${deviceId}_${treeId}`;
      const position = state.devicePositions[deviceKey];
      return position ? { nodeId: position.nodeId, nodeLabel: position.nodeLabel } : null;
    },
    [state.devicePositions],
  );

  const setDevicePosition = useCallback(
    (host: Host, deviceId: string, treeId: string, nodeId: string, nodeLabel: string) => {
      const deviceKey = `${host.host_name}_${host.host_url}_${deviceId}_${treeId}`;
      console.log(
        `[DeviceDataContext] Setting device position for ${deviceKey}: ${nodeId} (${nodeLabel})`,
      );

      setState((prev) => ({
        ...prev,
        devicePositions: {
          ...prev.devicePositions,
          [deviceKey]: {
            nodeId,
            nodeLabel,
            treeId,
            timestamp: Date.now(),
          },
        },
      }));
    },
    [],
  );

  const initializeDevicePosition = useCallback(
    (host: Host, deviceId: string, treeId: string, rootNodeId: string, rootNodeLabel: string) => {
      const deviceKey = `${host.host_name}_${host.host_url}_${deviceId}_${treeId}`;
      const existingPosition = state.devicePositions[deviceKey];

      if (existingPosition) {
        console.log(
          `[DeviceDataContext] Device position already exists for ${deviceKey}: ${existingPosition.nodeId} (${existingPosition.nodeLabel})`,
        );
        return { nodeId: existingPosition.nodeId, nodeLabel: existingPosition.nodeLabel };
      }

      console.log(
        `[DeviceDataContext] Initializing device position for ${deviceKey}: ${rootNodeId} (${rootNodeLabel})`,
      );

      setState((prev) => ({
        ...prev,
        devicePositions: {
          ...prev.devicePositions,
          [deviceKey]: {
            nodeId: rootNodeId,
            nodeLabel: rootNodeLabel,
            treeId,
            timestamp: Date.now(),
          },
        },
      }));

      return { nodeId: rootNodeId, nodeLabel: rootNodeLabel };
    },
    [state.devicePositions],
  );

  // ========================================
  // EFFECTS
  // ========================================

  // Auto-fetch data when control becomes active
  useEffect(() => {
    if (state.isControlActive && state.currentHost) {
      fetchAllData(false); // Don't force, use cache if available
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
    // Only trigger when control state changes, not when fetchAllData reference changes
  }, [state.isControlActive, state.currentHost]);

  // ========================================
  // CONTEXT VALUE
  // ========================================

  const contextValue: DeviceDataContextType = useMemo(
    () => ({
      // State
      ...state,

      // Actions
      fetchReferences,
      fetchAvailableActions,
      fetchAvailableVerifications,
      fetchAllData,
      getModelReferences,
      getAvailableActions,
      getAvailableVerificationTypes,
      setControlState,
      clearData,
      reloadData,
      reloadReferences,

      // Reference cache management
      addReferenceToCache,

      // Device position management
      getDevicePosition,
      setDevicePosition,
      initializeDevicePosition,
    }),
    [
      state,
      fetchReferences,
      fetchAvailableActions,
      fetchAvailableVerifications,
      fetchAllData,
      getModelReferences,
      getAvailableActions,
      getAvailableVerificationTypes,
      setControlState,
      clearData,
      reloadData,
      reloadReferences,
      addReferenceToCache,
      getDevicePosition,
      setDevicePosition,
      initializeDevicePosition,
    ],
  );

  return <DeviceDataContext.Provider value={contextValue}>{children}</DeviceDataContext.Provider>;
};
