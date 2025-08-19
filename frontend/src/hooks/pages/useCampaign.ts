/**
 * Campaign Execution Hook
 *
 * This hook handles campaign execution operations including:
 * - Campaign configuration and validation
 * - Campaign execution with real-time progress tracking
 * - Campaign history management
 * - Script analysis and parameter management
 */

import { useState, useCallback, useEffect } from 'react';
import {
  CampaignConfig,
  CampaignExecution,
  CampaignExecutionResult,
  CampaignHistoryItem,
  CampaignValidationResult,
  ScriptConfiguration,
  ScriptAnalysis,

  CampaignBuilderState,
  ScriptConfigurationValidation
} from '../../types/pages/Campaign_Types';

interface UseCampaignReturn {
  // Campaign Execution
  executeCampaign: (config: CampaignConfig) => Promise<CampaignExecutionResult>;
  isExecuting: boolean;
  currentExecution: CampaignExecution | null;
  executionProgress: {
    current_script_index: number;
    total_scripts: number;
    completed_scripts: number;
    successful_scripts: number;
    failed_scripts: number;
  };

  // Campaign Configuration
  campaignConfig: Partial<CampaignConfig>;
  updateCampaignConfig: (updates: Partial<CampaignConfig>) => void;
  resetCampaignConfig: () => void;

  // Script Management
  availableScripts: string[];
  aiTestCasesInfo: any[];
  loadAvailableScripts: () => Promise<void>;
  addScript: (scriptName: string) => void;
  removeScript: (index: number) => void;
  reorderScripts: (fromIndex: number, toIndex: number) => void;
  updateScriptConfiguration: (index: number, updates: Partial<ScriptConfiguration>) => void;

  // Script Analysis
  scriptAnalysisCache: { [scriptName: string]: ScriptAnalysis };
  loadScriptAnalysis: (scriptName: string) => Promise<ScriptAnalysis | null>;

  // Validation
  validateCampaignConfig: (config?: CampaignConfig) => CampaignValidationResult;
  validateScriptConfiguration: (scriptConfig: ScriptConfiguration) => ScriptConfigurationValidation;

  // Campaign History
  campaignHistory: CampaignHistoryItem[];

  // State Management
  builderState: CampaignBuilderState;
  isLoading: boolean;
  error: string | null;
}

const CAMPAIGN_API_BASE_URL = '/server/campaigns';
const SCRIPT_API_BASE_URL = '/server/script';

