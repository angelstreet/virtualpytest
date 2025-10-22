/**
 * EdgeSelector Component
 * 
 * Fetches and displays available edge action_set labels for KPI measurement scripts.
 * Loads edges from the navigation tree via the backend API.
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Autocomplete, TextField, CircularProgress, Box, Typography } from '@mui/material';
import { buildServerUrl } from '../../utils/buildUrlUtils';

// Hardcoded team_id (same as used throughout the app)
const TEAM_ID = '7fdeb4bb-3639-4ec3-959f-b54769a219ce';

interface EdgeOption {
  label: string;
  from: string;
  to: string;
  direction: 'forward' | 'reverse';
}

interface EdgeSelectorProps {
  value: string;
  onChange: (edge: string) => void;
  label?: string;
  size?: 'small' | 'medium';
  fullWidth?: boolean;
  required?: boolean;
  userinterfaceName?: string; // Required to fetch edges
  hostName?: string; // Required to fetch edges
  disabled?: boolean; // Disable fetching until ready
}

export const EdgeSelector: React.FC<EdgeSelectorProps> = ({
  value,
  onChange,
  label = 'Edge',
  size = 'medium',
  fullWidth = false,
  required = false,
  userinterfaceName,
  hostName,
  disabled = false,
}) => {
  const [edges, setEdges] = useState<EdgeOption[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Prevent duplicate fetch requests
  const fetchInProgress = useRef(false);
  const lastFetchKey = useRef<string | null>(null);
  
  // Track if component has mounted - don't fetch on initial mount with cached values
  const hasMounted = useRef(false);

  const fetchEdges = useCallback(async () => {
    // Don't fetch if disabled OR if required props are missing
    if (disabled || !userinterfaceName || !hostName) {
      setEdges([]);
      setError(null);
      return;
    }
    
    // Don't fetch on initial mount (prevents fetching from cached values)
    // Only fetch when values change after mount
    if (!hasMounted.current) {
      hasMounted.current = true;
      return;
    }

    const fetchKey = `${userinterfaceName}-${hostName}-${TEAM_ID}`;
    
    // Prevent duplicate requests
    if (fetchInProgress.current && lastFetchKey.current === fetchKey) {
      console.log('[EdgeSelector] Fetch already in progress, skipping duplicate');
      return;
    }

    fetchInProgress.current = true;
    lastFetchKey.current = fetchKey;
    setLoading(true);
    setError(null);

    try {
      console.log('[EdgeSelector] Fetching edges for:', { userinterfaceName, hostName, team_id: TEAM_ID, disabled });
      
      const response = await fetch(buildServerUrl('/server/script/get_edge_options'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          userinterface_name: userinterfaceName,
          team_id: TEAM_ID,
          host_name: hostName,
        }),
      });

      const data = await response.json();

      if (data.success && data.edge_details) {
        setEdges(data.edge_details);
        console.log('[EdgeSelector] Loaded', data.edge_details.length, 'edges');
      } else {
        const errorMsg = data.error || 'Failed to load edges';
        setError(errorMsg);
        console.error('[EdgeSelector] Error:', errorMsg);
        setEdges([]);
      }
    } catch (err) {
      const errorMsg = 'Failed to fetch edges from server';
      setError(errorMsg);
      console.error('[EdgeSelector] Fetch error:', err);
      setEdges([]);
    } finally {
      setLoading(false);
      fetchInProgress.current = false;
    }
  }, [userinterfaceName, hostName, disabled]);

  // Fetch edges when dependencies change
  useEffect(() => {
    fetchEdges();
  }, [fetchEdges]);

  // Get the selected edge option (for display)
  const selectedEdge = edges.find((e) => e.label === value) || undefined;

  // Render option - simplified (just edge label, smaller font)
  const renderOption = (props: any, option: EdgeOption) => (
    <Box component="li" {...props} sx={{ py: 0.5, px: 1, whiteSpace: 'nowrap' }}>
      <Typography variant="body2" sx={{ fontSize: '0.875rem' }}>
        {option.label}
      </Typography>
    </Box>
  );

  // Render input with loading indicator
  const renderInput = (params: any) => (
    <TextField
      {...params}
      label={label}
      size={size}
      fullWidth={fullWidth}
      error={!!error || (required && !value)}
      helperText={
        error ||
        (loading ? 'Loading edges with KPI...' : '') ||
        (!userinterfaceName ? 'Select user interface first' : '') ||
        (!hostName ? 'Select host first' : '') ||
        (required && !value ? 'This field is required' : '')
      }
      InputProps={{
        ...params.InputProps,
        style: { fontSize: '0.875rem' },
        endAdornment: (
          <>
            {loading ? <CircularProgress color="inherit" size={20} /> : null}
            {params.InputProps.endAdornment}
          </>
        ),
      }}
    />
  );

  return (
    <Autocomplete
      value={selectedEdge}
      onChange={(_event, newValue) => {
        onChange(newValue?.label || '');
      }}
      options={edges}
      getOptionLabel={(option) => option.label}
      renderOption={renderOption}
      renderInput={renderInput}
      loading={loading}
      disabled={disabled || !userinterfaceName || !hostName || loading}
      disableClearable
      noOptionsText={
        !userinterfaceName
          ? 'Select user interface first'
          : !hostName
          ? 'Select host first'
          : loading
          ? 'Loading...'
          : 'No edges with KPI found'
      }
      size={size}
      fullWidth={fullWidth}
      ListboxProps={{
        style: {
          maxHeight: '400px',
        },
      }}
      componentsProps={{
        paper: {
          sx: {
            minWidth: '350px',
            maxWidth: '450px',
          },
        },
      }}
    />
  );
};

