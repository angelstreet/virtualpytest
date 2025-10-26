/**
 * AI Execution Panel - Unified Modal AI System
 * 
 * Two execution modes:
 * 1. PROMPT: Generate graph from prompt using AIGraphBuilder (with smart preprocessing)
 * 2. LOAD: Load existing test case from database
 * 
 * After graph is ready (from either mode), shows preview and executes.
 * 
 * NO LEGACY CODE - Uses AIGraphBuilder only, no backward compatibility.
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Typography,
  TextField,
  Button,
  CircularProgress,
  Autocomplete,
  ToggleButton,
  ToggleButtonGroup,
} from '@mui/material';
import {
  SmartToy as AIIcon,
  Edit as PromptIcon,
  FolderOpen as LoadIcon,
} from '@mui/icons-material';

import { Host, Device } from '../../types/common/Host_Types';
import { getZIndex } from '../../utils/zIndexUtils';
import { AIStepDisplay } from './AIStepDisplay';
import { UserinterfaceSelector } from '../common';
import { buildServerUrl } from '../../utils/buildUrlUtils';
import { useToast } from '../../hooks/useToast';
import { APP_CONFIG } from '../../config/constants';

interface AIExecutionPanelProps {
  host: Host;
  device: Device;
  isControlActive: boolean;
  isVisible: boolean;
  // Export disambiguation state to parent for modal rendering
  onDisambiguationDataChange?: (
    data: any,
    resolve: (selections: Record<string, string>, saveToDb: boolean) => void,
    cancel: () => void
  ) => void;
}

interface TestCaseDefinition {
  testcase_id: string;
  testcase_name: string;
  graph_json: any;
  ai_analysis?: string;
  userinterface_name: string;
}

export const AIExecutionPanel: React.FC<AIExecutionPanelProps> = ({
  host,
  device,
  isControlActive,
  isVisible,
  onDisambiguationDataChange,
}) => {
  // Execution mode
  const [mode, setMode] = useState<'prompt' | 'load'>('prompt');
  
  // Prompt mode state
  const [prompt, setPrompt] = useState('');
  const [selectedUserinterface, setSelectedUserinterface] = useState<string>('');
  
  // Load mode state
  const [testCases, setTestCases] = useState<TestCaseDefinition[]>([]);
  const [selectedTestCase, setSelectedTestCase] = useState<TestCaseDefinition | null>(null);
  const [isLoadingTestCases, setIsLoadingTestCases] = useState(false);
  
  // Generated/loaded graph state
  const [graph, setGraph] = useState<any>(null);
  const [analysis, setAnalysis] = useState<string>('');
  const [isGenerating, setIsGenerating] = useState(false);
  
  // Execution state
  const [isExecuting, setIsExecuting] = useState(false);
  const [executionProgress, setExecutionProgress] = useState<any>(null);
  
  const { showError, showSuccess, showInfo } = useToast();

  // Load test cases when switching to load mode
  useEffect(() => {
    if (mode === 'load' && testCases.length === 0) {
      loadTestCases();
    }
  }, [mode]);

  // Load available test cases
  const loadTestCases = useCallback(async () => {
    setIsLoadingTestCases(true);
    try {
      const response = await fetch(
        buildServerUrl(`/server/testcase/list?team_id=${APP_CONFIG.DEFAULT_TEAM_ID}`)
      );
      
      if (!response.ok) throw new Error('Failed to load test cases');
      
      const data = await response.json();
      if (data.success) {
        setTestCases(data.testcases || []);
      }
    } catch (error) {
      console.error('[@AIExecutionPanel] Error loading test cases:', error);
      showError('Failed to load test cases');
    } finally {
      setIsLoadingTestCases(false);
    }
  }, [showError]);

  // Generate graph from prompt using AIGraphBuilder
  const handleGenerateFromPrompt = useCallback(async () => {
    if (!prompt.trim() || !selectedUserinterface) return;
    
    setIsGenerating(true);
    setGraph(null);
    setAnalysis('');
    
    try {
      console.log('[@AIExecutionPanel] Generating graph from prompt');
      
      const response = await fetch(
        buildServerUrl(`/server/ai/generatePlan?team_id=${APP_CONFIG.DEFAULT_TEAM_ID}`),
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            prompt,
            userinterface_name: selectedUserinterface,
            device_id: device.device_id,
            host_name: host.host_name,
          }),
        }
      );
      
      const result = await response.json();
      
      // Handle disambiguation
      if (result.needs_disambiguation) {
        if (onDisambiguationDataChange) {
          onDisambiguationDataChange(
            result,
            (selections, saveToDb) => {
              // Resolve disambiguation and regenerate
              handleDisambiguationResolve(selections, saveToDb);
            },
            () => {
              // Cancel
              setIsGenerating(false);
            }
          );
        }
        setIsGenerating(false);
        return;
      }
      
      if (!response.ok || !result.success) {
        throw new Error(result.error || 'Graph generation failed');
      }
      
      console.log('[@AIExecutionPanel] Graph generated successfully');
      setGraph(result.graph);
      setAnalysis(result.analysis || '');
      showSuccess('Graph generated! Review and click Execute.');
      
    } catch (error: any) {
      console.error('[@AIExecutionPanel] Generation error:', error);
      showError(error.message || 'Failed to generate graph');
    } finally {
      setIsGenerating(false);
    }
  }, [prompt, selectedUserinterface, device, host, showError, showSuccess, onDisambiguationDataChange]);

  // Handle disambiguation resolution
  const handleDisambiguationResolve = useCallback(async (
    selections: Record<string, string>,
    saveToDb: boolean
  ) => {
    setIsGenerating(true);
    
    try {
      // Save disambiguation choices if requested
      if (saveToDb) {
        await fetch(buildServerUrl('/server/ai/saveDisambiguationAndRegenerate'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            prompt,
            userinterface_name: selectedUserinterface,
            device_id: device.device_id,
            host_name: host.host_name,
            team_id: APP_CONFIG.DEFAULT_TEAM_ID,
            selections,
          }),
        });
      }
      
      // Regenerate with resolved selections
      handleGenerateFromPrompt();
    } catch (error) {
      console.error('[@AIExecutionPanel] Disambiguation resolve error:', error);
      showError('Failed to apply disambiguation');
      setIsGenerating(false);
    }
  }, [prompt, selectedUserinterface, device, host, handleGenerateFromPrompt, showError]);

  // Load test case from database
  const handleLoadTestCase = useCallback(async () => {
    if (!selectedTestCase) return;
    
    setIsGenerating(true);
    setGraph(null);
    setAnalysis('');
    
    try {
      console.log('[@AIExecutionPanel] Loading test case:', selectedTestCase.testcase_id);
      
      const response = await fetch(
        buildServerUrl(`/server/testcase/${selectedTestCase.testcase_id}?team_id=${APP_CONFIG.DEFAULT_TEAM_ID}`)
      );
      
      if (!response.ok) throw new Error('Failed to load test case');
      
      const result = await response.json();
      if (result.success && result.testcase) {
        setGraph(result.testcase.graph_json);
        setAnalysis(result.testcase.ai_analysis || 'Loaded from database');
        
        // Set userinterface from test case if available
        if (result.testcase.userinterface_name) {
          setSelectedUserinterface(result.testcase.userinterface_name);
        }
        
        showSuccess('Test case loaded! Review and click Execute.');
      }
    } catch (error: any) {
      console.error('[@AIExecutionPanel] Load error:', error);
      showError(error.message || 'Failed to load test case');
    } finally {
      setIsGenerating(false);
    }
  }, [selectedTestCase, showError, showSuccess]);

  // Execute the graph (works for both prompt-generated and loaded graphs)
  const handleExecute = useCallback(async () => {
    if (!graph) return;
    
    setIsExecuting(true);
    setExecutionProgress(null);
    
    try {
      console.log('[@AIExecutionPanel] Executing graph');
      
      // Call testcase executor with graph
      const response = await fetch(
        buildServerUrl(`/server/testcase/execute?team_id=${APP_CONFIG.DEFAULT_TEAM_ID}`),
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            device_id: device.device_id,
            host_name: host.host_name,
            userinterface_name: selectedUserinterface,
            graph_json: graph,
            async_execution: true,
          }),
        }
      );
      
      const result = await response.json();
      
      if (!response.ok || !result.success) {
        throw new Error(result.error || 'Execution failed');
      }
      
      showInfo('Executing test case...');
      
      // Start polling for progress
      pollExecutionStatus(result.execution_id);
      
    } catch (error: any) {
      console.error('[@AIExecutionPanel] Execution error:', error);
      showError(error.message || 'Failed to execute test case');
      setIsExecuting(false);
    }
  }, [graph, device, host, showError, showInfo]);

  // Poll execution status
  const pollExecutionStatus = useCallback((execId: string) => {
    const interval = setInterval(async () => {
      try {
        const response = await fetch(
          buildServerUrl(`/server/testcase/execution/${execId}/status`)
        );
        
        const result = await response.json();
        
        if (result.status === 'completed' || result.status === 'failed') {
          clearInterval(interval);
          setIsExecuting(false);
          setExecutionProgress(result);
          
          if (result.status === 'completed') {
            showSuccess('Test case completed successfully!');
          } else {
            showError('Test case execution failed');
          }
        } else {
          setExecutionProgress(result);
        }
      } catch (error) {
        console.error('[@AIExecutionPanel] Poll error:', error);
      }
    }, 1000);
  }, [showSuccess, showError]);

  // Don't render if not visible
  if (!isVisible) return null;

  return (
    <Box
      sx={{
        position: 'absolute',
        top: '50%',
        right: 10,
        transform: 'translateY(-50%)',
        zIndex: getZIndex('MODAL_CONTENT'),
        pointerEvents: 'auto',
        width: '480px',
        backgroundColor: 'rgba(0,0,0,0.9)',
        borderRadius: 2,
        border: '1px solid rgba(255,255,255,0.2)',
        backdropFilter: 'blur(10px)',
      }}
    >
      <Box sx={{ p: 2 }}>
        {/* Header */}
        <Typography
          variant="h6"
          sx={{
            color: '#ffffff',
            mb: 2,
            display: 'flex',
            alignItems: 'center',
            gap: 1,
          }}
        >
          <AIIcon />
          AI Agent
          {isExecuting && (
            <Typography variant="caption" sx={{ color: '#2196f3', ml: 1 }}>
              Executing...
            </Typography>
          )}
        </Typography>

        {/* Mode Toggle */}
        <ToggleButtonGroup
          value={mode}
          exclusive
          onChange={(_, value) => value && setMode(value)}
          fullWidth
          size="small"
          sx={{ mb: 2 }}
        >
          <ToggleButton value="prompt">
            <PromptIcon sx={{ mr: 0.5 }} fontSize="small" />
            Prompt
          </ToggleButton>
          <ToggleButton value="load">
            <LoadIcon sx={{ mr: 0.5 }} fontSize="small" />
            Load Test Case
          </ToggleButton>
        </ToggleButtonGroup>

        {/* PROMPT MODE */}
        {mode === 'prompt' && (
          <>
            <UserinterfaceSelector
              deviceModel={device.device_model}
              value={selectedUserinterface}
              onChange={setSelectedUserinterface}
              label="User Interface"
              size="small"
              fullWidth
              sx={{ mb: 2 }}
            />
            
            <TextField
              size="small"
              fullWidth
              multiline
              rows={3}
              placeholder={
                isControlActive 
                  ? "Enter task (e.g., 'Go to live TV and check audio')"
                  : "Take control of the device first to enter a prompt"
              }
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              disabled={!isControlActive || isGenerating || isExecuting}
              sx={{ mb: 2 }}
            />
            
            <Button
              variant="contained"
              fullWidth
              onClick={handleGenerateFromPrompt}
              disabled={!isControlActive || !prompt.trim() || !selectedUserinterface || isGenerating || isExecuting}
              startIcon={isGenerating ? <CircularProgress size={16} /> : undefined}
            >
              {isGenerating ? 'Generating...' : 'Generate Graph'}
            </Button>
          </>
        )}

        {/* LOAD MODE */}
        {mode === 'load' && (
          <>
            <Autocomplete
              size="small"
              options={testCases}
              getOptionLabel={(option) => option.testcase_name}
              value={selectedTestCase}
              onChange={(_, newValue) => setSelectedTestCase(newValue)}
              loading={isLoadingTestCases}
              renderInput={(params) => (
                <TextField
                  {...params}
                  placeholder="Select a test case..."
                  InputProps={{
                    ...params.InputProps,
                    endAdornment: (
                      <>
                        {isLoadingTestCases ? <CircularProgress size={20} /> : null}
                        {params.InputProps.endAdornment}
                      </>
                    ),
                  }}
                />
              )}
              sx={{ mb: 2 }}
            />
            
            <Button
              variant="contained"
              fullWidth
              onClick={handleLoadTestCase}
              disabled={!isControlActive || !selectedTestCase || isGenerating || isExecuting}
              startIcon={isGenerating ? <CircularProgress size={16} /> : undefined}
            >
              {isGenerating ? 'Loading...' : 'Load & Preview'}
            </Button>
          </>
        )}

        {/* GRAPH PREVIEW (shown after generation/load) */}
        {graph && !isExecuting && (
          <Box sx={{ mt: 2, p: 2, backgroundColor: 'rgba(255,255,255,0.05)', borderRadius: 1 }}>
            <Typography variant="subtitle2" sx={{ color: '#4caf50', mb: 1 }}>
              ✅ Graph Ready
            </Typography>
            
            {analysis && (
              <Typography variant="body2" sx={{ color: '#aaa', mb: 2, fontSize: '0.85rem' }}>
                {analysis}
              </Typography>
            )}
            
            <Typography variant="caption" sx={{ color: '#888', display: 'block', mb: 1 }}>
              {graph.nodes?.length || 0} nodes • {graph.edges?.length || 0} edges
            </Typography>
            
            <Button
              variant="contained"
              fullWidth
              color="success"
              onClick={handleExecute}
              disabled={!isControlActive}
            >
              Execute Test Case
            </Button>
          </Box>
        )}

        {/* EXECUTION PROGRESS */}
        {isExecuting && executionProgress && (
          <Box sx={{ mt: 2, p: 2, backgroundColor: 'rgba(255,255,255,0.05)', borderRadius: 1 }}>
            <Typography variant="subtitle2" sx={{ color: '#2196f3', mb: 1 }}>
              🔄 Executing...
            </Typography>
            
            {executionProgress.steps?.map((step: any, idx: number) => (
              <AIStepDisplay key={idx} step={step} showExpand={false} compact />
            ))}
          </Box>
        )}
      </Box>
    </Box>
  );
};
