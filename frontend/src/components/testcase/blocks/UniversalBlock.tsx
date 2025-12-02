import React, { useState } from 'react';
import { Box, Typography, IconButton, CircularProgress, TextField } from '@mui/material';
import { Handle, Position, NodeProps } from 'reactflow';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import CheckIcon from '@mui/icons-material/Check';
import CloseIcon from '@mui/icons-material/Close';
import EditIcon from '@mui/icons-material/Edit';
import { useTheme } from '../../../contexts/ThemeContext';
import { useToastContext } from '../../../contexts/ToastContext';
import { useDeviceData } from '../../../contexts/device/DeviceDataContext';
import { useTestCaseBuilder } from '../../../contexts/testcase/TestCaseBuilderContext';
import { useNavigationConfig } from '../../../contexts/navigation/NavigationConfigContext';
import { useAction } from '../../../hooks/actions/useAction';
import { buildServerUrl } from '../../../utils/buildUrlUtils';
import { BlockExecutionState } from '../../../hooks/testcase/useExecutionState';
import { executeNavigationAsync } from '../../../utils/navigationExecutionUtils';
import { resolveParamsVariables } from '../../../utils/variableResolutionUtils';
import { InputDisplay } from './InputDisplay';
import { OutputDisplay } from './OutputDisplay';
import { ActionConfigDialog } from '../dialogs/ActionConfigDialog';

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
  const { updateBlock, userinterfaceName, unifiedExecution, scriptInputs, scriptVariables, scriptOutputs, scriptMetadata, nodes } = useTestCaseBuilder();
  const { actualTreeId } = useNavigationConfig();
  const { executeActions } = useAction(); // ✅ Use existing hook with async polling
  
  const [isExecuting, setIsExecuting] = useState(false);
  const [animateHandle, setAnimateHandle] = useState<'success' | 'failure' | null>(null);
  const [isEditingLabel, setIsEditingLabel] = useState(false);
  const [editedLabel, setEditedLabel] = useState(data.label || '');
  const [isConfigDialogOpen, setIsConfigDialogOpen] = useState(false);
  
  // ✅ NEW: Calculate what this block's outputs are linked to
  const calculateLinkedTo = (): Record<string, Array<{ targetType: 'variable' | 'output' | 'metadata' | 'input'; targetName: string }>> => {
    const linkedTo: Record<string, Array<{ targetType: 'variable' | 'output' | 'metadata' | 'input'; targetName: string }>> = {};
    
    // Check script variables
    scriptVariables?.forEach((variable: any) => {
      // Support both old single-link and new multi-link format
      const links = variable.sourceLinks || (variable.sourceBlockId ? [{
        sourceBlockId: variable.sourceBlockId,
        sourceOutputName: variable.sourceOutputName
      }] : []);
      
      links.forEach((link: any) => {
        if (link.sourceBlockId === id) {
          const outputName = link.sourceOutputName;
          if (!linkedTo[outputName]) linkedTo[outputName] = [];
          linkedTo[outputName].push({ targetType: 'variable', targetName: variable.name });
        }
      });
    });
    
    // Check script outputs
    scriptOutputs?.forEach((output: any) => {
      if (output.sourceBlockId === id) {
        const outputName = output.sourceOutputName;
        if (!linkedTo[outputName]) linkedTo[outputName] = [];
        linkedTo[outputName].push({ targetType: 'output', targetName: output.name });
      }
    });
    
    // Check script metadata
    scriptMetadata?.forEach((meta: any) => {
      if (meta.sourceBlockId === id) {
        const outputName = meta.sourceOutputName;
        if (!linkedTo[outputName]) linkedTo[outputName] = [];
        linkedTo[outputName].push({ targetType: 'metadata', targetName: meta.name });
      }
    });
    
    // Check other blocks' paramLinks
    nodes?.forEach((node: any) => {
      if (node.id !== id && node.data?.paramLinks) {
        Object.entries(node.data.paramLinks).forEach(([paramKey, linkInfo]: [string, any]) => {
          if (linkInfo.sourceBlockId === id) {
            const outputName = linkInfo.sourceOutputName;
            if (!linkedTo[outputName]) linkedTo[outputName] = [];
            linkedTo[outputName].push({ 
              targetType: 'input', 
              targetName: `${node.data?.label || node.id}.${paramKey}` 
            });
          }
        });
      }
    });
    
    return linkedTo;
  };
  const [draggedOutput, setDraggedOutput] = useState<{blockId: string, outputName: string, outputType: string} | null>(null);
  
  // Get command configuration from toolbox config
  // Determine color based on type category (muted, professional palette)
  let color: string;
  if (type === 'navigation') {
    color = '#7c3aed'; // violet (muted)
  } else if (type === 'action') {
    color = '#ea580c'; // orange (muted)
  } else if (type === 'verification') {
    color = '#2563eb'; // blue (muted)
  } else if (['sleep', 'get_current_time', 'condition', 'set_variable', 'set_variable_io', 'set_metadata', 'loop', 'custom_code', 'common_operation', 'evaluate_condition'].includes(type as string)) {
    color = '#64748b'; // slate (muted)
  } else {
    color = '#64748b'; // default
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
        const rawParams = data.params || {};
        console.log('[@UniversalBlock] Params before resolution:', rawParams);
        // ✅ Resolve {variable} references AND clean schema objects in one pass
        const resolvedParams = resolveParamsVariables(rawParams, scriptInputs, scriptVariables);
        
        console.log('[@UniversalBlock] Params after variable resolution:', resolvedParams);
        
        // Build action in EdgeAction format (standard blocks use same executor)
        const block = {
          command: data.command,
          params: resolvedParams, // ✅ Use cleaned + resolved params
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
        let lastStatusResponse: any = null; // ✅ Capture last response for transformation

        while (attempts < maxAttempts) {
          await new Promise((resolve) => setTimeout(resolve, 1000)); // Poll every 1s
          attempts++;

          const statusResult = await fetch(statusUrl);
          const statusResponse = await statusResult.json();
          lastStatusResponse = statusResponse; // ✅ Store for later use

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
        
        // ✅ Transform standard block result to frontend format
        // Standard blocks return: { result_success: 0/1/-1, result_output: any, error_msg: string }
        // Frontend expects: { success: boolean, output_data: object }
        if (lastStatusResponse?.result?.results?.[0]) {
          const blockResult = lastStatusResponse.result.results[0];
          result = {
            success: blockResult.result_success === 0,
            error: blockResult.error_msg || null,
            message: blockResult.result_success === 0 ? 'Block executed successfully' : 'Block execution failed',
            output_data: {
              result: blockResult.result_output,
              // Include other outputs if they exist
              ...blockResult
            },
            logs: lastStatusResponse.result?.logs || blockResult.logs || ''
          };
          console.log('[@UniversalBlock] Transformed block result:', result);
        }
      } else {
        // ✅ Execute action or verification using existing useAction hook (async polling built-in)
        const rawParams = data.params || {};
        
        console.log('[@UniversalBlock] Action/Verification params before resolution:', rawParams);
        
        // ✅ Resolve {variable} references AND schema objects (ensures area, etc. are concrete values)
        const resolvedParams = resolveParamsVariables(rawParams, scriptInputs, scriptVariables);
        console.log('[@UniversalBlock] Action/Verification params after variable resolution:', resolvedParams);
        
        // Build action in EdgeAction format for useAction hook
        const action = {
          command: data.command,
          name: data.label || data.command, // EdgeAction requires name field
          params: resolvedParams, // ✅ Use cleaned + resolved params
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
        
        // ✅ Update block outputs with actual values from execution
        console.log('[@UniversalBlock] Checking output update:', {
          hasOutputData: Boolean(result.output_data),
          hasBlockOutputs: Boolean(data.blockOutputs),
          outputDataKeys: result.output_data ? Object.keys(result.output_data) : [],
          blockOutputs: data.blockOutputs
        });
        console.log('[@UniversalBlock] Full result.output_data:', JSON.stringify(result.output_data, null, 2));
        
        if (result.output_data && data.blockOutputs) {
          const outputData = result.output_data;
          
          console.log('[@UniversalBlock] Mapping outputs from output_data:', {
            outputDataKeys: Object.keys(outputData),
            blockOutputNames: data.blockOutputs.map((o: any) => o.name)
          });
          
          const updatedOutputs = data.blockOutputs.map((output: any) => {
            // Map output directly from top-level output_data keys
            const mappedValue = outputData[output.name];
            console.log(`[@UniversalBlock] Mapping ${output.name}:`, {
              found: mappedValue !== undefined,
              valueType: typeof mappedValue,
              isObject: typeof mappedValue === 'object',
              keys: typeof mappedValue === 'object' && mappedValue !== null ? Object.keys(mappedValue).slice(0, 5) : 'N/A'
            });
            return {
              ...output,
              value: mappedValue !== undefined ? mappedValue : output.value
            };
          });
          
          console.log('[@UniversalBlock] Updated outputs:', updatedOutputs);
          updateBlock(id as string, { blockOutputs: updatedOutputs });
        }
        
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
    // For standard blocks: show command name directly in header (no duplicate label)
    else if (['sleep', 'get_current_time', 'condition', 'set_variable', 'set_variable_io', 'set_metadata', 'loop', 'custom_code', 'common_operation', 'evaluate_condition'].includes(type as string)) {
      headerLabel = categoryLabel; // Show command name in header
      contentLabel = ''; // Don't duplicate in content
    }
    // For generic action blocks from toolboxBuilder: header = "ACTION", content = empty (command shown in header)
    else if (type === 'action' || ['press_key', 'press_sequence', 'tap', 'swipe', 'type_text'].includes(type as string)) {
      headerLabel = 'ACTION';
      contentLabel = ''; // Don't duplicate - already shown in header
    }
    // For generic verification blocks from toolboxBuilder: header = "VERIFICATION", content = empty (command shown in header)
    else if (type === 'verification' || ['verify_image', 'verify_ocr', 'verify_audio', 'verify_element'].includes(type as string)) {
      headerLabel = 'VERIFICATION';
      contentLabel = ''; // Don't duplicate - already shown in header
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
        content = <CheckIcon sx={{ fontSize: isActive ? 18 : 16 }} />;
      } else if (output === 'failure' || output === 'false') {
        content = <CloseIcon sx={{ fontSize: isActive ? 18 : 16 }} />;
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
              width: isActive ? 60 : 50,
              height: isActive ? 24 : 20,
              borderRadius: 4,
              border: 'none',
              bottom: isActive ? -26 : -22,
              left: '50%',
              transform: 'translateX(-50%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'white',
              fontWeight: 'bold',
              fontSize: 12,
              cursor: 'pointer',
              boxShadow: isActive ? `0 0 12px ${handleColor}` : '0 1px 3px rgba(0,0,0,0.2)',
              transition: 'all 0.2s ease',
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
                  '50%': { transform: 'scale(1.15)' },
                },
              }}
            >
              {content}
            </Box>
          </Handle>
        </>
      );
    }
    
    // Multiple outputs - compact, centered with gap
    return (
      <Box
        sx={{
          position: 'absolute',
          bottom: -22,
          left: '50%',
          transform: 'translateX(-50%)',
          display: 'flex',
          gap: 0.5,
        }}
      >
        {outputs.map((output) => {
          const handleColor = getHandleColor(output);
          const isAnimating = animateHandle === output;
          const isActive = isHandleActive(output);
          
          // Determine icon/text based on output type
          let content;
          if (output === 'success' || output === 'true' || output === 'complete') {
            content = <CheckIcon sx={{ fontSize: isActive ? 16 : 14 }} />;
          } else if (output === 'failure' || output === 'false') {
            content = <CloseIcon sx={{ fontSize: isActive ? 16 : 14 }} />;
          } else if (output === 'break') {
            content = <Typography fontSize={9} fontWeight="bold">BRK</Typography>;
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
                position: 'relative',
                transform: 'none',
                top: 0,
                left: 0,
                background: handleColor,
                width: isActive ? 48 : 40,
                height: isActive ? 22 : 18,
                borderRadius: 4,
                border: 'none',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'white',
                fontWeight: 'bold',
                fontSize: 12,
                cursor: 'pointer',
                boxShadow: isActive ? `0 0 12px ${handleColor}` : '0 1px 3px rgba(0,0,0,0.2)',
                transition: 'all 0.2s ease',
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
                    '50%': { transform: 'scale(1.15)' },
                  },
                }}
              >
                {content}
              </Box>
            </Handle>
          );
        })}
      </Box>
    );
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
        width: 340,  // Fixed width - increased for longer labels
        minHeight: 120,  // Fixed minimum height
        maxHeight: 320, // Fixed maximum height - increased for expanded inputs/outputs
        border: selected ? '2px solid #fbbf24' : `1px solid ${actualMode === 'dark' ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)'}`,
        borderLeft: `3px solid ${color}`, // Left accent bar for type indication
        ...getExecutionStyling(), // Apply execution styling
        borderRadius: 1.5,
        background: actualMode === 'dark' ? '#1e293b' : '#ffffff',
        boxShadow: actualMode === 'dark' 
          ? '0 2px 8px rgba(0,0,0,0.3)' 
          : '0 2px 8px rgba(0,0,0,0.08)',
        cursor: 'pointer',
        opacity: dragging ? 0.5 : (isExecuting ? 0.7 : 1),
        transition: 'all 0.2s ease',
        pointerEvents: isExecuting ? 'none' : 'auto', // Disable interaction during execution
        position: 'relative',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'visible', // Changed to visible to show output handles
        '&:hover': {
          boxShadow: isExecuting 
            ? (actualMode === 'dark' ? '0 2px 8px rgba(0,0,0,0.3)' : '0 2px 8px rgba(0,0,0,0.08)')
            : (actualMode === 'dark' ? '0 4px 16px rgba(0,0,0,0.4)' : '0 4px 16px rgba(0,0,0,0.12)'),
        },
      }}
    >
      {/* Duration Badge - Above Block */}
      {executionState?.duration !== undefined && ['success', 'failure', 'error'].includes(executionState.status) && (
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
            fontSize: 18,
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
          background: actualMode === 'dark' ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.02)',
          borderBottom: `1px solid ${actualMode === 'dark' ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)'}`,
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
                  style: { color: color, fontSize: 14, fontWeight: 600, padding: '2px 4px' }
                }}
                sx={{
                  '& .MuiOutlinedInput-root': {
                    '& fieldset': {
                      borderColor: color,
                    },
                    '&:hover fieldset': {
                      borderColor: color,
                    },
                    '&.Mui-focused fieldset': {
                      borderColor: color,
                    },
                  },
                  flex: 1,
                  maxWidth: '300px',
                }}
              />
              <IconButton
                size="small"
                onClick={(e) => {
                  e.stopPropagation();
                  handleLabelCancel();
                }}
                sx={{
                  color: 'text.secondary',
                  padding: '2px',
                  '&:hover': {
                    backgroundColor: 'action.hover',
                  },
                }}
              >
                <CloseIcon sx={{ fontSize: 14 }} />
              </IconButton>
            </>
          ) : (
            <>
              <Typography 
                fontWeight={600}
                fontSize={14}
                sx={{ 
                  flex: 1,
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                  color: color, // Use accent color for label
                }}
              >
                {data.label || headerLabel}
              </Typography>
              <IconButton
                size="small"
                onClick={handleLabelEdit}
                sx={{
                  color: 'text.secondary',
                  padding: '2px',
                  '&:hover': {
                    backgroundColor: 'action.hover',
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
                color: color,
                padding: '4px',
                '&:hover': {
                  backgroundColor: 'action.hover',
                },
                '&.Mui-disabled': {
                  color: 'text.disabled',
                },
              }}
            >
              {isExecuting ? <CircularProgress size={14} sx={{ color: color }} /> : <PlayArrowIcon sx={{ fontSize: 18 }} />}
            </IconButton>
          )}
        </Box>
      </Box>
      
      {/* Content */}
      <Box sx={{ 
        p: 1.5, 
        flex: 1, 
        overflowY: 'auto', 
        overflowX: 'hidden',
        '&::-webkit-scrollbar': {
          width: '4px',
        },
        '&::-webkit-scrollbar-track': {
          background: 'transparent',
        },
        '&::-webkit-scrollbar-thumb': {
          background: 'rgba(128, 128, 128, 0.3)',
          borderRadius: '2px',
          '&:hover': {
            background: 'rgba(128, 128, 128, 0.5)',
          },
        },
      }}>
        {isConfigured ? (
          <>
            {contentLabel && (
              <Typography 
                fontSize={type === 'navigation' ? 14 : 20} 
                fontWeight="medium" 
                mb={1}
                textAlign={type === 'navigation' ? 'center' : 'left'}
              >
                {contentLabel}
              </Typography>
            )}
            
            {/* Universal Input Display */}
            <InputDisplay
              params={data.params}
              paramLinks={data.paramLinks}
              command={data.command} 
              draggedOutput={draggedOutput}
              onDrop={(paramKey, dragData) => {
                updateBlock(id as string, {
                  paramLinks: {
                    ...data.paramLinks,
                    [paramKey]: {
                      sourceBlockId: dragData.blockId,
                      sourceOutputName: dragData.outputName,
                      sourceOutputType: dragData.outputType
                    }
                  }
                });
                setDraggedOutput(null);
                showSuccess(`Linked ${paramKey} ← ${dragData.outputName}`);
              }}
              onUnlink={(paramKey) => {
                const newLinks = { ...data.paramLinks };
                delete newLinks[paramKey];
                updateBlock(id as string, { paramLinks: newLinks });
                showSuccess(`Unlinked ${paramKey}`);
              }}
              onConfigureClick={
                // ✅ For action/verification blocks, open ActionConfigDialog
                (type === 'action' || type === 'verification')
                  ? () => {
                      console.log('[@UniversalBlock] onConfigureClick called, opening dialog');
                      setIsConfigDialogOpen(true);
                    }
                  // ✅ For standard blocks, clicking input opens config dialog
                  : ['evaluate_condition', 'custom_code', 'common_operation', 'set_variable', 'set_variable_io', 'get_current_time', 'sleep'].includes(type as string)
                    ? () => {
                        // Trigger config dialog opening through context
                        const event = new CustomEvent('openBlockConfig', { detail: { blockId: id } });
                        window.dispatchEvent(event);
                      }
                    : undefined
              }
            />
            
            {/* Universal Output Display */}
            <OutputDisplay
              blockOutputs={data.blockOutputs}
              blockId={id as string}
              linkedTo={calculateLinkedTo()} // ✅ NEW: Pass linked information
              onDragStart={(dragData) => {
                setDraggedOutput(dragData);
              }}
              onDragEnd={() => {
                setDraggedOutput(null);
              }}
            />
            
            {data.iterations && data.iterations > 1 && (
              <Typography fontSize={12} color="text.secondary" mt={0.5}>
                × {data.iterations} iterations
              </Typography>
            )}
            {data.iterator && data.iterator > 1 && (
              <Typography fontSize={12} color="text.secondary" mt={0.5}>
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
          width: 24,
          height: 24,
          borderRadius: '50%',
          border: 'none',
          top: -12,
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
          border: 'none',
          top: -7,
          boxShadow: '0 1px 3px rgba(0,0,0,0.2)',
          pointerEvents: 'none',
        }}
      />
      
      {/* Output handles at bottom - rectangles with icons */}
      {renderOutputHandles()}
      
      {/* Action/Verification Configuration Dialog */}
      {(type === 'action' || type === 'verification') && (
        <ActionConfigDialog
          open={isConfigDialogOpen}
          initialData={{
            command: data.command,
            params: data.params || {},
            action_type: data.action_type
          }}
          onSave={(actionData) => {
            console.log('[@UniversalBlock] Saving action data:', actionData);
            updateBlock(id as string, {
              params: actionData.params
            });
            setIsConfigDialogOpen(false);
            showSuccess('Parameters updated');
          }}
          onCancel={() => {
            console.log('[@UniversalBlock] Dialog cancelled');
            setIsConfigDialogOpen(false);
          }}
        />
      )}
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

