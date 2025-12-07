import { useState, useEffect, useRef, useCallback } from 'react';
import { io, Socket } from 'socket.io-client';
import { buildServerUrl, getServerBaseUrl } from '../../utils/buildUrlUtils';
import { APP_CONFIG } from '../../config/constants';

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
    cache_read_tokens?: number;
    cache_create_tokens?: number;
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
  const [pendingConversationId, setPendingConversationId] = useState<string | null>(null); // Which conversation is awaiting response
  const [currentEvents, setCurrentEvents] = useState<AgentEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  
  // API Key state
  const [apiKeyInput, setApiKeyInput] = useState('');
  const [showApiKey, setShowApiKey] = useState(false);
  const [isValidating, setIsValidating] = useState(false);
  
  // Refs
  const socketRef = useRef<Socket | null>(null);
  const processingTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const activeConversationIdRef = useRef<string | null>(null);
  const pendingConversationIdRef = useRef<string | null>(null); // Track which conversation is awaiting response

  // --- Conversation Persistence ---

  // Load conversations from localStorage
  const loadConversations = useCallback(() => {
    const savedConvos = localStorage.getItem(STORAGE_KEY_CONVERSATIONS);
    const savedActiveId = localStorage.getItem(STORAGE_KEY_ACTIVE_CONVERSATION);
    
    if (savedConvos) {
      try {
        const parsed = JSON.parse(savedConvos);
        setConversations(parsed);
        // Restore active conversation or use most recent
        if (savedActiveId && parsed.find((c: Conversation) => c.id === savedActiveId)) {
          setActiveConversationId(savedActiveId);
          activeConversationIdRef.current = savedActiveId;
        } else if (parsed.length > 0) {
          setActiveConversationId(parsed[0].id);
          activeConversationIdRef.current = parsed[0].id;
        }
      } catch (err) {
        console.error('Failed to load conversations:', err);
      }
    }
  }, []);

  // Load conversations on mount
  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  // Listen for updates from AIContext (Cmd+K commands)
  useEffect(() => {
    const handleConversationUpdate = () => {
      console.log('🔄 useAgentChat: Received conversation update from AIContext');
      loadConversations();
    };

    window.addEventListener('agent-conversation-updated', handleConversationUpdate);
    return () => window.removeEventListener('agent-conversation-updated', handleConversationUpdate);
  }, [loadConversations]);

  // Save conversations on change
  useEffect(() => {
    if (conversations.length > 0) {
      localStorage.setItem(STORAGE_KEY_CONVERSATIONS, JSON.stringify(conversations));
    }
  }, [conversations]);

  // Save active conversation ID and keep ref in sync
  useEffect(() => {
    activeConversationIdRef.current = activeConversationId;
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
    activeConversationIdRef.current = newConvo.id; // Immediately update ref
    setCurrentEvents([]);
    return newConvo.id;
  }, []); // initializeSession is called on mount, not needed here

  const switchConversation = useCallback((conversationId: string) => {
    setActiveConversationId(conversationId);
    activeConversationIdRef.current = conversationId;
    // Don't clear currentEvents or isProcessing - they belong to the pending conversation
    // The UI will only show processing state when viewing the pending conversation
  }, []);

  const deleteConversation = useCallback((conversationId: string) => {
    setConversations(prev => {
      const filtered = prev.filter(c => c.id !== conversationId);
      // If deleting active, switch to most recent
      if (conversationId === activeConversationId && filtered.length > 0) {
        setActiveConversationId(filtered[0].id);
        activeConversationIdRef.current = filtered[0].id; // Update ref
      } else if (filtered.length === 0) {
        setActiveConversationId(null);
        activeConversationIdRef.current = null; // Update ref
      }
      // Clean up localStorage if empty
      if (filtered.length === 0) {
        localStorage.removeItem(STORAGE_KEY_CONVERSATIONS);
        localStorage.removeItem(STORAGE_KEY_ACTIVE_CONVERSATION);
      }
      return filtered;
    });
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
      // Accumulate all events except terminal ones
      if (event.type !== 'session_ended' && event.type !== 'complete') {
        setCurrentEvents(prev => [...prev, event]);
      }
      
      if (event.type === 'mode_detected') {
        setSession(prev => prev ? { ...prev, mode: event.content.split(': ')[1] } : null);
      }

      if (event.type === 'agent_delegated') {
        const agentName = event.content.replace('Delegating to ', '').replace(' agent...', '');
        setSession(prev => prev ? { ...prev, active_agent: agentName } : null);
      }

      // Finalize message only when session ends or completes
      if (event.type === 'session_ended' || event.type === 'complete') {
        setIsProcessing(false);
        
        if (processingTimeoutRef.current) {
          clearTimeout(processingTimeoutRef.current);
          processingTimeoutRef.current = null;
        }
        
        setCurrentEvents(prevEvents => {
          // Only create message if we have message/result events
          const messageResultEvents = prevEvents.filter(e => e.type === 'message' || e.type === 'result');
          if (messageResultEvents.length === 0) {
            return [];
          }
          
          // Accumulate content from message/result events only (thinking shown separately in UI)
          const accumulatedContent = messageResultEvents
            .map(e => e.content)
            .filter(Boolean)
            .join('\n\n');

          // Find the last agent to attribute the message to
          const lastAgentEvent = [...prevEvents].reverse().find(e => e.agent);
          const agentName = lastAgentEvent?.agent || 'QA Manager';
          
          const newMessage: Message = {
            id: `${Date.now()}-${Math.random()}`,
            role: 'agent',
            content: accumulatedContent,
            agent: agentName,
            timestamp: new Date().toISOString(),
            events: prevEvents,
          };
          
          // Update conversation with new message - use pendingConversationIdRef (the one that initiated the request)
          const targetConvoId = pendingConversationIdRef.current;
          if (targetConvoId) {
            setConversations(prev => {
              return prev.map(c => {
                if (c.id !== targetConvoId) return c;
                const updatedMessages = [...c.messages, newMessage];
                return {
                  ...c,
                  messages: updatedMessages,
                  title: extractTitle(updatedMessages),
                  updatedAt: new Date().toISOString(),
                };
              });
            });
          }
          
          // Clear pending conversation
          pendingConversationIdRef.current = null;
          setPendingConversationId(null);
          
          return [];
        });
      }
      
      // Failsafe: If we get an error or failed event, unstick processing
      if (event.type === 'error' || event.type === 'failed') {
        setIsProcessing(false);
        pendingConversationIdRef.current = null;
        setPendingConversationId(null);
        if (processingTimeoutRef.current) {
          clearTimeout(processingTimeoutRef.current);
          processingTimeoutRef.current = null;
        }
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
  }, []); // Remove activeConversationId from dependencies since we use ref now

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
        const teamId = APP_CONFIG.DEFAULT_TEAM_ID;
        
        const response = await fetch(buildServerUrl(`/server/agent/health?team_id=${teamId}`));
        const data = await response.json();
        
        if (data.api_key_configured) {
          setStatus('ready');
          initializeSession();
        } else {
          // Check if we have a saved key in localStorage
          const savedKey = localStorage.getItem(STORAGE_KEY_API);
          if (savedKey) {
            // Send the saved key to backend
            try {
              const saveResponse = await fetch(buildServerUrl('/server/agent/api-key'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                  api_key: savedKey,
                  team_id: teamId
                })
              });
              
              const saveData = await saveResponse.json();
              if (saveData.success) {
                setStatus('ready');
                initializeSession();
              } else {
                setStatus('needs_key');
              }
            } catch (err) {
              console.error('Failed to restore saved API key:', err);
              setStatus('needs_key');
            }
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

  const saveApiKey = useCallback(async (teamId?: string) => {
    if (!apiKeyInput.trim().startsWith('sk-ant-')) {
      setError('Invalid Key');
      return;
    }
    
    setIsValidating(true);
    setError(null);
    
    try {
      const effectiveTeamId = teamId || APP_CONFIG.DEFAULT_TEAM_ID;
      
      // Save to backend for validation
      const response = await fetch(buildServerUrl('/server/agent/api-key'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          api_key: apiKeyInput.trim(),
          team_id: effectiveTeamId
        })
      });
      
      const data = await response.json();
      
      if (data.success) {
        // Also save to localStorage for persistence
        localStorage.setItem(STORAGE_KEY_API, apiKeyInput.trim());
        setStatus('ready');
        setIsValidating(false);
        initializeSession();
      } else {
        setError(data.error || 'Failed to validate API key');
        setIsValidating(false);
      }
    } catch (err) {
      console.error('Failed to save API key:', err);
      setError('Failed to save API key - check server connection');
      setIsValidating(false);
    }
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
      activeConversationIdRef.current = newConvo.id; // Immediately update ref
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

    // Track which conversation is awaiting response (for when user switches chats)
    pendingConversationIdRef.current = targetConvoId;
    setPendingConversationId(targetConvoId);

    setInput('');
    setIsProcessing(true);
    setCurrentEvents([]);
    setError(null);

    // Failsafe: Auto-unstick processing after 5 minutes
    if (processingTimeoutRef.current) {
      clearTimeout(processingTimeoutRef.current);
    }
    processingTimeoutRef.current = setTimeout(() => {
      console.warn('[@useAgentChat] Processing timeout - auto-unsticking');
      setIsProcessing(false);
      setError('Processing timeout - please try again');
    }, 5 * 60 * 1000);

    socketRef.current?.emit('send_message', {
      session_id: session?.id,
      message: input.trim(),
      team_id: APP_CONFIG.DEFAULT_TEAM_ID,
      agent_id: agentIdRef.current || 'ai-assistant',
      allow_auto_navigation: allowAutoNavigationRef.current,
      current_page: currentPageRef.current,
    });
  }, [input, isProcessing, session?.id, activeConversationId]);

  // Allow external code to set the agent
  const agentIdRef = useRef<string>('ai-assistant');
  const setAgentId = useCallback((agentId: string) => {
    agentIdRef.current = agentId;
  }, []);

  // Navigation context refs (set by parent component)
  const allowAutoNavigationRef = useRef<boolean>(false);
  const currentPageRef = useRef<string>('/');
  
  const setNavigationContext = useCallback((allowAutoNavigation: boolean, currentPage: string) => {
    allowAutoNavigationRef.current = allowAutoNavigation;
    currentPageRef.current = currentPage;
  }, []);

  const handleApproval = useCallback((approved: boolean) => {
    socketRef.current?.emit('approve', { session_id: session?.id, approved });
  }, [session?.id]);

  const stopGeneration = useCallback(() => {
    if (!session?.id) return;
    
    setIsProcessing(false);
    setCurrentEvents([]);
    
    // Clear timeout failsafe
    if (processingTimeoutRef.current) {
      clearTimeout(processingTimeoutRef.current);
      processingTimeoutRef.current = null;
    }
    
    socketRef.current?.emit('stop_generation', { session_id: session.id });
    
    // Add system message to the conversation that initiated the request
    const targetConvoId = pendingConversationIdRef.current;
    if (targetConvoId) {
      setConversations(prev => prev.map(c => {
        if (c.id !== targetConvoId) return c;
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
    
    // Clear pending conversation
    pendingConversationIdRef.current = null;
    setPendingConversationId(null);
  }, [session?.id]);

  const clearHistory = useCallback(() => {
    setConversations([]);
    setActiveConversationId(null);
    activeConversationIdRef.current = null;
    pendingConversationIdRef.current = null;
    setPendingConversationId(null);
    setIsProcessing(false);
    setCurrentEvents([]);
    localStorage.removeItem(STORAGE_KEY_CONVERSATIONS);
    localStorage.removeItem(STORAGE_KEY_ACTIVE_CONVERSATION);
  }, []);

  // Cleanup socket and timeout on unmount
  useEffect(() => {
    return () => {
      if (socketRef.current) {
        socketRef.current.disconnect();
      }
      if (processingTimeoutRef.current) {
        clearTimeout(processingTimeoutRef.current);
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
    pendingConversationId,
    
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
    setAgentId,
    setNavigationContext,
    
    // Conversation Actions
    createNewConversation,
    switchConversation,
    deleteConversation,
  };
};
