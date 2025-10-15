import { PlayArrow, Pause, Delete, Add, Close } from '@mui/icons-material';
import {
  Box, Typography, Card, CardContent, Button, Grid, TextField, Select, MenuItem,
  FormControl, InputLabel, Table, TableBody, TableCell, TableContainer, TableHead,
  TableRow, Paper, IconButton, Chip
} from '@mui/material';
import React, { useState, useEffect } from 'react';
import { UserinterfaceSelector } from '../components/common/UserinterfaceSelector';
import { useHostManager } from '../hooks/useHostManager';
import { useToast } from '../hooks/useToast';
import { useDeployment, Deployment } from '../hooks/useDeployment';
import { useRun } from '../hooks/useRun';
import { buildServerUrl } from '../utils/buildUrlUtils';

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
  const [scheduleType, setScheduleType] = useState<'hourly' | 'daily' | 'weekly'>('daily');
  const [scheduleHour, setScheduleHour] = useState(10);
  const [scheduleMinute, setScheduleMinute] = useState(0);
  const [deployments, setDeployments] = useState<Deployment[]>([]);
  const [executions, setExecutions] = useState<any[]>([]);
  const [scripts, setScripts] = useState<string[]>([]);
  const [additionalDevices, setAdditionalDevices] = useState<AdditionalDevice[]>([]);

  const hosts = getAllHosts();
  
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
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
    
    // Create deployments for all devices
    let successCount = 0;
    for (const device of allDevices) {
      const deploymentName = `${selectedScript}_${device.hostName}_${device.deviceId}_${timestamp}`;
      
      const res = await createDeployment({
        name: deploymentName,
        host_name: device.hostName,
        device_id: device.deviceId,
        script_name: selectedScript,
        userinterface_name: device.userinterface,
        parameters: params,
        schedule_type: scheduleType,
        schedule_config: { hour: scheduleHour, minute: scheduleMinute }
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

  const handleDelete = async (id: string) => {
    await deleteDeployment(id);
    loadDeployments();
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
                  <Box sx={{ display: 'flex', gap: 1, mb: 1, flexWrap: 'wrap' }}>
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
                    <FormControl size="small" sx={{ minWidth: 120 }}>
                      <InputLabel>Schedule</InputLabel>
                      <Select value={scheduleType} label="Schedule" onChange={e => setScheduleType(e.target.value as any)}>
                        <MenuItem value="hourly">Hourly</MenuItem>
                        <MenuItem value="daily">Daily</MenuItem>
                        <MenuItem value="weekly">Weekly</MenuItem>
                      </Select>
                    </FormControl>
                    {scheduleType !== 'hourly' && (
                      <TextField label="Hour" type="number" value={scheduleHour} onChange={e => setScheduleHour(+e.target.value)} size="small" sx={{ width: 80 }} />
                    )}
                    <TextField label="Min" type="number" value={scheduleMinute} onChange={e => setScheduleMinute(+e.target.value)} size="small" sx={{ width: 80 }} />
                    {displayParameters.map(p => (
                      <TextField key={p.name} label={p.name} value={parameterValues[p.name] || ''} onChange={e => handleParameterChange(p.name, e.target.value)} size="small" />
                    ))}
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
                          <TableCell>{d.schedule_type} {d.schedule_config?.hour}:{d.schedule_config?.minute}</TableCell>
                          <TableCell><Chip label={d.status} color={d.status === 'active' ? 'success' : 'default'} size="small" /></TableCell>
                          <TableCell>
                            {d.status === 'active' ? (
                              <IconButton size="small" onClick={() => handlePause(d.id)}><Pause /></IconButton>
                            ) : (
                              <IconButton size="small" onClick={() => handleResume(d.id)}><PlayArrow /></IconButton>
                            )}
                            <IconButton size="small" onClick={() => handleDelete(d.id)}><Delete /></IconButton>
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
                          <TableCell>{new Date(e.started_at).toLocaleString()}</TableCell>
                          <TableCell>{e.completed_at ? `${Math.round((new Date(e.completed_at).getTime() - new Date(e.started_at).getTime()) / 1000)}s` : '-'}</TableCell>
                          <TableCell><Chip label={e.success ? 'Success' : e.completed_at ? 'Failed' : 'Running'} color={e.success ? 'success' : e.completed_at ? 'error' : 'warning'} size="small" /></TableCell>
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
    </Box>
  );
};

export default Deployments;

