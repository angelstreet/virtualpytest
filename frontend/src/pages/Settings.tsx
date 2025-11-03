import {
  Save as SaveIcon,
  Refresh as RefreshIcon,
  Settings as SettingsIcon,
  Storage as ServerIcon,
  Computer as HostIcon,
  Language as FrontendIcon,
  Add as AddIcon,
  Delete as DeleteIcon,
  ExpandMore as ExpandIcon,
} from '@mui/icons-material';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Button,
  TextField,
  Alert,
  Grid,
  Divider,
  CircularProgress,
  Tabs,
  Tab,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  IconButton,
  MenuItem,
} from '@mui/material';
import React, { useState, useEffect } from 'react';

import { useSettings } from '../hooks/pages';

const Settings: React.FC = () => {
  const [activeTab, setActiveTab] = useState(0);

  const {
    config,
    loading,
    saving,
    error,
    success,
    loadConfig,
    saveConfig,
    updateServerConfig,
    updateFrontendConfig,
    updateHostConfig,
    updateDeviceConfig,
    addDevice,
    deleteDevice,
    setError,
  } = useSettings();

  useEffect(() => {
    loadConfig();
  }, [loadConfig]);

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Box sx={{ mb: 0, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Box>
          <Typography variant="h4" gutterBottom>
            <SettingsIcon sx={{ mr: 1, verticalAlign: 'bottom' }} />
            System Settings
          </Typography>
        </Box>
        <Box display="flex" gap={1}>
          <Button variant="outlined" startIcon={<RefreshIcon />} onClick={loadConfig}>
            Refresh
          </Button>
          <Button
            variant="contained"
            startIcon={saving ? <CircularProgress size={20} /> : <SaveIcon />}
            onClick={saveConfig}
            disabled={saving}
          >
            Save
          </Button>
        </Box>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 1 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {success && (
        <Alert severity="success" sx={{ mb: 1 }}>
          Configuration saved successfully! Some changes may require service restart to take effect.
        </Alert>
      )}

      <Tabs value={activeTab} onChange={(_, newValue) => setActiveTab(newValue)} sx={{ mb: 1 }}>
        <Tab icon={<ServerIcon />} label="Backend Server" iconPosition="start" />
        <Tab icon={<FrontendIcon />} label="Frontend" iconPosition="start" />
        <Tab icon={<HostIcon />} label="Host & Devices" iconPosition="start" />
      </Tabs>

      {/* Tab 1: Backend Server */}
      {activeTab === 0 && (
        <Card>
          <CardContent>
            <Box display="flex" alignItems="center" mb={1}>
              <ServerIcon sx={{ mr: 1 }} color="primary" />
              <Typography variant="h6">Backend Server Configuration</Typography>
            </Box>
            <Divider sx={{ mb: 2 }} />

            <Grid container spacing={2}>
              <Grid item xs={12} md={6}>
                <TextField
                  label="Server Name"
                  value={config.server.SERVER_NAME}
                  onChange={(e) => updateServerConfig('SERVER_NAME', e.target.value)}
                  placeholder="Awesomation"
                  fullWidth
                  size="small"
                  helperText="Display name for this server"
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  label="Server URL"
                  value={config.server.SERVER_URL}
                  onChange={(e) => updateServerConfig('SERVER_URL', e.target.value)}
                  placeholder="http://localhost:5109"
                  fullWidth
                  size="small"
                  helperText="Base URL for the backend server"
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  label="Server Port"
                  value={config.server.SERVER_PORT}
                  onChange={(e) => updateServerConfig('SERVER_PORT', e.target.value)}
                  placeholder="5109"
                  fullWidth
                  size="small"
                  type="number"
                  helperText="Port for the backend server API"
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  label="Environment"
                  value={config.server.ENVIRONMENT}
                  onChange={(e) => updateServerConfig('ENVIRONMENT', e.target.value)}
                  fullWidth
                  size="small"
                  select
                  helperText="Current environment mode"
                >
                  <MenuItem value="development">Development</MenuItem>
                  <MenuItem value="staging">Staging</MenuItem>
                  <MenuItem value="production">Production</MenuItem>
                </TextField>
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  label="Debug Mode"
                  value={config.server.DEBUG}
                  onChange={(e) => updateServerConfig('DEBUG', e.target.value)}
                  fullWidth
                  size="small"
                  select
                  helperText="Enable debug logging"
                >
                  <MenuItem value="1">Enabled</MenuItem>
                  <MenuItem value="0">Disabled</MenuItem>
                </TextField>
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  label="Python Unbuffered"
                  value={config.server.PYTHONUNBUFFERED}
                  onChange={(e) => updateServerConfig('PYTHONUNBUFFERED', e.target.value)}
                  fullWidth
                  size="small"
                  select
                  helperText="Python stdout/stderr buffering"
                >
                  <MenuItem value="1">Unbuffered</MenuItem>
                  <MenuItem value="0">Buffered</MenuItem>
                </TextField>
              </Grid>
            </Grid>
          </CardContent>
        </Card>
      )}

      {/* Tab 2: Frontend */}
      {activeTab === 1 && (
        <Card>
          <CardContent>
            <Box display="flex" alignItems="center" mb={2}>
              <FrontendIcon sx={{ mr: 1 }} color="primary" />
              <Typography variant="h6">Frontend Configuration</Typography>
            </Box>
            <Divider sx={{ mb: 3 }} />

            <Grid container spacing={2}>
              <Grid item xs={12} md={6}>
                <TextField
                  label="Server URL"
                  value={config.frontend.VITE_SERVER_URL}
                  onChange={(e) => updateFrontendConfig('VITE_SERVER_URL', e.target.value)}
                  placeholder="http://localhost:5109"
                  fullWidth
                  size="small"
                  helperText="Backend server URL for API calls"
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  label="Slave Server URLs"
                  value={config.frontend.VITE_SLAVE_SERVER_URL}
                  onChange={(e) => updateFrontendConfig('VITE_SLAVE_SERVER_URL', e.target.value)}
                  placeholder="[]"
                  fullWidth
                  size="small"
                  helperText="JSON array of additional server URLs"
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  label="Grafana URL"
                  value={config.frontend.VITE_GRAFANA_URL}
                  onChange={(e) => updateFrontendConfig('VITE_GRAFANA_URL', e.target.value)}
                  placeholder="http://localhost:3000"
                  fullWidth
                  size="small"
                  helperText="Grafana dashboard URL"
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  label="R2 Public URL"
                  value={config.frontend.VITE_CLOUDFLARE_R2_PUBLIC_URL}
                  onChange={(e) =>
                    updateFrontendConfig('VITE_CLOUDFLARE_R2_PUBLIC_URL', e.target.value)
                  }
                  placeholder="https://pub-..."
                  fullWidth
                  size="small"
                  helperText="Cloudflare R2 public URL for assets"
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  label="Dev Mode"
                  value={config.frontend.VITE_DEV_MODE}
                  onChange={(e) => updateFrontendConfig('VITE_DEV_MODE', e.target.value)}
                  fullWidth
                  size="small"
                  select
                  helperText="Enable development mode features"
                >
                  <MenuItem value="true">Enabled</MenuItem>
                  <MenuItem value="false">Disabled</MenuItem>
                </TextField>
              </Grid>
            </Grid>

          </CardContent>
        </Card>
      )}

      {/* Tab 3: Host & Devices */}
      {activeTab === 2 && (
        <Box>
          <Card sx={{ mb: 2 }}>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <HostIcon sx={{ mr: 1 }} color="primary" />
                <Typography variant="h6">Host Configuration</Typography>
              </Box>
              <Divider sx={{ mb: 3 }} />

              <Grid container spacing={2}>
                <Grid item xs={12} md={6}>
                  <TextField
                    label="Host Name"
                    value={config.host.HOST_NAME}
                    onChange={(e) => updateHostConfig('HOST_NAME', e.target.value)}
                    placeholder="sunri-pi1"
                    fullWidth
                    size="small"
                    helperText="Unique identifier for this host"
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <TextField
                    label="Host Port"
                    value={config.host.HOST_PORT}
                    onChange={(e) => updateHostConfig('HOST_PORT', e.target.value)}
                    placeholder="6109"
                    fullWidth
                    size="small"
                    type="number"
                    helperText="Port for the host service"
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <TextField
                    label="Host URL"
                    value={config.host.HOST_URL}
                    onChange={(e) => updateHostConfig('HOST_URL', e.target.value)}
                    placeholder="http://localhost:6109"
                    fullWidth
                    size="small"
                    helperText="Base URL for the host service"
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <TextField
                    label="Host API URL"
                    value={config.host.HOST_API_URL}
                    onChange={(e) => updateHostConfig('HOST_API_URL', e.target.value)}
                    placeholder="http://localhost:6109"
                    fullWidth
                    size="small"
                    helperText="API endpoint URL for the host"
                  />
                </Grid>
              </Grid>
            </CardContent>
          </Card>

          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
                <Typography variant="h6">Device Configuration</Typography>
                <Button variant="contained" size="small" startIcon={<AddIcon />} onClick={addDevice}>
                  Add Device
                </Button>
              </Box>
              <Divider sx={{ mb: 2 }} />

              {Object.keys(config.devices).length === 0 && (
                <Alert severity="info">
                  No devices configured. Click "Add Device" to add a new device configuration.
                </Alert>
              )}

              {Object.entries(config.devices).map(([deviceKey, device]) => (
                <Accordion key={deviceKey} defaultExpanded={Object.keys(config.devices).length === 1}>
                  <AccordionSummary expandIcon={<ExpandIcon />}>
                    <Box display="flex" alignItems="center" justifyContent="space-between" width="100%" mr={2}>
                      <Typography>
                        {deviceKey}: {device.DEVICE_NAME || 'Unnamed Device'}
                      </Typography>
                      <IconButton
                        size="small"
                        onClick={(e) => {
                          e.stopPropagation();
                          deleteDevice(deviceKey);
                        }}
                        color="error"
                      >
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </Box>
                  </AccordionSummary>
                  <AccordionDetails>
                    <Grid container spacing={2}>
                      <Grid item xs={12}>
                        <Typography variant="subtitle2" color="primary" gutterBottom>
                          Basic Information
                        </Typography>
                      </Grid>
                      <Grid item xs={12} md={6}>
                        <TextField
                          label="Device Name"
                          value={device.DEVICE_NAME}
                          onChange={(e) => updateDeviceConfig(deviceKey, 'DEVICE_NAME', e.target.value)}
                          placeholder="S21x"
                          fullWidth
                          size="small"
                        />
                      </Grid>
                      <Grid item xs={12} md={6}>
                        <TextField
                          label="Device Model"
                          value={device.DEVICE_MODEL}
                          onChange={(e) => updateDeviceConfig(deviceKey, 'DEVICE_MODEL', e.target.value)}
                          placeholder="android_mobile"
                          fullWidth
                          size="small"
                        />
                      </Grid>
                      <Grid item xs={12} md={6}>
                        <TextField
                          label="IP Address"
                          value={device.DEVICE_IP}
                          onChange={(e) => updateDeviceConfig(deviceKey, 'DEVICE_IP', e.target.value)}
                          placeholder="192.168.1.124"
                          fullWidth
                          size="small"
                        />
                      </Grid>
                      <Grid item xs={12} md={6}>
                        <TextField
                          label="Port"
                          value={device.DEVICE_PORT}
                          onChange={(e) => updateDeviceConfig(deviceKey, 'DEVICE_PORT', e.target.value)}
                          placeholder="5555"
                          fullWidth
                          size="small"
                        />
                      </Grid>

                      <Grid item xs={12}>
                        <Typography variant="subtitle2" color="primary" gutterBottom sx={{ mt: 2 }}>
                          Video Configuration
                        </Typography>
                      </Grid>
                      <Grid item xs={12} md={6}>
                        <TextField
                          label="Video Device"
                          value={device.DEVICE_VIDEO}
                          onChange={(e) => updateDeviceConfig(deviceKey, 'DEVICE_VIDEO', e.target.value)}
                          placeholder="/dev/video0"
                          fullWidth
                          size="small"
                        />
                      </Grid>
                      <Grid item xs={12} md={6}>
                        <TextField
                          label="Audio Device"
                          value={device.DEVICE_VIDEO_AUDIO}
                          onChange={(e) =>
                            updateDeviceConfig(deviceKey, 'DEVICE_VIDEO_AUDIO', e.target.value)
                          }
                          placeholder="plughw:2,0"
                          fullWidth
                          size="small"
                        />
                      </Grid>
                      <Grid item xs={12} md={6}>
                        <TextField
                          label="FPS"
                          value={device.DEVICE_VIDEO_FPS}
                          onChange={(e) => updateDeviceConfig(deviceKey, 'DEVICE_VIDEO_FPS', e.target.value)}
                          placeholder="10"
                          fullWidth
                          size="small"
                          type="number"
                        />
                      </Grid>
                      <Grid item xs={12} md={6}>
                        <TextField
                          label="Stream Path"
                          value={device.DEVICE_VIDEO_STREAM_PATH}
                          onChange={(e) =>
                            updateDeviceConfig(deviceKey, 'DEVICE_VIDEO_STREAM_PATH', e.target.value)
                          }
                          placeholder="/host/stream/capture1"
                          fullWidth
                          size="small"
                        />
                      </Grid>
                      <Grid item xs={12}>
                        <TextField
                          label="Capture Path"
                          value={device.DEVICE_VIDEO_CAPTURE_PATH}
                          onChange={(e) =>
                            updateDeviceConfig(deviceKey, 'DEVICE_VIDEO_CAPTURE_PATH', e.target.value)
                          }
                          placeholder="/var/www/html/stream/capture1"
                          fullWidth
                          size="small"
                        />
                      </Grid>

                      <Grid item xs={12}>
                        <Typography variant="subtitle2" color="primary" gutterBottom sx={{ mt: 2 }}>
                          Power Control
                        </Typography>
                      </Grid>
                      <Grid item xs={12} md={6}>
                        <TextField
                          label="Power Device Name"
                          value={device.DEVICE_POWER_NAME}
                          onChange={(e) =>
                            updateDeviceConfig(deviceKey, 'DEVICE_POWER_NAME', e.target.value)
                          }
                          placeholder="TAPO_P100_EOS"
                          fullWidth
                          size="small"
                        />
                      </Grid>
                      <Grid item xs={12} md={6}>
                        <TextField
                          label="Power Device IP"
                          value={device.DEVICE_POWER_IP}
                          onChange={(e) =>
                            updateDeviceConfig(deviceKey, 'DEVICE_POWER_IP', e.target.value)
                          }
                          placeholder="192.168.1.220"
                          fullWidth
                          size="small"
                        />
                      </Grid>
                     
                    </Grid>
                  </AccordionDetails>
                </Accordion>
              ))}
            </CardContent>
          </Card>
        </Box>
      )}
    </Box>
  );
};

export default Settings;
