import React from 'react';
import { Box, Typography } from '@mui/material';
import { Handle, Position, NodeProps } from 'reactflow';

interface TerminalBlockProps extends NodeProps {
  label: string;
  color: string;
}

/**
 * Terminal Block - Generic component for PASS/FAIL blocks
 * Used by SuccessBlock and FailureBlock
 */
export const TerminalBlock: React.FC<TerminalBlockProps> = ({ label, color, selected, dragging }) => {
  return (
    <Box
      sx={{
        width: 60,
        height: 30,
        borderRadius: 2,
        background: color,
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
      <Typography color="white" fontWeight="bold" fontSize={14}>
        {label}
      </Typography>
      
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
    </Box>
  );
};

