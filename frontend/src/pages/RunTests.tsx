import { Terminal as ScriptIcon, Link as LinkIcon, Add as AddIcon } from '@mui/icons-material';
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
  Autocomplete,
} from '@mui/material';
import React, { useState, useEffect } from 'react';

import { HLSVideoPlayer } from '../components/common/HLSVideoPlayer';
import { useStream } from '../hooks/controller/useStream';
import { useScript } from '../hooks/script/useScript';
import { useHostManager } from '../hooks/useHostManager';
import { useToast } from '../hooks/useToast';
import { calculateVncScaling } from '../utils/vncUtils';


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

interface ScriptAnalysis {
  success: boolean;
  parameters: ScriptParameter[];
  script_name: string;
  has_parameters: boolean;
  error?: string;
}

// Component for displaying a grid of device streams
interface DeviceStreamGridProps {
  devices: {hostName: string, deviceId: string}[];
  allHosts: any[];
  getDevicesFromHost: (hostName: string) => any[];
}

const DeviceStreamGrid: React.FC<DeviceStreamGridProps> = ({ devices, allHosts, getDevicesFromHost }) => {
  return (
    <Box
      sx={{
        display: 'grid',
        gridTemplateColumns: `repeat(${Math.min(devices.length, 3)}, 1fr)`, // Max 3 columns
        gap: 2,
        maxWidth: '100%',
      }}
    >
      {devices.map((device, index) => (
        <DeviceStreamItem
          key={`${device.hostName}-${device.deviceId}-${index}`}
          device={device}
          allHosts={allHosts}
          getDevicesFromHost={getDevicesFromHost}
        />
      ))}
    </Box>
  );
};

// Component for individual device stream
interface DeviceStreamItemProps {
  device: {hostName: string, deviceId: string};
  allHosts: any[];
  getDevicesFromHost: (hostName: string) => any[];
}

const DeviceStreamItem: React.FC<DeviceStreamItemProps> = ({ device, allHosts, getDevicesFromHost }) => {
  const hostObject = allHosts.find((host) => host.host_name === device.hostName);
  
  // Use stream hook to get device stream
  const { streamUrl, isLoadingUrl, urlError } = useStream({
    host: hostObject!,
    device_id: device.deviceId || '',
  });

  // Get device model
  const deviceObject = getDevicesFromHost(device.hostName).find(
    (d) => d.device_id === device.deviceId
  );
  const deviceModel = deviceObject?.device_model || 'unknown';
  
  // Check if mobile model for sizing
  const isMobileModel = !!(deviceModel && deviceModel.toLowerCase().includes('mobile'));
  
  // Calculate sizes for grid layout - use larger height to show full content
  const streamHeight = 250; // Increased from 200 to show more content
  const streamWidth = isMobileModel ? Math.round(streamHeight * (9/16)) : Math.round(streamHeight * (16/9));

  return (
    <Box
      sx={{
        backgroundColor: 'black',
        borderRadius: 1,
        overflow: 'hidden',
        height: streamHeight,
        minWidth: streamWidth,
        display: 'flex',
        flexDirection: 'column',
        position: 'relative', // Add positioning context like RecHostStreamModal
      }}
    >
      {/* Device label */}
      <Box sx={{ px: 1, py: 0.5, backgroundColor: 'rgba(0,0,0,0.8)', color: 'white' }}>
        <Typography variant="caption" noWrap>
          {device.hostName}:{device.deviceId} ({deviceModel})
        </Typography>
      </Box>
      
      {/* Stream content */}
      <Box sx={{ 
        flex: 1, 
        position: 'relative', 
        backgroundColor: 'black',
        overflow: 'hidden', // Ensure content doesn't overflow
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}>
        {streamUrl && hostObject ? (
          // VNC devices: Show iframe, Others: Use HLSVideoPlayer
          deviceModel === 'host_vnc' ? (
            <Box
              sx={{
                position: 'relative',
                width: '100%',
                height: '100%',
                backgroundColor: 'black',
                overflow: 'hidden',
              }}
            >
              <iframe
                src={streamUrl}
                style={{
                  border: 'none',
                  backgroundColor: '#000',
                  pointerEvents: 'none',
                  display: 'block',
                  margin: '0 auto',
                  ...calculateVncScaling({ width: streamWidth, height: streamHeight - 24 }), // Subtract label height
                }}
                title={`VNC Desktop - ${device.hostName}:${device.deviceId}`}
                allow="fullscreen"
              />
            </Box>
          ) : (
            <HLSVideoPlayer
              streamUrl={streamUrl}
              isStreamActive={true}
              isCapturing={false}
              model={deviceModel}
              layoutConfig={{
                minHeight: `${streamHeight - 24}px`,
                aspectRatio: isMobileModel ? '9/16' : '16/9',
                objectFit: 'contain', // Prevent cropping like RecHostStreamModal
                isMobileModel,
              }}
              isExpanded={false}
              muted={true}
              sx={{
                width: '100%',
                height: '100%',
              }}
            />
          )
        ) : (
          <Box
            sx={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'white',
              textAlign: 'center',
              height: '100%',
            }}
          >
            {isLoadingUrl ? (
              <>
                <CircularProgress sx={{ color: 'white', mb: 1 }} size={20} />
                <Typography variant="caption">Loading...</Typography>
              </>
            ) : urlError ? (
              <>
                <Typography color="error" variant="caption" sx={{ mb: 1 }}>
                  Stream Error
                </Typography>
                <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.6rem' }}>
                  {urlError}
                </Typography>
              </>
            ) : (
              <Typography variant="caption">No stream available</Typography>
            )}
          </Box>
        )}
      </Box>
    </Box>
  );
};

