/**
 * Global Agent Activity Context
 * 
 * Tracks all agent activities across the application.
 * Provides data for floating badges and task history.
 */

import React, { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react';
import { io, Socket } from 'socket.io-client';
import { getServerBaseUrl } from '../utils/buildUrlUtils';

// Agent metadata with nicknames
export const AGENT_METADATA: Record<string, { name: string; nickname: string; icon: string }> = {
  'ai-assistant': { name: 'AI Assistant', nickname: 'Atlas', icon: '🤖' },
  'qa-manager': { name: 'QA Manager', nickname: 'Captain', icon: '🎖️' },
  'qa-web-manager': { name: 'QA Web Manager', nickname: 'Sherlock', icon: '🧪' },
  'qa-mobile-manager': { name: 'QA Mobile Manager', nickname: 'Scout', icon: '🔍' },
  'qa-stb-manager': { name: 'QA STB Manager', nickname: 'Watcher', icon: '📺' },
  'monitoring-manager': { name: 'Monitoring Manager', nickname: 'Guardian', icon: '🛡️' },
  'explorer': { name: 'Explorer', nickname: 'Pathfinder', icon: '🧭' },
  'executor': { name: 'Executor', nickname: 'Runner', icon: '⚡' },
};

// Types
export interface AgentTask {
  id: string;
  agentId: string;
  prompt: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  triggerType: 'manual' | 'auto' | 'alert';
  triggerSource?: string; // chat, dashboard, event, schedule
  steps: TaskStep[];
  response?: string;
  summary?: { title: string; data: Record<string, any> };
  redirectedTo?: string;
  redirectedFrom?: string;
  startedAt: string;
  completedAt?: string;
  feedback?: { rating: number; comment?: string };
  error?: string;
}

export interface TaskStep {
  id: string;
  label: string;
  status: 'pending' | 'active' | 'done' | 'error';
  detail?: string;
  timestamp: string;
}

export interface AgentActivity {
  agentId: string;
  tasks: AgentTask[];
  isExpanded: boolean;
}

interface AgentActivityState {
  activities: Record<string, AgentActivity>;
  
  // Actions
  startTask: (agentId: string, prompt: string, triggerType: 'manual' | 'auto' | 'alert') => string;
  updateTaskStep: (agentId: string, taskId: string, step: TaskStep) => void;
  completeTask: (agentId: string, taskId: string, response: string, summary?: AgentTask['summary']) => void;
  failTask: (agentId: string, taskId: string, error: string) => void;
  submitFeedback: (agentId: string, taskId: string, rating: number, comment?: string) => void;
  dismissTask: (agentId: string, taskId: string) => void;
  toggleExpanded: (agentId: string) => void;
  
  // Computed
  getActiveAgents: () => string[];
  getManualTasks: () => { agentId: string; task: AgentTask }[];
  getAutoTasks: () => { agentId: string; task: AgentTask }[];
  hasActiveManualTask: () => boolean;
}

const AgentActivityContext = createContext<AgentActivityState | undefined>(undefined);

export const AgentActivityProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [activities, setActivities] = useState<Record<string, AgentActivity>>({});
  const socketRef = useRef<Socket | null>(null);
  const completionTimeouts = useRef<Record<string, NodeJS.Timeout>>({});

  // Connect to agent socket for real-time updates
  useEffect(() => {
    const serverBaseUrl = getServerBaseUrl();
    const socket = io(`${serverBaseUrl}/agent`, {
      path: '/server/socket.io',
      transports: ['polling', 'websocket'],
    });

    socket.on('connect', () => {
      console.log('🎯 AgentActivity connected to /agent namespace');
    });

    // Listen for agent events from any agent
    socket.on('agent_activity', (event: any) => {
      console.log('🎯 Agent Activity Event:', event);
      
      const { agent_id, type, task_id, ...data } = event;
      
      if (type === 'task_started') {
        startTask(agent_id, data.prompt || 'Processing...', data.trigger_type || 'auto');
      }
      
      if (type === 'step_update' && task_id) {
        updateTaskStep(agent_id, task_id, {
          id: `step-${Date.now()}`,
          label: data.label || 'Processing',
          status: data.status || 'active',
          detail: data.detail,
          timestamp: new Date().toISOString(),
        });
      }
      
      if (type === 'task_completed' && task_id) {
        completeTask(agent_id, task_id, data.response || '', data.summary);
      }
      
      if (type === 'task_failed' && task_id) {
        failTask(agent_id, task_id, data.error || 'Unknown error');
      }
    });

    socketRef.current = socket;

    return () => {
      socket.disconnect();
    };
  }, []);

  const generateId = () => `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;

  const startTask = useCallback((agentId: string, prompt: string, triggerType: 'manual' | 'auto' | 'alert'): string => {
    const taskId = generateId();
    const task: AgentTask = {
      id: taskId,
      agentId,
      prompt,
      status: 'running',
      triggerType,
      triggerSource: triggerType === 'manual' ? 'chat' : 'event',
      steps: [
        { id: 'start', label: 'Starting', status: 'done', timestamp: new Date().toISOString() },
        { id: 'process', label: 'Processing', status: 'active', timestamp: new Date().toISOString() },
      ],
      startedAt: new Date().toISOString(),
      redirectedFrom: window.location.pathname,
    };

    setActivities(prev => ({
      ...prev,
      [agentId]: {
        agentId,
        tasks: [...(prev[agentId]?.tasks || []), task],
        isExpanded: triggerType === 'manual', // Auto-expand for manual tasks
      },
    }));

    return taskId;
  }, []);

  const updateTaskStep = useCallback((agentId: string, taskId: string, step: TaskStep) => {
    setActivities(prev => {
      const activity = prev[agentId];
      if (!activity) return prev;

      return {
        ...prev,
        [agentId]: {
          ...activity,
          tasks: activity.tasks.map(t => {
            if (t.id !== taskId) return t;
            return {
              ...t,
              steps: [...t.steps.filter(s => s.status !== 'active').map(s => ({ ...s, status: 'done' as const })), step],
            };
          }),
        },
      };
    });
  }, []);

  const completeTask = useCallback((agentId: string, taskId: string, response: string, summary?: AgentTask['summary']) => {
    setActivities(prev => {
      const activity = prev[agentId];
      if (!activity) return prev;

      return {
        ...prev,
        [agentId]: {
          ...activity,
          tasks: activity.tasks.map(t => {
            if (t.id !== taskId) return t;
            return {
              ...t,
              status: 'completed',
              response,
              summary,
              completedAt: new Date().toISOString(),
              steps: t.steps.map(s => ({ ...s, status: 'done' as const })),
            };
          }),
          isExpanded: true, // Expand on completion for manual tasks
        },
      };
    });

    // Auto-dismiss auto tasks after 10 seconds
    setActivities(prev => {
      const task = prev[agentId]?.tasks.find(t => t.id === taskId);
      if (task?.triggerType !== 'manual') {
        completionTimeouts.current[taskId] = setTimeout(() => {
          dismissTask(agentId, taskId);
        }, 10000);
      }
      return prev;
    });
  }, []);

  const failTask = useCallback((agentId: string, taskId: string, error: string) => {
    setActivities(prev => {
      const activity = prev[agentId];
      if (!activity) return prev;

      return {
        ...prev,
        [agentId]: {
          ...activity,
          tasks: activity.tasks.map(t => {
            if (t.id !== taskId) return t;
            return {
              ...t,
              status: 'failed',
              error,
              completedAt: new Date().toISOString(),
              steps: [...t.steps.filter(s => s.status !== 'active'), { id: 'error', label: 'Error', status: 'error' as const, detail: error, timestamp: new Date().toISOString() }],
            };
          }),
          isExpanded: true,
        },
      };
    });
  }, []);

  const submitFeedback = useCallback((agentId: string, taskId: string, rating: number, comment?: string) => {
    setActivities(prev => {
      const activity = prev[agentId];
      if (!activity) return prev;

      return {
        ...prev,
        [agentId]: {
          ...activity,
          tasks: activity.tasks.map(t => {
            if (t.id !== taskId) return t;
            return { ...t, feedback: { rating, comment } };
          }),
        },
      };
    });

    // Dismiss after feedback
    setTimeout(() => dismissTask(agentId, taskId), 1000);
  }, []);

  const dismissTask = useCallback((agentId: string, taskId: string) => {
    // Clear any pending timeout
    if (completionTimeouts.current[taskId]) {
      clearTimeout(completionTimeouts.current[taskId]);
      delete completionTimeouts.current[taskId];
    }

    setActivities(prev => {
      const activity = prev[agentId];
      if (!activity) return prev;

      const remainingTasks = activity.tasks.filter(t => t.id !== taskId);
      
      if (remainingTasks.length === 0) {
        const { [agentId]: _, ...rest } = prev;
        return rest;
      }

      return {
        ...prev,
        [agentId]: {
          ...activity,
          tasks: remainingTasks,
        },
      };
    });
  }, []);

  const toggleExpanded = useCallback((agentId: string) => {
    setActivities(prev => {
      const activity = prev[agentId];
      if (!activity) return prev;

      return {
        ...prev,
        [agentId]: {
          ...activity,
          isExpanded: !activity.isExpanded,
        },
      };
    });
  }, []);

  const getActiveAgents = useCallback((): string[] => {
    return Object.keys(activities).filter(agentId => 
      activities[agentId].tasks.some(t => t.status === 'running' || t.status === 'completed')
    );
  }, [activities]);

  const getManualTasks = useCallback((): { agentId: string; task: AgentTask }[] => {
    const result: { agentId: string; task: AgentTask }[] = [];
    Object.entries(activities).forEach(([agentId, activity]) => {
      activity.tasks
        .filter(t => t.triggerType === 'manual')
        .forEach(task => result.push({ agentId, task }));
    });
    return result.sort((a, b) => new Date(b.task.startedAt).getTime() - new Date(a.task.startedAt).getTime());
  }, [activities]);

  const getAutoTasks = useCallback((): { agentId: string; task: AgentTask }[] => {
    const result: { agentId: string; task: AgentTask }[] = [];
    Object.entries(activities).forEach(([agentId, activity]) => {
      activity.tasks
        .filter(t => t.triggerType !== 'manual')
        .forEach(task => result.push({ agentId, task }));
    });
    return result.sort((a, b) => new Date(b.task.startedAt).getTime() - new Date(a.task.startedAt).getTime());
  }, [activities]);

  const hasActiveManualTask = useCallback((): boolean => {
    return getManualTasks().some(({ task }) => task.status === 'running' || task.status === 'completed');
  }, [getManualTasks]);

  return (
    <AgentActivityContext.Provider value={{
      activities,
      startTask,
      updateTaskStep,
      completeTask,
      failTask,
      submitFeedback,
      dismissTask,
      toggleExpanded,
      getActiveAgents,
      getManualTasks,
      getAutoTasks,
      hasActiveManualTask,
    }}>
      {children}
    </AgentActivityContext.Provider>
  );
};

export const useAgentActivity = () => {
  const context = useContext(AgentActivityContext);
  if (!context) throw new Error('useAgentActivity must be used within AgentActivityProvider');
  return context;
};

