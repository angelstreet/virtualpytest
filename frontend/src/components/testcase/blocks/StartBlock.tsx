import React from 'react';
import { Box, Typography } from '@mui/material';
import { Handle, Position, NodeProps } from 'reactflow';
import { useTheme } from '../../../contexts/ThemeContext';

/**
 * Start Block - Entry point for testcase execution
 * Only has output handles (success/failure)
 */
export const StartBlock: React.FC<NodeProps> = ({ selected, dragging }) => {
  const { actualMode } = useTheme();
  
  return (
    <Box
      sx={{
        width: 40,
        height: 40,
        borderRadius: '50%',
        background: actualMode === 'dark' ? '#2563eb' : '#3b82f6',
        border: selected ? '3px solid #fbbf24' : 'none',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        boxShadow: 3,
        cursor: 'pointer',
        opacity: dragging ? 0.5 : 1,
        transition: 'opacity 0.2s',
        '&:hover': {
          boxShadow: 6,
        },
      }}
    >
      <Typography color="white" fontWeight="bold" fontSize={10}>
        START
      </Typography>
      
      {/* Transparent larger handle for better grabbing */}
      <Handle
        type="source"
        position={Position.Bottom}
        id="success-hitarea"
        style={{
          background: 'transparent',
          width: 32,
          height: 32,
          borderRadius: '50%',
          border: 'none',
          bottom: -16,
          pointerEvents: 'all',
        }}
      />
      
      {/* Visible output handle at bottom - circle, blue to match START */}
      <Handle
        type="source"
        position={Position.Bottom}
        id="success"
        style={{
          background: '#3b82f6',
          width: 14,
          height: 14,
          borderRadius: '50%',
          border: '2px solid white',
          bottom: -8,
          pointerEvents: 'none',
        }}
      />
    </Box>
  );
};

