/**
 * AI Agent TypeScript Interfaces
 * Defines types for AI agent execution, steps, and task management
 */

export interface AIStep {
  step: number;
  command: string;
  description: string;
  params?: Record<string, any>;
  estimatedDuration?: number;
}

export interface AIPlan {
  plan: AIStep[];
  analysis: string;
  feasible: boolean;
  estimated_time?: string;
  risk_level?: 'low' | 'medium' | 'high';
}

export interface AIExecutionLogEntry {
  timestamp: string;
  type: string;
  action_type: 'plan_generated' | 'plan_ready' | 'step_start' | 'step_success' | 'step_failed' | 'task_completed' | 'task_failed';
  value: any;
  description: string;
}

export interface AIStepResult {
  step: number;
  command: string;
  success: boolean;
  duration: number;
  error?: string;
}

export interface AITaskExecution {
  id: string;
  taskDescription: string;
  startTime: number;
  endTime?: number;
  totalDuration?: number;
  steps: AIStep[];
  executedSteps: AIStepResult[];
  success: boolean;
  summary: string;
}

export interface AIExecutionSummary {
  totalSteps: number;
  completedSteps: number;
  failedSteps: number;
  totalDuration: number;
  averageStepDuration: number;
  success: boolean;
  message: string;
}

export interface AITaskResult {
  success: boolean;
  message: string;
  executionDetails: {
    total_executed: number;
    total_planned: number;
    actions_executed: number;
    actions_planned: number;
    verifications_executed: number;
    verifications_planned: number;
  };
  summary: AIExecutionSummary;
}

export const AI_CONSTANTS = {
  POLL_INTERVAL: 2000,
  MAX_WAIT_TIME: 300000,
  TOAST_DURATION: {
    INFO: 2000,
    SUCCESS: 4000,
    ERROR: 5000,
  },
  PROGRESS_COLORS: {
    CURRENT: '#2196f3',
    SUCCESS: '#4caf50',
    FAILED: '#f44336',
    PENDING: '#666',
  }
} as const;
