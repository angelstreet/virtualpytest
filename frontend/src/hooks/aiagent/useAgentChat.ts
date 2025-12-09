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

  // 🔄 REAL-TIME SYNC: Listen for AIContext events (from Cmd+K command bar)
  useEffect(() => {
    // When a message is sent from AIContext
    const handleMessageSent = (e: CustomEvent) => {
      const { conversationId, userMessage } = e.detail;
      console.log('🔄 useAgentChat: AIContext sent message', { conversationId, userMessage: userMessage?.slice(0, 30) });
      
      // Create new conversation if needed
      const newConvo: Conversation = {
        id: conversationId,
        title: userMessage?.slice(0, 50) || 'New Chat',
        messages: [{
          id: `${Date.now()}-user`,
          role: 'user',
          content: userMessage,
          timestamp: new Date().toISOString(),
        }],
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };
      
      setConversations(prev => {
        // Check if conversation already exists
        const exists = prev.find(c => c.id === conversationId);
        if (exists) return prev;
        return [newConvo, ...prev];
      });
      
      // Switch to the new conversation and set processing state
      setActiveConversationId(conversationId);
      activeConversationIdRef.current = conversationId;
      pendingConversationIdRef.current = conversationId;
      setPendingConversationId(conversationId);
      setIsProcessing(true);
      setCurrentEvents([]);
    };
    
    // Real-time agent events from AIContext
    const handleAgentEvent = (e: CustomEvent) => {
      const { event, conversationId } = e.detail;
      
      // Only process if this is for our pending conversation
      if (conversationId !== pendingConversationIdRef.current) return;
      
      // Accumulate events (same as socket handler)
      if (event.type !== 'session_ended' && event.type !== 'complete') {
        setCurrentEvents(prev => [...prev, event]);
      }
    };
    
    // When AIContext completes
    const handleComplete = (e: CustomEvent) => {
      const { conversationId } = e.detail;
      
      // Only process if this is for our pending conversation
      if (conversationId !== pendingConversationIdRef.current) return;
      
      console.log('🔄 useAgentChat: AIContext completed, reloading conversations');
      
      // AIContext saves to localStorage, so just reload
      // Small delay to ensure localStorage is updated
      setTimeout(() => {
        loadConversations();
        setIsProcessing(false);
        setCurrentEvents([]);
        pendingConversationIdRef.current = null;
        setPendingConversationId(null);
      }, 100);
    };

    window.addEventListener('aicontext-message-sent', handleMessageSent as EventListener);
    window.addEventListener('aicontext-agent-event', handleAgentEvent as EventListener);
    window.addEventListener('aicontext-complete', handleComplete as EventListener);
    
    return () => {
      window.removeEventListener('aicontext-message-sent', handleMessageSent as EventListener);
      window.removeEventListener('aicontext-agent-event', handleAgentEvent as EventListener);
      window.removeEventListener('aicontext-complete', handleComplete as EventListener);
    };
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

  // Clear backend session for conversation isolation
  const clearBackendSession = useCallback(() => {
    socketRef.current?.emit('clear_session', { session_id: session?.id });
  }, [session?.id]);

  const createNewConversation = useCallback(() => {
    clearBackendSession(); // Fresh backend session
    const newConvo: Conversation = {
      id: generateId(),
      title: 'New Chat',
      messages: [],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    setConversations(prev => [newConvo, ...prev]);
    setActiveConversationId(newConvo.id);
    activeConversationIdRef.current = newConvo.id;
    setCurrentEvents([]);
    return newConvo.id;
  }, [clearBackendSession]);

  const switchConversation = useCallback((conversationId: string) => {
    setActiveConversationId(conversationId);
    activeConversationIdRef.current = conversationId;
  }, []);

  const deleteConversation = useCallback((conversationId: string) => {
    clearBackendSession(); // Fresh start after delete
    setConversations(prev => {
      const filtered = prev.filter(c => c.id !== conversationId);
      if (conversationId === activeConversationId && filtered.length > 0) {
        setActiveConversationId(filtered[0].id);
        activeConversationIdRef.current = filtered[0].id;
      } else if (filtered.length === 0) {
        setActiveConversationId(null);
        activeConversationIdRef.current = null;
      }
      if (filtered.length === 0) {
        localStorage.removeItem(STORAGE_KEY_CONVERSATIONS);
        localStorage.removeItem(STORAGE_KEY_ACTIVE_CONVERSATION);
      }
      return filtered;
    });
  }, [activeConversationId, clearBackendSession]);

  // --- Socket Connection ---

  const connectSocket = useCallback((sessionId: string) => {
    if (socketRef.current?.connected) return;

    const serverBaseUrl = getServerBaseUrl();
    const socket = io(`${serverBaseUrl}/agent`, {
      path: '/server/socket.io',
      transports: ['polling'],
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
    });

    socket.on('connect', () => {
      console.log('[useAgentChat] Socket connected');
      socket.emit('join_session', { session_id: sessionId });
    });
    
    socket.on('disconnect', (reason) => {
      console.warn(`[useAgentChat] Socket disconnected: ${reason}`);
      // If server closed connection, session may have ended - auto-unstick after brief delay
      if (reason === 'io server disconnect' || reason === 'transport close') {
        setTimeout(() => {
          // Only unstick if still processing (session_ended wasn't received)
          if (pendingConversationIdRef.current) {
            console.warn('[useAgentChat] Unsticking after disconnect - session likely ended');
            setIsProcessing(false);
            pendingConversationIdRef.current = null;
            setPendingConversationId(null);
          }
        }, 2000);
      }
    });
    
    socket.on('reconnect', () => {
      console.log('[useAgentChat] Socket reconnected, rejoining session');
      socket.emit('join_session', { session_id: sessionId });
    });

    socket.on('agent_event', (event: AgentEvent) => {
      // Helper to save current events as a message
      const saveCurrentEventsAsMessage = (agentName: string, eventsToSave: AgentEvent[]) => {
        const messageResultEvents = eventsToSave.filter(e => 
          e.type === 'message' || e.type === 'result' || e.type === 'agent_delegated'
        );
        const errorEvents = eventsToSave.filter(e => e.type === 'error');
        const toolCallEvents = eventsToSave.filter(e => e.type === 'tool_call');
        
        // Nothing meaningful to save - no messages, errors, or tools
        if (messageResultEvents.length === 0 && errorEvents.length === 0 && toolCallEvents.length === 0) {
          return;
        }
        
        // Build content: prioritize error messages if present
        let accumulatedContent = '';
        if (errorEvents.length > 0) {
          // Extract error content from error events (content has the human-readable message)
          accumulatedContent = errorEvents
            .map(e => e.content || 'An error occurred')
            .filter(Boolean)
            .join('\n\n');
        } else {
          accumulatedContent = messageResultEvents
            .map(e => e.content)
            .filter(Boolean)
            .join('\n\n');
        }
        
        const newMessage: Message = {
          id: `${Date.now()}-${Math.random()}`,
          role: 'agent',
          content: accumulatedContent || `${agentName} completed`,
          agent: agentName,
          timestamp: new Date().toISOString(),
          events: eventsToSave,
        };
        
        const targetConvoId = pendingConversationIdRef.current;
        if (targetConvoId) {
          setConversations(prev => prev.map(c => {
            if (c.id !== targetConvoId) return c;
            const updatedMessages = [...c.messages, newMessage];
            return {
              ...c,
              messages: updatedMessages,
              title: extractTitle(updatedMessages),
              updatedAt: new Date().toISOString(),
            };
          }));
        }
      };
      
      // Debug: Log every event received
      console.log(`[useAgentChat] Event received: type=${event.type}, agent=${event.agent}`);
      
      // Track mode
      if (event.type === 'mode_detected') {
        setSession(prev => prev ? { ...prev, mode: event.content.split(': ')[1] } : null);
      }

      // When manager delegates: save manager's message, update active agent
      if (event.type === 'agent_delegated') {
        console.log('[useAgentChat] AGENT_DELEGATED - saving Atlas message, switching to delegated agent');
        const agentName = event.content.replace('Delegating to ', '').replace('...', '').trim();
        
        // Include this event in the delegating agent's message (use event.agent, not hardcoded)
        setCurrentEvents(prev => {
          const eventsWithDelegation = [...prev, event];
          saveCurrentEventsAsMessage(event.agent, eventsWithDelegation);
          return []; // Clear for next agent
        });
        
        setSession(prev => prev ? { ...prev, active_agent: agentName } : null);
        return;
      }

      // When sub-agent starts: update badge
      if (event.type === 'agent_started') {
        console.log(`[useAgentChat] AGENT_STARTED - ${event.agent} taking over`);
        setSession(prev => prev ? { ...prev, active_agent: event.agent } : null);
        setCurrentEvents([]); // Fresh start for this agent
        return;
      }
      
      // When sub-agent completes: save its message
      if (event.type === 'agent_completed') {
        console.log(`[useAgentChat] AGENT_COMPLETED - saving ${event.agent} message`);
        setCurrentEvents(prev => {
          console.log(`[useAgentChat] Saving ${prev.length} events for ${event.agent}`);
          saveCurrentEventsAsMessage(event.agent, prev);
          return []; // Clear for next agent (or QA Manager summary)
        });
        return;
      }

      // Accumulate events for current agent
      if (event.type !== 'session_ended' && event.type !== 'complete') {
        setCurrentEvents(prev => {
          const newEvents = [...prev, event];
          console.log(`[useAgentChat] Accumulated ${newEvents.length} events for current agent`);
          return newEvents;
        });
      }

      // Session ends: save any remaining events as final message
      if (event.type === 'session_ended' || event.type === 'complete') {
        console.log(`[useAgentChat] SESSION_ENDED - finalizing conversation`);
        setIsProcessing(false);
        
        if (processingTimeoutRef.current) {
          clearTimeout(processingTimeoutRef.current);
          processingTimeoutRef.current = null;
        }
        
        setCurrentEvents(prevEvents => {
          if (prevEvents.length > 0) {
            // Use event.agent if available, otherwise use session's active agent
            const finalAgent = event.agent || session?.active_agent || 'System';
            saveCurrentEventsAsMessage(finalAgent, prevEvents);
          }
          
          // Clear pending conversation
          pendingConversationIdRef.current = null;
          setPendingConversationId(null);
          setSession(prev => prev ? { ...prev, active_agent: undefined } : null);
          
          return [];
        });
      }
      
      // Note: Don't stop processing on error events - tool errors are recoverable
      // The agent will continue and try other approaches
      // Only session_ended or complete should stop processing
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

    // Failsafe: Auto-unstick processing after 15 minutes
    if (processingTimeoutRef.current) {
      clearTimeout(processingTimeoutRef.current);
    }
    processingTimeoutRef.current = setTimeout(() => {
      console.warn('[@useAgentChat] Processing timeout - auto-unsticking');
      setIsProcessing(false);
      setError('Processing timeout - please try again');
    }, 15 * 60 * 1000);

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
    clearBackendSession(); // Fresh backend session
    setConversations([]);
    setActiveConversationId(null);
    activeConversationIdRef.current = null;
    pendingConversationIdRef.current = null;
    setPendingConversationId(null);
    setIsProcessing(false);
    setCurrentEvents([]);
    localStorage.removeItem(STORAGE_KEY_CONVERSATIONS);
    localStorage.removeItem(STORAGE_KEY_ACTIVE_CONVERSATION);
  }, [clearBackendSession]);

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
