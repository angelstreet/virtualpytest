import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

interface AIState {
  // Panel Visibility
  isCommandOpen: boolean;
  isPilotOpen: boolean; // Right Panel (Agent Status)
  isLogsOpen: boolean;  // Bottom Panel (Logs/Terminal)
  
  // Task State
  activeTask: string | null;
  isProcessing: boolean;
  
  // Actions
  toggleCommand: () => void;
  togglePilot: () => void;
  toggleLogs: () => void;
  openCommand: () => void;
  closeCommand: () => void;
  setTask: (task: string) => void;
  setProcessing: (processing: boolean) => void;
}

const AIContext = createContext<AIState | undefined>(undefined);

export const AIProvider: React.FC<{children: React.ReactNode}> = ({ children }) => {
  const [isCommandOpen, setCmdOpen] = useState(false);
  const [isPilotOpen, setPilotOpen] = useState(false);
  const [isLogsOpen, setLogsOpen] = useState(false);
  const [activeTask, setTask] = useState<string | null>(null);
  const [isProcessing, setProcessing] = useState(false);
  
  const location = useLocation();
  const navigate = useNavigate();

  // Toggle functions
  const toggleCommand = useCallback(() => setCmdOpen(prev => !prev), []);
  const togglePilot = useCallback(() => setPilotOpen(prev => !prev), []);
  const toggleLogs = useCallback(() => setLogsOpen(prev => !prev), []);
  
  // Explicit open/close
  const openCommand = useCallback(() => setCmdOpen(true), []);
  const closeCommand = useCallback(() => setCmdOpen(false), []);

  // Initialize the Orchestrator (Socket Listener)
  // This needs to be inside the provider to access context values, 
  // but useAIOrchestrator also needs the context. 
  // Circular dependency solution: We'll instantiate it in a separate child component or 
  // handle the logic directly here if simple.
  
  // Better approach: The orchestrator hook attaches listeners. We can just call it here?
  // NO - hooks must be called at top level. 
  // BUT useAIOrchestrator uses useAIContext which is provided BY this component.
  // So we cannot call useAIOrchestrator inside AIProvider.
  
  // We need a wrapper component in App.tsx or a child component that activates it.
  
  // Keyboard Shortcut: Cmd+K (or Ctrl+K)
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

  // Auto-open Pilot panel when a task starts processing
  useEffect(() => {
    if (isProcessing && !isPilotOpen) {
      setPilotOpen(true);
    }
  }, [isProcessing, isPilotOpen]);

  // Auto-close Command bar on navigation (optional, keeps UI clean)
  useEffect(() => {
    if (isCommandOpen) {
      setCmdOpen(false);
    }
  }, [location.pathname]);

  return (
    <AIContext.Provider value={{ 
      isCommandOpen, 
      isPilotOpen, 
      isLogsOpen, 
      activeTask, 
      isProcessing,
      toggleCommand, 
      togglePilot, 
      toggleLogs, 
      openCommand,
      closeCommand,
      setTask,
      setProcessing
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
