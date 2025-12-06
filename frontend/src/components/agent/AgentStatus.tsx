/**
 * Agent Status Component
 * 
 * Displays detailed status and metrics for a selected agent instance
 */

import React, { useState, useEffect } from 'react';
import { Activity, Clock, Zap, DollarSign, TrendingUp } from 'lucide-react';

interface AgentStatusProps {
  instanceId: string | null;
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
}

export const AgentStatus: React.FC<AgentStatusProps> = ({ instanceId }) => {
  const [status, setStatus] = useState<InstanceStatus | null>(null);
  const [loading, setLoading] = useState(false);

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
            </div>
          </div>
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

