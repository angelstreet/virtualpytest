import { useState, useEffect, useRef, useCallback } from 'react';
import { io, Socket } from 'socket.io-client';
import { buildServerUrl, getServerBaseUrl } from '../../utils/buildUrlUtils';

// --- Constants ---

const STORAGE_KEY_API = 'virtualpytest_anthropic_key';
const STORAGE_KEY_CONVERSATIONS = 'virtualpytest_agent_conversations';
const STORAGE_KEY_ACTIVE_CONVERSATION = 'virtualpytest_active_conversation';

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
  metrics?: {
    duration_ms: number;
    input_tokens: number;
    output_tokens: number;
  };
}

export interface Message {
  id: string;
  role: 'user' | 'agent';
  content: string;
  agent?: string;
  timestamp: string;
  events?: AgentEvent[];
}

export interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  createdAt: string;
  updatedAt: string;
}

export interface Session {
  id: string;
  mode?: string;
  active_agent?: string;
}

export type Status = 'checking' | 'ready' | 'needs_key' | 'error';

// --- Utilities ---

const generateId = () => `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;

const extractTitle = (messages: Message[]): string => {
  const firstUserMsg = messages.find(m => m.role === 'user');
  if (!firstUserMsg) return 'New Chat';
  // Take first 40 chars, truncate at word boundary
  const text = firstUserMsg.content.slice(0, 50);
  return text.length < firstUserMsg.content.length ? text.replace(/\s+\S*$/, '...') : text;
};

// --- Hook ---

export const useAgentChat = () => {
  // Conversations state
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  
  // Current conversation messages (derived)
  const activeConversation = conversations.find(c => c.id === activeConversationId);
  const messages = activeConversation?.messages || [];
  
  // Session & UI state
  const [status, setStatus] = useState<Status>('checking');
  const [session, setSession] = useState<Session | null>(null);
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

  // --- Conversation Persistence ---

  // Load conversations on mount
  useEffect(() => {
    const savedConvos = localStorage.getItem(STORAGE_KEY_CONVERSATIONS);
    const savedActiveId = localStorage.getItem(STORAGE_KEY_ACTIVE_CONVERSATION);
    
    if (savedConvos) {
      try {
        const parsed = JSON.parse(savedConvos);
        setConversations(parsed);
        // Restore active conversation or use most recent
        if (savedActiveId && parsed.find((c: Conversation) => c.id === savedActiveId)) {
          setActiveConversationId(savedActiveId);
        } else if (parsed.length > 0) {
          setActiveConversationId(parsed[0].id);
        }
      } catch (err) {
        console.error('Failed to load conversations:', err);
      }
    }
  }, []);

  // Save conversations on change
  useEffect(() => {
    if (conversations.length > 0) {
      localStorage.setItem(STORAGE_KEY_CONVERSATIONS, JSON.stringify(conversations));
    }
  }, [conversations]);

  // Save active conversation ID
  useEffect(() => {
    if (activeConversationId) {
      localStorage.setItem(STORAGE_KEY_ACTIVE_CONVERSATION, activeConversationId);
    }
  }, [activeConversationId]);

  // --- Conversation Management ---

  const createNewConversation = useCallback(() => {
    const newConvo: Conversation = {
      id: generateId(),
      title: 'New Chat',
      messages: [],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    setConversations(prev => [newConvo, ...prev]);
    setActiveConversationId(newConvo.id);
    setCurrentEvents([]);
    initializeSession();
    return newConvo.id;
  }, []);

  const switchConversation = useCallback((conversationId: string) => {
    setActiveConversationId(conversationId);
    setCurrentEvents([]);
    setIsProcessing(false);
  }, []);

  const deleteConversation = useCallback((conversationId: string) => {
    setConversations(prev => {
      const filtered = prev.filter(c => c.id !== conversationId);
      // If deleting active, switch to most recent
      if (conversationId === activeConversationId && filtered.length > 0) {
        setActiveConversationId(filtered[0].id);
      } else if (filtered.length === 0) {
        setActiveConversationId(null);
      }
      // Clean up localStorage if empty
      if (filtered.length === 0) {
        localStorage.removeItem(STORAGE_KEY_CONVERSATIONS);
        localStorage.removeItem(STORAGE_KEY_ACTIVE_CONVERSATION);
      }
      return filtered;
    });
  }, [activeConversationId]);

  const updateMessages = useCallback((newMessages: Message[]) => {
    if (!activeConversationId) return;
    
    setConversations(prev => prev.map(c => {
      if (c.id !== activeConversationId) return c;
      return {
        ...c,
        messages: newMessages,
        title: extractTitle(newMessages),
        updatedAt: new Date().toISOString(),
      };
    }));
  }, [activeConversationId]);

  // --- Socket Connection ---

  const connectSocket = useCallback((sessionId: string) => {
    if (socketRef.current?.connected) return;

    const serverBaseUrl = getServerBaseUrl();
    const socket = io(`${serverBaseUrl}/agent`, {
      path: '/server/socket.io',
      transports: ['polling'],
    });

    socket.on('connect', () => {
      socket.emit('join_session', { session_id: sessionId });
    });

    socket.on('agent_event', (event: AgentEvent) => {
      setCurrentEvents(prev => [...prev, event]);
      
      if (event.type === 'mode_detected') {
        setSession(prev => prev ? { ...prev, mode: event.content.split(': ')[1] } : null);
      }

      if (event.type === 'agent_delegated') {
        const agentName = event.content.replace('Delegating to ', '').replace(' agent...', '');
        setSession(prev => prev ? { ...prev, active_agent: agentName } : null);
      }

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
          
          // Update conversation with new message
          setConversations(prev => prev.map(c => {
            if (c.id !== activeConversationId) return c;
            const updatedMessages = [...c.messages, newMessage];
            return {
              ...c,
              messages: updatedMessages,
              title: extractTitle(updatedMessages),
              updatedAt: new Date().toISOString(),
            };
          }));
          
          return [];
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
  }, [activeConversationId]);

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

    // Create new conversation if none exists
    let targetConvoId = activeConversationId;
    if (!targetConvoId) {
      const newConvo: Conversation = {
        id: generateId(),
        title: 'New Chat',
        messages: [],
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };
      setConversations(prev => [newConvo, ...prev]);
      setActiveConversationId(newConvo.id);
      targetConvoId = newConvo.id;
    }

    const userMsg: Message = {
      id: `${Date.now()}-user`,
      role: 'user',
      content: input.trim(),
      timestamp: new Date().toISOString(),
    };

    // Add user message to conversation
    setConversations(prev => prev.map(c => {
      if (c.id !== targetConvoId) return c;
      const updatedMessages = [...c.messages, userMsg];
      return {
        ...c,
        messages: updatedMessages,
        title: extractTitle(updatedMessages),
        updatedAt: new Date().toISOString(),
      };
    }));

    setInput('');
    setIsProcessing(true);
    setCurrentEvents([]);
    setError(null);

    socketRef.current?.emit('send_message', {
      session_id: session?.id,
      message: input.trim(),
    });
  }, [input, isProcessing, session?.id, activeConversationId]);

  const handleApproval = useCallback((approved: boolean) => {
    socketRef.current?.emit('approve', { session_id: session?.id, approved });
  }, [session?.id]);

  const stopGeneration = useCallback(() => {
    if (!session?.id) return;
    
    setIsProcessing(false);
    setCurrentEvents([]);
    
    socketRef.current?.emit('stop_generation', { session_id: session.id });
    
    // Add system message to current conversation
    if (activeConversationId) {
      setConversations(prev => prev.map(c => {
        if (c.id !== activeConversationId) return c;
        return {
          ...c,
          messages: [...c.messages, {
            id: `${Date.now()}-stop`,
            role: 'agent' as const,
            agent: 'System',
            content: '🛑 Generation stopped by user.',
            timestamp: new Date().toISOString(),
          }],
          updatedAt: new Date().toISOString(),
        };
      }));
    }
  }, [session?.id, activeConversationId]);

  const clearHistory = useCallback(() => {
    setConversations([]);
    setActiveConversationId(null);
    localStorage.removeItem(STORAGE_KEY_CONVERSATIONS);
    localStorage.removeItem(STORAGE_KEY_ACTIVE_CONVERSATION);
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
    
    // Conversations
    conversations,
    activeConversationId,
    
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
    
    // Conversation Actions
    createNewConversation,
    switchConversation,
    deleteConversation,
  };
};
