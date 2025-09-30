/**
 * Parameter Input Renderer Component
 * 
 * Reusable component for rendering script parameter inputs with different types.
 * Extracted from RunTests.tsx to be shared between script runner and campaign interface.
 */

import React from 'react';
import { TextField, Autocomplete } from '@mui/material';
import { UserinterfaceSelector } from '../UserinterfaceSelector';

export interface ScriptParameter {
  name: string;
  type: 'positional' | 'optional';
  required: boolean;
  help: string;
  default?: string;
  suggestions?: {
    suggested?: string;
    confidence?: string;
  };
}

interface ParameterInputRendererProps {
  parameter: ScriptParameter;
  value: string;
  onChange: (name: string, value: string) => void;
  error?: boolean;
  deviceModel?: string; // Device model for fetching compatible userinterfaces
}

export const ParameterInputRenderer: React.FC<ParameterInputRendererProps> = ({
  parameter,
  value,
  onChange,
  error = false,
  deviceModel,
}) => {
  const handleChange = (newValue: string) => {
    onChange(parameter.name, newValue);
  };

  // Special handling for userinterface_name - use UserinterfaceSelector to fetch compatible interfaces
  if (parameter.name === 'userinterface_name') {
    return (
      <UserinterfaceSelector
        key={parameter.name}
        deviceModel={deviceModel}
        value={value}
        onChange={(userinterface) => handleChange(userinterface)}
        label={`${parameter.name}${parameter.required ? ' *' : ''}`}
        size="small"
        fullWidth
      />
    );
  }

  // Special handling for blackscreen_area with preset options
  if (parameter.name === 'blackscreen_area') {
    const options = [
      '0,0,1920,720',      // Top 2/3 (default)
      '0,0,1920,540',      // Top 1/2
      '0,0,1920,810',      // Top 3/4
      '0,100,1920,620',    // Top 2/3 excluding top banner
      '0,0,1920,1080',     // Full screen
    ];

    return (
      <Autocomplete
        key={parameter.name}
        options={options}
        value={value}
        onChange={(_event, newValue) => handleChange(newValue || '')}
        onInputChange={(_event, newInputValue) => handleChange(newInputValue)}
        freeSolo
        size="small"
        renderInput={(params) => (
          <TextField
            {...params}
            label={`${parameter.name}${parameter.required ? ' *' : ''}`}
            size="small"
            fullWidth
            error={parameter.required && !value.trim() || error}
            placeholder="x,y,width,height (e.g., 0,0,1920,720)"
            helperText={parameter.help || "Blackscreen analysis area: x,y,width,height"}
          />
        )}
      />
    );
  }

  // Default text field for other parameters
  return (
    <TextField
      key={parameter.name}
      label={`${parameter.name}${parameter.required ? ' *' : ''}`}
      value={value}
      onChange={(e) => handleChange(e.target.value)}
      size="small"
      fullWidth
      error={parameter.required && !value.trim() || error}
      placeholder={parameter.name === 'node' ? 'home' : (parameter.default || '')}
      helperText={parameter.help}
    />
  );
};
