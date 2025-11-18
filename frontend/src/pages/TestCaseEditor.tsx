import {
  Add as AddIcon,
} from '@mui/icons-material';
import {
  Box,
  Paper,
  Typography,
  Button,
} from '@mui/material';
import React, { useRef } from 'react';

// Reuse TestCaseSelector component
import { TestCaseSelector } from '../components/testcase/TestCaseSelector';
import { useConfirmDialog } from '../hooks/useConfirmDialog';
import { ConfirmDialog } from '../components/common/ConfirmDialog';

import { buildServerUrl } from '../utils/buildUrlUtils';

const TestCaseEditor: React.FC = () => {
  // Ref to access TestCaseSelector's refresh method
  const selectorRef = useRef<{ refresh: () => void }>(null);
  
  // Confirmation dialog
  const { dialogState, confirm, handleConfirm, handleCancel } = useConfirmDialog();

  // Handle testcase load - store in sessionStorage and navigate to builder
  const handleLoad = (testcaseId: string) => {
    console.log('[@TestCaseEditor] Loading testcase:', testcaseId);
    
    // Store testcase ID to load in sessionStorage
    sessionStorage.setItem('testcase_to_load', testcaseId);
    
    // Navigate to TestCase Builder (it will check sessionStorage on mount)
    window.location.href = '/builder/test-builder';
  };

  // Handle testcase delete
  const handleDelete = async (testcaseId: string, testcaseName: string) => {
    confirm({
      title: 'Confirm Delete',
      message: `Are you sure you want to delete "${testcaseName}"?`,
      confirmColor: 'error',
      onConfirm: async () => {
        try {
          const response = await fetch(buildServerUrl(`/server/testcase/${testcaseId}`), {
            method: 'DELETE',
          });

          if (!response.ok) {
            throw new Error('Failed to delete test case');
          }
          
          // After successful deletion, refresh the list
          if (selectorRef.current) {
            selectorRef.current.refresh();
          }
        } catch (err) {
          console.error('Error deleting test case:', err);
          throw err;
        }
      },
    });
  };

  // Navigate to TestCase Builder for new test case
  const handleCreateNew = () => {
    // Clear any stored testcase to load
    sessionStorage.removeItem('testcase_to_load');
    window.location.href = '/builder/test-builder';
  };

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" component="h1">
          Test Case
        </Typography>
        <Button variant="contained" startIcon={<AddIcon />} onClick={handleCreateNew}>
          Create Test Case
        </Button>
      </Box>

      {/* Reuse TestCaseSelector component - same as dialog */}
      <Paper sx={{ p: 2, flex: 1, display: 'flex', flexDirection: 'column' }}>
        <TestCaseSelector
          ref={selectorRef}
          onLoad={handleLoad}
          onDelete={handleDelete}
          selectedTestCaseId={null}
        />
      </Paper>

      {/* Confirmation Dialog */}
      <ConfirmDialog
        open={dialogState.open}
        title={dialogState.title}
        message={dialogState.message}
        confirmText={dialogState.confirmText}
        cancelText={dialogState.cancelText}
        confirmColor={dialogState.confirmColor}
        onConfirm={handleConfirm}
        onCancel={handleCancel}
      />
    </Box>
  );
};

export default TestCaseEditor;