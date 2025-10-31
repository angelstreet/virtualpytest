import React, { useState } from 'react';
import { Box, Typography, Chip, IconButton, CircularProgress, TextField, Collapse } from '@mui/material';
import { Handle, Position, NodeProps } from 'reactflow';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import CheckIcon from '@mui/icons-material/Check';
import CloseIcon from '@mui/icons-material/Close';
import EditIcon from '@mui/icons-material/Edit';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import LinkIcon from '@mui/icons-material/Link';
import { useTheme } from '../../../contexts/ThemeContext';
import { useToastContext } from '../../../contexts/ToastContext';
import { useDeviceData } from '../../../contexts/device/DeviceDataContext';
import { useTestCaseBuilder } from '../../../contexts/testcase/TestCaseBuilderContext';
import { useNavigationConfig } from '../../../contexts/navigation/NavigationConfigContext';
import { useAction } from '../../../hooks/actions/useAction';
import { buildServerUrl } from '../../../utils/buildUrlUtils';
import { BlockExecutionState } from '../../../hooks/testcase/useExecutionState';
import { executeNavigationAsync } from '../../../utils/navigationExecutionUtils';

export type OutputType = 'success' | 'failure' | 'true' | 'false' | 'complete' | 'break';

/**
 * Universal Block - Renders any command type with appropriate handles
 * Handles are generated based on command configuration
 * 
 * Now supports execution state visualization:
 * - executing: Blue glow + pulse animation
 * - success: Green border
 * - failure: Red border
 * - error: Orange border
 */
