import {
  Add as AddIcon,
} from '@mui/icons-material';
import {
  Box,
  Paper,
  Typography,
  Button,
} from '@mui/material';
import React from 'react';

// Reuse TestCaseSelector component
import { TestCaseSelector } from '../components/testcase/TestCaseSelector';

import { buildServerUrl } from '../utils/buildUrlUtils';

const TestCaseEditor: React.FC = () => {
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

  // Navigate to TestCase Builder for new test case
  const handleCreateNew = () => {
    window.location.href = '/test-creation/testcase-builder';
  };

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" component="h1">
          Test Case Management
        </Typography>
        <Button variant="contained" startIcon={<AddIcon />} onClick={handleCreateNew}>
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
    </Box>
  );
};

export default TestCaseEditor;