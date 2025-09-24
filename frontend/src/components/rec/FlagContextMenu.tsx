import React from 'react';
import { Menu, MenuItem, ListItemText } from '@mui/material';
import { useDeviceFlags } from '../../hooks/useDeviceFlags';

interface FlagContextMenuProps {
  anchorEl: HTMLElement | null;
  open: boolean;
  onClose: () => void;
  sourceFlags: string[];
  targetHostName: string;
  targetDeviceId: string;
}

export const FlagContextMenu: React.FC<FlagContextMenuProps> = ({
  anchorEl,
  open,
  onClose,
  sourceFlags,
  targetHostName,
  targetDeviceId,
}) => {
  const { updateDeviceFlags, deviceFlags } = useDeviceFlags();

  const handleCopyFlags = async () => {
    const success = await updateDeviceFlags(targetHostName, targetDeviceId, sourceFlags);
    if (success) {
      console.log('Flags copied successfully');
    }
    onClose();
  };

  const handleClearFlags = async () => {
    const success = await updateDeviceFlags(targetHostName, targetDeviceId, []);
    if (success) {
      console.log('Flags cleared successfully');
    }
    onClose();
  };

  const currentFlags = deviceFlags.find(df => 
    df.host_name === targetHostName && df.device_id === targetDeviceId
  )?.flags || [];

  return (
    <Menu
      anchorEl={anchorEl}
      open={open}
      onClose={onClose}
      PaperProps={{
        sx: { minWidth: 120 }
      }}
    >
      {sourceFlags.length > 0 && (
        <MenuItem onClick={handleCopyFlags}>
          <ListItemText 
            primary="Copy flags here" 
            secondary={`${sourceFlags.length} flag(s)`}
            primaryTypographyProps={{ fontSize: '0.8rem' }}
            secondaryTypographyProps={{ fontSize: '0.7rem' }}
          />
        </MenuItem>
      )}
      {currentFlags.length > 0 && (
        <MenuItem onClick={handleClearFlags}>
          <ListItemText 
            primary="Clear all flags"
            primaryTypographyProps={{ fontSize: '0.8rem' }}
          />
        </MenuItem>
      )}
    </Menu>
  );
};
