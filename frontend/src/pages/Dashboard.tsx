import React, { useState, useCallback, useMemo } from 'react';
import { buildServerUrl } from '../utils/buildUrlUtils';

import {
  Computer as ComputerIcon,
  TableRows as TableViewIcon,
  Refresh as RefreshIcon,
  Assignment as TestIcon,
  Campaign as CampaignIcon,
  AccountTree as TreeIcon,
  Devices as DevicesIcon,
  Add as AddIcon,
  PlayArrow as PlayIcon,
  GridView as GridViewIcon,
  Phone as PhoneIcon,
  Tv as TvIcon,
  CheckCircle as SuccessIcon,
  ExpandMore as ExpandMoreIcon,
  RestartAlt as RestartServiceIcon,
  PowerSettingsNew as RebootIcon,
  VideoSettings as RestartStreamIcon,
} from '@mui/icons-material';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  Chip,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Tooltip,
  ToggleButton,
  ToggleButtonGroup,
  CircularProgress,
  Paper,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material';

import { useHostManager } from '../hooks/useHostManager';
import { useRec } from '../hooks/pages/useRec';
import { useDashboard } from '../hooks/pages/useDashboard';
import { Host } from '../types/common/Host_Types';
import { ViewMode } from '../types/pages/Dashboard_Types';

