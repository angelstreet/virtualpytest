import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Box,
  Typography,
  CircularProgress,
} from '@mui/material';
import { ActionBlockData, ActionForm } from '../../../types/testcase/TestCase_Types';
import { useTestCaseBuilder } from '../../../contexts/testcase/TestCaseBuilderContext';

interface ActionConfigDialogProps {
  open: boolean;
  initialData?: ActionBlockData;
  onSave: (data: ActionBlockData) => void;
  onCancel: () => void;
}

export const ActionConfigDialog: React.FC<ActionConfigDialogProps> = ({
  open,
  initialData,
  onSave,
  onCancel,
}) => {
  const { availableActions, isLoadingOptions } = useTestCaseBuilder();
  const [formData, setFormData] = useState<ActionForm>({
    command: initialData?.command || '',
    params: initialData?.params || {},
    is Valid: false,
  });

  useEffect(() => {
    // Validate form
    const isValid = Boolean(formData.command);
    setFormData((prev) => ({ ...prev, isValid }));
  }, [formData.command]);

  const handleCommandChange = (command: string) => {
    const selectedAction = availableActions.find((action) => action.command === command);
    setFormData((prev) => ({
      ...prev,
      command,
      params: selectedAction?.params || {},
    }));
  };

  const handleSave = () => {
    const { isValid, ...dataToSave } = formData;
    onSave(dataToSave);
  };

  return (
    <Dialog open={open} onClose={onCancel} maxWidth="sm" fullWidth>
      <DialogTitle>Configure Action Block</DialogTitle>
      <DialogContent>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
          <Typography variant="body2" color="text.secondary">
            Select the action command to execute
          </Typography>

          {isLoadingOptions ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
              <CircularProgress size={24} />
            </Box>
          ) : (
            <>
              <FormControl fullWidth>
                <InputLabel>Command</InputLabel>
                <Select
                  value={formData.command}
                  label="Command"
                  onChange={(e) => handleCommandChange(e.target.value)}
                >
                  {availableActions.map((action) => (
                    <MenuItem key={action.command} value={action.command}>
                      {action.description || action.command}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              {formData.command === 'click_element' && (
                <TextField
                  label="Element ID"
                  value={formData.params?.element_id || ''}
                  onChange={(e) =>
                    setFormData((prev) => ({
                      ...prev,
                      params: { ...prev.params, element_id: e.target.value },
                    }))
                  }
                  fullWidth
                />
              )}

              {formData.command === 'send_text' && (
                <TextField
                  label="Text"
                  value={formData.params?.text || ''}
                  onChange={(e) =>
                    setFormData((prev) => ({
                      ...prev,
                      params: { ...prev.params, text: e.target.value },
                    }))
                  }
                  fullWidth
                  multiline
                  rows={3}
                />
              )}

              {formData.command === 'wait' && (
                <TextField
                  label="Duration (seconds)"
                  type="number"
                  value={formData.params?.seconds || 1}
                  onChange={(e) =>
                    setFormData((prev) => ({
                      ...prev,
                      params: { ...prev.params, seconds: parseInt(e.target.value) },
                    }))
                  }
                  fullWidth
                />
              )}
            </>
          )}
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onCancel}>Cancel</Button>
        <Button onClick={handleSave} variant="contained" disabled={!formData.isValid || isLoadingOptions}>
          Save
        </Button>
      </DialogActions>
    </Dialog>
  );
};
