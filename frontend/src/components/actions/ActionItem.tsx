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
  Checkbox,
  Tooltip,
} from '@mui/material';
import React from 'react';

import type { Actions } from '../../types/controller/Action_Types';
import type { Action } from '../../types/pages/Navigation_Types';
import { useDeviceData } from '../../contexts/device/DeviceDataContext';
import { useNavigation } from '../../contexts/navigation/NavigationContext';

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
  // Get device data context for model references
  const { getModelReferences, references } = useDeviceData();
  
  // Get userInterface from navigation context - this is the ONLY source of truth
  const { userInterface } = useNavigation();

  // Use userinterface name for reference lookup
  const referenceKey = userInterface?.name;

  // Get model references using the userinterface name
  // IMPORTANT: Must depend on references state to re-render when references are added
  const modelReferences = React.useMemo(() => {
    if (!referenceKey) return {};
    return getModelReferences(referenceKey);
  }, [getModelReferences, referenceKey, references]);
  const handleParamChange = (paramName: string, value: string | number) => {
    const newParams = {
      ...(action.params as any),
      [paramName]: value,
    };
    
    console.log('🔍 [ActionItem:handleParamChange] Updating param:', {
      paramName,
      value,
      oldParams: action.params,
      newParams,
      actionIndex: index,
      actionCommand: action.command
    });
    
    onUpdateAction(index, {
      params: newParams,
    });
  };

  // Helper function to safely handle params with null/undefined check
  const safeHandleParamChange = (key: string, value: any) => {
    console.log('🔍 [DEBUG] safeHandleParamChange called:', {
      key,
      value,
      currentParams: action.params,
      actionIndex: index
    });
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

    // Find the current action definition to check requiresInput
    const currentActionDef = Object.values(availableActions)
      .flat()
      .find((act) => {
        if (act.command !== action.command) return false;
        
        // If action has options (combobox), match by command only - params are user-filled
        if ((act as any).options && Array.isArray((act as any).options) && (act as any).options.length > 0) {
          return true;
        }
        
        // For press_key actions without options (predefined), match the key parameter
        if (action.command === 'press_key' && action.params && act.params) {
          return (action.params as any).key === (act.params as any).key;
        }
        
        // For other actions, just match by command
        return true;
      });

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

    // Iterator field for non-verification actions only
    if (action.action_type !== 'verification') {
      fields.push(
        <TextField
          key="iterator"
          label="Iterations"
          type="number"
          size="small"
          value={action.iterator || 1}
          onChange={(e) => {
            const value = parseInt(e.target.value);
            const clampedValue = isNaN(value) ? 1 : Math.max(1, Math.min(100, value));
            onUpdateAction(index, { iterator: clampedValue });
          }}
          inputProps={{ min: 1, max: 100, step: 1 }}
          sx={{
            width: 100,
            '& .MuiInputBase-input': {
              padding: '3px 6px',
              fontSize: '0.75rem',
            },
          }}
        />,
      );
      
      // Continue on fail checkbox for web and mobile actions only
      if (action.action_type === 'web' || action.action_type === 'remote') {
        fields.push(
          <Tooltip key="continue_on_fail" title="Continue execution even if this action fails (useful for optional actions like cookie popups)">
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              <Checkbox
                checked={action.continue_on_fail || false}
                onChange={(e) => {
                  onUpdateAction(index, { continue_on_fail: e.target.checked });
                }}
                size="small"
                sx={{ padding: '2px' }}
              />
              <Box sx={{ fontSize: '0.7rem', color: 'text.secondary', whiteSpace: 'nowrap' }}>
                Optional
              </Box>
            </Box>
          </Tooltip>,
        );
      }
    }

    // Action-specific parameter fields
    switch (action.command) {
      case 'press_key':
        // Show key field for both remote and web actions if they require input
        if (currentActionDef?.requiresInput) {
          const placeholder = action.action_type === 'web' 
            ? "e.g., BACK, OK, ESCAPE" 
            : "e.g., UP, DOWN, HOME, BACK";
          
          // Check if action definition has options array for dropdown
          const options = (currentActionDef as any)?.options;
          
          console.log('🔍 [ActionItem] press_key options check:', {
            command: action.command,
            action_type: action.action_type,
            currentActionDef,
            hasOptions: !!options,
            optionsLength: options?.length,
            options
          });
          
          if (options && Array.isArray(options) && options.length > 0) {
            // Render dropdown/select
            fields.push(
              <FormControl key="key" size="small" sx={{ width: 150 }}>
                <InputLabel>Key</InputLabel>
                <Select
                  value={getParamValue('key') || ''}
                  onChange={(e) => safeHandleParamChange('key', e.target.value)}
                  label="Key"
                  sx={{
                    '& .MuiSelect-select': {
                      padding: '3px 6px',
                      fontSize: '0.75rem',
                    },
                  }}
                >
                  {options.map((option: string) => (
                    <MenuItem key={option} value={option} sx={{ fontSize: '0.75rem' }}>
                      {option}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            );
          } else {
            // Render text input (fallback)
            fields.push(
              <TextField
                key="key"
                label="Key"
                size="small"
                value={getParamValue('key') || ''}
                onChange={(e) => safeHandleParamChange('key', e.target.value)}
                placeholder={placeholder}
                sx={{
                  width: 150,
                  '& .MuiInputBase-input': {
                    padding: '3px 6px',
                    fontSize: '0.75rem',
                  },
                }}
              />,
            );
          }
        }
        break;

      case 'input_text':
        // Handle both remote and web input_text actions
        if (currentActionDef?.requiresInput) {
          if (action.action_type === 'web') {
            // Web input_text needs selector and text fields
            fields.push(
              <TextField
                key="selector"
                label="Selector"
                size="small"
                value={getParamValue('selector') || ''}
                onChange={(e) => safeHandleParamChange('selector', e.target.value)}
                placeholder="#username"
                sx={{
                  width: 150,
                  '& .MuiInputBase-input': {
                    padding: '3px 6px',
                    fontSize: '0.75rem',
                  },
                }}
              />,
              <TextField
                key="text"
                label="Text"
                size="small"
                value={getParamValue('text') || ''}
                onChange={(e) => safeHandleParamChange('text', e.target.value)}
                placeholder="Text to input"
                sx={{
                  width: 150,
                  '& .MuiInputBase-input': {
                    padding: '3px 6px',
                    fontSize: '0.75rem',
                  },
                }}
              />,
            );
          } else {
            // Remote input_text only needs text field
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
          }
        }
        break;

      case 'click_element':
        // UNIFIED: Both remote and web use element_id parameter (same principle: dump UI → find element → click)
        if (currentActionDef?.requiresInput) {
          fields.push(
            <TextField
              key="element_id"
              label="Element Text/ID"
              size="small"
              value={getParamValue('element_id') || getParamValue('selector') || ''}  // Support legacy selector param
              onChange={(e) => safeHandleParamChange('element_id', e.target.value)}
              placeholder="e.g., Home Button, Submit"
              sx={{
                width: 220,
                '& .MuiInputBase-input': {
                  padding: '3px 6px',
                  fontSize: '0.75rem',
                },
              }}
            />,
          );
        }
        break;

      case 'find_element':
        // Web action: Find element by selector or text (returns element ID and position)
        if (currentActionDef?.requiresInput) {
          fields.push(
            <TextField
              key="selector"
              label="Selector or Text"
              size="small"
              value={getParamValue('selector') || ''}
              onChange={(e) => safeHandleParamChange('selector', e.target.value)}
              placeholder="e.g., TV Guide, #element-id, .class-name"
              sx={{
                width: 220,
                '& .MuiInputBase-input': {
                  padding: '3px 6px',
                  fontSize: '0.75rem',
                },
              }}
            />,
          );
        }
        break;

      case 'hover_element':
        // Web action: Hover over element to trigger rollover effects
        if (currentActionDef?.requiresInput) {
          fields.push(
            <TextField
              key="selector"
              label="Selector or Text"
              size="small"
              value={getParamValue('selector') || ''}
              onChange={(e) => safeHandleParamChange('selector', e.target.value)}
              placeholder="e.g., #player-controls, Play Button"
              sx={{
                width: 220,
                '& .MuiInputBase-input': {
                  padding: '3px 6px',
                  fontSize: '0.75rem',
                },
              }}
            />,
          );
        }
        break;

      case 'click_element_by_id':
        // Only show element_id field if the action requires input
        if (currentActionDef?.requiresInput) {
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
        }
        break;

      case 'tap_coordinates':
        // Only show coordinate fields if the action requires input
        if (currentActionDef?.requiresInput) {
          fields.push(
            <Box key="coordinates" sx={{ display: 'flex', gap: 0.5, alignItems: 'center' }}>
              <TextField
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
              />
              <TextField
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
              />
            </Box>,
          );
        }
        break;

      case 'swipe':
        fields.push(
          <TextField
            key="from_x"
            label="From X"
            type="number"
            size="small"
            value={getParamValue('from_x') || ''}
            onChange={(e) => safeHandleParamChange('from_x', parseInt(e.target.value) || 0)}
            sx={{
              width: 70,
              '& .MuiInputBase-input': {
                padding: '3px 6px',
                fontSize: '0.75rem',
              },
            }}
          />,
          <TextField
            key="from_y"
            label="From Y"
            type="number"
            size="small"
            value={getParamValue('from_y') || ''}
            onChange={(e) => safeHandleParamChange('from_y', parseInt(e.target.value) || 0)}
            sx={{
              width: 70,
              '& .MuiInputBase-input': {
                padding: '3px 6px',
                fontSize: '0.75rem',
              },
            }}
          />,
          <TextField
            key="to_x"
            label="To X"
            type="number"
            size="small"
            value={getParamValue('to_x') || ''}
            onChange={(e) => safeHandleParamChange('to_x', parseInt(e.target.value) || 0)}
            sx={{
              width: 70,
              '& .MuiInputBase-input': {
                padding: '3px 6px',
                fontSize: '0.75rem',
              },
            }}
          />,
          <TextField
            key="to_y"
            label="To Y"
            type="number"
            size="small"
            value={getParamValue('to_y') || ''}
            onChange={(e) => safeHandleParamChange('to_y', parseInt(e.target.value) || 0)}
            sx={{
              width: 70,
              '& .MuiInputBase-input': {
                padding: '3px 6px',
                fontSize: '0.75rem',
              },
            }}
          />,
          <TextField
            key="duration"
            label="Duration (ms)"
            type="number"
            size="small"
            value={getParamValue('duration') || 300}
            onChange={(e) => safeHandleParamChange('duration', parseInt(e.target.value) || 300)}
            inputProps={{ min: 100, max: 2000, step: 100 }}
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

      case 'swipe_up':
        fields.push(
          <TextField
            key="from_x"
            label="From X"
            type="number"
            size="small"
            value={getParamValue('from_x') || 500}
            onChange={(e) => safeHandleParamChange('from_x', parseInt(e.target.value) || 500)}
            sx={{
              width: 70,
              '& .MuiInputBase-input': {
                padding: '3px 6px',
                fontSize: '0.75rem',
              },
            }}
          />,
          <TextField
            key="from_y"
            label="From Y"
            type="number"
            size="small"
            value={getParamValue('from_y') || 1500}
            onChange={(e) => safeHandleParamChange('from_y', parseInt(e.target.value) || 1500)}
            sx={{
              width: 70,
              '& .MuiInputBase-input': {
                padding: '3px 6px',
                fontSize: '0.75rem',
              },
            }}
          />,
          <TextField
            key="to_x"
            label="To X"
            type="number"
            size="small"
            value={getParamValue('to_x') || 500}
            onChange={(e) => safeHandleParamChange('to_x', parseInt(e.target.value) || 500)}
            sx={{
              width: 70,
              '& .MuiInputBase-input': {
                padding: '3px 6px',
                fontSize: '0.75rem',
              },
            }}
          />,
          <TextField
            key="to_y"
            label="To Y"
            type="number"
            size="small"
            value={getParamValue('to_y') || 500}
            onChange={(e) => safeHandleParamChange('to_y', parseInt(e.target.value) || 500)}
            sx={{
              width: 70,
              '& .MuiInputBase-input': {
                padding: '3px 6px',
                fontSize: '0.75rem',
              },
            }}
          />,
          <TextField
            key="duration"
            label="Duration (ms)"
            type="number"
            size="small"
            value={getParamValue('duration') || 300}
            onChange={(e) => safeHandleParamChange('duration', parseInt(e.target.value) || 300)}
            inputProps={{ min: 100, max: 2000, step: 100 }}
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

      case 'swipe_down':
        fields.push(
          <TextField
            key="from_x"
            label="From X"
            type="number"
            size="small"
            value={getParamValue('from_x') || 500}
            onChange={(e) => safeHandleParamChange('from_x', parseInt(e.target.value) || 500)}
            sx={{
              width: 70,
              '& .MuiInputBase-input': {
                padding: '3px 6px',
                fontSize: '0.75rem',
              },
            }}
          />,
          <TextField
            key="from_y"
            label="From Y"
            type="number"
            size="small"
            value={getParamValue('from_y') || 500}
            onChange={(e) => safeHandleParamChange('from_y', parseInt(e.target.value) || 500)}
            sx={{
              width: 70,
              '& .MuiInputBase-input': {
                padding: '3px 6px',
                fontSize: '0.75rem',
              },
            }}
          />,
          <TextField
            key="to_x"
            label="To X"
            type="number"
            size="small"
            value={getParamValue('to_x') || 500}
            onChange={(e) => safeHandleParamChange('to_x', parseInt(e.target.value) || 500)}
            sx={{
              width: 70,
              '& .MuiInputBase-input': {
                padding: '3px 6px',
                fontSize: '0.75rem',
              },
            }}
          />,
          <TextField
            key="to_y"
            label="To Y"
            type="number"
            size="small"
            value={getParamValue('to_y') || 1500}
            onChange={(e) => safeHandleParamChange('to_y', parseInt(e.target.value) || 1500)}
            sx={{
              width: 70,
              '& .MuiInputBase-input': {
                padding: '3px 6px',
                fontSize: '0.75rem',
              },
            }}
          />,
          <TextField
            key="duration"
            label="Duration (ms)"
            type="number"
            size="small"
            value={getParamValue('duration') || 300}
            onChange={(e) => safeHandleParamChange('duration', parseInt(e.target.value) || 300)}
            inputProps={{ min: 100, max: 2000, step: 100 }}
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

      case 'swipe_left':
        fields.push(
          <TextField
            key="from_x"
            label="From X"
            type="number"
            size="small"
            value={getParamValue('from_x') || 800}
            onChange={(e) => safeHandleParamChange('from_x', parseInt(e.target.value) || 800)}
            sx={{
              width: 70,
              '& .MuiInputBase-input': {
                padding: '3px 6px',
                fontSize: '0.75rem',
              },
            }}
          />,
          <TextField
            key="from_y"
            label="From Y"
            type="number"
            size="small"
            value={getParamValue('from_y') || 1000}
            onChange={(e) => safeHandleParamChange('from_y', parseInt(e.target.value) || 1000)}
            sx={{
              width: 70,
              '& .MuiInputBase-input': {
                padding: '3px 6px',
                fontSize: '0.75rem',
              },
            }}
          />,
          <TextField
            key="to_x"
            label="To X"
            type="number"
            size="small"
            value={getParamValue('to_x') || 200}
            onChange={(e) => safeHandleParamChange('to_x', parseInt(e.target.value) || 200)}
            sx={{
              width: 70,
              '& .MuiInputBase-input': {
                padding: '3px 6px',
                fontSize: '0.75rem',
              },
            }}
          />,
          <TextField
            key="to_y"
            label="To Y"
            type="number"
            size="small"
            value={getParamValue('to_y') || 1000}
            onChange={(e) => safeHandleParamChange('to_y', parseInt(e.target.value) || 1000)}
            sx={{
              width: 70,
              '& .MuiInputBase-input': {
                padding: '3px 6px',
                fontSize: '0.75rem',
              },
            }}
          />,
          <TextField
            key="duration"
            label="Duration (ms)"
            type="number"
            size="small"
            value={getParamValue('duration') || 300}
            onChange={(e) => safeHandleParamChange('duration', parseInt(e.target.value) || 300)}
            inputProps={{ min: 100, max: 2000, step: 100 }}
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

      case 'swipe_right':
        fields.push(
          <TextField
            key="from_x"
            label="From X"
            type="number"
            size="small"
            value={getParamValue('from_x') || 200}
            onChange={(e) => safeHandleParamChange('from_x', parseInt(e.target.value) || 200)}
            sx={{
              width: 70,
              '& .MuiInputBase-input': {
                padding: '3px 6px',
                fontSize: '0.75rem',
              },
            }}
          />,
          <TextField
            key="from_y"
            label="From Y"
            type="number"
            size="small"
            value={getParamValue('from_y') || 1000}
            onChange={(e) => safeHandleParamChange('from_y', parseInt(e.target.value) || 1000)}
            sx={{
              width: 70,
              '& .MuiInputBase-input': {
                padding: '3px 6px',
                fontSize: '0.75rem',
              },
            }}
          />,
          <TextField
            key="to_x"
            label="To X"
            type="number"
            size="small"
            value={getParamValue('to_x') || 800}
            onChange={(e) => safeHandleParamChange('to_x', parseInt(e.target.value) || 800)}
            sx={{
              width: 70,
              '& .MuiInputBase-input': {
                padding: '3px 6px',
                fontSize: '0.75rem',
              },
            }}
          />,
          <TextField
            key="to_y"
            label="To Y"
            type="number"
            size="small"
            value={getParamValue('to_y') || 1000}
            onChange={(e) => safeHandleParamChange('to_y', parseInt(e.target.value) || 1000)}
            sx={{
              width: 70,
              '& .MuiInputBase-input': {
                padding: '3px 6px',
                fontSize: '0.75rem',
              },
            }}
          />,
          <TextField
            key="duration"
            label="Duration (ms)"
            type="number"
            size="small"
            value={getParamValue('duration') || 300}
            onChange={(e) => safeHandleParamChange('duration', parseInt(e.target.value) || 300)}
            inputProps={{ min: 100, max: 2000, step: 100 }}
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

      case 'launch_app':
      case 'close_app':
        // Only show package field if the action requires input
        if (currentActionDef?.requiresInput) {
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
        }
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
        // Scroll actions have hardcoded direction and amount in backend params
        // No user input required - scroll_up/down/left/right are predefined actions
        break;

      case 'auto_return':
        fields.push(
          <TextField
            key="timer"
            label="Timer (ms)"
            type="number"
            size="small"
            value={getParamValue('timer') || 2000}
            onChange={(e) => safeHandleParamChange('timer', parseInt(e.target.value) || 2000)}
            inputProps={{ min: 0, max: 30000, step: 100 }}
            sx={{
              width: 120,
              '& .MuiInputBase-input': {
                padding: '3px 6px',
                fontSize: '0.75rem',
              },
            }}
          />,
          <TextField
            key="target_node_id"
            label="Target Node ID"
            size="small"
            value={getParamValue('target_node_id') || ''}
            onChange={(e) => safeHandleParamChange('target_node_id', e.target.value)}
            placeholder="Node to return to"
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

      case 'waitForTextToAppear':
      case 'waitForTextToDisappear':
        // Debug verification action properties
        console.log('[ActionItem] Text verification action debug:', {
          command: action.command,
          action_type: action.action_type,
          verification_type: action.verification_type,
          full_action: action
        });
        
        // Check if this is a verification action with text type
        if (action.action_type === 'verification' && action.verification_type === 'text') {
          console.log('[ActionItem] Rendering text verification UI');
          // Text reference selection (same as VerificationItem.tsx for text)
          fields.push(
            <FormControl key="text_reference" size="small" sx={{ width: 250 }}>
              <InputLabel>Text Reference</InputLabel>
              <Select
                value={action.params?.reference_name || ''}
                onChange={(e) => {
                  const internalKey = e.target.value;
                  const selectedRef = modelReferences[internalKey];
                  
                  console.log('🔍 [DEBUG] Text reference selection:', {
                    internalKey,
                    selectedRef,
                    modelReferences,
                    currentParams: action.params
                  });
                  
                  if (selectedRef && selectedRef.type === 'text') {
                    console.log('🔍 [DEBUG] Updating text reference params:', {
                      reference_name: internalKey,
                      text: selectedRef.text || ''
                    });
                    
                    // Update both parameters in a single call to avoid state race condition
                    const newParams = {
                      ...(action.params as any),
                      reference_name: internalKey,
                      text: selectedRef.text || ''
                    };
                    
                    console.log('🔍 [DEBUG] Setting combined params:', newParams);
                    onUpdateAction(index, { params: newParams });
                  } else {
                    console.log('🔍 [DEBUG] Reference selection failed - invalid ref or type');
                  }
                }}
                label="Text Reference"
                size="small"
                sx={{
                  '& .MuiSelect-select': {
                    fontSize: '0.8rem',
                    py: 0.5,
                  },
                }}
              >
                {Object.entries(modelReferences)
                  .filter(([_internalKey, ref]) => ref.type === 'text')
                  .map(([internalKey, ref]) => (
                    <MenuItem key={internalKey} value={internalKey} sx={{ fontSize: '0.75rem' }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        📝 <span>{ref.name || internalKey}</span>
                      </Box>
                    </MenuItem>
                  ))}
                {Object.entries(modelReferences).filter(([_internalKey, ref]) => ref.type === 'text')
                  .length === 0 && (
                  <MenuItem disabled value="" sx={{ fontSize: '0.75rem', fontStyle: 'italic' }}>
                    No text references available
                  </MenuItem>
                )}
              </Select>
            </FormControl>,
          );
        } else {
          console.log('[ActionItem] NOT rendering text verification UI - check failed');
        }
        break;

      case 'waitForImageToAppear':
      case 'waitForImageToDisappear':
        // Debug verification action properties
        console.log('[ActionItem] Image verification action debug:', {
          command: action.command,
          action_type: action.action_type,
          verification_type: action.verification_type,
          full_action: action
        });
        
        // Check if this is a verification action with image type
        if (action.action_type === 'verification' && action.verification_type === 'image') {
          console.log('[ActionItem] Rendering image verification UI');
          // Image reference selection (same as VerificationItem.tsx for image)
          fields.push(
            <FormControl key="image_reference" size="small" sx={{ width: 250 }}>
              <InputLabel>Image Reference</InputLabel>
              <Select
                value={action.params?.reference_name || ''}
                onChange={(e) => {
                  const internalKey = e.target.value;
                  const selectedRef = modelReferences[internalKey];
                  console.log('🔍 [DEBUG] Image reference selection:', {
                    internalKey,
                    selectedRef,
                    modelReferences,
                    currentParams: action.params
                  });
                  
                  if (selectedRef && selectedRef.type === 'image') {
                    console.log('🔍 [DEBUG] Updating image reference params:', {
                      reference_name: internalKey,
                      image_path: selectedRef.name || internalKey
                    });
                    
                    // Update both parameters in a single call to avoid state race condition
                    const newParams = {
                      ...(action.params as any),
                      reference_name: internalKey,
                      image_path: selectedRef.name || internalKey
                    };
                    
                    console.log('🔍 [DEBUG] Setting combined image params:', newParams);
                    onUpdateAction(index, { params: newParams });
                  } else {
                    console.log('🔍 [DEBUG] Image reference selection failed - invalid ref or type');
                  }
                }}
                label="Image Reference"
                size="small"
                sx={{
                  '& .MuiSelect-select': {
                    fontSize: '0.8rem',
                    py: 0.5,
                  },
                }}
              >
                {Object.entries(modelReferences)
                  .filter(([_internalKey, ref]) => ref.type === 'image')
                  .map(([internalKey, ref]) => (
                    <MenuItem key={internalKey} value={internalKey} sx={{ fontSize: '0.75rem' }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        🖼️ <span>{ref.name || internalKey}</span>
                      </Box>
                    </MenuItem>
                  ))}
                {Object.entries(modelReferences).filter(([_internalKey, ref]) => ref.type === 'image')
                  .length === 0 && (
                  <MenuItem disabled value="" sx={{ fontSize: '0.75rem', fontStyle: 'italic' }}>
                    No image references available
                  </MenuItem>
                )}
              </Select>
            </FormControl>,
          );
        } else {
          console.log('[ActionItem] NOT rendering image verification UI - check failed');
        }
        break;

      case 'waitForImageToAppearThenDisappear':
        // Debug action properties
        console.log('[ActionItem] Image appear-then-disappear action debug:', {
          command: action.command,
          action_type: action.action_type,
          verification_type: action.verification_type,
          full_action: action
        });
        
        // Check if this is a verification action with image type
        if (action.action_type === 'verification' && action.verification_type === 'image') {
          console.log('[ActionItem] Rendering image appear-then-disappear UI');
          // Image reference selection (same as other image verifications)
          fields.push(
            <FormControl key="image_reference" size="small" sx={{ width: 250 }}>
              <InputLabel>Image Reference</InputLabel>
              <Select
                value={action.params?.reference_name || ''}
                onChange={(e) => {
                  const internalKey = e.target.value;
                  const selectedRef = modelReferences[internalKey];
                  console.log('🔍 [DEBUG] Image reference selection (appear-then-disappear):', {
                    internalKey,
                    selectedRef,
                    modelReferences,
                    currentParams: action.params
                  });
                  
                  if (selectedRef && selectedRef.type === 'image') {
                    console.log('🔍 [DEBUG] Updating image reference params:', {
                      reference_name: internalKey,
                      image_path: selectedRef.name || internalKey
                    });
                    
                    // Update both parameters in a single call to avoid state race condition
                    const newParams = {
                      ...(action.params as any),
                      reference_name: internalKey,
                      image_path: selectedRef.name || internalKey
                    };
                    
                    console.log('🔍 [DEBUG] Setting combined image params:', newParams);
                    onUpdateAction(index, { params: newParams });
                  } else {
                    console.log('🔍 [DEBUG] Image reference selection failed - invalid ref or type');
                  }
                }}
                label="Image Reference"
                size="small"
                sx={{
                  '& .MuiSelect-select': {
                    fontSize: '0.8rem',
                    py: 0.5,
                  },
                }}
              >
                {Object.entries(modelReferences)
                  .filter(([_internalKey, ref]) => ref.type === 'image')
                  .map(([internalKey, ref]) => (
                    <MenuItem key={internalKey} value={internalKey} sx={{ fontSize: '0.75rem' }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        🖼️ <span>{ref.name || internalKey}</span>
                      </Box>
                    </MenuItem>
                  ))}
                {Object.entries(modelReferences).filter(([_internalKey, ref]) => ref.type === 'image')
                  .length === 0 && (
                  <MenuItem disabled value="" sx={{ fontSize: '0.75rem', fontStyle: 'italic' }}>
                    No image references available
                  </MenuItem>
                )}
              </Select>
            </FormControl>,
          );
        } else {
          console.log('[ActionItem] NOT rendering image appear-then-disappear UI - check failed');
        }
        break;

      case 'waitForElementToAppear':
      case 'waitForElementToDisappear':
        // Debug verification action properties
        console.log('[ActionItem] Web element verification action debug:', {
          command: action.command,
          action_type: action.action_type,
          verification_type: action.verification_type,
          full_action: action
        });
        
        // Check if this is a verification action with appium type (web automation)
        if (action.action_type === 'verification' && action.verification_type === 'appium') {
          console.log('[ActionItem] Rendering web element verification UI (text input like ADB)');
          // Simple text input for search term (like ADB verifications - consistent parameter name)
          fields.push(
            <TextField
              key="search_term"
              label="Element Text/ID"
              size="small"
              value={getParamValue('search_term') || ''}
              onChange={(e) => safeHandleParamChange('search_term', e.target.value)}
              placeholder="e.g., Submit, Login Button, #element-id"
              sx={{
                width: 250,
                '& .MuiInputBase-input': {
                  padding: '3px 6px',
                  fontSize: '0.75rem',
                },
              }}
            />,
          );
        } else {
          console.log('[ActionItem] NOT rendering web element verification UI - check failed');
        }
        break;

      // Desktop actions (PyAutoGUI and Bash)
      case 'execute_pyautogui_click':
      case 'execute_pyautogui_rightclick':
      case 'execute_pyautogui_doubleclick':
      case 'execute_pyautogui_move':
        if (currentActionDef?.requiresInput) {
          fields.push(
            <Box key="coordinates" sx={{ display: 'flex', gap: 0.5, alignItems: 'center' }}>
              <TextField
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
              />
              <TextField
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
              />
            </Box>,
          );
        }
        break;

      case 'execute_pyautogui_keypress':
        if (currentActionDef?.requiresInput) {
          // Check if action definition has options array for dropdown
          const options = (currentActionDef as any)?.options;
          
          if (options && Array.isArray(options) && options.length > 0) {
            // Render dropdown/select
            fields.push(
              <FormControl key="key" size="small" sx={{ width: 150 }}>
                <InputLabel>Key</InputLabel>
                <Select
                  value={getParamValue('key') || ''}
                  onChange={(e) => safeHandleParamChange('key', e.target.value)}
                  label="Key"
                  sx={{
                    '& .MuiSelect-select': {
                      padding: '3px 6px',
                      fontSize: '0.75rem',
                    },
                  }}
                >
                  {options.map((option: string) => (
                    <MenuItem key={option} value={option}>
                      {option}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            );
          } else {
            // Render text input (fallback)
            fields.push(
              <TextField
                key="key"
                label="Key"
                size="small"
                value={getParamValue('key') || ''}
                onChange={(e) => safeHandleParamChange('key', e.target.value)}
                placeholder="enter, space, tab, ctrl"
                sx={{
                  width: 150,
                  '& .MuiInputBase-input': {
                    padding: '3px 6px',
                    fontSize: '0.75rem',
                  },
                }}
              />
            );
          }
        }
        break;

      case 'execute_pyautogui_type':
        if (currentActionDef?.requiresInput) {
          fields.push(
            <TextField
              key="text"
              label="Text"
              size="small"
              value={getParamValue('text') || ''}
              onChange={(e) => safeHandleParamChange('text', e.target.value)}
              placeholder="Text to type"
              sx={{
                width: 200,
                '& .MuiInputBase-input': {
                  padding: '3px 6px',
                  fontSize: '0.75rem',
                },
              }}
            />,
          );
        }
        break;

      case 'execute_pyautogui_scroll':
        if (currentActionDef?.requiresInput) {
          fields.push(
            <TextField
              key="clicks"
              label="Scroll Clicks"
              type="number"
              size="small"
              value={getParamValue('clicks') || 1}
              onChange={(e) => safeHandleParamChange('clicks', parseInt(e.target.value) || 1)}
              placeholder="Positive=up, Negative=down"
              sx={{
                width: 120,
                '& .MuiInputBase-input': {
                  padding: '3px 6px',
                  fontSize: '0.75rem',
                },
              }}
            />,
          );
        }
        break;

      case 'execute_pyautogui_locate':
      case 'execute_pyautogui_locate_and_click':
        if (currentActionDef?.requiresInput) {
          fields.push(
            <TextField
              key="image_path"
              label="Image Path"
              size="small"
              value={getParamValue('image_path') || ''}
              onChange={(e) => safeHandleParamChange('image_path', e.target.value)}
              placeholder="/path/to/image.png"
              sx={{
                width: 250,
                '& .MuiInputBase-input': {
                  padding: '3px 6px',
                  fontSize: '0.75rem',
                },
              }}
            />,
          );
        }
        break;

      case 'execute_pyautogui_launch':
        if (currentActionDef?.requiresInput) {
          fields.push(
            <TextField
              key="app_name"
              label="App Name"
              size="small"
              value={getParamValue('app_name') || ''}
              onChange={(e) => safeHandleParamChange('app_name', e.target.value)}
              placeholder="notepad, calc, firefox"
              sx={{
                width: 180,
                '& .MuiInputBase-input': {
                  padding: '3px 6px',
                  fontSize: '0.75rem',
                },
              }}
            />,
          );
        }
        break;

      case 'execute_bash_command':
        if (currentActionDef?.requiresInput) {
          fields.push(
            <TextField
              key="command"
              label="Bash Command"
              size="small"
              value={getParamValue('command') || getParamValue('bash_command') || ''}
              onChange={(e) => safeHandleParamChange('command', e.target.value)}
              placeholder="ls -la, ps aux, echo hello"
              sx={{
                width: 300,
                '& .MuiInputBase-input': {
                  padding: '3px 6px',
                  fontSize: '0.75rem',
                },
              }}
            />,
          );
        }
        break;

      // Web actions (Playwright)
      case 'navigate_to_url':
        if (currentActionDef?.requiresInput) {
          fields.push(
            <TextField
              key="url"
              label="URL"
              size="small"
              value={getParamValue('url') || ''}
              onChange={(e) => safeHandleParamChange('url', e.target.value)}
              placeholder="https://google.com"
              sx={{
                width: 250,
                '& .MuiInputBase-input': {
                  padding: '3px 6px',
                  fontSize: '0.75rem',
                },
              }}
            />,
          );
        }
        break;



      case 'tap_x_y':
        // Handle web tap_x_y
        if (action.action_type === 'web' && currentActionDef?.requiresInput) {
          fields.push(
            <Box key="coordinates" sx={{ display: 'flex', gap: 0.5, alignItems: 'center' }}>
              <TextField
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
              />
              <TextField
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
              />
            </Box>,
          );
        }
        break;

      case 'execute_javascript':
        if (currentActionDef?.requiresInput) {
          fields.push(
            <TextField
              key="script"
              label="JavaScript"
              size="small"
              value={getParamValue('script') || ''}
              onChange={(e) => safeHandleParamChange('script', e.target.value)}
              placeholder="alert('Hello World')"
              sx={{
                width: 300,
                '& .MuiInputBase-input': {
                  padding: '3px 6px',
                  fontSize: '0.75rem',
                },
              }}
            />,
          );
        }
        break;

      case 'browser_use_task':
        if (currentActionDef?.requiresInput) {
          fields.push(
            <TextField
              key="task"
              label="Task Description"
              size="small"
              value={getParamValue('task') || ''}
              onChange={(e) => safeHandleParamChange('task', e.target.value)}
              placeholder="Search for Python tutorials"
              sx={{
                width: 300,
                '& .MuiInputBase-input': {
                  padding: '3px 6px',
                  fontSize: '0.75rem',
                },
              }}
            />,
          );
        }
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
              // Match by command only for actions with options (combobox), or by command+params for predefined actions
              action.command &&
              Object.values(availableActions)
                .flat()
                .find((act) => {
                  if (act.command !== action.command) return false;
                  
                  // If action has options (combobox), match by command only - params are user-filled
                  if ((act as any).options && Array.isArray((act as any).options) && (act as any).options.length > 0) {
                    return true;
                  }
                  
                  // For press_key actions without options (predefined), match the key parameter
                  if (action.command === 'press_key' && action.params && act.params) {
                    return (action.params as any).key === (act.params as any).key;
                  }
                  
                  // For scroll actions (predefined), match the direction parameter
                  if (action.command === 'scroll' && action.params && act.params) {
                    return (action.params as any).direction === (act.params as any).direction;
                  }
                  
                  // For other actions, just match by command
                  return true;
                })?.id || ''
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
