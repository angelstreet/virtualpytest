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
        timeout_minutes: 120, // Fixed to 2 hours
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
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
      {/* Compact form - all fields in minimal space */}
      <Box sx={{ display: 'flex', gap: 1, mb: 1 }}>
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

      <Box sx={{ display: 'flex', gap: 1, mb: 1 }}>
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

      {/* Simple execution settings */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
        <Typography variant="body2" color="text.secondary">
          Timeout: 2h
        </Typography>
        <FormControlLabel
          control={
            <Switch
              checked={config.execution_config?.continue_on_failure ?? true}
              onChange={(e) => handleExecutionConfigChange('continue_on_failure', e.target.checked)}
              size="small"
            />
          }
          label="Continue on Failure"
        />
      </Box>
    </Box>
  );
};
