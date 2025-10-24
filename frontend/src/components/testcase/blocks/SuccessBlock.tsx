import React from 'react';
import { Box, Typography } from '@mui/material';
import { Handle, Position, NodeProps } from 'reactflow';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';

/**
 * Success Block - Terminal node for successful testcase completion
 * Only has input handle (no outputs)
 */
export const SuccessBlock: React.FC<NodeProps> = ({ selected }) => {
  return (
    <Box
      sx={{
        width: 100,
        height: 100,
        borderRadius: '50%',
        background: '#10b981',
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
      <CheckCircleIcon sx={{ color: 'white', fontSize: 40 }} />
      <Typography color="white" fontWeight="bold" fontSize={12} mt={0.5}>
        SUCCESS
      </Typography>
      
      {/* Input handle only */}
      <Handle
        type="target"
        position={Position.Left}
        id="input"
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

