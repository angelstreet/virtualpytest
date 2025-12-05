import { Terminal as ScriptIcon, Link as LinkIcon, Add as AddIcon, Close as CloseIcon, ExpandMore as ExpandMoreIcon, ExpandLess as ExpandLessIcon, AccountTree as VisualBuilderIcon } from '@mui/icons-material';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Button,
  Grid,
  Chip,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  CircularProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  Collapse,
} from '@mui/material';
import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { UserinterfaceSelector } from '../components/common/UserinterfaceSelector';
import { ParameterInputRenderer } from '../components/common/ParameterInput/ParameterInputRenderer';
import { UnifiedExecutableSelector, ExecutableItem } from '../components/common/UnifiedExecutableSelector';




import { useScript } from '../hooks/script/useScript';
import { useHostManager } from '../hooks/useHostManager';
import { useToast } from '../hooks/useToast';
import { useRun } from '../hooks/useRun';
import { getStatusChip, getScriptDisplayName, getLogsUrl } from '../utils/executionUtils';
import { useTestCaseExecution } from '../hooks/testcase/useTestCaseExecution';
import { useTestCaseSave } from '../hooks/testcase/useTestCaseSave';

import { DeviceStreamGrid } from '../components/common/DeviceStreaming/DeviceStreamGrid';



import { buildServerUrl } from '../utils/buildUrlUtils';
import { getR2Url, extractR2Path, isCloudflareR2Url } from '../utils/infrastructure/cloudflareUtils';
// Simple execution record interface
interface ExecutionRecord {
  id: string;
  scriptName: string;
  hostName: string;
  deviceId: string;
  deviceModel?: string; // Add device model field
  startTime: string;
  endTime?: string;
  status: 'running' | 'completed' | 'failed' | 'aborted';
  testResult?: 'success' | 'failure'; // New field for actual test outcome
  parameters?: string;
  reportUrl?: string;
  logsUrl?: string; // Add logs URL field
}

// Script parameter interface
interface ScriptParameter {
  name: string;
  type: 'positional' | 'optional';
  required: boolean;
  help: string;
  default?: string;
  suggestions?: {
    suggested?: string;
    confidence?: string;
  };
}





