import { PlayArrow, Pause, Delete, Add, Close, Link as LinkIcon, Edit, Save, Cancel } from '@mui/icons-material';
import {
  Box, Typography, Card, CardContent, Button, Grid, TextField, Select, MenuItem,
  FormControl, InputLabel, Table, TableBody, TableCell, TableContainer, TableHead,
  TableRow, Paper, IconButton, Chip, Dialog, DialogTitle, DialogContent, DialogActions
} from '@mui/material';
import React, { useState, useEffect } from 'react';
import { UserinterfaceSelector } from '../components/common/UserinterfaceSelector';
import { CronHelper } from '../components/common/CronHelper';
import { useHostManager } from '../hooks/useHostManager';
import { useToast } from '../hooks/useToast';
import { useDeployment, Deployment } from '../hooks/useDeployment';
import { useRun } from '../hooks/useRun';
import { buildServerUrl } from '../utils/buildUrlUtils';
import { getLogsUrl } from '../utils/executionUtils';
import { getUserTimezone, formatToLocalTime } from '../utils/dateUtils';
import { validateCronExpression, cronToHuman } from '../utils/cronUtils';

interface AdditionalDevice {
  hostName: string;
  deviceId: string;
  deviceModel: string;
  userinterface: string;
}

const Deployments: React.FC = () => {
  const { createDeployment, listDeployments, pauseDeployment, resumeDeployment, deleteDeployment, getRecentExecutions } = useDeployment();
  const { getAllHosts, getDevicesFromHost } = useHostManager();
  const { showSuccess, showError } = useToast();

  const [showCreate, setShowCreate] = useState(false);
  const [selectedScript, setSelectedScript] = useState('');
  const [selectedHost, setSelectedHost] = useState('');
  const [selectedDevice, setSelectedDevice] = useState('');
  const [selectedUserinterface, setSelectedUserinterface] = useState('');
  
  // Cron-based scheduling
  const [cronExpression, setCronExpression] = useState('*/10 * * * *'); // Default: every 10 min
  const [cronError, setCronError] = useState<string>('');
  
  // Optional constraints with smart defaults
  const [startDateOption, setStartDateOption] = useState<'now' | '1hour' | '6hours' | 'tomorrow' | 'nextMonday' | 'custom'>('now');
  const [startDateCustom, setStartDateCustom] = useState<string>('');
  const [endDateOption, setEndDateOption] = useState<'never' | '1day' | '7days' | '30days' | '90days' | 'custom'>('never');
  const [endDateCustom, setEndDateCustom] = useState<string>('');
  const [maxExecutions, setMaxExecutions] = useState<string>(''); // Empty by default (unlimited)
  
  const [deployments, setDeployments] = useState<Deployment[]>([]);
  const [executions, setExecutions] = useState<any[]>([]);
  const [scripts, setScripts] = useState<string[]>([]);
  const [additionalDevices, setAdditionalDevices] = useState<AdditionalDevice[]>([]);
  
  // Edit deployment state
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editingDeployment, setEditingDeployment] = useState<Deployment | null>(null);
  const [editCron, setEditCron] = useState('');
  const [editStartDate, setEditStartDate] = useState('');
  const [editEndDate, setEditEndDate] = useState('');
  const [editMaxExecutions, setEditMaxExecutions] = useState('');

  const hosts = getAllHosts();
  const userTimezone = getUserTimezone();
  
  // Validate cron expression
  useEffect(() => {
    if (cronExpression) {
      const { valid, error } = validateCronExpression(cronExpression);
      setCronError(valid ? '' : (error || 'Invalid cron expression'));
    }
  }, [cronExpression]);

  // Helper functions to convert dropdown options to dates
  const getStartDate = (): string | null => {
    if (startDateOption === 'now') return null; // Start immediately
    if (startDateOption === 'custom') return startDateCustom ? new Date(startDateCustom).toISOString() : null;
    
    const now = new Date();
    switch (startDateOption) {
      case '1hour':
        now.setHours(now.getHours() + 1);
        break;
      case '6hours':
        now.setHours(now.getHours() + 6);
        break;
      case 'tomorrow':
        now.setDate(now.getDate() + 1);
        now.setHours(0, 0, 0, 0);
        break;
      case 'nextMonday':
        const daysUntilMonday = (8 - now.getDay()) % 7 || 7;
        now.setDate(now.getDate() + daysUntilMonday);
        now.setHours(0, 0, 0, 0);
        break;
    }
    return now.toISOString();
  };

  const getEndDate = (): string | null => {
    if (endDateOption === 'never') return null; // Run forever
    if (endDateOption === 'custom') return endDateCustom ? new Date(endDateCustom).toISOString() : null;
    
    const now = new Date();
    switch (endDateOption) {
      case '1day':
        now.setDate(now.getDate() + 1);
        break;
      case '7days':
        now.setDate(now.getDate() + 7);
        break;
      case '30days':
        now.setDate(now.getDate() + 30);
        break;
      case '90days':
        now.setDate(now.getDate() + 90);
        break;
    }
    return now.toISOString();
  };
  
  // Function to get available devices for selection (excluding already selected ones)
  const getAvailableDevicesForSelection = () => {
    if (!selectedHost) return [];
    
    const allDevicesForHost = getDevicesFromHost(selectedHost);
    const selectedDeviceIds = additionalDevices
      .filter(d => d.hostName === selectedHost)
      .map(d => d.deviceId);
    
    return allDevicesForHost.filter(device => 
      !selectedDeviceIds.includes(device.device_id)
    );
  };

  const devices = getAvailableDevicesForSelection();
  const deviceModel = devices.find(d => d.device_id === selectedDevice)?.device_model || 'unknown';

  // Function to check if there are more devices available to add across all hosts
  const hasMoreDevicesAvailable = () => {
    const allSelectedDevices = [...additionalDevices];
    if (selectedHost && selectedDevice) {
      allSelectedDevices.push({ 
        hostName: selectedHost, 
        deviceId: selectedDevice,
        deviceModel: deviceModel,
        userinterface: selectedUserinterface
      });
    }
    
    for (const host of hosts) {
      const hostDevices = getDevicesFromHost(host.host_name);
      const selectedDevicesForHost = allSelectedDevices
        .filter(d => d.hostName === host.host_name)
        .map(d => d.deviceId);
      
      const availableDevicesForHost = hostDevices.filter(device => 
        !selectedDevicesForHost.includes(device.device_id)
      );
      
      if (availableDevicesForHost.length > 0) {
        return true;
      }
    }
    
    return false;
  };

  const { scriptAnalysis, parameterValues, handleParameterChange } = useRun({
    selectedScript,
    selectedDevice,
    selectedHost,
    deviceModel,
    showWizard: showCreate
  });

  const FRAMEWORK_PARAMS = ['host', 'device', 'userinterface_name'];
  const displayParameters = scriptAnalysis?.parameters.filter(p => !FRAMEWORK_PARAMS.includes(p.name)) || [];

  useEffect(() => {
    loadScripts();
    loadDeployments();
    loadExecutions();
    
    // Auto-refresh executions every 10 seconds
    const intervalId = setInterval(() => {
      loadExecutions();
    }, 10000);
    
    return () => clearInterval(intervalId);
  }, []);

  const loadScripts = async () => {
    try {
      const res = await fetch(buildServerUrl('/server/script/list'));
      const data = await res.json();
      if (data.success) setScripts(data.scripts);
    } catch (error) {
      showError('Failed to load scripts');
      console.error('Error loading scripts:', error);
    }
  };

  const loadDeployments = async () => {
    const res = await listDeployments();
    if (res.success) setDeployments(res.deployments);
  };

  const loadExecutions = async () => {
    const res = await getRecentExecutions();
    if (res.success) setExecutions(res.executions);
  };

  const handleCreate = async () => {
    // Validate cron expression
    const { valid, error } = validateCronExpression(cronExpression);
    if (!valid) {
      showError(`Invalid cron expression: ${error}`);
      return;
    }
    
    // Build complete device list: primary device + additional devices
    const allDevices: AdditionalDevice[] = [];
    
    // Add primary device if selected
    if (selectedHost && selectedDevice && selectedUserinterface) {
      allDevices.push({ 
        hostName: selectedHost, 
        deviceId: selectedDevice,
        deviceModel: deviceModel,
        userinterface: selectedUserinterface
      });
    }
    
    // Add additional devices
    allDevices.push(...additionalDevices);

    if (allDevices.length === 0 || !selectedScript) {
      showError('Please select at least one device and a script');
      return;
    }

    const params = displayParameters.map(p => `--${p.name} ${parameterValues[p.name] || ''}`).join(' ');
    // Simple timestamp: HHMMSS
    const now = new Date();
    const timestamp = `${now.getHours().toString().padStart(2, '0')}${now.getMinutes().toString().padStart(2, '0')}${now.getSeconds().toString().padStart(2, '0')}`;
    
    // Prepare optional constraints using helper functions
    const deploymentData: any = {
      cron_expression: cronExpression,
    };
    
    const startDate = getStartDate();
    if (startDate) {
      deploymentData.start_date = startDate;
    }
    
    const endDate = getEndDate();
    if (endDate) {
      deploymentData.end_date = endDate;
    }
    
    if (maxExecutions && parseInt(maxExecutions) > 0) {
      deploymentData.max_executions = parseInt(maxExecutions);
    }
    
    // Create deployments for all devices
    let successCount = 0;
    for (const device of allDevices) {
      const deploymentName = `${selectedScript}_${timestamp}`;
      
      const res = await createDeployment({
        name: deploymentName,
        host_name: device.hostName,
        device_id: device.deviceId,
        script_name: selectedScript,
        userinterface_name: device.userinterface,
        parameters: params,
        ...deploymentData
      });

      if (res.success) {
        successCount++;
      } else {
        showError(`Failed to create deployment for ${device.hostName}:${device.deviceId}`);
      }
    }

    if (successCount > 0) {
      showSuccess(`Created ${successCount} deployment${successCount > 1 ? 's' : ''} successfully`);
      setShowCreate(false);
      setSelectedHost('');
      setSelectedDevice('');
      setSelectedUserinterface('');
      setAdditionalDevices([]);
      setCronExpression('*/10 * * * *');
      setStartDateOption('now');
      setStartDateCustom('');
      setEndDateOption('never');
      setEndDateCustom('');
      setMaxExecutions('');
      loadDeployments();
    }
  };

  const handlePause = async (id: string) => {
    await pauseDeployment(id);
    loadDeployments();
  };

  const handleResume = async (id: string) => {
    await resumeDeployment(id);
    loadDeployments();
  };

  const handleDelete = async (id: string, deploymentName: string) => {
    if (!window.confirm(`Are you sure you want to delete deployment "${deploymentName}"?\n\nThis action cannot be undone.`)) {
      return;
    }
    await deleteDeployment(id);
    loadDeployments();
  };

  const handleEditOpen = (deployment: Deployment) => {
    setEditingDeployment(deployment);
    setEditCron(deployment.cron_expression);
    setEditStartDate(deployment.start_date || '');
    setEditEndDate(deployment.end_date || '');
    setEditMaxExecutions(deployment.max_executions?.toString() || '');
    setEditDialogOpen(true);
  };

  const handleEditClose = () => {
    setEditDialogOpen(false);
    setEditingDeployment(null);
  };

  const handleEditSave = async () => {
    if (!editingDeployment) return;

    const { valid } = validateCronExpression(editCron);
    if (!valid) {
      showError('Invalid cron expression');
      return;
    }

    try {
      const updateData: any = {
        cron_expression: editCron,
        start_date: editStartDate || null,
        end_date: editEndDate || null,
        max_executions: editMaxExecutions ? parseInt(editMaxExecutions) : null,
      };

      // Call update API
      const res = await fetch(buildServerUrl(`/server/deployment/update/${editingDeployment.id}`), {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updateData),
      });

      const data = await res.json();
      if (data.success) {
        showSuccess('Deployment updated successfully');
        handleEditClose();
        loadDeployments();
      } else {
        showError(data.error || 'Failed to update deployment');
      }
    } catch (error) {
      showError('Failed to update deployment');
      console.error('Error updating deployment:', error);
    }
  };

  return (
    <Box sx={{ p: 1 }}>
      <Typography variant="h5" sx={{ mb: 1 }}>Deployments</Typography>

      <Grid container spacing={2}>
        {/* Create Deployment */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 1 }}>Create Deployment</Typography>
              {!showCreate ? (
                <Button variant="contained" startIcon={<Add />} onClick={() => setShowCreate(true)}>
                  New Deployment
                </Button>
              ) : (
                <>
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                    {/* Configuration */}
                    <Box>
                      <Typography variant="subtitle2" sx={{ mb: 1 }}>Configuration</Typography>
                      <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                        <FormControl size="small" sx={{ minWidth: 150 }}>
                          <InputLabel>Script</InputLabel>
                          <Select value={selectedScript} label="Script" onChange={e => setSelectedScript(e.target.value)}>
                            {scripts.map(s => <MenuItem key={s} value={s}>{s}</MenuItem>)}
                          </Select>
                        </FormControl>
                        <FormControl size="small" sx={{ minWidth: 150 }}>
                          <InputLabel>Host</InputLabel>
                          <Select value={selectedHost} label="Host" onChange={e => setSelectedHost(e.target.value)}>
                            {hosts.map(h => <MenuItem key={h.host_name} value={h.host_name}>{h.host_name}</MenuItem>)}
                          </Select>
                        </FormControl>
                        <FormControl size="small" sx={{ minWidth: 150 }}>
                          <InputLabel>Device</InputLabel>
                          <Select value={selectedDevice} label="Device" onChange={e => setSelectedDevice(e.target.value)} disabled={!selectedHost}>
                            {devices.map(d => <MenuItem key={d.device_id} value={d.device_id}>{d.device_name}</MenuItem>)}
                          </Select>
                        </FormControl>
                        <Box sx={{ minWidth: 150 }}>
                          <UserinterfaceSelector deviceModel={deviceModel} value={selectedUserinterface} onChange={setSelectedUserinterface} label="Userinterface" size="small" fullWidth />
                        </Box>
                        {displayParameters.map(p => (
                          <TextField key={p.name} label={p.name} value={parameterValues[p.name] || ''} onChange={e => handleParameterChange(p.name, e.target.value)} size="small" />
                        ))}
                      </Box>
                    </Box>

                    {/* Schedule - Everything on ONE line */}
                    <Box>
                      <Typography variant="subtitle2" sx={{ mb: 1 }}>Schedule</Typography>
                      <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', flexWrap: 'wrap' }}>
                        {/* Cron pattern selector */}
                        <CronHelper 
                          value={cronExpression} 
                          onChange={setCronExpression}
                          error={cronError}
                        />
                        
                        {/* Cron expression display */}
                        <Typography 
                          variant="body2" 
                          sx={{ 
                            fontFamily: 'monospace', 
                            color: 'text.secondary',
                            fontSize: '0.875rem',
                            minWidth: 100
                          }}
                        >
                          {cronExpression}
                        </Typography>

                        {/* Start constraint */}
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                          <Typography variant="body2" sx={{ minWidth: 40 }}>Start</Typography>
                          <FormControl size="small" sx={{ minWidth: 120 }}>
                            <Select
                              value={startDateOption}
                              onChange={e => setStartDateOption(e.target.value as any)}
                              displayEmpty
                            >
                              <MenuItem value="now">Now</MenuItem>
                              <MenuItem value="1hour">In 1 hour</MenuItem>
                              <MenuItem value="6hours">In 6 hours</MenuItem>
                              <MenuItem value="tomorrow">Tomorrow 00:00</MenuItem>
                              <MenuItem value="nextMonday">Next Monday</MenuItem>
                              <MenuItem value="custom">Pick date...</MenuItem>
                            </Select>
                          </FormControl>
                          {startDateOption === 'custom' && (
                            <TextField
                              type="datetime-local"
                              size="small"
                              value={startDateCustom}
                              onChange={e => setStartDateCustom(e.target.value)}
                              sx={{ width: 200 }}
                            />
                          )}
                        </Box>

                        {/* End constraint */}
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                          <Typography variant="body2" sx={{ minWidth: 30 }}>End</Typography>
                          <FormControl size="small" sx={{ minWidth: 120 }}>
                            <Select
                              value={endDateOption}
                              onChange={e => setEndDateOption(e.target.value as any)}
                              displayEmpty
                            >
                              <MenuItem value="never">No end</MenuItem>
                              <MenuItem value="1day">+1 day</MenuItem>
                              <MenuItem value="7days">+7 days</MenuItem>
                              <MenuItem value="30days">+30 days</MenuItem>
                              <MenuItem value="90days">+90 days</MenuItem>
                              <MenuItem value="custom">Pick date...</MenuItem>
                            </Select>
                          </FormControl>
                          {endDateOption === 'custom' && (
                            <TextField
                              type="datetime-local"
                              size="small"
                              value={endDateCustom}
                              onChange={e => setEndDateCustom(e.target.value)}
                              sx={{ width: 200 }}
                            />
                          )}
                        </Box>

                        {/* Max executions */}
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                          <Typography variant="body2" sx={{ minWidth: 30 }}>Max</Typography>
                          <TextField
                            type="number"
                            size="small"
                            value={maxExecutions}
                            onChange={e => setMaxExecutions(e.target.value)}
                            placeholder="unlimited"
                            inputProps={{ min: 1 }}
                            sx={{ width: 100 }}
                          />
                          <Typography variant="body2" color="text.secondary">runs</Typography>
                        </Box>
                      </Box>
                    </Box>
                  </Box>

                  {/* Add Device button - only show if more devices are available */}
                  {hasMoreDevicesAvailable() && (
                    <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 1 }}>
                      {selectedHost && selectedDevice && selectedUserinterface && (
                        <Button
                          variant="outlined"
                          startIcon={<Add />}
                          onClick={() => {
                            const exists = additionalDevices.some(d => d.hostName === selectedHost && d.deviceId === selectedDevice);
                            if (!exists) {
                              setAdditionalDevices(prev => [...prev, { 
                                hostName: selectedHost, 
                                deviceId: selectedDevice,
                                deviceModel: deviceModel,
                                userinterface: selectedUserinterface
                              }]);
                              setSelectedHost('');
                              setSelectedDevice('');
                              setSelectedUserinterface('');
                            }
                          }}
                          disabled={!selectedHost || !selectedDevice || !selectedUserinterface}
                          size="small"
                        >
                          Add Device
                        </Button>
                      )}
                    </Box>
                  )}

                  {/* Show additional devices with remove option */}
                  {additionalDevices.length > 0 && (
                    <Box sx={{ mt: 2, mb: 1 }}>
                      <Typography variant="body2" sx={{ mb: 1, fontWeight: 'bold' }}>
                        Additional Devices ({additionalDevices.length}):
                      </Typography>
                      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                        {additionalDevices.map((device, index) => {
                          const hostDevices = getDevicesFromHost(device.hostName);
                          const deviceObject = hostDevices.find(d => d.device_id === device.deviceId);
                          const deviceDisplayName = deviceObject?.device_name || device.deviceId;
                          
                          return (
                            <Card 
                              key={`${device.hostName}:${device.deviceId}`}
                              variant="outlined"
                              sx={{ p: 1, backgroundColor: 'rgba(0, 0, 0, 0.02)' }}
                            >
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                <Box sx={{ flex: '0 0 200px' }}>
                                  <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                                    📱 {device.hostName}:{deviceDisplayName}
                                  </Typography>
                                  <Typography variant="caption" color="text.secondary">
                                    {device.deviceModel}
                                  </Typography>
                                </Box>
                                
                                <Box sx={{ flex: 1, minWidth: 200 }}>
                                  <UserinterfaceSelector
                                    deviceModel={device.deviceModel}
                                    value={device.userinterface}
                                    onChange={(newUserinterface) => {
                                      setAdditionalDevices(prev => prev.map((d, i) => 
                                        i === index ? { ...d, userinterface: newUserinterface } : d
                                      ));
                                    }}
                                    label="Userinterface"
                                    size="small"
                                    fullWidth
                                  />
                                </Box>
                                
                                <IconButton
                                  size="small"
                                  onClick={() => {
                                    setAdditionalDevices(prev => prev.filter((_, i) => i !== index));
                                  }}
                                  sx={{ ml: 'auto' }}
                                >
                                  <Close />
                                </IconButton>
                              </Box>
                            </Card>
                          );
                        })}
                      </Box>
                    </Box>
                  )}

                  <Box display="flex" gap={1}>
                    <Button 
                      variant="contained" 
                      onClick={handleCreate} 
                      disabled={(!selectedHost || !selectedDevice) && additionalDevices.length === 0 || !selectedScript}
                    >
                      Create{((selectedHost && selectedDevice) ? 1 : 0) + additionalDevices.length > 1 ? ` ${((selectedHost && selectedDevice) ? 1 : 0) + additionalDevices.length} Deployments` : ' Deployment'}
                    </Button>
                    <Button variant="outlined" onClick={() => {
                      setShowCreate(false);
                      setSelectedHost('');
                      setSelectedDevice('');
                      setSelectedUserinterface('');
                      setAdditionalDevices([]);
                      setCronExpression('*/10 * * * *');
                      setStartDateOption('now');
                      setStartDateCustom('');
                      setEndDateOption('never');
                      setEndDateCustom('');
                      setMaxExecutions('');
                    }}>Cancel</Button>
                  </Box>
                </>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Active Deployments */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 1 }}>Active Deployments</Typography>
              <TableContainer component={Paper} variant="outlined">
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Name</TableCell>
                        <TableCell>Script</TableCell>
                        <TableCell>Host:Device</TableCell>
                        <TableCell>Parameters</TableCell>
                        <TableCell>Schedule</TableCell>
                        <TableCell>Status</TableCell>
                        <TableCell>Actions</TableCell>
                      </TableRow>
                    </TableHead>
                  <TableBody>
                    {deployments.map(d => {
                      const hostDevices = getDevicesFromHost(d.host_name);
                      const deviceObject = hostDevices.find(device => device.device_id === d.device_id);
                      const deviceDisplayName = deviceObject?.device_name || d.device_id;
                      
                      return (
                        <TableRow 
                          key={d.id}
                          sx={{
                            '&:hover': {
                              backgroundColor: 'rgba(0, 0, 0, 0.04) !important',
                            },
                          }}
                        >
                          <TableCell>{d.name}</TableCell>
                          <TableCell>{d.script_name}</TableCell>
                          <TableCell>{d.host_name}:{deviceDisplayName}</TableCell>
                          <TableCell>
                            <Typography variant="caption" sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
                              {d.parameters && d.parameters.trim() ? d.parameters : '-'}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>
                              {d.cron_expression}
                            </Typography>
                            <Typography variant="caption" display="block" color="text.secondary">
                              {cronToHuman(d.cron_expression)}
                            </Typography>
                            {d.execution_count > 0 && (
                              <Typography variant="caption" display="block" color="primary">
                                Runs: {d.execution_count}{d.max_executions ? `/${d.max_executions}` : ''}
                              </Typography>
                            )}
                          </TableCell>
                          <TableCell><Chip label={d.status} color={d.status === 'active' ? 'success' : 'default'} size="small" /></TableCell>
                          <TableCell>
                            <IconButton size="small" onClick={() => handleEditOpen(d)} title="Edit"><Edit /></IconButton>
                            {d.status === 'active' ? (
                              <IconButton size="small" onClick={() => handlePause(d.id)} title="Pause"><Pause /></IconButton>
                            ) : (
                              <IconButton size="small" onClick={() => handleResume(d.id)} title="Resume"><PlayArrow /></IconButton>
                            )}
                            <IconButton size="small" onClick={() => handleDelete(d.id, d.name)} title="Delete"><Delete /></IconButton>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Grid>

        {/* Recent Executions */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 1 }}>Recent Executions</Typography>
              <TableContainer component={Paper} variant="outlined">
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Deployment</TableCell>
                      <TableCell>Script</TableCell>
                      <TableCell>Host:Device</TableCell>
                      <TableCell>Started</TableCell>
                      <TableCell>Duration</TableCell>
                      <TableCell>Status</TableCell>
                      <TableCell>Report</TableCell>
                      <TableCell>Logs</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {executions.map(e => {
                      const hostName = e.deployments?.host_name;
                      const deviceId = e.deployments?.device_id;
                      let deviceDisplayName = deviceId;
                      
                      if (hostName && deviceId) {
                        const hostDevices = getDevicesFromHost(hostName);
                        const deviceObject = hostDevices.find(device => device.device_id === deviceId);
                        deviceDisplayName = deviceObject?.device_name || deviceId;
                      }
                      
                      return (
                        <TableRow 
                          key={e.id}
                          sx={{
                            '&:hover': {
                              backgroundColor: 'rgba(0, 0, 0, 0.04) !important',
                            },
                          }}
                        >
                          <TableCell>{e.deployments?.name}</TableCell>
                          <TableCell>{e.deployments?.script_name}</TableCell>
                          <TableCell>{hostName && deviceId ? `${hostName}:${deviceDisplayName}` : '-'}</TableCell>
                          <TableCell>
                            {formatToLocalTime(e.started_at)}
                            <Typography variant="caption" display="block" color="text.secondary">
                              {userTimezone}
                            </Typography>
                          </TableCell>
                          <TableCell>{e.completed_at ? `${Math.round((new Date(e.completed_at).getTime() - new Date(e.started_at).getTime()) / 1000)}s` : '-'}</TableCell>
                          <TableCell><Chip label={e.success ? 'Success' : e.completed_at ? 'Failed' : 'Running'} color={e.success ? 'success' : e.completed_at ? 'error' : 'warning'} size="small" /></TableCell>
                          <TableCell>
                            {e.report_url ? (
                              <Chip
                                label="View Report"
                                component="a"
                                href={e.report_url}
                                target="_blank"
                                clickable
                                size="small"
                                sx={{ cursor: 'pointer' }}
                                icon={<LinkIcon />}
                                color="primary"
                                variant="outlined"
                              />
                            ) : (
                              <Chip label="No Report" size="small" variant="outlined" disabled />
                            )}
                          </TableCell>
                          <TableCell>
                            {e.report_url ? (
                              <Chip
                                icon={<LinkIcon />}
                                label="Logs"
                                size="small"
                                clickable
                                onClick={() => window.open(getLogsUrl(e.report_url), '_blank')}
                                color="secondary"
                                variant="outlined"
                              />
                            ) : (
                              <Chip label="No Logs" size="small" variant="outlined" disabled />
                            )}
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Edit Deployment Dialog */}
      <Dialog open={editDialogOpen} onClose={handleEditClose} maxWidth="md" fullWidth>
        <DialogTitle>Edit Deployment: {editingDeployment?.name}</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
            {/* Schedule */}
            <Box>
              <Typography variant="subtitle2" sx={{ mb: 1 }}>Schedule</Typography>
              <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                <TextField
                  label="Cron Expression"
                  value={editCron}
                  onChange={(e) => setEditCron(e.target.value)}
                  size="small"
                  fullWidth
                  helperText={cronToHuman(editCron)}
                />
              </Box>
            </Box>

            {/* Start Date */}
            <Box>
              <Typography variant="subtitle2" sx={{ mb: 1 }}>Start Date (Optional)</Typography>
              <TextField
                type="datetime-local"
                value={editStartDate ? new Date(editStartDate).toISOString().slice(0, 16) : ''}
                onChange={(e) => setEditStartDate(e.target.value ? new Date(e.target.value).toISOString() : '')}
                size="small"
                fullWidth
                helperText="Leave empty to start immediately"
              />
            </Box>

            {/* End Date */}
            <Box>
              <Typography variant="subtitle2" sx={{ mb: 1 }}>End Date (Optional)</Typography>
              <TextField
                type="datetime-local"
                value={editEndDate ? new Date(editEndDate).toISOString().slice(0, 16) : ''}
                onChange={(e) => setEditEndDate(e.target.value ? new Date(e.target.value).toISOString() : '')}
                size="small"
                fullWidth
                helperText="Leave empty for no end date"
              />
            </Box>

            {/* Max Executions */}
            <Box>
              <Typography variant="subtitle2" sx={{ mb: 1 }}>Max Executions (Optional)</Typography>
              <TextField
                type="number"
                value={editMaxExecutions}
                onChange={(e) => setEditMaxExecutions(e.target.value)}
                size="small"
                fullWidth
                placeholder="Unlimited"
                inputProps={{ min: 1 }}
                helperText="Leave empty for unlimited executions"
              />
            </Box>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleEditClose} startIcon={<Cancel />}>Cancel</Button>
          <Button onClick={handleEditSave} variant="contained" startIcon={<Save />}>Save Changes</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Deployments;

