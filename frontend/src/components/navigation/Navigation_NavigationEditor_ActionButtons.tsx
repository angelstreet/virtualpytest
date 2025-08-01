import {
  Add as AddIcon,
  FitScreen as FitScreenIcon,
  Save as SaveIcon,
  Cancel as CancelIcon,
} from '@mui/icons-material';
import { Box, Button, IconButton, CircularProgress } from '@mui/material';
import React from 'react';

import { NavigationEditorActionButtonsProps } from '../../types/pages/NavigationHeader_Types';
import { ValidationButtonClient } from '../validation';

export const NavigationEditorActionButtons: React.FC<NavigationEditorActionButtonsProps> = ({
  treeId,
  isLocked: _isLocked,
  hasUnsavedChanges,
  isLoading,
  error,
  selectedHost,
  selectedDeviceId,
  isControlActive,
  onAddNewNode,
  onFitView,
  onSaveToConfig,
  onDiscardChanges,
}) => {
  return (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 1,
        minWidth: 0,
      }}
    >
      {/* Validation Button */}
      <ValidationButtonClient
        treeId={treeId}
        disabled={isLoading || !!error || !selectedHost || !selectedDeviceId || !isControlActive || !treeId}
        selectedHost={selectedHost}
        selectedDeviceId={selectedDeviceId}
      />

      {/* Add Node Button */}
      <Button
        startIcon={<AddIcon />}
        onClick={() => onAddNewNode('screen', { x: 250, y: 250 })}
        size="small"
        disabled={isLoading || !!error || !isControlActive}
        variant="outlined"
        sx={{
          minWidth: 'auto',
          whiteSpace: 'nowrap',
          fontSize: '0.75rem',
        }}
        title={!isControlActive ? 'Take control to add nodes' : 'Add Node'}
      >
        Add&nbsp;Node
      </Button>

      {/* Fit View Button */}
      <IconButton onClick={onFitView} size="small" title="Fit View" disabled={isLoading || !!error}>
        <FitScreenIcon />
      </IconButton>

      {/* Save Button */}
      <IconButton
        onClick={() => {
          if (onSaveToConfig) {
            onSaveToConfig();
          }
        }}
        size="small"
        title={
          hasUnsavedChanges
            ? 'Save Changes to Config'
            : 'Save to Config'
        }
        disabled={isLoading || !!error}
        color={hasUnsavedChanges ? 'primary' : 'default'}
      >
        {isLoading ? <CircularProgress size={20} /> : <SaveIcon />}
      </IconButton>

      {/* Discard Changes Button */}
      <IconButton
        onClick={onDiscardChanges}
        size="small"
        title={hasUnsavedChanges ? 'Discard Unsaved Changes' : 'Discard Changes'}
        color={hasUnsavedChanges ? 'warning' : 'default'}
        disabled={isLoading || !!error}
      >
        <CancelIcon />
      </IconButton>
    </Box>
  );
};

export default NavigationEditorActionButtons;
