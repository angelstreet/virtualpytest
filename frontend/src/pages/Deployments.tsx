import { PlayArrow, Pause, Delete, Add } from '@mui/icons-material';
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

  const hosts = getAllHosts();
  const devices = selectedHost ? getDevicesFromHost(selectedHost) : [];
  const deviceModel = devices.find(d => d.device_id === selectedDevice)?.device_model || 'unknown';

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
    const params = displayParameters.map(p => `--${p.name} ${parameterValues[p.name] || ''}`).join(' ');
    
    // Auto-generate deployment name from script name and timestamp
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
    const deploymentName = `${selectedScript}_${timestamp}`;
    
    const res = await createDeployment({
      name: deploymentName,
      host_name: selectedHost,
      device_id: selectedDevice,
      script_name: selectedScript,
      userinterface_name: selectedUserinterface,
      parameters: params,
      schedule_type: scheduleType,
      schedule_config: { hour: scheduleHour, minute: scheduleMinute }
    });

    if (res.success) {
      showSuccess('Deployment created');
      setShowCreate(false);
      loadDeployments();
    } else {
      showError(res.error);
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
                  <Box display="flex" gap={1}>
                    <Button variant="contained" onClick={handleCreate} disabled={!selectedScript || !selectedHost || !selectedDevice}>Create</Button>
                    <Button variant="outlined" onClick={() => setShowCreate(false)}>Cancel</Button>
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
                      <TableCell>Schedule</TableCell>
                      <TableCell>Status</TableCell>
                      <TableCell>Actions</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {deployments.map(d => (
                      <TableRow key={d.id}>
                        <TableCell>{d.name}</TableCell>
                        <TableCell>{d.script_name}</TableCell>
                        <TableCell>{d.host_name}:{d.device_id}</TableCell>
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
                    ))}
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
                      <TableCell>Started</TableCell>
                      <TableCell>Duration</TableCell>
                      <TableCell>Status</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {executions.map(e => (
                      <TableRow key={e.id}>
                        <TableCell>{e.deployments?.name}</TableCell>
                        <TableCell>{e.deployments?.script_name}</TableCell>
                        <TableCell>{new Date(e.started_at).toLocaleString()}</TableCell>
                        <TableCell>{e.completed_at ? `${Math.round((new Date(e.completed_at).getTime() - new Date(e.started_at).getTime()) / 1000)}s` : '-'}</TableCell>
                        <TableCell><Chip label={e.success ? 'Success' : e.completed_at ? 'Failed' : 'Running'} color={e.success ? 'success' : e.completed_at ? 'error' : 'warning'} size="small" /></TableCell>
                      </TableRow>
                    ))}
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

