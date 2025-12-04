import { Computer as ComputerIcon, Refresh as RefreshIcon } from '@mui/icons-material';
import {
  Box,
  Typography,
  Alert,
  Grid,
  CircularProgress,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  Stack,
  Button,
  SelectChangeEvent,
  TextField,
  Autocomplete,
  Backdrop,
} from '@mui/material';
import React, { useEffect, useState, useMemo, useCallback, memo, useRef } from 'react';

import { RecHostPreview } from '../components/rec/RecHostPreview';
import { useRec } from '../hooks/pages/useRec';
import { useDeviceFlags } from '../hooks/useDeviceFlags';
import { useServerManager } from '../hooks/useServerManager';
import { Host, Device } from '../types/common/Host_Types';
import { RecHostStreamModal } from '../components/rec/RecHostStreamModal';

// Optimized memoization with deep comparison to prevent re-renders from object reference changes
const MemoizedRecHostPreview = memo(RecHostPreview, (prevProps, nextProps) => {
  // Quick reference check first - if references are same, no need for deep comparison
  if (
    prevProps.host === nextProps.host &&
    prevProps.device === nextProps.device &&
    prevProps.isEditMode === nextProps.isEditMode &&
    prevProps.isSelected === nextProps.isSelected &&
    prevProps.deviceFlags === nextProps.deviceFlags &&
    prevProps.onSelectionChange === nextProps.onSelectionChange &&
    prevProps.onOpenModal === nextProps.onOpenModal &&
    prevProps.isAnyModalOpen === nextProps.isAnyModalOpen &&
    prevProps.isSelectedForModal === nextProps.isSelectedForModal
  ) {
    return true; // Props haven't changed, skip re-render
  }

  // Log what changed for debugging
  const deviceKey = `${nextProps.host.host_name}-${nextProps.device?.device_id}`;
  const changes = {
    host: prevProps.host !== nextProps.host,
    device: prevProps.device !== nextProps.device,
    isEditMode: prevProps.isEditMode !== nextProps.isEditMode,
    isSelected: prevProps.isSelected !== nextProps.isSelected,
    deviceFlags: prevProps.deviceFlags !== nextProps.deviceFlags,
    onSelectionChange: prevProps.onSelectionChange !== nextProps.onSelectionChange,
    onOpenModal: prevProps.onOpenModal !== nextProps.onOpenModal,
    isAnyModalOpen: prevProps.isAnyModalOpen !== nextProps.isAnyModalOpen,
    isSelectedForModal: prevProps.isSelectedForModal !== nextProps.isSelectedForModal,
  };
  
  if (Object.values(changes).some(v => v)) {
    console.log(`[@Rec] Card ${deviceKey} props changed:`, changes);
  }

  // Deep comparison when references differ
  const areEqual = (
    prevProps.host.host_name === nextProps.host.host_name &&
    prevProps.device?.device_id === nextProps.device?.device_id &&
    prevProps.isEditMode === nextProps.isEditMode &&
    prevProps.isSelected === nextProps.isSelected &&
    JSON.stringify(prevProps.deviceFlags) === JSON.stringify(nextProps.deviceFlags) &&
    JSON.stringify(prevProps.host) === JSON.stringify(nextProps.host) &&
    JSON.stringify(prevProps.device) === JSON.stringify(nextProps.device) &&
    prevProps.onSelectionChange === nextProps.onSelectionChange &&
    prevProps.onOpenModal === nextProps.onOpenModal &&
    prevProps.isAnyModalOpen === nextProps.isAnyModalOpen &&
    prevProps.isSelectedForModal === nextProps.isSelectedForModal // Handler should be stable now
  );
  
  return areEqual; // Return true to skip re-render, false to re-render
});

