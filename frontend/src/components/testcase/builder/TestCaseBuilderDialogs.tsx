import React from 'react';
import { 
  Dialog, 
  DialogTitle, 
  DialogContent, 
  DialogActions, 
  TextField, 
  Button, 
  List, 
  ListItem,
  Box,
  Typography,
  Alert,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  IconButton
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';

interface TestCaseBuilderDialogsProps {
  // Save Dialog
  saveDialogOpen: boolean;
  setSaveDialogOpen: (open: boolean) => void;
  testcaseName: string;
  setTestcaseName: (name: string) => void;
  testcaseDescription: string;
  setTestcaseDescription: (desc: string) => void;
  testcaseEnvironment: string;
  setTestcaseEnvironment: (env: string) => void;
  currentTestcaseId: string | null;
  currentVersion?: number | null;
  handleSave: () => void;
  
  // Load Dialog
  loadDialogOpen: boolean;
  setLoadDialogOpen: (open: boolean) => void;
  availableTestcases: any[];
  handleLoad: (testcaseId: string) => void;
  handleDelete?: (testcaseId: string, testcaseName: string) => void;
  
  // Edit Dialog
  editDialogOpen: boolean;
  setEditDialogOpen: (open: boolean) => void;
  editingNode: any;
  editFormData: Record<string, any>;
  setEditFormData: (data: Record<string, any>) => void;
  handleSaveEdit: () => void;
  
  // AI Generate Confirmation Dialog
  aiGenerateConfirmOpen?: boolean;
  setAiGenerateConfirmOpen?: (open: boolean) => void;
  handleConfirmAIGenerate?: () => void;
}

export const TestCaseBuilderDialogs: React.FC<TestCaseBuilderDialogsProps> = ({
  saveDialogOpen,
  setSaveDialogOpen,
  testcaseName,
  setTestcaseName,
  testcaseDescription,
  setTestcaseDescription,
  testcaseEnvironment,
  setTestcaseEnvironment,
  currentTestcaseId,
  currentVersion,
  handleSave,
  loadDialogOpen,
  setLoadDialogOpen,
  availableTestcases,
  handleLoad,
  handleDelete,
  editDialogOpen,
  setEditDialogOpen,
  editingNode,
  editFormData,
  setEditFormData,
  handleSaveEdit,
  aiGenerateConfirmOpen,
  setAiGenerateConfirmOpen,
  handleConfirmAIGenerate,
}) => {
  // Get environment color for chips
  const getEnvironmentColor = (env: string) => {
    switch (env) {
      case 'prod': return 'error';
      case 'test': return 'warning';
      case 'dev': return 'success';
      default: return 'default';
    }
  };

  return (
    <>
      {/* Save Dialog */}
      <Dialog 
        open={saveDialogOpen} 
        onClose={() => setSaveDialogOpen(false)} 
        maxWidth="sm" 
        fullWidth
        PaperProps={{
          sx: {
            border: 2,
            borderColor: 'divider',
          }
        }}
      >
        <DialogTitle sx={{ 
          borderBottom: 1, 
          borderColor: 'divider', 
          pb: 2,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <Typography variant="h6">
            {currentTestcaseId ? 'Update Test Case' : 'Save Test Case'}
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <Chip 
              label={(testcaseEnvironment || 'dev').toUpperCase()} 
              color={getEnvironmentColor(testcaseEnvironment || 'dev')} 
              size="small" 
              sx={{ fontWeight: 'bold' }}
            />
            <Chip 
              label={`Version ${currentVersion || 1}`} 
              color="primary" 
              size="small" 
              variant="outlined"
              sx={{ fontWeight: 'bold' }}
            />
          </Box>
        </DialogTitle>
        <DialogContent sx={{ pt: 3 }}>
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
            sx={{ mb: 2 }}
          />
          <FormControl fullWidth margin="dense">
            <InputLabel>Environment</InputLabel>
            <Select
              value={testcaseEnvironment}
              label="Environment"
              onChange={(e) => setTestcaseEnvironment(e.target.value)}
            >
              <MenuItem value="dev">
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Chip label="DEV" color="success" size="small" />
                  <Typography variant="body2">Development (default)</Typography>
                </Box>
              </MenuItem>
              <MenuItem value="test">
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Chip label="TEST" color="warning" size="small" />
                  <Typography variant="body2">Testing</Typography>
                </Box>
              </MenuItem>
              <MenuItem value="prod">
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Chip label="PROD" color="error" size="small" />
                  <Typography variant="body2">Production</Typography>
                </Box>
              </MenuItem>
            </Select>
          </FormControl>
        </DialogContent>
        <DialogActions sx={{ borderTop: 1, borderColor: 'divider', pt: 2, pb: 2, px: 3 }}>
          <Button onClick={() => setSaveDialogOpen(false)} variant="outlined">
            Cancel
          </Button>
          <Button onClick={handleSave} variant="contained" disabled={!testcaseName.trim()}>
            {currentTestcaseId ? 'Update' : 'Save'}
          </Button>
        </DialogActions>
      </Dialog>
      
      {/* Load Dialog */}
      <Dialog 
        open={loadDialogOpen} 
        onClose={() => setLoadDialogOpen(false)} 
        maxWidth="md" 
        fullWidth
        PaperProps={{
          sx: {
            border: 2,
            borderColor: 'divider',
          }
        }}
      >
        <DialogTitle sx={{ borderBottom: 1, borderColor: 'divider', pb: 2 }}>
          Load Test Case
        </DialogTitle>
        <DialogContent sx={{ pt: 3 }}>
          {availableTestcases.length === 0 ? (
            <Alert severity="info">No test cases found. Create one first!</Alert>
          ) : (
            <List>
              {availableTestcases.map((tc) => (
                <ListItem
                  key={tc.testcase_id}
                  sx={{ 
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'stretch',
                    border: '1px solid',
                    borderColor: 'divider',
                    borderRadius: 1,
                    mb: 1,
                    p: 0,
                    '&:hover': {
                      bgcolor: 'action.hover'
                    }
                  }}
                >
                  {/* Header Row: Name and Chips + Delete Button */}
                  <Box sx={{ 
                    display: 'flex', 
                    justifyContent: 'space-between', 
                    alignItems: 'center',
                    p: 2,
                    pb: 1,
                    cursor: 'pointer'
                  }}
                  onClick={() => handleLoad(tc.testcase_id)}
                  >
                    <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>
                      {tc.testcase_name}
                    </Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, flexShrink: 0, ml: 2 }}>
                      <Chip 
                        label={(tc.environment || 'dev').toUpperCase()} 
                        color={getEnvironmentColor(tc.environment || 'dev')} 
                        size="small" 
                        sx={{ fontWeight: 'bold' }}
                      />
                      <Chip 
                        label={`Version ${tc.current_version || 1}`} 
                        color="primary" 
                        size="small" 
                        variant="outlined"
                        sx={{ fontWeight: 'bold' }}
                      />
                      {handleDelete && (
                        <IconButton 
                          size="small" 
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDelete(tc.testcase_id, tc.testcase_name);
                          }}
                          sx={{ ml: 0.5 }}
                        >
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      )}
                    </Box>
                  </Box>
                  
                  {/* Content: Description, UI, and Execution Info */}
                  <Box sx={{ px: 2, pb: 2, cursor: 'pointer' }} onClick={() => handleLoad(tc.testcase_id)}>
                    {tc.description && (
                      <Typography variant="body2" color="text.secondary" sx={{ mb: 0.5 }}>
                        {tc.description}
                      </Typography>
                    )}
                    <Typography variant="body2" color="text.secondary">
                      UI: {tc.userinterface_name || 'Not specified'} - {tc.graph_json?.nodes?.length || 0} blocks
                    </Typography>
                    {tc.execution_count > 0 ? (
                      <Typography variant="body2" color="text.secondary" sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mt: 0.5 }}>
                        Last run: {tc.last_execution_success ? 
                          <CheckCircleIcon fontSize="small" style={{ color: '#10b981' }} /> : 
                          <ErrorIcon fontSize="small" style={{ color: '#ef4444' }} />
                        } {tc.execution_count} execution{tc.execution_count > 1 ? 's' : ''}
                      </Typography>
                    ) : (
                      <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                        Last run: Never executed
                      </Typography>
                    )}
                    <Typography variant="caption" color="text.secondary">
                      Created: {new Date(tc.created_at).toLocaleDateString()} - Modified: {new Date(tc.updated_at).toLocaleDateString()}
                    </Typography>
                  </Box>
                </ListItem>
              ))}
            </List>
          )}
        </DialogContent>
        <DialogActions sx={{ borderTop: 1, borderColor: 'divider', pt: 2, pb: 2, px: 3 }}>
          <Button onClick={() => setLoadDialogOpen(false)} variant="outlined">
            Close
          </Button>
        </DialogActions>
      </Dialog>
      
      {/* Edit Node Dialog */}
      <Dialog 
        open={editDialogOpen} 
        onClose={() => setEditDialogOpen(false)} 
        maxWidth="sm" 
        fullWidth
        PaperProps={{
          sx: {
            border: 2,
            borderColor: 'divider',
          }
        }}
      >
        <DialogTitle sx={{ borderBottom: 1, borderColor: 'divider', pb: 2 }}>
          Edit {editingNode?.type || 'Node'}
        </DialogTitle>
        <DialogContent sx={{ pt: 3 }}>
          {editingNode && (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
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
        <DialogActions sx={{ borderTop: 1, borderColor: 'divider', pt: 2, pb: 2, px: 3 }}>
          <Button onClick={() => setEditDialogOpen(false)} variant="outlined">
            Cancel
          </Button>
          <Button onClick={handleSaveEdit} variant="contained">
            Save
          </Button>
        </DialogActions>
      </Dialog>
      
      {/* AI Generate Confirmation Dialog */}
      {aiGenerateConfirmOpen !== undefined && setAiGenerateConfirmOpen && handleConfirmAIGenerate && (
        <Dialog 
          open={aiGenerateConfirmOpen} 
          onClose={() => setAiGenerateConfirmOpen(false)}
          maxWidth="sm"
          fullWidth
          PaperProps={{
            sx: {
              border: 2,
              borderColor: 'warning.main',
            }
          }}
        >
          <DialogTitle sx={{ borderBottom: 1, borderColor: 'divider', pb: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <ErrorIcon color="warning" />
              <Typography variant="h6">Unsaved Changes</Typography>
            </Box>
          </DialogTitle>
          <DialogContent sx={{ pt: 3 }}>
            <Alert severity="warning" sx={{ mb: 2 }}>
              <Typography variant="body2">
                You have an existing test case with unsaved changes. 
                Generating a new AI test case will <strong>replace</strong> the current graph.
              </Typography>
            </Alert>
            <Typography variant="body2" color="text.secondary">
              <strong>Options:</strong>
            </Typography>
            <Box component="ul" sx={{ mt: 1, ml: 2 }}>
              <Typography component="li" variant="body2" color="text.secondary">
                <strong>Cancel</strong> - Save your current work first
              </Typography>
              <Typography component="li" variant="body2" color="text.secondary">
                <strong>Continue</strong> - Replace current graph (changes will be lost)
              </Typography>
            </Box>
          </DialogContent>
          <DialogActions sx={{ borderTop: 1, borderColor: 'divider', pt: 2, pb: 2, px: 3 }}>
            <Button 
              onClick={() => setAiGenerateConfirmOpen(false)} 
              variant="outlined"
            >
              Cancel
            </Button>
            <Button 
              onClick={handleConfirmAIGenerate} 
              variant="contained" 
              color="warning"
            >
              Continue & Replace
            </Button>
          </DialogActions>
        </Dialog>
      )}
    </>
  );
};

