import React from 'react';
import { Box, Typography } from '@mui/material';
import { Handle, Position, NodeProps } from 'reactflow';
import { useTheme } from '../../../contexts/ThemeContext';

/**
 * Start Block - Entry point for testcase execution
 * Only has output handles (success/failure)
 */
export const StartBlock: React.FC<NodeProps> = ({ data, selected }) => {
  const { actualMode } = useTheme();
  
  return (
    <Box
      sx={{
        width: 100,
        height: 100,
        borderRadius: '50%',
        background: actualMode === 'dark' ? '#2563eb' : '#3b82f6',
        border: selected ? '3px solid #fbbf24' : 'none',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        boxShadow: 3,
        cursor: 'pointer',
        '&:hover': {
          boxShadow: 6,
        },
      }}
    >
      <Typography color="white" fontWeight="bold" fontSize={16}>
        START
      </Typography>
      
      {/* Output handle - only success (start always succeeds) */}
      <Handle
        type="source"
        position={Position.Right}
        id="success"
        style={{
          background: '#10b981',
          width: 12,
          height: 12,
          border: '2px solid white',
        }}
      />
    </Box>
  );
};

