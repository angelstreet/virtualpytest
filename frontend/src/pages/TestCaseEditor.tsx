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

  const handleDelete = async (testId: string) => {
    try {
      setLoading(true);
      // Use correct testcases endpoint
      const response = await fetch(`/server/testcases/deleteTestCase/${testId}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        await fetchTestCases();
      } else {
        setError('Failed to delete test case');
      }
    } catch (err) {
      setError('Error deleting test case');
    } finally {
      setLoading(false);
    }
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

  const handleAITestCaseGenerated = (aiTestCase: AITestCase) => {
    // Refresh test cases list to show the newly generated one
    fetchTestCases();
    handleCloseDialog();
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
              <TableCell>Test ID</TableCell>
              <TableCell>Name</TableCell>
              <TableCell>Type</TableCell>
              <TableCell>Creator</TableCell>
              <TableCell>Priority</TableCell>
              <TableCell>Duration</TableCell>
              <TableCell>Tags</TableCell>
              <TableCell>Steps</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {testCases.length === 0 ? (
              <TableRow>
                <TableCell colSpan={9} align="center">
                  <Typography variant="body2" color="textSecondary" sx={{ py: 4 }}>
                    No test cases found. Create your first test case to get started.
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              testCases.map((testCase) => (
                <TableRow key={testCase.test_id}>
                  <TableCell>{testCase.test_id}</TableCell>
                  <TableCell>{testCase.name}</TableCell>
                  <TableCell>
                    <Chip label={testCase.test_type} size="small" variant="outlined" />
                  </TableCell>
                  <TableCell>
                    <Chip 
                      label={testCase.creator === 'ai' ? '🤖 AI' : '👤 Manual'} 
                      size="small" 
                      color={testCase.creator === 'ai' ? 'primary' : 'default'}
                      variant="outlined"
                    />
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={getPriorityLabel(testCase.priority || 1)}
                      size="small"
                      color={getPriorityColor(testCase.priority || 1) as any}
                    />
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">{testCase.estimated_duration || 60}s</Typography>
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
                    <IconButton onClick={() => handleOpenDialog(testCase)} color="primary">
                      <EditIcon />
                    </IconButton>
                    <IconButton onClick={() => handleDelete(testCase.test_id)} color="error">
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
            <AITestCaseGenerator onTestCaseGenerated={handleAITestCaseGenerated} />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancel</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default TestCaseEditor;