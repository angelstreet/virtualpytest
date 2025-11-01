import React from 'react';
import { Box, Typography } from '@mui/material';
import { Handle, Position, NodeProps } from 'reactflow';

/**
 * Start Block - Entry point for testcase execution
 * Only has output handles (success/failure)
 */
export const StartBlock: React.FC<NodeProps> = ({ selected, dragging }) => {
  return (
    <Box
      sx={{
        minWidth: 120,
        minHeight: 60,
        background: '#e3f2fd',
        border: selected ? '3px solid #fbbf24' : '2px solid #2196f3',
        borderRadius: 2,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontWeight: 'bold',
        color: '#1976d2',
        fontSize: '1.1rem',
        cursor: 'pointer',
        opacity: dragging ? 0.5 : 1,
        transition: 'opacity 0.2s',
        boxShadow: selected ? 4 : 2,
        '&:hover': {
          boxShadow: 4,
        },
      }}
    >
      <Typography variant="body1" fontWeight="bold" color="#1976d2">
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
          background: '#2196f3',
          width: 20,
          height: 20,
          borderRadius: '50%',
          border: '2px solid white',
          bottom: -10,
          pointerEvents: 'none',
        }}
      />
    </Box>
  );
};

