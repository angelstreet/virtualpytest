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
import { buildServerUrl } from '../../utils/buildUrlUtils';

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

  useEffect(() => {
    const fetchInterfaces = async () => {
      // If pre-filtered list provided, use it directly
      if (compatibleInterfaces && compatibleInterfaces.length > 0) {
        const options = compatibleInterfaces.map(name => ({
          id: name,
          name: name
        }));
        setInterfaces(options);
        
        // Auto-select first if no value set
        if (!value && onChange) {
          onChange(options[0].name);
        }
        return;
      }

      // Otherwise, fetch from API based on device model
      if (!deviceModel) {
        setError('No device model or compatible interfaces provided');
        return;
      }

      try {
        setLoading(true);
        setError(null);

        const response = await fetch(
          buildServerUrl(`/server/userinterface/getCompatibleInterfaces?team_id=7fdeb4bb-3639-4ec3-959f-b54769a219ce&device_model=${deviceModel}`)
        );
        const data = await response.json();

        if (data.success && data.interfaces && data.interfaces.length > 0) {
          const options = data.interfaces.map((iface: any) => ({
            id: iface.id,
            name: iface.name
          }));
          setInterfaces(options);

          // Auto-select first if no value set
          if (!value && onChange) {
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
  }, [deviceModel, compatibleInterfaces]);

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
        >
          <MenuItem value="">Loading...</MenuItem>
        </Select>
      </FormControl>
    );
  }

  if (error || interfaces.length === 0) {
    return (
      <FormControl size={size} fullWidth={fullWidth} disabled sx={sx}>
        <InputLabel error>{error || 'No interfaces available'}</InputLabel>
        <Select value="" label={label} disabled>
          <MenuItem value="">{error || 'No compatible interfaces'}</MenuItem>
        </Select>
      </FormControl>
    );
  }

  return (
    <FormControl size={size} fullWidth={fullWidth} disabled={disabled} sx={sx}>
      <InputLabel>{label}</InputLabel>
      <Select
        value={value}
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
