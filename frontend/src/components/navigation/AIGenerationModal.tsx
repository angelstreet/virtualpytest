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
  userinterfaceName?: string; // NEW: From tree data
  onGenerated: () => void; // Refresh ReactFlow after generation
}

export const AIGenerationModal: React.FC<AIGenerationModalProps> = ({
  isOpen,
  onClose,
  treeId,
  selectedHost,
  selectedDeviceId,
  userinterfaceName,
  onGenerated
}) => {
  const [explorationDepth, setExplorationDepth] = useState(5);
  const [selectedNodeIds, setSelectedNodeIds] = useState<string[]>([]);
  const [selectedEdgeIds, setSelectedEdgeIds] = useState<string[]>([]);

  const {
    isExploring,
    status,
    phase,
    currentStep,
    progress,
    currentAnalysis,
    explorationPlan,
    proposedNodes,
    proposedEdges,
    error,
    isGenerating,
    startExploration,
    continueExploration,
    cancelExploration,
    approveGeneration,
    resetState,
    canStart,
    hasResults,
    isAwaitingApproval
  } = useGenerateModel({
    treeId,
    selectedHost,
    selectedDeviceId,
    userinterfaceName,
    isControlActive: true
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
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: { maxHeight: '90vh' }
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
                      {/* Nodes Found */}
                      {explorationPlan.lines && explorationPlan.lines.length > 0 && (
                        <details>
                          <summary style={{ cursor: 'pointer', userSelect: 'none', padding: '4px 0' }}>
                            <Typography variant="body2" component="span" sx={{ fontWeight: 500 }}>
                              Nodes found ({explorationPlan.items.length})
                            </Typography>
                          </summary>
                          <Box sx={{ mt: 1, pl: 2, maxHeight: 200, overflow: 'auto' }}>
                            {explorationPlan.lines.map((line: string[], idx: number) => (
                              <Typography 
                                key={idx} 
                                variant="body2" 
                                sx={{ fontFamily: 'monospace', fontSize: '0.75rem', color: 'text.secondary' }}
                              >
                                Line {idx + 1}: {line.join(', ')}
                              </Typography>
                            ))}
                          </Box>
                        </details>
                      )}

                      {/* Edges Found */}
                      <details>
                        <summary style={{ cursor: 'pointer', userSelect: 'none', padding: '4px 0' }}>
                          <Typography variant="body2" component="span" sx={{ fontWeight: 500 }}>
                            Edges found ({explorationPlan.items.length})
                          </Typography>
                        </summary>
                        <Box sx={{ mt: 1, pl: 2, maxHeight: 200, overflow: 'auto' }}>
                          {explorationPlan.items.map((item: string, idx: number) => (
                            <Typography key={idx} variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.75rem', color: 'text.secondary' }}>
                              home → {item}
                            </Typography>
                          ))}
                        </Box>
                      </details>
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
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
              <AnalyzeIcon />
              <Typography variant="h6">
                {isExploring ? 'AI Exploration in Progress' : 'Exploration Complete'}
              </Typography>
            </Box>

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
        {/* Phase 1: Awaiting Approval - Show Continue, Retry, Abort */}
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
              onClick={continueExploration}
              startIcon={<NavigationIcon />}
            >
              Continue to Phase 2
            </Button>
          </>
        )}

        {/* Initial State: Show Close and Start */}
        {!isExploring && !hasResults && !isAwaitingApproval && (
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

        {/* Results: Show Close and Generate */}
        {hasResults && (
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
