/**
 * AI Agent Chat Page
 * 
 * Chat interface for interacting with the QA Manager and specialist agents.
 * Supports modes: CREATE, VALIDATE, ANALYZE, MAINTAIN
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  IconButton,
  Chip,
  Divider,
  CircularProgress,
  Collapse,
  Button,
  Alert,
} from '@mui/material';
import {
  Send as SendIcon,
  RocketLaunch as AgentIcon,
  Build as ToolIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  ExpandMore as ExpandIcon,
  ExpandLess as CollapseIcon,
  Add as NewSessionIcon,
} from '@mui/icons-material';
import { io, Socket } from 'socket.io-client';

// Types
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
  approval?: {
    id: string;
    options: string[];
  };
}

interface Message {
  id: string;
  role: 'user' | 'agent';
  content: string;
  agent?: string;
  timestamp: Date;
  events?: AgentEvent[];
}

interface Session {
  id: string;
  mode?: string;
  active_agent?: string;
  created_at: string;
}

// Agent icon color
const AGENT_ICON_COLOR = '#FFD700'; // Gold

// Mode colors
const MODE_COLORS: Record<string, string> = {
  CREATE: '#4caf50',
  VALIDATE: '#2196f3',
  ANALYZE: '#ff9800',
  MAINTAIN: '#9c27b0',
};

// Agent colors
const AGENT_COLORS: Record<string, string> = {
  'QA Manager': '#1976d2',
  'Explorer': '#4caf50',
  'Builder': '#ff9800',
  'Executor': '#f44336',
  'Analyst': '#9c27b0',
  'Maintainer': '#00bcd4',
};

const AgentChat: React.FC = () => {
  // State
  const [session, setSession] = useState<Session | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentEvents, setCurrentEvents] = useState<AgentEvent[]>([]);
  const [expandedTools, setExpandedTools] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);
  
  // Refs
  const socketRef = useRef<Socket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  
  // Server URL
  const serverUrl = import.meta.env.VITE_SERVER_URL || 'http://localhost:5109';

  // Scroll to bottom
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, currentEvents, scrollToBottom]);

  // Create new session
  const createSession = async () => {
    try {
      const response = await fetch(`${serverUrl}/agent/sessions`, {
        method: 'POST',
      });
      const data = await response.json();
      if (data.success) {
        setSession(data.session);
        setMessages([]);
        setCurrentEvents([]);
        setError(null);
        
        // Join session room via socket
        if (socketRef.current?.connected) {
          socketRef.current.emit('join_session', { session_id: data.session.id });
        }
      }
    } catch (err) {
      setError('Failed to create session');
      console.error('Create session error:', err);
    }
  };

  // Initialize socket connection
  useEffect(() => {
    const socket = io(`${serverUrl}/agent`, {
      path: '/server/socket.io',
      transports: ['websocket', 'polling'],
    });

    socket.on('connect', () => {
      console.log('Connected to agent namespace');
      setIsConnected(true);
    });

    socket.on('disconnect', () => {
      console.log('Disconnected from agent namespace');
      setIsConnected(false);
    });

    socket.on('joined', (data: { session_id: string }) => {
      console.log('Joined session:', data.session_id);
    });

    socket.on('agent_event', (event: AgentEvent) => {
      console.log('Agent event:', event);
      
      // Add to current events
      setCurrentEvents(prev => [...prev, event]);
      
      // Handle specific event types
      if (event.type === 'message' || event.type === 'result') {
        // Create a message from the event
        const newMessage: Message = {
          id: `${Date.now()}-${Math.random()}`,
          role: 'agent',
          content: event.content,
          agent: event.agent,
          timestamp: new Date(event.timestamp),
          events: [...currentEvents, event],
        };
        setMessages(prev => [...prev, newMessage]);
        setCurrentEvents([]);
      }
      
      if (event.type === 'session_ended') {
        setIsProcessing(false);
      }
      
      if (event.type === 'mode_detected' && session) {
        setSession(prev => prev ? { ...prev, mode: event.content.split(': ')[1] } : null);
      }
      
      if (event.type === 'agent_delegated' && session) {
        const agentName = event.content.replace('Delegating to ', '').replace(' agent...', '');
        setSession(prev => prev ? { ...prev, active_agent: agentName } : null);
      }
    });

    socket.on('error', (data: { error: string }) => {
      setError(data.error);
      setIsProcessing(false);
    });

    socketRef.current = socket;

    // Create initial session
    createSession();

    return () => {
      socket.disconnect();
    };
  }, [serverUrl]);

  // Send message
  const sendMessage = () => {
    if (!input.trim() || !session || !socketRef.current?.connected || isProcessing) {
      return;
    }

    const userMessage: Message = {
      id: `${Date.now()}-user`,
      role: 'user',
      content: input.trim(),
      timestamp: new Date(),
    };
    
    setMessages(prev => [...prev, userMessage]);
    setCurrentEvents([]);
    setIsProcessing(true);
    setError(null);
    
    socketRef.current.emit('send_message', {
      session_id: session.id,
      message: input.trim(),
    });
    
    setInput('');
    inputRef.current?.focus();
  };

  // Toggle tool expansion
  const toggleTool = (toolId: string) => {
    setExpandedTools(prev => {
      const next = new Set(prev);
      if (next.has(toolId)) {
        next.delete(toolId);
      } else {
        next.add(toolId);
      }
      return next;
    });
  };

  // Handle approval
  const handleApproval = (approved: boolean) => {
    if (!session || !socketRef.current?.connected) return;
    
    socketRef.current.emit('approve', {
      session_id: session.id,
      approved,
    });
  };

  // Render tool call
  const renderToolCall = (event: AgentEvent, index: number) => {
    const toolId = `${event.tool_name}-${index}`;
    const isExpanded = expandedTools.has(toolId);
    
    return (
      <Box
        key={toolId}
        sx={{
          backgroundColor: 'rgba(0, 0, 0, 0.1)',
          borderRadius: 1,
          p: 1,
          mb: 1,
          fontSize: '0.85rem',
        }}
      >
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            cursor: 'pointer',
          }}
          onClick={() => toggleTool(toolId)}
        >
          <ToolIcon sx={{ fontSize: 16, mr: 1, color: 'text.secondary' }} />
          <Typography variant="body2" sx={{ fontFamily: 'monospace', flex: 1 }}>
            {event.tool_name}
          </Typography>
          {event.success !== undefined && (
            event.success ? (
              <SuccessIcon sx={{ fontSize: 16, color: 'success.main', mr: 1 }} />
            ) : (
              <ErrorIcon sx={{ fontSize: 16, color: 'error.main', mr: 1 }} />
            )
          )}
          {isExpanded ? <CollapseIcon /> : <ExpandIcon />}
        </Box>
        
        <Collapse in={isExpanded}>
          <Box sx={{ mt: 1, pl: 3 }}>
            {event.tool_params && (
              <Box sx={{ mb: 1 }}>
                <Typography variant="caption" color="text.secondary">Params:</Typography>
                <pre style={{ margin: 0, fontSize: '0.75rem', overflow: 'auto' }}>
                  {JSON.stringify(event.tool_params, null, 2)}
                </pre>
              </Box>
            )}
            {event.tool_result && (
              <Box>
                <Typography variant="caption" color="text.secondary">Result:</Typography>
                <pre style={{ margin: 0, fontSize: '0.75rem', overflow: 'auto', maxHeight: 200 }}>
                  {typeof event.tool_result === 'string' 
                    ? event.tool_result 
                    : JSON.stringify(event.tool_result, null, 2)}
                </pre>
              </Box>
            )}
            {event.error && (
              <Typography variant="body2" color="error.main">
                Error: {event.error}
              </Typography>
            )}
          </Box>
        </Collapse>
      </Box>
    );
  };

  // Render message
  const renderMessage = (message: Message) => {
    const isUser = message.role === 'user';
    const agentColor = message.agent ? AGENT_COLORS[message.agent] || '#666' : '#666';
    
    return (
      <Box
        key={message.id}
        sx={{
          display: 'flex',
          justifyContent: isUser ? 'flex-end' : 'flex-start',
          mb: 2,
        }}
      >
        <Box
          sx={{
            maxWidth: '80%',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          {/* Agent name badge */}
          {!isUser && message.agent && (
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 0.5 }}>
              <AgentIcon sx={{ fontSize: 16, color: AGENT_ICON_COLOR, mr: 0.5 }} />
              <Typography variant="caption" sx={{ color: agentColor, fontWeight: 600 }}>
                {message.agent}
              </Typography>
            </Box>
          )}
          
          {/* Message bubble */}
          <Paper
            elevation={1}
            sx={{
              p: 2,
              backgroundColor: isUser ? 'primary.main' : 'background.paper',
              color: isUser ? 'primary.contrastText' : 'text.primary',
              borderRadius: 2,
              borderTopRightRadius: isUser ? 0 : 2,
              borderTopLeftRadius: isUser ? 2 : 0,
            }}
          >
            {/* Tool calls (if any) */}
            {message.events?.filter(e => e.type === 'tool_call').map((event, i) => 
              renderToolCall(event, i)
            )}
            
            {/* Message content */}
            <Typography
              variant="body1"
              sx={{ whiteSpace: 'pre-wrap' }}
            >
              {message.content}
            </Typography>
            
            {/* Timestamp */}
            <Typography
              variant="caption"
              sx={{
                display: 'block',
                mt: 1,
                opacity: 0.7,
                textAlign: isUser ? 'right' : 'left',
              }}
            >
              {message.timestamp.toLocaleTimeString()}
            </Typography>
          </Paper>
        </Box>
      </Box>
    );
  };

  return (
    <Box sx={{ height: 'calc(100vh - 180px)', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2, gap: 2 }}>
        <AgentIcon sx={{ fontSize: 32, color: AGENT_ICON_COLOR }} />
        <Typography variant="h5" sx={{ flex: 1 }}>
          AI Agent
        </Typography>
        
        {/* Status chips */}
        <Chip
          label={isConnected ? 'Connected' : 'Disconnected'}
          color={isConnected ? 'success' : 'error'}
          size="small"
        />
        
        {session?.mode && (
          <Chip
            label={session.mode}
            size="small"
            sx={{ 
              backgroundColor: MODE_COLORS[session.mode] || '#666',
              color: 'white',
            }}
          />
        )}
        
        {session?.active_agent && (
          <Chip
            icon={<AgentIcon sx={{ color: '#FFD700' }} />}
            label={session.active_agent}
            size="small"
            variant="outlined"
            sx={{ 
              borderColor: AGENT_COLORS[session.active_agent] || '#666',
              color: AGENT_COLORS[session.active_agent] || '#666',
            }}
          />
        )}
        
        <IconButton onClick={createSession} title="New Session">
          <NewSessionIcon />
        </IconButton>
      </Box>
      
      <Divider sx={{ mb: 2 }} />
      
      {/* Error alert */}
      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}
      
      {/* Messages area */}
      <Paper
        elevation={0}
        sx={{
          flex: 1,
          overflow: 'auto',
          p: 2,
          backgroundColor: 'background.default',
          borderRadius: 2,
          mb: 2,
        }}
      >
        {messages.length === 0 ? (
          <Box sx={{ textAlign: 'center', py: 8 }}>
            <AgentIcon sx={{ fontSize: 64, color: 'text.disabled', mb: 2 }} />
            <Typography variant="h6" color="text.secondary" gutterBottom>
              Start a conversation
            </Typography>
            <Typography variant="body2" color="text.disabled" sx={{ maxWidth: 400, mx: 'auto' }}>
              Try: "Automate sauce-demo.com with login and cart flows" or "Run regression tests for sauce-demo"
            </Typography>
          </Box>
        ) : (
          <>
            {messages.map(renderMessage)}
            
            {/* Current processing events */}
            {currentEvents.length > 0 && (
              <Box sx={{ mb: 2 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <CircularProgress size={16} sx={{ mr: 1 }} />
                  <Typography variant="caption" color="text.secondary">
                    Processing...
                  </Typography>
                </Box>
                {currentEvents.filter(e => e.type === 'thinking').map((event, i) => (
                  <Typography
                    key={i}
                    variant="body2"
                    color="text.secondary"
                    sx={{ fontStyle: 'italic', mb: 0.5 }}
                  >
                    {event.content}
                  </Typography>
                ))}
                {currentEvents.filter(e => e.type === 'tool_call').map((event, i) =>
                  renderToolCall(event, i)
                )}
              </Box>
            )}
            
            {/* Approval prompt */}
            {currentEvents.some(e => e.type === 'approval_required') && (
              <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center', my: 2 }}>
                <Button
                  variant="contained"
                  color="success"
                  onClick={() => handleApproval(true)}
                >
                  Approve
                </Button>
                <Button
                  variant="outlined"
                  color="error"
                  onClick={() => handleApproval(false)}
                >
                  Reject
                </Button>
              </Box>
            )}
          </>
        )}
        <div ref={messagesEndRef} />
      </Paper>
      
      {/* Input area */}
      <Paper
        elevation={2}
        sx={{
          display: 'flex',
          alignItems: 'center',
          p: 1,
          gap: 1,
        }}
      >
        <TextField
          inputRef={inputRef}
          fullWidth
          placeholder={isProcessing ? 'Processing...' : 'Type your message...'}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && !e.shiftKey && sendMessage()}
          disabled={isProcessing || !isConnected || !session}
          multiline
          maxRows={4}
          variant="outlined"
          size="small"
        />
        <IconButton
          color="primary"
          onClick={sendMessage}
          disabled={!input.trim() || isProcessing || !isConnected || !session}
        >
          {isProcessing ? <CircularProgress size={24} /> : <SendIcon />}
        </IconButton>
      </Paper>
    </Box>
  );
};

export default AgentChat;

