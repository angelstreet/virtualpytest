/**
 * Agent Status Component
 * 
 * Displays detailed status and metrics for a selected agent instance
 * with control actions and subagent visibility
 */

import React, { useState, useEffect } from 'react';
import { 
  Activity, Clock, Zap, DollarSign, TrendingUp, 
  Pause, Play, StopCircle, ChevronDown, ChevronRight,
  FileText, AlertCircle, CheckCircle, XCircle
} from 'lucide-react';

interface AgentStatusProps {
  instanceId: string | null;
}

interface SubAgent {
  id: string;
  name: string;
  state: 'idle' | 'running' | 'error' | 'completed';
  current_task: string | null;
}

interface ExecutionLog {
  timestamp: string;
  level: 'info' | 'warning' | 'error' | 'success';
  message: string;
}

interface InstanceStatus {
  instance_id: string;
  agent_id: string;
  version: string;
  state: string;
  current_task: string | null;
  task_id: string | null;
  started_at: string;
  last_activity: string;
  team_id: string;
  subagents?: SubAgent[];
  execution_logs?: ExecutionLog[];
  progress?: {
    current: number;
    total: number;
    percentage: number;
  };
}

export const AgentStatus: React.FC<AgentStatusProps> = ({ instanceId }) => {
  const [status, setStatus] = useState<InstanceStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [showLogs, setShowLogs] = useState(false);
  const [showSubAgents, setShowSubAgents] = useState(true);
  const [actionInProgress, setActionInProgress] = useState<string | null>(null);

  useEffect(() => {
    if (!instanceId) {
      setStatus(null);
      return;
    }

    const fetchStatus = async () => {
      setLoading(true);
      try {
        const response = await fetch(`/api/runtime/instances/${instanceId}`);
        if (!response.ok) throw new Error('Failed to fetch status');
        
        const data = await response.json();
        setStatus(data);
      } catch (err) {
        console.error('Failed to fetch agent status:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchStatus();
    const interval = setInterval(fetchStatus, 2000);

    return () => clearInterval(interval);
  }, [instanceId]);

  if (!instanceId) {
    return (
      <div className="text-center p-8 bg-gray-50 rounded-lg border-2 border-dashed border-gray-300">
        <Activity className="w-12 h-12 mx-auto text-gray-400 mb-3" />
        <p className="text-gray-600 font-medium">No agent selected</p>
        <p className="text-sm text-gray-500 mt-1">Select an agent to view details</p>
      </div>
    );
  }

  if (loading && !status) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (!status) {
    return null;
  }

  const getUptime = () => {
    const start = new Date(status.started_at);
    const now = new Date();
    const diff = now.getTime() - start.getTime();
    
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
    
    return `${hours}h ${minutes}m`;
  };

  const handleControlAction = async (action: 'pause' | 'resume' | 'abort') => {
    if (!instanceId) return;
    
    setActionInProgress(action);
    try {
      const endpoint = action === 'abort' ? 'stop' : action;
      const response = await fetch(`/api/runtime/instances/${instanceId}/${endpoint}`, {
        method: 'POST'
      });
      
      if (!response.ok) throw new Error(`Failed to ${action} agent`);
    } catch (err) {
      console.error(`Failed to ${action} agent:`, err);
      alert(`Failed to ${action} agent. Check console for details.`);
    } finally {
      setActionInProgress(null);
    }
  };

  const getSubAgentIcon = (state: string) => {
    switch (state) {
      case 'running':
        return <Activity className="w-3 h-3 text-green-500 animate-pulse" />;
      case 'completed':
        return <CheckCircle className="w-3 h-3 text-green-600" />;
      case 'error':
        return <XCircle className="w-3 h-3 text-red-500" />;
      default:
        return <Pause className="w-3 h-3 text-gray-400" />;
    }
  };

  const getLogIcon = (level: string) => {
    switch (level) {
      case 'error':
        return <XCircle className="w-3 h-3 text-red-500" />;
      case 'warning':
        return <AlertCircle className="w-3 h-3 text-yellow-500" />;
      case 'success':
        return <CheckCircle className="w-3 h-3 text-green-500" />;
      default:
        return <Activity className="w-3 h-3 text-blue-500" />;
    }
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">{status.agent_id}</h3>
          <p className="text-sm text-gray-500">Version {status.version}</p>
        </div>
        <div className={`px-3 py-1 rounded-full text-sm font-medium ${
          status.state === 'running' ? 'bg-green-100 text-green-800' :
          status.state === 'idle' ? 'bg-gray-100 text-gray-800' :
          status.state === 'error' ? 'bg-red-100 text-red-800' :
          'bg-yellow-100 text-yellow-800'
        }`}>
          {status.state.toUpperCase()}
        </div>
      </div>

      {/* Control Actions */}
      <div className="grid grid-cols-4 gap-2">
        <button
          onClick={() => handleControlAction(status.state === 'paused' ? 'resume' : 'pause')}
          disabled={status.state === 'stopped' || status.state === 'error' || actionInProgress !== null}
          className={`
            flex items-center justify-center gap-2 px-4 py-2 rounded-lg font-medium text-sm
            transition-all disabled:opacity-50 disabled:cursor-not-allowed
            ${status.state === 'paused' 
              ? 'bg-green-100 text-green-700 hover:bg-green-200' 
              : 'bg-yellow-100 text-yellow-700 hover:bg-yellow-200'
            }
          `}
        >
          {status.state === 'paused' ? (
            <><Play className="w-4 h-4" /> Resume</>
          ) : (
            <><Pause className="w-4 h-4" /> Pause</>
          )}
        </button>

        <button
          onClick={() => handleControlAction('abort')}
          disabled={status.state === 'stopped' || actionInProgress !== null}
          className="flex items-center justify-center gap-2 px-4 py-2 bg-red-100 text-red-700 hover:bg-red-200 rounded-lg font-medium text-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <StopCircle className="w-4 h-4" /> Abort
        </button>

        <button
          onClick={() => setShowLogs(!showLogs)}
          className="flex items-center justify-center gap-2 px-4 py-2 bg-gray-100 text-gray-700 hover:bg-gray-200 rounded-lg font-medium text-sm transition-all"
        >
          <FileText className="w-4 h-4" /> Logs
        </button>

        <button
          onClick={() => setShowSubAgents(!showSubAgents)}
          disabled={!status.subagents || status.subagents.length === 0}
          className="flex items-center justify-center gap-2 px-4 py-2 bg-purple-100 text-purple-700 hover:bg-purple-200 rounded-lg font-medium text-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {showSubAgents ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
          Agents
        </button>
      </div>

      {/* Current Task */}
      {status.current_task && (
        <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <div className="flex items-start gap-3">
            <Activity className="w-5 h-5 text-blue-500 mt-0.5 animate-pulse" />
            <div className="flex-1">
              <p className="font-medium text-blue-900">Current Task</p>
              <p className="text-sm text-blue-700 mt-1">{status.current_task}</p>
              {status.task_id && (
                <p className="text-xs text-blue-600 mt-1">Task ID: {status.task_id}</p>
              )}
              
              {/* Progress Bar */}
              {status.progress && (
                <div className="mt-3">
                  <div className="flex justify-between text-xs text-blue-600 mb-1">
                    <span>{status.progress.current} / {status.progress.total}</span>
                    <span>{status.progress.percentage}%</span>
                  </div>
                  <div className="w-full bg-blue-200 rounded-full h-2">
                    <div 
                      className="bg-blue-600 h-2 rounded-full transition-all duration-500"
                      style={{ width: `${status.progress.percentage}%` }}
                    />
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* SubAgents Tree View */}
      {showSubAgents && status.subagents && status.subagents.length > 0 && (
        <div className="p-4 bg-purple-50 border border-purple-200 rounded-lg">
          <div className="flex items-center gap-2 mb-3">
            <Activity className="w-5 h-5 text-purple-600" />
            <h4 className="font-medium text-purple-900">Sub-Agents ({status.subagents.length})</h4>
          </div>
          
          <div className="space-y-2">
            {status.subagents.map((subagent, index) => (
              <div 
                key={`${subagent.id}-${index}`}
                className="pl-4 border-l-2 border-purple-300 py-2"
              >
                <div className="flex items-center gap-2 mb-1">
                  {getSubAgentIcon(subagent.state)}
                  <span className="font-medium text-sm text-gray-900">{subagent.name}</span>
                  <span className={`
                    text-xs px-2 py-0.5 rounded-full
                    ${subagent.state === 'running' ? 'bg-green-100 text-green-700' :
                      subagent.state === 'completed' ? 'bg-green-100 text-green-800' :
                      subagent.state === 'error' ? 'bg-red-100 text-red-700' :
                      'bg-gray-100 text-gray-700'}
                  `}>
                    {subagent.state}
                  </span>
                </div>
                {subagent.current_task && (
                  <p className="text-xs text-gray-600 ml-5">{subagent.current_task}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Execution Logs */}
      {showLogs && (
        <div className="p-4 bg-gray-50 border border-gray-200 rounded-lg max-h-64 overflow-y-auto">
          <h4 className="font-medium text-gray-900 text-sm mb-3 flex items-center gap-2">
            <FileText className="w-4 h-4" />
            Execution Logs
          </h4>
          
          {status.execution_logs && status.execution_logs.length > 0 ? (
            <div className="space-y-2 font-mono text-xs">
              {status.execution_logs.map((log, index) => (
                <div 
                  key={index}
                  className="flex items-start gap-2 p-2 bg-white rounded border border-gray-200"
                >
                  {getLogIcon(log.level)}
                  <div className="flex-1">
                    <span className="text-gray-500">{new Date(log.timestamp).toLocaleTimeString()}</span>
                    <span className="text-gray-900 ml-2">{log.message}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-500 text-center py-4">No logs available</p>
          )}
        </div>
      )}

      {/* Metrics Grid */}
      <div className="grid grid-cols-2 gap-4">
        {/* Uptime */}
        <div className="p-4 bg-white border border-gray-200 rounded-lg">
          <div className="flex items-center gap-2 text-gray-500 text-sm mb-2">
            <Clock className="w-4 h-4" />
            <span>Uptime</span>
          </div>
          <p className="text-2xl font-bold text-gray-900">{getUptime()}</p>
        </div>

        {/* State Duration */}
        <div className="p-4 bg-white border border-gray-200 rounded-lg">
          <div className="flex items-center gap-2 text-gray-500 text-sm mb-2">
            <Zap className="w-4 h-4" />
            <span>State</span>
          </div>
          <p className="text-2xl font-bold text-gray-900 capitalize">{status.state}</p>
        </div>
      </div>

      {/* Instance Details */}
      <div className="p-4 bg-gray-50 rounded-lg space-y-2">
        <h4 className="font-medium text-gray-900 text-sm mb-3">Instance Details</h4>
        
        <div className="flex justify-between text-sm">
          <span className="text-gray-600">Instance ID</span>
          <span className="text-gray-900 font-mono text-xs">{status.instance_id}</span>
        </div>

        <div className="flex justify-between text-sm">
          <span className="text-gray-600">Started</span>
          <span className="text-gray-900">{new Date(status.started_at).toLocaleString()}</span>
        </div>

        <div className="flex justify-between text-sm">
          <span className="text-gray-600">Last Activity</span>
          <span className="text-gray-900">{new Date(status.last_activity).toLocaleString()}</span>
        </div>

        <div className="flex justify-between text-sm">
          <span className="text-gray-600">Team</span>
          <span className="text-gray-900">{status.team_id}</span>
        </div>
      </div>

      {/* Placeholder for future metrics */}
      <div className="p-4 bg-gradient-to-br from-purple-50 to-blue-50 border border-purple-200 rounded-lg">
        <div className="flex items-center gap-2 mb-2">
          <TrendingUp className="w-5 h-5 text-purple-600" />
          <span className="font-medium text-purple-900">Performance Metrics</span>
        </div>
        <p className="text-sm text-purple-700">
          Coming soon: Task completion rate, avg duration, cost tracking
        </p>
      </div>
    </div>
  );
};

