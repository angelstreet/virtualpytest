/**
 * Execution Utility Functions
 * 
 * Shared utility functions and components for script and campaign execution.
 * Extracted from RunTests.tsx to be reused across execution interfaces.
 */

import React from 'react';
import { Chip } from '@mui/material';

// Convert report URL to logs URL helper
export const getLogsUrl = (reportUrl: string): string => {
  return reportUrl.replace('script-reports', 'script-logs').replace('report.html', 'execution.txt');
};

// Helper function to get display name for scripts (especially AI test cases)
export const getScriptDisplayName = (scriptName: string, aiTestCasesInfo?: any[]): string => {
  if (scriptName.startsWith('ai_testcase_')) {
    const aiInfo = aiTestCasesInfo?.find(info => info.script_name === scriptName);
    if (aiInfo) {
      return aiInfo.name || 'Unnamed Test Case';
    }
    return scriptName.replace('ai_testcase_', '').substring(0, 8) + '...';
  }
  return scriptName;
};

// Helper function to check if script is AI generated
export const isAIScript = (scriptName: string): boolean => {
  return scriptName.startsWith('ai_testcase_');
};

// Helper function to determine test result from script output
export const determineTestResult = (result: any): 'success' | 'failure' | undefined => {
  // Use the script_success field provided by the host - this is the authoritative result
  if (result.script_success !== undefined && result.script_success !== null) {
    return result.script_success ? 'success' : 'failure';
  }
  
  // If no script_success field, script execution likely failed at system level
  if (result.exit_code !== undefined && result.exit_code !== 0) {
    return 'failure';
  }
  
  // If script completed but no script_success field, leave undefined
  return undefined;
};

// Helper function to format execution duration
export const formatExecutionDuration = (startTime: string, endTime?: string): string => {
  if (!endTime) return 'Running...';
  
  try {
    const start = new Date(`1970-01-01 ${startTime}`);
    const end = new Date(`1970-01-01 ${endTime}`);
    const diffMs = end.getTime() - start.getTime();
    
    if (diffMs < 0) return 'Invalid';
    
    const seconds = Math.floor(diffMs / 1000);
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    
    if (minutes > 0) {
      return `${minutes}m ${remainingSeconds}s`;
    }
    return `${seconds}s`;
  } catch (error) {
    return 'Invalid';
  }
};

// Helper function to generate unique execution ID
export const generateExecutionId = (prefix: string, hostName: string, deviceId: string): string => {
  return `${prefix}_${Date.now()}_${hostName}_${deviceId}`;
};

// Helper function to extract device info from execution ID
export const extractDeviceFromExecutionId = (executionId: string): { hostName?: string; deviceId?: string } => {
  const parts = executionId.split('_');
  if (parts.length >= 4) {
    return {
      hostName: parts[2],
      deviceId: parts[3],
    };
  }
  return {};
};

// Helper function to validate parameter values
export interface ParameterValidationResult {
  valid: boolean;
  errors: string[];
}

export const validateParameterValues = (
  parameters: { name: string; required: boolean }[],
  values: { [name: string]: string }
): ParameterValidationResult => {
  const errors: string[] = [];
  
  parameters.forEach(param => {
    if (param.required && (!values[param.name] || !values[param.name].trim())) {
      errors.push(`${param.name} is required`);
    }
  });
  
  return {
    valid: errors.length === 0,
    errors,
  };
};

// Status types for consistency across components
export type ExecutionStatus = 'running' | 'completed' | 'failed' | 'aborted';
export type CampaignStatus = 'pending' | 'running' | 'completed' | 'failed' | 'aborted';
export type ScriptStatus = 'pending' | 'running' | 'completed' | 'failed' | 'skipped';

// Centralized status chip helper - extracted from RunTests.tsx to be shared
export const getStatusChip = (status: ExecutionStatus | CampaignStatus | ScriptStatus): React.JSX.Element => {
  switch (status) {
    case 'pending':
      return <Chip label="Pending" color="default" size="small" />;
    case 'running':
      return <Chip label="Running" color="warning" size="small" />;
    case 'completed':
      return <Chip label="Completed" color="success" size="small" />;
    case 'failed':
      return <Chip label="Failed" color="error" size="small" />;
    case 'aborted':
      return <Chip label="Aborted" color="error" size="small" />;
    case 'skipped':
      return <Chip label="Skipped" color="default" size="small" />;
    default:
      return <Chip label="Unknown" color="default" size="small" />;
  }
};
