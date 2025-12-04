/**
 * AI Agent Chat Page
 * 
 * Professional QA Assistant Interface - "Sober Dark" Edition
 * Inspired by Claude/Linear aesthetics.
 * 
 * Features:
 * - Dark-first professional UI
 * - Focus-mode input (center initially, bottom when chatting)
 * - Minimalist message stream
 * - No double scrollbars
 */

import React, { useRef, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  IconButton,
  Button,
  Alert,
  Avatar,
  Chip,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Container,
  useTheme,
  Fade,
} from '@mui/material';
import {
  ArrowUpward as SendIcon,
  AutoAwesome as SparkleIcon,
  Terminal as ConsoleIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  ExpandMore as ExpandIcon,
  Psychology as ThinkingIcon,
  Stop as StopIcon,
  Visibility,
  VisibilityOff,
  ContentCopy as CopyIcon,
  FileDownload as ExportIcon,
  DeleteOutline as ClearIcon,
} from '@mui/icons-material';
import { useAgentChat, type AgentEvent } from '../hooks/aiagent';

// --- Constants & Configuration ---

// Refined Palette (Claude-inspired warmth)
const PALETTE = {
  background: '#1a1a1a',
  surface: '#242424',
  inputBg: '#2a2a2a',
  textPrimary: '#f0f0f0',
  textSecondary: '#9a9a9a',
  accent: '#d4a574',     // Warm earthy tone
  accentHover: '#c49464',
  agentBubble: '#262626',
  agentBorder: '#333333',
  userBubble: '#3a3a3a',
  userBorder: '#4a4a4a',
  borderColor: '#383838',
  cardShadow: '0 2px 8px rgba(0,0,0,0.3)',
};

// Agent Identities (Subtle Colors)
const AGENT_CONFIG: Record<string, { color: string; label: string }> = {
  'QA Manager': { color: '#607d8b', label: 'Orchestrator' },
  'Explorer': { color: '#81c784', label: 'Explorer' },
  'Builder': { color: '#ffb74d', label: 'Builder' },
  'Executor': { color: '#e57373', label: 'Executor' },
  'Analyst': { color: '#ba68c8', label: 'Analyst' },
  'Maintainer': { color: '#4fc3f7', label: 'Maintainer' },
};

const getInitials = (name: string) => name.split(' ').map(n => n[0]).join('').substring(0, 2);

// --- Components ---

