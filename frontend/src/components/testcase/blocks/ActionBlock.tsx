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
export const ActionBlock: React.FC<NodeProps> = ({ data, selected }) => {
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
        '&:hover': {
          boxShadow: 4,
        },
        opacity: isConfigured ? 1 : 0.6,
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
      
      {/* Input handle */}
      <Handle
        type="target"
        position={Position.Left}
        id="input"
        style={{
          background: actualMode === 'dark' ? '#3b82f6' : '#2563eb',
          width: 10,
          height: 10,
          border: '2px solid white',
        }}
      />
      
      {/* Output handles - success and failure */}
      <Handle
        type="source"
        position={Position.Right}
        id="success"
        style={{
          top: '30%',
          background: '#10b981',
          width: 10,
          height: 10,
          border: '2px solid white',
        }}
      />
      <Handle
        type="source"
        position={Position.Right}
        id="failure"
        style={{
          top: '70%',
          background: '#ef4444',
          width: 10,
          height: 10,
          border: '2px solid white',
        }}
      />
    </Box>
  );
};

