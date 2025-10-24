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
        width: 70,
        height: 70,
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
      <Typography color="white" fontWeight="bold" fontSize={12}>
        START
      </Typography>
      
      {/* Output handle at bottom - rectangle for vertical flow */}
      <Handle
        type="source"
        position={Position.Bottom}
        id="success"
        style={{
          background: '#10b981',
          width: 40,
          height: 8,
          borderRadius: '4px',
          border: '2px solid white',
        }}
      />
    </Box>
  );
};

