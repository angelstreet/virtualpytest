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
  Chip,
  Stack
} from '@mui/material';
import { 
  AutoAwesome as AIIcon,
  Analytics as AnalyticsIcon
} from '@mui/icons-material';

import { useAITestCase } from '../../hooks/aiagent/useAITestCase';
import { AIAnalysisResponse, TestCase } from '../../types/pages/TestCase_Types';

interface AITestCaseGeneratorProps {
  onTestCasesCreated: (testCases: TestCase[]) => void;
  onCancel: () => void;
}

type GenerationStep = 'input' | 'analysis' | 'generation';

export const AITestCaseGenerator: React.FC<AITestCaseGeneratorProps> = ({
  onTestCasesCreated
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
        {/* Compact Header */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2, p: 2, bgcolor: 'background.paper', borderRadius: 1, border: '1px solid', borderColor: 'divider' }}>
          <AnalyticsIcon sx={{ fontSize: 24, color: 'success.main' }} />
          <Box sx={{ flex: 1 }}>
            <Typography variant="h6" sx={{ mb: 0.5 }}>
              🔍 Compatibility Analysis
            </Typography>
            <Box sx={{ display: 'flex', gap: 1.5, alignItems: 'center', flexWrap: 'wrap' }}>
              <Chip size="small" label={`${analysis.compatible_count} Compatible`} color="success" />
              <Chip size="small" label={`${analysis.total_analyzed} Total`} variant="outlined" />
              <Chip size="small" label={analysis.estimated_complexity.toUpperCase()} 
                color={analysis.estimated_complexity === 'low' ? 'success' : 
                       analysis.estimated_complexity === 'medium' ? 'warning' : 'error'} />
            </Box>
          </Box>
        </Box>

        {/* AI Understanding & Context - Compact */}
        <Alert severity="info" sx={{ mb: 2 }}>
          <Typography variant="body2" sx={{ fontWeight: 'bold', mb: 0.5 }}>
            🎯 Original Prompt: <span style={{ fontWeight: 'normal' }}>{prompt}</span>
          </Typography>
          <Typography variant="body2" sx={{ fontWeight: 'bold', mb: 0.5 }}>
            🤖 AI Understanding: <span style={{ fontWeight: 'normal' }}>{analysis.understanding}</span>
          </Typography>
          <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
            📋 AI Analysis: <span style={{ fontWeight: 'normal' }}>Task analyzed for compatibility across all user interfaces</span>
          </Typography>
        </Alert>

        {/* Compatible Interfaces - Compact Grid */}
        {hasCompatible && (
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle1" gutterBottom sx={{ fontWeight: 'bold' }}>
              ✅ Compatible Interfaces ({compatibility_matrix.compatible_userinterfaces.length})
            </Typography>
            <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 1 }}>
              {compatibility_matrix.compatible_userinterfaces.map((interfaceName) => (
                <Card key={interfaceName} sx={{ p: 1.5, border: '1px solid', borderColor: 'success.light' }}>
                  <FormControlLabel
                    control={
                      <Checkbox
                        size="small"
                        checked={selectedInterfaces.includes(interfaceName)}
                        onChange={() => handleInterfaceToggle(interfaceName)}
                      />
                    }
                    label={
                      <Box>
                        <Typography variant="body2" fontWeight="bold">
                          {interfaceName}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          Devices: {getDevicesForInterface(interfaceName).join(', ')}
                        </Typography>
                        <Typography variant="caption" color="success.main" display="block">
                          ✅ {compatibility_matrix.reasons[interfaceName]}
                        </Typography>
                      </Box>
                    }
                  />
                </Card>
              ))}
            </Box>
          </Box>
        )}

        {/* Incompatible Interfaces - Compact */}
        {hasIncompatible && (
          <Alert severity="warning" sx={{ mb: 2 }}>
            <Typography variant="subtitle2" gutterBottom>
              ⚠️ Incompatible: {compatibility_matrix.incompatible.join(', ')}
            </Typography>
            {compatibility_matrix.incompatible.map((interfaceName) => (
              <Typography key={interfaceName} variant="caption" display="block">
                • {interfaceName}: {compatibility_matrix.reasons[interfaceName]}
              </Typography>
            ))}
          </Alert>
        )}

        {/* Compact Action Buttons */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 2 }}>
          <Button 
            onClick={() => setCurrentStep('input')} 
            variant="outlined"
            size="small"
          >
            ← Back
          </Button>
          <Button
            variant="contained"
            onClick={handleGenerate}
            disabled={selectedInterfaces.length === 0 || isGenerating}
            startIcon={isGenerating ? <CircularProgress size={16} /> : <AIIcon />}
          >
            {isGenerating ? 'Generating...' : `Generate Test Case for ${selectedInterfaces.length} Interface${selectedInterfaces.length !== 1 ? 's' : ''}`}
          </Button>
        </Box>
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
          {selectedInterfaces.map((interfaceName) => (
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