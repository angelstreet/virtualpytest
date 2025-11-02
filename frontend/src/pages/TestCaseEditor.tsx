import {
  Add as AddIcon,
  Settings as SettingsIcon,
} from '@mui/icons-material';
import {
  Box,
  Paper,
  Typography,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import React, { useState } from 'react';

// Reuse TestCaseSelector component
import { TestCaseSelector } from '../components/testcase/TestCaseSelector';
import { AITestCaseGenerator } from '../components/testcase/AITestCaseGenerator';
import { TestCase as AITestCase } from '../types/pages/TestCase_Types';

import { buildServerUrl } from '../utils/buildUrlUtils';

const TestCaseEditor: React.FC = () => {
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  const handleOpenDialog = () => {
    setIsDialogOpen(true);
  };

  const handleCloseDialog = () => {
    setIsDialogOpen(false);
  };

  const handleAITestCasesCreated = (aiTestCases: AITestCase[]) => {
    handleCloseDialog();
    
    // Show success message
    const testCase = aiTestCases[0];
    const interfaceCount = testCase?.compatible_userinterfaces?.length || 1;
    console.log(`Successfully generated 1 AI test case compatible with ${interfaceCount} interface${interfaceCount > 1 ? 's' : ''}`);
  };

  // Handle testcase load (navigate to builder)
  const handleLoad = (testcaseId: string) => {
    console.log('[@TestCaseEditor] Loading testcase:', testcaseId);
    // Navigate to TestCase Builder with loaded testcase
    window.location.href = `/test-creation/testcase-builder?load=${testcaseId}`;
  };

  // Handle testcase delete
  const handleDelete = async (testcaseId: string, testcaseName: string) => {
    if (!window.confirm(`Are you sure you want to delete "${testcaseName}"?`)) {
      throw new Error('Deletion cancelled');
    }

    try {
      const response = await fetch(buildServerUrl(`/server/testcase/${testcaseId}`), {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error('Failed to delete test case');
      }
    } catch (err) {
      console.error('Error deleting test case:', err);
      throw err;
    }
  };

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" component="h1">
          Test Case Management
        </Typography>
        <Button variant="contained" startIcon={<AddIcon />} onClick={handleOpenDialog}>
          Create Test Case
        </Button>
      </Box>

      {/* Reuse TestCaseSelector component - same as dialog */}
      <Paper sx={{ p: 2, flex: 1, display: 'flex', flexDirection: 'column' }}>
        <TestCaseSelector
          onLoad={handleLoad}
          onDelete={handleDelete}
          selectedTestCaseId={null}
        />
      </Paper>

      {/* AI Test Case Generator Dialog */}
      <Dialog open={isDialogOpen} onClose={handleCloseDialog} maxWidth="lg" fullWidth>
        <DialogTitle>🤖 AI Test Case Generator</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 0 }}>
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
    </Box>
  );
};

export default TestCaseEditor;