import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { io, Socket } from 'socket.io-client';
import { buildServerUrl, getServerBaseUrl } from '../utils/buildUrlUtils';
import { APP_CONFIG } from '../config/constants';

// Same storage key as useAgentChat to share API key
const STORAGE_KEY_API = 'virtualpytest_anthropic_key';
const STORAGE_KEY_AUTO_NAV = 'virtualpytest_allow_auto_navigation';

interface AIState {
  // Panel Visibility
  isCommandOpen: boolean;
  isPilotOpen: boolean;
  isLogsOpen: boolean;
  
  // Task State
  activeTask: string | null;
  isProcessing: boolean;
  executionSteps: ExecutionStep[];
  
  // Status
  status: 'checking' | 'ready' | 'needs_key' | 'error';
  
  // Skills Control
  allowAutoNavigation: boolean;
  setAllowAutoNavigation: (value: boolean) => void;
  
  // Actions
  toggleCommand: () => void;
  togglePilot: () => void;
  toggleLogs: () => void;
  openCommand: () => void;
  closeCommand: () => void;
  setTask: (task: string) => void;
  setProcessing: (processing: boolean) => void;
  
  // Backend Communication
  sendMessage: (message: string, agentId?: string) => void;
  isConnected: boolean;
  
  // Agent Selection
  selectedAgentId: string;
  setSelectedAgentId: (id: string) => void;
}

interface ExecutionStep {
  id: string;
  label: string;
  status: 'pending' | 'active' | 'done' | 'error';
  detail?: string;
}

const AIContext = createContext<AIState | undefined>(undefined);

