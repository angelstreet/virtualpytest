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
  
  // Fallback values if command not found in config
  const color = commandConfig?.color || '#6b7280';
  const label = commandConfig?.label || type;
  const icon = commandConfig?.icon || null;
  const outputs: OutputType[] = commandConfig?.outputs || ['success', 'failure'];
  
  // Check if block is configured (has command or other required data)
  const isConfigured = Boolean(
    data.command || 
    data.target_node_label || 
    data.iterations ||
    Object.keys(data).length > 0
  );
  
  // Get display label from data or use default
  const displayLabel = data.command || label;
  
  // Render output handles based on configured outputs
  const renderOutputHandles = () => {
    if (outputs.length === 0) {
      return null; // No output handles (shouldn't happen but safe)
    }
    
    if (outputs.length === 1) {
      // Single output - centered at bottom
      const output = outputs[0];
      const handleColor = getHandleColor(output);
      
      return (
        <Handle
          type="source"
          position={Position.Bottom}
          id={output}
          style={{
            background: handleColor,
            width: 40,
            height: 8,
            borderRadius: '4px',
            border: '2px solid white',
            bottom: -4,
            left: '50%',
            transform: 'translateX(-50%)',
          }}
        />
      );
    }
    
    // Multiple outputs - positioned left and right
    return outputs.map((output, idx) => {
      const handleColor = getHandleColor(output);
      const leftPosition = idx === 0 ? '30%' : '70%';
      
      return (
        <Handle
          key={output}
          type="source"
          position={Position.Bottom}
          id={output}
          style={{
            left: leftPosition,
            background: handleColor,
            width: 35,
            height: 8,
            borderRadius: '4px',
            border: '2px solid white',
            bottom: -4,
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
        opacity: dragging ? 0.5 : (isConfigured ? 1 : 0.6),
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
          {label.toUpperCase()}
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
              {displayLabel}
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
            {data.target_node_label && (
              <Typography fontSize={12} color="text.secondary" mt={0.5}>
                → {data.target_node_label}
              </Typography>
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
      
      {/* Input handle at top */}
      <Handle
        type="target"
        position={Position.Top}
        id="input"
        style={{
          background: color,
          width: 40,
          height: 8,
          borderRadius: '4px',
          border: '2px solid white',
          top: -4,
        }}
      />
      
      {/* Output handles at bottom */}
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

