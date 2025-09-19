import { Close as CloseIcon } from '@mui/icons-material';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Button,
  Box,
  Typography,
  IconButton,
  LinearProgress,
} from '@mui/material';
import React from 'react';

import { useNodeEdit } from '../../hooks/navigation/useNodeEdit';
import { NodeEditDialogProps } from '../../types/pages/Navigation_Types';
import { getZIndex } from '../../utils/zIndexUtils';
import { VerificationsList } from '../verification/VerificationsList';

export const NodeEditDialog: React.FC<NodeEditDialogProps> = ({
  isOpen,
  nodeForm,
  nodes,
  setNodeForm,
  onSubmit,
  onClose,
  onResetNode,
  selectedHost,
  isControlActive = false,
  model,
}) => {
  // Early return if nodeForm is null or undefined
  if (!nodeForm) {
    return null;
  }

  // Early return if this is an entry node - entry nodes should not be editable
  if ((nodeForm.type as string) === 'entry') {
    return null;
  }

  // Early return if selectedHost is invalid - don't show dialog at all
  if (!selectedHost) {
    return null;
  }

  // Use the focused node edit hook
  const nodeEdit = useNodeEdit({
    isOpen,
    nodeForm,
    setNodeForm,
    selectedHost,
    isControlActive,
  });

  const handleSave = () => {
    nodeEdit.handleSave(onSubmit);
  };

  // Get button visibility from the hook
  const { canTest } = nodeEdit.getButtonVisibility();

  // Check if there are verifications to run
  const hasVerifications = nodeEdit.verification.verifications.length > 0;

  // Helper function to format verification results similar to edge dialog
  const formatVerificationResult = (result: any) => {
    const prefix = result.success ? '✅' : '❌';
    const message = result.message || result.error || 'No details';
    return `${prefix} ${result.verification_type}: ${message}`;
  };

  return (
    <Dialog
      open={isOpen}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      sx={{ zIndex: getZIndex('NAVIGATION_DIALOGS') }}
    >
      <DialogTitle sx={{ pb: 0.5 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h6">Edit Node</Typography>
          <IconButton onClick={onClose} size="small">
            <CloseIcon />
          </IconButton>
        </Box>
      </DialogTitle>

      <DialogContent sx={{ py: 0.5 }}>
        {/* Node Name and Type in columns */}
        <Box sx={{ display: 'flex', gap: 1, mb: 1 }}>
          <TextField
            label="Node Name"
            value={nodeForm?.label || ''}
            onChange={(e) => setNodeForm({ ...nodeForm, label: e.target.value })}
            fullWidth
            required
            error={!nodeForm?.label?.trim()}
            margin="dense"
            size="small"
          />
          <FormControl fullWidth margin="dense" size="small">
            <InputLabel>Type</InputLabel>
            <Select
              value={nodeForm?.type || 'screen'}
              label="Type"
              onChange={(e) => setNodeForm({ ...nodeForm, type: e.target.value as any })}
            >
              <MenuItem value="menu">Menu</MenuItem>
              <MenuItem value="screen">Screen</MenuItem>
              <MenuItem value="action">Action</MenuItem>
            </Select>
          </FormControl>
        </Box>

        {/* Depth, Priority and Parent below in columns */}
        <Box sx={{ display: 'flex', gap: 1, mb: 1 }}>
          <TextField
            label="Depth"
            value={nodeForm?.depth || 0}
            fullWidth
            InputProps={{ readOnly: true }}
            variant="outlined"
            margin="dense"
            size="small"
          />
          <FormControl fullWidth margin="dense" size="small">
            <InputLabel>Priority</InputLabel>
            <Select
              value={nodeForm?.priority || 'p3'}
              label="Priority"
              onChange={(e) =>
                setNodeForm({ ...nodeForm, priority: e.target.value as 'p1' | 'p2' | 'p3' })
              }
            >
              <MenuItem value="p1">P1 Critical</MenuItem>
              <MenuItem value="p2">P2 Major</MenuItem>
              <MenuItem value="p3">P3 Minor</MenuItem>
            </Select>
          </FormControl>
          <TextField
            label="Parent"
            value={nodeEdit.getParentNames(nodeForm?.parent || [], nodes)}
            fullWidth
            InputProps={{ readOnly: true }}
            variant="outlined"
            margin="dense"
            size="small"
          />
        </Box>

        {/* Single line description */}
        <TextField
          label="Description"
          value={nodeForm?.description || ''}
          onChange={(e) => setNodeForm({ ...nodeForm, description: e.target.value })}
          fullWidth
          margin="dense"
          size="small"
          sx={{ mb: 1 }}
        />

        {/* Screenshot URL Field - only show for non-entry nodes */}
        {(nodeForm?.type as string) !== 'entry' && (
          <TextField
            label="Screenshot URL"
            value={nodeForm?.screenshot || ''}
            onChange={(e) => setNodeForm({ ...nodeForm, screenshot: e.target.value })}
            fullWidth
            margin="dense"
            size="small"
            sx={{ mb: 1 }}
          />
        )}

        {/* Show linear progress when verification test is running */}
        {nodeEdit.verification.loading && (
          <Box sx={{ mt: 1, mb: 1 }}>
            <LinearProgress sx={{ borderRadius: 1 }} />
          </Box>
        )}

        {/* Verification Section */}
        <VerificationsList
          verifications={nodeEdit.verification.verifications}
          availableVerifications={nodeEdit.verification.availableVerificationTypes}
          onVerificationsChange={nodeEdit.handleVerificationsChange}
          loading={nodeEdit.verification.loading}
          model={nodeEdit.deviceModel || model || 'android_mobile'}
          selectedHost={selectedHost}
          testResults={[]} // Don't show individual results, only show consolidated results below
          onReferenceSelected={() => {}}
          modelReferences={nodeEdit.modelReferences}
          referencesLoading={nodeEdit.referencesLoading}
          showCollapsible={false}
          title="Verifications"
          onTest={nodeEdit.verification.handleTest}
        />


        {/* Verification Test Results - updated to match edge dialog style */}
        {nodeEdit.verification.testResults && nodeEdit.verification.testResults.length > 0 && (
          <Box
            sx={{
              p: 1,
              bgcolor: nodeEdit.verification.testResults.every((r: any) => r.success)
                ? 'success.light'
                : 'error.light',
              borderRadius: 1,
              maxHeight: 200,
              overflow: 'auto',
              mt: 1,
              border: '1px solid rgba(0, 0, 0, 0.12)',
            }}
          >
            <Typography variant="subtitle2" sx={{ mb: 0.5 }}>
              Verification Results:
              {nodeEdit.verification.testResults.every((r: any) => r.success) && (
                <span style={{ marginLeft: '8px', color: 'green' }}>
                  ✅
                </span>
              )}
            </Typography>
            <Typography
              variant="caption"
              sx={{
                fontFamily: 'monospace',
                whiteSpace: 'pre-line',
                fontSize: '0.7rem',
                lineHeight: 1.2,
              }}
            >
              {nodeEdit.verification.testResults.map(formatVerificationResult).join('\n')}
            </Typography>
          </Box>
        )}
      </DialogContent>

      <DialogActions sx={{ pt: 0.5, display: 'flex', gap: 1 }}>
        {onResetNode && (
          <Button onClick={() => onResetNode()} variant="outlined" color="warning">
            Reset Node
          </Button>
        )}
        <Button onClick={handleSave} variant="contained" disabled={!nodeEdit.isFormValid(nodeForm)}>
          {nodeEdit.saveSuccess ? '✓' : 'Save'}
        </Button>
        {/* Run button - positioned right after Save button, same as EdgeEditDialog */}
        {hasVerifications && (
          <Button
            onClick={nodeEdit.verification.handleTest}
            variant="contained"
            disabled={!canTest}
          >
            {nodeEdit.verification.loading ? 'Running...' : 'Run'}
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
};
