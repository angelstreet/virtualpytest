import React from 'react';
import { FormControl, InputLabel, Select, MenuItem } from '@mui/material';
import { useHostManager } from '../../hooks/useHostManager';
import { useDashboard } from '../../hooks/pages/useDashboard';

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
  const { selectedServer, setSelectedServer } = useHostManager();
  const { serverHostsData } = useDashboard();

  return (
    <FormControl size={size} sx={{ minWidth }} variant={variant}>
      <InputLabel>{label}</InputLabel>
      <Select
        value={selectedServer}
        label={label}
        onChange={(e) => setSelectedServer(e.target.value)}
      >
        {serverHostsData.map((serverData) => (
          <MenuItem 
            key={serverData.server_info.server_url} 
            value={serverData.server_info.server_url}
          >
            {serverData.server_info.server_name.replace('Server (', '').replace(')', '')}
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  );
};
