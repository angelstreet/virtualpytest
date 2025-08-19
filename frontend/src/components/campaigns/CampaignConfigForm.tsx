/**
 * Campaign Configuration Form Component
 * 
 * Form for configuring campaign-level settings like name, description,
 * execution configuration, and device selection.
 */

import React from 'react';
import {
  Box,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  FormControlLabel,
  Switch,
  Typography,
  Slider,
  Card,
  CardContent,
} from '@mui/material';
import { CampaignConfig, CampaignExecutionConfig } from '../../types/pages/Campaign_Types';

interface CampaignConfigFormProps {
  config: Partial<CampaignConfig>;
  hosts: any[];
  getDevicesFromHost: (hostName: string) => any[];
  onConfigChange: (updates: Partial<CampaignConfig>) => void;
  errors: string[];
}

export const CampaignConfigForm: React.FC<CampaignConfigFormProps> = ({
  config,
  hosts,
  getDevicesFromHost,
  onConfigChange,
  errors,
}) => {
  const handleBasicInfoChange = (field: keyof CampaignConfig, value: string) => {
    onConfigChange({ [field]: value });
  };

  const handleExecutionConfigChange = (field: keyof CampaignExecutionConfig, value: any) => {
    onConfigChange({
      execution_config: {
        ...config.execution_config,
        [field]: value,
      } as CampaignExecutionConfig,
    });
  };

  const handleHostChange = (hostName: string) => {
    onConfigChange({
      host: hostName,
      device: '', // Reset device when host changes
    });
  };

  const selectedHostDevices = config.host ? getDevicesFromHost(config.host) : [];

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      {/* Basic Campaign Information */}
      <Card variant="outlined">
        <CardContent>
          <Typography variant="h6" sx={{ mb: 2 }}>
            Campaign Information
          </Typography>
          
          <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
            <TextField
              label="Campaign Name *"
              value={config.name || ''}
              onChange={(e) => handleBasicInfoChange('name', e.target.value)}
              size="small"
              fullWidth
              error={errors.some(e => e.includes('name'))}
            />
            
            <TextField
              label="Campaign ID *"
              value={config.campaign_id || ''}
              onChange={(e) => handleBasicInfoChange('campaign_id', e.target.value)}
              size="small"
              fullWidth
              error={errors.some(e => e.includes('Campaign ID'))}
              placeholder="e.g., fullzap-test-2024"
            />
          </Box>

          <TextField
            label="Description"
            value={config.description || ''}
            onChange={(e) => handleBasicInfoChange('description', e.target.value)}
            size="small"
            fullWidth
            multiline
            rows={2}
            placeholder="Brief description of what this campaign tests..."
          />
        </CardContent>
      </Card>

      {/* Device Selection */}
      <Card variant="outlined">
        <CardContent>
          <Typography variant="h6" sx={{ mb: 2 }}>
            Device Selection
          </Typography>
          
          <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
            <FormControl fullWidth size="small">
              <InputLabel>Host *</InputLabel>
              <Select
                value={config.host || ''}
                label="Host *"
                onChange={(e) => handleHostChange(e.target.value)}
                error={errors.some(e => e.includes('Host'))}
              >
                {hosts.map((host) => (
                  <MenuItem key={host.host_name} value={host.host_name}>
                    {host.host_name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <FormControl fullWidth size="small">
              <InputLabel>Device *</InputLabel>
              <Select
                value={config.device || ''}
                label="Device *"
                onChange={(e) => handleBasicInfoChange('device', e.target.value)}
                disabled={!config.host || selectedHostDevices.length === 0}
                error={errors.some(e => e.includes('Device'))}
              >
                {selectedHostDevices.map((device) => (
                  <MenuItem key={device.device_id} value={device.device_id}>
                    {device.device_id} ({device.device_model})
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <FormControl fullWidth size="small">
              <InputLabel>User Interface *</InputLabel>
              <Select
                value={config.userinterface_name || ''}
                label="User Interface *"
                onChange={(e) => handleBasicInfoChange('userinterface_name', e.target.value)}
                error={errors.some(e => e.includes('interface'))}
              >
                <MenuItem value="horizon_android_mobile">Horizon Android Mobile</MenuItem>
                <MenuItem value="horizon_android_tv">Horizon Android TV</MenuItem>
                <MenuItem value="perseus_360_web">Perseus 360 Web</MenuItem>
              </Select>
            </FormControl>
          </Box>
        </CardContent>
      </Card>

      {/* Execution Configuration */}
      <Card variant="outlined">
        <CardContent>
          <Typography variant="h6" sx={{ mb: 2 }}>
            Execution Settings
          </Typography>
          
          <Box sx={{ mb: 2 }}>
            <Typography variant="body2" gutterBottom>
              Timeout: {config.execution_config?.timeout_minutes || 60} minutes
            </Typography>
            <Slider
              value={config.execution_config?.timeout_minutes || 60}
              onChange={(_e, value) => handleExecutionConfigChange('timeout_minutes', value)}
              min={5}
              max={480}
              step={5}
              marks={[
                { value: 30, label: '30m' },
                { value: 60, label: '1h' },
                { value: 120, label: '2h' },
                { value: 240, label: '4h' },
              ]}
              valueLabelDisplay="auto"
            />
          </Box>

          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
            <FormControlLabel
              control={
                <Switch
                  checked={config.execution_config?.continue_on_failure ?? true}
                  onChange={(e) => handleExecutionConfigChange('continue_on_failure', e.target.checked)}
                />
              }
              label="Continue on Failure"
            />
            <Typography variant="caption" color="text.secondary">
              If enabled, campaign continues even if individual scripts fail
            </Typography>

            <FormControlLabel
              control={
                <Switch
                  checked={config.execution_config?.parallel ?? false}
                  onChange={(e) => handleExecutionConfigChange('parallel', e.target.checked)}
                  disabled // For now, only sequential execution is supported
                />
              }
              label="Parallel Execution (Coming Soon)"
            />
            <Typography variant="caption" color="text.secondary">
              Currently only sequential execution is supported
            </Typography>
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
};
