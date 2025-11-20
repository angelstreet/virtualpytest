import React, { useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  LinearProgress,
  Chip,
  Alert,
  Paper,
  Grid,
  CircularProgress
} from '@mui/material';
import {
  SmartToy as AIIcon,
  Visibility as AnalyzeIcon,
  Navigation as NavigationIcon,
  Error as ErrorIcon,
  Cancel as CancelIcon,
  CheckCircle as ValidateIcon,
  DeleteForever as AbortIcon
} from '@mui/icons-material';
import { useGenerateModel } from '../../hooks/useGenerateModel';
import { useAIGenerationModal } from '../../hooks/navigation/useAIGenerationModal';
import { AIGenerationPhaseIndicator } from './AIGenerationPhaseIndicator';
import { Phase2IncrementalView } from './Phase2IncrementalView';
import { ContextSummary } from './ContextSummary';

interface AIGenerationModalProps {
  isOpen: boolean;
  onClose: () => void;
  treeId: string;
  selectedHost: any;
  selectedDeviceId: string;
  userinterfaceName?: string;
  onGenerated: () => void; // Refresh ReactFlow after structure creation
  onStructureCreated: (nodesCount: number, edgesCount: number, explorationId: string, explorationHostName: string) => void; // Notify parent to show ValidationReadyPrompt
  onCleanupTemp?: () => void; // Cleanup _temp nodes from frontend state
}