// REC page - directly uses the global HostManagerProvider from App.tsx
// No local HostManagerProvider needed since we only need AV capability filtering
// Memoized to prevent re-renders when HostManagerProvider updates (e.g., take/release control)
const RecContent: React.FC<ReturnType<typeof useRec>> = memo(({ 
  avDevices, 
  isLoading, 
  error, 
  restartStreams, 
  isRestarting 
}) => {
  // Server change transition state - blocks UI during stream initialization
  const { isServerChanging } = useServerManager();
  
  // Device flags hook
  const { deviceFlags, uniqueFlags, batchUpdateDeviceFlags } = useDeviceFlags();

  // Filter states
  const [hostFilter, setHostFilter] = useState<string>('');
  const [deviceModelFilter, setDeviceModelFilter] = useState<string>('');
  const [deviceFilter, setDeviceFilter] = useState<string>('');
  const [flagFilter, setFlagFilter] = useState<string>('');

  // Edit mode state
  const [isEditMode, setIsEditMode] = useState(false);
  const [selectedDevices, setSelectedDevices] = useState<Set<string>>(new Set());
  const [pendingChanges, setPendingChanges] = useState<Map<string, string[]>>(new Map());
  const [isSaving, setIsSaving] = useState(false);
  const [pendingTags, setPendingTags] = useState<string[]>([]);

  // Modal state
  const [modalHost, setModalHost] = useState<Host | null>(null);
  const [modalDevice, setModalDevice] = useState<Device | null>(null);

  const openModal = useCallback((host: Host, device: Device) => {
    setModalHost(host);
    setModalDevice(device);
  }, []);

  const closeModal = useCallback(() => {
    requestAnimationFrame(() => {
      setModalHost(null);
      setModalDevice(null);
    });
  }, []);

  useEffect(() => {
    console.log('[@Rec] RecContent mounted');
    return () => {
      console.log('[@Rec] RecContent unmounted');
    };
  }, []);

  useEffect(() => {
    console.log('[@Rec] isEditMode changed:', isEditMode);
  }, [isEditMode]);

  // Get unique host names, device models, and device names for filter dropdowns
  const { uniqueHosts, uniqueDeviceModels, uniqueDevices } = useMemo(() => {
    const hosts = new Set<string>();
    const deviceModels = new Set<string>();
    const devices = new Set<string>();

    avDevices.forEach(({ host, device }) => {
      hosts.add(host.host_name);
      if (device.device_model) {
        deviceModels.add(device.device_model);
      }
      if (device.device_name) {
        devices.add(device.device_name);
      }
    });

    return {
      uniqueHosts: Array.from(hosts).sort(),
      uniqueDeviceModels: Array.from(deviceModels).sort(),
      uniqueDevices: Array.from(devices).sort(),
    };
  }, [avDevices]);

  // Filter devices based on selected filters
  const filteredDevices = useMemo(() => {
    return avDevices.filter(({ host, device }) => {
      const matchesHost = !hostFilter || host.host_name === hostFilter;
      const matchesDeviceModel = !deviceModelFilter || device.device_model === deviceModelFilter;
      const matchesDevice = !deviceFilter || device.device_name === deviceFilter;
      
      // Flag filtering
      let matchesFlag = true;
      if (flagFilter) {
        const deviceFlag = deviceFlags.find((df: any) => 
          df.host_name === host.host_name && df.device_id === device.device_id
        );
        matchesFlag = deviceFlag?.flags?.includes(flagFilter) || false;
      }

      return matchesHost && matchesDeviceModel && matchesDevice && matchesFlag;
    });
  }, [avDevices, hostFilter, deviceModelFilter, deviceFilter, flagFilter, deviceFlags]);

  // Clear filters
  const clearFilters = () => {
    setHostFilter('');
    setDeviceModelFilter('');
    setDeviceFilter('');
    setFlagFilter('');
  };

  // Edit mode toggle handler
  const handleEditModeToggle = useCallback(() => {
    setIsEditMode(prev => {
      const newEditMode = !prev;
      if (prev) {
        // Exiting edit mode - clear selections and pending changes
        setSelectedDevices(new Set());
        setPendingChanges(new Map());
      }
      return newEditMode;
    });
  }, []);

  // Create stable selection handlers per device using refs
  const selectionHandlersRef = useRef<Map<string, (selected: boolean) => void>>(new Map());
  
  // Create or get stable handler for a device
  const getSelectionHandler = useCallback((deviceKey: string) => {
    if (!selectionHandlersRef.current.has(deviceKey)) {
      const handler = (selected: boolean) => {
        setSelectedDevices(prev => {
          const newSet = new Set(prev);
          if (selected) {
            newSet.add(deviceKey);
          } else {
            newSet.delete(deviceKey);
          }
          return newSet;
        });
      };
      selectionHandlersRef.current.set(deviceKey, handler);
    }
    return selectionHandlersRef.current.get(deviceKey)!;
  }, []);

  const handleSelectAll = useCallback(() => {
    const allDeviceKeys = filteredDevices.map(({ host, device }) => `${host.host_name}-${device.device_id}`);
    setSelectedDevices(new Set(allDeviceKeys));
  }, [filteredDevices]);

  const handleClearSelection = useCallback(() => {
    setSelectedDevices(new Set());
  }, []);

  // Clear only filtered device selections (keep selections for devices hidden by filters)
  const handleClearFilteredSelection = useCallback(() => {
    const filteredDeviceKeys = new Set(filteredDevices.map(({ host, device }) => `${host.host_name}-${device.device_id}`));
    setSelectedDevices(prev => {
      const newSet = new Set(prev);
      filteredDeviceKeys.forEach(deviceKey => newSet.delete(deviceKey));
      return newSet;
    });
  }, [filteredDevices]);

  // Memoize device flags lookup to prevent unnecessary re-renders
  const deviceFlagsMap = useMemo(() => {
    const map = new Map<string, string[]>();
    deviceFlags.forEach((df: any) => {
      const key = `${df.host_name}-${df.device_id}`;
      map.set(key, df.flags || []);
    });
    return map;
  }, [deviceFlags]);

  // Get current flags for a device (considering pending changes) - memoized per device
  const getCurrentFlags = useCallback((hostName: string, deviceId: string): string[] => {
    const deviceKey = `${hostName}-${deviceId}`;
    if (pendingChanges.has(deviceKey)) {
      return pendingChanges.get(deviceKey) || [];
    }
    return deviceFlagsMap.get(deviceKey) || [];
  }, [deviceFlagsMap, pendingChanges]);

  // Stable empty array to avoid creating new arrays on every render
  const emptyFlagsArray = useMemo(() => [], []);
  
  // Memoize device flags per device to prevent unnecessary re-renders
  const memoizedDeviceFlags = useMemo(() => {
    const flagsMap = new Map<string, string[]>();
    filteredDevices.forEach(({ host, device }) => {
      const deviceKey = `${host.host_name}-${device.device_id}`;
      const flags = getCurrentFlags(host.host_name, device.device_id);
      // Use stable empty array reference for devices with no flags
      flagsMap.set(deviceKey, flags.length > 0 ? flags : emptyFlagsArray);
    });
    return flagsMap;
  }, [filteredDevices, getCurrentFlags, emptyFlagsArray]);

  // Bulk flag operations (now work with pending changes)
  const handleBulkAddFlag = useCallback((flag: string) => {
    const trimmedFlag = flag.trim();
    if (!trimmedFlag) return;
    
    setPendingChanges(prev => {
      const newChanges = new Map(prev);
      Array.from(selectedDevices).forEach(deviceKey => {
        const [hostName, deviceId] = deviceKey.split('-');
        
        // Get current flags from either pending changes or device flags
        let currentFlags: string[];
        if (prev.has(deviceKey)) {
          currentFlags = prev.get(deviceKey) || [];
        } else {
          currentFlags = deviceFlags.find((df: any) => df.host_name === hostName && df.device_id === deviceId)?.flags || [];
        }
        
        if (!currentFlags.includes(trimmedFlag)) {
          const updatedFlags = [...currentFlags, trimmedFlag];
          newChanges.set(deviceKey, updatedFlags);
        }
      });
      return newChanges;
    });
  }, [selectedDevices, deviceFlags]);

  const handleBulkRemoveFlag = useCallback((flag: string) => {
    setPendingChanges(prev => {
      const newChanges = new Map(prev);
      Array.from(selectedDevices).forEach(deviceKey => {
        const [hostName, deviceId] = deviceKey.split('-');
        
        // Get current flags from either pending changes or device flags
        let currentFlags: string[];
        if (prev.has(deviceKey)) {
          currentFlags = prev.get(deviceKey) || [];
        } else {
          currentFlags = deviceFlags.find((df: any) => df.host_name === hostName && df.device_id === deviceId)?.flags || [];
        }
        
        const updatedFlags = currentFlags.filter(f => f !== flag);
        newChanges.set(deviceKey, updatedFlags);
      });
      return newChanges;
    });
  }, [selectedDevices, deviceFlags]);

  // Save all pending changes
  const handleSaveChanges = useCallback(async () => {
    if (pendingChanges.size === 0) return;
    
    setIsSaving(true);
    try {
      const updates = Array.from(pendingChanges.entries()).map(([deviceKey, flags]) => {
        const [hostName, deviceId] = deviceKey.split('-');
        return { hostName, deviceId, flags };
      });
      
      const success = await batchUpdateDeviceFlags(updates);
      if (success) {
        setPendingChanges(new Map()); // Clear pending changes
      }
    } catch (error) {
      console.error('Error saving changes:', error);
    } finally {
      setIsSaving(false);
    }
  }, [pendingChanges, batchUpdateDeviceFlags]);

  // Check if there are unsaved changes
  const hasUnsavedChanges = pendingChanges.size > 0;
  
  // Debug logging for save button state (reduced)
  // console.log('[@Rec] hasUnsavedChanges:', hasUnsavedChanges, 'pendingChanges.size:', pendingChanges.size, 'isSaving:', isSaving);


  // Clean up stale selections when devices change
  useEffect(() => {
    if (isEditMode && selectedDevices.size > 0) {
      const currentDeviceKeys = new Set(avDevices.map(({ host, device }) => `${host.host_name}-${device.device_id}`));
      const staleSelections = Array.from(selectedDevices).filter(deviceKey => !currentDeviceKeys.has(deviceKey));
      
      if (staleSelections.length > 0) {
        console.log(`[@page:Rec] Cleaning up ${staleSelections.length} stale device selections`);
        setSelectedDevices(prev => {
          const newSet = new Set(prev);
          staleSelections.forEach(staleKey => newSet.delete(staleKey));
          return newSet;
        });
        
        // Also clean up stale pending changes
        setPendingChanges(prev => {
          const newMap = new Map(prev);
          staleSelections.forEach(staleKey => newMap.delete(staleKey));
          return newMap;
        });
      }
    }
  }, [avDevices, isEditMode, selectedDevices]);

  // Log AV devices count
  useEffect(() => {
    console.log(`[@page:Rec] Found ${avDevices.length} devices with AV capability`);
    console.log(`[@page:Rec] Filtered to ${filteredDevices.length} devices`);
  }, [avDevices.length, filteredDevices.length]);

  useEffect(() => {
    const deviceKeys = filteredDevices.map(({ host, device }) => `${host.host_name}-${device.device_id}`);
    console.log('[@Rec] filteredDevices keys:', deviceKeys);
  }, [filteredDevices]);

  const hasActiveFilters = hostFilter || deviceModelFilter || deviceFilter || flagFilter;

  // Track what's causing re-renders
  const prevAvDevicesRef = useRef(avDevices);
  const prevFilteredDevicesRef = useRef(filteredDevices);
  const prevDeviceFlagsRef = useRef(deviceFlags);
  
  console.log('[@Rec] RecContent render', {
    isEditMode,
    selectedDevicesCount: selectedDevices.size,
    filteredDevicesCount: filteredDevices.length,
    avDevicesChanged: prevAvDevicesRef.current !== avDevices,
    filteredDevicesChanged: prevFilteredDevicesRef.current !== filteredDevices,
    deviceFlagsChanged: prevDeviceFlagsRef.current !== deviceFlags,
  });
  
  prevAvDevicesRef.current = avDevices;
  prevFilteredDevicesRef.current = filteredDevices;
  prevDeviceFlagsRef.current = deviceFlags;

  return (
    <Box sx={{ p: 3, position: 'relative' }}>
      {/* Server change loading overlay - blocks interaction during stream initialization */}
      <Backdrop
        open={isServerChanging}
        sx={{
          position: 'absolute',
          zIndex: (theme) => theme.zIndex.drawer + 1,
          backgroundColor: 'rgba(0, 0, 0, 0.5)',
          borderRadius: 1,
        }}
      >
        <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
          <CircularProgress color="inherit" />
          <Typography variant="body1" color="white">
            Switching server...
          </Typography>
        </Box>
      </Backdrop>
      
      {/* Header with integrated filters */}
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          mb: 3,
          flexWrap: 'nowrap',
          gap: 2,
        }}
      >
        {/* Left side - Title and description */}
        <Box sx={{ flex: 1, minWidth: 250 }}>
          <Typography variant="h5" component="h1" gutterBottom>
            Remote Eye Controller
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ whiteSpace: 'nowrap' }}>
            {isEditMode ? (
              (() => {
                // Calculate how many of the currently filtered devices are selected
                const filteredDeviceKeys = new Set(filteredDevices.map(({ host, device }) => `${host.host_name}-${device.device_id}`));
                const selectedFilteredCount = Array.from(selectedDevices).filter(deviceKey => filteredDeviceKeys.has(deviceKey)).length;
                
                return (
                  <>
                    Flag Edit Mode • {selectedFilteredCount} of {filteredDevices.length} selected
                    {selectedDevices.size > selectedFilteredCount && (
                      <span style={{ color: '#ff9800', fontWeight: 500 }}>
                        {' '}
                        ({selectedDevices.size - selectedFilteredCount} hidden by filters)
                      </span>
                    )}
                    {hasUnsavedChanges && (
                      <span style={{ color: '#ff9800', fontWeight: 500 }}>
                        {' '}
                        • {pendingChanges.size} unsaved changes
                      </span>
                    )}
                  </>
                );
              })()
            ) : (
              <>
                View and control connected devices
                {hasActiveFilters && (
                  <span>
                    {' '}
                    • Showing {filteredDevices.length} of {avDevices.length} devices
                  </span>
                )}
              </>
            )}
          </Typography>
        </Box>

        {/* Right side - Restart button and compact filters */}
        <Stack direction="row" spacing={1.5} sx={{ alignItems: 'center' }}>
          {/* Edit Mode Toggle */}
          <Button
            variant="text"
            size="small"
            onClick={handleEditModeToggle}
            sx={{ 
              color: '#1976d2', 
              textTransform: 'none',
              fontWeight: 500,
              minWidth: 'auto',
              px: 1
            }}
          >
            {isEditMode ? 'Cancel' : 'Edit'}
          </Button>


          {/* Restart Streams Button */}
          {!isEditMode && (
            <Button
              variant="outlined"
              size="small"
              startIcon={isRestarting ? <CircularProgress size={16} /> : <RefreshIcon />}
              onClick={restartStreams}
              disabled={isRestarting || avDevices.length === 0}
              sx={{ height: 32, minWidth: 120 }}
            >
              {isRestarting ? 'Restarting...' : 'Restart'}
            </Button>
          )}

          {/* Normal Mode - Filters */}
          {!isEditMode && (
            <>
              <FormControl size="small" sx={{ minWidth: 140 }}>
                <InputLabel>Host</InputLabel>
                <Select value={hostFilter} label="Host" onChange={(e: SelectChangeEvent) => setHostFilter(e.target.value)}>
                  <MenuItem value="">
                    <em>All Hosts</em>
                  </MenuItem>
                  {uniqueHosts.map((hostName) => (
                    <MenuItem key={hostName} value={hostName}>
                      {hostName}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              <FormControl size="small" sx={{ minWidth: 140 }}>
                <InputLabel>Model</InputLabel>
                <Select
                  value={deviceModelFilter}
                  label="Model"
                  onChange={(e: SelectChangeEvent) => setDeviceModelFilter(e.target.value)}
                >
                  <MenuItem value="">
                    <em>All Models</em>
                  </MenuItem>
                  {uniqueDeviceModels.map((deviceModel) => (
                    <MenuItem key={deviceModel} value={deviceModel}>
                      {deviceModel}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              <FormControl size="small" sx={{ minWidth: 140 }}>
                <InputLabel>Device</InputLabel>
                <Select
                  value={deviceFilter}
                  label="Device"
                  onChange={(e: SelectChangeEvent) => setDeviceFilter(e.target.value)}
                >
                  <MenuItem value="">
                    <em>All Devices</em>
                  </MenuItem>
                  {uniqueDevices.map((deviceName) => (
                    <MenuItem key={deviceName} value={deviceName}>
                      {deviceName}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              <FormControl size="small" sx={{ minWidth: 140 }}>
                <InputLabel>Flag</InputLabel>
                <Select
                  value={flagFilter}
                  label="Flag"
                  onChange={(e: SelectChangeEvent) => setFlagFilter(e.target.value)}
                >
                  <MenuItem value="">
                    <em>All Flags</em>
                  </MenuItem>
                  {uniqueFlags.map((flag: string) => (
                    <MenuItem key={flag} value={flag}>
                      {flag}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              {hasActiveFilters && (
                <Chip
                  label="Clear"
                  size="small"
                  variant="outlined"
                  onClick={clearFilters}
                  sx={{ height: 32 }}
                />
              )}
            </>
          )}

          {/* Edit Mode - Bulk Actions */}
          {isEditMode && (
            <>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                <Autocomplete
                  multiple
                  freeSolo
                  size="small"
                  options={uniqueFlags}
                  value={pendingTags}
                  onChange={(_, newValue) => setPendingTags(newValue)}
                  renderTags={() => null}
                  renderInput={(params) => (
                    <TextField
                      {...params}
                      placeholder={selectedDevices.size === 0 ? "Select devices first..." : "Add tags..."}
                      disabled={selectedDevices.size === 0}
                    />
                  )}
                  sx={{ minWidth: 200 }}
                />
                
                {/* Tags Preview */}
                {selectedDevices.size > 0 && (pendingTags.length > 0 || selectedDevices.size === 1) && (
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                    {selectedDevices.size === 1 && (() => {
                      const deviceKey = Array.from(selectedDevices)[0];
                      const [hostName, deviceId] = deviceKey.split('-');
                      const existingTags = getCurrentFlags(hostName, deviceId);
                      return existingTags.map(tag => (
                        <Chip key={`existing-${tag}`} label={tag} size="small" color="default" 
                              onDelete={() => handleBulkRemoveFlag(tag)} />
                      ));
                    })()}
                    {pendingTags.map((tag, i) => (
                      <Chip key={`pending-${i}`} label={tag} size="small" color="primary" variant="outlined"
                            onDelete={() => setPendingTags(prev => prev.filter((_, idx) => idx !== i))} />
                    ))}
                  </Box>
                )}
              </Box>

              <Button
                size="small"
                variant="contained"
                disabled={pendingTags.length === 0}
                onClick={() => {
                  pendingTags.forEach(tag => handleBulkAddFlag(tag));
                  setPendingTags([]);
                }}
              >
                Save ({pendingTags.length})
              </Button>

              <Button
                size="small"
                onClick={handleSelectAll}
                disabled={(() => {
                  if (filteredDevices.length === 0) return true;
                  // Check if all filtered devices are already selected
                  const filteredDeviceKeys = filteredDevices.map(({ host, device }) => `${host.host_name}-${device.device_id}`);
                  return filteredDeviceKeys.every(deviceKey => selectedDevices.has(deviceKey));
                })()}
                sx={{ height: 32, textTransform: 'none' }}
              >
                Select All ({filteredDevices.length})
              </Button>

              <Button
                size="small"
                onClick={hasActiveFilters ? handleClearFilteredSelection : handleClearSelection}
                disabled={(() => {
                  if (hasActiveFilters) {
                    // For filtered view, check if any filtered devices are selected
                    const filteredDeviceKeys = filteredDevices.map(({ host, device }) => `${host.host_name}-${device.device_id}`);
                    return !filteredDeviceKeys.some(deviceKey => selectedDevices.has(deviceKey));
                  } else {
                    // For unfiltered view, check if any devices are selected
                    return selectedDevices.size === 0;
                  }
                })()}
                sx={{ height: 32, textTransform: 'none' }}
                title={hasActiveFilters ? "Clear selection for visible devices only" : "Clear all selections"}
              >
                {hasActiveFilters ? 'Clear Visible' : 'Clear All'}
              </Button>

              <Button
                variant="contained"
                size="small"
                onClick={handleSaveChanges}
                disabled={!hasUnsavedChanges || isSaving}
                startIcon={isSaving ? <CircularProgress size={16} /> : undefined}
                title={
                  !hasUnsavedChanges 
                    ? "No changes to save" 
                    : isSaving 
                    ? "Saving changes..." 
                    : `Save ${pendingChanges.size} changes`
                }
                sx={{ 
                  height: 32, 
                  textTransform: 'none',
                  backgroundColor: hasUnsavedChanges ? '#1976d2' : undefined,
                  '&:disabled': {
                    backgroundColor: hasUnsavedChanges ? 'rgba(25, 118, 210, 0.3)' : undefined
                  }
                }}
              >
                {isSaving ? 'Saving...' : hasUnsavedChanges ? `Save (${pendingChanges.size})` : 'Save'}
              </Button>
            </>
          )}
        </Stack>
      </Box>

      {/* Error state */}
      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {/* Loading state */}
      {isLoading ? (
        <Box
          sx={{
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            height: '200px',
          }}
        >
          <CircularProgress />
        </Box>
      ) : filteredDevices.length === 0 ? (
        <Alert 
          severity={error?.includes('not responding') ? 'error' : 'info'} 
          icon={<ComputerIcon />}
        >
          {error?.includes('not responding') 
            ? error 
            : (hasActiveFilters 
              ? 'No devices match the selected filters. Try adjusting your filter criteria.' 
              : 'No AV devices found. Make sure your devices are connected and have AV capabilities.')
          }
        </Alert>
      ) : (
        <Grid container spacing={2}>
          {filteredDevices.map(({ host, device }) => {
            const deviceKey = `${host.host_name}-${device.device_id}`;
            console.log('[@Rec] Rendering device card', {
              deviceKey,
              isEditMode,
              isSelected: selectedDevices.has(deviceKey),
            });
            
            return (
              <Grid item xs={12} sm={6} md={4} lg={3} key={deviceKey}>
                <MemoizedRecHostPreview
                  host={host}
                  device={device}
                  isEditMode={isEditMode}
                  isSelected={selectedDevices.has(deviceKey)}
                  onSelectionChange={getSelectionHandler(deviceKey)}
                  deviceFlags={memoizedDeviceFlags.get(deviceKey)!}
                  onOpenModal={() => openModal(host, device)}
                  isAnyModalOpen={!!modalHost}
                  isSelectedForModal={modalHost?.host_name === host.host_name && modalDevice?.device_id === device.device_id}
                />
              </Grid>
            );
          })}
        </Grid>
      )}
      {modalHost && modalDevice && (
        <RecHostStreamModal
          host={modalHost}
          device={modalDevice}
          isOpen={true}
          onClose={closeModal}
        />
      )}
    </Box>
  );
});

// Add display name for debugging
RecContent.displayName = 'RecContent';

const Rec: React.FC = () => {
  const recProps = useRec();
  return <RecContent {...recProps} />;
};

export default Rec;
