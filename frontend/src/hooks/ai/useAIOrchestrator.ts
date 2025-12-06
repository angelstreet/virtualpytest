import { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { io, Socket } from 'socket.io-client';
import { getServerBaseUrl } from '../../utils/buildUrlUtils';
import { useAIContext } from '../../contexts/AIContext';

interface UIEvent {
  type: 'ui_action';
  action: string;
  payload: any;
  agent_message?: string;
}

export const useAIOrchestrator = () => {
  const { 
    setTask, 
    setProcessing, 
    togglePilot 
  } = useAIContext();
  
  const navigate = useNavigate();
  const socketRef = useRef<Socket | null>(null);

  useEffect(() => {
    // 1. Initialize Socket Connection
    const serverBaseUrl = getServerBaseUrl();
    // Ensure we don't create multiple connections
    if (!socketRef.current) {
      socketRef.current = io(`${serverBaseUrl}/agent`, {
        path: '/server/socket.io',
        transports: ['polling', 'websocket'],
        reconnection: true,
      });
    }

    const socket = socketRef.current;

    socket.on('connect', () => {
      console.log('🤖 AI Orchestrator connected');
    });

    // 2. Listen for UI Actions (Navigation, etc.)
    socket.on('ui_action', (event: UIEvent) => {
      console.log('🤖 Received UI Action:', event);

      if (event.action === 'navigate') {
        const path = event.payload.path;
        if (path) {
          console.log(`🤖 Navigating to: ${path}`);
          navigate(path);
          
          // Optional: Show toast or update status
        }
      }
    });

    // 3. Listen for Agent Events to update UI state
    socket.on('agent_event', (event: any) => {
      // Auto-open pilot panel if agent is thinking or acting
      if (['thinking', 'tool_call', 'agent_delegated'].includes(event.type)) {
        setProcessing(true);
      }
      
      if (['session_ended', 'complete', 'error'].includes(event.type)) {
        setProcessing(false);
      }
    });

    return () => {
      if (socketRef.current) {
        socketRef.current.disconnect();
        socketRef.current = null;
      }
    };
  }, [navigate, setProcessing]);

  return {
    socket: socketRef.current
  };
};


