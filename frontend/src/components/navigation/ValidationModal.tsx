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
  Paper
} from '@mui/material';
import {
  CheckCircle as CompleteIcon,
  Cancel as CancelIcon
} from '@mui/icons-material';
import { buildServerUrl } from '../../utils/buildUrlUtils';

interface ValidationModalProps {
  isOpen: boolean;
  onClose: () => void;
  
  // Exploration details
  explorationId: string;
  explorationHostName: string;
  treeId: string;
  
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
  onValidationStarted,
  onValidationComplete
}) => {
  const [isValidating, setIsValidating] = useState(false);
  const [isValidationComplete, setIsValidationComplete] = useState(false);
  const [validationProgress, setValidationProgress] = useState({ current: 0, total: 0 });
  const [validationResults, setValidationResults] = useState<ValidationResult[]>([]);
  const [currentStep, setCurrentStep] = useState('');
  const [error, setError] = useState<string | null>(null);

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
        const result: ValidationResult = {
          step: data.progress?.current_item || validationResults.length + 1,
          itemName: data.item,
          sourceNode: 'home',
          targetNode: data.node_name || '',
          forward: {
            action: data.action_sets.forward?.actions?.map((a: any) => `${a.command}${a.params?.text ? `("${a.params.text}")` : a.params?.key ? `(${a.params.key})` : ''}`).join(', ') || '',
            result: data.click_result === 'success' ? 'success' : 'failure',
            message: data.click_result === 'failed' ? 'Click failed' : undefined
          },
          backward: {
            action: data.action_sets.backward?.actions?.map((a: any) => `${a.command}${a.params?.key ? `(${a.params.key})` : ''}`).join(', ') || '',
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
        onValidationComplete?.();
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

  return (
    <Dialog
      open={isOpen}
      onClose={onClose}
      maxWidth="sm"
      fullWidth
      PaperProps={{
        sx: {
          position: 'fixed',
          top: 20,
          right: 20,
          margin: 0,
          maxWidth: '420px',
          maxHeight: 'calc(100vh - 40px)',
          boxShadow: 3,
          border: 'none',
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
          <Box sx={{ mb: 2, p: 2, bgcolor: 'error.dark', borderRadius: 1 }}>
            <Typography variant="body2" color="error.light">
              {error}
            </Typography>
          </Box>
        )}

        {/* Progress Bar */}
        {validationProgress.total > 0 && (
          <Box sx={{ mb: 2, position: 'sticky', top: 0, bgcolor: 'background.paper', zIndex: 1, pb: 1 }}>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              Step {validationProgress.current}/{validationProgress.total}
            </Typography>
            <LinearProgress 
              variant="determinate" 
              value={(validationProgress.current / validationProgress.total) * 100}
            />
          </Box>
        )}
        
        {/* Initial State - Show pending steps before validation starts */}
        {!isValidating && validationResults.length === 0 && validationProgress.total === 0 && (
          <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', py: 4, gap: 1 }}>
            <Typography variant="body2" color="text.secondary">
              Starting navigation tests...
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={{ textAlign: 'center', maxWidth: '300px' }}>
              Testing if created actions work correctly. Edges are already saved.
            </Typography>
          </Box>
        )}

        {/* Results List */}
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
          {/* Completed steps */}
          {validationResults.map((result, index) => (
            <Paper 
              key={index}
              sx={{ 
                p: 2,
                bgcolor: 'background.default',
                border: '2px solid',
                borderColor: result.forward.result === 'failure' ? 'error.main' : 'success.main',
                borderRadius: 2
              }}
            >
              {/* Header */}
              <Typography variant="body2" sx={{ fontWeight: 'bold', mb: 1.5, color: 'text.primary' }}>
                Step {result.step}: "{result.itemName}"
              </Typography>
              
              {/* Step 1.1: Forward (source → target) */}
              <Box sx={{ 
                mb: 1, 
                p: 1.5, 
                bgcolor: result.forward.result === 'success' ? 'rgba(46, 125, 50, 0.1)' : 'rgba(211, 47, 47, 0.1)',
                borderRadius: 1,
                border: '1px solid',
                borderColor: result.forward.result === 'success' ? 'success.dark' : 'error.dark'
              }}>
                <Typography variant="caption" sx={{ fontWeight: 'bold', display: 'block', mb: 0.5, color: 'text.secondary' }}>
                  Step {result.step}.1 (Forward)
                </Typography>
                <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.85rem', mb: 0.5 }}>
                  {result.sourceNode} → {result.targetNode}
                </Typography>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
                  <Typography 
                    variant="body2" 
                    sx={{ 
                      fontWeight: 'bold',
                      color: result.forward.result === 'success' ? 'success.main' : 'error.main'
                    }}
                  >
                    {result.forward.result === 'success' ? '✅ SUCCESS' : '❌ FAILURE'}
                  </Typography>
                  <Typography variant="caption" sx={{ fontFamily: 'monospace', color: 'text.secondary' }}>
                    ({result.forward.action})
                  </Typography>
                </Box>
                {result.forward.message && (
                  <Typography variant="caption" sx={{ display: 'block', mt: 0.5, color: 'error.light' }}>
                    {result.forward.message}
                  </Typography>
                )}
              </Box>
              
              {/* Step 1.2: Backward (target → source) */}
              <Box sx={{ 
                p: 1.5, 
                bgcolor: result.backward.result === 'success' ? 'rgba(46, 125, 50, 0.1)' : 
                         result.backward.result === 'warning' ? 'rgba(237, 108, 2, 0.1)' :
                         result.backward.result === 'skipped' ? 'rgba(158, 158, 158, 0.1)' : 'rgba(211, 47, 47, 0.1)',
                borderRadius: 1,
                border: '1px solid',
                borderColor: result.backward.result === 'success' ? 'success.dark' : 
                            result.backward.result === 'warning' ? 'warning.dark' :
                            result.backward.result === 'skipped' ? 'grey.600' : 'error.dark'
              }}>
                <Typography variant="caption" sx={{ fontWeight: 'bold', display: 'block', mb: 0.5, color: 'text.secondary' }}>
                  Step {result.step}.2 (Backward)
                </Typography>
                <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.85rem', mb: 0.5 }}>
                  {result.targetNode} → {result.sourceNode}
                </Typography>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
                  <Typography 
                    variant="body2" 
                    sx={{ 
                      fontWeight: 'bold',
                      color: result.backward.result === 'success' ? 'success.main' : 
                             result.backward.result === 'warning' ? 'warning.main' :
                             result.backward.result === 'skipped' ? 'text.secondary' : 'error.main'
                    }}
                  >
                    {result.backward.result === 'success' ? '✅ SUCCESS' :
                     result.backward.result === 'warning' ? '⚠️ WARNING' :
                     result.backward.result === 'skipped' ? '⏭️ SKIPPED' : '❌ FAILURE'}
                  </Typography>
                  <Typography variant="caption" sx={{ fontFamily: 'monospace', color: 'text.secondary' }}>
                    ({result.backward.action})
                  </Typography>
                </Box>
                {result.backward.message && result.backward.result !== 'success' && (
                  <Typography variant="caption" sx={{ display: 'block', mt: 0.5, color: 'warning.light' }}>
                    {result.backward.message}
                  </Typography>
                )}
              </Box>
            </Paper>
          ))}
          
          {/* Current step (in progress) */}
          {isValidating && validationProgress.current > validationResults.length && (
            <Paper sx={{ 
              p: 2, 
              bgcolor: 'info.dark', 
              border: '2px solid', 
              borderColor: 'info.main',
              borderRadius: 2
            }}>
              <Typography variant="body2" sx={{ fontWeight: 'bold', mb: 1, display: 'flex', alignItems: 'center', gap: 1 }}>
                <Box 
                  component="span" 
                  sx={{ 
                    animation: 'spin 1s linear infinite',
                    '@keyframes spin': {
                      '0%': { transform: 'rotate(0deg)' },
                      '100%': { transform: 'rotate(360deg)' }
                    }
                  }}
                >
                  🔄
                </Box>
                Step {validationProgress.current} (IN PROGRESS)
              </Typography>
              <Typography variant="caption" sx={{ fontFamily: 'monospace', display: 'block', color: 'info.light' }}>
                {currentStep || 'Processing...'}
              </Typography>
            </Paper>
          )}
          
          {/* Pending steps */}
          {validationProgress.total > 0 && 
           [...Array(Math.max(0, validationProgress.total - validationProgress.current))].map((_, index) => (
            <Paper 
              key={`pending-${index}`}
              sx={{ 
                p: 1.5, 
                bgcolor: 'action.hover', 
                opacity: 0.5,
                borderRadius: 1,
                border: '1px dashed',
                borderColor: 'divider'
              }}
            >
              <Typography variant="body2" color="text.secondary">
                ⏳ Step {validationProgress.current + index + 1} (PENDING)
              </Typography>
            </Paper>
          ))}
        </Box>

        {/* Summary */}
        {isValidationComplete && validationResults.length > 0 && (
          <Box sx={{ 
            mt: 2, 
            p: 2, 
            bgcolor: 'action.selected', 
            borderRadius: 1, 
            border: '1px solid', 
            borderColor: 'divider'
          }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 1.5 }}>
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
        
        {/* After validation complete - show Close */}
        {isValidationComplete && (
          <Button
            onClick={onClose}
            variant="contained"
            color="success"
            startIcon={<CompleteIcon />}
            fullWidth
          >
            Close
          </Button>
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
  );
};

