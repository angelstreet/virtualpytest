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
  Box,
  Typography,
  CircularProgress,
} from '@mui/material';
import { NavigationBlockData, NavigationForm } from '../../../types/testcase/TestCase_Types';
import { useNavigationConfig } from '../../../contexts/navigation/NavigationConfigContext';

interface NavigationConfigDialogProps {
  open: boolean;
  initialData?: NavigationBlockData;
  onSave: (data: NavigationBlockData) => void;
  onCancel: () => void;
}

export const NavigationConfigDialog: React.FC<NavigationConfigDialogProps> = ({
  open,
  initialData,
  onSave,
  onCancel,
}) => {
  const { treeData } = useNavigationConfig();
  const [formData, setFormData] = useState<NavigationForm>({
    target_node_label: initialData?.target_node_label || '',
    target_node_id: initialData?.target_node_id || '',
    isValid: false,
  });

  // Get available nodes from tree data
  const availableNodes = treeData?.nodes || [];
  const isLoading = !treeData;

  useEffect(() => {
    // Validate form
    const isValid = Boolean(formData.target_node_label);
    setFormData((prev) => ({ ...prev, isValid }));
  }, [formData.target_node_label]);

  const handleNodeChange = (nodeId: string) => {
    const selectedNode = availableNodes.find((node) => node.node_id === nodeId);
    setFormData((prev) => ({
      ...prev,
      target_node_id: nodeId,
      target_node_label: selectedNode?.label || selectedNode?.node_name || nodeId,
    }));
  };

  const handleSave = () => {
    const { isValid, ...dataToSave } = formData;
    onSave(dataToSave);
  };

  return (
    <Dialog open={open} onClose={onCancel} maxWidth="sm" fullWidth>
      <DialogTitle>Configure Navigation Block</DialogTitle>
      <DialogContent>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
          <Typography variant="body2" color="text.secondary">
            Select the destination node for navigation
          </Typography>

          {isLoading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
              <CircularProgress size={24} />
            </Box>
          ) : (
            <FormControl fullWidth>
              <InputLabel>Target Node</InputLabel>
              <Select
                value={formData.target_node_id}
                label="Target Node"
                onChange={(e) => handleNodeChange(e.target.value)}
              >
                {availableNodes.map((node) => (
                  <MenuItem key={node.node_id} value={node.node_id}>
                    {node.label || node.node_name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          )}
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onCancel}>Cancel</Button>
        <Button onClick={handleSave} variant="contained" disabled={!formData.isValid || isLoading}>
          Save
        </Button>
      </DialogActions>
    </Dialog>
  );
};

