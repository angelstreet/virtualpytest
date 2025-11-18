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
  Checkbox,
  FormControlLabel,
} from '@mui/material';
import React, { useState, useMemo } from 'react';

import { useEdgeEdit } from '../../hooks/navigation/useEdgeEdit';
import { useEdge } from '../../hooks/navigation/useEdge';
import { Host } from '../../types/common/Host_Types';
import { UINavigationEdge, EdgeForm } from '../../types/pages/Navigation_Types';
import { getZIndex } from '../../utils/zIndexUtils';
import { ActionsList } from '../actions';
import { ActionDependencyDialog } from '../actions/ActionDependencyDialog';
import { VerificationsList } from '../verification/VerificationsList';

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
  model?: string; // Device model for verifications
}

export const EdgeEditDialog: React.FC<EdgeEditDialogProps> = ({
  isOpen,
  edgeForm,
  setEdgeForm,
  onSubmit: _onSubmit,
  onClose,
  selectedEdge: _selectedEdge,
  isControlActive = false,
  selectedHost,
  selectedDeviceId,
  fromLabel = '',
  toLabel = '',
  model = 'android_mobile',
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

  // Filter available verifications for KPI - only show wait functions (same as NodeEditDialog)
  const kpiAvailableVerifications = useMemo(() => {
    const allowedKpiCommands = [
      'waitForImageToAppear',
      'waitForImageToDisappear',
      'waitForTextToAppear',
      'waitForTextToDisappear'
    ];

    const filtered: Record<string, any> = {};

    // Get verifications from edgeEdit verification hook
    const availableTypes = edgeEdit.verification?.availableVerificationTypes || {};

    Object.entries(availableTypes).forEach(([category, verifications]) => {
      if (Array.isArray(verifications)) {
        const filteredVerifications = verifications.filter((v: any) => 
          allowedKpiCommands.includes(v.command)
        );
        
        if (filteredVerifications.length > 0) {
          filtered[category] = filteredVerifications;
        }
      }
    });

    return filtered;
  }, [edgeEdit.verification]);

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
        // No dependencies found, proceed with saving (self-contained)
        await edgeEdit.handleSave();
        onClose();
      } else {
        // Handle other cases (like API errors)
        console.warn('Unexpected dependency check result:', result);
        await edgeEdit.handleSave();
        onClose();
      }
    } catch (error) {
      console.warn('Failed to check dependencies for actions:', error);
      // Continue with save if dependency check fails
      await edgeEdit.handleSave();
      onClose();
    } finally {
      setIsCheckingDependencies(false);
    }
  };

  const handleDependencyConfirm = async () => {
    setDependencyDialogOpen(false);
    if (pendingSubmit) {
      await edgeEdit.handleSave();
      onClose();
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
    // Use the actual selected edge if available, otherwise create edge structure from form data
    if (!edgeForm) return;
    
    // Prefer using the actual selected edge to preserve source/target metadata
    const edgeToExecute: UINavigationEdge = _selectedEdge || {
      id: edgeForm.edgeId,
      source: 'unknown',
      target: 'unknown',
      type: 'navigation',
      data: {
        action_sets: edgeForm.action_sets,  // Use form data, not empty array
        default_action_set_id: edgeForm.default_action_set_id,  // Use form data, not empty string
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
              {/* 🔗 Conditional Edge Indicator */}
              {_selectedEdge?.data?.is_conditional && (
                <Box
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 0.5,
                    px: 1,
                    py: 0.3,
                    borderRadius: 1,
                    backgroundColor: '#fff3e0',
                    border: '1px solid #ff9800',
                  }}
                >
                  <Typography
                    variant="caption"
                    sx={{
                      fontSize: '0.7rem',
                      fontWeight: 'bold',
                      color: '#ff9800',
                    }}
                  >
                    🔗 CONDITIONAL
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
              autoComplete="off"
              inputProps={{ step: 100, min: 0 }}
            />
          </Box>

          {/* Sibling Shortcuts Checkbox */}
          <Box sx={{ mb: 1 }}>
            <FormControlLabel
              control={
                <Checkbox
                  checked={edgeForm?.enable_sibling_shortcuts ?? false}
                  onChange={(e) =>
                    setEdgeForm({
                      ...edgeForm,
                      enable_sibling_shortcuts: e.target.checked,
                    })
                  }
                  size="small"
                />
              }
              label={
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                  <Typography variant="body2" sx={{ fontSize: '0.875rem' }}>
                    Enable sibling shortcuts
                  </Typography>
                  <Typography variant="caption" sx={{ fontSize: '0.75rem', color: 'text.secondary', fontStyle: 'italic' }}>
                    (web/mobile: allow direct navigation between sibling nodes)
                  </Typography>
                </Box>
              }
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

          {/* KPI Measurement Section - Only for current action_set */}
          {edgeForm?.action_sets && (() => {
            // Get the current action_set based on direction
            const direction = edgeForm.direction || 'forward';
            const actionSetIndex = edgeForm.action_sets.length === 1 ? 0 : (direction === 'forward' ? 0 : 1);
            const actionSet = edgeForm.action_sets[actionSetIndex];
            
            if (!actionSet) return null;
            
            return (
              <Box
                sx={{
                  border: '1px solid',
                  borderColor: 'divider',
                  borderRadius: 1,
                  p: 1,
                  mb: 1,
                }}
              >
                {/* Title and Checkbox on same line */}
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 0.5 }}>
                  <Typography variant="h6" sx={{ fontSize: '1rem', m: 0 }}>
                    📊 KPI Measurement - {actionSet.label}
                  </Typography>
                  
                  {/* Checkbox to use verifications for KPI */}
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={actionSet.use_verifications_for_kpi || false}
                        onChange={(e) => edgeEdit.handleUseVerificationsForKpiChange(actionSetIndex, e.target.checked)}
                        size="small"
                      />
                    }
                    label={
                      <Typography variant="body2" sx={{ fontSize: '0.875rem' }}>
                        Use target node verifications
                      </Typography>
                    }
                    sx={{ m: 0 }}
                  />
                </Box>
                
                {/* Helper text */}
                <Typography variant="caption" sx={{ fontSize: '0.75rem', color: 'text.secondary', mb: 0.5, display: 'block' }}>
                  Measure time from action to visual confirmation
                </Typography>
                
                {/* KPI References List - disabled when checkbox is checked */}
                <Box
                  sx={{
                    opacity: actionSet.use_verifications_for_kpi ? 0.5 : 1,
                    pointerEvents: actionSet.use_verifications_for_kpi ? 'none' : 'auto',
                    transition: 'opacity 0.2s',
                  }}
                >
                  <VerificationsList
                    verifications={actionSet.kpi_references || []}
                    availableVerifications={kpiAvailableVerifications}
                    onVerificationsChange={(newRefs) => edgeEdit.handleKpiReferencesChange(actionSetIndex, newRefs)}
                    loading={false}
                    model={model}
                    selectedHost={selectedHost || undefined}
                    testResults={[]}
                    onReferenceSelected={() => {}}
                    modelReferences={edgeEdit.modelReferences}
                    referencesLoading={edgeEdit.referencesLoading}
                    showCollapsible={false}
                    title=""
                    onTest={undefined}  // KPI measurements are post-processed, cannot be tested in real-time
                  />
                </Box>
              </Box>
            );
          })()}

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
                bgcolor: edgeHook.runResult.includes('❌ FAILED') || edgeHook.runResult.toLowerCase().includes('failed')
                  ? 'error.light'
                  : edgeHook.runResult.includes('✅ SUCCESS')
                    ? 'success.light'
                    : edgeHook.runResult.includes('❌') && !edgeHook.runResult.includes('✅')
                      ? 'error.light'
                      : edgeHook.runResult.includes('⚠️')
                        ? 'warning.light'
                        : 'error.light',
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
