import React from 'react';
import { Box, Typography, Chip } from '@mui/material';
import { Handle, Position, NodeProps } from 'reactflow';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import { useTheme } from '../../../contexts/ThemeContext';
import { ActionBlockData } from '../../../types/testcase/TestCase_Types';

/**
 * Action Block - Executes actions (press_key, tap, etc.)
 * Has both success and failure output handles
 */
export const ActionBlock: React.FC<NodeProps> = ({ data, selected, dragging }) => {
  const { actualMode } = useTheme();
  const actionData = data as ActionBlockData;
  
  const isConfigured = Boolean(actionData.command);
  
  return (
    <Box
      sx={{
        minWidth: 180,
        border: selected ? '3px solid #fbbf24' : `2px solid ${actualMode === 'dark' ? '#3b82f6' : '#2563eb'}`,
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
          background: actualMode === 'dark' ? '#3b82f6' : '#2563eb',
          p: 1,
          display: 'flex',
          alignItems: 'center',
          gap: 1,
        }}
      >
        <PlayArrowIcon sx={{ color: 'white', fontSize: 18 }} />
        <Typography color="white" fontWeight="bold" fontSize={13}>
          ACTION
        </Typography>
      </Box>
      
      {/* Content */}
      <Box sx={{ p: 1.5 }}>
        {isConfigured ? (
          <>
            <Typography fontSize={14} fontWeight="medium">
              {actionData.command}
            </Typography>
            {actionData.params && Object.keys(actionData.params).length > 0 && (
              <Box sx={{ mt: 0.5, display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                {Object.entries(actionData.params).slice(0, 2).map(([key, value]) => (
                  <Chip
                    key={key}
                    label={`${key}: ${value}`}
                    size="small"
                    sx={{ fontSize: 10, height: 20 }}
                  />
                ))}
              </Box>
            )}
            {actionData.iterator && actionData.iterator > 1 && (
              <Typography fontSize={11} color="text.secondary" mt={0.5}>
                × {actionData.iterator}
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
          background: actualMode === 'dark' ? '#3b82f6' : '#2563eb',
          width: 12,
          height: 12,
          borderRadius: '50%',
          border: '2px solid white',
          top: -6,
        }}
      />
      
      {/* Output handles at bottom - circles */}
      <Handle
        type="source"
        position={Position.Bottom}
        id="success"
        style={{
          left: '35%',
          background: '#10b981',
          width: 12,
          height: 12,
          borderRadius: '50%',
          border: '2px solid white',
          bottom: -6,
        }}
      />
      <Handle
        type="source"
        position={Position.Bottom}
        id="failure"
        style={{
          left: '65%',
          background: '#ef4444',
          width: 12,
          height: 12,
          borderRadius: '50%',
          border: '2px solid white',
          bottom: -6,
        }}
      />
    </Box>
  );
};

