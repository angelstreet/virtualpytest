/**
 * AI Test Case Generator Page - Clean Modern Implementation
 * No legacy code, no backward compatibility, AI-focused only
 */

import React from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
} from '@mui/material';

import { AITestCaseGenerator } from '../components/testcase/AITestCaseGenerator';
import { TestCase } from '../types/pages/TestCase_Types';

const TestCaseEditor: React.FC = () => {
  const handleTestCaseGenerated = (testCase: TestCase) => {
    console.log('AI Generated Test Case:', testCase);
    // Test case is automatically saved by the AI generator
    // Future: Could add success notification or redirect to test case list
  };

  return (
    <Box sx={{ p: 3, maxWidth: 1200, mx: 'auto' }}>
      {/* Header */}
      <Box sx={{ mb: 4, textAlign: 'center' }}>
        <Typography variant="h4" component="h1" sx={{ mb: 1, fontWeight: 600 }}>
          AI Test Case Generator
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Generate executable test cases from natural language descriptions
        </Typography>
      </Box>

      {/* AI Generator */}
      <Card elevation={2}>
        <CardContent sx={{ p: 4 }}>
          <AITestCaseGenerator onTestCaseGenerated={handleTestCaseGenerated} />
        </CardContent>
      </Card>
    </Box>
  );
};

export default TestCaseEditor;