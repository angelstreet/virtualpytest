import CloseIcon from '@mui/icons-material/Close';
import React, { useState, useMemo } from 'react';
import {
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
import { StyledDialog } from '../../common/StyledDialog';

interface VerificationConfigDialogProps {
  open: boolean;
  initialData?: VerificationBlockData;
  onSave: (data: VerificationBlockData) => void;
  onCancel: () => void;
  // For showing output values
  mode?: 'configure' | 'viewValue';
  outputName?: string;
  outputValue?: any;
}

export const VerificationConfigDialog: React.FC<VerificationConfigDialogProps> = ({
  open,
  initialData,
  onSave,
  onCancel,
  mode = 'configure',
  outputName,
  outputValue
}) => {
  // Try to get available verifications from context (if available)
  // This allows the component to work both within and outside TestCaseBuilderProvider
  let contextData: any = null;
  try {
    contextData = useTestCaseBuilder();
  } catch (error) {
    // Context not available
    // Continue with empty array
  }
  
  const availableVerifications = contextData?.availableVerifications || [];
  
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

  // Format value for display
  const formatValue = (value: any): string => {
    if (value === null) return 'null';
    if (value === undefined) return 'undefined';
    if (typeof value === 'object') {
      return JSON.stringify(value, null, 2);
    }
    return String(value);
  };

  const hasExecutionValue = outputValue !== undefined;

  return (
    <StyledDialog 
      open={open} 
      onClose={onCancel} 
      maxWidth={mode === 'viewValue' ? 'sm' : 'md'} 
      fullWidth
      sx={{ zIndex: getZIndex('NAVIGATION_DIALOGS') }}
    >
      <DialogTitle sx={{ borderBottom: 1, borderColor: 'divider', pb: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h6">
            {mode === 'viewValue' ? (outputName || 'Output Value') : 'Configure Verification'}
          </Typography>
          <IconButton onClick={onCancel} size="small">
            <CloseIcon />
          </IconButton>
        </Box>
      </DialogTitle>

      <DialogContent sx={{ py: mode === 'viewValue' ? 3 : 0.5 }}>
        {mode === 'viewValue' ? (
          // Show output value
          <>
            {hasExecutionValue ? (
              <Box>
                <Typography variant="caption" sx={{ color: 'text.secondary', mb: 1, display: 'block' }}>
                  VALUE
                </Typography>
                <Box
                  sx={{
                    bgcolor: 'rgba(16, 185, 129, 0.1)',
                    border: '1px solid rgba(16, 185, 129, 0.3)',
                    borderRadius: 1,
                    p: 2,
                    fontFamily: 'monospace',
                    fontSize: '0.9rem',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-all',
                    maxHeight: '400px',
                    overflowY: 'auto'
                  }}
                >
                  {formatValue(outputValue)}
                </Box>
              </Box>
            ) : (
              <Box
                sx={{
                  bgcolor: 'rgba(239, 68, 68, 0.1)',
                  border: '1px solid rgba(239, 68, 68, 0.3)',
                  borderRadius: 1,
                  p: 2,
                  textAlign: 'center'
                }}
              >
                <Typography variant="body2" color="text.secondary">
                  No value yet. Run the test case to see the output value.
                </Typography>
              </Box>
            )}
          </>
        ) : (
          // Show verification config
          <>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              Edit the verification parameters
            </Typography>

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
          </>
        )}
      </DialogContent>

      <DialogActions sx={{ borderTop: 1, borderColor: 'divider', pt: 2, pb: 2, px: 3 }}>
        {mode === 'viewValue' ? (
          <Button onClick={onCancel} variant="contained">
            Close
          </Button>
        ) : (
          <>
            <Button onClick={onCancel} variant="outlined">
              Cancel
            </Button>
            <Button onClick={handleSave} variant="contained" disabled={!isValid}>
              Save
            </Button>
          </>
        )}
      </DialogActions>
    </StyledDialog>
  );
};
