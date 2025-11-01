/**
 * StandardBlockConfigDialog
 * 
 * Universal configuration dialog for standard blocks (evaluate_condition, custom_code, etc.)
 * Supports dependent dropdowns where one field's choices depend on another field's value
 */

import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Box,
  Typography,
  Chip
} from '@mui/material';

interface ParamDef {
  type: string;
  required?: boolean;
  default?: any;
  description?: string;
  choices?: Array<{ label: string; value: string }>;
  depends_on?: string;  // Field that this field depends on
  choices_map?: Record<string, Array<{ label: string; value: string }>>;  // Choices grouped by parent value
  placeholder?: string;
  min?: number;
  max?: number;
}

interface StandardBlockConfigDialogProps {
  open: boolean;
  blockCommand: string;  // e.g., 'evaluate_condition'
  blockLabel: string;    // e.g., 'Evaluate Condition'
  params: Record<string, ParamDef>;  // Parameter definitions from get_block_info()
  initialData?: Record<string, any>;  // Initial values
  onSave: (data: Record<string, any>) => void;
  onCancel: () => void;
}

export const StandardBlockConfigDialog: React.FC<StandardBlockConfigDialogProps> = ({
  open,
  blockCommand,
  blockLabel,
  params,
  initialData = {},
  onSave,
  onCancel,
}) => {
  // Initialize form data from initial values or defaults
  const [formData, setFormData] = useState<Record<string, any>>(() => {
    const initial: Record<string, any> = {};
    Object.entries(params).forEach(([key, paramDef]) => {
      initial[key] = initialData[key] !== undefined 
        ? initialData[key] 
        : (paramDef.default !== undefined ? paramDef.default : '');
    });
    return initial;
  });

  // Reset form data when dialog opens with new initial data
  useEffect(() => {
    if (open) {
      const initial: Record<string, any> = {};
      Object.entries(params).forEach(([key, paramDef]) => {
        initial[key] = initialData[key] !== undefined 
          ? initialData[key] 
          : (paramDef.default !== undefined ? paramDef.default : '');
      });
      setFormData(initial);
    }
  }, [open, initialData, params]);

  const handleChange = (paramName: string, value: any) => {
    setFormData(prev => {
      const updated = { ...prev, [paramName]: value };
      
      // If this field has dependent fields, reset them to default
      Object.entries(params).forEach(([key, paramDef]) => {
        if (paramDef.depends_on === paramName) {
          // Reset dependent field to its default
          updated[key] = paramDef.default !== undefined ? paramDef.default : '';
        }
      });
      
      return updated;
    });
  };

  const handleSave = () => {
    onSave(formData);
  };

  const renderParam = (paramName: string, paramDef: ParamDef) => {
    const value = formData[paramName];
    
    // Handle dependent ENUM: get choices based on parent field value
    if (paramDef.type === 'enum' && paramDef.depends_on && paramDef.choices_map) {
      const parentValue = formData[paramDef.depends_on];
      const dependentChoices = paramDef.choices_map[parentValue] || [];
      
      return (
        <FormControl key={paramName} fullWidth sx={{ mb: 2 }}>
          <InputLabel>{paramDef.description || paramName}</InputLabel>
          <Select
            value={value}
            label={paramDef.description || paramName}
            onChange={(e) => handleChange(paramName, e.target.value)}
            disabled={!parentValue}  // Disable if parent not selected
          >
            {dependentChoices.map((choice) => (
              <MenuItem key={choice.value} value={choice.value}>
                {choice.label}
              </MenuItem>
            ))}
          </Select>
          {!parentValue && (
            <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5 }}>
              Select {paramDef.depends_on} first
            </Typography>
          )}
        </FormControl>
      );
    }
    
    // Handle regular ENUM
    if (paramDef.type === 'enum' && paramDef.choices) {
      return (
        <FormControl key={paramName} fullWidth sx={{ mb: 2 }}>
          <InputLabel>{paramDef.description || paramName}</InputLabel>
          <Select
            value={value}
            label={paramDef.description || paramName}
            onChange={(e) => handleChange(paramName, e.target.value)}
          >
            {paramDef.choices.map((choice) => (
              <MenuItem key={choice.value} value={choice.value}>
                {choice.label}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      );
    }
    
    // Handle NUMBER
    if (paramDef.type === 'number') {
      return (
        <TextField
          key={paramName}
          fullWidth
          type="number"
          label={paramDef.description || paramName}
          value={value}
          onChange={(e) => handleChange(paramName, parseFloat(e.target.value) || 0)}
          placeholder={paramDef.placeholder}
          inputProps={{
            min: paramDef.min,
            max: paramDef.max,
          }}
          sx={{ mb: 2 }}
        />
      );
    }
    
    // Handle BOOLEAN
    if (paramDef.type === 'boolean') {
      return (
        <FormControl key={paramName} fullWidth sx={{ mb: 2 }}>
          <InputLabel>{paramDef.description || paramName}</InputLabel>
          <Select
            value={value ? 'true' : 'false'}
            label={paramDef.description || paramName}
            onChange={(e) => handleChange(paramName, e.target.value === 'true')}
          >
            <MenuItem value="true">True</MenuItem>
            <MenuItem value="false">False</MenuItem>
          </Select>
        </FormControl>
      );
    }
    
    // Default to STRING
    return (
      <TextField
        key={paramName}
        fullWidth
        label={paramDef.description || paramName}
        value={value}
        onChange={(e) => handleChange(paramName, e.target.value)}
        placeholder={paramDef.placeholder}
        required={paramDef.required}
        sx={{ mb: 2 }}
      />
    );
  };

  return (
    <Dialog open={open} onClose={onCancel} maxWidth="sm" fullWidth>
      <DialogTitle>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Typography variant="h6">Configure {blockLabel}</Typography>
          <Chip label="Standard" size="small" sx={{ bgcolor: '#6b7280', color: 'white' }} />
        </Box>
      </DialogTitle>
      <DialogContent>
        <Box sx={{ display: 'flex', flexDirection: 'column', pt: 1 }}>
          {Object.entries(params).map(([paramName, paramDef]) => 
            renderParam(paramName, paramDef)
          )}
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onCancel}>Cancel</Button>
        <Button onClick={handleSave} variant="contained">
          Save
        </Button>
      </DialogActions>
    </Dialog>
  );
};

