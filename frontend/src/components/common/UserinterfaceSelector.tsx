/**
 * Shared Userinterface Selector Component
 * 
 * Provides a dropdown to select userinterface from compatible options.
 * Used across:
 * - AI Execution Panel (live execution)
 * - Test Case Editor (execute modal)
 * - Run Tests (script parameters)
 */

import React, { useState, useEffect } from 'react';
import { FormControl, InputLabel, Select, MenuItem, CircularProgress, SelectChangeEvent } from '@mui/material';
import { useUserInterface } from '../../hooks/pages/useUserInterface';

interface UserinterfaceSelectorProps {
  deviceModel?: string;  // Device model to find compatible interfaces for (undefined = show all)
  compatibleInterfaces?: string[];  // Pre-filtered list (e.g., from test case)
  value?: string;
  onChange: (userinterface: string) => void;
  label?: string;
  disabled?: boolean;
  size?: 'small' | 'medium';
  fullWidth?: boolean;
  sx?: any;
}

interface UserinterfaceOption {
  id: string;
  name: string;
}

export const UserinterfaceSelector: React.FC<UserinterfaceSelectorProps> = ({
  deviceModel,
  compatibleInterfaces,
  value = '',
  onChange,
  label = 'Userinterface',
  disabled = false,
  size = 'medium',
  fullWidth = true,
  sx = {}
}) => {
  const [interfaces, setInterfaces] = useState<UserinterfaceOption[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { getCompatibleInterfaces, getAllUserInterfaces } = useUserInterface();

  useEffect(() => {
    const fetchInterfaces = async () => {
      // If pre-filtered list provided, use it directly
      if (compatibleInterfaces && compatibleInterfaces.length > 0) {
        const options = compatibleInterfaces.map(name => ({
          id: name,
          name: name
        }));
        console.log('[@UserinterfaceSelector] Setting interfaces from compatibleInterfaces:', options);
        console.log('[@UserinterfaceSelector] Current value:', value);
        setInterfaces(options);
        setError(null); // Clear any previous error

        // Auto-select first if no value set or value is empty string
        if ((!value || value.trim() === '') && onChange) {
          console.log('[@UserinterfaceSelector] Auto-selecting first interface:', options[0].name);
          onChange(options[0].name);
        }
        return;
      }

      try {
        setLoading(true);
        setError(null);

        let interfacesList: any[];

        if (deviceModel && deviceModel !== 'unknown') {
          // Fetch compatible interfaces for specific device model
          console.log('[@UserinterfaceSelector] Fetching compatible interfaces for device model:', deviceModel);
          interfacesList = await getCompatibleInterfaces(deviceModel);
        } else {
          // Fetch all interfaces when no device is selected
          console.log('[@UserinterfaceSelector] No device selected - fetching all interfaces');
          const allInterfaces = await getAllUserInterfaces();
          interfacesList = allInterfaces;
        }

        if (interfacesList && interfacesList.length > 0) {
          const options = interfacesList.map((iface: any) => ({
            id: iface.id,
            name: iface.name
          }));
          setInterfaces(options);
          console.log(`[@UserinterfaceSelector] Loaded ${options.length} interfaces`);

          // Auto-select first interface if no value is set and deviceModel is provided (device selected)
          if ((!value || value.trim() === '') && onChange && deviceModel) {
            console.log('[@UserinterfaceSelector] Auto-selecting first compatible interface for device:', options[0].name);
            onChange(options[0].name);
          }
        } else {
          setError('No interfaces found');
          setInterfaces([]);
        }
      } catch (err) {
        console.error('[@UserinterfaceSelector] Error fetching interfaces:', err);
        setError('Failed to load interfaces');
        setInterfaces([]);
      } finally {
        setLoading(false);
      }
    };

    fetchInterfaces();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [deviceModel, compatibleInterfaces]); // getCompatibleInterfaces, getAllUserInterfaces excluded to prevent unnecessary re-fetches

  const handleChange = (event: SelectChangeEvent<string>) => {
    onChange(event.target.value);
  };

  if (loading) {
    return (
      <FormControl size={size} fullWidth={fullWidth} disabled sx={sx}>
        <InputLabel>{label}</InputLabel>
        <Select
          value=""
          label={label}
          disabled
          startAdornment={<CircularProgress size={16} sx={{ mr: 1 }} />}
          sx={sx}
        >
          <MenuItem value="">Loading...</MenuItem>
        </Select>
      </FormControl>
    );
  }

  if (error || interfaces.length === 0) {
    // Don't show as error if just waiting for device selection
    const isWaitingForDevice = error === 'Select a device first';
    
    return (
      <FormControl size={size} fullWidth={fullWidth} disabled sx={sx}>
        <InputLabel error={!isWaitingForDevice}>{label}</InputLabel>
        <Select value="" label={label} disabled sx={sx}>
          <MenuItem value="">{error || 'No compatible interfaces'}</MenuItem>
        </Select>
      </FormControl>
    );
  }
  
  return (
    <FormControl size={size} fullWidth={fullWidth} disabled={disabled} sx={sx}>
      <InputLabel>{label}</InputLabel>
      <Select
        value={value || ''}
        onChange={handleChange}
        label={label}
        sx={sx}
      >
        <MenuItem value="">
          <em>Select Interface...</em>
        </MenuItem>
        {interfaces.map((iface) => (
          <MenuItem key={iface.id} value={iface.name}>
            {iface.name}
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  );
};
