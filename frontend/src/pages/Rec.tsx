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
} from '@mui/material';
import React, { useEffect, useState, useMemo, useCallback } from 'react';

import { RecHostPreview } from '../components/rec/RecHostPreview';
import { ModalProvider } from '../contexts/ModalContext';
import { useRec } from '../hooks/pages/useRec';
import { useDeviceFlags } from '../hooks/useDeviceFlags';

// REC page - directly uses the global HostManagerProvider from App.tsx
// No local HostManagerProvider needed since we only need AV capability filtering
const RecContent: React.FC = () => {
  const {
    avDevices,
    isLoading,
    error,
    restartStreams,
    isRestarting,
  } = useRec();


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
        const deviceFlag = deviceFlags.find(df => 
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

  // Selection handlers
  const handleDeviceSelection = useCallback((deviceKey: string, selected: boolean) => {
    setSelectedDevices(prev => {
      const newSet = new Set(prev);
      if (selected) {
        newSet.add(deviceKey);
      } else {
        newSet.delete(deviceKey);
      }
      return newSet;
    });
  }, []);

  const handleSelectAll = useCallback(() => {
    const allDeviceKeys = filteredDevices.map(({ host, device }) => `${host.host_name}-${device.device_id}`);
    setSelectedDevices(new Set(allDeviceKeys));
  }, [filteredDevices]);

  const handleClearSelection = useCallback(() => {
    setSelectedDevices(new Set());
  }, []);

  // Get current flags for a device (considering pending changes)
  const getCurrentFlags = useCallback((hostName: string, deviceId: string): string[] => {
    const deviceKey = `${hostName}-${deviceId}`;
    if (pendingChanges.has(deviceKey)) {
      return pendingChanges.get(deviceKey) || [];
    }
    return deviceFlags.find(df => df.host_name === hostName && df.device_id === deviceId)?.flags || [];
  }, [deviceFlags, pendingChanges]);

  // Bulk flag operations (now work with pending changes)
  const handleBulkAddFlag = useCallback((flag: string) => {
    if (!flag.trim()) return;
    
    console.log('[@handleBulkAddFlag] Adding flag:', flag.trim(), 'to devices:', Array.from(selectedDevices));
    
    setPendingChanges(prev => {
      const newChanges = new Map(prev);
      Array.from(selectedDevices).forEach(deviceKey => {
        const [hostName, deviceId] = deviceKey.split('-');
        const currentFlags = getCurrentFlags(hostName, deviceId);
        console.log('[@handleBulkAddFlag] Device:', deviceKey, 'current flags:', currentFlags);
        if (!currentFlags.includes(flag.trim())) {
          const updatedFlags = [...currentFlags, flag.trim()];
          newChanges.set(deviceKey, updatedFlags);
          console.log('[@handleBulkAddFlag] Updated flags for', deviceKey, ':', updatedFlags);
        } else {
          console.log('[@handleBulkAddFlag] Flag already exists for', deviceKey);
        }
      });
      console.log('[@handleBulkAddFlag] Final pending changes:', newChanges);
      return newChanges;
    });
  }, [selectedDevices, getCurrentFlags]);

  const handleBulkRemoveFlag = useCallback((flag: string) => {
    setPendingChanges(prev => {
      const newChanges = new Map(prev);
      Array.from(selectedDevices).forEach(deviceKey => {
        const [hostName, deviceId] = deviceKey.split('-');
        const currentFlags = getCurrentFlags(hostName, deviceId);
        const updatedFlags = currentFlags.filter(f => f !== flag);
        newChanges.set(deviceKey, updatedFlags);
      });
      return newChanges;
    });
  }, [selectedDevices, getCurrentFlags]);

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
  
  // Debug logging for save button state
  console.log('[@Rec] hasUnsavedChanges:', hasUnsavedChanges, 'pendingChanges.size:', pendingChanges.size, 'isSaving:', isSaving);


  // Log AV devices count
  useEffect(() => {
    console.log(`[@page:Rec] Found ${avDevices.length} devices with AV capability`);
    console.log(`[@page:Rec] Filtered to ${filteredDevices.length} devices`);
  }, [avDevices.length, filteredDevices.length]);

  const hasActiveFilters = hostFilter || deviceModelFilter || deviceFilter || flagFilter;

  return (
    <Box sx={{ p: 3 }}>
      {/* Header with integrated filters */}
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          mb: 3,
          flexWrap: 'wrap',
          gap: 2,
        }}
      >
        {/* Left side - Title and description */}
        <Box sx={{ flex: 1, minWidth: 250 }}>
          <Typography variant="h5" component="h1" gutterBottom>
            Remote Eye Controller
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {isEditMode ? (
              <>
                Flag Edit Mode • {selectedDevices.size} selected
                {hasUnsavedChanges && (
                  <span style={{ color: '#ff9800', fontWeight: 500 }}>
                    {' '}
                    • {pendingChanges.size} unsaved changes
                  </span>
                )}
              </>
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
            onClick={() => {
              setIsEditMode(!isEditMode);
              setSelectedDevices(new Set());
              setPendingChanges(new Map()); // Clear pending changes when toggling edit mode
            }}
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
                  {uniqueFlags.map((flag) => (
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
              <TextField
                size="small"
                placeholder={selectedDevices.size === 0 ? "Select devices first..." : "Add flag..."}
                disabled={selectedDevices.size === 0}
                onKeyPress={(e: React.KeyboardEvent<HTMLInputElement>) => {
                  if (e.key === 'Enter' && e.currentTarget.value.trim()) {
                    console.log('[@TextField] Enter pressed, adding flag:', e.currentTarget.value.trim());
                    handleBulkAddFlag(e.currentTarget.value.trim());
                    e.currentTarget.value = '';
                  }
                }}
                sx={{ minWidth: 140 }}
                helperText={selectedDevices.size === 0 ? "Select devices to add flags" : ""}
              />

              <FormControl size="small" sx={{ minWidth: 140 }}>
                <InputLabel>Remove Flag</InputLabel>
                <Select
                  value=""
                  label="Remove Flag"
                  disabled={selectedDevices.size === 0}
                  onChange={(e: SelectChangeEvent) => {
                    if (e.target.value) {
                      handleBulkRemoveFlag(e.target.value);
                    }
                  }}
                >
                  {uniqueFlags.map((flag) => (
                    <MenuItem key={flag} value={flag}>
                      {flag}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              <Button
                size="small"
                onClick={handleSelectAll}
                disabled={selectedDevices.size === filteredDevices.length}
                sx={{ height: 32, textTransform: 'none' }}
              >
                Select All
              </Button>

              <Button
                size="small"
                onClick={handleClearSelection}
                disabled={selectedDevices.size === 0}
                sx={{ height: 32, textTransform: 'none' }}
              >
                Unselect All
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
        <Alert severity="info" icon={<ComputerIcon />}>
          {hasActiveFilters
            ? 'No devices match the selected filters. Try adjusting your filter criteria.'
            : 'No AV devices found. Make sure your devices are connected and have AV capabilities.'}
        </Alert>
      ) : (
        <Grid container spacing={2}>
          {filteredDevices.map(({ host, device }) => {
            const deviceKey = `${host.host_name}-${device.device_id}`;
            // Get current flags (including pending changes)
            const currentDeviceFlags = getCurrentFlags(host.host_name, device.device_id);
            
            return (
              <Grid item xs={12} sm={6} md={4} lg={3} key={deviceKey}>
                <RecHostPreview
                  host={host}
                  device={device}
                  isEditMode={isEditMode}
                  isSelected={selectedDevices.has(deviceKey)}
                  onSelectionChange={(selected) => handleDeviceSelection(deviceKey, selected)}
                  deviceFlags={currentDeviceFlags}
                />
              </Grid>
            );
          })}
        </Grid>
      )}
    </Box>
  );
};

const Rec: React.FC = () => {
  return (
    <ModalProvider>
      <RecContent />
    </ModalProvider>
  );
};

export default Rec;