export const useCampaign = (): UseCampaignReturn => {
  // Execution State
  const [isExecuting, setIsExecuting] = useState(false);
  const [currentExecution, setCurrentExecution] = useState<CampaignExecution | null>(null);
  const [executionProgress, setExecutionProgress] = useState({
    current_script_index: 0,
    total_scripts: 0,
    completed_scripts: 0,
    successful_scripts: 0,
    failed_scripts: 0,
  });

  // Configuration State
  const [campaignConfig, setCampaignConfig] = useState<Partial<CampaignConfig>>({
    execution_config: {
      continue_on_failure: true,
      timeout_minutes: 120, // Fixed to 2 hours
      parallel: false,
    },
    script_configurations: [],
  });

  // Script Management State
  const [availableScripts, setAvailableScripts] = useState<string[]>([]);
  const [aiTestCasesInfo, setAiTestCasesInfo] = useState<any[]>([]);
  const [scriptAnalysisCache, setScriptAnalysisCache] = useState<{ [scriptName: string]: ScriptAnalysis }>({});

  // History State (managed locally like RunTests.tsx)
  const [campaignHistory, setCampaignHistory] = useState<CampaignHistoryItem[]>([]);

  // General State
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Validation Functions (defined early to avoid hoisting issues)
  const validateCampaignConfig = useCallback((config?: CampaignConfig): CampaignValidationResult => {
    const configToValidate = config || (campaignConfig as CampaignConfig);
    const errors: string[] = [];
    const warnings: string[] = [];

    // Required fields
    if (!configToValidate.campaign_id) errors.push('Campaign ID is required');
    if (!configToValidate.name) errors.push('Campaign name is required');
    if (!configToValidate.host) errors.push('Host is required');
    if (!configToValidate.device) errors.push('Device is required');
    if (!configToValidate.userinterface_name) errors.push('User interface is required');

    // Script configurations
    if (!configToValidate.script_configurations || configToValidate.script_configurations.length === 0) {
      errors.push('At least one script must be configured');
    } else {
      // Validate each script configuration
      configToValidate.script_configurations.forEach((script, index) => {
        if (!script.script_name) errors.push(`Script ${index + 1}: Script name is required`);
        if (!script.script_type) errors.push(`Script ${index + 1}: Script type is required`);
        if (script.order === undefined || script.order < 0) errors.push(`Script ${index + 1}: Valid order is required`);
        
        // Validate parameters if available
        if (script.parameters) {
          Object.entries(script.parameters).forEach(([paramName, paramValue]) => {
            if (paramValue === '' || paramValue === null || paramValue === undefined) {
              warnings.push(`Script ${index + 1}: Parameter '${paramName}' is empty`);
            }
          });
        }
      });
    }

    // Execution config validation (timeout fixed to 2h)
    if (!configToValidate.execution_config) {
      configToValidate.execution_config = {
        timeout_minutes: 120,
        continue_on_failure: true,
        parallel: false,
      };
    } else {
      // Always ensure timeout is 2 hours
      configToValidate.execution_config.timeout_minutes = 120;
    }

    return {
      valid: errors.length === 0,
      errors,
      warnings,
    };
  }, [campaignConfig]);

  // Builder State (computed)
  const builderState: CampaignBuilderState = {
    config: campaignConfig,
    selectedHost: campaignConfig.host || '',
    selectedDevice: campaignConfig.device || '',
    availableScripts,
    scriptAnalysisCache,
    isValid: validateCampaignConfig(campaignConfig as CampaignConfig).valid,
    validationErrors: validateCampaignConfig(campaignConfig as CampaignConfig).errors,
  };

  // Load available scripts on mount
  useEffect(() => {
    loadAvailableScripts();
  }, []);

  // Campaign Execution Functions
  const executeCampaign = useCallback(async (config: CampaignConfig): Promise<CampaignExecutionResult> => {
    console.log(`[@hook:useCampaign:executeCampaign] Starting campaign: ${config.name}`);
    
    setIsExecuting(true);
    setError(null);
    
    // Initialize execution tracking
    const execution: CampaignExecution = {
      id: `campaign_exec_${Date.now()}`,
      campaign_id: config.campaign_id,
      campaign_name: config.name,
      hostName: config.host,
      deviceId: config.device,
      startTime: new Date().toLocaleTimeString(),
      status: 'running',
      current_script_index: 0,
      total_scripts: config.script_configurations.length,
      completed_scripts: 0,
      successful_scripts: 0,
      failed_scripts: 0,
      script_executions: config.script_configurations.map((script, index) => ({
        script_name: script.script_name,
        script_type: script.script_type,
        description: script.description,
        order: index,
        status: 'pending',
        parameters: script.parameters,
      })),
      execution_config: config.execution_config,
    };
    
    setCurrentExecution(execution);
    setExecutionProgress({
      current_script_index: 0,
      total_scripts: config.script_configurations.length,
      completed_scripts: 0,
      successful_scripts: 0,
      failed_scripts: 0,
    });

    try {
      const response = await fetch(`${CAMPAIGN_API_BASE_URL}/execute`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-ID': 'default-user', // TODO: Get from auth context
        },
        body: JSON.stringify(config),
      });

      const result: CampaignExecutionResult = await response.json();

      if (!response.ok) {
        throw new Error(result.message || 'Campaign execution failed');
      }

      console.log(`[@hook:useCampaign:executeCampaign] Campaign started:`, result);

      // Handle async execution (poll for status)
      if (result.async && result.execution_id) {
        await pollCampaignExecution(result.execution_id);
      }

      // Update execution record
      const updatedExecution: CampaignExecution = {
        ...currentExecution!,
        endTime: new Date().toLocaleTimeString(),
        status: result.success ? 'completed' : 'failed',
        overall_success: result.result?.overall_success,
      };
      
      setCurrentExecution(updatedExecution);
      
      // Convert to history item format (like RunTests.tsx does)
      const historyItem: CampaignHistoryItem = {
        id: updatedExecution.id,
        campaign_name: updatedExecution.campaign_name,
        campaign_id: updatedExecution.campaign_id,
        execution_id: result.execution_id || updatedExecution.id,
        hostName: updatedExecution.hostName,
        deviceId: updatedExecution.deviceId,
        deviceModel: updatedExecution.deviceModel,
        startTime: updatedExecution.startTime,
        endTime: updatedExecution.endTime,
        status: updatedExecution.status,
        overall_success: updatedExecution.overall_success,
        total_scripts: result.result?.total_scripts || updatedExecution.total_scripts,
        successful_scripts: result.result?.successful_scripts || updatedExecution.successful_scripts,
        failed_scripts: result.result?.failed_scripts || updatedExecution.failed_scripts,
        reportUrl: result.result?.script_executions?.[0]?.report_url, // Use first script's report for now
        logsUrl: result.result?.script_executions?.[0]?.logs_url, // Use first script's logs for now
      };
      
      setCampaignHistory(prev => [historyItem, ...prev]);

      return result;

    } catch (error) {
      console.error(`[@hook:useCampaign:executeCampaign] Error:`, error);
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      setError(errorMessage);
      
      // Update execution record with error
      const failedExecution: CampaignExecution = {
        ...currentExecution!,
        endTime: new Date().toLocaleTimeString(),
        status: 'failed',
        overall_success: false,
      };
      
      setCurrentExecution(failedExecution);
      
      // Convert to history item format (like RunTests.tsx does)
      const failedHistoryItem: CampaignHistoryItem = {
        id: failedExecution.id,
        campaign_name: failedExecution.campaign_name,
        campaign_id: failedExecution.campaign_id,
        execution_id: failedExecution.id, // Use ID as execution_id for failed campaigns
        hostName: failedExecution.hostName,
        deviceId: failedExecution.deviceId,
        deviceModel: failedExecution.deviceModel,
        startTime: failedExecution.startTime,
        endTime: failedExecution.endTime,
        status: failedExecution.status,
        overall_success: failedExecution.overall_success,
        total_scripts: failedExecution.total_scripts,
        successful_scripts: failedExecution.successful_scripts,
        failed_scripts: failedExecution.failed_scripts,
      };
      
      setCampaignHistory(prev => [failedHistoryItem, ...prev]);
      
      throw error;
    } finally {
      setIsExecuting(false);
    }
  }, []);

  // Poll campaign execution status
  const pollCampaignExecution = useCallback(async (executionId: string) => {
    const pollInterval = 5000; // 5 seconds
    const maxWaitTime = 7200000; // 2 hours
    const startTime = Date.now();

    while (Date.now() - startTime < maxWaitTime) {
      await new Promise(resolve => setTimeout(resolve, pollInterval));

      try {
        const response = await fetch(`${CAMPAIGN_API_BASE_URL}/status/${executionId}`);
        const statusResult = await response.json();

        if (statusResult.success && statusResult.execution) {
          const execution = statusResult.execution;
          
          // Update current execution with live data
          setCurrentExecution(prev => prev ? {
            ...prev,
            status: execution.status,
            current_script: execution.current_script,
            current_script_index: execution.current_script_index || 0,
            completed_scripts: execution.completed_scripts || 0,
            successful_scripts: execution.successful_scripts || 0,
            failed_scripts: execution.failed_scripts || 0,
            script_executions: execution.script_executions || prev.script_executions,
            overall_success: execution.overall_success,
          } : null);

          // Update progress
          setExecutionProgress(prev => ({
            ...prev,
            current_script_index: execution.current_script_index || 0,
            completed_scripts: execution.completed_scripts || 0,
            successful_scripts: execution.successful_scripts || 0,
            failed_scripts: execution.failed_scripts || 0,
          }));

          // Check if completed
          if (execution.status === 'completed' || execution.status === 'failed') {
            console.log(`[@hook:useCampaign] Campaign ${executionId} ${execution.status}`);
            break;
          }
        }
      } catch (pollError) {
        console.warn(`[@hook:useCampaign] Error polling campaign status:`, pollError);
      }
    }
  }, []);

  // Configuration Management
  const updateCampaignConfig = useCallback((updates: Partial<CampaignConfig>) => {
    setCampaignConfig(prev => ({
      ...prev,
      ...updates,
    }));
  }, []);

  const resetCampaignConfig = useCallback(() => {
    setCampaignConfig({
      execution_config: {
        continue_on_failure: true,
        timeout_minutes: 60,
        parallel: false,
      },
      script_configurations: [],
    });
  }, []);

  // Script Management (single API call like RunTests.tsx)
  const loadAvailableScripts = useCallback(async () => {
    try {
      setIsLoading(true);
      const response = await fetch(`${SCRIPT_API_BASE_URL}/list`);
      const data = await response.json();

      if (data.success && data.scripts) {
        setAvailableScripts(data.scripts);
        
        // Also load AI test cases info in the same call (avoid duplicate API calls)
        if (data.ai_test_cases_info) {
          setAiTestCasesInfo(data.ai_test_cases_info);
        }
      } else {
        throw new Error('Failed to load available scripts');
      }
    } catch (error) {
      console.error('[@hook:useCampaign] Error loading scripts:', error);
      setError(error instanceof Error ? error.message : 'Failed to load scripts');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const addScript = useCallback((scriptName: string) => {
    const newScript: ScriptConfiguration = {
      script_name: scriptName,
      script_type: scriptName.includes('fullzap') ? 'fullzap' : 'generic',
      description: `Execute ${scriptName}`,
      parameters: {},
      order: campaignConfig.script_configurations?.length || 0,
    };

    setCampaignConfig(prev => ({
      ...prev,
      script_configurations: [
        ...(prev.script_configurations || []),
        newScript,
      ],
    }));
  }, [campaignConfig.script_configurations]);

  const removeScript = useCallback((index: number) => {
    setCampaignConfig(prev => ({
      ...prev,
      script_configurations: (prev.script_configurations || []).filter((_, i) => i !== index),
    }));
  }, []);

  const reorderScripts = useCallback((fromIndex: number, toIndex: number) => {
    setCampaignConfig(prev => {
      const scripts = [...(prev.script_configurations || [])];
      const [movedScript] = scripts.splice(fromIndex, 1);
      scripts.splice(toIndex, 0, movedScript);
      
      // Update order numbers
      scripts.forEach((script, index) => {
        script.order = index;
      });

      return {
        ...prev,
        script_configurations: scripts,
      };
    });
  }, []);

  const updateScriptConfiguration = useCallback((index: number, updates: Partial<ScriptConfiguration>) => {
    setCampaignConfig(prev => ({
      ...prev,
      script_configurations: (prev.script_configurations || []).map((script, i) => 
        i === index ? { ...script, ...updates } : script
      ),
    }));
  }, []);

  // Script Analysis
  const loadScriptAnalysis = useCallback(async (scriptName: string): Promise<ScriptAnalysis | null> => {
    // Check cache first
    if (scriptAnalysisCache[scriptName]) {
      return scriptAnalysisCache[scriptName];
    }

    try {
      const response = await fetch(`${SCRIPT_API_BASE_URL}/analyze/${encodeURIComponent(scriptName)}`);
      const data = await response.json();

      if (data.success && data.analysis) {
        const analysis: ScriptAnalysis = {
          script_name: scriptName,
          parameters: data.analysis.parameters || [],
          description: data.analysis.description,
          estimated_duration: data.analysis.estimated_duration,
        };

        // Cache the analysis
        setScriptAnalysisCache(prev => ({
          ...prev,
          [scriptName]: analysis,
        }));

        return analysis;
      }
    } catch (error) {
      console.error(`[@hook:useCampaign] Error analyzing script ${scriptName}:`, error);
    }

    return null;
  }, [scriptAnalysisCache]);



  const validateScriptConfiguration = useCallback((scriptConfig: ScriptConfiguration): ScriptConfigurationValidation => {
    const errors: string[] = [];
    const parameter_errors: { [paramName: string]: string } = {};

    if (!scriptConfig.script_name) {
      errors.push('Script name is required');
    }

    // Validate parameters against script analysis
    const analysis = scriptAnalysisCache[scriptConfig.script_name];
    if (analysis) {
      analysis.parameters.forEach(param => {
        if (param.required && !scriptConfig.parameters[param.name]) {
          parameter_errors[param.name] = `${param.name} is required`;
        }
      });
    }

    return {
      script_name: scriptConfig.script_name,
      valid: errors.length === 0 && Object.keys(parameter_errors).length === 0,
      errors,
      parameter_errors,
    };
  }, [scriptAnalysisCache]);

  // Campaign History (local state management like RunTests.tsx - no refresh function needed)

  return {
    // Execution
    executeCampaign,
    isExecuting,
    currentExecution,
    executionProgress,

    // Configuration
    campaignConfig,
    updateCampaignConfig,
    resetCampaignConfig,

    // Script Management
    availableScripts,
    aiTestCasesInfo,
    loadAvailableScripts,
    addScript,
    removeScript,
    reorderScripts,
    updateScriptConfiguration,

    // Analysis
    scriptAnalysisCache,
    loadScriptAnalysis,

    // Validation
    validateCampaignConfig,
    validateScriptConfiguration,

    // History
    campaignHistory,

    // State
    builderState,
    isLoading,
    error,
  };
};
