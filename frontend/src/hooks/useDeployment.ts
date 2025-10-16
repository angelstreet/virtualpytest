import { useState } from 'react';
import { buildServerUrl } from '../utils/buildUrlUtils';

export interface Deployment {
  id: string;
  name: string;
  host_name: string;
  device_id: string;
  script_name: string;
  userinterface_name: string;
  parameters?: string;
  
  // Cron-based scheduling
  cron_expression: string;
  start_date?: string | null;
  end_date?: string | null;
  max_executions?: number | null;
  
  // Execution tracking
  execution_count: number;
  last_executed_at?: string | null;
  
  status: 'active' | 'paused' | 'stopped' | 'completed' | 'expired';
  created_at: string;
}

export interface DeploymentExecution {
  id: string;
  deployment_id: string;
  started_at: string;
  completed_at?: string;
  success?: boolean;
  error_message?: string;
}

export const useDeployment = () => {
  const [loading, setLoading] = useState(false);

  const createDeployment = async (data: Partial<Deployment>) => {
    setLoading(true);
    try {
      const response = await fetch(buildServerUrl('/server/deployment/create'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      return await response.json();
    } finally {
      setLoading(false);
    }
  };

  const listDeployments = async () => {
    const response = await fetch(buildServerUrl('/server/deployment/list'));
    return await response.json();
  };

  const pauseDeployment = async (id: string) => {
    const response = await fetch(buildServerUrl(`/server/deployment/pause/${id}`), { method: 'POST' });
    return await response.json();
  };

  const resumeDeployment = async (id: string) => {
    const response = await fetch(buildServerUrl(`/server/deployment/resume/${id}`), { method: 'POST' });
    return await response.json();
  };

  const deleteDeployment = async (id: string) => {
    const response = await fetch(buildServerUrl(`/server/deployment/delete/${id}`), { method: 'DELETE' });
    return await response.json();
  };

  const getDeploymentHistory = async (id: string) => {
    const response = await fetch(buildServerUrl(`/server/deployment/history/${id}`));
    return await response.json();
  };

  const getRecentExecutions = async () => {
    const response = await fetch(buildServerUrl('/server/deployment/executions/recent'));
    return await response.json();
  };

  return {
    loading,
    createDeployment,
    listDeployments,
    pauseDeployment,
    resumeDeployment,
    deleteDeployment,
    getDeploymentHistory,
    getRecentExecutions,
  };
};