const AgentChat: React.FC = () => {
  const theme = useTheme();
  const isDarkMode = theme.palette.mode === 'dark';
  
  // Use the extracted hook
  const {
    status,
    messages,
    input,
    isProcessing,
    currentEvents,
    error,
    apiKeyInput,
    showApiKey,
    isValidating,
    setInput,
    setShowApiKey,
    setApiKeyInput,
    setError,
    sendMessage,
    saveApiKey,
    handleApproval,
    stopGeneration,
    clearHistory,
  } = useAgentChat();
  
  // Refs for UI
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, currentEvents]);

  // --- Utility Functions ---

  // Format messages for export/copy
  const formatConversation = (): string => {
    return messages.map(msg => {
      const sender = msg.role === 'user' ? 'You' : (msg.agent || 'QA Assistant');
      const timestamp = new Date(msg.timestamp || Date.now()).toLocaleString();
      return `[${timestamp}] ${sender}:\n${msg.content}\n`;
    }).join('\n---\n\n');
  };

  // Copy conversation to clipboard
  const copyToClipboard = async () => {
    const text = formatConversation();
    try {
      await navigator.clipboard.writeText(text);
      // Could add a toast notification here
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  // Export conversation as file
  const exportConversation = () => {
    const text = formatConversation();
    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `qa-chat-${new Date().toISOString().split('T')[0]}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // --- Renderers ---

  const renderToolActivity = (event: AgentEvent, idx: number) => (
    <Accordion 
      key={idx} 
      disableGutters 
      elevation={0}
      sx={{ 
        bgcolor: 'transparent',
        border: 'none',
        '&:before': { display: 'none' },
        mb: 0.5
      }}
    >
      <AccordionSummary
        expandIcon={<ExpandIcon sx={{ fontSize: 14, color: 'text.disabled' }} />}
        sx={{ 
          minHeight: 24, 
          p: 0, 
          '& .MuiAccordionSummary-content': { my: 0 },
          flexDirection: 'row-reverse',
          gap: 1
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, width: '100%' }}>
           <ConsoleIcon sx={{ fontSize: 12, color: 'text.disabled' }} />
           <Typography variant="caption" sx={{ fontFamily: 'monospace', color: 'text.secondary', flex: 1 }}>
             {event.tool_name}
           </Typography>
           {event.success ? 
             <SuccessIcon sx={{ fontSize: 12, color: PALETTE.accent }} /> : 
             <ErrorIcon sx={{ fontSize: 12, color: 'error.main' }} />
           }
        </Box>
      </AccordionSummary>
      <AccordionDetails sx={{ p: 0, pl: 3 }}>
        <Paper 
          variant="outlined" 
          sx={{ 
            p: 1.5, 
            bgcolor: isDarkMode ? 'rgba(0,0,0,0.2)' : 'grey.50',
            borderColor: isDarkMode ? 'rgba(255,255,255,0.1)' : 'grey.300',
            borderRadius: 2
          }}
        >
           <Typography variant="caption" display="block" color="text.secondary" gutterBottom>Input</Typography>
           <Box component="pre" sx={{ m: 0, fontSize: '0.7rem', overflow: 'auto', color: 'text.primary' }}>
             {JSON.stringify(event.tool_params, null, 2)}
           </Box>
           {event.tool_result !== undefined && event.tool_result !== null && (
             <>
               <Typography variant="caption" display="block" color="text.secondary" gutterBottom sx={{ mt: 1 }}>Result</Typography>
               <Box component="pre" sx={{ m: 0, fontSize: '0.7rem', overflow: 'auto', color: 'text.primary', maxHeight: 200 }}>
                  {typeof event.tool_result === 'string' ? event.tool_result : JSON.stringify(event.tool_result, null, 2)}
               </Box>
             </>
           )}
        </Paper>
      </AccordionDetails>
    </Accordion>
  );

  // Empty State / Focus Mode
  if (status === 'ready' && messages.length === 0) {
    return (
      <Box sx={{ 
        height: 'calc(100vh - 64px)', // Adjust based on your app header
        display: 'flex', 
        flexDirection: 'column', 
        alignItems: 'center', 
        justifyContent: 'center',
        bgcolor: 'background.default'
      }}>
        <Fade in timeout={800}>
          <Box sx={{ textAlign: 'center', maxWidth: 640, width: '100%', p: 4 }}>
             {/* Logo/Icon */}
             <Box sx={{ 
               display: 'inline-flex',
               alignItems: 'center',
               justifyContent: 'center',
               width: 72,
               height: 72,
               borderRadius: '50%',
               bgcolor: `${PALETTE.accent}15`,
               mb: 3
             }}>
               <SparkleIcon sx={{ fontSize: 36, color: PALETTE.accent }} />
             </Box>
             
             <Typography 
               variant="h4" 
               sx={{ 
                 fontWeight: 500, 
                 mb: 1.5, 
                 color: 'text.primary',
                 letterSpacing: '-0.02em'
               }}
             >
               QA Assistant
             </Typography>
             <Typography 
               variant="body1" 
               sx={{ 
                 mb: 4, 
                 color: 'text.secondary',
                 maxWidth: 400,
                 mx: 'auto'
               }}
             >
               I can help you automate tests, run regressions, and analyze failures.
             </Typography>
             
             {/* Input Card */}
             <Paper
                elevation={0}
                sx={{
                  p: 1,
                  display: 'flex',
                  alignItems: 'center',
                  bgcolor: isDarkMode ? PALETTE.inputBg : '#fff',
                  border: '1px solid',
                  borderColor: isDarkMode ? PALETTE.borderColor : 'grey.300',
                  borderRadius: 3,
                  boxShadow: isDarkMode ? PALETTE.cardShadow : '0 2px 8px rgba(0,0,0,0.08)',
                  transition: 'all 0.2s',
                  '&:hover': {
                     borderColor: PALETTE.accent,
                     boxShadow: isDarkMode ? '0 4px 12px rgba(0,0,0,0.4)' : '0 4px 12px rgba(0,0,0,0.12)'
                  },
                  '&:focus-within': {
                     borderColor: PALETTE.accent,
                  }
                }}
              >
                <TextField
                  autoFocus
                  fullWidth
                  placeholder="What would you like to test?"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
                  sx={{ ml: 1.5, flex: 1 }}
                  variant="standard"
                  autoComplete="off"
                  InputProps={{ 
                    disableUnderline: true,
                    sx: { fontSize: '1rem' }
                  }}
                />
                <IconButton 
                   onClick={sendMessage}
                   disabled={!input.trim()}
                   sx={{ 
                     m: 0.5, 
                     width: 40,
                     height: 40,
                     bgcolor: input.trim() ? PALETTE.accent : 'transparent',
                     color: input.trim() ? '#fff' : 'text.disabled',
                     transition: 'all 0.2s',
                     '&:hover': { 
                       bgcolor: input.trim() ? PALETTE.accentHover : 'transparent',
                       transform: input.trim() ? 'scale(1.05)' : 'none'
                     }
                   }}
                >
                  <SendIcon fontSize="small" />
                </IconButton>
              </Paper>
              
              {/* Suggestion Chips */}
              <Box sx={{ mt: 4, display: 'flex', gap: 1.5, justifyContent: 'center', flexWrap: 'wrap' }}>
                 {[
                   '🚀 Automate web app https://sauce-demo.myshopify.com', 
                   '🧪 Run goto test case', 
                   '🔍 How many test cases are there?'
                 ].map((suggestion) => (
                    <Chip 
                      key={suggestion} 
                      label={suggestion} 
                      onClick={() => setInput(suggestion.replace(/^[^\s]+\s/, ''))}
                      sx={{ 
                        bgcolor: isDarkMode ? PALETTE.surface : 'grey.100', 
                        border: '1px solid', 
                        borderColor: isDarkMode ? PALETTE.borderColor : 'grey.200',
                        borderRadius: 2,
                        py: 2.5,
                        px: 0.5,
                        fontSize: '0.875rem',
                        transition: 'all 0.2s',
                        '&:hover': { 
                          borderColor: PALETTE.accent, 
                          bgcolor: isDarkMode ? PALETTE.agentBubble : 'grey.50',
                          cursor: 'pointer' 
                        }
                      }} 
                    />
                 ))}
              </Box>
          </Box>
        </Fade>
      </Box>
    );
  }

  // Main Chat Interface
  return (
    <Box sx={{ 
      height: 'calc(93vh - 64px)', 
      display: 'flex', 
      flexDirection: 'column', 
      bgcolor: 'background.default',
      overflow: 'hidden' // Prevent outer scroll
    }}>
      {/* Chat Stream */}
      <Box sx={{ 
        flex: 1, 
        overflowY: 'auto',
        overflowX: 'hidden',
        p: 3,
        display: 'flex',
        flexDirection: 'column',
        gap: 2,
        // Styled scrollbar - thin and subtle
        scrollbarWidth: 'thin', // Firefox
        scrollbarColor: isDarkMode ? `${PALETTE.borderColor} transparent` : '#c1c1c1 transparent',
        '&::-webkit-scrollbar': {
          width: 8,
        },
        '&::-webkit-scrollbar-track': {
          background: 'transparent',
        },
        '&::-webkit-scrollbar-thumb': {
          background: isDarkMode ? PALETTE.borderColor : '#c1c1c1',
          borderRadius: 4,
          '&:hover': {
            background: isDarkMode ? PALETTE.accent : '#a1a1a1',
          }
        },
      }}>
        <Container maxWidth="md">
          
          {status === 'needs_key' && (
             <Box sx={{ textAlign: 'center', mb: 2 }}>
               <Alert severity="info" sx={{ mb: 2 }}>Please configure your Anthropic API Key to proceed.</Alert>
               <Box sx={{ display: 'flex', gap: 1 }}>
                 <TextField 
                   size="small" 
                   placeholder="sk-ant-..." 
                   value={apiKeyInput} 
                   onChange={(e) => setApiKeyInput(e.target.value)} 
                   type={showApiKey ? "text" : "password"}
                   autoComplete="off"
                 />
                 <Button variant="contained" onClick={saveApiKey} disabled={isValidating}>Save</Button>
                 <IconButton onClick={() => setShowApiKey(!showApiKey)}>
                   {showApiKey ? <VisibilityOff /> : <Visibility />}
                 </IconButton>
               </Box>
               {error && <Typography color="error" variant="caption">{error}</Typography>}
             </Box>
          )}

          {messages.map((msg) => {
            const isUser = msg.role === 'user';
            const agentColor = AGENT_CONFIG[msg.agent || 'QA Manager']?.color;

            return (
              <Box 
                key={msg.id} 
                sx={{ 
                  display: 'flex', 
                  flexDirection: 'column', 
                  alignItems: isUser ? 'flex-end' : 'flex-start', 
                  mb: 1
                }}
              >
                 {/* Message Card */}
                 <Paper 
                   elevation={0}
                   sx={{ 
                     p: 1.5,
                     bgcolor: isDarkMode  
                       ? (isUser ? PALETTE.userBubble : PALETTE.agentBubble)
                       : (isUser ? 'grey.100' : 'grey.50'),
                     border: '1px solid',
                     borderColor: isDarkMode 
                       ? (isUser ? PALETTE.userBorder : PALETTE.agentBorder)
                       : 'grey.200',
                     borderRadius: 3,
                     maxWidth: isUser ? '75%' : '90%',
                     minWidth: isUser ? 'auto' : '60%',
                     boxShadow: isDarkMode ? PALETTE.cardShadow : '0 1px 3px rgba(0,0,0,0.1)',
                   }}
                 >
                    {/* Sender Info (inside card for agent) */}
                    {!isUser && (
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 1, pb: 1.5, borderBottom: '1px solid', borderColor: isDarkMode ? PALETTE.borderColor : 'grey.200' }}>
                        <Avatar sx={{ width: 28, height: 28, fontSize: 12, bgcolor: agentColor, fontWeight: 600 }}>
                          {getInitials(msg.agent || 'QA')}
                        </Avatar>
                        <Typography variant="subtitle2" fontWeight={600} color="text.primary">
                          {msg.agent || 'QA Manager'}
                        </Typography>
                      </Box>
                    )}

                    {/* Tool Logs */}
                    {!isUser && msg.events && msg.events.filter(e => e.type === 'tool_call').length > 0 && (
                       <Box sx={{ mb: 1, p: 1, bgcolor: isDarkMode ? 'rgba(0,0,0,0.2)' : 'grey.100', borderRadius: 2 }}>
                          {msg.events.filter(e => e.type === 'tool_call').map(renderToolActivity)}
                       </Box>
                    )}
                    
                    {/* Content (Collapsible for Reasoning/Plans) */}
                    {!isUser && msg.agent === 'QA Manager' && (msg.content.toLowerCase().includes('**plan**') || msg.content.toLowerCase().includes('**mode confirmed**') || msg.content.toLowerCase().includes('session summary')) ? (
                      <Accordion 
                        elevation={0} 
                        disableGutters
                        sx={{ 
                          bgcolor: 'transparent', 
                          '&:before': { display: 'none' },
                        }}
                      >
                        <AccordionSummary 
                          expandIcon={<ExpandIcon sx={{ color: 'text.secondary' }} />}
                          sx={{ 
                            minHeight: 'auto', 
                            p: 0,
                            '& .MuiAccordionSummary-content': { m: 0, alignItems: 'center', gap: 1 }
                          }}
                        >
                          <ThinkingIcon sx={{ fontSize: 16, color: 'text.secondary' }} />
                          <Typography variant="body2" color="text.secondary" sx={{ fontStyle: 'italic' }}>
                            View Reasoning & Plan
                          </Typography>
                        </AccordionSummary>
                        <AccordionDetails sx={{ p: 0, pt: 1 }}>
                           <Typography 
                             variant="body1" 
                             sx={{ 
                               whiteSpace: 'pre-wrap',
                               lineHeight: 1,
                               color: 'text.secondary', 
                               fontSize: '0.9rem',
                               '& p': { mb: 0 }
                             }}
                           >
                              {(msg.content || '').replace(/\n{3,}/g, '\n\n').trim()}
                           </Typography>
                        </AccordionDetails>
                      </Accordion>
                    ) : (
                      <Typography 
                        variant="body1" 
                        sx={{ 
                          whiteSpace: 'pre-wrap',
                          lineHeight: 1.6,
                          color: 'text.primary',
                          fontSize: '0.95rem',
                          '& p': { mb: 1 }
                        }}
                      >
                         {/* Clean up excessive newlines (max 1 blank line) */}
                         {(msg.content || '').replace(/\n{3,}/g, '\n\n').trim()}
                      </Typography>
                    )}

                    {/* User label (subtle, at bottom with separator) */}
                    {isUser && (
                      <Box sx={{ 
                        mt: 2, 
                        pt: 1.5, 
                        borderTop: '1px solid', 
                        borderColor: isDarkMode ? 'rgba(255,255,255,0.15)' : 'grey.200', // High contrast for visibility
                        display: 'flex',
                        justifyContent: 'flex-end'
                      }}>
                        <Typography variant="caption" sx={{ opacity: 0.6, color: 'text.secondary' }}>
                          You
                        </Typography>
                      </Box>
                    )}
                 </Paper>
              </Box>
            );
          })}

          {/* Processing State */}
          {isProcessing && (
            <Paper 
              elevation={0}
              sx={{ 
                p: 2.5,
                bgcolor: isDarkMode ? PALETTE.agentBubble : 'grey.50',
                border: '1px solid',
                borderColor: isDarkMode ? PALETTE.agentBorder : 'grey.200',
                borderRadius: 3,
                maxWidth: '90%',
                minWidth: '60%',
                boxShadow: isDarkMode ? PALETTE.cardShadow : '0 1px 3px rgba(0,0,0,0.1)',
              }}
            >
               {/* Thinking Header */}
               <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2, pb: 1.5, borderBottom: '1px solid', borderColor: isDarkMode ? PALETTE.borderColor : 'grey.200' }}>
                  <Box sx={{ 
                    display: 'flex', 
                    alignItems: 'center', 
                    justifyContent: 'center',
                    width: 28, 
                    height: 28, 
                    borderRadius: '50%',
                    bgcolor: `${PALETTE.accent}20`,
                  }}>
                    <ThinkingIcon sx={{ 
                      animation: 'pulse 1.5s infinite', 
                      color: PALETTE.accent, 
                      fontSize: 16 
                    }} />
                  </Box>
                  <Typography variant="subtitle2" fontWeight={600} color="text.primary">
                     Processing...
                  </Typography>
               </Box>
                  
               {/* Live Tool Stream */}
               {currentEvents.length > 0 && (
                 <Box sx={{ pl: 2, borderLeft: `2px solid ${PALETTE.accent}40`, mb: 2 }}>
                    {currentEvents.map((event, idx) => {
                       if (event.type === 'tool_call') return renderToolActivity(event, idx);
                       if (event.type === 'thinking') return (
                          <Typography 
                            key={idx} 
                            variant="body2" 
                            display="block" 
                            color="text.secondary" 
                            sx={{ 
                              mb: 0.5, 
                              fontSize: '0.875rem',
                              animation: 'slideIn 0.3s ease-out',
                              '@keyframes slideIn': {
                                '0%': { opacity: 0, transform: 'translateX(-8px)' },
                                '100%': { opacity: 1, transform: 'translateX(0)' },
                              },
                            }}
                          >
                             {event.content}
                          </Typography>
                       );
                       return null;
                    })}
                 </Box>
               )}

               {/* Waiting indicator when no events yet */}
               {currentEvents.length === 0 && (
                 <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, color: 'text.secondary' }}>
                   {/* Animated dots */}
                   <Box sx={{ display: 'flex', gap: 0.5 }}>
                     {[0, 1, 2].map((i) => (
                       <Box 
                         key={i}
                         sx={{ 
                           width: 6, 
                           height: 6, 
                           borderRadius: '50%', 
                           bgcolor: PALETTE.accent,
                           animation: 'bounce 1.4s ease-in-out infinite',
                           animationDelay: `${i * 0.16}s`,
                           '@keyframes bounce': {
                             '0%, 80%, 100%': { 
                               transform: 'scale(0.6)',
                               opacity: 0.4 
                             },
                             '40%': { 
                               transform: 'scale(1)',
                               opacity: 1 
                             },
                           },
                         }} 
                       />
                     ))}
                   </Box>
                   <Typography 
                     variant="body2" 
                     sx={{ 
                       fontStyle: 'italic',
                       animation: 'fadeInOut 2s ease-in-out infinite',
                       '@keyframes fadeInOut': {
                         '0%, 100%': { opacity: 0.5 },
                         '50%': { opacity: 1 },
                       },
                     }}
                   >
                     Analyzing your request
                   </Typography>
                 </Box>
               )}

               {/* Approval Card */}
               {currentEvents.some(e => e.type === 'approval_required') && (
                  <Box sx={{ 
                    p: 2, 
                    mt: 2, 
                    border: '1px solid',
                    borderColor: PALETTE.accent,
                    borderRadius: 2,
                    bgcolor: `${PALETTE.accent}10`
                  }}>
                     <Typography variant="subtitle2" sx={{ color: PALETTE.accent, fontWeight: 600 }} gutterBottom>
                        🔐 Permission Request
                     </Typography>
                     <Typography variant="body2" sx={{ mb: 2, color: 'text.secondary' }}>
                       The agent wants to perform a critical action.
                     </Typography>
                     <Box sx={{ display: 'flex', gap: 1 }}>
                        <Button 
                          variant="contained" 
                          size="small" 
                          onClick={() => handleApproval(true)} 
                          sx={{ 
                            bgcolor: PALETTE.accent, 
                            '&:hover': { bgcolor: PALETTE.accentHover },
                            textTransform: 'none',
                            fontWeight: 600
                          }}
                        >
                           Approve
                        </Button>
                        <Button 
                          variant="outlined" 
                          size="small" 
                          color="inherit" 
                          onClick={() => handleApproval(false)}
                          sx={{ textTransform: 'none' }}
                        >
                           Deny
                        </Button>
                     </Box>
                  </Box>
               )}
            </Paper>
          )}

          {/* Error Display */}
          {error && (
            <Alert 
              severity="error" 
              sx={{ mt: 2 }}
              onClose={() => setError(null)}
            >
              {error}
            </Alert>
          )}
          
          <div ref={messagesEndRef} />
        </Container>
      </Box>

      {/* Input Area (Fixed Bottom) */}
      <Box sx={{ 
        px: 3,
        py: 2,
        flexShrink: 0,
      }}>
        <Container maxWidth="md">
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
            {/* Input Box */}
            <Paper
              elevation={0}
              sx={{
                p: 1,
                flex: 1,
                display: 'flex',
                alignItems: 'center',
                bgcolor: isDarkMode ? PALETTE.inputBg : '#fff',
                border: '1px solid',
                borderColor: isDarkMode ? PALETTE.borderColor : 'grey.300',
                borderRadius: 3,
                boxShadow: isDarkMode ? PALETTE.cardShadow : '0 1px 3px rgba(0,0,0,0.08)',
                transition: 'all 0.2s',
                '&:focus-within': {
                  borderColor: PALETTE.accent,
                  boxShadow: isDarkMode 
                    ? `0 0 0 2px ${PALETTE.accent}30` 
                    : `0 0 0 2px ${PALETTE.accent}20`,
                }
              }}
            >
              <TextField
                inputRef={inputRef}
                fullWidth
                multiline
                maxRows={4}
                placeholder="Message QA Assistant..."
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && !e.shiftKey && sendMessage()}
                sx={{ ml: 1.5, flex: 1, py: 0.5 }}
                variant="standard"
                autoComplete="off"
                InputProps={{ 
                  disableUnderline: true,
                  sx: { fontSize: '0.95rem' }
                }}
              />
              <IconButton 
                onClick={isProcessing ? stopGeneration : sendMessage}
                disabled={!input.trim() && !isProcessing}
                sx={{  
                  m: 0.5, 
                  bgcolor: input.trim() ? PALETTE.accent : 'transparent',
                  color: input.trim() ? '#fff' : 'text.disabled',
                  width: 36,
                  height: 36,
                  transition: 'all 0.2s',
                  '&:hover': { 
                    bgcolor: input.trim() ? PALETTE.accentHover : 'transparent',
                    transform: input.trim() ? 'scale(1.05)' : 'none'
                  }
                }}
              >
                {isProcessing ? <StopIcon fontSize="small" /> : <SendIcon fontSize="small" />}
              </IconButton>
            </Paper>
            
            {/* Action Icons */}
            <Box sx={{ display: 'flex', gap: 0.5 }}>
              {/* Copy to Clipboard */}
              <IconButton
                size="small"
                onClick={copyToClipboard}
                disabled={messages.length === 0}
                title="Copy conversation"
                sx={{ 
                  opacity: messages.length > 0 ? 0.6 : 0.3,
                  color: 'text.secondary',
                  '&:hover': { 
                    opacity: 1,
                    color: PALETTE.accent,
                    bgcolor: isDarkMode ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)'
                  }
                }}
              >
                <CopyIcon fontSize="small" />
              </IconButton>
              
              {/* Export */}
              <IconButton
                size="small"
                onClick={exportConversation}
                disabled={messages.length === 0}
                title="Export conversation"
                sx={{ 
                  opacity: messages.length > 0 ? 0.6 : 0.3,
                  color: 'text.secondary',
                  '&:hover': { 
                    opacity: 1,
                    color: PALETTE.accent,
                    bgcolor: isDarkMode ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)'
                  }
                }}
              >
                <ExportIcon fontSize="small" />
              </IconButton>
              
              {/* Clear */}
              <IconButton
                size="small"
                onClick={clearHistory}
                disabled={messages.length === 0}
                title="Clear conversation"
                sx={{ 
                  opacity: messages.length > 0 ? 0.6 : 0.3,
                  color: 'text.secondary',
                  '&:hover': { 
                    opacity: 1,
                    color: 'error.main',
                    bgcolor: isDarkMode ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)'
                  }
                }}
              >
                <ClearIcon fontSize="small" />
              </IconButton>
            </Box>
          </Box>
        </Container>
      </Box>
    </Box>
  );
};

export default AgentChat;
