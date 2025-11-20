import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  List,
  ListItem,
  Checkbox,
  FormControlLabel,
  Alert
} from '@mui/material';
import {
  CheckCircle as CheckIcon,
  Error as ErrorIcon,
  Close as CloseIcon
} from '@mui/icons-material';

interface NodeVerificationModalProps {
  isOpen: boolean;
  onClose: () => void;
  suggestions: any[];
  onApprove: (approvedVerifications: any[]) => Promise<any>;
  isUpdating: boolean;
}

export const NodeVerificationModal: React.FC<NodeVerificationModalProps> = ({
  isOpen,
  onClose,
  suggestions,
  onApprove,
  isUpdating
}) => {
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [approvedMap, setApprovedMap] = useState<Record<string, boolean>>({});

  useEffect(() => {
    if (isOpen && suggestions.length > 0) {
      const initialApproved: Record<string, boolean> = {};
      suggestions.forEach(s => {
        initialApproved[s.node_id] = s.suggested_verification?.found || false;
      });
      setApprovedMap(initialApproved);
      setSelectedNodeId(suggestions[0]?.node_id || null);
    }
  }, [isOpen, suggestions]);

  const handleApprove = async () => {
    const approvedVerifications = suggestions
      .filter(s => approvedMap[s.node_id] && s.suggested_verification?.found)
      .map(s => ({
        node_id: s.node_id,
        verification: s.suggested_verification,
        screenshot_url: s.screenshot_url
      }));

    await onApprove(approvedVerifications);
    onClose();
  };

  const selectedSuggestion = suggestions.find(s => s.node_id === selectedNodeId);

  return (
    <Dialog
      open={isOpen}
      onClose={onClose}
      maxWidth="lg"
      fullWidth
      PaperProps={{
        sx: {
          maxHeight: '90vh',
          border: '2px solid',
          borderColor: 'divider',
          borderRadius: 2,
          bgcolor: 'background.paper'
        }
      }}
    >
      <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1, borderBottom: '1px solid', borderColor: 'divider' }}>
        <CheckIcon />
        Node Verification Review
        <Box sx={{ ml: 'auto', display: 'flex', gap: 1 }}>
          <Typography variant="body2" color="text.secondary">
            {suggestions.filter(s => approvedMap[s.node_id]).length} / {suggestions.length} selected
          </Typography>
        </Box>
      </DialogTitle>

      <DialogContent sx={{ p: 0, display: 'flex', height: 600 }}>
        <Box sx={{ width: 300, borderRight: '1px solid', borderColor: 'divider', overflow: 'auto' }}>
          <List dense disablePadding>
            {suggestions.map((suggestion) => {
              const isSelected = selectedNodeId === suggestion.node_id;
              const hasVerification = suggestion.suggested_verification?.found;
              
              return (
                <ListItem
                  key={suggestion.node_id}
                  onClick={() => setSelectedNodeId(suggestion.node_id)}
                  sx={{
                    cursor: 'pointer',
                    bgcolor: isSelected ? 'action.selected' : 'transparent',
                    borderLeft: isSelected ? 3 : 0,
                    borderColor: 'primary.main',
                    '&:hover': {
                      bgcolor: 'action.hover'
                    },
                    py: 1.5,
                    px: 2,
                    borderBottom: '1px solid',
                    borderBottomColor: 'divider'
                  }}
                >
                  <Box sx={{ display: 'flex', alignItems: 'center', width: '100%' }}>
                    <Checkbox
                      checked={approvedMap[suggestion.node_id] || false}
                      disabled={!hasVerification}
                      onChange={(e) => {
                        e.stopPropagation();
                        setApprovedMap(prev => ({
                          ...prev,
                          [suggestion.node_id]: e.target.checked
                        }));
                      }}
                      sx={{ p: 0, mr: 1 }}
                    />
                    <Box sx={{ flex: 1, minWidth: 0 }}>
                      <Typography variant="body2" noWrap>
                        {suggestion.node_label}
                      </Typography>
                      {hasVerification ? (
                        <Typography variant="caption" color="success.main">
                          ✓ Found
                        </Typography>
                      ) : (
                        <Typography variant="caption" color="error.main">
                          ✗ None
                        </Typography>
                      )}
                    </Box>
                  </Box>
                </ListItem>
              );
            })}
          </List>
        </Box>

        <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'auto' }}>
          {selectedSuggestion ? (
            <>
              <Box sx={{ p: 3, borderBottom: '1px solid', borderColor: 'divider' }}>
                <Typography variant="h6" gutterBottom>
                  {selectedSuggestion.node_label}
                </Typography>
                
                {selectedSuggestion.screenshot_url ? (
                  <Box
                    component="img"
                    src={selectedSuggestion.screenshot_url}
                    alt={selectedSuggestion.node_label}
                    sx={{
                      width: '100%',
                      maxHeight: 300,
                      objectFit: 'contain',
                      borderRadius: 1,
                      border: '1px solid',
                      borderColor: 'divider'
                    }}
                  />
                ) : (
                  <Alert severity="warning" sx={{ mt: 2 }}>
                    No screenshot available
                  </Alert>
                )}
              </Box>

              <Box sx={{ p: 3 }}>
                <Typography variant="subtitle2" gutterBottom>
                  Suggested Verification:
                </Typography>
                
                {selectedSuggestion.suggested_verification?.found ? (
                  <Box sx={{ mt: 1, p: 2, bgcolor: 'action.hover', borderRadius: 1, border: '1px solid', borderColor: 'divider' }}>
                    <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                      <strong>Method:</strong> {selectedSuggestion.suggested_verification.method}
                    </Typography>
                    <Typography variant="body2" sx={{ fontFamily: 'monospace', mt: 1 }}>
                      <strong>Type:</strong> {selectedSuggestion.suggested_verification.type}
                    </Typography>
                    <Typography variant="body2" sx={{ fontFamily: 'monospace', mt: 1, wordBreak: 'break-all' }}>
                      <strong>Value:</strong> {JSON.stringify(selectedSuggestion.suggested_verification.params)}
                    </Typography>
                    
                    <FormControlLabel
                      control={
                        <Checkbox
                          checked={approvedMap[selectedSuggestion.node_id] || false}
                          onChange={(e) => setApprovedMap(prev => ({
                            ...prev,
                            [selectedSuggestion.node_id]: e.target.checked
                          }))}
                        />
                      }
                      label="Use this verification"
                      sx={{ mt: 2 }}
                    />
                  </Box>
                ) : (
                  <Alert severity="error" sx={{ mt: 1 }}>
                    <Typography variant="body2">
                      No unique element found for this node.
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      You may need to manually add verification after generation.
                    </Typography>
                  </Alert>
                )}
              </Box>
            </>
          ) : (
            <Box sx={{ p: 3, display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
              <Typography color="text.secondary">
                Select a node to review
              </Typography>
            </Box>
          )}
        </Box>
      </DialogContent>

      <DialogActions sx={{ p: 2, gap: 1, borderTop: '1px solid', borderColor: 'divider' }}>
        <Button
          onClick={onClose}
          variant="outlined"
          startIcon={<CloseIcon />}
          disabled={isUpdating}
        >
          Cancel
        </Button>
        <Button
          onClick={handleApprove}
          variant="contained"
          color="primary"
          startIcon={<CheckIcon />}
          disabled={isUpdating || suggestions.filter(s => approvedMap[s.node_id]).length === 0}
        >
          {isUpdating ? 'Updating...' : `Approve (${suggestions.filter(s => approvedMap[s.node_id]).length})`}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

