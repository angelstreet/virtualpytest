import React from 'react';
import { Box, Typography } from '@mui/material';
import { UserinterfaceSelector } from '../common/UserinterfaceSelector';
import { NavigationEditorDeviceControls } from '../navigation/Navigation_NavigationEditor_DeviceControls';

interface MCPPlaygroundHeaderProps {
  // Theme
  actualMode: 'light' | 'dark';
  
  // Device & Host
  selectedHost: any;
  selectedDeviceId: string | null;
  isControlActive: boolean;
  isControlLoading: boolean;
  availableHosts: any[];
  isDeviceLocked: (deviceKey: string) => boolean;
  handleDeviceSelect: (host: any, deviceId: string) => void;
  handleDeviceControl: (host: any, deviceId: string) => void;
  
  // Interface
  compatibleInterfaceNames: string[];
  userinterfaceName: string;
  setUserinterfaceName: (name: string) => void;
  isLoadingTree: boolean;
}

export const MCPPlaygroundHeader: React.FC<MCPPlaygroundHeaderProps> = ({
  actualMode,
  selectedHost,
  selectedDeviceId,
  isControlActive,
  isControlLoading,
  availableHosts,
  isDeviceLocked,
  handleDeviceSelect,
  handleDeviceControl,
  compatibleInterfaceNames,
  userinterfaceName,
  setUserinterfaceName,
  isLoadingTree,
}) => {
  return (
    <Box
      sx={{
        px: 2,
        py: 0,
        borderBottom: 1,
        borderColor: 'divider',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        background: actualMode === 'dark' ? '#111827' : '#ffffff',
        height: '46px',
        flexShrink: 0,
      }}
    >
      {/* SECTION 1: Title */}
      <Box sx={{ display: 'flex', alignItems: 'center', minWidth: 0, flex: '0 0 830px', gap: 1 }}>
        <Typography variant="h6" fontWeight="bold" sx={{ whiteSpace: 'nowrap' }}>
          MCP - Model Context Protocol
        </Typography>
      </Box>
      
      {/* SECTION 2: Device Control */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flex: '0 0 auto', ml: 2, borderLeft: 1, borderColor: 'divider', pl: 2 }}>
        <NavigationEditorDeviceControls
          selectedHost={selectedHost}
          selectedDeviceId={selectedDeviceId}
          isControlActive={isControlActive}
          isControlLoading={isControlLoading}
          isRemotePanelOpen={false}
          availableHosts={availableHosts}
          isDeviceLocked={isDeviceLocked}
          onDeviceSelect={handleDeviceSelect as any}
          onTakeControl={handleDeviceControl as any}
          onToggleRemotePanel={() => {}}
          disableTakeControl={!userinterfaceName || isLoadingTree}
        />
      </Box>
      
      {/* SECTION 3: Interface Selector */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0, flex: '0 1 auto', ml: 0, justifyContent: 'center' }}>
        <UserinterfaceSelector
          compatibleInterfaces={compatibleInterfaceNames}
          value={userinterfaceName}
          onChange={setUserinterfaceName}
          label="Interface"
          size="small"
          fullWidth={false}
          sx={{ minWidth: 180, height: 32 }}
          disabled={!selectedDeviceId}
        />
      </Box>
    </Box>
  );
};

