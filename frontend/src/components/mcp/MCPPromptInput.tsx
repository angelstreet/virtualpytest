import React, { useState, useCallback, useEffect, useRef } from 'react';
import {
  Box,
  Card,
  CardContent,
  TextField,
  Button,
  Stack,
  Typography,
  IconButton,
  Tooltip,
  CircularProgress,
} from '@mui/material';
import {
  Mic as MicIcon,
  MicOff as MicOffIcon,
  Send as SendIcon,
  Clear as ClearIcon,
} from '@mui/icons-material';
import { useMCPPlayground } from '../../contexts/mcp/MCPPlaygroundContext';

export const MCPPromptInput: React.FC = () => {
  const {
    prompt,
    setPrompt,
    isGenerating,
    handleGenerate,
    isControlActive,
  } = useMCPPlayground();
  
  const [isRecording, setIsRecording] = useState(false);
  const [transcript, setTranscript] = useState('');
  const recognitionRef = useRef<any>(null);
  
  // Initialize speech recognition
  useEffect(() => {
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
      const SpeechRecognition = (window as any).webkitSpeechRecognition || (window as any).SpeechRecognition;
      recognitionRef.current = new SpeechRecognition();
      recognitionRef.current.continuous = true;
      recognitionRef.current.interimResults = true;
      recognitionRef.current.lang = 'en-US';
      
      recognitionRef.current.onresult = (event: any) => {
        let interimTranscript = '';
        let finalTranscript = '';
        
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const transcript = event.results[i][0].transcript;
          if (event.results[i].isFinal) {
            finalTranscript += transcript + ' ';
          } else {
            interimTranscript += transcript;
          }
        }
        
        setTranscript(finalTranscript || interimTranscript);
        if (finalTranscript) {
          setPrompt(prev => prev + finalTranscript);
        }
      };
      
      recognitionRef.current.onerror = (event: any) => {
        console.error('Speech recognition error:', event.error);
        setIsRecording(false);
      };
      
      recognitionRef.current.onend = () => {
        setIsRecording(false);
        setTranscript('');
      };
    }
    
    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
    };
  }, [setPrompt]);
  
  // Toggle voice recording
  const toggleRecording = useCallback(() => {
    if (!recognitionRef.current) {
      alert('Speech recognition is not supported in your browser');
      return;
    }
    
    if (isRecording) {
      recognitionRef.current.stop();
      setIsRecording(false);
      setTranscript('');
    } else {
      recognitionRef.current.start();
      setIsRecording(true);
    }
  }, [isRecording]);
  
  // Handle execute
  const handleExecute = useCallback(() => {
    if (!isControlActive) {
      alert('Please take control of the device first');
      return;
    }
    
    if (!prompt.trim()) {
      return;
    }
    
    handleGenerate();
  }, [prompt, isControlActive, handleGenerate]);
  
  // Handle Enter key (Cmd/Ctrl + Enter to execute)
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      handleExecute();
    }
  }, [handleExecute]);
  
  return (
    <Card
      sx={{
        border: 1,
        borderColor: 'divider',
        boxShadow: 'none',
      }}
    >
      <CardContent sx={{ p: { xs: 2, md: 2.5 }, '&:last-child': { pb: { xs: 2, md: 2.5 } } }}>
        <Typography variant="h6" sx={{ mb: 2, fontSize: { xs: '1rem', md: '1.1rem' } }}>
          What would you like to do?
        </Typography>
        
        <Stack spacing={2}>
          {/* Text Input */}
          <TextField
            multiline
            rows={{ xs: 4, md: 3, lg: 2 }}
            placeholder="Type your command here... (e.g., 'Navigate to home', 'Verify Replay button exists', 'Swipe up 3 times')"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isGenerating}
            fullWidth
            sx={{
              '& .MuiInputBase-input': {
                fontSize: { xs: '1rem', md: '0.95rem', lg: '0.875rem' },
              },
            }}
          />
          
          {/* Voice Transcript (while recording) */}
          {isRecording && transcript && (
            <Box
              sx={{
                p: 1.5,
                bgcolor: 'action.hover',
                borderRadius: 1,
                border: 1,
                borderColor: 'primary.main',
              }}
            >
              <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
                Listening...
              </Typography>
              <Typography variant="body2" sx={{ fontStyle: 'italic' }}>
                {transcript}
              </Typography>
            </Box>
          )}
          
          {/* Action Buttons */}
          <Stack
            direction={{ xs: 'column', sm: 'row' }}
            spacing={1}
            sx={{ width: '100%' }}
          >
            {/* Voice Button */}
            <Tooltip title={isRecording ? 'Stop recording' : 'Start voice input'}>
              <Button
                variant={isRecording ? 'contained' : 'outlined'}
                color={isRecording ? 'error' : 'primary'}
                startIcon={isRecording ? <MicOffIcon /> : <MicIcon />}
                onClick={toggleRecording}
                disabled={isGenerating}
                fullWidth={{ xs: true, sm: false }}
                sx={{
                  minHeight: { xs: 56, md: 48, lg: 40 },
                  fontSize: { xs: '1rem', md: '0.9rem' },
                  minWidth: { sm: 140 },
                }}
              >
                {isRecording ? 'Stop' : 'Voice'}
              </Button>
            </Tooltip>
            
            {/* Clear Button */}
            {prompt && !isGenerating && (
              <Tooltip title="Clear prompt">
                <IconButton
                  onClick={() => setPrompt('')}
                  sx={{
                    display: { xs: 'none', sm: 'flex' },
                    alignSelf: 'center',
                  }}
                >
                  <ClearIcon />
                </IconButton>
              </Tooltip>
            )}
            
            {/* Spacer */}
            <Box sx={{ flex: 1, display: { xs: 'none', sm: 'block' } }} />
            
            {/* Execute Button */}
            <Button
              variant="contained"
              color="primary"
              startIcon={isGenerating ? <CircularProgress size={20} color="inherit" /> : <SendIcon />}
              onClick={handleExecute}
              disabled={isGenerating || !prompt.trim() || !isControlActive}
              fullWidth={{ xs: true, sm: false }}
              sx={{
                minHeight: { xs: 56, md: 48, lg: 40 },
                fontSize: { xs: '1rem', md: '0.9rem' },
                minWidth: { sm: 160 },
                fontWeight: 600,
              }}
            >
              {isGenerating ? 'Generating...' : 'Execute'}
            </Button>
          </Stack>
          
          {/* Helper Text */}
          <Typography variant="caption" color="text.secondary" sx={{ textAlign: 'center' }}>
            {!isControlActive
              ? '⚠️ Take control of the device first'
              : 'Tip: Press Cmd/Ctrl + Enter to execute quickly'}
          </Typography>
        </Stack>
      </CardContent>
    </Card>
  );
};

