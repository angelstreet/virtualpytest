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
  deviceModel?: string;  // Device model to find compatible interfaces for
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
  const { getCompatibleInterfaces } = useUserInterface();

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

      // Otherwise, fetch from API based on device model using centralized hook
      if (!deviceModel || deviceModel === 'unknown') {
        setError('Select a device first');
        setInterfaces([]);
        return;
      }

      try {
        setLoading(true);
        setError(null);

        const compatibleList = await getCompatibleInterfaces(deviceModel);

        if (compatibleList && compatibleList.length > 0) {
          const options = compatibleList.map((iface: any) => ({
            id: iface.id,
            name: iface.name
          }));
          setInterfaces(options);

          // Auto-select first if no value set or value is empty string
          if ((!value || value.trim() === '') && onChange) {
            console.log('[@UserinterfaceSelector] Auto-selecting first interface:', options[0].name);
            onChange(options[0].name);
          }
        } else {
          setError('No compatible interfaces found');
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
  }, [deviceModel, compatibleInterfaces]); // getCompatibleInterfaces excluded to prevent unnecessary re-fetches

  const handleChange = (event: SelectChangeEvent<string>) => {
    onChange(event.target.value);
  };

  console.log('[@UserinterfaceSelector] Render state check:', { loading, error, interfacesLength: interfaces.length, value });

  if (loading) {
    console.log('[@UserinterfaceSelector] Rendering LOADING state');
    return (
      <FormControl size={size} fullWidth={fullWidth} disabled sx={sx}>
        <InputLabel>{label}</InputLabel>
        <Select
          value=""
          label={label}
          disabled
          startAdornment={<CircularProgress size={16} sx={{ mr: 1 }} />}
        >
          <MenuItem value="">Loading...</MenuItem>
        </Select>
      </FormControl>
    );
  }

  if (error || interfaces.length === 0) {
    // Don't show as error if just waiting for device selection
    const isWaitingForDevice = error === 'Select a device first';
    console.log('[@UserinterfaceSelector] Rendering ERROR/EMPTY state:', { error, interfacesLength: interfaces.length });
    
    return (
      <FormControl size={size} fullWidth={fullWidth} disabled sx={sx}>
        <InputLabel error={!isWaitingForDevice}>{label}</InputLabel>
        <Select value="" label={label} disabled>
          <MenuItem value="">{error || 'No compatible interfaces'}</MenuItem>
        </Select>
      </FormControl>
    );
  }

  console.log('[@UserinterfaceSelector] Rendering with value:', value, 'interfaces:', interfaces.map(i => i.name));
  
  return (
    <FormControl size={size} fullWidth={fullWidth} disabled={disabled} sx={sx}>
      <InputLabel>{label}</InputLabel>
      <Select
        value={value || ''}
        onChange={handleChange}
        label={label}
      >
        {interfaces.map((iface) => (
          <MenuItem key={iface.id} value={iface.name}>
            {iface.name}
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  );
};
