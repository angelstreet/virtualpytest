import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Button,
  Typography,
  Collapse,
  IconButton,
  Stack,
  Chip,
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Lock as LockIcon,
  LockOpen as LockOpenIcon,
} from '@mui/icons-material';
import { useMCPPlayground } from '../../contexts/mcp/MCPPlaygroundContext';

interface MCPDeviceSelectorProps {
  defaultCollapsed?: boolean;
}

export const MCPDeviceSelector: React.FC<MCPDeviceSelectorProps> = ({ defaultCollapsed = false }) => {
  const {
    selectedHost,
    setSelectedHost,
    selectedDeviceId,
    setSelectedDeviceId,
    userinterfaceName,
    setUserinterfaceName,
    availableHosts,
    availableInterfaces,
    isControlActive,
    isControlLoading,
    handleDeviceControl,
  } = useMCPPlayground();
  
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
        
        {/* Collapsible Content */}
        <Collapse in={!isCollapsed} timeout="auto">
          <Stack spacing={2}>
            {/* Host Selection */}
            <FormControl fullWidth size="small">
              <InputLabel>Host</InputLabel>
              <Select
                value={selectedHost}
                label="Host"
                onChange={(e) => setSelectedHost(e.target.value)}
                disabled={isControlActive}
                sx={{
                  fontSize: { xs: '0.95rem', md: '0.875rem' },
                  '& .MuiSelect-select': {
                    py: { xs: 1.5, md: 1 },
                  },
                }}
              >
                {availableHosts.map((host) => (
                  <MenuItem key={host} value={host}>
                    {host}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            
            {/* Device ID Input */}
            <FormControl fullWidth size="small">
              <InputLabel>Device ID</InputLabel>
              <Select
                value={selectedDeviceId}
                label="Device ID"
                onChange={(e) => setSelectedDeviceId(e.target.value)}
                disabled={isControlActive}
                sx={{
                  fontSize: { xs: '0.95rem', md: '0.875rem' },
                  '& .MuiSelect-select': {
                    py: { xs: 1.5, md: 1 },
                  },
                }}
              >
                <MenuItem value="device1">device1</MenuItem>
                <MenuItem value="device2">device2</MenuItem>
                <MenuItem value="device3">device3</MenuItem>
              </Select>
            </FormControl>
            
            {/* User Interface Selection */}
            <FormControl fullWidth size="small">
              <InputLabel>User Interface</InputLabel>
              <Select
                value={userinterfaceName}
                label="User Interface"
                onChange={(e) => setUserinterfaceName(e.target.value)}
                disabled={isControlActive}
                sx={{
                  fontSize: { xs: '0.95rem', md: '0.875rem' },
                  '& .MuiSelect-select': {
                    py: { xs: 1.5, md: 1 },
                  },
                }}
              >
                {availableInterfaces.map((iface) => (
                  <MenuItem key={iface.userinterface_name} value={iface.userinterface_name}>
                    {iface.userinterface_name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            
            {/* Control Button */}
            <Button
              variant={isControlActive ? 'contained' : 'outlined'}
              color={isControlActive ? 'success' : 'primary'}
              onClick={handleDeviceControl}
              disabled={isControlLoading || !selectedHost || !selectedDeviceId || !userinterfaceName}
              startIcon={isControlActive ? <LockIcon /> : <LockOpenIcon />}
              fullWidth
              sx={{
                minHeight: { xs: 56, md: 48, lg: 40 },
                fontSize: { xs: '1rem', md: '0.9rem' },
                fontWeight: 600,
              }}
            >
              {isControlLoading
                ? 'Connecting...'
                : isControlActive
                ? 'Release Control'
                : 'Take Control'}
            </Button>
            
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

