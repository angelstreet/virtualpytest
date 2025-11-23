import CloseIcon from '@mui/icons-material/Close';
import React, { useState } from 'react';
import {
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  IconButton,
} from '@mui/material';
import { ActionBlockData } from '../../../types/testcase/TestCase_Types';
import { ActionsList } from '../../actions';
import { getZIndex } from '../../../utils/zIndexUtils';
import { StyledDialog } from '../../common/StyledDialog';

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
  // Store single action in an array for ActionsList component
  const [actions, setActions] = useState<any[]>([
    initialData || { command: '', params: { wait_time: 500 } }
  ]);

  const handleSave = () => {
    // Save the first (and only) action
    if (actions.length > 0 && actions[0].command) {
      onSave(actions[0]);
    }
  };

  const isValid = actions.length > 0 && Boolean(actions[0].command);

  return (
    <StyledDialog 
      open={open} 
      onClose={onCancel} 
      maxWidth="md" 
      fullWidth
      sx={{ zIndex: getZIndex('NAVIGATION_DIALOGS') }}
    >
      <DialogTitle sx={{ borderBottom: 1, borderColor: 'divider', pb: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h6">Configure Action</Typography>
          <IconButton onClick={onCancel} size="small">
            <CloseIcon />
          </IconButton>
        </Box>
      </DialogTitle>

      <DialogContent sx={{ py: 0.5 }}>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
          Edit the action parameters
        </Typography>

        {/* Reuse ActionsList component from Navigation Editor */}
        <Box
          sx={{
            border: '1px solid',
            borderColor: 'divider',
            borderRadius: 1,
            p: 1,
          }}
        >
          <ActionsList
            actions={actions}
            onActionsUpdate={setActions}
          />
        </Box>
      </DialogContent>

      <DialogActions sx={{ borderTop: 1, borderColor: 'divider', pt: 2, pb: 2, px: 3 }}>
        <Button onClick={onCancel} variant="outlined">
          Cancel
        </Button>
        <Button onClick={handleSave} variant="contained" disabled={!isValid}>
          Save
        </Button>
      </DialogActions>
    </StyledDialog>
  );
};
