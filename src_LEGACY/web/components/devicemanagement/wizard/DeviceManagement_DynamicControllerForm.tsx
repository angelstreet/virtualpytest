import {
  Box,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Typography,
  Grid,
} from '@mui/material';
import React from 'react';

import {
  ControllerConfiguration,
  ControllerInputField,
} from '../../../types/controller/Controller_Types';

interface DynamicControllerFormProps {
  configuration: ControllerConfiguration;
  parameters: { [key: string]: any };
  onParametersChange: (parameters: { [key: string]: any }) => void;
  errors?: { [key: string]: string };
  fieldPrefix?: string;
}

export const DynamicControllerForm: React.FC<DynamicControllerFormProps> = ({
  configuration,
  parameters,
  onParametersChange,
  errors = {},
  fieldPrefix = '',
}) => {
  const handleFieldChange = (fieldName: string, value: any) => {
    const updatedParameters = {
      ...parameters,
      [fieldName]: value,
    };
    onParametersChange(updatedParameters);
  };

  const renderField = (field: ControllerInputField) => {
    const fieldKey = `${fieldPrefix}${field.name}`;
    const fieldValue = parameters[field.name] ?? field.defaultValue ?? '';
    const fieldError = errors[fieldKey];

    switch (field.type) {
      case 'select':
        return (
          <FormControl fullWidth size="small" error={!!fieldError}>
            <InputLabel>{field.label}</InputLabel>
            <Select
              value={fieldValue}
              onChange={(e) => handleFieldChange(field.name, e.target.value)}
              label={field.label}
            >
              {field.options?.map((option) => (
                <MenuItem key={option.value} value={option.value}>
                  {option.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        );

      case 'textarea':
        return (
          <TextField
            fullWidth
            size="small"
            label={field.label}
            multiline
            rows={3}
            value={fieldValue}
            onChange={(e) => handleFieldChange(field.name, e.target.value)}
            placeholder={field.placeholder}
            required={field.required}
            error={!!fieldError}
          />
        );

      case 'number':
        return (
          <TextField
            fullWidth
            size="small"
            label={field.label}
            type="number"
            value={fieldValue}
            onChange={(e) => handleFieldChange(field.name, e.target.value)}
            placeholder={field.placeholder}
            required={field.required}
            error={!!fieldError}
            inputProps={{
              min: field.validation?.min,
              max: field.validation?.max,
            }}
          />
        );

      case 'password':
        return (
          <TextField
            fullWidth
            size="small"
            label={field.label}
            type="password"
            value={fieldValue}
            onChange={(e) => handleFieldChange(field.name, e.target.value)}
            placeholder={field.placeholder}
            required={field.required}
            error={!!fieldError}
          />
        );

      case 'text':
      default:
        return (
          <TextField
            fullWidth
            size="small"
            label={field.label}
            type="text"
            value={fieldValue}
            onChange={(e) => handleFieldChange(field.name, e.target.value)}
            placeholder={field.placeholder}
            required={field.required}
            error={!!fieldError}
          />
        );
    }
  };

  // Group fields logically for better UI
  const groupFields = (fields: ControllerInputField[]) => {
    const groups: { [key: string]: ControllerInputField[] } = {
      connection: [],
      device: [],
      configuration: [],
      other: [],
    };

    fields.forEach((field) => {
      if (field.name.includes('host_') || field.name.includes('ssh_')) {
        groups.connection.push(field);
      } else if (
        field.name.includes('device_') ||
        field.name.includes('target_') ||
        field.name === 'video_device'
      ) {
        groups.device.push(field);
      } else if (
        field.name.includes('config') ||
        field.name.includes('setting') ||
        field.name === 'stream_path' ||
        field.name === 'resolution' ||
        field.name === 'fps' ||
        field.name === 'connection_timeout'
      ) {
        groups.configuration.push(field);
      } else {
        groups.other.push(field);
      }
    });

    return groups;
  };

  const fieldGroups = groupFields(configuration.inputFields);

  const renderFieldGroup = (title: string, fields: ControllerInputField[]) => {
    if (fields.length === 0) return null;

    return (
      <Box sx={{ mb: 1.5 }}>
        <Typography variant="subtitle2" sx={{ mb: 1, color: 'text.secondary' }}>
          {title}
        </Typography>
        <Grid container spacing={1}>
          {fields.map((field) => (
            <Grid item xs={12} sm={6} key={field.name}>
              {renderField(field)}
            </Grid>
          ))}
        </Grid>
      </Box>
    );
  };

  return (
    <Box>
      {/* SSH/Host Connection Fields */}
      {renderFieldGroup('Connection Settings', fieldGroups.connection)}

      {/* Device Target Fields */}
      {renderFieldGroup('Device Settings', fieldGroups.device)}

      {/* Configuration Fields */}
      {renderFieldGroup('Configuration', fieldGroups.configuration)}

      {/* Other Fields */}
      {fieldGroups.other.length > 0 && (
        <Grid container spacing={1}>
          {fieldGroups.other.map((field) => (
            <Grid item xs={12} sm={6} key={field.name}>
              {renderField(field)}
            </Grid>
          ))}
        </Grid>
      )}
    </Box>
  );
};
