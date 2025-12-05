import React, { useState, useCallback, useMemo } from 'react';
import { buildServerUrl, buildServerUrlForServer } from '../utils/buildUrlUtils';
import { formatToLocalTime } from '../utils/dateUtils';

import {
  Computer as ComputerIcon,
  Refresh as RefreshIcon,
  Assignment as TestIcon,
  Campaign as CampaignIcon,
  AccountTree as TreeIcon,
  Devices as DevicesIcon,
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
  Chip,
  Alert,
  IconButton,
  Tooltip,
  CircularProgress,
  Paper,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material';

import { useHostManager } from '../hooks/useHostManager';
import { useServerManager } from '../hooks/useServerManager';
import { useRec } from '../hooks/pages/useRec';
import { useDashboard } from '../hooks/pages/useDashboard';
import { Host } from '../types/common/Host_Types';

const Dashboard: React.FC = () => {
  const { getAllHosts } = useHostManager();
  const { serverHostsData, isLoading: serverLoading, error: serverError } = useServerManager();
  const availableHosts = useMemo(() => getAllHosts(), [getAllHosts]);
  const { restartStreams, isRestarting } = useRec();
  const { stats, loading: statsLoading, error: statsError } = useDashboard();
  
  // Combine loading and error states
  const loading = serverLoading || statsLoading;
  const error = serverError || statsError;
  
  // System control loading states
  const [isRestartingService, setIsRestartingService] = useState(false);
  const [isRebooting, setIsRebooting] = useState(false);

  // Note: Data refresh on server selection is now handled internally by useDashboard hook

  // System control handlers for HOSTS
  const handleRestartService = useCallback(async (hostName?: string) => {
    if (isRestartingService) return;
    
    setIsRestartingService(true);
    try {
      const hosts = hostName ? [availableHosts.find(h => h.host_name === hostName)].filter(Boolean) : availableHosts;
      
      for (const host of hosts) {
        if (!host) continue;
        
        const response = await fetch(buildServerUrl('/server/system/restartHostService'), {
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
        
        const response = await fetch(buildServerUrl('/server/system/rebootHost'), {
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

  // System control handlers for SERVER
  const [isRestartingServerService, setIsRestartingServerService] = useState(false);
  const handleRestartServerService = useCallback(async (serverUrl: string) => {
    if (isRestartingServerService) return;
    
    setIsRestartingServerService(true);
    try {
      const response = await fetch(buildServerUrlForServer(serverUrl, '/server/system/restartServerService'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      
      const result = await response.json();
      if (result.success) {
        console.log(`Successfully restarted vpt_server_host service on server ${serverUrl}`);
      } else {
        console.error(`Failed to restart vpt_server_host service on server ${serverUrl}:`, result.error);
      }
    } catch (error) {
      console.error('Error restarting vpt_server_host service:', error);
    } finally {
      setIsRestartingServerService(false);
    }
  }, [isRestartingServerService]);

  const [isRebootingServer, setIsRebootingServer] = useState(false);
  const handleRebootServer = useCallback(async (serverUrl: string) => {
    if (isRebootingServer) return;
    
    setIsRebootingServer(true);
    try {
      const response = await fetch(buildServerUrlForServer(serverUrl, '/server/system/rebootServer'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      
      const result = await response.json();
      if (result.success) {
        console.log(`Successfully initiated reboot on server ${serverUrl}`);
      } else {
        console.error(`Failed to reboot server ${serverUrl}:`, result.error);
      }
    } catch (error) {
      console.error('Error rebooting server:', error);
    } finally {
      setIsRebootingServer(false);
    }
  }, [isRebootingServer]);

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
    return formatToLocalTime(dateString) || 'Unknown';
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

        {/* Load Average */}
        {systemStats.load_average_1m !== undefined && (
          <Box display="flex" alignItems="center" gap={0.5}>
            <Typography variant="caption" color="textSecondary">
              Load:
            </Typography>
            <Typography variant="caption" fontWeight="bold">
              {systemStats.load_average_1m.toFixed(1)}
            </Typography>
          </Box>
        )}
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
            backgroundColor: 'transparent',
            '&:before': { display: 'none' },
          }}
        >
          <AccordionSummary
            expandIcon={<ExpandMoreIcon />}
            sx={{ 
              minHeight: '36px', 
              backgroundColor: 'transparent',
              '& .MuiAccordionSummary-content': { margin: '6px 0' } 
            }}
          >
            <Typography variant="subtitle2" sx={{ fontWeight: 'bold' }}>
              Devices ({host.device_count})
            </Typography>
          </AccordionSummary>
          <AccordionDetails sx={{ pt: 0, pb: 0.5, px: 1, backgroundColor: 'transparent' }}>
            <Box sx={{ maxHeight: '150px', overflowY: 'auto', overflowX: 'hidden', backgroundColor: 'transparent' }}>
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
                    backgroundColor: 'transparent',
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

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }


  return (
    <Box>
      {/* Dashboard Header */}
      <Typography variant="h4" component="h1" mb={1}>
        Dashboard
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 1 }}>
          {error}
        </Alert>
      )}

      {/* Statistics Cards */}
      <Box mb={1}>
      </Box>
      <Grid container spacing={3} sx={{ mb: 1 }}>
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
                  <Box display="flex" alignItems="center" gap={2}>
                    <Typography variant="h6">
                      Server: {serverData.server_info.server_name} - {serverData.server_info.server_url_display}
                    </Typography>
                    {/* Compact Server Stats */}
                    {serverData.server_info.system_stats && (
                      <Box display="flex" alignItems="center" gap={1}>
                        <Chip 
                          label={`CPU: ${serverData.server_info.system_stats.cpu_percent.toFixed(0)}%`}
                          size="small"
                          sx={{ 
                            height: 20, 
                            fontSize: '0.7rem',
                            bgcolor: `${getUsageColor(serverData.server_info.system_stats.cpu_percent)}.100`,
                            color: 'text.primary'
                          }}
                        />
                        <Chip 
                          label={`RAM: ${serverData.server_info.system_stats.memory_percent.toFixed(0)}%`}
                          size="small"
                          sx={{ 
                            height: 20, 
                            fontSize: '0.7rem',
                            bgcolor: `${getUsageColor(serverData.server_info.system_stats.memory_percent)}.100`,
                            color: 'text.primary'
                          }}
                        />
                        <Chip 
                          label={`Disk: ${serverData.server_info.system_stats.disk_percent.toFixed(0)}%`}
                          size="small"
                          sx={{ 
                            height: 20, 
                            fontSize: '0.7rem',
                            bgcolor: `${getUsageColor(serverData.server_info.system_stats.disk_percent)}.100`,
                            color: 'text.primary'
                          }}
                        />
                        {serverData.server_info.system_stats.cpu_temperature_celsius && (
                          <Chip 
                            label={`${serverData.server_info.system_stats.cpu_temperature_celsius.toFixed(0)}°C`}
                            size="small"
                            sx={{ height: 20, fontSize: '0.7rem' }}
                          />
                        )}
                        {serverData.server_info.system_stats.load_average_1m !== undefined && (
                          <Chip 
                            label={`Load: ${serverData.server_info.system_stats.load_average_1m.toFixed(1)}`}
                            size="small"
                            sx={{ height: 20, fontSize: '0.7rem' }}
                          />
                        )}
                      </Box>
                    )}
                  </Box>
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
                    <Tooltip title="Restart vpt_server_host service">
                      <span>
                        <IconButton 
                          onClick={() => handleRestartServerService(serverData.server_info.server_url)} 
                          disabled={isRestartingServerService}
                          size="small"
                          color="warning"
                        >
                          <RestartServiceIcon fontSize="small" />
                        </IconButton>
                      </span>
                    </Tooltip>
                    <Tooltip title="Reboot server">
                      <span>
                        <IconButton 
                          onClick={() => handleRebootServer(serverData.server_info.server_url)} 
                          disabled={isRebootingServer}
                          size="small"
                          color="error"
                        >
                          <RebootIcon fontSize="small" />
                        </IconButton>
                      </span>
                    </Tooltip>
                  </Box>
                </Box>
              
              {serverData.hosts.length > 0 ? (
                <Grid container spacing={2}>
                  {serverData.hosts.map((host) => (
                    <Grid item xs={12} sm={6} md={4} lg={4} xl={3} key={host.host_name}>
                      {renderHostCard(host)}
                    </Grid>
                  ))}
                </Grid>
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
