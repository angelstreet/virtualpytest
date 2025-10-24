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
import { VerificationBlockData, VerificationForm } from '../../../types/testcase/TestCase_Types';
import { useTestCaseBuilder } from '../../../contexts/testcase/TestCaseBuilderContext';

interface VerificationConfigDialogProps {
  open: boolean;
  initialData?: VerificationBlockData;
  onSave: (data: VerificationBlockData) => void;
  onCancel: () => void;
}

export const VerificationConfigDialog: React.FC<VerificationConfigDialogProps> = ({
  open,
  initialData,
  onSave,
  onCancel,
}) => {
  const { availableVerifications, isLoadingOptions } = useTestCaseBuilder();
  const [formData, setFormData] = useState<VerificationForm>({
    verification_type: initialData?.verification_type || '',
    reference: initialData?.reference || '',
    threshold: initialData?.threshold || 0.8,
    isValid: false,
  });

  useEffect(() => {
    // Validate form
    const isValid = Boolean(formData.verification_type);
    setFormData((prev) => ({ ...prev, isValid }));
  }, [formData.verification_type]);

  const handleTypeChange = (type: string) => {
    setFormData((prev) => ({
      ...prev,
      verification_type: type,
    }));
  };

  const handleSave = () => {
    const { isValid, ...dataToSave } = formData;
    onSave(dataToSave);
  };

  return (
    <Dialog open={open} onClose={onCancel} maxWidth="sm" fullWidth>
      <DialogTitle>Configure Verification Block</DialogTitle>
      <DialogContent>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
          <Typography variant="body2" color="text.secondary">
            Select the verification type to perform
          </Typography>

          {isLoadingOptions ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
              <CircularProgress size={24} />
            </Box>
          ) : (
            <>
              <FormControl fullWidth>
                <InputLabel>Verification Type</InputLabel>
                <Select
                  value={formData.verification_type}
                  label="Verification Type"
                  onChange={(e) => handleTypeChange(e.target.value)}
                >
                  {availableVerifications.map((verification) => (
                    <MenuItem key={verification.type} value={verification.type}>
                      {verification.description || verification.type}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              {(formData.verification_type === 'text' || formData.verification_type === 'image') && (
                <TextField
                  label={formData.verification_type === 'text' ? 'Text to Verify' : 'Image Reference'}
                  value={formData.reference || ''}
                  onChange={(e) =>
                    setFormData((prev) => ({
                      ...prev,
                      reference: e.target.value,
                    }))
                  }
                  fullWidth
                  required
                />
              )}

              <TextField
                label="Threshold (0-1)"
                type="number"
                inputProps={{ min: 0, max: 1, step: 0.1 }}
                value={formData.threshold}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    threshold: parseFloat(e.target.value),
                  }))
                }
                fullWidth
                helperText="Similarity threshold for verification (0 = any, 1 = exact)"
              />
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
