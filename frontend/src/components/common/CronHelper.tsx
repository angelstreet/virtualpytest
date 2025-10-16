import React from 'react';
import { Box, Select, MenuItem, FormControl, InputLabel, TextField, Typography, Chip } from '@mui/material';
import { Info } from '@mui/icons-material';

interface CronPattern {
  label: string;
  value: string;
  description: string;
}

const CRON_PATTERNS: CronPattern[] = [
  { label: 'Every 5 minutes', value: '*/5 * * * *', description: 'Runs 12 times per hour' },
  { label: 'Every 10 minutes', value: '*/10 * * * *', description: 'Runs 6 times per hour' },
  { label: 'Every 15 minutes', value: '*/15 * * * *', description: 'Runs 4 times per hour' },
  { label: 'Every 30 minutes', value: '*/30 * * * *', description: 'Runs twice per hour' },
  { label: 'Every hour', value: '0 * * * *', description: 'Runs at :00 past every hour' },
  { label: 'Every 2 hours', value: '0 */2 * * *', description: 'Runs at :00 every 2 hours' },
  { label: 'Every 6 hours', value: '0 */6 * * *', description: 'Runs 4 times per day' },
  { label: 'Daily at midnight', value: '0 0 * * *', description: 'Runs once per day at 00:00' },
  { label: 'Daily at 2am', value: '0 2 * * *', description: 'Runs once per day at 02:00' },
  { label: 'Daily at 10am', value: '0 10 * * *', description: 'Runs once per day at 10:00' },
  { label: 'Weekdays at 9am', value: '0 9 * * 1-5', description: 'Mon-Fri at 09:00' },
  { label: 'Business hours (hourly)', value: '0 9-17 * * 1-5', description: 'Every hour 9am-5pm, Mon-Fri' },
  { label: 'Weekly on Monday', value: '0 0 * * 1', description: 'Every Monday at midnight' },
  { label: 'Weekly on Sunday', value: '0 0 * * 0', description: 'Every Sunday at midnight' },
  { label: 'Custom...', value: '', description: 'Enter your own cron expression' },
];

interface CronHelperProps {
  value: string;
  onChange: (value: string) => void;
  error?: string;
  size?: 'small' | 'medium';
}

export const CronHelper: React.FC<CronHelperProps> = ({ value, onChange, error, size = 'small' }) => {
  const [usePreset, setUsePreset] = React.useState(true);
  
  const matchedPattern = CRON_PATTERNS.find(p => p.value === value && p.value !== '');
  
  React.useEffect(() => {
    // If value doesn't match any preset, switch to custom
    if (value && !matchedPattern) {
      setUsePreset(false);
    }
  }, [value, matchedPattern]);
  
  const handlePresetChange = (newValue: string) => {
    if (newValue === '') {
      // Custom selected
      setUsePreset(false);
      onChange('');
    } else {
      onChange(newValue);
    }
  };
  
  return (
    <Box>
      {usePreset ? (
        <FormControl fullWidth size={size}>
          <InputLabel>Schedule Pattern</InputLabel>
          <Select
            value={matchedPattern?.value || ''}
            label="Schedule Pattern"
            onChange={(e) => handlePresetChange(e.target.value)}
          >
            {CRON_PATTERNS.map((pattern) => (
              <MenuItem key={pattern.label} value={pattern.value}>
                <Box>
                  <Typography variant="body2">{pattern.label}</Typography>
                  <Typography variant="caption" color="text.secondary">
                    {pattern.description}
                  </Typography>
                </Box>
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      ) : (
        <Box sx={{ display: 'flex', gap: 1, alignItems: 'flex-start' }}>
          <TextField
            fullWidth
            size={size}
            label="Cron Expression"
            value={value}
            onChange={(e) => onChange(e.target.value)}
            error={!!error}
            helperText={error || 'Format: minute hour day month day_of_week'}
            placeholder="*/10 * * * *"
          />
          <Chip
            label="Presets"
            onClick={() => {
              setUsePreset(true);
              onChange('*/10 * * * *'); // Default to every 10 minutes
            }}
            size="small"
            sx={{ mt: size === 'small' ? 1 : 1.5 }}
          />
        </Box>
      )}
      
      {/* Cron help link */}
      {!usePreset && (
        <Typography variant="caption" sx={{ mt: 0.5, display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <Info sx={{ fontSize: 12 }} />
          Need help? Visit{' '}
          <a href="https://crontab.guru" target="_blank" rel="noopener noreferrer" style={{ color: 'inherit' }}>
            crontab.guru
          </a>
        </Typography>
      )}
    </Box>
  );
};

