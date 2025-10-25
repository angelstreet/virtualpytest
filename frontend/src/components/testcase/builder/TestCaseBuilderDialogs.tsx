import React from 'react';
import { 
  Dialog, 
  DialogTitle, 
  DialogContent, 
  DialogActions, 
  TextField, 
  Button, 
  List, 
  ListItemButton, 
  ListItemText,
  Box,
  Typography,
  Alert
} from '@mui/material';

interface TestCaseBuilderDialogsProps {
  // Save Dialog
  saveDialogOpen: boolean;
  setSaveDialogOpen: (open: boolean) => void;
  testcaseName: string;
  setTestcaseName: (name: string) => void;
  testcaseDescription: string;
  setTestcaseDescription: (desc: string) => void;
  currentTestcaseId: string | null;
  handleSave: () => void;
  
  // Load Dialog
  loadDialogOpen: boolean;
  setLoadDialogOpen: (open: boolean) => void;
  availableTestcases: any[];
  handleLoad: (testcase: any) => void;
  
  // Edit Dialog
  editDialogOpen: boolean;
  setEditDialogOpen: (open: boolean) => void;
  editingNode: any;
  editFormData: Record<string, any>;
  setEditFormData: (data: Record<string, any>) => void;
  handleSaveEdit: () => void;
}

export const TestCaseBuilderDialogs: React.FC<TestCaseBuilderDialogsProps> = ({
  saveDialogOpen,
  setSaveDialogOpen,
  testcaseName,
  setTestcaseName,
  testcaseDescription,
  setTestcaseDescription,
  currentTestcaseId,
  handleSave,
  loadDialogOpen,
  setLoadDialogOpen,
  availableTestcases,
  handleLoad,
  editDialogOpen,
  setEditDialogOpen,
  editingNode,
  editFormData,
  setEditFormData,
  handleSaveEdit,
}) => {
  return (
    <>
      {/* Save Dialog */}
      <Dialog open={saveDialogOpen} onClose={() => setSaveDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{currentTestcaseId ? 'Update Test Case' : 'Save Test Case'}</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Test Case Name"
            fullWidth
            value={testcaseName}
            onChange={(e) => setTestcaseName(e.target.value)}
            sx={{ mb: 2 }}
          />
          <TextField
            margin="dense"
            label="Description"
            fullWidth
            multiline
            rows={3}
            value={testcaseDescription}
            onChange={(e) => setTestcaseDescription(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSaveDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleSave} variant="contained" disabled={!testcaseName.trim()}>
            {currentTestcaseId ? 'Update' : 'Save'}
          </Button>
        </DialogActions>
      </Dialog>
      
      {/* Load Dialog */}
      <Dialog open={loadDialogOpen} onClose={() => setLoadDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Load Test Case</DialogTitle>
        <DialogContent>
          {availableTestcases.length === 0 ? (
            <Alert severity="info">No saved test cases available</Alert>
          ) : (
            <List>
              {availableTestcases.map((tc) => (
                <ListItemButton key={tc.id} onClick={() => handleLoad(tc)}>
                  <ListItemText
                    primary={tc.name}
                    secondary={
                      <Box>
                        <Typography variant="caption" component="div">
                          {tc.description || 'No description'}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          Updated: {new Date(tc.updated_at).toLocaleString()}
                        </Typography>
                      </Box>
                    }
                  />
                </ListItemButton>
              ))}
            </List>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setLoadDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
      
      {/* Edit Node Dialog */}
      <Dialog open={editDialogOpen} onClose={() => setEditDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Edit {editingNode?.type || 'Node'}</DialogTitle>
        <DialogContent>
          {editingNode && (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 1 }}>
              {Object.entries(editFormData).map(([key, value]) => (
                <TextField
                  key={key}
                  label={key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                  value={value || ''}
                  onChange={(e) => setEditFormData({ ...editFormData, [key]: e.target.value })}
                  fullWidth
                  multiline={typeof value === 'string' && value.length > 50}
                  rows={typeof value === 'string' && value.length > 50 ? 3 : 1}
                />
              ))}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleSaveEdit} variant="contained">Save</Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

