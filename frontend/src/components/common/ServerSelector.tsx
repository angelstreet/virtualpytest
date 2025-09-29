import React from 'react';
import { FormControl, InputLabel, Select, MenuItem } from '@mui/material';
import { useHostManager } from '../../hooks/useHostManager';

interface ServerSelectorProps {
  size?: 'small' | 'medium';
  minWidth?: number;
  label?: string;
  variant?: 'outlined' | 'standard' | 'filled';
}

export const ServerSelector: React.FC<ServerSelectorProps> = ({
  size = 'small',
  minWidth = 200,
  label = 'Server',
  variant = 'outlined'
}) => {
  const { selectedServer, setSelectedServer, availableServers } = useHostManager();

  return (
    <FormControl size={size} sx={{ minWidth }} variant={variant}>
      <InputLabel>{label}</InputLabel>
      <Select
        value={selectedServer}
        label={label}
        onChange={(e) => setSelectedServer(e.target.value)}
      >
        {availableServers.map((serverUrl) => (
          <MenuItem 
            key={serverUrl} 
            value={serverUrl}
          >
            {serverUrl.replace(/^https?:\/\//, '')}
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  );
};
