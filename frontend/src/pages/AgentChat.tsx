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

import React, { useState, useEffect, useRef, useCallback } from 'react';
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
} from '@mui/icons-material';
import { io, Socket } from 'socket.io-client';

// --- Constants & Configuration ---

const STORAGE_KEY_API = 'virtualpytest_anthropic_key';
const STORAGE_KEY_MESSAGES = 'virtualpytest_agent_messages';

// Sober Palette (Dark Mode Optimized)
const PALETTE = {
  background: '#1e1e1e', // Deep Charcoal
  surface: '#252526',    // Slightly lighter
  inputBg: '#2d2d2d',
  textPrimary: '#ececec',
  textSecondary: '#a1a1a3',
  accent: '#c29f82',     // "Claude" earthy brown/orange
  accentHover: '#a8866b',
  agentBubble: 'transparent',
  userBubble: '#2d2d2d',
  borderColor: '#3e3e42',
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

// --- Types ---

interface AgentEvent {
  type: string;
  agent: string;
  content: string;
  timestamp: string;
  tool_name?: string;
  tool_params?: Record<string, unknown>;
  tool_result?: unknown;
  success?: boolean;
  error?: string;
}

interface Message {
  id: string;
  role: 'user' | 'agent';
  content: string;
  agent?: string;
  timestamp: string;
  events?: AgentEvent[];
}

interface Session {
  id: string;
  mode?: string;
  active_agent?: string;
}

type Status = 'checking' | 'ready' | 'needs_key' | 'error';

// --- Components ---

const AgentChat: React.FC = () => {
  const theme = useTheme();
  const isDarkMode = theme.palette.mode === 'dark';
  
  // State
  const [status, setStatus] = useState<Status>('checking');
  const [session, setSession] = useState<Session | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentEvents, setCurrentEvents] = useState<AgentEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  
  // API Key state
  const [apiKeyInput, setApiKeyInput] = useState('');
  const [showApiKey, setShowApiKey] = useState(false);
  const [isValidating, setIsValidating] = useState(false);
  
  // Refs
  const socketRef = useRef<Socket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  
  // Server URL
  const serverUrl = typeof window !== 'undefined' && window.location.hostname !== 'localhost'
    ? `${window.location.protocol}//${window.location.hostname}:5109`
    : 'http://localhost:5109';

  // --- Effects ---

  // Load messages
  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY_MESSAGES);
    if (saved) {
      try {
        setMessages(JSON.parse(saved));
      } catch {}
    }
  }, []);

  // Save messages
  useEffect(() => {
    if (messages.length > 0) {
      localStorage.setItem(STORAGE_KEY_MESSAGES, JSON.stringify(messages));
    }
  }, [messages]);

  // Auto-scroll
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, currentEvents, scrollToBottom]);

  // Check Connectivity & Auth
  useEffect(() => {
    const checkConnection = async () => {
      try {
        const response = await fetch(`${serverUrl}/server/agent/health`);
        const data = await response.json();
        
        if (data.api_key_configured) {
          setStatus('ready');
          initializeSession();
        } else {
          const savedKey = localStorage.getItem(STORAGE_KEY_API);
          if (savedKey) {
            setStatus('ready');
            initializeSession();
          } else {
            setStatus('needs_key');
          }
        }
      } catch {
        setStatus('error');
        setError('Backend unavailable on port 5109');
      }
    };
    checkConnection();
  }, [serverUrl]);

  // --- Actions ---

  const initializeSession = async () => {
    try {
      const response = await fetch(`${serverUrl}/server/agent/sessions`, { method: 'POST' });
      const data = await response.json();
      if (data.success) {
        setSession(data.session);
        connectSocket(data.session.id);
      }
    } catch {
      setStatus('error');
    }
  };

  const connectSocket = (sessionId: string) => {
    if (socketRef.current?.connected) return;

    const socket = io(`${serverUrl}/agent`, {
      path: '/server/socket.io',
      transports: ['websocket', 'polling'],
    });

    socket.on('connect', () => {
      socket.emit('join_session', { session_id: sessionId });
    });

    socket.on('agent_event', (event: AgentEvent) => {
      setCurrentEvents(prev => [...prev, event]);
      
      // Mode Detection
      if (event.type === 'mode_detected' && session) {
         setSession(prev => prev ? { ...prev, mode: event.content.split(': ')[1] } : null);
      }

      // Agent Delegation
      if (event.type === 'agent_delegated') {
        const agentName = event.content.replace('Delegating to ', '').replace(' agent...', '');
        setSession(prev => prev ? { ...prev, active_agent: agentName } : null);
      }

      // Message Completion
      if (event.type === 'message' || event.type === 'result') {
        const newMessage: Message = {
          id: `${Date.now()}-${Math.random()}`,
          role: 'agent',
          content: event.content,
          agent: event.agent,
          timestamp: event.timestamp,
          events: [...currentEvents, event],
        };
        // Use function updater to access latest currentEvents
        setMessages(prev => [...prev, newMessage]);
        setCurrentEvents([]); // Clear current events buffer
      }
      
      if (event.type === 'session_ended') {
        setIsProcessing(false);
      }
    });

    socket.on('error', (data) => {
      setError(data.error);
      setIsProcessing(false);
    });

    socketRef.current = socket;
  };

  const saveApiKey = () => {
    if (!apiKeyInput.trim().startsWith('sk-ant-')) {
      setError('Invalid Key');
      return;
    }
    setIsValidating(true);
    localStorage.setItem(STORAGE_KEY_API, apiKeyInput.trim());
    setTimeout(() => {
      setStatus('ready');
      setIsValidating(false);
      initializeSession();
    }, 1000);
  };

  const sendMessage = () => {
    if (!input.trim() || isProcessing) return;

    const userMsg: Message = {
      id: `${Date.now()}-user`,
      role: 'user',
      content: input.trim(),
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsProcessing(true);
    setCurrentEvents([]);
    setError(null);

    socketRef.current?.emit('send_message', {
      session_id: session?.id,
      message: input.trim(),
    });
  };

  const handleApproval = (approved: boolean) => {
    socketRef.current?.emit('approve', { session_id: session?.id, approved });
  };

  const clearHistory = () => {
    setMessages([]);
    localStorage.removeItem(STORAGE_KEY_MESSAGES);
    initializeSession();
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
          <Box sx={{ textAlign: 'center', maxWidth: 600, width: '100%', p: 3 }}>
             <SparkleIcon sx={{ fontSize: 48, color: PALETTE.accent, mb: 3 }} />
             <Typography variant="h4" sx={{ fontFamily: 'serif', mb: 4, color: 'text.primary' }}>
               How can I help you test today?
             </Typography>
             
             <Paper
                elevation={0}
                sx={{
                  p: '2px 4px',
                  display: 'flex',
                  alignItems: 'center',
                  bgcolor: isDarkMode ? PALETTE.inputBg : 'grey.100',
                  border: `1px solid ${isDarkMode ? PALETTE.borderColor : '#e0e0e0'}`,
                  borderRadius: 3,
                  transition: 'all 0.2s',
                  '&:hover': {
                     borderColor: PALETTE.accent
                  }
                }}
              >
                <TextField
                  autoFocus
                  fullWidth
                  placeholder="Describe a test case or ask to automate a site..."
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
                  sx={{ ml: 2, flex: 1 }}
                  variant="standard"
                  InputProps={{ disableUnderline: true }}
                />
                <IconButton 
                   onClick={sendMessage}
                   disabled={!input.trim()}
                   sx={{ 
                     m: 1, 
                     bgcolor: input.trim() ? PALETTE.accent : 'transparent',
                     color: input.trim() ? '#fff' : 'text.disabled',
                     '&:hover': { bgcolor: PALETTE.accentHover }
                   }}
                >
                  <SendIcon />
                </IconButton>
              </Paper>
              
              <Box sx={{ mt: 3, display: 'flex', gap: 1, justifyContent: 'center', flexWrap: 'wrap' }}>
                 {['Automate sauce-demo login', 'Run regression tests', 'Why did checkout fail?'].map((suggestion) => (
                    <Chip 
                      key={suggestion} 
                      label={suggestion} 
                      onClick={() => setInput(suggestion)}
                      sx={{ 
                        bgcolor: 'transparent', 
                        border: '1px solid', 
                        borderColor: 'divider',
                        '&:hover': { borderColor: PALETTE.accent, cursor: 'pointer' }
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
      height: 'calc(100vh - 64px)', 
      display: 'flex', 
      flexDirection: 'column', 
      bgcolor: 'background.default',
      overflow: 'hidden' // Prevent outer scroll
    }}>
      
      {/* Minimal Header */}
      <Box sx={{ 
        p: 2, 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'space-between',
        borderBottom: '1px solid',
        borderColor: 'divider'
      }}>
         <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Typography variant="subtitle2" color="text.secondary">
              QA Assistant
            </Typography>
            {session?.mode && (
               <Chip label={session.mode} size="small" sx={{ height: 20, fontSize: '0.7rem', borderRadius: 1 }} />
            )}
         </Box>
         <Button size="small" color="inherit" onClick={clearHistory} sx={{ opacity: 0.5 }}>
           Clear
         </Button>
      </Box>

      {/* Chat Stream */}
      <Box sx={{ 
        flex: 1, 
        overflowY: 'auto', // Only this area scrolls
        p: 3,
        display: 'flex',
        flexDirection: 'column',
        gap: 3
      }}>
        <Container maxWidth="md">
          
          {status === 'needs_key' && (
             <Box sx={{ textAlign: 'center', mb: 4 }}>
               <Alert severity="info" sx={{ mb: 2 }}>Please configure your Anthropic API Key to proceed.</Alert>
               <Box sx={{ display: 'flex', gap: 1 }}>
                 <TextField 
                   size="small" 
                   placeholder="sk-ant-..." 
                   value={apiKeyInput} 
                   onChange={(e) => setApiKeyInput(e.target.value)} 
                   type={showApiKey ? "text" : "password"}
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
              <Box key={msg.id} sx={{ display: 'flex', flexDirection: 'column', alignItems: isUser ? 'flex-end' : 'flex-start', mb: 4 }}>
                 
                 {/* Sender Info */}
                 <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1, pl: isUser ? 0 : 1, pr: isUser ? 1 : 0 }}>
                    {!isUser ? (
                       <>
                        <Avatar sx={{ width: 20, height: 20, fontSize: 10, bgcolor: agentColor }}>{getInitials(msg.agent || 'QA')}</Avatar>
                        <Typography variant="caption" fontWeight="bold" color="text.primary">{msg.agent}</Typography>
                       </>
                    ) : (
                        <Typography variant="caption" color="text.secondary">You</Typography>
                    )}
                 </Box>

                 {/* Message Content */}
                 <Paper 
                   elevation={0}
                   sx={{ 
                     p: isUser ? 2 : 0, // Agents don't need bubble padding as much
                     px: isUser ? 2 : 1,
                     bgcolor: isUser ? (isDarkMode ? PALETTE.userBubble : 'grey.100') : 'transparent',
                     color: 'text.primary',
                     borderRadius: 2,
                     maxWidth: '85%',
                     fontSize: '1rem',
                     lineHeight: 1.6
                   }}
                 >
                    {/* Tool Logs */}
                    {!isUser && msg.events && (
                       <Box sx={{ mb: 2 }}>
                          {msg.events.filter(e => e.type === 'tool_call').map(renderToolActivity)}
                       </Box>
                    )}
                    
                    <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>
                       {msg.content}
                    </Typography>
                 </Paper>
              </Box>
            );
          })}

          {/* Processing State */}
          {isProcessing && (
            <Box sx={{ display: 'flex', gap: 2, mt: 2 }}>
               <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, width: '100%' }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                     <ThinkingIcon sx={{ animation: 'pulse 1.5s infinite', color: PALETTE.accent, fontSize: 18 }} />
                     <Typography variant="body2" color="text.secondary" sx={{ fontStyle: 'italic' }}>
                        Thinking...
                     </Typography>
                  </Box>
                  
                  {/* Live Tool Stream */}
                  <Box sx={{ pl: 3, borderLeft: `2px solid ${PALETTE.borderColor}` }}>
                     {currentEvents.map((event, idx) => {
                        if (event.type === 'tool_call') return renderToolActivity(event, idx);
                        if (event.type === 'thinking') return (
                           <Typography key={idx} variant="caption" display="block" color="text.secondary" sx={{ mb: 0.5 }}>
                              › {event.content}
                           </Typography>
                        );
                        return null;
                     })}
                  </Box>

                  {/* Approval Card */}
                  {currentEvents.some(e => e.type === 'approval_required') && (
                     <Paper variant="outlined" sx={{ p: 2, mt: 2, borderColor: PALETTE.accent, bgcolor: 'rgba(194, 159, 130, 0.05)' }}>
                        <Typography variant="subtitle2" color={PALETTE.accent} gutterBottom>
                           Permission Request
                        </Typography>
                        <Typography variant="body2" sx={{ mb: 2 }}>The agent wants to perform a critical action.</Typography>
                        <Box sx={{ display: 'flex', gap: 1 }}>
                           <Button variant="contained" size="small" onClick={() => handleApproval(true)} sx={{ bgcolor: PALETTE.accent, '&:hover': { bgcolor: PALETTE.accentHover } }}>
                              Approve
                           </Button>
                           <Button variant="outlined" size="small" color="inherit" onClick={() => handleApproval(false)}>
                              Deny
                           </Button>
                        </Box>
                     </Paper>
                  )}
               </Box>
            </Box>
          )}
          
          <div ref={messagesEndRef} />
        </Container>
      </Box>

      {/* Input Area (Sticky Bottom) */}
      <Box sx={{ p: 3, bgcolor: 'background.default' }}>
        <Container maxWidth="md">
           <Paper
                elevation={0}
                sx={{
                  p: '2px 4px',
                  display: 'flex',
                  alignItems: 'center',
                  bgcolor: isDarkMode ? PALETTE.inputBg : 'grey.50',
                  border: `1px solid ${isDarkMode ? PALETTE.borderColor : '#e0e0e0'}`,
                  borderRadius: 3,
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
                  sx={{ ml: 2, flex: 1, py: 1 }}
                  variant="standard"
                  InputProps={{ disableUnderline: true }}
                />
                <IconButton 
                   onClick={isProcessing ? () => {} : sendMessage}
                   disabled={!input.trim() && !isProcessing}
                   sx={{ 
                     m: 1, 
                     bgcolor: input.trim() ? PALETTE.accent : 'transparent',
                     color: input.trim() ? '#fff' : 'text.disabled',
                     width: 32,
                     height: 32,
                     '&:hover': { bgcolor: PALETTE.accentHover }
                   }}
                >
                  {isProcessing ? <StopIcon fontSize="small" /> : <SendIcon fontSize="small" />}
                </IconButton>
              </Paper>
        </Container>
      </Box>
    </Box>
  );
};

export default AgentChat;
