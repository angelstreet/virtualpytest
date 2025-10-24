import React from 'react';
import { Box, Typography } from '@mui/material';
import { Handle, Position, NodeProps } from 'reactflow';
import CancelIcon from '@mui/icons-material/Cancel';

/**
 * Failure Block - Terminal node for failed testcase
 * Only has input handle (no outputs)
 */
export const FailureBlock: React.FC<NodeProps> = ({ selected }) => {
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
        '&:hover': {
          boxShadow: 6,
        },
      }}
    >
      <CancelIcon sx={{ color: 'white', fontSize: 40 }} />
      <Typography color="white" fontWeight="bold" fontSize={12} mt={0.5}>
        FAILURE
      </Typography>
      
      {/* Input handle only */}
      <Handle
        type="target"
        position={Position.Left}
        id="input"
        style={{
          background: '#ef4444',
          width: 12,
          height: 12,
          border: '2px solid white',
        }}
      />
    </Box>
  );
};

