import React, { useState, useEffect } from 'react';
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
  FormControlLabel,
  Checkbox,
  Alert,
  Paper,
  CircularProgress,
  TextField,
  Grid
} from '@mui/material';
import {
  SmartToy as AIIcon,
  Visibility as AnalyzeIcon,
  Navigation as NavigationIcon,
  CheckCircle as CompleteIcon,
  Error as ErrorIcon,
  Cancel as CancelIcon
} from '@mui/icons-material';
import { useGenerateModel } from '../../hooks/useGenerateModel';

interface AIGenerationModalProps {
  isOpen: boolean;
  onClose: () => void;
  treeId: string;
  selectedHost: any;
  selectedDeviceId: string;
  userinterfaceName?: string;
  onGenerated: () => void; // Refresh ReactFlow after generation
  onStructureCreated?: (nodesCount: number, edgesCount: number) => void; // NEW: Notify parent of structure creation
}

export const AIGenerationModal: React.FC<AIGenerationModalProps> = ({
  isOpen,
  onClose,
  treeId,
  selectedHost,
  selectedDeviceId,
  userinterfaceName,
  onGenerated,
  onStructureCreated
}) => {
  const [explorationDepth, setExplorationDepth] = useState(5);
  const [selectedNodeIds, setSelectedNodeIds] = useState<string[]>([]);
  const [selectedEdgeIds, setSelectedEdgeIds] = useState<string[]>([]);

  const {
    isExploring,
    status,
    currentStep,
    progress,
    currentAnalysis,
    explorationPlan,
    proposedNodes,
    proposedEdges,
    error,
    isGenerating,
    validationProgress,
    startExploration,
    continueExploration,
    startValidation,
    validateNextItem,
    cancelExploration,
    approveGeneration,
    resetState,
    canStart,
    hasResults,
    isAwaitingApproval,
    isStructureCreated,
    isAwaitingValidation,
    isValidating,
    isValidationComplete
  } = useGenerateModel({
    treeId,
    selectedHost,
    selectedDeviceId,
    userinterfaceName,
    isControlActive: true,
    onStructureCreated: (nodesCount, edgesCount) => {
      console.log('[@AIGenerationModal] Structure created:', nodesCount, 'nodes,', edgesCount, 'edges');
      
      // Trigger ReactFlow refresh
      onGenerated();
      
      // Notify parent to show ValidationReadyPrompt
      if (onStructureCreated) {
        onStructureCreated(nodesCount, edgesCount);
      }
    },
    onClose: () => {
      // Close modal after structure creation
      onClose();
    }
  });

  // Select all nodes and edges by default when results arrive
  useEffect(() => {
    if (hasResults) {
      setSelectedNodeIds(proposedNodes.map(node => node.id));
      setSelectedEdgeIds(proposedEdges.map(edge => edge.id));
    }
  }, [hasResults, proposedNodes, proposedEdges]);

  // Reset state when modal closes
  useEffect(() => {
    if (!isOpen) {
      resetState();
      setSelectedNodeIds([]);
      setSelectedEdgeIds([]);
      setExplorationDepth(5);
    }
  }, [isOpen, resetState]);

  const handleStart = async () => {
    await startExploration(explorationDepth);
  };

  const handleCancel = async () => {
    if (isExploring) {
      await cancelExploration();
    }
    onClose();
  };
  
  const handleCreateStructure = async () => {
    await continueExploration(); // Phase 2a: Create nodes/edges
  };
  
  const handleStartValidation = async () => {
    await startValidation(); // Phase 2b: Initialize validation
    // Auto-start validating first item
    await handleValidateNext();
  };
  
  const handleValidateNext = async () => {
    const result = await validateNextItem();
    if (result && result.has_more_items) {
      // Auto-continue if more items (small modal in corner)
      setTimeout(() => handleValidateNext(), 500); // Small delay between validations
    }
  };

  const handleApprove = async () => {
    const result = await approveGeneration(selectedNodeIds, selectedEdgeIds);
    if (result) {
      onGenerated(); // Refresh the navigation tree
      onClose();
    }
  };

  const handleNodeSelect = (nodeId: string, checked: boolean) => {
    if (checked) {
      setSelectedNodeIds(prev => [...prev, nodeId]);
    } else {
      setSelectedNodeIds(prev => prev.filter(id => id !== nodeId));
    }
  };

  const handleEdgeSelect = (edgeId: string, checked: boolean) => {
    if (checked) {
      setSelectedEdgeIds(prev => [...prev, edgeId]);
    } else {
      setSelectedEdgeIds(prev => prev.filter(id => id !== edgeId));
    }
  };

  const getStatusIcon = () => {
    if (isAwaitingApproval) {
      return <AnalyzeIcon color="warning" />;
    }
    switch (status) {
      case 'exploring':
        return <CircularProgress size={20} />;
      case 'completed':
        return <CompleteIcon color="success" />;
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
    <Dialog
      open={isOpen}
      onClose={onClose}
      maxWidth={(isValidating || isAwaitingValidation) ? "sm" : "md"}
      fullWidth
      PaperProps={{
        sx: { 
          maxHeight: '90vh',
          ...(isValidating || isAwaitingValidation ? {
            position: 'fixed',
            top: 20,
            right: 20,
            margin: 0,
            maxWidth: '400px',
            boxShadow: 'none',
            border: '1px solid',
            borderColor: 'divider'
          } : {})
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
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {/* Configuration Section - Only show when not exploring */}
        {!isExploring && !hasResults && !isAwaitingApproval && (
          <Paper sx={{ p: 2, bgcolor: 'transparent' }}>
            <Grid container spacing={2} alignItems="center">
              <Grid item xs={12} sm={6}>
                <TextField
                  label="Depth"
                  type="number"
                  value={explorationDepth}
                  onChange={(e) => setExplorationDepth(Number(e.target.value))}
                  inputProps={{ min: 1, max: 10 }}
                  size="small"
                  fullWidth
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <Typography variant="body2" color="text.secondary">
                  Host: {selectedHost?.host_name}
                  <br />
                  Device: {selectedDeviceId}
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
                                      Forward: home → {cleanNodeName}: click_element("{item}")
                                    </Typography>
                                    {/* Reverse action */}
                                    <Typography variant="body2" sx={{ fontSize: '0.75rem', fontFamily: 'monospace', pl: 1 }}>
                                      Backward: {cleanNodeName} → home: press_key(BACK)
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

        {/* Exploration Progress Section */}
        {(isExploring || hasResults) && !isAwaitingApproval && (
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
            {isExploring && (
              <Box sx={{ mb: 2 }}>
                <LinearProgress variant="indeterminate" sx={{ mb: 1 }} />
                <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                  <Chip label={`Screens: ${progress.screens_analyzed}/${progress.total_screens_found}`} size="small" />
                  <Chip label={`Nodes: ${progress.nodes_proposed}`} size="small" />
                  <Chip label={`Edges: ${progress.edges_proposed}`} size="small" />
                </Box>
              </Box>
            )}

            {/* Current Analysis */}
            {currentAnalysis.screen_name && (
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle2" color="text.secondary">
                  Current Analysis:
                </Typography>
                <Paper sx={{ p: 1, bgcolor: 'transparent' }}>
                  {/* Screenshot Preview */}
                  {currentAnalysis.screenshot && (
                    <Box sx={{ mb: 1 }}>
                      <img
                        src={currentAnalysis.screenshot}
                        alt="Current screen being analyzed"
                        style={{
                          maxWidth: '100%',
                          maxHeight: '200px',
                          objectFit: 'contain',
                          borderRadius: '4px',
                          border: '1px solid rgba(255, 255, 255, 0.12)'
                        }}
                      />
                    </Box>
                  )}
                  <Typography variant="body2" sx={{ fontWeight: 'medium' }}>
                    Screen: {currentAnalysis.screen_name}
                  </Typography>
                  {currentAnalysis.elements_found.length > 0 && (
                    <Box sx={{ mt: 1 }}>
                      <Typography variant="caption" color="text.secondary">
                        Elements found:
                      </Typography>
                      <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mt: 0.5 }}>
                        {currentAnalysis.elements_found.slice(0, 5).map((element, index) => (
                          <Chip key={index} label={element} size="small" variant="outlined" />
                        ))}
                        {currentAnalysis.elements_found.length > 5 && (
                          <Chip label={`+${currentAnalysis.elements_found.length - 5} more`} size="small" />
                        )}
                      </Box>
                    </Box>
                  )}
                  {currentAnalysis.reasoning && (
                    <Typography variant="body2" sx={{ mt: 1, fontStyle: 'italic' }}>
                      {currentAnalysis.reasoning}
                    </Typography>
                  )}
                </Paper>
              </Box>
            )}
            
            {/* Validation Progress - Show during Phase 2b */}
            {(isStructureCreated || isAwaitingValidation || isValidating || isValidationComplete) && (
              <Paper sx={{ p: 2, bgcolor: 'transparent' }}>
                <Typography variant="h6" sx={{ mb: 2 }}>
                  {isStructureCreated && '✅ Structure Created'}
                  {isAwaitingValidation && '⏳ Validation Starting...'}
                  {isValidating && `🔄 Validating ${validationProgress.current}/${validationProgress.total}`}
                  {isValidationComplete && '✅ Validation Complete'}
                </Typography>
                
                {isStructureCreated && (
                  <Typography variant="body2" color="text.secondary">
                    All nodes and edges have been created with _temp suffix.
                    Click "Start Validation" to test each action set.
                  </Typography>
                )}
                
                {(isAwaitingValidation || isValidating) && (
                  <>
                    <LinearProgress 
                      variant="determinate" 
                      value={(validationProgress.current / validationProgress.total) * 100} 
                      sx={{ mb: 2 }}
                    />
                    {/* Current step with action details */}
                    {currentStep && (
                      <Box sx={{ mb: 1, p: 1, bgcolor: 'background.paper', borderRadius: 1, border: '1px solid rgba(255,255,255,0.1)' }}>
                        <Typography variant="body2" color="text.secondary" sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
                          {currentStep}
                        </Typography>
                      </Box>
                    )}
                    <Typography variant="caption" color="text.secondary" component="div">
                      <Box component="span" sx={{ display: 'block', color: 'success.main' }}>
                        1. Forward: click_element(target) → verify screen changed
                      </Box>
                      <Box component="span" sx={{ display: 'block', color: 'info.main' }}>
                        2. Reverse: press_key(BACK) → verify returned home
                      </Box>
                    </Typography>
                  </>
                )}
                
                {isValidationComplete && (
                  <Typography variant="body2" color="text.secondary">
                    All action sets have been validated. Click "Finalize" to remove _temp suffix and make permanent.
                  </Typography>
                )}
              </Paper>
            )}

            {/* Proposed Changes - Only show when exploration is complete */}
            {hasResults && (
              <Box sx={{ flex: 1, overflow: 'auto' }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                  <NavigationIcon />
                  <Typography variant="h6">
                    Proposed Navigation Structure
                  </Typography>
                </Box>

                {/* Proposed Nodes */}
                {proposedNodes.length > 0 && (
                  <Box sx={{ mb: 3 }}>
                    <Typography variant="subtitle1" sx={{ mb: 1, fontWeight: 'medium' }}>
                      Nodes ({proposedNodes.length})
                    </Typography>
                    <Box sx={{ maxHeight: 200, overflow: 'auto' }}>
                      {proposedNodes.map((node) => (
                        <Paper key={node.id} sx={{ p: 1, mb: 1, bgcolor: 'transparent' }}>
                          <FormControlLabel
                            control={
                              <Checkbox
                                checked={selectedNodeIds.includes(node.id)}
                                onChange={(e) => handleNodeSelect(node.id, e.target.checked)}
                              />
                            }
                            label={
                              <Box>
                                <Typography variant="body2" sx={{ fontWeight: 'medium' }}>
                                  {node.name} ({node.id})
                                </Typography>
                                <Typography variant="caption" color="text.secondary">
                                  Type: {node.screen_type} • {node.reasoning}
                                </Typography>
                              </Box>
                            }
                          />
                        </Paper>
                      ))}
                    </Box>
                  </Box>
                )}

                {/* Proposed Edges */}
                {proposedEdges.length > 0 && (
                  <Box>
                    <Typography variant="subtitle1" sx={{ mb: 1, fontWeight: 'medium' }}>
                      Edges ({proposedEdges.length})
                    </Typography>
                    <Box sx={{ maxHeight: 200, overflow: 'auto' }}>
                      {proposedEdges.map((edge) => (
                        <Paper key={edge.id} sx={{ p: 1, mb: 1, bgcolor: 'transparent' }}>
                          <FormControlLabel
                            control={
                              <Checkbox
                                checked={selectedEdgeIds.includes(edge.id)}
                                onChange={(e) => handleEdgeSelect(edge.id, e.target.checked)}
                              />
                            }
                            label={
                              <Box>
                                <Typography variant="body2" sx={{ fontWeight: 'medium' }}>
                                  {edge.source} → {edge.target}
                                </Typography>
                                <Typography variant="caption" color="text.secondary">
                                  {edge.reasoning}
                                </Typography>
                              </Box>
                            }
                          />
                        </Paper>
                      ))}
                    </Box>
                  </Box>
                )}
              </Box>
            )}
          </Paper>
        )}
      </DialogContent>

      <DialogActions sx={{ p: 2, gap: 1 }}>
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
              Create Nodes
            </Button>
          </>
        )}
        
        {/* Phase 2a: Structure Created - Show Start Validation */}
        {isStructureCreated && (
          <>
            <Button
              onClick={handleCancel}
              variant="outlined"
              startIcon={<CancelIcon />}
            >
              Cancel
            </Button>
            <Button
              onClick={handleStartValidation}
              variant="contained"
              color="primary"
              startIcon={<CompleteIcon />}
            >
              Start Validation
            </Button>
          </>
        )}
        
        {/* Phase 2b: Validating - Show progress (auto-running) */}
        {(isAwaitingValidation || isValidating) && (
          <Button
            onClick={handleCancel}
            variant="outlined"
            color="error"
            startIcon={<CancelIcon />}
            disabled={isValidating}
          >
            {isValidating ? 'Validating...' : 'Cancel'}
          </Button>
        )}
        
        {/* Phase 2b: Validation Complete - Show Finalize */}
        {isValidationComplete && (
          <>
            <Button
              onClick={handleCancel}
              variant="outlined"
              startIcon={<CancelIcon />}
            >
              Cancel
            </Button>
            <Button
              onClick={() => {
                // TODO: Call finalize endpoint to rename _temp nodes/edges
                onGenerated();
                onClose();
              }}
              variant="contained"
              color="success"
              startIcon={<CompleteIcon />}
            >
              Finalize
            </Button>
          </>
        )}

        {/* Initial State: Show Close and Start */}
        {!isExploring && !hasResults && !isAwaitingApproval && !isStructureCreated && !isAwaitingValidation && !isValidating && !isValidationComplete && (
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
              disabled={!canStart}
            >
              Start
            </Button>
          </>
        )}

        {/* Exploring (Phase 1): Show Cancel */}
        {isExploring && !isValidating && (
          <Button
            onClick={handleCancel}
            variant="outlined"
            color="error"
            startIcon={<CancelIcon />}
          >
            Cancel
          </Button>
        )}

        {/* OLD Results flow (keeping for now) */}
        {hasResults && !isValidationComplete && (
          <>
            <Button
              onClick={handleCancel}
              variant="outlined"
              startIcon={<CancelIcon />}
            >
              Close
            </Button>
            <Button
              onClick={handleApprove}
              variant="contained"
              color="success"
              startIcon={isGenerating ? <CircularProgress size={20} /> : <CompleteIcon />}
              disabled={isGenerating || (selectedNodeIds.length === 0 && selectedEdgeIds.length === 0)}
            >
              {isGenerating ? 'Generating...' : `Generate (${selectedNodeIds.length + selectedEdgeIds.length} items)`}
            </Button>
          </>
        )}
      </DialogActions>
    </Dialog>
  );
};
