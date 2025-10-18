import CloseIcon from '@mui/icons-material/Close';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  Box,
  Typography,
  IconButton,
  CircularProgress,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  LinearProgress,
} from '@mui/material';
import React, { useState } from 'react';

import { useEdgeEdit } from '../../hooks/navigation/useEdgeEdit';
import { useEdge } from '../../hooks/navigation/useEdge';
import { Host } from '../../types/common/Host_Types';
import { UINavigationEdge, EdgeForm } from '../../types/pages/Navigation_Types';
import { getZIndex } from '../../utils/zIndexUtils';
import { ActionsList } from '../actions';
import { ActionDependencyDialog } from '../actions/ActionDependencyDialog';

interface EdgeEditDialogProps {
  isOpen: boolean;
  edgeForm: EdgeForm | null;
  setEdgeForm: React.Dispatch<React.SetStateAction<EdgeForm | null>>;
  onSubmit: (formData: any) => void;
  onClose: () => void;
  selectedEdge?: UINavigationEdge | null;
  isControlActive?: boolean;
  selectedHost?: Host | null;
  selectedDeviceId?: string | null;
  fromLabel?: string;
  toLabel?: string;
}

export const EdgeEditDialog: React.FC<EdgeEditDialogProps> = ({
  isOpen,
  edgeForm,
  setEdgeForm,
  onSubmit,
  onClose,
  selectedEdge: _selectedEdge,
  isControlActive = false,
  selectedHost,
  selectedDeviceId,
  fromLabel = '',
  toLabel = '',
}) => {
  // State for dependency dialog
  const [dependencyDialogOpen, setDependencyDialogOpen] = useState(false);
  const [dependencyEdges, setDependencyEdges] = useState<any[]>([]);
  const [pendingSubmit, setPendingSubmit] = useState<any>(null);
  const [isCheckingDependencies, setIsCheckingDependencies] = useState(false);

  const edgeEdit = useEdgeEdit({
    isOpen,
    edgeForm,
    setEdgeForm,
    selectedEdge: _selectedEdge,
    selectedHost,
    isControlActive,
  });

  // Add the same edge hook used by the Edge Selection Panel
  const edgeHook = useEdge({
    selectedHost: selectedHost || null,
    selectedDeviceId: selectedDeviceId || null,
    isControlActive,
  });

      // Check if form has actions - same logic as EdgeSelectionPanel
    const hasActions = (edgeForm?.action_sets?.length || 0) > 0;
    
    // Simply check if actions can be run based on control being active, host being available, and actions existing
    const canRunActions = isControlActive && !!selectedHost && hasActions && !edgeHook.actionHook.loading;

  // Enhanced submit handler with dependency checking
  const handleSubmitWithDependencyCheck = async () => {
    if (!edgeEdit.isFormValid()) return;

    // Check for existing actions that might have dependencies
    const allActions = [...edgeEdit.localActions, ...edgeEdit.localRetryActions];

    setIsCheckingDependencies(true);
    try {
      // Use the new checkDependencies function from the hook
      const result = await edgeEdit.checkDependencies(allActions);

      if (result.success && result.has_shared_actions) {
        // Show dependency dialog
        setDependencyEdges(result.edges);
        setPendingSubmit(edgeForm);
        setDependencyDialogOpen(true);
      } else if (result.success && !result.has_shared_actions) {
        // No dependencies found, proceed with saving
        onSubmit(edgeForm);
      } else {
        // Handle other cases (like API errors)
        console.warn('Unexpected dependency check result:', result);
        onSubmit(edgeForm);
      }
    } catch (error) {
      console.warn('Failed to check dependencies for actions:', error);
      // Continue with save if dependency check fails
      onSubmit(edgeForm);
    } finally {
      setIsCheckingDependencies(false);
    }
  };

  const handleDependencyConfirm = () => {
    setDependencyDialogOpen(false);
    if (pendingSubmit) {
      onSubmit(pendingSubmit);
    }
    setPendingSubmit(null);
    setDependencyEdges([]);
  };

  const handleDependencyCancel = () => {
    setDependencyDialogOpen(false);
    setPendingSubmit(null);
    setDependencyEdges([]);
  };

  const handleRunActions = async () => {
    // Use the actual selected edge if available, otherwise create minimal edge structure
    if (!edgeForm) return;
    
    // Prefer using the actual selected edge to preserve source/target metadata
    const edgeToExecute: UINavigationEdge = _selectedEdge || {
      id: edgeForm.edgeId,
      source: 'unknown',
      target: 'unknown',
      type: 'navigation',
      data: {
        action_sets: [],
        default_action_set_id: '',
        final_wait_time: edgeForm.final_wait_time
      }
    } as UINavigationEdge;
    
    // Execute with local (unsaved) actions as overrides
    await edgeHook.executeEdgeActions(
      edgeToExecute,
      edgeEdit.localActions,
      edgeEdit.localRetryActions,
      edgeEdit.localFailureActions
    );
  };

  if (!edgeForm) return null;

  return (
    <>
      <Dialog
        open={isOpen}
        onClose={onClose}
        maxWidth="md"
        fullWidth
        sx={{ zIndex: getZIndex('NAVIGATION_DIALOGS') }}
      >
        <DialogTitle sx={{ pb: 0.5 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Typography variant="h6">Edit Edge</Typography>
              {fromLabel && toLabel && (
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Typography
                    variant="body2"
                    sx={{ fontSize: '0.8rem', fontWeight: 'bold', color: '#1976d2' }}
                  >
                    {fromLabel}
                  </Typography>
                  <Typography variant="body1" sx={{ fontSize: '1rem' }}>
                    →
                  </Typography>
                  <Typography
                    variant="body2"
                    sx={{ fontSize: '0.8rem', fontWeight: 'bold', color: '#4caf50' }}
                  >
                    {toLabel}
                  </Typography>
                </Box>
              )}
            </Box>
            <IconButton onClick={onClose} size="small">
              <CloseIcon />
            </IconButton>
          </Box>
        </DialogTitle>

        <DialogContent sx={{ py: 0.5 }}>
          {/* Priority and Threshold */}
          <Box sx={{ display: 'flex', gap: 1, mb: 1 }}>
            <FormControl fullWidth margin="dense" size="small">
              <InputLabel>Priority</InputLabel>
              <Select
                value={edgeForm?.priority || 'p3'}
                label="Priority"
                onChange={(e) =>
                  setEdgeForm({ ...edgeForm, priority: e.target.value as 'p1' | 'p2' | 'p3' })
                }
              >
                <MenuItem value="p1">P1 Critical</MenuItem>
                <MenuItem value="p2">P2 Major</MenuItem>
                <MenuItem value="p3">P3 Minor</MenuItem>
              </Select>
            </FormControl>
            <TextField
              label="Threshold (ms)"
              type="number"
              value={edgeForm?.threshold ?? 0}
              onChange={(e) => {
                const value = parseInt(e.target.value);
                setEdgeForm({
                  ...edgeForm,
                  threshold: isNaN(value) ? 0 : value,
                });
              }}
              fullWidth
              margin="dense"
              size="small"
              inputProps={{ step: 100, min: 0 }}
            />
          </Box>

          {/* Main Actions */}
          <Box
            sx={{
              border: '1px solid',
              borderColor: 'divider',
              borderRadius: 1,
              p: 1,
              mb: 1,
            }}
          >
            <Box
              sx={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                mb: 0.5,
              }}
            >
              <Typography variant="h6" sx={{ fontSize: '1rem', m: 0 }}>
                Main Actions
              </Typography>
              <Button
                variant="outlined"
                size="small"
                onClick={() => {
                  const newAction: any = {
                    command: '',
                    params: {
                      wait_time: 500
                    },
                  };
                  edgeEdit.handleActionsChange([...edgeEdit.localActions, newAction]);
                }}
                sx={{ fontSize: '0.75rem', px: 1, py: 0.25 }}
              >
                + Add
              </Button>
            </Box>
            {edgeEdit.localActions.length > 0 ? (
              <ActionsList
                actions={edgeEdit.localActions}
                onActionsUpdate={edgeEdit.handleActionsChange}
              />
            ) : (
              <Typography
                variant="body2"
                color="text.secondary"
                sx={{ fontStyle: 'italic', textAlign: 'center', py: 0.5 }}
              >
                No actions found
              </Typography>
            )}
          </Box>

          {/* Retry Actions */}
          <Box
            sx={{
              border: '1px solid',
              borderColor: 'divider',
              borderRadius: 1,
              p: 1,
              mb: 1,
            }}
          >
            <Box
              sx={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                mb: 0.5,
              }}
            >
              <Typography variant="h6" sx={{ fontSize: '1rem', m: 0 }}>
                Retry Actions
              </Typography>
              <Button
                variant="outlined"
                size="small"
                onClick={() => {
                  const newAction: any = {
                    command: '',
                    params: {
                      wait_time: 500
                    },
                  };
                  edgeEdit.handleRetryActionsChange([...edgeEdit.localRetryActions, newAction]);
                }}
                sx={{ fontSize: '0.75rem', px: 1, py: 0.25 }}
              >
                + Add
              </Button>
            </Box>
            {edgeEdit.localRetryActions.length > 0 ? (
              <ActionsList
                actions={edgeEdit.localRetryActions}
                onActionsUpdate={edgeEdit.handleRetryActionsChange}
              />
            ) : (
              <Typography
                variant="body2"
                color="text.secondary"
                sx={{ fontStyle: 'italic', textAlign: 'center', py: 0.5 }}
              >
                No retry actions found
              </Typography>
            )}
          </Box>

          {/* Failure Actions */}
          <Box
            sx={{
              border: '1px solid',
              borderColor: 'divider',
              borderRadius: 1,
              p: 1,
              mb: 1,
            }}
          >
            <Box
              sx={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                mb: 0.5,
              }}
            >
              <Typography variant="h6" sx={{ fontSize: '1rem', m: 0 }}>
                Failure Actions
              </Typography>
              <Button
                variant="outlined"
                size="small"
                onClick={() => {
                  const newAction: any = {
                    command: '',
                    params: {
                      wait_time: 500
                    },
                  };
                  edgeEdit.handleFailureActionsChange([...edgeEdit.localFailureActions, newAction]);
                }}
                sx={{ fontSize: '0.75rem', px: 1, py: 0.25 }}
              >
                + Add
              </Button>
            </Box>
            {edgeEdit.localFailureActions.length > 0 ? (
              <ActionsList
                actions={edgeEdit.localFailureActions}
                onActionsUpdate={edgeEdit.handleFailureActionsChange}
              />
            ) : (
              <Typography
                variant="body2"
                color="text.secondary"
                sx={{ fontStyle: 'italic', textAlign: 'center', py: 0.5 }}
              >
                No failure actions found
              </Typography>
            )}
          </Box>

          {/* Linear Progress - shown when running */}
          {edgeHook.actionHook.loading && (
            <Box sx={{ mt: 1 }}>
              <LinearProgress sx={{ borderRadius: 1 }} />
            </Box>
          )}

          {/* Action Result Display - same as Edge Selection Panel */}
          {edgeHook.runResult && (
            <Box
              sx={{
                mt: 1,
                p: 1,
                bgcolor: edgeHook.runResult.includes('❌ FAILED')
                  ? 'error.light'
                  : edgeHook.runResult.includes('✅ SUCCESS')
                    ? 'success.light'
                    : edgeHook.runResult.includes('❌') && !edgeHook.runResult.includes('✅')
                      ? 'error.light'
                      : edgeHook.runResult.includes('⚠️')
                        ? 'warning.light'
                        : 'success.light',
                borderRadius: 1,
                maxHeight: '200px', // Slightly taller in dialog
                overflow: 'auto',
                border: '1px solid rgba(0, 0, 0, 0.12)',
              }}
            >
              <Typography variant="subtitle2" sx={{ mb: 0.5 }}>
                Action Result:
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
                {edgeHook.formatRunResult(edgeHook.runResult)}
              </Typography>
            </Box>
          )}
        </DialogContent>

        <DialogActions sx={{ pt: 0.5 }}>
          <Button
            onClick={handleSubmitWithDependencyCheck}
            variant="contained"
            disabled={!edgeEdit.isFormValid() || isCheckingDependencies}
            startIcon={isCheckingDependencies ? <CircularProgress size={16} /> : null}
          >
            {isCheckingDependencies ? 'Checking...' : 'Save'}
          </Button>
          {/* Run button - only shown when actions exist, same as EdgeSelectionPanel */}
          {hasActions && (
            <Button
              onClick={handleRunActions}
              variant="contained"
              disabled={!canRunActions}
            >
              {edgeHook.actionHook.loading ? 'Running...' : 'Run'}
            </Button>
          )}
        </DialogActions>
      </Dialog>

      {/* Dependency Warning Dialog */}
      <ActionDependencyDialog
        isOpen={dependencyDialogOpen}
        edges={dependencyEdges}
        onConfirm={handleDependencyConfirm}
        onCancel={handleDependencyCancel}
      />
    </>
  );
};
