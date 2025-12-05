import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { io, Socket } from 'socket.io-client';
import { buildServerUrl, getServerBaseUrl } from '../utils/buildUrlUtils';

interface AIState {
  // Panel Visibility
  isCommandOpen: boolean;
  isPilotOpen: boolean;
  isLogsOpen: boolean;
  
  // Task State
  activeTask: string | null;
  isProcessing: boolean;
  executionSteps: ExecutionStep[];
  
  // Actions
  toggleCommand: () => void;
  togglePilot: () => void;
  toggleLogs: () => void;
  openCommand: () => void;
  closeCommand: () => void;
  setTask: (task: string) => void;
  setProcessing: (processing: boolean) => void;
  
  // Backend Communication
  sendMessage: (message: string) => void;
  isConnected: boolean;
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
  
  const socketRef = useRef<Socket | null>(null);
  const location = useLocation();
  const navigate = useNavigate();

  // Initialize Socket Connection
  useEffect(() => {
    const initSession = async () => {
      try {
        const response = await fetch(buildServerUrl('/server/agent/sessions'), { method: 'POST' });
        const data = await response.json();
        if (data.success) {
          setSessionId(data.session.id);
        }
      } catch (err) {
        console.error('Failed to create AI session:', err);
      }
    };
    
    initSession();
  }, []);

  useEffect(() => {
    if (!sessionId) return;

    const serverBaseUrl = getServerBaseUrl();
    const socket = io(`${serverBaseUrl}/agent`, {
      path: '/server/socket.io',
      transports: ['polling', 'websocket'],
    });

    socket.on('connect', () => {
      console.log('🤖 AI Global Context connected to /agent namespace');
      console.log('🤖 Socket ID:', socket.id);
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

    // Listen for UI Actions (Navigation)
    socket.on('ui_action', (event: any) => {
      console.log('🤖 UI Action:', event);
      
      if (event.action === 'navigate' && event.payload?.path) {
        console.log(`🤖 Navigating to: ${event.payload.path}`);
        navigate(event.payload.path);
      }
    });

    socketRef.current = socket;

    return () => {
      socket.disconnect();
      socketRef.current = null;
    };
  }, [sessionId, navigate]);

  // Send message to backend
  const sendMessage = useCallback((message: string) => {
    if (!socketRef.current || !sessionId) {
      console.error('Socket not connected or no session');
      return;
    }

    setActiveTask(message);
    setProcessing(true);
    setExecutionSteps([
      { id: 'parse', label: 'Parse Command', status: 'active', detail: 'Understanding request...' }
    ]);
    setPilotOpen(true);

    socketRef.current.emit('send_message', {
      session_id: sessionId,
      message: message,
    });
  }, [sessionId]);

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
      toggleCommand, togglePilot, toggleLogs, 
      openCommand, closeCommand, setTask, setProcessing,
      sendMessage, isConnected
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
