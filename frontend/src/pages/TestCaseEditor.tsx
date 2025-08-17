import {
  Add as AddIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  Settings as SettingsIcon,
} from '@mui/icons-material';
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Card,
  CardContent,
  CardActions,
  Grid,
  IconButton,
  Alert,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Tabs,
  Tab,
  Autocomplete,
  Slider,
} from '@mui/material';
import React, { useState, useEffect } from 'react';

// Import registration context
import { TestCase } from '../types';
import { AITestCaseGenerator } from '../components/testcase/AITestCaseGenerator';
import { TestCase as AITestCase } from '../types/pages/TestCase_Types';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`simple-tabpanel-${index}`}
      aria-labelledby={`simple-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

const TestCaseEditor: React.FC = () => {
  // Use registration context for centralized URL management
  const [testCases, setTestCases] = useState<TestCase[]>([]);
  const [isEditing, setIsEditing] = useState(false);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isDetailsDialogOpen, setIsDetailsDialogOpen] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [selectedTestCase, setSelectedTestCase] = useState<TestCase | null>(null);
  const [testCaseToDelete, setTestCaseToDelete] = useState<TestCase | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tabValue, setTabValue] = useState(0);

  const [formData, setFormData] = useState<TestCase>({
    test_id: '',
    name: '',
    test_type: 'functional',
    start_node: '',
    steps: [],
    // Simplified fields - removed device and environment dependencies
    tags: [],
    priority: 1,
    estimated_duration: 60,
  });

  useEffect(() => {
    fetchTestCases();
  }, []);

  const fetchTestCases = async () => {
    try {
      // Use correct testcases endpoint
      const response = await fetch('/server/testcases/getAllTestCases');
      if (response.ok) {
        const data = await response.json();
        setTestCases(data);
      }
    } catch (err) {
      console.error('Error fetching test cases:', err);
    }
  };

  const handleSave = async () => {
    try {
      setLoading(true);
      const method = isEditing ? 'PUT' : 'POST';
      // Use correct testcases endpoints
      const url = isEditing
        ? `/server/testcases/updateTestCase/${formData.test_id}`
        : '/server/testcases/createTestCase';

      const response = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });

      if (response.ok) {
        await fetchTestCases();
        handleCloseDialog();
      } else {
        setError('Failed to save test case');
      }
    } catch (err) {
      setError('Error saving test case');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = (testCase: TestCase) => {
    setTestCaseToDelete(testCase);
    setIsDeleteDialogOpen(true);
  };

  const handleConfirmDelete = async () => {
    if (!testCaseToDelete) return;

    try {
      setLoading(true);
      // Use correct testcases endpoint
      const response = await fetch(`/server/testcases/deleteTestCase/${testCaseToDelete.test_id}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        await fetchTestCases();
        setIsDeleteDialogOpen(false);
        setTestCaseToDelete(null);
      } else {
        setError('Failed to delete test case');
      }
    } catch (err) {
      setError('Error deleting test case');
    } finally {
      setLoading(false);
    }
  };

  const handleCancelDelete = () => {
    setIsDeleteDialogOpen(false);
    setTestCaseToDelete(null);
  };

  const handleOpenDialog = (testCase?: TestCase) => {
    if (testCase) {
      setFormData(testCase);
      setIsEditing(true);
    } else {
      setFormData({
        test_id: `test_${Date.now()}`,
        name: '',
        test_type: 'functional',
        start_node: '',
        steps: [],
        tags: [],
        priority: 1,
        estimated_duration: 60,
      });
      setIsEditing(false);
    }
    setIsDialogOpen(true);
  };

  const handleCloseDialog = () => {
    setIsDialogOpen(false);
    setError(null);
  };

  const handleAITestCasesCreated = (aiTestCases: AITestCase[]) => {
    // Refresh test cases list to show the newly generated ones
    fetchTestCases();
    handleCloseDialog();
    
    // Show success message - now always 1 unified test case
    const testCase = aiTestCases[0];
    const interfaceCount = testCase?.compatible_userinterfaces?.length || 1;
    console.log(`Successfully generated 1 AI test case compatible with ${interfaceCount} interface${interfaceCount > 1 ? 's' : ''}`);
  };

  const handleOpenTestCaseDetails = (testCase: TestCase) => {
    setSelectedTestCase(testCase);
    setIsDetailsDialogOpen(true);
  };

  const handleCloseTestCaseDetails = () => {
    setIsDetailsDialogOpen(false);
    setSelectedTestCase(null);
  };

  const handleExecuteTestCase = (testCase: TestCase) => {
    // Redirect to RunTests page with pre-filled data
    const aiScriptName = `ai_testcase_${testCase.test_id}`;
    const userinterface = testCase.compatible_userinterfaces?.[0] || 'horizon_android_mobile';
    
    // Store the script selection and parameters in localStorage for RunTests to pick up
    localStorage.setItem('preselected_script', aiScriptName);
    localStorage.setItem('preselected_userinterface', userinterface);
    localStorage.setItem('preselected_from_testcase', 'true');
    
    // Navigate to RunTests page
    window.location.href = '/run-tests';
  };

  const getPriorityColor = (priority: number) => {
    switch (priority) {
      case 1:
        return 'default';
      case 2:
        return 'primary';
      case 3:
        return 'secondary';
      case 4:
        return 'warning';
      case 5:
        return 'error';
      default:
        return 'default';
    }
  };

  const getPriorityLabel = (priority: number) => {
    switch (priority) {
      case 1:
        return 'Very Low';
      case 2:
        return 'Low';
      case 3:
        return 'Medium';
      case 4:
        return 'High';
      case 5:
        return 'Critical';
      default:
        return 'Unknown';
    }
  };

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" component="h1">
          Test Case Management
        </Typography>
        <Button variant="contained" startIcon={<AddIcon />} onClick={() => handleOpenDialog()}>
          Create Test Case
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {loading && (
        <Box display="flex" justifyContent="center" my={4}>
          <CircularProgress />
        </Box>
      )}

      <TableContainer component={Paper}>
        <Table
          sx={{
            '& .MuiTableRow-root:hover': {
              backgroundColor: (theme) =>
                theme.palette.mode === 'dark'
                  ? 'rgba(255, 255, 255, 0.08) !important'
                  : 'rgba(0, 0, 0, 0.04) !important',
            },
          }}
        >
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell>
              <TableCell>Type</TableCell>
              <TableCell>Priority</TableCell>
              <TableCell>Tags</TableCell>
              <TableCell>Steps</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {testCases.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} align="center">
                  <Typography variant="body2" color="textSecondary" sx={{ py: 4 }}>
                    No test cases found. Create your first test case to get started.
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              testCases.map((testCase) => (
                <TableRow 
                  key={testCase.test_id}
                  onClick={() => handleOpenTestCaseDetails(testCase)}
                  sx={{ 
                    cursor: 'pointer',
                    '&:hover': { backgroundColor: 'rgba(0, 0, 0, 0.04)' }
                  }}
                >
                  <TableCell>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      {testCase.creator === 'ai' && (
                        <Chip 
                          label="AI" 
                          size="small" 
                          color="primary" 
                          sx={{ fontSize: '0.7rem', height: '18px' }} 
                        />
                      )}
                      <Typography variant="body2">
                        {testCase.name}
                      </Typography>
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Chip label={testCase.test_type} size="small" variant="outlined" />
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={getPriorityLabel(testCase.priority || 1)}
                      size="small"
                      color={getPriorityColor(testCase.priority || 1) as any}
                    />
                  </TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                      {testCase.tags
                        ?.slice(0, 2)
                        .map((tag, index) => (
                          <Chip key={index} label={tag} size="small" variant="outlined" />
                        ))}
                      {(testCase.tags?.length || 0) > 2 && (
                        <Chip label={`+${(testCase.tags?.length || 0) - 2}`} size="small" />
                      )}
                    </Box>
                  </TableCell>
                  <TableCell>{testCase.steps.length}</TableCell>
                  <TableCell>
                    <IconButton 
                      onClick={(e) => {
                        e.stopPropagation();
                        handleOpenDialog(testCase);
                      }} 
                      color="primary"
                    >
                      <EditIcon />
                    </IconButton>
                    <IconButton 
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDelete(testCase);
                      }} 
                      color="error"
                    >
                      <DeleteIcon />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* AI Test Case Generator Dialog */}
      <Dialog open={isDialogOpen} onClose={handleCloseDialog} maxWidth="lg" fullWidth>
        <DialogTitle>🤖 AI Test Case Generator</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2 }}>
            <AITestCaseGenerator 
              onTestCasesCreated={handleAITestCasesCreated} 
              onCancel={handleCloseDialog}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancel</Button>
        </DialogActions>
      </Dialog>

      {/* Test Case Details Modal */}
      <Dialog 
        open={isDetailsDialogOpen} 
        onClose={handleCloseTestCaseDetails} 
        maxWidth="md" 
        fullWidth
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              {selectedTestCase?.creator === 'ai' && (
                <Chip 
                  label="AI Generated" 
                  size="small" 
                  color="primary" 
                  sx={{ fontSize: '0.7rem' }} 
                />
              )}
              <Typography variant="h6">
                {selectedTestCase?.name}
              </Typography>
            </Box>
          </Box>
        </DialogTitle>
        
        <DialogContent>
          {selectedTestCase && (
            <Box sx={{ py: 2 }}>
              {/* Original Prompt (for AI test cases) */}
              {selectedTestCase.creator === 'ai' && selectedTestCase.original_prompt && (
                <Box sx={{ mb: 3 }}>
                  <Typography variant="subtitle1" gutterBottom sx={{ fontWeight: 'bold' }}>
                    🎯 Original Prompt
                  </Typography>
                  <Alert severity="info" sx={{ mb: 2 }}>
                    <Typography variant="body2">
                      {selectedTestCase.original_prompt}
                    </Typography>
                  </Alert>
                </Box>
              )}

              {/* AI Reasoning (for AI test cases) */}
              {selectedTestCase.creator === 'ai' && selectedTestCase.ai_analysis?.reasoning && (
                <Box sx={{ mb: 3 }}>
                  <Typography variant="subtitle1" gutterBottom sx={{ fontWeight: 'bold' }}>
                    🤖 AI Analysis & Reasoning
                  </Typography>
                  <Paper sx={{ p: 2, bgcolor: 'background.default' }}>
                    <Typography variant="body2">
                      {selectedTestCase.ai_analysis.reasoning}
                    </Typography>
                  </Paper>
                </Box>
              )}

              {/* Test Case Info */}
              <Box sx={{ mb: 3 }}>
                <Typography variant="subtitle1" gutterBottom sx={{ fontWeight: 'bold' }}>
                  📋 Test Case Information
                </Typography>
                <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2 }}>
                  <Box>
                    <Typography variant="body2" color="text.secondary">Type:</Typography>
                    <Chip label={selectedTestCase.test_type} size="small" variant="outlined" />
                  </Box>
                  <Box>
                    <Typography variant="body2" color="text.secondary">Priority:</Typography>
                    <Chip 
                      label={getPriorityLabel(selectedTestCase.priority || 1)} 
                      size="small" 
                      color={getPriorityColor(selectedTestCase.priority || 1) as any}
                    />
                  </Box>
                  {selectedTestCase.compatible_userinterfaces?.length > 0 && (
                    <Box sx={{ gridColumn: '1 / -1' }}>
                      <Typography variant="body2" color="text.secondary" gutterBottom>
                        Compatible Interfaces:
                      </Typography>
                      <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                        {selectedTestCase.compatible_userinterfaces.map((ui, index) => (
                          <Chip key={index} label={ui} size="small" variant="outlined" />
                        ))}
                      </Box>
                    </Box>
                  )}
                </Box>
              </Box>

              {/* Steps & Commands */}
              <Box sx={{ mb: 3 }}>
                <Typography variant="subtitle1" gutterBottom sx={{ fontWeight: 'bold' }}>
                  ⚡ Execution Steps & Commands
                </Typography>
                {selectedTestCase.steps?.length > 0 ? (
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                    {selectedTestCase.steps.map((step, index) => (
                      <Paper key={index} sx={{ p: 2, border: '1px solid', borderColor: 'divider' }}>
                        <Typography variant="body2" sx={{ fontWeight: 'bold', mb: 1 }}>
                          Step {index + 1}: {step.type || 'action'}
                        </Typography>
                        <Box sx={{ pl: 2 }}>
                          <Typography variant="body2" color="text.secondary">
                            Command: <code>{step.command}</code>
                          </Typography>
                          {step.params && Object.keys(step.params).length > 0 && (
                            <Typography variant="body2" color="text.secondary">
                              Parameters: <code>{JSON.stringify(step.params)}</code>
                            </Typography>
                          )}
                          {step.description && (
                            <Typography variant="body2" sx={{ mt: 1 }}>
                              {step.description}
                            </Typography>
                          )}
                        </Box>
                      </Paper>
                    ))}
                  </Box>
                ) : (
                  <Typography variant="body2" color="text.secondary">
                    No steps defined for this test case.
                  </Typography>
                )}
              </Box>

              {/* Verification Conditions */}
              {selectedTestCase.verification_conditions?.length > 0 && (
                <Box sx={{ mb: 3 }}>
                  <Typography variant="subtitle1" gutterBottom sx={{ fontWeight: 'bold' }}>
                    ✅ Verification Conditions
                  </Typography>
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                    {selectedTestCase.verification_conditions.map((verification, index) => (
                      <Paper key={index} sx={{ p: 2, border: '1px solid', borderColor: 'success.main', bgcolor: 'success.50' }}>
                        <Typography variant="body2" sx={{ fontWeight: 'bold', mb: 1 }}>
                          Verification {index + 1}: {verification.verification_type}
                        </Typography>
                        <Box sx={{ pl: 2 }}>
                          {verification.command && (
                            <Typography variant="body2" color="text.secondary">
                              Command: <code>{verification.command}</code>
                            </Typography>
                          )}
                          {verification.params && (
                            <Typography variant="body2" color="text.secondary">
                              Parameters: <code>{JSON.stringify(verification.params)}</code>
                            </Typography>
                          )}
                          {verification.expected_result && (
                            <Typography variant="body2" sx={{ mt: 1 }}>
                              Expected: {verification.expected_result}
                            </Typography>
                          )}
                        </Box>
                      </Paper>
                    ))}
                  </Box>
                </Box>
              )}
            </Box>
          )}
        </DialogContent>
        
        <DialogActions>
          <Button onClick={handleCloseTestCaseDetails}>
            Close
          </Button>
          {selectedTestCase?.creator === 'ai' && (
            <Button 
              variant="contained" 
              onClick={() => {
                handleExecuteTestCase(selectedTestCase);
                handleCloseTestCaseDetails();
              }}
              startIcon={<SettingsIcon />}
            >
              Execute in RunTests
            </Button>
          )}
        </DialogActions>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={isDeleteDialogOpen} onClose={handleCancelDelete} maxWidth="sm" fullWidth>
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <DeleteIcon color="error" />
            <Typography variant="h6">
              Confirm Delete
            </Typography>
          </Box>
        </DialogTitle>
        
        <DialogContent>
          <Typography variant="body1" gutterBottom>
            Are you sure you want to delete this test case?
          </Typography>
          
          {testCaseToDelete && (
            <Box sx={{ mt: 2, p: 2, bgcolor: 'grey.100', borderRadius: 1 }}>
              <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                {testCaseToDelete.name}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                ID: {testCaseToDelete.test_id}
              </Typography>
              {testCaseToDelete.creator === 'ai' && (
                <Box sx={{ mt: 1 }}>
                  <Chip label="AI Generated" size="small" color="primary" />
                </Box>
              )}
            </Box>
          )}
          
          <Typography variant="body2" color="error" sx={{ mt: 2 }}>
            This action cannot be undone.
          </Typography>
        </DialogContent>
        
        <DialogActions>
          <Button onClick={handleCancelDelete} disabled={loading}>
            Cancel
          </Button>
          <Button 
            onClick={handleConfirmDelete} 
            color="error" 
            variant="contained"
            disabled={loading}
            startIcon={loading ? <CircularProgress size={16} /> : <DeleteIcon />}
          >
            {loading ? 'Deleting...' : 'Delete'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default TestCaseEditor;