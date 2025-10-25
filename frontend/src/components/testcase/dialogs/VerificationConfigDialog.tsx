import CloseIcon from '@mui/icons-material/Close';
import React, { useState, useMemo } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  IconButton,
} from '@mui/material';
import { VerificationBlockData } from '../../../types/testcase/TestCase_Types';
import { VerificationsList } from '../../verification/VerificationsList';
import { getZIndex } from '../../../utils/zIndexUtils';
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
  const { availableVerifications } = useTestCaseBuilder();
  
  // Store single verification in an array for VerificationsList component
  const [verifications, setVerifications] = useState<any[]>([
    initialData || { command: '', params: {} }
  ]);

  // Transform availableVerifications array to the format expected by VerificationsList
  const availableVerificationsFormatted = useMemo(() => {
    const formatted: Record<string, any[]> = {};
    
    availableVerifications.forEach((verification: any) => {
      const category = verification.category || 'General';
      if (!formatted[category]) {
        formatted[category] = [];
      }
      formatted[category].push(verification);
    });
    
    return formatted;
  }, [availableVerifications]);

  const handleSave = () => {
    // Save the first (and only) verification
    if (verifications.length > 0 && verifications[0].command) {
      onSave(verifications[0]);
    }
  };

  const isValid = verifications.length > 0 && Boolean(verifications[0].command);

  return (
    <Dialog 
      open={open} 
      onClose={onCancel} 
      maxWidth="md" 
      fullWidth
      sx={{ zIndex: getZIndex('NAVIGATION_DIALOGS') }}
      PaperProps={{
        sx: {
          border: 2,
          borderColor: 'divider',
        }
      }}
    >
      <DialogTitle sx={{ borderBottom: 1, borderColor: 'divider', pb: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h6">Configure Verification</Typography>
          <IconButton onClick={onCancel} size="small">
            <CloseIcon />
          </IconButton>
        </Box>
      </DialogTitle>

      <DialogContent sx={{ py: 0.5 }}>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
          Edit the verification parameters
        </Typography>

        {/* Reuse VerificationsList component from Navigation Editor */}
        <Box
          sx={{
            border: '1px solid',
            borderColor: 'divider',
            borderRadius: 1,
            p: 1,
          }}
        >
          <VerificationsList
            verifications={verifications}
            availableVerifications={availableVerificationsFormatted}
            onVerificationsChange={setVerifications}
            loading={false}
            model="android_mobile"
            selectedHost={undefined}
            testResults={[]}
            onReferenceSelected={() => {}}
            modelReferences={{}}
            referencesLoading={false}
            showCollapsible={false}
            title=""
            onTest={undefined}
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
    </Dialog>
  );
};
