import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Box,
  Typography,
} from '@mui/material';
import { LoopBlockData, LoopForm } from '../../../types/testcase/TestCase_Types';

interface LoopConfigDialogProps {
  open: boolean;
  initialData?: LoopBlockData;
  onSave: (data: LoopBlockData) => void;
  onCancel: () => void;
}

export const LoopConfigDialog: React.FC<LoopConfigDialogProps> = ({
  open,
  initialData,
  onSave,
  onCancel,
}) => {
  const [formData, setFormData] = useState<LoopForm>({
    iterations: initialData?.iterations || 1,
    nested_graph: initialData?.nested_graph,
    isValid: false,
  });

  useEffect(() => {
    // Validate form
    const isValid = formData.iterations > 0;
    setFormData((prev) => ({ ...prev, isValid }));
  }, [formData.iterations]);

  const handleSave = () => {
    const { isValid, ...dataToSave } = formData;
    onSave(dataToSave);
  };

  return (
    <Dialog open={open} onClose={onCancel} maxWidth="sm" fullWidth>
      <DialogTitle>Configure Loop Block</DialogTitle>
      <DialogContent>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
          <Typography variant="body2" color="text.secondary">
            Set the number of times to repeat the loop
          </Typography>

          <TextField
            label="Iterations"
            type="number"
            value={formData.iterations}
            onChange={(e) => setFormData((prev) => ({ ...prev, iterations: parseInt(e.target.value) || 1 }))}
            inputProps={{ min: 1, max: 100 }}
            fullWidth
            helperText="Number of times to execute the loop (1-100)"
          />

          <Box
            sx={{
              p: 2,
              border: '1px dashed',
              borderColor: 'divider',
              borderRadius: 1,
              textAlign: 'center',
            }}
          >
            <Typography variant="body2" color="text.secondary">
              Double-click the loop block to add actions inside
            </Typography>
          </Box>
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onCancel}>Cancel</Button>
        <Button onClick={handleSave} variant="contained" disabled={!formData.isValid}>
          Save
        </Button>
      </DialogActions>
    </Dialog>
  );
};