const RunTests: React.FC = () => {
  const { executeMultipleScripts, isExecuting, executingIds } = useScript();
  const { showInfo, showSuccess, showError } = useToast();
  


  const [selectedHost, setSelectedHost] = useState<string>('');
  const [selectedDevice, setSelectedDevice] = useState<string>('');
  const [selectedScript, setSelectedScript] = useState<string>('');
  const [availableScripts, setAvailableScripts] = useState<string[]>([]);
  const [loadingScripts, setLoadingScripts] = useState<boolean>(false);
  const [showWizard, setShowWizard] = useState<boolean>(false);
  const [executions, setExecutions] = useState<ExecutionRecord[]>([]);

  // Multi-device support state
  const [additionalDevices, setAdditionalDevices] = useState<{hostName: string, deviceId: string}[]>([]);
  const [completionStats, setCompletionStats] = useState<{
    total: number;
    completed: number;
    successful: number;
  }>({ total: 0, completed: 0, successful: 0 });

  // Script parameters state
  const [scriptAnalysis, setScriptAnalysis] = useState<ScriptAnalysis | null>(null);
  const [parameterValues, setParameterValues] = useState<Record<string, string>>({});
  const [_analyzingScript, setAnalyzingScript] = useState<boolean>(false);

  // Only fetch host data when wizard is shown
  const { getAllHosts, getDevicesFromHost } = useHostManager();

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
      allSelectedDevices.push({ hostName: selectedHost, deviceId: selectedDevice });
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
    const allDevices: {hostName: string, deviceId: string}[] = [];
    
    // Add primary device if selected
    if (selectedHost && selectedDevice) {
      allDevices.push({ hostName: selectedHost, deviceId: selectedDevice });
    }
    
    // Add additional devices
    allDevices.push(...additionalDevices);
    
    return allDevices;
  };

  // Get device model for the primary selected device (for script analysis)
  const getPrimaryDeviceModel = () => {
    if (!selectedHost || !selectedDevice) return 'unknown';
    
    const hostDevices = getDevicesFromHost(selectedHost);
    const deviceObject = hostDevices.find(device => device.device_id === selectedDevice);
    
    return deviceObject?.device_model || 'unknown';
  };

  // Load available scripts from virtualpytest/scripts folder
  useEffect(() => {
    const loadScripts = async () => {
      setLoadingScripts(true);
      try {
        const response = await fetch('/server/script/list');
        const data = await response.json();

        if (data.success && data.scripts) {
          setAvailableScripts(data.scripts);

          // Set default selection to first script if available
          if (data.scripts.length > 0 && !selectedScript) {
            setSelectedScript(data.scripts[0]);
          }
        } else {
          showError('Failed to load available scripts');
        }
      } catch (error) {
        showError('Failed to load available scripts');
        console.error('Error loading scripts:', error);
      } finally {
        setLoadingScripts(false);
      }
    };

    loadScripts();
  }, [selectedScript, showError]);

  // Analyze script parameters when script selection changes
  useEffect(() => {
    const analyzeScript = async () => {
      if (!selectedScript || !showWizard) {
        setScriptAnalysis(null);
        setParameterValues({});
        return;
      }

      setAnalyzingScript(true);
      try {
        const response = await fetch('/server/script/analyze', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            script_name: selectedScript,
            device_model: getPrimaryDeviceModel(),
            device_id: selectedDevice,
          }),
        });

        const analysis: ScriptAnalysis = await response.json();

        if (analysis.success) {
          setScriptAnalysis(analysis);

          // Pre-fill parameter values with suggestions
          const newParameterValues: Record<string, string> = {};
          analysis.parameters.forEach((param) => {
            if (param.suggestions?.suggested) {
              newParameterValues[param.name] = param.suggestions.suggested;
            } else if (param.default) {
              newParameterValues[param.name] = param.default;
            } else {
              newParameterValues[param.name] = '';
            }
          });
          setParameterValues(newParameterValues);
        } else {
          setScriptAnalysis(null);
          setParameterValues({});
        }
      } catch (error) {
        console.error('Error analyzing script:', error);
        setScriptAnalysis(null);
        setParameterValues({});
      } finally {
        setAnalyzingScript(false);
      }
    };

    analyzeScript();
  }, [selectedScript, selectedDevice, selectedHost, showWizard]);

  // Update parameter suggestions when device changes
  useEffect(() => {
    const deviceModel = getPrimaryDeviceModel();
    if (scriptAnalysis && selectedDevice && deviceModel) {
      const newParameterValues = { ...parameterValues };

      scriptAnalysis.parameters.forEach((param) => {
        // Re-evaluate suggestions based on new device context
        if (param.name === 'userinterface_name' && deviceModel) {
          const modelLower = deviceModel.toLowerCase();
          let suggested = '';

          if (modelLower.includes('mobile') || modelLower.includes('phone')) {
            suggested = 'horizon_android_mobile';
          } else if (modelLower.includes('tv') || modelLower.includes('android_tv')) {
            suggested = 'horizon_android_tv';
          } else if (modelLower.includes('web') || modelLower.includes('browser')) {
            suggested = 'perseus_360_web';
          } else {
            // Default to mobile interface for unknown device types
            suggested = 'horizon_android_mobile';
          }

          newParameterValues[param.name] = suggested;
        } else if (param.name === 'device' && selectedDevice) {
          newParameterValues[param.name] = selectedDevice;
        } else if (param.name === 'host' && selectedHost) {
          newParameterValues[param.name] = selectedHost;
        }
      });

      setParameterValues(newParameterValues);
    }
  }, [selectedDevice, selectedHost, scriptAnalysis]);

  const handleParameterChange = (paramName: string, value: string) => {
    setParameterValues((prev) => ({
      ...prev,
      [paramName]: value,
    }));
  };

  const buildParameterString = (deviceHost?: string, deviceId?: string) => {
    const paramStrings: string[] = [];

    // Use provided device info or fall back to selected values
    const targetHost = deviceHost || selectedHost;
    const targetDevice = deviceId || selectedDevice;

    // Always add userinterface_name as the first positional parameter if we have script analysis
    if (scriptAnalysis) {
      scriptAnalysis.parameters.forEach((param) => {
        let value = parameterValues[param.name]?.trim();
        
        // Override userinterface_name based on target device's model
        if (param.name === 'userinterface_name' && targetHost && targetDevice) {
          const hostDevices = getDevicesFromHost(targetHost);
          const deviceObject = hostDevices.find(device => device.device_id === targetDevice);
          const deviceModel = deviceObject?.device_model || 'unknown';
          const modelLower = deviceModel.toLowerCase();
          
          if (modelLower.includes('mobile') || modelLower.includes('phone')) {
            value = 'horizon_android_mobile';
          } else if (modelLower.includes('tv') || modelLower.includes('android_tv')) {
            value = 'horizon_android_tv';
          } else if (modelLower.includes('web') || modelLower.includes('browser') || modelLower.includes('vnc')) {
            value = 'perseus_360_web';
          } else {
            // Default to mobile interface for unknown device types
            value = 'horizon_android_mobile';
          }
        }
        
        if (value) {
          if (param.type === 'positional') {
            paramStrings.push(value);
          } else {
            paramStrings.push(`--${param.name} ${value}`);
          }
        }
      });
    } else {
      // If no script analysis, determine userinterface_name based on device model
      if (targetHost && targetDevice) {
        const hostDevices = getDevicesFromHost(targetHost);
        const deviceObject = hostDevices.find(device => device.device_id === targetDevice);
        const deviceModel = deviceObject?.device_model || 'unknown';
        const modelLower = deviceModel.toLowerCase();
        
        if (modelLower.includes('mobile') || modelLower.includes('phone')) {
          paramStrings.push('horizon_android_mobile');
        } else if (modelLower.includes('tv') || modelLower.includes('android_tv')) {
          paramStrings.push('horizon_android_tv');
        } else if (modelLower.includes('web') || modelLower.includes('browser') || modelLower.includes('vnc')) {
          paramStrings.push('perseus_360_web');
        } else {
          paramStrings.push('horizon_android_mobile');
        }
      } else {
        paramStrings.push('horizon_android_mobile');
      }
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

  const validateParameters = () => {
    if (!scriptAnalysis) return { valid: true, errors: [] };

    const errors: string[] = [];

    scriptAnalysis.parameters.forEach((param) => {
      const value = parameterValues[param.name]?.trim();
      if (param.required && !value) {
        errors.push(`${param.name} is required`);
      }
    });

    return { valid: errors.length === 0, errors };
  };

  // Helper function to determine test result from script output
  const determineTestResult = (result: any): 'success' | 'failure' | undefined => {
    // First, check for explicit SCRIPT_SUCCESS in stdout (most reliable)
    if (result.stdout && result.stdout.includes('SCRIPT_SUCCESS:')) {
      const successMatch = result.stdout.match(/SCRIPT_SUCCESS:(true|false)/);
      if (successMatch) {
        return successMatch[1] === 'true' ? 'success' : 'failure';
      }
    }
    
    // If script executed successfully (exit_code 0) and has a report URL, 
    // it likely completed its test logic - determine from execution status
    if (result.exit_code === 0 && result.report_url) {
      // If script completed successfully and generated a report, 
      // but no explicit SCRIPT_SUCCESS marker, assume success
      return 'success';
    }
    
    // If script execution failed completely (exit_code != 0)
    if (result.exit_code !== undefined && result.exit_code !== 0) {
      return 'failure';
    }
    
    // If script completed but no clear test result indicator, leave undefined
    return undefined;
  };

  const handleExecuteScript = async () => {
    // Build complete device list: primary device + additional devices
    const allDevices: {hostName: string, deviceId: string}[] = [];
    
    // Add primary device if selected
    if (selectedHost && selectedDevice) {
      allDevices.push({ hostName: selectedHost, deviceId: selectedDevice });
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
      parameters: buildParameterString(hostDevice.hostName, hostDevice.deviceId), // Device-specific parameters
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
      showInfo(`Script "${selectedScript}" started on ${allDevices[0].hostName}:${allDevices[0].deviceId}`);
    } else {
      showInfo(`Script "${selectedScript}" started on ${allDevices.length} devices`);
    }

    try {
      // LIVE UPDATES: Define callback for real-time completion updates
      const onExecutionComplete = (executionId: string, result: any) => {
        console.log(`[@RunTests] Execution ${executionId} completed with success: ${result.success}`);
        console.log(`[@RunTests] Result details:`, {
          success: result.success,
          exit_code: result.exit_code,
          report_url: result.report_url,
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
          if (scriptCompleted) {
            const testResultText = testResult === 'success' ? ' - Test PASSED' : 
                                 testResult === 'failure' ? ' - Test FAILED' : '';
            showSuccess(`✅ ${device.hostName}:${device.deviceId} completed successfully${testResultText}`);
          } else {
            showError(`❌ ${device.hostName}:${device.deviceId} execution failed`);
          }
        }
      };

      // Execute with live callback - this waits for ALL to complete before returning
      const results = await executeMultipleScripts(executions, onExecutionComplete);

      // Final summary (all executions are now complete)
      const successCount = Object.values(results).filter((r: any) => r.success).length;
      
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

  const getStatusChip = (status: ExecutionRecord['status']) => {
    switch (status) {
      case 'running':
        return <Chip label="Running" color="warning" size="small" />;
      case 'completed':
        return <Chip label="Completed" color="success" size="small" />;
      case 'failed':
        return <Chip label="Failed" color="error" size="small" />;
      case 'aborted':
        return <Chip label="Aborted" color="error" size="small" />;
      default:
        return <Chip label="Unknown" color="default" size="small" />;
    }
  };

  const renderParameterInput = (param: ScriptParameter) => {
    const value = parameterValues[param.name] || '';

    // Special handling for userinterface_name with autocomplete
    if (param.name === 'userinterface_name') {
      const options = ['horizon_android_mobile', 'horizon_android_tv', 'perseus_360_web'];

      return (
        <Autocomplete
          key={param.name}
          options={options}
          value={value}
          onChange={(_event, newValue) => handleParameterChange(param.name, newValue || '')}
          onInputChange={(_event, newInputValue) =>
            handleParameterChange(param.name, newInputValue)
          }
          freeSolo
          size="small"
          renderInput={(params) => (
            <TextField
              {...params}
              label={`${param.name}${param.required ? ' *' : ''}`}
              size="small"
              fullWidth
              error={param.required && !value.trim()}
            />
          )}
        />
      );
    }

    // Special handling for blackscreen_area with preset options
    if (param.name === 'blackscreen_area') {
      const options = [
        '0,0,1920,720',      // Top 2/3 (default)
        '0,0,1920,540',      // Top 1/2
        '0,0,1920,810',      // Top 3/4
        '0,100,1920,620',    // Top 2/3 excluding top banner
        '0,0,1920,1080',     // Full screen
      ];

      return (
        <Autocomplete
          key={param.name}
          options={options}
          value={value}
          onChange={(_event, newValue) => handleParameterChange(param.name, newValue || '')}
          onInputChange={(_event, newInputValue) =>
            handleParameterChange(param.name, newInputValue)
          }
          freeSolo
          size="small"
          renderInput={(params) => (
            <TextField
              {...params}
              label={`${param.name}${param.required ? ' *' : ''}`}
              size="small"
              fullWidth
              error={param.required && !value.trim()}
              placeholder="x,y,width,height (e.g., 0,0,1920,720)"
              helperText="Blackscreen analysis area: x,y,width,height"
            />
          )}
        />
      );
    }

    // Default text field for other parameters
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

  // Filter to show required parameters and important optional ones, excluding host/device (auto-filled)
  const displayParameters = scriptAnalysis?.parameters.filter((param) => 
    (param.required && param.name !== 'host' && param.name !== 'device') ||
    param.name === 'blackscreen_area'  // Always show blackscreen_area for configuration
  ) || [];

  // These variables are no longer needed since we moved to grid layout

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
                                {script}
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
                              {device.device_id}
                            </MenuItem>
                          ))}
                        </Select>
                      </FormControl>
                    </Box>

                    {/* Parameters on the same row */}
                    {displayParameters.length > 0 &&
                      displayParameters.map((param) => (
                        <Box key={param.name} sx={{ minWidth: 200, flex: '1 1 200px' }}>
                          {renderParameterInput(param)}
                        </Box>
                      ))}
                  </Box>

                  {/* Second row: Add Device button aligned right - only show if more devices are available */}
                  {hasMoreDevicesAvailable() && (
                    <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 1 }}>
                      {selectedHost && selectedDevice && (
                        <Button
                          variant="outlined"
                          startIcon={<AddIcon />}
                          onClick={() => {
                            const exists = additionalDevices.some(hd => hd.hostName === selectedHost && hd.deviceId === selectedDevice);
                            if (!exists) {
                              setAdditionalDevices(prev => [...prev, { hostName: selectedHost, deviceId: selectedDevice }]);
                              // Reset current selection to allow adding different device
                              setSelectedHost('');
                              setSelectedDevice('');
                            }
                          }}
                          disabled={!selectedHost || !selectedDevice}
                          size="small"
                        >
                          Add Device
                        </Button>
                      )}
                    </Box>
                  )}

                  {/* Show additional devices as chips */}
                  {additionalDevices.length > 0 && (
                    <Box sx={{ mt: 2, mb: 1 }}>
                      <Typography variant="body2" sx={{ mb: 1 }}>
                        Additional devices ({additionalDevices.length}):
                      </Typography>
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                        {additionalDevices.map((hd, index) => (
                          <Chip
                            key={`${hd.hostName}:${hd.deviceId}`}
                            label={`${hd.hostName}:${hd.deviceId}`}
                            onDelete={() => {
                              setAdditionalDevices(prev => prev.filter((_, i) => i !== index));
                            }}
                            color="secondary"
                            variant="outlined"
                            size="small"
                          />
                        ))}
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
                              const deviceInfo = parts.length >= 4 ? `${parts[2]}:${parts[3]}` : id;
                              return (
                                <Chip
                                  key={id}
                                  label={deviceInfo}
                                  color="warning"
                                  size="small"
                                  icon={<CircularProgress size={16} />}
                                />
                              );
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
                        setShowWizard(false);
                        setSelectedHost('');
                        setSelectedDevice('');
                        setScriptAnalysis(null);
                        setParameterValues({});
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
                
                <DeviceStreamGrid devices={getAllSelectedDevices()} allHosts={allHosts} getDevicesFromHost={getDevicesFromHost} />
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
                          <TableCell>{execution.scriptName}</TableCell>
                          <TableCell>
                            {execution.hostName}:{execution.deviceId}
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
