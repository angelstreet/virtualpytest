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
 * Now uses rectangular style like Campaign Builder
 */
export const TerminalBlock: React.FC<TerminalBlockProps> = ({ label, color, selected, dragging }) => {
  // Get colors based on type
  const getBgColor = () => {
    if (color === '#10b981') return '#e8f5e9'; // PASS - green background
    if (color === '#ef4444') return '#ffebee'; // FAIL - red background
    return '#f5f5f5';
  };

  const getTextColor = () => {
    if (color === '#10b981') return '#2e7d32'; // PASS - dark green text
    if (color === '#ef4444') return '#c62828'; // FAIL - dark red text
    return '#616161';
  };

  const getBorderColor = () => {
    if (color === '#10b981') return '#4caf50'; // PASS - green border
    if (color === '#ef4444') return '#f44336'; // FAIL - red border
    return '#9e9e9e';
  };
  
  return (
    <Box
      sx={{
        minWidth: 120,
        minHeight: 60,
        background: getBgColor(),
        border: selected ? '3px solid #fbbf24' : `2px solid ${getBorderColor()}`,
        borderRadius: 2,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontWeight: 'bold',
        color: getTextColor(),
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
      <Typography variant="body1" fontWeight="bold" color={getTextColor()}>
        {label}
      </Typography>
      
      {/* Transparent larger handle for better grabbing */}
      <Handle
        type="target"
        position={Position.Top}
        id="input-hitarea"
        style={{
          background: 'transparent',
          width: 32,
          height: 32,
          borderRadius: '50%',
          border: 'none',
          top: -16,
          pointerEvents: 'all',
        }}
      />
      
      {/* Visible input handle at top - circle */}
      <Handle
        type="target"
        position={Position.Top}
        id="input"
        style={{
          background: getBorderColor(),
          width: 20,
          height: 20,
          borderRadius: '50%',
          border: '2px solid white',
          top: -10,
          pointerEvents: 'none',
        }}
      />
    </Box>
  );
};
