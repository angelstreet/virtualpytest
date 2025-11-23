'use client';

import { PlayArrow as PlayArrowIcon, Visibility as VisibilityIcon } from '@mui/icons-material';
import {
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Box,
  Chip,
  Divider,
  CircularProgress,
  Checkbox,
  FormControlLabel,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
} from '@mui/material';
import { useState, useEffect } from 'react';

import { useValidation } from '../../hooks/validation';
import { StyledDialog } from '../common/StyledDialog';

interface ValidationPreviewClientProps {
  treeId: string;
  onClose?: () => void;
  selectedHost?: any;
  selectedDeviceId?: string | null;
}

export default function ValidationPreviewClient({ treeId, onClose, selectedHost, selectedDeviceId }: ValidationPreviewClientProps) {
  const validation = useValidation(treeId, selectedHost, selectedDeviceId);
  const [selectedEdges, setSelectedEdges] = useState<Set<string>>(new Set());

  // Load preview data when component mounts if not already loaded
  useEffect(() => {
    if (!validation.preview && !validation.isLoadingPreview && !validation.validationError) {
      validation.loadPreview();
    }
  }, [validation.preview, validation.isLoadingPreview, validation.validationError, validation.loadPreview]);

  // Auto-select all edges when preview loads
  useEffect(() => {
    if (validation.preview?.edges) {
      const allEdgeIds = validation.preview.edges.map(
        (edge) => `${edge.from_node}-${edge.to_node}`,
      );
      setSelectedEdges(new Set(allEdgeIds));
    }
  }, [validation.preview]);

  // Close preview when validation starts
  useEffect(() => {
    if (validation.isValidating && onClose) {
      onClose();
    }
  }, [validation.isValidating, onClose]);

  const handleEdgeToggle = (edgeId: string) => {
    setSelectedEdges((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(edgeId)) {
        newSet.delete(edgeId);
      } else {
        newSet.add(edgeId);
      }
      return newSet;
    });
  };

  const handleSelectAll = () => {
    if (validation.preview?.edges) {
      const allEdgeIds = validation.preview.edges.map(
        (edge) => `${edge.from_node}-${edge.to_node}`,
      );
      setSelectedEdges(new Set(allEdgeIds));
    }
  };

  const handleDeselectAll = () => {
    setSelectedEdges(new Set());
  };

  const handleRunValidation = () => {
    if (!validation.preview?.edges) return;

    // Convert selected edge IDs to array for validation
    const selectedEdgeArray = Array.from(selectedEdges);
    console.log(`[@component:ValidationPreview] Running validation with ${selectedEdgeArray.length} selected edges`);
    console.log(`[@component:ValidationPreview] Sample selected edges:`, selectedEdgeArray.slice(0, 3));
    validation.runValidation(selectedEdgeArray);
  };

  // Show error dialog if there's a persistent error
  if (validation.validationError && !validation.isLoadingPreview) {
    return (
      <StyledDialog open={true} maxWidth="md" fullWidth>
        <DialogTitle>Validation Preview Error</DialogTitle>
        <DialogContent>
          <Box py={1}>
            <Typography color="error" gutterBottom>
              Failed to load validation preview:
            </Typography>
            <Typography variant="body2" color="textSecondary">
              {validation.validationError}
            </Typography>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>Close</Button>
          <Button 
            variant="outlined" 
            onClick={() => {
              validation.loadPreview();
            }}
          >
            Retry
          </Button>
        </DialogActions>
      </StyledDialog>
    );
  }

  // Only show dialog when there's preview data or when loading
  if (!validation.preview && !validation.isLoadingPreview) {
    return null;
  }

  // Show loading dialog
  if (!validation.preview && validation.isLoadingPreview) {
    return (
      <StyledDialog open={true} maxWidth="md" fullWidth>
        <DialogTitle>Validation Preview</DialogTitle>
        <DialogContent>
          <Box display="flex" justifyContent="center" alignItems="center" py={1}>
            <CircularProgress size={24} sx={{ mr: 2 }} />
            <Typography>Loading validation preview...</Typography>
          </Box>
        </DialogContent>
      </StyledDialog>
    );
  }

  const selectedCount = selectedEdges.size;
  const totalCount = validation.preview?.edges?.length || 0;

  return (
    <StyledDialog open={true} maxWidth="md" fullWidth>
      <DialogTitle>
        <Box display="flex" alignItems="center" gap={1}>
          <VisibilityIcon />
          <Typography variant="h6">Validation Preview</Typography>
          <Chip
            label={`${selectedCount}/${totalCount} selected`}
            color={selectedCount > 0 ? 'primary' : 'default'}
            size="small"
          />
        </Box>
      </DialogTitle>

      <DialogContent>
        <Box sx={{ mb: 1, display: 'flex', gap: 1 }}>
          <Button size="small" onClick={handleSelectAll}>
            Select All
          </Button>
          <Button size="small" onClick={handleDeselectAll}>
            Deselect All
          </Button>
        </Box>

        <Divider sx={{ my: 0 }} />

        <List dense>
          {validation.preview?.edges?.map((edge, index) => {
            const edgeId = `${edge.from_node}-${edge.to_node}`;
            const isSelected = selectedEdges.has(edgeId);

            return (
              <ListItem key={edgeId} divider>
                <ListItemText
                  primary={
                    <Box display="flex" alignItems="center" gap={0}>
                      <Typography variant="body2" fontWeight="bold" sx={{ fontSize: '14px' }}>
                        {index + 1}. {edge.from_name} → {edge.to_name}
                      </Typography>
                      {edge.has_verifications && (
                        <Chip
                          label="Has Verifications"
                          size="small"
                          color="info"
                          variant="outlined"
                        />
                      )}
                      {edge.actions && edge.actions.length > 0 && (
                        <Chip
                          label={`${edge.actions.length} actions`}
                          size="small"
                          color="default"
                          variant="outlined"
                        />
                      )}
                    </Box>
                  }
                  primaryTypographyProps={{ component: 'div' }}
                />
                <ListItemSecondaryAction>
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={isSelected}
                        onChange={() => handleEdgeToggle(edgeId)}
                        color="primary"
                      />
                    }
                    label=""
                  />
                </ListItemSecondaryAction>
              </ListItem>
            );
          })}
        </List>
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button
          variant="contained"
          startIcon={<PlayArrowIcon />}
          onClick={handleRunValidation}
          disabled={selectedCount === 0}
        >
          Run
        </Button>
      </DialogActions>
    </StyledDialog>
  );
}