export const AIGenerationModal: React.FC<AIGenerationModalProps> = ({
  isOpen,
  onClose,
  treeId,
  selectedHost,
  selectedDeviceId,
  userinterfaceName,
  onGenerated,
  onStructureCreated,
  onCleanupTemp
}) => {
  const {
    explorationId,
    explorationHostName,
    isExploring,
    status,
    currentStep,
    progress,
    currentAnalysis,
    explorationPlan,
    error,
    startExploration,
    continueExploration,
    cancelExploration,
    resetState,
    canStart,
    isAwaitingApproval,
    context,
    currentPhase,
    strategy,
    selectedNodes,
    toggleNodeSelection
  } = useGenerateModel({
    treeId,
    selectedHost,
    selectedDeviceId,
    userinterfaceName,
    isControlActive: true,
    onStructureCreated: async (nodesCount, edgesCount) => {
      console.log('[@AIGenerationModal:Phase1] Structure created:', nodesCount, 'nodes,', edgesCount, 'edges');
      
      // Wait for cache to clear before refreshing
      await new Promise(resolve => setTimeout(resolve, 500));
      
      // Trigger ReactFlow refresh (refetches tree data)
      console.log('[@AIGenerationModal:Phase1] Triggering React Flow refresh...');
      onGenerated();
      
      // Notify parent to show ValidationReadyPrompt with exploration details
      if (explorationId && explorationHostName) {
        onStructureCreated(nodesCount, edgesCount, explorationId, explorationHostName);
      } else {
        console.error('[@AIGenerationModal:Phase1] Missing exploration details!');
      }
      
      // Close this modal - ValidationReadyPrompt will take over
      onClose();
    },
    onClose: () => {
      // Close modal after structure creation
      onClose();
    }
  });

  // Use custom hook for modal logic
  const {
    hasTempNodes,
    isValidating,
    isAborting,
    showCleanConfirm,
    existingNodesCount,
    existingEdgesCount,
    isCheckingTree,
    handleValidatePrevious,
    handleAbortPrevious,
    handleStart,
    handleConfirmClean,
    handleCancelClean
  } = useAIGenerationModal({
    isOpen,
    treeId,
    selectedHost,
    selectedDeviceId,
    onGenerated,
    onClose,
    onCleanupTemp,
    startExploration,
    explorationId: explorationId || undefined
  });

  // Reset state when modal closes
  useEffect(() => {
    if (!isOpen) {
      console.log('[@AIGenerationModal:Phase1] Modal closed - preserving state for potential retry');
    }
  }, [isOpen]);

  const handleCancel = async () => {
    // Call cancelExploration if we have an active exploration session
    if (explorationId) {
      await cancelExploration();
      // Clean up _temp nodes from frontend state
      onCleanupTemp?.();
    }
    
    // Explicitly reset hook state when canceling
    console.log('[@AIGenerationModal:Phase1] Resetting state on cancel');
    resetState();
    
    onClose();
  };
  
  const handleCreateStructure = async () => {
    console.log('[@AIGenerationModal:Phase1] Creating structure...');
    await continueExploration(); // Phase 2a: Create nodes/edges
    // onStructureCreated callback will be triggered by hook, which closes this modal
  };

  const getStatusIcon = () => {
    if (isAwaitingApproval) {
      return <AnalyzeIcon color="warning" />;
    }
    switch (status) {
      case 'exploring':
        return <AIIcon color="primary" />;
      case 'completed':
        return <NavigationIcon color="success" />;
      case 'failed':
        return <ErrorIcon color="error" />;
      default:
        return <AIIcon color="primary" />;
    }
  };

  const getStatusColor = () => {
    if (isAwaitingApproval) {
      return 'warning';
    }
    switch (status) {
      case 'exploring':
        return 'primary';
      case 'completed':
        return 'success';
      case 'failed':
        return 'error';
      default:
        return 'default';
    }
  };

  return (
    <>
      <Dialog
        open={isOpen}
        onClose={onClose}
        maxWidth="md"
        fullWidth
        PaperProps={{
          sx: { 
            maxHeight: '90vh',
            border: '2px solid white',
            borderRadius: 2
        }
      }}
    >
      <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <AIIcon />
        AI Interface Generation
        <Chip
          icon={getStatusIcon()}
          label={status.toUpperCase()}
          color={getStatusColor()}
          size="small"
          sx={{ ml: 'auto' }}
        />
      </DialogTitle>

      <DialogContent sx={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 2 }}>
        {/* v2.0: Phase Indicator */}
        {currentPhase && (
          <AIGenerationPhaseIndicator 
            currentPhase={currentPhase} 
            strategy={strategy} 
          />
        )}

        {/* v2.0: Context Summary */}
        {context && <ContextSummary context={context} />}

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {/* Configuration Section - Only show when not exploring */}
        {!isExploring && !isAwaitingApproval && (
          <Paper sx={{ p: 2, bgcolor: 'transparent' }}>
            <Grid container spacing={2} alignItems="center">
              <Grid item xs={12}>
                <Typography variant="body2">
                  The system will explore main navigation items
                  and their sub-items
                </Typography>
                <Typography variant="body2" sx={{ mt: 1 }}>
                  Host: {selectedHost?.host_name} | Device: {selectedDeviceId}
                </Typography>
           
              </Grid>
            </Grid>
          </Paper>
        )}

        {/* Approval Section - Show AI plan */}
        {isAwaitingApproval && explorationPlan && (
          <Paper sx={{ p: 2, bgcolor: 'transparent' }}>
            <Grid container spacing={2}>
              {/* Left: Screenshot */}
              <Grid item xs={12} md={5}>
                {currentAnalysis.screenshot ? (
                  <a 
                    href={currentAnalysis.screenshot} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    style={{ display: 'block', cursor: 'pointer' }}
                  >
                    <img
                      src={currentAnalysis.screenshot}
                      alt="Initial screen"
                      style={{
                        width: '100%',
                        maxHeight: '280px',
                        objectFit: 'contain',
                        borderRadius: '4px',
                        border: '1px solid rgba(255, 255, 255, 0.12)',
                        transition: 'opacity 0.2s'
                      }}
                      onMouseOver={(e) => e.currentTarget.style.opacity = '0.8'}
                      onMouseOut={(e) => e.currentTarget.style.opacity = '1'}
                    />
                  </a>
                ) : (
                  <Box sx={{ height: 280, display: 'flex', alignItems: 'center', justifyContent: 'center', border: '1px dashed rgba(255,255,255,0.3)', borderRadius: 1 }}>
                    <Typography variant="body2" color="text.secondary">No screenshot</Typography>
                  </Box>
                )}
              </Grid>

              {/* Right: AI Plan */}
              <Grid item xs={12} md={7}>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
                  {explorationPlan.items.length === 0 ? (
                    <Typography variant="body2" color="warning.main">No items detected - AI couldn't read screen</Typography>
                  ) : (
                    <>
                      {/* Nodes Found - Show cleaned preview */}
                      <details open>
                        <summary style={{ cursor: 'pointer', userSelect: 'none', padding: '4px 0' }}>
                          <Typography variant="body2" component="span" sx={{ fontWeight: 500 }}>
                            Nodes found ({explorationPlan.items.filter((item: string) => item.toLowerCase() !== 'home').length + 1})
                          </Typography>
                        </summary>
                        <Box sx={{ mt: 1, pl: 2, maxHeight: 200, overflow: 'auto' }}>
                          {explorationPlan.lines && explorationPlan.lines.length > 0 ? (
                            // DPAD navigation (TV/STB) - show line structure
                            explorationPlan.lines.map((line: string[], idx: number) => (
                              <Typography 
                                key={idx} 
                                variant="body2" 
                                sx={{ fontFamily: 'monospace', fontSize: '0.75rem', color: 'text.secondary' }}
                              >
                                Line {idx + 1}: {line.join(', ')}
                              </Typography>
                            ))
                          ) : (
                            // Click-based navigation (mobile/web) - show cleaned node names as chips
                            <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                              {/* Always show home first */}
                              <Chip label="home" size="small" variant="outlined" />
                              
                              {explorationPlan.items
                                .filter((item: string) => item.toLowerCase() !== 'home')
                                .map((item: string, idx: number) => {
                                  // Generate clean node name (same logic as action sets)
                                  const cleanNodeName = item.toLowerCase()
                                    .replace(/&amp;/g, ' ')
                                    .replace(/tab|register|button|screen|menu|page|currently selected/gi, ' ')
                                    .replace(/[^a-z0-9]+/g, '_')
                                    .replace(/_+/g, '_')
                                    .replace(/^_|_$/g, '');
                                  
                                  return (
                                    <Chip key={idx} label={cleanNodeName} size="small" variant="outlined" />
                                  );
                                })}
                            </Box>
                          )}
                        </Box>
                      </details>

                      {/* Edges Found - Show bilateral action sets - OPEN BY DEFAULT */}
                      {(() => {
                        // Filter out self-referencing edges (e.g., home → home)
                        const validEdges = explorationPlan.items.filter((item: string) => item.toLowerCase() !== 'home');
                        return (
                          <details open>
                            <summary style={{ cursor: 'pointer', userSelect: 'none', padding: '4px 0' }}>
                              <Typography variant="body2" component="span" sx={{ fontWeight: 500 }}>
                                Edge found ({validEdges.length})
                              </Typography>
                            </summary>
                            <Box sx={{ mt: 1, pl: 2, maxHeight: 200, overflow: 'auto' }}>
                              {validEdges.map((item: string, idx: number) => {
                                // Generate clean node name (simplified version of backend logic)
                                const cleanNodeName = item.toLowerCase()
                                  .replace(/&amp;/g, ' ')
                                  .replace(/tab|register|button|screen|menu|page|currently selected/gi, ' ')
                                  .replace(/[^a-z0-9]+/g, '_')
                                  .replace(/_+/g, '_')
                                  .replace(/^_|_$/g, '');
                                
                                return (
                                  <Box key={idx} sx={{ mb: 0.5, p: 1, bgcolor: 'rgba(255,255,255,0.02)', borderRadius: 1, border: '1px solid rgba(255,255,255,0.05)' }}>
                                    <Typography variant="caption" sx={{ fontWeight: 'bold', color: 'text.secondary', display: 'block', mb: 0.5 }}>
                                      Step {idx + 1}
                                    </Typography>
                                    {/* Forward action */}
                                    <Typography variant="body2" sx={{ fontSize: '0.75rem', fontFamily: 'monospace', pl: 1 }}>
                                      → home → {cleanNodeName}: click("{item}")
                                    </Typography>
                                    {/* Reverse action */}
                                    <Typography variant="body2" sx={{ fontSize: '0.75rem', fontFamily: 'monospace', pl: 1 }}>
                                      ← {cleanNodeName} → home: BACK
                                    </Typography>
                                  </Box>
                                );
                              })}
                            </Box>
                          </details>
                        );
                      })()}
                    </>
                  )}
                </Box>
              </Grid>
            </Grid>
          </Paper>
        )}

        {/* Exploration Progress Section - Phase 1 only */}
        {isExploring && currentPhase !== 'phase2' && (
          <Paper sx={{ p: 2, flex: 1, display: 'flex', flexDirection: 'column', bgcolor: 'transparent' }}>
            {/* Current Step */}
            <Box sx={{ mb: 2 }}>
              <Typography variant="subtitle2" color="text.secondary">
                Current Step:
              </Typography>
              <Typography variant="body2" sx={{ fontFamily: 'monospace', p: 1, borderRadius: 1 }}>
                {currentStep || 'Initializing...'}
              </Typography>
            </Box>

            {/* Progress Indicators */}
            <Box sx={{ mb: 2 }}>
              <LinearProgress variant="indeterminate" sx={{ mb: 1 }} />
              <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                <Chip label={`Nodes: ${progress.nodes_proposed}`} size="small" />
                <Chip label={`Edges: ${progress.edges_proposed}`} size="small" />
              </Box>
            </Box>
          </Paper>
        )}

        {/* v2.0: Phase 2 Incremental View */}
        {currentPhase === 'phase2' && (
          <Phase2IncrementalView 
            context={context} 
            error={error}
            selectedNodes={selectedNodes}
            onToggleNode={toggleNodeSelection}
          />
        )}
      </DialogContent>

      <DialogActions sx={{ p: 2, gap: 1, position: 'relative' }}>
        {/* Bottom-Left: Validate/Abort Previous - Show when temp nodes exist */}
        {hasTempNodes && !isExploring && !isAwaitingApproval && (
          <Box sx={{ position: 'absolute', left: 16, bottom: 16, display: 'flex', gap: 1 }}>
            <Button
              variant="contained"
              onClick={handleAbortPrevious}
              disabled={isValidating || isAborting}
              startIcon={isAborting ? <CircularProgress size={16} /> : <AbortIcon />}
              sx={{
                bgcolor: 'error.main',
                '&:hover': { bgcolor: 'error.dark' },
                textTransform: 'none'
              }}
            >
              {isAborting ? 'Aborting...' : 'Abort Previous'}
            </Button>
            <Button
              variant="contained"
              onClick={handleValidatePrevious}
              disabled={isValidating || isAborting}
              startIcon={isValidating ? <CircularProgress size={16} /> : <ValidateIcon />}
              sx={{
                bgcolor: 'success.main',
                '&:hover': { bgcolor: 'success.dark' },
                textTransform: 'none'
              }}
            >
              {isValidating ? 'Validating...' : 'Validate Previous'}
            </Button>
            
          </Box>
        )}

        {/* Phase 1: Awaiting Approval - Show Abort, Retry, Create Nodes */}
        {isAwaitingApproval && (
          <>
            <Button
              variant="outlined"
              color="error"
              onClick={handleCancel}
              startIcon={<CancelIcon />}
            >
              Abort
            </Button>
            <Button
              variant="outlined"
              color="warning"
              onClick={handleStart}
            >
              Retry
            </Button>
            <Button
              variant="contained"
              color="success"
              onClick={handleCreateStructure}
              startIcon={<NavigationIcon />}
            >
              Create Nodes/Edges
            </Button>
          </>
        )}

        {/* Initial State: Show Close and Start */}
        {!isExploring && !isAwaitingApproval && (
          <>
            <Button
              onClick={handleCancel}
              variant="outlined"
              startIcon={<CancelIcon />}
            >
              Close
            </Button>
            <Button
              onClick={handleStart}
              variant="contained"
              startIcon={<AIIcon />}
              disabled={!canStart || isCheckingTree}
            >
              {isCheckingTree ? 'Checking...' : 'Start'}
            </Button>
          </>
        )}

        {/* Exploring: Show Cancel */}
        {isExploring && (
          <Button
            onClick={handleCancel}
            variant="outlined"
            color="error"
            startIcon={<CancelIcon />}
          >
            Cancel
          </Button>
        )}
      </DialogActions>
    </Dialog>
    
    {/* Confirmation Dialog: Delete existing nodes/edges */}
    <Dialog 
      open={showCleanConfirm} 
      onClose={handleCancelClean} 
      maxWidth="sm" 
      fullWidth
      PaperProps={{
        sx: { 
          border: '2px solid white',
          borderRadius: 2
        }
      }}
    >
      <DialogTitle>Clean Tree Before AI Generation?</DialogTitle>
      <DialogContent>
        <Alert severity="warning" sx={{ mb: 2 }}>
          This tree already contains navigation data. AI generation requires a clean tree.
        </Alert>
        <Typography variant="body2" gutterBottom>
          Found existing data:
        </Typography>
        <Box sx={{ pl: 2, mb: 2 }}>
          <Typography variant="body2">• {existingNodesCount} node{existingNodesCount !== 1 ? 's' : ''} (excluding home)</Typography>
          <Typography variant="body2">• {existingEdgesCount} edge{existingEdgesCount !== 1 ? 's' : ''}</Typography>
        </Box>
        <Typography variant="body2" color="text.secondary">
          Do you agree to delete all existing nodes and edges before starting AI generation?
        </Typography>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleCancelClean} variant="outlined">
          Cancel
        </Button>
        <Button 
          onClick={handleConfirmClean} 
          variant="contained" 
          color="error"
          disabled={isCheckingTree}
          startIcon={isCheckingTree ? <CircularProgress size={16} sx={{ color: 'inherit' }} /> : undefined}
        >
          {isCheckingTree ? 'Deleting...' : 'Delete'}
        </Button>
      </DialogActions>
    </Dialog>
    </>
  );
};
