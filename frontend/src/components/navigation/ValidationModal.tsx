import React, { useState, useEffect, useCallback } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  LinearProgress,
  Paper,
  CircularProgress
} from '@mui/material';
import {
  CheckCircle as CompleteIcon,
  Cancel as CancelIcon,
  Visibility as ReviewIcon
} from '@mui/icons-material';
import { buildServerUrl } from '../../utils/buildUrlUtils';
import { NodeVerificationModal } from './NodeVerificationModal';

interface ValidationModalProps {
  isOpen: boolean;
  onClose: () => void;
  
  // Exploration details
  explorationId: string;
  explorationHostName: string;
  treeId: string;
  selectedDeviceId: string;
  
  // Callbacks
  onValidationStarted?: () => void;
  onValidationComplete?: () => void;
}

interface ValidationResult {
  step: number;
  itemName: string;
  sourceNode: string;
  targetNode: string;
  forward: {
    action: string;
    result: 'success' | 'failure';
    message?: string;
  };
  backward: {
    action: string;
    result: 'success' | 'warning' | 'skipped' | 'failure';
    message?: string;
  };
}

export const ValidationModal: React.FC<ValidationModalProps> = ({
  isOpen,
  onClose,
  explorationId,
  explorationHostName,
  treeId,
  selectedDeviceId,
  onValidationStarted,
  onValidationComplete
}) => {
  const [isValidating, setIsValidating] = useState(false);
  const [isValidationComplete, setIsValidationComplete] = useState(false);
  const [validationProgress, setValidationProgress] = useState({ current: 0, total: 0 });
  const [validationResults, setValidationResults] = useState<ValidationResult[]>([]);
  const [currentStep, setCurrentStep] = useState('');
  const [error, setError] = useState<string | null>(null);
  
  // Node verification state
  const [showNodeVerificationModal, setShowNodeVerificationModal] = useState(false);
  const [nodeVerificationSuggestions, setNodeVerificationSuggestions] = useState<any[]>([]);
  const [isAnalyzingVerifications, setIsAnalyzingVerifications] = useState(false);
  const [isUpdatingNodes, setIsUpdatingNodes] = useState(false);
  const [nodeVerificationComplete, setNodeVerificationComplete] = useState(false);

  // Start validation when modal opens
  useEffect(() => {
    if (isOpen && explorationId && !isValidating && !isValidationComplete) {
      startValidation();
    }
  }, [isOpen, explorationId]);

  const startValidation = useCallback(async () => {
    try {
      console.log('[@ValidationModal] Starting validation for exploration:', explorationId);
      
      const response = await fetch(
        buildServerUrl(`/server/ai-generation/start-validation`),
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            exploration_id: explorationId,
            host_name: explorationHostName,
            tree_id: treeId
          })
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to start validation: ${response.status}`);
      }

      const data = await response.json();
      console.log('[@ValidationModal] Validation started:', data);
      
      setIsValidating(true);
      onValidationStarted?.();
      
      // Start validating first item
      validateNextItem();
      
    } catch (err) {
      console.error('[@ValidationModal] Error starting validation:', err);
      setError(err instanceof Error ? err.message : 'Unknown error');
    }
  }, [explorationId, explorationHostName, treeId, onValidationStarted]);

  const validateNextItem = useCallback(async () => {
    try {
      console.log('[@ValidationModal] Validating next item...');
      setCurrentStep(''); // Clear previous step name
      
      const response = await fetch(
        buildServerUrl(`/server/ai-generation/validate-next-item`),
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            exploration_id: explorationId,
            host_name: explorationHostName
          })
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to validate item: ${response.status}`);
      }

      const data = await response.json();
      console.log('[@ValidationModal] Validation result:', data);
      
      // Update progress
      if (data.progress) {
        setValidationProgress({
          current: data.progress.current_item,
          total: data.progress.total_items
        });
      }
      
      // Update current step
      setCurrentStep(data.item || '');
      
      // Add result
      if (data.action_sets) {
        // Helper to format action with parameters
        const formatAction = (actionSet: any) => {
          if (!actionSet) return '';
          const action = actionSet.action || '';
          return action;
        };
        
        const result: ValidationResult = {
          step: data.progress?.current_item || validationResults.length + 1,
          itemName: data.item,
          sourceNode: data.action_sets.forward?.source || 'home',
          targetNode: data.action_sets.forward?.target || data.node_name || '',
          forward: {
            action: formatAction(data.action_sets.forward),
            result: data.click_result === 'success' ? 'success' : 'failure',
            message: data.click_result === 'failed' ? 'Click failed' : undefined
          },
          backward: {
            action: formatAction(data.action_sets.reverse),
            result: data.back_result === 'success' ? 'success' : 
                   data.back_result === 'warning' ? 'warning' : 
                   data.back_result === 'skipped' ? 'skipped' : 'failure',
            message: data.back_result !== 'success' ? data.back_result : undefined
          }
        };
        
        setValidationResults(prev => [...prev, result]);
      }
      
      // Check if done
      if (!data.has_more_items) {
        console.log('[@ValidationModal] Validation complete!');
        setIsValidating(false);
        setIsValidationComplete(true);
        
        // Force progress to 100%
        setValidationProgress(prev => ({
          ...prev,
          current: prev.total
        }));
        
        // Don't call onValidationComplete yet - wait for node verification approval
      } else {
        // Continue with next item
        setTimeout(() => validateNextItem(), 500);
      }
      
    } catch (err) {
      console.error('[@ValidationModal] Error validating item:', err);
      setError(err instanceof Error ? err.message : 'Unknown error');
      setIsValidating(false);
    }
  }, [explorationId, explorationHostName, validationResults.length]);

  // Helper function to truncate long text
  const truncate = (text: string, maxLength: number = 50) => {
    if (!text) return '';
    return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
  };
  
  // Start node verification analysis
  const handleStartNodeVerification = useCallback(async () => {
    try {
      setIsAnalyzingVerifications(true);
      setError(null);
      
      console.log('[@ValidationModal] Starting node verification analysis');
      
      const response = await fetch(buildServerUrl('/server/ai-generation/start-node-verification'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          device_id: selectedDeviceId,
          host_name: explorationHostName
        })
      });
      
      if (!response.ok) {
        throw new Error(`Failed to start node verification: ${response.status}`);
      }
      
      const data = await response.json();
      
      if (data.success) {
        setNodeVerificationSuggestions(data.suggestions || []);
        setShowNodeVerificationModal(true);
        console.log('[@ValidationModal] Got suggestions:', data.suggestions);
      } else {
        throw new Error(data.error || 'Failed to analyze node verifications');
      }
    } catch (err) {
      console.error('[@ValidationModal] Error starting node verification:', err);
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setIsAnalyzingVerifications(false);
    }
  }, []);
  
  // Approve node verifications
  const handleApproveNodeVerifications = useCallback(async (approvedVerifications: any[]) => {
    try {
      setIsUpdatingNodes(true);
      setError(null);
      
      console.log('[@ValidationModal] Approving node verifications:', approvedVerifications);
      
      const response = await fetch(buildServerUrl('/server/ai-generation/approve-node-verifications'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          device_id: selectedDeviceId,
          host_name: explorationHostName,
          approved_verifications: approvedVerifications
        })
      });
      
      if (!response.ok) {
        throw new Error(`Failed to approve verifications: ${response.status}`);
      }
      
      const data = await response.json();
      
      if (data.success) {
        console.log('[@ValidationModal] Node verifications approved:', data.nodes_updated);
        setShowNodeVerificationModal(false);
        setNodeVerificationComplete(true);
      } else {
        throw new Error(data.error || 'Failed to update nodes');
      }
      
      return data;
    } catch (err) {
      console.error('[@ValidationModal] Error approving verifications:', err);
      setError(err instanceof Error ? err.message : 'Unknown error');
      return null;
    } finally {
      setIsUpdatingNodes(false);
    }
  }, []);

  // Cancel exploration
  const handleCancelExploration = useCallback(async () => {
    try {
      console.log('[@ValidationModal] Cancelling exploration...');
      
      // Call backend to clean up
      await fetch(buildServerUrl('/server/ai-generation/cancel-exploration'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          device_id: selectedDeviceId,
          host_name: explorationHostName,
          exploration_id: explorationId,
          tree_id: treeId
        })
      });
      
      // Close modal
      onClose();
      
    } catch (err) {
      console.error('[@ValidationModal] Error cancelling exploration:', err);
      // Close anyway
      onClose();
    }
  }, [selectedDeviceId, explorationHostName, explorationId, treeId, onClose]);

  return (
    <>
    <Dialog
      open={isOpen}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: {
          position: 'fixed',
          top: 20,
          right: 20,
          margin: 0,
          maxWidth: '800px',
          maxHeight: 'calc(100vh - 40px)',
          boxShadow: 3,
          border: '3px solid',
          borderColor: isValidating ? 'info.main' : isValidationComplete ? 'success.main' : error ? 'error.main' : 'divider',
          borderRadius: 2,
          overflow: 'hidden'
        }
      }}
    >
      {/* Header */}
      <DialogTitle>
        {isValidating && '🔄 TESTING NAVIGATION'}
        {isValidationComplete && '✅ TESTING COMPLETE'}
        {error && '❌ TEST ERROR'}
      </DialogTitle>

      <DialogContent sx={{ 
        maxHeight: 'calc(100vh - 200px)', 
        overflow: 'auto',
        p: 2,
        '&::-webkit-scrollbar': {
          width: '8px'
        },
        '&::-webkit-scrollbar-track': {
          background: 'transparent'
        },
        '&::-webkit-scrollbar-thumb': {
          background: 'rgba(255,255,255,0.2)',
          borderRadius: '4px'
        }
      }}>
        {error && (
          <Box sx={{ mb: 1, p: 1, bgcolor: 'error.dark', borderRadius: 1 }}>
            <Typography variant="body2" color="error.light">
              {error}
            </Typography>
          </Box>
        )}

        {/* Progress Bar */}
        {validationProgress.total > 0 && (
          <Box sx={{ mb: 0.5, position: 'sticky', top: 0, bgcolor: 'background.paper', zIndex: 1, pb: 1 }}>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1, pl: 1.5 }}>
              Progress: {validationProgress.current}/{validationProgress.total}
            </Typography>
            <LinearProgress 
              variant="determinate" 
              value={(validationProgress.current / validationProgress.total) * 100}
            />
          </Box>
        )}

        {/* Summary - MOVED UP */}
        {isValidationComplete && validationResults.length > 0 && (
          <Box sx={{ 
            mb: 2,  // Margin bottom instead of top
            p: 1, 
            bgcolor: 'action.selected', 
            borderRadius: 1, 
            border: '1px solid', 
            borderColor: 'divider'
          }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 0.5 }}>
              📊 Summary
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
              <Typography variant="body2">
                ✅ Successful forward: {validationResults.filter(r => r.forward.result === 'success').length}/{validationResults.length}
              </Typography>
              <Typography variant="body2">
                ❌ Failed forward: {validationResults.filter(r => r.forward.result === 'failure').length}/{validationResults.length}
              </Typography>
              <Typography variant="body2">
                ⚠️ Backward warnings: {validationResults.filter(r => r.backward.result === 'warning').length}/{validationResults.length}
              </Typography>
            </Box>
          </Box>
        )}

        {/* Results List - Compact Format - Reverse order (newest first) */}
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
          {/* Current step (in progress) - Show first so user doesn't need to scroll */}
          {(isValidating || validationResults.length === 0) && (
            <Paper sx={{ 
              p: 1.5, 
              bgcolor: 'info.dark', 
              border: '2px solid', 
              borderColor: 'info.main',
              borderRadius: 1
            }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                <CircularProgress size={16} sx={{ color: 'info.light' }} />
                <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                  Step {Math.max(1, (validationProgress.current || 0) + 1)} - IN PROGRESS
                </Typography>
              </Box>
              <Typography variant="caption" sx={{ fontFamily: 'monospace', display: 'block', color: 'info.light', ml: 3 }}>
                {truncate(currentStep || 'Validating...', 70)}
              </Typography>
            </Paper>
          )}
          
          {/* Completed steps - Reverse chronological order (newest first) */}
          {[...validationResults].reverse().map((result, index) => (
            <Paper 
              key={validationResults.length - 1 - index}
              sx={{ 
                p: 1.5,
                bgcolor: 'background.default',
                border: '2px solid',
                borderColor: result.forward.result === 'failure' || result.backward.result === 'failure' ? 'error.main' : 'success.main',
                borderRadius: 1
              }}
            >
              {/* Step X.1 (Forward) - One Line */}
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5, flexWrap: 'wrap' }}>
                <Typography variant="body2" sx={{ fontWeight: 'bold', minWidth: '70px' }}>
                  Step {result.step}.1
                </Typography>
                <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.85rem', color: 'text.secondary' }}>
                  {truncate(`${result.sourceNode} → ${result.targetNode}`, 30)}
                </Typography>
                <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.8rem', color: 'text.disabled' }}>
                  {truncate(result.forward.action, 40)}
                </Typography>
                <Typography 
                  variant="body2" 
                  sx={{ 
                    fontWeight: 'bold',
                    ml: 'auto',
                    color: result.forward.result === 'success' ? 'success.main' : 'error.main'
                  }}
                >
                  {result.forward.result === 'success' ? '✅ SUCCESS' : '❌ FAILED'}
                </Typography>
              </Box>
              
              {/* Step X.2 (Backward) - One Line */}
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
                <Typography variant="body2" sx={{ fontWeight: 'bold', minWidth: '70px' }}>
                  Step {result.step}.2
                </Typography>
                <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.85rem', color: 'text.secondary' }}>
                  {truncate(`${result.targetNode} → ${result.sourceNode}`, 30)}
                </Typography>
                <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.8rem', color: 'text.disabled' }}>
                  {truncate(result.backward.action, 40)}
                </Typography>
                <Typography 
                  variant="body2" 
                  sx={{ 
                    fontWeight: 'bold',
                    ml: 'auto',
                    color: result.backward.result === 'success' ? 'success.main' : 
                           result.backward.result === 'warning' ? 'warning.main' :
                           result.backward.result === 'skipped' ? 'text.secondary' : 'error.main'
                  }}
                >
                  {result.backward.result === 'success' ? '✅ SUCCESS' :
                   result.backward.result === 'warning' ? '⚠️ WARNING' :
                   result.backward.result === 'skipped' ? '⏭️ SKIPPED' : '❌ FAILED'}
                </Typography>
              </Box>
            </Paper>
          ))}
          
          {/* Pending steps */}
          {validationProgress.total > 0 && 
           [...Array(Math.max(0, validationProgress.total - (validationProgress.current || 0) - 1))].map((_, index) => (
            <Paper 
              key={`pending-${index}`}
              sx={{ 
                p: 1, 
                bgcolor: 'action.hover', 
                opacity: 0.4,
                borderRadius: 1,
                border: '1px dashed',
                borderColor: 'divider'
              }}
            >
              <Typography variant="body2" color="text.secondary">
                ⏳ Step {(validationProgress.current || 0) + index + 2} - PENDING
              </Typography>
            </Paper>
          ))}
        </Box>
      </DialogContent>

      {/* Actions */}
      <DialogActions sx={{ p: 2, gap: 1 }}>
        {/* During validation - only show disabled cancel */}
        {isValidating && (
          <Button
            onClick={onClose}
            variant="outlined"
            color="error"
            startIcon={<CancelIcon />}
            disabled
          >
            Validating...
          </Button>
        )}
        
        {/* After validation complete - show Review Node Verifications or Confirm & Save */}
        {isValidationComplete && !nodeVerificationComplete && (
          <>
            <Button
              onClick={handleCancelExploration}
              variant="outlined"
              color="error"
              startIcon={<CancelIcon />}
            >
              Cancel & Delete
            </Button>
            <Button
              onClick={handleStartNodeVerification}
              variant="contained"
              color="primary"
              startIcon={<ReviewIcon />}
              disabled={isAnalyzingVerifications}
            >
              {isAnalyzingVerifications ? 'Analyzing...' : 'Review Node Verifications'}
            </Button>
          </>
        )}
        
        {/* After node verification complete - show Confirm & Save */}
        {nodeVerificationComplete && (
          <>
            <Button
              onClick={handleCancelExploration}
              variant="outlined"
              color="error"
              startIcon={<CancelIcon />}
            >
              Cancel & Delete
            </Button>
            <Button
              onClick={() => {
                onValidationComplete?.();
              }}
              variant="contained"
              color="success"
              startIcon={<CompleteIcon />}
            >
              Confirm & Save
            </Button>
          </>
        )}
        
        {/* Error state */}
        {error && !isValidating && (
          <Button
            onClick={onClose}
            variant="contained"
            color="error"
          >
            Close
          </Button>
        )}
      </DialogActions>
    </Dialog>
    
    {/* Node Verification Modal */}
    <NodeVerificationModal
      isOpen={showNodeVerificationModal}
      onClose={() => setShowNodeVerificationModal(false)}
      onCancel={() => {
        setShowNodeVerificationModal(false);
        handleCancelExploration();
      }}
      suggestions={nodeVerificationSuggestions}
      onApprove={handleApproveNodeVerifications}
      isUpdating={isUpdatingNodes}
    />
    </>
  );
};

