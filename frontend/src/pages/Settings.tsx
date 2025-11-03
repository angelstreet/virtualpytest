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

import { buildServerUrl } from '../utils/buildUrlUtils';

interface ServerConfig {
  SERVER_NAME: string;
  SERVER_URL: string;
  SERVER_PORT: string;
  ENVIRONMENT: string;
  DEBUG: string;
  PYTHONUNBUFFERED: string;
}

interface FrontendConfig {
  VITE_SERVER_URL: string;
  VITE_SLAVE_SERVER_URL: string;
  VITE_GRAFANA_URL: string;
  VITE_CLOUDFLARE_R2_PUBLIC_URL: string;
  VITE_DEV_MODE: string;
}

interface HostConfig {
  HOST_NAME: string;
  HOST_PORT: string;
  HOST_URL: string;
  HOST_API_URL: string;
}

interface DeviceConfig {
  DEVICE_NAME: string;
  DEVICE_MODEL: string;
  DEVICE_VIDEO: string;
  DEVICE_VIDEO_STREAM_PATH: string;
  DEVICE_VIDEO_CAPTURE_PATH: string;
  DEVICE_VIDEO_FPS: string;
  DEVICE_VIDEO_AUDIO: string;
  DEVICE_IP: string;
  DEVICE_PORT: string;
  DEVICE_POWER_NAME: string;
  DEVICE_POWER_IP: string;
}

interface SettingsConfig {
  server: ServerConfig;
  frontend: FrontendConfig;
  host: HostConfig;
  devices: { [key: string]: DeviceConfig };
}