const RunTests: React.FC = () => {
  const navigate = useNavigate();
  const { executeMultipleScripts, isExecuting, executingIds } = useScript();
  const { executeTestCase } = useTestCaseExecution();
  const { getTestCase } = useTestCaseSave();
  const { showInfo, showSuccess, showError } = useToast();
  
  // State for collapsible script selector
  const [scriptSelectorExpanded, setScriptSelectorExpanded] = useState(true);
  


  const [selectedHost, setSelectedHost] = useState<string>('');
  const [selectedDevice, setSelectedDevice] = useState<string>('');
  const [selectedExecutable, setSelectedExecutable] = useState<ExecutableItem | null>(null);
  const [selectedScript, setSelectedScript] = useState<string>(''); // Keep for backward compatibility
  const [selectedUserinterface, setSelectedUserinterface] = useState<string>(''); // 🆕 NEW: Separate state for UI userinterface selection
  const [availableScripts, setAvailableScripts] = useState<string[]>([]);
  const [aiTestCasesInfo, setAiTestCasesInfo] = useState<any[]>([]);
  
  // Cache for loaded test case graphs (testcase_id -> graph)
  const [testCaseGraphCache, setTestCaseGraphCache] = useState<Record<string, any>>({});

  const [loadingScripts, setLoadingScripts] = useState<boolean>(false);
  const [showWizard, setShowWizard] = useState<boolean>(false);
  const [executions, setExecutions] = useState<ExecutionRecord[]>([]);
  const [streamsActive, setStreamsActive] = useState<boolean>(true);
  
  // Ref to prevent duplicate API calls in React Strict Mode
  const isLoadingScriptsRef = useRef<boolean>(false);

  // Multi-device support state
  interface AdditionalDevice {
    hostName: string;
    deviceId: string;
    deviceModel: string;
    userinterface: string;
  }
  const [additionalDevices, setAdditionalDevices] = useState<AdditionalDevice[]>([]);
  const [completionStats, setCompletionStats] = useState<{
    total: number;
    completed: number;
    successful: number;
  }>({ total: 0, completed: 0, successful: 0 });

  // Get host manager functions first
  const { getAllHosts, getDevicesFromHost } = useHostManager();

  // Get device model for the primary selected device (for script analysis)
  const getPrimaryDeviceModel = () => {
    if (!selectedHost || !selectedDevice) return 'unknown';
    
    const hostDevices = getDevicesFromHost(selectedHost);
    const deviceObject = hostDevices.find(device => device.device_id === selectedDevice);
    
    return deviceObject?.device_model || 'unknown';
  };



  // Sync selectedScript from selectedExecutable for backward compatibility
  useEffect(() => {
    if (selectedExecutable) {
      setSelectedScript(selectedExecutable.id);
    } else {
      setSelectedScript('');
    }
  }, [selectedExecutable]);

  // Reverse sync: When selectedScript has a value but selectedExecutable is null,
  // fetch the executable details from the backend (happens on page load with saved state)
  useEffect(() => {
    const syncExecutableFromScript = async () => {
      // Only sync if we have a script selected but no executable object
      if (selectedScript && !selectedExecutable) {
        console.log('[@RunTests] 🔄 Reverse sync triggered - selectedScript exists but selectedExecutable is null');
        console.log('[@RunTests] selectedScript:', selectedScript);
        
        try {
          // Fetch executables to find the matching one
          console.log('[@RunTests] Fetching executable list...');
          const response = await fetch(buildServerUrl('/server/executable/list'));
          const data = await response.json();
          
          console.log('[@RunTests] API response:', {
            success: data.success,
            foldersCount: data.folders?.length
          });
          
          if (data.success && data.folders) {
            // Search through all folders for the matching script/testcase
            console.log('[@RunTests] Searching for matching executable...');
            for (const folder of data.folders) {
              console.log('[@RunTests] Checking folder:', folder.name, 'items:', folder.items?.length);
              
              // Try exact match first
              let foundItem = folder.items.find((item: any) => item.id === selectedScript);
              
              // If not found and selectedScript doesn't have an extension, try adding .py
              if (!foundItem && !selectedScript.includes('.')) {
                console.log('[@RunTests] Exact match failed, trying with .py extension...');
                foundItem = folder.items.find((item: any) => item.id === `${selectedScript}.py`);
              }
              
              // If still not found, try removing extension from selectedScript
              if (!foundItem && selectedScript.includes('.')) {
                const scriptWithoutExt = selectedScript.split('.')[0];
                console.log('[@RunTests] Trying without extension:', scriptWithoutExt);
                foundItem = folder.items.find((item: any) => item.id === scriptWithoutExt);
              }
              
              if (foundItem) {
                console.log('[@RunTests] ✅ FOUND! Setting selectedExecutable:', foundItem);
                setSelectedExecutable(foundItem);
                break;
              }
            }
            if (!selectedExecutable) {
              console.log('[@RunTests] ⚠️ No matching executable found for:', selectedScript);
            }
          }
        } catch (error) {
          console.error('[@RunTests] ❌ Failed to sync executable from script:', error);
        }
      } else {
        console.log('[@RunTests] Skipping reverse sync:', {
          hasSelectedScript: !!selectedScript,
          hasSelectedExecutable: !!selectedExecutable,
          selectedScript,
          selectedExecutableName: selectedExecutable?.name
        });
      }
    };

    syncExecutableFromScript();
  }, [selectedScript, selectedExecutable]);

  // Use run hook for script analysis and parameter management
  const { 
    scriptAnalysis, 
    parameterValues, 
    handleParameterChange,
    validateParameters
  } = useRun({
    selectedScript,
    selectedDevice,
    selectedHost,
    deviceModel: getPrimaryDeviceModel(),
    showWizard
  });

  // Get hosts and devices - ensure hosts are available for stream
  const allHosts = getAllHosts(); // Always get the current hosts
  const hosts = showWizard ? allHosts : []; // Only show hosts in wizard when opened

  // Function to get available devices for selection (excluding already selected ones)
  const getAvailableDevicesForSelection = () => {
    if (!showWizard || !selectedHost) return [];
    
    const allDevicesForHost = getDevicesFromHost(selectedHost);
    const selectedDeviceIds = additionalDevices
      .filter(hd => hd.hostName === selectedHost)
      .map(hd => hd.deviceId);
    
    return allDevicesForHost.filter(device => 
      !selectedDeviceIds.includes(device.device_id)
    );
  };

  // Function to check if there are more devices available to add across all hosts
  const hasMoreDevicesAvailable = () => {
    if (!showWizard) return false;
    
    // Get all selected device combinations (host:device pairs)
    const allSelectedDevices = [...additionalDevices];
    if (selectedHost && selectedDevice) {
      // Get device model for the selected device
      const hostDevices = getDevicesFromHost(selectedHost);
      const deviceObject = hostDevices.find(device => device.device_id === selectedDevice);
      const deviceModel = deviceObject?.device_model || 'unknown';
      
      allSelectedDevices.push({ 
        hostName: selectedHost, 
        deviceId: selectedDevice,
        deviceModel: deviceModel,
        userinterface: selectedUserinterface || ''
      });
    }
    
    // Check each host to see if it has unselected devices
    for (const host of hosts) {
      const hostDevices = getDevicesFromHost(host.host_name);
      const selectedDevicesForHost = allSelectedDevices
        .filter(hd => hd.hostName === host.host_name)
        .map(hd => hd.deviceId);
      
      const availableDevicesForHost = hostDevices.filter(device => 
        !selectedDevicesForHost.includes(device.device_id)
      );
      
      if (availableDevicesForHost.length > 0) {
        return true; // Found at least one available device
      }
    }
    
    return false; // No more devices available across all hosts
  };

  // Get all devices for grid display (primary device + additional devices)
  const getAllSelectedDevices = () => {
    interface DeviceWithUserinterface {
      hostName: string;
      deviceId: string;
      userinterface?: string; // Optional for backwards compatibility with DeviceStreamGrid
    }
    const allDevices: DeviceWithUserinterface[] = [];
    
    // Add primary device if selected
    if (selectedHost && selectedDevice) {
      allDevices.push({ 
        hostName: selectedHost, 
        deviceId: selectedDevice,
        userinterface: selectedUserinterface || ''
      });
    }
    
    // Add additional devices (already have userinterface)
    allDevices.push(...additionalDevices);
    
    return allDevices;
  };

  // Check if a specific device is currently executing
  const isDeviceExecuting = (hostName: string, deviceId: string): boolean => {
    return executingIds.some(id => id.includes(`${hostName}_${deviceId}`));
  };

  // Load available scripts from virtualpytest/scripts folder
  useEffect(() => {
    const loadScripts = async () => {
      // Prevent duplicate calls in React Strict Mode
      if (isLoadingScriptsRef.current) {
        console.log('[@RunTests] Script loading already in progress, skipping duplicate call');
        return;
      }
      
      isLoadingScriptsRef.current = true;
      setLoadingScripts(true);
      
      try {
        console.log('[@RunTests] Loading scripts from API...');
        const response = await fetch(buildServerUrl('/server/script/list'));
        
        if (!response.ok) {
          throw new Error(`API returned ${response.status}`);
        }
        
        const data = await response.json();

        if (data.success) {
          setAvailableScripts(data.scripts || []);
          
          // Store AI test case metadata for display
          if (data.ai_test_cases_info) {
            setAiTestCasesInfo(data.ai_test_cases_info);
          }

          // Set default selection to first script if available
          if (data.scripts && data.scripts.length > 0 && !selectedScript) {
            setSelectedScript(data.scripts[0]);
          }
          
          console.log('[@RunTests] Scripts loaded successfully:', (data.scripts || []).length);
        } else {
          // API returned success: false - this is an actual error
          throw new Error(data.error || 'API returned success: false');
        }
      } catch (error) {
        showError('Failed to load available scripts');
        console.error('Error loading scripts:', error);
      } finally {
        setLoadingScripts(false);
        isLoadingScriptsRef.current = false;
      }
    };

    loadScripts();
  }, [showError]); // Remove selectedScript dependency - no need to reload scripts when selection changes

  // Handle pre-selection from TestCase page
  useEffect(() => {
    const handlePreSelection = () => {
      const preselectedScript = localStorage.getItem('preselected_script');
      const fromTestCase = localStorage.getItem('preselected_from_testcase');
      
      if (fromTestCase === 'true' && preselectedScript && availableScripts.includes(preselectedScript)) {
        // Set the script and open the wizard to show pre-selection
        setSelectedScript(preselectedScript);
        setShowWizard(true);
        
        // TODO: Auto-select compatible device/host based on userinterface
        // For now, user still needs to select device manually
        
        // Clear the localStorage flags
        localStorage.removeItem('preselected_script');
        localStorage.removeItem('preselected_userinterface');
        localStorage.removeItem('preselected_from_testcase');
        
        // Show toast to inform user
        showSuccess(`Pre-selected AI test case: ${getScriptDisplayName(preselectedScript, aiTestCasesInfo)}`);
      }
    };

    // Only run after scripts are loaded
    if (availableScripts.length > 0) {
      handlePreSelection();
    }
  }, [availableScripts, showSuccess]);

  // Cleanup streams when component unmounts or wizard closes
  useEffect(() => {
    return () => {
      console.log('[@RunTests] Component unmounting, stopping all streams');
      setStreamsActive(false);
    };
  }, []);

  // Stop streams when wizard closes
  useEffect(() => {
    if (!showWizard) {
      console.log('[@RunTests] Wizard closed, stopping streams');
      setStreamsActive(false);
    } else {
      console.log('[@RunTests] Wizard opened, activating streams');
      setStreamsActive(true);
    }
  }, [showWizard]);





  // Helper function to quote parameter values that need it (contain spaces or special chars)
  const quoteIfNeeded = (value: string): string => {
    // If value contains spaces, quotes, or special shell characters, wrap it in double quotes
    if (/[\s"'`$\\()&|;<>]/.test(value)) {
      // Escape any existing double quotes and backslashes
      const escaped = value.replace(/\\/g, '\\\\').replace(/"/g, '\\"');
      return `"${escaped}"`;
    }
    return value;
  };

  // Open R2 URL with automatic signed URL generation (handles both public and private modes)
  const handleOpenR2Url = async (url: string) => {
    try {
      // Extract path from full URL if needed (database stores full public URLs)
      let path = url;
      if (isCloudflareR2Url(url)) {
        const extracted = extractR2Path(url);
        if (extracted) {
          path = extracted;
        }
      }
      
      // getR2Url handles both public and private modes automatically
      const signedUrl = await getR2Url(path);
      window.open(signedUrl, '_blank');
    } catch (error) {
      console.error('[@RunTests] Failed to open R2 URL:', error);
      showError('Failed to open file. Please try again.');
    }
  };

  const buildParameterString = (deviceHost?: string, deviceId?: string, deviceUserinterface?: string) => {
    const paramStrings: string[] = [];

    // Use provided device info or fall back to selected values
    const targetHost = deviceHost || selectedHost;
    const targetDevice = deviceId || selectedDevice;
    // ✅ NEW: Get userinterface from selectedUserinterface state (not from script parameters)
    const targetUserinterface = deviceUserinterface || selectedUserinterface || '';

    // Add parameters from script analysis
    // ✅ SKIP framework params: host, device, userinterface (added at the end)
    if (scriptAnalysis) {
      scriptAnalysis.parameters.forEach((param) => {
        const value = parameterValues[param.name]?.trim() || '';
        
        // Skip framework parameters - they're added at the end
        if (param.name === 'host' || param.name === 'device' || param.name === 'userinterface') {
          return;
        }
        
        if (value) {
          if (param.type === 'positional') {
            paramStrings.push(quoteIfNeeded(value));
          } else {
            paramStrings.push(`--${param.name} ${quoteIfNeeded(value)}`);
          }
        }
      });
    }

    // ✅ Always add framework parameters at the end: --host, --device, --userinterface
    if (targetHost) {
      paramStrings.push(`--host ${quoteIfNeeded(targetHost)}`);
    }
    if (targetDevice) {
      paramStrings.push(`--device ${quoteIfNeeded(targetDevice)}`);
    }
    if (targetUserinterface) {
      paramStrings.push(`--userinterface ${quoteIfNeeded(targetUserinterface)}`);
    }

    return paramStrings.join(' ');
  };



  // Helper function to determine test result from script output
  const determineTestResult = (result: any): 'success' | 'failure' | undefined => {
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

  // Load test case graph from database (with caching) - returns full testcase data
  const loadTestCaseGraph = async (testcaseId: string): Promise<{ graph: any; scriptConfig: any } | null> => {
    // Check cache first
    if (testCaseGraphCache[testcaseId]) {
      console.log(`[@RunTests] Using cached graph for test case: ${testcaseId}`);
      return testCaseGraphCache[testcaseId];
    }
    
    console.log(`[@RunTests] Loading graph for test case: ${testcaseId}`);
    
    try {
      const response = await getTestCase(testcaseId);
      
      if (!response.success || !response.testcase) {
        showError(`Failed to load test case: ${response.error || 'Unknown error'}`);
        return null;
      }
      
      const graph = response.testcase.graph_json;
      
      // Extract script config (inputs, outputs, variables) from graph
      const scriptConfig = graph.scriptConfig || {
        inputs: [],
        outputs: [],
        variables: []
      };
      
      const cacheData = { graph, scriptConfig };
      
      // Cache the data
      setTestCaseGraphCache(prev => ({ ...prev, [testcaseId]: cacheData }));
      
      return cacheData;
    } catch (error) {
      console.error('[@RunTests] Error loading test case graph:', error);
      showError(`Failed to load test case: ${error}`);
      return null;
    }
  };

  const handleExecuteScript = async () => {
    // Determine if this is a script or test case execution
    const isTestCase = selectedExecutable?.type === 'testcase';
    
    console.log(`[@RunTests] Starting execution - Type: ${isTestCase ? 'TESTCASE' : 'SCRIPT'}`);
    
    if (isTestCase) {
      // Route to test case execution
      await handleExecuteTestCase();
    } else {
      // Route to script execution (existing logic)
      await handleExecuteScriptLegacy();
    }
  };
  
  // Test case execution handler (reusing useTestCaseExecution)
  const handleExecuteTestCase = async () => {
    if (!selectedExecutable || !selectedScript) {
      showError('Please select a test case');
      return;
    }
    
    console.log('[@RunTests:handleExecuteTestCase] Current selectedUserinterface:', selectedUserinterface);

    // Build complete device list: primary device + additional devices
    interface DeviceExecution {
      hostName: string;
      deviceId: string;
      userinterface: string;
      deviceModel: string;  // Add deviceModel
    }
    const allDevices: DeviceExecution[] = [];
    
    // ✅ ALWAYS use selectedUserinterface from UI - never from script parameters
    const userinterfaceValue = selectedUserinterface || '';
    console.log('[@RunTests:handleExecuteTestCase] Setting userinterfaceValue to:', userinterfaceValue);
    
    // Add primary device if selected
    const canAddPrimaryDevice = selectedHost && selectedDevice && userinterfaceValue;
    console.log('[@RunTests:handleExecuteTestCase] Adding primary with userinterface:', userinterfaceValue);
    
    if (canAddPrimaryDevice) {
      const hostDevices = getDevicesFromHost(selectedHost);
      const deviceObject = hostDevices.find(d => d.device_id === selectedDevice);
      const deviceModel = deviceObject?.device_model || 'unknown';
      allDevices.push({ 
        hostName: selectedHost, 
        deviceId: selectedDevice,
        userinterface: userinterfaceValue,
        deviceModel: deviceModel
      });
    }
    
    // Add additional devices
    allDevices.push(...additionalDevices);

    if (allDevices.length === 0) {
      showError('Please select at least one device');
      return;
    }
    
    // Load test case graph
    const testCaseData = await loadTestCaseGraph(selectedScript);
    if (!testCaseData) {
      return; // Error already shown in loadTestCaseGraph
    }
    
    const { graph, scriptConfig } = testCaseData;
    
    // Extract script inputs and variables for variable resolution
    const scriptInputs = scriptConfig.inputs || [];
    const scriptVariables = scriptConfig.variables || [];
    
    // ✅ CRITICAL: Rebuild graph with scriptConfig (EXACT SAME as TestCaseBuilder line 496-520)
    // TestCaseBuilder doesn't use graph from DB directly - it rebuilds it!
    const executionGraph = {
      nodes: graph.nodes,
      edges: graph.edges,
      scriptConfig: {
        inputs: scriptInputs,
        outputs: scriptConfig.outputs || [],
        variables: scriptVariables,
        metadata: {
          mode: 'append',
          fields: scriptConfig.metadata?.fields || scriptConfig.metadata || []
        }
      }
    };
    
    // Initialize completion stats
    setCompletionStats({ total: allDevices.length, completed: 0, successful: 0 });
    
    // Create execution records upfront
    const executions = allDevices.map((device) => {
      const hostDevices = getDevicesFromHost(device.hostName);
      const deviceObject = hostDevices.find(d => d.device_id === device.deviceId);
      const deviceModel = deviceObject?.device_model || 'unknown';
      
      return {
        id: `exec_${Date.now()}_${device.hostName}_${device.deviceId}`,
        scriptName: selectedExecutable.name,
        hostName: device.hostName,
        deviceId: device.deviceId,
        deviceModel: deviceModel,
        startTime: new Date().toLocaleTimeString(),
        status: 'running' as const,
        parameters: '', // Test cases don't have CLI parameters
      };
    });

    setExecutions(prev => [...executions, ...prev]);

    if (allDevices.length === 1) {
      const hostDevices = getDevicesFromHost(allDevices[0].hostName);
      const deviceObject = hostDevices.find(dev => dev.device_id === allDevices[0].deviceId);
      const deviceDisplayName = deviceObject?.device_name || allDevices[0].deviceId;
      showInfo(`Test case "${selectedExecutable.name}" started on ${allDevices[0].hostName}:${deviceDisplayName}`);
    } else {
      showInfo(`Test case "${selectedExecutable.name}" started on ${allDevices.length} devices`);
    }

    try {
      // Execute on all devices concurrently
      const executionPromises = executions.map(async (exec, index) => {
        const device = allDevices[index];
        
        try {
          console.log(`[@RunTests] Executing test case on ${device.hostName}:${device.deviceId}`);
          console.log(`[@RunTests] 🔍 DEBUG - Graph structure:`);
          console.log('  • Graph has scriptConfig?', !!graph.scriptConfig);
          console.log('  • Graph.scriptConfig:', JSON.stringify(graph.scriptConfig, null, 2));
          console.log('  • Passing scriptInputs:', scriptInputs.length, 'items');
          console.log('  • Passing scriptVariables:', scriptVariables.length, 'items');
          console.log('  • Passing userinterface:', device.userinterface);
          
          // Prepare input values for resolution
          const inputValues = scriptConfig.inputs.map((input: {name: string; default?: string; [key: string]: any}) => {
            let value = input.default || '';
            if (input.name === 'device_model_name') value = device.deviceModel || 'unknown';
            if (input.name === 'host_name') value = device.hostName;
            if (input.name === 'device_name') value = device.deviceId;
            if (input.name === 'userinterface_name') value = device.userinterface;
            return { ...input, value };
          });

          // Pass inputValues instead of scriptInputs
          const result = await executeTestCase(
            executionGraph,
            device.deviceId,
            device.hostName,
            device.userinterface,
            inputValues,  // Pass prepared input values
            scriptConfig.variables,
            selectedExecutable.name
          );
          
          // Determine result
          const executionStatus = result.success ? 'completed' : 'failed';
          const testResult = result.result_type === 'success' ? 'success' : 
                           result.result_type === 'failure' ? 'failure' : undefined;
          
          // Update execution record
          setExecutions(prev => prev.map(e => 
            e.id === exec.id ? {
              ...e,
              endTime: new Date().toLocaleTimeString(),
              status: executionStatus,
              testResult: testResult,
              reportUrl: result.report_url,
              logsUrl: result.logs_url,
              deviceModel: e.deviceModel,
            } : e
          ));
          
          // Update completion stats
          setCompletionStats(prev => ({
            ...prev,
            completed: prev.completed + 1,
            successful: prev.successful + (result.success ? 1 : 0)
          }));
          
          // Show completion toast
          const hostDevices = getDevicesFromHost(device.hostName);
          const deviceObject = hostDevices.find(dev => dev.device_id === device.deviceId);
          const deviceDisplayName = deviceObject?.device_name || device.deviceId;
          const deviceLabel = `${device.hostName}:${deviceDisplayName}`;
          
          if (result.success) {
            if (testResult === 'success') {
              showSuccess(`✅ ${deviceLabel} completed successfully - Test PASSED`);
            } else if (testResult === 'failure') {
              showError(`❌ ${deviceLabel} completed - Test FAILED`);
            } else {
              showSuccess(`✅ ${deviceLabel} completed successfully`);
            }
          } else {
            showError(`❌ ${deviceLabel} execution failed: ${result.error}`);
          }
          
          return result;
        } catch (error) {
          console.error(`[@RunTests] Error executing test case on ${device.hostName}:${device.deviceId}:`, error);
          
          // Update execution record as failed
          setExecutions(prev => prev.map(e => 
            e.id === exec.id ? {
              ...e,
              endTime: new Date().toLocaleTimeString(),
              status: 'failed',
              deviceModel: e.deviceModel,
            } : e
          ));
          
          // Update completion stats
          setCompletionStats(prev => ({
            ...prev,
            completed: prev.completed + 1
          }));
          
          return { success: false, error: error instanceof Error ? error.message : 'Unknown error' };
        }
      });
      
      // Wait for all executions to complete
      const results = await Promise.all(executionPromises);
      
      // Final summary
      const successCount = results.filter((r: any) => r.success).length;
      
      if (allDevices.length === 1) {
        // Single device summary already shown
      } else {
        // Multi-device final summary
        if (successCount === allDevices.length) {
          showSuccess(`🎉 All ${allDevices.length} devices completed successfully!`);
        } else if (successCount > 0) {
          showInfo(`📊 Final: ${successCount}/${allDevices.length} devices successful`);
        } else {
          showError(`💥 All ${allDevices.length} devices failed`);
        }
      }
      
    } catch (error) {
      showError(`Execution failed: ${error}`);
      // Mark remaining as aborted
      executions.forEach(exec => {
        setExecutions(prev => prev.map(e => 
          e.id === exec.id && e.status === 'running' ? { 
            ...e, 
            status: 'aborted', 
            endTime: new Date().toLocaleTimeString(),
            deviceModel: e.deviceModel,
          } : e
        ));
      });
    } finally {
      // Reset completion stats
      setCompletionStats({ total: 0, completed: 0, successful: 0 });
    }
  };
  
  // Script execution handler (existing logic renamed)
  const handleExecuteScriptLegacy = async () => {
    // Build complete device list: primary device + additional devices
    interface DeviceExecution {
      hostName: string;
      deviceId: string;
      userinterface: string;
    }
    const allDevices: DeviceExecution[] = [];
    
    // ✅ ALWAYS use selectedUserinterface from UI - never from script parameters
    const userinterfaceValue = selectedUserinterface;
    
    // Add primary device if selected
    const canAddPrimaryDevice = selectedHost && selectedDevice && userinterfaceValue;
    
    if (canAddPrimaryDevice) {
      allDevices.push({ 
        hostName: selectedHost, 
        deviceId: selectedDevice,
        userinterface: userinterfaceValue
      });
    }
    
    // Add additional devices
    allDevices.push(...additionalDevices);

    if (allDevices.length === 0 || !selectedScript) {
      showError('Please select at least one device and a script');
      return;
    }

    // Validate parameters
    const validation = validateParameters();
    if (!validation.valid) {
      showError(`Parameter validation failed: ${validation.errors.join(', ')}`);
      return;
    }

    // Prepare executions for concurrent processing - build parameters per device
    const executions = allDevices.map((hostDevice) => ({
      id: `exec_${Date.now()}_${hostDevice.hostName}_${hostDevice.deviceId}`,
      scriptName: selectedScript,
      hostName: hostDevice.hostName,
      deviceId: hostDevice.deviceId,
      parameters: buildParameterString(hostDevice.hostName, hostDevice.deviceId, hostDevice.userinterface), // Device-specific parameters
    }));

    // Initialize completion stats
    setCompletionStats({ total: executions.length, completed: 0, successful: 0 });

    // Create execution records upfront
    const newExecutions: ExecutionRecord[] = executions.map(exec => {
      // Get device model for this execution
      const hostDevices = getDevicesFromHost(exec.hostName);
      const deviceObject = hostDevices.find(device => device.device_id === exec.deviceId);
      const deviceModel = deviceObject?.device_model || 'unknown';
      
      return {
        id: exec.id,
        scriptName: exec.scriptName,
        hostName: exec.hostName,
        deviceId: exec.deviceId,
        deviceModel: deviceModel,
        startTime: new Date().toLocaleTimeString(),
        status: 'running',
        parameters: exec.parameters,
      };
    });

    setExecutions(prev => [...newExecutions, ...prev]);

    if (allDevices.length === 1) {
      // Get device name for single device execution toast
      const hostDevices = getDevicesFromHost(allDevices[0].hostName);
      const deviceObject = hostDevices.find(dev => dev.device_id === allDevices[0].deviceId);
      const deviceDisplayName = deviceObject?.device_name || allDevices[0].deviceId;
      showInfo(`Script "${selectedScript}" started on ${allDevices[0].hostName}:${deviceDisplayName}`);
    } else {
      showInfo(`Script "${selectedScript}" started on ${allDevices.length} devices`);
    }

    try {
      // LIVE UPDATES: Define callback for real-time completion updates
      const onExecutionComplete = (executionId: string, result: any) => {
        console.log(`[@RunTests] Execution ${executionId} completed with exit_code: ${result.exit_code}`);
        console.log(`[@RunTests] Result details:`, {
          exit_code: result.exit_code,
          report_url: result.report_url,
          logs_url: result.logs_url,
          has_stdout: !!result.stdout,
          stdout_length: result.stdout?.length || 0,
          script_success: result.script_success,
        });
        console.log(`[@RunTests] FULL RESULT OBJECT:`, result);
        
        // Update execution record immediately
        // Determine if script execution completed (vs system error)
        const scriptCompleted = result.stdout || result.stderr || result.exit_code !== undefined;
        const executionStatus = scriptCompleted ? 'completed' : 'failed';
        const testResult = determineTestResult(result);

        console.log(`[@RunTests] Determined status: ${executionStatus}, testResult: ${testResult}, reportUrl: ${result.report_url}`);

        // IMMEDIATE UI UPDATE
        setExecutions(prev => prev.map(exec => 
          exec.id === executionId ? {
            ...exec,
            endTime: new Date().toLocaleTimeString(),
            status: executionStatus,
            testResult: testResult,
            reportUrl: result.report_url,
            logsUrl: result.report_url ? getLogsUrl(result.report_url) : undefined,
            // Preserve deviceModel when updating
            deviceModel: exec.deviceModel,
          } : exec
        ));

        // Update completion stats in real-time
        setCompletionStats(prev => ({
          ...prev,
          completed: prev.completed + 1,
          successful: prev.successful + (scriptCompleted ? 1 : 0)
        }));

        // Show individual completion toast
        const device = allDevices.find(d => executionId.includes(`${d.hostName}_${d.deviceId}`));
        if (device) {
          // Get device name for display in toast
          const hostDevices = getDevicesFromHost(device.hostName);
          const deviceObject = hostDevices.find(dev => dev.device_id === device.deviceId);
          const deviceDisplayName = deviceObject?.device_name || device.deviceId;
          const deviceLabel = `${device.hostName}:${deviceDisplayName}`;
          
          if (scriptCompleted) {
            if (testResult === 'success') {
              showSuccess(`✅ ${deviceLabel} completed successfully - Test PASSED`);
            } else if (testResult === 'failure') {
              showError(`❌ ${deviceLabel} completed - Test FAILED`);
            } else {
              showSuccess(`✅ ${deviceLabel} completed successfully`);
            }
          } else {
            showError(`❌ ${deviceLabel} execution failed`);
          }
        }
      };

      // Execute with live callback - this waits for ALL to complete before returning
      const results = await executeMultipleScripts(executions, onExecutionComplete);

      // Final summary (all executions are now complete)
      // Use same logic as individual completion callbacks - count script completions (not system errors)
      const successCount = Object.values(results).filter((r: any) => {
        // Script completed if it has output or a defined exit code
        const scriptCompleted = r.stdout || r.stderr || r.exit_code !== undefined;
        return scriptCompleted;
      }).length;
      
      if (allDevices.length === 1) {
        // Single device summary already shown in callback
      } else {
        // Multi-device final summary
        if (successCount === allDevices.length) {
          showSuccess(`🎉 All ${allDevices.length} devices completed successfully!`);
        } else if (successCount > 0) {
          showInfo(`📊 Final: ${successCount}/${allDevices.length} devices successful`);
        } else {
          showError(`💥 All ${allDevices.length} devices failed`);
        }
      }

    } catch (error) {
      showError(`Execution failed: ${error}`);
      // Mark remaining as aborted
      executions.forEach(exec => {
        setExecutions(prev => prev.map(e => 
          e.id === exec.id && e.status === 'running' ? { 
            ...e, 
            status: 'aborted', 
            endTime: new Date().toLocaleTimeString(),
            // Preserve deviceModel when updating
            deviceModel: e.deviceModel,
          } : e
        ));
      });
    } finally {
      // Reset completion stats
      setCompletionStats({ total: 0, completed: 0, successful: 0 });
    }
  };



  const renderParameterInput = (param: ScriptParameter) => {
    const value = parameterValues[param.name] || '';

    // Special handling for goto-live boolean parameter
    if (param.name === 'goto-live') {
      return (
        <FormControl key={param.name} fullWidth size="small">
          <InputLabel>{`${param.name}${param.required ? ' *' : ''}`}</InputLabel>
          <Select
            value={value || 'true'}
            label={`${param.name}${param.required ? ' *' : ''}`}
            onChange={(e) => handleParameterChange(param.name, e.target.value)}
          >
            <MenuItem value="true">true</MenuItem>
            <MenuItem value="false">false</MenuItem>
          </Select>
        </FormControl>
      );
    }

    // Special handling for audio-analysis boolean parameter
    if (param.name === 'audio-analysis') {
      return (
        <FormControl key={param.name} fullWidth size="small">
          <InputLabel>{`${param.name}${param.required ? ' *' : ''}`}</InputLabel>
          <Select
            value={value || 'false'}
            label={`${param.name}${param.required ? ' *' : ''}`}
            onChange={(e) => handleParameterChange(param.name, e.target.value)}
          >
            <MenuItem value="true">true</MenuItem>
            <MenuItem value="false">false</MenuItem>
          </Select>
        </FormControl>
      );
    }

    // Use ParameterInputRenderer for all other parameters (including edge selector for KPI measurement)
    return (
      <ParameterInputRenderer
        key={param.name}
        parameter={param}
        value={value}
        onChange={handleParameterChange}
        error={param.required && !value.trim()}
        deviceModel={getPrimaryDeviceModel()}
        userinterfaceName={selectedUserinterface || ''}
        hostName={selectedHost}
      />
    );
  };

  // Framework parameters with dedicated selectors at the top (host, device, userinterface)
  // All other parameters show inline in Section 3
  // ✅ Scripts should NEVER declare these - they're framework-level infrastructure
  const FRAMEWORK_PARAMS = ['host', 'device', 'userinterface'];
  
  const displayParameters = scriptAnalysis?.parameters.filter((param) => 
    // Show all parameters EXCEPT framework params (which have dedicated UI elements)
    !FRAMEWORK_PARAMS.includes(param.name)
  ) || [];


  return (
    <Box sx={{ p: 1 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h5">
        Script Runner
      </Typography>
        <Button
          variant="outlined"
          startIcon={<VisualBuilderIcon />}
          onClick={() => navigate('/builder/test-builder')}
          size="large"
        >
          Create TestCase
        </Button>
      </Box>

      <Grid container spacing={2}>
        {/* Script Execution */}
        <Grid item xs={12}>
          <Card sx={{ '& .MuiCardContent-root': { p: 2, '&:last-child': { pb: 2 } } }}>
            <CardContent>

              {!showWizard ? (
                // Show launch button when wizard is not active
                <Box display="flex" justifyContent="center" py={2}>
                  <Button
                    variant="contained"
                    size="large"
                    startIcon={<ScriptIcon />}
                    onClick={() => setShowWizard(true)}
                  >
                    Launch Script
                  </Button>
                </Box>
              ) : (
                // Show wizard form when active
                <>
                  {/* SECTION 1: DEVICE SELECTION */}
                  <Box sx={{ mb: 1 }}>
                    <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                      <Box sx={{ minWidth: 150, flex: '1 1 150px' }}>
                        <FormControl fullWidth size="small">
                          <InputLabel>Host</InputLabel>
                          <Select
                            value={selectedHost}
                            label="Host"
                            onChange={(e) => {
                              setSelectedHost(e.target.value);
                              setSelectedDevice('');
                              setSelectedUserinterface('');
                            }}
                          >
                            {hosts.map((host) => (
                              <MenuItem key={host.host_name} value={host.host_name}>
                                {host.host_name}
                              </MenuItem>
                            ))}
                          </Select>
                        </FormControl>
                      </Box>

                      <Box sx={{ minWidth: 150, flex: '1 1 150px' }}>
                        <FormControl fullWidth size="small">
                          <InputLabel>Device</InputLabel>
                          <Select
                            value={selectedDevice}
                            label="Device"
                            onChange={(e) => {
                              setSelectedDevice(e.target.value);
                              setSelectedUserinterface('');
                            }}
                            disabled={!selectedHost || getAvailableDevicesForSelection().length === 0}
                          >
                            {getAvailableDevicesForSelection().map((device) => {
                              const deviceIsExecuting = isDeviceExecuting(selectedHost, device.device_id);
                              return (
                                <MenuItem 
                                  key={device.device_id} 
                                  value={device.device_id}
                                  disabled={deviceIsExecuting}
                                >
                                  {device.device_name || device.device_id}
                                  {deviceIsExecuting && (
                                    <Chip 
                                      label="Executing" 
                                      size="small" 
                                      color="warning" 
                                      sx={{ ml: 1, fontSize: '0.7rem', height: '18px' }} 
                                    />
                                  )}
                                </MenuItem>
                              );
                            })}
                          </Select>
                        </FormControl>
                      </Box>

                      <Box sx={{ minWidth: 150, flex: '1 1 150px' }}>
                        <UserinterfaceSelector
                          deviceModel={getPrimaryDeviceModel()}
                          value={selectedUserinterface}
                          onChange={setSelectedUserinterface}
                          label="Userinterface"
                          size="small"
                          fullWidth
                        />
                      </Box>
                    </Box>
                  </Box>

                  {/* SECTION 2: SCRIPT SELECTION - COLLAPSIBLE */}
                  <Box sx={{ mb: 1 }}>
                    <Collapse in={scriptSelectorExpanded}>
                      <UnifiedExecutableSelector
                        value={selectedExecutable}
                        onChange={setSelectedExecutable}
                        placeholder="Search by name..."
                        filters={{ folders: true, tags: true, search: true }}
                        collapseIcon={
                          <IconButton 
                            size="small" 
                            onClick={() => setScriptSelectorExpanded(!scriptSelectorExpanded)}
                          >
                            <ExpandLessIcon fontSize="small" />
                          </IconButton>
                        }
                      />
                    </Collapse>
                    {!scriptSelectorExpanded && (
                      <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
                        <IconButton 
                          size="small" 
                          onClick={() => setScriptSelectorExpanded(true)}
                        >
                          <ExpandMoreIcon fontSize="small" />
                        </IconButton>
                      </Box>
                    )}
                  </Box>

                  {/* SECTION 3: SELECTED SCRIPT + PARAMETERS - ONE LINE WITH FIXED HEIGHT */}
                  <Box sx={{ 
                    mb: 1, 
                    p: 1, 
                    bgcolor: 'action.hover', 
                    borderRadius: 1, 
                    display: 'flex', 
                    alignItems: 'center', 
                    gap: 1, 
                    flexWrap: 'wrap',
                    minHeight: 48  // Fixed height to prevent flash effect
                  }}>
                    {selectedExecutable ? (
                      <>
                        {/* Script badge + name */}
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                          <Chip
                            label={selectedExecutable.type === 'script' ? 'S' : 'TC'}
                            size="small"
                            color={selectedExecutable.type === 'script' ? 'primary' : 'secondary'}
                            sx={{ height: '20px', fontSize: '0.65rem', minWidth: '28px' }}
                          />
                          <Typography variant="body2" fontWeight="bold" sx={{ fontSize: '0.9rem' }}>
                            {selectedExecutable.name}
                          </Typography>
                        </Box>

                        {/* Bullet separator if there are parameters */}
                        {displayParameters.length > 0 && (
                          <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 'bold' }}>
                            •
                          </Typography>
                        )}

                        {/* Parameters inline without redundant labels (labels are in the inputs) */}
                        {displayParameters.map((param) => (
                          <Box key={param.name} sx={{ minWidth: 150 }}>
                            {renderParameterInput(param)}
                          </Box>
                        ))}
                      </>
                    ) : (
                      <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.85rem' }}>
                        No script selected
                      </Typography>
                    )}
                  </Box>

                  {/* Multi-device section (keep as is) */}
                  {hasMoreDevicesAvailable() && (
                    <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 1 }}>
                      {selectedHost && selectedDevice && (
                        <Button
                          variant="outlined"
                          startIcon={<AddIcon />}
                          onClick={() => {
                            const exists = additionalDevices.some(hd => hd.hostName === selectedHost && hd.deviceId === selectedDevice);
                            if (!exists) {
                              const hostDevices = getDevicesFromHost(selectedHost);
                              const deviceObject = hostDevices.find(device => device.device_id === selectedDevice);
                              const deviceModel = deviceObject?.device_model || 'unknown';
                              
                              setAdditionalDevices(prev => [...prev, { 
                                hostName: selectedHost, 
                                deviceId: selectedDevice,
                                deviceModel: deviceModel,
                                userinterface: selectedUserinterface || ''
                              }]);
                              setSelectedHost('');
                              setSelectedDevice('');
                            }
                          }}
                          disabled={
                            !selectedHost || 
                            !selectedDevice || 
                            isDeviceExecuting(selectedHost, selectedDevice)
                          }
                          size="small"
                        >
                          Add Device
                        </Button>
                      )}
                    </Box>
                  )}

                  {additionalDevices.length > 0 && (
                    <Box sx={{ mt: 2, mb: 1 }}>
                      <Typography variant="body2" sx={{ mb: 1, fontWeight: 'bold' }}>
                        Additional Devices ({additionalDevices.length}):
                      </Typography>
                      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                        {additionalDevices.map((device, index) => {
                          // Get device name and model for display
                          const hostDevices = getDevicesFromHost(device.hostName);
                          const deviceObject = hostDevices.find(d => d.device_id === device.deviceId);
                          const deviceDisplayName = deviceObject?.device_name || device.deviceId;
                          
                          return (
                            <Card 
                              key={`${device.hostName}:${device.deviceId}`}
                              variant="outlined"
                              sx={{ p: 1, backgroundColor: 'rgba(0, 0, 0, 0.02)' }}
                            >
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                {/* Device Info */}
                                <Box sx={{ flex: '0 0 200px' }}>
                                  <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                                    📱 {device.hostName}:{deviceDisplayName}
                                  </Typography>
                                  <Typography variant="caption" color="text.secondary">
                                    {device.deviceModel}
                                  </Typography>
                                </Box>
                                
                                {/* Userinterface Selector */}
                                <Box sx={{ flex: 1, minWidth: 200 }}>
                                  <UserinterfaceSelector
                                    deviceModel={device.deviceModel}
                                    value={device.userinterface}
                                    onChange={(newUserinterface) => {
                                      setAdditionalDevices(prev => prev.map((d, i) => 
                                        i === index ? { ...d, userinterface: newUserinterface } : d
                                      ));
                                    }}
                                    label="Userinterface"
                                    size="small"
                                    fullWidth
                                  />
                                </Box>
                                
                                {/* Remove Button */}
                                <IconButton
                                  size="small"
                                  onClick={() => {
                                    setAdditionalDevices(prev => prev.filter((_, i) => i !== index));
                                  }}
                                  sx={{ ml: 'auto' }}
                                >
                                  <CloseIcon />
                                </IconButton>
                              </Box>
                            </Card>
                          );
                        })}
                      </Box>
                    </Box>
                  )}

                  {/* Real-time progress indicator */}
                  {isExecuting && completionStats.total > 1 && (
                    <Box sx={{ mb: 2 }}>
                      <Card variant="outlined">
                        <CardContent sx={{ py: 1 }}>
                          <Typography variant="body2" color="text.secondary">
                            Execution Progress: {completionStats.completed}/{completionStats.total} completed 
                            ({completionStats.successful} successful)
                          </Typography>
                          <Box sx={{ display: 'flex', gap: 1, mt: 1, flexWrap: 'wrap' }}>
                            {executingIds.map(id => {
                              // Extract device info from execution ID
                              const parts = id.split('_');
                              if (parts.length >= 4) {
                                const hostName = parts[2];
                                const deviceId = parts[3];
                                // Get device name for display
                                const hostDevices = getDevicesFromHost(hostName);
                                const deviceObject = hostDevices.find(device => device.device_id === deviceId);
                                const deviceDisplayName = deviceObject?.device_name || deviceId;
                                const deviceInfo = `${hostName}:${deviceDisplayName}`;
                                
                                return (
                                  <Chip
                                    key={id}
                                    label={deviceInfo}
                                    color="warning"
                                    size="small"
                                    icon={<CircularProgress size={16} />}
                                  />
                                );
                              } else {
                                return (
                                  <Chip
                                    key={id}
                                    label={id}
                                    color="warning"
                                    size="small"
                                    icon={<CircularProgress size={16} />}
                                  />
                                );
                              }
                            })}
                          </Box>
                        </CardContent>
                      </Card>
                    </Box>
                  )}

                  {/* SECTION 4: EXECUTE/CANCEL BUTTONS */}
                  <Box display="flex" gap={1}>
                    <Button
                      variant="contained"
                      startIcon={isExecuting ? <CircularProgress size={16} /> : <ScriptIcon />}
                      onClick={handleExecuteScript}
                      disabled={
                        // Check if selected device is currently executing
                        (selectedHost && selectedDevice && isDeviceExecuting(selectedHost, selectedDevice)) ||
                        // Need at least one device
                        ((!selectedHost || !selectedDevice) && additionalDevices.length === 0) ||
                        !selectedScript ||
                        loadingScripts ||
                        !validateParameters().valid ||
                        (selectedExecutable?.type === 'testcase' && !selectedUserinterface && additionalDevices.every(d => !d.userinterface))
                      }
                      size="small"
                    >
                      {isExecuting 
                        ? `Executing... (${executingIds.length} running)` 
                        : `Execute${((selectedHost && selectedDevice) ? 1 : 0) + additionalDevices.length > 1 ? ` on ${((selectedHost && selectedDevice) ? 1 : 0) + additionalDevices.length} devices` : ''}`
                      }
                    </Button>
                    <Button
                      variant="outlined"
                      onClick={() => {
                        console.log('[@RunTests] Cancel clicked, stopping streams and closing wizard');
                        setStreamsActive(false);
                        setShowWizard(false);
                        setSelectedHost('');
                        setSelectedDevice('');
                        setAdditionalDevices([]);
                      }}
                      size="small"
                    >
                      Cancel
                    </Button>
                  </Box>
                </>
              )}
            </CardContent>
          </Card>
        </Grid>



        {/* Device Stream Grid - Show when we have at least one device */}
        {showWizard && ((selectedHost && selectedDevice) || additionalDevices.length > 0) && (
          <Grid item xs={12}>
            <Card sx={{ '& .MuiCardContent-root': { p: 2, '&:last-child': { pb: 2 } } }}>
              <CardContent>
                <Typography variant="h6" sx={{ mb: 2 }}>
                  Device Streams ({getAllSelectedDevices().length})
                </Typography>
                
                <DeviceStreamGrid devices={getAllSelectedDevices()} allHosts={allHosts} getDevicesFromHost={getDevicesFromHost} isActive={streamsActive} />
              </CardContent>
            </Card>
          </Grid>
        )}

        {/* Execution History */}
        <Grid item xs={12}>
          <Card sx={{ '& .MuiCardContent-root': { p: 2, '&:last-child': { pb: 2 } } }}>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 1 }}>
                Execution History
              </Typography>

              {executions.length === 0 ? (
                <Box
                  sx={{
                    p: 2,
                    textAlign: 'center',
                    borderRadius: 1,
                    backgroundColor: 'background.default',
                  }}
                >
                  <Typography variant="body2" color="textSecondary">
                    No script executions yet
                  </Typography>
                </Box>
              ) : (
                <TableContainer component={Paper} variant="outlined">
                  <Table size="small" sx={{ '& .MuiTableCell-root': { py: 0.5 } }}>
                    <TableHead>
                      <TableRow>
                        <TableCell>Script</TableCell>
                        <TableCell>Device</TableCell>
                        <TableCell>Start Time</TableCell>
                        <TableCell>End Time</TableCell>
                        <TableCell>Status</TableCell>
                        <TableCell>Results</TableCell>
                        <TableCell>Report</TableCell>
                        <TableCell>Logs</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {executions.map((execution) => (
                        <TableRow
                          key={execution.id}
                          sx={{
                            '&:hover': {
                              backgroundColor: 'rgba(0, 0, 0, 0.04) !important',
                            },
                          }}
                        >
                          <TableCell>{getScriptDisplayName(execution.scriptName, aiTestCasesInfo)}</TableCell>
                          <TableCell>
                            {(() => {
                              // Get device name for display in execution history
                              const hostDevices = getDevicesFromHost(execution.hostName);
                              const deviceObject = hostDevices.find(device => device.device_id === execution.deviceId);
                              const deviceDisplayName = deviceObject?.device_name || execution.deviceId;
                              return `${execution.hostName}:${deviceDisplayName}`;
                            })()}
                            {execution.deviceModel && (
                              <Typography variant="caption" display="block" color="text.secondary">
                                ({execution.deviceModel})
                              </Typography>
                            )}
                          </TableCell>
                          <TableCell>{execution.startTime}</TableCell>
                          <TableCell>{execution.endTime || '-'}</TableCell>
                          <TableCell>{getStatusChip(execution.status)}</TableCell>
                          <TableCell>
                            {execution.testResult ? (
                              execution.testResult === 'success' ? (
                                <Chip label="SUCCESS" color="success" size="small" />
                              ) : (
                                <Chip label="FAILURE" color="error" size="small" />
                              )
                            ) : execution.status === 'completed' ? (
                              <Chip label="UNKNOWN" color="default" size="small" />
                            ) : (
                              '-'
                            )}
                          </TableCell>
                          <TableCell>
                            {execution.reportUrl ? (
                              <Chip
                                label="View Report"
                                clickable
                                onClick={() => handleOpenR2Url(execution.reportUrl!)}
                                size="small"
                                sx={{ cursor: 'pointer' }}
                                icon={<LinkIcon />}
                                color="primary"
                                variant="outlined"
                              />
                            ) : (
                              <Chip label="No Report" size="small" variant="outlined" disabled />
                            )}
                          </TableCell>
                          <TableCell>
                            {execution.logsUrl ? (
                              <Chip
                                icon={<LinkIcon />}
                                label="Logs"
                                size="small"
                                clickable
                                onClick={() => handleOpenR2Url(execution.logsUrl!)}
                                color="secondary"
                                variant="outlined"
                              />
                            ) : (
                              <Chip label="No Logs" size="small" variant="outlined" disabled />
                            )}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default RunTests;
