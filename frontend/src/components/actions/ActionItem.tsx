import {
  Close as CloseIcon,
  KeyboardArrowUp as KeyboardArrowUpIcon,
  KeyboardArrowDown as KeyboardArrowDownIcon,
} from '@mui/icons-material';
import {
  Box,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  IconButton,
  TextField,
} from '@mui/material';
import React from 'react';

import type { Actions, Action } from '../../types/controller/Action_Types';

interface ActionItemProps {
  action: Action;
  index: number;
  availableActions: Actions;
  onActionSelect: (index: number, actionId: string) => void;
  onUpdateAction: (index: number, updates: Partial<Action>) => void;
  onRemoveAction: (index: number) => void;
  onMoveUp: (index: number) => void;
  onMoveDown: (index: number) => void;
  canMoveUp: boolean;
  canMoveDown: boolean;
}

export const ActionItem: React.FC<ActionItemProps> = ({
  action,
  index,
  availableActions,
  onActionSelect,
  onUpdateAction,
  onRemoveAction,
  onMoveUp,
  onMoveDown,
  canMoveUp,
  canMoveDown,
}) => {
  const handleParamChange = (paramName: string, value: string | number) => {
    onUpdateAction(index, {
      params: {
        ...(action.params as any),
        [paramName]: value,
      },
    });
  };

  // Helper function to safely handle params with null/undefined check
  const safeHandleParamChange = (key: string, value: any) => {
    handleParamChange(key, value);
  };

  // Helper function to safely get parameter values
  const getParamValue = (key: string): any => {
    return (action.params as any)?.[key] || '';
  };

  const renderParameterFields = () => {
    if (!action.command) return null;

    const fields = [];
    const params = action.params as any;

    // Common wait_time field for all actions
    fields.push(
      <TextField
        key="wait_time"
        label="Wait Time (ms)"
        type="number"
        size="small"
        value={params?.wait_time || 0}
        onChange={(e) => {
          const value = parseInt(e.target.value);
          handleParamChange('wait_time', isNaN(value) ? 0 : value);
        }}
        inputProps={{ min: 0, max: 10000, step: 100 }}
        sx={{
          width: 120,
          '& .MuiInputBase-input': {
            padding: '3px 6px',
            fontSize: '0.75rem',
          },
        }}
      />,
    );

    // Action-specific parameter fields
    switch (action.command) {
      case 'press_key':
        fields.push(
          <TextField
            key="key"
            label="Key"
            size="small"
            value={params?.key || ''}
            onChange={(e) => handleParamChange('key', e.target.value)}
            placeholder="e.g., UP, DOWN, HOME, BACK"
            sx={{
              width: 180,
              '& .MuiInputBase-input': {
                padding: '3px 6px',
                fontSize: '0.75rem',
              },
            }}
          />,
        );
        break;

      case 'input_text':
        fields.push(
          <TextField
            key="text"
            label="Text"
            size="small"
            value={getParamValue('text') || ''}
            onChange={(e) => safeHandleParamChange('text', e.target.value)}
            placeholder="Text to input"
            sx={{
              width: 220,
              '& .MuiInputBase-input': {
                padding: '3px 6px',
                fontSize: '0.75rem',
              },
            }}
          />,
        );
        break;

      case 'click_element':
        fields.push(
          <TextField
            key="element_id"
            label="Element ID"
            size="small"
            value={getParamValue('element_id') || ''}
            onChange={(e) => safeHandleParamChange('element_id', e.target.value)}
            placeholder="e.g., Home Button, Menu Icon"
            sx={{
              width: 220,
              '& .MuiInputBase-input': {
                padding: '3px 6px',
                fontSize: '0.75rem',
              },
            }}
          />,
        );
        break;

      case 'click_element_by_id':
        fields.push(
          <TextField
            key="element_id"
            label="Element ID"
            size="small"
            value={getParamValue('element_id') || ''}
            onChange={(e) => safeHandleParamChange('element_id', e.target.value)}
            placeholder="e.g., 8, 15, 23"
            sx={{
              width: 220,
              '& .MuiInputBase-input': {
                padding: '3px 6px',
                fontSize: '0.75rem',
              },
            }}
          />,
        );
        break;

      case 'tap_coordinates':
        fields.push(
          <TextField
            key="x"
            label="X"
            type="number"
            size="small"
            value={getParamValue('x') || ''}
            onChange={(e) => safeHandleParamChange('x', parseInt(e.target.value) || 0)}
            sx={{
              width: 70,
              '& .MuiInputBase-input': {
                padding: '3px 6px',
                fontSize: '0.75rem',
              },
            }}
          />,
          <TextField
            key="y"
            label="Y"
            type="number"
            size="small"
            value={getParamValue('y') || ''}
            onChange={(e) => safeHandleParamChange('y', parseInt(e.target.value) || 0)}
            sx={{
              width: 70,
              '& .MuiInputBase-input': {
                padding: '3px 6px',
                fontSize: '0.75rem',
              },
            }}
          />,
        );
        break;

      case 'swipe':
        fields.push(
          <TextField
            key="direction"
            label="Direction"
            size="small"
            value={getParamValue('direction') || ''}
            onChange={(e) => safeHandleParamChange('direction', e.target.value)}
            placeholder="e.g., up, down, left, right"
            sx={{
              width: 130,
              '& .MuiInputBase-input': {
                padding: '3px 6px',
                fontSize: '0.75rem',
              },
            }}
          />,
        );
        break;

      case 'launch_app':
      case 'close_app':
        fields.push(
          <TextField
            key="package"
            label="Package Name"
            size="small"
            value={getParamValue('package') || ''}
            onChange={(e) => safeHandleParamChange('package', e.target.value)}
            placeholder="e.g., com.example.app"
            sx={{
              width: 220,
              '& .MuiInputBase-input': {
                padding: '3px 6px',
                fontSize: '0.75rem',
              },
            }}
          />,
        );
        break;

      case 'wait':
        fields.push(
          <TextField
            key="duration"
            label="Duration (s)"
            type="number"
            size="small"
            value={getParamValue('duration') || 1}
            onChange={(e) => safeHandleParamChange('duration', parseFloat(e.target.value) || 1)}
            inputProps={{ min: 0.1, max: 60, step: 0.1 }}
            sx={{
              width: 100,
              '& .MuiInputBase-input': {
                padding: '3px 6px',
                fontSize: '0.75rem',
              },
            }}
          />,
        );
        break;

      case 'scroll':
        fields.push(
          <TextField
            key="direction"
            label="Direction"
            size="small"
            value={getParamValue('direction') || ''}
            onChange={(e) => safeHandleParamChange('direction', e.target.value)}
            placeholder="e.g., up, down"
            sx={{
              width: 130,
              '& .MuiInputBase-input': {
                padding: '3px 6px',
                fontSize: '0.75rem',
              },
            }}
          />,
          <TextField
            key="amount"
            label="Amount"
            type="number"
            size="small"
            value={getParamValue('amount') || 1}
            onChange={(e) => safeHandleParamChange('amount', parseInt(e.target.value) || 1)}
            sx={{
              width: 80,
              '& .MuiInputBase-input': {
                padding: '3px 6px',
                fontSize: '0.75rem',
              },
            }}
          />,
        );
        break;
    }

    // Organize fields based on count
    if (fields.length <= 3) {
      // ≤3 parameters: show in one line
      return (
        <Box sx={{ display: 'flex', gap: 0.5, alignItems: 'center', flexWrap: 'nowrap' }}>
          {fields}
        </Box>
      );
    } else {
      // >3 parameters: show 3 per line
      const rows = [];
      for (let i = 0; i < fields.length; i += 3) {
        const rowFields = fields.slice(i, i + 3);
        rows.push(
          <Box key={i} sx={{ display: 'flex', gap: 0.5, alignItems: 'center', mb: 0.5 }}>
            {rowFields}
          </Box>,
        );
      }
      return <Box>{rows}</Box>;
    }
  };

  return (
    <Box
      sx={{
        mb: 0.5,
        px: 0.5,
        py: 0.5,
        border: '1px solid',
        borderColor: 'divider',
        borderRadius: 1,
      }}
    >
      {/* Line 1: Action command dropdown */}
      <Box sx={{ display: 'flex', gap: 0.5, alignItems: 'center', mb: 0.5 }}>
        <FormControl size="small" sx={{ flex: 1, minWidth: 200, maxWidth: 300 }}>
          <InputLabel>Action</InputLabel>
          <Select
            value={
              // Match by command since backend actions don't have IDs
              action.command &&
              Object.values(availableActions)
                .flat()
                .find((act) => act.command === action.command)?.id || ''
            }
            onChange={(e) => onActionSelect(index, e.target.value)}
            label="Action"
            size="small"
            sx={{
              '& .MuiSelect-select': {
                fontSize: '0.8rem',
                py: 0.5,
              },
              '& .MuiInputBase-root': {
                minHeight: '24px',
              },
            }}
            renderValue={(selected) => {
              // Find the selected action and return its label
              const selectedAction = Object.values(availableActions)
                .flat()
                .find((act) => act.id === selected);
              if (selectedAction) {
                return selectedAction.label;
              }
              return selected;
            }}
          >
            {Object.entries(availableActions).map(([category, actions]) => {
              // Ensure actions is an array
              if (!Array.isArray(actions)) {
                console.warn(
                  `[@component:ActionItem] Invalid actions for category ${category}:`,
                  actions,
                );
                return null;
              }

              return [
                <MenuItem
                  key={`header-${category}`}
                  disabled
                  sx={{ fontWeight: 'bold', fontSize: '0.65rem', minHeight: '20px' }}
                >
                  {category.replace(/_/g, ' ').toUpperCase()}
                </MenuItem>,
                ...actions.map((actionDef) => (
                  <MenuItem
                    key={actionDef.id}
                    value={actionDef.id}
                    sx={{ pl: 3, fontSize: '0.7rem', minHeight: '20px' }}
                  >
                    {actionDef.label}
                  </MenuItem>
                )),
              ];
            })}
          </Select>
        </FormControl>

        {/* Move buttons */}
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.25 }}>
          <IconButton
            size="small"
            onClick={() => onMoveUp(index)}
            disabled={!canMoveUp}
            sx={{ p: 0.5, minWidth: 24, width: 24, height: 20 }}
          >
            <KeyboardArrowUpIcon sx={{ fontSize: '1rem' }} />
          </IconButton>
          <IconButton
            size="small"
            onClick={() => onMoveDown(index)}
            disabled={!canMoveDown}
            sx={{ p: 0.5, minWidth: 24, width: 24, height: 20 }}
          >
            <KeyboardArrowDownIcon sx={{ fontSize: '1rem' }} />
          </IconButton>
        </Box>

        {/* Remove button */}
        <IconButton
          size="small"
          onClick={() => onRemoveAction(index)}
          sx={{ p: 0.5, minWidth: 24, width: 24, height: 24, ml: 0.5 }}
        >
          <CloseIcon sx={{ fontSize: '1rem' }} />
        </IconButton>
      </Box>

      {/* Parameter fields section - organized by count */}
      {action.command && renderParameterFields()}
    </Box>
  );
};
