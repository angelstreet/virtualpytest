import {
  SmartToy as AIIcon,
  Send as SendIcon,
  Clear as ClearIcon,
} from '@mui/icons-material';
import {
  Box,
  Button,
  Card,
  CardContent,
  FormControl,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  TextField,
  Typography,
  CircularProgress,
  Divider,
} from '@mui/material';
import React, { useState, useRef, useEffect } from 'react';

import { buildServerUrl } from '../../utils/buildUrlUtils';
import { useToast } from '../../hooks/useToast';

interface LogEntry {
  timestamp: string;
  level: 'info' | 'error' | 'success';
  source: 'frontend' | 'server' | 'host';
  message: string;
}

const OpenRouterDebug: React.FC = () => {
  // State
  const [selectedModel, setSelectedModel] = useState('qwen/qwen-2.5-vl-7b-instruct');
  const [prompt, setPrompt] = useState('You are controlling a TV application on a device (STB/mobile/PC).\nYour task is to navigate through the app using available commands provided.\n\nTask: "go to live"\nDevice: android_mobile\nNodes: ["ENTRY", "home", "home_tvguide", "live_fullscreen", "live", "home_movies", "home_replay", "home_saved", "tvguide_livetv", "live_fullscreen_audiomenu", "live_fullscreen_chup", "live_fullscreen_chdown", "live_chup", "live_chdown", "live_volumeup", "live_volumedown", "live_audiomenu"]\n\nCommands: ["execute_navigation", "click_element", "press_key", "wait"]\n\nRules:\n- "go to node X" → execute_navigation, target_node="X"\n- "click X" → click_element, element_id="X"\n- "press X" → press_key, key="X"\n\nCRITICAL: You MUST include an "analysis" field explaining your reasoning.\n\nExample response format:\n{"analysis": "Task requires navigating to live content. Since live node is available, I will navigate there directly.", "feasible": true, "plan": [{"step": 1, "command": "execute_navigation", "params": {"target_node": "live"}, "description": "Navigate to live content"}]}\n\nIf task is not possible:\n{"analysis": "Task cannot be completed because the requested node does not exist in the navigation tree.", "feasible": false, "plan": []}\n\nRESPOND WITH JSON ONLY. ANALYSIS FIELD IS REQUIRED:');
  const [isLoading, setIsLoading] = useState(false);
  const [logs, setLogs] = useState<LogEntry[]>([]);

  // Refs
  const logsEndRef = useRef<HTMLDivElement>(null);

  // Hooks
  const toast = useToast();

  // Available models
  const models = [
    { value: 'qwen/qwen-2.5-vl-7b-instruct', label: 'Qwen 2.5 VL 7B (Default)' },
    { value: 'microsoft/phi-3-mini-128k-instruct', label: 'Microsoft Phi-3 Mini 128K' },
    { value: 'deepseek/deepseek-chat', label: 'DeepSeek Chat' },
  ];

  // Auto-scroll logs to bottom
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  // Add log entry
  const addLog = (source: LogEntry['source'], level: LogEntry['level'], message: string) => {
    const logEntry: LogEntry = {
      timestamp: new Date().toLocaleTimeString(),
      level,
      source,
      message,
    };
    setLogs(prev => [...prev, logEntry]);
  };

  // Clear logs
  const clearLogs = () => {
    setLogs([]);
    addLog('frontend', 'info', 'Logs cleared');
  };

  // Execute OpenRouter test
  const executeTest = async () => {
    if (!prompt.trim()) {
      toast.showError('Please enter a prompt');
      return;
    }

    setIsLoading(true);
    addLog('frontend', 'info', `Starting OpenRouter test with model: ${selectedModel}`);
    addLog('frontend', 'info', `Prompt length: ${prompt.length} characters`);

    try {
      // Call the AI utils directly through the debug endpoint
      const response = await fetch(buildServerUrl('/server/aiagent/debug'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          model: selectedModel,
          prompt: prompt,
          max_tokens: 1000,
          temperature: 0.0,
        }),
      });

      addLog('server', 'info', `Server response status: ${response.status}`);

      const result = await response.json();
      
      if (response.ok && result.success) {
        addLog('server', 'success', 'OpenRouter call successful');
        addLog('host', 'info', `Provider used: ${result.provider_used || 'unknown'}`);
        addLog('host', 'info', `Response length: ${result.content?.length || 0} characters`);
        
        if (result.content) {
          addLog('host', 'success', `AI Response: ${result.content}`);
          
          // Try to parse as JSON to validate
          try {
            const parsed = JSON.parse(result.content);
            addLog('frontend', 'success', 'Response is valid JSON');
            addLog('frontend', 'info', `Parsed fields: ${Object.keys(parsed).join(', ')}`);
          } catch (e) {
            addLog('frontend', 'error', `Response is not valid JSON: ${e}`);
          }
        } else {
          addLog('frontend', 'error', 'Response content is empty');
        }
        
        toast.showSuccess('OpenRouter test completed successfully');
      } else {
        const errorMsg = result.error || 'Unknown error';
        addLog('server', 'error', `Server error: ${errorMsg}`);
        toast.showError(`Test failed: ${errorMsg}`);
      }
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Unknown error';
      addLog('frontend', 'error', `Network error: ${errorMsg}`);
      toast.showError(`Network error: ${errorMsg}`);
    } finally {
      setIsLoading(false);
    }
  };

  // Get log color based on level and source
  const getLogColor = (entry: LogEntry) => {
    if (entry.level === 'error') return '#f44336';
    if (entry.level === 'success') return '#4caf50';
    
    switch (entry.source) {
      case 'frontend': return '#2196f3';
      case 'server': return '#ff9800';
      case 'host': return '#9c27b0';
      default: return '#666';
    }
  };

  return (
    <Box sx={{ p: 3, maxWidth: 1200, mx: 'auto' }}>
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <AIIcon sx={{ mr: 2, fontSize: 32, color: 'primary.main' }} />
        <Typography variant="h4" component="h1">
          OpenRouter Debug
        </Typography>
      </Box>

      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        Test OpenRouter AI models directly with custom prompts and view detailed logs.
      </Typography>

      {/* Test Form */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" sx={{ mb: 2 }}>
            Test Configuration
          </Typography>

          {/* Model Selection */}
          <FormControl fullWidth sx={{ mb: 2 }}>
            <InputLabel>AI Model</InputLabel>
            <Select
              value={selectedModel}
              label="AI Model"
              onChange={(e) => setSelectedModel(e.target.value)}
              disabled={isLoading}
            >
              {models.map((model) => (
                <MenuItem key={model.value} value={model.value}>
                  {model.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          {/* Prompt Input */}
          <TextField
            label="Prompt"
            multiline
            rows={12}
            fullWidth
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            disabled={isLoading}
            sx={{ mb: 2 }}
            placeholder="Enter your prompt here..."
          />

          {/* Action Buttons */}
          <Box sx={{ display: 'flex', gap: 2 }}>
            <Button
              variant="contained"
              startIcon={isLoading ? <CircularProgress size={20} /> : <SendIcon />}
              onClick={executeTest}
              disabled={isLoading || !prompt.trim()}
              sx={{ minWidth: 120 }}
            >
              {isLoading ? 'Testing...' : 'Execute'}
            </Button>

            <Button
              variant="outlined"
              startIcon={<ClearIcon />}
              onClick={clearLogs}
              disabled={isLoading}
            >
              Clear Logs
            </Button>
          </Box>
        </CardContent>
      </Card>

      {/* Logs Display */}
      <Card>
        <CardContent>
          <Typography variant="h6" sx={{ mb: 2 }}>
            Debug Logs ({logs.length})
          </Typography>

          <Paper
            sx={{
              height: 400,
              overflow: 'auto',
              p: 2,
              backgroundColor: '#1a1a1a',
              fontFamily: 'monospace',
            }}
          >
            {logs.length === 0 ? (
              <Typography sx={{ color: '#666', fontStyle: 'italic' }}>
                No logs yet. Execute a test to see logs here.
              </Typography>
            ) : (
              logs.map((entry, index) => (
                <Box key={index} sx={{ mb: 1 }}>
                  <Typography
                    component="div"
                    sx={{
                      fontSize: '0.875rem',
                      color: getLogColor(entry),
                      fontFamily: 'monospace',
                      wordBreak: 'break-word',
                    }}
                  >
                    <Box component="span" sx={{ color: '#888' }}>
                      [{entry.timestamp}]
                    </Box>{' '}
                    <Box component="span" sx={{ fontWeight: 'bold', textTransform: 'uppercase' }}>
                      [{entry.source}]
                    </Box>{' '}
                    {entry.message}
                  </Typography>
                  {index < logs.length - 1 && (
                    <Divider sx={{ my: 0.5, borderColor: '#333' }} />
                  )}
                </Box>
              ))
            )}
            <div ref={logsEndRef} />
          </Paper>
        </CardContent>
      </Card>
    </Box>
  );
};

export default OpenRouterDebug;
