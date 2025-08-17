/**
 * AI Test Case Generator Component - Two-Step Process
 * Step 1: Analysis -> Step 2: Generation
 * Clean modern implementation with no fallbacks
 */

import React, { useState, useCallback } from 'react';
import {
  Box,
  TextField,
  Button,
  Typography,
  Alert,
  CircularProgress,
  Card,
  Checkbox,
  FormControlLabel,
  List,
  ListItem,
  ListItemText,
  Divider,
  Chip,
  Stack
} from '@mui/material';
import { 
  AutoAwesome as AIIcon,
  Analytics as AnalyticsIcon,
  Check as CheckIcon,
  Warning as WarningIcon
} from '@mui/icons-material';

import { useAITestCase } from '../../hooks/aiagent/useAITestCase';
import { AIAnalysisResponse, TestCase } from '../../types/pages/TestCase_Types';

interface AITestCaseGeneratorProps {
  onTestCasesCreated: (testCases: TestCase[]) => void;
  onCancel: () => void;
}

type GenerationStep = 'input' | 'analysis' | 'generation';

export const AITestCaseGenerator: React.FC<AITestCaseGeneratorProps> = ({
  onTestCasesCreated,
  onCancel
}) => {
  // State management
  const [currentStep, setCurrentStep] = useState<GenerationStep>('input');
  const [prompt, setPrompt] = useState('');
  const [analysis, setAnalysis] = useState<AIAnalysisResponse | null>(null);
  const [selectedInterfaces, setSelectedInterfaces] = useState<string[]>([]);
  
  // Hook for AI operations
  const { 
    analyzeTestCase, 
    generateTestCases, 
    isAnalyzing, 
    isGenerating, 
    error 
  } = useAITestCase();

  // Helper function to get sample prompts
  const getSamplePrompts = () => [
    "Go to live and check audio",
    "Navigate to settings and change language to English", 
    "Go to live TV and zap 3 times, verify audio and video each time",
    "Open recordings and play the first video",
    "Check system information and verify all details are correct"
  ];

  // Step 1: Handle analysis
  const handleAnalyze = useCallback(async () => {
    if (!prompt.trim()) return;

    try {
      const analysisResult = await analyzeTestCase(prompt);
      setAnalysis(analysisResult);
      setCurrentStep('analysis');
      
      // Pre-select all compatible interfaces by default
      setSelectedInterfaces(analysisResult.compatibility_matrix.compatible_userinterfaces);
    } catch (err) {
      console.error('Analysis failed:', err);
      // Error is already handled by the hook
    }
  }, [prompt, analyzeTestCase]);

  // Step 2: Handle generation
  const handleGenerate = useCallback(async () => {
    if (!analysis || selectedInterfaces.length === 0) return;

    try {
      const generatedTestCases = await generateTestCases(
        analysis.analysis_id,
        selectedInterfaces
      );
      
      if (generatedTestCases.length > 0) {
        onTestCasesCreated(generatedTestCases);
      }
    } catch (err) {
      console.error('Generation failed:', err);
      // Error is already handled by the hook
    }
  }, [analysis, selectedInterfaces, generateTestCases, onTestCasesCreated]);

  // Interface toggle handler
  const handleInterfaceToggle = useCallback((interfaceName: string) => {
    setSelectedInterfaces(prev => 
      prev.includes(interfaceName)
        ? prev.filter(name => name !== interfaceName)
        : [...prev, interfaceName]
    );
  }, []);

  // Helper to get devices for an interface (mock data for now)
  const getDevicesForInterface = useCallback((interfaceName: string): string[] => {
    // This would come from actual device data in production
    const deviceMap: Record<string, string[]> = {
      'horizon_android_mobile': ['Samsung Galaxy', 'Pixel 6'],
      'horizon_android_tv': ['NVIDIA Shield', 'Sony Bravia'],
      'web_interface': ['Chrome Browser', 'Firefox Browser']
    };
    return deviceMap[interfaceName] || ['Compatible Device'];
  }, []);

  // Render Step 1: Input
  const renderInputStep = () => (
    <Box>
      <Stack spacing={3}>
        <Box sx={{ textAlign: 'center' }}>
          <AIIcon sx={{ fontSize: 48, color: 'primary.main', mb: 2 }} />
          <Typography variant="h5" gutterBottom>
            🤖 Describe Your Test Case
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Use natural language to describe what you want to test
          </Typography>
        </Box>

        <TextField
          fullWidth
          multiline
          rows={3}
          placeholder="Go to live and check audio"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          variant="outlined"
        />

        {/* Sample prompts */}
        <Box>
          <Typography variant="subtitle2" gutterBottom>
            Sample prompts:
          </Typography>
          <Stack direction="row" spacing={1} flexWrap="wrap" gap={1}>
            {getSamplePrompts().map((sample, index) => (
              <Chip
                key={index}
                label={sample}
                variant="outlined"
                size="small"
                onClick={() => setPrompt(sample)}
                sx={{ cursor: 'pointer' }}
              />
            ))}
          </Stack>
        </Box>

        <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 3 }}>
          <Button
            variant="contained"
            onClick={handleAnalyze}
            disabled={!prompt.trim() || isAnalyzing}
            startIcon={isAnalyzing ? <CircularProgress size={16} /> : <AnalyticsIcon />}
            size="large"
          >
            {isAnalyzing ? 'Analyzing...' : 'Analyze Compatibility'}
          </Button>
        </Box>
      </Stack>
    </Box>
  );

  // Render Step 2: Analysis Results
  const renderAnalysisStep = () => {
    if (!analysis) return null;

    const { compatibility_matrix } = analysis;
    const hasCompatible = compatibility_matrix.compatible_userinterfaces.length > 0;
    const hasIncompatible = compatibility_matrix.incompatible.length > 0;

    return (
      <Box>
        <Stack spacing={3}>
          <Box sx={{ textAlign: 'center' }}>
            <AnalyticsIcon sx={{ fontSize: 48, color: 'success.main', mb: 2 }} />
            <Typography variant="h5" gutterBottom>
              🔍 Compatibility Analysis
            </Typography>
          </Box>

          {/* AI Understanding */}
          <Alert severity="info">
            <Typography variant="subtitle2">AI Understanding:</Typography>
            <Typography>{analysis.understanding}</Typography>
          </Alert>

          {/* Analysis Stats */}
          <Box sx={{ display: 'flex', justifyContent: 'center', gap: 3 }}>
            <Chip 
              label={`${analysis.compatible_count} Compatible`} 
              color="success" 
              icon={<CheckIcon />}
            />
            <Chip 
              label={`${analysis.total_analyzed} Total Analyzed`} 
              variant="outlined"
            />
            <Chip 
              label={analysis.estimated_complexity.toUpperCase()} 
              color={analysis.estimated_complexity === 'low' ? 'success' : 
                     analysis.estimated_complexity === 'medium' ? 'warning' : 'error'}
            />
          </Box>

          {/* Compatible Interfaces */}
          {hasCompatible && (
            <Box>
              <Typography variant="h6" gutterBottom>
                ✅ Compatible User Interfaces
              </Typography>
              <List>
                {compatibility_matrix.compatible_userinterfaces.map((interfaceName) => (
                  <ListItem key={interfaceName} sx={{ pl: 0 }}>
                    <Card sx={{ width: '100%', p: 2 }}>
                      <FormControlLabel
                        control={
                          <Checkbox
                            checked={selectedInterfaces.includes(interfaceName)}
                            onChange={() => handleInterfaceToggle(interfaceName)}
                          />
                        }
                        label={
                          <Box>
                            <Typography variant="body1" fontWeight="bold">
                              {interfaceName}
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                              Compatible devices: {getDevicesForInterface(interfaceName).join(', ')}
                            </Typography>
                            <Typography variant="caption" color="success.main">
                              ✅ {compatibility_matrix.reasons[interfaceName]}
                            </Typography>
                          </Box>
                        }
                      />
                    </Card>
                  </ListItem>
                ))}
              </List>
            </Box>
          )}

          {/* Incompatible Interfaces */}
          {hasIncompatible && (
            <Box>
              <Typography variant="h6" gutterBottom>
                ⚠️ Incompatible User Interfaces
              </Typography>
              <Alert severity="warning">
                <List dense>
                  {compatibility_matrix.incompatible.map((interfaceName) => (
                    <ListItem key={interfaceName} sx={{ pl: 0 }}>
                      <ListItemText
                        primary={<strong>{interfaceName}</strong>}
                        secondary={compatibility_matrix.reasons[interfaceName]}
                      />
                    </ListItem>
                  ))}
                </List>
              </Alert>
            </Box>
          )}

          {/* Action Buttons */}
          <Stack direction="row" justifyContent="space-between" sx={{ mt: 4 }}>
            <Button 
              onClick={() => setCurrentStep('input')} 
              variant="outlined"
            >
              Back
            </Button>
            <Button
              variant="contained"
              onClick={handleGenerate}
              disabled={selectedInterfaces.length === 0 || isGenerating}
              startIcon={isGenerating ? <CircularProgress size={16} /> : <AIIcon />}
              size="large"
            >
              {isGenerating 
                ? 'Generating...' 
                : `Generate ${selectedInterfaces.length} Test Case${selectedInterfaces.length !== 1 ? 's' : ''}`
              }
            </Button>
          </Stack>
        </Stack>
      </Box>
    );
  };

  // Render Step 3: Generation Progress
  const renderGenerationStep = () => (
    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', py: 4 }}>
      <Stack spacing={3} alignItems="center">
        <CircularProgress size={80} />
        <Typography variant="h5" textAlign="center">
          🔧 Generating Test Case...
        </Typography>
        <Typography variant="body1" color="text.secondary" textAlign="center">
          Creating 1 unified test case
          <br />compatible with {selectedInterfaces.length} user interface{selectedInterfaces.length !== 1 ? 's' : ''}
        </Typography>
        <Box sx={{ mt: 2 }}>
          {selectedInterfaces.map((interfaceName, index) => (
            <Chip 
              key={interfaceName}
              label={interfaceName}
              variant="outlined"
              sx={{ mr: 1, mb: 1 }}
            />
          ))}
        </Box>
      </Stack>
    </Box>
  );

  return (
    <Box sx={{ width: '100%' }}>
      {/* Error Display */}
      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          <Typography variant="subtitle2">Error:</Typography>
          <Typography>{error}</Typography>
        </Alert>
      )}

      {/* Step Content */}
      {currentStep === 'input' && renderInputStep()}
      {currentStep === 'analysis' && renderAnalysisStep()}
      {currentStep === 'generation' && renderGenerationStep()}
    </Box>
  );
};