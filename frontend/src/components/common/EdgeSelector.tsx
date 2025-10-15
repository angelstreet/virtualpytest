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
}) => {
  const [edges, setEdges] = useState<EdgeOption[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Prevent duplicate fetch requests
  const fetchInProgress = useRef(false);
  const lastFetchKey = useRef<string | null>(null);

  const fetchEdges = useCallback(async () => {
    if (!userinterfaceName || !hostName) {
      setEdges([]);
      setError(null);
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
      console.log('[EdgeSelector] Fetching edges for:', { userinterfaceName, hostName, team_id: TEAM_ID });
      
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
  }, [userinterfaceName, hostName, team?.id]);

  // Fetch edges when dependencies change
  useEffect(() => {
    fetchEdges();
  }, [fetchEdges]);

  // Get the selected edge option (for display)
  const selectedEdge = edges.find((e) => e.label === value) || null;

  // Render option with from/to node information
  const renderOption = (props: any, option: EdgeOption) => (
    <Box component="li" {...props} sx={{ display: 'flex', flexDirection: 'column', py: 1 }}>
      <Typography variant="body2" fontWeight="bold">
        {option.label}
      </Typography>
      <Typography variant="caption" color="text.secondary">
        {option.from} → {option.to} ({option.direction})
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
        (loading ? 'Loading edges...' : '') ||
        (!userinterfaceName ? 'Select user interface first' : '') ||
        (!hostName ? 'Select host first' : '') ||
        (required && !value ? 'This field is required' : '')
      }
      InputProps={{
        ...params.InputProps,
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
      disabled={!userinterfaceName || !hostName || loading}
      noOptionsText={
        !userinterfaceName
          ? 'Select user interface first'
          : !hostName
          ? 'Select host first'
          : loading
          ? 'Loading...'
          : 'No edges available'
      }
      size={size}
      fullWidth={fullWidth}
    />
  );
};