const Settings: React.FC = () => {
  const [activeTab, setActiveTab] = useState(0);
  const [config, setConfig] = useState<SettingsConfig>({
    server: {
      SERVER_NAME: '',
      SERVER_URL: '',
      SERVER_PORT: '5109',
      ENVIRONMENT: 'development',
      DEBUG: '1',
      PYTHONUNBUFFERED: '1',
    },
    frontend: {
      VITE_SERVER_URL: '',
      VITE_SLAVE_SERVER_URL: '[]',
      VITE_GRAFANA_URL: '',
      VITE_CLOUDFLARE_R2_PUBLIC_URL: '',
      VITE_DEV_MODE: 'true',
    },
    host: {
      HOST_NAME: '',
      HOST_PORT: '6109',
      HOST_URL: '',
      HOST_API_URL: '',
    },
    devices: {},
  });

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // Load current configuration from backend
  const loadConfig = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(buildServerUrl('/server/settings/config'));

      if (!response.ok) {
        throw new Error(`Failed to load configuration: ${response.status}`);
      }

      const data = await response.json();
      setConfig(data);
    } catch (err) {
      console.error('[@page:Settings] Error loading configuration:', err);
      setError(err instanceof Error ? err.message : 'Failed to load configuration');
    } finally {
      setLoading(false);
    }
  };

  // Save configuration to backend
  const saveConfig = async () => {
    try {
      setSaving(true);
      setError(null);
      setSuccess(false);

      const response = await fetch(buildServerUrl('/server/settings/config'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(config),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `Failed to save configuration: ${response.status}`);
      }

      setSuccess(true);
      setTimeout(() => setSuccess(false), 5000);
    } catch (err) {
      console.error('[@page:Settings] Error saving configuration:', err);
      setError(err instanceof Error ? err.message : 'Failed to save configuration');
    } finally {
      setSaving(false);
    }
  };

  useEffect(() => {
    loadConfig();
  }, []);

  const handleServerChange = (field: keyof ServerConfig, value: string) => {
    setConfig((prev) => ({
      ...prev,
      server: { ...prev.server, [field]: value },
    }));
  };

  const handleFrontendChange = (field: keyof FrontendConfig, value: string) => {
    setConfig((prev) => ({
      ...prev,
      frontend: { ...prev.frontend, [field]: value },
    }));
  };

  const handleHostChange = (field: keyof HostConfig, value: string) => {
    setConfig((prev) => ({
      ...prev,
      host: { ...prev.host, [field]: value },
    }));
  };

  const handleDeviceChange = (deviceKey: string, field: keyof DeviceConfig, value: string) => {
    setConfig((prev) => ({
      ...prev,
      devices: {
        ...prev.devices,
        [deviceKey]: {
          ...prev.devices[deviceKey],
          [field]: value,
        },
      },
    }));
  };

  const addDevice = () => {
    const deviceNumbers = Object.keys(config.devices)
      .map((key) => parseInt(key.replace('DEVICE', '')))
      .filter((n) => !isNaN(n));
    const nextNumber = deviceNumbers.length > 0 ? Math.max(...deviceNumbers) + 1 : 1;
    const newDeviceKey = `DEVICE${nextNumber}`;

    setConfig((prev) => ({
      ...prev,
      devices: {
        ...prev.devices,
        [newDeviceKey]: {
          DEVICE_NAME: '',
          DEVICE_MODEL: '',
          DEVICE_VIDEO: '',
          DEVICE_VIDEO_STREAM_PATH: '',
          DEVICE_VIDEO_CAPTURE_PATH: '',
          DEVICE_VIDEO_FPS: '10',
          DEVICE_VIDEO_AUDIO: '',
          DEVICE_IP: '',
          DEVICE_PORT: '',
          DEVICE_POWER_NAME: '',
          DEVICE_POWER_IP: '',
        },
      },
    }));
  };

  const deleteDevice = (deviceKey: string) => {
    setConfig((prev) => {
      const newDevices = { ...prev.devices };
      delete newDevices[deviceKey];
      return { ...prev, devices: newDevices };
    });
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Box>
          <Typography variant="h4" gutterBottom>
            <SettingsIcon sx={{ mr: 1, verticalAlign: 'bottom' }} />
            System Settings
          </Typography>
          <Typography variant="body1" color="textSecondary">
            Configure non-sensitive system settings. Sensitive data (secrets, passwords, API keys)
            must be configured in .env files.
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
            Save All Changes
          </Button>
        </Box>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {success && (
        <Alert severity="success" sx={{ mb: 2 }}>
          Configuration saved successfully! Some changes may require service restart to take effect.
        </Alert>
      )}

      <Tabs value={activeTab} onChange={(_, newValue) => setActiveTab(newValue)} sx={{ mb: 2 }}>
        <Tab icon={<ServerIcon />} label="Backend Server" iconPosition="start" />
        <Tab icon={<FrontendIcon />} label="Frontend" iconPosition="start" />
        <Tab icon={<HostIcon />} label="Host & Devices" iconPosition="start" />
      </Tabs>

      {/* Tab 1: Backend Server */}
      {activeTab === 0 && (
        <Card>
          <CardContent>
            <Box display="flex" alignItems="center" mb={2}>
              <ServerIcon sx={{ mr: 1 }} color="primary" />
              <Typography variant="h6">Backend Server Configuration</Typography>
            </Box>
            <Divider sx={{ mb: 3 }} />

            <Grid container spacing={2}>
              <Grid item xs={12} md={6}>
                <TextField
                  label="Server Name"
                  value={config.server.SERVER_NAME}
                  onChange={(e) => handleServerChange('SERVER_NAME', e.target.value)}
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
                  onChange={(e) => handleServerChange('SERVER_URL', e.target.value)}
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
                  onChange={(e) => handleServerChange('SERVER_PORT', e.target.value)}
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
                  onChange={(e) => handleServerChange('ENVIRONMENT', e.target.value)}
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
                  onChange={(e) => handleServerChange('DEBUG', e.target.value)}
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
                  onChange={(e) => handleServerChange('PYTHONUNBUFFERED', e.target.value)}
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

            <Alert severity="info" sx={{ mt: 3 }}>
              <Typography variant="body2">
                <strong>Note:</strong> Sensitive data (Flask secret key, database credentials, API
                keys) must be configured directly in the root .env file.
              </Typography>
            </Alert>
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
                  onChange={(e) => handleFrontendChange('VITE_SERVER_URL', e.target.value)}
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
                  onChange={(e) => handleFrontendChange('VITE_SLAVE_SERVER_URL', e.target.value)}
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
                  onChange={(e) => handleFrontendChange('VITE_GRAFANA_URL', e.target.value)}
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
                    handleFrontendChange('VITE_CLOUDFLARE_R2_PUBLIC_URL', e.target.value)
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
                  onChange={(e) => handleFrontendChange('VITE_DEV_MODE', e.target.value)}
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

            <Alert severity="info" sx={{ mt: 3 }}>
              <Typography variant="body2">
                <strong>Note:</strong> Frontend configuration changes take effect after reloading
                the page.
              </Typography>
            </Alert>
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
                    onChange={(e) => handleHostChange('HOST_NAME', e.target.value)}
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
                    onChange={(e) => handleHostChange('HOST_PORT', e.target.value)}
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
                    onChange={(e) => handleHostChange('HOST_URL', e.target.value)}
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
                    onChange={(e) => handleHostChange('HOST_API_URL', e.target.value)}
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
                    <Box display="flex" alignItems="center" justifyContent="space-between" width="100%">
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
                          onChange={(e) => handleDeviceChange(deviceKey, 'DEVICE_NAME', e.target.value)}
                          placeholder="S21x"
                          fullWidth
                          size="small"
                        />
                      </Grid>
                      <Grid item xs={12} md={6}>
                        <TextField
                          label="Device Model"
                          value={device.DEVICE_MODEL}
                          onChange={(e) => handleDeviceChange(deviceKey, 'DEVICE_MODEL', e.target.value)}
                          placeholder="android_mobile"
                          fullWidth
                          size="small"
                        />
                      </Grid>
                      <Grid item xs={12} md={6}>
                        <TextField
                          label="IP Address"
                          value={device.DEVICE_IP}
                          onChange={(e) => handleDeviceChange(deviceKey, 'DEVICE_IP', e.target.value)}
                          placeholder="192.168.1.124"
                          fullWidth
                          size="small"
                        />
                      </Grid>
                      <Grid item xs={12} md={6}>
                        <TextField
                          label="Port"
                          value={device.DEVICE_PORT}
                          onChange={(e) => handleDeviceChange(deviceKey, 'DEVICE_PORT', e.target.value)}
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
                          onChange={(e) => handleDeviceChange(deviceKey, 'DEVICE_VIDEO', e.target.value)}
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
                            handleDeviceChange(deviceKey, 'DEVICE_VIDEO_AUDIO', e.target.value)
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
                          onChange={(e) => handleDeviceChange(deviceKey, 'DEVICE_VIDEO_FPS', e.target.value)}
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
                            handleDeviceChange(deviceKey, 'DEVICE_VIDEO_STREAM_PATH', e.target.value)
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
                            handleDeviceChange(deviceKey, 'DEVICE_VIDEO_CAPTURE_PATH', e.target.value)
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
                            handleDeviceChange(deviceKey, 'DEVICE_POWER_NAME', e.target.value)
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
                            handleDeviceChange(deviceKey, 'DEVICE_POWER_IP', e.target.value)
                          }
                          placeholder="192.168.1.220"
                          fullWidth
                          size="small"
                        />
                      </Grid>
                      <Grid item xs={12}>
                        <Alert severity="info" sx={{ mt: 1 }}>
                          <Typography variant="body2">
                            Power control credentials (email/password) must be configured in the
                            backend_host/src/.env file.
                          </Typography>
                        </Alert>
                      </Grid>
                    </Grid>
                  </AccordionDetails>
                </Accordion>
              ))}
            </CardContent>
          </Card>

          <Alert severity="info" sx={{ mt: 2 }}>
            <Typography variant="body2">
              <strong>Note:</strong> Host and device changes may require service restart to take
              effect. Sensitive device credentials must be configured in backend_host/src/.env file.
            </Typography>
          </Alert>
        </Box>
      )}
    </Box>
  );
};

export default Settings;