const Dashboard: React.FC = () => {
  const { getAllHosts, availableServers, selectedServer, setSelectedServer } = useHostManager();
  const availableHosts = useMemo(() => getAllHosts(), [getAllHosts]);
  const { restartStreams, isRestarting } = useRec();
  const { stats, serverHostsData, loading, error } = useDashboard();
  const [viewMode, setViewMode] = useState<ViewMode>('grid');
  
  // System control loading states
  const [isRestartingService, setIsRestartingService] = useState(false);
  const [isRebooting, setIsRebooting] = useState(false);

  // Note: Data refresh on server selection is now handled internally by useDashboard hook


  const handleViewModeChange = (_event: React.MouseEvent<HTMLElement>, newViewMode: ViewMode) => {
    if (newViewMode !== null) {
      setViewMode(newViewMode);
      console.log(`View mode changed to ${newViewMode}`);
    }
  };

  // System control handlers
  const handleRestartService = useCallback(async (hostName?: string) => {
    if (isRestartingService) return;
    
    setIsRestartingService(true);
    try {
      const hosts = hostName ? [availableHosts.find(h => h.host_name === hostName)].filter(Boolean) : availableHosts;
      
      for (const host of hosts) {
        if (!host) continue;
        
        const response = await fetch(buildServerUrl('/server/restart/restartService'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ host_name: host.host_name }),
        });
        
        const result = await response.json();
        if (result.success) {
          console.log(`Successfully restarted vpt_host service on ${host.host_name}`);
        } else {
          console.error(`Failed to restart vpt_host service on ${host.host_name}:`, result.error);
        }
      }
    } catch (error) {
      console.error('Error restarting vpt_host service:', error);
    } finally {
      setIsRestartingService(false);
    }
  }, [availableHosts, isRestartingService]);

  const handleReboot = useCallback(async (hostName?: string) => {
    if (isRebooting) return;
    
    setIsRebooting(true);
    try {
      const hosts = hostName ? [availableHosts.find(h => h.host_name === hostName)].filter(Boolean) : availableHosts;
      
      for (const host of hosts) {
        if (!host) continue;
        
        const response = await fetch(buildServerUrl('/server/restart/rebootHost'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ host_name: host.host_name }),
        });
        
        const result = await response.json();
        if (result.success) {
          console.log(`Successfully initiated reboot on ${host.host_name}`);
        } else {
          console.error(`Failed to reboot ${host.host_name}:`, result.error);
        }
      }
    } catch (error) {
      console.error('Error rebooting hosts:', error);
    } finally {
      setIsRebooting(false);
    }
  }, [availableHosts, isRebooting]);

  const getDeviceIcon = (deviceModel: string) => {
    switch (deviceModel) {
      case 'android_mobile':
        return <PhoneIcon color="primary" />;
      case 'android_tv':
        return <TvIcon color="secondary" />;
      default:
        return <ComputerIcon color="info" />;
    }
  };

  const formatLastSeen = (timestamp: number) => {
    const now = Date.now() / 1000;
    const diff = now - timestamp;

    if (diff < 60) return 'Just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return `${Math.floor(diff / 86400)}d ago`;
  };

  const formatRegisteredAt = (dateString: string) => {
    try {
      const date = new Date(dateString);
      return date.toLocaleString();
    } catch {
      return 'Unknown';
    }
  };

  const getUsageColor = (percentage: number) => {
    if (percentage >= 90) return 'error';
    if (percentage >= 75) return 'warning';
    if (percentage >= 50) return 'info';
    return 'success';
  };

  const SystemStatsDisplay: React.FC<{ stats: Host['system_stats'] }> = ({
    stats: systemStats,
  }) => {
    if (!systemStats) {
      return (
        <Typography variant="caption" color="error">
          No system stats available
        </Typography>
      );
    }

    if (systemStats.error) {
      return (
        <Typography variant="caption" color="error">
          {systemStats.error}
        </Typography>
      );
    }

    return (
      <Box display="flex" alignItems="center" gap={2} flexWrap="wrap">
        {/* CPU */}
        <Box display="flex" alignItems="center" gap={0.5}>
          <Typography variant="caption" color="textSecondary">
            CPU:
          </Typography>
          <Typography variant="caption" fontWeight="bold">
            {systemStats.cpu_percent}%
          </Typography>
          <Box sx={{ width: 30, height: 3, backgroundColor: 'grey.300', borderRadius: 1 }}>
            <Box
              sx={{
                width: `${Math.min(systemStats.cpu_percent, 100)}%`,
                height: '100%',
                backgroundColor: `${getUsageColor(systemStats.cpu_percent)}.main`,
                borderRadius: 1,
              }}
            />
          </Box>
        </Box>

        {/* Memory */}
        <Box display="flex" alignItems="center" gap={0.5}>
          <Typography variant="caption" color="textSecondary">
            RAM:
          </Typography>
          <Typography variant="caption" fontWeight="bold">
            {systemStats.memory_percent}%
          </Typography>
          <Box sx={{ width: 30, height: 3, backgroundColor: 'grey.300', borderRadius: 1 }}>
            <Box
              sx={{
                width: `${Math.min(systemStats.memory_percent, 100)}%`,
                height: '100%',
                backgroundColor: `${getUsageColor(systemStats.memory_percent)}.main`,
                borderRadius: 1,
              }}
            />
          </Box>
        </Box>

        {/* Disk */}
        <Box display="flex" alignItems="center" gap={0.5}>
          <Typography variant="caption" color="textSecondary">
            Disk:
          </Typography>
          <Typography variant="caption" fontWeight="bold">
            {systemStats.disk_percent}%
          </Typography>
          <Box sx={{ width: 30, height: 3, backgroundColor: 'grey.300', borderRadius: 1 }}>
            <Box
              sx={{
                width: `${Math.min(systemStats.disk_percent, 100)}%`,
                height: '100%',
                backgroundColor: `${getUsageColor(systemStats.disk_percent)}.main`,
                borderRadius: 1,
              }}
            />
          </Box>
        </Box>
      </Box>
    );
  };

  const renderHostCard = (host: Host) => (
    <Card variant="outlined" sx={{ height: '100%' }}>
      <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
        {/* Host Header */}
        <Box display="flex" alignItems="center" justifyContent="space-between" mb={1.5}>
          <Box display="flex" alignItems="center" gap={1}>
            <ComputerIcon color="primary" />
            <Typography variant="h6" component="div" noWrap>
              {host.host_name}
            </Typography>
            <Chip
              label={`${host.device_count} device${host.device_count > 1 ? 's' : ''}`}
              size="small"
              variant="outlined"
              sx={{ fontSize: '0.7rem' }}
            />
          </Box>
          <Chip
            label={host.status}
            size="small"
            color={host.status === 'online' ? 'success' : 'error'}
            variant="outlined"
          />
        </Box>

        <Typography color="textSecondary" variant="body2" gutterBottom>
          {host.host_url}
        </Typography>

        {/* System Stats - Compact */}
        <Box sx={{ mb: 1.5 }}>
          <Box
            display="flex"
            alignItems="center"
            justifyContent="space-between"
            sx={{ mb: 0.5 }}
          >
            <Typography variant="subtitle2" sx={{ fontWeight: 'bold' }}>
              System Stats
            </Typography>
            <Typography variant="caption" color="textSecondary">
              {host.system_stats?.platform} ({host.system_stats?.architecture})
            </Typography>
          </Box>
          <SystemStatsDisplay stats={host.system_stats} />
        </Box>

        {/* Devices - Collapsible Accordion */}
        <Accordion
          sx={{
            mb: 1.5,
            boxShadow: 'none',
            border: '1px solid #e0e0e0',
            '&:before': { display: 'none' },
          }}
        >
          <AccordionSummary
            expandIcon={<ExpandMoreIcon />}
            sx={{ minHeight: '36px', '& .MuiAccordionSummary-content': { margin: '6px 0' } }}
          >
            <Typography variant="subtitle2" sx={{ fontWeight: 'bold' }}>
              Devices ({host.device_count})
            </Typography>
          </AccordionSummary>
          <AccordionDetails sx={{ pt: 0, pb: 0.5, px: 1 }}>
            <Box sx={{ maxHeight: '150px', overflowY: 'auto', overflowX: 'hidden' }}>
              {host.devices.map((device) => (
                <Box
                  key={device.device_id}
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 1,
                    py: 0.2,
                    px: 0,
                    borderRadius: 1,
                    '&:hover': { backgroundColor: 'grey.100' },
                  }}
                >
                  {getDeviceIcon(device.device_model)}
                  <Typography
                    variant="body2"
                    sx={{ minWidth: '70px', fontWeight: 500, fontSize: '0.8rem' }}
                  >
                    {device.device_name}
                  </Typography>
                  <Chip
                    label={device.device_model}
                    size="small"
                    variant="outlined"
                    sx={{ fontSize: '0.6rem', height: '18px' }}
                  />
                  <Typography
                    variant="caption"
                    color="textSecondary"
                    sx={{ ml: 'auto', fontFamily: 'monospace', fontSize: '0.7rem' }}
                  >
                    {device.device_ip}:{device.device_port}
                  </Typography>
                </Box>
              ))}
            </Box>
          </AccordionDetails>
        </Accordion>

        {/* Per-Host System Controls */}
        <Box display="flex" alignItems="center" justifyContent="center" gap={0.5} sx={{ mb: 1 }}>
          <Tooltip title="Restart vpt_host service">
            <span>
              <IconButton 
                onClick={() => handleRestartService(host.host_name)} 
                disabled={isRestartingService}
                size="small"
                color="warning"
              >
                <RestartServiceIcon fontSize="small" />
              </IconButton>
            </span>
          </Tooltip>
          <Tooltip title="Reboot host">
            <span>
              <IconButton 
                onClick={() => handleReboot(host.host_name)} 
                disabled={isRebooting}
                size="small"
                color="error"
              >
                <RebootIcon fontSize="small" />
              </IconButton>
            </span>
          </Tooltip>
          <Tooltip title="Restart streams">
            <span>
              <IconButton 
                onClick={() => restartStreams()} 
                disabled={isRestarting}
                size="small"
                color="info"
              >
                <RestartStreamIcon fontSize="small" />
              </IconButton>
            </span>
          </Tooltip>
        </Box>

        <Typography color="textSecondary" variant="caption" display="block">
          Last seen: {formatLastSeen(host.last_seen)}
        </Typography>

        <Typography color="textSecondary" variant="caption" display="block">
          Registered: {formatRegisteredAt(host.registered_at)}
        </Typography>
      </CardContent>
    </Card>
  );

  const renderHostTable = (hosts: Host[]) => (
    <TableContainer component={Paper} variant="outlined">
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>Host</TableCell>
            <TableCell>Devices</TableCell>
            <TableCell>Status</TableCell>
            <TableCell>Host URL</TableCell>
            <TableCell>CPU</TableCell>
            <TableCell>RAM</TableCell>
            <TableCell>Disk</TableCell>
            <TableCell>Last Seen</TableCell>
            <TableCell>Registered</TableCell>
            <TableCell>Actions</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {hosts.map((host) => (
            <TableRow
              key={host.host_name}
              sx={{
                '&:hover': {
                  backgroundColor: 'transparent !important',
                },
                '&.MuiTableRow-hover:hover': {
                  backgroundColor: 'transparent !important',
                },
              }}
            >
              <TableCell>
                <Box display="flex" alignItems="center" gap={1}>
                  <ComputerIcon color="primary" />
                  <Typography variant="body2">{host.host_name}</Typography>
                  <Chip
                    label={`${host.device_count} device${host.device_count > 1 ? 's' : ''}`}
                    size="small"
                    variant="outlined"
                    sx={{ fontSize: '0.7rem' }}
                  />
                </Box>
              </TableCell>
              <TableCell>
                <Box>
                  {host.devices.map((device) => (
                    <Box key={device.device_id} display="flex" alignItems="center" gap={1} mb={0.5}>
                      {getDeviceIcon(device.device_model)}
                      <Typography variant="body2" fontFamily="monospace">
                        {device.device_name} ({device.device_ip}:{device.device_port})
                      </Typography>
                    </Box>
                  ))}
                </Box>
              </TableCell>
              <TableCell>
                <Chip
                  label={host.status}
                  size="small"
                  color={host.status === 'online' ? 'success' : 'error'}
                  variant="outlined"
                />
              </TableCell>
              <TableCell>
                <Typography variant="body2" fontFamily="monospace">
                  {host.host_url}
                </Typography>
              </TableCell>
              <TableCell>
                <Box display="flex" alignItems="center" gap={1}>
                  <Typography variant="body2" fontWeight="bold">
                    {host.system_stats.cpu_percent}%
                  </Typography>
                  <Box
                    sx={{
                      width: 40,
                      height: 4,
                      backgroundColor: 'grey.300',
                      borderRadius: 1,
                    }}
                  >
                    <Box
                      sx={{
                        width: `${Math.min(host.system_stats.cpu_percent, 100)}%`,
                        height: '100%',
                        backgroundColor: `${getUsageColor(host.system_stats.cpu_percent)}.main`,
                        borderRadius: 1,
                      }}
                    />
                  </Box>
                </Box>
              </TableCell>
              <TableCell>
                <Box display="flex" alignItems="center" gap={1}>
                  <Typography variant="body2" fontWeight="bold">
                    {host.system_stats.memory_percent}%
                  </Typography>
                  <Box
                    sx={{
                      width: 40,
                      height: 4,
                      backgroundColor: 'grey.300',
                      borderRadius: 1,
                    }}
                  >
                    <Box
                      sx={{
                        width: `${Math.min(host.system_stats.memory_percent, 100)}%`,
                        height: '100%',
                        backgroundColor: `${getUsageColor(host.system_stats.memory_percent)}.main`,
                        borderRadius: 1,
                      }}
                    />
                  </Box>
                </Box>
              </TableCell>
              <TableCell>
                <Box display="flex" alignItems="center" gap={1}>
                  <Typography variant="body2" fontWeight="bold">
                    {host.system_stats.disk_percent}%
                  </Typography>
                  <Box
                    sx={{
                      width: 40,
                      height: 4,
                      backgroundColor: 'grey.300',
                      borderRadius: 1,
                    }}
                  >
                    <Box
                      sx={{
                        width: `${Math.min(host.system_stats.disk_percent, 100)}%`,
                        height: '100%',
                        backgroundColor: `${getUsageColor(host.system_stats.disk_percent)}.main`,
                        borderRadius: 1,
                      }}
                    />
                  </Box>
                </Box>
              </TableCell>
              <TableCell>
                <Typography variant="body2">{formatLastSeen(host.last_seen)}</Typography>
              </TableCell>
              <TableCell>
                <Typography variant="body2">{formatRegisteredAt(host.registered_at)}</Typography>
              </TableCell>
              <TableCell>
                <Box display="flex" alignItems="center" gap={0.5}>
                  <Tooltip title="Restart vpt_host service">
                    <span>
                      <IconButton 
                        onClick={() => handleRestartService(host.host_name)} 
                        disabled={isRestartingService}
                        size="small"
                        color="warning"
                      >
                        <RestartServiceIcon fontSize="small" />
                      </IconButton>
                    </span>
                  </Tooltip>
                  <Tooltip title="Reboot host">
                    <span>
                      <IconButton 
                        onClick={() => handleReboot(host.host_name)} 
                        disabled={isRebooting}
                        size="small"
                        color="error"
                      >
                        <RebootIcon fontSize="small" />
                      </IconButton>
                    </span>
                  </Tooltip>
                  <Tooltip title="Restart streams">
                    <span>
                      <IconButton 
                        onClick={() => restartStreams()} 
                        disabled={isRestarting}
                        size="small"
                        color="info"
                      >
                        <RestartStreamIcon fontSize="small" />
                      </IconButton>
                    </span>
                  </Tooltip>
                </Box>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );



  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }


  return (
    <Box>
      {/* Server Selector */}
      <Box display="flex" alignItems="center" justifyContent="space-between" mb={1}>
        <Typography variant="h4" component="h1">
          Dashboard
        </Typography>
        <FormControl size="small" sx={{ minWidth: 300 }}>
          <InputLabel>Primary Server</InputLabel>
          <Select
            value={(() => {
              // If selectedServer doesn't match any MenuItem value, find the best match
              const hasExactMatch = serverHostsData.some(serverData => 
                serverData.server_info.server_url === selectedServer
              );
              
              if (hasExactMatch) {
                return selectedServer;
              }
              
              // Find a matching server by comparing normalized URLs
              const normalizeUrl = (url: string) => url.replace(/^https?:\/\//, '').replace(/:\d+$/, '');
              const normalizedSelected = normalizeUrl(selectedServer);
              
              const matchingServer = serverHostsData.find(serverData => {
                const normalizedServerUrl = normalizeUrl(serverData.server_info.server_url);
                return normalizedSelected === normalizedServerUrl;
              });
              
              return matchingServer ? matchingServer.server_info.server_url : '';
            })()}
            label="Primary Server"
            onChange={(e) => setSelectedServer(e.target.value)}
          >
            {serverHostsData
              .sort((a, b) => {
                // Ensure primary server (first in availableServers) appears first
                const primaryServerUrl = availableServers[0];
                const aIsPrimary = a.server_info.server_url.includes(primaryServerUrl?.replace(/^https?:\/\//, '') || '');
                const bIsPrimary = b.server_info.server_url.includes(primaryServerUrl?.replace(/^https?:\/\//, '') || '');
                if (aIsPrimary && !bIsPrimary) return -1;
                if (!aIsPrimary && bIsPrimary) return 1;
                return 0;
              })
              .map((serverData, index) => {
                const isSelected = selectedServer === serverData.server_info.server_url;
                return (
                  <MenuItem 
                    key={`${serverData.server_info.server_url}-${index}`} 
                    value={serverData.server_info.server_url}
                    sx={{
                      fontWeight: isSelected ? 'bold' : 'normal',
                      color: isSelected ? 'primary.main' : 'text.primary',
                      backgroundColor: isSelected ? 'primary.light' : 'transparent',
                      '&:hover': {
                        backgroundColor: isSelected ? 'primary.light' : 'action.hover',
                      }
                    }}
                  >
                    {serverData.server_info.server_name} ({serverData.server_info.server_url.replace(/^https?:\/\//, '')})
                  </MenuItem>
                );
              })}
          </Select>
        </FormControl>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 1 }}>
          {error}
        </Alert>
      )}

      {/* Statistics Cards */}
      <Box mb={1}>
      </Box>
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography color="textSecondary" gutterBottom>
                    Test Cases
                  </Typography>
                  <Typography variant="h4">{stats.testCases}</Typography>
                </Box>
                <TestIcon color="primary" sx={{ fontSize: 40 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography color="textSecondary" gutterBottom>
                    Campaigns
                  </Typography>
                  <Typography variant="h4">{stats.campaigns}</Typography>
                </Box>
                <CampaignIcon color="secondary" sx={{ fontSize: 40 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography color="textSecondary" gutterBottom>
                    Navigation Trees
                  </Typography>
                  <Typography variant="h4">{stats.trees}</Typography>
                </Box>
                <TreeIcon color="info" sx={{ fontSize: 40 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography color="textSecondary" gutterBottom>
                    Connected Devices
                  </Typography>
                  <Typography variant="h4">
                    {serverHostsData.reduce((total, serverData) => 
                      total + serverData.hosts.reduce((hostTotal, host) => hostTotal + (host.device_count || 0), 0), 0
                    )}
                  </Typography>
                </Box>
                <DevicesIcon color="success" sx={{ fontSize: 40 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Grid container spacing={3}>
        {/* Quick Actions */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Quick Actions
            </Typography>
            <Box display="flex" flexDirection="column" gap={2}>
              <Button variant="contained" startIcon={<AddIcon />} href="/testcases" fullWidth>
                Create New Test Case
              </Button>
              <Button
                variant="contained"
                startIcon={<AddIcon />}
                href="/campaigns"
                fullWidth
                color="secondary"
              >
                Create New Campaign
              </Button>
              <Button variant="outlined" startIcon={<PlayIcon />} fullWidth disabled>
                Run Test Campaign (Coming Soon)
              </Button>
            </Box>
          </Paper>
        </Grid>
      </Grid>

      {/* Connected Devices */}
      <Paper sx={{ p: 2, mt: 3 }}>
        <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
          <Typography variant="h6">
            Registered Servers ({serverHostsData.length}) -{' '}
            {serverHostsData.reduce((total, serverData) => total + serverData.hosts.length, 0)} Hosts -{' '}
            {serverHostsData.reduce((total, serverData) => 
              total + serverData.hosts.reduce((hostTotal, host) => hostTotal + (host.device_count || 0), 0), 0
            )} Devices
          </Typography>
          <Box display="flex" alignItems="center" gap={1}>
            {/* Global System Controls */}
            <Tooltip title="Restart vpt_host service on all hosts">
              <span>
                <IconButton 
                  onClick={() => handleRestartService()} 
                  disabled={isRestartingService}
                  size="small"
                  color="warning"
                >
                  <RestartServiceIcon />
                </IconButton>
              </span>
            </Tooltip>
            <Tooltip title="Reboot all hosts">
              <span>
                <IconButton 
                  onClick={() => handleReboot()} 
                  disabled={isRebooting}
                  size="small"
                  color="error"
                >
                  <RebootIcon />
                </IconButton>
              </span>
            </Tooltip>
            <Tooltip title="Restart streams on all hosts">
              <span>
                <IconButton 
                  onClick={() => restartStreams()} 
                  disabled={isRestarting}
                  size="small"
                  color="info"
                >
                  <RestartStreamIcon />
                </IconButton>
              </span>
            </Tooltip>
            
            <ToggleButtonGroup
              value={viewMode}
              exclusive
              onChange={handleViewModeChange}
              size="small"
            >
              <ToggleButton value="grid">
                <Tooltip title="Grid View">
                  <GridViewIcon />
                </Tooltip>
              </ToggleButton>
              <ToggleButton value="table">
                <Tooltip title="Table View">
                  <TableViewIcon />
                </Tooltip>
              </ToggleButton>
            </ToggleButtonGroup>
            <Tooltip title="Hosts automatically refresh">
              <span>
                <IconButton disabled size="small">
                  <RefreshIcon />
                </IconButton>
              </span>
            </Tooltip>
          </Box>
        </Box>

        {serverHostsData.length > 0 ? (
          serverHostsData.map((serverData, index) => {
            const hostCount = serverData.hosts.length;
            const deviceCount = serverData.hosts.reduce((total, host) => total + (host.device_count || 0), 0);
            const serverIp = serverData.server_info.server_url.replace(/^https?:\/\//, '');
            
            return (
              <Box 
                key={index} 
                sx={{ 
                  backgroundColor: 'transparent', 
                  borderRadius: 2, 
                  p: 2, 
                  mb: 2,
                  border: '1px solid',
                  borderColor: 'grey.200'
                }}
              >
                <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
                  <Typography variant="h6">
                    Server: {serverData.server_info.server_name} ({serverIp})
                  </Typography>
                  <Box display="flex" alignItems="center" gap={2}>
                    <Chip 
                      label={`${hostCount} host${hostCount !== 1 ? 's' : ''}`}
                      size="small"
                      variant="outlined"
                      color="primary"
                    />
                    <Chip 
                      label={`${deviceCount} device${deviceCount !== 1 ? 's' : ''}`}
                      size="small"
                      variant="outlined"
                      color="secondary"
                    />
                  </Box>
                </Box>
              
              {serverData.hosts.length > 0 ? (
                viewMode === 'grid' ? (
                  <Grid container spacing={2}>
                    {serverData.hosts.map((host) => (
                      <Grid item xs={12} sm={6} md={4} lg={4} xl={3} key={host.host_name}>
                        {/* Reuse existing host card rendering */}
                        {renderHostCard(host)}
                      </Grid>
                    ))}
                  </Grid>
                ) : (
                  renderHostTable(serverData.hosts)
                )
              ) : (
                <Typography color="textSecondary">No hosts connected to this server</Typography>
              )}
            </Box>
          )})
        ) : (
          <Box textAlign="center" py={4}>
            <DevicesIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
            <Typography color="textSecondary" variant="h6" gutterBottom>
              No servers connected
            </Typography>
          </Box>
        )}
      </Paper>

      {/* System Status */}
      <Paper sx={{ p: 1, mt: 3 }}>
        <Grid container spacing={2}>
          <Grid item xs={12} sm={6} md={3} key="api-server">
            <Box display="flex" alignItems="center" gap={1}>
              <SuccessIcon color="success" />
              <Typography>API Server: Online</Typography>
            </Box>
          </Grid>
          <Grid item xs={12} sm={6} md={3} key="database">
            <Box display="flex" alignItems="center" gap={1}>
              <SuccessIcon color="success" />
              <Typography>Database: Connected</Typography>
            </Box>
          </Grid>
        </Grid>
      </Paper>
    </Box>
  );
};

export default Dashboard;