export const UniversalBlock: React.FC<NodeProps & { 
  executionState?: BlockExecutionState // Optional - for unified execution tracking
}> = ({ data, selected, dragging, type, id }) => {
  // Extract executionState from data (passed by TestCaseBuilder)
  const executionState = data.executionState as BlockExecutionState | undefined;
  const { actualMode } = useTheme();
  const { showSuccess, showError } = useToastContext();
  const { currentHost, currentDeviceId } = useDeviceData();
  const { updateBlock, userinterfaceName, unifiedExecution } = useTestCaseBuilder();
  const { actualTreeId } = useNavigationConfig();
  const { executeActions } = useAction(); // ✅ Use existing hook with async polling
  const [isExecuting, setIsExecuting] = useState(false);
  const [animateHandle, setAnimateHandle] = useState<'success' | 'failure' | null>(null);
  const [isEditingLabel, setIsEditingLabel] = useState(false);
  const [editedLabel, setEditedLabel] = useState(data.label || '');
  const [inputsExpanded, setInputsExpanded] = useState(false);
  const [outputsExpanded, setOutputsExpanded] = useState(false);
  const [draggedOutput, setDraggedOutput] = useState<{blockId: string, outputName: string, outputType: string} | null>(null);
  
  // Metadata fields to hide from parameter display
  const HIDDEN_METADATA_FIELDS = ['description', 'default', 'key', 'type', 'required', 'optional', 'placeholder', 'hidden', 'min', 'max'];
  
  // Get command configuration from toolbox config
  // Determine color based on type category
  let color: string;
  if (type === 'navigation') {
    color = '#8b5cf6'; // purple
  } else if (type === 'action') {
    color = '#f97316'; // orange
  } else if (type === 'verification') {
    color = '#3b82f6'; // blue
  } else if (['sleep', 'get_current_time', 'condition', 'set_variable', 'set_variable_io', 'set_metadata', 'loop', 'custom_code'].includes(type as string)) {
    color = '#6b7280'; // grey (standard blocks)
  } else {
    color = '#6b7280'; // default
  }
  
  const categoryLabel = data.label || data.command || type;
  
  // Determine outputs based on type or data
  const outputs: OutputType[] = data.outputs || (type === 'loop' ? ['complete', 'break'] : (type === 'condition' ? ['true', 'false'] : ['success', 'failure']));
  
  // Label editing handlers
  const handleLabelEdit = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsEditingLabel(true);
    setEditedLabel(data.label || '');
  };
  
  const handleLabelSave = () => {
    // Validate label: max 20 chars, only alphanumeric, -, _, and :
    const sanitizedLabel = editedLabel
      .replace(/[^a-zA-Z0-9\-_:]/g, '') // Remove invalid chars (keep : - _)
      .substring(0, 20); // Max 20 chars
    
    if (sanitizedLabel.length === 0) {
      showError('Label cannot be empty');
      return;
    }
    
    // Update block data with new label
    updateBlock(id as string, { label: sanitizedLabel });
    setEditedLabel(sanitizedLabel);
    setIsEditingLabel(false);
  };
  
  const handleLabelCancel = () => {
    setIsEditingLabel(false);
    setEditedLabel(data.label || '');
  };
  
  const handleLabelKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleLabelSave();
    } else if (e.key === 'Escape') {
      handleLabelCancel();
    }
  };
  
  // Execute handler for action/verification/navigation blocks
  const handleExecute = async (e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent block selection
    
    // Validate
    if (!currentHost) {
      showError('No host selected');
      return;
    }
    
    // Determine block type
    const isAction = type === 'action' || ['press_key', 'press_sequence', 'tap', 'swipe', 'type_text'].includes(type as string);
    const isVerification = type === 'verification' || ['verify_image', 'verify_ocr', 'verify_audio', 'verify_element'].includes(type as string);
    const isNavigation = type === 'navigation';
    const isStandardBlock = ['sleep', 'get_current_time', 'condition', 'set_variable', 'loop', 'custom_code', 'common_operation', 'evaluate_condition', 'set_metadata'].includes(type as string);
    
    // Validate based on type
    if (isNavigation) {
      if (!data.target_node_label) {
        showError('No target node configured');
        return;
      }
    } else if (!data.command) {
      showError('No command configured');
      return;
    }
    
    if (!isAction && !isVerification && !isNavigation && !isStandardBlock) {
      showError('Unknown block type');
      return;
    }
    
    setIsExecuting(true);
    
    // 🆕 START: Unified execution for single block
    unifiedExecution.startExecution('single_block', [id]);
    unifiedExecution.startBlockExecution(id);
    
    const startTime = Date.now();
    
    try {
      let result: any; // Result from either navigation or action execution
      
      if (isNavigation) {
        // ✅ REUSE: Execute navigation using shared utility with async polling
        const tree_id = actualTreeId;
        const interfaceName = data.userinterface_name || userinterfaceName;
        
        if (!tree_id) {
          throw new Error(`No navigation tree loaded. Please select a userinterface first.`);
        }
        
        if (!interfaceName) {
          throw new Error(`No userinterface selected. Please select a userinterface first.`);
        }
        
        // Use shared navigation execution utility (same as useNode)
        const navResult = await executeNavigationAsync({
          treeId: tree_id,
          targetNodeLabel: data.target_node_label,
          hostName: currentHost.host_name,
          deviceId: currentDeviceId || 'device1',
          userinterfaceName: interfaceName,
          onProgress: (msg: string) => {
            console.log('[@UniversalBlock] Navigation progress:', msg);
          }
        });
        
        // Convert to response format expected by result handling below
        result = navResult;
      } else if (isStandardBlock) {
        // ✅ Execute standard block using async polling (same as actions/verifications)
        // Filter out null/undefined values from params
        const cleanParams: Record<string, any> = {};
        if (data.params) {
          Object.entries(data.params).forEach(([key, value]) => {
            if (value !== null && value !== undefined) {
              cleanParams[key] = value;
            }
          });
        }
        
        // Build action in EdgeAction format (standard blocks use same executor)
        const block = {
          command: data.command,
          params: cleanParams,
        };
        
        // Standard blocks should use async pattern too (e.g., sleep(60) would timeout with sync)
        // Start async execution (team_id is automatically added by buildServerUrl)
        const executionUrl = buildServerUrl(`/server/builder/execute`);
        
        const startResult = await fetch(executionUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            command: block.command,
            params: block.params,
            host_name: currentHost.host_name,
            device_id: currentDeviceId || 'device1',
          }),
        });

        const startResponse = await startResult.json();

        if (!startResponse.success) {
          throw new Error(startResponse.error || 'Failed to start block execution');
        }

        const executionId = startResponse.execution_id;
        console.log('[@UniversalBlock] ✅ Async block execution started:', executionId);

        // Poll for completion
        const statusUrl = buildServerUrl(
          `/server/builder/execution/${executionId}/status?host_name=${currentHost.host_name}&device_id=${currentDeviceId || 'device1'}`
        );

        let attempts = 0;
        const maxAttempts = 120; // 120 * 1000ms = 120 seconds (for long sleep, etc.)

        while (attempts < maxAttempts) {
          await new Promise((resolve) => setTimeout(resolve, 1000)); // Poll every 1s
          attempts++;

          const statusResult = await fetch(statusUrl);
          const statusResponse = await statusResult.json();

          if (!statusResponse.success) {
            throw new Error(statusResponse.error || 'Failed to get execution status');
          }

          if (statusResponse.status === 'completed') {
            result = statusResponse.result;
            console.log('[@UniversalBlock] Block execution completed:', result);
            break;
          } else if (statusResponse.status === 'error') {
            throw new Error(statusResponse.error || 'Block execution failed');
          }
        }

        if (attempts >= maxAttempts) {
          throw new Error('Block execution timeout - took too long');
        }
      } else {
        // ✅ Execute action or verification using existing useAction hook (async polling built-in)
        // Filter out null/undefined values from params
        const cleanParams: Record<string, any> = {};
        if (data.params) {
          Object.entries(data.params).forEach(([key, value]) => {
            if (value !== null && value !== undefined) {
              cleanParams[key] = value;
            }
          });
        }
        
        // Build action in EdgeAction format for useAction hook
        const action = {
          command: data.command,
          name: data.label || data.command, // EdgeAction requires name field
          params: cleanParams,
          action_type: data.action_type,
          verification_type: data.verification_type,
          threshold: data.threshold,
          reference: data.reference,
        };
        
        // Use existing hook which already handles async + polling
        const actionResult = await executeActions([action], [], []);
        
        // Convert to expected result format
        // ✅ logs and output_data are now passed through directly from backend
        result = {
          success: actionResult.success,
          message: actionResult.message,
          error: actionResult.error,
          output_data: actionResult.output_data || actionResult.results?.[0]?.output_data || {},
          logs: actionResult.logs || '', // ✅ Now available at top level from useAction
        };
        
        console.log('[@UniversalBlock] Action result with logs:', { 
          hasLogs: Boolean(actionResult.logs), 
          logsLength: actionResult.logs?.length || 0,
          logs: actionResult.logs 
        });
      }
      
      const duration = Date.now() - startTime;
      const durationText = `${(duration / 1000).toFixed(2)}s`;
      const commandLabel = isNavigation ? `Navigate to ${data.target_node_label}` : data.command;
      
      if (result.success) {
        // 🆕 Complete block execution with success
        unifiedExecution.completeBlockExecution(id, true, undefined, result);
        
        setAnimateHandle('success');
        
        // Show different message if already at destination
        if (isNavigation && result.already_at_target) {
          showSuccess(`ℹ️ Already at ${data.target_node_label} - ${durationText}`);
        } else {
          // Build success message with output data if available
          let successMessage = `✓ ${commandLabel} - ${durationText}`;
          
          // If verification has output_data (like getMenuInfo), show key count
          if (result.output_data && typeof result.output_data === 'object') {
            const outputData = result.output_data;
            
            // Check for parsed_data (getMenuInfo, etc.)
            if (outputData.parsed_data && typeof outputData.parsed_data === 'object') {
              const parsedCount = Object.keys(outputData.parsed_data).length;
              successMessage += `\n📋 Extracted ${parsedCount} fields`;
              
              // Show first 3 key-value pairs as preview
              const entries = Object.entries(outputData.parsed_data).slice(0, 3);
              if (entries.length > 0) {
                successMessage += '\n' + entries.map(([k, v]) => {
                  const displayValue = typeof v === 'string' && v.length > 30 
                    ? `${v.substring(0, 30)}...` 
                    : String(v);
                  return `  • ${k}: ${displayValue}`;
                }).join('\n');
                
                if (Object.keys(outputData.parsed_data).length > 3) {
                  successMessage += `\n  ... +${Object.keys(outputData.parsed_data).length - 3} more`;
                }
              }
            }
            
            // Log full output to console for debugging
            console.log('[@UniversalBlock] Verification output_data:', outputData);
          }
          
          showSuccess(successMessage);
        }
        
        // Clear animation after 2 seconds
        setTimeout(() => setAnimateHandle(null), 2000);
        
        // 🆕 Complete overall execution with success (reached SUCCESS terminal)
        unifiedExecution.completeExecution({
          success: true,
          result_type: 'success',
          execution_time_ms: duration,
          step_count: 1,
        });
      } else {
        // 🆕 Complete block execution with failure
        unifiedExecution.completeBlockExecution(id, false, result.error || 'Action failed', result);
        
        setAnimateHandle('failure');
        showError(`✗ ${commandLabel} - ${durationText}\n${result.error || 'Execution failed'}`);
        // Clear animation after 2 seconds
        setTimeout(() => setAnimateHandle(null), 2000);
        
        // 🆕 Complete overall execution with failure (reached FAILURE terminal)
        unifiedExecution.completeExecution({
          success: false,
          result_type: 'failure',
          execution_time_ms: duration,
          error: result.error || 'Action failed',
          step_count: 1,
        });
      }
    } catch (error) {
      const duration = Date.now() - startTime;
      const durationText = `${(duration / 1000).toFixed(2)}s`;
      const commandLabel = isNavigation ? `Navigate to ${data.target_node_label}` : data.command;
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      
      // 🆕 Complete block execution with error
      unifiedExecution.completeBlockExecution(id, false, errorMessage, undefined);
      
      setAnimateHandle('failure');
      showError(`✗ ${commandLabel} - ${durationText}\nError: ${errorMessage}`);
      // Clear animation after 2 seconds
      setTimeout(() => setAnimateHandle(null), 2000);
      
      // 🆕 Complete overall execution with error
      unifiedExecution.completeExecution({
        success: false,
        result_type: 'error',
        execution_time_ms: duration,
        error: errorMessage,
        step_count: 1,
      });
    } finally {
      setIsExecuting(false);
    }
  };
  
  // Render I/O handles for data flow - REMOVED (now using collapsible sections inside block)
  // Old IN/OUT handles above block are no longer needed
  
  // Determine header and content based on block type
  let headerLabel = categoryLabel;
  let contentLabel = 'Click to configure';
  
  // Check if block is configured
  const isConfigured = Boolean(
    data.command || 
    data.target_node_label || 
    data.iterations ||
    data.block_label || // For any blocks with auto-generated labels
    Object.keys(data).length > 1 // More than just position data
  );
  
  // Determine if this block can be executed
  const canExecute = Boolean(
    // Actions and verifications
    (type === 'action' || type === 'verification' || 
     ['press_key', 'press_sequence', 'tap', 'swipe', 'type_text', 
      'verify_image', 'verify_ocr', 'verify_audio', 'verify_element'].includes(type as string)) &&
    data.command
  ) || Boolean(
    // Navigation blocks
    type === 'navigation' && data.target_node_label
  ) || Boolean(
    // Standard blocks
    ['sleep', 'get_current_time', 'condition', 'set_variable', 'loop', 'custom_code', 'common_operation', 'evaluate_condition', 'set_metadata'].includes(type as string) &&
    data.command
  );
  
  if (isConfigured) {
    // For navigation blocks: show block_label:target_node_label in header, target_node_label in content
    if (type === 'navigation' && data.target_node_label) {
      // If has custom block_label (e.g., "navigation_1"), show "navigation_1:home"
      // Otherwise just show "navigation:home"
      if (data.block_label) {
        headerLabel = `${data.block_label}`;
      } else {
        headerLabel = `navigation:${data.target_node_label}`;
      }
      contentLabel = data.target_node_label;
    }
    // For standard blocks: header = "STANDARD", content = command (e.g., "Sleep")
    else if (['sleep', 'get_current_time', 'condition', 'set_variable', 'loop'].includes(type as string)) {
      headerLabel = 'STANDARD';
      contentLabel = categoryLabel;
    }
    // For generic action blocks from toolboxBuilder: header = "ACTION", content = command label
    else if (type === 'action' || ['press_key', 'press_sequence', 'tap', 'swipe', 'type_text'].includes(type as string)) {
      headerLabel = 'ACTION';
      contentLabel = categoryLabel;
    }
    // For generic verification blocks from toolboxBuilder: header = "VERIFICATION", content = command label
    else if (type === 'verification' || ['verify_image', 'verify_ocr', 'verify_audio', 'verify_element'].includes(type as string)) {
      headerLabel = 'VERIFICATION';
      contentLabel = categoryLabel;
    }
    // Fallback to command or display label
    else {
      contentLabel = data.command || data.label || categoryLabel;
    }
  }
  
  // Render output handles based on configured outputs
  const renderOutputHandles = () => {
    if (outputs.length === 0) {
      return null; // No output handles (shouldn't happen but safe)
    }
    
    // Check if this handle was the execution result
    const isHandleActive = (output: OutputType) => {
      if (!executionState || !['success', 'failure', 'error'].includes(executionState.status)) {
        return false;
      }
      // Map execution status to handle output type
      if (executionState.status === 'success' && (output === 'success' || output === 'true' || output === 'complete')) {
        return true;
      }
      if ((executionState.status === 'failure' || executionState.status === 'error') && (output === 'failure' || output === 'false')) {
        return true;
      }
      return false;
    };
    
    if (outputs.length === 1) {
      // Single output - centered at bottom, rectangle
      const output = outputs[0];
      const handleColor = getHandleColor(output);
      const isAnimating = animateHandle === output;
      const isActive = isHandleActive(output);
      
      let content;
      if (output === 'success' || output === 'true' || output === 'complete') {
        content = <CheckIcon sx={{ fontSize: isActive ? 28 : 20, fontWeight: isActive ? 900 : 'normal' }} />;
      } else if (output === 'failure' || output === 'false') {
        content = <CloseIcon sx={{ fontSize: isActive ? 28 : 20, fontWeight: isActive ? 900 : 'normal' }} />;
      } else if (output === 'break') {
        content = <Typography fontSize={10} fontWeight="bold">BREAK</Typography>;
      } else {
        content = null;
      }
      
      return (
        <>
          <Handle
            type="source"
            position={Position.Bottom}
            id={output}
            style={{
              background: handleColor,
              width: isActive ? 90 : 80,
              height: isActive ? 38 : 32,
              borderRadius: 4,
              border: isActive ? '4px solid white' : '2px solid white',
              bottom: isActive ? -40 : -36,
              left: '50%',
              transform: 'translateX(-50%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'white',
              fontWeight: 'bold',
              fontSize: 12,
              cursor: 'pointer',
              boxShadow: isActive ? `0 0 20px ${handleColor}` : 'none',
              transition: 'all 0.3s ease',
            }}
          >
            <Box
              sx={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                pointerEvents: 'none',
                animation: isAnimating ? 'pulse 0.5s ease-in-out 3' : 'none',
                '@keyframes pulse': {
                  '0%, 100%': { transform: 'scale(1)' },
                  '50%': { transform: 'scale(1.2)' },
                },
              }}
            >
              {content}
            </Box>
          </Handle>
        </>
      );
    }
    
    // Multiple outputs - positioned left and right, rectangles with icons
    return outputs.map((output, idx) => {
      const handleColor = getHandleColor(output);
      const leftPosition = idx === 0 ? '25%' : '75%';
      const isAnimating = animateHandle === output;
      const isActive = isHandleActive(output);
      
      // Determine icon/text based on output type
      let content;
      if (output === 'success' || output === 'true' || output === 'complete') {
        content = <CheckIcon sx={{ fontSize: isActive ? 26 : 18, fontWeight: isActive ? 900 : 'normal' }} />;
      } else if (output === 'failure' || output === 'false') {
        content = <CloseIcon sx={{ fontSize: isActive ? 26 : 18, fontWeight: isActive ? 900 : 'normal' }} />;
      } else if (output === 'break') {
        content = <Typography fontSize={10} fontWeight="bold">BREAK</Typography>;
      } else {
        content = null;
      }
      
      return (
        <Handle
          key={output}
          type="source"
          position={Position.Bottom}
          id={output}
          style={{
            left: leftPosition,
            background: handleColor,
            width: isActive ? 80 : 70,
            height: isActive ? 34 : 28,
            borderRadius: 4,
            border: isActive ? '4px solid white' : '2px solid white',
            bottom: isActive ? -36 : -32,
            transform: 'translateX(-50%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'white',
            fontWeight: 'bold',
            fontSize: 11,
            cursor: 'pointer',
            boxShadow: isActive ? `0 0 20px ${handleColor}` : 'none',
            transition: 'all 0.3s ease',
          }}
        >
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              pointerEvents: 'none',
              animation: isAnimating ? 'pulse 0.5s ease-in-out 3' : 'none',
              '@keyframes pulse': {
                '0%, 100%': { transform: 'scale(1)' },
                '50%': { transform: 'scale(1.2)' },
              },
            }}
          >
            {content}
          </Box>
        </Handle>
      );
    });
  };
  
  // Get execution state styling
  const getExecutionStyling = () => {
    // Priority: executionState > isExecuting (local)
    const state = executionState || (isExecuting ? { status: 'executing' as const } : null);
    
    if (!state) return {};
    
    switch (state.status) {
      case 'executing':
        return {
          border: '3px solid #3b82f6',
          boxShadow: '0 0 20px rgba(59, 130, 246, 0.6), 0 0 40px rgba(59, 130, 246, 0.3)',
          animation: 'executePulse 1.5s ease-in-out infinite',
          '@keyframes executePulse': {
            '0%, 100%': { 
              boxShadow: '0 0 20px rgba(59, 130, 246, 0.6), 0 0 40px rgba(59, 130, 246, 0.3)',
            },
            '50%': { 
              boxShadow: '0 0 30px rgba(59, 130, 246, 0.8), 0 0 60px rgba(59, 130, 246, 0.4)',
            },
          },
        };
      case 'success':
        return {
          border: '4px solid #10b981',
          backgroundColor: actualMode === 'dark' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(16, 185, 129, 0.05)',
          boxShadow: '0 0 15px rgba(16, 185, 129, 0.5)',
        };
      case 'failure':
        return {
          border: '4px solid #ef4444',
          backgroundColor: actualMode === 'dark' ? 'rgba(239, 68, 68, 0.1)' : 'rgba(239, 68, 68, 0.05)',
          boxShadow: '0 0 15px rgba(239, 68, 68, 0.5)',
        };
      case 'error':
        return {
          border: '2px solid #f59e0b',
          backgroundColor: actualMode === 'dark' ? 'rgba(245, 158, 11, 0.1)' : 'rgba(245, 158, 11, 0.05)',
          boxShadow: '0 0 10px rgba(245, 158, 11, 0.3)',
        };
      case 'pending':
        return {
          opacity: 0.6,
          filter: 'grayscale(0.3)',
        };
      default:
        return {};
    }
  };
  
  return (
    <Box
      sx={{
        minWidth: 240,
        border: selected ? '3px solid #fbbf24' : `2px solid ${color}`,
        ...getExecutionStyling(), // Apply execution styling
        borderRadius: 2,
        background: actualMode === 'dark' ? '#1f2937' : '#ffffff',
        boxShadow: 2,
        cursor: 'pointer',
        opacity: dragging ? 0.5 : (isExecuting ? 0.7 : 1),
        transition: 'all 0.3s ease',
        pointerEvents: isExecuting ? 'none' : 'auto', // Disable interaction during execution
        position: 'relative',
        '&:hover': {
          boxShadow: isExecuting ? 2 : 4,
        },
      }}
    >
      {/* Duration Badge - Above Block */}
      {executionState?.duration && ['success', 'failure', 'error'].includes(executionState.status) && (
        <Box
          sx={{
            position: 'absolute',
            top: -28,
            right: 0,
            transform: 'translateX(-50%)',
            zIndex: 10,
            backgroundColor: 
              executionState.status === 'success' ? '#10b981' :
              executionState.status === 'failure' ? '#ef4444' : '#f59e0b',
            color: 'white',
            borderRadius: 1,
            px: 1,
            py: 0.5,
            fontSize: 11,
            fontWeight: 'bold',
            fontFamily: 'monospace',
            boxShadow: '0 2px 8px rgba(0,0,0,0.2)',
          }}
        >
          {(executionState.duration / 1000).toFixed(2)}s
        </Box>
      )}
      
      {/* Header */}
      <Box
        sx={{
          background: color,
          p: 1,
          display: 'flex',
          alignItems: 'center',
          gap: 1,
          justifyContent: 'space-between',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flex: 1 }}>
          {isEditingLabel ? (
            <>
              <TextField
                value={editedLabel}
                onChange={(e) => setEditedLabel(e.target.value)}
                onKeyDown={handleLabelKeyDown}
                onBlur={handleLabelSave}
                autoFocus
                size="small"
                inputProps={{
                  maxLength: 20,
                  style: { color: 'white', fontSize: 13, fontWeight: 'bold', padding: '2px 4px' }
                }}
                sx={{
                  '& .MuiOutlinedInput-root': {
                    '& fieldset': {
                      borderColor: 'rgba(255, 255, 255, 0.5)',
                    },
                    '&:hover fieldset': {
                      borderColor: 'rgba(255, 255, 255, 0.8)',
                    },
                    '&.Mui-focused fieldset': {
                      borderColor: 'white',
                    },
                  },
                  flex: 1,
                  maxWidth: '150px',
                }}
              />
              <IconButton
                size="small"
                onClick={(e) => {
                  e.stopPropagation();
                  handleLabelCancel();
                }}
                sx={{
                  color: 'white',
                  padding: '2px',
                  '&:hover': {
                    backgroundColor: 'rgba(255, 255, 255, 0.2)',
                  },
                }}
              >
                <CloseIcon sx={{ fontSize: 14 }} />
              </IconButton>
            </>
          ) : (
            <>
              <Typography color="white" fontWeight="bold" fontSize={13}>
                {data.label || headerLabel}
              </Typography>
              <IconButton
                size="small"
                onClick={handleLabelEdit}
                sx={{
                  color: 'white',
                  padding: '2px',
                  '&:hover': {
                    backgroundColor: 'rgba(255, 255, 255, 0.2)',
                  },
                }}
              >
                <EditIcon sx={{ fontSize: 14 }} />
              </IconButton>
            </>
          )}
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          {canExecute && (
            <IconButton
              size="small"
              onClick={handleExecute}
              disabled={isExecuting}
              sx={{
                color: 'white',
                padding: '4px',
                '&:hover': {
                  backgroundColor: 'rgba(255, 255, 255, 0.2)',
                },
                '&.Mui-disabled': {
                  color: 'rgba(255, 255, 255, 0.5)',
                },
              }}
            >
              {isExecuting ? <CircularProgress size={16} sx={{ color: 'white' }} /> : <PlayArrowIcon fontSize="small" />}
            </IconButton>
          )}
        </Box>
      </Box>
      
      {/* Content */}
      <Box sx={{ p: 1.5 }}>
        {isConfigured ? (
          <>
            <Typography fontSize={14} fontWeight="medium" mb={1}>
              {contentLabel}
            </Typography>
            
            {/* Collapsible INPUTS section */}
            {data.params && Object.keys(data.params).length > 0 && (() => {
              // Filter out metadata fields
              const displayParams = Object.entries(data.params).filter(([key]) => !HIDDEN_METADATA_FIELDS.includes(key));
              if (displayParams.length === 0) return null;
              
              return (
                <Box sx={{ mb: 1 }}>
                  <Box
                    onClick={() => setInputsExpanded(!inputsExpanded)}
                    sx={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      gap: 0.5,
                      cursor: 'pointer',
                      py: 0.5,
                      px: 1,
                      bgcolor: actualMode === 'dark' ? 'rgba(139, 92, 246, 0.15)' : 'rgba(139, 92, 246, 0.1)',
                      borderRadius: 1,
                      border: '1px solid',
                      borderColor: actualMode === 'dark' ? 'rgba(139, 92, 246, 0.3)' : 'rgba(139, 92, 246, 0.2)',
                      '&:hover': {
                        bgcolor: actualMode === 'dark' ? 'rgba(139, 92, 246, 0.2)' : 'rgba(139, 92, 246, 0.15)',
                      },
                    }}
                  >
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, flex: 1, minWidth: 0 }}>
                      <Typography fontSize={11} fontWeight="bold" color="#8b5cf6" sx={{ flexShrink: 0 }}>
                        📋 INPUTS ({displayParams.length})
                      </Typography>
                      {/* Preview: Show first 1-3 inputs inline when collapsed */}
                      {!inputsExpanded && (
                        <Box sx={{ 
                          display: 'flex', 
                          alignItems: 'center', 
                          gap: 0.5, 
                          overflow: 'hidden',
                          flex: 1,
                          minWidth: 0,
                        }}>
                          {displayParams.slice(0, 3).map(([key]) => {
                            const link = data.paramLinks?.[key];
                            const isLinked = Boolean(link);
                            
                            return (
                              <Chip
                                key={key}
                                label={key}
                                size="small"
                                icon={isLinked ? <LinkIcon sx={{ fontSize: 10, color: '#10b981' }} /> : undefined}
                                sx={{ 
                                  fontSize: 9, 
                                  height: 18,
                                  maxWidth: '80px',
                                  bgcolor: isLinked 
                                    ? (actualMode === 'dark' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(16, 185, 129, 0.1)')
                                    : (actualMode === 'dark' ? 'rgba(139, 92, 246, 0.1)' : 'rgba(139, 92, 246, 0.08)'),
                                  borderColor: isLinked ? '#10b981' : '#8b5cf6',
                                  '& .MuiChip-label': {
                                    px: 0.5,
                                    overflow: 'hidden',
                                    textOverflow: 'ellipsis',
                                    whiteSpace: 'nowrap',
                                  }
                                }}
                                variant="outlined"
                              />
                            );
                          })}
                          {displayParams.length > 3 && (
                            <Typography fontSize={9} color="#8b5cf6" sx={{ flexShrink: 0 }}>
                              +{displayParams.length - 3}
                            </Typography>
                          )}
                        </Box>
                      )}
                    </Box>
                    {inputsExpanded ? <ExpandLessIcon sx={{ fontSize: 16, color: '#8b5cf6', flexShrink: 0 }} /> : <ExpandMoreIcon sx={{ fontSize: 16, color: '#8b5cf6', flexShrink: 0 }} />}
                  </Box>
                  <Collapse in={inputsExpanded}>
                    <Box sx={{ mt: 0.5, display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                      {displayParams.map(([key, value]) => {
                        // Check if this param is linked to an output
                        const link = data.paramLinks?.[key];
                        const isLinked = Boolean(link);
                        
                        return (
                          <Box
                            key={key}
                            onDragOver={(e) => {
                              e.preventDefault();
                              e.stopPropagation();
                            }}
                            onDrop={(e) => {
                              e.preventDefault();
                                e.stopPropagation();
                              if (draggedOutput) {
                                // Create link: this param <- draggedOutput
                                updateBlock(id as string, {
                                  paramLinks: {
                                    ...data.paramLinks,
                                    [key]: {
                                      sourceBlockId: draggedOutput.blockId,
                                      sourceOutputName: draggedOutput.outputName,
                                      sourceOutputType: draggedOutput.outputType
                                    }
                                  }
                                });
                                setDraggedOutput(null);
                                showSuccess(`Linked ${key} ← ${draggedOutput.outputName}`);
                              }
                            }}
                            sx={{ position: 'relative' }}
                          >
                            <Chip
                              label={isLinked 
                                ? `${key} ← ${link.sourceOutputName}` 
                                : (() => {
                                    // Extract actual value from object structure
                                    let actualValue = value;
                                    if (typeof value === 'object' && value !== null) {
                                      // If object has a 'value' property, use that
                                      actualValue = (value as any).value !== undefined ? (value as any).value : value;
                                      
                                      // If still an object, filter out metadata fields
                                      if (typeof actualValue === 'object' && actualValue !== null) {
                                        const filtered: Record<string, any> = {};
                                        Object.entries(actualValue).forEach(([k, v]) => {
                                          if (!HIDDEN_METADATA_FIELDS.includes(k)) {
                                            filtered[k] = v;
                                          }
                                        });
                                        // If filtered object is empty or only has metadata, show the value property
                                        if (Object.keys(filtered).length === 0 && (value as any).value !== undefined) {
                                          actualValue = (value as any).value;
                                        } else {
                                          actualValue = filtered;
                                        }
                                      }
                                    }
                                    const displayValue = typeof actualValue === 'object' 
                                      ? JSON.stringify(actualValue) 
                                      : String(actualValue);
                                    return `${key}: ${displayValue.substring(0, 30)}${displayValue.length > 30 ? '...' : ''}`;
                                  })()
                              }
                              size="small"
                              icon={isLinked ? <LinkIcon sx={{ fontSize: 12, color: '#10b981' }} /> : undefined}
                              onDelete={isLinked ? () => {
                                // Remove link
                                const newLinks = { ...data.paramLinks };
                                delete newLinks[key];
                                updateBlock(id as string, { paramLinks: newLinks });
                                showSuccess(`Unlinked ${key}`);
                              } : undefined}
                              sx={{ 
                                fontSize: 10, 
                                height: 24,
                                bgcolor: isLinked 
                                  ? (actualMode === 'dark' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(16, 185, 129, 0.1)')
                                  : (actualMode === 'dark' ? 'rgba(139, 92, 246, 0.1)' : 'rgba(139, 92, 246, 0.08)'),
                                borderColor: isLinked ? '#10b981' : '#8b5cf6',
                                cursor: 'pointer',
                                '&:hover': {
                                  bgcolor: isLinked
                                    ? (actualMode === 'dark' ? 'rgba(16, 185, 129, 0.25)' : 'rgba(16, 185, 129, 0.2)')
                                    : (actualMode === 'dark' ? 'rgba(139, 92, 246, 0.2)' : 'rgba(139, 92, 246, 0.15)'),
                                }
                              }}
                              variant="outlined"
                            />
                          </Box>
                        );
                      })}
                    </Box>
                  </Collapse>
                </Box>
              );
            })()}
            
            {/* Collapsible OUTPUTS section */}
            {data.blockOutputs && data.blockOutputs.length > 0 && (
              <Box>
                <Box
                  onClick={() => setOutputsExpanded(!outputsExpanded)}
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    cursor: 'pointer',
                    py: 0.5,
                    px: 1,
                    bgcolor: actualMode === 'dark' ? 'rgba(249, 115, 22, 0.15)' : 'rgba(249, 115, 22, 0.1)',
                    borderRadius: 1,
                    border: '1px solid',
                    borderColor: actualMode === 'dark' ? 'rgba(249, 115, 22, 0.3)' : 'rgba(249, 115, 22, 0.2)',
                    '&:hover': {
                      bgcolor: actualMode === 'dark' ? 'rgba(249, 115, 22, 0.2)' : 'rgba(249, 115, 22, 0.15)',
                    },
                  }}
                >
                  <Typography fontSize={11} fontWeight="bold" color="#f97316">
                    OUTPUTS ({data.blockOutputs.length})
                  </Typography>
                  {outputsExpanded ? <ExpandLessIcon sx={{ fontSize: 16, color: '#f97316' }} /> : <ExpandMoreIcon sx={{ fontSize: 16, color: '#f97316' }} />}
                </Box>
                <Collapse in={outputsExpanded}>
                  <Box sx={{ mt: 0.5, display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                    {data.blockOutputs.map((output: any, idx: number) => (
                      <Chip
                        key={output.name || idx}
                        label={`${output.name}: ${output.type}`}
                        size="small"
                        draggable
                        onDragStart={(e) => {
                          e.stopPropagation();
                          const dragData = {
                            blockId: id as string,
                            outputName: output.name,
                            outputType: output.type
                          };
                          setDraggedOutput(dragData);
                          // Set data for drop handlers
                          e.dataTransfer.setData('application/json', JSON.stringify(dragData));
                          e.dataTransfer.effectAllowed = 'link';
                        }}
                        onDragEnd={() => {
                          setDraggedOutput(null);
                        }}
                        sx={{ 
                          fontSize: 10, 
                          height: 24,
                          bgcolor: actualMode === 'dark' ? 'rgba(249, 115, 22, 0.1)' : 'rgba(249, 115, 22, 0.08)',
                          borderColor: '#f97316',
                          cursor: 'grab',
                          '&:hover': {
                            bgcolor: actualMode === 'dark' ? 'rgba(249, 115, 22, 0.2)' : 'rgba(249, 115, 22, 0.15)',
                          },
                          '&:active': {
                            cursor: 'grabbing',
                          }
                        }}
                        variant="outlined"
                      />
                    ))}
                  </Box>
                </Collapse>
              </Box>
            )}
            
            {data.iterations && data.iterations > 1 && (
              <Typography fontSize={11} color="text.secondary" mt={0.5}>
                × {data.iterations} iterations
              </Typography>
            )}
            {data.iterator && data.iterator > 1 && (
              <Typography fontSize={11} color="text.secondary" mt={0.5}>
                × {data.iterator}
              </Typography>
            )}
          </>
        ) : (
          <Typography fontSize={12} color="text.secondary">
            Click to configure
          </Typography>
        )}
      </Box>
      
      {/* Transparent larger handle for better grabbing */}
      <Handle
        type="target"
        position={Position.Top}
        id="input-hitarea"
        style={{
          background: 'transparent',
          width: 32,
          height: 32,
          borderRadius: '50%',
          border: 'none',
          top: -16,
          pointerEvents: 'all',
        }}
      />
      
      {/* Visible input handle at top - circle */}
      <Handle
        type="target"
        position={Position.Top}
        id="input"
        style={{
          background: color,
          width: 14,
          height: 14,
          borderRadius: '50%',
          border: '2px solid white',
          top: -8,
          pointerEvents: 'none',
        }}
      />
      
      {/* Output handles at bottom - rectangles with icons */}
      {renderOutputHandles()}
    </Box>
  );
};

/**
 * Get handle color based on output type
 */
const getHandleColor = (outputType: OutputType): string => {
  switch (outputType) {
    case 'success':
      return '#10b981'; // green
    case 'failure':
      return '#ef4444'; // red
    case 'true':
      return '#10b981'; // green
    case 'false':
      return '#ef4444'; // red
    case 'complete':
      return '#10b981'; // green
    case 'break':
      return '#eab308'; // yellow - distinguishable from orange actions
    default:
      return '#6b7280'; // gray
  }
};

