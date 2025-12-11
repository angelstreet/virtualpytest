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
  // Background task fields (from dry-run events)
  task_id?: string;
  task_type?: string;
  task_data?: Record<string, unknown>;
  queue_name?: string;
  dry_run?: boolean;
}

// Generic background task - works for any agent with background_queues
export interface BackgroundTask {
  id: string;
  agentId: string;
  agentNickname: string;
  title: string;           // Script name, incident type, etc.
  subtitle?: string;       // Host name, device, etc.
  status: 'in_progress' | 'completed';
  severity?: string;       // For alerts: critical, high, normal, low
  classification?: string; // For analysis: VALID_PASS, BUG, etc.
  conversationId: string;
  startedAt: string;
  completedAt?: string;
  viewed: boolean;
  taskType?: string;       // script, alert, incident, etc.
}

// Background agent info (loaded from API)
export interface BackgroundAgentInfo {
  id: string;
  nickname: string;
  queues: string[];
  dryRun: boolean;
  color?: string;
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
  const sessionEndedRef = useRef<boolean>(false); // Track if session_ended was received (prevents premature reset)
  const disconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null); // For delayed disconnect handling
  
  // Generic background tasks state - keyed by agent ID
  // Loaded dynamically based on agents with background_queues config
  const [backgroundTasks, setBackgroundTasks] = useState<Record<string, {
    inProgress: BackgroundTask[];
    recent: BackgroundTask[];
  }>>({});
  
  // Background agents info (agents with background_queues) - set from parent
  const backgroundAgentsRef = useRef<Map<string, BackgroundAgentInfo>>(new Map());
  
  // Set background agents (called by parent after loading from API)
  const setBackgroundAgents = useCallback((agents: BackgroundAgentInfo[]) => {
    console.log(`[useAgentChat] setBackgroundAgents called with ${agents.length} agents:`, agents.map(a => `${a.id}/${a.nickname}`));
    const map = new Map<string, BackgroundAgentInfo>();
    agents.forEach(a => {
      map.set(a.id, a);
      map.set(a.nickname, a); // Also index by nickname for event matching
      console.log(`[useAgentChat] Registered background agent: id="${a.id}", nickname="${a.nickname}"`);
    });
    backgroundAgentsRef.current = map;
    console.log(`[useAgentChat] Background agents map keys:`, Array.from(map.keys()));
    
    // Initialize empty state for each background agent
    const initialState: Record<string, { inProgress: BackgroundTask[]; recent: BackgroundTask[] }> = {};
    agents.forEach(a => {
      initialState[a.id] = { inProgress: [], recent: [] };
    });
    setBackgroundTasks(prev => ({ ...initialState, ...prev }));
  }, []);

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

  // --- Generic Background Event Handler ---
  // Handles events from any agent with background_queues config
  
  // Track active background sessions per agent
  const backgroundSessionsRef = useRef<Map<string, { conversationId: string; taskId: string; title: string }>>(new Map());
  
  const handleBackgroundEvent = useCallback((event: AgentEvent): boolean => {
    // Check if this event is from a background agent
    console.log(`[handleBackgroundEvent] Checking event.agent="${event.agent}", available agents:`, Array.from(backgroundAgentsRef.current.keys()));
    const agentInfo = backgroundAgentsRef.current.get(event.agent);
    if (!agentInfo) {
      console.log(`[handleBackgroundEvent] Agent "${event.agent}" NOT FOUND in background agents map`);
      return false; // Not a background agent event
    }
    console.log(`[handleBackgroundEvent] Agent "${event.agent}" FOUND! agentInfo:`, agentInfo);
    
    const agentId = agentInfo.id;
    const agentNickname = agentInfo.nickname;
    const isDryRun = agentInfo.dryRun;
    
    console.log(`[Background:${agentNickname}] Handling event:`, event.type, event.content?.slice(0, 50));
    
    // Extract task info from event (generic patterns)
    const taskData = event.task_data || {};
    const taskId = event.task_id || 
      event.content?.match(/SCRIPT_RESULT_ID:\s*([a-f0-9-]+)/)?.[1] ||
      event.content?.match(/INCIDENT_ID:\s*([^\n]+)/)?.[1]?.trim() ||
      event.content?.match(/ALERT_ID:\s*([^\n]+)/)?.[1]?.trim() ||
      event.content?.match(/TASK_ID:\s*([^\n]+)/)?.[1]?.trim() ||
      `temp_${Date.now()}`;
    
    const taskType: string = event.task_type || (taskData.type as string) || 'task';
    
    // Build title and subtitle based on task type
    // Try task_data first, then parse from event.content
    let title = 'Task';
    let subtitle: string | undefined;
    let severity: string | undefined;
    let classification: string | undefined;
    
    if (taskType === 'script' || event.content?.includes('SCRIPT:')) {
      title = event.content?.match(/SCRIPT:\s*([^\n]+)/)?.[1]?.trim() || (taskData.script_name as string) || 'Script';
    } else if (taskType === 'alert' || taskType === 'incident') {
      // For alerts: title = "host_name - device_name", subtitle = incident_type
      const hostName = (taskData.host_name as string) || event.content?.match(/HOST:\s*([^\n(]+)/)?.[1]?.trim();
      const deviceName = taskData.device_name as string;
      const incidentType = (taskData.incident_type as string) || (taskData.alert_type as string) || 
        event.content?.match(/TYPE:\s*([^\n]+)/)?.[1]?.trim();
      
      // Title: host - device (or just host if no device)
      if (hostName && deviceName) {
        title = `${hostName} - ${deviceName}`;
      } else if (hostName) {
        title = hostName;
      } else {
        title = 'Unknown device';
      }
      
      // Subtitle: incident type (freeze, blackscreen, etc.)
      subtitle = incidentType || 'alert';
      severity = taskData.severity as string | undefined;
    } else {
      title = taskType;
    }
    
    const conversationId = `bg_${agentId}_${taskId}`;
    
    // Store session info
    backgroundSessionsRef.current.set(agentId, { conversationId, taskId, title });
    
    // Create conversation for this task WITH initial message
    const emoji = isDryRun ? '🌙' : '🔍';
    const initialMessage = {
      id: `${Date.now()}-${Math.random()}`,
      role: 'agent' as const,
      content: event.content || `${taskType} received`,
      agent: agentNickname,
      timestamp: new Date().toISOString(),
      events: [event],
    };
    
    const newConvo: Conversation = {
      id: conversationId,
      title: subtitle ? `${emoji} ${title} - ${subtitle}` : `${emoji} ${title}`,
      messages: [initialMessage], // Start with initial message
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    
    setConversations(prev => {
      const exists = prev.find(c => c.id === conversationId);
      if (exists) return prev;
      console.log(`[Background:${agentNickname}] Created conversation with message:`, conversationId);
      return [newConvo, ...prev];
    });
    
    // Create task object
    const task: BackgroundTask = {
      id: taskId,
      agentId,
      agentNickname,
      title,
      subtitle,
      status: isDryRun ? 'completed' : 'in_progress', // Dry run = instant complete
      severity,
      conversationId,
      startedAt: new Date().toISOString(),
      completedAt: isDryRun ? new Date().toISOString() : undefined,
      viewed: false,
      taskType,
    };
    
    // Update tasks state
    setBackgroundTasks(prev => {
      const agentTasks = prev[agentId] || { inProgress: [], recent: [] };
      
      if (isDryRun) {
        // Dry run mode: add directly to recent
        return {
          ...prev,
          [agentId]: {
            ...agentTasks,
            recent: [task, ...agentTasks.recent].slice(0, 5),
          }
        };
      } else {
        // Normal mode: add to in-progress
        const exists = agentTasks.inProgress.find(t => t.id === taskId);
        if (exists) return prev;
        return {
          ...prev,
          [agentId]: {
            ...agentTasks,
            inProgress: [task, ...agentTasks.inProgress.filter(t => !t.id.startsWith('temp_'))],
          }
        };
      }
    });
    
    // Check for completion markers (tool calls that indicate completion)
    if (event.type === 'tool_call' && event.tool_name === 'update_execution_analysis') {
      classification = event.tool_params?.classification as string || 'UNKNOWN';
      
      setBackgroundTasks(prev => {
        const agentTasks = prev[agentId] || { inProgress: [], recent: [] };
        const inProgressTask = agentTasks.inProgress.find(t => t.conversationId === conversationId);
        if (!inProgressTask) return prev;
        
        const completedTask: BackgroundTask = {
          ...inProgressTask,
          status: 'completed',
          classification,
          completedAt: new Date().toISOString(),
        };
        
        return {
          ...prev,
          [agentId]: {
            inProgress: agentTasks.inProgress.filter(t => t.conversationId !== conversationId),
            recent: [completedTask, ...agentTasks.recent].slice(0, 5),
          }
        };
      });
    }
    
    // Handle session_ended
    if (event.type === 'session_ended') {
      const sessionInfo = backgroundSessionsRef.current.get(agentId);
      if (sessionInfo) {
        setBackgroundTasks(prev => {
          const agentTasks = prev[agentId] || { inProgress: [], recent: [] };
          const inProgressTask = agentTasks.inProgress.find(t => t.conversationId === sessionInfo.conversationId);
          if (!inProgressTask) return prev;
          
          const completedTask: BackgroundTask = {
            ...inProgressTask,
            status: 'completed',
            classification: 'COMPLETED',
            completedAt: new Date().toISOString(),
          };
          
          return {
            ...prev,
            [agentId]: {
              inProgress: agentTasks.inProgress.filter(t => t.conversationId !== sessionInfo.conversationId),
              recent: [completedTask, ...agentTasks.recent].slice(0, 5),
            }
          };
        });
        backgroundSessionsRef.current.delete(agentId);
      }
    }
    
    // Add event to conversation (for subsequent events only - initial event added with conversation)
    setConversations(prev => prev.map(c => {
      if (c.id !== conversationId) return c;
      
      const lastMsg = c.messages[c.messages.length - 1];
      
      // Skip if event already exists in last message (prevents duplicate on initial event)
      if (lastMsg?.events?.some(e => e.task_id === event.task_id && e.type === event.type)) {
        return c;
      }
      
      if (lastMsg && lastMsg.role === 'agent' && event.type !== 'session_ended') {
        return {
          ...c,
          messages: [
            ...c.messages.slice(0, -1),
            {
              ...lastMsg,
              content: event.type === 'message' ? event.content : lastMsg.content,
              events: [...(lastMsg.events || []), event]
            }
          ],
          updatedAt: new Date().toISOString(),
        };
      } else if (event.type !== 'session_ended') {
        return {
          ...c,
          messages: [
            ...c.messages,
            {
              id: `${Date.now()}-${Math.random()}`,
              role: 'agent',
              content: event.content || `${event.type} event`,
              agent: agentNickname,
              timestamp: new Date().toISOString(),
              events: [event],
            }
          ],
          updatedAt: new Date().toISOString(),
        };
      }
      
      return c;
    }));
    
    return true; // Event was handled
  }, []);

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
      
      // Join background_tasks room for Sherlock analysis updates
      socket.emit('join_session', { session_id: 'background_tasks' });
      console.log('[useAgentChat] Joined background_tasks room for Sherlock updates');
      
      // Cancel any pending disconnect timeout on successful connect
      if (disconnectTimeoutRef.current) {
        clearTimeout(disconnectTimeoutRef.current);
        disconnectTimeoutRef.current = null;
      }
    });
    
    socket.on('disconnect', (reason) => {
      console.warn(`[useAgentChat] Socket disconnected: ${reason}`);
      
      // Only consider resetting on explicit server disconnect, NOT on transport close
      // Transport close happens during normal window switching/backgrounding
      if (reason === 'io server disconnect') {
        // Even then, only reset if session_ended was actually received
        // Use a longer timeout to give reconnection a chance
        if (disconnectTimeoutRef.current) {
          clearTimeout(disconnectTimeoutRef.current);
        }
        
        disconnectTimeoutRef.current = setTimeout(() => {
          // Only unstick if session actually ended AND we're still "processing"
          if (pendingConversationIdRef.current && sessionEndedRef.current) {
            console.warn('[useAgentChat] Server disconnect confirmed - cleaning up');
            setIsProcessing(false);
            pendingConversationIdRef.current = null;
            setPendingConversationId(null);
          }
          // If sessionEndedRef is false, the session is still active - don't reset
        }, 5000); // Wait 5 seconds for reconnection before cleaning up
      }
      // For transport close (tab backgrounding), do nothing - socket will reconnect
    });
    
    socket.on('reconnect', () => {
      console.log('[useAgentChat] Socket reconnected, rejoining session');
      socket.emit('join_session', { session_id: sessionId });
      
      // Cancel any pending disconnect timeout on successful reconnect
      if (disconnectTimeoutRef.current) {
        clearTimeout(disconnectTimeoutRef.current);
        disconnectTimeoutRef.current = null;
      }
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
      console.log(`[useAgentChat] Event received: type=${event.type}, agent=${event.agent}, task_id=${event.task_id}, dry_run=${event.dry_run}`);
      console.log(`[useAgentChat] Full event:`, JSON.stringify(event, null, 2));
      
      // Handle background agent events (any agent with background_queues config)
      // The handler checks if the event.agent is a background agent
      if (event.agent && handleBackgroundEvent(event)) {
        console.log(`[useAgentChat] Background event handled for agent: ${event.agent}`);
        // Event was handled by a background agent, don't return - still process for conversation view
      } else if (event.agent) {
        console.log(`[useAgentChat] Event NOT handled as background (agent: ${event.agent})`);
      }
      
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
        sessionEndedRef.current = true; // Mark that session properly ended
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
    sessionEndedRef.current = false; // Reset for new message - session is active

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
      agent_id: agentIdRef.current || 'assistant',
      allow_auto_navigation: allowAutoNavigationRef.current,
      current_page: currentPageRef.current,
    });
  }, [input, isProcessing, session?.id, activeConversationId]);

  // Allow external code to set the agent
  const agentIdRef = useRef<string>('assistant');
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
    
    // Clear timeout failsafe
    if (processingTimeoutRef.current) {
      clearTimeout(processingTimeoutRef.current);
      processingTimeoutRef.current = null;
    }
    
    socketRef.current?.emit('stop_generation', { session_id: session.id });
    
    const targetConvoId = pendingConversationIdRef.current;
    
    // Save current events as a partial message before clearing
    setCurrentEvents(prevEvents => {
      if (targetConvoId && prevEvents.length > 0) {
        // Build partial message from accumulated events
        const messageResultEvents = prevEvents.filter(e => 
          e.type === 'message' || e.type === 'result' || e.type === 'agent_delegated'
        );
        const toolCallEvents = prevEvents.filter(e => e.type === 'tool_call');
        
        // Only save if we have meaningful content
        if (messageResultEvents.length > 0 || toolCallEvents.length > 0) {
          const accumulatedContent = messageResultEvents
            .map(e => e.content)
            .filter(Boolean)
            .join('\n\n');
          
          // Get the active agent name from events or session
          const agentName = prevEvents.find(e => e.agent)?.agent || session?.active_agent || 'Agent';
          
          const partialMessage: Message = {
            id: `${Date.now()}-partial`,
            role: 'agent',
            content: accumulatedContent || '(partial response)',
            agent: agentName,
            timestamp: new Date().toISOString(),
            events: prevEvents,
          };
          
          setConversations(prev => prev.map(c => {
            if (c.id !== targetConvoId) return c;
            return {
              ...c,
              messages: [...c.messages, partialMessage, {
                id: `${Date.now()}-stop`,
                role: 'agent' as const,
                agent: 'System',
                content: '🛑 Generation stopped by user.',
                timestamp: new Date().toISOString(),
              }],
              updatedAt: new Date().toISOString(),
            };
          }));
        } else {
          // No meaningful events, just add stop message
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
      } else if (targetConvoId) {
        // No events but we have a conversation, just add stop message
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
      
      return []; // Clear events after saving
    });
    
    setIsProcessing(false);
    
    // Clear pending conversation
    pendingConversationIdRef.current = null;
    setPendingConversationId(null);
  }, [session?.id, session?.active_agent]);

  const clearHistory = useCallback(() => {
    clearBackendSession(); // Fresh backend session
    
    // Preserve background agent conversations (prefix: bg_)
    setConversations(prev => {
      const backgroundConversations = prev.filter(c => c.id.startsWith('bg_'));
      
      // Update localStorage with only background conversations
      if (backgroundConversations.length > 0) {
        localStorage.setItem(STORAGE_KEY_CONVERSATIONS, JSON.stringify(backgroundConversations));
      } else {
        localStorage.removeItem(STORAGE_KEY_CONVERSATIONS);
      }
      
      return backgroundConversations;
    });
    
    // Clear active conversation if it was a regular one
    setActiveConversationId(prev => {
      if (prev && prev.startsWith('bg_')) {
        return prev; // Keep background conversation active
      }
      localStorage.removeItem(STORAGE_KEY_ACTIVE_CONVERSATION);
      activeConversationIdRef.current = null;
      return null;
    });
    
    pendingConversationIdRef.current = null;
    setPendingConversationId(null);
    setIsProcessing(false);
    setCurrentEvents([]);
  }, [clearBackendSession]);

  // Handle visibility change - ensure socket reconnects when tab becomes visible
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        console.log('[useAgentChat] Tab became visible - checking socket connection');
        
        // Cancel any pending disconnect timeout
        if (disconnectTimeoutRef.current) {
          clearTimeout(disconnectTimeoutRef.current);
          disconnectTimeoutRef.current = null;
        }
        
        // If socket is disconnected but we're still processing, attempt reconnect
        if (socketRef.current && !socketRef.current.connected && pendingConversationIdRef.current) {
          console.log('[useAgentChat] Reconnecting socket after tab visibility change');
          socketRef.current.connect();
        }
      }
    };
    
    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
  }, []);

  // Cleanup socket and timeouts on unmount
  useEffect(() => {
    return () => {
      if (socketRef.current) {
        socketRef.current.disconnect();
      }
      if (processingTimeoutRef.current) {
        clearTimeout(processingTimeoutRef.current);
      }
      if (disconnectTimeoutRef.current) {
        clearTimeout(disconnectTimeoutRef.current);
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
    
    // Background Tasks (generic - keyed by agent ID)
    backgroundTasks,
    setBackgroundAgents,
    
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
