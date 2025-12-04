import { useState, useEffect, useRef, useCallback } from 'react';
import { io, Socket } from 'socket.io-client';
import { buildServerUrl, getServerBaseUrl } from '../../utils/buildUrlUtils';

// --- Constants ---

const STORAGE_KEY_API = 'virtualpytest_anthropic_key';
const STORAGE_KEY_MESSAGES = 'virtualpytest_agent_messages';

// --- Types ---

export interface AgentEvent {
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

export interface Message {
  id: string;
  role: 'user' | 'agent';
  content: string;
  agent?: string;
  timestamp: string;
  events?: AgentEvent[];
}

export interface Session {
  id: string;
  mode?: string;
  active_agent?: string;
}

export type Status = 'checking' | 'ready' | 'needs_key' | 'error';

// --- Hook ---

export const useAgentChat = () => {
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

  // --- Message Persistence ---

  // Load messages on mount
  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY_MESSAGES);
    if (saved) {
      try {
        setMessages(JSON.parse(saved));
      } catch (err) {
        console.error('Failed to load messages:', err);
      }
    }
  }, []);

  // Save messages on change
  useEffect(() => {
    if (messages.length > 0) {
      localStorage.setItem(STORAGE_KEY_MESSAGES, JSON.stringify(messages));
    }
  }, [messages]);

  // --- Socket Connection ---

  const connectSocket = useCallback((sessionId: string) => {
    if (socketRef.current?.connected) return;

    const serverBaseUrl = getServerBaseUrl();
    const socket = io(`${serverBaseUrl}/agent`, {
      path: '/server/socket.io',
      transports: ['polling'], // Use polling only to avoid WebSocket errors
    });

    socket.on('connect', () => {
      socket.emit('join_session', { session_id: sessionId });
    });

    socket.on('agent_event', (event: AgentEvent) => {
      setCurrentEvents(prev => [...prev, event]);
      
      // Mode Detection
      if (event.type === 'mode_detected') {
        setSession(prev => prev ? { ...prev, mode: event.content.split(': ')[1] } : null);
      }

      // Agent Delegation
      if (event.type === 'agent_delegated') {
        const agentName = event.content.replace('Delegating to ', '').replace(' agent...', '');
        setSession(prev => prev ? { ...prev, active_agent: agentName } : null);
      }

      // Message Completion
      if (event.type === 'message' || event.type === 'result') {
        setCurrentEvents(prevEvents => {
          const newMessage: Message = {
            id: `${Date.now()}-${Math.random()}`,
            role: 'agent',
            content: event.content,
            agent: event.agent,
            timestamp: event.timestamp,
            events: [...prevEvents, event],
          };
          setMessages(prev => [...prev, newMessage]);
          return []; // Clear current events buffer
        });
      }
      
      if (event.type === 'session_ended') {
        setIsProcessing(false);
      }
    });

    socket.on('error', (data) => {
      const errorMessage = data.type 
        ? `${data.type}: ${data.error}`
        : data.error || 'Unknown error occurred';
      console.error('[@useAgentChat] Socket error:', errorMessage);
      setError(errorMessage);
      setIsProcessing(false);
    });

    socketRef.current = socket;
  }, []);

  // --- Session Management ---

  const initializeSession = useCallback(async () => {
    try {
      const response = await fetch(buildServerUrl('/server/agent/sessions'), { method: 'POST' });
      const data = await response.json();
      if (data.success) {
        setSession(data.session);
        connectSocket(data.session.id);
      }
    } catch (err) {
      console.error('Failed to initialize session:', err);
      setStatus('error');
    }
  }, [connectSocket]);

  // --- Check Connectivity & Auth ---

  useEffect(() => {
    const checkConnection = async () => {
      try {
        const response = await fetch(buildServerUrl('/server/agent/health'));
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
      } catch (err) {
        console.error('Connection check failed:', err);
        setStatus('error');
        setError('Backend unavailable - check server connection');
      }
    };
    checkConnection();
  }, [initializeSession]);

  // --- Actions ---

  const saveApiKey = useCallback(() => {
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
  }, [apiKeyInput, initializeSession]);

  const sendMessage = useCallback(() => {
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
  }, [input, isProcessing, session?.id]);

  const handleApproval = useCallback((approved: boolean) => {
    socketRef.current?.emit('approve', { session_id: session?.id, approved });
  }, [session?.id]);

  const stopGeneration = useCallback(() => {
    if (!session?.id) return;
    
    setIsProcessing(false); // Optimistic update
    setCurrentEvents([]); // Clear current stream
    
    // Send stop signal to backend
    socketRef.current?.emit('stop_generation', { session_id: session.id });
    
    // Add system message
    setMessages(prev => [...prev, {
      id: `${Date.now()}-stop`,
      role: 'agent',
      agent: 'System',
      content: '🛑 Generation stopped by user.',
      timestamp: new Date().toISOString(),
    }]);
  }, [session?.id]);

  const clearHistory = useCallback(() => {
    setMessages([]);
    localStorage.removeItem(STORAGE_KEY_MESSAGES);
    initializeSession();
  }, [initializeSession]);

  // Cleanup socket on unmount
  useEffect(() => {
    return () => {
      if (socketRef.current) {
        socketRef.current.disconnect();
      }
    };
  }, []);

  return {
    // State
    status,
    session,
    messages,
    input,
    isProcessing,
    currentEvents,
    error,
    apiKeyInput,
    showApiKey,
    isValidating,
    
    // Actions
    setInput,
    setShowApiKey,
    setApiKeyInput,
    setError,
    sendMessage,
    saveApiKey,
    handleApproval,
    stopGeneration,
    clearHistory,
  };
};

