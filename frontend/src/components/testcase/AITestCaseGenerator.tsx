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
  Checkbox,
  FormControlLabel,
  Chip,
  Stack,
  IconButton,
  Collapse
} from '@mui/material';
import { 
  AutoAwesome as AIIcon,
  Analytics as AnalyticsIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon
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
  const [expandedSteps, setExpandedSteps] = useState<Set<number>>(new Set());
  
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
      
      // Reset expanded steps for new analysis
      setExpandedSteps(new Set());
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

  // Step expansion toggle handler
  const handleStepToggle = useCallback((stepIndex: number) => {
    setExpandedSteps(prev => {
      const newSet = new Set(prev);
      if (newSet.has(stepIndex)) {
        newSet.delete(stepIndex);
      } else {
        newSet.add(stepIndex);
      }
      return newSet;
    });
  }, []);



  // Render Step 1: Input
  const renderInputStep = () => (
    <Box>
      <Stack spacing={3}>
        <Box sx={{ textAlign: 'center' }}>
          <AIIcon sx={{ fontSize: 48, color: 'primary.main', mb: 0 }} />
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
          <Stack direction="row" spacing={0.5} flexWrap="wrap" gap={0.5}>
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

        <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 1 }}>
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
    const compatibleCount = analysis.compatible_count || 0;
    const incompatibleCount = analysis.incompatible_count || 0;

    return (
      <Box>

        {/* Compatibility Summary - Compact & Collapsible */}
        <Box sx={{ 
          mb: 1, 
          bgcolor: 'background.paper', 
          borderRadius: 1, 
          border: '1px solid', 
          borderColor: 'divider'
        }}>
          {/* Header - Always Visible */}
          <Box 
            sx={{ 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'space-between',
              p: 1,
              cursor: 'pointer',
              '&:hover': { bgcolor: 'action.hover' }
            }}
            onClick={() => handleStepToggle(-2)}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>
                🎯 Compatibility Analysis
              </Typography>
              <Box sx={{ display: 'flex', gap: 2 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                  <span style={{ fontSize: '0.9em' }}>✅</span>
                  <Typography variant="body2" sx={{ fontWeight: 'bold', color: 'success.main' }}>
                    {compatibleCount}
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                  <span style={{ fontSize: '0.9em' }}>❌</span>
                  <Typography variant="body2" sx={{ fontWeight: 'bold', color: 'error.main' }}>
                    {incompatibleCount}
                  </Typography>
                </Box>
              </Box>
            </Box>
            <IconButton size="small">
              {expandedSteps.has(-2) ? <ExpandLessIcon /> : <ExpandMoreIcon />}
            </IconButton>
          </Box>

          {/* Collapsible Details */}
          <Collapse in={expandedSteps.has(-2)}>
            <Box sx={{ px: 1, pb: 1 }}>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                {analysis.compatibility_details?.map((detail, index) => (
                  <Box key={index} sx={{ 
                    display: 'flex', 
                    alignItems: 'center', 
                    gap: 1,
                    py: 0.5,
                    px: 1,
                    borderRadius: 0.5,
                    bgcolor: detail.compatible ? 'success.light' : 'error.light',
                    color: detail.compatible ? 'success.contrastText' : 'error.contrastText'
                  }}>
                    <span style={{ fontSize: '0.8em' }}>
                      {detail.compatible ? '✅' : '❌'}
                    </span>
                    <Typography variant="caption" sx={{ fontWeight: 'bold', flex: 1 }}>
                      {detail.userinterface}
                    </Typography>
                    <Typography variant="caption" sx={{ 
                      fontStyle: 'italic',
                      opacity: 0.8,
                      fontSize: '0.7rem'
                    }}>
                      {detail.compatible 
                        ? 'All capabilities available'
                        : `Missing: ${detail.missing_capabilities?.join(', ') || 'Unknown capabilities'}`
                      }
                    </Typography>
                  </Box>
                ))}
              </Box>
            </Box>
          </Collapse>
        </Box>

        {/* Step Preview - MAIN FOCUS */}
        {analysis.step_preview && analysis.step_preview.length > 0 && (
          <Box>
            <Typography variant="h6" sx={{ fontWeight: 'bold', color: 'primary.main' }}>
              📋 Generated Test Steps Preview
            </Typography>
            <Box sx={{ 
              p: 1, 
              bgcolor: 'background.paper', 
              borderRadius: 1, 
              border: '1px solid', 
              borderColor: 'primary.light',
              boxShadow: 1
            }}>
              {analysis.step_preview.map((step, index) => {
                const expanded = expandedSteps.has(index);
                
                return (
                  <Box key={index} sx={{ 
                    borderBottom: index < analysis.step_preview.length - 1 ? '1px solid' : 'none',
                    borderColor: 'divider'
                  }}>
                    {/* Main Step Row - Clickable */}
                    <Box 
                      sx={{ 
                        display: 'flex', 
                        alignItems: 'center', 
                        gap: 1, 
                        py: 0.5,
                        px: 0.5,
                        cursor: 'pointer',
                        '&:hover': { bgcolor: 'action.hover' },
                        borderRadius: 0.5
                      }}
                      onClick={() => handleStepToggle(index)}
                    >
                      <Chip 
                        label={step.step} 
                        size="small" 
                        color="primary" 
                        sx={{ minWidth: 28, height: 20, fontSize: '0.7rem' }}
                      />
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, flex: 1 }}>
                        {step.type === 'action' ? (
                          <Typography variant="body2" sx={{ fontWeight: 'bold', fontSize: '0.875rem' }}>
                            🧭 {step.description}
                          </Typography>
                        ) : (
                          <Typography variant="body2" sx={{ fontWeight: 'bold', fontSize: '0.875rem' }}>
                            🔍 {step.description}
                          </Typography>
                        )}
                      </Box>
                      <Chip 
                        label={step.type} 
                        size="small" 
                        variant="outlined"
                        color={step.type === 'action' ? 'primary' : 'secondary'}
                        sx={{ fontSize: '0.7rem', height: 20 }}
                      />
                      <IconButton size="small">
                        {expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                      </IconButton>
                    </Box>
                    
                    {/* Expanded Details - Compact one-line format */}
                    <Collapse in={expanded}>
                      <Box sx={{ ml: 6, mr: 2, mb: 1 }}>
                        {step.type === 'action' ? (
                          <Typography variant="body2" sx={{ fontFamily: 'monospace', color: 'text.primary' }}>
                            {step.command}({Object.entries(step.params || {}).map(([key, value]) => 
                              `${key}='${value}'`
                            ).join(', ')})
                          </Typography>
                        ) : (
                          <Typography variant="body2" sx={{ fontFamily: 'monospace', color: 'text.primary' }}>
                            {step.verification_type && `${step.verification_type}.`}{step.command}({Object.entries(step.params || {}).map(([key, value]) => 
                              `${key}='${value}'`
                            ).join(', ')})
                          </Typography>
                        )}
                      </Box>
                    </Collapse>
                  </Box>
                );
              })}
            </Box>
          </Box>
        )}

        {/* Compatible Interfaces - MINIMAL */}

        {/* Interface Selection - Simple Checkboxes */}
        {hasCompatible && (
          <Box>
            <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>
              🎯 Select Interfaces for Generation
            </Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
              {compatibility_matrix.compatible_userinterfaces.map((interfaceName) => (
                <FormControlLabel
                  key={interfaceName}
                  control={
                    <Checkbox
                      size="small"
                      checked={selectedInterfaces.includes(interfaceName)}
                      onChange={() => handleInterfaceToggle(interfaceName)}
                    />
                  }
                  label={
                    <Typography variant="body2" fontWeight="bold">
                      {interfaceName}
                    </Typography>
                  }
                />
              ))}
            </Box>
          </Box>
        )}

        {/* Generation Debug Panel - At Bottom */}
        <Box>
          <Box 
            sx={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: 1, 
              cursor: 'pointer',
              py: 1,
              '&:hover': { opacity: 0.7 }
            }}
            onClick={() => setExpandedSteps(prev => 
              prev.has(-1) ? new Set([...prev].filter(i => i !== -1)) : new Set([...prev, -1])
            )}
          >
            <Typography variant="subtitle2" sx={{ fontWeight: 'bold', color: 'text.secondary' }}>
              🔧 Generation Details
            </Typography>
            <IconButton size="small">
              {expandedSteps.has(-1) ? <ExpandLessIcon /> : <ExpandMoreIcon />}
            </IconButton>
          </Box>
          
          <Collapse in={expandedSteps.has(-1)}>
            <Box sx={{ ml: 2, py: 0 }}>
              {analysis.model_commands && analysis.compatibility_details ? (
                <>
                  <Typography variant="body2" sx={{ fontWeight: 'bold', mb: 1 }}>
                    Interface Analysis:
                  </Typography>
                  
                  {/* Per UserInterface Results */}
                  {analysis.compatibility_details.map((interfaceResult) => (
                    <Box key={interfaceResult.userinterface} sx={{ mb: 2, p: 1, border: '1px solid', borderColor: 'divider', borderRadius: 1 }}>
                      <Typography variant="body2" sx={{ fontWeight: 'bold', mb: 1, display: 'flex', alignItems: 'center', gap: 1 }}>
                        <span style={{ color: interfaceResult.compatible ? '#4caf50' : '#f44336' }}>
                          {interfaceResult.compatible ? '✅' : '❌'}
                        </span>
                        📱 {interfaceResult.userinterface}
                      </Typography>
                      
                      {/* Show only the actual models configured for this specific interface */}
                      {(() => {
                        // Get the actual models for this specific user interface
                        const getInterfaceModels = (interfaceName: string) => {
                          // Map interface names to their actual supported models
                          const interfaceModelMap: Record<string, string[]> = {
                            'horizon_android_mobile': ['android_mobile'],
                            'horizon_android_tv': ['android_tv','fire_tv','apple_tv'],
                            'horizon_tv': [ 'stb'], // Fire TV and STB for horizon_tv
                            'perseus_360_web': ['web'],
                          };
                          return interfaceModelMap[interfaceName] || [];
                        };
                        
                        const interfaceModels = getInterfaceModels(interfaceResult.userinterface);
                        
                        if (interfaceModels.length === 0) {
                          return (
                            <Typography variant="caption" sx={{ display: 'block', color: 'text.secondary', fontStyle: 'italic' }}>
                              No models configured for this interface
                            </Typography>
                          );
                        }
                        
                        return (
                          <Box sx={{ mt: 1 }}>
                            {/* Show commands for this interface's models - no redundant labels */}
                            {analysis.model_commands && interfaceModels.map((model: string) => {
                              const commands = analysis.model_commands?.[model];
                              if (!commands) return (
                                <Typography key={model} variant="caption" sx={{ display: 'block', color: 'error.main', fontStyle: 'italic' }}>
                                  {model}: No command data available
                                </Typography>
                              );
                              
                              return (
                                <Box key={model} sx={{ mt: 0.5 }}>
                                  <Typography variant="caption" sx={{ fontWeight: 'bold', display: 'block', mb: 0.5 }}>
                                    {commands.actions.length} actions, {commands.verifications.length} verifications
                                  </Typography>
                                  
                                  {/* Actions - Compact */}
                                  <Typography variant="caption" sx={{ color: 'primary.main', fontWeight: 'bold' }}>
                                    Actions: 
                                  </Typography>
                                  <Typography variant="caption" sx={{ display: 'block', ml: 1, fontFamily: 'monospace', fontSize: '0.65rem', mb: 0.5 }}>
                                    {commands.actions.map((a: any) => a.command).join(', ')}
                                  </Typography>
                                  
                                  {/* Verifications - Compact */}
                                  <Typography variant="caption" sx={{ color: 'secondary.main', fontWeight: 'bold' }}>
                                    Verifications: 
                                  </Typography>
                                  <Typography variant="caption" sx={{ display: 'block', ml: 1, fontFamily: 'monospace', fontSize: '0.65rem' }}>
                                    {commands.verifications.length > 0 
                                      ? commands.verifications.map((v: any) => v.command).join(', ')
                                      : 'None available'
                                    }
                                  </Typography>
                                </Box>
                              );
                            })}
                          </Box>
                        );
                      })()}
                    </Box>
                  ))}
                </>
              ) : (
                <>
                  <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                    Loading Interface Analysis...
                  </Typography>
                  <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                    Analyzing userinterface compatibility and available commands
                  </Typography>
                </>
              )}
            </Box>
          </Collapse>
        </Box>

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
            startIcon={isGenerating ? <CircularProgress size={16} /> : undefined}
          >
            {isGenerating ? 'Generating...' : 'Generate'}
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