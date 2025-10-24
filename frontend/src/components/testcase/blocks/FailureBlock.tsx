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
        width: 100,
        height: 100,
        borderRadius: '50%',
        background: '#ef4444',
        border: selected ? '3px solid #fbbf24' : 'none',
        display: 'flex',
        flexDirection: 'column',
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
      <CancelIcon sx={{ color: 'white', fontSize: 40 }} />
      <Typography color="white" fontWeight="bold" fontSize={12} mt={0.5}>
        FAILURE
      </Typography>
      
      {/* Input handle at top */}
      <Handle
        type="target"
        position={Position.Top}
        id="input"
        style={{
          background: '#ef4444',
          width: 40,
          height: 8,
          borderRadius: '4px',
          border: '2px solid white',
          top: -4,
        }}
      />
    </Box>
  );
};