export const AIProvider: React.FC<{children: React.ReactNode}> = ({ children }) => {
  const [isCommandOpen, setCmdOpen] = useState(false);
  const [isPilotOpen, setPilotOpen] = useState(false);
  const [isLogsOpen, setLogsOpen] = useState(false);
  const [activeTask, setActiveTask] = useState<string | null>(null);
  const [isProcessing, setProcessing] = useState(false);
  const [executionSteps, setExecutionSteps] = useState<ExecutionStep[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [status, setStatus] = useState<'checking' | 'ready' | 'needs_key' | 'error'>('checking');
  const [selectedAgentId, setSelectedAgentId] = useState('ai-assistant');
  
  // Skills control - default OFF (disabled)
  const [allowAutoNavigation, setAllowAutoNavigationState] = useState(() => {
    const saved = localStorage.getItem(STORAGE_KEY_AUTO_NAV);
    return saved === 'true'; // Default false if not set
  });
  
  // Persist auto-navigation preference
  const setAllowAutoNavigation = useCallback((value: boolean) => {
    setAllowAutoNavigationState(value);
    localStorage.setItem(STORAGE_KEY_AUTO_NAV, String(value));
  }, []);
  
  const socketRef = useRef<Socket | null>(null);
  const location = useLocation();
  const navigate = useNavigate();

  // Check API key and initialize session
  useEffect(() => {
    const initSession = async () => {
      try {
        const teamId = APP_CONFIG.DEFAULT_TEAM_ID;
        
        // First check if API key is configured on backend
        const healthResponse = await fetch(buildServerUrl(`/server/agent/health?team_id=${teamId}`));
        const healthData = await healthResponse.json();
        
        if (healthData.api_key_configured) {
          // API key already configured on backend
          setStatus('ready');
        } else {
          // Check if we have a saved key in localStorage (same as AgentChat)
          const savedKey = localStorage.getItem(STORAGE_KEY_API);
          if (savedKey) {
            // Send the saved key to backend
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
            } else {
              setStatus('needs_key');
              return;
            }
          } else {
            setStatus('needs_key');
            return;
          }
        }
        
        // Create session
        const response = await fetch(buildServerUrl('/server/agent/sessions'), { method: 'POST' });
        const data = await response.json();
        if (data.success) {
          setSessionId(data.session.id);
        }
      } catch (err) {
        console.error('Failed to initialize AI session:', err);
        setStatus('error');
      }
    };
    
    initSession();
  }, []);

  useEffect(() => {
    if (!sessionId || status !== 'ready') return;

    const serverBaseUrl = getServerBaseUrl();
    const socket = io(`${serverBaseUrl}/agent`, {
      path: '/server/socket.io',
      transports: ['polling', 'websocket'],
    });

    socket.on('connect', () => {
      console.log('🤖 AI Global Context connected to /agent namespace');
      socket.emit('join_session', { session_id: sessionId });
      setIsConnected(true);
    });
    
    // Debug: log all incoming events
    socket.onAny((eventName, ...args) => {
      console.log('🔵 Socket Event Received:', eventName, args);
    });

    socket.on('disconnect', () => {
      setIsConnected(false);
    });

    // Listen for agent events
    socket.on('agent_event', (event: any) => {
      console.log('🤖 Agent Event:', event.type);
      
      // Update execution steps based on event type
      if (event.type === 'thinking') {
        setExecutionSteps(prev => [
          ...prev.map(s => s.status === 'active' ? { ...s, status: 'done' as const } : s),
          { id: `think-${Date.now()}`, label: 'Thinking', status: 'active', detail: event.content }
        ]);
      }
      
      if (event.type === 'tool_call') {
        const params = event.tool_params ? JSON.stringify(event.tool_params) : '';
        setExecutionSteps(prev => [
          ...prev.map(s => s.status === 'active' ? { ...s, status: 'done' as const } : s),
          { id: `tool-${Date.now()}`, label: event.tool_name || 'Tool', status: 'active', detail: params || 'Executing...' }
        ]);
      }
      
      if (event.type === 'tool_result') {
        // Show actual result in the step detail
        const resultStr = event.tool_result?.result || event.tool_result || 'Complete';
        const isError = typeof resultStr === 'string' && resultStr.toLowerCase().includes('error');
        setExecutionSteps(prev => 
          prev.map(s => s.status === 'active' ? { 
            ...s, 
            status: isError ? 'error' as const : 'done' as const, 
            detail: typeof resultStr === 'string' ? resultStr : JSON.stringify(resultStr)
          } : s)
        );
      }
      
      if (event.type === 'session_ended' || event.type === 'complete') {
        setProcessing(false);
        setExecutionSteps(prev => prev.map(s => ({ ...s, status: 'done' as const })));
      }
      
      if (event.type === 'error') {
        setProcessing(false);
        setExecutionSteps(prev => [
          ...prev,
          { id: `error-${Date.now()}`, label: 'Error', status: 'error', detail: event.content }
        ]);
      }
    });

    // Listen for UI Actions (Navigation, Interaction, Highlight, Toast)
    socket.on('ui_action', (event: any) => {
      console.log('🤖 UI Action:', event);
      
      // Navigation - only if enabled
      if (event.action === 'navigate' && event.payload?.path) {
        if (allowAutoNavigation) {
          console.log(`🤖 Navigating to: ${event.payload.path}`);
          
          // Emit navigation event for badge tracking
          window.dispatchEvent(new CustomEvent('ai-navigation', {
            detail: {
              from: location.pathname,
              to: event.payload.path,
              sessionId,
            }
          }));
          
          navigate(event.payload.path);
        } else {
          console.log(`🤖 Navigation blocked (disabled): ${event.payload.path}`);
        }
      }
      
      // Element Interaction
      if (event.action === 'interact' && event.payload?.element_id) {
        const { element_id, action, params } = event.payload;
        console.log(`🤖 Interacting with: ${element_id}, action: ${action}`);
        window.dispatchEvent(new CustomEvent('ai-interact', { 
          detail: { element_id, action, params } 
        }));
      }
      
      // Element Highlight
      if (event.action === 'highlight' && event.payload?.element_id) {
        const { element_id, duration_ms = 2000 } = event.payload;
        console.log(`🤖 Highlighting: ${element_id}`);
        window.dispatchEvent(new CustomEvent('ai-highlight', { 
          detail: { element_id, duration_ms } 
        }));
      }
      
      // Toast Notification
      if (event.action === 'toast' && event.payload?.message) {
        const { message, severity = 'info' } = event.payload;
        console.log(`🤖 Toast: ${severity} - ${message}`);
        window.dispatchEvent(new CustomEvent('ai-toast', { 
          detail: { message, severity } 
        }));
      }
    });

    socketRef.current = socket;

    return () => {
      socket.disconnect();
      socketRef.current = null;
    };
  }, [sessionId, status, navigate, allowAutoNavigation]);

  // Send message to backend
  const sendMessage = useCallback((message: string, agentId?: string) => {
    // Check if API key is configured
    if (status === 'needs_key') {
      setExecutionSteps([
        { 
          id: 'error-key', 
          label: 'Error', 
          status: 'error', 
          detail: '⚠️ API key not configured. Please go to AI Agent page to set your Anthropic API key.' 
        }
      ]);
      setPilotOpen(true);
      return;
    }
    
    if (!socketRef.current || !sessionId) {
      console.error('Socket not connected or no session');
      setExecutionSteps([
        { 
          id: 'error-conn', 
          label: 'Error', 
          status: 'error', 
          detail: '⚠️ Not connected to AI backend. Please refresh the page.' 
        }
      ]);
      setPilotOpen(true);
      return;
    }

    const effectiveAgentId = agentId || selectedAgentId;
    setActiveTask(message);
    setProcessing(true);
    setExecutionSteps([
      { id: 'parse', label: 'Parse Command', status: 'active', detail: 'Understanding request...' }
    ]);
    setPilotOpen(true);

    socketRef.current.emit('send_message', {
      session_id: sessionId,
      message: message,
      team_id: APP_CONFIG.DEFAULT_TEAM_ID,
      agent_id: effectiveAgentId,
    });
  }, [sessionId, status, selectedAgentId]);

  // Toggle functions
  const toggleCommand = useCallback(() => setCmdOpen(prev => !prev), []);
  const togglePilot = useCallback(() => setPilotOpen(prev => !prev), []);
  const toggleLogs = useCallback(() => setLogsOpen(prev => !prev), []);
  const openCommand = useCallback(() => setCmdOpen(true), []);
  const closeCommand = useCallback(() => setCmdOpen(false), []);
  const setTask = useCallback((task: string) => setActiveTask(task), []);

  // Keyboard Shortcut: Cmd+K
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        toggleCommand();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [toggleCommand]);

  // Auto-close Command bar on navigation
  useEffect(() => {
    if (isCommandOpen) {
      setCmdOpen(false);
    }
  }, [location.pathname]);

  return (
    <AIContext.Provider value={{ 
      isCommandOpen, isPilotOpen, isLogsOpen, 
      activeTask, isProcessing, executionSteps,
      status,
      allowAutoNavigation, setAllowAutoNavigation,
      toggleCommand, togglePilot, toggleLogs, 
      openCommand, closeCommand, setTask, setProcessing,
      sendMessage, isConnected,
      selectedAgentId, setSelectedAgentId
    }}>
      {children}
    </AIContext.Provider>
  );
};

export const useAIContext = () => {
  const context = useContext(AIContext);
  if (!context) throw new Error("useAIContext must be used within AIProvider");
  return context;
};
