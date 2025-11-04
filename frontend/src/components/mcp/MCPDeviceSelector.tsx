import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Collapse,
  IconButton,
  Stack,
  Chip,
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
} from '@mui/icons-material';
import { NavigationEditorDeviceControls } from '../navigation/Navigation_NavigationEditor_DeviceControls';
import { UserinterfaceSelector } from '../common/UserinterfaceSelector';

interface MCPDeviceSelectorProps {
  selectedHost: any;
  selectedDeviceId: string | null;
  userinterfaceName: string;
  setUserinterfaceName: (name: string) => void;
  availableHosts: any[];
  compatibleInterfaceNames: string[];
  isControlActive: boolean;
  isControlLoading: boolean;
  isDeviceLocked: (deviceKey: string) => boolean;
  handleDeviceSelect: (host: any | null, deviceId: string | null) => void;
  handleDeviceControl: () => Promise<void>;
  currentTreeId: string | null;
  isLoadingTree: boolean;
  defaultCollapsed?: boolean;
}

export const MCPDeviceSelector: React.FC<MCPDeviceSelectorProps> = ({
  selectedHost,
  selectedDeviceId,
  userinterfaceName,
  setUserinterfaceName,
  availableHosts,
  compatibleInterfaceNames,
  isControlActive,
  isControlLoading,
  isDeviceLocked,
  handleDeviceSelect,
  handleDeviceControl,
  currentTreeId,
  isLoadingTree,
  defaultCollapsed = false
}) => {
  
  const [isCollapsed, setIsCollapsed] = useState(defaultCollapsed);
  
  return (
    <Card
      sx={{
        border: 1,
        borderColor: 'divider',
        boxShadow: 'none',
      }}
    >
      <CardContent sx={{ p: { xs: 2, md: 2.5 }, '&:last-child': { pb: { xs: 2, md: 2.5 } } }}>
        {/* Header */}
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            mb: isCollapsed ? 0 : 2,
            cursor: { xs: 'pointer', md: 'default' },
          }}
          onClick={() => setIsCollapsed(!isCollapsed)}
        >
          <Typography variant="h6" sx={{ fontSize: { xs: '1rem', md: '1.1rem' } }}>
            Device Setup
          </Typography>
          <IconButton
            size="small"
            sx={{ display: { xs: 'block', md: 'none' } }}
          >
            {isCollapsed ? <ExpandMoreIcon /> : <ExpandLessIcon />}
          </IconButton>
        </Box>
        
        {/* Collapsible Content - REUSE TestCaseBuilder components */}
        <Collapse in={!isCollapsed} timeout="auto">
          <Stack spacing={2}>
            {/* Device Control - SAME as TestCaseBuilderHeader */}
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
              disableTakeControl={!userinterfaceName || isLoadingTree || !currentTreeId}
            />
            
            {/* Interface Selector - SAME as TestCaseBuilderHeader */}
            <UserinterfaceSelector
              compatibleInterfaces={compatibleInterfaceNames}
              value={userinterfaceName}
              onChange={setUserinterfaceName}
              label="User Interface"
              size="small"
              fullWidth={true}
              disabled={!selectedDeviceId}
            />
            
            {/* Status Chip */}
            {isControlActive && (
              <Chip
                label="Device Locked"
                color="success"
                size="small"
                sx={{
                  alignSelf: 'center',
                  fontSize: { xs: '0.85rem', md: '0.75rem' },
                }}
              />
            )}
          </Stack>
        </Collapse>
      </CardContent>
    </Card>
  );
};
