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

interface MCPPromptInputProps {
  prompt: string;
  setPrompt: (prompt: string) => void;
  isGenerating: boolean;
  handleGenerate: () => Promise<void>;
  isControlActive: boolean;
}

export const MCPPromptInput: React.FC<MCPPromptInputProps> = ({
  prompt,
  setPrompt,
  isGenerating,
  handleGenerate,
  isControlActive,
}) => {
  
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
        height: '500px', // FIXED HEIGHT - same as Quick Actions
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <CardContent sx={{ 
        p: 2.5, 
        '&:last-child': { pb: 2.5 },
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
      }}>
        <Typography variant="h6" sx={{ mb: 2, fontSize: '1.1rem' }}>
          What would you like to do?
        </Typography>
        
        <Stack spacing={2} sx={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          {/* Text Input - Flex to fill available space */}
          <TextField
            multiline
            placeholder={
              isControlActive
                ? "Type your command here... (e.g., 'Navigate to home', 'Verify Replay button exists', 'Swipe up 3 times')"
                : "Take control of the device first"
            }
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={!isControlActive || isGenerating}
            fullWidth
            sx={{
              flex: 1,
              '& .MuiInputBase-root': {
                height: '100%',
                alignItems: 'flex-start',
              },
              '& .MuiInputBase-input': {
                height: '100% !important',
                overflow: 'auto !important',
                fontSize: '0.95rem',
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
              <span>
                <Button
                  variant={isRecording ? 'contained' : 'outlined'}
                  color={isRecording ? 'error' : 'primary'}
                  startIcon={isRecording ? <MicOffIcon /> : <MicIcon />}
                  onClick={toggleRecording}
                  disabled={!isControlActive || isGenerating}
                  sx={{
                    minHeight: { xs: 56, md: 48, lg: 40 },
                    fontSize: { xs: '1rem', md: '0.9rem' },
                    minWidth: { xs: '100%', sm: 140 },
                    width: { xs: '100%', sm: 'auto' },
                  }}
                >
                  {isRecording ? 'Stop' : 'Voice'}
                </Button>
              </span>
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
              sx={{
                minHeight: { xs: 56, md: 48, lg: 40 },
                fontSize: { xs: '1rem', md: '0.9rem' },
                minWidth: { xs: '100%', sm: 160 },
                width: { xs: '100%', sm: 'auto' },
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

