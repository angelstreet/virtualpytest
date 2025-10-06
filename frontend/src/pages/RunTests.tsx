import { Terminal as ScriptIcon, Link as LinkIcon, Add as AddIcon, Close as CloseIcon } from '@mui/icons-material';
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
  TextField,
  IconButton,
} from '@mui/material';
import React, { useState, useEffect, useRef } from 'react';
import { UserinterfaceSelector } from '../components/common/UserinterfaceSelector';




import { useScript } from '../hooks/script/useScript';
import { useHostManager } from '../hooks/useHostManager';
import { useToast } from '../hooks/useToast';
import { useRun } from '../hooks/useRun';
import { getStatusChip, getScriptDisplayName, isAIScript, getLogsUrl } from '../utils/executionUtils';

import { DeviceStreamGrid } from '../components/common/DeviceStreaming/DeviceStreamGrid';



import { buildServerUrl } from '../utils/buildUrlUtils';
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
  const { executeMultipleScripts, isExecuting, executingIds } = useScript();
  const { showInfo, showSuccess, showError } = useToast();
  


  const [selectedHost, setSelectedHost] = useState<string>('');
  const [selectedDevice, setSelectedDevice] = useState<string>('');
  const [selectedScript, setSelectedScript] = useState<string>('');
  const [selectedUserinterface, setSelectedUserinterface] = useState<string>(''); // Framework-level parameter
  const [availableScripts, setAvailableScripts] = useState<string[]>([]);
  const [aiTestCasesInfo, setAiTestCasesInfo] = useState<any[]>([]);

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
        userinterface: selectedUserinterface
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
        userinterface: selectedUserinterface 
      });
    }
    
    // Add additional devices (already have userinterface)
    allDevices.push(...additionalDevices);
    
    return allDevices;
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
        const data = await response.json();

        if (data.success && data.scripts) {
          setAvailableScripts(data.scripts);
          
          // Store AI test case metadata for display
          if (data.ai_test_cases_info) {
            setAiTestCasesInfo(data.ai_test_cases_info);
          }

          // Set default selection to first script if available
          if (data.scripts.length > 0 && !selectedScript) {
            setSelectedScript(data.scripts[0]);
          }
          
          console.log('[@RunTests] Scripts loaded successfully:', data.scripts.length);
        } else {
          showError('Failed to load available scripts');
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





  const buildParameterString = (deviceHost?: string, deviceId?: string, deviceUserinterface?: string) => {
    const paramStrings: string[] = [];

    // Use provided device info or fall back to selected values
    const targetHost = deviceHost || selectedHost;
    const targetDevice = deviceId || selectedDevice;
    const targetUserinterface = deviceUserinterface || selectedUserinterface;

    // FIRST: Add userinterface_name as positional argument (framework requirement)
    if (targetUserinterface) {
      paramStrings.push(targetUserinterface);
    }

    // Add parameters from script analysis
    if (scriptAnalysis) {
      scriptAnalysis.parameters.forEach((param) => {
        const value = parameterValues[param.name]?.trim();
        
        // Skip host, device, and userinterface_name - they're framework parameters
        if (param.name === 'host' || param.name === 'device' || param.name === 'userinterface_name') {
          return;
        }
        
        if (value) {
          if (param.type === 'positional') {
            paramStrings.push(value);
          } else {
            paramStrings.push(`--${param.name} ${value}`);
          }
        }
      });
    }

    // Always add --host and --device parameters
    if (targetHost) {
      paramStrings.push(`--host ${targetHost}`);
    }
    if (targetDevice) {
      paramStrings.push(`--device ${targetDevice}`);
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

  const handleExecuteScript = async () => {
    // Build complete device list: primary device + additional devices
    interface DeviceExecution {
      hostName: string;
      deviceId: string;
      userinterface: string;
    }
    const allDevices: DeviceExecution[] = [];
    
    // Add primary device if selected
    if (selectedHost && selectedDevice && selectedUserinterface) {
      allDevices.push({ 
        hostName: selectedHost, 
        deviceId: selectedDevice,
        userinterface: selectedUserinterface
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
      parameters: buildParameterString(hostDevice.hostName, hostDevice.deviceId, hostDevice.userinterface), // Device-specific parameters including userinterface
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

    // Note: userinterface_name is a framework parameter shown at top level, not here

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

    // Default text field for all parameters - use value from useRun hook (which handles defaults)
    return (
      <TextField
        key={param.name}
        label={`${param.name}${param.required ? ' *' : ''}`}
        value={value}
        onChange={(e) => handleParameterChange(param.name, e.target.value)}
        size="small"
        fullWidth
        error={param.required && !value.trim()}
        placeholder={param.default || ''}
      />
    );
  };

  // Filter to show required parameters and important optional ones
  // Exclude framework parameters: host, device, userinterface_name (shown at top level)
  // Important optional parameters to always show (even if not required)
  const importantOptionalParams = ['node', 'max-iteration', 'action', 'goto-live', 'audio-analysis', 'edges'];
  
  const displayParameters = scriptAnalysis?.parameters.filter((param) => 
    // Show required parameters (except framework ones)
    (param.required && param.name !== 'host' && param.name !== 'device' && param.name !== 'userinterface_name') ||
    // Show important optional parameters
    importantOptionalParams.includes(param.name)
  ) || [];


  return (
    <Box sx={{ p: 1 }}>
      <Typography variant="h5" sx={{ mb: 1 }}>
        Script Runner
      </Typography>

      <Grid container spacing={2}>
        {/* Script Execution */}
        <Grid item xs={12}>
          <Card sx={{ '& .MuiCardContent-root': { p: 2, '&:last-child': { pb: 2 } } }}>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 1 }}>
                Execute Script
              </Typography>

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
                  {/* First row: All main parameters on one line */}
                  <Box sx={{ display: 'flex', gap: 1, mb: 1, flexWrap: 'wrap' }}>
                    <Box sx={{ minWidth: 150, flex: '1 1 150px' }}>
                      <FormControl fullWidth size="small">
                        <InputLabel>Script</InputLabel>
                        <Select
                          value={selectedScript}
                          label="Script"
                          onChange={(e) => setSelectedScript(e.target.value)}
                          disabled={loadingScripts}
                        >
                          {loadingScripts ? (
                            <MenuItem value="">
                              <CircularProgress size={20} />
                            </MenuItem>
                          ) : availableScripts.length === 0 ? (
                            <MenuItem value="">No scripts available</MenuItem>
                          ) : (
                            availableScripts.map((script) => (
                              <MenuItem key={script} value={script}>
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                  {isAIScript(script) && (
                                    <Chip 
                                      label="AI" 
                                      size="small" 
                                      color="primary" 
                                      sx={{ fontSize: '0.7rem', height: '18px' }} 
                                    />
                                  )}
                                  <Typography variant="body2">
                                    {getScriptDisplayName(script, aiTestCasesInfo)}
                                  </Typography>
                                </Box>
                              </MenuItem>
                            ))
                          )}
                        </Select>
                      </FormControl>
                    </Box>

                    <Box sx={{ minWidth: 150, flex: '1 1 150px' }}>
                      <FormControl fullWidth size="small">
                        <InputLabel>Host</InputLabel>
                        <Select
                          value={selectedHost}
                          label="Host"
                          onChange={(e) => {
                            setSelectedHost(e.target.value);
                            setSelectedDevice(''); // Reset device when host changes
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
                          onChange={(e) => setSelectedDevice(e.target.value)}
                          disabled={!selectedHost || getAvailableDevicesForSelection().length === 0}
                        >
                          {getAvailableDevicesForSelection().map((device) => (
                            <MenuItem key={device.device_id} value={device.device_id}>
                              {device.device_name || device.device_id}
                            </MenuItem>
                          ))}
                        </Select>
                      </FormControl>
                    </Box>

                    {/* Userinterface - Framework parameter (like host/device) */}
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

                    {/* Parameters on the same row */}
                    {displayParameters.length > 0 &&
                      displayParameters.map((param) => (
                        <Box key={param.name} sx={{ minWidth: 120, flex: '1 1 120px' }}>
                          {renderParameterInput(param)}
                        </Box>
                      ))}
                  </Box>

                  {/* Second row: Add Device button aligned right - only show if more devices are available */}
                  {hasMoreDevicesAvailable() && (
                    <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 1 }}>
                      {selectedHost && selectedDevice && selectedUserinterface && (
                        <Button
                          variant="outlined"
                          startIcon={<AddIcon />}
                          onClick={() => {
                            const exists = additionalDevices.some(hd => hd.hostName === selectedHost && hd.deviceId === selectedDevice);
                            if (!exists) {
                              // Get device model for the selected device
                              const hostDevices = getDevicesFromHost(selectedHost);
                              const deviceObject = hostDevices.find(device => device.device_id === selectedDevice);
                              const deviceModel = deviceObject?.device_model || 'unknown';
                              
                              setAdditionalDevices(prev => [...prev, { 
                                hostName: selectedHost, 
                                deviceId: selectedDevice,
                                deviceModel: deviceModel,
                                userinterface: selectedUserinterface // Use currently selected userinterface
                              }]);
                              // Reset current selection to allow adding different device
                              setSelectedHost('');
                              setSelectedDevice('');
                              setSelectedUserinterface('');
                            }
                          }}
                          disabled={!selectedHost || !selectedDevice || !selectedUserinterface}
                          size="small"
                        >
                          Add Device
                        </Button>
                      )}
                    </Box>
                  )}

                  {/* Show additional devices with per-device userinterface selectors */}
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

                  <Box display="flex" gap={1}>
                    <Button
                      variant="contained"
                      startIcon={isExecuting ? <CircularProgress size={16} /> : <ScriptIcon />}
                      onClick={handleExecuteScript}
                      disabled={
                        isExecuting ||  // EXECUTION LOCK: Prevent new executions while any are running
                        ((!selectedHost || !selectedDevice) && additionalDevices.length === 0) ||  // Need at least one device
                        !selectedScript ||
                        !selectedUserinterface ||  // Framework parameter required
                        loadingScripts ||
                        !validateParameters().valid
                      }
                      size="small"
                    >
                      {isExecuting 
                        ? `Executing... (${executingIds.length} running)` 
                        : `Execute Script${((selectedHost && selectedDevice) ? 1 : 0) + additionalDevices.length > 1 ? ` on ${((selectedHost && selectedDevice) ? 1 : 0) + additionalDevices.length} devices` : ''}`
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
                        setSelectedUserinterface('');
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
                                component="a"
                                href={execution.reportUrl}
                                target="_blank"
                                clickable
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
                                onClick={() => window.open(execution.logsUrl!, '_blank')}
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
