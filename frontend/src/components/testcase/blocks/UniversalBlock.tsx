import React, { useState } from 'react';
import { Box, Typography, Chip, IconButton, CircularProgress } from '@mui/material';
import { Handle, Position, NodeProps } from 'reactflow';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import CheckIcon from '@mui/icons-material/Check';
import CloseIcon from '@mui/icons-material/Close';
import { useTheme } from '../../../contexts/ThemeContext';
import { useToastContext } from '../../../contexts/ToastContext';
import { useDeviceData } from '../../../contexts/device/DeviceDataContext';
import { buildServerUrl } from '../../../utils/buildUrlUtils';
import { getCommandConfig, OutputType } from '../builder/toolboxConfig';

/**
 * Universal Block - Renders any command type with appropriate handles
 * Handles are generated based on command configuration
 */
export const UniversalBlock: React.FC<NodeProps> = ({ data, selected, dragging, type }) => {
  const { actualMode } = useTheme();
  const { showSuccess, showError } = useToastContext();
  const { currentHost, currentDeviceId } = useDeviceData();
  const [isExecuting, setIsExecuting] = useState(false);
  const [animateHandle, setAnimateHandle] = useState<'success' | 'failure' | null>(null);
  
  // Get command configuration from toolbox config
  const commandConfig = getCommandConfig(type as string);
  
  // Determine color based on type category (fallback if not in static config)
  let color = commandConfig?.color;
  if (!color) {
    // Generic types from toolboxBuilder need color assignment
    if (type === 'navigation') {
      color = '#8b5cf6'; // purple
    } else if (type === 'action') {
      color = '#f97316'; // orange - distinguishable from failure (red)
    } else if (type === 'verification') {
      color = '#3b82f6'; // blue - distinguishable from success (green)
    } else if (['sleep', 'get_current_time', 'condition', 'set_variable', 'loop'].includes(type as string)) {
      color = '#6b7280'; // grey (standard)
    } else {
      color = '#6b7280'; // gray fallback
    }
  }
  
  const categoryLabel = commandConfig?.label || data.command || type;
  const icon = commandConfig?.icon || null;
  const outputs: OutputType[] = commandConfig?.outputs || ['success', 'failure'];
  
  // Execute handler for action/verification blocks
  const handleExecute = async (e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent block selection
    
    // Validate
    if (!currentHost) {
      showError('No host selected');
      return;
    }
    
    if (!data.command) {
      showError('No command configured');
      return;
    }
    
    // Determine if action or verification
    const isAction = type === 'action' || ['press_key', 'press_sequence', 'tap', 'swipe', 'type_text'].includes(type as string);
    const isVerification = type === 'verification' || ['verify_image', 'verify_ocr', 'verify_audio', 'verify_element'].includes(type as string);
    
    if (!isAction && !isVerification) {
      showError('Only actions and verifications can be executed');
      return;
    }
    
    setIsExecuting(true);
    
    // Dispatch custom event to trigger overlay
    window.dispatchEvent(new CustomEvent('blockExecutionStart', {
      detail: {
        command: data.command,
        params: data.params,
      }
    }));
    
    const startTime = Date.now();
    
    try {
      // Build action payload
      const actionPayload = {
        command: data.command,
        params: data.params || {},
        action_type: data.action_type,
        verification_type: data.verification_type,
        threshold: data.threshold,
        reference: data.reference,
      };
      
      // Execute via API
      const endpoint = isAction ? '/server/action/execute' : '/server/action/execute'; // Verifications use same endpoint
      const response = await fetch(buildServerUrl(`${endpoint}?team_id=default-team-id`), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: actionPayload,
          host_name: currentHost.host_name,
          device_id: currentDeviceId || 'device1',
        }),
      });
      
      const result = await response.json();
      const duration = Date.now() - startTime;
      const durationText = `${(duration / 1000).toFixed(2)}s`;
      
      if (result.success) {
        setAnimateHandle('success');
        showSuccess(`✓ ${data.command} - ${durationText}`);
        // Clear animation after 2 seconds
        setTimeout(() => setAnimateHandle(null), 2000);
      } else {
        setAnimateHandle('failure');
        showError(`✗ ${data.command} - ${durationText}\n${result.error || 'Execution failed'}`);
        // Clear animation after 2 seconds
        setTimeout(() => setAnimateHandle(null), 2000);
      }
    } catch (error) {
      const duration = Date.now() - startTime;
      const durationText = `${(duration / 1000).toFixed(2)}s`;
      setAnimateHandle('failure');
      showError(`✗ ${data.command} - ${durationText}\nError: ${error instanceof Error ? error.message : 'Unknown error'}`);
      // Clear animation after 2 seconds
      setTimeout(() => setAnimateHandle(null), 2000);
    } finally {
      setIsExecuting(false);
      // Dispatch custom event to clear overlay
      window.dispatchEvent(new CustomEvent('blockExecutionEnd'));
    }
  };
  
  // Determine header and content based on block type
  let headerLabel = categoryLabel;
  let contentLabel = 'Click to configure';
  
  // Check if block is configured
  const isConfigured = Boolean(
    data.command || 
    data.target_node_label || 
    data.iterations ||
    data.label || // For navigation blocks
    Object.keys(data).length > 1 // More than just position data
  );
  
  // Determine if this block can be executed
  const canExecute = Boolean(
    (type === 'action' || type === 'verification' || 
     ['press_key', 'press_sequence', 'tap', 'swipe', 'type_text', 
      'verify_image', 'verify_ocr', 'verify_audio', 'verify_element'].includes(type as string)) &&
    data.command
  );
  
  if (isConfigured) {
    // For navigation blocks: header = "NAVIGATION", content = node name (e.g., "home")
    if (type === 'navigation' && data.target_node_label) {
      headerLabel = 'NAVIGATION';
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
    
    if (outputs.length === 1) {
      // Single output - centered at bottom, rectangle
      const output = outputs[0];
      const handleColor = getHandleColor(output);
      const isAnimating = animateHandle === output;
      
      let content;
      if (output === 'success' || output === 'true' || output === 'complete') {
        content = <CheckIcon />;
      } else if (output === 'failure' || output === 'false') {
        content = <CloseIcon />;
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
              width: 80,
              height: 32,
              borderRadius: 4,
              border: '2px solid white',
              bottom: -36,
              left: '50%',
              transform: 'translateX(-50%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'white',
              fontWeight: 'bold',
              fontSize: 12,
              cursor: 'pointer',
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
      
      // Determine icon/text based on output type
      let content;
      if (output === 'success' || output === 'true' || output === 'complete') {
        content = <CheckIcon fontSize="small" />;
      } else if (output === 'failure' || output === 'false') {
        content = <CloseIcon fontSize="small" />;
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
            width: 70,
            height: 28,
            borderRadius: 4,
            border: '2px solid white',
            bottom: -32,
            transform: 'translateX(-50%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'white',
            fontWeight: 'bold',
            fontSize: 11,
            cursor: 'pointer',
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
  
  return (
    <Box
      sx={{
        minWidth: 240,
        border: selected ? '3px solid #fbbf24' : `2px solid ${color}`,
        borderRadius: 2,
        background: actualMode === 'dark' ? '#1f2937' : '#ffffff',
        boxShadow: 2,
        cursor: 'pointer',
        opacity: dragging ? 0.5 : (isExecuting ? 0.7 : 1),
        transition: 'opacity 0.2s',
        pointerEvents: isExecuting ? 'none' : 'auto', // Disable interaction during execution
        '&:hover': {
          boxShadow: isExecuting ? 2 : 4,
        },
      }}
    >
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
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          {icon && (
            <Box sx={{ color: 'white', display: 'flex', alignItems: 'center' }}>
              {icon}
            </Box>
          )}
          <Typography color="white" fontWeight="bold" fontSize={13}>
            {headerLabel.toUpperCase()}
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          {(data.action_type || data.verification_type) && (
            <Chip
              label={data.action_type || data.verification_type}
              size="small"
              sx={{ 
                fontSize: 10, 
                height: 20,
                backgroundColor: 'rgba(255, 255, 255, 0.2)',
                color: 'white',
              }}
            />
          )}
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
            <Typography fontSize={14} fontWeight="medium">
              {contentLabel}
            </Typography>
            {data.params && Object.keys(data.params).length > 0 && (
              <Box sx={{ mt: 0.5, display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                {Object.entries(data.params).slice(0, 2).map(([key, value]) => (
                  <Chip
                    key={key}
                    label={`${key}: ${String(value).substring(0, 15)}${String(value).length > 15 ? '...' : ''}`}
                    size="small"
                    sx={{ fontSize: 10, height: 20 }}
                  />
                ))}
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

