import React from 'react';
import { Box, Typography, Chip } from '@mui/material';
import { Handle, Position, NodeProps } from 'reactflow';
import { useTheme } from '../../../contexts/ThemeContext';
import { getCommandConfig, OutputType } from '../builder/toolboxConfig';

/**
 * Universal Block - Renders any command type with appropriate handles
 * Handles are generated based on command configuration
 */
export const UniversalBlock: React.FC<NodeProps> = ({ data, selected, dragging, type }) => {
  const { actualMode } = useTheme();
  
  // Get command configuration from toolbox config
  const commandConfig = getCommandConfig(type as string);
  
  // Determine color based on type category (fallback if not in static config)
  let color = commandConfig?.color;
  if (!color) {
    // Generic types from toolboxBuilder need color assignment
    if (type === 'navigation') {
      color = '#8b5cf6'; // purple
    } else if (type === 'action') {
      color = '#ef4444'; // red
    } else if (type === 'verification') {
      color = '#10b981'; // green
    } else if (['sleep', 'get_current_time', 'condition', 'set_variable', 'loop'].includes(type as string)) {
      color = '#3b82f6'; // blue (standard)
    } else {
      color = '#6b7280'; // gray fallback
    }
  }
  
  const categoryLabel = commandConfig?.label || data.command || type;
  const icon = commandConfig?.icon || null;
  const outputs: OutputType[] = commandConfig?.outputs || ['success', 'failure'];
  
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
      // Single output - centered at bottom, circle
      const output = outputs[0];
      const handleColor = getHandleColor(output);
      
      return (
        <Handle
          type="source"
          position={Position.Bottom}
          id={output}
          style={{
            background: handleColor,
            width: 12,
            height: 12,
            borderRadius: '50%',
            border: '2px solid white',
            bottom: -6,
            left: '50%',
            transform: 'translateX(-50%)',
          }}
        />
      );
    }
    
    // Multiple outputs - positioned left and right, circles
    return outputs.map((output, idx) => {
      const handleColor = getHandleColor(output);
      const leftPosition = idx === 0 ? '35%' : '65%';
      
      return (
        <Handle
          key={output}
          type="source"
          position={Position.Bottom}
          id={output}
          style={{
            left: leftPosition,
            background: handleColor,
            width: 12,
            height: 12,
            borderRadius: '50%',
            border: '2px solid white',
            bottom: -6,
          }}
        />
      );
    });
  };
  
  return (
    <Box
      sx={{
        minWidth: 180,
        border: selected ? '3px solid #fbbf24' : `2px solid ${color}`,
        borderRadius: 2,
        background: actualMode === 'dark' ? '#1f2937' : '#ffffff',
        boxShadow: 2,
        cursor: 'pointer',
        opacity: dragging ? 0.5 : 1, // No transparency for configured blocks
        transition: 'opacity 0.2s',
        '&:hover': {
          boxShadow: 4,
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
        }}
      >
        {icon && (
          <Box sx={{ color: 'white', display: 'flex', alignItems: 'center' }}>
            {icon}
          </Box>
        )}
        <Typography color="white" fontWeight="bold" fontSize={13}>
          {headerLabel.toUpperCase()}
        </Typography>
      </Box>
      
      {/* Content */}
      <Box sx={{ p: 1.5 }}>
        {isConfigured ? (
          <>
            {data.action_type && (
              <Chip
                label={data.action_type}
                size="small"
                sx={{ fontSize: 10, height: 20, mb: 0.5 }}
              />
            )}
            {data.verification_type && (
              <Chip
                label={data.verification_type}
                size="small"
                sx={{ fontSize: 10, height: 20, mb: 0.5 }}
              />
            )}
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
      
      {/* Input handle at top - circle */}
      <Handle
        type="target"
        position={Position.Top}
        id="input"
        style={{
          background: color,
          width: 12,
          height: 12,
          borderRadius: '50%',
          border: '2px solid white',
          top: -6,
        }}
      />
      
      {/* Output handles at bottom - circles */}
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
      return '#f59e0b'; // orange/yellow
    default:
      return '#6b7280'; // gray
  }
};

