import React from 'react';
import { Box, Typography } from '@mui/material';
import { Handle, Position, NodeProps } from 'reactflow';
import CancelIcon from '@mui/icons-material/Cancel';

/**
 * Failure Block - Terminal node for failed testcase
 * Only has input handle (no outputs)
 */
export const FailureBlock: React.FC<NodeProps> = ({ selected, dragging }) => {
  return (
    <Box
      sx={{
        width: 120,
        height: 60,
        borderRadius: 2,
        background: '#ef4444',
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
      <Typography color="white" fontWeight="bold" fontSize={18}>
        FAIL
      </Typography>
      
      {/* Input handle at top - circle */}
      <Handle
        type="target"
        position={Position.Top}
        id="input"
        style={{
          background: '#ef4444',
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

